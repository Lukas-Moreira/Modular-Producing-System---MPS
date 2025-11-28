
# Scanner

Scanner I/O configurável para com interface amigável e configuração flexível.

## 🚀 Características

- ✅ Configuração externa via JSON
- ✅ Interface intuitiva com emojis
- ✅ Logging robusto
- ✅ Tratamento de erros avançado
- ✅ Editor de descrições integrado
- ✅ Múltiplos filtros de visualização
- ✅ Código modular e organizando

## 📁 Estrutura do Projeto

```
├── 📁 .cfg
│   └── ⚙️ config.json
├── 📁 scan_complete
│   └── 🐍 factory_io_scanner_complete.py
├── 📁 src
│   ├── 📁 controllers
│   ├── 📁 logs
│   ├── 📁 modules
│   │   ├── 🐍 config.py
│   │   ├── 🐍 edge_monitor.py
│   │   ├── 🐍 modbus_client.py
│   │   └── 🐍 scanner.py
│   ├── 📁 services
│   │   ├── 🐍 ui.py
│   │   └── 🐍 utils.py
│   └── 🐍 main.py
├── 📁 tests
│   └── 🐍 test_edge.py
├── 📝 README.md
└── 📄 requirements.txt
```

## ⚙️ Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
Execute a aplicação:
bash

# Scanner

Scanner I/O configurável para com interface leve, logging e configuração flexível.

**Resumo rápido:**
- **Entrada/Leitura**: escaneia I/Os via Modbus.
- **Configuração**: centralizada em `./.cfg/config.json` (gerada automaticamente na primeira execução).
- **Execução**: `python src/main.py` (ou `python scan_complete/factory_io_scanner_complete.py`).

**Projeto em uma árvore**

```
├── 📁 .cfg
│   └── ⚙️ config.json
├── 📁 scan_complete
│   └── 🐍 factory_io_scanner_complete.py
├── 📁 src
│   ├── 📁 controllers
│   ├── 📁 logs
│   ├── 📁 modules
│   │   ├── 🐍 config.py
│   │   ├── 🐍 edge_monitor.py
│   │   ├── 🐍 modbus_client.py
│   │   └── 🐍 scanner.py
│   ├── 📁 services
│   │   ├── 🐍 ui.py
│   │   └── 🐍 utils.py
│   └── 🐍 main.py
├── 📁 tests
│   └── 🐍 test_edge.py
├── 📝 README.md
└── 📄 requirements.txt
```

**Observação:** este `README` documenta o projeto como está na árvore acima (pt-BR).

**Índice**
- **Projeto**
- **Instalação**
- **Configuração**
- **Como executar**
- **Arquitetura dos módulos**
- **Logs e arquivos gerados**
- **Testes**
- **Desenvolvimento e contribuição**

**Instalação**

- **Requisitos:** Python 3.8+ (recomendado 3.10+).
- **Instalar dependências:**

```powershell
pip install -r requirements.txt
```

**Configuração**

- O arquivo principal de configuração fica em `./.cfg/config.json` e é criado automaticamente na primeira execução com valores padrão.
- Principais chaves esperadas (exemplo):

```json
{
	"connection": {"ip": "127.0.0.1", "port": 502, "timeout": 3},
	"mapping": {
		"coils": [],
		"discrete_inputs": [],
		"holding_registers": [],
		"input_registers": []
	},
	"display": {"scale": 1.0, "decimals": 2},
	"files": {"descriptions": "factory_io_descriptions.json", "logs_dir": "src/logs"}
}
```

- Edite `./.cfg/config.json` para ajustar IP/porta do servidor Modbus, timeouts, mapeamento de endereços e opções de display.

**Como executar**

- Executar a versão principal (modular):

```powershell
python src/main.py
```

- Executar o script completo de exemplo (variante completa):

```powershell
python scan_complete/factory_io_scanner_complete.py
```

- Durante a execução pelo `ui.py` (CLI), siga o menu exibido para iniciar o escaneamento, aplicar filtros e editar descrições.

**Arquitetura e responsabilidade dos módulos**

- **`src/main.py`**: orquestra a aplicação e inicializa configuração, logging e interface.
- **`src/modules/config.py`**: leitura/validação e gerenciamento do arquivo `./.cfg/config.json`.
- **`src/modules/modbus_client.py`**: abstrai a comunicação Modbus (conexão, leitura de coils/registers, timeouts).
- **`src/modules/scanner.py`**: lógica de escaneamento dos endereços configurados, conversões e detecção de mudanças.
- **`src/modules/edge_monitor.py`**: processamento de eventos de borda (edge detection) e geração de alertas/ações.
- **`src/services/ui.py`**: interface do usuário (menu CLI), validação de entradas e exibição de resultados.
- **`src/services/utils.py`**: utilitários de suporte: formatação, serialização JSON, helpers de logging.
- **`src/logs/`**: local onde os logs de execução são gravados por padrão.
- **`scan_complete/factory_io_scanner_complete.py`**: versão auto-contida/mais direta do scanner (script utilitário).

**Logs e rastreamento**

- Logs estruturados são escritos em `src/logs/` (ou no caminho definido em `config.json`).
- Em caso de erro, verifique `src/logs/factory_io_scanner.log` (nome e local dependem da configuração).

**Testes**

- Testes unitários estão em `tests/test_edge.py`.
- Executar testes com `pytest`:

```powershell
python -m pytest -q
```

Se não tiver `pytest` instalado, adicione `pytest` ao `requirements.txt` ou instale com `pip install pytest`.

**Notas de desenvolvimento**

- Codestyle: siga o estilo já presente no repositório. Evite mudanças de formatação não solicitadas.
- Se for modificar `config.json`, mantenha o esquema das chaves para compatibilidade.

**Problemas comuns & Resolução rápida**

- Erro de conexão Modbus: verifique `connection.ip`, `connection.port` e `timeout` em `./.cfg/config.json`.
- Arquivo de configuração não criado: verifique permissões do diretório onde o repositório está sendo executado.

**Contribuição**

- Abra uma issue ou PR no repositório com descrição clara do problema/feature.
- Inclua testes para mudanças de lógica relevantes.

---

Se quiser, eu posso:
- rodar os testes agora (`python -m pytest -q`) ou
- ajustar o `config.json` de exemplo com valores reais.

Diga qual opção prefere e eu procedo.