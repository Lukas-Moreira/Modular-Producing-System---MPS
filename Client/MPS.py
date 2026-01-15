import json
import logging
import Utils.logger as loggerManager

from pathlib import Path
from typing import Dict, Any
from itertools import islice
from Utils.config import ConfigurationManager
from Client.ModbusClientWrapper import ModbusClientWrapper

class MPS:
    
    def __init__(self, cfg: ConfigurationManager):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name('MPS_Client')

        self.modbus_clients: dict[str, ModbusClientWrapper] = {}

        clps = list(islice(cfg.config_clps.keys(), 0, 3))
        
        for clp in clps:
            self.logger.logger.info(f"Iniciando cliente para CLP: {clp}")
            clp_config = cfg.config_clps[clp]['connection']
            clp_holding_registers = cfg.config_clps[clp]['holding_registers']

        

            try:
                modbus_client = ModbusClientWrapper(
                    host=clp_config['host'],
                    port=clp_config['port'],
                    timeout=clp_config.get('timeout', 5.0),
                    client=clp,
                    holding_registers=clp_holding_registers
                )

                if modbus_client.client.is_open:
                    self.modbus_clients[clp] = modbus_client
            
            except Exception as e:
                print(e)
                self.logger.set_level("ERROR")
                self.logger.logger.error(f"Erro ao iniciar cliente para {clp}: {e}")
        
        try:
            self.logger.logger.info(f"Todos os clientes Modbus inicializados: {list(self.modbus_clients.keys())}")
        except Exception as e:
            self.logger.set_level("ERROR")
            print(e)
            self.logger.logger.error(f"Erro ao listar clientes Modbus: {e}")