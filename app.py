import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading, os, json, subprocess, shutil, base64, requests
from datetime import datetime
import fitz
from docx import Document
from PIL import Image, ImageTk

# ── CONFIG ──────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR     = os.path.join(BASE_DIR, "data")
COMMAND_BANK = os.path.join(DATA_DIR, "command_bank.json")
TECTONIC     = os.path.join(BASE_DIR, "tectonic.exe") if os.path.exists(os.path.join(BASE_DIR, "tectonic.exe")) else (shutil.which("tectonic") or "tectonic")

OPENROUTER_KEY = ""
GEMINI_KEY     = ""
GITHUB_TOKEN   = ""
GITHUB_REPO    = "SHox1Developer/latex-journal-ai"

cfg_path = os.path.join(BASE_DIR, "config.json")
if os.path.exists(cfg_path):
    with open(cfg_path, encoding="utf-8") as f:
        _c = json.load(f)
    OPENROUTER_KEY = _c.get("openrouter_key", "")
    GEMINI_KEY     = _c.get("gemini_key", "")
    GITHUB_TOKEN   = _c.get("github_token", "")

# ── COLORS (Catppuccin Mocha) ────────────────────────────────────────────────
BG    = "#1e1e2e"
BG2   = "#313244"
BG3   = "#45475a"
TEXT  = "#cdd6f4"
BLUE  = "#89b4fa"
GREEN = "#a6e3a1"
AMBER = "#f9e2af"
MAUVE = "#cba6f7"
BORDER= "#585b70"

# ── DEFAULT TEMPLATES ────────────────────────────────────────────────────────
DEFAULT_BANK = {
    "article": "\\documentclass[12pt,a4paper]{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath,graphicx,hyperref}\n\\title{%TITLE%}\n\\author{%AUTHOR%}\n\\date{%DATE%}\n\\begin{document}\n\\maketitle\n\\tableofcontents\n\\section{Kirish}\n%CONTENT%\n\\section{Xulosa}\nHujjat yakunlandi.\n\\end{document}",
    "report":  "\\documentclass[12pt,a4paper]{report}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath,graphicx}\n\\title{%TITLE%}\n\\author{%AUTHOR%}\n\\date{%DATE%}\n\\begin{document}\n\\maketitle\n\\tableofcontents\n\\chapter{Kirish}\n%CONTENT%\n\\chapter{Xulosa}\nHisobot yakunlandi.\n\\end{document}",
    "beamer":  "\\documentclass{beamer}\n\\usepackage[utf8]{inputenc}\n\\title{%TITLE%}\n\\author{%AUTHOR%}\n\\date{%DATE%}\n\\begin{document}\n\\begin{frame}\\titlepage\\end{frame}\n\\begin{frame}{Kirish}\n%CONTENT%\n\\end{frame}\n\\end{document}"
}

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(COMMAND_BANK):
    with open(COMMAND_BANK, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_BANK, f, indent=2)

SYSTEM_PROMPT = "Sen professional LaTeX mutaxassisisan. Berilgan matnga asoslanib toliq kompilyatsiya qilinadigan LaTeX hujjat yarat. FAQAT LaTeX kod qaytar, boshqa hech narsa yozma."

# ── HELPERS ──────────────────────────────────────────────────────────────────
def is_online():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False

def ai_generate(prompt, status_cb):
    if is_online():
        status_cb("Online: OpenRouter sinab ko'rilmoqda...")
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": f"https://github.com/{GITHUB_REPO}",
                },
                json={
                    "model": "openai/gpt-4o",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000
                },
                timeout=60
            )
            d = r.json()
            if "choices" in d:
                return d["choices"][0]["message"]["content"]
        except Exception:
            pass
        status_cb("Gemini sinab ko'rilmoqda...")
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]}]},
                timeout=60
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            status_cb(f"Online xato: {e}")
    return None

def offline_gen(tpl, title, author, date, content):
    with open(COMMAND_BANK, encoding="utf-8") as f:
        bank = json.load(f)
    t = bank.get(tpl, bank["article"])
    return (t.replace("%TITLE%", title)
             .replace("%AUTHOR%", author)
             .replace("%DATE%", date)
             .replace("%CONTENT%", content))

def clean_latex(text):
    for fence in ["```latex", "```tex", "```"]:
        if fence in text:
            text = text.split(fence)[1].split("```")[0].strip()
            break
    return text

