import Utils.logger as loggerManager

from Client.MES import MES
from Client.MPS import MPS
from Utils.config import config

def main():
    """ Ponto de entrada principal da aplicação MPS Festo. """
    logger = loggerManager.LoggerManager()
    logger.set_name('MPS_Festo_Main')

    running = True

    try:
        mps_client = MPS(config)
        mes_client = MES(mps_client.modbus_clients)

        while running:
            mes_client.maintain_MES()
            running = False
        
    except KeyboardInterrupt:
        running = False
              
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

    finally:
        logger.logger.info("Encerrando aplicação...")
        print("✅ Aplicação encerrada.")

if __name__ == "__main__":
    main()