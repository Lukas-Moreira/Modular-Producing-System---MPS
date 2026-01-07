class holding_register_handling_plc:
    MB_RemoteEnable_W = 0
    MB_Running =        1
    MB_Stopped =        2
    MB_Emergency =      3
    MB_Start_W =        4
    MB_Stop_W =         5
    MB_Reset_W =        6
    MB_Auto_W =         7

    MB_L_VD_CAN =       8
    MB_L_AM_CAN =       9
    MB_L_VM_CAN =       10
    MB_L_START =        11
    MB_L_RESET =        12
    MB_Q1 =             13
    MB_Q2 =             14
    MB_M0_ESQ_CAN =     15
    MB_M0_DIR_CAN =     16
    MB_A1_CAN =         17
    MB_A2_CAN =         18
    MB_A3_CAN =         19

class input_register_handling_plc:
    MB_PART_AV_CAN =    0
    MB_1B1_CAN =        1
    MB_1B2_CAN =        2
    MB_1B3_CAN =        3
    MB_2B1_CAN =        4
    MB_2B2_CAN =        5
    MB_3B1_CAN =        6
    MB_IP_FI_CAN =      7

class holding_register_pressing_plc:
    MB_Start_W=    0
    MB_L_START=    1
    MB_L_RESET=    2
    MB_Q1     =    3
    MB_Q2     =    4
    MB_M0     =    5
    MB_A0     =    6
    MB_A1     =    7
    MB_A2     =    8
    MB_A3     =    9
    MB_A4     =    10

class input_register_ppressing_plc:
    MB_PART_AV      = 0
    MB_1B1          = 1
    MB_1B2          = 2
    MB_2B1          = 3
    MB_3B1          = 4
    MB_4B1          = 5
    MB_5B1          = 6
    MB_5B2          = 7
    MB_B_START      = 8
    MB_B_STOP       = 9
    MB_CH_AT_MAN    = 10
    MB_B_RESET      = 11