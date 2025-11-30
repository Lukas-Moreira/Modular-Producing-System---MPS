"""Edge detection helper for Modbus digital inputs.

Fornece uma pequena classe `EdgeMonitor` que pode:
- Aceitar um dicionário de mapeamento (com `start_address` e `count`) ou uma lista explícita de endereços.
- Manter o estado anterior para cada endereço e detetar bordas ascendentes/descendentes.
- Chamar callbacks registados quando uma borda é detetada.
- Processar instantâneos (um dicionário endereço->bool) para que possa ser integrado com qualquer loop de leitura Modbus.

Exemplo de utilização:

    from src.modules.edge_handler import EdgeMonitor

    # exemplo de mapeamento (proveniente de config.cfg.get(‘modbus_mapping.digital_inputs’))
    mapping = {“start_address”: 0, “count”: 8}

    # assinatura de retorno de chamada: fn(endereço: int, borda: str, antigo: bool, novo: bool)
    def on_edge(addr, edge, old, new):
        print(f“Borda em {addr}: {edge} ({old} -> {new})”)

    monitor = EdgeMonitor(mapping=mapping)
    monitor.register_callback (on_edge)

    # No seu loop de leitura, produza um dicionário de instantâneos: {address: bool}
    snapshot = {0: False, 1: True, 2: False}
    monitor.process_snapshot(snapshot)
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, overload
import logging

from services.enums import Verbose

logger = logging.getLogger(__name__)


def mapping_to_addresses(mapping: Dict, verbose: Optional[Verbose] = None) -> List[int]:
    """Converte um mapping com `start_address` e `count` em lista de endereços.

    Se a chave `addresses` estiver presente e for uma lista, retorna-a diretamente.
    """
    if not mapping:
        return []
    if isinstance(mapping.get("addresses"), list):
        return list(mapping["addresses"])
    start = int(mapping.get("start_address", 0))
    count = int(mapping.get("count", 0))
    list_map = [start + i for i in range(count)]

    if verbose == 2:
        print(f"List_map created: \n {list_map}")

    return list_map


class EdgeMonitor:
    """Classe para detecção de bordas (rising/falling) em endereços digitais.

    Este componente permite monitorar mudanças de estado em um conjunto de
    endereços binários (ex.: coils ou discrete inputs Modbus), identificando
    transições de 0→1 (rising) e 1→0 (falling).

    1. Defina os endereços a serem monitorados
    - usando `mapping=`: dicionário com `{start_address, count}`
        (ex.: mapping={"start_address": 0, "count": 8})
    - ou usando `addresses=`: lista/iterável de endereços individuais
        (ex.: addresses=[1, 5, 7, 12])

    2. Escolha como fornecer as leituras:
    A) Polling automático
        - Passe um `read_snapshot` (callable que retorna um dict {address: bool})
        - Chame `start()` para iniciar a thread de monitoramento.
        - A cada leitura, bordas detectadas serão notificadas via callbacks.

    B) Processamento manual
        - Quando já tiver uma leitura externa (ex.: resposta Modbus), chame diretamente:

            process_snapshot(snapshot)

            onde `snapshot` é um dict {address: bool}.

    3. A classe gera eventos de borda:
    - on_rising(address)
    - on_falling(address)
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EdgeMonitor, cls).__new__(cls)
            cls._initialized = False
        return cls._instance

    def __init__(
        self,
        mapping: Optional[Dict] = None,
        addresses: Optional[Iterable[int]] = None,
        read_snapshot: Optional[Callable[[], Dict[int, bool]]] = None,
        poll_interval: float = 0.1,
        # opcional: monitoramento por cliente
        clients: Optional[Dict[str, Any]] = None,
        client_read_fn: Optional[Callable[[str, Any], Dict[int, bool]]] = None,
        client_poll_interval: Optional[float] = None,
    ) -> None:

        if self.__class__._initialized:
            return

        self.__class__._initialized = True

        if mapping is not None:
            self.addresses = mapping_to_addresses(mapping, verbose=Verbose.DEBUG)
        elif addresses is not None:
            self.addresses = list(addresses)
        else:
            self.addresses = []

        # estado anterior (inicia como False para todos)
        # estados estáveis confirmados
        self._prev: Dict[int, bool] = {addr: False for addr in self.addresses}
        # para debouncing: candidato e contadores
        self._candidate: Dict[int, bool] = {}
        self._candidate_count: Dict[int, int] = {}
        # quantas leituras consecutivas são necessárias para confirmar mudança
        self.debounce_count: int = 1

        # callbacks: fn(address, edge, old, new)
        self._callbacks: List[Callable[[int, str, bool, bool], None]] = []

        # polling
        self.read_snapshot = read_snapshot
        self.poll_interval = float(poll_interval)
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()

        # clients monitoring (paralelo)
        # clientes: dict chave->client_obj
        self.clients = clients or {}
        # função: (client_key, client_obj) -> {address: bool}
        self.client_read_fn = client_read_fn
        # por-client threads
        self._client_threads: Dict[str, threading.Thread] = {}
        # eventos de controle por cliente (não necessário mas mantido simples)
        self.client_poll_interval = (
            float(client_poll_interval) if client_poll_interval else self.poll_interval
        )

    def register_callback(self, cb: Callable[[int, str, bool, bool], None]) -> None:
        """Registra um callback que será chamado em toda borda detectada."""
        self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable[[int, str, bool, bool], None]) -> None:
        try:
            self._callbacks.remove(cb)
        except ValueError:
            pass

    def _emit(self, addr: int, edge: str, old: bool, new: bool) -> None:
        for cb in list(self._callbacks):
            try:
                cb(addr, edge, old, new)
            except Exception:
                logger.exception("Erro no callback de borda para %s", addr)

    def process_snapshot(self, snapshot: Dict[int, bool]) -> List[tuple]:
        """Processa um snapshot `address -> bool`, detecta mudanças e emite eventos.

        Retorna uma lista de tuplas (address, edge, old, new) detectadas.
        """
        events = []
        # Garantir que endereços novos sejam inicializados
        for addr in snapshot.keys():
            if addr not in self._prev:
                self._prev[addr] = False
                if addr not in self.addresses:
                    self.addresses.append(addr)

        for addr in self.addresses:
            old = self._prev.get(addr, False)
            new = bool(snapshot.get(addr, False))

            # sem debouncing (comportamento padrão)
            if self.debounce_count <= 1:
                if new != old:
                    edge = "rising" if new else "falling"
                    self._prev[addr] = new
                    events.append((addr, edge, old, new))
                    self._emit(addr, edge, old, new)
                continue

            # com debouncing: aguardar 'debounce_count' leituras consecutivas
            cand = self._candidate.get(addr)
            if cand is None or cand != new:
                self._candidate[addr] = new
                self._candidate_count[addr] = 1
            else:
                self._candidate_count[addr] = self._candidate_count.get(addr, 0) + 1

            if self._candidate_count.get(addr, 0) >= self.debounce_count:
                # confirmar mudança
                if new != old:
                    edge = "rising" if new else "falling"
                    self._prev[addr] = new
                    events.append((addr, edge, old, new))
                    self._emit(addr, edge, old, new)
                # reset candidato
                self._candidate_count[addr] = 0

        return events

    def _poll_loop(self) -> None:
        while self._running.is_set():
            try:
                if callable(self.read_snapshot):
                    snapshot = self.read_snapshot() or {}
                else:
                    snapshot = {}
                self.process_snapshot(snapshot)
            except Exception:
                logger.exception("Erro no loop de polling do EdgeMonitor")
            time.sleep(self.poll_interval)

    def _client_poll_loop(self, client_key: str, client_obj: Any) -> None:
        """Loop de polling dedicado para um cliente específico.

        A função `client_read_fn` deve retornar um dict {address: bool} para
        aquele cliente. As chaves serão prefixadas com `client_key:` para
        manter separação entre endereços iguais de diferentes clientes.
        """
        if not callable(self.client_read_fn):
            return

        while self._running.is_set():
            try:
                snapshot = self.client_read_fn(client_key, client_obj) or {}
                # prefixa chaves para distinguir clientes
                prefixed = {
                    f"{client_key}:{addr}": bool(val) for addr, val in snapshot.items()
                }
                self.process_snapshot(prefixed)
            except Exception:
                logger.exception("Erro no loop de polling do cliente %s", client_key)
            time.sleep(self.client_poll_interval)

    def start(self, background: bool = True) -> None:
        """Inicia o monitoramento em loop. Se `read_snapshot` não foi fornecido,
        o loop apenas dorme e não faz leituras.
        """
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        # thread global: somente se uma função de leitura global foi fornecida
        if callable(self.read_snapshot):
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
        else:
            self._thread = None

        # iniciar threads por cliente, se fornecidos
        if self.clients and callable(self.client_read_fn):
            for key, client in list(self.clients.items()):
                if key in self._client_threads and self._client_threads[key].is_alive():
                    continue
                t = threading.Thread(
                    target=self._client_poll_loop, args=(key, client), daemon=True
                )
                self._client_threads[key] = t
                t.start()

        # depois de iniciar as threads por cliente
        print(
            f"[EdgeMonitor] global_thread_started={bool(self._thread)} clients_monitors={len(self._client_threads)} debounce_count={self.debounce_count}"
        )

    def stop(self) -> None:
        """Para o loop de polling (se estiver rodando)."""
        self._running.clear()
        if self._thread:
            try:
                self._thread.join(timeout=1.0)
            except Exception:
                pass
            self._thread = None
        # terminar threads dos clientes
        for key, t in list(self._client_threads.items()):
            if t and t.is_alive():
                t.join(timeout=1.0)
        self._client_threads.clear()

    @classmethod
    def is_initialized(cls):
        return getattr(cls, "_initialized", False)


__all__ = ["EdgeMonitor", "mapping_to_addresses"]
