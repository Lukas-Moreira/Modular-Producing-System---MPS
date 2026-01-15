# Sistema MPS Festo - Documentação

## Visão Geral

Sistema de monitoramento e controle para linha de produção modular MPS Festo com 3 PLCs:
- MPS_HANDLING: Manipulação de peças com garra pneumática
- MPS_PRESSING: Esteira transportadora e sensores
- MPS_SORTING: Classificação final

## Arquitetura

### Backend (Python)
- FastAPI para API REST
- PyModbus para comunicação Modbus TCP
- SQL Server para banco de dados
- Threads para controle concorrente dos PLCs

### Frontend (React TypeScript)
- Dashboard de monitoramento em tempo real
- Gerenciamento de ordens de produção
- Visualização de estatísticas

### Banco de Dados
Duas tabelas principais:
- production_orders: Ordens de produção
- pieces: Peças produzidas com resultado (aprovada/rejeitada)

## Fluxo de Produção

### 1. Detecção Inicial (PLC 1 - Handling)
- Magazine ejeta peça para suporte
- Garra move para posição de coleta
- Garra fecha e verifica cor com sensor_peca_garra:
  - sensor_peca_garra = 0: Peça PRETA
  - sensor_peca_garra = 1: Peça PRATA ou ROSA (indefinido)
- Garra transporta peça para esteira

### 2. Identificação de Cor (PLC 2 - Pressing)
- Peça entra na esteira
- Esteira para na barreira indutiva
- Sensor indutivo identifica metal:
  - MB_SENSOR_IND = 1: Peça PRATA
  - MB_SENSOR_IND = 0: Peça ROSA
- Esteira continua até o final

### 3. Registro no Banco
- Ao finalizar, API recebe cor da peça
- Compara com cor solicitada na ordem
- Registra como aprovada (cores iguais) ou rejeitada (cores diferentes)
- Atualiza progresso da ordem

## SystemState (Singleton)

Gerencia estado global do sistema:

### Atributos
- state_machine: Estado atual (idle, running, stopped, cycle)
- parts_queue: Fila de peças em produção
- current_order: Ordem sendo executada

### Métodos Principais
- set_state_machine(state): Altera estado da máquina
- add_part_to_queue(color): Adiciona peça detectada
- update_last_part_in_queue(color): Atualiza cor após sensor indutivo
- set_current_order(): Define ordem em execução

## Estados da Máquina

- idle: Pronta para iniciar (LED verde + amarelo piscando)
- running: Em operação (LED verde)
- stopped: Parada por botão STOP (LED vermelho)
- cycle: Teste de LEDs (vermelho -> amarelo -> verde)

## Botões de Controle

### START
- Condição: state_machine = idle
- Ação: Inicia produção (state_machine = running)

### STOP
- Condição: Qualquer estado
- Ação: Para todas operações, zera registradores dos PLCs

### RESET
- Condição: state_machine = stopped ou cycle
- Ação: Sobe garra, recua magazine, move para home (state_machine = idle)

## API Endpoints

### GET /api/machine-status
Retorna estado da máquina e sensores

### GET /api/current-order
Retorna ordem em execução

### GET /api/parts-queue
Retorna fila de peças aguardando processamento

### POST /api/part-finished
Parâmetro: color (string)
Registra peça finalizada, remove da fila, salva no banco

### GET /api/production-stats
Estatísticas do dia: total, aprovadas, rejeitadas

### GET /api/hourly-production
Produção por hora do dia

### GET /api/recent-orders
Últimas 10 ordens criadas

### POST /api/create-order
Body: {orderName, color, quantity}
Cria nova ordem de produção

## Estrutura de Arquivos

```
├── Client/
│   └── MES.py              # Lógica de controle dos PLCs
├── Maps/
│   └── Mapping.py          # Mapeamento de registradores Modbus
├── SystemState.py          # Singleton de estado global
├── api.py                  # API REST FastAPI
├── main.py                 # Ponto de entrada, inicia threads
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── Sidebar.tsx
    │   ├── pages/
    │   │   ├── Dashboard.tsx
    │   │   └── Orders.tsx
    │   └── App.tsx
    └── public/
```

## Como Executar

### Backend
```bash
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Acessos
- API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Banco de Dados

### Tabela: production_orders
- id
- order_name
- quantity_requested
- quantity_processed
- color_requested
- created_at
- updated_at
- finished_at

### Tabela: pieces
- id
- order_id (FK)
- piece_color
- result (1=aprovada, 0=rejeitada)
- created_at

## Cores Suportadas
- prata: Tampa metálica prateada
- preto: Tampa plástica preta
- rosa: Tampa plástica rosa

## Checagens de Parada

Todas as funções de movimento checam state_machine != running e param imediatamente se detectarem mudança de estado.