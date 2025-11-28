
# Factory I/O Scanner

Scanner I/O configurável para Factory I/O com interface amigável e configuração flexível.

## 🚀 Características

- ✅ Configuração externa via JSON
- ✅ Interface intuitiva com emojis
- ✅ Logging robusto
- ✅ Tratamento de erros avançado
- ✅ Editor de descrições integrado
- ✅ Múltiplos filtros de visualização
- ✅ Código modular e organizando

## 📁 Estrutura do Projeto

factory_io_scanner/ ├── main.py # Arquivo principal ├── config.py # Gerenciamento de configurações ├── scanner.py # Lógica de escaneamento ├── modbus_client.py # Cliente Modbus ├── ui.py # Interface do usuário ├── utils.py # Utilitários e logging ├── requirements.txt # Dependências ├── config.json # Configuração (gerado automaticamente) ├── factory_io_descriptions.json # Descrições personalizadas └── logs/ # Diretório de logs └── factory_io_scanner.log
text



## ⚙️ Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
Execute a aplicação:
bash


python main.py

🔧 Configuração
O arquivo config.json é gerado automaticamente com as configurações padrão. Você pode editá-lo para personalizar:
Conexão: IP, porta, timeout
Mapeamento Modbus: Quantidade e endereços dos I/Os
Display: Fator de escala, casas decimais
Arquivos: Localização dos arquivos de dados

📋 Uso
Execute python main.py
Escolha opção "1" para escanear I/Os
Use as opções 2-7 para visualizar com filtros
Use opção "8" para editar descrições personalizadas
🛠️ Melhorias Implementadas
✅ Correção de problemas de encoding UTF-8
✅ Configuração externa flexível
✅ Validação robusta de entrada do usuário
✅ Tratamento específico de exceções
✅ Timeout configurável para conexões Modbus
✅ Logging estruturado com níveis
✅ Código modular e bem documentado
✅ Interface melhorada com feedback visual
📞 Suporte
Para dúvidas ou problemas, verifique os logs em logs/factory_io_scanner.log
text


📊 RESUMO DAS MELHORIAS
✅ Versão Completa:
Encoding corrigido - UTF-8 adequado 
Configuração externa - Arquivo JSON configurável
Validação robusta - Input do usuário validado
Logging estruturado - Logs organizados por nível
Tratamento de erros específico - Exceções detalhadas
Timeout configurável - Conexões Modbus com timeout
Documentação completa - Docstrings detalhadas
🗂️ Versão Modular:
config.py - Gerenciamento centralizado de configurações
modbus_client.py - Cliente Modbus encapsulado
scanner.py - Lógica de escaneamento isolada
ui.py - Interface do usuário separada
utils.py - Utilitários e logging
main.py - Orquestração da aplicação
requirements.txt - Dependências explícitas
README.md - Documentação completa