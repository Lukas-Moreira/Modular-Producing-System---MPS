# MPS Festo Dashboard - Frontend

Dashboard web em React + TypeScript para monitoramento e controle do sistema de automação industrial MPS Festo Didactic Plant.

## Tecnologias

- React 18.x com TypeScript
- React Router para navegação
- Axios para requisições HTTP
- React Toastify para notificações
- CSS3 para estilização

## Pré-requisitos

- Node.js (versão 14.x ou superior)
- npm (gerenciador de pacotes)

Verificar instalação:
```bash
node --version
npm --version
```

Download: https://nodejs.org/

## Instalação

Acesse a pasta do frontend:
```bash
cd frontend/mps-dashboard-ts
```

Instale as dependências:
```bash
npm install
```

## Executando o projeto

### Modo desenvolvimento (local)
```bash
npm start
```

Acesso: http://localhost:3000

### Build para produção
```bash
npm run build
```

Gera versão otimizada na pasta `build/`.

## Acessando de outros dispositivos na rede

### Descobrir IP local

**Windows:**
```bash
ipconfig
```

**Linux/Mac:**
```bash
ifconfig
```
ou
```bash
ip addr show
```

### Iniciar servidor com acesso externo

**Windows:**
```bash
set HOST=0.0.0.0 && npm start
```

**Linux/Mac:**
```bash
HOST=0.0.0.0 npm start
```

Outros dispositivos acessam via: `http://SEU_IP:3000`

### Configuração permanente

Crie arquivo `.env` na raiz do projeto:
```env
HOST=0.0.0.0
PORT=3000
```

## Configuração da API

O dashboard conecta em `http://localhost:8000` por padrão.

Para alterar, edite as URLs nos arquivos:
- `src/pages/Orders.tsx`
- `src/pages/Dashboard.tsx`
- `src/components/LoginModal.tsx`

## Funcionalidades

- Dashboard em tempo real com monitoramento de sensores
- Gerenciamento de ordens de produção
- Estatísticas e gráficos de produção
- Sistema de autenticação com JWT
- Histórico de peças processadas

## Credenciais padrão

Conforme cadastrado na tabela `users` do banco de dados:

- Usuário: admin
- Senha: admin123

## Scripts disponíveis

| Comando | Descrição |
|---------|-----------|
| `npm start` | Inicia servidor de desenvolvimento |
| `npm run build` | Cria build de produção |
| `npm test` | Executa testes |

## Estrutura do projeto
```
mps-dashboard-ts/
├── public/              # Arquivos estáticos
├── src/
│   ├── components/      # Componentes reutilizáveis
│   ├── pages/          # Páginas da aplicação
│   ├── utils/          # Funções auxiliares
│   ├── App.tsx         # Componente raiz
│   └── index.tsx       # Entry point
├── package.json        # Dependências e scripts
└── tsconfig.json       # Configuração TypeScript
```

## Troubleshooting

### Porta 3000 em uso

**Windows:**
```bash
netstat -ano | findstr :3000
taskkill /PID <numero_processo> /F
```

**Linux/Mac:**
```bash
lsof -ti:3000 | xargs kill -9
```

Ou altere a porta no `.env`:
```env
PORT=3001
```

### Erro de CORS

Verifique configuração no backend FastAPI:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API não responde

1. Verifique se backend está em `http://localhost:8000`
2. Teste API: `http://localhost:8000/docs`
3. Verifique console do navegador (F12)