/**
 * Transcribe audio with Deepgram (pre-recorded / batch API).
 *
 * Standalone ES module — no project deps beyond `@deepgram/sdk` (v5+).
 * Optional: `yt-dlp` on PATH enables transcribing URLs (Instagram reels,
 * YouTube, TikTok, X/Twitter videos, etc.) — audio is downloaded first.
 *
 *   npm install @deepgram/sdk
 *   brew install yt-dlp           # only for URL inputs
 *   export DEEPGRAM_API_KEY=...   # or put it in a local .env
 *
 *   # as a CLI — files or URLs (auto-detected)
 *   node deepgramTranscribe.mjs audio.m4a
 *   node deepgramTranscribe.mjs a.mp3 b.wav --language en --diarize --out md
 *   node deepgramTranscribe.mjs "https://www.instagram.com/reel/..."
 *   node deepgramTranscribe.mjs "https://youtu.be/..." --language auto --out -
 *
 *   # as a library
 *   import { transcribe } from "./deepgramTranscribe.mjs";
 *   const { text, confidence, language } = await transcribe("audio.m4a");
 */

import { readFileSync, writeFileSync, existsSync, mkdtempSync, rmSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import os from "node:os";
import process from "node:process";

const API_KEY_ENV = "DEEPGRAM_API_KEY";
const DEFAULT_MODEL = "nova-3";
const DEFAULT_LANGUAGE = "multi"; // nova-3 multilingual; better than "es" for Spanish. Override with --language es|en|auto
const DEFAULT_TIMEOUT = 600; // seconds to await the API (large files)
const DEFAULT_RETRIES = 2; // SDK-native retries on retryable failures

/** Transcribe a local audio file -> { text, confidence, language }. */
export async function transcribe(
  audioPath,
  {
    model = DEFAULT_MODEL,
    language = DEFAULT_LANGUAGE,
    smartFormat = true,
    diarize = false,
    timeout = DEFAULT_TIMEOUT,
    maxRetries = DEFAULT_RETRIES,
    apiKey,
  } = {},
) {
  if (!existsSync(audioPath)) throw new Error(`Audio file not found: ${audioPath}`);

  const key = apiKey || loadApiKey();
  if (!key) {
    throw new Error(`Missing Deepgram API key. Set ${API_KEY_ENV} in your environment or a local .env file.`);
  }

  let DeepgramClient;
  try {
    ({ DeepgramClient } = await import("@deepgram/sdk"));
  } catch {
    throw new Error("The @deepgram/sdk package is not installed. Install it with: npm install @deepgram/sdk");
  }

  const client = new DeepgramClient({ apiKey: key });
  const options = { model, smart_format: smartFormat };
  if (language) options.language = language;
  if (diarize) options.diarize = true;
  // Final `requestOptions` arg (fern convention) handles timeout/retries natively.
  const requestOptions = { timeoutInSeconds: timeout, maxRetries };

  let response;
  try {
    response = await client.listen.v1.media.transcribeFile(readFileSync(audioPath), options, requestOptions);
  } catch (err) {
    throw new Error(
      `Deepgram transcription failed (model '${model}'). ` +
        "Check the API key is valid, you have remaining credit, and the file is a supported audio format. " +
        `Original error: ${err?.message || err}`,
    );
  }

  return parseResponse(response, language);
}

function parseResponse(response, fallbackLanguage) {
  const channel = response?.results?.channels?.[0];
  const alt = channel?.alternatives?.[0];
  const text = (alt?.transcript || "").trim();
  if (!text) throw new Error("Deepgram produced an empty transcript (or an unexpected response structure).");
  return {
    text,
    confidence: alt?.confidence ?? null,
    language: channel?.detected_language || fallbackLanguage || "und",
  };
}

function loadApiKey() {
  const fromEnv = (process.env[API_KEY_ENV] || "").trim();
  if (fromEnv) return fromEnv;
  const envFile = path.join(process.cwd(), ".env");
  if (existsSync(envFile)) {
    for (const line of readFileSync(envFile, "utf8").split("\n")) {
      const t = line.trim();
      if (t.startsWith(`${API_KEY_ENV}=`)) return t.slice(API_KEY_ENV.length + 1).trim().replace(/^["']|["']$/g, "");
    }
  }
  return "";
}

// --------------------------------------------------------------------------- //
// URL support (yt-dlp)
// --------------------------------------------------------------------------- //
function isUrl(arg) {
  return arg.startsWith("http://") || arg.startsWith("https://");
}

function downloadAudio(url, destDir) {
  const check = spawnSync("yt-dlp", ["--version"], { stdio: "ignore" });
  if (check.error || check.status !== 0) {
    throw new Error("yt-dlp not found. Install with: brew install yt-dlp  (or: pipx install yt-dlp)");
  }
  // Use `-f bestaudio/best` so yt-dlp gives us the source's native audio (m4a,
  // webm, mp4, …) without re-encoding — Deepgram accepts all of these, so we
  // avoid the ffmpeg dependency for the typical case.
  const outTemplate = path.join(destDir, "%(id)s.%(ext)s");
  const args = [
    "-f", "bestaudio/best",
    "--no-playlist",
    "--quiet", "--no-warnings",
    "-o", outTemplate,
    url,
  ];
  const res = spawnSync("yt-dlp", args, { encoding: "utf8" });
  if (res.status !== 0) {
    const stderr = (res.stderr || "").trim();
    const lowered = stderr.toLowerCase();
    if (lowered.includes("ffmpeg") || lowered.includes("ffprobe")) {
      throw new Error(
        "yt-dlp needs ffmpeg for this specific URL (separate audio+video streams to merge). " +
          "Install it with: brew install ffmpeg  (Linux: apt install ffmpeg / pacman -S ffmpeg)\n" +
          `yt-dlp stderr: ${stderr.slice(0, 600)}`,
      );
    }
    throw new Error(
      "yt-dlp failed to download the URL. The reel/video may be private, age-gated, or removed.\n" +
        `yt-dlp stderr: ${stderr.slice(0, 600)}`,
    );
  }
  const files = readdirSync(destDir);
  if (files.length === 0) throw new Error("yt-dlp finished but produced no audio file — unexpected.");
  const audio = path.join(destDir, files[0]);
  const stem = files[0].replace(/\.[^.]+$/, "");
  return { audio, stem };
}

function renderMarkdown(name, source, r) {
  const conf = typeof r.confidence === "number" ? r.confidence.toFixed(2) : "n/a";
  return `# ${name}\n\n- **Fuente:** ${source}\n- **Modelo:** Deepgram\n- **Idioma:** ${r.language}\n- **Confidence:** ${conf}\n\n---\n\n${r.text}\n`;
}

// --------------------------------------------------------------------------- //
// CLI
// --------------------------------------------------------------------------- //
async function processOne(arg, opts) {
  let label = arg;
  let tmpDir = null;
  try {
    let audioPath, outBase, source;
    if (isUrl(arg)) {
      tmpDir = mkdtempSync(path.join(os.tmpdir(), "dg_"));
      const { audio, stem } = downloadAudio(arg, tmpDir);
      audioPath = audio;
      source = arg;
      outBase = path.join(process.cwd(), stem);
      label = path.basename(audio);
    } else {
      audioPath = arg;
      source = path.basename(arg);
      outBase = arg.replace(/\.[^.]+$/, "");
      label = path.basename(arg);
    }
    const r = await transcribe(audioPath, opts);
    const conf = typeof r.confidence === "number" ? r.confidence.toFixed(2) : "n/a";
    if (opts.out === "-") {
      console.log(`\n=== ${source} (${r.language}, confidence ${conf}) ===`);
      console.log(r.text);
    } else {
      const outPath = outBase + "." + opts.out;
      writeFileSync(
        outPath,
        opts.out === "md" ? renderMarkdown(path.basename(outBase), source, r) : r.text + "\n",
        "utf8",
      );
      console.log(`✓ ${source} → ${path.basename(outPath)}  (${r.language}, confidence ${conf})`);
    }
    return 0;
  } catch (err) {
    console.error(`✗ ${label}: ${err?.message || err}`);
    return 1;
  } finally {
    if (tmpDir) rmSync(tmpDir, { recursive: true, force: true });
  }
}

async function main(argv) {
  const files = [];
  let model = DEFAULT_MODEL;
  let language = DEFAULT_LANGUAGE;
  let smartFormat = true;
  let diarize = false;
  let timeout = DEFAULT_TIMEOUT;
  let maxRetries = DEFAULT_RETRIES;
  let out = "txt"; // txt | md | -

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--model") model = argv[++i];
    else if (a === "--language") language = argv[++i];
    else if (a === "--no-smart-format") smartFormat = false;
    else if (a === "--diarize") diarize = true;
    else if (a === "--timeout") timeout = Number(argv[++i]);
    else if (a === "--retries") maxRetries = Number(argv[++i]);
    else if (a === "--out") out = argv[++i];
    else files.push(a);
  }
  if (files.length === 0) {
    console.error(
      "Usage: node deepgramTranscribe.mjs <audio-or-url...> [--model nova-3] " +
        "[--language multi|es|en|auto] [--diarize] [--timeout 600] [--retries 2] [--out txt|md|-]",
    );
    return 2;
  }
  const lang = language.toLowerCase() === "auto" ? null : language;
  const opts = { model, language: lang, smartFormat, diarize, timeout, maxRetries, out };

  let exitCode = 0;
  for (const arg of files) {
    exitCode |= await processOne(arg, opts);
  }
  return exitCode;
}

// Run as CLI only when invoked directly (not when imported).
if (import.meta.url === `file://${process.argv[1]}`) {
  process.exit(await main(process.argv.slice(2)));
}
