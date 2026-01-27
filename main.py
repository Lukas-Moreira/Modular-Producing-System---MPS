import Utils.logger as loggerManager
import uvicorn
import threading
import time
from pymodbus.client import ModbusTcpClient
from Server.DigitalTwin import DigitalTwin

from Client.MES import MES
from api import app

# ========================================
# ============= LÓGICA DO MES ============
# ========================================

def run_lamps(mes_client: MES) -> None:
    '''
    Função para rodar o monitoramento e controle das lâmpadas em uma thread separada.

    Args:
        - mes_client (MES): Instância do cliente MES.
    '''
    try:
        mes_client.handle_lamp()
    except Exception as e:
        print(f"Erro nas lâmpadas: {e}")

def run_buttons(mes_client: MES) -> None:
    '''
    Função para rodar o monitoramento dos botões em uma thread separada.

    Args:
        - mes_client (MES): Instância do cliente MES.
    '''
    try:
        mes_client.monitor_buttons()
    except Exception as e:
        print(f"Erro nos botões: {e}")

def run_flow_first(mes_client: MES) -> None:
    '''
    Função para rodar o monitoramento do primeiro fluxo em uma thread separada.

    Args:
        - mes_client (MES): Instância do cliente MES.
    '''
    try:
        mes_client.flow_first_plc()
    except Exception as e:
        print(f"Erro no flow_first_plc: {e}")

def run_flow_second(mes_client: MES) -> None:
    '''
    Função para rodar o monitoramento e controle do segundo fluxo em uma thread separada.

    Args:
        - mes_client (MES): Instância do cliente MES.
    '''
    try:
        mes_client.flow_second_plc()
    except Exception as e:
        print(f"Erro no flow_second_plc: {e}")

# ========================================
# ================= MAIN =================
# ========================================

def main() -> None:
    '''
    Entry point da aplicação de controle MPS da Festo.

    Esta função inicializa as conexões Modbus TCP com os PLCs do sistema MPS, inicia o Digital Twin e o cliente MES,
    e inicia as threads responsáveis pelo monitoramento e controle dos componentes do sistema.
    Em seguida, inicia a API FastAPI para interação com o sistema.

    Fluxo:
        1. Configura o logger.
        2. Estabelece conexões Modbus TCP com os PLCs do MPS.
        3. Inicia o Digital Twin e vincula ao MES.
        4. Inicia threads para monitoramento de lâmpadas, botões e fluxos.
        5. Inicia a API FastAPI na porta 8000.
    
    Raises:
        - KeyboardInterrupt: Permite o encerramento gracioso da aplicação via Ctrl+C.
        - Exception: Captura e loga quaisquer erros inesperados durante a execução.
    '''
    logger = loggerManager.LoggerManager()
    logger.set_name('MPS_Festo_Main')

    try:
        print("=== Iniciando conexões Modbus TCP ===")
        
        client_handling = ModbusTcpClient("192.168.0.31", port = 504, timeout = 3)
        client_pressing = ModbusTcpClient("192.168.0.32", port = 502, timeout = 3)
        client_sorting = ModbusTcpClient("192.168.0.33", port = 502, timeout = 3)
        
        if not client_handling.connect():
            print("Falha ao conectar no MPS_HANDLING")
            # return
        print("MPS_HANDLING conectado!")
        
        if not client_pressing.connect():
            print("Falha ao conectar no MPS_PRESSING")
            # return
        print("MPS_PRESSING conectado!")
        
        # if not client_sorting.connect():
        #     print("Falha ao conectar no MPS_SORTING")
        #     # return
        #     print("MPS_SORTING  nao conectado!")
        
        modbus_clients = {
            'MPS_HANDLING': client_handling,
            'MPS_PRESSING': client_pressing,
            # 'MPS_SORTING': client_sorting
        }

        try:
            gemeo = DigitalTwin()
            print("Digital Twin iniciado e vinculado ao MES!")
        except Exception as e:
            print(f"Erro ao iniciar o Digital Twin: {e}")
            gemeo = None
        
        mes_client: MES = MES(modbus_clients, gemeo=gemeo)
        mes_client.state_machine = 'cycle'
        
        print("\nIniciando threads do MES...")
        
        lamp_thread: threading.Thread = threading.Thread(target=run_lamps, args=(mes_client,), daemon=True)
        lamp_thread.start()

        time.sleep(3)
        
        button_thread: threading.Thread = threading.Thread(target=run_buttons, args=(mes_client,), daemon=True)
        button_thread.start()
        
        flow1_thread: threading.Thread = threading.Thread(target=run_flow_first, args=(mes_client,), daemon=True)
        flow1_thread.start()
        
        flow2_thread: threading.Thread = threading.Thread(target=run_flow_second, args=(mes_client,), daemon=True)
        flow2_thread.start()
        
        time.sleep(1)
        print("Todas as threads iniciadas!")
        
        print("\nIniciando API na porta 3000...")
        print("Acesse: http://localhost:3000/docs\n")

        uvicorn.run(app, host = "0.0.0.0", port = 3000)
    
    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")
        
        # Fecha as conexões
        if 'client_handling' in locals():
            client_handling.close()
        if 'client_pressing' in locals():
            client_pressing.close()
        if 'client_sorting' in locals():
            client_sorting.close()
            
        exit(0)
              
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    main()