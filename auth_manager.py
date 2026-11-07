import json
import os
import hashlib

USERS_FILE = "users.json"
TASKS_FILE = "tasks_db.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {"password": hash_password("admin123"), "role": "admin"},
            "user": {"password": hash_password("user123"), "role": "user"}
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f)
            
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "w") as f:
            json.dump({}, f)

def login(username, password):
    init_db()
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    
    if username in users and users[username]["password"] == hash_password(password):
        return users[username]["role"]
    return None

def register(username, password):
    init_db()
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
        
    if username in users:
        return False
        
    users[username] = {"password": hash_password(password), "role": "user"}
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)
    return True

def get_user_tasks(username):
    init_db()
    with open(TASKS_FILE, "r") as f:
        all_tasks = json.load(f)
    return all_tasks.get(username, [])

def save_user_tasks(username, tasks):
    init_db()
    with open(TASKS_FILE, "r") as f:
        all_tasks = json.load(f)
    all_tasks[username] = tasks
    with open(TASKS_FILE, "w") as f:
        json.dump(all_tasks, f)

def get_all_system_tasks():
    init_db()
    with open(TASKS_FILE, "r") as f:
        all_tasks = json.load(f)
    
    # Flatten for admin view
    flat_tasks = []
    for user, tasks in all_tasks.items():
        for t in tasks:
            t["owner"] = user
            flat_tasks.append(t)
    return flat_tasks