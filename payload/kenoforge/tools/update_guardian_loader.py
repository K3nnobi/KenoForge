"""Import the existing hyphenated Guardian tool without running its CLI."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('kenoforge_update_guardian', Path(__file__).with_name('update-guardian.py'))
guardian = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardian)
