#!/usr/bin/env python3
"""Baja las imágenes de un post/carrusel de Instagram y las deja como PNG numerados.

Uso:
    python3 ig_carousel_fetch.py "https://www.instagram.com/p/XXXX/" [--out DIR] [--browser chrome]

Por qué existe: yt-dlp solo baja *video* de Instagram — ignora las imágenes de un
carrusel ("No video formats found"). gallery-dl sí baja las N imágenes. Este helper
envuelve gallery-dl, ordena las slides y las convierte a PNG para que Claude las lea
por VISIÓN (tool Read) y cure/extraiga el contenido.

Imprime, una por línea, la ruta absoluta de cada PNG en orden de slide. Ese es el
contrato: quien lo invoca lee esas rutas con la herramienta de visión.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Extensiones de imagen que gallery-dl puede dejar para un post de IG.
IMG_EXTS = {".webp", ".jpg", ".jpeg", ".png"}


def _fail(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def _gallery_dl_cmd() -> list[str]:
    """gallery-dl como binario en PATH, o `python3 -m gallery_dl` si se instaló como módulo."""
    if shutil.which("gallery-dl"):
        return ["gallery-dl"]
    probe = subprocess.run(
        [sys.executable, "-m", "gallery_dl", "--version"],
        capture_output=True, text=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "gallery_dl"]
    _fail(
        "gallery-dl no está instalado. Instálalo con:\n"
        "  python3 -m pip install --user gallery-dl   (o: pipx install gallery-dl)"
    )
    return []  # inalcanzable


def download(url: str, out_dir: Path, browser: str | None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = _gallery_dl_cmd() + ["-D", str(out_dir)]
    if browser:
        cmd += ["--cookies-from-browser", browser]
    cmd.append(url)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        hint = ""
        low = (proc.stderr + proc.stdout).lower()
        if "login" in low or "empty" in low or "403" in low or "challenge" in low:
            hint = (
                "\nInstagram pidió autenticación. Reintenta con cookies del navegador "
                "donde tengas sesión iniciada: --browser chrome (o safari/firefox)."
            )
        _fail(f"gallery-dl falló:\n{proc.stderr.strip()}{hint}")

    imgs = sorted(p for p in out_dir.iterdir() if p.suffix.lower() in IMG_EXTS)
    if not imgs:
        _fail("gallery-dl no dejó imágenes. ¿El post es accesible con tu sesión?")
    return imgs


def to_png(imgs: list[Path], out_dir: Path) -> list[Path]:
    """Convierte/renombra cada imagen a slide_NN.png. Usa sips (macOS) o Pillow."""
    pngs: list[Path] = []
    have_sips = shutil.which("sips") is not None
    try:
        from PIL import Image  # noqa: F401
        have_pil = True
    except Exception:
        have_pil = False

    for i, src in enumerate(imgs, 1):
        dst = out_dir / f"slide_{i:02d}.png"
        if src.suffix.lower() == ".png":
            if src != dst:
                shutil.copyfile(src, dst)
        elif have_sips:
            subprocess.run(
                ["sips", "-s", "format", "png", str(src), "--out", str(dst)],
                capture_output=True,
            )
        elif have_pil:
            from PIL import Image
            Image.open(src).convert("RGB").save(dst, "PNG")
        else:
            _fail("No hay forma de convertir a PNG: falta `sips` (macOS) y `Pillow` (pip install Pillow).")
        pngs.append(dst)
    return pngs


def main() -> None:
    ap = argparse.ArgumentParser(description="Baja un carrusel de Instagram como PNG numerados.")
    ap.add_argument("url", help="URL del post de Instagram (https://www.instagram.com/p/XXXX/)")
    ap.add_argument("--out", default=None, help="Directorio de salida (default: ./ig_<shortcode>)")
    ap.add_argument("--browser", default="chrome",
                    help="Navegador para --cookies-from-browser (default: chrome; usa '' para no usar cookies)")
    args = ap.parse_args()

    shortcode = args.url.rstrip("/").split("/")[-1].split("?")[0] or "post"
    out_dir = Path(args.out) if args.out else Path.cwd() / f"ig_{shortcode}"

    browser = args.browser or None
    imgs = download(args.url, out_dir, browser)
    pngs = to_png(imgs, out_dir)

    print(f"# {len(pngs)} slides descargadas en {out_dir}", file=sys.stderr)
    for p in pngs:
        print(p.resolve())


if __name__ == "__main__":
    main()
