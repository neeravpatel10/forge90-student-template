#!/usr/bin/env python3
"""Forge90 submission checker.

Checks one day's work in your repo against that day's checklist (checks/dayNN.json), prints what
passed and what did not, and gives an automatic completeness score out of 100.

Run it from the root of your work repo BEFORE you push:

    python check_submission.py day03          # check one day
    python check_submission.py --all          # check every day that has a folder

It needs only Python (nothing to install) and never calls the model or uses your API key.

IMPORTANT: the score measures COMPLETENESS and HYGIENE (files exist, code compiles, sections are
written, no secrets leaked, notebooks were saved after running). It does NOT judge how good your
answers are. Your instructor still reads your work.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # very old consoles: carry on with the default encoding
    pass

SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".ipynb_checkpoints", ".idea", ".vscode"}
TEXT_LIMIT = 2_000_000  # bytes; bigger files are skipped when scanning

# A Google API key is "AIza" followed by 35 more characters.
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{35}")
KEY_ASSIGN = re.compile(r"""GEMINI_API_KEY\s*=\s*["']?([A-Za-z0-9_\-]{20,})""")
PLACEHOLDER_HINTS = ("your", "xxx", "example", "placeholder", "paste", "<", "changeme", "insert")


# ---------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not (set(path.relative_to(root).parts) & SKIP_DIRS):
            yield path


def looks_like_placeholder(value: str) -> bool:
    low = value.lower()
    return any(hint in low for hint in PLACEHOLDER_HINTS)


def git(repo: Path, *args: str, timeout: int = 30) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                             errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def scan_for_secrets(repo: Path) -> list[str]:
    """Return human-readable problems: keys in files, a tracked .env, or a key hiding in git history."""
    problems: list[str] = []
    for path in iter_files(repo):
        if path.name == "check_submission.py":
            continue  # this file contains the patterns themselves
        try:
            if path.stat().st_size > TEXT_LIMIT:
                continue
        except OSError:
            continue
        text = read_text(path)
        rel = path.relative_to(repo).as_posix()
        if GOOGLE_KEY.search(text):
            problems.append(f"{rel}: contains something shaped like a Google API key")
            continue
        for match in KEY_ASSIGN.finditer(text):
            if not looks_like_placeholder(match.group(1)):
                problems.append(f"{rel}: GEMINI_API_KEY is set to a real-looking value")
                break

    tracked = git(repo, "ls-files")
    if tracked is not None:
        for name in tracked.splitlines():
            if Path(name).name == ".env" or name.endswith(".env"):
                problems.append(f"{name}: a .env file is tracked by git (it must be in .gitignore)")

    history = git(repo, "log", "--all", "-p", "--no-color", timeout=45)
    if history and GOOGLE_KEY.search(history):
        problems.append("git history: a Google-API-key-shaped string was committed at some point "
                        "(deleting the file is not enough: revoke that key)")
    return problems


# ---------------------------------------------------------------------------------------------
# notebook helpers
# ---------------------------------------------------------------------------------------------
def load_notebook(path: Path):
    try:
        return json.loads(read_text(path)), None
    except (json.JSONDecodeError, OSError) as error:
        return None, f"not a valid notebook ({error.__class__.__name__})"


def code_cells(nb) -> list[dict]:
    return [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]


def outputs_text(nb) -> str:
    parts = []
    for cell in code_cells(nb):
        for out in cell.get("outputs", []):
            if "text" in out:
                parts.append("".join(out["text"]))
            data = out.get("data", {})
            if "text/plain" in data:
                parts.append("".join(data["text/plain"]))
    return "\n".join(parts)


def markdown_text(nb) -> str:
    return "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []) if c.get("cell_type") == "markdown")


# ---------------------------------------------------------------------------------------------
# check implementations. Each returns (fraction_earned 0..1, detail_text)
# ---------------------------------------------------------------------------------------------
def all_or_nothing(ok: bool, detail_ok: str, detail_bad: str):
    return (1.0, detail_ok) if ok else (0.0, detail_bad)


def proportion(found: list[str], missing: list[str], what: str):
    total = len(found) + len(missing)
    frac = len(found) / total if total else 1.0
    if missing:
        return frac, f"missing {what}: " + ", ".join(missing)
    return frac, "all present"


