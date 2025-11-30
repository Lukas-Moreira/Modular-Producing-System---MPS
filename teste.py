# config.py
import json
import os
from pathlib import Path
from typing import Dict, Any, overload


class ConfigurationManager:
    """Gerenciador centralizado de configurações da aplicação

    Utiliza o padrão Singleton para garantir uma única instância
    e mantém a configuração carregada do arquivo JSON.

    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigurationManager, cls).__new__(cls)
        return cls._instance

    # def __init__(self, config_file: str = "../../.cfg/config.json"):
    def __init__(self, config_file: str = "./config.json"):

        if getattr(self.__class__, "_initialized", False):
            return

        # Garante que o diretorio seja baseado no arquivo local deste modulo
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        # Define o a instancia como inicializada para evitar re-inicializações
        self._initialized = True
        self.config_file = os.path.join(self.BASE_DIR, config_file)

        self.config_file = Path(self.config_file)
        print(f"State on config file: {self.config_file}")
        self.default_config = {
            "Source": {
                "connection": {
                    "host": "127.0.0.1",
                    "port": 5021,
                    "timeout": 5.0,
                    "auto_open": True,
                    "auto_close": True
                },
                "modbus_mapping": {
                    "digital_inputs": {
                        "count": 30,
                        "start_address": 0,
                        "register_type": "COIL",
                        "description": "Botões e Sensores"
                    },
                    "digital_outputs": {
                        "count": 29,
                        "start_address": 0,
                        "register_type": "DISCRETE_INPUT",
                        "description": "Motores, Luzes e Válvulas"
                    },
                    "analog_inputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "HOLDING_REGISTER",
                        "description": "Sensores Analógicos"
                    },
                    "analog_outputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "INPUT_REGISTER",
                        "description": "Setpoints e Comandos"
                    }
                },
                "display": {
                    "scale_factor": 100,
                    "decimal_places": 2,
                    "show_inactive_analogs": False
                },
                "files": {
                    "descriptions_file": "factory_io_descriptions.json",
                    "log_level": "INFO"
                }
            },
            "Conveyor": {
                "connection": {
                    "host": "127.0.0.1",
                    "port": 5021,
                    "timeout": 5.0,
                    "auto_open": True,
                    "auto_close": True
                },
                "modbus_mapping": {
                    "digital_inputs": {
                        "count": 30,
                        "start_address": 0,
                        "register_type": "COIL",
                        "description": "Botões e Sensores"
                    },
                    "digital_outputs": {
                        "count": 29,
                        "start_address": 0,
                        "register_type": "DISCRETE_INPUT",
                        "description": "Motores, Luzes e Válvulas"
                    },
                    "analog_inputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "HOLDING_REGISTER",
                        "description": "Sensores Analógicos"
                    },
                    "analog_outputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "INPUT_REGISTER",
                        "description": "Setpoints e Comandos"
                    }
                },
                "display": {
                    "scale_factor": 100,
                    "decimal_places": 2,
                    "show_inactive_analogs": False
                },
                "files": {
                    "descriptions_file": "factory_io_descriptions.json",
                    "log_level": "INFO"
                }
            },
            "Deposit": {
                "connection": {
                    "host": "127.0.0.1",
                    "port": 5021,
                    "timeout": 5.0,
                    "auto_open": True,
                    "auto_close": True
                },
                "modbus_mapping": {
                    "digital_inputs": {
                        "count": 30,
                        "start_address": 0,
                        "register_type": "COIL",
                        "description": "Botões e Sensores"
                    },
                    "digital_outputs": {
                        "count": 29,
                        "start_address": 0,
                        "register_type": "DISCRETE_INPUT",
                        "description": "Motores, Luzes e Válvulas"
                    },
                    "analog_inputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "HOLDING_REGISTER",
                        "description": "Sensores Analógicos"
                    },
                    "analog_outputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "INPUT_REGISTER",
                        "description": "Setpoints e Comandos"
                    }
                },
                "display": {
                    "scale_factor": 100,
                    "decimal_places": 2,
                    "show_inactive_analogs": False
                },
                "files": {
                    "descriptions_file": "factory_io_descriptions.json",
                    "log_level": "INFO"
                }
            },
            "UR_Robot": {
                "connection": {
                    "host": "127.0.0.1",
                    "port": 5021,
                    "timeout": 5.0,
                    "auto_open": True,
                    "auto_close": True
                },
                "modbus_mapping": {
                    "digital_inputs": {
                        "count": 30,
                        "start_address": 0,
                        "register_type": "COIL",
                        "description": "Botões e Sensores"
                    },
                    "digital_outputs": {
                        "count": 29,
                        "start_address": 0,
                        "register_type": "DISCRETE_INPUT",
                        "description": "Motores, Luzes e Válvulas"
                    },
                    "analog_inputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "HOLDING_REGISTER",
                        "description": "Sensores Analógicos"
                    },
                    "analog_outputs": {
                        "count": 8,
                        "start_address": 0,
                        "register_type": "INPUT_REGISTER",
                        "description": "Setpoints e Comandos"
                    }
                },
                "display": {
                    "scale_factor": 100,
                    "decimal_places": 2,
                    "show_inactive_analogs": False
                },
                "files": {
                    "descriptions_file": "factory_io_descriptions.json",
                    "log_level": "INFO"
                }
            }
        }
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Carrega configuração do arquivo ou cria padrão"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    return self._deep_merge(self.default_config, loaded_config)
            else:
                self._save_config()
                return self.default_config.copy()
        except Exception as e:
            print(f"⚠️ Erro carregando configuração, usando padrão: {e}")
            return self.default_config.copy()

    def _deep_merge(self, default: Dict, override: Dict) -> Dict:
        """Merge profundo entre dicionários"""
        result = default.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save_config(self):
        """Salva configuração atual no arquivo"""
        try:
            to_save = getattr(self, "config", self.default_config)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Erro salvando configuração: {e}")

    def get(self, key_path: str, default=None):
        """Obtém valor usando caminho pontuado"""
        keys = key_path.split(".")
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """Define valor usando caminho pontuado"""
        keys = key_path.split(".")
        config = self.config
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        config[keys[-1]] = value
        self._save_config()

cfg = ConfigurationManager()
print("Configuração carregada:")
print(json.dumps(cfg.config, indent=2, ensure_ascii=False))