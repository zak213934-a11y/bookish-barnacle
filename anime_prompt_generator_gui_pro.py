#!/usr/bin/env python3
"""
Professional GUI for anime_prompt_generator_plus.py (v6.5.1 compatible)

Implements:
- Left/Right split layout (controls vs output)
- Control tabs: Basics / Style / Auto-append / Data / Advanced
- Output tabs: Output / History / Favorites
- Preset bar (incl. Locked 90s OVA) + preset save/load JSON
- Data audit (Found vs Used vs Unused) + unused browser
- Auto-append extra pools with:
    - enable toggle, master probability, max tags
    - per-file sliders (scrollable)
    - search + filters (show enabled only / show nonzero only)
- Batch generation with progress + cancel (non-blocking via after())
- Keyboard shortcuts (Ctrl+Enter generate, Ctrl+Shift+C copy all, Ctrl+C copy current, Ctrl+S save)
- Status bar (data loaded counts, last action)
"""

import json
import os
import sys
import time
import tkinter as tk
from typing import List, cast
from tkinter import ttk, filedialog, messagebox

import anime_prompt_generator_plus as apg


# ---------- optional modern theming ----------
def _try_apply_modern_theme(root):
    # Try ttkbootstrap first; fall back to built-in clam.
    try:
        import ttkbootstrap as tb  # type: ignore
        style = tb.Style("darkly")
        # root is already a Tk from tb? if not, we still benefit from ttkbootstrap styles.
        return ("ttkbootstrap", style)
    except Exception:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        return ("ttk", style)


OVA_ANCHOR_TAGS = [
    "90s anime aesthetic",
    "OVA-era style",
    "vhs scanlines",
    "film grain",
    "cel shading",
    "hand-drawn look",
    "soft chromatic aberration",
]


# ---------- helpers ----------
class ScrollFrame(ttk.Frame):
    """Scrollable vertical frame."""
    def __init__(self, master, height=420):
        super().__init__(master)
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas)

        # Mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self.win, width=event.width)

    def _on_mousewheel(self, event):
        try:
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -1 * int(event.delta / 120)
            self.canvas.yview_scroll(delta, "units")
        except Exception:
            pass


class TagText(tk.Text):
    """Text widget with simple tag highlighting."""
    def __init__(self, master, **kwargs):
        super().__init__(master, wrap="word", **kwargs)
        self.tag_configure("dim", foreground="#7a7a7a")
        self.tag_configure("hi", foreground="#ffffff")
        self.tag_configure("extra", foreground="#7bdcff")
        self.configure(font=("TkDefaultFont", 10))

    def set_prompt(self, prompt: str, extra_markers=None):
        self.delete("1.0", "end")
        self.insert("1.0", prompt)
        self._apply_highlight(extra_markers or [])

    def _apply_highlight(self, extra_markers):
        # Dim anchor/boilerplate-ish tokens a bit, highlight extras if provided.
        txt = self.get("1.0", "end-1c")
        parts = [p.strip() for p in txt.split(",") if p.strip()]
        # Rebuild with tags: easiest is clear and insert chunk by chunk.
        self.delete("1.0", "end")
        for i, p in enumerate(parts):
            if i:
                self.insert("end", ", ")
            tag = "hi"
            low = p.lower()
            if low in {"masterpiece", "best quality", "high quality", "ultra detailed"}:
                tag = "dim"
            if any(m.lower() in low for m in extra_markers):
                tag = "extra"
            self.insert("end", p, (tag,))


