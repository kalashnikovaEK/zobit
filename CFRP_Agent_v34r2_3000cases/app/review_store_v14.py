# [NEW v14] Server-bound review records; client cannot assert a guard result.
import json,hashlib,threading
from datetime import datetime,timezone
from core import ROOT
_CACHE={}
_LOCK=threading.Lock()

def register_display(display=None):
    clean={k:v for k,v in display.items() if k!='run_id_v14'}
    rid=hashlib.sha256(json.dumps(clean,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    with _LOCK:
        _CACHE[rid]={'condition':display['condition'],'summary':display['summary'],'limits':display['decision']['limits'],'model_hash':display['model_hash'],'boundary_input_kind':display.get('boundary_input_kind','nominal')}
        while len(_CACHE)>32:_CACHE.pop(next(iter(_CACHE)))
    display['run_id_v14']=rid
    return display

def record_review(body=None):
    if not isinstance(body,dict) or set(body)!={'run_id','reviewer','status'}:raise ValueError('run_id/reviewer/status 필수')
    reviewer=body['reviewer']
    if not isinstance(reviewer,str) or not 1<=len(reviewer.strip())<=100:raise ValueError('검토자 이름 1~100자 필수')
    if body['status'] not in ('reviewed_demo_only','held'):raise ValueError('검토 상태 오류')
    with _LOCK:
        data=_CACHE.get(body['run_id'])
        if data is None:raise ValueError('현재 서버의 검증 결과가 아닙니다. 다시 계산하십시오.')
        record={**data,'run_id':body['run_id'],'reviewer':reviewer.strip(),'status':body['status'],'timestamp_utc':datetime.now(timezone.utc).isoformat(),'scope':'simulation review only; not equipment approval'}
        target=ROOT/'artifacts/reviews_v14.jsonl';target.parent.mkdir(exist_ok=True)
        with target.open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
    return record
