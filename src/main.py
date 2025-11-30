import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from modules.config import ConfigurationManager
from modules.scanner import MPScanner
from services.ui import UserInterface, get_valid_choice
from services.utils import setup_logging

def show_current_config(config_manager: ConfigurationManager):
    """Exibe configuração atual"""
    print("\n⚙️ CONFIGURAÇÃO ATUAL:")
    print("=" * 50)
    print(f"🌐 Conexão: {config_manager.get('connection.host')}:{config_manager.get('connection.port')}")
    print(f"⏱️ Timeout: {config_manager.get('connection.timeout')}s")
    print(f"📊 Fator de escala: {config_manager.get('display.scale_factor')}")
    print(f"📝 Arquivo descrições: {config_manager.get('files.descriptions_file')}")
    print(f"🗂️ Arquivo configuração: {config_manager.config_file}")

def main():
    """Função principal da aplicação"""
    print("🏭 FACTORY I/O - SCANNER CONFIGURÁVEL v2.0")
    print("=" * 65)
    
    try:
        # Inicializa componentes
        cfg = ConfigurationManager()
        setup_logging(cfg.get('files.log_level', 'INFO'))
        scanner = MPScanner(cfg)
        ui = UserInterface(scanner)
        
        # Testa conexão inicial
        if not scanner.test_connection():
            print("🚨 chamada no main")
            print("❌ Não foi possível conectar!")
            print("💡 Verifique se o Factory I/O está rodando")
            print("💡 Verifique IP/porta no arquivo config.json")
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
                ui.display_table('ALL')
            elif escolha == "3":
                ui.display_table('ENTRADA')
            elif escolha == "4":
                ui.display_table('SAÍDA')
            elif escolha == "5":
                ui.display_table('DIGITAL')
            elif escolha == "6":
                ui.display_table('ANALÓGICO')
            elif escolha == "7":
                ui.display_table('ATIVO')
            elif escolha == "8":
                ui.edit_descriptions()
            elif escolha == "9":
                show_current_config(cfg)
            elif escolha == "0":
                break
                
    except KeyboardInterrupt:
        print("\n🔄 Encerrando aplicação...")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logging.getLogger('FactoryIO').error(f"Erro inesperado na main: {e}")

if __name__ == "__main__":
    main()
