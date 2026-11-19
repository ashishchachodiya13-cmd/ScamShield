import json
from pathlib import Path
from typing import Dict, Any, Optional

from app.schemas import ActionItem


class ActionsManager:
    """Manages predefined safety action checklists (do's, don'ts, reporting channels)."""

    def __init__(self, actions_path: Optional[Path] = None):
        if actions_path is None:
            actions_path = Path(__file__).resolve().parent.parent.parent / "data" / "actions.json"
        
        self.actions_path = Path(actions_path)
        self.data: Dict[str, Any] = self._load_actions()

    def _load_actions(self) -> Dict[str, Any]:
        if not self.actions_path.exists():
            raise FileNotFoundError(f"Actions file not found at: {self.actions_path}")
        with open(self.actions_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_actions(self, category_id: str, language: str = "en") -> ActionItem:
        """
        Retrieves predefined safety actions for the given category and language.
        Always returns verified, static safety guidance (never LLM-generated).
        """
        lang = "hi" if language == "hi" else "en"
        
        # Check category-specific actions
        category_actions = self.data.get("categories", {}).get(category_id, {}).get(lang)
        if not category_actions:
            # Fallback to general actions
            category_actions = self.data.get("general", {}).get(lang, {})

        return ActionItem(
            dos=category_actions.get("dos", []),
            donts=category_actions.get("donts", []),
            official_channels=category_actions.get("official_channels", [])
        )
