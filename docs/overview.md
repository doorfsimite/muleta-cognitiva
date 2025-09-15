## Visão Geral

O Muleta Cognitiva é um sistema open-source de aprendizado pessoal que utiliza grafos de conhecimento para mapear, organizar e otimizar a retenção de informações extraídas de diferentes fontes (vídeos, textos, PDFs). O sistema funciona como uma fonte de dados rica que alimenta plataformas externas especializadas, enquanto oferece análise local via MCP (Model Context Protocol) server.
# Sistema — Resumo e Estado Atual

## Features Principais

### 1. Extração e Processamento de Conteúdo

**Video-to-Text OCR**
- Extração automática de frames de vídeos
- OCR com Tesseract (português + inglês)
- Detecção de cenas para otimizar extração
- Saída estruturada em diretórios organizados

**Image-to-Text OCR em Lote** 
- Conversão automática de múltiplas imagens para texto
- Suporte a formatos PNG, JPG
- OCR com Tesseract (português + inglês)
- Processamento paralelo para alta performance
- Saída estruturada por imagem em diretórios organizados

**Processamento via LLM**
- Identificação automática de entidades e conceitos
- Extração de relações semânticas entre conceitos
- Geração de observações estruturadas
- Classificação automática por tipo/categoria

### 2. Grafo de Conhecimento

**Estrutura de Dados** (memory)
- Entidades: conceitos, pessoas, teorias, métodos
- Relações: conexões semânticas tipificadas
- Observações: notas detalhadas por entidade
- Metadados: fontes, timestamps, confiabilidade
- Arquivos: informações detalhadas sobre o tema

**Visualização Interativa** ([index.html](../index.html))
- Grafo de força com ECharts
- Layout circular para visão estrutural
- Diagramas Sankey para fluxo de relações
- Tooltips com observações completas
- Filtros por categoria e tipo de relação

### 3. Sistema de Revisão Espaçada Automatizada

**Integração com Anki**
- Geração automática de flashcards baseada em entidades
- Algoritmo de Ebbinghaus para intervalos de revisão
- Sincronização via API ou export/import
- Métricas de performance e dificuldade

**Cards Inteligentes**
- Perguntas geradas via LLM baseadas no contexto
- Diferentes tipos: definição, relação, aplicação
- Questões socráticas integradas

### 4. Gerador de Questões Socráticas

**Templates Inteligentes**
- "Por que X é importante para Y?"
- "Que evidências sustentam a ideia de X?"
- "Como X se relaciona com Y e Z?"
- "Quais as implicações práticas de X?"
- "Que objeções alguém poderia fazer contra X?"

**Contextualização**
- Questões baseadas nas relações do grafo
- Diferentes níveis de profundidade
- Integração com sistema de revisão
- Tracking de progresso no entendimento

### 5. Sequências Lógicas Argumentativas

**Análise de Argumentação**
- Identificação de premissas, inferências e conclusões
- Mapeamento de conectores lógicos
- Geração de diagramas ECharts para fluxos argumentativos
- Detecção de falácias e gaps lógicos

### 7. Avaliação de aprendizado

**Provas Customizadas**
- Questões baseadas em entidades selecionadas 
- Múltipla escolha, dissertativas, verdadeiro/falso
- Avaliação automática via LLM
- Feedback detalhado sobre lacunas de conhecimento
- Formatação simples de ser preenchida e avaliada ao ser retornada para a LLM

## Integrações com Sistemas Terceiros

### Anki - Revisão Espaçada
- **Export automático**: Cards em formato .apkg
- **API Integration**: Sync bidirecional via AnkiConnect
- **Métricas**: Import de estatísticas de performance
- **Customização**: Templates baseados no tipo de entidade

## Arquitetura Técnica

### LLM Local

**Responsabilidades**
- Processamento de novos conteúdos via LLM
- Análise e extração de entidades/relações
- Geração de cards e questões

### Base de Dados SQLite

**Tabelas Principais**
- `entities`: conceitos e suas classificações
- `relations`: conexões tipificadas entre entidades
- `observations`: notas detalhadas por entidade
- `argument_sequences`: fluxogramas argumentativos

## Workflow Típico de Uso

### 1. Ingestão de Conteúdo
1. Usuário envia um conteúdo via UI podendo ser text, video, imagens, ou arquivos de texto como pdf
2. API extrai o texto 
3. Sistema identifica entidades e relações automaticamente  via LLM
4. Dados são persistidos no SQLite com metadados
5. Visualização web é atualizada automaticamente

### 2. Análise e Insights
1. Visualização do grafo revela padrões e conexões
2. Relatórios mostram evolução temporal do conhecimento
3. Sequências argumentativas são mapeadas visualmente
4. Resumos progressivos são atualizados incrementalmente

### 3. Avaliação de aprendizado
1. Usuário seleciona tópicos para avaliação
2. Sistema faz perguntas sobre o tema customizada via LLM para entender o que o usuário aprendeu
3. Verifica se existem informações inválidas, lacunas de conhecimento e outras métricas de qualidade da responsta
4. Respostas são avaliadas automaticamente
5. A LLM ensina o conteúdo que identificou estar errado ou faltando. Auxiliando na compreensão do conteúdo.
