import os
import sys
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from modules.scanner import MPScanner

class UserInterface:
    """Interface do usuário para o scanner Factory I/O"""
    
    def __init__(self, scanner: MPScanner):
        self.scanner = scanner
    
    def display_table(self, filter_type: str = 'ALL'):
        """Exibe tabela formatada com dados dos I/Os"""
        if not self.scanner.io_data:
            print("❌ Nenhum dado disponível. Execute primeiro o escaneamento.")
            return
        
        filtered_data = self._apply_filter(filter_type)
        
        if not filtered_data:
            print(f"❌ Nenhum I/O encontrado com filtro: {filter_type}")
            return
        
        self._print_table(filtered_data, filter_type)
    
    def _apply_filter(self, filter_type: str) -> List[Dict]:
        """Aplica filtro aos dados"""
        data = self.scanner.io_data
        
        if filter_type == 'ALL':
            return data
        elif filter_type == 'ENTRADA':
            return [io for io in data if io['io_type'] == 'ENTRADA']
        elif filter_type == 'SAÍDA':
            return [io for io in data if io['io_type'] == 'SAÍDA']
        elif filter_type == 'DIGITAL':
            return [io for io in data if io['data_type'] == 'DIGITAL']
        elif filter_type == 'ANALÓGICO':
            return [io for io in data if io['data_type'] == 'ANALÓGICO']
        elif filter_type == 'ATIVO':
            return [io for io in data if io['state'] not in ['OFF', '0', '0.00']]
        else:
            return data
    
    def _print_table(self, data: List[Dict], filter_type: str):
        """Imprime tabela formatada"""
        os.system('cls' if sys.platform == 'win32' else 'clear')
        
        title = f"TABELA I/O FACTORY I/O - ({len(data)} registros)"
        if filter_type != 'ALL':
            title += f" - FILTRO: {filter_type}"
        
        print(f"\n📋 {title}")
        print("=" * 110)
        
        # Cabeçalho
        header = f"{'TAG':<6} {'MODBUS':<12} {'E/S':<8} {'TIPO':<10} {'ESTADO':<15} {'FUNÇÃO':<18} {'DESCRIÇÃO':<35}"
        print(header)
        print("-" * 110)
        
        # Dados
        for io in data:
            tag = io['tag']
            modbus_info = f"{io['modbus_type']} {io['address']}"
            io_type = io['io_type']
            data_type = io['data_type']
            state = f"{io['state_emoji']} {io['state']}"
            function = io['function']
            
            description = io['description'] or "[Pressione 8 para editar]"
            if len(description) > 32:
                description = description[:29] + "..."
            
            row = f"{tag:<6} {modbus_info:<12} {io_type:<8} {data_type:<10} {state:<15} {function:<18} {description:<35}"
            print(row)
        
        self._print_statistics(data)
    
    def _print_statistics(self, data: List[Dict]):
        """Imprime estatísticas dos dados"""
        print("-" * 110)
        
        digitais = len([io for io in data if io['data_type'] == 'DIGITAL'])
        analogicos = len([io for io in data if io['data_type'] == 'ANALÓGICO'])
        entradas = len([io for io in data if io['io_type'] == 'ENTRADA'])
        saidas = len([io for io in data if io['io_type'] == 'SAÍDA'])
        ativos = len([io for io in data if io['state'] not in ['OFF', '0', '0.00']])
        
        print(f"📊 ESTATÍSTICAS:")
        print(f"   🟢 Entradas: {entradas} | 🔴 Saídas: {saidas}")
        print(f"   ⚡ Digitais: {digitais} | 📊 Analógicos: {analogicos}")
        print(f"   🔥 Ativos: {ativos} | 📋 Total: {len(data)}")
    
    def edit_descriptions(self):
        """Editor interativo de descrições"""
        if not self.scanner.io_data:
            print("❌ Execute primeiro o escaneamento.")
            return
        
        print("\n✏️ EDITOR DE DESCRIÇÕES - FACTORY I/O")
        print("=" * 50)
        print("💡 Exemplos de descrições úteis:")
        print("   • DI01: 'Botão Start Linha 1'")
        print("   • DO05: 'Motor Esteira Principal'")
        print("   • AI02: 'Sensor Temperatura (°C)'")
        print("💡 Digite 'sair' para terminar\n")
        
        changes_made = False
        
        for io in self.scanner.io_data:
            current_desc = io['description'] or "[VAZIO]"
            
            print(f"\n🔧 {io['tag']} - {io['function']}")
            print(f"   Modbus: {io['modbus_type']} {io['address']}")
            print(f"   Estado: {io['state_emoji']} {io['state']}")
            print(f"   Descrição atual: {current_desc}")
            
            try:
                new_desc = input("   Nova descrição: ").strip()
            except KeyboardInterrupt:
                print("\n⚠️ Operação cancelada.")
                break
            
            if new_desc.lower() == 'sair':
                break
            
            if new_desc != io['description']:
                io['description'] = new_desc
                self.scanner.custom_descriptions[io['key']] = new_desc
                changes_made = True
                print(f"   ✅ {io['tag']} atualizado!")
        
        if changes_made:
            if self.scanner.save_custom_descriptions():
                print(f"\n💾 Descrições salvas!")
            else:
                print(f"\n❌ Erro salvando descrições!")

def get_valid_choice(prompt: str, valid_choices: List[str]) -> str:
    """Solicita entrada válida do usuário"""
    while True:
        try:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            else:
                print(f"❌ Opção inválida! Escolha entre: {', '.join(valid_choices)}")
        except KeyboardInterrupt:
            print("\n⚠️ Operação cancelada.")
            return "0"
