---
name: video-pipeline
description: Pipeline híbrido local-first para dissecar vídeos (talks, demos, marketing). Combina Whisper ASR local + OpenCV shot detection + Tesseract OCR + MiniMax Vision API (quando necessário). Pipeline Opção B: extrai frame em TODO shot change, ASR cobre 100% do áudio. Companion user-invoked do `system-dissector` quando usado via `triage-video`.
license: MIT
compatibility: Claude Code, Codex, OpenCode
metadata:
  author: Anderson Oliveira (neodissector)
  version: "0.1.0"
  framework: neodissector
  role: tooling
disable-model-invocation: true
---

Você é o **video-pipeline** do neodissector. Sua missão é dissecar vídeos **automaticamente** gerando um índice navegável de:

1. **ASR completo** (Whisper local) — 100% do áudio transcrito
2. **Shot detection** (OpenCV) — 100% das cenas detectadas
3. **Frames-chave** (ffmpeg) — 1 frame por cena
4. **OCR** (Tesseract local) — texto na tela
5. **Vision API** (MiniMax) — SÓ onde OCR não resolveu

## Capacidades

| Stage | Ferramenta | Output |
|-------|-----------|--------|
| 1. Audio extraction | ffmpeg | audio/audio.mp3 |
| 2. ASR | OpenAI Whisper (local) | transcript.json com 221+ segments |
| 3. Shot detection | OpenCV | 30-100 cenas |
| 4. Frame extraction | ffmpeg | 30-100 frames em frames/ |
| 5. OCR | Tesseract | texto em ocr/frame_NNN.txt |
| 6. Vision API | MiniMax Vision | descrição semântica (só quando OCR falha) |

## Pré-requisitos (todos já instalados)

```bash
yt-dlp
ffmpeg
brew install tesseract deno   # deno para yt-dlp JS challenges
python3 -m pip install --break-system-packages openai-whisper opencv-python-headless pytesseract pillow
```

## Stack

```
Local (grátis, ~95% do trabalho):
├── yt-dlp                    # download YouTube
├── ffmpeg                    # audio + frames
├── opencv-python-headless    # shot detection
├── openai-whisper            # ASR (modelo base ~150MB)
├── pytesseract + tesseract-ocr  # OCR
└── (opcional) easyocr

Externo (pago, ~5% do trabalho):
└── MiniMax Vision API (MINIMAX_API_KEY)
```

## Uso

```bash
# Download + analyze
yt-dlp -f "worstvideo+worstaudio/worst" -o "source.%(ext)s" "URL_DO_VIDEO"
python3 ~/.agents/skills/video-pipeline/resources/scripts/analyze.py \
  --video source.mp4 \
  --output-dir ./output/ \
  --whisper-model base \
  --scene-threshold 15.0 \
  --vision-key $MINIMAX_API_KEY
```

## Quando usar

| Cenário | Caso |
|---------|------|
| ✅ Talk de conference técnica | PyCon, FOSDEM, JSConf, Odoo Experience |
| ✅ Demo de software com UI na tela | Captura UI flows + fala |
| ✅ Marketing video de vendor | Extrai claims + demo visual |
| ✅ Security POC video | Captura fala + exploit visual |
| ✅ Tutorial técnico (código na tela) | Tesseract captura código |
| ❌ Live stream (não tem arquivo) | Use `--video URL` com m3u8 |

## Quando NÃO usar

- Vídeos só de narração (sem conteúdo visual) — use só Whisper
- Vídeos longos (>3h) — Whisper fica lento em CPU; use GPU ou `tiny`/`base` models
- Vídeos confidenciais (enviar frames pra Vision API é privacy concern) — só use pipeline local

## Output schema

```
output/
├── audio/audio.mp3                  # 5-20MB
├── transcript.json                   # Whisper ASR
├── timeline.json                     # MASTER: timeline indexada
├── frames/
│   ├── frame_scene000_t000005.jpg   # 1 per cena
│   └── ...
├── ocr/
│   ├── frame_scene000_t000005.jpg.txt
│   └── ...
└── vision/                           # SÓ se Vision API chamada
    └── ...
```

## Política

- **Privacidade**: ~95% processamento local, ~5% Vision API (apenas frames com OCR falho)
- **Custo típico**: ~$0.05-0.50 por vídeo de 30min (Vision API só onde preciso)
- **Latência**: 30s-2min para vídeo de 30min em CPU (Whisper base)

## Concessões (decisões de design)

1. **Frame em TODO shot change** (não só em demonstration cues) — heurística de cue era frágil
2. **Vision API SÓ onde OCR falha** — economia sem perder informação
3. **Whisper "base" como default** — velocidade vs qualidade (use `small`/`medium` se quiser melhor)
4. **OpenCV threshold 15.0** — balanço entre sensibilidade e ruído

## Não viola

- **Não envia áudio** pra Vision API — só frames
- **Não envia transcript** pra lugar nenhum — Whisper é 100% local
- **OCR é 100% local** — Tesseract não tem rede
- **Sanitização final**: rode `verify-no-verbatim.py` no output se for integrar com dissecador

## Conexão com `triage-video`

O sub-agent `triage-video` (em `system-dissector/resources/scripts/prompts/`) orquestra este pipeline como parte do workflow de dissecação de UI-only + vídeo.
