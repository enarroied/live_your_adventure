import sys
import os
from engine import play


def get_story_path():
    """Validate input and return path to selected story file."""
    if len(sys.argv) > 1:
        story_path = sys.argv[1]
    else:
        story_path = select_interactive_story()

    validate_story_path(story_path)
    return story_path


def get_stories_directory():
    """Return the stories directory path."""
    return "stories"


def list_story_files(stories_dir):
    """Return list of YAML story files in directory."""
    return [f for f in os.listdir(stories_dir) if f.endswith((".yaml", ".yml"))]


def select_interactive_story():
    """Prompt user to select a story interactively."""
    stories_dir = get_stories_directory()

    if not os.path.exists(stories_dir):
        print(f"Error: '{stories_dir}' directory not found!")
        sys.exit(1)

    story_files = list_story_files(stories_dir)

    if not story_files:
        print(f"No story files found in '{stories_dir}'!")
        sys.exit(1)

    print("Available stories:")
    for i, f in enumerate(sorted(story_files), 1):
        print(f"  {i}. {f}")

    while True:
        try:
            choice = int(input("\nSelect a story: "))
            if 1 <= choice <= len(story_files):
                return os.path.join(stories_dir, sorted(story_files)[choice - 1])
            print("Invalid choice.")
        except ValueError:
            print("Please enter a number.")


def validate_story_path(story_path):
    """Validate that the story file exists."""
    if not os.path.exists(story_path):
        print(f"Error: '{story_path}' not found!")
        sys.exit(1)


def main():
    story_path = get_story_path()
    play(story_path)


if __name__ == "__main__":
    main()
