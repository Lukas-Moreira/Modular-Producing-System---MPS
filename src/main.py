import sys
import logging
from pathlib import Path
from rich.table import Table
from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from modules.config import ConfigurationManager
from modules.scanner import MPScanner
from services.utils import setup_logging


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
        logger = logging.getLogger("Main")
        scanner = MPScanner(cfg)

        # Executa escaneamento inicial (inclui teste de conexão internamente)
        if not scanner.scan_all_ios():
            print("❌ Não foi possível conectar ou escanear!")
            print("💡 Verifique se o Factory I/O está rodando e a configuração de rede")
            return
        
        logger.info("Inicialização completa, preparando para monitoramento.")

        while True:
            pass

    except KeyboardInterrupt:
        print("\n🔄 Encerrando aplicação...")
    except Exception as e:
        logging.getLogger("Main_Erro").error(f"Erro inesperado na main: {e}\n")


if __name__ == "__main__":
    main()
