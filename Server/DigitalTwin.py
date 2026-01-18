import time
import threading
import Utils.logger as loggerManager

from enum import IntEnum
from dataclasses import dataclass
from typing import Callable, Iterable, Any
from pyModbusTCP.server import ModbusServer


DI_SIZE = 10
INPUT_HR_SIZE = 10

di = [False] * DI_SIZE
input_hr = [False] * INPUT_HR_SIZE


class DI(IntEnum):
    Cylinder_Pusher_Feeder = 0
    Conveyor_Job = 2
    LAMP_GREEN_DT = 20
    LAMP_YELLOW_DT = 21
    LAMP_RED_DT = 22
    START_BUTTON_LIGHT = 23
    RESET_BUTTON_LIGHT = 24


class INPUT_HR(IntEnum):
    Crane_Fedder_Setpoint_X = 0
    Crane_Fedder_Setpoint_Z = 2


class DigitalTwin:
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
        self.db.set_discrete_inputs(0, di)
        self.logger.logger.info("Discrete inputs committed")
        # Fazendo o set de todos os INPUT_HR de uma vez
        if hasattr(self.db, 'set_holding_registers'):
            self.db.set_holding_registers(0, input_hr)
            self.logger.logger.info("Holding registers committed")
        else:
            self.db.set_words(0, input_hr)
            self.logger.logger.info("Words committed")
    
    def set_parameter(self, parameter, value: int | bool):
        if isinstance(parameter, DI):
            di[parameter] = bool(value)
            self.commit_all()
            self.logger.logger.info(f"DI {parameter.name} set to {value}")
        
        elif isinstance(parameter, INPUT_HR):
            input_hr[parameter] = int(value)
            self.commit_all()
            self.logger.logger.info(f"INPUT_HR {parameter.name} set to {value}")
        
        else:
            self.logger.logger.error(f"Parâmetro desconhecido: {parameter}")



