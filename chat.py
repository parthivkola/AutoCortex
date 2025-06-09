import pyttsx3
import speech_recognition as sr
import requests
import json
import os
import re
import fitz
import spacy
import threading
import colorama
from colorama import Fore, Style
from datetime import datetime
from memory import save_interaction, get_recent_memory, get_memory_by_topic, reset_memory, remove_memory_by_topic

# Initialize colorama
colorama.init()

# ---------------- Keyword Extraction ----------------
nlp = spacy.load("en_core_web_sm")
custom_stopwords = {
    "what", "how", "is", "the", "in", "on", "tell", "me", "of", "a", "an",
    "thing", "info", "stuff", "topic", "information", "about", "can", "you",
    "please", "do", "does", "and", "to", "it", "this"
}

def extract_topic(user_input):
    doc = nlp(user_input)
    candidates = [
        token.text.lower()
        for token in doc
        if token.pos_ in {"NOUN", "PROPN"} and token.text.lower() not in custom_stopwords
    ]
    return candidates[0] if candidates else "general"

# ---------------------- Config ----------------------
OPENWEATHERMAP_API_KEY = "d2d6306d13faf7b56061f7dd9de3ed72"
DOCUMENTS_FOLDER = "./documents"
# memory_file removed per new storage system
facts_file = "facts.json"
feedback_file = "feedback_log.txt"
tasks_file = "tasks.json"
GNEWS_API_KEY = "0e08a801401a73410acbccffbb39561f"

# ------------------ Voice Input ---------------------
def get_voice_input():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            print(Fore.CYAN + "🎤 Listening..." + Style.RESET_ALL)
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
        return r.recognize_google(audio)
    except OSError:
        print(Fore.YELLOW + "⚠️ No microphone found. Switching to text input." + Style.RESET_ALL)
        return input(Fore.GREEN + "⌨️ You: " + Style.RESET_ALL).strip()
    except (sr.UnknownValueError, sr.WaitTimeoutError):
        print(Fore.YELLOW + "🤖 Didn't catch that. Please try again." + Style.RESET_ALL)
        return ""
    except sr.RequestError as e:
        print(Fore.RED + f"🤖 Speech error: {e}" + Style.RESET_ALL)
        return input(Fore.GREEN + "⌨️ You: " + Style.RESET_ALL).strip()

# ------------------ Voice Output --------------------
def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(Fore.RED + f"🔇 Voice error: {e}" + Style.RESET_ALL)

# ------------------ File Helpers --------------------
def load_text_file(filename, default=""):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return f.read()
    except Exception:
        pass
    return default

def save_text_file(filename, content):
    try:
        with open(filename, "w") as f:
            f.write(content)
    except Exception as e:
        print(Fore.RED + f"📁 File error: {e}" + Style.RESET_ALL)

def load_json_file(filename, default):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json_file(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(Fore.RED + f"📁 JSON error: {e}" + Style.RESET_ALL)

def save_feedback(q, a, fb):
    try:
        with open(feedback_file, "a") as f:
            f.write(f"Q: {q}\nA: {a}\nFeedback: {fb}\n\n")
    except Exception as e:
        print(Fore.RED + f"📝 Feedback error: {e}" + Style.RESET_ALL)

# ---------------- Context Builder -------------------
def build_context():
    context = ""
    try:
        if facts:
            context += "Here are some facts about the user:\n"
            for k, v in facts.items():
                context += f"- {k.replace('_', ' ').capitalize()}: {v}\n"
        recent_interactions = get_recent_memory(limit=3)
        for entry in recent_interactions:
            user_part = entry.get('user_input', '')
            assistant_part = entry.get('assistant_response', '')
            context += f"You: {user_part}\nAssistant: {assistant_part}\n"
    except Exception:
        pass
    return context

# ---------------- LLM via Ollama --------------------
def ask_ollama(prompt):
    context = build_context()
    current_topic = extract_topic(prompt)
    style = get_style_for_topic(current_topic)
    style_prefix = "[System: Respond concisely] " if style == "simple" else ""
    full_prompt = style_prefix + context + f"\nYou: {prompt}\nAssistant:"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": full_prompt, "stream": True},
            stream=True,
            timeout=20
        )
        if response.status_code != 200:
            return Fore.RED + f"⚠️ API error: {response.status_code}" + Style.RESET_ALL
    except requests.exceptions.RequestException as e:
        return Fore.RED + f"⚠️ Connection error: {str(e)}" + Style.RESET_ALL

    full_response = ""
    print(Fore.BLUE + "Assistant: " + Style.RESET_ALL, end='', flush=True)

    try:
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    part = data.get("response", "")
                    print(part, end='', flush=True)
                    full_response += part
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n⏹️ Reply stopped by user (Ctrl+C)" + Style.RESET_ALL)
        return full_response.strip() + " ...[stopped]"
    except requests.exceptions.Timeout:
        return Fore.RED + "⚠️ Response timed out" + Style.RESET_ALL

    print()  # Final newline
    return full_response

