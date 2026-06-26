import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import anthropic
import requests
import base64
import json
import os
import threading
from datetime import datetime

# === SOZLAMALAR ===
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
GITHUB_REPO = "SHox1Developer/latex-journal-ai"
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"

TEMPLATES = {
    "Ilmiy maqola": "article",
    "Hisobot": "report",
    "Kitob": "book",
    "Taqdimot (Beamer)": "beamer",
}

SYSTEM_PROMPT = """Siz professional LaTeX muharrirsiz. 
Foydalanuvchi bergan ma'lumotlar asosida to'liq, kompilyatsiya qilinuvchi LaTeX hujjat yaratasiz.
Faqat LaTeX kodni qaytaring, boshqa hech narsa yozmang.
Hujjat \\documentclass bilan boshlanib \\end{document} bilan tugashi shart.
O'zbek tilini qo'llab-quvvatlash uchun babel yoki polyglossia paketini ishlating."""

class LaTeXJournalAI:
    def __init__(self, root):
        self.root = root
        self.root.title("LaTeX Journal AI 📄")
        self.root.geometry("900x700")
        self.root.configure(bg="#1e1e2e")
        self.setup_ui()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Consolas", 11))
        style.configure("TButton", background="#89b4fa", foreground="#1e1e2e", font=("Consolas", 11, "bold"))
        style.configure("TCombobox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4")

        # Sarlavha
        header = tk.Label(self.root, text="📄 LaTeX Journal AI", 
                         bg="#1e1e2e", fg="#89b4fa", 
                         font=("Consolas", 20, "bold"))
        header.pack(pady=15)

        # Asosiy frame
        main = tk.Frame(self.root, bg="#1e1e2e")
        main.pack(fill="both", expand=True, padx=20)

        # Chap panel
        left = tk.Frame(main, bg="#313244", width=280)
        left.pack(side="left", fill="y", padx=(0, 10), pady=5)
        left.pack_propagate(False)

        tk.Label(left, text="⚙️ Sozlamalar", bg="#313244", fg="#89b4fa",
                font=("Consolas", 13, "bold")).pack(pady=10)

        # Template
        tk.Label(left, text="Template:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10)
        self.template_var = tk.StringVar(value="Ilmiy maqola")
        template_cb = ttk.Combobox(left, textvariable=self.template_var, 
                                   values=list(TEMPLATES.keys()), state="readonly")
        template_cb.pack(fill="x", padx=10, pady=5)

        # Sarlavha
        tk.Label(left, text="Jurnal sarlavhasi:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10)
        self.title_entry = tk.Entry(left, bg="#45475a", fg="#cdd6f4", insertbackground="white")
        self.title_entry.insert(0, "Mening Jurnalim")
        self.title_entry.pack(fill="x", padx=10, pady=5)

        # Muallif
        tk.Label(left, text="Muallif:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10)
        self.author_entry = tk.Entry(left, bg="#45475a", fg="#cdd6f4", insertbackground="white")
        self.author_entry.insert(0, "Frank")
        self.author_entry.pack(fill="x", padx=10, pady=5)

        # Sana
        tk.Label(left, text="Sana:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10)
        self.date_entry = tk.Entry(left, bg="#45475a", fg="#cdd6f4", insertbackground="white")
        self.date_entry.insert(0, datetime.now().strftime("%Y"))
        self.date_entry.pack(fill="x", padx=10, pady=5)

        # API Key
        tk.Label(left, text="Anthropic API Key:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10, pady=(15,0))
        self.api_key_entry = tk.Entry(left, bg="#45475a", fg="#cdd6f4", show="*", insertbackground="white")
        self.api_key_entry.pack(fill="x", padx=10, pady=5)

        # GitHub Token
        tk.Label(left, text="GitHub Token:", bg="#313244", fg="#cdd6f4").pack(anchor="w", padx=10)
        self.gh_token_entry = tk.Entry(left, bg="#45475a", fg="#cdd6f4", show="*", insertbackground="white")
        self.gh_token_entry.pack(fill="x", padx=10, pady=5)

        # Tugmalar
        tk.Button(left, text="🤖 AI bilan LaTeX yarat", 
                 bg="#a6e3a1", fg="#1e1e2e", font=("Consolas", 11, "bold"),
                 command=self.generate_latex).pack(fill="x", padx=10, pady=(20,5))

        tk.Button(left, text="📤 GitHub ga yuklash", 
                 bg="#89b4fa", fg="#1e1e2e", font=("Consolas", 11, "bold"),
                 command=self.upload_to_github).pack(fill="x", padx=10, pady=5)

        tk.Button(left, text="💾 Lokal saqlash", 
                 bg="#fab387", fg="#1e1e2e", font=("Consolas", 11, "bold"),
                 command=self.save_locally).pack(fill="x", padx=10, pady=5)

        # O'ng panel
        right = tk.Frame(main, bg="#1e1e2e")
        right.pack(side="right", fill="both", expand=True, pady=5)

        # Kontent kiritish
        tk.Label(right, text="📝 Jurnal kontenti (nima haqida yozilsin):",
                bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.content_text = scrolledtext.ScrolledText(right, height=8,
                                                      bg="#313244", fg="#cdd6f4",
                                                      insertbackground="white",
                                                      font=("Consolas", 11))
        self.content_text.pack(fill="x", pady=5)
        self.content_text.insert("1.0", "Bu yerga jurnalingiz haqida ma'lumot kiriting...\nMasalan: bo'limlar, mavzular, asosiy g'oyalar...")

        # LaTeX natija
        tk.Label(right, text="📄 Yaratilgan LaTeX kod:",
                bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.latex_text = scrolledtext.ScrolledText(right, height=18,
                                                    bg="#1e1e1e", fg="#a6e3a1",
                                                    insertbackground="white",
                                                    font=("Consolas", 10))
        self.latex_text.pack(fill="both", expand=True, pady=5)

        # Status bar
        self.status_var = tk.StringVar(value="✅ Tayyor")
        status = tk.Label(self.root, textvariable=self.status_var,
                         bg="#313244", fg="#a6e3a1",
                         font=("Consolas", 10), anchor="w")
        status.pack(fill="x", padx=20, pady=5)

    def generate_latex(self):
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Xato", "Anthropic API Key kiriting!")
            return

        content = self.content_text.get("1.0", "end").strip()
        template = TEMPLATES[self.template_var.get()]
        title = self.title_entry.get()
        author = self.author_entry.get()
        date = self.date_entry.get()

        self.status_var.set("🤖 AI LaTeX yaratmoqda...")
        self.root.update()

        def run():
            try:
                client = anthropic.Anthropic(api_key=api_key)
                prompt = f"""Quyidagi ma'lumotlar asosida LaTeX hujjat yarat:

Template: {template}
Sarlavha: {title}
Muallif: {author}
Sana: {date}

Kontent:
{content}

To'liq, kompilyatsiya qilinuvchi LaTeX kodni yarat."""

                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )

                latex_code = message.content[0].text
                # Markdown code block ni tozalash
                if "```latex" in latex_code:
                    latex_code = latex_code.split("```latex")[1].split("```")[0].strip()
                elif "```" in latex_code:
                    latex_code = latex_code.split("```")[1].split("```")[0].strip()

                self.latex_text.delete("1.0", "end")
                self.latex_text.insert("1.0", latex_code)
                self.status_var.set("✅ LaTeX kod yaratildi! GitHub ga yuklashingiz mumkin.")
            except Exception as e:
                self.status_var.set(f"❌ Xato: {str(e)}")

        threading.Thread(target=run, daemon=True).start()

    def upload_to_github(self):
        gh_token = self.gh_token_entry.get().strip()
        if not gh_token:
            messagebox.showwarning("Xato", "GitHub Token kiriting!")
            return

        latex_code = self.latex_text.get("1.0", "end").strip()
        if not latex_code or "documentclass" not in latex_code:
            messagebox.showwarning("Xato", "Avval LaTeX kod yarating!")
            return

        filename = f"output/journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tex"
        content_b64 = base64.b64encode(latex_code.encode()).decode()

        self.status_var.set("📤 GitHub ga yuklanmoqda...")
        self.root.update()

        def run():
            try:
                url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
                headers = {
                    "Authorization": f"token {gh_token}",
                    "Content-Type": "application/json"
                }
                data = {
                    "message": f"📄 Yangi jurnal: {self.title_entry.get()}",
                    "content": content_b64
                }
                resp = requests.put(url, headers=headers, json=data)
                if resp.status_code in [200, 201]:
                    self.status_var.set("✅ GitHub ga yuklandi! PDF avtomatik build bo'lmoqda...")
                    messagebox.showinfo("Muvaffaqiyat!", 
                                       f"✅ Fayl yuklandi!\n\nhttps://github.com/{GITHUB_REPO}/actions\n\nPDF tayyor bo'lgach yuklab olishingiz mumkin.")
                else:
                    self.status_var.set(f"❌ GitHub xato: {resp.json().get('message', 'Noma`lum')}")
            except Exception as e:
                self.status_var.set(f"❌ Xato: {str(e)}")

        threading.Thread(target=run, daemon=True).start()

    def save_locally(self):
        latex_code = self.latex_text.get("1.0", "end").strip()
        if not latex_code:
            messagebox.showwarning("Xato", "LaTeX kod yo'q!")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".tex",
            filetypes=[("LaTeX fayl", "*.tex"), ("Barcha fayllar", "*.*")],
            initialfile=f"journal_{datetime.now().strftime('%Y%m%d')}.tex"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(latex_code)
            self.status_var.set(f"✅ Saqlandi: {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LaTeXJournalAI(root)
    root.mainloop()
