#!/usr/bin/env python3
"""
Tkinter GUI for anime_prompt_generator_plus.py (v6.3.1 compatible)

Adds:
- Data audit panel: Found vs Used vs Unused .txt files
- Auto-append extra pools from UNUSED files (toggle + master prob + max tags + per-file sliders)
- Keeps: List genres, Locked 90s OVA mode
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import anime_prompt_generator_plus as apg


OVA_ANCHOR_TAGS = [
    "90s anime aesthetic",
    "OVA-era style",
    "vhs scanlines",
    "film grain",
    "cel shading",
    "hand-drawn look",
    "soft chromatic aberration",
]


class ScrollFrame(ttk.Frame):
    """A simple scrollable frame (vertical)."""
    def __init__(self, master, height=420):
        super().__init__(master)
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")

        # Make inner frame width track canvas width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)


class AuditDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Data audit")
        self.geometry("860x520")

        audit = apg.data_audit()

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=f"Data folder: {audit['data_dir']}").pack(anchor="w")
        ttk.Label(top, text=f"Found: {audit['found_count']}   Used (referenced by generator): {audit['used_count']}   Unused: {audit['unused_count']}").pack(anchor="w", pady=(6,0))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        def make_list(tab_name, items):
            frm = ttk.Frame(nb, padding=10)
            nb.add(frm, text=tab_name)
            frm.columnconfigure(0, weight=1)
            frm.rowconfigure(0, weight=1)
            lb = tk.Listbox(frm)
            lb.grid(row=0, column=0, sticky="nsew")
            sb = ttk.Scrollbar(frm, orient="vertical", command=lb.yview)
            sb.grid(row=0, column=1, sticky="ns")
            lb.configure(yscrollcommand=sb.set)
            for it in items:
                lb.insert("end", it)

        make_list("Found (.txt)", audit["found"])
        make_list("Used by generator", audit["used"])
        make_list("Unused (eligible for Auto-append)", audit["unused"])


class GenresDialog(tk.Toplevel):
    def __init__(self, master, on_select):
        super().__init__(master)
        self.title("Genres")
        self.geometry("520x420")
        self.on_select = on_select

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        cols = ("name", "is_ecchi", "mood")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings")
        self.tree.heading("name", text="Genre")
        self.tree.heading("is_ecchi", text="Ecchi?")
        self.tree.heading("mood", text="Mood")
        self.tree.column("name", width=260, anchor="w")
        self.tree.column("is_ecchi", width=70, anchor="center")
        self.tree.column("mood", width=140, anchor="w")
        self.tree.pack(fill="both", expand=True)

        for row in apg.list_genres():
            self.tree.insert("", "end", values=(row["name"], row["is_ecchi"], row.get("mood","")))

        ttk.Label(frm, text="Tip: double-click a row to select it.").pack(anchor="w", pady=(8,0))
        self.tree.bind("<Double-1>", self._dbl)

    def _dbl(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        if vals:
            self.on_select(vals[0])
            self.destroy()


class WeightsDialog(tk.Toplevel):
    def __init__(self, master, vars_):
        super().__init__(master)
        self.title("Auto-append extra pools (unused .txt)")
        self.geometry("760x560")
        self.vars_ = vars_

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        # Controls
        ctl = ttk.LabelFrame(outer, text="Controls", padding=10)
        ctl.pack(fill="x")

        ttk.Checkbutton(ctl, text="Enable auto-append extra pools", variable=self.vars_["enabled"]).grid(row=0, column=0, sticky="w")
        ttk.Label(ctl, text="Master probability").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Scale(ctl, from_=0, to=100, orient="horizontal", variable=self.vars_["master_prob"]).grid(row=1, column=1, sticky="ew", padx=(10,0), pady=(10,0))
        ttk.Label(ctl, text="Max extra tags").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Spinbox(ctl, from_=1, to=10, textvariable=self.vars_["max_extra_tags"], width=6).grid(row=2, column=1, sticky="w", padx=(10,0), pady=(10,0))

        ctl.columnconfigure(1, weight=1)

        # Per-file sliders (scroll)
        per = ttk.LabelFrame(outer, text="Per-file probability (only UNUSED files)", padding=10)
        per.pack(fill="both", expand=True, pady=(12,0))

        sf = ScrollFrame(per, height=360)
        sf.pack(fill="both", expand=True)

        audit = apg.data_audit()
        unused = audit["unused"]

        if not unused:
            ttk.Label(sf.inner, text="No unused .txt files detected. Nothing to auto-append.").grid(row=0, column=0, sticky="w")
        else:
            ttk.Label(sf.inner, text="Set file slider >0% to allow it to contribute. Default is 0% (off).").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,8))
            r = 1
            for fn in unused:
                key = f"file::{fn}"
                if key not in self.vars_:
                    self.vars_[key] = tk.DoubleVar(value=0.0)
                ttk.Label(sf.inner, text=fn).grid(row=r, column=0, sticky="w", pady=2)
                ttk.Scale(sf.inner, from_=0, to=100, orient="horizontal", variable=self.vars_[key]).grid(row=r, column=1, sticky="ew", padx=(10,0))
                sf.inner.columnconfigure(1, weight=1)
                r += 1

        # Footer buttons
        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(12,0))
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.master = master
        self.grid(sticky="nsew")
        master.title("Anime Prompt Generator GUI (v6.3.1 + Audit + Auto-append)")

        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.data_dir = tk.StringVar(value=apg.DATA_DIR)

        self.genre = tk.StringVar(value="random")
        self.count = tk.IntVar(value=1)
        self.seed = tk.StringVar(value="")
        self.force_1girl = tk.BooleanVar(value=False)
        self.quality = tk.StringVar(value="ultra")
        self.distance = tk.StringVar(value="random")
        self.ova_locked = tk.BooleanVar(value=False)
        self.extra = tk.StringVar(value="")

        # Auto-append tuning vars (0..100 in UI)
        self.extra_vars = {
            "enabled": tk.BooleanVar(value=False),
            "master_prob": tk.DoubleVar(value=35),
            "max_extra_tags": tk.IntVar(value=2),
            # file::FILENAME -> DoubleVar (added dynamically)
        }

        self._build_top()
        self._build_controls()
        self._build_output()
        self._refresh_genres()

    def _build_top(self):
        top = ttk.LabelFrame(self, text="Data folder", padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="data/ path").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.data_dir).grid(row=0, column=1, sticky="ew", padx=(10,10))
        ttk.Button(top, text="Browse…", command=self._browse_data).grid(row=0, column=2, sticky="e")
        ttk.Button(top, text="Reload", command=self._reload_data).grid(row=0, column=3, sticky="e", padx=(6,0))
        ttk.Button(top, text="Audit…", command=self._open_audit).grid(row=0, column=4, sticky="e", padx=(6,0))

    def _build_controls(self):
        box = ttk.LabelFrame(self, text="Generator settings", padding=10)
        box.grid(row=1, column=0, sticky="ew", pady=(10,0))
        for c in range(7):
            box.columnconfigure(c, weight=1)

        ttk.Label(box, text="Genre").grid(row=0, column=0, sticky="w")
        self.genre_combo = ttk.Combobox(box, textvariable=self.genre, state="readonly")
        self.genre_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(10,10))
        ttk.Button(box, text="List genres…", command=self._open_genres).grid(row=0, column=3, sticky="w")
        ttk.Checkbutton(box, text="Locked 90s OVA mode", variable=self.ova_locked, command=self._apply_ova_mode).grid(row=0, column=4, columnspan=3, sticky="e")

        ttk.Label(box, text="Count").grid(row=1, column=0, sticky="w", pady=(10,0))
        ttk.Spinbox(box, from_=1, to=999, textvariable=self.count, width=6).grid(row=1, column=1, sticky="w", padx=(10,0), pady=(10,0))
        ttk.Label(box, text="Seed (optional)").grid(row=1, column=2, sticky="w", pady=(10,0))
        ttk.Entry(box, textvariable=self.seed).grid(row=1, column=3, sticky="ew", padx=(10,10), pady=(10,0))
        ttk.Checkbutton(box, text="Force 1girl, solo", variable=self.force_1girl).grid(row=1, column=4, columnspan=3, sticky="e", pady=(10,0))

        ttk.Label(box, text="Quality").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Combobox(box, textvariable=self.quality, state="readonly", values=["ultra","high","standard","artistic"]).grid(row=2, column=1, sticky="ew", padx=(10,10), pady=(10,0))

        ttk.Label(box, text="Camera distance").grid(row=2, column=2, sticky="w", pady=(10,0))
        ttk.Combobox(box, textvariable=self.distance, state="readonly",
                     values=["random","face_closeup","portrait","half_body","full_body","wide_scene"]).grid(row=2, column=3, sticky="ew", padx=(10,10), pady=(10,0))

        ttk.Button(box, text="Auto-append…", command=self._open_weights).grid(row=2, column=4, sticky="e", pady=(10,0))
        ttk.Button(box, text="Generate", command=self._generate).grid(row=2, column=6, sticky="e", pady=(10,0))

        ttk.Label(box, text="Extra tags (appended)").grid(row=3, column=0, sticky="w", pady=(10,0))
        ttk.Entry(box, textvariable=self.extra).grid(row=3, column=1, columnspan=3, sticky="ew", padx=(10,10), pady=(10,0))
        ttk.Button(box, text="Clear extra", command=lambda: self.extra.set("")).grid(row=3, column=4, sticky="e", pady=(10,0))
        ttk.Button(box, text="Copy output", command=self._copy_output).grid(row=3, column=6, sticky="e", pady=(10,0))

    def _build_output(self):
        out = ttk.LabelFrame(self, text="Output", padding=10)
        out.grid(row=3, column=0, sticky="nsew", pady=(10,0))
        out.rowconfigure(0, weight=1)
        out.columnconfigure(0, weight=1)

        self.text = tk.Text(out, wrap="word", height=18)
        self.text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(out, orient="vertical", command=self.text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scroll.set)

        btns = ttk.Frame(out)
        btns.grid(row=1, column=0, columnspan=2, sticky="e", pady=(10,0))
        ttk.Button(btns, text="Save…", command=self._save_output).grid(row=0, column=0, padx=(0,8))
        ttk.Button(btns, text="Clear", command=lambda: self.text.delete("1.0","end")).grid(row=0, column=1)

    # --- Actions ---
    def _browse_data(self):
        d = filedialog.askdirectory(title="Select your data folder", initialdir=self.data_dir.get() or ".")
        if d:
            self.data_dir.set(d)

    def _reload_data(self):
        d = self.data_dir.get().strip()
        if not d or not os.path.isdir(d):
            messagebox.showerror("Invalid folder", "That data folder path doesn’t exist.")
            return
        try:
            apg.set_data_dir(d)
            self._refresh_genres()
            messagebox.showinfo("Reloaded", f"Reloaded data from:\n{d}")
        except Exception as e:
            messagebox.showerror("Reload failed", str(e))

    def _open_audit(self):
        AuditDialog(self.master)

    def _refresh_genres(self):
        genres = [g["name"] for g in apg.list_genres()]
        if "random" not in genres:
            genres = ["random"] + genres
        self.genre_combo["values"] = genres
        if self.genre.get() not in genres:
            self.genre.set("random")

    def _open_weights(self):
        WeightsDialog(self.master, self.extra_vars)

    def _open_genres(self):
        GenresDialog(self.master, on_select=lambda g: self.genre.set(g))

    def _apply_ova_mode(self):
        if self.ova_locked.get():
            cur = self.extra.get().strip()
            tags = [t.strip() for t in cur.split(",") if t.strip()]
            lowset = {x.lower() for x in tags}
            for t in OVA_ANCHOR_TAGS:
                if t.lower() not in lowset:
                    tags.append(t)
            self.extra.set(", ".join(tags))

    def _extra_tuning(self) -> apg.ExtraPoolsTuning:
        audit = apg.data_audit()
        unused = audit["unused"]

        per_file = {}
        for fn in unused:
            key = f"file::{fn}"
            if key in self.extra_vars:
                per_file[fn] = float(self.extra_vars[key].get()) / 100.0

        return apg.ExtraPoolsTuning(
            enabled=bool(self.extra_vars["enabled"].get()),
            master_prob=float(self.extra_vars["master_prob"].get()) / 100.0,
            max_extra_tags=int(self.extra_vars["max_extra_tags"].get()),
            per_file_prob=per_file,
        )

    def _generate(self):
        try:
            count = int(self.count.get())
            if count <= 0:
                raise ValueError
        except Exception:
            messagebox.showerror("Invalid count", "Count must be a positive integer.")
            return

        seed_txt = self.seed.get().strip()
        seed = None
        if seed_txt:
            try:
                seed = int(seed_txt)
            except Exception:
                messagebox.showerror("Invalid seed", "Seed must be an integer (or blank).")
                return

        genre = self.genre.get().strip() or "random"
        extra = self.extra.get().strip()
        quality = self.quality.get().strip() or "ultra"
        distance = self.distance.get().strip() or "random"
        force_1girl = bool(self.force_1girl.get())

        extra_tuning = self._extra_tuning()

        lines = []
        for i in range(count):
            s = (seed + i) if seed is not None else None
            prompt = apg.generate_prompt(
                genre=genre,
                seed=s,
                extra_words=extra,
                distance_preset=distance,
                force_1girl=force_1girl,
                quality_preset=quality,
                extra_pools_tuning=extra_tuning,
            )
            lines.append(prompt)

        self.text.delete("1.0","end")
        self.text.insert("1.0", "\n".join(lines))

    def _copy_output(self):
        txt = self.text.get("1.0","end").strip()
        if not txt:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(txt)
        messagebox.showinfo("Copied", "Output copied to clipboard.")

    def _save_output(self):
        txt = self.text.get("1.0","end").strip()
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
            messagebox.showinfo("Saved", f"Saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    App(root)
    root.minsize(980, 620)
    root.mainloop()

if __name__ == "__main__":
    main()
