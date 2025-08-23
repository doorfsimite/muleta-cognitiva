# Vídeo → Texto (OCR) – macOS

Script `video_to_text.sh` para converter um vídeo de páginas de livro em texto (e PDF pesquisável opcional).

## Pré-requisitos
- Homebrew instalado
- Ferramentas:
  - ffmpeg
  - tesseract (com `por` para português; opcional `eng`)
  - imagemagick (comando `magick` ou `convert`)
- Opcional para unir PDFs:
  - ghostscript (`gs`) ou `pdfunite`

Instalação rápida:

```bash
brew install ffmpeg tesseract imagemagick ghostscript poppler
```

Se faltar o idioma português no Tesseract, baixe `por.traineddata` e coloque em:
- Apple Silicon: `/opt/homebrew/share/tessdata`
- Intel: `/usr/local/share/tessdata`

## Uso básico
No Terminal:
```bash
cd "/Users/davisimite/Documents/grafo filosofico"
bash video_to_text.sh -i caminho/para/livro.mp4
```
Saída em `output/<nome do vídeo>/`. O texto unido estará em `output/<nome>/<nome>.txt`.

## Opções úteis
- `-l por+eng` define idiomas do OCR (padrão: `por+eng`).
- `-p` também gera PDF pesquisável único (se `gs`/`pdfunite` disponível).
- `-f 1` usa 1 quadro/segundo em vez de detecção de cena.
- `-t 0.25` ajusta sensibilidade da detecção de cena (0.2–0.5 bons pontos de partida).
- `--keep-frames` e `--keep-proc` evitam apagar intermediários.

## Dicas de captura
- Luz forte e uniforme; evite reflexos.
- Tripé; virar páginas devagar.
- 4K/60fps reduz borrões; trave foco/exposição.

## Observações legais
Use apenas com conteúdo que você tem direito de copiar. Evite redistribuição de material protegido.
