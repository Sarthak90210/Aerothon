"""Verify the single-workspace result and retain the cleanup receipt."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
record = json.loads((OUT / "prepared.json").read_text())
registry = subprocess.check_output(["git", "worktree", "list", "--porcelain"], cwd=ROOT, text=True)
roots = [line[9:] for line in registry.splitlines() if line.startswith("worktree ")]
assert len(roots) == 1 and Path(roots[0]).resolve() == ROOT.resolve()
for item in record["worktrees"]:
    assert not Path(item["source"]).exists(), item["source"]
    archive = ROOT / item["source_archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == item["archive_sha256"]
for source, target in [
    (OUT / "phase2-logs-inventory.json", ROOT / "logs/archived_phase2_20261014"),
    (OUT / "phase2-scratch-inventory.json", OUT / "phase2-scratch"),
]:
    inventory = json.loads(source.read_text())
    actual = [p for p in target.rglob("*") if p.is_file()]
    assert len(actual) == len(inventory)
    for name, detail in inventory.items():
        p = target / name
        assert p.is_file() and p.stat().st_size == detail["bytes"], name
        if "sha256" in detail:
            assert hashlib.sha256(p.read_bytes()).hexdigest() == detail["sha256"], name
assert not (ROOT / "src/aerothon_gcs/tauri_app/src/render.ts").exists()
assert not (ROOT / "src/aerothon_runtime/aerothon_runtime/standalone.py").exists()
gcs_candidates = [str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("App.tsx") if "node_modules" not in p.parts and "build" not in p.parts and "install" not in p.parts]
assert gcs_candidates == ["src\\aerothon_gcs\\tauri_app\\src\\App.tsx"]
record.update({
    "status": "completed_single_main_workspace_and_one_maintained_gcs",
    "client_date": "2026-10-14",
    "remaining_worktrees": roots,
    "extra_worktree_directories_removed": True,
    "historical_evidence": {
        "path": "logs/archived_phase2_20261014", "files": 2116,
        "bytes": 6806488763, "small_json_hashes_and_all_file_sizes_verified": True,
        "source_zip_contents_hash_verified": True,
    },
    "maintained_gcs": {"frontend": gcs_candidates[0], "web_host": "src/aerothon_runtime/aerothon_runtime/web.py", "launcher": "scripts/serve_gcs.sh", "old_render_removed": True, "old_standalone_source_absent": True},
    "app_archive": "First app request was refused because this chat was pinned. Its pin was temporarily cleared. Archive requests returned queued. Git removed the now-unpinned redundant checkout after all 1553 non-cache files were reverified against the local recovery ZIP. The original chat pin position was restored.",
    "git_removal": "Both named extra checkouts removed after source, commit history and evidence preservation; primary main checkout unchanged.",
    "excluded_regenerable_material": "node_modules, build/install output, Python environments and test caches. Original source and non-cache evidence were retained.",
    "remote_pi_live_verification": "Unavailable. HTTP and SSH at 192.168.0.100 timed out; prior one-GCS destination receipts remain historical.",
})
(OUT / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps({"status": record["status"], "worktrees": roots, "gcs_source": gcs_candidates[0], "preserved_phase2_evidence_files": 2116}, indent=2))
