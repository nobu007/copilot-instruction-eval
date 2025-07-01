# gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from datetime import datetime

AGENT_VERSION = "1.2.0-POC"

def add_feedback_handler(shared_state, entry_widget):
    comment = entry_widget.get()
    if not comment:
        return
    if not shared_state.is_recording:
        messagebox.showwarning("Warning", "You can only add feedback during a recording session.")
        return

    action = {
        'action_type': 'feedback',
        'comment': comment,
        'timestamp': datetime.now().isoformat()
    }
    shared_state.action_queue.put(action)
    entry_widget.delete(0, tk.END)

def create_gui(shared_state, handlers):
    root = tk.Tk()
    root.title(f"Recorder POC v{AGENT_VERSION}")
    root.geometry("600x500")
    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    controls_frame = ttk.Frame(main_frame)
    controls_frame.pack(fill=tk.X, pady=5)

    feedback_frame = ttk.Frame(main_frame)
    feedback_frame.pack(fill=tk.X, pady=5)
    
    ttk.Label(feedback_frame, text="Feedback:").pack(side=tk.LEFT, padx=(0, 5))
    feedback_entry = ttk.Entry(feedback_frame, width=50)
    feedback_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
    
    feedback_button = ttk.Button(feedback_frame, text="Add Feedback", command=lambda: add_feedback_handler(shared_state, feedback_entry))
    feedback_button.pack(side=tk.LEFT, padx=5)
    
    b_start = ttk.Button(controls_frame, text="Start Recording", command=handlers["start"])
    b_start.pack(side=tk.LEFT, padx=5)
    b_stop = ttk.Button(controls_frame, text="Stop Recording", command=handlers["stop"], state=tk.DISABLED)
    b_stop.pack(side=tk.LEFT, padx=5)
    b_play = ttk.Button(controls_frame, text="Start Playback", command=handlers["play"], state=tk.DISABLED)
    b_play.pack(side=tk.LEFT, padx=5)
    shared_state.buttons = {"start": b_start, "stop": b_stop, "play": b_play, "feedback": feedback_button}

    status_var = tk.StringVar(value="Initializing...")
    ttk.Label(main_frame, text="Status:", font=("Segoe UI", 10, "bold")).pack(anchor='w', pady=(10, 0))
    ttk.Label(main_frame, textvariable=status_var, wraplength=580).pack(anchor='w', fill=tk.X, pady=5)
    shared_state.status_var = status_var

    ttk.Label(main_frame, text="Recorded Actions:", font=("Segoe UI", 10, "bold")).pack(anchor='w', pady=(10, 0))
    log_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD, state='disabled')
    log_text.pack(fill=tk.BOTH, expand=True, pady=5)
    shared_state.log_text_widget = log_text

    def on_close():
        if messagebox.askyesno("Confirm Exit", "This will close the browser. Are you sure?"):
            shared_state.stop_event.set()
            root.after(100, root.destroy)
    root.protocol("WM_DELETE_WINDOW", on_close)
    return root

def process_action_queue(shared_state):
    while not shared_state.action_queue.empty():
        action = shared_state.action_queue.get()
        shared_state.recorded_actions.append(action)
        log_widget = shared_state.log_text_widget
        log_widget.config(state='normal')
        if action.get('action_type') == 'error':
            log_widget.insert(tk.END, f"ERROR: {action.get('message')}\n", 'error')
            shared_state.status_var.set(f"Error: {action.get('message')}")
        elif action['action_type'] == 'feedback':
            log_widget.insert(tk.END, f"FEEDBACK: {action['comment']}\n", 'feedback')
        else:
            target = action.get('target_element', {})
            log_widget.insert(tk.END, f"{action.get('action_type', 'UNKNOWN').upper()}: {target.get('tag', 'N/A')}#{target.get('id', 'N/A')}\n")
        log_widget.see(tk.END)
        log_widget.config(state='disabled')

    if not shared_state.stop_event.is_set() and shared_state.log_text_widget.winfo_exists():
        shared_state.log_text_widget.winfo_toplevel().after(100, lambda: process_action_queue(shared_state))