# ---------- main app ----------
class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.master = master
        self.grid(sticky="nsew")

        master.title("Anime Prompt Generator (Pro UI v6.5.1)")
        master.minsize(1120, 680)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # State
        self.data_dir = tk.StringVar(value=apg.DATA_DIR)

        self.genre = tk.StringVar(value="random")
        self.count = tk.IntVar(value=1)
        self.seed = tk.StringVar(value="")
        self.force_1girl = tk.BooleanVar(value=False)
        self.quality = tk.StringVar(value="ultra")
        self.distance = tk.StringVar(value="random")
        self.extra_tags = tk.StringVar(value="")
        self.ova_locked = tk.BooleanVar(value=False)

        self.negative_tags = tk.StringVar(value="")
        self.lock_seed = tk.BooleanVar(value=False)
        self.increment_seed = tk.BooleanVar(value=True)

        # Auto-append (extra pools)
        self.auto_enabled = tk.BooleanVar(value=False)
        self.auto_master_prob = tk.DoubleVar(value=35.0)
        self.auto_max_tags = tk.IntVar(value=2)
        self.auto_search = tk.StringVar(value="")
        self.auto_filter_enabled_only = tk.BooleanVar(value=False)
        self.auto_filter_nonzero_only = tk.BooleanVar(value=True)

        self.per_file_vars = {}  # filename -> DoubleVar 0..100

        # History / Favorites
        self.history = []   # list of dicts
        self.favorites = [] # list of dicts
        self.current_prompt = ""

        # Batch/progress
        self._cancel_batch = False

        # UI
        self._build_preset_bar()
        self._build_split()
        self._build_status()

        self._refresh_genres()
        self._reload_data(silent=True)
        self._bind_shortcuts()

    # ---------- UI build ----------
    def _build_preset_bar(self):
        bar = ttk.Frame(self)
        bar.grid(row=0, column=0, sticky="ew", pady=(0,8))
        bar.columnconfigure(9, weight=1)

        ttk.Label(bar, text="Presets:").grid(row=0, column=0, sticky="w", padx=(0,8))

        ttk.Button(bar, text="Locked 90s OVA", command=self._preset_ova).grid(row=0, column=1, padx=4)
        ttk.Button(bar, text="Clean (non-ecchi)", command=self._preset_clean).grid(row=0, column=2, padx=4)
        ttk.Button(bar, text="Cyberpunk grit", command=self._preset_cyber).grid(row=0, column=3, padx=4)
        ttk.Button(bar, text="Soft romance", command=self._preset_romance).grid(row=0, column=4, padx=4)
        ttk.Separator(bar, orient="vertical").grid(row=0, column=5, sticky="ns", padx=10)

        ttk.Button(bar, text="Save preset…", command=self._save_preset).grid(row=0, column=6, padx=4)
        ttk.Button(bar, text="Load preset…", command=self._load_preset).grid(row=0, column=7, padx=4)
        ttk.Button(bar, text="Reset", command=self._reset_defaults).grid(row=0, column=8, padx=4)

    def _build_split(self):
        pan = ttk.Panedwindow(self, orient="horizontal")
        pan.grid(row=1, column=0, sticky="nsew")
        self.rowconfigure(1, weight=1)

        left = ttk.Frame(pan, padding=(0,0,8,0))
        right = ttk.Frame(pan, padding=(8,0,0,0))
        pan.add(left, weight=1)
        pan.add(right, weight=2)

        # Left notebook (controls)
        self.ctrl_nb = ttk.Notebook(left)
        self.ctrl_nb.pack(fill="both", expand=True)

        self.tab_basics = ttk.Frame(self.ctrl_nb, padding=10)
        self.tab_style = ttk.Frame(self.ctrl_nb, padding=10)
        self.tab_auto = ttk.Frame(self.ctrl_nb, padding=10)
        self.tab_data = ttk.Frame(self.ctrl_nb, padding=10)
        self.tab_adv = ttk.Frame(self.ctrl_nb, padding=10)

        self.ctrl_nb.add(self.tab_basics, text="Basics")
        self.ctrl_nb.add(self.tab_style, text="Style")
        self.ctrl_nb.add(self.tab_auto, text="Auto-append")
        self.ctrl_nb.add(self.tab_data, text="Data")
        self.ctrl_nb.add(self.tab_adv, text="Advanced")

        self._build_basics_tab()
        self._build_style_tab()
        self._build_auto_tab()
        self._build_data_tab()
        self._build_adv_tab()

        # Right notebook (output)
        self.out_nb = ttk.Notebook(right)
        self.out_nb.pack(fill="both", expand=True)

        self.out_output = ttk.Frame(self.out_nb, padding=10)
        self.out_history = ttk.Frame(self.out_nb, padding=10)
        self.out_favs = ttk.Frame(self.out_nb, padding=10)

        self.out_nb.add(self.out_output, text="Output")
        self.out_nb.add(self.out_history, text="History")
        self.out_nb.add(self.out_favs, text="Favorites")

        self._build_output_tab()
        self._build_history_tab()
        self._build_favorites_tab()

    def _build_status(self):
        st = ttk.Frame(self)
        st.grid(row=2, column=0, sticky="ew", pady=(8,0))
        st.columnconfigure(1, weight=1)
        self.status_left = ttk.Label(st, text="Ready")
        self.status_left.grid(row=0, column=0, sticky="w")
        self.status_right = ttk.Label(st, text="")
        self.status_right.grid(row=0, column=1, sticky="e")

    def _build_basics_tab(self):
        f = self.tab_basics
        f.columnconfigure(1, weight=1)

        # Data folder
        box = ttk.LabelFrame(f, text="Data folder", padding=10)
        box.grid(row=0, column=0, columnspan=2, sticky="ew")
        box.columnconfigure(1, weight=1)
        ttk.Label(box, text="Path").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.data_dir).grid(row=0, column=1, sticky="ew", padx=(10,10))
        ttk.Button(box, text="Browse…", command=self._browse_data).grid(row=0, column=2)
        ttk.Button(box, text="Reload", command=self._reload_data).grid(row=0, column=3, padx=(6,0))
        ttk.Button(box, text="Audit…", command=self._open_audit).grid(row=0, column=4, padx=(6,0))

        # Core settings
        core = ttk.LabelFrame(f, text="Core", padding=10)
        core.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10,0))
        for c in range(3):
            core.columnconfigure(c, weight=1)

        ttk.Label(core, text="Genre").grid(row=0, column=0, sticky="w")
        self.genre_combo = ttk.Combobox(core, textvariable=self.genre, state="readonly")
        self.genre_combo.grid(row=0, column=1, sticky="ew", padx=(10,10))
        ttk.Button(core, text="List…", command=self._open_genres).grid(row=0, column=2, sticky="e")

        ttk.Label(core, text="Count").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Spinbox(core, from_=1, to=999, textvariable=self.count, width=6).grid(row=1, column=1, sticky="w", padx=(10,0), pady=(10,0))

        ttk.Label(core, text="Seed").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Entry(core, textvariable=self.seed).grid(row=2, column=1, sticky="ew", padx=(10,10), pady=(10,0))
        seed_ops = ttk.Frame(core)
        seed_ops.grid(row=2, column=2, sticky="e", pady=(10,0))
        ttk.Checkbutton(seed_ops, text="Lock", variable=self.lock_seed).pack(side="left")
        ttk.Checkbutton(seed_ops, text="Increment", variable=self.increment_seed).pack(side="left", padx=(8,0))

        ttk.Checkbutton(core, text="Force 1girl, solo", variable=self.force_1girl).grid(row=3, column=0, columnspan=3, sticky="w", pady=(10,0))

        ttk.Label(core, text="Quality").grid(row=4, column=0, sticky="w", pady=(10,0))
        ttk.Combobox(core, textvariable=self.quality, state="readonly", values=["ultra","high","standard","artistic"]).grid(row=4, column=1, sticky="ew", padx=(10,10), pady=(10,0))

        ttk.Label(core, text="Camera distance").grid(row=5, column=0, sticky="w", pady=(10,0))
        ttk.Combobox(core, textvariable=self.distance, state="readonly",
                     values=["random","face_closeup","portrait","half_body","full_body","wide_scene"]).grid(row=5, column=1, sticky="ew", padx=(10,10), pady=(10,0))

        ttk.Checkbutton(core, text="Locked 90s OVA mode", variable=self.ova_locked, command=self._apply_ova_mode).grid(row=6, column=0, columnspan=3, sticky="w", pady=(10,0))

        # Extra tags
        ex = ttk.LabelFrame(f, text="Extra tags", padding=10)
        ex.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10,0))
        ex.columnconfigure(0, weight=1)
        ttk.Entry(ex, textvariable=self.extra_tags).grid(row=0, column=0, sticky="ew")
        ttk.Button(ex, text="Clear", command=lambda: self.extra_tags.set("")).grid(row=0, column=1, padx=(8,0))

    def _build_style_tab(self):
        f = self.tab_style
        f.columnconfigure(0, weight=1)

        # Quick style chips
        chips = ttk.LabelFrame(f, text="Quick add (click to append)", padding=10)
        chips.grid(row=0, column=0, sticky="ew")
        chips.columnconfigure(0, weight=1)

        chip_items = [
            "soft lighting", "dramatic shadows", "rim light", "neon glow",
            "night city", "sunset", "rainy alley", "warm palette", "cool palette",
            "vhs scanlines", "film grain", "cel shading",
        ]
        chip_frame = ttk.Frame(chips)
        chip_frame.grid(row=0, column=0, sticky="ew")
        for i, t in enumerate(chip_items):
            ttk.Button(chip_frame, text=t, command=lambda x=t: self._append_extra(x)).grid(row=i//3, column=i%3, padx=4, pady=4, sticky="ew")

        # Negative prompt
        neg = ttk.LabelFrame(f, text="Negative tags (optional)", padding=10)
        neg.grid(row=1, column=0, sticky="ew", pady=(10,0))
        neg.columnconfigure(0, weight=1)
        ttk.Entry(neg, textvariable=self.negative_tags).grid(row=0, column=0, sticky="ew")
        ttk.Button(neg, text="Clear", command=lambda: self.negative_tags.set("")).grid(row=0, column=1, padx=(8,0))

        ttk.Label(f, text="Tip: negative tags are not injected into the base generator; they are appended at the end as 'NEGATIVE: ...' so you can copy/paste into UIs that support it.").grid(row=2, column=0, sticky="w", pady=(10,0))

    def _build_auto_tab(self):
        f = self.tab_auto
        f.columnconfigure(0, weight=1)

        ctl = ttk.LabelFrame(f, text="Auto-append extra pools (from UNUSED .txt)", padding=10)
        ctl.grid(row=0, column=0, sticky="ew")
        ctl.columnconfigure(1, weight=1)

        ttk.Checkbutton(ctl, text="Enable auto-append", variable=self.auto_enabled, command=self._refresh_auto_file_list).grid(row=0, column=0, sticky="w")
        ttk.Label(ctl, text="Master probability").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Scale(ctl, from_=0, to=100, orient="horizontal", variable=self.auto_master_prob).grid(row=1, column=1, sticky="ew", padx=(10,0), pady=(10,0))
        ttk.Label(ctl, text="Max extra tags").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Spinbox(ctl, from_=1, to=10, textvariable=self.auto_max_tags, width=6).grid(row=2, column=1, sticky="w", padx=(10,0), pady=(10,0))

        flt = ttk.LabelFrame(f, text="Per-file controls", padding=10)
        flt.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        f.rowconfigure(1, weight=1)
        flt.columnconfigure(1, weight=1)

        ttk.Label(flt, text="Search").grid(row=0, column=0, sticky="w")
        ent = ttk.Entry(flt, textvariable=self.auto_search)
        ent.grid(row=0, column=1, sticky="ew", padx=(10,0))
        ent.bind("<KeyRelease>", lambda e: self._refresh_auto_file_list())

        opts = ttk.Frame(flt)
        opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8,0))
        ttk.Checkbutton(opts, text="Show enabled only", variable=self.auto_filter_enabled_only, command=self._refresh_auto_file_list).pack(side="left")
        ttk.Checkbutton(opts, text="Show nonzero only", variable=self.auto_filter_nonzero_only, command=self._refresh_auto_file_list).pack(side="left", padx=(10,0))
        ttk.Button(opts, text="Set all visible to 10%", command=lambda: self._set_visible_auto(10)).pack(side="right")
        ttk.Button(opts, text="Set all visible to 0%", command=lambda: self._set_visible_auto(0)).pack(side="right", padx=(8,0))

        self.auto_list_frame = ScrollFrame(flt, height=360)
        self.auto_list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10,0))

        self._refresh_auto_file_list()

    def _build_data_tab(self):
        f = self.tab_data
        f.columnconfigure(0, weight=1)

        ttk.Label(f, text="Data summary").grid(row=0, column=0, sticky="w")
        self.data_summary = ttk.Label(f, text="")
        self.data_summary.grid(row=1, column=0, sticky="w", pady=(6,10))

        tools = ttk.Frame(f)
        tools.grid(row=2, column=0, sticky="ew")
        ttk.Button(tools, text="Audit…", command=self._open_audit).pack(side="left")
        ttk.Button(tools, text="Open data folder", command=self._open_data_folder).pack(side="left", padx=(8,0))

        ttk.Separator(f).grid(row=3, column=0, sticky="ew", pady=12)

        ttk.Label(f, text="Unused files browser (read-only preview)").grid(row=4, column=0, sticky="w")
        pane = ttk.Panedwindow(f, orient="horizontal")
        pane.grid(row=5, column=0, sticky="nsew")
        f.rowconfigure(5, weight=1)

        left = ttk.Frame(pane, padding=0)
        right = ttk.Frame(pane, padding=0)
        pane.add(left, weight=1)
        pane.add(right, weight=2)

        self.unused_list = tk.Listbox(left)
        self.unused_list.pack(fill="both", expand=True)
        self.unused_list.bind("<<ListboxSelect>>", self._on_unused_select)

        self.unused_preview = tk.Text(right, wrap="word")
        self.unused_preview.pack(fill="both", expand=True)

        ttk.Button(f, text="Refresh unused list", command=self._populate_unused).grid(row=6, column=0, sticky="w", pady=(10,0))

    def _build_adv_tab(self):
        f = self.tab_adv
        f.columnconfigure(0, weight=1)

        ttk.Label(f, text="Export options").grid(row=0, column=0, sticky="w")
        exp = ttk.Frame(f)
        exp.grid(row=1, column=0, sticky="ew", pady=(8,0))
        ttk.Button(exp, text="Export History…", command=self._export_history).pack(side="left")
        ttk.Button(exp, text="Export Favorites…", command=self._export_favorites).pack(side="left", padx=(8,0))

        ttk.Separator(f).grid(row=2, column=0, sticky="ew", pady=12)

        ttk.Label(f, text="Coherence / safety").grid(row=3, column=0, sticky="w")
        ttk.Label(f, text="(Placeholder) You can add hard exclusions or max-length limits here if you want.").grid(row=4, column=0, sticky="w", pady=(8,0))

    def _build_output_tab(self):
        f = self.out_output
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        actions = ttk.Frame(f)
        actions.grid(row=0, column=0, sticky="ew")
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Generate (Ctrl+Enter)", command=self.generate).pack(side="left")
        ttk.Button(actions, text="Copy current (Ctrl+C)", command=self._copy_current).pack(side="left", padx=(8,0))
        ttk.Button(actions, text="Copy all (Ctrl+Shift+C)", command=self._copy_all).pack(side="left", padx=(8,0))
        ttk.Button(actions, text="Save… (Ctrl+S)", command=self._save_output).pack(side="left", padx=(8,0))
        ttk.Button(actions, text="★ Favorite", command=self._favorite_current).pack(side="right")

        # Progress
        prog = ttk.Frame(f)
        prog.grid(row=2, column=0, sticky="ew", pady=(8,0))
        prog.columnconfigure(0, weight=1)
        self.progbar = ttk.Progressbar(prog, mode="determinate")
        self.progbar.grid(row=0, column=0, sticky="ew")
        self.cancel_btn = ttk.Button(prog, text="Cancel", command=self._cancel)
        self.cancel_btn.grid(row=0, column=1, padx=(8,0))
        self._set_progress(0, 0)

        # Output text
        self.output_text = TagText(f, height=18)
        self.output_text.grid(row=1, column=0, sticky="nsew", pady=(10,0))

    def _build_history_tab(self):
        f = self.out_history
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="Clear history", command=self._clear_history).pack(side="left")
        ttk.Button(top, text="Export…", command=self._export_history).pack(side="left", padx=(8,0))

        self.history_list = tk.Listbox(f)
        self.history_list.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        self.history_list.bind("<<ListboxSelect>>", self._on_history_select)

    def _build_favorites_tab(self):
        f = self.out_favs
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="Remove selected", command=self._remove_favorite).pack(side="left")
        ttk.Button(top, text="Export…", command=self._export_favorites).pack(side="left", padx=(8,0))

        self.favs_list = tk.Listbox(f)
        self.favs_list.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        self.favs_list.bind("<<ListboxSelect>>", self._on_fav_select)

    # ---------- shortcuts ----------
    def _bind_shortcuts(self):
        self.master.bind("<Control-Return>", lambda e: self.generate())
        self.master.bind("<Control-c>", lambda e: self._copy_current())
        self.master.bind("<Control-Shift-C>", lambda e: self._copy_all())
        self.master.bind("<Control-s>", lambda e: self._save_output())

    # ---------- status ----------
    def _set_status(self, left="", right=""):
        if left:
            self.status_left.configure(text=left)
        if right is not None:
            self.status_right.configure(text=right)

    # ---------- data / audit ----------
    def _browse_data(self):
        d = filedialog.askdirectory(title="Select your data folder", initialdir=self.data_dir.get() or ".")
        if d:
            self.data_dir.set(d)

    def _reload_data(self, silent=False):
        d = self.data_dir.get().strip()
        if not d or not os.path.isdir(d):
            if not silent:
                messagebox.showerror("Invalid folder", "That data folder path doesn’t exist.")
            return
        try:
            apg.set_data_dir(d)
            self._refresh_genres()
            self._populate_unused()
            self._refresh_auto_file_list()
            audit = apg.data_audit()
            self.data_summary.configure(text=f"Found {audit['found_count']} .txt | Used {audit['used_count']} | Unused {audit['unused_count']}")
            self._set_status("Data loaded", f"Found {audit['found_count']} | Used {audit['used_count']} | Unused {audit['unused_count']}")
            if not silent:
                messagebox.showinfo("Reloaded", f"Reloaded data from:\n{d}")
        except Exception as e:
            if not silent:
                messagebox.showerror("Reload failed", str(e))
            self._set_status("Reload failed", str(e))

    def _open_audit(self):
        audit = apg.data_audit()
        msg = (
            f"Data folder:\n{audit['data_dir']}\n\n"
            f"Found: {audit['found_count']}\n"
            f"Used (referenced by generator): {audit['used_count']}\n"
            f"Unused (eligible for auto-append): {audit['unused_count']}\n\n"
            f"Tip: go to Data tab to preview unused files."
        )
        messagebox.showinfo("Data audit", msg)

    def _open_data_folder(self):
        d = self.data_dir.get().strip()
        if not d:
            return
        try:
            if os.name == "nt":
                os.startfile(d)
            elif sys.platform == "darwin":
                os.system(f'open "{d}"')
            else:
                os.system(f'xdg-open "{d}" >/dev/null 2>&1 &')
        except Exception:
            pass

    # ---------- genres ----------
    def _refresh_genres(self):
        genres = [g["name"] for g in apg.list_genres()]
        if "random" not in genres:
            genres = ["random"] + genres
        self.genre_combo["values"] = genres
        if self.genre.get() not in genres:
            self.genre.set("random")

    def _open_genres(self):
        # Simple selector dialog
        top = tk.Toplevel(self.master)
        top.title("Genres")
        top.geometry("520x420")

        frm = ttk.Frame(top, padding=10)
        frm.pack(fill="both", expand=True)

        cols = ("name", "is_ecchi", "mood")
        tree = ttk.Treeview(frm, columns=cols, show="headings")
        tree.heading("name", text="Genre")
        tree.heading("is_ecchi", text="Ecchi?")
        tree.heading("mood", text="Mood")
        tree.column("name", width=260, anchor="w")
        tree.column("is_ecchi", width=70, anchor="center")
        tree.column("mood", width=140, anchor="w")
        tree.pack(fill="both", expand=True)

        for row in apg.list_genres():
            tree.insert("", "end", values=(row["name"], row["is_ecchi"], row.get("mood","")))

        ttk.Label(frm, text="Double-click to select.").pack(anchor="w", pady=(8,0))

        def dbl(_):
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            if vals:
                self.genre.set(vals[0])
                top.destroy()

        tree.bind("<Double-1>", dbl)

    # ---------- unused browser ----------
    def _populate_unused(self):
        self.unused_list.delete(0, "end")
        audit = apg.data_audit()
        unused = cast(List[str], audit["unused"])
        for fn in unused:
            self.unused_list.insert("end", fn)
        self.unused_preview.delete("1.0", "end")
        self.unused_preview.insert("1.0", "Select a file to preview its contents.\n")

    def _on_unused_select(self, _evt):
        sel = self.unused_list.curselection()
        if not sel:
            return
        fn = self.unused_list.get(sel[0])
        path = os.path.join(apg.DATA_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
        except Exception as e:
            txt = f"Failed to read: {e}"
        self.unused_preview.delete("1.0", "end")
        self.unused_preview.insert("1.0", txt[:20000])

    # ---------- auto-append per-file UI ----------
    def _refresh_auto_file_list(self):
        audit = apg.data_audit()
        unused = cast(List[str], audit["unused"])

        q = self.auto_search.get().strip().lower()
        show_enabled_only = bool(self.auto_filter_enabled_only.get())
        show_nonzero_only = bool(self.auto_filter_nonzero_only.get())

        # clear
        for w in self.auto_list_frame.inner.winfo_children():
            w.destroy()

        if not unused:
            ttk.Label(self.auto_list_frame.inner, text="No unused .txt files detected.").grid(row=0, column=0, sticky="w")
            return

        ttk.Label(self.auto_list_frame.inner, text="Set a slider >0% to allow that file to contribute.").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,8))

        r = 1
        visible = 0
        for fn in unused:
            if q and q not in fn.lower():
                continue
            if fn not in self.per_file_vars:
                self.per_file_vars[fn] = tk.DoubleVar(value=0.0)
            v = float(self.per_file_vars[fn].get())
            if show_nonzero_only and v <= 0:
                continue
            if show_enabled_only and not self.auto_enabled.get():
                continue

            ttk.Label(self.auto_list_frame.inner, text=fn).grid(row=r, column=0, sticky="w", pady=2)
            s = ttk.Scale(self.auto_list_frame.inner, from_=0, to=100, orient="horizontal", variable=self.per_file_vars[fn],
                          command=lambda _x=None: None)
            s.grid(row=r, column=1, sticky="ew", padx=(10,10))
            ent = ttk.Entry(self.auto_list_frame.inner, width=5)
            ent.grid(row=r, column=2, sticky="e")

            # keep entry synced
            def _bind_entry(e, var=self.per_file_vars[fn]):
                txt = e.widget.get().strip()
                try:
                    val = float(txt)
                    var.set(max(0.0, min(100.0, val)))
                except Exception:
                    pass

            ent.insert(0, f"{v:.0f}")
            def _sync_entry(var=self.per_file_vars[fn], entry=ent):
                try:
                    entry.delete(0, "end")
                    entry.insert(0, f"{float(var.get()):.0f}")
                except Exception:
                    pass

            self.per_file_vars[fn].trace_add("write", lambda *_a, var=self.per_file_vars[fn], entry=ent: _sync_entry(var, entry))
            ent.bind("<Return>", _bind_entry)

            self.auto_list_frame.inner.columnconfigure(1, weight=1)
            r += 1
            visible += 1

        if visible == 0:
            ttk.Label(self.auto_list_frame.inner, text="No files match your filters.").grid(row=1, column=0, sticky="w")

    def _set_visible_auto(self, pct: float):
        audit = apg.data_audit()
        unused = cast(List[str], audit["unused"])
        q = self.auto_search.get().strip().lower()
        for fn in unused:
            if q and q not in fn.lower():
                continue
            if fn not in self.per_file_vars:
                self.per_file_vars[fn] = tk.DoubleVar(value=0.0)
            self.per_file_vars[fn].set(float(pct))
        self._refresh_auto_file_list()

    # ---------- generation ----------
    def _parse_seed(self):
        txt = self.seed.get().strip()
        if not txt:
            return None
        try:
            return int(txt)
        except Exception:
            raise ValueError("Seed must be an integer (or blank).")

    def _auto_tuning_obj(self) -> apg.ExtraPoolsTuning:
        audit = apg.data_audit()
        unused = cast(List[str], audit["unused"])
        per_file = {}
        for fn in unused:
            if fn in self.per_file_vars:
                per_file[fn] = float(self.per_file_vars[fn].get()) / 100.0
        return apg.ExtraPoolsTuning(
            enabled=bool(self.auto_enabled.get()),
            master_prob=float(self.auto_master_prob.get()) / 100.0,
            max_extra_tags=int(self.auto_max_tags.get()),
            per_file_prob=per_file
        )

    def _set_progress(self, cur, total):
        if total <= 0:
            self.progbar.configure(value=0, maximum=1)
            self.cancel_btn.configure(state="disabled")
            return
        self.progbar.configure(maximum=total, value=cur)
        self.cancel_btn.configure(state="normal")

    def _cancel(self):
        self._cancel_batch = True
        self._set_status("Cancelling…", "")

    def generate(self):
        # Start batch run
        try:
            n = int(self.count.get())
            if n <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid count", "Count must be a positive integer.")
            return

        try:
            seed0 = self._parse_seed()
        except ValueError as e:
            messagebox.showerror("Invalid seed", str(e))
            return

        if seed0 is None and self.lock_seed.get():
            # lock without a seed is meaningless; just ignore lock
            self.lock_seed.set(False)

        genre = self.genre.get().strip() or "random"
        extra = self.extra_tags.get().strip()
        quality = self.quality.get().strip() or "ultra"
        distance = self.distance.get().strip() or "random"
        force_1girl = bool(self.force_1girl.get())
        negative = self.negative_tags.get().strip()

        tuning = self._auto_tuning_obj()

        # Setup batch
        self._cancel_batch = False
        self._set_progress(0, n)
        t0 = time.time()

        prompts = []

        def step(i):
            if self._cancel_batch:
                self._set_progress(0, 0)
                self._set_status("Cancelled", "")
                return

            # decide seed for this prompt
            if seed0 is None:
                seed = None
            else:
                if self.lock_seed.get():
                    seed = seed0
                else:
                    seed = seed0 + i if self.increment_seed.get() else seed0

            p = apg.generate_prompt(
                genre=genre,
                seed=seed,
                extra_words=extra,
                distance_preset=distance,
                force_1girl=force_1girl,
                quality_preset=quality,
                extra_pools_tuning=tuning,
            )

            if negative:
                p = p + f" | NEGATIVE: {negative}"

            prompts.append(p)
            self._set_progress(i + 1, n)

            if i + 1 < n:
                self.master.after(1, lambda: step(i + 1))
            else:
                self._set_progress(0, 0)
                dt = time.time() - t0
                joined = "\n".join(prompts)
                self.current_prompt = joined
                self.output_text.set_prompt(joined, extra_markers=["NEGATIVE:"])
                self._push_history(prompts, genre=genre, seed=seed0, n=n)
                self._set_status("Generated", f"{n} prompt(s) in {dt:.2f}s")

        step(0)

    def _push_history(self, prompts, genre, seed, n):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        item = {
            "time": ts,
            "genre": genre,
            "seed": seed,
            "count": n,
            "prompts": prompts,
        }
        self.history.append(item)
        label = f"[{ts}] {genre} | seed={seed if seed is not None else '—'} | x{n}"
        self.history_list.insert("end", label)

    # ---------- copy/save ----------
    def _copy_current(self):
        txt = self.output_text.get("1.0", "end-1c").strip()
        if not txt:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(txt)
        self._set_status("Copied current", "")

    def _copy_all(self):
        if not self.history:
            self._copy_current()
            return
        # copy all prompts in history
        all_prompts = []
        for h in self.history:
            all_prompts.extend(h["prompts"])
        txt = "\n".join(all_prompts).strip()
        if not txt:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(txt)
        self._set_status("Copied all history", f"{len(all_prompts)} prompt(s)")

    def _save_output(self):
        txt = self.output_text.get("1.0", "end-1c").strip()
        if not txt:
            messagebox.showerror("Nothing to save", "Generate something first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save output",
            defaultextension=".txt",
            filetypes=[("Text","*.txt"),("JSON","*.json"),("All files","*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                prompts = [line for line in txt.splitlines() if line.strip()]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"prompts": prompts}, f, ensure_ascii=False, indent=2)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt + "\n")
            self._set_status("Saved", os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    # ---------- history/favorites ----------
    def _on_history_select(self, _evt):
        sel = self.history_list.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            item = self.history[idx]
        except Exception:
            return
        joined = "\n".join(item["prompts"])
        self.current_prompt = joined
        self.output_text.set_prompt(joined, extra_markers=["NEGATIVE:"])
        self.out_nb.select(self.out_output)
        self._set_status("Loaded from history", f"{item['genre']}")

    def _clear_history(self):
        self.history.clear()
        self.history_list.delete(0, "end")
        self._set_status("History cleared", "")

    def _favorite_current(self):
        txt = self.output_text.get("1.0", "end-1c").strip()
        if not txt:
            return
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        item = {"time": ts, "text": txt}
        self.favorites.append(item)
        self.favs_list.insert("end", f"[{ts}] {txt[:60].strip()}...")
        self._set_status("Favorited", "")

    def _on_fav_select(self, _evt):
        sel = self.favs_list.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            item = self.favorites[idx]
        except Exception:
            return
        self.current_prompt = item["text"]
        self.output_text.set_prompt(item["text"], extra_markers=["NEGATIVE:"])
        self.out_nb.select(self.out_output)
        self._set_status("Loaded favorite", "")

    def _remove_favorite(self):
        sel = self.favs_list.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            self.favorites.pop(idx)
        except Exception:
            return
        self.favs_list.delete(idx)
        self._set_status("Removed favorite", "")

    def _export_history(self):
        if not self.history:
            messagebox.showerror("No history", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Export history",
            defaultextension=".json",
            filetypes=[("JSON","*.json"),("Text","*.txt"),("All files","*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                lines = []
                for h in self.history:
                    lines.extend(h["prompts"])
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"history": self.history}, f, ensure_ascii=False, indent=2)
            self._set_status("Exported history", os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _export_favorites(self):
        if not self.favorites:
            messagebox.showerror("No favorites", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(
            title="Export favorites",
            defaultextension=".json",
            filetypes=[("JSON","*.json"),("Text","*.txt"),("All files","*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join([x["text"] for x in self.favorites]) + "\n")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"favorites": self.favorites}, f, ensure_ascii=False, indent=2)
            self._set_status("Exported favorites", os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    # ---------- presets ----------
    def _append_extra(self, tag: str):
        cur = self.extra_tags.get().strip()
        parts = [p.strip() for p in cur.split(",") if p.strip()]
        low = {p.lower() for p in parts}
        if tag.lower() not in low:
            parts.append(tag)
        self.extra_tags.set(", ".join(parts))

    def _apply_ova_mode(self):
        cur = self.extra_tags.get().strip()
        parts = [p.strip() for p in cur.split(",") if p.strip()]
        if self.ova_locked.get():
            low = {p.lower() for p in parts}
            for t in OVA_ANCHOR_TAGS:
                if t.lower() not in low:
                    parts.append(t)
        else:
            ova_set = {t.lower() for t in OVA_ANCHOR_TAGS}
            parts = [p for p in parts if p.lower() not in ova_set]
        self.extra_tags.set(", ".join(parts))

    def _preset_ova(self):
        self.ova_locked.set(True)
        self._apply_ova_mode()
        self.genre.set("random")
        self.quality.set("ultra")
        self.distance.set("random")
        self._set_status("Preset applied", "Locked 90s OVA")

    def _preset_clean(self):
        self.ova_locked.set(False)
        self.extra_tags.set("90s anime aesthetic, cel shading, film grain")
        self.negative_tags.set("nsfw, nude, explicit")
        self.auto_enabled.set(False)
        self._set_status("Preset applied", "Clean (non-ecchi)")

    def _preset_cyber(self):
        self.ova_locked.set(False)
        self.extra_tags.set("night city, neon glow, rainy alley, dramatic shadows, 90s anime aesthetic")
        self.negative_tags.set("")
        self._set_status("Preset applied", "Cyberpunk grit")

    def _preset_romance(self):
        self.ova_locked.set(False)
        self.extra_tags.set("soft lighting, warm palette, sunset, gentle smile, 90s anime aesthetic")
        self._set_status("Preset applied", "Soft romance")

    def _reset_defaults(self):
        self.genre.set("random")
        self.count.set(1)
        self.seed.set("")
        self.force_1girl.set(False)
        self.quality.set("ultra")
        self.distance.set("random")
        self.extra_tags.set("")
        self.negative_tags.set("")
        self.ova_locked.set(False)
        self.lock_seed.set(False)
        self.increment_seed.set(True)

        self.auto_enabled.set(False)
        self.auto_master_prob.set(35.0)
        self.auto_max_tags.set(2)
        self.auto_search.set("")
        self.auto_filter_enabled_only.set(False)
        self.auto_filter_nonzero_only.set(True)
        for v in self.per_file_vars.values():
            v.set(0.0)
        self._refresh_auto_file_list()
        self._set_status("Reset", "Defaults")

    def _collect_preset_state(self):
        audit = apg.data_audit()
        unused = cast(List[str], audit["unused"])
        per = {}
        for fn in unused:
            if fn in self.per_file_vars:
                val = float(self.per_file_vars[fn].get())
                if val != 0:
                    per[fn] = val
        return {
            "data_dir": self.data_dir.get(),
            "basics": {
                "genre": self.genre.get(),
                "count": int(self.count.get()),
                "seed": self.seed.get(),
                "force_1girl": bool(self.force_1girl.get()),
                "quality": self.quality.get(),
                "distance": self.distance.get(),
                "extra_tags": self.extra_tags.get(),
                "negative_tags": self.negative_tags.get(),
                "ova_locked": bool(self.ova_locked.get()),
                "lock_seed": bool(self.lock_seed.get()),
                "increment_seed": bool(self.increment_seed.get()),
            },
            "auto_append": {
                "enabled": bool(self.auto_enabled.get()),
                "master_prob": float(self.auto_master_prob.get()),
                "max_extra_tags": int(self.auto_max_tags.get()),
                "per_file": per,
                "filters": {
                    "search": self.auto_search.get(),
                    "enabled_only": bool(self.auto_filter_enabled_only.get()),
                    "nonzero_only": bool(self.auto_filter_nonzero_only.get()),
                }
            }
        }

    def _apply_preset_state(self, st):
        try:
            if "data_dir" in st and st["data_dir"]:
                self.data_dir.set(st["data_dir"])
                self._reload_data(silent=True)
        except Exception:
            pass

        b = st.get("basics", {})
        self.genre.set(b.get("genre", "random"))
        self.count.set(int(b.get("count", 1)))
        self.seed.set(b.get("seed", ""))
        self.force_1girl.set(bool(b.get("force_1girl", False)))
        self.quality.set(b.get("quality", "ultra"))
        self.distance.set(b.get("distance", "random"))
        self.extra_tags.set(b.get("extra_tags", ""))
        self.negative_tags.set(b.get("negative_tags", ""))
        self.ova_locked.set(bool(b.get("ova_locked", False)))
        if self.ova_locked.get():
            self._apply_ova_mode()
        self.lock_seed.set(bool(b.get("lock_seed", False)))
        self.increment_seed.set(bool(b.get("increment_seed", True)))

        a = st.get("auto_append", {})
        self.auto_enabled.set(bool(a.get("enabled", False)))
        self.auto_master_prob.set(float(a.get("master_prob", 35.0)))
        self.auto_max_tags.set(int(a.get("max_extra_tags", 2)))

        filters = a.get("filters", {})
        self.auto_search.set(filters.get("search", ""))
        self.auto_filter_enabled_only.set(bool(filters.get("enabled_only", False)))
        self.auto_filter_nonzero_only.set(bool(filters.get("nonzero_only", True)))

        per = a.get("per_file", {})
        for fn, val in per.items():
            if fn not in self.per_file_vars:
                self.per_file_vars[fn] = tk.DoubleVar(value=0.0)
            self.per_file_vars[fn].set(float(val))

        self._refresh_auto_file_list()

    def _save_preset(self):
        st = self._collect_preset_state()
        path = filedialog.asksaveasfilename(
            title="Save preset",
            defaultextension=".json",
            filetypes=[("JSON","*.json")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False, indent=2)
            self._set_status("Preset saved", os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def _load_preset(self):
        path = filedialog.askopenfilename(
            title="Load preset",
            filetypes=[("JSON","*.json")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                st = json.load(f)
            self._apply_preset_state(st)
            self._set_status("Preset loaded", os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Load failed", str(e))


def main():
    root = tk.Tk()
    _try_apply_modern_theme(root)
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
