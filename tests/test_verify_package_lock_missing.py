from pathlib import Path
import shutil
import subprocess


def test_verify_package_lock_skips_when_root_lock_is_absent(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    scripts_directory = tmp_path / "scripts"
    scripts_directory.mkdir()

    shutil.copy2(repository_root / "scripts" / "verify-package-lock.mjs", scripts_directory / "verify-package-lock.mjs")
    shutil.copy2(repository_root / "package.json", tmp_path / "package.json")

    completed_process = subprocess.run(
        ["node", str(scripts_directory / "verify-package-lock.mjs")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed_process.returncode == 0
    assert "verification skipped" in completed_process.stderr
    assert "root package-lock.json is not present" in completed_process.stderr
