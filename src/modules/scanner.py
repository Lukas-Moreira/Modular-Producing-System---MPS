import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from modules.edge_monitor import EdgeMonitor
from modules.config import ConfigurationManager
from modules.modbus_client import ModbusClientWrapper
from modules.client_io_state import ClientIOStateManager


class MPScanner:
    """Scanner I/O para I/O com configuração flexível"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MPScanner, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_manager: ConfigurationManager):

        if getattr(self.__class__, "_initialized", False):
            return

        self.__class__._initialized = True

        self.config_manager = config_manager
        self.logger = logging.getLogger("MPScanner")

        # Cria clientes Modbus dinamicamente a partir do config.json
        self.services = ["Source", "Conveyor", "Deposit", "UR_Robot"]
        self.clients: Dict[str, ModbusClientWrapper] = {}
        self.clients_info: Dict[str, str] = {}

        # Mapeia a chave usada no dict de clients para o título/section do config
        self.service_title_map: Dict[str, str] = {}

        # Aqui eu crio os clientes para cada Entidade presente em services.
        # Vale lembrar que cada entidade deve estar presente no config.json.
        for svc in self.services:
            try:
                # Puxa a configuração de conexão específica para a entidade
                conn = self.config_manager.config[svc]["connection"]
            except KeyError:
                self.logger.warning(
                    f"Configuração de conexão não encontrada para: {svc}"
                )
                continue

            client = ModbusClientWrapper(
                host=conn.get("host"),
                port=conn.get("port"),
                timeout=conn.get("timeout", 5),
            )

            """
            Mapa do título/section do config para a chave usada no dict de clients
                'source'   <- 'Source',
                'conveyor' <- 'Conveyor',
                'deposit'  <- 'Deposit',
                'ur_robot' <- 'UR_Robot'
            """
            key = svc.lower().replace(" ", "_")

            """ 
            Adiciono client ao dict de clients no formato
                'source':   ModbusClientWrapper(...),
                'conveyor': ModbusClientWrapper(...),
                'deposit':  ModbusClientWrapper(...),
                'ur_robot': ModbusClientWrapper(...)
            """
            self.clients[key] = client

            """
            Mapeia a chave do client para o título/section do config
                'source'   -> 'Source   (<ip>:<port>)',
                'conveyor' -> 'Conveyor (<ip>:<port>)',
                'deposit'  -> 'Deposit  (<ip>:<port>)',
                'ur_robot' -> 'UR_Robot (<ip>:<port>)'
            """
            self.clients_info[key] = f"{svc} ({conn.get('host')}:{conn.get('port')})"

            # Mantém compatibilidade com código que espera atributos individuais
            setattr(self, f"{key}_modbus_client", client)
            # mapear título/section do config para serviço (usado em leituras por cliente)
            self.service_title_map[key] = svc

            # criar/obter estados singleton para este cliente (inputs/outputs)
            state = ClientIOStateManager.get_state(key)
            print(
                f"[MPScanner] created state for {key} -> inputs={state.get_inputs_snapshot()} outputs={state.get_outputs_snapshot()}"
            )

        # Estruturas de dados
        self.io_data: List[Dict] = []
        self.custom_descriptions: Dict[str, str] = {}

        # Carrega descrições personalizadas
        self._load_custom_descriptions()

        # Inicializa as listas de inputs/outputs por cliente com formato estruturado
        # (addr, state, description) usando o mapeamento de configuração e descrições
        for client_key in list(self.clients.keys()):
            svc = self.service_title_map.get(client_key, client_key)
            # digital inputs
            try:
                di_cfg = self.config_manager.config[svc]["modbus_mapping"][
                    "digital_inputs"
                ]
            except Exception:
                di_cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "digital_inputs"
                )

            if di_cfg:
                start = int(di_cfg.get("start_address", 0))
                count = int(di_cfg.get("count", 0))
                addrs = [start + i for i in range(count)]
                # montar descrições por endereco: procura por chave 'clientkey_DI_{addr:02d}'
                desc_map = {}
                for a in addrs:
                    key = f"{client_key}_DI_{a:02d}"
                    desc_map[a] = self.custom_descriptions.get(key, "")
                state = ClientIOStateManager.get_state(client_key)
                state.initialize_inputs(addrs, desc_map)

            # digital outputs
            try:
                do_cfg = self.config_manager.config[svc]["modbus_mapping"][
                    "digital_outputs"
                ]
            except Exception:
                do_cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "digital_outputs"
                )

            if do_cfg:
                start = int(do_cfg.get("start_address", 0))
                count = int(do_cfg.get("count", 0))
                addrs = [start + i for i in range(count)]
                desc_map = {}
                for a in addrs:
                    key = f"{client_key}_DO_{a:02d}"
                    desc_map[a] = self.custom_descriptions.get(key, "")
                state = ClientIOStateManager.get_state(client_key)
                state.initialize_outputs(addrs, desc_map)

        # Inicializa monitor de bordas (exemplo para entradas digitais)
        self.di_mapping = config_manager.config["modbus_mapping"]["digital_inputs"]

        # Passa também o dicionário de clients e uma função que lê as DI por cliente
        self.edge_monitor = EdgeMonitor(
            mapping=self.di_mapping,
            read_snapshot=self._read_di_snapshot,
            clients=self.clients,
            client_read_fn=self._client_read_di_snapshot,
            client_poll_interval=self.config_manager.get(
                "scan.client_poll_interval", 0.1
            ),
        )
        self.edge_monitor.start()

        # registrar callback que atualiza apenas as listas de entradas por cliente
        self.edge_monitor.register_callback(self._on_edge_event)

    def _on_edge_event(self, addr, edge, old, new):
        """Callback registrado no EdgeMonitor: atualiza o ClientIOState correspondente.

        Espera `addr` no formato "client_key:address" quando o EdgeMonitor estiver
        rodando em modo por-client. Se `addr` for int, ignora (global snapshot mode).
        """
        # somente atualizamos quando recebemos eventos por cliente (formatado)
        if isinstance(addr, str) and ":" in addr:
            client_key, raw_addr = addr.split(":", 1)
            try:
                address = int(raw_addr)
            except ValueError:
                return

            state = ClientIOStateManager.get_state(client_key)
            # apenas EdgeMonitor usa esta API para atualizar inputs
            state.set_input(address, new)
            print(
                f"[EdgeEvent] {client_key} addr={address} edge={edge} -> inputs={state.get_inputs_snapshot()}"
            )

    def _client_read_di_snapshot(self, client_key: str, client) -> Dict[int, bool]:
        """Lê as entradas digitais específicas de um cliente e retorna dict addr->bool.

        Usado pelo EdgeMonitor quando é solicitado polling por cliente.
        """
        svc = self.service_title_map.get(client_key, client_key)
        try:
            cfg = self.config_manager.config[svc]["modbus_mapping"]["digital_inputs"]
        except Exception:
            cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                "digital_inputs"
            )
            if not cfg:
                self.logger.debug(f"Configuração digital_inputs ausente para {svc}")
                return {}

        try:
            values = client.read_coils(cfg["start_address"], cfg["count"])
        except Exception as e:
            self.logger.exception(
                f"Erro lendo coils de {client_key} (client mode): {e}"
            )
            return {}

        if not values:
            return {}

        return {
            cfg["start_address"] + i: bool(values[i])
            for i in range(min(cfg["count"], len(values)))
        }

    def test_connection(self) -> bool:
        """Testa conectividade com todos os clientes configurados.

        Retorna True somente se todas as conexões responderem com sucesso.
        """
        all_ok = True

        # Se não houver clientes configurados, retorna False
        if not self.clients:
            self.logger.error("Nenhum cliente Modbus configurado para testar.")
            return False

        """
        Para cada cliente em clients, tenta testar a conexão.

        name = chave do dict (ex: 'source', 'conveyor', etc)
        client = instância ModbusClientWrapper correspondente
        """
        for name, client in self.clients.items():
            try:
                ok = client.test_connection()
            except Exception as e:
                ok = False
                self.logger.exception(f"Erro testando conexão '{name}': {e}")

            # Pego o endereço do objeto client <ip>:<port>
            addr = f"{getattr(client, 'host', '?')}:{getattr(client, 'port', '?')}"
            if ok:
                self.logger.info(f"Conectado: {name} -> {addr}")
            else:
                self.logger.error(f"Falha na conexão: {name} -> {addr}")
                all_ok = False

        if all_ok:
            self._print_configuration()

        return all_ok

    def scan_all_ios(self) -> bool:
        """Executa escaneamento completo"""
        os.system("cls" if os.name == "nt" else "clear")
        print("\n🔍 INICIANDO ESCANEAMENTO COMPLETO...")

        # Se a conexão falhar, aborta o escaneamento
        if not self.test_connection():
            return False

        # Limpa dados anteriores antes de escanear
        self.io_data.clear()

        try:
            self._scan_digital_inputs()
            self._scan_digital_outputs()
            self._scan_analog_inputs()
            self._scan_analog_outputs()

            self.io_data.sort(key=lambda x: (x["type_order"], x["address"]))

            print(f"✅ Escaneamento concluído: {len(self.io_data)} I/Os encontrados")
            return True

        except Exception as e:
            self.logger.error(f"Erro durante escaneamento: {e}")
            return False

    def _scan_digital_inputs(self):
        """Escaneia entradas digitais (COILS)"""
        # Para cada cliente/serviço, tenta ler as coils usando a configuração específica
        for client_key, client in self.clients.items():
            svc = self.service_title_map.get(client_key, client_key)
            try:
                cfg = self.config_manager.config[svc]["modbus_mapping"][
                    "digital_inputs"
                ]
            except Exception:
                cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "digital_inputs"
                )
                if not cfg:
                    self.logger.debug(f"Configuração digital_inputs ausente para {svc}")
                    continue

            try:
                discretes = client.read_discrete_inputs(
                    cfg["start_address"], cfg["count"]
                )
            except Exception as e:
                self.logger.exception(f"Erro lendo coils de {client_key}: {e}")
                continue

            if not discretes:
                continue

            for i, value in enumerate(discretes):
                address = cfg["start_address"] + i
                key = f"{client_key}_DI_{address:02d}"

                self.io_data.append(
                    {
                        "address": address,
                        "tag": f"DI{address:02d}",
                        "service": svc,
                        "service_key": client_key,
                        "type_order": 1,
                        "io_type": "ENTRADA",
                        "data_type": "DIGITAL",
                        "modbus_type": "DISCRETE",
                        "state": "ON" if value else "OFF",
                        "state_emoji": "🟢" if value else "⚫",
                        "raw_value": value,
                        "display_value": "ON" if value else "OFF",
                        "description": self.custom_descriptions.get(key, ""),
                        "key": key,
                        "function": "Botão/Sensor",
                    }
                )

    def _scan_digital_outputs(self):
        """Escaneia saídas digitais (DISCRETE INPUTS) por cliente/serviço."""
        # Para cada cliente/serviço, tenta ler os discrete inputs usando a
        # configuração específica do serviço, com fallback para o mapeamento
        # global `modbus_mapping.digital_outputs`.
        for client_key, client in self.clients.items():
            svc = self.service_title_map.get(client_key, client_key)
            try:
                cfg = self.config_manager.config[svc]["modbus_mapping"][
                    "digital_outputs"
                ]
            except Exception:
                cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "digital_outputs"
                )
                if not cfg:
                    self.logger.debug(
                        f"Configuração digital_outputs ausente para {svc}"
                    )
                    continue

            try:
                coils = client.read_coils(cfg["start_address"], cfg["count"])
            except Exception as e:
                self.logger.exception(f"Erro lendo coils de {client_key}: {e}")
                continue

            if not coils:
                continue

            for i, value in enumerate(coils):
                address = cfg["start_address"] + i
                key = f"{client_key}_DO_{address:02d}"

                self.io_data.append(
                    {
                        "address": address,
                        "tag": f"DO{address:02d}",
                        "service": svc,
                        "service_key": client_key,
                        "type_order": 2,
                        "io_type": "SAÍDA",
                        "data_type": "DIGITAL",
                        "modbus_type": "COIL",
                        "state": "ON" if value else "OFF",
                        "state_emoji": "🔴" if value else "⚫",
                        "raw_value": value,
                        "display_value": "ON" if value else "OFF",
                        "description": self.custom_descriptions.get(key, ""),
                        "key": key,
                        "function": "Motor/Luz/Válvula",
                    }
                )

    def _scan_analog_inputs(self):
        """Escaneia entradas analógicas (HOLDING REGISTERS)"""
        scale_factor = self.config_manager.get("display.scale_factor", 100)
        decimal_places = self.config_manager.get("display.decimal_places", 2)
        show_inactive = self.config_manager.get("display.show_inactive_analogs", False)

        for client_key, client in self.clients.items():
            svc = self.service_title_map.get(client_key, client_key)
            try:
                cfg = self.config_manager.config[svc]["modbus_mapping"]["analog_inputs"]
            except Exception:
                cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "analog_inputs"
                )
                if not cfg:
                    self.logger.debug(f"Configuração analog_inputs ausente para {svc}")
                    continue

            try:
                registers = client.read_input_registers(
                    cfg["start_address"], cfg["count"]
                )
            except Exception as e:
                self.logger.exception(
                    f"Erro lendo holding registers de {client_key}: {e}"
                )
                continue

            if not registers:
                continue

            for i, value in enumerate(registers):
                if show_inactive or value != 0:
                    address = cfg["start_address"] + i
                    key = f"{client_key}_AI_{address:02d}"

                    real_value = value / scale_factor
                    display_value = f"{real_value:.{decimal_places}f}"

                    self.io_data.append(
                        {
                            "address": address,
                            "tag": f"AI{address:02d}",
                            "service": svc,
                            "service_key": client_key,
                            "type_order": 3,
                            "io_type": "ENTRADA",
                            "data_type": "ANALÓGICO",
                            "modbus_type": "HOLDING",
                            "state": display_value,
                            "state_emoji": "📊",
                            "raw_value": value,
                            "display_value": display_value,
                            "real_value": real_value,
                            "description": self.custom_descriptions.get(key, ""),
                            "key": key,
                            "function": "Sensor Analógico",
                        }
                    )

    def _scan_analog_outputs(self):
        """Escaneia saídas analógicas (INPUT REGISTERS)"""
        scale_factor = self.config_manager.get("display.scale_factor", 100)
        decimal_places = self.config_manager.get("display.decimal_places", 2)
        show_inactive = self.config_manager.get("display.show_inactive_analogs", False)

        for client_key, client in self.clients.items():
            svc = self.service_title_map.get(client_key, client_key)
            try:
                cfg = self.config_manager.config[svc]["modbus_mapping"][
                    "analog_outputs"
                ]
            except Exception:
                cfg = self.config_manager.config.get("modbus_mapping", {}).get(
                    "analog_outputs"
                )
                if not cfg:
                    self.logger.debug(f"Configuração analog_outputs ausente para {svc}")
                    continue

            try:
                registers = client.read_holding_registers(
                    cfg["start_address"], cfg["count"]
                )
            except Exception as e:
                self.logger.exception(
                    f"Erro lendo input registers de {client_key}: {e}"
                )
                continue

            if not registers:
                continue

            for i, value in enumerate(registers):
                if show_inactive or value != 0:
                    address = cfg["start_address"] + i
                    key = f"{client_key}_AO_{address:02d}"

                    real_value = value / scale_factor
                    display_value = f"{real_value:.{decimal_places}f}"

                    self.io_data.append(
                        {
                            "address": address,
                            "tag": f"AO{address:02d}",
                            "service": svc,
                            "service_key": client_key,
                            "type_order": 4,
                            "io_type": "SAÍDA",
                            "data_type": "ANALÓGICO",
                            "modbus_type": "INPUT_REG",
                            "state": display_value,
                            "state_emoji": "📈",
                            "raw_value": value,
                            "display_value": display_value,
                            "real_value": real_value,
                            "description": self.custom_descriptions.get(key, ""),
                            "key": key,
                            "function": "Setpoint/Comando",
                        }
                    )

    def _print_configuration(self):
        """Exibe configuração detectada"""
        mapping = self.config_manager.config.get("modbus_mapping", {})

        print("✅ Configuração de I/Os detectada:")
        # Imprime resumo de cada cliente com identificador
        for key, info in self.clients_info.items():
            print(f"   🔸 {key}: {info}")

        print("🔧 Mapeamento I/O:")
        for io_type, config in mapping.items():
            try:
                start = config["start_address"]
                count = config["count"]
                reg = config.get("register_type", "")
                desc = config.get("description", io_type)
                print(f"   🔹 {desc}: {count} ({reg} {start}-{start + count - 1})")
            except Exception:
                self.logger.debug(f"Configuração inválida para {io_type}: {config}")

    def _load_custom_descriptions(self):
        """Carrega descrições personalizadas"""
        desc_file = Path(self.config_manager.get("files.descriptions_file"))

        try:
            if desc_file.exists():
                with open(desc_file, "r", encoding="utf-8") as f:
                    self.custom_descriptions = json.load(f)
            else:
                self.custom_descriptions = {}
        except Exception as e:
            self.logger.error(f"Erro carregando descrições: {e}")
            self.custom_descriptions = {}

    def save_custom_descriptions(self):
        """Salva descrições personalizadas"""
        desc_file = Path(self.config_manager.get("files.descriptions_file"))

        try:
            with open(desc_file, "w", encoding="utf-8") as f:
                json.dump(self.custom_descriptions, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Descrições salvas em: {desc_file}")
            return True
        except Exception as e:
            self.logger.error(f"Erro salvando descrições: {e}")
            return False

    def _read_di_snapshot(self) -> Dict[int, bool]:
        """Lê as entradas digitais e retorna um dict addr->bool para o EdgeMonitor."""
        config = self.di_mapping
        start = config["start_address"]
        count = config["count"]

        # Tenta ler a partir do primeiro cliente que responder (compatibilidade)
        values = None
        for client in self.clients.values():
            try:
                values = client.read_coils(start, count)
                if values:
                    break
            except Exception:
                continue

        if not values:
            return {}

        return {start + i: bool(values[i]) for i in range(min(count, len(values)))}

    @classmethod
    def is_initialized(cls):
        return getattr(cls, "_initialize", False)
