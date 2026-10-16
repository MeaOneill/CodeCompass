"""Read-only machine/dependency/network probes with separate exit statuses."""
import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = ROOT / 'experiments/B/B-D01-20261016-environment'
    out.mkdir(parents=True, exist_ok=False)
    probes = {}
    commands = {
        'git_version': ['git', '--version'],
        'origin_refs': ['git', 'ls-remote', 'origin'],
        'pip_check': [sys.executable, '-m', 'pip', 'check'],
        'pip_freeze': [sys.executable, '-m', 'pip', 'freeze'],
        'hardware': ['powershell', '-NoProfile', '-Command', "@{os=(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture,TotalVisibleMemorySize);cpu=(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);display=(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM)} | ConvertTo-Json -Depth 5; if(-not $?){exit 1}"],
    }
    for name, command in commands.items():
        r = subprocess.run(command, cwd=ROOT, capture_output=True)
        (out / (name + '.stdout.txt')).write_bytes(r.stdout)
        (out / (name + '.stderr.txt')).write_bytes(r.stderr)
        probes[name] = {'command': command, 'exit_code': r.returncode}
    result = {'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'machine': platform.node(), 'owner': 'member B', 'executor': 'Codex Agent B', 'model_id': None, 'python_executable': sys.executable, 'python_version': platform.python_version(), 'platform': platform.platform(), 'machine_architecture': platform.machine(), 'logical_cpu': os.cpu_count(), 'disk_usage_bytes': shutil.disk_usage(ROOT)._asdict(), 'packages': {p: importlib.metadata.version(p) for p in ('jsonschema', 'pytest', 'Pillow', 'pip')}, 'probes': probes, 'cuda_runtime': None, 'gpu_compute_test': 'NOT_RUN', 'model_api': 'NOT_CONFIGURED_NOT_TESTED', 'other_machine_hardware': None}
    (out / 'environment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    wheels = [{'filename': f.name, 'sha256': __import__('hashlib').sha256(f.read_bytes()).hexdigest(), 'bytes': f.stat().st_size} for f in sorted((ROOT / 'tmp/B-D01-wheels').glob('*.whl'))]
    (out / 'wheel_manifest.json').write_text(json.dumps(wheels, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
