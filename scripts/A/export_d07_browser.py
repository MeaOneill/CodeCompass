"""A-owned deidentified automated UI export; cannot label an agent as a human."""
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.B.export_d05 import export


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();db=a.database.resolve();out=a.output.resolve()
    if not db.is_relative_to(ROOT/'tmp') or not db.name.startswith('A-D07-'):
        p.error('Use this task own A-D07 database under tmp')
    if not out.is_relative_to(ROOT/'experiments/A') or 'agent_browser' not in out.parts:
        p.error('Use an A-owned agent_browser partition and a new output directory')
    print(json.dumps(export(db,out,'agent_browser')))
