import json
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from modules.config import ConfigurationManager
from modules.scanner import MPScanner
from services.utils import setup_logging
from modules.client_io_state import ClientIOStateManager
from modules.edge_monitor import EdgeMonitor
from datetime import datetime
import time


def show_current_config(config_manager: ConfigurationManager):
    """Exibe configuração atual"""
    print("\n⚙️ CONFIGURAÇÃO ATUAL:")
    print("=" * 50)
    print(
        f"🌐 Conexão: {config_manager.get('connection.host')}:{config_manager.get('connection.port')}"
    )
    print(f"⏱️ Timeout: {config_manager.get('connection.timeout')}s")
    print(f"📊 Fator de escala: {config_manager.get('display.scale_factor')}")
    print(f"📝 Arquivo descrições: {config_manager.get('files.descriptions_file')}")
    print(f"🗂️ Arquivo configuração: {config_manager.config_file}")


def main():
    """Função principal da aplicação"""
    print("🏭 MPS FACTORY - PLC")
    print("=" * 65)

    try:
        # Inicializa componentes
        cfg = ConfigurationManager()
        setup_logging(cfg.get("files.log_level", "INFO"))
        logger = logging.getLogger("MPS Factory")
        print("[main] logging configurado")
        scanner = MPScanner(cfg)
        print("[main] scanner inicializado")

        # Executa escaneamento inicial (inclui teste de conexão internamente)
        if not scanner.scan_all_ios():
            print("❌ Não foi possível conectar ou escanear!")
            print("💡 Verifique se o Factory I/O está rodando e a configuração de rede")
            return
        else:
            print("[main] scan_all_ios retornou True")

        # Mostrar estados de I/O por cliente (consumo inicial de ClientIOState)
        # print("\n🔎 Estados de I/O por cliente:")
        keys = ClientIOStateManager.list_keys()
        print(f"[main] ClientIOStateManager keys: {keys}")
        for key in keys:
            state = ClientIOStateManager.get_state(key)
            snapshot = state.get_inputs_snapshot()
            addr_state = {entry["addr"]: entry["state"] for entry in snapshot}
            logger.info(f" - {key}: inputs={addr_state} outputs={addr_state}")

        # Use o EdgeMonitor já criado pelo scanner (singleton inicializado no Scanner)
        monitor = getattr(scanner, "edge_monitor", EdgeMonitor())
        print(f"[main] edge_monitor presente: {hasattr(scanner, 'edge_monitor')}")
        try:
            print(f"[main] edge_monitor.debounce_count = {monitor.debounce_count}")
        except Exception:
            pass

        def _edge_cb(addr, edge, old, new):
            saddr = str(addr)
            client_key = None
            raw_addr = saddr
            if ":" in saddr:
                client_key, raw_addr = saddr.split(":", 1)
            ts = datetime.now().isoformat(sep=" ", timespec="seconds")
            print(
                f"[EdgeMonitor] {ts} client={client_key or '-'} addr={raw_addr} edge={edge} {old}->{new}"
            )

        # registra apenas um callback de exibição; o Scanner já registra seu próprio
        monitor.register_callback(_edge_cb)
        print("[main] callback de exibição registrado no EdgeMonitor")

        logger.info("Inicialização completa, preparando para monitoramento.")

        # Mantém o processo vivo sem busy-wait (EdgeMonitor roda em threads)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Será tratado pelo bloco externo
            raise

    except KeyboardInterrupt:
        print("\n🔄 Encerrando aplicação...")
    except Exception as e:
        logging.getLogger("Main_Erro").error(f"Erro inesperado na main: {e}\n")


if __name__ == "__main__":
    main()
