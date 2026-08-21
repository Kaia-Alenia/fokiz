"""conftest.py — pytest configuration root for Fokiz."""
import sys
from pathlib import Path

# Add src/ to the Python path so tests can import app.* without installation.
sys.path.insert(0, str(Path(__file__).parent / "src"))
