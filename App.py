"""
HR Import GUI — the primary front end (and what the packaged desktop builds run).

A tkinter window where you drag-and-drop one or more HR CSV files, pick the
tenant(s) to split out from a multi-select dropdown, and click PROCESS FILES.
Each file is backed up to an "Original Files" folder beside it, then transformed
in place via HRImport.run(); results and any errors are reported in the LOG panel.
Tenant options come from tenants.json (Tenants.load_tenants); the CLI equivalent
is Main.py.
"""
import os
import re
import sys
import shutil
import Tenants
import HRImport
import tkinter as tk
from tkinter import messagebox
from tkinter import Menubutton
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
        status_label.config(text=f"{current_text}\nError occurred while processing file: {filename_short} - {type(e).__name__}: {e}")

def handle_drop(event):
    # Raw data
    raw_data = event.data

    # Split the raw data into individual file paths
    file_paths = root.tk.splitlist(raw_data)

    # Clear listbox and display droped file paths
    file_listbox.delete(0, tk.END)
    for path in file_paths:
        file_listbox.insert(tk.END, path)

def on_process_button_click():
    # Map the selected human-readable names back to their full tenant dicts, since
    # HRImport expects dicts with business_unit_description/tenant_id, not name strings.
    selected_names = tenant_dropdown.get_selected()
    selected_tenants = [t for t in tenants if t["tenant_name"] in selected_names]
    for file in file_listbox.get(0, tk.END):
        print(f"Processing file: {file}")
        process(file, selected_tenants)
        print(f"Finished processing file: {file}")

def on_clear_button_click():
    status_label.config(text="Ready to process files.")

HELP_TEXT = (
    "How to use HR Import\n"
    "\n"
    "1.  Add your files\n"
    "     Drag and drop one or more HR files into the box at the top, "
    "or drop a whole selection at once. The full path of each file "
    "appears in the list.\n"
    "\n"
    "2.  Choose your tenant(s)\n"
    "     Open the SELECT TENANT(S) menu and tick every tenant the data "
    "should be imported for. You can select more than one.\n"
    "\n"
    "3.  Process\n"
    "     Click PROCESS FILES. Each file is processed in turn for the "
    "tenants you chose.\n"
    "\n"
    "What happens to my files\n"
    "     Before any changes are made, an untouched copy of each file is "
    "saved to an \"Original Files\" folder next to it, so the source data "
    "is always preserved.\n"
    "\n"
    "Reading the LOG\n"
    "     The LOG shows the result of each file: success, a warning if the "
    "backup failed, or an error with details. Use CLEAR LOG to reset it "
    "before a new run.\n"
    "\n"
    "Tip: if a file errors, check that it is the right format and isn't "
    "open in another program, then try again."
)

def on_help_button_click():
    win = tk.Toplevel(root)
    win.title("Help — HR Import")
    win.geometry("440x520")
    win.minsize(360, 400)
    win.configure(bg=MID_PURPLE)
    win.transient(root)

    header = tk.Frame(win, bg=DEEP_PURPLE, height=70)
    header.pack(fill=tk.X)
    header.pack_propagate(False)

    help_canvas = tk.Canvas(header, bg=DEEP_PURPLE, highlightthickness=0, bd=0)
    help_canvas.pack(fill=tk.BOTH, expand=True)
    help_font = tkfont.Font(family="Helvetica", size=28, weight="bold")
    attach_marquee(help_canvas, "HELP      ", font=help_font)

    help_label = tk.Label(
        win,
        text=HELP_TEXT,
        bg=BLUSH,
        fg=DEEP_PURPLE,
        font=FONT_BODY,
        justify="left",
        anchor="nw",
        wraplength=400,
        padx=16,
        pady=14,
    )
    help_label.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    close_button = ttk.Button(win, text="CLOSE", command=win.destroy,
                              style="ClearLog.TButton")
    close_button.pack(pady=(0, 16))

    win.focus_set()

