# 🤖 AutoCortex – Local AI Assistant (Offline & Privacy-First)

AutoCortex is a fully offline, privacy-focused AI assistant that runs on your local machine — no internet or cloud calls required. Powered by open-source LLMs like Mistral (via Ollama), AutoCortex is designed to learn from your feedback, recall past conversations by topic, and even adapt its tone and personality.

---

## ✨ Features

- 💬 Chat with a fully local LLM (`mistral` via Ollama)
- 🧠 Memory tagging & topic recall (e.g. “What did we talk about Python?”)
- 🔁 Learns your feedback (e.g. “too long” → shorter replies next time)
- 📁 File search (search PDFs, text files)
- 🌤️ Weather, 📖 Dictionary, 😂 Jokes, 📰 Tech News, 🎤 Voice input/output
- 🎨 CLI or basic GUI (optional)
- 🔐 100% offline — **no cloud or tracking**

---

## ⚡️ Quick Start (for non-developers)

> Want to use AutoCortex without setting up anything? Just follow these simple steps:

1. ✅ Install [**Ollama**](https://ollama.com)  
   (Windows/macOS/Linux — one click install)

2. ✅ Double-click `autocortex.bat` to launch AutoCortex
   *(This starts Ollama + the assistant in one go)*

## 🧑‍💻 Developer Setup (for contributors)

> Clone and run the assistant manually.

```bash
git clone https://github.com/yourusername/AutoCortex.git
cd AutoCortex
python -m venv venv
venv\Scripts\activate       # or source venv/bin/activate on Linux
pip install -r requirements.txt
ollama serve
ollama pull mistral
python chat.py
```

---

## 📁 Folder Structure

```
autocortex/
├── chat.py                # Main interface
├── memory.py              # Memory manager
├── api_tools.py           # Jokes, dictionary, weather, etc.
├── requirements.txt       # Pip dependencies
├── autocortex.bat         # One-click launcher
├── facts.json             # User facts
├── memory.txt             # Session history (legacy)
├── interactions.json      # Persistent memory (TinyDB)
├── documents/             # For PDF/TXT search
└── knowledge_base/        # (optional) for local RAG
```

---

## 📌 Example Commands You Can Use

* `"What is Python?"` → get smart answer with memory
* `"Define recursion"` → dictionary lookup
* `"Weather in New York"` → real-time weather
* `"Search for 'AI' in files"` → local document search
* `"Add task: finish project"` / `"list tasks"` → to-do manager
* `"Can you show memory of Azure?"` → tagged memory recall
* `"Forget memory of jokes"` → deletes topic-specific history

---

## 📣 Feedback?

If you like AutoCortex, consider ⭐ starring the repo and sharing it!
Pull requests, issues, and feedback are welcome 🙌

---

## 📜 License

MIT License – free to use, modify and share.

```
---
Let me know if you want to add:
- Your name or GitHub profile
- A screenshot or demo GIF
- A logo or icon
- Advanced build instructions (`.exe`, `.bat`, etc.)

I'll update the README accordingly!
```
