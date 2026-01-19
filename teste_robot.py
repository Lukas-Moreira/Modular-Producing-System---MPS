import rtde_io
import rtde_receive

def escrever_saida_digital_robot(host, output_id, valor):
    """
    Conecta ao robô e escreve um valor na saída digital padrão.

    Args:
        host (str): Endereço IP do robô.
        output_id (int): ID da saída digital [0-7] para saídas padrão.
        valor (bool): True para ligar (HIGH), False para desligar (LOW).

    Returns:
        bool: True se o comando foi executado com sucesso.
    """
    try:
        rtde_io_interface = rtde_io.RTDEIOInterface(host)
        
        sucesso = rtde_io_interface.setStandardDigitalOut(output_id, valor)
        
        if sucesso:
            estado = "LIGADA" if valor else "DESLIGADA"
            print(f"Saída digital {output_id} {estado} com sucesso!")
        else:
            print(f"Falha ao configurar saída digital {output_id}")
        
        # Desconecta
        rtde_io_interface.disconnect()
        
        return sucesso
    
    except Exception as e:
        print(f"erro ao escrever na saída digital: {e}")
        return False
    
def ler_saida_digital_robot(host, output_id):
    """
    Conecta ao robô e lê o valor atual da saída digital padrão.

    Args:
        host (str): Endereço IP do robô.
        output_id (int): ID da saída digital [0-7] para saídas padrão.

    Returns:
        bool or None: True se HIGH, False se LOW, None se erro.
    """
    try:
        rtde_r = rtde_receive.RTDEReceiveInterface(host)
        
        valor_atual = rtde_r.getDigitalOutState(output_id)
        
        print(f"[robot] - Saída digital {output_id} está: {valor_atual}")

        rtde_r.disconnect()
        
        return valor_atual
    
    except Exception as e:
        print(f"Erro ao ler a saída digital: {e}")
        return None

HOST = "192.168.0.10"
OUTPUT_ID = 0 
VALOR = True
# VALOR = True

escrever_saida_digital_robot(HOST, OUTPUT_ID, VALOR)

print(ler_saida_digital_robot(HOST, 5))