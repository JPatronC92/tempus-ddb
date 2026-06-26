"""Smoke tests for runnable example scripts."""

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    "basic_record.py",
    "verify_chain.py",
    "full_agent_flow.py",
]


def test_examples_run_successfully(tmp_path):
    env = os.environ.copy()
    python_path = str(REPO_ROOT / "python")
    env["PYTHONPATH"] = (
        python_path
        if not env.get("PYTHONPATH")
        else f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    )

    for example in EXAMPLES:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "examples" / example)],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"{example} failed with exit code {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
