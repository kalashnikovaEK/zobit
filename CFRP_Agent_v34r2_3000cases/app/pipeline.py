# [NEW v01] Development-only dataset, group-held-out evaluation and bounded inference.
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import qmc
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from core import ROOT,FEATURES,TARGETS,BOUNDS,MODEL_HASH,normalize,simulate
# [NEW v01] Physics-informed time target; other targets retain their original RF estimators.
from time_surrogate import CycleTimeSurrogate


# [NEW v07] Validate caller-supplied surrogate bundles before indexing/predicting so corrupted bundles fail deterministically.
def _validate_bundle(bundle=None):
    if not isinstance(bundle,dict): raise ValueError('Train/load the local surrogate first')
    if bundle.get('model_hash')!=MODEL_HASH: raise ValueError('Model/material version mismatch')
    models=bundle.get('models')
    if not isinstance(models,(list,tuple)) or len(models)!=len(TARGETS) or not all(hasattr(m,'predict') for m in models):
        raise ValueError('Invalid surrogate bundle: expected one predict-capable model per target')
    return models

def sample_conditions(count=None,seed=None,thickness=None):
    n=1000 if count is None else int(count)
    if n<1 or n>10000: raise ValueError('Candidate count must be 1–10000')
    x=qmc.LatinHypercube(d=len(FEATURES),seed=42 if seed is None else int(seed)).random(n)
    lo=np.array([BOUNDS[k][0] for k in FEATURES]);hi=np.array([BOUNDS[k][1] for k in FEATURES])
    x=qmc.scale(x,lo,hi)
    if thickness is not None: x[:,-1]=float(thickness)
    return [dict(zip(FEATURES,map(float,row))) for row in x]

def generate_dataset(count=None,seed=None,mode=None,output=None):
    n=128 if count is None else int(count);mode=mode or 'development'
    # External experimental gate is intentionally closed in v01.
    if mode!='development' or n>256:
        raise RuntimeError('External validation is pending. Only <=256 development cases are permitted; production data generation blocked.')
    if n<32 or n%4: raise ValueError('Use a multiple of 4 between 32 and 256')
    cases=sample_conditions(n//4,seed)
    rows=[];failures=[];start=time.perf_counter()
    for group,c in enumerate(cases):
        for th in (2.,10.,20.,30.):
            cc=dict(c,thickness=th)
            try:
                r=simulate(cc)
                rows.append({**cc,**{k:r['summary'][k] for k in TARGETS},'group':group,'model_hash':MODEL_HASH,'data_kind':'unvalidated_development_synthetic'})
            except ValueError as e: failures.append({'condition':cc,'error':str(e)})
    df=pd.DataFrame(rows)
    if len(df)==0 or not np.isfinite(df[FEATURES+TARGETS].to_numpy()).all(): raise RuntimeError('Dataset QC failed')
    qc={'requested':n,'valid':len(df),'failed':len(failures),'failures':failures,'duplicate_inputs':int(df.duplicated(FEATURES).sum()),'nonfinite':0,'seed':42 if seed is None else seed,'seconds':time.perf_counter()-start,'model_hash':MODEL_HASH,'external_validation_passed':False,'purpose':'software integration only; not a qualified manufacturing dataset'}
    out=Path(output) if output else ROOT/'artifacts'
    out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/'development_cases.csv',index=False)
    (out/'dataset_qc.json').write_text(json.dumps(qc,ensure_ascii=False,indent=2),encoding='utf-8')
    return df,qc

def train_surrogate(data=None,output=None):
    df=pd.read_csv(ROOT/'artifacts/development_cases.csv') if data is None else data.copy()
    # [NEW v07] Fail with an explicit dataset-contract error instead of a downstream KeyError/GroupShuffleSplit exception.
    required=set(FEATURES+TARGETS+['group','model_hash']);missing=required-set(df.columns)
    if missing: raise ValueError('Training data missing columns: '+','.join(sorted(missing)))
    if not (df['model_hash']==MODEL_HASH).all(): raise ValueError('Dataset/material version mismatch')
    if not np.isfinite(df[FEATURES+TARGETS].to_numpy()).all() or len(df)<32: raise ValueError('Insufficient or invalid training data')
    if df['group'].nunique()<2: raise ValueError('Training data requires at least two independent groups')
    tr,te=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(df,groups=df['group']))
    models=[];metrics={};predictions={};start=time.perf_counter()
    for k in TARGETS:
        model=RandomForestRegressor(n_estimators=160,min_samples_leaf=1,random_state=42,n_jobs=1)
        if k=='cycle_time': model=CycleTimeSurrogate()  # [NEW v01]
        model.fit(df.iloc[tr][FEATURES],df.iloc[tr][k]);pred=model.predict(df.iloc[te][FEATURES]);truth=df.iloc[te][k]
        models.append(model);predictions[k]=pred.tolist()
        metrics[k]={'MAE':float(mean_absolute_error(truth,pred)),'RMSE':float(np.sqrt(mean_squared_error(truth,pred))),'R2':float(r2_score(truth,pred))}
    report={'metrics':metrics,'train_rows':len(tr),'test_rows':len(te),'train_groups':sorted(map(int,df.iloc[tr]['group'].unique())),'test_groups':sorted(map(int,df.iloc[te]['group'].unique())),'split':'grouped by identical 6-parameter cycle; all four thickness variants stay together','model_hash':MODEL_HASH,'training_seconds':time.perf_counter()-start,'external_validation_passed':False,'qualified':False,'note':'Held-out errors against the unvalidated numerical model, NOT experimental accuracy.'}
    if output:
        out=Path(output);out.mkdir(parents=True,exist_ok=True)
        (out/'surrogate_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        test=df.iloc[te].copy()
        for k in TARGETS:test['predicted_'+k]=predictions[k]
        test.to_csv(out/'heldout_predictions.csv',index=False)
    return {'models':models,'report':report,'model_hash':MODEL_HASH}

def predict_process(condition=None,bundle=None):
    c=normalize(condition,True);models=_validate_bundle(bundle)
    X=pd.DataFrame([c],columns=FEATURES)
    return {'condition':c,'summary':{k:float(m.predict(X)[0]) for k,m in zip(TARGETS,models)},'kind':'surrogate_estimate','qualified':False,'model_hash':MODEL_HASH}

def predict_batch(conditions=None,bundle=None):
    # [NEW v06] Keep batch inference under the same trained-model/version guard as single inference.
    models=_validate_bundle(bundle)
    if conditions is None: raise ValueError('conditions are required')
    cs=[normalize(c,True) for c in conditions]
    if not cs: raise ValueError('conditions must contain at least one case')
    X=pd.DataFrame(cs,columns=FEATURES)
    return np.column_stack([m.predict(X) for m in models])
