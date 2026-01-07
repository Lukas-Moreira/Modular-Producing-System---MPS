import asyncio
import Utils.logger as loggerManager

from typing import Optional
from States.PLCState import PLC
from dataclasses import dataclass
from Client.ModbusClientWrapper import ModbusClientWrapper

PLC_ROLE_MAP = {
    "MPS_HANDLING": "handling",
    "MPS_PRESSING": "pressing",
    "MPS_SORTING":  "sorting",
}

@dataclass
class Piece:
    """ Representa uma peça no sistema MES. """
    id: int

class MES:
    """ Classe principal do MES, gerenciando múltiplos PLCs conectados via Modbus. """
    def __init__(self, clients: Optional[dict[str, ModbusClientWrapper]] = None):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name('MES of MPS')

        self.clients = clients or {}
        self.plcs: dict[str, PLC] = {}

        if not self.clients:
            self.logger.set_level("ERROR")
            self.logger.logger.error("MES inicializado sem clientes Modbus.")
            raise ValueError("MES inicializado sem clientes Modbus.")

        self._build_plcs()

    """ Construir objetos PLC para cada cliente Modbus fornecido. """
    def _build_plcs(self):
        for name, modbus_client in self.clients.items():
            self.plcs[name] = PLC(
                name=name, 
                client=modbus_client
            )
        
        try:
            for plc_name, plc in self.plcs.items():
                if plc_name in PLC_ROLE_MAP:
                    setattr(self, PLC_ROLE_MAP[plc_name], plc)
        except KeyError as e:
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"PLC necessário não encontrado: {e}")
            raise KeyError(f"PLC necessário não encontrado: {e}")

    """ Manter a comunicação e o estado dos PLCs. """
    def get_plc(self, name: str) -> PLC:
        try:
            return self.plcs[name]
        except KeyError:
            raise KeyError(f"PLC '{name}' não encontrado no MES.")
        
    
