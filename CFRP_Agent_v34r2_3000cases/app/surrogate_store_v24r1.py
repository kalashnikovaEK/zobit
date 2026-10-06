# [NEW v24r1] Separate 3000-case store; existing 256/700-case assets stay intact.
import hashlib,json,threading
from pathlib import Path
from core import ROOT
from surrogate_store_v23 import export_bundle_v23,load_bundle_v23,fingerprints_v23
STORE=ROOT/'artifacts/trained_surrogate_v24r1'
DATASET=ROOT/'artifacts/development_cases_3000_v24r1.csv'
_LOCK=threading.Lock()
_CACHE={}

def export_bundle_v24r1(bundle=None,output=None):
    path=STORE if output is None else Path(output)
    manifest=export_bundle_v23(bundle=bundle,output=path)
    manifest['expanded_dataset_sha256']=hashlib.sha256(DATASET.read_bytes()).hexdigest()
    manifest['training_run_v24r1']=True
    manifest['training_script_sha256']=hashlib.sha256((ROOT/'train_physics_v24r1.py').read_bytes()).hexdigest()
    (path/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def load_bundle_v24r1(path=None):
    path=STORE if path is None else Path(path)
    if not (path/'manifest.json').exists() and not (path/'forest_arrays.npz').exists():return None
    m=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    if m.get('expanded_dataset_sha256')!=hashlib.sha256(DATASET.read_bytes()).hexdigest():raise ValueError('3000-case dataset fingerprint mismatch')
    if m.get('training_run_v24r1') is not True:raise ValueError('Missing v24r1 training provenance')
    if m.get('training_script_sha256')!=hashlib.sha256((ROOT/'train_physics_v24r1.py').read_bytes()).hexdigest():raise ValueError('v24r1 training script fingerprint mismatch')
    return load_bundle_v23(path=path)

def get_trained_bundle_v24r1(event_sink=None):
    signature=tuple(fingerprints_v23().values())
    for p in [DATASET,STORE/'manifest.json',STORE/'forest_arrays.npz',ROOT/'train_physics_v24r1.py']:
        signature+=(p.stat().st_mtime_ns if p.exists() else None,p.stat().st_size if p.exists() else None)
    with _LOCK:
        if _CACHE.get('signature')!=signature:
            _CACHE.clear();bundle=load_bundle_v24r1()
            if bundle is not None:_CACHE.update(signature=signature,bundle=bundle)
        bundle=_CACHE.get('bundle')
    if event_sink is not None and bundle is not None:
        event_sink({'phase':'surrogate_loading','status':'completed','detail':{'source':'pretrained_physics_surrogate_v24r1','fit_rows':bundle['report'].get('final_fit_rows'),'external_validation_passed':False}})
    return bundle