# ---------------- Feedback Tone Analysis ------------------
def analyze_feedback(feedback):
    if not feedback:
        return None
    feedback = feedback.lower()
    if any(kw in feedback for kw in ["shorter", "simplify", "simpler", "less", "brief"]):
        return "simple"
    elif any(kw in feedback for kw in ["more detail", "elaborate", "longer", "in depth", "detailed"]):
        return "detailed"
    return None

def ask_ollama(prompt):
    context = build_context()
    current_topic = extract_topic(prompt)
    style = get_style_for_topic(current_topic)
    style_prefix = "[System: Respond concisely] " if style == "simple" else ""
    full_prompt = style_prefix + context + f"\nYou: {prompt}\nAssistant:"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": full_prompt, "stream": True},
            stream=True,
            timeout=20
        )
        if response.status_code != 200:
            return Fore.RED + f"⚠️ API error: {response.status_code}" + Style.RESET_ALL
    except requests.exceptions.RequestException as e:
        return Fore.RED + f"⚠️ Connection error: {str(e)}" + Style.RESET_ALL

    full_response = ""
    print(Fore.BLUE + "Assistant: " + Style.RESET_ALL, end='', flush=True)

    try:
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    part = data.get("response", "")
                    print(part, end='', flush=True)
                    full_response += part
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n⏹️ Reply stopped by user (Ctrl+C)" + Style.RESET_ALL)
        return full_response.strip() + " ...[stopped]"
    except requests.exceptions.Timeout:
        return Fore.RED + "⚠️ Response timed out" + Style.RESET_ALL

    print()  # Final newline
    return full_response

# ------------------ Load Data -----------------------
facts = load_json_file(facts_file, {})
tasks = load_json_file(tasks_file, {"tasks": []})
def save_facts(facts): save_json_file(facts_file, facts)
def save_tasks(tasks): save_json_file(tasks_file, tasks)

