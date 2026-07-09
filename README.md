# deepgram-transcribe

Claude Code skill todo-en-uno para [Deepgram](https://deepgram.com/) — el motor de transcripción de audio en la nube. Cubre **el ciclo completo** en cualquier proyecto:

- **Setup** — configura Deepgram en el proyecto actual (instala el SDK, copia un módulo transcriptor reutilizable, deja `DEEPGRAM_API_KEY` en `.env`, corre smoke test).
- **Transcribir archivos** — locales (`.m4a`, `.mp3`, `.wav`, `.ogg`, `.webm`, `.flac`, `.aac`).
- **Transcribir URLs** — Instagram reels, YouTube, TikTok, X/Twitter… cualquier cosa que [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) sepa bajar.
- **Carruseles de Instagram** — posts de **fotos** (no video): baja cada slide con [`gallery-dl`](https://github.com/mikf/gallery-dl) y Claude las lee por **visión** para extraer y sintetizar la info valiosa de cada imagen.

Defaults: modelo `nova-3` multilingüe, `smart_format` activado, salida `.txt` junto al audio. Soporta Python y Node/JS — el skill detecta el runtime del proyecto.

---

## Requisitos

| Requisito | Cómo obtenerlo |
|---|---|
| [Claude Code](https://claude.com/claude-code) instalado | `npm i -g @anthropic-ai/claude-code` o ver docs oficiales |
| API key de Deepgram | Registrarse gratis en https://console.deepgram.com (incluye **$200 USD en créditos**) |
| Python 3.11+ **o** Node 18+ | Según el proyecto donde lo uses |
| `yt-dlp` *(opcional, solo para URLs)* | `brew install yt-dlp` o `pipx install yt-dlp` |
| `gallery-dl` *(opcional, solo para carruseles de IG)* | `pipx install gallery-dl` o `python3 -m pip install --user gallery-dl` |
| `ffmpeg` *(opcional, raro)* | Solo necesario para algunas URLs que entregan audio+video en pistas separadas y exigen merge. Para el 99% de los casos **no hace falta** (el template usa `-f bestaudio/best`, audio nativo sin conversión). Si lo necesitas: `brew install ffmpeg`. |

---

## Instalación (en 3 pasos)

### 1) Clonar el skill en tu carpeta de skills de Claude Code

```bash
git clone https://github.com/Navech/deepgram-transcribe.git ~/.claude/skills/deepgram-transcribe
```

Eso es todo lo que necesita Claude Code para reconocer el skill — se autocarga al iniciar la sesión.

### 2) Tu API key de Deepgram

**Importante:** este repo **no incluye ninguna API key**. Cada quien usa la suya.

Cuando uses el skill en un proyecto, Claude te pedirá la key si no la encuentra. La pega y se guarda en el `.env` del proyecto (que el skill mismo agrega al `.gitignore`).

Si prefieres exportarla manualmente para una sesión:

```bash
export DEEPGRAM_API_KEY="tu-key-aquí"
```

### 3) Invocar el skill

Abre Claude Code en tu proyecto y escribe:

```
/deepgram-transcribe
```

…o simplemente pídele en lenguaje natural lo que quieras hacer (ver "Uso" más abajo). El skill se autodispara con los triggers correctos.

---

## Uso

### Modo A · Setup en un proyecto

```
/deepgram-transcribe
```

o

> "Configura Deepgram aquí" / "Deja Deepgram listo en este repo"

→ Claude analiza el proyecto (Python o Node), instala el SDK adecuado (`deepgram-sdk` o `@deepgram/sdk`), copia el módulo transcriptor a tu repo, configura `.env`, y corre un smoke test con un audio del proyecto para verificar.

### Modo B · Transcribir un archivo local

> "Transcribe esto.m4a" / "Pásame este audio a texto"

→ Claude llama al template directo (sin tocar nada del proyecto), imprime el texto y/o guarda un `.txt` junto al audio.

Equivalente manual:
```bash
python3 ~/.claude/skills/deepgram-transcribe/templates/deepgram_transcribe.py audio.m4a
# o, si configuraste el proyecto (Modo A):
python3 deepgram_transcribe.py audio.m4a --out md --diarize
```

### Modo C · Transcribir una URL (reel, video, short…)

> "Transcribe este reel: https://www.instagram.com/reel/XXX/"
> "Pásame el audio de este video a texto"

→ Claude usa `yt-dlp` para bajar el audio, lo manda a Deepgram, y borra el temporal. Funciona con todo lo que yt-dlp soporta (IG, YouTube, TikTok, X, Twitch…).

Equivalente manual:
```bash
python3 ~/.claude/skills/deepgram-transcribe/templates/deepgram_transcribe.py \
  "https://www.instagram.com/reel/XXX/" --out -
```

> **Contenido privado** (cuentas privadas, lives suscritos): el skill no lo maneja directamente. Baja el audio aparte con `yt-dlp --cookies-from-browser chrome <url>` y luego usa el Modo B sobre el archivo.

### Modo D · Carrusel de Instagram (fotos → análisis)

> "Extrae las fotos de este carrusel: https://www.instagram.com/p/XXXX/"
> "Analiza / resume este post de Instagram"

→ Claude baja cada slide con `gallery-dl`, las convierte a PNG, las **lee por visión**, descarta la decoración/portadas y te sintetiza la información valiosa de cada imagen.

Equivalente manual (baja + numera; luego Claude lee los PNG):
```bash
python3 ~/.claude/skills/deepgram-transcribe/templates/ig_carousel_fetch.py \
  "https://www.instagram.com/p/XXXX/" --out ./ig_XXXX --browser chrome
```

> Instagram casi siempre exige sesión: el helper usa las cookies de Chrome por defecto (`--browser safari|firefox` para otro navegador). Ojo: `yt-dlp` **no** sirve para carruseles de fotos — solo baja video.

---

## Flags del CLI

```
python3 deepgram_transcribe.py <audio-o-url...> [opciones]
```

| Flag | Default | Qué hace |
|---|---|---|
| `--model` | `nova-3` | Modelo Deepgram. |
| `--language` | `multi` | `multi` (multilingüe nova-3), o `es`, `en`, `auto` (autodetectar). |
| `--no-smart-format` | off | Desactiva puntuación/capitalización automática. |
| `--diarize` | off | Etiqueta hablantes (Speaker 0, 1, …). Útil para conversaciones. |
| `--out` | `txt` | `txt` (junto al audio), `md` (con metadata), `-` (solo imprimir). |
| `--timeout` | `600` | Segundos a esperar por la API. Subir para audios largos (`--timeout 1800`). |
| `--retries` | `2` | Reintentos del SDK ante fallos transitorios. |

---

## Troubleshooting

- **`deepgram-sdk` / `@deepgram/sdk` no instalado** → `pip install deepgram-sdk` o `npm install @deepgram/sdk`.
- **`401 Unauthorized` / "insufficient credits"** → verificar la key en https://console.deepgram.com y el saldo de tu cuenta.
- **`yt-dlp not found`** → `brew install yt-dlp` o `pipx install yt-dlp`.
- **`yt-dlp needs ffmpeg`** → Caso raro: la URL trae audio+video en pistas separadas y yt-dlp necesita ffmpeg para mergearlas. Instala con `brew install ffmpeg` (Linux: `apt install ffmpeg` / `pacman -S ffmpeg`). En general el template evita esto pidiéndole a yt-dlp el audio nativo (`-f bestaudio/best`) — Deepgram acepta m4a/webm/mp4 directos sin reconvertir.
- **`No video formats found` en un link de IG** → es un carrusel de **fotos**, no video. Usa el **Modo D** (`ig_carousel_fetch.py`, con `gallery-dl`).
- **`gallery-dl no está instalado`** → `pipx install gallery-dl` o `python3 -m pip install --user gallery-dl`.
- **gallery-dl: login / respuesta vacía / 403** → el post requiere sesión; pásale cookies con `--browser chrome` (o el navegador donde tengas IG abierto). En macOS, Safari bloquea el acceso a sus cookies — usa Chrome o Firefox.
- **`yt-dlp failed: ... unavailable`** → el video es privado, fue eliminado, o está geobloqueado. Probar con cookies del navegador como se explica en Modo C.
- **`write operation timed out`** (archivos grandes) → subir `--timeout` (p. ej. 1200) y/o `--retries`.
- **Transcripción vacía** → audio sin habla, corrupto, o formato no soportado. Probar otro archivo.

---

## Privacidad

El audio se envía a los servidores de Deepgram para ser procesado. Para contenido sensible (terapia, conversaciones privadas, datos médicos), revisa la política de retención de tu cuenta en https://console.deepgram.com — Deepgram permite desactivar el almacenamiento del audio. Para máxima privacidad, usar un motor local como `whisper.cpp` o `mlx-whisper` en su lugar.

---

## Estructura

```
deepgram-transcribe/
├── SKILL.md                          # workflow que Claude sigue
├── README.md                         # este archivo
├── LICENSE                           # MIT
├── .gitignore
└── templates/
    ├── deepgram_transcribe.py        # módulo Python autocontenido + CLI
    ├── deepgramTranscribe.mjs        # módulo Node ESM + CLI
    └── ig_carousel_fetch.py          # Modo D: baja carrusel de IG → PNG numerados
```

Los templates son **standalone**: puedes usarlos directo (sin el skill, sin Claude Code) como una librería o como CLI, importándolos en cualquier proyecto.

---

## Licencia

[MIT](./LICENSE) — usa, modifica y comparte libremente.
