"""
image.py — Image rendering for story nodes.

Tries the best available protocol in order, falls back gracefully:

  1. Kitty  — native pixel-perfect rendering via APC escape sequences.
             Detected by: $TERM == "xterm-kitty"  or  $KITTY_WINDOW_ID set.
             Supported by: Kitty.

  2. iTerm2 — native inline image via OSC 1337 escape sequence.
             Detected by: $TERM_PROGRAM == "iTerm.app"  or  $WEZTERM_PANE set.
             Supported by: iTerm2, WezTerm, Konsole, mintty.

  3. rich-pixels — half-block Unicode fallback, works everywhere Rich runs.

All failures are caught and logged; gameplay is never interrupted.

Node fields:
    image_url     (str)  — http/https URL, file:// URI, or bare filesystem path.
    image_enhance (bool) — boost contrast + sharpness before rendering (good for photos).
"""

from __future__ import annotations

import base64
import logging
import os
import sys
import warnings
from enum import Enum, auto
from io import BytesIO
from pathlib import Path

from PIL import Image as PILImage
from rich.console import Console

logger = logging.getLogger(__name__)

# ── Tuning ─────────────────────────────────────────────────────────────────────

# rich-pixels fallback dimensions (half-block characters)
PIXEL_WIDTH  = 120
PIXEL_HEIGHT = 60

# iTerm2 / Kitty display width (character cells; height is auto-calculated)
NATIVE_WIDTH = "80"   # character cells — matches PIXEL_WIDTH for visual consistency

ENHANCE_CONTRAST  = 1.6
ENHANCE_SHARPNESS = 1.4


# ── Protocol detection ─────────────────────────────────────────────────────────

class Protocol(Enum):
    KITTY   = auto()
    ITERM2  = auto()
    PIXELS  = auto()   # rich-pixels Unicode fallback


def detect_protocol() -> Protocol:
    """
    Detect the best image protocol available in the current terminal.
    Result is cached after the first call.
    """
    term         = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")

    if term == "xterm-kitty" or os.environ.get("KITTY_WINDOW_ID"):
        return Protocol.KITTY

    if term_program == "iTerm.app" or os.environ.get("WEZTERM_PANE"):
        return Protocol.ITERM2

    return Protocol.PIXELS


# Cache detection so we only probe once per session
_PROTOCOL: Protocol | None = None


def _get_protocol() -> Protocol:
    global _PROTOCOL
    if _PROTOCOL is None:
        _PROTOCOL = detect_protocol()
        logger.debug("Image protocol selected: %s", _PROTOCOL.name)
    return _PROTOCOL


# ── Public API ─────────────────────────────────────────────────────────────────

def render_image(url: str, console: Console, enhance: bool = False) -> None:
    """
    Render *url* using the best available protocol.
    Fails silently on any error.
    """
    try:
        _render(url, console, enhance)
    except Exception as exc:          # noqa: BLE001
        logger.warning("Image could not be displayed (%s): %s", url, exc)


# ── Internal render dispatcher ─────────────────────────────────────────────────

def _render(url: str, console: Console, enhance: bool) -> None:
    protocol = _get_protocol()
    image    = _load_and_prepare(url, enhance)

    if protocol == Protocol.KITTY:
        _render_kitty(image, console)
    elif protocol == Protocol.ITERM2:
        _render_iterm2(image, console)
    else:
        _render_pixels(image, console)


# ── Image loading + preprocessing ─────────────────────────────────────────────

def _load_and_prepare(url: str, enhance: bool):
    """Load image from any source, convert to RGB, apply optional enhancement."""

    image = _load_image(url).convert("RGB")

    # LANCZOS resampling — always better than nearest-neighbour at small sizes
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        image.thumbnail((PIXEL_WIDTH * 4, PIXEL_HEIGHT * 4), PILImage.LANCZOS)

    if enhance:
        from PIL import ImageEnhance
        image = ImageEnhance.Contrast(image).enhance(ENHANCE_CONTRAST)
        image = ImageEnhance.Sharpness(image).enhance(ENHANCE_SHARPNESS)

    return image


def _load_image(url: str):
    """Return a PIL Image from an http/https URL, file:// URI, or filesystem path."""

    if url.startswith("file://"):
        return PILImage.open(Path(url[7:]))

    if not url.startswith(("http://", "https://")):
        return PILImage.open(Path(url))

    import requests
    headers  = {"User-Agent": "TerminalAdventureEngine/1.0"}
    response = requests.get(url, timeout=8, stream=True, headers=headers)
    response.raise_for_status()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return PILImage.open(BytesIO(response.content))


def _image_to_png_bytes(image) -> bytes:
    """Encode a PIL image as PNG bytes."""
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# ── Protocol renderers ─────────────────────────────────────────────────────────

def _render_kitty(image, console: Console) -> None:
    """
    Kitty Graphics Protocol (APC escape sequences).
    Transmits image as base64-encoded PNG in 4096-byte chunks.
    Reference: https://sw.kovidgoyal.net/kitty/graphics-protocol/
    """
    display = image.copy()
    width_px = int(NATIVE_WIDTH) * 8
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        display.thumbnail((width_px, 9999), PILImage.LANCZOS)

    data   = base64.standard_b64encode(_image_to_png_bytes(display))
    stdout = sys.stdout.buffer if hasattr(sys.stdout, "buffer") else sys.stdout

    # Send in 4096-byte chunks as required by the protocol
    chunk_size = 4096
    first      = True

    while data:
        chunk, data = data[:chunk_size], data[chunk_size:]
        more = 1 if data else 0

        if first:
            # a=T  → transmit and display immediately
            # f=100 → PNG format
            # q=2  → suppress response (no terminal acknowledgement needed)
            cmd = f"a=T,f=100,q=2,m={more}"
            first = False
        else:
            cmd = f"m={more}"

        seq = b"\x1b_G" + cmd.encode("ascii") + b";" + chunk + b"\x1b\\"
        stdout.write(seq)
        stdout.flush()

    console.print()   # newline after image


def _render_iterm2(image, console: Console) -> None:
    """
    iTerm2 Inline Image Protocol (OSC 1337).
    Also supported by WezTerm, Konsole, mintty.
    Reference: https://iterm2.com/documentation-images.html
    """
    png_bytes  = _image_to_png_bytes(image)
    b64_data   = base64.b64encode(png_bytes).decode("ascii")
    size       = len(png_bytes)

    # width in character cells; height auto-calculated to preserve aspect ratio
    seq = (
        f"\x1b]1337;"
        f"File=inline=1;"
        f"size={size};"
        f"width={NATIVE_WIDTH};"
        f"preserveAspectRatio=1:"
        f"{b64_data}\a"
    )

    sys.stdout.write(seq)
    sys.stdout.flush()
    console.print()   # newline after image


def _render_pixels(image, console: Console) -> None:
    """
    rich-pixels Unicode half-block fallback.
    Works in any terminal that Rich supports.
    """
    try:
        from rich_pixels import Pixels
    except ImportError:
        logger.warning("rich-pixels not installed; image skipped.")
        return

    display = image.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        display.thumbnail((PIXEL_WIDTH, PIXEL_HEIGHT), PILImage.LANCZOS)

    console.print(Pixels.from_image(display))
    console.print()
