"""The small window you see when you open the program: pick folders, press Start, and the screen opens in your browser."""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, ttk

from . import __version__, settings
from .app import App
from .server import create_server, url_of


class Launcher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.server = None
        self.url = ''
        root.title(f'Word Splicer {__version__}')
        root.minsize(640, 330)
        s = settings.load()
        self.vars = {'lines': tk.StringVar(value=s.lines), 'plan': tk.StringVar(value=s.plan), 'work': tk.StringVar(value=s.work)}

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='Word Splicer', font=('Segoe UI', 16, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w')
        ttk.Label(frame, text='Replace single words inside existing voice lines with clips you provide.', foreground='#555').grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 12))

        self.fields = []
        rows = [
            ('lines', 'Voice lines folder', 'The folder of existing voice lines to change, e.g. the "splice" folder made by the swap scan.', True, True),
            ('plan', 'Swap plan (optional)', 'swap-plan.json from the swap scan. Only used to show the expected wording.', False, False),
            ('work', 'Your work folder', 'Where your clips, your choices and the finished lines are kept.', True, True),
        ]
        for i, (key, label, tip, folder, _required) in enumerate(rows):
            r = 2 + i * 2
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky='w')
            entry = ttk.Entry(frame, textvariable=self.vars[key])
            entry.grid(row=r, column=1, sticky='ew', padx=8)
            btn = ttk.Button(frame, text='Browse…', command=lambda k=key, f=folder: self.browse(k, f))
            btn.grid(row=r, column=2)
            ttk.Label(frame, text=tip, foreground='#666', wraplength=560).grid(row=r + 1, column=1, columnspan=2, sticky='w', padx=8, pady=(0, 8))
            self.fields += [entry, btn]

        buttons = ttk.Frame(frame)
        buttons.grid(row=8, column=0, columnspan=3, sticky='w', pady=(8, 0))
        self.start_btn = ttk.Button(buttons, text='Start', command=self.toggle)
        self.start_btn.pack(side='left')
        self.open_btn = ttk.Button(buttons, text='Open the screen again', command=self.open_browser, state='disabled')
        self.open_btn.pack(side='left', padx=8)
        self.status = ttk.Label(frame, text='Choose the folder of voice lines, then press Start.', wraplength=590, justify='left')
        self.status.grid(row=9, column=0, columnspan=3, sticky='w', pady=(12, 0))
        root.bind('<Return>', lambda _e: self.toggle() if self.server is None else None)
        root.protocol('WM_DELETE_WINDOW', self.quit)

    def say(self, text: str, error: bool = False) -> None:
        self.status.configure(text=text, foreground='#b42318' if error else '')

    def browse(self, key: str, folder: bool) -> None:
        current = self.vars[key].get() or None
        picked = filedialog.askdirectory(initialdir=current, title='Choose a folder') if folder else filedialog.askopenfilename(initialdir=current, title='Choose swap-plan.json', filetypes=[('JSON', '*.json'), ('All files', '*.*')])
        if picked:
            self.vars[key].set(picked)

    def current(self) -> settings.Settings:
        return settings.Settings(**{k: v.get().strip() for k, v in self.vars.items()})

    def toggle(self) -> None:
        self.stop() if self.server else self.start()

    def start(self) -> None:
        s = self.current()
        problem = settings.check(s)
        if problem:
            self.say(problem, error=True)
            return
        try:
            from pathlib import Path
            app = App(Path(s.lines), Path(s.work), None, Path(s.plan) if s.plan else None)
            self.server = create_server(app)
        except Exception as e:  # e.g. the work folder can't be created
            self.say(f'Could not start: {e}', error=True)
            return
        settings.save(s)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = url_of(self.server)
        for w in self.fields:
            w.configure(state='disabled')
        self.start_btn.configure(text='Stop')
        self.open_btn.configure(state='normal')
        self.say(f'Running. The screen is open in your browser at {self.url}\nKeep this window open while you work. Your clips and choices are saved in {s.work}')
        self.open_browser()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        for w in self.fields:
            w.configure(state='normal')
        self.start_btn.configure(text='Start')
        self.open_btn.configure(state='disabled')
        self.say('Stopped. Your work is saved.')

    def open_browser(self) -> None:
        if self.url:
            webbrowser.open(self.url)

    def quit(self) -> None:
        self.stop()
        self.root.destroy()


def run() -> None:
    root = tk.Tk()
    Launcher(root)
    root.mainloop()
