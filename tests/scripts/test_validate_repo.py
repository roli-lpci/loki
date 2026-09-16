from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_repo.py"
SPEC = importlib.util.spec_from_file_location("validate_repo", SCRIPT)
assert SPEC and SPEC.loader
validate_repo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_repo)


def test_quick_pytest_uses_current_interpreter_when_pytest_is_available():
    with patch.object(validate_repo, "interpreter_can_import", return_value=True):
        command = validate_repo.quick_pytest_command(["-q", "tests/example.py"])

    assert command == [validate_repo.sys.executable, "-m", "pytest", "-q", "tests/example.py"]


def test_quick_pytest_falls_back_to_uv_overlay_when_active_python_lacks_pytest():
    with (
        patch.object(validate_repo, "interpreter_can_import", return_value=False),
        patch.object(validate_repo.shutil, "which", return_value="/usr/local/bin/uv"),
    ):
        command = validate_repo.quick_pytest_command(["-q", "tests/example.py"])

    assert command == [
        "/usr/local/bin/uv",
        "run",
        "--with",
        "pytest",
        "python",
        "-m",
        "pytest",
        "-q",
        "tests/example.py",
    ]
