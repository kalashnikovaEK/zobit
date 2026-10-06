# [NEW v34] v33 semantic guards + explicit confirmation of the stored interpretation.
import copy
import json
import secrets
import threading
import time
from pathlib import Path
from core import ROOT, FEATURES


def make_preview(request=None, spec=None, condition=None, limits=None, config=None):
    from AI import merge_inputs, load_config
    cfg=load_config(config)
    c,lim=merge_inputs(spec,condition,limits)
    variables=spec['search_variables'] or cfg['default_search_variables']
    if spec['action']!='optimize_cycle': variables=[]
    labels={'ramp1':'1차 승온속도 (°C/min)','T1':'1차 유지온도 (°C)','hold1':'1차 유지시간 (min)', 'ramp2':'2차 승온속도 (°C/min)','T2':'2차 유지온도 (°C)','hold2':'2차 유지시간 (min)','thickness':'두께 (mm)'}
    goals={'minimize_time':'공정시간 최소화','minimize_peak':'최고 내부온도 최소화','minimize_spread':'온도편차 최소화','balanced':'균형 목표'}
    actions={'simulate_process':'물리 계산','predict_process':'AI 예측 + 물리 계산','optimize_cycle':'공정 최적화'}
    preview={'request':request,'action':actions[spec['action']],'target':goals[spec['target']], 'material':'AS4/8552 평판','search_variables':variables,'change_labels':[labels[k] for k in variables], 'fixed_variables':[labels[k] for k in FEATURES if k not in variables], 'condition':c,'limits':lim, 'condition_patch':spec['condition_patch'],'limits_patch':spec['limits_patch']}
    return {'status':'confirmation_required','answer':'해석한 목표·변경 변수·수치·제약을 확인한 뒤 실행하십시오. 잘못 해석했다면 요청을 수정하십시오.', 'interpreted_request':spec,'preview':preview,'display':None,'candidates':[],'result_guard':{}}


PENDING={}
PENDING_LOCK=threading.Lock()
TTL=600

def issue_preview(body=None, spec=None):
    token=secrets.token_urlsafe(32)
    with PENDING_LOCK:
        now=time.monotonic()
        for k in list(PENDING):
            if now-PENDING[k]['time']>TTL: del PENDING[k]
        if len(PENDING)>=100: raise ValueError('확인 대기 요청이 너무 많습니다.')
        PENDING[token]={'body':copy.deepcopy(body),'spec':copy.deepcopy(spec),'time':now}
    return token


def consume_preview(body=None, token=None):
    if not isinstance(token,str): raise ValueError('실행 확인 토큰이 필요합니다.')
    with PENDING_LOCK:
        item=PENDING.get(token)
        if not item or time.monotonic()-item['time']>TTL: raise ValueError('확인이 만료되었습니다. 요청을 다시 보내십시오.')
        if body!=item['body']: raise ValueError('요청·입력·모델이 변경되었습니다. 다시 해석하십시오.')
        del PENDING[token]
    return item['spec']


def serve_preview_chat(handler=None):
    from integrated_api_v14 import read_body
    from chat_bridge import parse_chat, AI_RUN_LOCK, chat_result
    from llm_profiles_v14 import profile_config
    from AI import extract_request, json_ready
    from async_runtime_v17 import call_sync, run_ai_async
    import asyncio
    try:
        raw=read_body(handler)
        token=raw.get('confirmation_token')
        body={k:v for k,v in raw.items() if k!='confirmation_token'}
        request,condition,limits=parse_chat(body)
        cfg=profile_config(body.get('profile'))
    except (ValueError,TypeError,KeyError,UnicodeError) as e:
        return handler._json({'ok':False,'error':str(e)},400)
    if not AI_RUN_LOCK.acquire(blocking=False):return handler._json({'ok':False,'error':'다른 AI 작업이 진행 중입니다.'},429)
    try:
        try:
            approved=consume_preview(body,token) if token is not None else None
        except (ValueError,TypeError) as e:
            return handler._json({'ok':False,'error':str(e)},400)
        handler._headers(200,'application/x-ndjson; charset=utf-8')
        def send(kind=None,data=None):
            handler.wfile.write((json.dumps({'type':kind,'data':data},ensure_ascii=False,allow_nan=False)+'\n').encode())
            handler.wfile.flush()
        try:
            if approved is None:
                result=asyncio.run(run_ai_async(request=request,condition=condition,limits=limits,config=cfg,preview_only=True,event_sink=lambda e:send('event',json_ready(e))))
                if result['status']!='confirmation_required':
                    send('result',chat_result(result))
                    return
                parsed=result['interpreted_request']
                result['confirmation_token']=issue_preview(body,parsed)
                send('result',result)
                return
            state=asyncio.run(run_ai_async(request=request,condition=condition,limits=limits,config=cfg,spec=approved,event_sink=lambda e:send('event',json_ready(e))))
            send('result',chat_result(state))
        except (BrokenPipeError,ConnectionResetError):return
        except Exception as e:send('error',{'error':str(e)})
    finally:AI_RUN_LOCK.release()