# ------------------ Task Commands -------------------
def process_task_command(prompt):
    global tasks
    lower = prompt.lower()

    # Helper to extract task substring from prompt
    def extract_task(text):
        patterns = [
            r'"(.*?)"',             # Double-quoted tasks
            r"'(.*?)'",             # Single-quoted tasks
            r'task:\s*(.+)',        # "task: something"
            r'complete\s+(.+)',     # "complete something"
            r'finish\s+(.+)',       # "finish something"
            r'done\s+with\s+(.+)',  # "done with something"
            r'remove\s+(.+)',       # "remove something"
            r'delete\s+(.+)'        # "delete something"
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    # Add reminder or task
    if "remind me to " in lower:
        match = re.search(r'remind me to (.+)', prompt, re.IGNORECASE)
        if match:
            task_text = match.group(1).strip()
            tasks["tasks"].append({"task": task_text, "done": False})
            save_tasks(tasks)
            print(Fore.GREEN + f"✅ Reminder added: {task_text}" + Style.RESET_ALL)
        else:
            print(Fore.RED + "❌ Please specify a task to add" + Style.RESET_ALL)
        return True

    elif "add task" in lower or "new task" in lower:
        match = re.search(r'(?:add task|new task)\s+(.+)', prompt, re.IGNORECASE)
        if match:
            task_text = match.group(1).strip()
            tasks["tasks"].append({"task": task_text, "done": False})
            save_tasks(tasks)
            print(Fore.GREEN + f"✅ Task added: {task_text}" + Style.RESET_ALL)
        else:
            print(Fore.RED + "❌ Please specify a task to add" + Style.RESET_ALL)
        return True

    elif "add " in lower and ("todo" in lower or "to-do" in lower or "my tasks" in lower):
        match = re.search(r'add (.+?) to (?:my )?(?:to-?do list|tasks)', prompt, re.IGNORECASE)
        if match:
            task_text = match.group(1).strip()
            tasks["tasks"].append({"task": task_text, "done": False})
            save_tasks(tasks)
            print(Fore.GREEN + f"✅ Task added: {task_text}" + Style.RESET_ALL)
        return True

    elif "add " in lower:
        match = re.search(r'\badd\s+(.+)', prompt, re.IGNORECASE)
        if match:
            task_text = match.group(1).strip()
            tasks["tasks"].append({"task": task_text, "done": False})
            save_tasks(tasks)
            print(Fore.GREEN + f"✅ Task added: {task_text}" + Style.RESET_ALL)
        return True

    # List tasks
    elif ("list" in lower or "show" in lower or "to-do" in lower or "todo" in lower or
          "what do i need" in lower or "everything i need" in lower or "my tasks" in lower) and not any(x in lower for x in ["add", "delete", "remove", "complete", "finish", "done"]):
        if not tasks["tasks"]:
            print(Fore.YELLOW + "📋 No tasks." + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "📝 Your Tasks:" + Style.RESET_ALL)
            for t in tasks["tasks"]:
                status = Fore.GREEN + "✅" if t["done"] else Fore.YELLOW + "🔲"
                print(f"{status} {t['task']}" + Style.RESET_ALL)
        return True

    # Complete task (with partial/fuzzy matching)
    elif "complete" in lower or "done with" in lower or "finish" in lower:
        task_key = extract_task(lower)
        if not task_key:
            print(Fore.RED + "❌ Please specify a task" + Style.RESET_ALL)
            return True
        # Exact match
        removed_task = None
        for t in tasks["tasks"]:
            if t["task"].lower() == task_key.lower():
                t["done"] = True
                save_tasks(tasks)
                print(Fore.GREEN + f"🎉 Completed: {t['task']}" + Style.RESET_ALL)
                return True
        # Partial match
        partial_matches = [t for t in tasks["tasks"] if task_key.lower() in t["task"].lower()]
        if len(partial_matches) == 1:
            t = partial_matches[0]
            t["done"] = True
            save_tasks(tasks)
            print(Fore.GREEN + f"🎉 Completed: {t['task']}" + Style.RESET_ALL)
            return True
        elif len(partial_matches) > 1:
            print(Fore.YELLOW + "❓ Multiple tasks match. Please be more specific." + Style.RESET_ALL)
            return True
        # Fuzzy match
        try:
            from difflib import get_close_matches
            task_list = [t["task"] for t in tasks["tasks"]]
            matches = get_close_matches(task_key, task_list, n=1, cutoff=0.5)
            if matches:
                match = matches[0]
                for t in tasks["tasks"]:
                    if t["task"] == match:
                        t["done"] = True
                        save_tasks(tasks)
                        print(Fore.GREEN + f"🎉 Completed: {t['task']}" + Style.RESET_ALL)
                        return True
        except ImportError:
            pass
        print(Fore.RED + f"❌ Task not found: {task_key}" + Style.RESET_ALL)
        return True

    # Delete or remove task (with partial/fuzzy matching)
    elif "delete" in lower or "remove" in lower:
        task_key = extract_task(lower)
        if not task_key:
            print(Fore.RED + "❌ Please specify a task" + Style.RESET_ALL)
            return True
        # Exact match
        for t in tasks["tasks"]:
            if t["task"].lower() == task_key.lower():
                removed_task = t["task"]
                tasks["tasks"].remove(t)
                save_tasks(tasks)
                print(Fore.GREEN + f"🗑️ Removed: {removed_task}" + Style.RESET_ALL)
                return True
        # Partial match
        partial_matches = [t for t in tasks["tasks"] if task_key.lower() in t["task"].lower()]
        if len(partial_matches) == 1:
            t = partial_matches[0]
            removed_task = t["task"]
            tasks["tasks"].remove(t)
            save_tasks(tasks)
            print(Fore.GREEN + f"🗑️ Removed: {removed_task}" + Style.RESET_ALL)
            return True
        elif len(partial_matches) > 1:
            print(Fore.YELLOW + "❓ Multiple tasks match. Please be more specific." + Style.RESET_ALL)
            return True
        # Fuzzy match
        try:
            from difflib import get_close_matches
            task_list = [t["task"] for t in tasks["tasks"]]
            matches = get_close_matches(task_key, task_list, n=1, cutoff=0.5)
            if matches:
                match = matches[0]
                for t in tasks["tasks"]:
                    if t["task"] == match:
                        removed_task = t["task"]
                        tasks["tasks"].remove(t)
                        save_tasks(tasks)
                        print(Fore.GREEN + f"🗑️ Removed: {removed_task}" + Style.RESET_ALL)
                        return True
        except ImportError:
            pass
        print(Fore.RED + f"❌ Task not found: {task_key}" + Style.RESET_ALL)
        return True

    return False

# -------------- Extract & Store Facts ---------------
def extract_facts(prompt):
    global facts
    lowered = prompt.lower()
    patterns = {
        "name": r"\b(?:my name is|i am|call me)\s+([a-zA-Z ]+)",
        "likes": r"\bi (?:like|love|enjoy)\s+([a-zA-Z ]+)",
        "favorite_color": r"\b(?:my favorite color is|i love)\s+([a-zA-Z ]+)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, lowered)
        if match:
            value = match.group(1).strip().title()
            facts[key] = value
            print(Fore.CYAN + f"🧠 Learned: {key} = {value}" + Style.RESET_ALL)
            save_facts(facts)

# ------------------- API Plugins --------------------
def get_weather(city):
    city_clean = re.sub(r'\b(?:today|tomorrow|in|weather|for)\b', '', city, flags=re.IGNORECASE).strip()
    if not city_clean:
        return Fore.RED + "❌ Please specify a city" + Style.RESET_ALL
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city_clean}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if data.get("cod") != 200:
            return Fore.RED + f"❌ City not found: {city_clean}" + Style.RESET_ALL
        temp = data["main"]["temp"]
        desc = data["weather"][0]["description"]
        return f"🌦️ {city_clean.title()}: {desc}, {temp}°C"
    except Exception:
        return Fore.RED + "⚠️ Weather service unavailable" + Style.RESET_ALL

def get_definition(word):
    if len(word) <= 2 or word.lower() in custom_stopwords:
        return None
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        if isinstance(data, list) and data:
            meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
            return f"📖 {word}: {meaning}"
        return Fore.RED + f"❌ No definition for '{word}'" + Style.RESET_ALL
    except Exception:
        return Fore.RED + "⚠️ Dictionary unavailable" + Style.RESET_ALL

def get_joke():
    try:
        res = requests.get("https://official-joke-api.appspot.com/jokes/random", timeout=3)
        joke = res.json()
        return f"😂 {joke['setup']} — {joke['punchline']}"
    except Exception:
        return Fore.RED + "⚠️ Joke service down" + Style.RESET_ALL

def get_quote():
    try:
        res = requests.get("https://zenquotes.io/api/random", timeout=3)
        quote = res.json()[0]
        return f"💡 \"{quote['q']}\" — {quote['a']}"
    except Exception:
        return Fore.RED + "⚠️ Quote service down" + Style.RESET_ALL

def get_tech_news():
    try:
        url = f"https://gnews.io/api/v4/top-headlines?topic=technology&lang=en&token={GNEWS_API_KEY}"
        res = requests.get(url, timeout=3)
        articles = res.json().get("articles", [])[:3]
        if not articles:
            return "📰 No tech news"
        output = "🧠 Top Tech News:\n"
        for i, article in enumerate(articles, 1):
            output += f"{i}. {article['title']}\n"
        return output.strip()
    except Exception:
        return Fore.RED + "⚠️ News service down" + Style.RESET_ALL

# ------------------ Topic Memory Management ------------------
def get_style_for_topic(topic):
    entries = get_memory_by_topic(topic)
    if not entries:
        return None
    # Find most recent non-null style
    for entry in sorted(entries, key=lambda x: x['timestamp'], reverse=True):
        if entry.get('style'):
            return entry['style']
    return None

# ------------------ Command Handler -----------------
def process_command(prompt):
    global facts  # removed history
    lower = prompt.lower()

    # Memory commands
    if lower == "show memory":
        entries = get_recent_memory()
        if not entries:
            print(Fore.YELLOW + "❌ No recent memory" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "🧠 Recent Memory:" + Style.RESET_ALL)
            for m in entries:
                print(f"- You: {m['user_input'][:50]}...")
        return True

    if lower.startswith(("memory topic:", "show memory of")):
        topic = lower.split(":", 1)[-1].strip()
        results = get_memory_by_topic(topic)
        if results:
            print(Fore.CYAN + f"📚 Memory for '{topic}':" + Style.RESET_ALL)
            for r in results[:3]:
                print(f"- You: {r['user_input'][:50]}...")
        else:
            print(Fore.YELLOW + f"❌ No memory for '{topic}'" + Style.RESET_ALL)
        return True

    if lower.startswith("forget memory of "):
        topic = lower.replace("forget memory of ", "").strip()
        count = remove_memory_by_topic(topic)
        if count > 0:
            print(Fore.GREEN + f"🧹 Removed {count} memories" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + f"❌ No memories for '{topic}'" + Style.RESET_ALL)
        return True

    if "did we talk about" in lower:
        topic_match = re.search(r"did we talk about (.+)$", lower)
        if topic_match:
            topic = topic_match.group(1).strip().rstrip(' ?!.')
            results = get_memory_by_topic(topic)
            if results:
                print(Fore.CYAN + f"✅ Yes, {len(results)} discussions" + Style.RESET_ALL)
            else:
                print(Fore.YELLOW + f"❌ No discussions about '{topic}'" + Style.RESET_ALL)
        return True

    # Facts commands
    if lower.startswith("remember this:"):
        fact = prompt[15:].strip()
        facts.setdefault("custom_facts", []).append(fact)
        save_facts(facts)
        print(Fore.GREEN + "🧠 Fact remembered" + Style.RESET_ALL)
        return True

    elif lower.startswith("forget this:"):
        fact = prompt[13:].strip()
        if "custom_facts" in facts and fact in facts["custom_facts"]:
            facts["custom_facts"].remove(fact)
            save_facts(facts)
            print(Fore.GREEN + "🧽 Fact forgotten" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "🤔 Fact not found" + Style.RESET_ALL)
        return True

    elif lower.startswith("list facts"):
        if not facts:
            print(Fore.YELLOW + "🤷 I know nothing about you" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "🧠 What I know:" + Style.RESET_ALL)
            for key, value in facts.items():
                if key == "custom_facts":
                    print("- Custom facts:")
                    for fact in value[:3]:
                        print(f"  • {fact}")
                else:
                    print(f"- {key.replace('_', ' ').title()}: {value}")
        return True

    elif "weather" in lower:
        match = re.search(r'weather\s*(?:in|for)?\s*([a-zA-Z ]+)', prompt, re.IGNORECASE)
        if match:
            city = match.group(1).strip().strip(' ?!.')
            print(get_weather(city))
        else:
            print(Fore.RED + "❌ Please specify a city" + Style.RESET_ALL)
        return True

    elif lower.startswith("define "):
        word = prompt[7:].strip()
        definition = get_definition(word)
        if definition:
            print(definition)
        return True

    elif "joke" in lower:
        print(get_joke())
        return True

    elif "quote" in lower:
        print(get_quote())
        return True

    elif "tech news" in lower:
        print(get_tech_news())
        return True

    elif "what do you know about me" in lower:
        if not facts:
            print(Fore.YELLOW + "🤷 I know nothing about you" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + "🧠 What I know:" + Style.RESET_ALL)
            for key, value in facts.items():
                if key == "custom_facts":
                    print("- Custom facts:")
                    for fact in value[:3]:
                        print(f"  • {fact}")
                else:
                    print(f"- {key.replace('_', ' ').title()}: {value}")
        return True

    elif lower in ["help", "what can you do?"]:
        print_help()
        return True

    return process_task_command(prompt)

# ---------------- Reset All Memory ------------------
def reset_all():
    global facts, tasks  # removed history
    facts, tasks = {}, {"tasks": []}
    for file in [facts_file, tasks_file]:
        if os.path.exists(file):
            os.remove(file)
    reset_memory()
    print(Fore.GREEN + "🧼 Memory reset complete\n" + Style.RESET_ALL)

# ------------------ Help System --------------------
def print_help():
    help_text = f"""
{Fore.CYAN}🤖 Assistant Help:{Style.RESET_ALL}
{Fore.YELLOW}Basic Commands:{Style.RESET_ALL}
- help / what can you do? : Show this help
- exit/quit/bye : Exit program
- reset memory / forget everything : Clear all memory

{Fore.YELLOW}Information Services:{Style.RESET_ALL}
- weather in [city] : Get current weather
- define [word] : Get word definition
- joke : Tell a random joke
- quote : Get inspirational quote
- tech news : Show top tech headlines

{Fore.YELLOW}Task Management:{Style.RESET_ALL}
- add task [description] : Add new task
- list tasks : Show all tasks
- complete [task] : Mark task as done
- delete [task] : Remove task
"""
    print(help_text)

# ------------------- Main Loop ----------------------
print(Fore.CYAN + "🤖 Hello! I'm AutoCortex, your personal assistant." + Style.RESET_ALL)
print(Fore.YELLOW + "Type 'help' for commands." + Style.RESET_ALL)
print(Fore.YELLOW + "Type 'Ctrl + C' to stop reply." + Style.RESET_ALL)

try:
    use_voice = input(Fore.MAGENTA + "🗣️ Enable voice? (y/n): " + Style.RESET_ALL).strip().lower() == "y"
except:
    use_voice = False

while True:
    try:
        user_input = get_voice_input() if use_voice else input(Fore.GREEN + "You: " + Style.RESET_ALL).strip()
        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "bye"}:
            print(Fore.CYAN + "👋 Goodbye!" + Style.RESET_ALL)
            break

        if any(kw in user_input.lower() for kw in ["forget everything", "reset memory", "clear all"]):
            reset_all()
            continue

        if process_command(user_input):
            continue

        extract_facts(user_input)
        response = ask_ollama(user_input)

        if use_voice and response:
            speak_text(response)

        feedback = input(Fore.MAGENTA + "\n💬 Feedback (Enter to skip): " + Style.RESET_ALL).strip().lower()
        
        topic = extract_topic(user_input)
        style = analyze_feedback(feedback)
        save_interaction(user_input, response, feedback, topic=topic, style=style)

    except KeyboardInterrupt:
        print(Fore.RED + "\n🛑 Session ended" + Style.RESET_ALL)
        break
    except Exception as e:
        print(Fore.RED + f"⚠️ Error: {e}" + Style.RESET_ALL)
        continue
