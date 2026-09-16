from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _materialize_runner_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parent.parent
    repo_root = tmp_path / "repo"
    scripts = repo_root / "scripts"
    tests = repo_root / "tests"
    scripts.mkdir(parents=True)
    tests.mkdir()
    shutil.copy2(source_root / "scripts" / "run_tests.sh", scripts / "run_tests.sh")
    shutil.copy2(source_root / "scripts" / "run_tests_parallel.py", scripts / "run_tests_parallel.py")
    (tests / "test_probe.py").write_text("def test_probe():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "add", "scripts", "tests"], cwd=repo_root, check=True)
    return repo_root


def _python_path_with_current_interpreter(tmp_path: Path) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python3 = bin_dir / "python3"
    try:
        python3.symlink_to(sys.executable)
    except OSError:
        shutil.copy2(sys.executable, python3)
    return os.pathsep.join([str(bin_dir), os.environ.get("PATH", "")])


def test_run_tests_rejects_venv_that_only_finds_pytest_via_leaked_environment(tmp_path: Path) -> None:
    repo_root = _materialize_runner_repo(tmp_path)
    fake_python = repo_root / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "if [ -n \"${PYTHONPATH:-}\" ]; then exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = _python_path_with_current_interpreter(tmp_path)
    env["PYTHONPATH"] = str(tmp_path / "leaked-site")
    env["LOKI_TEST_WORKERS"] = "1"

    proc = subprocess.run(
        ["bash", "scripts/run_tests.sh", "tests/test_probe.py", "--file-retries", "0"],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stdout
    assert "skipping interpreter without hermetic pytest" in proc.stdout
    assert "No module named pytest" not in proc.stdout
    assert "1 tests passed" in proc.stdout


def test_run_tests_honors_explicit_test_interpreter(tmp_path: Path) -> None:
    repo_root = _materialize_runner_repo(tmp_path)
    poison_python = repo_root / ".venv" / "bin" / "python"
    poison_python.parent.mkdir(parents=True)
    poison_python.write_text("#!/usr/bin/env bash\nexit 91\n", encoding="utf-8")
    poison_python.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = _python_path_with_current_interpreter(tmp_path)
    env["LOKI_TEST_PYTHON"] = sys.executable
    env["LOKI_TEST_WORKERS"] = "1"

    proc = subprocess.run(
        ["bash", "scripts/run_tests.sh", "tests/test_probe.py", "--file-retries", "0"],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stdout
    assert f"using explicitly selected test interpreter: {sys.executable}" in proc.stdout
    assert "1 tests passed" in proc.stdout
