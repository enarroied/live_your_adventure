"""
engine.py — Terminal Adventure Engine v1

Usage:
    python engine.py <story_file>

Example:
    python engine.py stories/medieval_easy_v1.json
    python engine.py stories/scifi_medium_v1.json

The engine resolves the graph automatically from the story's graph_id.
Graphs are looked up in GRAPHS_DIR (default: ./graphs/ next to this file).
Override with the ADVENTURE_GRAPHS_DIR environment variable if needed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from image import render_image
from state import GameState
from validator import validate


console = Console()

# ── Graph resolution ───────────────────────────────────────────────────────────
#
# Resolved relative to engine.py itself — not the working directory —
# so the engine works correctly regardless of where it is invoked from.
# Overridable via environment variable for non-standard setups.

GRAPHS_DIR = Path(
    os.environ.get("ADVENTURE_GRAPHS_DIR", Path(__file__).parent / "graphs")
)


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_json(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_graph(story: dict) -> tuple[dict, Path]:
    """
    Load the graph that matches story['graph_id'] from GRAPHS_DIR.
    Returns (graph_dict, graph_path).
    Exits with a clear error if the file cannot be found.
    """
    graph_id   = story.get("graph_id", "")
    graph_path = GRAPHS_DIR / f"{graph_id}.json"

    if not graph_path.exists():
        console.print(
            f"[red]Graph not found:[/red] [white]{graph_path}[/white]\n"
            f"[grey50]The story requires graph_id '[bold]{graph_id}[/bold]'. "
            f"Expected file: {graph_path}[/grey50]"
        )
        sys.exit(1)

    return load_json(graph_path), graph_path


def normalise_choices(story: dict) -> dict[tuple[str, str], str]:
    """
    Convert story choice keys to uniform (src, tgt) tuples regardless of
    whether the JSON stored them as "A,AA" strings or ["A","AA"] arrays.
    """
    normalised: dict[tuple[str, str], str] = {}
    for key, label in story.get("choices", {}).items():
        if isinstance(key, str):
            parts = key.split(",", 1)
            normalised[(parts[0].strip(), parts[1].strip())] = label
        elif isinstance(key, (list, tuple)) and len(key) == 2:
            normalised[(str(key[0]), str(key[1]))] = label
    return normalised


# ── Rendering ─────────────────────────────────────────────────────────────────

SCENE_BORDER  = "dark_orange"
ENDING_GOOD   = "gold1"
ENDING_BAD    = "grey50"
CHOICE_COLOR  = "cyan"
PROMPT_COLOR  = "bright_white"


def render_scene(node_id: str, node_data: dict, choices: list[tuple[str, str]]) -> None:
    """Render a scene node: title panel, optional image, description, choices table."""

    console.print()
    console.print(Rule(style="dark_orange dim"))
    console.print()

    # Title
    console.print(
        Panel(
            Text(node_data["title"], justify="center", style="bold dark_orange"),
            border_style=SCENE_BORDER,
            padding=(0, 4),
        )
    )
    console.print()

    # Optional image
    if node_data.get("image_url"):
        render_image(
            node_data["image_url"],
            console,
            enhance=node_data.get("image_enhance", False),
        )

    # Description
    console.print(Markdown(node_data["description"]))
    console.print()

    # Choices table
    if choices:
        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style=f"bold {CHOICE_COLOR}",
            border_style="grey42",
            padding=(0, 2),
        )
        table.add_column("#", style=f"bold {CHOICE_COLOR}", width=3, justify="right")
        table.add_column("What do you do?", style="white")

        for idx, (_, label) in enumerate(choices, start=1):
            table.add_row(str(idx), label)

        console.print(table)


def render_ending(node_id: str, node_data: dict) -> None:
    """Render an ending node with appropriate styling."""

    console.print()
    console.print(Rule(style="grey42 dim"))
    console.print()

    is_good = "GOOD" in node_id or "ESCAPE" in node_id
    border  = ENDING_GOOD if is_good else ENDING_BAD
    emoji   = "✦" if is_good else "✧"

    title_text = Text(
        f"{emoji}  {node_data['title']}  {emoji}",
        justify="center",
        style=f"bold {border}",
    )

    console.print(Panel(title_text, border_style=border, padding=(0, 4)))
    console.print()

    # Optional image
    if node_data.get("image_url"):
        render_image(
            node_data["image_url"],
            console,
            enhance=node_data.get("image_enhance", False),
        )

    console.print(Markdown(node_data["description"]))
    console.print()
    console.print(Rule(style=f"{border} dim"))
    console.print()


def render_errors(errors: list[str]) -> None:
    error_text = "\n".join(f"  • {e}" for e in errors)
    console.print(
        Panel(
            f"[bold red]Validation failed — {len(errors)} error(s):[/bold red]\n\n"
            f"[red]{error_text}[/red]",
            border_style="red",
            title="[bold red]Engine Error[/bold red]",
            padding=(1, 2),
        )
    )


def render_welcome(graph: dict, story: dict) -> None:
    console.print()
    console.print(Rule("[bold dark_orange]⚔  Terminal Adventure Engine  ⚔[/bold dark_orange]", style="dark_orange"))
    console.print()

    meta = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    meta.add_column("key",   style="grey58")
    meta.add_column("value", style="white")
    meta.add_row("Graph",   graph["graph_id"])
    meta.add_row("Story",   story.get("nodes", {}).get("A", {}).get("title", "—"))
    console.print(meta)


# ── Gameplay loop ──────────────────────────────────────────────────────────────

def get_player_choice(num_choices: int) -> int:
    """
    Prompt the player until they enter a valid integer in [1, num_choices].
    Returns a 0-based index.
    """
    while True:
        raw = Prompt.ask(
            f"\n[{PROMPT_COLOR}]Your choice[/{PROMPT_COLOR}]",
            console=console,
        )
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= num_choices:
                return choice - 1
        console.print(
            f"[red]Please enter a number between 1 and {num_choices}.[/red]"
        )


def run(graph: dict, story: dict) -> None:
    """Main gameplay loop."""

    choices_map = normalise_choices(story)
    edges       = graph["edges"]
    nodes_graph = graph["nodes"]
    nodes_story = story["nodes"]

    state = GameState(current_node=graph["start_node"])

    while True:
        node_id   = state.current_node
        node_type = nodes_graph[node_id]["type"]
        node_data = nodes_story[node_id]

        # ── Ending ─────────────────────────────────────────────────────────
        if node_type == "ending":
            render_ending(node_id, node_data)
            break

        # ── Scene ──────────────────────────────────────────────────────────
        targets = edges.get(node_id, [])
        choices = [(tgt, choices_map[(node_id, tgt)]) for tgt in targets]

        render_scene(node_id, node_data, choices)

        idx = get_player_choice(len(choices))
        next_node, _ = choices[idx]

        state.visit(next_node)


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        console.print(
            "[red]Usage:[/red] python engine.py [white]<story_file>[/white]\n"
            "[grey50]Example: python engine.py stories/medieval_easy_v1.json[/grey50]"
        )
        sys.exit(1)

    story_path = Path(sys.argv[1])

    if not story_path.exists():
        console.print(f"[red]Story file not found:[/red] [white]{story_path}[/white]")
        sys.exit(1)

    story = load_json(story_path)
    graph, graph_path = resolve_graph(story)

    render_welcome(graph, story)

    errors = validate(graph, story)
    if errors:
        render_errors(errors)
        sys.exit(1)

    console.print("[green]✓ Validation passed. Starting game...[/green]")

    try:
        run(graph, story)
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[grey50]Game interrupted. Farewell, traveller.[/grey50]\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
