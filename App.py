import os
import re
import sys
import shutil
import Tenants
import HRImport
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import font as tkfont
from tkinterdnd2 import DND_FILES, TkinterDnD

def normalize_input_path(raw: str) -> str:
    """
    Clean a file path pasted or drag-and-dropped into the prompt, cross-platform.

    File explorers and terminals add noise that differs by OS:
    - macOS/Linux terminals backslash-escape spaces and special chars (``My\\ File``),
      where the backslash is an escape character, NOT a path separator.
    - Windows uses the backslash as its path separator, so it must be preserved.
    - Both may wrap the path in quotes or prepend stray ``&`` characters.

    Backslash handling is therefore platform-specific: on POSIX we unescape
    ``\\`` sequences; on Windows we leave backslashes intact.
    """
    path = raw.strip().strip('&').strip('"').strip("'").strip()
    if os.sep != "\\":
        # POSIX: backslashes are shell escapes (e.g. "\ " for a space) — unescape them.
        path = re.sub(r'\\(.)', r'\1', path)
    return os.path.normpath(path)

def process(filename: str, use_tenants: list[dict[str, str]]) -> None:
    filename = normalize_input_path(filename)

    filename_short = os.path.basename(filename)

    current_text = status_label.cget("text")

    # Backup original files to a separate directory to preserve unmodified data for auditing or reprocessing if needed
    try:
        original_files_dir = os.path.join(os.path.dirname(filename), "Original Files")
        os.makedirs(original_files_dir, exist_ok=True)
        shutil.copy(filename, os.path.join(original_files_dir, "Original " + os.path.basename(filename)))
    except FileNotFoundError as e:
        status_label.config(text=f"{current_text}\nWarning: Failed to backup original file '{filename_short}' - {e}")

    # Instantiate HR import handler for this file and execute transformations with selected tenants
    try:
        hr_import: HRImport.HRImport = HRImport.HRImport(filename)
        hr_import.run(use_tenants)
        status_label.config(text=f"{current_text}\nSuccessfully processed file: {filename_short}")
    except Exception as e:
        status_label.config(text=f"{current_text}\nError occurred while processing file: {filename_short} - {e}")

def handle_drop(event):
    # Raw data
    raw_data = event.data

    # Split the raw data into individual file paths
    file_paths = root.tk.splitlist(raw_data)

    # Clear listbox and display droped file paths
    file_listbox.delete(0, tk.END)
    for path in file_paths:
        file_listbox.insert(tk.END, path)

def on_button_click():
    for file in file_listbox.get(0, tk.END):
        print(f"Processing file: {file}")
        process(file, selected_tenants)
        print(f"Finished processing file: {file}")

def on_select(event):
    selected_name = combo.get()
    # Map the selected human-readable name back to its full tenant dict, since
    # HRImport expects dicts with business_unit_description/tenant_id, not name strings.
    selected_tenant = next((t for t in tenants if t["tenant_name"] == selected_name), None)
    if selected_tenant is not None and selected_tenant not in selected_tenants:
        selected_tenants.append(selected_tenant)

# --- Bold teal / blue / purple theme ---------------------------------------
AQUA = "#0cead9"          # bright aqua  (12,234,217)
CYAN = "#3acadf"          # cyan         (58,202,223)
BLUE = "#729efd"          # periwinkle   (114,158,253)
MID_PURPLE = "#8a64d6"    # medium purple(138,100,214)
DEEP_PURPLE = "#5c3a92"   # deep purple  (92,58,146)

FONT_TITLE = ("Helvetica", 36, "bold")
FONT_HEADING = ("Helvetica", 13, "bold")
FONT_BODY = ("Helvetica", 11)
FONT_BUTTON = ("Helvetica", 14, "bold")

# Create the main application window
root = TkinterDnD.Tk()
root.title("HR Import GUI")
root.geometry("520x620")
root.minsize(460, 540)
root.configure(bg=MID_PURPLE)

# ttk styling (clam honors custom colors across platforms)
style = ttk.Style(root)
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "Process.TButton",
    background=AQUA,
    foreground=DEEP_PURPLE,
    font=FONT_BUTTON,
    borderwidth=0,
    focusthickness=0,
    padding=(20, 14),
)
style.map(
    "Process.TButton",
    background=[("active", CYAN), ("pressed", CYAN)],
)
style.configure(
    "Tenant.TCombobox",
    fieldbackground=CYAN,
    background=BLUE,
    foreground=DEEP_PURPLE,
    arrowcolor=DEEP_PURPLE,
    bordercolor=AQUA,
    padding=8,
)

# List to hold selected tenants
selected_tenants = []

# --- Header block: big block-letter title on deep purple (~15% of window) ---
header = tk.Frame(root, bg=DEEP_PURPLE, height=90)
header.pack(fill=tk.X)
header.pack_propagate(False)  # keep the fixed/managed height instead of shrinking to the label

