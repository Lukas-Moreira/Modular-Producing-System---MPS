class holding_register_handling_plc:
    '''
    Classe de endereçamento dos registradores de escrita (Holding Registers) do módulo Handling da MPS.
    '''
    REMOTE_ENABLE =           0  # Habilita controle remoto
    MACHINE_RUNNING =         1  # Indica máquina rodando
    MACHINE_STOPPED =         2  # Indica máquina parada
    MACHINE_EMERGENCY =       3  # Indica máquina em emergência
    
    CMD_START =               4  # Pulso Start
    CMD_STOP =                5  # Pulso Stop
    CMD_RESET =               6  # Pulso Reset
    MODE_AUTO =               7  # Modo Auto(1) / Manual(0)

    LAMP_GREEN =              8  # Liga lâmpada verde
    LAMP_YELLOW =             9  # Liga lâmpada amarela
    LAMP_RED =               10  # Liga lâmpada vermelha
    LAMP_START =             11  # Liga lâmpada de Start
    LAMP_RESET =             12  # Liga lâmpada de Reset
    LAMP_Q1 =                13  # Liga lâmpada Q1
    LAMP_Q2 =                14  # Liga lâmpada Q2
    
    GRIPPER_TO_MAGAZINE_ESQ =    15  # Move unidade da garra para posição magazine (esquerda)
    GRIPPER_TO_STATION_DIR =     16  # Move unidade da garra para posição próxima estação (direita)
    GRIPPER_DOWN =           17  # Desce a garra
    GRIPPER_OPEN =           18  # Abre a garra
    MAGAZINE_EJECT =         19  # Recua o atuador do magazine (expulsa a peça)

class input_register_handling_plc:
    '''
    Classe de endereçamento dos registradores de leitura (Input Registers) do módulo Handling da MPS.
    '''
    sensor_peca_suporte =    0
    sensor_braco_deixa =        1
    sensor_braco_home = 2
    sensor_braco_rejeito =        3
    sensor_garra_avancada =        4
    sensor_garra_recuada =        5
    sensor_peca_garra =        6
    MB_IP_FI_CAN =      7
    button_start = 8
    button_stop = 9
    button_reset = 10
    sensor_magazine_entrada_recuado =      11
    sensor_magazine_entrada_avancado =      12


class holding_register_pressing_plc:
    '''
    Registradores de escrita (Holding Registers) do PLC do módulo de prensagem da MPS. 
    '''
    
    # Controles da esteira e componentes
    MB_LIGA_ESTEIRA = 0
    MB_REC_BLOQUEADOR = 1
    MB_REC_COINS = 2
    MB_PRESS_ON = 3
    MB_REC_ACTUATOR_STOP_COIN = 4
    MB_AVANCA_COINS = 5
    
    # Controles de lógica
    MB_L_START = 6
    MB_L_RESET = 7
    MB_L_Q1 = 8
    MB_L_Q2 = 9
    

class input_register_pressing_plc:
    '''
    Registradores de leitura (Input Registers) do PLC do módulo de prensagem da MPS. 
    '''
    
    # Controles principais
    MB_START = 0
    MB_STOP = 1
    MB_RESET = 2
    
    # Sensores e estados de peças
    MB_PART_AV = 3
    MB_PC_COIN = 4
    MB_PC_FIM = 5
    MB_SENSOR_IND = 6
    MB_BARREIRA_IND = 7
    
    # Posições e bloqueios
    MB_BLOQ_FRONT = 8
    MB_COIN_REC = 9
    MB_COIN_FRONT = 10