# ── MAIN APP ─────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LaTeX Journal AI")
        self.geometry("1280x800")
        self.configure(bg=BG)
        self.current_file = None
        self.pdf_pages    = []
        self.pdf_idx      = 0
        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_statusbar()
        self._tree_refresh()

    def _build_menu(self):
        mb = tk.Menu(self, bg=BG2, fg=TEXT)
        self.config(menu=mb)
        fm = tk.Menu(mb, tearoff=0, bg=BG2, fg=TEXT)
        mb.add_cascade(label="Fayl", menu=fm)
        fm.add_command(label="Yangi loyiha",            command=self._new)
        fm.add_command(label="Import (.txt/.docx/.pdf)", command=self._import)
        fm.add_separator()
        fm.add_command(label="Chiqish", command=self.quit)
        em = tk.Menu(mb, tearoff=0, bg=BG2, fg=TEXT)
        mb.add_cascade(label="Export", menu=em)
        em.add_command(label="Export .tex",        command=lambda: self._export("tex"))
        em.add_command(label="Export .pdf",        command=lambda: self._export("pdf"))
        em.add_command(label="GitHub ga yuklash",  command=self._github)

    def _build_toolbar(self):
        tb = tk.Frame(self, bg=BG2, height=48)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        def btn(text, cmd, color=BLUE):
            b = tk.Button(tb, text=text, command=cmd,
                          bg=color, fg=BG, font=("Consolas", 10, "bold"),
                          relief="flat", padx=12, pady=6, cursor="hand2")
            b.pack(side="left", padx=4, pady=6)

        btn("▶ Compile",   self._compile,  GREEN)
        btn("🤖 AI Yarat", self._ai_gen,   MAUVE)
        btn("📥 Import",   self._import,   AMBER)
        btn("⬆ GitHub",   self._github,   BLUE)

        tk.Label(tb, text="  Template:", bg=BG2, fg=TEXT, font=("Consolas", 10)).pack(side="left")
        self.tpl = tk.StringVar(value="article")
        ttk.Combobox(tb, textvariable=self.tpl,
                     values=["article", "report", "beamer"],
                     state="readonly", width=10).pack(side="left", padx=4)

        tk.Label(tb, text="  Sarlavha:", bg=BG2, fg=TEXT, font=("Consolas", 10)).pack(side="left")
        self.ttl = tk.StringVar(value="Mening Jurnalim")
        tk.Entry(tb, textvariable=self.ttl, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, width=20,
                 font=("Consolas", 10)).pack(side="left", padx=4)

        tk.Label(tb, text="  Muallif:", bg=BG2, fg=TEXT, font=("Consolas", 10)).pack(side="left")
        self.auth = tk.StringVar(value="Frank")
        tk.Entry(tb, textvariable=self.auth, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, width=12,
                 font=("Consolas", 10)).pack(side="left", padx=4)

    def _build_main(self):
        pane = tk.PanedWindow(self, orient="horizontal",
                              bg=BORDER, sashwidth=4)
        pane.pack(fill="both", expand=True)

        # LEFT — File tree
        L = tk.Frame(pane, bg=BG2, width=220)
        pane.add(L, minsize=160)
        tk.Label(L, text=" Loyihalar", bg=BG2, fg=BLUE,
                 font=("Consolas", 11, "bold"), anchor="w").pack(fill="x", pady=4)
        self.tree = ttk.Treeview(L, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._tree_sel)
        s = ttk.Style()
        s.configure("Treeview", background=BG2, foreground=TEXT,
                    fieldbackground=BG2, borderwidth=0)

        # CENTER — LaTeX editor
        M = tk.Frame(pane, bg=BG)
        pane.add(M, minsize=400)
        tk.Label(M, text=" LaTeX Editor", bg=BG, fg=GREEN,
                 font=("Consolas", 11, "bold"), anchor="w").pack(fill="x")
        self.editor = tk.Text(M, bg="#1e1e1e", fg="#a6e3a1",
                              insertbackground=TEXT, font=("Consolas", 11),
                              wrap="none", undo=True, relief="flat")
        sb = ttk.Scrollbar(M, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True)
        self.editor.insert("1.0", "% LaTeX kodingiz bu yerda paydo bo'ladi\n% Yuqorida AI Yarat yoki Import tugmasini bosing\n")

        # RIGHT — PDF preview
        R = tk.Frame(pane, bg=BG2, width=380)
        pane.add(R, minsize=280)
        hdr = tk.Frame(R, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text=" PDF Preview", bg=BG2, fg=MAUVE,
                 font=("Consolas", 11, "bold"), anchor="w").pack(side="left")
        tk.Button(hdr, text="▶", command=self._next_pg,
                  bg=BG3, fg=TEXT, relief="flat", cursor="hand2").pack(side="right", padx=2)
        tk.Button(hdr, text="◀", command=self._prev_pg,
                  bg=BG3, fg=TEXT, relief="flat", cursor="hand2").pack(side="right")
        self.pg_lbl = tk.Label(hdr, text="0/0", bg=BG2, fg=TEXT, font=("Consolas", 9))
        self.pg_lbl.pack(side="right", padx=6)
        self.canvas = tk.Canvas(R, bg="#2a2a3a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

    def _build_statusbar(self):
        self.sv = tk.StringVar(value="✅ Tayyor | tectonic: " + TECTONIC)
        tk.Label(self, textvariable=self.sv, bg=BG3, fg=GREEN,
                 font=("Consolas", 9), anchor="w", padx=8).pack(fill="x", side="bottom")

    # ── TREE ─────────────────────────────────────────────────────────────────
    def _tree_refresh(self):
        self.tree.delete(*self.tree.get_children())
        for n in sorted(os.listdir(PROJECTS_DIR)):
            if n.endswith(".tex"):
                self.tree.insert("", "end", text=f" {n}",
                                 values=[os.path.join(PROJECTS_DIR, n)])

    def _tree_sel(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        if v:
            with open(v[0], encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.current_file = v[0]
            self.sv.set(f"Ochildi: {os.path.basename(v[0])}")

    # ── NEW ──────────────────────────────────────────────────────────────────
    def _new(self):
        n = f"journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"
        p = os.path.join(PROJECTS_DIR, n)
        tpl = offline_gen(self.tpl.get(), self.ttl.get(),
                          self.auth.get(), str(datetime.now().year),
                          "Kontent shu yerga.")
        with open(p, "w", encoding="utf-8") as f:
            f.write(tpl)
        self.current_file = p
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", tpl)
        self._tree_refresh()
        self.sv.set(f"Yangi: {n}")

    # ── IMPORT ───────────────────────────────────────────────────────────────
    def _import(self):
        p = filedialog.askopenfilename(
            filetypes=[("Fayllar", "*.txt *.docx *.pdf *.tex"), ("Barcha", "*.*")])
        if not p:
            return
        ext = os.path.splitext(p)[1].lower()
        try:
            if ext == ".txt":
                with open(p, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
            elif ext == ".docx":
                txt = "\n".join(par.text for par in Document(p).paragraphs)
            elif ext == ".pdf":
                txt = "\n".join(pg.get_text() for pg in fitz.open(p))
            elif ext == ".tex":
                with open(p, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                self.editor.delete("1.0", "end")
                self.editor.insert("1.0", txt)
                self.sv.set(f"Import: {os.path.basename(p)}")
                return
            else:
                messagebox.showwarning("Xato", "Fayl formati qo'llab-quvvatlanmaydi.")
                return
            self._ai_gen_from(txt)
        except Exception as e:
            messagebox.showerror("Import xato", str(e))

    # ── AI GENERATE ──────────────────────────────────────────────────────────
    def _ai_gen(self):
        content = self.editor.get("1.0", "end").strip()
        if not content or content.startswith("%"):
            content = f"Mavzu: {self.ttl.get()}\nMuallif: {self.auth.get()}"
        self._ai_gen_from(content)

    def _ai_gen_from(self, content):
        self.sv.set("🤖 AI ishlayapti...")
        def run():
            prompt = (f"Template: {self.tpl.get()}\nSarlavha: {self.ttl.get()}\n"
                      f"Muallif: {self.auth.get()}\nSana: {datetime.now().year}\n\n"
                      f"Kontent:\n{content[:3000]}\n\nToliq LaTeX hujjat yarat.")
            latex = ai_generate(prompt, lambda m: self.after(0, lambda: self.sv.set(m)))
            if latex is None:
                latex = offline_gen(self.tpl.get(), self.ttl.get(),
                                    self.auth.get(), str(datetime.now().year),
                                    content[:1500])
                self.after(0, lambda: self.sv.set("Offline rejim ishlatildi."))
            latex = clean_latex(latex)
            fn = f"{self.ttl.get().replace(' ','_')[:25]}_{datetime.now().strftime('%H%M%S')}.tex"
            fp = os.path.join(PROJECTS_DIR, fn)
            with open(fp, "w", encoding="utf-8") as f:
                f.write(latex)
            self.current_file = fp
            self.after(0, lambda: (
                self.editor.delete("1.0", "end"),
                self.editor.insert("1.0", latex),
                self._tree_refresh(),
                self.sv.set(f"✅ AI tayyor: {fn}")
            ))
        threading.Thread(target=run, daemon=True).start()

    # ── COMPILE ──────────────────────────────────────────────────────────────
    def _compile(self):
        latex = self.editor.get("1.0", "end").strip()
        if not latex or "documentclass" not in latex:
            messagebox.showwarning("Xato", "LaTeX kod yo'q!")
            return
        if not self.current_file:
            fn = f"journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"
            self.current_file = os.path.join(PROJECTS_DIR, fn)
        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write(latex)
        self.sv.set("⚙️ Compile bo'lmoqda...")
        def run():
            try:
                out_dir = os.path.dirname(self.current_file)
                r = subprocess.run(
                    [TECTONIC, self.current_file, "--outdir", out_dir],
                    capture_output=True, text=True, timeout=120
                )
                pdf = self.current_file.replace(".tex", ".pdf")
                if os.path.exists(pdf):
                    self.after(0, lambda: self._show_pdf(pdf))
                    self.after(0, lambda: self.sv.set("✅ Compile muvaffaqiyatli!"))
                else:
                    err = (r.stderr or "PDF yaratilmadi")[-300:]
                    self.after(0, lambda: self.sv.set(f"❌ {err}"))
            except FileNotFoundError:
                self.after(0, lambda: self.sv.set("❌ tectonic.exe topilmadi!"))
            except Exception as e:
                self.after(0, lambda: self.sv.set(f"❌ {str(e)[:100]}"))
        threading.Thread(target=run, daemon=True).start()

    # ── PDF PREVIEW ──────────────────────────────────────────────────────────
    def _show_pdf(self, path):
        try:
            doc = fitz.open(path)
            self.pdf_pages = []
            w = max(self.canvas.winfo_width(), 360)
            for page in doc:
                mat = fitz.Matrix(w / page.rect.width, w / page.rect.width)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                self.pdf_pages.append(ImageTk.PhotoImage(img))
            self.pdf_idx = 0
            self._draw_pg()
        except Exception as e:
            self.sv.set(f"PDF preview xato: {e}")

    def _draw_pg(self):
        if not self.pdf_pages:
            return
        img = self.pdf_pages[self.pdf_idx]
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=img)
        self.canvas.image = img
        self.pg_lbl.config(text=f"{self.pdf_idx+1}/{len(self.pdf_pages)}")

    def _prev_pg(self):
        if self.pdf_idx > 0:
            self.pdf_idx -= 1
            self._draw_pg()

    def _next_pg(self):
        if self.pdf_idx < len(self.pdf_pages) - 1:
            self.pdf_idx += 1
            self._draw_pg()

    # ── EXPORT ───────────────────────────────────────────────────────────────
    def _export(self, fmt):
        latex = self.editor.get("1.0", "end").strip()
        if not latex:
            messagebox.showwarning("Xato", "Editor bo'sh!")
            return
        p = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()}", f"*.{fmt}"), ("Barcha", "*.*")])
        if not p:
            return
        if fmt == "tex":
            with open(p, "w", encoding="utf-8") as f:
                f.write(latex)
            self.sv.set(f"✅ .tex saqlandi: {p}")
        elif fmt == "pdf":
            pdf = self.current_file.replace(".tex", ".pdf") if self.current_file else ""
            if pdf and os.path.exists(pdf):
                shutil.copy2(pdf, p)
                self.sv.set(f"✅ .pdf saqlandi: {p}")
            else:
                messagebox.showinfo("", "Avval Compile qiling!")

    # ── GITHUB ───────────────────────────────────────────────────────────────
    def _github(self):
        latex = self.editor.get("1.0", "end").strip()
        if not latex or "documentclass" not in latex:
            messagebox.showwarning("Xato", "LaTeX kod yo'q!")
            return
        fn  = f"output/journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"
        b64 = base64.b64encode(latex.encode()).decode()
        self.sv.set("📤 GitHub ga yuklanmoqda...")
        def run():
            try:
                r = requests.put(
                    f"https://api.github.com/repos/{GITHUB_REPO}/contents/{fn}",
                    headers={"Authorization": f"token {GITHUB_TOKEN}",
                             "Content-Type": "application/json"},
                    json={"message": f"Jurnal: {self.ttl.get()}", "content": b64},
                    timeout=30
                )
                if r.status_code in [200, 201]:
                    self.after(0, lambda: self.sv.set(f"✅ GitHub ga yuklandi!"))
                else:
                    msg = r.json().get("message", "")
                    self.after(0, lambda: self.sv.set(f"❌ GitHub: {msg}"))
            except Exception as e:
                self.after(0, lambda: self.sv.set(f"❌ {str(e)[:80]}"))
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
