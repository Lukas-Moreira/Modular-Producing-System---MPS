# 📟 Scanner Modbus (Factory I/O)

Scanner I/O modular, leve e configurável, com detecção de bordas, logging estruturado e configuração externa via JSON.

---

## 🚀 Principais Recursos

- ✅ Configuração totalmente externa em `./.cfg/config.json`
- ✅ Interface CLI intuitiva com exibição amigável (emojis)
- ✅ Detecção de bordas (*rising/falling*) via `EdgeMonitor`
- ✅ Logging robusto em `src/logs`
- ✅ Editor de descrições integrado
- ✅ Suporte a filtros e ordenação
- ✅ Código modular e bem organizado

---

## 📁 Estrutura do Projeto

```text
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

⚙️ Instalação

Requisitos:

Python 3.8+ (recomendado 3.10+)

Instale as dependências:

pip install -r requirements.txt

🔧 Configuração

O arquivo principal de configuração fica em:

./.cfg/config.json


Ele é criado automaticamente na primeira execução com valores padrão.

Exemplo de estrutura:

{
  "connection": {
    "host": "127.0.0.1",
    "port": 502,
    "timeout": 3
  },
  "modbus_mapping": {
    "digital_inputs": {
      "start_address": 0,
      "count": 16,
      "register_type": "COIL",
      "description": "Entradas digitais (botões/sensores)"
    },
    "digital_outputs": {
      "start_address": 0,
      "count": 16,
      "register_type": "DISCRETE",
      "description": "Saídas digitais (motores/luzes)"
    },
    "analog_inputs": {
      "start_address": 0,
      "count": 8,
      "register_type": "HOLDING",
      "description": "Entradas analógicas"
    },
    "analog_outputs": {
      "start_address": 0,
      "count": 8,
      "register_type": "INPUT_REG",
      "description": "Saídas analógicas"
    }
  },
  "display": {
    "scale_factor": 100,
    "decimal_places": 2,
    "show_inactive_analogs": false
  },
  "files": {
    "descriptions_file": ".cfg/factory_io_descriptions.json",
    "logs_dir": "src/logs"
  }
}


Você pode editar esse arquivo para ajustar:

IP/porta do servidor Modbus (connection.host / connection.port)

quantidade e faixa de endereços (modbus_mapping.*)

escala e casas decimais para valores analógicos (display)

caminhos de logs e descrições (files)

▶️ Como Executar
🔹 Versão principal (modular)

Na raiz do projeto:

python src/main.py

🔹 Versão completa (script único de exemplo)
python scan_complete/factory_io_scanner_complete.py


Durante a execução pela CLI (ui.py), você poderá:

iniciar o escaneamento

navegar pelos I/Os

aplicar filtros

editar descrições e salvar no arquivo configurado

🏗️ Arquitetura dos Módulos
Visão geral

src/main.py
Inicializa a aplicação: carrega configuração, configura logging e chama a interface de usuário (CLI).

src/modules/config.py
Gerencia o arquivo ./.cfg/config.json: criação inicial, leitura, validação e acesso simplificado aos valores.

src/modules/modbus_client.py
Wrapper de comunicação Modbus (ex.: TCP): conexão, leitura de coils, discrete inputs, holding registers e input registers.

src/modules/scanner.py
Lógica principal de escaneamento dos endereços configurados:

leitura Modbus conforme modbus_mapping

montagem das estruturas de dados usadas pela UI

integração com EdgeMonitor para detecção de bordas

src/modules/edge_monitor.py
Componente de detecção de bordas (rising/falling) em sinais digitais:

aceita mapping (start_address + count) ou lista de endereços

mantém estado anterior (old) e compara com o novo (new)

dispara callbacks registrados quando há transição
# 📟 Scanner Modbus (Factory I/O)

Scanner leve e modular para leitura e monitoramento de I/Os via Modbus (por exemplo, integrável ao Factory I/O). Fornece detecção de bordas (rising/falling), logging estruturado, configuração externa e uma interface CLI para inspeção e edição de descrições.

**Visão geral:**
- **Projeto:** Modular Producing System (MPS) — scanner Modbus
- **Linguagem:** Python
- **Compatível:** Python 3.8+ (recomendado 3.10+)

**Principais recursos:**
- **Detecção de bordas:** `src/modules/edge_monitor.py` (rising/falling)
- **Configuração externa:** `./.cfg/config.json`
- **Cliente Modbus:** `src/modules/modbus_client.py` (leitura de coils, discrete inputs, holding/input registers)
- **CLI leve:** `src/services/ui.py` para navegação, filtros e edição de descrições
- **Logs estruturados:** por padrão em `src/logs/`

## Índice
- **Instalação**
- **Execução**
- **Configuração**
- **Estrutura do projeto**
- **Módulos principais**
- **Logs**
- **Testes**
- **Contribuição**
- **Licença & Contato**

## Instalação

Recomendo criar um ambiente virtual e instalar dependências:

PowerShell:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS (bash):
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

- Executar a versão modular (recomendada):
```
python src/main.py
```
- Executar a versão completa de exemplo (monolítica):
```
python scan_complete/factory_io_scanner_complete.py
```

Durante a execução pela CLI você poderá iniciar o escaneamento, navegar pelos I/Os, aplicar filtros e editar descrições que são salvas no arquivo configurado.

## Configuração

O arquivo principal de configuração é `./.cfg/config.json`. Ele é criado automaticamente na primeira execução com valores padrão se não existir.

Exemplo simplificado:
```json
{
  "connection": { "host": "127.0.0.1", "port": 502, "timeout": 3 },
  "modbus_mapping": {
    "digital_inputs": { "start_address": 0, "count": 16, "register_type": "COIL" },
    "digital_outputs": { "start_address": 0, "count": 16, "register_type": "DISCRETE" },
    "analog_inputs": { "start_address": 0, "count": 8, "register_type": "HOLDING" },
    "analog_outputs": { "start_address": 0, "count": 8, "register_type": "INPUT_REG" }
  },
  "display": { "scale_factor": 100, "decimal_places": 2 },
  "files": { "descriptions_file": ".cfg/factory_io_descriptions.json", "logs_dir": "src/logs" }
}
```

Edite `./.cfg/config.json` para ajustar IP/porta, mapeamento Modbus, escala de valores analógicos ou caminhos de logs.

## Estrutura do projeto

- **`src/main.py`**: Inicialização da aplicação, carregamento da configuração e start da UI.
- **`src/modules/config.py`**: Gerenciamento e validação do arquivo de configuração.
- **`src/modules/modbus_client.py`**: Abstração do cliente Modbus (TCP).
- **`src/modules/scanner.py`**: Lógica de leitura e montagem dos snapshots.
- **`src/modules/edge_monitor.py`**: Detecção de transições (bordas) em sinais digitais.
- **`src/services/ui.py`**: Interface CLI para interação com o scanner.
- **`src/services/utils.py`**: Helpers e utilitários.
- **`src/logs/`**: Diretório de logs.
- **`scan_complete/factory_io_scanner_complete.py`**: Exemplo monolítico do scanner.
- **`tests/`**: Testes unitários (ex.: `tests/test_edge.py`).

## Logs

Por padrão os logs são gravados em `src/logs/` ou no caminho configurado em `files.logs_dir` dentro do `config.json`. Em caso de problemas, verifique os arquivos em `src/logs/` (por exemplo `factory_io_scanner.log`).

## Testes

Testes existentes (ex.: detecção de bordas) estão em `tests/test_edge.py`.

Para executar os testes:
```
python -m pytest -q
```

Se necessário, instale o `pytest`:
```
pip install pytest
```

## Contribuição

- Abra uma issue descrevendo o problema ou a feature desejada.
- Para mudanças maiores, crie um branch por feature e envie um Pull Request.
- Adicione/atualize testes para lógica crítica (scanner, modbus, edge detection).

## Licença

Inclua aqui a licença do projeto (por exemplo, MIT). Se ainda não há licença, adicione um arquivo `LICENSE` na raiz.

## Contato

Se quiser ajuda com execução, testes ou integração, abra uma issue ou envie uma mensagem para o mantenedor.

---

Se quiser, posso também:
- rodar os testes agora (`pytest`),
- ou criar um commit com essa atualização do `README.md`.
