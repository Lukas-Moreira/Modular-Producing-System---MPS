import Utils.logger as loggerManager
import uvicorn
import threading
import time
from pymodbus.client import ModbusTcpClient

from Client.MES import MES
from api import app

# ========================================
# ============= LÓGICA DO MES ============
# ========================================

def run_lamps(mes_client: MES) -> None:
    try:
        mes_client.handle_lamp()
    except Exception as e:
        print(f"Erro nas lâmpadas: {e}")

def run_buttons(mes_client: MES) -> None:
    try:
        mes_client.monitor_buttons()
    except Exception as e:
        print(f"Erro nos botões: {e}")

def run_flow_first(mes_client: MES) -> None:
    try:
        mes_client.flow_first_plc()
    except Exception as e:
        print(f"Erro no flow_first_plc: {e}")

def run_flow_second(mes_client: MES) -> None:
    try:
        mes_client.flow_second_plc()
    except Exception as e:
        print(f"Erro no flow_second_plc: {e}")

# ========================================
# ================= MAIN =================
# ========================================

def main() -> None:
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
        
        mes_client: MES = MES(modbus_clients)
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
        
        print("\nIniciando API na porta 8000...")
        print("Acesse: http://localhost:8000/docs\n")

        uvicorn.run(app, host = "0.0.0.0", port = 8000)
    
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