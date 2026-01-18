import time
import Utils.logger as loggerManager

from typing import Optional
from States.PLCState import PLC
from dataclasses import dataclass
from pymodbus.client import ModbusTcpClient

from Maps.Mapping import input_register_handling_plc
from Maps.Mapping import holding_register_handling_plc
from Maps.Mapping import input_register_pressing_plc
from Maps.Mapping import holding_register_pressing_plc
import rtde_io
from Server.DigitalTwin import DigitalTwin, DI, INPUT_HR

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
        print(f"❌ Erro ao escrever na saída digital: {e}")
        return False


HOST = "192.168.0.10"



PLC_ROLE_MAP = {
    "MPS_HANDLING": "handling",
    "MPS_PRESSING": "pressing",
    "MPS_SORTING":  "sorting",
}

@dataclass
class Piece:
    id: int

class MES:
    def __init__(self, clients: Optional[dict[str, ModbusTcpClient]] = None, gemeo: DigitalTwin = None):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name('MES of MPS')

        self.clients = clients or {}
        self.parts = []

        self.state_machine = 'running'
        self.gemeo = gemeo

        if not self.clients:
            self.logger.set_level("ERROR")
            self.logger.logger.error("MES inicializado sem clientes Modbus.")
            raise ValueError("MES inicializado sem clientes Modbus.")

    def get_plc(self, name: str) -> ModbusTcpClient:
        try:
            return self.clients[name]
        except KeyError:
            raise KeyError(f"PLC '{name}' não encontrado no MES.")
        

    def stop_all_operations(self):
        """Para todas as operações dos 3 PLCs escrevendo 0 em todos os registradores de saída"""
        print("PARANDO TODAS AS OPERAÇÕES...")
        
        try:
            for register in range(20):
                self.clients['MPS_HANDLING'].write_register(address=register, value=0, slave=0)

            self.clients['MPS_HANDLING'].write_register(address = 0, value = 0, slave = 0)
            print("MPS_HANDLING parado")

            
            for register in range(20):
                self.clients['MPS_PRESSING'].write_register(address=register, value=0, slave=0)

            self.clients['MPS_PRESSING'].write_register(address=0, value=0, slave=0)
            print("MPS_PRESSING parado")
            

            if 'MPS_SORTING' in self.clients:
                for register in range(20):
                    self.clients['MPS_SORTING'].write_register(address = register, value = 0, slave = 0)
                
                self.clients['MPS_SORTING'].write_register(address = 0, value = 0, slave = 0)
                print("MPS_SORTING parado")
            
            print("Todas as operações foram paradas com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro ao parar operações: {e}")
            return False

    def reset_to_home_position(self):
        """Reseta o sistema: sobe garra, recua magazine e vai para home"""
        print("RESETANDO SISTEMA...")
        
        try:
            print("1. Subindo garra...")
            self.gripper_up()
            time.sleep(0.5)
            
            print("2. Recuando magazine...")
            self.magazine_eject()
            time.sleep(0.5)
            
            print("3. Movendo para HOME...")
            self.move_to_home_reset()
            
            print("Sistema resetado com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro ao resetar sistema: {e}")
            return False


    def monitor_buttons(self):
        last_start = 0
        last_stop = 0
        last_reset = 0
        
        while True:
            try:
                result_start = self.clients['MPS_HANDLING'].read_input_registers(address=input_register_handling_plc.button_start, count=1, slave=0)
                result_stop = self.clients['MPS_HANDLING'].read_input_registers(address=input_register_handling_plc.button_stop, count=1, slave=0)
                result_reset = self.clients['MPS_HANDLING'].read_input_registers(address=input_register_handling_plc.button_reset, count=1, slave=0)
                
                if result_start.isError() or result_stop.isError() or result_reset.isError():
                    time.sleep(0.1)
                    continue
                
                current_start = result_start.registers[0]
                current_stop = result_stop.registers[0]
                current_reset = result_reset.registers[0]
                
                if current_start == 1 and last_start == 0 and self.state_machine == 'idle':
                    print("Botão START pressionado!")
                    
                    self.state_machine = "running"
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_START, value=1, slave=0)
                    self.gemeo.set_parameter(DI.START_BUTTON_LIGHT, True)
                    self.gemeo.commit_all()                    
                    time.sleep(0.5)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_START, value=0, slave=0)
                    self.gemeo.set_parameter(DI.START_BUTTON_LIGHT, False)
                    self.gemeo.commit_all()
                
                if current_stop == 0 and last_stop == 1:
                    print("Botão STOP pressionado!")
                    
                    self.state_machine = "stopped"
                    self.stop_all_operations()
                
                if current_reset == 1 and last_reset == 0 and (self.state_machine == 'stopped' or self.state_machine == 'cycle'):
                    print("Botão RESET pressionado!")
                    
                    self.state_machine = "idle"
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RESET, value=1, slave=0)
                    self.gemeo.set_parameter(DI.RESET_BUTTON_LIGHT, True)
                    self.gemeo.commit_all()
                    
                    time.sleep(0.5)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RESET, value=0, slave=0)
                    self.gemeo.set_parameter(DI.RESET_BUTTON_LIGHT, False)
                    self.gemeo.commit_all()
                    self.reset_to_home_position()
                
                last_start = current_start
                last_stop = current_stop
                last_reset = current_reset
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Erro ao monitorar botões: {e}")
                time.sleep(0.1)
    
    def handle_lamp(self):
        while True:
            state = self.state_machine if hasattr(self, 'state_machine') else "stopped"
            
            try:
                if state == "running":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(0.1)
                
                elif state == "idle":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(0.5)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(0.2)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(0.2)
                
                elif state == "error":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(0.1)
                
                elif state == "emergency":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(0.5)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(0.5)
                
                elif state == "cycle":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(1)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(1)
                    
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value= 0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, True)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(1)
                
                elif state == "stopped":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(0.1)
                
                else:
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=0, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, False)
                    self.gemeo.commit_all()
                    time.sleep(0.1)
            
            except Exception as e:
                print(f"Erro ao controlar lâmpadas: {e}")
                time.sleep(0.1)

    # ============================================
    #  ================ FIRST PLC ================ 
    # ============================================

    def gripper_open(self):
        print("Abrindo garra...")
        
        resultado = self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.GRIPPER_OPEN, value=1, slave=0)
        
        if resultado.isError():
            print(f"Erro ao abrir garra: {resultado}")
            return False
        
        time.sleep(0.5)
        print("Garra aberta")
        return True

    def gripper_close(self):
        print("Fechando garra...")
        
        resultado = self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.GRIPPER_OPEN, value=0, slave=0)
        
        if resultado.isError():
            print(f"Erro ao fechar garra: {resultado}")
            return False
        
        time.sleep(0.7)
        print("Garra fechada")
        return True

    def gripper_down(self):
        print("Descendo garra...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_garra_avancada, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Garra já está embaixo")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 1, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_Z, 1000)
        self.gemeo.commit_all()
        
        timeout = 5
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 0, slave = 0)
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_garra_avancada, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                print("Garra desceu")
                return True
            
            time.sleep(0.05)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 0, slave = 0)
        print("ERRO: Timeout ao descer garra\n")
        return False

    def gripper_up(self):
        print("Subindo garra...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_garra_recuada, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Garra já está em cima")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 0, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_Z, 0)
        self.gemeo.commit_all()
        
        timeout = 5
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_garra_recuada, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                print("Garra subiu")
                return True
            
            time.sleep(0.05)
        
        print("ERRO: Timeout ao subir garra")
        return False


    def move_to_home_reset(self):
        self.gripper_up()
        
        print("Movendo para HOME...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Braço já está na posição HOME")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 1, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 1000)
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
                self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 1000)
                self.gemeo.commit_all()
                print("Braço chegou na posição HOME")
                return True
            
            time.sleep(0.1)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
        print("ERRO: Timeout ao mover para HOME")
        return False
    
    def move_to_home(self):
        self.gripper_up()
        
        if self.state_machine != 'running':
            return False
        
        print("Movendo para HOME...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Braço já está na posição HOME")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 1, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 1000)
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
                print("Braço chegou na posição HOME")
                return True
            
            time.sleep(0.1)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
        print("ERRO: Timeout ao mover para HOME")
        return False

    def move_to_reject(self):
        self.gripper_up()
        
        if self.state_machine != 'running':
            return False
        
        print("Movendo para REJEITO...")
        
        result_rejeito = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_rejeito, count = 1, slave = 0)
        
        if not result_rejeito.isError() and result_rejeito.registers[0] == 1:
            print("Braço já está na posição REJEITO")
            return True
        
        result_home = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
        
        if not result_home.isError() and result_home.registers[0] == 1:
            register_move = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ
            direction = "esquerda"
        else:
            register_move = holding_register_handling_plc.GRIPPER_TO_STATION_DIR
            direction = "direita"
        
        print(f"Movendo para {direction}...")
        self.clients['MPS_HANDLING'].write_register(address = register_move, value = 1, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 6200)
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                self.clients['MPS_HANDLING'].write_register(address = register_move, value = 0, slave = 0)
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_rejeito, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                self.clients['MPS_HANDLING'].write_register(address = register_move, value = 0, slave = 0)
                print("Braço chegou na posição REJEITO")
                return True
            
            time.sleep(0.05)
        
        self.clients['MPS_HANDLING'].write_register(address = register_move, value = 0, slave = 0)
        print("ERRO: Timeout ao mover para REJEITO")
        return False

    def move_to_drop(self):
        self.gripper_up()
        
        if self.state_machine != 'running':
            return False
        
        print("Movendo para DEIXA...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_deixa, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Braço já está na posição DEIXA")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 1, slave = 0)
        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 0)
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 0, slave = 0)
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_deixa, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 0, slave = 0)
                print("Braço chegou na posição DEIXA")
                return True
            
            time.sleep(0.1)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 0, slave = 0)
        print("ERRO: Timeout ao mover para DEIXA")
        return False
    
    def magazine_eject(self):
        print("Ejetando peça do magazine...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_magazine_entrada_recuado, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Magazine já está recuado")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.MAGAZINE_EJECT, value = 0, slave = 0)
        self.gemeo.set_parameter(DI.Cylinder_Pusher_Feeder, False)
        self.gemeo.commit_all()
        
        timeout = 5
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_magazine_entrada_recuado, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                print("Peça ejetada")
                return True
            
            time.sleep(0.05)
        
        print("ERRO: Timeout ao ejetar peça")
        return False

    def magazine_advance(self):
        print("Avançando magazine...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_magazine_entrada_avancado, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1:
            print("Magazine já está avançado")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.MAGAZINE_EJECT, value = 1, slave = 0)
        self.gemeo.set_parameter(DI.Cylinder_Pusher_Feeder, True)
        self.gemeo.commit_all()        
        
        timeout = 5
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Checa se parou
            if self.state_machine != 'running':
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.MAGAZINE_EJECT, value = 0, slave = 0)
                self.gemeo.set_parameter(DI.Cylinder_Pusher_Feeder, False)
                self.gemeo.commit_all()
                print("Operação cancelada - sistema parado")
                return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_magazine_entrada_avancado, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                print("Magazine avançado")
                return True
            
            time.sleep(0.05)
        
        print("ERRO: Timeout ao avançar magazine")
        return False


    def recognize_inputs_handling(self):
        while True:
            time.sleep(2)
            inputs = []
            
            result_start = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.button_start, count=1, slave=0)
            result_stop = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.button_stop, count=1, slave=0)
            result_reset = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.button_reset, count=1, slave=0)
            
            if not result_start.isError():
                inputs.append(('button_start', result_start.registers))
            if not result_stop.isError():
                inputs.append(('button_stop', result_stop.registers))
            if not result_reset.isError():
                inputs.append(('button_reset', result_reset.registers))
            
            print("=" * 50)
            for name, value in inputs:
                print(f"{name:20} | {value}")
            print("=" * 50)
            print('\n\n')

    def flow_first_plc(self):
        print('Iniciando flow_first_plc...')
        self.magazine_eject()
        
        while True:
            # Checa se está parado
            if self.state_machine != 'running':
                time.sleep(0.1)
                continue
            
            self.magazine_advance()
            if self.state_machine != 'running':
                continue
                
            self.magazine_eject()
            if self.state_machine != 'running':
                continue
            
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_peca_suporte, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                if self.state_machine != 'running':
                    continue
                    
                self.gripper_open()
                if self.state_machine != 'running':
                    continue
                
                self.move_to_drop()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.1)
                
                self.gripper_down()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.1)
                
                self.gripper_close()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.1)
                
                self.gripper_up()
                if self.state_machine != 'running':
                    continue
                
                time.sleep(0.2)
                result_sensor_garra = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_peca_garra, count = 1, slave = 0)
                
                if not result_sensor_garra.isError():
                    if result_sensor_garra.registers[0] == 0:
                        print("Peça PRETA detectada!")
                        self.parts.append("preto")
                    else:
                        print("Peça PRATA ou ROSA detectada - aguardando confirmação no PLC 2")
                        self.parts.append("indefinido")
                
                time.sleep(0.1)
                
                self.move_to_home()
                if self.state_machine != 'running':
                    continue
                
                self.gripper_down()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.1)
                
                self.gripper_open()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.1)
                
                self.gripper_up()
                if self.state_machine != 'running':
                    continue
                time.sleep(0.2)


    # =============================================
    #  ================ SECOND PLC ================ 
    # =============================================

    def flow_second_plc(self):
        while True:
            if self.state_machine != 'running':
                time.sleep(0.1)
                continue
            
            try:
                result = self.clients['MPS_PRESSING'].read_input_registers(address = input_register_pressing_plc.MB_PART_AV, slave = 0)
            except ValueError as e:
                print('meu erro: ', e)
                continue
                
            if result.registers[0] == 1:
                if self.state_machine != 'running':
                    continue
                    
                print("Peça detectada no início da esteira")
                time.sleep(1)
                
                if self.state_machine != 'running':
                    continue
                    
                self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 1, slave = 0)
                self.gemeo.set_parameter(DI.Conveyor_Job, True)
                self.gemeo.commit_all()
                
                while True:
                    if self.state_machine != 'running':
                        self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 0, slave = 0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        break
                    
                    result_barreira = self.clients['MPS_PRESSING'].read_input_registers(address = input_register_pressing_plc.MB_BARREIRA_IND, count = 1, slave = 0)
                    
                    if not result_barreira.isError() and result_barreira.registers[0] == 1:
                        print("Peça chegou na barreira indutiva - identificando cor...")
                        
                        self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 0, slave = 0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        time.sleep(0.3)
                        
                        result_sensor = self.clients['MPS_PRESSING'].read_input_registers(address = input_register_pressing_plc.MB_SENSOR_IND, count = 1, slave = 0)
                        
                        if not result_sensor.isError():
                            if result_sensor.registers[0] == 1:

                                print("Peça PRATA confirmada!")

                                if self.parts and self.parts[-1] == "indefinido":
                                    self.parts[-1] = "prata"

                            else:
                                print("Peça ROSA confirmada!")
                                if self.parts and self.parts[-1] == "indefinido":
                                    self.parts[-1] = "rosa"
                        
                        time.sleep(0.5)
                        self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 1, slave = 0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, True)
                        self.gemeo.commit_all()
                        break
                    
                    time.sleep(0.05)
                
                while True:
                    if self.state_machine != 'running':
                        self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 0, slave = 0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        break
                        
                    result_fim = self.clients['MPS_PRESSING'].read_input_registers(address = input_register_pressing_plc.MB_PC_FIM, count = 1, slave = 0)
                    
                    if not result_fim.isError() and result_fim.registers[0] == 1:
                        print("Peça chegou no final da esteira")
                        self.clients['MPS_PRESSING'].write_register(address = holding_register_pressing_plc.MB_LIGA_ESTEIRA, value = 0, slave = 0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        
                        if(self.parts[0] == 'prata'):
                            
                            escrever_saida_digital(HOST, 0, True)
                            escrever_saida_digital(HOST, 1, False)
                            escrever_saida_digital(HOST, 2, True)

                        elif(self.parts[0] == 'rosa'):
                            
                            escrever_saida_digital(HOST, 0, True)
                            escrever_saida_digital(HOST, 1, True)
                            escrever_saida_digital(HOST, 2, False)

                        elif(self.parts[0] == 'preto'):
                            
                            escrever_saida_digital(HOST, 0, True)
                            escrever_saida_digital(HOST, 1, True)
                            escrever_saida_digital(HOST, 2, True)

                        time.sleep(60)

                        escrever_saida_digital(HOST, 0, False)
                        escrever_saida_digital(HOST, 1, False)
                        escrever_saida_digital(HOST, 2, False)


                        print(f"\n =========> Histórico de peças: {self.parts}")
                        self.parts.pop(0)
                        print(f"\n =========> Histórico de peças: {self.parts}")

                        break
                    
                    time.sleep(0.05)