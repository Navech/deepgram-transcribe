---
name: deepgram-transcribe
description: Cubre todo el ciclo de transcripción de audio con Deepgram en cualquier proyecto. Tres modos según lo que pida el usuario - (A) SETUP - configura Deepgram en el proyecto actual (instala deepgram-sdk / @deepgram/sdk, copia el módulo transcriptor, deja DEEPGRAM_API_KEY en .env/.env.example con .gitignore, corre smoke test); (B) TRANSCRIBE ARCHIVO - transcribe un audio local (m4a/mp3/wav/ogg/webm/flac/aac) imprimiendo o guardando .txt/.md junto al archivo; (C) TRANSCRIBE URL - baja con yt-dlp y transcribe URLs de Instagram reels, YouTube, TikTok, X/Twitter. Defaults nova-3, multilingüe, smart_format. Usar cuando el usuario invoca /deepgram-transcribe o pide "configura Deepgram aquí", "deja Deepgram listo", "transcribe este audio", "transcríbeme esto", "pasa esto a texto", "transcribe este reel/video/short", "transcribe https://...", o pega un link de IG/YouTube/TikTok pidiendo el texto.
---

# deepgram-transcribe

Skill todo-en-uno para Deepgram. Cubre el setup inicial en un proyecto **y** el uso diario (transcribir archivos locales o URLs de redes). Defaults agresivos — el usuario quiere velocidad.

## Cuándo invocar y qué modo correr

Elige el modo según la intención del mensaje:

| Trigger del usuario | Modo |
|---|---|
| `/deepgram-transcribe` sin argumentos, "configura Deepgram aquí", "deja Deepgram listo en este repo" | **A — Setup** |
| Menciona un archivo de audio local ("transcribe esto.m4a", "transcríbeme el audio X") | **B — Transcribe archivo** |
| Pega una URL (IG reel, YouTube, TikTok, X) o dice "transcribe este reel/video" | **C — Transcribe URL** |

Si la intención es ambigua, asumir B/C antes que A (lo más frecuente).

## Defaults (NO preguntar — el usuario quiere rapidez)
- Modelo: `nova-3` · Idioma: `multi` (multilingüe; mejor que `es` para audio en español).
- `smart_format: true`, diarización off (`--diarize` para activarla).
- `--timeout 600`, `--retries 2` nativos del SDK.
- Salida: `.txt` junto al audio (URLs: en CWD). `--out md` para metadata, `--out -` para solo imprimir.
- Templates en `~/.claude/skills/deepgram-transcribe/templates/`.
- **Único prompt esperable**: API key si no se encuentra.

---

## Modo A — Setup en el proyecto

### 1. Analizar el proyecto y decidir runtime
- **Node** si hay `package.json`.
- **Python** si hay `pyproject.toml`, `requirements.txt`, `setup.py`, un venv, o archivos `*.py`.
- Si **ambos**, elegir el principal según dónde vive el código fuente; si es ambiguo, preguntar UNA vez.
- Si **ninguno** → Python standalone (script en CWD).

Detectar layout (`src/`, `app/`, raíz) y, en Node, el gestor (`pnpm-lock.yaml`→pnpm, `yarn.lock`→yarn, si no npm).

### 2. Instalar la dependencia
- **Python**: si hay `pyproject.toml`, añadir `deepgram-sdk>=7.0` (preferir extra opcional, p.ej. `[project.optional-dependencies] transcription = ["deepgram-sdk>=7.0"]`); si solo hay `requirements.txt`, añadir la línea ahí. Instalar: `python3 -m pip install "deepgram-sdk>=7.0"` (usar el venv del proyecto si existe).
- **Node**: `npm install @deepgram/sdk` (o pnpm/yarn según lockfile).

### 3. Copiar el módulo transcriptor
- **Python**: copiar `templates/deepgram_transcribe.py` a una ubicación sensata (raíz, o `src/`/`app/`).
- **Node**: copiar `templates/deepgramTranscribe.mjs` (si es TypeScript, mantener `.mjs` o adaptarlo a `.ts` conservando la API).

Ambos traen función `transcribe(...)` + CLI con soporte de URL.

