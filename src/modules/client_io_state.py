from __future__ import annotations

import threading
from typing import Dict, List, Optional


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

    def set_input(self, address: int, value: bool) -> None:
        with self._lock:
            for entry in self.inputs:
                if int(entry.get("addr")) == int(address):
                    entry["state"] = bool(value)
                    return
            # se não existir, adiciona
            self.inputs.append(
                {"addr": int(address), "state": bool(value), "description": ""}
            )

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


__all__ = ["ClientIOState", "ClientIOStateManager"]
