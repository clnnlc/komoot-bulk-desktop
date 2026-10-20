import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from exporter import DesktopApi, Cancelled, export_tours

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Komoot Bulk · GPX Export')
        self.geometry('760x660')
        self.minsize(650, 570)
        self.configure(bg='#f4f6f2')
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 11))
        style.configure('TFrame', background='#f4f6f2')
        style.configure('TLabel', background='#f4f6f2', foreground='#203427')
        style.configure('Title.TLabel', font=('Segoe UI', 25, 'bold'))
        style.configure('TButton', padding=9)
        style.configure('Go.TButton', background='#286442', foreground='white')
        style.configure('Horizontal.TProgressbar', background='#286442')
        box = ttk.Frame(self, padding=28)
        box.pack(fill='both', expand=True)
        ttk.Label(box, text='Deine Touren. Dein Archiv.', style='Title.TLabel').pack(anchor='w')
        ttk.Label(box, text='Alle abgeschlossenen Komoot-Touren als GPX herunterladen.').pack(anchor='w', pady=(5, 22))
        self.email = self.field(box, 'Komoot E-Mail')
        self.password = self.field(box, 'Komoot Passwort', show='•')
        ttk.Label(box, text='Das Passwort wird nur für diese Sitzung verwendet.').pack(anchor='w', pady=(0, 14))
        ttk.Label(box, text='Zielordner').pack(anchor='w')
        row = ttk.Frame(box)
        row.pack(fill='x', pady=(5, 14))
        self.folder = tk.StringVar()
        ttk.Entry(row, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        self.choose = ttk.Button(row, text='Auswählen …', command=self.browse)
        self.choose.pack(side='right', padx=(8, 0))
        ttk.Label(box, text='Nur abgeschlossene Touren · vorhandene GPX überspringen').pack(anchor='w')
        actions = ttk.Frame(box)
        actions.pack(fill='x', pady=16)
        self.start_button = ttk.Button(actions, text='Alle Touren herunterladen', style='Go.TButton', command=self.start)
        self.start_button.pack(side='left')
        self.cancel = ttk.Button(actions, text='Abbrechen', command=self.abort, state='disabled')
        self.cancel.pack(side='left', padx=8)
        ttk.Button(actions, text='Ordner öffnen', command=self.open_folder).pack(side='right')
        self.status = tk.StringVar(value='Bereit. Melde dich mit deinem eigenen Komoot-Konto an.')
        ttk.Label(box, textvariable=self.status, wraplength=680).pack(anchor='w', pady=(0, 8))
        self.progress = ttk.Progressbar(box)
        self.progress.pack(fill='x')
        self.log = tk.Text(box, height=9, state='disabled', font=('Segoe UI', 10), relief='flat', padx=10, pady=10)
        self.log.pack(fill='both', expand=True, pady=12)
        ttk.Label(box, text='Basiert auf KomootGPX von Tim Schneeberger · GPL-3.0', font=('Segoe UI', 9)).pack(anchor='w')
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def field(self, parent, label, **kwargs):
        ttk.Label(parent, text=label).pack(anchor='w')
        entry = ttk.Entry(parent, **kwargs)
        entry.pack(fill='x', pady=(5, 12))
        return entry

    def browse(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def open_folder(self):
        if os.path.isdir(self.folder.get()):
            os.startfile(self.folder.get())

    def start(self):
        email, password, folder = self.email.get().strip(), self.password.get(), self.folder.get().strip()
        if not email or not password or not folder:
            messagebox.showinfo('Angaben fehlen', 'Bitte E-Mail, Passwort und Zielordner angeben.')
            return
        self.password.delete(0, 'end')
        self.busy = True
        self.stop.clear()
        self.start_button.configure(state='disabled')
        self.choose.configure(state='disabled')
        self.cancel.configure(state='normal')
        self.progress.configure(mode='indeterminate', value=0)
        self.progress.start()
        self.status.set('Anmeldung bei Komoot …')
        threading.Thread(target=self.run, args=(email, password, folder), daemon=True).start()

    def run(self, email, password, folder):
        api = DesktopApi(self.stop)
        try:
            api.login(email, password)
            password = None
            result = export_tours(api, folder, self.stop, lambda *event: self.events.put(event))
            self.events.put(('done', result))
        except Cancelled:
            self.events.put(('error', 'Export abgebrochen.'))
        except Exception as exc:
            self.events.put(('error', str(exc)))
        finally:
            password = None
            api.token = ''

    def abort(self):
        self.stop.set()
        self.status.set('Abbruch angefordert – laufende Anfrage wird beendet …')

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == 'status':
                    self.status.set(event[1])
                elif kind == 'total':
                    self.progress.stop()
                    self.progress.configure(mode='determinate', maximum=max(event[1], 1), value=0)
                elif kind == 'progress':
                    _, index, total, row = event
                    self.progress['value'] = index
                    self.status.set(f'{index} von {total} Touren bearbeitet')
                    self.log.configure(state='normal')
                    self.log.insert('end', f"{row['status']}: {row['name']}" + (f" — {row['error']}" if 'error' in row else '') + '\n')
                    self.log.see('end')
                    self.log.configure(state='disabled')
                elif kind in ('done', 'error'):
                    self.busy = False
                    self.progress.stop()
                    self.start_button.configure(state='normal')
                    self.choose.configure(state='normal')
                    self.cancel.configure(state='disabled')
                    if kind == 'error':
                        self.status.set(event[1])
                    else:
                        r = event[1]
                        prefix = 'Abgebrochen' if r['cancelled'] else 'Export beendet'
                        self.status.set(f"{prefix}: {r['saved']} gespeichert, {r['skipped']} vorhanden, {r['failed']} fehlgeschlagen.")
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def close(self):
        if self.busy:
            self.abort()
            self.after(150, self.close_when_idle)
        else:
            self.destroy()

    def close_when_idle(self):
        if self.busy:
            self.after(150, self.close_when_idle)
        else:
            self.destroy()

if __name__ == '__main__':
    app = App()
    if '--smoke-test' in sys.argv:
        app.withdraw()
        app.update()
        app.destroy()
    else:
        app.mainloop()
