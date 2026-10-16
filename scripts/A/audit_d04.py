"""Strict saved-artifact audit. Independent of all search success decisions."""
import argparse,copy,hashlib,json,sys,traceback,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from codecompass.learner import mastery_gate,planning_rows
from codecompass.graph import read_snapshot,validate_span
from codecompass.planner.comparison_validator import verify_result,verify_certificate

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Invalid run ID')
    source=ROOT/'experiments/A'/a.run_id;output=ROOT/a.output
    if not output.resolve().is_relative_to((ROOT/'experiments/A').resolve()):p.error('Audit output must be in experiments/A')
    if output.exists():p.error('Refusing to overwrite audit')
    load=lambda p:json.loads(p.read_text(encoding='utf-8'));checks=[];mutations=0
    def check(label,value):
        checks.append({'check':label,'passed':bool(value)})
        if not value:raise AssertionError(label)
    try:
        summary=load(source/'summary.json');check('mechanism only',not summary['formal_study_ready'] and summary['human_profiles']==0 and summary['learning_effect']=='NOT_MEASURED')
        for row in load(source/'input_manifest.json'):
            for key in ('path','frozen_copy'):check('byte hash '+row[key],hashlib.sha256((ROOT/row[key]).read_bytes()).hexdigest()==row['sha256'])
        old=load(ROOT/'experiments/A/A-D03-short-tests04/input_manifest.json');core=next(r for r in old if r['path']=='src/codecompass/planner/core.py');check('strong B2 exact original bytes',hashlib.sha256((ROOT/core['path']).read_bytes()).hexdigest()==core['sha256'])
        snap=load(ROOT/'benchmarks/sources/boltons/snapshot.json');contents=read_snapshot(ROOT/'benchmarks/sources/boltons',snap);groups={}
        for row in summary['comparisons']:groups.setdefault(row['case_id'],[]).append(row)
        check('18 common-input comparisons / 54 outcomes',len(groups)==18 and len(summary['comparisons'])==54)
        for name,rows in groups.items():
            folder=source/'cases'/name;f=load(folder/'input.json');req=f['request'];units=f['units'];state=f['state'];config=f['config']
            check('simulated profile '+name,state['is_simulated'] is True and req['is_fixture'] is True and f['is_simulated'] is True)
            check('raw ledger matches request '+name,planning_rows(state,req['snapshot_id'],quantile=config['quantile'],allow_simulated=True)==req['learner_state'])
            gate=mastery_gate(state,req['snapshot_id'],{c for u in units for c in u['concept_ids']}|set(req['target_concept_ids']),threshold=config['threshold'],quantile=config['quantile'],allow_simulated=True)
            cert=load(folder/'certificate.json');ca=verify_certificate(req,units,gate,cert);check('independent complete exact certificate '+name,ca['valid'])
            for u in units:
                if not u['is_fixture']:
                    check('real edges stay soft '+name,not any(e['hard'] for e in u['prerequisites']))
                    for span in u['source_spans']:validate_span(span,snap,contents)
            for row in rows:
                data=load(folder/(row['method']+'.json'));result=data['result'];details=data['details'];audit=verify_result(req,units,result,gate,details.get('certificate'))
                check('independent route '+name+'/'+row['method'],audit['valid'] and details['gate']==gate and details['replay_audit']==audit)
                check('summary and raw agree '+name+'/'+row['method'],row['status']==result['status'] and row['route']==result['ordered_units'] and row['partial_proxy_cost']==result['estimated_cost'])
                check('no human success/time '+name+'/'+row['method'],row['human_task_success'] is None and row['human_elapsed_minutes'] is None)
                expected_cost=result['estimated_cost'] if result['status']=='FEASIBLE' else None
                check('missing not zero; exact gap '+name+'/'+row['method'],row['feasible_proxy_cost']==expected_cost and row['exact_proxy_cost']==ca['optimal_cost'] and row['additive_cost_gap']==(expected_cost-ca['optimal_cost'] if expected_cost is not None and ca['optimal_cost'] is not None else None))
                if row['method']=='beam':check('beam not optimal '+name,not row['optimality_claim'] and not details['optimality_claim'])
                variants=[{**result,'estimated_cost':result['estimated_cost']+1},{**result,'request_id':'forged-request'},{**result,'coverage':{**result['coverage'],'ratio':-1}}]
                if result['ordered_units']:variants.append({**result,'ordered_units':result['ordered_units']+[result['ordered_units'][0]]})
                if result['status']=='INFEASIBLE_PROVEN':variants.append({**result,'proof_path':None})
                for bad in variants:
                    check('reject altered output '+str(mutations),not verify_result(req,units,bad,gate,details.get('certificate'))['valid']);mutations+=1
        for sample in summary['status_examples']:
            folder=source/'status_examples'/sample['expected'];f=load(folder/'input.json');data=load(folder/'output.json');d=data['details'];r=data['result'];audit=verify_result(f['request'],f['units'],r,d['gate'],d.get('certificate'))
            check('real status invocation '+sample['expected'],r['status']==sample['expected'] and audit['valid'])
            if sample['expected']=='NO_FEASIBLE_FOUND':check('feasible witness does not become false proof',d['exact_feasible_witness']['status']=='FEASIBLE')
            if sample['expected']=='TIMEOUT':check('actual zero wall budget',sample['options']['time_limit_seconds']==0 and d['termination']=='WALL_CLOCK_TIMEOUT')
        fig=ROOT/'report_materials/A/A-D04'/a.run_id;render=load(fig/'render_config.json');check('figure source hash',render['source_sha256']==hashlib.sha256((source/'summary.json').read_bytes()).hexdigest())
        for name in ('F03_search_framework','exact_B2_beam_table','beam_decision_trace'):
            with Image.open(fig/(name+'.png')) as image:image.verify()
            with Image.open(fig/(name+'.png')) as image:check('PNG300dpi '+name,all(abs(d-300)<.1 for d in image.info['dpi']))
            svg=ET.parse(fig/(name+'.svg')).getroot();check('native SVG '+name,bool(svg.findall('{http://www.w3.org/2000/svg}text')) and not svg.findall('.//{http://www.w3.org/2000/svg}image'))
        result={'task_id':'A-D04','source_run':a.run_id,'engineering_passed':True,'checks':checks,'negative_mutations_rejected':mutations,'independent_human_review':'NOT_REVIEWED','formal_study_ready':False,'release_pending':['final tests','committed-copy replay','remote SHA verification'],'exit_code':0}
    except Exception:result={'engineering_passed':False,'checks':checks,'error':traceback.format_exc(),'exit_code':1}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2));return result['exit_code']
if __name__=='__main__':raise SystemExit(main())
