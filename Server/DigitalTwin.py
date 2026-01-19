import Utils.logger as loggerManager

from enum import IntEnum
from pyModbusTCP.server import ModbusServer


DI_SIZE = 10        # Tamanho do array de Discrete Inputs
INPUT_HR_SIZE = 10  # Tamanho do array de Holding Registers

di = [False] * DI_SIZE              # Array de Discrete Inputs inicializado com False
input_hr = [False] * INPUT_HR_SIZE  # Array de Holding Registers inicializado com False


class DI(IntEnum):
    '''
    Enum de Discrete Inputs (DI) do Digital Twin.

    Atributos:
        Cylinder_Pusher_Feeder (int): DI para o empurrador do cilindro do alimentador.
        Conveyor_Job (int)          : DI para a esteira de trabalho.
        LAMP_GREEN_DT (int)         : DI para a lâmpada verde do Andon.
        LAMP_YELLOW_DT (int)        : DI para a lâmpada amarela do Andon.
        LAMP_RED_DT (int)           : DI para a lâmpada vermelha do Andon.
        START_BUTTON_LIGHT (int)    : DI para a luz do botão de início.
        RESET_BUTTON_LIGHT (int)    : DI para a luz do botão de reset.
    '''
    Cylinder_Pusher_Feeder = 0
    Conveyor_Job           = 2
    LAMP_GREEN_DT          = 20
    LAMP_YELLOW_DT         = 21
    LAMP_RED_DT            = 22
    START_BUTTON_LIGHT     = 23
    RESET_BUTTON_LIGHT     = 24


class INPUT_HR(IntEnum):
    '''
    Enum de Holding Registers (INPUT_HR) do Digital Twin.

    Atributos:
        Crane_Fedder_Setpoint_X (int): INPUT_HR para o setpoint X do braço do alimentador.
        Crane_Fedder_Setpoint_Z (int): INPUT_HR para o setpoint Z do braço do alimentador.
    '''
    Crane_Fedder_Setpoint_X = 0
    Crane_Fedder_Setpoint_Z = 2


class DigitalTwin:
    '''
    Classe que representa o Digital Twin do sistema Modular Producing System (MPS) da Festo.

    Metodos:
        __init__(): Inicializa o servidor Modbus e configura o banco de registradores.
        commit_all(): Atualiza todos os Discrete Inputs e Holding Registers no servidor Modbus.
        set_parameter(parameter, value): Define o valor de um parâmetro específico (DI ou INPUT_HR).
    '''
    def __init__(self):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name("DigitalTwin_MPS_Festo")

        try:
            self.server = ModbusServer(host="127.0.0.1", port=502, no_block=True)
            self.server.start()
            self.db = self.server.data_bank
            self.DI = DI
            self.INPUT_HR = INPUT_HR
            self.logger.logger.info("Servidor Modbus iniciado na porta 502")
        except Exception as e:
            self.logger.logger.error(f"Erro ao iniciar o servidor Modbus: {e}")

    def commit_all(self):
        '''
        Metodo da classe DigitalTwin que atualiza todos os Discrete Inputs e Holding Registers no servidor Modbus.
        '''
        self.db.set_discrete_inputs(0, di)
        self.logger.logger.info("Discrete inputs committed")
        # Fazendo o set de todos os INPUT_HR de uma vez
        if hasattr(self.db, "set_holding_registers"):
            self.db.set_holding_registers(0, input_hr)
            self.logger.logger.info("Holding registers committed")
        else:
            self.db.set_words(0, input_hr)
            self.logger.logger.info("Words committed")

    def set_parameter(self, parameter, value: int | bool):
        '''
        Metodo da classe DigitalTwin que faz o set do valor de um parâmetro específico (DI ou INPUT_HR).
        
        Args:
            parameter (DI | INPUT_HR): O parâmetro a ser definido.
            value (int | bool)       : O valor a ser atribuído ao parâmetro.

        No caso dos parâmetros INPUT_HR, o valor, por se tratar de um registrador, deve ser um inteiro que varie dentro do intervalo 0 a 1000.
        Isso se deve ao fato de que no factoryIO esses registradores variam entre 0 até 10.0
        '''
        if isinstance(parameter, self.DI):
            di[parameter] = bool(value)
            self.commit_all()
            self.logger.logger.info(f"DI {parameter.name} set to {value}")

        elif isinstance(parameter, self.INPUT_HR):
            input_hr[parameter] = int(value)
            self.commit_all()
            self.logger.logger.info(f"INPUT_HR {parameter.name} set to {value}")

        else:
            self.logger.logger.error(f"Parâmetro desconhecido: {parameter}")
