from __future__ import annotations
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import logging
from pathlib import Path

from .recorder import Recorder
from .config import AGENT_VERSION, RECORDING_FILE

_LOG = logging.getLogger(__name__)


class RecorderGUI:
    """Tkinter façade layer – depends on Recorder only."""

    def __init__(self, root: tk.Tk, recorder: Recorder, auto_test: bool = False):
        self.root = root
        self.recorder = recorder

        self.status_var = tk.StringVar(value="Connecting browser…")
        self._build_widgets()

        if auto_test:
            _LOG.info("RecorderGUI initialized. Scheduling automatic test.")
            self.root.after(1000, self._run_auto_test_step1)

    # ---------- Widget layout ----------
    def _build_widgets(self):
        self.root.title(f"Recorder POC v{AGENT_VERSION}")
        self.root.geometry("600x500")
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Controls
        ctrl = ttk.Frame(frame)
        ctrl.pack(fill=tk.X, pady=5)
        self.btn_start = ttk.Button(ctrl, text="Start Recording", command=self._on_start)
        self.btn_stop = ttk.Button(ctrl, text="Stop Recording", command=self._on_stop, state=tk.DISABLED)
        self.btn_play = ttk.Button(ctrl, text="Start Playback", command=self._on_play, state=tk.DISABLED)
        self.btn_send_enter = ttk.Button(ctrl, text="Send Enter Key", command=self._on_send_enter, state=tk.DISABLED)
        for b in (self.btn_start, self.btn_stop, self.btn_play, self.btn_send_enter):
            b.pack(side=tk.LEFT, padx=5)

        # Feedback
        feedback_frame = ttk.Frame(frame)
        feedback_frame.pack(fill=tk.X, pady=5, side=tk.BOTTOM)
        self.feedback_entry = ttk.Entry(feedback_frame)
        self.feedback_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.btn_feedback = ttk.Button(feedback_frame, text="Add Feedback", command=self._on_feedback, state=tk.DISABLED)
        self.btn_feedback.pack(side=tk.LEFT)

        # Status
        ttk.Label(frame, text="Status:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status_var, wraplength=580).pack(anchor="w", fill=tk.X, pady=5)

        # Log area
        ttk.Label(frame, text="Recorded Actions:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.log_txt = scrolledtext.ScrolledText(frame, height=15, state="disabled", wrap=tk.WORD)
        self.log_txt.pack(fill=tk.BOTH, expand=True, pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)



    # ---------- UI Callbacks ----------
    def _on_start(self):
        self.recorder.recorded.clear()
        self.log_txt.config(state="normal"); self.log_txt.delete("1.0", tk.END); self.log_txt.config(state="disabled")
        self.recorder.start()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_feedback.config(state=tk.NORMAL)
        self.btn_send_enter.config(state=tk.NORMAL)
        self.status_var.set("Recording…")
        threading.Thread(target=self._drain_queue, daemon=True).start()

    def _on_stop(self):
        self.recorder.stop()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_feedback.config(state=tk.DISABLED)
        self.btn_send_enter.config(state=tk.DISABLED)
        if self.recorder.recorded:
            self.btn_play.config(state=tk.NORMAL)
        self.status_var.set(f"Saved → {RECORDING_FILE}")

    def _on_play(self):
        self.btn_play.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        self.status_var.set("Starting playback…")
        t = threading.Thread(target=self._playback_thread, daemon=True)
        t.start()

    def _on_send_enter(self):
        _LOG.info("GUI action: Sending Enter key.")
        # Run in a separate thread to avoid blocking the GUI
        threading.Thread(target=self._send_enter_key_thread, daemon=True).start()

    def _send_enter_key_thread(self):
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys
            ActionChains(self.recorder.driver).send_keys(Keys.ENTER).perform()
            _LOG.info("Enter key sent successfully via GUI.")
        except Exception as e:
            _LOG.error(f"Failed to send Enter key from GUI: {e}")
            # Optionally, show an error to the user
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send Enter key: {e}"))

    def _on_feedback(self):
        comment = self.feedback_entry.get()
        if not comment:
            return
        if not self.recorder._is_recording:
            messagebox.showwarning("Not Recording", "Please start recording before adding feedback.")
            return

        self.recorder.record_feedback(comment)
        self.feedback_entry.delete(0, tk.END)

    def _playback_thread(self):
        try:
            self.recorder.playback(status_cb=self.status_var.set)
            self.status_var.set("Playback complete ✓")
        except Exception as err:
            messagebox.showerror("Playback error", str(err))
            self.status_var.set("Playback failed ✗")
        finally:
            self.btn_play.config(state=tk.NORMAL); self.btn_start.config(state=tk.NORMAL)

    def _drain_queue(self):
        while self.recorder._is_recording:
            self.root.after(100, self._flush_log)
            if not self.recorder._is_recording:
                break

    def _flush_log(self):
        while not self.recorder.action_queue.empty():
            act = self.recorder.action_queue.get()
            if act["action_type"] == "feedback":
                msg = f"FEEDBACK: {act['comment']}\n"
            else:
                tag = act["target_element"].get("tag", "?")
                eid = act["target_element"].get("id", "")
                msg = f"{act['action_type'].upper()}: {tag}#{eid}\n"
            self.log_txt.config(state="normal"); self.log_txt.insert(tk.END, msg); self.log_txt.see(tk.END); self.log_txt.config(state="disabled")

    def _on_close(self):
        """Custom close handler to ensure data is saved without blocking the UI."""
        
        # Immediately destroy the window to give the user instant feedback.
        if self.root.winfo_exists():
            self.root.destroy()

        # Perform the potentially slow I/O operation in a separate thread.
        def _save_and_exit():
            if self.recorder._is_recording:
                _LOG.info("Recording is active. Stopping and saving in background before exit.")
                self.recorder.stop() # This handles saving the file
            _LOG.info("Background cleanup finished.")

        threading.Thread(target=_save_and_exit, daemon=True).start()

    # ---------- Automatic Test Sequence ----------
    def _run_auto_test_step1(self):
        _LOG.info("[AutoTest] Step 1: Starting recording...")
        self._on_start()
        self.root.after(2000, self._run_auto_test_step2)

    def _run_auto_test_step2(self):
        _LOG.info("[AutoTest] Step 2: Sending Enter key...")
        self._on_send_enter()
        self.root.after(2000, self._run_auto_test_step3)

    def _run_auto_test_step3(self):
        _LOG.info("[AutoTest] Step 3: Stopping recording...")
        self._on_stop()
        self.root.after(1000, self._run_auto_test_step4)

    def _run_auto_test_step4(self):
        _LOG.info("[AutoTest] Step 4: Closing application...")
        self._on_close()
