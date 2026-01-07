import Utils.logger as loggerManager

from typing import List, Optional
from pyModbusTCP.client import ModbusClient


class ModbusClientWrapper:
    """Wrapper para o cliente ModbusTCP que de fato cria os clientes Modbus e expõe funções de escrita e leitura."""
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 5.0,
        client: Optional[str] = None,
        holding_registers: Optional[List[str]] = None,
    ):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name(client if client else "Module no named")
        self.holding_registers = holding_registers

        try:
            self.client = ModbusClient(
                host=host, port=port, auto_open=False, auto_close=False, timeout=timeout
            )

            if not self.client.open():
                self.logger.logger.warning(
                    f"Conexão não estabelecida para {host}:{port}."
                )
                return

            self.logger.logger.info(
                f"Cliente {client if client else 'Module no named'} criado no endereço {host}:{port}"
            )

            self.logger.set_name("MPS_Client")
        except Exception as e:
            self.logger = loggerManager.LoggerManager()
            self.logger.set_name("ModbusClientWrapper")
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"Erro ao criar cliente Modbus: {e}")
            raise e

    """ Operações assíncronas de escrita de registros. """
    def write_register(self, address: int, values: int) -> bool:
        try:
            res = self.client.write_single_register(address, values)

            if not res:
                self.logger.logger.warning(
                    f"Falha ao escrever registros no endereço {address} com valor {values}."
                )
                return False

            return True

        except Exception as e:
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"Erro ao escrever registros: {e}")
            return False

    """ Operações assíncronas de leitura de registros. """
    def read_holding_register(self, address: int, count: int) -> Optional[List[int]]:
        try:
            res = self.client.read_holding_registers(address, count)

            if res is None:
                self.logger.logger.warning(
                    f"Falha ao ler registros no endereço {address} com contagem {count}."
                )
                return None

            return res

        except Exception as e:
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"Erro ao ler registros: {e}")
            return None

    """ Propriedade para obter o nome do cliente Modbus. """
    @property
    def name(self) -> str:
        return self.client
