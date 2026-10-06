# [NEW v23] Portable, data-only Random Forest store. No pickle or executable model payload.
import hashlib
import json
import platform
import threading
from pathlib import Path
import numpy as np
import pandas as pd
from core import ROOT,FEATURES,TARGETS,MODEL_HASH,BOUNDS
from time_surrogate import scheduled_duration

STORE=ROOT/'artifacts/trained_surrogate_v23'
_LOCK=threading.Lock()
_CACHE={}


def fingerprints_v23():
    return {'model_hash':MODEL_HASH,'dataset_sha256':hashlib.sha256((ROOT/'artifacts/development_cases.csv').read_bytes()).hexdigest(),
            'training_code_sha256':hashlib.sha256((ROOT/'pipeline.py').read_bytes()+(ROOT/'time_surrogate.py').read_bytes()).hexdigest()}


class PortableForestV23:
    def __init__(self,arrays=None,time_base=None):
        self.arrays=arrays
        self.time_base=bool(time_base)

    def predict(self,X=None):
        frame=X.loc[:,FEATURES] if isinstance(X,pd.DataFrame) else pd.DataFrame(X,columns=FEATURES)
        # sklearn tree inference uses float32 feature inputs even when fitted with float64 data.
        features=frame.to_numpy(dtype=np.float32)
        if features.ndim!=2 or features.shape[1]!=len(FEATURES) or not np.isfinite(features).all():raise ValueError('Invalid portable model inputs')
        a=self.arrays
        result=np.zeros(len(features),dtype=float)
        for root in a['roots']:
            nodes=np.full(len(features),int(root),dtype=np.int64)
            active=a['left'][nodes]>=0
            while active.any():
                rows=np.flatnonzero(active)
                current=nodes[rows]
                cols=a['feature'][current]
                go_left=features[rows,cols]<=a['threshold'][current]
                nodes[rows]=np.where(go_left,a['left'][current],a['right'][current])
                active=a['left'][nodes]>=0
            result+=a['value'][nodes]
        result/=len(a['roots'])
        if self.time_base:result+=scheduled_duration(frame)
        return result


def export_bundle_v23(bundle=None,output=None):
    from pipeline import _validate_bundle
    import sklearn
    models=_validate_bundle(bundle)
    path=Path(output) if output is not None else STORE
    path.mkdir(parents=True,exist_ok=True)
    arrays={}
    for index,model in enumerate(models):
        forest=model.model if TARGETS[index]=='cycle_time' else model
        offset=0
        blocks={key:[] for key in ['left','right','feature','threshold','value']}
        roots=[]
        for estimator in forest.estimators_:
            tree=estimator.tree_
            roots.append(offset)
            blocks['left'].append(np.where(tree.children_left>=0,tree.children_left+offset,-1))
            blocks['right'].append(np.where(tree.children_right>=0,tree.children_right+offset,-1))
            blocks['feature'].append(tree.feature)
            blocks['threshold'].append(tree.threshold)
            blocks['value'].append(tree.value[:,0,0])
            offset+=tree.node_count
        for key,value in blocks.items():arrays[f'm{index}_{key}']=np.concatenate(value)
        arrays[f'm{index}_roots']=np.asarray(roots,dtype=np.int64)
    target=path/'forest_arrays.npz'
    np.savez_compressed(target,**arrays)
    manifest={'format':'cfrp-portable-forest-v23','features':FEATURES,'targets':TARGETS,'bounds':BOUNDS,
              **fingerprints_v23(),'array_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
              'training_python':platform.python_version(),'training_sklearn':sklearn.__version__,
              'portable_across_python_minor_versions':True,'runtime_requires_sklearn_pickle':False,
              'report':bundle['report'],'qualified':False,'external_validation_passed':False}
    (path/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest


def load_bundle_v23(path=None):
    path=Path(path) if path is not None else STORE
    manifest_path=path/'manifest.json'
    array_path=path/'forest_arrays.npz'
    if not manifest_path.exists() and not array_path.exists():return None
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('format')!='cfrp-portable-forest-v23' or manifest.get('features')!=FEATURES or manifest.get('targets')!=TARGETS:raise ValueError('Unsupported pretrained surrogate format')
    for key,value in fingerprints_v23().items():
        if manifest.get(key)!=value:raise ValueError('Pretrained surrogate fingerprint mismatch: '+key+'; retrain before use')
    if hashlib.sha256(array_path.read_bytes()).hexdigest()!=manifest.get('array_sha256'):raise ValueError('Pretrained surrogate array checksum mismatch')
    models=[]
    with np.load(array_path,allow_pickle=False) as saved:
        for index,target in enumerate(TARGETS):
            arrays={key:saved[f'm{index}_{key}'].copy() for key in ['roots','left','right','feature','threshold','value']}
            if not len(arrays['roots']) or any(not np.isfinite(a).all() for a in arrays.values()):raise ValueError('Invalid pretrained forest arrays')
            models.append(PortableForestV23(arrays=arrays,time_base=target=='cycle_time'))
    bundle={'models':models,'report':manifest['report'],'model_hash':MODEL_HASH,'portable_manifest_v23':manifest}
    from pipeline import _validate_bundle
    _validate_bundle(bundle)
    return bundle


def get_trained_bundle_v23(event_sink=None):
    # Small signature checks on every request; arrays are loaded only once per unchanged version.
    signature=tuple(fingerprints_v23().values())
    for name in ['manifest.json','forest_arrays.npz']:
        file=STORE/name
        signature+=(file.stat().st_mtime_ns if file.exists() else None,)
    with _LOCK:
        if _CACHE.get('signature')!=signature:
            _CACHE.clear()
            bundle=load_bundle_v23()
            if bundle is not None:_CACHE.update(signature=signature,bundle=bundle)
        bundle=_CACHE.get('bundle')
    if event_sink is not None and bundle is not None:
        event_sink({'phase':'surrogate_loading','status':'completed','detail':{'source':'pretrained_physics_surrogate_v23','model_hash':MODEL_HASH,'fit_rows':bundle['report'].get('final_fit_rows'),'external_validation_passed':False}})
    return bundle
