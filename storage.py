import json
import os

DATA_FILE = "data.json"


def load_data() -> dict:
    """Load persistent data from disk. Returns default structure if file missing."""
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_submission(data: dict):
    """Write data back to disk."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
