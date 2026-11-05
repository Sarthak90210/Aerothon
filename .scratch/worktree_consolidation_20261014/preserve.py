"""Preserve source and evidence before the user-requested worktree removal."""
import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(r"D:\MY DOCUMENTS\VIT\Team Rotor Fpv\AEROTHON").resolve()
OUT = ROOT / ".scratch" / "worktree_consolidation_20261014"
SOURCES = [
    ("pi-web-gcs", Path(r"C:\Users\sarth\.codex\worktrees\pi-web-gcs\AEROTHON")),
    ("phase2", Path(r"D:\MY DOCUMENTS\VIT\Team Rotor Fpv\AEROTHON_phase2")),
]
CACHES = {".git", "node_modules", "build", "install", "log", ".venv", "venv",
          "testenv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

OUT.mkdir(parents=True, exist_ok=True)
receipts = []
for label, source in SOURCES:
    source = source.resolve(strict=True)
    expected = dict(SOURCES)[label].resolve()
    if source != expected or source == ROOT:
        raise RuntimeError("Unexpected source or primary workspace")
    archive = OUT / f"{label}-source.zip"
    if archive.exists():
        raise RuntimeError(f"Refusing to overwrite {archive}")
    manifest = {}
    links = {}
    skipped = []
    status = git(source, "status", "--porcelain", "--untracked-files=all")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for base, dirs, files in os.walk(source, followlinks=False):
            relative = Path(base).relative_to(source)
            kept = []
            for name in dirs:
                p = Path(base) / name
                if name in CACHES or label == "phase2" and relative == Path(".") and name in {"logs", ".scratch"}:
                    skipped.append(str(p.relative_to(source)))
                elif p.is_symlink():
                    links[str(p.relative_to(source))] = os.readlink(p)
                else:
                    kept.append(name)
            dirs[:] = kept
            for name in files:
                p = Path(base) / name
                if name == ".git":
                    continue
                key = p.relative_to(source).as_posix()
                if p.is_symlink():
                    links[key] = os.readlink(p)
                    continue
                data = p.read_bytes()
                manifest[key] = {"sha256": sha(data), "bytes": len(data)}
                z.writestr(key, data)
        z.writestr("ARCHIVE_RECEIPT.json", json.dumps({"source": str(source), "head": git(source, "rev-parse", "HEAD"), "status": status, "files": manifest, "symlinks": links, "regenerable_or_separately_preserved": skipped}, indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError("Archive CRC failure")
        for key, detail in manifest.items():
            if sha(z.read(key)) != detail["sha256"]:
                raise RuntimeError(f"Archive hash failure: {key}")
    receipt = {"label": label, "source": str(source), "head": git(source, "rev-parse", "HEAD"), "source_archive": str(archive.relative_to(ROOT)), "archive_sha256": sha(archive.read_bytes()), "verified_files": len(manifest), "bytes_preserved": sum(x["bytes"] for x in manifest.values()), "status": status, "regenerable_or_separate": skipped}
    if label == "phase2":
        separately_preserved = []
        for name in ("logs", ".scratch"):
            folder = source / name
            inventory = {}
            for base, _, files in os.walk(folder):
                for file in files:
                    p = Path(base) / file
                    if p.is_file():
                        key = p.relative_to(folder).as_posix()
                        item = {"bytes": p.stat().st_size}
                        if p.suffix in {".json", ".jsonl"} and p.stat().st_size < 1_000_000:
                            item["sha256"] = sha(p.read_bytes())
                        inventory[key] = item
            inventory_path = OUT / f"phase2-{name.strip('.')}-inventory.json"
            inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
            separately_preserved.append({"folder": name, "files": len(inventory), "bytes": sum(v["bytes"] for v in inventory.values()), "inventory": str(inventory_path.relative_to(ROOT))})
        receipt["separately_preserve_before_removal"] = separately_preserved
    receipts.append(receipt)
bundle = OUT / "phase2-history.bundle"
if bundle.exists():
    raise RuntimeError("Refusing to overwrite history bundle")
subprocess.run(["git", "bundle", "create", str(bundle), "phase2-arena"], cwd=ROOT, check=True, capture_output=True)
subprocess.run(["git", "bundle", "verify", str(bundle)], cwd=ROOT, check=True, capture_output=True)
result = {"status": "source_archives_verified_evidence_moves_pending", "worktrees": receipts, "history_bundle": {"path": str(bundle.relative_to(ROOT)), "sha256": sha(bundle.read_bytes())}}
(OUT / "prepared.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"status": result["status"], "archives": [{k: v for k, v in x.items() if k in {"label", "verified_files", "archive_sha256", "bytes_preserved", "separately_preserve_before_removal"}} for x in receipts]}, indent=2))
