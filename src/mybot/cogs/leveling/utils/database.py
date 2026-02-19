import json
import os
import time

DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "levels.json")

class Database:

    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        os.makedirs(DATA_FOLDER, exist_ok=True)

        # ensure file exists
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # try to load JSON; if invalid (empty/corrupt), back it up and reinitialize
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # backup corrupt file
            backup_name = DATA_FILE + f".bad-{int(time.time())}"
            try:
                os.replace(DATA_FILE, backup_name)
            except Exception:
                pass
            # create fresh file
            self.data = {}
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f)

    def save(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_user(self, user_id):
        user_id = str(user_id)

        if user_id not in self.data:
            self.data[user_id] = {
                "xp": 0,
                "level": 1,
                "messages": 0,
                "voice_time": 0,
                "achievements": []
            }

        return self.data[user_id]