# Scrolling marquee: "HR IMPORT" repeated across the banner, sliding right->left.
title_canvas = tk.Canvas(header, bg=DEEP_PURPLE, highlightthickness=0, bd=0)
title_canvas.pack(fill=tk.BOTH, expand=True)

title_font = tkfont.Font(family="Helvetica", size=36, weight="bold")
MARQUEE_UNIT = "HR IMPORT      "   # trailing spaces give breathing room between repeats
MARQUEE_SPEED = 2                  # pixels shifted per frame
MARQUEE_DELAY = 30                 # ms between frames (~33 fps)

# Holds the two text "bands" and their measured width; two copies laid end to
# end let us recycle a band the moment it leaves the screen for a seamless loop.
marquee = {"items": [], "band_w": 0}

def _build_marquee(event=None):
    title_canvas.delete("marquee")
    w = title_canvas.winfo_width()
    h = title_canvas.winfo_height()
    if w <= 1:               # not laid out yet
        return
    # Repeat the unit until one band is at least as wide as the canvas, so a
    # single band can cover the whole banner with no gaps.
    text = MARQUEE_UNIT
    while title_font.measure(text) < w:
        text += MARQUEE_UNIT
    band_w = title_font.measure(text)
    y = h // 2
    items = []
    for i in range(2):
        items.append(title_canvas.create_text(
            i * band_w, y, text=text, fill=AQUA, font=title_font,
            anchor="w", tags="marquee",
        ))
    marquee["items"] = items
    marquee["band_w"] = band_w

def _animate_marquee():
    band_w = marquee["band_w"]
    items = marquee["items"]
    if band_w and items:
        for item in items:
            title_canvas.move(item, -MARQUEE_SPEED, 0)
        # Recycle any band that has fully scrolled off the left edge by
        # placing it immediately after the rightmost band.
        for item in items:
            x, y = title_canvas.coords(item)
            if x <= -band_w:
                rightmost = max(title_canvas.coords(o)[0] for o in items)
                title_canvas.coords(item, rightmost + band_w, y)
    root.after(MARQUEE_DELAY, _animate_marquee)

title_canvas.bind("<Configure>", _build_marquee)

def _resize_header(event):
    # Keep the purple header at ~15% of the window height as it resizes.
    if event.widget is root:
        header.configure(height=max(70, int(event.height * 0.15)))

root.bind("<Configure>", _resize_header)

# --- Body on medium-purple background --------------------------------------
body = tk.Frame(root, bg=MID_PURPLE, padx=24, pady=18)
body.pack(fill=tk.BOTH, expand=True)

# Create a label
label = tk.Label(body, text="DRAG / DROP FILES HERE",
                 bg=MID_PURPLE, fg=AQUA, font=FONT_HEADING)
label.pack(anchor="w", pady=(0, 6))

# Add a text label widget
file_listbox = tk.Listbox(
    body,
    width=40,
    height=5,
    bg=CYAN,
    fg=DEEP_PURPLE,
    font=FONT_BODY,
    relief="flat",
    highlightthickness=2,
    highlightbackground=AQUA,
    highlightcolor=AQUA,
    selectbackground=DEEP_PURPLE,
    selectforeground=AQUA,
    activestyle="none",
)
file_listbox.pack(pady=(0, 16), fill=tk.BOTH, expand=True)

# Register listbox component as a drop target for files
file_listbox.drop_target_register(DND_FILES)

# Bind the drop event to the handler
file_listbox.dnd_bind('<<Drop>>', handle_drop)

# Options for dropdown menu (tenants)
tenants = Tenants.load_tenants()
options = [tenant["tenant_name"] for tenant in tenants]

# Create a dropdown menu for tenant selection
combo_label = tk.Label(body, text="TENANT",
                       bg=MID_PURPLE, fg=AQUA, font=FONT_HEADING)
combo_label.pack(anchor="w", pady=(0, 6))

combo = ttk.Combobox(body, values=options, font=FONT_BODY, style="Tenant.TCombobox")
combo.pack(fill=tk.X, pady=(0, 16))
combo.bind("<<ComboboxSelected>>", on_select)

# Create a button to process the files
process_button = ttk.Button(body, text="PROCESS FILES",
                            command=on_button_click, style="Process.TButton",
                            cursor="hand2")
process_button.pack(fill=tk.X, pady=(0, 16))

# Log box describing ready to run/completion status
log_label = tk.Label(body, text="LOG",
                     bg=MID_PURPLE, fg=AQUA, font=FONT_HEADING)
log_label.pack(anchor="w", pady=(0, 6))

status_label = tk.Label(
    body,
    text="Ready to process files.",
    bg=CYAN,
    fg=DEEP_PURPLE,
    font=FONT_BODY,
    justify="left",
    anchor="nw",
    wraplength=440,
    relief="flat",
    bd=0,
    padx=12,
    pady=10,
)
status_label.pack(fill=tk.BOTH, expand=True)

# Build the banner once geometry is known, then start the scrolling animation.
root.after(100, _build_marquee)
root.after(150, _animate_marquee)

# Start application main event loop
root.mainloop()
