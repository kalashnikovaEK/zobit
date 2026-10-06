# [NEW v24r1] Reproducible development expansion, separate blind evaluation and portable export.
import copy,hashlib,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd
from core import ROOT,FEATURES,TARGETS,MODEL_HASH,simulate
from pipeline import sample_conditions,train_surrogate
from train_physics_v24 import metric_v24
from surrogate_store_v24 import load_bundle_v24
from surrogate_store_v24r1 import STORE,DATASET,export_bundle_v24r1,load_bundle_v24r1
OPTIONS={'nz':31,'tool_nz':21,'dt':2.,'save_seconds':30.}
CHECK_OPTIONS={'nz':41,'tool_nz':21,'dt':1.,'save_seconds':30.}

def tasks_v24r1(count=None,seed=None,offset=None,options=None):
    cycles=sample_conditions(count=count,seed=seed)
    rng=np.random.default_rng(seed+1);tasks=[]
    for index,c in enumerate(cycles):
        for band in range(4):
            tasks.append({'case_id':index*4+band,'condition':dict(c,thickness=float(rng.uniform(2+7*band,9+7*band))),'group':offset+index,'options':options})
    return tasks

def calculate_v24r1(task=None):
    r=simulate(condition=task['condition'],options=task['options'])
    return {'case_id':task['case_id'],**task['condition'],**{k:r['summary'][k] for k in TARGETS},'group':task['group'],'model_hash':MODEL_HASH,'data_kind':'unvalidated_development_synthetic','solver_options':task['options']}

def generate_v24r1(tasks=None,path=None,workers=None):
    done={}
    if path.exists():
        for line in path.read_text().splitlines():
            row=json.loads(line);i=int(row['case_id'])
            if i<0 or i>=len(tasks) or row['model_hash']!=MODEL_HASH or row['solver_options']!=tasks[i]['options']:raise ValueError('Stale checkpoint')
            if any(row[k]!=tasks[i]['condition'][k] for k in FEATURES) or row['group']!=tasks[i]['group']:raise ValueError('Checkpoint input mismatch')
            done[i]=row
    with ProcessPoolExecutor(max_workers=4 if workers is None else int(workers)) as pool:
        futures=[pool.submit(calculate_v24r1,t) for t in tasks if t['case_id'] not in done]
        for f in as_completed(futures):
            row=f.result();done[row['case_id']]=row
            with path.open('a') as out:out.write(json.dumps(row)+'\n')
            if len(done)%100==0 or len(done)==len(tasks):print(f'{path.name}: {len(done)}/{len(tasks)}',flush=True)
    return pd.DataFrame([done[i] for i in range(len(tasks))]).drop(columns=['case_id','solver_options'])

def evaluate_v24r1(data=None,bundle=None):
    return {k:metric_v24(truth=data[k],prediction=m.predict(data[FEATURES])) for k,m in zip(TARGETS,bundle['models'])}

def run_training_v24r1(workers=None):
    start=time.perf_counter();STORE.mkdir(parents=True,exist_ok=True)
    base=pd.read_csv(ROOT/'artifacts/development_cases_700_v24.csv')
    if len(base)!=700 or not (base.model_hash==MODEL_HASH).all():raise ValueError('Expected version-matched 700-case base')
    # Warm JIT once before child processes; independently recheck an archived label.
    r=simulate(condition=base.iloc[0][FEATURES].to_dict(),options=OPTIONS)
    if any(abs(r['summary'][k]-base.iloc[0][k])>1e-6 for k in TARGETS):raise ValueError('Source label recheck failed')
    tasks=tasks_v24r1(count=575,seed=35001,offset=175,options=OPTIONS)
    added=generate_v24r1(tasks=tasks,path=ROOT/'artifacts/generated_2300_v24r1.jsonl',workers=workers)
    data=pd.concat([base,added],ignore_index=True)
    if len(data)!=3000 or data.group.nunique()!=750 or data.duplicated(FEATURES).any() or not np.isfinite(data[FEATURES+TARGETS].to_numpy()).all():raise ValueError('Dataset QC failed')
    data.to_csv(DATASET,index=False)
    qc={'training_rows':3000,'preserved_rows':700,'new_physics_rows':2300,'groups':750,'duplicate_inputs':0,'nonfinite':0,'model_hash':MODEL_HASH,'seeds':[35001,35002],'solver_options':OPTIONS,'external_validation_passed':False}
    (STORE/'dataset_qc.json').write_text(json.dumps(qc,indent=2))
    evaluation=train_surrogate(data=data,output=STORE)
    final=copy.deepcopy(evaluation)
    for k,m in zip(TARGETS,final['models']):m.fit(data[FEATURES],data[k])
    final['report'].update(final_fit_rows=3000,evaluation_model_fit_rows=evaluation['report']['train_rows'],evaluation_model_test_rows=evaluation['report']['test_rows'],deployment_refit=True,evaluation_scope='Grouped holdout evaluation followed by all-3000 deployment fit; fresh 100 cases never fitted')
    export_bundle_v24r1(bundle=final);portable=load_bundle_v24r1();baseline=load_bundle_v24()
    probe=pd.concat([data[FEATURES],pd.DataFrame(sample_conditions(count=256,seed=35003))],ignore_index=True)
    equivalence={k:float(np.max(np.abs(a.predict(probe)-b.predict(probe)))) for k,a,b in zip(TARGETS,final['models'],portable['models'])}
    if max(equivalence.values())>1e-9:raise ValueError('Portable export mismatch')
    checks=generate_v24r1(tasks=tasks_v24r1(count=25,seed=35004,offset=750,options=CHECK_OPTIONS),path=ROOT/'artifacts/validation_100_v24r1.jsonl',workers=workers)
    # Exclude exact cycles as well as exact rows to prevent thickness siblings leaking.
    if set(map(tuple,data[FEATURES[:-1]].to_numpy())) & set(map(tuple,checks[FEATURES[:-1]].to_numpy())):raise ValueError('Validation cycle leakage')
    for label,bundle in [('700',baseline),('3000',portable)]:
        for k,m in zip(TARGETS,bundle['models']):checks[f'predicted_{label}_{k}']=m.predict(checks[FEATURES])
    checks.to_csv(STORE/'blind_100_predictions.csv',index=False)
    fixed=pd.read_csv(ROOT/'artifacts/trained_surrogate_v24/fixed_physics_benchmark_v24.csv')
    audit={'dataset_qc':qc,'group_holdout':evaluation['report'],'blind_evaluation_rows':100,'blind_evaluation_groups':25,'blind_options':CHECK_OPTIONS,'blind_seeds':[35004,35005],'blind_700':evaluate_v24r1(data=checks,bundle=baseline),'blind_3000':evaluate_v24r1(data=checks,bundle=portable),'fixed8_700':evaluate_v24r1(data=fixed,bundle=baseline),'fixed8_3000':evaluate_v24r1(data=fixed,bundle=portable),'portable_match_rows':len(probe),'portable_max_errors':equivalence,'seconds':time.perf_counter()-start,'external_validation_passed':False,'evaluation_scope':'Independent synthetic conditions at higher solver resolution, not experimental accuracy; no hyperparameter selection on these 100 cases'}
    final['report']['validation_v24r1']=audit;export_bundle_v24r1(bundle=final)
    (STORE/'training_audit_v24r1.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2),flush=True)
    return audit

if __name__=='__main__':run_training_v24r1()
