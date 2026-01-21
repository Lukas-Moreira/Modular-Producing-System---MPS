# UR5 Robot Programs - MPS Festo Integration

Programas extraídos do robô colaborativo Universal Robots UR5 para integração com o sistema MPS Festo Didactic Plant.

## Arquivos do Programa

- `TesteUFAM.urp` - Arquivo de programa principal do UR5
- `TesteUFAM.script` - Script URScript compilado
- `TesteUFAM.txt` - Documentação legível do fluxo do programa
- `default.installation` - Configurações de instalação do robô
- `default.variables` - Variáveis globais do sistema

## Estrutura do Programa

### Programa Principal

Loop contínuo que monitora sinais digitais de entrada e executa subprogramas conforme a configuração:

- **Condição 1:** `DO[0]=True AND DO[1]=False AND DO[2]=True` → Executa Subprograma_1 - PEÇA PRATA
- **Condição 2:** `DO[0]=True AND DO[1]=True AND DO[2]=False` → Executa Subprograma_2 - PEÇA ROSA
- **Condição 3:** `DO[0]=True AND DO[1]=True AND DO[2]=True` → Executa Subprograma_3 -PEÇA PRETO

Após cada subprograma, executa Subprograma_4 para reset de sinais.

### Subprogramas

#### Subprograma_1
Sequência de pick and place para posição 1:
1. Move para home
2. Move para Pick_Standby → Get_Piece (pega peça) → Pick_Standby
3. Retorna para home
4. Move para Place_Sub1 → desce_1 (coloca peça) → Place_Sub1
5. Retorna para home
6. Ativa DO[5]

#### Subprograma_2
Sequência de pick and place para posição 2:
1. Move para home
2. Move para Pick_Standby → Get_Piece (pega peça) → Pick_Standby
3. Retorna para home
4. Move para Place_Sub2 → desce2 (coloca peça) → Place_Sub2
5. Retorna para home
6. Ativa DO[5]

#### Subprograma_3
Sequência de pick and place para posição 3:
1. Move para home
2. Move para Pick_Standby → Get_Piece (pega peça) → Pick_Standby
3. Retorna para home
4. Move para Place_Sub3 → desce_3 (coloca peça) → Place_Sub3
5. Retorna para home
6. Ativa DO[5]

#### Subprograma_4
Reset de sinais digitais:
1. Aguarda 1s
2. Desliga DO[5]
3. Aguarda 1s
4. Desliga DO[0]
5. Aguarda 1s
6. Desliga DO[1]
7. Aguarda 1s
8. Desliga DO[2]

## Mapeamento de I/O

### Saídas Digitais (Digital Outputs)

| Pino | Função | Descrição |
|------|--------|-----------|
| DO[0] | Seletor de cor/posição (bit 0) | Parte do código binário para seleção |
| DO[1] | Seletor de cor/posição (bit 1) | Parte do código binário para seleção |
| DO[2] | Seletor de cor/posição (bit 2) | Parte do código binário para seleção |
| DO[5] | Confirmação de operação | Sinal de conclusão de tarefa |

### Combinações de Seleção

| DO[0] | DO[1] | DO[2] | Ação |
|-------|-------|-------|------|
| 1 | 0 | 1 | Place posição 1 |
| 1 | 1 | 0 | Place posição 2 |
| 1 | 1 | 1 | Place posição 3 |

## Waypoints Configurados

- `home` - Posição inicial/segura do robô
- `Pick_Standby` - Posição de aproximação para pegar peça
- `Get_Piece` - Posição exata para pegar peça
- `Place_Sub1` - Posição de aproximação para colocar peça 1
- `desce_1` - Posição exata para colocar peça 1
- `Place_Sub2` - Posição de aproximação para colocar peça 2
- `desce2` - Posição exata para colocar peça 2
- `Place_Sub3` - Posição de aproximação para colocar peça 3
- `desce_3` - Posição exata para colocar peça 3

## Carregando o Programa no UR5

### Via Pendant (Teach Pendant)

1. Conecte USB com os arquivos no pendant
2. Acesse: `Program` → `Load Program`
3. Navegue até a pasta com `TesteUFAM.urp`
4. Selecione o arquivo e carregue

### Via Interface Web (UR Polyscope)

1. Acesse a interface web do robô: `http://IP_DO_ROBO`
2. Vá em `Program` → `Load`
3. Faça upload do arquivo `TesteUFAM.urp`

### Via FTP/SFTP

1. Conecte via FTP ao robô
2. Navegue até `/programs/`
3. Faça upload de todos os arquivos `.urp`, `.script`, `.installation`, `.variables`

## Configuração de Rede

### Padrão de Fábrica
- IP: 192.168.1.102
- Subnet: 255.255.255.0
- Gateway: 192.168.1.1

### Alterar IP do Robô

1. No pendant: `Setup` → `Network`
2. Configure IP, máscara e gateway
3. Reinicie o robô

## Integração com Sistema MPS

O robô deve estar conectado à rede de controle do sistema MPS Festo:

1. Configure o IP do robô na mesma rede dos PLCs
2. Os sinais digitais DO[0], DO[1], DO[2] devem ser conectados ao sistema de controle
3. O sinal DO[5] indica conclusão de operação para o MES coordinator

## Segurança

### Antes de Executar

- Verifique área de trabalho livre de obstáculos
- Confirme posições de todos os waypoints
- Teste em modo baixa velocidade primeiro
- Mantenha botão de emergência acessível

### Limites de Segurança

Configure no pendant:
- `Setup` → `Safety` → `Boundaries`
- Defina planos de segurança conforme workspace
- Configure força e velocidade máximas

## Backup do Programa

### Criar Backup

1. No pendant: `Program` → `Save Program As`
2. Salve com nome descritivo + data
3. Copie para USB ou via rede

### Restaurar Backup

1. Carregue o arquivo `.urp` conforme instruções acima
2. Verifique configurações de instalação
3. Teste waypoints antes de executar

## Troubleshooting

### Robô não responde a sinais digitais

- Verifique conexões físicas dos cabos de I/O
- Confirme mapeamento no `Setup` → `I/O`
- Teste sinais manualmente no pendant

### Waypoints desconfigurados

- Recarregue `default.installation`
- Reconfigure posições manualmente
- Salve novo programa

### Erro de comunicação de rede

- Verifique cabo Ethernet conectado
- Confirme IP do robô com `ping`
- Reinicie controlador do robô

## Especificações do UR5

- Payload: 5 kg
- Alcance: 850 mm
- Repetibilidade: ±0.1 mm
- Graus de liberdade: 6
- Velocidade máxima: 1 m/s

## Manutenção

### Diária
- Inspeção visual de cabos e conexões
- Verificação de ruídos anormais
- Teste de botão de emergência

### Mensal
- Limpeza de superfícies
- Verificação de torques das juntas
- Backup de programas

### Anual
- Calibração de TCP (Tool Center Point)
- Verificação de precisão
- Atualização de firmware