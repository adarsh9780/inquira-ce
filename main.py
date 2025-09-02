import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from inquira.main import run

if __name__ == "__main__":
    run()