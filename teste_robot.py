import rtde_io

def escrever_saida_digital(host, output_id, valor):
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


HOST = "192.168.0.10"
OUTPUT_ID = 0 
VALOR = True
# VALOR = True

escrever_saida_digital(HOST, OUTPUT_ID, VALOR)