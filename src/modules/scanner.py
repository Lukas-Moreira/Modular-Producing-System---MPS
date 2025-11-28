import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from edge_monitor import EdgeMonitor
from config import ConfigurationManager
from modbus_client import ModbusClientWrapper

class MPScanner:
    """Scanner I/O para I/O com configuração flexível"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance in None:
            cls._instance = super(MPScanner, cls).__new__(cls)
            cls._initialize = False
        return cls._instance         
    
    def __init__(self, config_manager: ConfigurationManager):

        if self.__class__._initialize:
            return
        
        self.__class__._initialize = True

        self.config_manager = config_manager
        self.logger = logging.getLogger('MPScanner')
        
        # Inicializa cliente Modbus
        conn_config = config_manager.config['connection']
        self.modbus_client = ModbusClientWrapper(
            host=conn_config['host'],
            port=conn_config['port'],
            timeout=conn_config.get('timeout', 5.0)
        )
        
        # Estruturas de dados
        self.io_data: List[Dict] = []
        self.custom_descriptions: Dict[str, str] = {}

        # Carrega descrições personalizadas
        self._load_custom_descriptions()

        # Inicializa monitor de bordas (exemplo para entradas digitais)
        self.di_mapping = config_manager.config['modbus_mapping']['digital_inputs']
        self.edge_monitor = EdgeMonitor(mapping=self.di_mapping, read_snapshot=self._read_di_snapshot)
        self.edge_monitor.start()
    
    def test_connection(self) -> bool:
        """Testa conectividade com I/O"""
        if self.modbus_client.test_connection():
            self.logger.info(f"Conectado ao I/O")
            self._print_configuration()
            return True
        else:
            self.logger.error("Falha na conexão")
            return False
    
    def scan_all_ios(self) -> bool:
        """Executa escaneamento completo"""
        print("\n🔍 INICIANDO ESCANEAMENTO COMPLETO...")
        
        if not self.test_connection():
            return False
        
        self.io_data.clear()
        
        try:
            self._scan_digital_inputs()
            self._scan_digital_outputs()
            self._scan_analog_inputs()
            self._scan_analog_outputs()
            
            self.io_data.sort(key=lambda x: (x['type_order'], x['address']))
            
            print(f"✅ Escaneamento concluído: {len(self.io_data)} I/Os encontrados")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro durante escaneamento: {e}")
            return False
    
    def _scan_digital_inputs(self):
        """Escaneia entradas digitais (COILS)"""
        config = self.config_manager.config['modbus_mapping']['digital_inputs']
        
        coils = self.modbus_client.read_coils(
            config['start_address'], 
            config['count']
        )
        
        if coils:
            for i, value in enumerate(coils):
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
    
    def _scan_digital_outputs(self):
        """Escaneia saídas digitais (DISCRETE INPUTS)"""
        config = self.config_manager.config['modbus_mapping']['digital_outputs']
        
        discretes = self.modbus_client.read_discrete_inputs(
            config['start_address'], 
            config['count']
        )
        
        if discretes:
            for i, value in enumerate(discretes):
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
    
    def _scan_analog_inputs(self):
        """Escaneia entradas analógicas (HOLDING REGISTERS)"""
        config = self.config_manager.config['modbus_mapping']['analog_inputs']
        scale_factor = self.config_manager.get('display.scale_factor', 100)
        decimal_places = self.config_manager.get('display.decimal_places', 2)
        show_inactive = self.config_manager.get('display.show_inactive_analogs', False)
        
        registers = self.modbus_client.read_holding_registers(
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
    
    def _scan_analog_outputs(self):
        """Escaneia saídas analógicas (INPUT REGISTERS)"""
        config = self.config_manager.config['modbus_mapping']['analog_outputs']
        scale_factor = self.config_manager.get('display.scale_factor', 100)
        decimal_places = self.config_manager.get('display.decimal_places', 2)
        show_inactive = self.config_manager.get('display.show_inactive_analogs', False)
        
        registers = self.modbus_client.read_input_registers(
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
    
    def _print_configuration(self):
        """Exibe configuração detectada"""
        mapping = self.config_manager.config['modbus_mapping']
        host = self.config_manager.get('connection.host')
        port = self.config_manager.get('connection.port')
        
        print(f"✅ Conectado ao I/O em {host}:{port}")
        print(f"🔧 Configuração detectada:")
        for io_type, config in mapping.items():
            print(f"   🔹 {config['description']}: {config['count']} "
                  f"({config['register_type']} {config['start_address']}-"
                  f"{config['start_address'] + config['count'] - 1})")
    
    def _load_custom_descriptions(self):
        """Carrega descrições personalizadas"""
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
    
    def save_custom_descriptions(self):
        """Salva descrições personalizadas"""
        desc_file = Path(self.config_manager.get('files.descriptions_file'))
        
        try:
            with open(desc_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_descriptions, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Descrições salvas em: {desc_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro salvando descrições: {e}")
            return False

    def _read_di_snapshot(self) -> Dict[int, bool]:
        """Lê as entradas digitais e retorna um dict addr->bool para o EdgeMonitor."""
        config = self.di_mapping
        start = config['start_address']
        count = config['count']

        values = self.modbus_client.read_coils(start, count)
        if not values:
            return {}

        return { start + i: bool(values[i]) for i in range(count) }

    @classmethod
    def is_initialized(cls):
        return getattr(cls, '_initialize', False)
    
scan = MPScanner(ConfigurationManager())