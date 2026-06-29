"""
CLI integration tests using subprocess.

Run with: pytest tests/test_cli.py -v  (after `pip install -e .`)
"""

import json
import os
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest


def run_cli(args, cwd=None):
    """Run the tempus CLI and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "tempus_ddb.cli"] + args
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent / "python")
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, encoding="utf-8")
    return result.returncode, result.stdout, result.stderr


def test_cli_version():
    code, out, _ = run_cli(["--version"])
    assert code == 0
    assert "0.2.0-dev" in out or "tempus" in out.lower()


def test_cli_help():
    code, out, _ = run_cli(["--help"])
    assert code == 0
    assert "init" in out and "record" in out and "status" in out and "verify" in out


def test_cli_init_creates_files(tmp_path):
    code, out, _ = run_cli(["init"], cwd=tmp_path)
    assert code == 0
    assert (tmp_path / "keys.json").exists()
    assert (tmp_path / "tempus.db").exists()
    assert "ready" in out.lower()


def test_cli_status_before_and_after_init(tmp_path):
    code, out, _ = run_cli(["status"], cwd=tmp_path)
    assert code == 0
    assert "not found" in out.lower() or "Keys" in out

    run_cli(["init"], cwd=tmp_path)
    code2, out2, _ = run_cli(["status"], cwd=tmp_path)
    assert code2 == 0
    assert "Keys file" in out2 and "Database" in out2


def test_cli_record_genesis_and_verify(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    payload = json.dumps({"action": "test_cli", "value": 123})
    rules = json.dumps({"approved": True})

    code, out, _ = run_cli(["record", "--payload", payload, "--rules", rules, "--genesis"], cwd=tmp_path)
    assert code == 0
    assert "recorded successfully" in out.lower() or "success" in out.lower()

    code_v, out_v, _ = run_cli(["verify"], cwd=tmp_path)
    assert code_v == 0
    assert "valid" in out_v.lower() or "successful" in out_v.lower()


def test_cli_record_requires_payload_and_rules(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    code, out, err = run_cli(["record", "--payload", "{}", "--rules", ""], cwd=tmp_path)
    combined = (out + err).lower()
    assert code != 0
    assert "rules" in combined or "required" in combined


def test_cli_record_invalid_json(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    code, out, err = run_cli(["record", "--payload", "not-json", "--rules", '{}', "--genesis"], cwd=tmp_path)
    combined = (out + err).lower()
    assert code != 0
    assert "json" in combined


def test_cli_record_without_keys_fails(tmp_path):
    code, out, err = run_cli(["record", "--payload", "{}", "--rules", "{}", "--genesis"], cwd=tmp_path)
    combined = (out + err).lower()
    assert code != 0
    assert "keys" in combined or "init" in combined


def test_cli_status_after_record(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    run_cli(["record", "--payload", '{"a":1}', "--rules", "{}", "--genesis"], cwd=tmp_path)
    code, out, _ = run_cli(["status"], cwd=tmp_path)
    assert code == 0
    assert "Chain integrity" in out or "VALID" in out


def test_cli_record_multiple_and_verify(tmp_path):
    code_init, out_init, err_init = run_cli(["init"], cwd=tmp_path)
    assert code_init == 0, out_init + err_init

    code_1, out_1, err_1 = run_cli(["record", "--payload", '{"step":1}', "--rules", "{}", "--genesis"], cwd=tmp_path)
    assert code_1 == 0, out_1 + err_1

    code_2, out_2, err_2 = run_cli(["record", "--payload", '{"step":2}', "--rules", "{}"], cwd=tmp_path)
    assert code_2 == 0, out_2 + err_2

    code, out, err = run_cli(["verify"], cwd=tmp_path)
    assert code == 0, out + err
    assert "total_records" in out or "valid" in out.lower()


def test_cli_record_with_file_inputs(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    pfile = tmp_path / "p.json"
    rfile = tmp_path / "r.json"
    pfile.write_text(json.dumps({"from": "file"}))
    rfile.write_text(json.dumps({"ok": True}))

    code, out, _ = run_cli(
        ["record", "--payload", str(pfile), "--rules", str(rfile), "--genesis"], cwd=tmp_path
    )
    assert code == 0
    assert "recorded" in out.lower()


def test_cli_verify_reports_error_on_corrupt(tmp_path):
    run_cli(["init"], cwd=tmp_path)
    run_cli(["record", "--payload", "{}", "--rules", "{}", "--genesis"], cwd=tmp_path)
    db = tmp_path / "tempus.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("UPDATE decisions SET payload = ?", ('{"tampered":true}',))
        conn.commit()
    finally:
        conn.close()

    code, out, err = run_cli(["verify"], cwd=tmp_path)
    combined = (out + err).lower()
    assert code != 0 or "invalid" in combined or "error" in combined or "mismatch" in combined


def test_cli_status_shows_helpful_next_steps(tmp_path):
    code, out, _ = run_cli(["status"], cwd=tmp_path)
    assert code == 0
    assert "Next steps" in out or "init" in out.lower()