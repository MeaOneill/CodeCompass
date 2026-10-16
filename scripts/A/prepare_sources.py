"""Capture fixed local checkouts without executing their build systems."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
GIT = os.environ.get("CODECOMPASS_GIT", "git")
PINS = {
    "boltons": ("mahmoud/boltons", "4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d", "BSD-3-Clause", "LICENSE", "boltons/iterutils.py", "boltons"),
    "more-itertools": ("more-itertools/more-itertools", "4aeb4338ae1407d8da9723e86da99efeb446f719", "MIT", "LICENSE", "more_itertools/more.py", "more_itertools"),
    "click": ("pallets/click", "2247b35ea1c47c727d7a06e51fa280e12a863ff6", "BSD-3-Clause", "LICENSE.txt", "src/click/core.py", "click"),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    records = []
    for name, (repo, commit, license_id, license_path, module, package) in PINS.items():
        checkout = ROOT / "third_party/checkouts" / name
        actual = subprocess.check_output([GIT, "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        if actual != commit:
            raise ValueError(f"unexpected snapshot {name}: {actual}")
        def blob(path):
            return subprocess.check_output([GIT, "-C", str(checkout), "show", f"{commit}:{path}"])
        tracked = subprocess.check_output([GIT, "-C", str(checkout), "ls-tree", "-r", "--name-only", commit], text=True).splitlines()
        py = [x for x in tracked if x.endswith(".py")]
        target = blob(module)
        t0 = time.perf_counter()
        import_root = checkout / "src" if name == "click" else checkout
        proc = subprocess.run([sys.executable, "-B", "-c", "import sys;sys.path.insert(0,sys.argv[1]);m=__import__(sys.argv[2]);print(m.__file__)", str(import_root), package], capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        smoke_elapsed = time.perf_counter() - t0
        record = dict(name=name, url=f"https://github.com/{repo}", commit=commit,
                      license=license_id, license_path=license_path, license_sha256=sha(blob(license_path)),
                      retrieved_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      tracked_python_files=len(py), tracked_python_lines=sum(len(blob(x).splitlines()) for x in py),
                      target_module=module, target_module_lines=len(target.splitlines()),
                      metadata_install_estimate="pure Python; no runtime dependencies declared; build isolation needs flit_core (not run)",
                      package_install_status="NOT_RUN", import_exit_code=proc.returncode,
                      import_smoke_seconds=smoke_elapsed, import_stdout=proc.stdout.strip(), import_stderr=proc.stderr.strip(),
                      license_url=f"https://github.com/{repo}/blob/{commit}/{license_path}")
        records.append(record)
        if name == "boltons":
            dest = ROOT / "benchmarks/sources/boltons"
            inventory = []
            for path in ["LICENSE", "pyproject.toml", "boltons/iterutils.py", "tests/test_iterutils.py"]:
                data = blob(path)
                out = dest / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                inventory.append(dict(path=path, sha256=sha(data), bytes=len(data), git_blob=subprocess.check_output([GIT, "-C", str(checkout), "rev-parse", f"{commit}:{path}"], text=True).strip()))
            inventory.sort(key=lambda x:x["path"])
            digest = sha(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode())
            snapshot = dict(schema_version="1.0.0", object_type="RepoSnapshot", is_fixture=False, snapshot_id="boltons-"+commit[:12], url=record["url"], commit=commit, license=license_id, retrieved_at=record["retrieved_at"], hash=digest,
                            hash_scope="selected_files_manifest_sha256", files=inventory, license_path="LICENSE", snapshot_scope="partial_source_bundle", complete_checkout_included=False)
            (dest / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    out = ROOT / "benchmarks/sources/candidates.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(records, ensure_ascii=False, indent=2))
    assert all(x["import_exit_code"] == 0 for x in records)

if __name__ == "__main__":
    main()
