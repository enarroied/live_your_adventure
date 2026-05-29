"""
image.py — Optional image rendering for story nodes.

Supports:
  - http:// and https:// URLs  (downloaded via requests)
  - file:// URIs               (e.g. file:///home/user/photo.jpg)
  - bare filesystem paths      (e.g. /home/user/photo.jpg or ./img/castle.png)

Image display is entirely best-effort:
  - Network errors, missing files, bad formats → silent skip + log warning
  - Missing libraries (rich-pixels, Pillow) → silent skip + log warning
  - Gameplay is never interrupted by image failures

Quality settings
  - LANCZOS resampling is always used (much cleaner than nearest-neighbour)
  - Contrast boost is applied when the node sets "image_enhance": true
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

from rich.console import Console

logger = logging.getLogger(__name__)

IMAGE_WIDTH       = 80    # terminal columns
IMAGE_HEIGHT      = 40    # half-block rows
ENHANCE_CONTRAST  = 1.6   # multiplier when image_enhance is true
ENHANCE_SHARPNESS = 1.4   # subtle sharpness lift for photos


def render_image(url: str, console: Console, enhance: bool = False) -> None:
    """
    Render *url* as pixel art to *console*.

    Parameters
    ----------
    url:     http/https URL, file:// URI, or a plain filesystem path.
    console: Rich Console instance.
    enhance: If True, apply contrast + sharpness boost (good for photos).
    """
    try:
        _render(url, console, enhance)
    except Exception as exc:          # noqa: BLE001
        logger.warning("Image could not be displayed (%s): %s", url, exc)


def _render(url: str, console: Console, enhance: bool) -> None:
    """Inner render — may raise freely; all exceptions caught by caller."""

    try:
        from PIL import Image, ImageEnhance
        from rich_pixels import Pixels
    except ImportError as exc:
        logger.warning("Image rendering unavailable — missing library: %s", exc)
        return

    image = _load_image(url)

    # ── Resize with LANCZOS for clean downscaling ──────────────────────────
    image = image.convert("RGB")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        image.thumbnail((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)

    # ── Optional photo enhancement ─────────────────────────────────────────
    if enhance:
        image = ImageEnhance.Contrast(image).enhance(ENHANCE_CONTRAST)
        image = ImageEnhance.Sharpness(image).enhance(ENHANCE_SHARPNESS)

    pixels = Pixels.from_image(image)
    console.print(pixels)
    console.print()


def _load_image(url: str):
    """Return a PIL Image from a URL, file:// URI, or filesystem path."""
    from PIL import Image

    # ── Local file (file:// URI or bare path) ─────────────────────────────
    if url.startswith("file://"):
        path = Path(url[7:])          # strip "file://"
        return Image.open(path)

    if not url.startswith("http://") and not url.startswith("https://"):
        # Treat as a plain filesystem path
        return Image.open(Path(url))

    # ── Remote URL ────────────────────────────────────────────────────────
    import requests
    from io import BytesIO

    headers = {"User-Agent": "TerminalAdventureEngine/1.0"}
    response = requests.get(url, timeout=8, stream=True, headers=headers)
    response.raise_for_status()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return Image.open(BytesIO(response.content))
