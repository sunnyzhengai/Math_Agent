
import os, sys, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)
