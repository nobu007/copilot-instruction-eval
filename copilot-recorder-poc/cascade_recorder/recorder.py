from __future__ import annotations
import json
import logging
from typing import List
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from .actions import Action
from .config import RECORDED_ACTIONS_JSON_PATH
from .browser import inject_listeners, remove_listeners

_LOG = logging.getLogger(__name__)


class Recorder:
    """Captures user interactions via injected JS and replays them."""

    def __init__(self, driver):
        self.driver = driver
        self.recorded: List[Action] = []
        self._is_recording: bool = False

    # ---------- Recording ----------
    def start(self):
        if self._is_recording:
            return
        inject_listeners(self.driver)
        self._is_recording = True
        _LOG.info("Recording started…")

    def record_feedback(self, comment: str):
        """Records a user feedback action."""
        if not self._is_recording:
            _LOG.warning("Tried to record feedback while not recording.")
            return

        action = Action.now(action_type="feedback", comment=comment)
        self.recorded.append(action)
        _LOG.info("Recorded feedback action: %s", comment)

    def stop(self):
        """Stop recording and flush actions to file."""
        if not self._is_recording:
            return
        remove_listeners(self.driver)

        # Get recorded actions directly from the browser's window.recordedActions
        try:
            js_recorded_actions = self.driver.execute_script("return window.recordedActions;")
            if js_recorded_actions:
                self.recorded = [Action(**d) for d in js_recorded_actions]
        except Exception as e:
            _LOG.error(f"Failed to retrieve recorded actions from browser: {e}", exc_info=True)

        self._dump()
        self._is_recording = False
        _LOG.info("Recording stopped. %d actions captured", len(self.recorded))

    # ---------- Persistence ----------
    def _dump(self):
        with open(RECORDED_ACTIONS_JSON_PATH, "w", encoding="utf‑8") as fh:
            json.dump([a.to_dict() for a in self.recorded], fh, indent=2, ensure_ascii=False)

    def load(self, path=RECORDED_ACTIONS_JSON_PATH):
        from pathlib import Path

        p = Path(path)
        if p.exists():
            with p.open(encoding="utf‑8") as fh:
                data = json.load(fh)
            self.recorded = [Action(**d) for d in data]

    # ---------- Playback ----------
    @staticmethod
    def _generate_selector(info: dict) -> str:
        if info.get("id"):
            return f"#{info['id']}"
        sel = info["tag"]
        if info.get("aria-label"):
            sel += f"[aria-label='{info['aria-label']}']"
        elif info.get("name"):
            sel += f"[name='{info['name']}']"
        elif info.get("className"):
            cls = info["className"].split()[0]
            sel += f".{cls}"
        return sel

    def playback(self, status_cb=lambda *a, **kw: None):
        if not self.recorded:
            self.load()
        actions = [a for a in self.recorded if a.action_type != "feedback"]
        for idx, action in enumerate(actions, start=1):
            status_cb(f"Executing {idx}/{len(actions)} → {action.action_type}")
            sel = self._generate_selector(action.target_element)
            try:
                wait = WebDriverWait(self.driver, 20)
                el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                if action.action_type == "click":
                    self.driver.execute_script("arguments[0].click();", el)
                elif action.action_type == "input":
                    el.clear()
                    el.send_keys(action.input_text)
            except TimeoutException:
                raise RuntimeError(f"Timeout locating element: {sel}")