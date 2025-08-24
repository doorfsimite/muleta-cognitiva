# Módulos do Sistema

## Índice
- [Core Modules](#core-modules)
- [Processing Modules](#processing-modules)
- [API Modules](#api-modules)
- [Learning Modules](#learning-modules)
- [Visualization Modules](#visualization-modules)
- [Integration Modules](#integration-modules)

## Core Modules

### MCP Server (`src/api/mcp_server.py`)
**Purpose**: Servidor principal MCP para integração com LLMs e GitHub Copilot
**Key Interfaces**:
- `MCPServer` - Classe principal do servidor
- `handle_call()` - Processamento de chamadas MCP
- `get_tools()` - Lista de ferramentas disponíveis

**Dependencies**: SQLite database, Content processors
**Simplified Flow**: 
1. Recebe chamada MCP
2. Valida parâmetros
3. Executa ferramenta apropriada
4. Retorna resultado estruturado

**Example Usage**:
```python
server = MCPServer(database_path="knowledge.db")
result = server.handle_call("process_content", {"text": "...", "source": "manual"})
```

**LLM Cues**: Ponto central para adicionar novas ferramentas MCP; todas as operações devem passar por aqui para manter contexto

---

### Database Manager (`src/api/database.py`)
**Purpose**: Gerenciamento centralizado da base de dados SQLite
**Key Interfaces**:
- `DatabaseManager` - Classe principal de gerenciamento
- `create_tables()` - Inicialização do schema
- `get_entities()`, `get_relations()` - Queries principais
- `migrate_from_memory()` - Migração de dados legacy

**Dependencies**: SQLite3
**Simplified Flow**:
1. Inicializa conexão SQLite
2. Valida/cria schema
3. Executa operações CRUD
4. Mantém índices para performance

**Example Usage**:
```python
db = DatabaseManager("knowledge.db")
entities = db.get_entities(entity_type="concept")
db.add_relation(from_id=1, to_id=2, relation_type="supports")
```

**LLM Cues**: Todas as operações de dados devem usar este módulo; adicione índices para queries frequentes; schema migrations vão aqui

---

### Content Processor (`src/api/content_processor.py`)
**Purpose**: Processamento de conteúdo via LLM para extração de entidades
**Key Interfaces**:
- `ContentProcessor` - Classe principal
- `process_text()` - Extração de entidades e relações
- `extract_entities()` - Identificação de conceitos
- `extract_relations()` - Mapeamento de conexões

**Dependencies**: LLM APIs, Database Manager
**Simplified Flow**:
1. Recebe texto bruto
2. Envia para LLM com prompt estruturado
3. Processa resposta JSON
4. Persiste entidades e relações

**Example Usage**:
```python
processor = ContentProcessor(llm_client=openai_client)
result = processor.process_text("Texto sobre filosofia...", source_path="aula1.txt")
```

**LLM Cues**: Central para qualidade dos dados; ajuste prompts aqui; valide sempre output do LLM antes de persistir

## Processing Modules

### Video to Text (`video_to_text.sh`)
**Purpose**: Extração OCR automatizada de vídeos
**Key Functions**:
- Frame extraction com detecção de cena
- Preprocessamento de imagem para OCR
- OCR com Tesseract multi-idioma
- Agregação e limpeza de texto

**Dependencies**: FFmpeg, ImageMagick, Tesseract
**Simplified Flow**:
1. Extrai frames baseado em mudanças de cena
2. Preprocessa imagens (contraste, nitidez)
3. Executa OCR em paralelo
4. Agrega texto e gera arquivo final

**Example Usage**:
```bash
bash video_to_text.sh -i lecture.mp4 -l por+eng -p
```

**LLM Cues**: Script standalone; modifique parâmetros OCR baseado no tipo de conteúdo; adicione validação de qualidade

---

### Text Cleaner (`src/api/text_cleaner.py`)
**Purpose**: Limpeza e normalização de texto OCR
**Key Functions**:
- `clean_ocr_text()` - Correção de artefatos OCR
- `normalize_spacing()` - Normalização de espaçamento
- `fix_line_breaks()` - Correção de quebras de linha

**Dependencies**: re, unicodedata
**Simplified Flow**:
1. Remove artefatos de OCR
2. Corrige espaçamento
3. Normaliza quebras de linha
4. Remove caracteres especiais

**Example Usage**:
```python
cleaner = TextCleaner()
clean_text = cleaner.clean_ocr_text(raw_ocr_output)
```

**LLM Cues**: Ajuste regexes baseado na qualidade do OCR; preserve formatação importante como listas

## API Modules

### FastAPI Server (`src/api/api.py`)
**Purpose**: API REST para interface web e integrações
**Key Endpoints**:
- `GET /api/entities` - Lista entidades
- `GET /api/visualization` - Dados para grafo
- `POST /api/content/process` - Processamento de conteúdo
- `GET /api/cards/due` - Cards para revisão

**Dependencies**: FastAPI, Database Manager
**Simplified Flow**:
1. Recebe requisição HTTP
2. Valida parâmetros
3. Chama módulo apropriado
4. Retorna JSON estruturado

**Example Usage**:
```python
app = FastAPI()
@app.get("/api/entities")
def get_entities():
    return db.get_entities()
```

**LLM Cues**: Mantenha endpoints RESTful; adicione validação Pydantic; use dependency injection para database

---

### Response Models (`src/api/models.py`)
**Purpose**: Modelos Pydantic para validação de API
**Key Classes**:
- `Entity` - Modelo de entidade
- `Relation` - Modelo de relação
- `VisualizationData` - Dados para ECharts
- `ProcessingRequest` - Request de processamento

**Dependencies**: Pydantic
**Example Usage**:
```python
class Entity(BaseModel):
    id: int
    name: str
    entity_type: str
    description: Optional[str]
```

**LLM Cues**: Use para validação automática; mantenha consistência com schema do banco; adicione validators customizados

## Learning Modules

### Spaced Repetition (`src/api/spaced_repetition.py`)
**Purpose**: Sistema de revisão espaçada com algoritmo SM-2
**Key Classes**:
- `SpacedRepetitionManager` - Gerenciador principal
- `Card` - Modelo de card
- `ReviewSession` - Sessão de revisão

**Dependencies**: Database Manager, datetime
**Simplified Flow**:
1. Calcula cards devido
2. Apresenta para revisão
3. Processa resposta do usuário
4. Ajusta próximo intervalo

**Example Usage**:
```python
srm = SpacedRepetitionManager(db)
due_cards = srm.get_due_cards()
srm.review_card(card_id=1, quality=4)
```

**LLM Cues**: Algoritmo sensível; não modifique constantes sem testes; adicione logs para debugging

---

### Card Generator (`src/api/card_generator.py`)
**Purpose**: Geração automática de cards de diferentes tipos
**Key Functions**:
- `generate_definition_card()` - Cards de definição
- `generate_relation_card()` - Cards de relação
- `generate_socratic_card()` - Questões socráticas

**Dependencies**: LLM APIs, Database Manager
**Example Usage**:
```python
generator = CardGenerator(llm_client)
card = generator.generate_socratic_card(entity_id=1, question_type="why_important")
```

**LLM Cues**: Prompts são críticos para qualidade; teste com diferentes tipos de entidade; valide output

---

### Socratic Questions (`src/api/socratic_questions.py`)
**Purpose**: Geração de questões socráticas contextualizadas
**Key Functions**:
- `generate_why_important()` - "Por que X é importante?"
- `generate_evidence_questions()` - "Que evidências sustentam X?"
- `generate_implications()` - "Quais as implicações de X?"

**Dependencies**: LLM APIs, Knowledge Graph
**Example Usage**:
```python
sq = SocraticQuestions(llm_client)
questions = sq.generate_for_entity(entity_id=1, types=["why_important", "evidence"])
```

**LLM Cues**: Baseie questões nas relações do grafo; diferentes templates por tipo de entidade

## Visualization Modules

### Web Interface (`index.html`)
**Purpose**: Interface web para visualização e interação
**Key Components**:
- ECharts integration
- Graph type switching
- Interactive controls
- Real-time updates

**Dependencies**: ECharts, modern browser
**Example Usage**:
```javascript
const chart = echarts.init(document.getElementById('chart'));
chart.setOption(graphOption);
```

**LLM Cues**: Mantenha compatibilidade com ECharts versão atual; adicione progressive loading para grafos grandes

---

### Visualization API (`src/api/visualization.py`)
**Purpose**: Preparação de dados para visualização ECharts
**Key Functions**:
- `format_for_echarts()` - Conversão para formato ECharts
- `generate_categories()` - Categorias para coloração
- `calculate_layout()` - Posicionamento de nós

**Dependencies**: Database Manager
**Example Usage**:
```python
viz = VisualizationAPI(db)
chart_data = viz.format_for_echarts(graph_type="force")
```

**LLM Cues**: Otimize para grandes grafos; cache dados quando possível; mantenha consistência visual

## Integration Modules

### Anki Exporter (`src/api/anki_exporter.py`)
**Purpose**: Export de cards para formato Anki
**Key Functions**:
- `export_to_apkg()` - Geração de arquivo .apkg
- `format_card_html()` - Formatação HTML dos cards
- `create_deck_config()` - Configuração do deck

**Dependencies**: genanki, Database Manager
**Example Usage**:
```python
exporter = AnkiExporter(db)
exporter.export_to_apkg(entity_ids=[1,2,3], output_path="deck.apkg")
```

**LLM Cues**: Mantenha compatibilidade com formato Anki; teste importação após export

---

### Assessment Creator (`src/api/assessment_creator.py`)
**Purpose**: Geração de avaliações abrangentes
**Key Functions**:
- `create_assessment()` - Criação de prova completa
- `generate_multiple_choice()` - Questões múltipla escolha
- `generate_essay_questions()` - Questões dissertativas

**Dependencies**: LLM APIs, Database Manager
**Example Usage**:
```python
creator = AssessmentCreator(llm_client)
assessment = creator.create_assessment(entity_ids=[1,2,3], difficulty=3)
```

**LLM Cues**: Balanceie tipos de questão; crie distractors inteligentes; valide qualidade das questões

---

### Knowledge Analyzer (`src/api/knowledge_analyzer.py`)
**Purpose**: Análise de gaps e padrões de conhecimento
**Key Functions**:
- `identify_gaps()` - Identificação de lacunas
- `analyze_performance()` - Análise de performance
- `suggest_study_plan()` - Sugestões de estudo

**Dependencies**: Database Manager, Statistics
**Example Usage**:
```python
analyzer = KnowledgeAnalyzer(db)
gaps = analyzer.identify_gaps(user_performance_data)
```

**LLM Cues**: Use métricas estatísticas sólidas; correlacione performance entre diferentes tipos de card

## Extension Points

### Adicionando Novos Tipos de Card
1. Estenda `CardGenerator` com novo método
2. Adicione tipo no enum `CardType`
3. Atualize templates de review
4. Adicione testes específicos

### Adicionando Novos Processadores de Conteúdo
1. Implemente interface `ContentProcessor`
2. Registre no `MCP Server`
3. Adicione validação de formato
4. Documente limitações

### Adicionando Novas Visualizações
1. Estenda `VisualizationAPI`
2. Adicione opção no frontend
3. Configure ECharts options
4. Teste com dados reais

**Owners**: Módulos core mantidos pelo desenvolvedor principal; extensões podem ser contribuições da comunidade