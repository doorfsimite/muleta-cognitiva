#!/usr/bin/env sh
set -eu

# Defaults
LANGS="por+eng"
SCENE_THRESHOLD="0.3"
FPS=""
OUTPUT_DIR="output"
MAKE_PDF=0
KEEP_FRAMES=0
KEEP_PROC=0

print_usage() {
  cat <<'EOF'
Uso: bash video_to_text.sh -i <video.mp4> [opções]

Opções:
  -i, --input <arquivo>       Caminho do vídeo de entrada (obrigatório)
  -o, --outdir <pasta>        Pasta de saída (default: output)
  -l, --langs <tesseract>     Idiomas Tesseract (default: por+eng)
  -t, --threshold <0-1>       limiar de cena do ffmpeg (default: 0.3)
  -f, --fps <num>             Extrair por FPS (ex.: 1) em vez de detecção de cena
  -p, --pdf                   Também gerar PDF pesquisável (une páginas se possível)
      --keep-frames           Não apagar frames extraídos
      --keep-proc             Não apagar imagens processadas
  -h, --help                  Mostrar ajuda

Exemplos:
  bash video_to_text.sh -i livro.mp4
  bash video_to_text.sh -i livro.mp4 -l por -p
  bash video_to_text.sh -i livro.mp4 -f 1               # 1 quadro por segundo
  bash video_to_text.sh -i livro.mp4 -t 0.25 -o saida   # detecção de cena mais sensível

Pré-requisitos (Homebrew):
  brew install ffmpeg tesseract imagemagick
  # Idioma português (se necessário):
  # baixe por.traineddata em /opt/homebrew/share/tessdata (Apple Silicon)
EOF
}

# parse args
INPUT_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    -i|--input)
      INPUT_FILE="${2:-}"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [ -z "${INPUT_FILE}" ]; then
  echo "Error: input file not provided. Use -i <path-to-video>" >&2
  exit 1
fi
if [ ! -f "${INPUT_FILE}" ]; then
  echo "Error: input file not found: ${INPUT_FILE}" >&2
  exit 1
fi

export VIDEO_PATH="${INPUT_FILE}"

# Check deps
need() { command -v "$1" >/dev/null 2>&1; }
if ! need ffmpeg; then echo "Falta ffmpeg. Instale: brew install ffmpeg" >&2; exit 1; fi
if ! need tesseract; then echo "Falta tesseract. Instale: brew install tesseract" >&2; exit 1; fi
# ImageMagick 7 usa 'magick', às vezes 'convert'
IMG_CMD=""
if need magick; then IMG_CMD="magick"; elif need convert; then IMG_CMD="convert"; else echo "Falta ImageMagick. Instale: brew install imagemagick" >&2; exit 1; fi

 # Setup paths
INPUT_ABS=$(python3 - "$INPUT_FILE" <<PY
import os,sys
if len(sys.argv) > 1:
  p = os.path.abspath(sys.argv[1])
  print(p)
else:
  raise SystemExit("No input file provided to Python (argv[1])")
PY
)
BASE_NAME=$(basename "$INPUT_ABS")
NAME_NOEXT="${BASE_NAME%.*}"
OUT_ROOT="${OUTPUT_DIR}/${NAME_NOEXT}"
FRAMES_DIR="${OUT_ROOT}/frames"
PROC_DIR="${OUT_ROOT}/proc"
TXT_DIR="${OUT_ROOT}/txt"
PDF_DIR="${OUT_ROOT}/pdf"

mkdir -p "$FRAMES_DIR" "$PROC_DIR" "$TXT_DIR"
[ "$MAKE_PDF" -eq 1 ] && mkdir -p "$PDF_DIR"

# 1) Extract frames
echo "[1/4] Extraindo quadros…"
mkdir -p "$FRAMES_DIR"

# Check video properties for debugging
echo "Verificando propriedades do vídeo..."
ffprobe -v quiet -print_format json -show_format -show_streams "$INPUT_ABS" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Erro: Não foi possível analisar o vídeo. Verifique se o arquivo está corrompido." >&2
  exit 2
fi

# Get video duration and frame count for reference
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT_ABS" 2>/dev/null)
echo "Duração do vídeo: ${DURATION:-desconhecida} segundos"

# Try frame extraction with multiple fallback methods
EXTRACTED=0

if [ -n "$FPS" ]; then
  echo "Extraindo quadros por FPS (${FPS})..."
  ffmpeg -hide_banner -loglevel error -y -i "$INPUT_ABS" \
    -vf "fps=${FPS}" \
    -q:v 2 -pix_fmt yuvj420p \
    "${FRAMES_DIR}/pagina_%04d.jpg"
  
  # Check if extraction worked
  if ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
    EXTRACTED=1
  fi
else
  echo "Tentando detecção de cena (threshold=${SCENE_THRESHOLD})..."
  ffmpeg -hide_banner -loglevel warning -y -i "$INPUT_ABS" \
    -vf "select='gt(scene,${SCENE_THRESHOLD})'" \
    -vsync vfr \
    -q:v 2 -pix_fmt yuvj420p \
    "${FRAMES_DIR}/pagina_%04d.jpg"
  
  # Check if extraction worked
  if ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
    EXTRACTED=1
    echo "Detecção de cena funcionou."
  else
    echo "Detecção de cena não extraiu quadros. Tentando threshold mais baixo..."
    # Try with lower threshold
    ffmpeg -hide_banner -loglevel warning -y -i "$INPUT_ABS" \
      -vf "select='gt(scene,0.1)'" \
      -vsync vfr \
      -q:v 2 -pix_fmt yuvj420p \
      "${FRAMES_DIR}/pagina_%04d.jpg"
    
    if ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
      EXTRACTED=1
      echo "Threshold mais baixo (0.1) funcionou."
    fi
  fi
