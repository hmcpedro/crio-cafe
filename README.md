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
- Certifique-se de que todas as bibliotecas em requirements.txt estejam instaladas
- Suba o conteiner
```bash
docker compose up -d
```
- Inicialize o serviço
```bash
uvicorn main:app --reload
``
- Aesse: http://127.0.0.1:8000/login
- Credenciais de Admin:
```bash
email:admin@admin.com
senha:admin
```