from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List
import json
from pathlib import Path



@dataclass
class Action:
    action_type: str
    timestamp: str
    target_element: Dict[str, Any] | None = None
    input_text: str | None = None
    comment: str | None = None
    key_pressed: str | None = None
    url: str | None = None

    @staticmethod
    def now(action_type: str, **kwargs) -> "Action":
        return Action(action_type=action_type, timestamp=datetime.utcnow().isoformat(), **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