fi

# Fallback: extract frames at 1 second intervals if scene detection failed
if [ "$EXTRACTED" -eq 0 ]; then
  echo "Detecção de cena falhou. Extraindo 1 quadro por segundo como fallback..."
  ffmpeg -hide_banner -loglevel warning -y -i "$INPUT_ABS" \
    -vf "fps=1" \
    -q:v 2 -pix_fmt yuvj420p \
    "${FRAMES_DIR}/pagina_%04d.jpg"
  
  if ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
    EXTRACTED=1
    echo "Extração por FPS (1/seg) funcionou."
  fi
fi

# Final fallback: extract every 30th frame
if [ "$EXTRACTED" -eq 0 ]; then
  echo "Último recurso: extraindo a cada 30 quadros..."
  ffmpeg -hide_banner -loglevel warning -y -i "$INPUT_ABS" \
    -vf "select='not(mod(n\,30))'" \
    -vsync vfr \
    -q:v 2 -pix_fmt yuvj420p \
    "${FRAMES_DIR}/pagina_%04d.jpg"
  
  if ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
    EXTRACTED=1
    echo "Extração a cada 30 quadros funcionou."
  fi
fi

# Final check
if [ "$EXTRACTED" -eq 0 ]; then
  echo "ERRO: Nenhum método de extração funcionou." >&2
  echo "Tente:" >&2
  echo "1. Verificar se o vídeo não está corrompido" >&2
  echo "2. Usar --fps 0.5 para extrair menos quadros" >&2
  echo "3. Converter o vídeo para outro formato primeiro" >&2
  echo "Comando de teste: ffmpeg -i \"$INPUT_ABS\" -t 10 -vf fps=1 test_%03d.jpg" >&2
  exit 2
fi

# Report success
FRAME_COUNT=$(ls "$FRAMES_DIR"/*.jpg 2>/dev/null | wc -l | tr -d ' ')
echo "Sucesso: $FRAME_COUNT quadros extraídos."

# sanity: se não extraiu nada
if ! ls "$FRAMES_DIR"/*.jpg >/dev/null 2>&1; then
  echo "Nenhum quadro extraído. Tente ajustar --fps ou --threshold, ou verifique se o vídeo tem conteúdo visível." >&2
  exit 2
fi

# 2) Preprocess
echo "[2/4] Pré-processando imagens…"
for f in "$FRAMES_DIR"/*.jpg; do
  bn=$(basename "$f")
  # Ajustes: orientação, cinza, contraste, nitidez, redimensionamento gentil
  "$IMG_CMD" "$f" -auto-orient -resize 2000x -colorspace Gray \
    -contrast-stretch 0x10% -unsharp 0x0.5 "${PROC_DIR}/${bn}"
done

# 3) OCR
echo "[3/4] Executando OCR (Tesseract, langs=$LANGS)…"
COUNT=0
for f in "$PROC_DIR"/*.jpg; do
  bn=$(basename "$f" .jpg)
  out_base="${TXT_DIR}/${bn}"
  tesseract "$f" "$out_base" -l "$LANGS" --psm 1 > /dev/null 2>&1 || true
  COUNT=$((COUNT+1))
  if [ "$MAKE_PDF" -eq 1 ]; then
    tesseract "$f" "${PDF_DIR}/${bn}" -l "$LANGS" --psm 1 pdf > /dev/null 2>&1 || true
  fi
  printf "\rPáginas processadas: %d" "$COUNT"
done
printf "\n"

# 4) Merge outputs
echo "[4/4] Unindo textos…"
out_txt="${OUT_ROOT}/${NAME_NOEXT}.txt"
cat "$TXT_DIR"/*.txt > "$out_txt" || true

if [ "$MAKE_PDF" -eq 1 ]; then
  echo "Gerando PDF único (se possível)…"
  combined_pdf="${OUT_ROOT}/${NAME_NOEXT}.pdf"
  # Preferir gs, senão pdfunite
  if need gs; then
    gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile="$combined_pdf" "$PDF_DIR"/*.pdf || true
  elif need pdfunite; then
    pdfunite "$PDF_DIR"/*.pdf "$combined_pdf" || true
  else
    echo "Nem 'gs' (Ghostscript) nem 'pdfunite' encontrados. PDFs por página estão em: $PDF_DIR" >&2
  fi
fi

# Cleanup
if [ "$KEEP_FRAMES" -ne 1 ]; then rm -rf "$FRAMES_DIR"; fi
if [ "$KEEP_PROC" -ne 1 ]; then rm -rf "$PROC_DIR"; fi

# Summary
TXT_BYTES=$(wc -c < "$out_txt" | tr -d ' ')
PAGES=$(ls "$TXT_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')

echo "\nConcluído."
echo "- Texto: $out_txt ($TXT_BYTES bytes)"
echo "- Páginas OCR: $PAGES (arquivos em $TXT_DIR)"
if [ "$MAKE_PDF" -eq 1 ]; then
  if [ -f "$combined_pdf" ]; then
    echo "- PDF pesquisável: $combined_pdf"
  else
    echo "- PDFs por página: $PDF_DIR"
  fi
fi

echo "Done."
