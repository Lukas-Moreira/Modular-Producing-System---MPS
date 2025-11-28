# modbus_client.py
from pyModbusTCP.client import ModbusClient
from typing import List, Optional
import logging

class ModbusClientWrapper:
    """Wrapper para cliente Modbus com tratamento de erros robusto"""
    
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.client = ModbusClient(
            host=host,
            port=port,
            auto_open=True,
            auto_close=True,
            timeout=timeout
        )
        self.host = host
        self.port = port
        self.logger = logging.getLogger('ModbusClient')
    
    def test_connection(self) -> bool:
        """Testa conectividade com servidor Modbus"""
        try:
            result = self.client.read_coils(0, 1)
            return result is not None
        except Exception as e:
            self.logger.error(f"Erro teste conexão: {e}")
            return False
    
    def read_coils(self, address: int, count: int) -> Optional[List[bool]]:
        """Lê registradores COIL"""
        try:
            return self.client.read_coils(address, count)
        except Exception as e:
            self.logger.error(f"Erro lendo coils {address}-{address+count-1}: {e}")
            return None
    
    def read_discrete_inputs(self, address: int, count: int) -> Optional[List[bool]]:
        """Lê DISCRETE INPUTS"""
        try:
            return self.client.read_discrete_inputs(address, count)
        except Exception as e:
            self.logger.error(f"Erro lendo discrete inputs {address}-{address+count-1}: {e}")
            return None
    
    def read_holding_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Lê HOLDING REGISTERS"""
        try:
            return self.client.read_holding_registers(address, count)
        except Exception as e:
            self.logger.error(f"Erro lendo holding registers {address}-{address+count-1}: {e}")
            return None
    
    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Lê INPUT REGISTERS"""
        try:
            return self.client.read_input_registers(address, count)
        except Exception as e:
            self.logger.error(f"Erro lendo input registers {address}-{address+count-1}: {e}")
            return None
