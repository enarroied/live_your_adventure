# Live Your Adventure

A text adventure game engine that plays interactive stories from YAML files.

## Installation

```bash
pip install -e .
```

## Usage

Run the engine with a story file:

```bash
python adventure.py stories/your_story.yaml
```

Or select from available stories interactively:

```bash
python adventure.py
```

## Creating Stories

Stories are defined in YAML files with the following structure:

```yaml
title: "Your Story Title"
start_scene: intro

ascii_art:
  intro_art: |
    _____
    |   |
    |___|

scenes:
  intro:
    text: "Your story begins..."
    choices:
      - text: "Go left"
        next: left_path
      - text: "Go right"
        next: right_path

  left_path:
    text: "You went left..."
    art: intro_art
    choices:
      - text: "Continue"
        next: ending
      - text: "Go back"
        next: intro

  right_path:
    text: "You went right..."

  ending:
    text: "The end."
```

### Scene Fields

- `text` (string or list): Story text to display
- `art` (string): Key from `ascii_art` to display
- `choices` (list): Available options, each with:
  - `text`: Choice description
  - `next`: ID of the next scene

### ASCII Art

Add ASCII art in the `ascii_art` section as either multiline strings or lists of lines.

## License

MIT License - see [LICENSE](LICENSE) file.

---

Built with [opencode](https://opencode.ai)
