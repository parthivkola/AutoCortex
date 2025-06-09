# memory.py (optimized version)
from tinydb import TinyDB, Query
from datetime import datetime
import os

# Database location
DB_FILE = "interactions.json"
db = TinyDB(DB_FILE)

# Save one interaction with topic and tags
def save_interaction(user_input, assistant_response, feedback, tags=[], topic="general", style="default"):
    try:
        db.insert({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:200],  # Limit input size
            "assistant_response": assistant_response[:500],  # Limit response size
            "feedback": feedback[:100],  # Limit feedback size
            "tags": tags,
            "topic": topic,
            "style": style
        })
    except Exception:
        pass  # Fail silently

# Return most recent N conversations
def get_recent_memory(limit=5):
    try:
        entries = db.all()
        return sorted(entries, key=lambda k: k['timestamp'], reverse=True)[:limit]
    except Exception:
        return []

# Get interactions by topic
def get_memory_by_topic(topic):
    try:
        return db.search(Query().topic == topic)
    except Exception:
        return []

# Clear database
def reset_memory():
    try:
        db.truncate()
    except Exception:
        pass

# Remove interactions by topic
def remove_memory_by_topic(topic):
    try:
        query = Query()
        records = db.search(query.topic == topic)
        db.remove(query.topic == topic)
        return len(records)
    except Exception:
        return 0
