# Guia de Troubleshooting

## GitHub Copilot CLI

### Problema: CLI não funciona ou retorna erros de autenticação

**Diagnóstico**:
```bash
# Verificar status da autenticação
gh auth status

# Verificar se Copilot está instalado
gh extension list | grep copilot

# Verificar status do Copilot
gh copilot status
```

**Soluções**:

1. **Re-autenticar com GitHub**:
```bash
gh auth logout
gh auth login
```

2. **Instalar/atualizar extensão Copilot**:
```bash
gh extension install github/gh-copilot
# ou se já instalado:
gh extension upgrade gh-copilot
```

3. **Verificar permissões Copilot**:
```bash
gh copilot auth
```

4. **Reinstalar GitHub CLI** (se necessário):
```bash
# macOS
brew uninstall gh
brew install gh

# Linux
# Seguir instruções oficiais do GitHub CLI
```

### Problema: Copilot CLI instalado mas comandos não respondem

**Possíveis causas**:
- Token expirado
- Copilot não habilitado na conta
- Problemas de rede

**Soluções**:
```bash
# Verificar conectividade
gh api user

# Verificar subscription Copilot
gh copilot status

# Limpar cache e re-autenticar
rm -rf ~/.config/gh
gh auth login
gh copilot auth
```

## Video to Text Script

### Problema: Nenhum quadro extraído do vídeo

**Diagnóstico**:
```bash
# Verificar se o vídeo é válido
ffprobe -v quiet -show_format -show_streams video.mp4

# Testar extração manual
ffmpeg -i video.mp4 -vf "select=gt(scene\,0.3)" -frames:v 10 test_%03d.jpg
```

**Soluções**:
1. **Ajustar threshold de detecção de cena**:
```bash
bash video_to_text.sh -i video.mp4 -t 0.1  # mais sensível
bash video_to_text.sh -i video.mp4 -t 0.5  # menos sensível
```

2. **Usar extração por tempo fixo**:
```bash
bash video_to_text.sh -i video.mp4 -f 1  # 1 frame por segundo
```

3. **Verificar dependências**:
```bash
# Verificar se FFmpeg está instalado
ffmpeg -version

# Verificar se ImageMagick está instalado
magick -version

# Verificar se Tesseract está instalado
tesseract --version
```

### Problema: OCR retorna texto com muitos erros

**Diagnóstico**:
- Verificar qualidade das imagens intermediárias em `frames/` e `processed/`
- Testar OCR manual: `tesseract processed/frame001.jpg output -l por+eng`

**Soluções**:
1. **Melhorar qualidade de captura**:
   - Usar iluminação mais uniforme
   - Evitar reflexos na superfície
   - Estabilizar câmera (tripé)
   - Usar resolução 4K se disponível

2. **Ajustar pré-processamento**:
```bash
# Modificar parâmetros no script (linhas 200-210)
# Aumentar contraste:
-contrast-stretch 0x5%   # em vez de 0x10%

# Aumentar nitidez:
-unsharp 0x1.0   # em vez de 0x0.5
```

3. **Ajustar idiomas OCR**:
```bash
bash video_to_text.sh -i video.mp4 -l por  # apenas português
bash video_to_text.sh -i video.mp4 -l eng  # apenas inglês
```

### Problema: Script falha com "command not found"

**Instalação de dependências no macOS**:
```bash
# Instalar Homebrew se necessário
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar dependências
brew install ffmpeg imagemagick tesseract

# Instalar idiomas adicionais para Tesseract
brew install tesseract-lang
```

**Instalação no Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install ffmpeg imagemagick tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
```

## Problemas de Sistema

### Problema: MCP Server não inicia

**Diagnóstico**:
```bash
# Verificar Python e dependências
python3 --version
pip list | grep fastapi

# Verificar se porta está em uso
lsof -i :8000
```

**Soluções**:
1. **Instalar dependências**:
```bash
cd src/
pip install -r requirements.txt
```

2. **Verificar configuração**:
```bash
# Verificar se arquivo de configuração existe
ls -la config/

# Verificar logs de startup
python3 api/mcp_server.py --verbose
```

### Problema: Base de dados corrompida

**Diagnóstico**:
```bash
# Verificar integridade do SQLite
sqlite3 knowledge.db "PRAGMA integrity_check;"
```

**Soluções**:
1. **Backup e restauração**:
```bash
# Criar backup
cp knowledge.db knowledge.db.backup

# Tentar reparar
sqlite3 knowledge.db ".recover" | sqlite3 knowledge_recovered.db
```

2. **Migração limpa**:
```bash
# Fazer backup dos dados atuais
python3 scripts/export_data.py --output backup.json

# Recriar base de dados
rm knowledge.db
python3 api/database.py --init

# Reimportar dados
python3 scripts/import_data.py --input backup.json
```

### Problema: Interface web não carrega dados

**Diagnóstico**:
1. **Verificar API**:
```bash
curl http://localhost:8000/api/entities
```

2. **Verificar console do browser** (F12 → Console)

3. **Verificar rede** (F12 → Network tab)

**Soluções**:
1. **Verificar se API está rodando**:
```bash
ps aux | grep fastapi
# ou
lsof -i :8000
```

2. **Verificar CORS**:
```python
# Em api/api.py, verificar se CORS está configurado
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para desenvolvimento
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Verificar cache do browser**:
```bash
# Forçar reload sem cache
Cmd+Shift+R (macOS)
Ctrl+Shift+R (Linux/Windows)
```

## Problemas de Performance

### Problema: Visualização lenta com grafos grandes

**Soluções**:
1. **Implementar filtros**:
```javascript
// Em index.html, adicionar filtros por categoria
const filteredData = data.nodes.filter(node => 
    selectedCategories.includes(node.category)
);
```

2. **Implementar paginação**:
```python
# Em visualization.py
def get_entities_paginated(offset=0, limit=100):
    return db.get_entities(limit=limit, offset=offset)
```

3. **Usar clustering**:
```javascript
// Agrupar nós próximos
const clusteredData = clusterNodes(data, threshold=0.1);
```

### Problema: LLM APIs lentas ou falhando

**Diagnóstico**:
```bash
# Testar conectividade
curl -X POST https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "test"}]}'
```

**Soluções**:
1. **Implementar retry logic**:
```python
import time
import random

def call_llm_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm_client.chat.completions.create(...)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                raise e
```

2. **Implementar fallback models**:
```python
MODELS = ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku"]

def process_with_fallback(prompt):
    for model in MODELS:
        try:
            return call_llm(prompt, model=model)
        except Exception:
            continue
    raise Exception("All models failed")
```

3. **Implementar cache local**:
```python
import hashlib
import json

def cached_llm_call(prompt):
    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    cache_file = f"cache/{cache_key}.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    result = call_llm(prompt)
    
    os.makedirs("cache", exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f)
    
    return result
```

## Logs e Debugging

### Ativar logs detalhados

**MCP Server**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Video to Text Script**:
```bash
bash video_to_text.sh -i video.mp4 --verbose
```

**FastAPI**:
```bash
uvicorn api:app --log-level debug
```

### Verificar logs do sistema

**macOS**:
```bash
# Logs do sistema
log show --predicate 'process == "python3"' --last 1h

# Logs específicos da aplicação
tail -f logs/muleta_cognitiva.log
```

**Linux**:
```bash
# Logs do sistema
journalctl -u muleta-cognitiva -f

# Logs específicos
tail -f /var/log/muleta_cognitiva/app.log
```
