from dataclasses import dataclass
from typing import Any, Dict, Optional
from Client.ModbusClientWrapper import ModbusClientWrapper

@dataclass
class PLCState:
    has_piece:      bool = False
    running:        bool = False
    stopped:        bool = False
    emergency:      bool = False
    remote_enabled: bool = False


class PLC:
    """ Representa um Controlador Lógico Programável (PLC) conectado via Modbus. """
    def __init__(self, name: str, client: Optional[ModbusClientWrapper] = None):
        self.name = name
        self.client = client

        if client is None:
            raise ValueError(f"PLC '{name}' inicializado sem ModbusClientWrapper")
        
        self.map = client.holding_registers
        self.state = PLCState()
    
    """ Obter o endereço de um registro pelo nome. """
    def addr(self, reg_name: str) -> int:
        try:
            return self.map[reg_name]
        except KeyError:
            raise KeyError(f"Registro '{reg_name}' não encontrado no mapa de registros do PLC '{self.name}'.")
    
    """ Operações assíncronas de leitura e escrita de registros. """
    async def read_word(self, reg_name: str) -> int:
        address = self.addr(reg_name)
        return await self.client.read_holding_register(address, 1)
    
    """ Operações assíncronas de escrita de registros. """
    async def write_word(self, reg_name: str, value: int) -> None:
        address = self.addr(reg_name)
        await self.client.write_register(address, value)

    """ Operação de pulso assíncrona em um registro. """
    async def pulse(self, reg_name: str, on_value: int = 1, off_value: int = 0, pulse_ms: int = 100) -> None:
        await self.write_word(reg_name, on_value)
        await self.client.sleep_ms(pulse_ms)
        await self.write_word(reg_name, off_value)

    """ Atualizar o estado do PLC lendo os registros relevantes. """
    async def refresh_state(self) -> None:
        self.state.has_piece      = bool(await self.read_word("MB_Has_Piece"))
        self.state.running        = bool(await self.read_word("MB_Running"))
        self.state.stopped        = bool(await self.read_word("MB_Stopped"))
        self.state.emergency      = bool(await self.read_word("MB_Emergency"))
        self.state.remote_enabled = bool(await self.read_word("MB_Remote_Enabled"))