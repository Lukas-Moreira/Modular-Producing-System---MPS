import json
import Utils.logger as loggerManager

from pathlib import Path
from typing import Dict, Any

class ConfigurationManager:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigurationManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    """ Gerenciador de configuração que carrega parâmetros de um arquivo JSON. """
    def __init__(self, config_file: str = "./config.json"):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name('ConfigurationManager')
        self.config_file = Path(config_file).resolve()
        try:
            self.logger.logger.info(f"Carregando configuração de {self.config_file}")
            self.config = self.load_config()
        except Exception as e:
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"Erro ao carregar configuração: {e}")
            raise

    def load_config(self) -> Dict[str, Any]:
        
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")

            with open(self.config_file, 'r', encoding='utf-8') as file:
                self.config_clps = json.load(file)

            self.logger.logger.info(f"Configuração carregada de {self.config_clps.keys()}")
            return self.config_clps
        except json.JSONDecodeError as e:
            self.logger.set_level("ERROR")
            self.logger.logger.error(f"Erro ao decodificar JSON: {e}")
            raise

""" Instância única do gerenciador de configuração. """
config = ConfigurationManager()