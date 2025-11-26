from dataclasses import dataclass
from datetime import datetime
import typing


@dataclass
class SavedState_Pseudo:
    """Pseudocode for representing a saved state"""

    dt: datetime
    realization_file: str


class StateManager_Pseudo:
    """Pseudocode for managing saved states"""

    def __init__(self):
        self.saved_states: dict[typing.Any, SavedState_Pseudo] = {}

    def add_saved_state(self, *args, **kwargs):
        pass

    def get_saved_state(self, *args, **kwargs):
        pass
