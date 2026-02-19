import json
import os

DATA_FOLDER = "data"
DATA_FILE = os.path.join(DATA_FOLDER, "levels.json")

class Database:

    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump({}, f)

        with open(DATA_FILE, "r") as f:
            self.data = json.load(f)

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
