# rthook_pillow_tk.py
# Force Pillow's Tk helpers to be importable inside the frozen app
# and register the ImageTk bridge early.
try:
    import PIL._tkinter_finder  # noqa: F401
except Exception:
    pass

try:
    from PIL import ImageTk  # noqa: F401
except Exception:
    pass
