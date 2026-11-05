"""Verify the real-model lifecycle using a disposable schema in the testing database."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "project" / "backend"

if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_live_ai.py", "-q", "-p", "no:cacheprovider"],
        cwd=BACKEND,
    )
    sys.exit(result.returncode)
