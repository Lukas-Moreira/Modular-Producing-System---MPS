import time
from pymodbus.client import ModbusTcpClient

IP = "192.168.0.32"
PORTA = 502

print("=== Comunicação Modbus TCP ===")
print(f"Conectando em {IP}:{PORTA}...\n")

while True:
    try:
        client = ModbusTcpClient(IP, port=PORTA, timeout=3)
        
        if client.connect():
            print("✓ Conectado com sucesso!")
            
            resultado = client.write_register(address=0,value=0, slave=0)
            # resultado = client.read_input_registers(address=3,slave=0)
            if not resultado.isError():
                print(f"Registradores lidos: {resultado.registers}")
            else:
                print(f"Erro na leitura: {resultado}")
            
            client.close()
            print("\nConexão fechada.")
            break  # Sai do loop após sucesso
            
        else:
            print("Falha na conexão. Tentando novamente em 5 segundos...")
            time.sleep(5)
            
    except Exception as e:
        print(f"Erro: {e}")
        print("Tentando novamente em 5 segundos...")
        time.sleep(5)

print("\nPrograma finalizado.")