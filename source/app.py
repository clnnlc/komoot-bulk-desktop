import os
import ctypes
import base64
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from exporter import DesktopApi, Cancelled, export_tours

class App(tk.Tk):
    def __init__(self):
        if os.name == 'nt':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('KomootBulk.Desktop')
        super().__init__()
        self.title('Komoot Bulk · GPX Export')
        self.geometry('900x740')
        self.minsize(800, 700)
        self.configure(bg='#EEF3F2')
        assets = Path(__file__).resolve().parent / 'assets'
        self.iconbitmap(str(assets / 'app.ico'))
        self.app_icon = tk.PhotoImage(data=base64.b64encode((assets / 'app.png').read_bytes()))
        self.iconphoto(True, self.app_icon)
        self.brand_icon = tk.PhotoImage(data=base64.b64encode((assets / 'brand.png').read_bytes()))
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 11))
        style.configure('TFrame', background='#EEF3F2')
        style.configure('TLabel', background='#EEF3F2', foreground='#203E38')
        style.configure('Card.TFrame', background='white')
        style.configure('Card.TLabel', background='white', foreground='#203E38')
        style.configure('Muted.TLabel', background='white', foreground='#5D716C', font=('Segoe UI', 10))
        style.configure('Section.TLabel', background='white', foreground='#174C43', font=('Segoe UI', 13, 'bold'))
        style.configure('TEntry', padding=9, fieldbackground='#F7FAF9', bordercolor='#CDDBD6', lightcolor='#CDDBD6', darkcolor='#CDDBD6')
        style.map('TEntry', bordercolor=[('focus', '#287B68')])
        style.configure('TButton', padding=(15, 10), background='#E5EDE9', foreground='#174C43', borderwidth=0)
        style.map('TButton', background=[('active', '#D5E3DC')], foreground=[('disabled', '#8B9A95')])
        style.configure('Go.TButton', background='#17634F', foreground='white', font=('Segoe UI', 11, 'bold'))
        style.map('Go.TButton', background=[('disabled', '#D9E4DF'), ('active', '#114D3D')], foreground=[('disabled', '#83968D')])
        style.configure('Horizontal.TProgressbar', background='#287B68', troughcolor='#E4ECE8', borderwidth=0, thickness=8)
        header = tk.Frame(self, bg='#174C43', padx=30, pady=18)
        header.pack(fill='x')
        tk.Label(header, image=self.brand_icon, bg='#174C43').pack(side='left', padx=(0, 16))
        titles = tk.Frame(header, bg='#174C43')
        titles.pack(side='left')
        tk.Label(titles, text='Komoot Bulk', font=('Segoe UI', 26, 'bold'), fg='white', bg='#174C43').pack(anchor='w')
        tk.Label(titles, text='Deine abgeschlossenen Touren. Als GPX in deinem Archiv.', font=('Segoe UI', 11), fg='#C6DDD5', bg='#174C43').pack(anchor='w', pady=(3, 0))
        box = ttk.Frame(self, padding=(30, 16, 30, 12))
        box.pack(fill='both', expand=True)
        account = ttk.Frame(box, style='Card.TFrame', padding=14)
        account.pack(fill='x')
        ttk.Label(account, text='Mit Komoot verbinden', style='Section.TLabel').pack(anchor='w', pady=(0, 14))
        fields = ttk.Frame(account, style='Card.TFrame')
        fields.pack(fill='x')
        left = ttk.Frame(fields, style='Card.TFrame')
        left.pack(side='left', fill='x', expand=True, padx=(0, 10))
        right = ttk.Frame(fields, style='Card.TFrame')
        right.pack(side='left', fill='x', expand=True, padx=(10, 0))
        self.email = self.field(left, 'E-Mail-Adresse')
        self.password = self.field(right, 'Passwort', show='•')
        ttk.Label(account, text='Deine Zugangsdaten werden nicht gespeichert.', style='Muted.TLabel').pack(anchor='w')
        destination = ttk.Frame(box, style='Card.TFrame', padding=14)
        destination.pack(fill='x', pady=(12, 0))
        ttk.Label(destination, text='Exportziel', style='Section.TLabel').pack(anchor='w')
        row = ttk.Frame(destination, style='Card.TFrame')
        row.pack(fill='x', pady=(12, 10))
        self.folder = tk.StringVar()
        ttk.Entry(row, textvariable=self.folder).pack(side='left', fill='x', expand=True)
        self.choose = ttk.Button(row, text='Auswählen …', command=self.browse)
        self.choose.pack(side='right', padx=(8, 0))
        ttk.Label(destination, text='Eine GPX pro Tour. Bereits exportierte Touren werden übersprungen.', style='Muted.TLabel').pack(anchor='w')
        actions = ttk.Frame(box)
        actions.pack(fill='x', pady=12)
        self.start_button = ttk.Button(actions, text='Alle Touren herunterladen', style='Go.TButton', command=self.start)
        self.start_button.pack(side='left')
        self.cancel = ttk.Button(actions, text='Abbrechen', command=self.abort, state='disabled')
        self.cancel.pack(side='left', padx=8)
        ttk.Button(actions, text='Ordner öffnen', command=self.open_folder).pack(side='right')
        activity = ttk.Frame(box, style='Card.TFrame', padding=14)
        activity.pack(fill='both', expand=True)
        ttk.Label(activity, text='Exportfortschritt', style='Section.TLabel').pack(anchor='w', pady=(0, 10))
        self.status = tk.StringVar(value='Bereit – Konto und Zielordner angeben, dann Export starten.')
        ttk.Label(activity, textvariable=self.status, style='Muted.TLabel', wraplength=700).pack(anchor='w', pady=(0, 12))
        self.progress = ttk.Progressbar(activity)
        self.progress.pack(fill='x')
        logframe = ttk.Frame(activity, style='Card.TFrame')
        logframe.pack(fill='both', expand=True, pady=(12, 0))
        self.log = tk.Text(logframe, height=5, state='disabled', font=('Segoe UI', 10), bg='#F7FAF9', fg='#354D45', relief='flat', padx=12, pady=10, wrap='word', highlightthickness=0)
        scrollbar = ttk.Scrollbar(logframe, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.log.pack(side='left', fill='both', expand=True)
        self.log.tag_configure('error', foreground='#AE3A32')
        self.log.tag_configure('success', foreground='#17634F')
        ttk.Label(box, text='Komoot Bulk 1.1.0  •  Basiert auf KomootGPX  •  GPL-3.0', font=('Segoe UI', 9), foreground='#60756C').pack(anchor='w', pady=(12, 0))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def field(self, parent, label, **kwargs):
        ttk.Label(parent, text=label, style='Card.TLabel').pack(anchor='w')
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
                    self.log.insert('end', f"{row['status']}: {row['name']}" + (f" — {row['error']}" if 'error' in row else '') + '\n', 'error' if 'error' in row else 'success')
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

