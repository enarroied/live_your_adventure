# Terminal Adventure Engine

A Python engine for running text-based adventure games in the terminal, built on [Rich](https://github.com/Textualize/rich).

Stories and game structure are kept strictly separate: a **graph template** defines the branching topology, and a **story package** provides all the narrative content. The same graph can power any number of different stories.

```
adventure/
├── engine.py                          # Core gameplay loop and rendering
├── validator.py                       # Compatibility checks
├── state.py                           # Runtime game state
├── image.py                           # Optional pixel image rendering
├── graphs/
│   ├── easy_v1.json                   # Graph template: easy difficulty
│   └── medium_v1.json                 # Graph template: medium difficulty
└── stories/
    ├── medieval_easy_v1.json          # Sir Aldric defends Ironveil
    └── scifi_medium_v1.json           # The Wreck of the Helios Drift
```

---

## Running a game

### Requirements

Python 3.10+ and the following packages:

```bash
pip install rich rich-pixels pillow requests
```

### Starting a game

Pass a story file as the only argument. The engine resolves the graph automatically.

```bash
python engine.py stories/medieval_easy_v1.json
python engine.py stories/scifi_medium_v1.json
```

### Playing

At each scene, numbered choices are displayed in a table. Type the number and press Enter.

```
     #     What do you do?
 ─────────────────────────────────────────────────
     1     Ride north into the Whispering Forest
     2     Descend into the old undercroft
     3     Climb the battlements and take stock

Your choice: _
```

The game ends when you reach an ending node. Press `Ctrl+C` at any time to quit.

### Graph location

By default, graphs are loaded from the `graphs/` folder next to `engine.py`, regardless of your working directory. To use a different location:

```bash
ADVENTURE_GRAPHS_DIR=/my/graphs python engine.py stories/my_story.json
```

---

## Extending the engine: writing new content

The engine is designed so that new stories can be added without touching any Python code. You only need to create two JSON files: a graph template and a story package.

### Step 1 — Choose or create a graph template

A graph template defines the structure of the adventure: nodes, connections, and endings. It contains no story text.

You can reuse an existing graph (`easy_v1`, `medium_v1`) or write a new one.

```json
{
    "graph_id": "easy_v1",
    "start_node": "A",
    "nodes": {
        "A":            { "type": "scene" },
        "AA":           { "type": "scene" },
        "AB":           { "type": "scene" },
        "GOOD_ENDING":  { "type": "ending" },
        "BAD_ENDING":   { "type": "ending" }
    },
    "edges": {
        "A":  ["AA", "AB"],
        "AA": ["GOOD_ENDING"],
        "AB": ["BAD_ENDING"]
    }
}
```

**Node types:**

| Type     | Description                                       |
|----------|---------------------------------------------------|
| `scene`  | A playable node. Must have at least one outgoing edge. |
| `ending` | A terminal node. Must have no outgoing edges. Game ends here. |

**Rules the validator enforces:**

- The start node must be `"A"`.
- Every `scene` node must have at least one outgoing edge.
- Every `ending` node must have no outgoing edges.
- Every node must be reachable from `A`.
- Every path must eventually reach an ending node.
- All edge targets must exist as nodes.

Save graph files in `graphs/` as `<graph_id>.json`.

---

### Step 2 — Write the story package

A story package provides narrative content for every node in the graph. It declares which graph it is compatible with via `graph_id`.

```json
{
    "graph_id": "easy_v1",
    "nodes": {
        "A": {
            "title": "The Crossroads",
            "description": "You stand at a fork in the road."
        },
        "AA": {
            "title": "The High Road",
            "description": "A steep path winds upward into the mountains."
        },
        "AB": {
            "title": "The Low Road",
            "description": "A muddy track descends into the valley."
        },
        "GOOD_ENDING": {
            "title": "Safe at Last",
            "description": "You arrive home before nightfall."
        },
        "BAD_ENDING": {
            "title": "Lost in the Valley",
            "description": "The fog rolls in and you lose the path."
        }
    },
    "choices": {
        "A,AA": "Take the high road",
        "A,AB": "Take the low road",
        "AA,GOOD_ENDING": "Press on to the summit",
        "AB,BAD_ENDING":  "Wade into the fog"
    }
}
```

**Node fields:**

| Field           | Required | Description                                      |
|-----------------|----------|--------------------------------------------------|
| `title`         | Yes      | Displayed in the scene panel header.             |
| `description`   | Yes      | Main narrative text. Supports Markdown.          |
| `image_url`     | No       | Image to display above the description.          |
| `image_enhance` | No       | Set to `true` to boost contrast and sharpness.  |

**Choice keys** use the format `"SOURCE,TARGET"` — for example `"A,AA"` labels the edge from node `A` to node `AA`. Every edge in the graph must have a corresponding choice label.

Save story files in `stories/` as `<anything>_<graph_id>.json` (the naming convention is just for clarity — the engine matches by `graph_id` content, not filename).

---

### Step 3 — Add images (optional)

Images are displayed above the node description using [rich-pixels](https://github.com/darrenburns/rich-pixels), rendered at 80×40 characters.

**Supported sources:**

```json
"image_url": "https://example.com/scene.jpg"
"image_url": "/home/user/photos/forest.jpg"
"image_url": "file:///home/user/photos/forest.jpg"
```

**Photo enhancement** — recommended for personal photos, which tend to lose contrast at block-pixel scale:

```json
"image_url": "/home/user/photo.jpg",
"image_enhance": true
```

This applies a contrast boost (×1.6) and sharpness lift (×1.4) before rendering.

---

### Step 4 — Run and validate

Run your story directly. The validator runs automatically before gameplay begins and reports all errors at once:

```bash
python engine.py stories/my_story.json
```

Example validation output:

```
╭─ Engine Error ────────────────────────────────────────╮
│ Validation failed — 2 error(s):                       │
│                                                       │
│   • Graph node 'B2' is missing from the story package │
│   • Edge 'AA' → 'GOOD_ENDING' has no choice label    │
╰───────────────────────────────────────────────────────╯
```

Fix the reported errors and rerun. A clean start looks like:

```
✓ Validation passed. Starting game...
```

---

## Bundled graphs

### `easy_v1`

```
A
├─ AA ── B1 ── GOOD_ENDING
├─ AB ── B2 ── BAD_ENDING
└─ AC ── B3 ── GOOD_ENDING
```

Depth 3. Three opening choices, each leading to a single decision that resolves the story. Two good endings, one bad. Forgiving — the majority of paths succeed.

### `medium_v1`

```
A
├─ AA ── BA ── ESCAPE_ENDING
│    └── BB ── SACRIFICE_ENDING
├─ AB ── BB ── SACRIFICE_ENDING  (converges)
│    └── BC ── TRAPPED_ENDING
└─ AC ── BC ── TRAPPED_ENDING    (converges)
     └── BD ── ESCAPE_ENDING
```

Depth 3, but with path convergence. Nodes `BB` and `BC` are reachable from two different opening branches, making outcomes harder to predict. Two escape endings, one ambiguous ending, one bad ending.

---

## Architecture notes

### Why structure and story are separated

The graph defines *topology* — branching factor, depth, ending positions. The story defines *meaning* — setting, characters, consequence. Keeping them separate means:

- The same graph can host multiple stories at no cost.
- Stories can be written and edited without any knowledge of Python.
- Difficulty is a property of graph topology, not narrative.

### Validation happens before gameplay

The validator runs ten checks before the first scene is rendered. All errors are collected and reported together so you see the full picture at once, not one error at a time.

### Image rendering is best-effort

Image failures — broken URLs, missing files, network timeouts, unsupported formats — are caught, logged as warnings, and silently skipped. The game never crashes due to an image.

### State is future-ready

`GameState` currently tracks only `current_node` and `history`. The fields `inventory`, `flags`, and `health` are present but dormant, ready for a future version with items, conditional choices, and stat-based outcomes.

---

## Planned future features

- **State system** — inventory, health, story flags
- **Conditional choices** — edges that only appear if a flag is set or an item is held
- **Random events** — probability-weighted branching
- **Hard difficulty graph** — depth 6+, deceptive routes, multiple ending categories
- **Session save/restore** — persist `GameState` to disk between sessions
