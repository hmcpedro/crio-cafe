# Aromap - Crio Cafe

## Sobre o projeto
O **Aromap** e um sistema desenvolvido para a **Crio Cafe** com o objetivo de equilibrar o fluxo diario de clientes nas unidades da cafeteria. A proposta utiliza **geolocalizacao**, **notificacoes automaticas** e **campanhas promocionais programaveis** para atrair consumidores proximos da loja em momentos estrategicos.

## Objetivo
O projeto busca melhorar a distribuicao do movimento ao longo do dia, aumentando a efetividade das campanhas e apoiando a tomada de decisao com base no comportamento e na interacao dos clientes.

## Escopo principal
O sistema contempla:
- identificacao de clientes proximos as unidades;
- envio automatico de notificacoes;
- cadastro e programacao de campanhas promocionais;
- monitoramento de movimentacao e interacoes dos clientes;
- geracao de relatorios sobre retorno e efetividade das campanhas.

O projeto **nao inclui** funcionalidades de vendas, controle de estoque, delivery ou alteracoes na infraestrutura fisica das lojas.

## Proposta de valor
Com essa solucao, a Crio Cafe pode tornar suas acoes promocionais mais inteligentes, direcionadas e mensuraveis, melhorando a experiencia do cliente e o aproveitamento do fluxo nas lojas.

## Instruções de Uso

### 1. Subir os serviços

```bash
docker compose up -d
```

Isso sobe três containers:
- `aromap-postgres` — banco de dados
- `aromap-backend` — API FastAPI na porta 8000
- `aromap-evolution` — Evolution API (gateway WhatsApp) na porta 8080

### 2. Acessar o sistema

Acesse: http://127.0.0.1:8000/login

Credenciais de admin:
```
email: admin@admin.com
senha: admin
```

### 3. Configurar o WhatsApp (apenas na primeira vez)

O módulo de notificações usa a **Evolution API** para enviar mensagens via WhatsApp. É necessário vincular um número uma única vez.

**a) Acesse o manager da Evolution API:**
```
http://localhost:8080/manager
```
A senha de acesso é o valor de `EVOLUTION_API_KEY` definido no `.env` (padrão: `aromap-evolution-key-2025`).

**b) Se a instância `aromap` ainda não existir, crie via terminal:**
```bash
source venv/bin/activate
python notificador.py --criar-instancia
```

**c) Gere o QR Code:**
```bash
python notificador.py --qr
```

No manager, clique na instância `aromap` — o QR Code aparecerá na tela. Escaneie com o WhatsApp do celular em:
`WhatsApp > ... > Dispositivos vinculados > Vincular dispositivo`

> O QR Code expira em ~20 segundos. Tenha a câmera pronta antes de abrir a página.

**d) Verifique se conectou:**
```bash
python notificador.py --status
```
Deve exibir `state='open'`.

A sessão fica salva no volume Docker `evolution_data`. Não é necessário repetir esse processo após reiniciar — só se o WhatsApp desconectar.

### 4. Rodar o notificador

O `notificador.py` é um processo separado que fica observando o banco a cada 10 segundos. Quando uma campanha é marcada para disparo, ele envia as mensagens para todos os clientes ativos.

```bash
source venv/bin/activate
python notificador.py
```

Deixe esse terminal aberto enquanto quiser que as notificações funcionem. Os logs também são gravados em `notificador.log`.

### 5. Criar e disparar campanhas

1. Acesse http://localhost:8000/admin/campanhas
2. Crie uma campanha — escolha o tipo de notificação:
   - **Imediata** — enfileira o disparo assim que salvar
   - **Agendada** — dispara na data/hora escolhida
   - **Manual** — dispara ao clicar no botão na página de detalhe
3. Para campanhas manuais: acesse o detalhe da campanha e clique em **"Enviar notificação"**
4. O `notificador.py` detecta em até 10 segundos e envia para toda a base de clientes ativos

### Observações

- Os clientes precisam ter número de telefone cadastrado no sistema
- O número pode estar salvo com ou sem o código do país (`11999999999` ou `5511999999999`)
- Se o envio de imagem falhar, o sistema faz fallback automático e envia só o texto
- Para reinstalar dependências locais: `pip install requests sqlalchemy psycopg[binary] python-dotenv`