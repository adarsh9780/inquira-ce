import sys
import os

# Add full project to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from app.main import run

if __name__ == "__main__":
    run()