### 4. Configurar `.env`
- Añadir `DEEPGRAM_API_KEY=` a `.env.example` (crear si no existe) y a `.env`.
- Asegurar `.env` en `.gitignore` (añadir si falta).
- Si la key ya está en entorno o `.env`, reusarla. Si no, **pedir al usuario que la pegue** y escribirla en `.env` (nunca en versionados).

### 5. Smoke test
Buscar un audio en el proyecto (`.m4a .mp3 .wav .ogg .webm .flac .aac`). Si hay, transcribir el primero:
- Python: `python3 <ruta>/deepgram_transcribe.py "<audio>" --out -`
- Node: `node <ruta>/deepgramTranscribe.mjs "<audio>" --out -`

Si no hay audio, saltar avisando que quedó configurado pero sin verificar.

### 6. Reportar
Runtime detectado, dependencia añadida, archivos creados, y cómo usar (ver "Uso" abajo). Nota de privacidad.

---

## Modo B — Transcribir un archivo local

Llamar directamente al template (no hay que copiar nada al proyecto):
```bash
python3 ~/.claude/skills/deepgram-transcribe/templates/deepgram_transcribe.py "<audio>" --out -
```
(Equivalente Node con `node …deepgramTranscribe.mjs`.)

Pasar `--language` (`es|en|auto|multi`), `--diarize`, `--out txt|md|-`, `--timeout <s>` según contexto.

Si falta `DEEPGRAM_API_KEY` en el entorno o `.env` (CWD o junto al script), pedir al usuario que la pegue y exportarla para la sesión (`export DEEPGRAM_API_KEY=...`) o escribirla en un `.env` del CWD.

Si falla con "deepgram-sdk no instalado", correr `pip install "deepgram-sdk>=7.0"` (o `pipx inject`).

---

## Modo C — Transcribir desde URL (reels IG, YouTube, TikTok, X)

El template **auto-detecta** URLs: pasa la URL como argumento, el script usa `yt-dlp` para bajar el audio (m4a), transcribe, y borra el temporal.

```bash
python3 ~/.claude/skills/deepgram-transcribe/templates/deepgram_transcribe.py "https://www.instagram.com/reel/XXX/" --out -
```

Verificaciones previas:
- `yt-dlp` debe estar en PATH. Si no: `brew install yt-dlp` (o `pipx install yt-dlp`). El script da el mensaje.
- Para **contenido privado** (cuentas privadas, lives), agregar cookies del navegador: el usuario debe correr `yt-dlp --cookies-from-browser chrome -x --audio-format m4a "<url>" -o audio.m4a` y luego usar Modo B sobre el archivo.

El `.txt`/`.md` se guarda en el CWD con el `id` del video como nombre (a no ser que se use `--out -`).

---

## Estructura del skill

- `SKILL.md` — este archivo.
- `templates/deepgram_transcribe.py` — Python autocontenido + CLI (`argparse`). SDK v7: `DeepgramClient(api_key).listen.v1.media.transcribe_file(request=bytes, model=, language=, smart_format=, diarize=, request_options={timeout_in_seconds, max_retries})`.
- `templates/deepgramTranscribe.mjs` — Node ESM + CLI. SDK v5+: `new DeepgramClient({apiKey}).listen.v1.media.transcribeFile(buffer, opts, {timeoutInSeconds, maxRetries})`.

Ambos parsean defensivamente: `response.results.channels[0].alternatives[0].transcript` + `.confidence`.

## Errores comunes

- **`deepgram-sdk` no instalado / import falla**: correr el `pip install` / `npm install` del paso de Setup.
- **401 / sin créditos**: API key inválida o sin saldo — verificar en panel de Deepgram.
- **Respuesta inesperada del SDK**: las APIs cambian entre mayores. Verificar firma (Python v7 / Node v5) y `results.channels[0].alternatives[0]`.
- **Transcripción vacía**: audio sin habla, corrupto o formato no soportado.
- **`write operation timed out`**: subir `--timeout` (p. ej. 1200) o `--retries`.
- **`yt-dlp not found`**: `brew install yt-dlp` o `pipx install yt-dlp`.
- **`yt-dlp failed`**: video privado/eliminado/age-gated; probar con `--cookies-from-browser` aparte y usar Modo B.
