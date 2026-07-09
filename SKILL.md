---
name: deepgram-transcribe
description: Cubre todo el ciclo de transcripción de audio con Deepgram en cualquier proyecto, MÁS extraer imágenes de carruseles de Instagram. Cuatro modos según lo que pida el usuario - (A) SETUP - configura Deepgram en el proyecto actual (instala deepgram-sdk / @deepgram/sdk, copia el módulo transcriptor, deja DEEPGRAM_API_KEY en .env/.env.example con .gitignore, corre smoke test); (B) TRANSCRIBE ARCHIVO - transcribe un audio local (m4a/mp3/wav/ogg/webm/flac/aac) imprimiendo o guardando .txt/.md junto al archivo; (C) TRANSCRIBE URL - baja con yt-dlp y transcribe URLs de Instagram reels, YouTube, TikTok, X/Twitter; (D) CARRUSEL IG - baja con gallery-dl las imágenes de un post/carrusel de Instagram (fotos, no reel) y Claude las lee por VISIÓN para extraer y sintetizar la información valiosa de cada slide. Defaults nova-3, multilingüe, smart_format. Usar cuando el usuario invoca /deepgram-transcribe o pide "configura Deepgram aquí", "deja Deepgram listo", "transcribe este audio", "transcríbeme esto", "pasa esto a texto", "transcribe este reel/video/short", "transcribe https://...", "extrae las fotos de este carrusel/post de IG", "analiza este post de Instagram", "resume este carrusel", o pega un link de IG/YouTube/TikTok pidiendo el texto o el contenido.
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
| Pega un post de Instagram de **fotos/carrusel** (`/p/…` o `/reel/…` que es galería) o dice "extrae/analiza/resume las fotos de este post" | **D — Carrusel IG** |

Si la intención es ambigua, asumir B/C/D antes que A (lo más frecuente).

**Reel vs carrusel (ambos usan `/p/` o `/reel/`):** un mismo link puede ser video (Modo C) o galería de imágenes (Modo D). Si el usuario habla de "fotos", "carrusel", "slides", "infografía" → Modo D. Si habla de "audio", "lo que dice", "transcribe" → Modo C. Si no está claro y el Modo C reporta "No video formats found", es un carrusel → cae a Modo D.

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
- **No requiere ffmpeg** en el caso típico — el template usa `-f bestaudio/best` (audio nativo del origen, sin reconvertir) y Deepgram acepta m4a/webm/mp4 directamente. Solo si la URL trae streams separados, el script pide `brew install ffmpeg`.
- Para **contenido privado** (cuentas privadas, lives), agregar cookies del navegador: el usuario debe correr `yt-dlp --cookies-from-browser chrome -f bestaudio/best "<url>" -o audio.m4a` y luego usar Modo B sobre el archivo.

El `.txt`/`.md` se guarda en el CWD con el `id` del video como nombre (a no ser que se use `--out -`).

---

## Modo D — Carrusel de Instagram (fotos → VISIÓN)

Para posts de **imágenes** (carruseles/infografías), no video. `yt-dlp` **no sirve** aquí: para Instagram solo baja formatos de video y devuelve "No video formats found". Se usa **gallery-dl**, que baja las N imágenes del post. Luego **Claude las lee por visión** (tool Read) y cura/extrae — mismo patrón de `clase-a-apunte` (capturar todo → la visión cura).

### Flujo
1. **Bajar y numerar** las slides con el helper:
   ```bash
   python3 ~/.claude/skills/deepgram-transcribe/templates/ig_carousel_fetch.py "https://www.instagram.com/p/XXXX/" --out ./ig_XXXX
   ```
   - Imprime en stdout la ruta absoluta de cada `slide_NN.png` en orden. Las descarga (gallery-dl), las ordena y convierte `.webp`→`.png` (con `sips` en macOS o Pillow).
   - Por defecto usa `--browser chrome` para las cookies (Instagram casi siempre exige sesión). Si el usuario usa otro navegador, pasar `--browser safari|firefox`. Para no usar cookies: `--browser ''`.

2. **Leer TODAS las PNG** con la herramienta Read (visión), en orden de slide. Se pueden leer varias por mensaje.

3. **Curar y extraer** (rol de Claude, no del script):
   - **Descartar** portadas puramente estéticas, slides de "guarda/comparte/sígueme", y decoración sin info (igual que `clase-a-apunte` descarta intro/outro).
   - **Transcribir** el texto real de cada slide; **describir** figuras/diagramas/tablas si aportan.
   - **Sintetizar** los puntos valiosos en orden, no slide-por-slide literal salvo que el usuario lo pida.
   - Mantener criterio de **espejo, no oráculo**: si el post es marketing/hype, decirlo y separar lo aprovechable del gancho.

### Verificaciones previas
- `gallery-dl` en PATH o como módulo. Si falta: `python3 -m pip install --user gallery-dl` (o `pipx install gallery-dl`). El helper da el mensaje.
- **Autenticación**: si gallery-dl reporta login/empty/403, reintentar con `--browser <navegador con sesión de IG>`. En macOS, Safari bloquea el acceso a sus cookies (usar Chrome/Firefox).
- Conversión a PNG: `sips` viene con macOS; en otros SO instalar `Pillow`.

---

## Estructura del skill

- `SKILL.md` — este archivo.
- `templates/deepgram_transcribe.py` — Python autocontenido + CLI (`argparse`). SDK v7: `DeepgramClient(api_key).listen.v1.media.transcribe_file(request=bytes, model=, language=, smart_format=, diarize=, request_options={timeout_in_seconds, max_retries})`.
- `templates/deepgramTranscribe.mjs` — Node ESM + CLI. SDK v5+: `new DeepgramClient({apiKey}).listen.v1.media.transcribeFile(buffer, opts, {timeoutInSeconds, maxRetries})`.
- `templates/ig_carousel_fetch.py` — Modo D: baja un carrusel de IG con gallery-dl, convierte a PNG numerados (`slide_NN.png`) e imprime sus rutas para leerlas por visión. Sin dependencias del SDK de Deepgram.

Los transcriptores parsean defensivamente: `response.results.channels[0].alternatives[0].transcript` + `.confidence`.

## Errores comunes

- **`deepgram-sdk` no instalado / import falla**: correr el `pip install` / `npm install` del paso de Setup.
- **401 / sin créditos**: API key inválida o sin saldo — verificar en panel de Deepgram.
- **Respuesta inesperada del SDK**: las APIs cambian entre mayores. Verificar firma (Python v7 / Node v5) y `results.channels[0].alternatives[0]`.
- **Transcripción vacía**: audio sin habla, corrupto o formato no soportado.
- **`write operation timed out`**: subir `--timeout` (p. ej. 1200) o `--retries`.
- **`yt-dlp not found`**: `brew install yt-dlp` o `pipx install yt-dlp`.
- **`yt-dlp failed`**: video privado/eliminado/age-gated; probar con `--cookies-from-browser` aparte y usar Modo B.
- **`No video formats found` en un link de IG**: es un carrusel de fotos, no video → usar **Modo D** (gallery-dl).
- **`gallery-dl no está instalado`**: `python3 -m pip install --user gallery-dl` o `pipx install gallery-dl`.
- **gallery-dl pide login / respuesta vacía / 403**: post que requiere sesión → `--browser chrome` (o el navegador con sesión de IG). En macOS, Safari bloquea sus cookies; usar Chrome/Firefox.
