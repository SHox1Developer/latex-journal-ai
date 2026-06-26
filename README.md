# 📄 LaTeX Journal AI

> AI yordamida professional LaTeX jurnallar yaratuvchi desktop ilova

## 🚀 Imkoniyatlar

- 🤖 Claude AI orqali avtomatik LaTeX kod generatsiya
- 📤 GitHub ga avtomatik yuklash
- ⚙️ GitHub Actions orqali PDF build
- 💾 Lokal saqlash imkoniyati
- 🎨 Bir nechta template (maqola, hisobot, kitob, taqdimot)

## 📦 O'rnatish

```bash
pip install anthropic requests
python app.py
```

## 🔧 Sozlash

1. [Anthropic API Key](https://console.anthropic.com) oling
2. GitHub Personal Access Token yarating
3. Ilovani ishga tushiring va tokenlarni kiriting

## 📖 Ishlatish

1. Template tanlang
2. Sarlavha, muallif va sana kiriting
3. Jurnal kontentini yozing
4. **"AI bilan LaTeX yarat"** tugmasini bosing
5. **"GitHub ga yuklash"** tugmasini bosing
6. GitHub Actions da PDF avtomatik build bo'ladi!

## 🏗️ Arxitektura

```
Desktop App (Python/Tkinter)
    ↓
Claude API (LaTeX generatsiya)
    ↓
GitHub API (fayl yuklash)
    ↓
GitHub Actions (PDF build)
    ↓
PDF artifact (yuklab olish)
```

## 👨‍💻 Muallif

**Frank** | SHox1Developer
