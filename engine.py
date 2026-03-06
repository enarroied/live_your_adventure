import os
import sys
import time
import yaml


def print_slow(text, delay=0.03):
    """Print text character by character with a delay."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_art(art):
    """Print ASCII art immediately without delay."""
    for line in art:
        print(line)


def print_choice(options):
    """Display numbered choices to the user."""
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")


def get_choice(max_option):
    """Get and validate user choice from 1 to max_option."""
    while True:
        try:
            choice = int(input("\n> "))
            if 1 <= choice <= max_option:
                return choice
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")


def load_story(yaml_path):
    """Load story data from a YAML file."""
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def get_art(story_data, art_key, story_path=None):
    """Retrieve ASCII art from file or story data by key."""
    if art_key and story_path:
        art_file = f"ascii_art/{art_key}.txt"
        story_dir = os.path.dirname(os.path.abspath(story_path))
        root_dir = os.path.dirname(story_dir)
        full_path = os.path.join(root_dir, art_file)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                return [line.rstrip("\n") for line in f]

    ascii_art = story_data.get("ascii_art", {})
    if art_key and art_key in ascii_art:
        art = ascii_art[art_key]
        if isinstance(art, list):
            return art
        elif isinstance(art, str):
            return art.split("\n")
    return None


def run_scene(scene_id, story_data, story_path):
    """Execute a scene: display art, text, choices, and return next scene ID."""
    scenes = story_data.get("scenes", {})
    scene = scenes.get(scene_id)

    if scene is None:
        print(f"Error: Scene '{scene_id}' not found!")
        return None

    print()

    art_key = scene.get("art")
    if art_key:
        art = get_art(story_data, art_key, story_path)
        if art:
            print_art(art)

    text = scene.get("text", "")
    if isinstance(text, list):
        for line in text:
            print_slow(line)
    else:
        print_slow(text)

    choices = scene.get("choices", [])

    if not choices:
        return None

    choice_texts = [c["text"] for c in choices]
    print_choice(choice_texts)

    choice = get_choice(len(choices))
    selected = choices[choice - 1]

    return selected.get("next")


def play(story_path):
    """Main game loop: load story and run scenes until end."""
    story = load_story(story_path)

    print_slow("\n" + "=" * 40)
    print_slow(f"   {story.get('title', 'Adventure')}")
    print_slow("=" * 40)

    current_scene = story.get("start_scene")

    while current_scene:
        current_scene = run_scene(current_scene, story, story_path)

    print_slow("\nTHE END")
