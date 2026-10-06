# [NEW v24] 700-case store; preserve v23 data, models and portable format.
import hashlib,json,threading
from pathlib import Path
from core import ROOT
from surrogate_store_v23 import load_bundle_v23,export_bundle_v23,fingerprints_v23
STORE=ROOT/'artifacts/trained_surrogate_v24'
DATASET=ROOT/'artifacts/development_cases_700_v24.csv'
_LOCK=threading.Lock()
_CACHE={}

def export_bundle_v24(bundle=None,output=None):
    path=STORE if output is None else Path(output)
    manifest=export_bundle_v23(bundle=bundle,output=path)
    manifest['expanded_dataset_sha256']=hashlib.sha256(DATASET.read_bytes()).hexdigest()
    manifest['training_run_v24']=True
    (path/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest

def load_bundle_v24(path=None):
    path=STORE if path is None else Path(path)
    if not (path/'manifest.json').exists() and not (path/'forest_arrays.npz').exists():return None
    manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('expanded_dataset_sha256')!=hashlib.sha256(DATASET.read_bytes()).hexdigest():raise ValueError('Expanded dataset fingerprint mismatch; retrain before use')
    if manifest.get('training_run_v24') is not True:raise ValueError('Missing v24 training provenance')
    return load_bundle_v23(path=path)

def get_trained_bundle_v24(event_sink=None):
    signature=tuple(fingerprints_v23().values())
    for path in [DATASET,STORE/'manifest.json',STORE/'forest_arrays.npz']:
        signature+=(path.stat().st_mtime_ns if path.exists() else None,path.stat().st_size if path.exists() else None)
    with _LOCK:
        if _CACHE.get('signature')!=signature:
            _CACHE.clear()
            bundle=load_bundle_v24()
            if bundle is not None:_CACHE.update(signature=signature,bundle=bundle)
        bundle=_CACHE.get('bundle')
    if event_sink is not None and bundle is not None:
        event_sink({'phase':'surrogate_loading','status':'completed','detail':{'source':'pretrained_physics_surrogate_v24','fit_rows':bundle['report'].get('final_fit_rows'),'external_validation_passed':False}})
    return bundle