class MultiSelectDropdown(tk.Menubutton):
    def __init__(self, parent, label, options, **kwargs):
        super().__init__(parent, text=label, relief="raised", **kwargs)

        # Create dropdwon menu
        self.menu = tk.Menu(self, tearoff=0)
        self["menu"] = self.menu

        # "None"/"All" entries at the top clear or select every tenant.
        self.menu.add_command(label="None", command=self._clear_selection)
        self.menu.add_command(label="All", command=self._select_all)
        self.menu.add_separator()

        # Track selected items
        self.choices = {}
        for option in options:
            self.choices[option] = tk.BooleanVar(value=False)
            self.menu.add_checkbutton(
                label=option,
                variable=self.choices[option],
                command=self._update_button_text
            )
        self.default_label = label

    def _clear_selection(self):
        for var in self.choices.values():
            var.set(False)
        self._update_button_text()

    def _select_all(self):
        for var in self.choices.values():
            var.set(True)
        self._update_button_text()

    def _update_button_text(self):
        selected = self.get_selected()
        if not selected:
            self.config(text=self.default_label)
        else:
            self.config(text=", ".join(selected))

    def get_selected(self):
        return [option for option, var in self.choices.items() if var.get()]

# --- Bold teal / blue / purple theme ---------------------------------------
CORAL = "#ff6b6b"          # coral        (255,107,107)
BLUSH = "#ffc2c2"          # blush        (255,194,194)
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
    background=CORAL,
    foreground=DEEP_PURPLE,
    font=FONT_BUTTON,
    borderwidth=0,
    focusthickness=0,
    padding=(20, 14),
)
style.map(
    "Process.TButton",
    background=[("active", BLUSH), ("pressed", BLUSH)],
)
style.configure(
    "ClearLog.TButton",
    background=CORAL,
    foreground=DEEP_PURPLE,
    font=FONT_BODY,
    borderwidth=0,
    focusthickness=0,
    padding=(8, 2),
)
style.map(
    "ClearLog.TButton",
    background=[("active", BLUSH), ("pressed", BLUSH)],
)
style.configure(
    "Tenant.TCombobox",
    fieldbackground=BLUSH,
    background=BLUE,
    foreground=DEEP_PURPLE,
    arrowcolor=DEEP_PURPLE,
    bordercolor=CORAL,
    padding=8,
)

# --- Header block: big block-letter title on deep purple (~15% of window) ---
header = tk.Frame(root, bg=DEEP_PURPLE, height=90)
header.pack(fill=tk.X)
header.pack_propagate(False)  # keep the fixed/managed height instead of shrinking to the label

# Scrolling marquee: "HR IMPORT" repeated across the banner, sliding right->left.
title_canvas = tk.Canvas(header, bg=DEEP_PURPLE, highlightthickness=0, bd=0)
title_canvas.pack(fill=tk.BOTH, expand=True)

title_font = tkfont.Font(family="Helvetica", size=36, weight="bold")
MARQUEE_SPEED = 2                  # pixels shifted per frame
MARQUEE_DELAY = 30                 # ms between frames (~33 fps)

def attach_marquee(canvas, unit, font=None):
    """Turn ``canvas`` into a seamless right->left scrolling banner of ``unit``.

    Two text "bands" are laid end to end; whichever scrolls fully off the left
    edge is recycled to just past the rightmost band, giving an endless loop.
    Each canvas keeps its own state, so the same effect can drive several
    banners (e.g. the title and the help window) independently.
    """
    if font is None:
        font = title_font
    state = {"items": [], "band_w": 0}

    def build(event=None):
        canvas.delete("marquee")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:               # not laid out yet
            return
        # Repeat the unit until one band is at least as wide as the canvas, so a
        # single band can cover the whole banner with no gaps.
        text = unit
        while font.measure(text) < w:
            text += unit
        band_w = font.measure(text)
        y = h // 2
        items = []
        for i in range(2):
            items.append(canvas.create_text(
                i * band_w, y, text=text, fill=CORAL, font=font,
                anchor="w", tags="marquee",
            ))
        state["items"] = items
        state["band_w"] = band_w

    def animate():
        band_w = state["band_w"]
        items = state["items"]
        if band_w and items:
            for item in items:
                canvas.move(item, -MARQUEE_SPEED, 0)
            for item in items:
                x, y = canvas.coords(item)
                if x <= -band_w:
                    rightmost = max(canvas.coords(o)[0] for o in items)
                    canvas.coords(item, rightmost + band_w, y)
        canvas.after(MARQUEE_DELAY, animate)

    canvas.bind("<Configure>", build)
    # Build once geometry is known, then start the scrolling animation.
    canvas.after(100, build)
    canvas.after(150, animate)

