from __future__ import annotations

import threading
from typing import Dict, List, Optional, Callable
import logging


class ClientIOState:
    """Armazena estado de I/O para um cliente com proteção por lock.

    - `inputs` e `outputs` são dicionários address->bool (mantive dict para
      flexibilidade; podem ser tratados como "listas" conceituais).
    - Métodos `get_inputs_snapshot()` / `get_outputs_snapshot()` retornam cópias
      protegidas.
    - `set_input(address, value)` é a API para mutação (destinada a ser usada
      somente pelo EdgeMonitor via callback registrado).
    """

    def __init__(self, client_key: str):
        self.client_key = client_key
        self._lock = threading.RLock()
        # agora usamos listas de dicts: {'addr': int, 'state': bool, 'description': str}
        self.inputs: List[Dict[str, object]] = []
        self.outputs: List[Dict[str, object]] = []

    def set_input(self, address: int, value: bool, notify: bool = True) -> None:
        # altera o estado apenas se houver mudança e notifica listeners
        old_state = False
        changed = False
        with self._lock:
            for entry in self.inputs:
                if int(entry.get("addr")) == int(address):
                    old_state = bool(entry.get("state", False))
                    if old_state != bool(value):
                        entry["state"] = bool(value)
                        changed = True
                    break
            else:
                # se não existir, considera old_state False e adiciona
                self.inputs.append(
                    {"addr": int(address), "state": bool(value), "description": ""}
                )
                old_state = False
                changed = True

        if changed and notify:
            # notificar fora do lock para evitar deadlocks
            try:
                ClientIOStateManager._notify_listeners(
                    self.client_key, int(address), old_state, bool(value)
                )
            except Exception:
                pass

    def set_output(self, address: int, value: bool) -> None:
        with self._lock:
            for entry in self.outputs:
                if int(entry.get("addr")) == int(address):
                    entry["state"] = bool(value)
                    return
            self.outputs.append(
                {"addr": int(address), "state": bool(value), "description": ""}
            )

    def get_inputs_snapshot(self) -> Dict[int, bool]:
        with self._lock:
            # retornar cópia da lista
            return [dict(e) for e in self.inputs]

    def get_outputs_snapshot(self) -> Dict[int, bool]:
        with self._lock:
            return [dict(e) for e in self.outputs]

    def initialize_inputs(
        self, addresses: List[int], descriptions: Optional[Dict[int, str]] = None
    ) -> None:
        """Inicializa a lista de inputs com os endereços e descrições fornecidas."""
        with self._lock:
            desc_map = descriptions or {}
            self.inputs = [
                {
                    "addr": int(addr),
                    "state": False,
                    "description": str(desc_map.get(addr, "")),
                }
                for addr in addresses
            ]

    def initialize_outputs(
        self, addresses: List[int], descriptions: Optional[Dict[int, str]] = None
    ) -> None:
        with self._lock:
            desc_map = descriptions or {}
            self.outputs = [
                {
                    "addr": int(addr),
                    "state": False,
                    "description": str(desc_map.get(addr, "")),
                }
                for addr in addresses
            ]


class ClientIOStateManager:
    """Gerencia instâncias singleton de ClientIOState por client_key."""

    _instances: Dict[str, ClientIOState] = {}
    _global_lock = threading.RLock()
    # listeners: fn(client_key: str, addr: int, old: bool, new: bool)
    _listeners: List[Callable[[str, int, bool, bool], None]] = []

    @classmethod
    def get_state(cls, client_key: str) -> ClientIOState:
        with cls._global_lock:
            if client_key not in cls._instances:
                cls._instances[client_key] = ClientIOState(client_key)
            return cls._instances[client_key]

    @classmethod
    def list_keys(cls) -> List[str]:
        with cls._global_lock:
            return list(cls._instances.keys())

    @classmethod
    def register_listener(cls, cb: Callable[[str, int, bool, bool], None]) -> None:
        with cls._global_lock:
            cls._listeners.append(cb)

    @classmethod
    def unregister_listener(cls, cb: Callable[[str, int, bool, bool], None]) -> None:
        with cls._global_lock:
            try:
                cls._listeners.remove(cb)
            except ValueError:
                pass

    @classmethod
    def _notify_listeners(
        cls, client_key: str, addr: int, old: bool, new: bool
    ) -> None:
        # chamar cópia para evitar problemas se listeners modificarem a lista
        with cls._global_lock:
            listeners = list(cls._listeners)
        logger = logging.getLogger("ClientIOStateManager")
        # info de debug sobre notificações
        try:
            logger.info(f"notify -> {client_key}:{addr} {old}->{new}")
        except Exception:
            pass

        for cb in listeners:
            try:
                cb(client_key, addr, old, new)
            except Exception:
                logger.exception(
                    "Erro em listener de ClientIOStateManager para %s:%s",
                    client_key,
                    addr,
                )


__all__ = ["ClientIOState", "ClientIOStateManager"]
