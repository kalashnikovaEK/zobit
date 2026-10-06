# [NEW v24] Explicit 700-case development expansion; original <=256 generator stays intact.
import copy,hashlib,json,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
import pandas as pd
from core import ROOT,FEATURES,TARGETS,MODEL_HASH,simulate
from pipeline import sample_conditions,train_surrogate
from surrogate_store_v23 import load_bundle_v23
from surrogate_store_v24 import STORE,DATASET,export_bundle_v24,load_bundle_v24
OPTIONS={'nz':31,'tool_nz':21,'dt':2.,'save_seconds':30.}
CHECKPOINT=ROOT/'artifacts/generated_444_v24.jsonl'

def expanded_inputs_v24():
    cycles=sample_conditions(count=111,seed=2401)
    rng=np.random.default_rng(2402);tasks=[]
    for index,c in enumerate(cycles):
        for band in range(4):
            condition=dict(c,thickness=float(rng.uniform(2+7*band,9+7*band)))
            tasks.append({'case_id':index*4+band,'condition':condition,'group':64+index})
    return tasks

def calculate_case_v24(task=None):
    result=simulate(condition=task['condition'],options=OPTIONS)
    return {'case_id':task['case_id'],**task['condition'],**{k:result['summary'][k] for k in TARGETS},'group':task['group'],'model_hash':MODEL_HASH,'data_kind':'unvalidated_development_synthetic'}

def generate_700_v24(workers=None):
    base=pd.read_csv(ROOT/'artifacts/development_cases.csv')
    if len(base)!=256 or base.group.nunique()!=64 or not (base.model_hash==MODEL_HASH).all():raise ValueError('Expected original version-matched 256-case dataset')
    tasks=expanded_inputs_v24();done={}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            row=json.loads(line);case=int(row['case_id'])
            if case not in range(444) or row['model_hash']!=MODEL_HASH:raise ValueError('Stale generation checkpoint')
            if any(row[k]!=tasks[case]['condition'][k] for k in FEATURES):raise ValueError('Checkpoint input mismatch')
            done[case]=row
    pending=[task for task in tasks if task['case_id'] not in done]
    print(f'Generating {len(pending)} new physics labels; {len(done)} completed checkpoint rows',flush=True)
    with ProcessPoolExecutor(max_workers=4 if workers is None else int(workers)) as pool:
        futures={pool.submit(calculate_case_v24,task):task for task in pending}
        for future in as_completed(futures):
            row=future.result();done[row['case_id']]=row
            with CHECKPOINT.open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
            if len(done)%12==0 or len(done)==444:print(f'Physics labels {len(done)}/444',flush=True)
    added=pd.DataFrame([done[i] for i in range(444)]).drop(columns=['case_id'])
    data=pd.concat([base,added],ignore_index=True)
    if len(data)!=700 or data.duplicated(FEATURES).any() or not np.isfinite(data[FEATURES+TARGETS].to_numpy()).all():raise ValueError('700-case dataset QC failed')
    data.to_csv(DATASET,index=False)
    qc={'requested':700,'valid':len(data),'original_rows':256,'new_physics_rows':444,'groups':int(data.group.nunique()),'duplicate_inputs':0,'nonfinite':0,'model_hash':MODEL_HASH,'solver_options':OPTIONS,'original_dataset_sha256':hashlib.sha256((ROOT/'artifacts/development_cases.csv').read_bytes()).hexdigest(),'expanded_dataset_sha256':hashlib.sha256(DATASET.read_bytes()).hexdigest(),'seeds':[2401,2402],'external_validation_passed':False,'qualified':False,'purpose':'development surrogate search; not experimentally qualified'}
    (ROOT/'artifacts/dataset_qc_700_v24.json').write_text(json.dumps(qc,indent=2))
    return data

def metric_v24(truth=None,prediction=None):
    from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
    return {'MAE':float(mean_absolute_error(truth,prediction)),'RMSE':float(np.sqrt(mean_squared_error(truth,prediction))),'R2':float(r2_score(truth,prediction)),'max_abs_error':float(np.max(np.abs(np.asarray(truth)-np.asarray(prediction))))}

def run_training_v24(workers=None):
    start=time.perf_counter();data=generate_700_v24(workers=workers)
    evaluation=train_surrogate(data=data,output=STORE)
    checks=pd.read_csv(ROOT/'artifacts/trained_surrogate_v23/fresh_physics_checks.csv')
    for _,row in checks.iterrows():
        if np.any(np.all(np.isclose(data[FEATURES].to_numpy(),row[FEATURES].to_numpy(dtype=float),rtol=0,atol=1e-10),axis=1)):raise ValueError('Benchmark leaked into training')
    baseline=load_bundle_v23();final=copy.deepcopy(evaluation)
    for target,model in zip(TARGETS,final['models']):model.fit(data[FEATURES],data[target])
    final['report'].update(final_fit_rows=700,evaluation_model_fit_rows=evaluation['report']['train_rows'],evaluation_model_test_rows=evaluation['report']['test_rows'],deployment_refit=True,evaluation_scope='Group holdout evaluated separately, then deployment refit on all 700 rows')
    export_bundle_v24(bundle=final);portable=load_bundle_v24()
    inputs=pd.concat([data[FEATURES],pd.DataFrame(sample_conditions(count=256,seed=2403))],ignore_index=True);equivalence={}
    for target,a,b in zip(TARGETS,final['models'],portable['models']):
        error=float(np.max(np.abs(a.predict(inputs)-b.predict(inputs))))
        if error>1e-9:raise ValueError('Portable export mismatch: '+target)
        equivalence[target]=error
    actual_metrics={};prior_metrics={}
    for i,target in enumerate(TARGETS):
        checks['predicted_700_'+target]=portable['models'][i].predict(checks[FEATURES])
        checks['error_700_'+target]=checks['predicted_700_'+target]-checks[target]
        actual_metrics[target]=metric_v24(truth=checks[target],prediction=checks['predicted_700_'+target])
        prior_metrics[target]=metric_v24(truth=checks[target],prediction=baseline['models'][i].predict(checks[FEATURES]))
    checks.to_csv(STORE/'fixed_physics_benchmark_v24.csv',index=False)
    recheck=simulate(condition=checks.iloc[0][FEATURES].to_dict(),options={'nz':41,'tool_nz':21,'dt':1.,'save_seconds':30.})
    errors={k:float(recheck['summary'][k]-checks.iloc[0][k]) for k in TARGETS}
    if any(abs(v)>1e-6 for v in errors.values()):raise ValueError('Archived benchmark no longer matches current solver')
    audit={'training_rows':700,'new_physics_rows':444,'group_count':int(data.group.nunique()),'evaluation':evaluation['report'],'final_fit_rows':700,'fixed_benchmark_rows':8,'benchmark_scope':'Untrained fixed 8-case numerical benchmark from v23, reused for direct comparison; not new or experimental data','benchmark_700_metrics':actual_metrics,'benchmark_256_metrics':prior_metrics,'benchmark_recheck_errors':errors,'portable_match_inputs':len(inputs),'portable_max_errors':equivalence,'training_options':OPTIONS,'benchmark_options':{'nz':41,'tool_nz':21,'dt':1.,'save_seconds':30.},'seconds':time.perf_counter()-start,'qualified':False,'external_validation_passed':False}
    final['report']['validation_v24']=audit;export_bundle_v24(bundle=final)
    (STORE/'training_audit_v24.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2),flush=True)
    return audit

if __name__=='__main__':run_training_v24()
