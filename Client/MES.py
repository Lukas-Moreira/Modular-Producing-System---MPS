import time
import Utils.logger as loggerManager

from typing import Optional
from dataclasses import dataclass
from pymodbus.client import ModbusTcpClient

from Maps.Mapping import input_register_handling_plc
from Maps.Mapping import holding_register_handling_plc
from Maps.Mapping import input_register_pressing_plc
from Maps.Mapping import holding_register_pressing_plc

import pyodbc

# ==== robot
import rtde_io
import rtde_receive
from Server.DigitalTwin import DigitalTwin, DI, INPUT_HR


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
        print(f"Erro ao escrever na saída digital: {e}")
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

PLC_ROLE_MAP = {
    "MPS_HANDLING": "handling",
    "MPS_PRESSING": "pressing",
    "MPS_SORTING":  "sorting",
}

@dataclass
class Piece:
    id: int

class MES:
    '''
    Classe que abstrai o MES do Sistema de Produção Modular (MPS).

    Métodos:
        - get_plc(name: str) -> ModbusTcpClient: Retorna o cliente Modbus do PLC pelo nome.
        - stop_all_operations(): Para todas as operações de todos os PLC's.
        - reset_to_home_position(): Reseta o sistema para a posição home.
        - monitor_buttons(): Monitora os botões de start, stop e reset.
        - handle_lamp(): Controla as lâmpadas indicadoras de status.
        - gripper_open(): Abre a garra do manipulador.
        - gripper_close(): Fecha a garra do manipulador.
        - gripper_down(): Desce a garra do manipulador.
        - gripper_up(): Sobe a garra do manipulador.
        - move_to_home(): Move o manipulador para a posição home.
        - move_to_reject(): Move o manipulador para a posição de rejeito.
        - move_to_drop(): Move o manipulador para a posição de deixar peça.
        - magazine_eject(): Ejetar peça do magazine.
        - magazine_advance(): Avança o magazine para a posição de pegar peça.
        - flow_first_plc(): Fluxo principal do PLC de manuseio.
        - flow_second_plc(): Fluxo principal do PLC de prensagem.
    '''
    def __init__(self, clients: Optional[dict[str, ModbusTcpClient]] = None, gemeo: DigitalTwin = None):
        self.logger = loggerManager.LoggerManager()
        self.logger.set_name('MES of MPS')

        self.clients = clients or {}
        self.parts = []

        self.preemption_lamp_control = False

        self.state_machine = 'running'
        self.gemeo = gemeo

        self.db_connection_string = (
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=localhost\\SQLEXPRESS;'
            'DATABASE=db_mps;'
            'Trusted_Connection=yes;'
        )

        self.is_conveyor_available = True

        if not self.clients:
            self.logger.set_level("ERROR")
            self.logger.logger.error("MES inicializado sem clientes Modbus.")
            raise ValueError("MES inicializado sem clientes Modbus.")
        

    def get_db_connection(self):
        """Cria e retorna uma conexão com o banco de dados."""
        return pyodbc.connect(self.db_connection_string)
    

    def get_active_order(self):
        """
        Busca a ordem de produção mais antiga que ainda não foi finalizada.
        
        Returns:
            dict: Dicionário com os dados da ordem ativa ou None se não houver ordem ativa.
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT TOP 1
                id,
                order_name,
                color_requested,
                quantity_requested,
                quantity_processed,
                created_at
            FROM production_orders
            WHERE finished_at IS NULL
            ORDER BY created_at ASC
            """
            
            cursor.execute(query)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row.id,
                    'order_name': row.order_name,
                    'color_requested': row.color_requested,
                    'quantity_requested': row.quantity_requested,
                    'quantity_processed': row.quantity_processed,
                    'created_at': row.created_at
                }
            
            return None
            
        except Exception as e:
            print(f"Erro ao buscar ordem ativa: {e}")

            return None
    

    def register_piece(self, color: str, result: int, order_id: int = None):
        """
        Registra uma peça processada no banco de dados.
        
        Args:
            color (str): Cor da peça ('preto', 'prata', 'rosa')
            result (int): 1 para aprovada, 0 para rejeitada
            order_id (int): ID da ordem de produção (opcional)
        
        Returns:
            bool: True se registrado com sucesso, False caso contrário
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = """
            INSERT INTO pieces (piece_color, result, order_id, created_at)
            VALUES (?, ?, ?, GETDATE())
            """
            
            cursor.execute(query, color, result, order_id)
            conn.commit()
            conn.close()
            
            status = "APROVADA" if result == 1 else "REJEITADA"
            print(f"Peça {color} {status} registrada no banco (Order ID: {order_id})")
            return True
            
        except Exception as e:
            print(f"Erro ao registrar peça: {e}")
            return False
        

    def update_order_progress(self, order_id: int):
        """
        Incrementa o contador de peças processadas de uma ordem.
        Se atingir a quantidade solicitada, marca a ordem como finalizada.
        Sempre atualiza updated_at.
        
        Args:
            order_id (int): ID da ordem a ser atualizada
        
        Returns:
            bool: True se atualizado com sucesso, False caso contrário
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query_update = """
            UPDATE production_orders
            SET quantity_processed = quantity_processed + 1,
                updated_at = GETDATE()
            WHERE id = ?
            """
            
            cursor.execute(query_update, order_id)
            
            query_check = """
            SELECT quantity_requested, quantity_processed
            FROM production_orders
            WHERE id = ?
            """
            
            cursor.execute(query_check, order_id)
            row = cursor.fetchone()
            
            if row and row.quantity_processed >= row.quantity_requested:
                query_finish = """
                UPDATE production_orders
                SET finished_at = GETDATE(),
                    updated_at = GETDATE()
                WHERE id = ?
                """
                cursor.execute(query_finish, order_id)
                print(f"Ordem ID {order_id} FINALIZADA!")
            
            conn.commit()
            conn.close()
            
            print(f"Ordem ID {order_id} atualizada: {row.quantity_processed}/{row.quantity_requested}")
            return True
            
        except Exception as e:
            print(f"Erro ao atualizar ordem: {e}")
            return False
    
    def get_plc(self, name: str) -> ModbusTcpClient:
        '''
        Método para obter o cliente Modbus de um PLC pelo nome.

        Args:
            name (str): Nome do PLC (e.g., 'MPS_HANDLING', 'MPS_PRESSING', 'MPS_SORTING').

        Returns:
            ModbusTcpClient: Cliente Modbus do PLC solicitado.

        Raises:
            KeyError: Se o PLC com o nome fornecido não for encontrado.
        '''
        try:
            return self.clients[name]
        except KeyError:
            raise KeyError(f"PLC '{name}' não encontrado no MES.")
        

    def stop_all_operations(self):
        '''
        Método para parar todas as operações de todos os PLC's.
        '''
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
        '''
        Método que reseta o sistema: sobe garra, recua magazine e vai para home
        '''        
        print("RESETANDO SISTEMA...")
        
        try:
            print("1. Subindo garra...")
            self.gripper_up()
            time.sleep(0.5)
            
            print("2. Recuando magazine...")
            self.magazine_eject()
            time.sleep(0.5)

            gripper_state = self.clients['MPS_HANDLING'].read_holding_registers(address = holding_register_handling_plc.GRIPPER_OPEN, slave = 0)
            
            if(gripper_state.registers[0] == 0):
                print("movendo para o rejeito")
                self.move_to_reject_reset()
                
                self.gripper_down()
                
                time.sleep(0.1)
                self.gripper_open()

                time.sleep(0.2)

                self.gripper_up()
                time.sleep(0.5)

            
            print("3. Movendo para HOME...")
            self.move_to_home_reset()
            
            print("Sistema resetado com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro ao resetar sistema: {e}")
            return False


    def monitor_buttons(self):
        '''
        Método que monitora os botões de start, stop e reset do sistema.

        Principal funcionalidade:
            - Start: Inicia o sistema se estiver em estado 'idle'.
            - Stop: Para o sistema se estiver em estado 'running' ou 'cycle'.
            - Reset: Reseta o sistema se estiver em estado 'stopped' ou 'cycle'.
        
        Observação:
            - O estado do sistema é gerenciado pela variável 'state_machine'.
            - As ações dos botões são refletidas nas lâmpadas indicadoras e no Digital Twin.
        '''

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
        '''
        Método que controla as lâmpadas indicadoras de status do sistema.

        Estados e comportamentos:
            - running: Lâmpada verde acesa.
            - idle:        Lâmpada verde acesa, lâmpada amarela piscando.
            - error:       Lâmpada vermelha e amarela acesas.
            - emergency:   Lâmpada vermelha piscando.
            - cycle:       Lâmpadas vermelha, amarela e verde piscando em sequência.
            - stopped:     Lâmpada vermelha acesa.
        
        Observação:
            - O estado do sistema é determinado pela variável 'state_machine'.
            - As lâmpadas são controladas via registros Modbus e atualizadas no Digital Twin.
        '''
        while True:

            if self.preemption_lamp_control: 
                time.sleep(0.1)
                continue
    
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

                elif state == "no_product":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                    self.gemeo.set_parameter(DI.LAMP_GREEN_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_YELLOW_DT, False)
                    self.gemeo.set_parameter(DI.LAMP_RED_DT, True)
                    self.gemeo.commit_all()
                    time.sleep(0.1)

                elif state == "no_product":
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                    self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
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
        '''
        Método para abrir a garra do sistema.

        Returns:
            bool: True se a garra foi aberta com sucesso, False em caso de erro.
        '''
        print("Abrindo garra...")
        
        resultado = self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.GRIPPER_OPEN, value=1, slave=0)
        self.gemeo.set_parameter(DI.Crane_Feeder_Claw, False)
        self.gemeo.commit_all()
        
        if resultado.isError():
            print(f"Erro ao abrir garra: {resultado}")
            return False
        
        time.sleep(0.5)
        print("Garra aberta")
        return True

    def gripper_close(self):
        '''
        Método para fechar a garra do sistema.

        Returns:
            bool: True se a garra foi fechada com sucesso, False em caso de erro.
        '''

        print("Fechando garra...")
        
        resultado = self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.GRIPPER_OPEN, value=0, slave=0)
        self.gemeo.set_parameter(DI.Crane_Feeder_Claw, True)
        self.gemeo.commit_all()
        
        if resultado.isError():
            print(f"Erro ao fechar garra: {resultado}")
            return False
        
        time.sleep(0.7)
        print("Garra fechada")
        return True

    def gripper_down(self):
        '''
        Método para descer a garra do sistema.

        Returns:
            bool: True se a garra desceu com sucesso, False em caso de erro.
        
        Observação:
            - Verifica se a garra já está na posição baixa antes de descer.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''

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
            # if self.state_machine != 'running':
            #     self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 0, slave = 0)
            #     print("Operação cancelada - sistema parado")
            #     return False
                
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_garra_avancada, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                print("Garra desceu")
                return True
            
            time.sleep(0.05)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_DOWN, value = 0, slave = 0)
        print("ERRO: Timeout ao descer garra\n")
        return False

    def gripper_up(self):
        '''
        Método para subir a garra do sistema.

        Returns:
            bool: True se a garra subiu com sucesso, False em caso de erro.
        
        Observação:
            - Verifica se a garra já está na posição alta antes de subir.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''

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
        '''
        Método para mover o manipulador para a posição home durante o reset do sistema.

        Returns:
            bool: True se o manipulador chegou na posição home com sucesso, False em caso de erro.
        
        Observação:
            - Não verifica o estado da máquina, pois é usado durante o reset.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''

        print("Movendo para HOME (reset)...")
        
        result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
        
        if not result.isError() and result.registers[0] == 1 and INPUT_HR.Crane_Fedder_Setpoint_X == 1000:
            print("Braço já está na posição HOME")
            return True
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 0, slave = 0)
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 1, slave = 0)

        self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 1000)
        print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.clients['MPS_HANDLING'].read_input_registers(address = input_register_handling_plc.sensor_braco_home, count = 1, slave = 0)
            
            if not result.isError() and result.registers[0] == 1:
                
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
                self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_MAGAZINE_ESQ, value = 0, slave = 0)                
                
                self.gemeo.set_parameter(INPUT_HR.Crane_Fedder_Setpoint_X, 1000)
                
                print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
                
                self.gemeo.commit_all()
                
                print("Braço chegou na posição HOME")
                return True
            
            time.sleep(0.1)
        
        self.clients['MPS_HANDLING'].write_register(address = holding_register_handling_plc.GRIPPER_TO_STATION_DIR, value = 0, slave = 0)
        print("ERRO: Timeout ao mover para HOME")
        return False
    
    def move_to_home(self):
        '''
        Método para mover o manipulador para a posição home durante a operação normal.

        Returns:
            bool: True se o manipulador chegou na posição home com sucesso, False em caso de erro.
        
        Observação:
            - Verifica o estado da máquina antes de iniciar o movimento.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
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
        print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
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
        '''
        Método para mover o manipulador para a posição rejeito durante a operação normal.

        Returns:
            bool: True se o manipulador chegou na posição rejeito com sucesso, False em caso de erro.
        
        Observação:
            - Verifica o estado da máquina antes de iniciar o movimento.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
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
        print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
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
    
    def move_to_reject_reset(self):
        '''
        Método para mover o manipulador para a posição rejeito durante a operação normal.

        Returns:
            bool: True se o manipulador chegou na posição rejeito com sucesso, False em caso de erro.
        
        Observação:
            - Verifica o estado da máquina antes de iniciar o movimento.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
        
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

        print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
        self.gemeo.commit_all()
        
        timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < timeout:
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
        '''
        Método para mover o manipulador para a posição deixa durante a operação normal.

        Returns:
            bool: True se o manipulador chegou na posição deixa com sucesso, False em caso de erro.
        
        Observação:
            - Verifica o estado da máquina antes de iniciar o movimento.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
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
        print(f"Valor: {INPUT_HR.Crane_Fedder_Setpoint_X}")
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
        '''
        Método para ejetar a peça do magazine.

        Returns:
            bool: True se a peça foi ejetada com sucesso, False em caso de erro.
        
        Observação:
            - Verifica se o magazine já está recuado antes de ejetar.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
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
        '''
        Método para avançar o magazine.

        Returns:
            bool: True se o magazine foi avançado com sucesso, False em caso de erro.
        
        Observação:
            - Verifica se o magazine já está avançado antes de avançar.
            - Utiliza um timeout para evitar espera indefinida.
            - Notifica o Digital Twin sobre o status da operação.
        '''
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
        '''
        Método para reconhecer e exibir o estado dos botões de start, stop e reset do PLC de manuseio.

        Returns:
            None
        
        Observação:
            - Lê os registradores de entrada correspondentes aos botões.
            - Exibe o estado atual dos botões a cada 2 segundos.
        '''
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
        '''
        Método principal para o fluxo de operações do PLC de manuseio.

        Funcionalidades:
            - Verificação do estado da máquina.
            - Avanço e ejeção do magazine.
            - Operações da garra (abrir, fechar, mover para posições específicas).
            - Detecção e classificação de peças (preto, prata, rosa).
            - SÓ PROCESSA SE HOUVER ORDEM ATIVA
        
        Returns:
            None
        
        Observação:
            - O fluxo é contínuo e depende do estado da máquina.
            - Utiliza registros Modbus para comunicação com o PLC.
            - Armazena a classificação das peças em uma lista 'parts'.
            - BLOQUEIA processamento se não houver ordem ativa
        '''

        print('Iniciando flow_first_plc...')
        self.magazine_eject()
        
        while True:
            if self.state_machine != 'running':
                time.sleep(0.1)
                continue
            
            active_order = self.get_active_order()
            
            if not active_order:
                print("Nenhuma ordem ativa - aguardando nova ordem...")
                time.sleep(2)
                continue
            
            self.magazine_advance()
            if self.state_machine != 'running':
                continue
                
            self.magazine_eject()
            if self.state_machine != 'running':
                continue
            
            result = self.clients['MPS_HANDLING'].read_input_registers(address=input_register_handling_plc.sensor_peca_suporte, count=1, slave=0)
            
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
                result_sensor_garra = self.clients['MPS_HANDLING'].read_input_registers(address=input_register_handling_plc.sensor_peca_garra, count=1, slave=0)
                
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
                
                removido = True

                print("Aguardando esteira ficar disponível...")
                timeout_esteira = 120 
                start_wait = time.time()
                
                while not self.is_conveyor_available:
                    if self.state_machine != 'running':
                        print("Operação cancelada - sistema parado")
                        return False
                    
                    if time.time() - start_wait > timeout_esteira:
                        print("ERRO: Timeout ao aguardar liberação da esteira!")
                        self.state_machine = "error"
                        removido = False
                        return False
                    
                    time.sleep(0.1)
                
                print("Esteira disponível! Depositando peça...")
                
                self.is_conveyor_available = False
                
                if removido == True:
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

            else:
                self.preemption_lamp_control = True
                time.sleep(0.1)

                self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_GREEN, value=0, slave=0)
                self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_YELLOW, value=1, slave=0)
                self.clients['MPS_HANDLING'].write_register(address=holding_register_handling_plc.LAMP_RED, value=1, slave=0)
                
                time.sleep(5)

                self.preemption_lamp_control = False


    # =============================================
    #  ================ SECOND PLC ================ 
    # =============================================

    def flow_second_plc(self):
        '''
        Método principal para o fluxo de operações do PLC de prensagem.

        Funcionalidades:
            - Verificação do estado da máquina.
            - Detecção de peças na esteira.
            - Identificação da cor das peças (prata, rosa).
            - Controle da esteira e sinalização via Digital Twin.
            - Liberação da flag is_conveyor_available quando peça sai do sensor final
            - Integração com ordens de produção (aprovação/rejeição baseada em cor)
            - SÓ PROCESSA SE HOUVER ORDEM ATIVA
        
        Returns:
            None
        
        Observação:
            - O fluxo é contínuo e depende do estado da máquina.
            - Utiliza registros Modbus para comunicação com o PLC.
            - Utiliza a lista 'parts' para armazenar a classificação das peças
            - Registra peças aprovadas/rejeitadas no banco de dados
            - BLOQUEIA processamento se não houver ordem ativa
        '''
        while True:
            if self.state_machine != 'running':
                time.sleep(0.1)
                continue
            
            active_order = self.get_active_order()
            
            if not active_order:
                print("Nenhuma ordem ativa - aguardando nova ordem...")
                time.sleep(2)
                continue
            
            try:
                result = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_PART_AV, count=1, slave=0)
            except Exception as e:
                print(f'Erro ao ler sensor de entrada: {e}')
                time.sleep(0.1)
                continue
            
            if result.isError():
                print("Erro ao ler MB_PART_AV")
                time.sleep(0.1)
                continue
                
            if result.registers[0] == 1:
                self.is_conveyor_available = False
                
                if self.state_machine != 'running':
                    continue
                    
                print("Peça detectada no início da esteira")
                time.sleep(1)
                
                if self.state_machine != 'running':
                    continue
                    
                self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=1, slave=0)
                self.gemeo.set_parameter(DI.Conveyor_Job, True)
                self.gemeo.commit_all()
                
                while True:
                    if self.state_machine != 'running':
                        self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=0, slave=0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        break
                    
                    result_barreira = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_BARREIRA_IND, count=1, slave=0)
                    
                    if not result_barreira.isError() and result_barreira.registers[0] == 1:
                        print("Peça chegou na barreira indutiva - identificando cor...")
                        
                        self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=0, slave=0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        time.sleep(0.3)
                        
                        result_sensor = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_SENSOR_IND, count=1, slave=0)
                        
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
                        self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=1, slave=0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, True)
                        self.gemeo.commit_all()
                        break
                    
                    time.sleep(0.05)
                
                while True:
                    if self.state_machine != 'running':
                        self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=0, slave=0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        break
                        
                    result_fim = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_PC_FIM, count=1, slave=0)
                    
                    if not result_fim.isError() and result_fim.registers[0] == 1:
                        print("Peça chegou no final da esteira")
                        
                        self.clients['MPS_PRESSING'].write_register(address=holding_register_pressing_plc.MB_LIGA_ESTEIRA, value=0, slave=0)
                        self.gemeo.set_parameter(DI.Conveyor_Job, False)
                        self.gemeo.commit_all()
                        
                        if not self.parts:
                            print("AVISO: Lista de peças vazia! Pulando comando do robô.")
                            self.is_conveyor_available = True
                            break
                        
                        cor_atual: str
                        cor_atual = self.parts[0]
                        print(f"\n========================================")
                        print(f"Processando peça: {cor_atual.upper()}")
                        print(f"Histórico: {self.parts}")
                        
                        active_order = self.get_active_order()
                        
                        if not active_order:
                            print("ERRO: Ordem ativa desapareceu durante processamento!")
                            print("Liberando esteira sem processar")
                            self.is_conveyor_available = True
                            self.parts.pop(0)
                            print(f"========================================\n")
                            break
                        
                        print(f"Ordem ativa: {active_order['order_name']}")
                        print(f"Cor solicitada: {active_order['color_requested']}")
                        print(f"Progresso: {active_order['quantity_processed']}/{active_order['quantity_requested']}")
                        
                        if cor_atual == active_order['color_requested']:
                            print(f"Peça APROVADA - Cor corresponde à ordem!")
                            piece_approved = True
                            self.register_piece(cor_atual, result=1, order_id=active_order['id'])
                            self.update_order_progress(active_order['id'])
                        else:
                            print(f"Peça REJEITADA - Cor não corresponde (esperado: {active_order['color_requested']}, recebido: {cor_atual})")
                            piece_approved = False
                            self.register_piece(cor_atual, result=0, order_id=active_order['id'])
                        
                        print(f"========================================\n")
                        
                        if cor_atual == 'prata':
                            escrever_saida_digital_robot(HOST, 0, True)
                            escrever_saida_digital_robot(HOST, 1, False)
                            escrever_saida_digital_robot(HOST, 2, True)

                        elif cor_atual == 'rosa':
                            escrever_saida_digital_robot(HOST, 0, True)
                            escrever_saida_digital_robot(HOST, 1, True)
                            escrever_saida_digital_robot(HOST, 2, False)

                        elif cor_atual == 'preto':
                            escrever_saida_digital_robot(HOST, 0, True)
                            escrever_saida_digital_robot(HOST, 1, True)
                            escrever_saida_digital_robot(HOST, 2, True)
                        
                        timeout = 60
                        start_time = time.time()
                        robot_finished = False
                        conveyor_freed = False
                        
                        while time.time() - start_time < timeout:
                            if self.state_machine != 'running':
                                print("Operação cancelada - parando robô!")
                                escrever_saida_digital_robot(HOST, 0, False)
                                escrever_saida_digital_robot(HOST, 1, False)
                                escrever_saida_digital_robot(HOST, 2, False)
                                return False
                            
                            try:
                                result_sensor_fim = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_PC_FIM, count=1, slave=0)
                                
                                if not result_sensor_fim.isError() and result_sensor_fim.registers[0] == 0:
                                    if not conveyor_freed:
                                        print("Sensor final LIBERADO - Peça removida da esteira!")
                                        self.is_conveyor_available = True
                                        conveyor_freed = True
                                        self.parts.pop(0)
                                        print(f"Histórico atualizado: {self.parts}\n")
                            except Exception as e:
                                print(f"Erro ao ler sensor final: {e}")
                            
                            try:
                                result_robot = ler_saida_digital_robot(HOST, 5)
                                if result_robot == 1:
                                    print("Robô sinalizou conclusão (DO5 = HIGH)")
                                    robot_finished = True
                                    break
                            except Exception as e:
                                print(f"Erro ao ler saída do robô: {e}")
                            
                            time.sleep(0.05)
                        
                        if not robot_finished:
                            print("TIMEOUT: Robô não sinalizou conclusão em 60s")
                        
                        if not conveyor_freed:
                            print("Forçando liberação da esteira (timeout/erro)")
                            
                            while result_sensor_fim.registers[0] == 1:
                                try:
                                    result_sensor_fim = self.clients['MPS_PRESSING'].read_input_registers(address=input_register_pressing_plc.MB_PC_FIM, count=1, slave=0)
                                    
                                    if not result_sensor_fim.isError() and result_sensor_fim.registers[0] == 0:
                                        print("Esteira liberada manualmente")
                                        self.is_conveyor_available = True
                                        self.parts.pop(0)
                                        print(f"Histórico atualizado: {self.parts}\n")
                                        break
                                except Exception as e:
                                    print(f"Erro na liberação manual: {e}")
                                
                                time.sleep(0.1)
                        
                        escrever_saida_digital_robot(HOST, 0, False)
                        escrever_saida_digital_robot(HOST, 1, False)
                        escrever_saida_digital_robot(HOST, 2, False)
                        
                        print(f"Status: Esteira livre={self.is_conveyor_available} | Peças restantes={len(self.parts)}\n")
                        break
                    
                    time.sleep(0.05)
            
            time.sleep(0.1)