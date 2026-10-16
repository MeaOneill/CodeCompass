"""Read-only audit of D02 graph outputs, provenance, fixtures, and figure files."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from codecompass.graph import read_snapshot, validate_span, cyclic_components


def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
 out=ROOT/'experiments/A'/a.run_id
 load=lambda p:json.loads(p.read_text(encoding='utf-8'))
 snap=load(ROOT/'benchmarks/sources/boltons/snapshot.json');contents=read_snapshot(ROOT/'benchmarks/sources/boltons',snap)
 for row in load(out/'input_manifest.json'):
  assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
 nodes=load(out/'nodes.json');edges=load(out/'edges.json');ids={n['id'] for n in nodes};assert len(ids)==len(nodes)
 for obj in nodes+edges:validate_span(obj['source_span'],snap,contents)
 for e in edges:
  assert e['from'] in ids and (e['to'] is None or e['to'] in ids)
  if e['kind']=='call_unknown':assert e['resolution']=='unknown' and e['to'] is None
 teaching=load(out/'teaching_edges.json');assert len(teaching)==2
 assert all(not e['hard'] and e['provenance']['review_status']=='pending' and e['provenance']['reviewer'] is None for e in teaching)
 fixture=load(out/'controlled_fixture.json');assert fixture['is_fixture']
 assert fixture['cycle_components']==cyclic_components({u['id'] for u in fixture['units']},[(e['from'],e['to']) for e in fixture['teaching_edges']])==[['cycle_X','cycle_Y']]
 assert fixture['fixture_mastered_concepts']==['iterator']
 assert len([u for u in fixture['units'] if 'chunk_behavior' in u['concept_ids']])==2
 figures=ROOT/'report_materials/A/A-D02'
 for name in ['F01_architecture','F02_source_graph','F02_controlled_fixture']:
  with Image.open(figures/(name+'.png')) as im:
   im.verify()
  with Image.open(figures/(name+'.png')) as im:assert all(abs(d-300)<.1 for d in im.info['dpi'])
  svg=ET.parse(figures/(name+'.svg')).getroot()
  assert svg.findall('{http://www.w3.org/2000/svg}text')
  assert not svg.findall('.//{http://www.w3.org/2000/svg}image')
 print(json.dumps({'source_spans_verified':len(nodes)+len(edges),'nodes':len(nodes),'edges':dict(Counter(e['kind'] for e in edges)),'hard_teaching_edges':0,'synthetic_cycle_preserved':True,'png_svg_pairs_verified':3,'input_hashes_verified':True,'evidence_type':'development_validation','independent_review':'NOT_REVIEWED'},indent=2))

if __name__=='__main__':main()