def run_check(check: dict, ctx: dict):
    kind = check["type"]
    day_dir: Path = ctx["day_dir"]
    repo: Path = ctx["repo"]
    path = day_dir / check["path"] if "path" in check else None

    if kind == "no_secrets":
        problems = ctx["secrets"]
        return all_or_nothing(not problems, "no keys found", "; ".join(problems[:3]) + (" ..." if len(problems) > 3 else ""))

    if path is not None and kind != "file_exists" and not path.exists():
        return 0.0, f"{check['path']} not found"

    if kind == "file_exists":
        return all_or_nothing(path.exists() and path.stat().st_size > 0, "found",
                              f"{check['path']} is missing" if not path.exists() else f"{check['path']} is empty")

    if kind == "min_words":
        n = words(read_text(path))
        return all_or_nothing(n >= check["words"], f"{n} words", f"only {n} words, expected at least {check['words']}")

    if kind == "sections":  # every regex must match somewhere (case-insensitive); partial credit
        text = read_text(path)
        found = [p for p in check["patterns"] if re.search(p, text, re.I | re.M)]
        missing = [p for p in check["patterns"] if p not in found]
        return proportion(found, missing, "sections")

    if kind == "contains_all":  # same idea, for code or text
        text = read_text(path)
        found = [p for p in check["patterns"] if re.search(p, text, re.I | re.M)]
        missing = [p for p in check["patterns"] if p not in found]
        return proportion(found, missing, "expected pieces")

    if kind == "count_at_least":
        n = len(re.findall(check["pattern"], read_text(path), re.I | re.M))
        return all_or_nothing(n >= check["count"], f"{n} found", f"found {n}, expected at least {check['count']}")

    if kind == "py_compiles":
        try:
            compile(read_text(path), str(path), "exec")
        except SyntaxError as error:
            return 0.0, f"syntax error on line {error.lineno}"
        return 1.0, "compiles"

    if kind == "py_runs":
        try:
            done = subprocess.run([sys.executable, path.name], cwd=path.parent, capture_output=True,
                                  text=True, errors="replace", timeout=check.get("timeout", 30))
        except subprocess.TimeoutExpired:
            return 0.0, "took too long to run"
        tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or [""]
        return all_or_nothing(done.returncode == 0, "runs and its own tests pass", f"exit code {done.returncode}: {tail[0][:120]}")

    if kind.startswith("notebook_"):
        nb, error = load_notebook(path)
        if error:
            return 0.0, error
        if kind == "notebook_valid":
            n = len(nb.get("cells", []))
            return all_or_nothing(n >= check.get("cells", 1), f"{n} cells", f"only {n} cells")
        cells = code_cells(nb)
        if kind == "notebook_executed":
            ran = sum(1 for c in cells if c.get("execution_count") is not None)
            frac = ran / len(cells) if cells else 0
            return all_or_nothing(frac >= check.get("min_fraction", 0.9), f"{ran}/{len(cells)} code cells were run",
                                  f"only {ran}/{len(cells)} code cells were run: run all cells, then SAVE the notebook")
        if kind == "notebook_no_errors":
            errs = [o for c in cells for o in c.get("outputs", []) if o.get("output_type") == "error"]
            if errs:
                return 0.0, f"{len(errs)} cell(s) ended in an error (e.g. {errs[0].get('ename')})"
            return 1.0, "no error cells"
        if kind == "notebook_outputs_contain":
            text = outputs_text(nb)
            found = [p for p in check["patterns"] if re.search(p, text, re.I)]
            missing = [p for p in check["patterns"] if p not in found]
            return proportion(found, missing, "saved outputs")
        if kind == "notebook_text_absent":  # placeholder text the student was meant to replace
            text = markdown_text(nb)  # only the written cells: a leftover "# TODO" comment in code is not a placeholder
            left = [p for p in check["patterns"] if re.search(p, text)]
            return all_or_nothing(not left, "placeholders replaced", "still has TODO placeholder text: " + ", ".join(left))

    return 0.0, f"unknown check type {kind!r} (ask the instructor)"