# Scrolling marquee: "HR IMPORT" repeated across the banner, sliding right->left.
attach_marquee(title_canvas, "HR IMPORT      ")

def _resize_header(event):
    # Keep the purple header at ~15% of the window height as it resizes.
    if event.widget is root:
        header.configure(height=max(70, int(event.height * 0.15)))

root.bind("<Configure>", _resize_header)

# --- Body on medium-purple background --------------------------------------
body = tk.Frame(root, bg=MID_PURPLE, padx=24, pady=18)
body.pack(fill=tk.BOTH, expand=True)

# Create a label
label_row = tk.Frame(body, bg=MID_PURPLE)
label_row.pack(fill=tk.X, pady=(0, 6))

label = tk.Label(label_row, text="DRAG / DROP FILES HERE",
                 bg=MID_PURPLE, fg=CORAL, font=FONT_HEADING)
label.pack(side=tk.LEFT, anchor="w")

help_button = ttk.Button(label_row, text="HELP",
                         command=on_help_button_click, style="ClearLog.TButton")
help_button.pack(side=tk.RIGHT)

# Add a text label widget
file_listbox = tk.Listbox(
    body,
    width=40,
    height=5,
    bg=BLUSH,
    fg=DEEP_PURPLE,
    font=FONT_BODY,
    relief="flat",
    highlightthickness=2,
    highlightbackground=CORAL,
    highlightcolor=CORAL,
    selectbackground=DEEP_PURPLE,
    selectforeground=CORAL,
    activestyle="none",
)
file_listbox.pack(pady=(0, 16), fill=tk.BOTH, expand=True)

# Register listbox component as a drop target for files
file_listbox.drop_target_register(DND_FILES)

# Bind the drop event to the handler
file_listbox.dnd_bind('<<Drop>>', handle_drop)

# Options for dropdown menu (tenants)
tenants = Tenants.load_tenants()
options = [tenant["tenant_name"] for tenant in sorted(tenants, key=lambda t: t["tenant_name"])]

# Create a dropdown menu for tenant selection
tenant_dropdown = MultiSelectDropdown(body, "SELECT TENANT(S)", options,
                                      bg=MID_PURPLE, fg=CORAL, font=FONT_HEADING)
tenant_dropdown.pack(fill=tk.X, pady=(0, 16))

# Create a button to process the files
process_button = ttk.Button(body, text="PROCESS FILES",
                            command=on_process_button_click, style="Process.TButton")
process_button.pack(fill=tk.X, pady=(0, 16))

# Log box describing ready to run/completion status
log_header = tk.Frame(body, bg=MID_PURPLE)
log_header.pack(fill=tk.X, pady=(0, 6))

log_label = tk.Label(log_header, text="LOG",
                     bg=MID_PURPLE, fg=CORAL, font=FONT_HEADING)
log_label.pack(side=tk.LEFT, anchor="w")

clear_status_button = ttk.Button(log_header, text="CLEAR LOG",
                                 command=on_clear_button_click, style="ClearLog.TButton")
clear_status_button.pack(side=tk.RIGHT)

status_label = tk.Label(
    body,
    text="Ready to process files.",
    bg=BLUSH,
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

# Start application main event loop
root.mainloop()
