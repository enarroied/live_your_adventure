from dataclasses import dataclass, field


@dataclass
class GameState:
    """
    Carries all runtime state for an active game session.

    v1 uses only `current_node`.
    All other fields are dormant but present for future extensions
    (state system, conditional choices, inventory, random events).
    """

    current_node: str

    # --- Future-ready slots (unused in v1) ---
    history: list[str] = field(default_factory=list)
    inventory: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
    health: int = 10

    def visit(self, node_id: str) -> None:
        """Transition to a new node, recording the move in history."""
        self.history.append(self.current_node)
        self.current_node = node_id
