# [NEW v23] Reproducible training on version-matched physics data and fresh solver checks.
import copy
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from core import ROOT,FEATURES,TARGETS,DEFAULT,MODEL_HASH,simulate
from pipeline import train_surrogate,sample_conditions,predict_batch
from surrogate_store_v23 import export_bundle_v23,load_bundle_v23,STORE


def run_training_v23(output=None):
    out=Path(output) if output is not None else STORE
    out.mkdir(parents=True,exist_ok=True)
    data=pd.read_csv(ROOT/'artifacts/development_cases.csv')
    if len(data)>256:raise ValueError('Development data cap is 256; external qualification is pending')
    start=time.perf_counter()
    evaluation=train_surrogate(data=data,output=out)
    print(f'Group holdout evaluation: {evaluation["report"]["train_rows"]} train / {evaluation["report"]["test_rows"]} test',flush=True)
    final=copy.deepcopy(evaluation)
    for target,model in zip(TARGETS,final['models']):model.fit(data[FEATURES],data[target])
    final['report'].update(final_fit_rows=len(data),evaluation_model_fit_rows=evaluation['report']['train_rows'],evaluation_model_test_rows=evaluation['report']['test_rows'],deployment_refit=True,
                          evaluation_scope='Group holdout metrics refer to evaluation model; deployment refit uses all rows, fresh checks reported separately')
    export_bundle_v23(bundle=final,output=out)
    portable=load_bundle_v23(path=out)
    test_inputs=pd.concat([data[FEATURES],pd.DataFrame(sample_conditions(256,seed=2301))],ignore_index=True)
    for target,a,b in zip(TARGETS,final['models'],portable['models']):
        difference=float(np.max(np.abs(a.predict(test_inputs)-b.predict(test_inputs))))
        if difference>1e-9:raise ValueError('Portable export mismatch: '+target+' '+str(difference))
    print(f'Final {len(data)}-row model saved; portable inference matches on {len(test_inputs)} inputs',flush=True)
    original_condition=data.iloc[0][FEATURES].to_dict()
    recheck=simulate(original_condition)
    source_errors={k:float(recheck['summary'][k]-data.iloc[0][k]) for k in TARGETS}
    if any(abs(v)>1e-6 for v in source_errors.values()):raise ValueError('Archived dataset label no longer matches current solver')
    print('Current solver matches archived data label',flush=True)
    candidates=sample_conditions(6,seed=2302)
    conditions=[dict(DEFAULT)]+[dict(c,thickness=th) for c,th in zip(candidates,[2.,5.,15.,20.,25.,30.])]+[dict(DEFAULT,T2=185.,hold2=125.)]
    options={'nz':41,'tool_nz':21,'dt':1.,'save_seconds':30.}
    rows=[]
    for i,condition in enumerate(conditions):
        before=time.perf_counter()
        actual=simulate(condition,options)
        predicted=predict_batch(conditions=[condition],bundle=portable)[0]
        row={**condition,'validation_case':i,'physics_seconds':time.perf_counter()-before}
        for target,prediction in zip(TARGETS,predicted):row.update({target:actual['summary'][target],'predicted_'+target:float(prediction),'error_'+target:float(prediction-actual['summary'][target])})
        rows.append(row)
        pd.DataFrame(rows).to_csv(out/'fresh_physics_checks.csv',index=False)
        print(f'Fresh physics validation {i+1}/{len(conditions)}: thickness {condition["thickness"]} mm; Tmax error {row["error_Tmax"]:+.3f} C',flush=True)
    checks=pd.DataFrame(rows)
    fresh_metrics={}
    for target in TARGETS:
        truth=checks[target];prediction=checks['predicted_'+target]
        fresh_metrics[target]={'MAE':float(mean_absolute_error(truth,prediction)),'RMSE':float(np.sqrt(mean_squared_error(truth,prediction))),'R2':float(r2_score(truth,prediction)),'max_abs_error':float(np.max(np.abs(prediction-truth)))}
    audit={'model_hash':MODEL_HASH,'training_rows':len(data),'group_count':int(data.group.nunique()),'source_label_recheck_errors':source_errors,
           'group_holdout_metrics':evaluation['report']['metrics'],'final_fit_rows':len(data),'fresh_check_rows':len(checks),'fresh_check_metrics':fresh_metrics,
           'fresh_solver_options':options,'training_solver_options':{'nz':31,'tool_nz':21,'dt':2.,'save_seconds':30.},
           'fresh_check_scope':'Eight current solver runs at Agent resolution; includes 5/15/25 mm absent from training thickness levels. Not experimental validation.',
           'portable_match_inputs':len(test_inputs),'portable_max_error_tolerance':1e-9,'seconds':time.perf_counter()-start,'external_validation_passed':False}
    final['report']['fresh_physics_validation']=audit
    export_bundle_v23(bundle=final,output=out)
    (out/'training_audit_v23.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2),flush=True)
    return audit


if __name__=='__main__':run_training_v23()
