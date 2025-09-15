# Enhanced Web Interface Documentation

## Overview

The Muleta Cognitiva web interface has been enhanced with advanced visualizations including argument flowcharts, learning analytics dashboard, and assessment results visualization. The interface now provides a comprehensive learning management system with interactive knowledge graph exploration.

## Features Implemented

### 1. Modern Multi-Tab Interface

**Four Main Sections:**
- **Grafo de Conhecimento**: Interactive knowledge graph visualization
- **Dashboard de Aprendizagem**: Learning analytics and progress tracking
- **Fluxogramas Argumentativos**: Argument sequence flowcharts
- **Avaliações**: Assessment results and knowledge gap analysis

### 2. Enhanced Knowledge Graph Visualization

**Graph Types:**
- **Force-directed**: Traditional force layout with entity relationships
- **Circular**: Circular layout for better pattern recognition
- **Sankey Flow**: Flow diagram showing relationship strengths
- **Fluxograma Argumentativo**: Specialized layout for argument sequences

**Interactive Features:**
- Real-time filtering by entity category
- Entity search and selection
- Zoom and pan controls
- Hover tooltips with detailed information
- Export visualization as PNG

**Analytics Charts:**
- **Review Progress**: Weekly review activity line chart
- **Card Type Distribution**: Pie chart showing card types (Definition, Socratic, Relation, Application)
- Real-time updates from API data

### 4. Argument Flowcharts

**Flowchart Creation:**
- Interactive node placement for argument structures
- Support for different node types:
  - **Premises** (green): Starting assumptions
  - **Inferences** (blue): Logical deductions
  - **Conclusions** (yellow): Final outcomes
  - **Evidence** (red): Supporting facts
  - **Objections** (orange): Counter-arguments
### 7. Submissão de Texto (Processar Texto)

Um novo painel na barra lateral permite enviar texto diretamente do navegador para processamento pelo endpoint `POST /api/content/process`.

Recursos:
- Campo de texto obrigatório (mín. 10, máx. 50.000 caracteres)
- Campo de fonte (opcional), padrão: `browser:manual`
- Botão "Processar Texto" com estado de carregamento e botão "Cancelar" (AbortController)
- Resumo de resultados: `entities_created`, `relations_created`, `observations_created`
- Atualização automática das estatísticas e visualizações via `refreshData()` após sucesso
- Mensagens de erro amigáveis para validação, tempo limite, problemas de rede e erros de aplicação

#### Suporte a diferentes tipos de conteúdo

Além de texto simples, o painel permite o envio dos seguintes tipos de conteúdo para processamento:

- **Imagens**: Faça upload de arquivos de imagem (`.png`, `.jpg`, `.jpeg`). As imagens são processadas para extração de entidades e relações visuais.
- **Vídeos**: Envie vídeos. O sistema extrai transcrições e identifica entidades mencionadas.
- **Arquivos PDF**: Faça upload de documentos PDF. O texto é extraído e processado para análise semântica.
- **Arquivos de texto**: Suporte para arquivos `.txt`.

Cada tipo de conteúdo apresenta um campo de upload dedicado, com validação de tamanho e formato. Após o processamento, os resultados são exibidos em um painel de resumo, incluindo visualizações específicas para cada tipo (exemplo: visualização de entidades extraídas de imagens ou transcrições de vídeo).

### Data Flow

1. **Initialization**: Load entities, statistics, and visualization data
2. **User Interaction**: Filter, select, and navigate through data
3. **Real-time Updates**: Refresh data on user actions
4. **State Management**: Maintain selection and view state