# ---------------------------------------------------------------------------------------------
# a whole day
# ---------------------------------------------------------------------------------------------
def load_spec(specs_dir: Path, day: str):
    path = specs_dir / f"{day}.json"
    if not path.exists():
        return None
    return json.loads(read_text(path))


def check_day(repo: Path, day: str, specs_dir: Path, secrets: list[str] | None = None) -> dict:
    spec = load_spec(specs_dir, day)
    if spec is None:
        return {"day": day, "status": "NO SPEC", "score": 0, "max": 0, "items": [], "secrets": [], "title": day}
    day_dir = repo / day
    if secrets is None:
        secrets = scan_for_secrets(repo)
    result = {"day": day, "title": spec.get("title", day), "pass_mark": spec.get("pass_mark", 80),
              "secrets": secrets, "items": [], "score": 0.0, "max": sum(c["points"] for c in spec["checks"])}
    if not day_dir.is_dir() or not any(p.is_file() and p.name != ".gitkeep" for p in day_dir.rglob("*")):
        result.update(status="NOT SUBMITTED")
        return result
    ctx = {"day_dir": day_dir, "repo": repo, "secrets": secrets}
    for check in spec["checks"]:
        try:
            frac, detail = run_check(check, ctx)
        except Exception as error:  # never let one odd file stop the whole report
            frac, detail = 0.0, f"could not check ({error.__class__.__name__}: {error})"
        earned = round(check["points"] * frac, 1)
        result["items"].append({"label": check["label"], "points": check["points"], "earned": earned,
                                "ok": frac >= 0.999, "detail": detail})
        result["score"] += earned
    result["score"] = round(result["score"], 1)
    if secrets:
        result["status"] = "BLOCKED"
    elif result["score"] >= result["pass_mark"]:
        result["status"] = "COMPLETE"
    else:
        result["status"] = "PARTIAL"
    return result


def print_report(r: dict) -> None:
    print(f"\n{r['title']}")
    print("=" * len(r["title"]))
    if r["status"] == "NO SPEC":
        print(f"No checklist found for {r['day']}. Make sure you have the latest checks/ folder.")
        return
    if r["status"] == "NOT SUBMITTED":
        print(f"Nothing found in {r['day']}/ yet. Put this day's files there, then run this again.")
        return
    for item in r["items"]:
        mark = "ok " if item["ok"] else "-- "
        print(f"  [{mark}] {item['earned']:>5}/{item['points']:<3} {item['label']}"
              + ("" if item["ok"] else f"\n              -> {item['detail']}"))
    print(f"\n  Score: {r['score']}/{r['max']}   (complete at {r['pass_mark']}+)   Status: {r['status']}")
    if r["secrets"]:
        print("\n  !! POSSIBLE SECRET FOUND. Read this before you push anything:")
        for problem in r["secrets"]:
            print(f"     - {problem}")
        print("     Revoke that key at aistudio.google.com/apikey and create a new one. Never push a real key.")
    print("  Reminder: this score measures completeness and hygiene, not quality. Your instructor still reads your work.")


def days_with_folders(repo: Path, specs_dir: Path) -> list[str]:
    names = sorted(p.stem for p in specs_dir.glob("day*.json"))
    return [d for d in names if (repo / d).is_dir()]


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Check a day's submission and print an automatic completeness score.")
    ap.add_argument("day", nargs="?", help="for example day03 (omit with --all)")
    ap.add_argument("--all", action="store_true", help="check every day that has a folder")
    ap.add_argument("--repo", default=str(here), help="repo root (instructor use)")
    ap.add_argument("--specs", default=None, help="folder with the checklists (instructor use: your own copy)")
    ap.add_argument("--json", action="store_true", help="print machine-readable results")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    specs = Path(args.specs).resolve() if args.specs else repo / "checks"
    if not args.day and not args.all:
        ap.print_help()
        return 2
    days = days_with_folders(repo, specs) if args.all else [args.day.lower()]
    secrets = scan_for_secrets(repo)  # scanned once, shared by every day
    results = [check_day(repo, d, specs, secrets) for d in days]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print_report(r)
    return 1 if any(r["status"] == "BLOCKED" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
