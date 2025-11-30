# factory_io_scanner_complete.py
from pyModbusTCP.client import ModbusClient
import time
import logging
import sys
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

class CustomFormatter(logging.Formatter):
    """Formatador personalizado para logs com tratamento de encoding"""
    def format(self, record):
        msg = super().format(record)
        try:
            return msg.encode('utf-8').decode('utf-8')
        except UnicodeError:
            return msg.encode('ascii', errors='ignore').decode('ascii')

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configura sistema de logging
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger('FactoryIO')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    try:
        # Handler para arquivo
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_path / 'factory_io_scanner.log', 
            encoding='utf-8'
        )
        file_formatter = CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_formatter = CustomFormatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
    except Exception as e:
        print(f"⚠️ Erro configurando logging: {e}")
    
    return logger

class ConfigurationManager:
    """Gerenciador de configurações da aplicação"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.default_config = {
            "connection": {
                "host": "10.5.0.2",
                "port": 5021,
                "timeout": 5.0,
                "auto_open": True,
                "auto_close": True
            },
            "modbus_mapping": {
                "digital_inputs": {
                    "count": 16,
                    "start_address": 0,
                    "register_type": "COIL",
                    "description": "Botões e Sensores"
                },
                "digital_outputs": {
                    "count": 16,
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
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Carrega configuração do arquivo ou cria padrão"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge com configuração padrão
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
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self):
        """Salva configuração atual no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Erro salvando configuração: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Obtém valor da configuração usando caminho pontuado
        
        Args:
            key_path: Caminho tipo "connection.host"
            default: Valor padrão se não encontrado
        """
        keys = key_path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

class FactoryIOScanner:
    """Scanner I/O para Factory I/O com configuração flexível"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.logger = setup_logging(config_manager.get('files.log_level', 'INFO'))
        
        # Configuração da conexão
        conn_config = config_manager.config['connection']
        self.client = ModbusClient(
            host=conn_config['host'],
            port=conn_config['port'],
            auto_open=conn_config.get('auto_open', True),
            auto_close=conn_config.get('auto_close', True),
            timeout=conn_config.get('timeout', 5.0)
        )
        
        self.host = conn_config['host']
        self.port = conn_config['port']
        
        # Estruturas de dados
        self.io_data: List[Dict] = []
        self.custom_descriptions: Dict[str, str] = {}
        
        # Carrega descrições personalizadas
        self._load_custom_descriptions()
    
    def test_connection(self) -> bool:
        """
        Testa conectividade com o servidor Factory I/O
        
        Returns:
            True se conectado com sucesso, False caso contrário
        """
        try:
            result = self.client.read_coils(0, 1)
            if result is not None:
                self.logger.info(f"Conectado ao Factory I/O em {self.host}:{self.port}")
                self._print_configuration()
                return True
            else:
                self.logger.error("Falha na conexão - sem resposta do servidor")
                print(f"❌ Falha na conexão - sem resposta do servidor")
                return False
        except Exception as e:
            self.logger.error(f"Erro de conexão: {e}")
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def _print_configuration(self):
        """Exibe configuração detectada"""
        mapping = self.config_manager.config['modbus_mapping']
        print(f"✅ Conectado ao Factory I/O em {self.host}:{self.port}")
        print(f"🔧 Configuração detectada:")
        for io_type, config in mapping.items():
            print(f"   🔹 {config['description']}: {config['count']} "
                  f"({config['register_type']} {config['start_address']}-"
                  f"{config['start_address'] + config['count'] - 1})")
    
    def scan_all_ios(self) -> bool:
        """
        Executa escaneamento completo de todos os I/Os configurados
        
        Returns:
            True se escaneamento bem-sucedido
        """
        print("\n🔍 INICIANDO ESCANEAMENTO COMPLETO...")
        print("=" * 80)
        
        if not self.test_connection():
            return False
        
        self.io_data.clear()
        
        try:
            # Escaneia todos os tipos configurados
            self._scan_digital_inputs()
            self._scan_digital_outputs()
            self._scan_analog_inputs()
            self._scan_analog_outputs()
            
            # Ordena dados
            self.io_data.sort(key=lambda x: (x['type_order'], x['address']))
            
            print(f"✅ Escaneamento concluído: {len(self.io_data)} I/Os encontrados")
            self.logger.info(f"Escaneamento concluído: {len(self.io_data)} I/Os")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante escaneamento: {e}")
            print(f"❌ Erro durante escaneamento: {e}")
            return False
    
    def _scan_digital_inputs(self):
        """Escaneia entradas digitais (DISCRETE INPUTS) - Botões e Sensores"""
        config = self.config_manager.config['modbus_mapping']['digital_inputs']
        
        try:
            discretes = self.client.read_discrete_inputs(
                config['start_address'], 
                config['count']
            )
            
            if discretes:
                for i, value in enumerate(discretes):
                    address = config['start_address'] + i
                    key = f"DI_{address:02d}"
                    
                    self.io_data.append({
                        'address': address,
                        'tag': f'DI{address:02d}',
                        'type_order': 1,
                        'io_type': 'ENTRADA',
                        'data_type': 'DIGITAL',
                        'modbus_type': 'COIL',
                        'state': 'ON' if value else 'OFF',
                        'state_emoji': '🟢' if value else '⚫',
                        'raw_value': value,
                        'display_value': 'ON' if value else 'OFF',
                        'description': self.custom_descriptions.get(key, ""),
                        'key': key,
                        'function': 'Botão/Sensor'
                    })
                    
        except Exception as e:
            self.logger.error(f"Erro lendo entradas digitais: {e}")
            raise
    
    def _scan_digital_outputs(self):
        """Escaneia saídas digitais (COILS) - Motores e Luzes"""
        config = self.config_manager.config['modbus_mapping']['digital_outputs']
        
        try:
            coils = self.client.read_coils(
                config['start_address'], 
                config['count']
            )
            
            if coils:
                for i, value in enumerate(coils):
                    address = config['start_address'] + i
                    key = f"DO_{address:02d}"
                    
                    self.io_data.append({
                        'address': address,
                        'tag': f'DO{address:02d}',
                        'type_order': 2,
                        'io_type': 'SAÍDA',
                        'data_type': 'DIGITAL',
                        'modbus_type': 'DISCRETE',
                        'state': 'ON' if value else 'OFF',
                        'state_emoji': '🔴' if value else '⚫',
                        'raw_value': value,
                        'display_value': 'ON' if value else 'OFF',
                        'description': self.custom_descriptions.get(key, ""),
                        'key': key,
                        'function': 'Motor/Luz/Válvula'
                    })
                    
        except Exception as e:
            self.logger.error(f"Erro lendo saídas digitais: {e}")
            raise
    
    def _scan_analog_inputs(self):
        """Escaneia entradas analógicas (HOLDING REGISTERS) - Sensores analógicos"""
        config = self.config_manager.config['modbus_mapping']['analog_inputs']
        scale_factor = self.config_manager.get('display.scale_factor', 100)
        decimal_places = self.config_manager.get('display.decimal_places', 2)
        show_inactive = self.config_manager.get('display.show_inactive_analogs', False)
        
        try:
            registers = self.client.read_holding_registers(
                config['start_address'], 
                config['count']
            )
            
            if registers:
                for i, value in enumerate(registers):
                    if show_inactive or value != 0:
                        address = config['start_address'] + i
                        key = f"AI_{address:02d}"
                        
                        real_value = value / scale_factor
                        display_value = f"{real_value:.{decimal_places}f}"
                        
                        self.io_data.append({
                            'address': address,
                            'tag': f'AI{address:02d}',
                            'type_order': 3,
                            'io_type': 'ENTRADA',
                            'data_type': 'ANALÓGICO',
                            'modbus_type': 'HOLDING',
                            'state': display_value,
                            'state_emoji': '📊',
                            'raw_value': value,
                            'display_value': display_value,
                            'real_value': real_value,
                            'description': self.custom_descriptions.get(key, ""),
                            'key': key,
                            'function': 'Sensor Analógico'
                        })
                        
        except Exception as e:
            self.logger.error(f"Erro lendo entradas analógicas: {e}")
            raise
    
    def _scan_analog_outputs(self):
        """Escaneia saídas analógicas (INPUT REGISTERS) - Setpoints e comandos"""
        config = self.config_manager.config['modbus_mapping']['analog_outputs']
        scale_factor = self.config_manager.get('display.scale_factor', 100)
        decimal_places = self.config_manager.get('display.decimal_places', 2)
        show_inactive = self.config_manager.get('display.show_inactive_analogs', False)
        
        try:
            registers = self.client.read_input_registers(
                config['start_address'], 
                config['count']
            )
            
            if registers:
                for i, value in enumerate(registers):
                    if show_inactive or value != 0:
                        address = config['start_address'] + i
                        key = f"AO_{address:02d}"
                        
                        real_value = value / scale_factor
                        display_value = f"{real_value:.{decimal_places}f}"
                        
                        self.io_data.append({
                            'address': address,
                            'tag': f'AO{address:02d}',
                            'type_order': 4,
                            'io_type': 'SAÍDA',
                            'data_type': 'ANALÓGICO',
                            'modbus_type': 'INPUT_REG',
                            'state': display_value,
                            'state_emoji': '📈',
                            'raw_value': value,
                            'display_value': display_value,
                            'real_value': real_value,
                            'description': self.custom_descriptions.get(key, ""),
                            'key': key,
                            'function': 'Setpoint/Comando'
                        })
                        
        except Exception as e:
            self.logger.error(f"Erro lendo saídas analógicas: {e}")
            raise
    
    def display_table(self, filter_type: str = 'ALL'):
        """
        Exibe tabela formatada com dados dos I/Os
        
        Args:
            filter_type: Tipo de filtro (ALL, ENTRADA, SAÍDA, DIGITAL, ANALÓGICO, ATIVO)
        """
        if not self.io_data:
            print("❌ Nenhum dado disponível. Execute primeiro o escaneamento.")
            return
        
        # Aplicar filtros
        filtered_data = self._apply_filter(filter_type)
        
        if not filtered_data:
            print(f"❌ Nenhum I/O encontrado com filtro: {filter_type}")
            return
        
        self._print_table(filtered_data, filter_type)
    
    def _apply_filter(self, filter_type: str) -> List[Dict]:
        """Aplica filtro aos dados"""
        if filter_type == 'ALL':
            return self.io_data
        elif filter_type == 'ENTRADA':
            return [io for io in self.io_data if io['io_type'] == 'ENTRADA']
        elif filter_type == 'SAÍDA':
            return [io for io in self.io_data if io['io_type'] == 'SAÍDA']
        elif filter_type == 'DIGITAL':
            return [io for io in self.io_data if io['data_type'] == 'DIGITAL']
        elif filter_type == 'ANALÓGICO':
            return [io for io in self.io_data if io['data_type'] == 'ANALÓGICO']
        elif filter_type == 'ATIVO':
            return [io for io in self.io_data if io['state'] not in ['OFF', '0', '0.00']]
        else:
            return self.io_data
    
    def _print_table(self, data: List[Dict], filter_type: str):
        """Imprime tabela formatada"""
        title = f"TABELA I/O FACTORY I/O - ({len(data)} registros)"
        if filter_type != 'ALL':
            title += f" - FILTRO: {filter_type}"
        
        print(f"\n📋 {title}")
        print("=" * 110)
        
        # Cabeçalho
        header = f"{'TAG':<6} {'MODBUS':<12} {'E/S':<8} {'TIPO':<10} {'ESTADO':<15} {'FUNÇÃO':<18} {'DESCRIÇÃO':<35}"
        print(header)
        print("-" * 110)
        
        # Dados
        for io in data:
            tag = io['tag']
            modbus_info = f"{io['modbus_type']} {io['address']}"
            io_type = io['io_type']
            data_type = io['data_type']
            state = f"{io['state_emoji']} {io['state']}"
            function = io['function']
            
            description = io['description'] or "[Pressione 8 para editar]"
            if len(description) > 32:
                description = description[:29] + "..."
            
            row = f"{tag:<6} {modbus_info:<12} {io_type:<8} {data_type:<10} {state:<15} {function:<18} {description:<35}"
            print(row)
        
        self._print_statistics(data)
    
    def _print_statistics(self, data: List[Dict]):
        """Imprime estatísticas dos dados"""
        print("-" * 110)
        
        digitais = len([io for io in data if io['data_type'] == 'DIGITAL'])
        analogicos = len([io for io in data if io['data_type'] == 'ANALÓGICO'])
        entradas = len([io for io in data if io['io_type'] == 'ENTRADA'])
        saidas = len([io for io in data if io['io_type'] == 'SAÍDA'])
        ativos = len([io for io in data if io['state'] not in ['OFF', '0', '0.00']])
        
        print(f"📊 ESTATÍSTICAS:")
        print(f"   🟢 Entradas: {entradas} | 🔴 Saídas: {saidas}")
        print(f"   ⚡ Digitais: {digitais} | 📊 Analógicos: {analogicos}")
        print(f"   🔥 Ativos: {ativos} | 📋 Total: {len(data)}")
    
    def edit_descriptions(self):
        """Editor interativo de descrições"""
        if not self.io_data:
            print("❌ Execute primeiro o escaneamento.")
            return
        
        print("\n✏️ EDITOR DE DESCRIÇÕES - FACTORY I/O")
        print("=" * 50)
        print("💡 Exemplos de descrições úteis:")
        print("   • DI01: 'Botão Start Linha 1'")
        print("   • DO05: 'Motor Esteira Principal'")
        print("   • AI02: 'Sensor Temperatura (°C)'")
        print("💡 Digite 'sair' para terminar\n")
        
        changes_made = False
        
        for io in self.io_data:
            current_desc = io['description'] or "[VAZIO]"
            
            print(f"\n🔧 {io['tag']} - {io['function']}")
            print(f"   Modbus: {io['modbus_type']} {io['address']}")
            print(f"   Estado: {io['state_emoji']} {io['state']}")
            print(f"   Descrição atual: {current_desc}")
            
            try:
                new_desc = input("   Nova descrição: ").strip()
            except KeyboardInterrupt:
                print("\n⚠️ Operação cancelada.")
                break
            
            if new_desc.lower() == 'sair':
                break
            
            if new_desc != io['description']:
                io['description'] = new_desc
                self.custom_descriptions[io['key']] = new_desc
                changes_made = True
                print(f"   ✅ {io['tag']} atualizado!")
        
        if changes_made:
            self._save_custom_descriptions()
            print(f"\n💾 Descrições salvas!")
    
    def _load_custom_descriptions(self):
        """Carrega descrições personalizadas do arquivo"""
        desc_file = Path(self.config_manager.get('files.descriptions_file'))
        
        try:
            if desc_file.exists():
                with open(desc_file, 'r', encoding='utf-8') as f:
                    self.custom_descriptions = json.load(f)
            else:
                self.custom_descriptions = {}
        except Exception as e:
            self.logger.error(f"Erro carregando descrições: {e}")
            self.custom_descriptions = {}
    
    def _save_custom_descriptions(self):
        """Salva descrições personalizadas no arquivo"""
        desc_file = Path(self.config_manager.get('files.descriptions_file'))
        
        try:
            with open(desc_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_descriptions, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Descrições salvas em: {desc_file}")
        except Exception as e:
            self.logger.error(f"Erro salvando descrições: {e}")
            print(f"❌ Erro salvando: {e}")

def get_valid_choice(prompt: str, valid_choices: List[str]) -> str:
    """
    Solicita entrada válida do usuário
    
    Args:
        prompt: Texto do prompt
        valid_choices: Lista de opções válidas
    
    Returns:
        Escolha válida do usuário
    """
    while True:
        try:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            else:
                print(f"❌ Opção inválida! Escolha entre: {', '.join(valid_choices)}")
        except KeyboardInterrupt:
            print("\n⚠️ Operação cancelada.")
            return "0"

def main():
    """Função principal da aplicação"""
    print("🏭 FACTORY I/O - SCANNER CONFIGURÁVEL")
    print("=" * 65)
    
    try:
        # Inicializa configuração e scanner
        config_manager = ConfigurationManager()
        scanner = FactoryIOScanner(config_manager)
        
        if not scanner.test_connection():
            print("❌ Não foi possível conectar!")
            return
        
        # Menu principal
        menu_options = {
            "1": ("🔍", "Escanear I/Os"),
            "2": ("📋", "Tabela COMPLETA"),
            "3": ("🟢", "Apenas ENTRADAS"),
            "4": ("🔴", "Apenas SAÍDAS"),
            "5": ("⚡", "I/Os DIGITAIS"),
            "6": ("📊", "I/Os ANALÓGICOS"),
            "7": ("🔥", "Apenas ATIVOS"),
            "8": ("✏️", "Editar descrições"),
            "9": ("⚙️", "Mostrar configuração"),
            "0": ("❌", "Sair")
        }
        
        valid_choices = list(menu_options.keys())
        
        while True:
            print(f"\n🎛️ OPÇÕES:")
            for key, (emoji, description) in menu_options.items():
                print(f"{key}. {emoji} {description}")
            
            escolha = get_valid_choice("\nEscolha: ", valid_choices)
            
            if escolha == "1":
                scanner.scan_all_ios()
            elif escolha == "2":
                scanner.display_table('ALL')
            elif escolha == "3":
                scanner.display_table('ENTRADA')
            elif escolha == "4":
                scanner.display_table('SAÍDA')
            elif escolha == "5":
                scanner.display_table('DIGITAL')
            elif escolha == "6":
                scanner.display_table('ANALÓGICO')
            elif escolha == "7":
                scanner.display_table('ATIVO')
            elif escolha == "8":
                scanner.edit_descriptions()
            elif escolha == "9":
                _show_current_config(config_manager)
            elif escolha == "0":
                break
                
    except KeyboardInterrupt:
        print("\n🔄 Encerrando...")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logging.getLogger('FactoryIO').error(f"Erro inesperado: {e}")

def _show_current_config(config_manager: ConfigurationManager):
    """Exibe configuração atual"""
    print("\n⚙️ CONFIGURAÇÃO ATUAL:")
    print("=" * 50)
    print(f"🌐 Conexão: {config_manager.get('connection.host')}:{config_manager.get('connection.port')}")
    print(f"⏱️ Timeout: {config_manager.get('connection.timeout')}s")
    print(f"📊 Fator de escala: {config_manager.get('display.scale_factor')}")
    print(f"📝 Arquivo descrições: {config_manager.get('files.descriptions_file')}")

if __name__ == "__main__":
    main()
