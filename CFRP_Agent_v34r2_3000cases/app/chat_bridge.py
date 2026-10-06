# [NEW v13] HTML chat bridge; existing physics, AI and guard remain unchanged.
import json
import threading
from urllib.parse import urlparse
import numpy as np
from core import FEATURES, LIMITS, normalize, judge
from web_bridge import browser_config, _parse_payload

AI_RUN_LOCK = threading.Lock()


def parse_chat(body=None):
    # [NEW v14] Only named server-side model profiles may be selected by clients.
    if isinstance(body,dict) and 'profile' in body:
        from llm_profiles_v14 import profile_config
        profile_config(body['profile'])
        body={k:v for k,v in body.items() if k!='profile'}
    if not isinstance(body, dict) or set(body) != {'request', 'inputs'}:
        raise ValueError('요청에는 request와 inputs만 필요합니다.')
    request = body['request']
    if not isinstance(request, str) or not request.strip() or len(request) > 4000:
        raise ValueError('자연어 요청은 1~4000자로 입력하십시오.')
    inputs = body['inputs']
    if not isinstance(inputs, dict) or set(inputs) != {'condition', 'options', 'limits'}:
        raise ValueError('공정·경계·제약 입력이 필요합니다.')
    if not isinstance(inputs['condition'], dict) or set(inputs['condition']) != set(FEATURES):
        raise ValueError('화면의 공정 입력 7개를 모두 지정하십시오.')
    if not isinstance(inputs['limits'], dict) or set(inputs['limits']) != set(LIMITS):
        raise ValueError('화면의 제약 입력 3개를 모두 지정하십시오.')
    condition, options, limits = _parse_payload(inputs)
    condition = normalize(condition)
    judge({'Tmax':25,'delta_Tmax':0,'final_DoC':1},limits)
    defaults = browser_config()['solver_defaults']
    # AI training assumes these boundary/material values; never ignore edited UI values.
    if set(options) != set(defaults) or any(options[k] != defaults[k] for k in defaults):
        raise ValueError('AI는 기본 열경계에서만 지원합니다. 고급 열경계를 기본값으로 되돌리거나 기존 물리모델 계산을 사용하십시오.')
    return request, condition, limits


def serialize_verified(result=None, limits=None):
    """Use the exact verified arrays; do not rerun the solver for chart data."""
    row = lambda v: np.asarray(v, dtype=float).tolist()
    mid = len(result['z']) // 2
    out = {k:result[k] for k in ('condition','options','summary','outside_training_domain',
                               'external_validation_passed','physics_status','model_version','model_hash')}
    out['decision'] = judge(result['summary'], limits)
    out['series'] = {k:row(result[k]) for k in ('t','T_air','T_part_top_surface','T_part_bottom_surface',
                                              'T_tool_interface_surface','T_tool_outer_surface','q_contact')}
    out['series'].update(T_part_center=row(result['T'][:,mid]), alpha_top_cell=row(result['alpha'][:,0]),
                         alpha_center_cell=row(result['alpha'][:,mid]),alpha_bottom_cell=row(result['alpha'][:,-1]),
                         alpha_min=row(result['alpha'].min(axis=1)))
    out['field'] = {name:row(result[key]) for name,key in
                    [('z_part','z'),('z_tool','z_tool'),('T_part','T'),('alpha_part','alpha'),('T_tool','T_tool')]}
    # [NEW v14] Review IDs belong to the exact verified display.
    from review_store_v14 import register_display
    return register_display(out)


def chat_result(state=None):
    guard = state.get('result_guard') or {}
    output = {'status':state['status'],'answer':state['answer'],
              'interpreted_request':state.get('interpreted_request'), 'result_guard':guard,
              'condition':state.get('condition'),'limits':state.get('limits'), 'candidates':[],
              'display':None, 'display_source':None}
    if guard.get('status') != 'passed' or state['status'] not in ('completed','no_feasible_candidate'):
        return output
    opt = state.get('optimization') or {}
    recs = opt.get('recommendations') or []
    output['candidates'] = [{'condition':r['condition'],'actual':r['actual'],
                             'time_change_percent':r['time_change_percent']} for r in recs]
    physical = recs[0]['result'] if recs else state.get('physical')
    # [NEW v14] Return bounded (<=3) verified candidates and the same-run baseline.
    if state.get('physical') is not None:output['baseline_display']=serialize_verified(state['physical'],state['limits'])
    output['candidate_displays']=[serialize_verified(r['result'],state['limits']) for r in recs]
    output['target']=opt.get('target')
    if physical is not None:
        output['display'] = serialize_verified(physical, state['limits'])
        output['display_source'] = 'verified_recommendation' if recs else 'baseline_only'
    return output


def serve_chat(handler=None):
    # [NEW v34] Browser execution always requires a server-bound interpretation confirmation.
    if handler is not None:
        from request_preview_v34 import serve_preview_chat
        return serve_preview_chat(handler)
    # [NEW v13] Limit the new costly API to its local page or the existing file:// UI.
    origin = handler.headers.get('Origin')
    if origin not in (None,'null'):
        try:
            parsed = urlparse(origin)
            allowed = parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1','localhost') and parsed.port == handler.server.server_port and not parsed.username and parsed.path in ('','/')
        except ValueError:
            allowed = False
        if not allowed:
            return handler._json({'ok':False,'error':'허용되지 않는 웹 Origin입니다.'},403)
    try:
        length = int(handler.headers.get('Content-Length','0'))
        if not 0 < length <= 1024*1024:
            raise ValueError('요청 본문 크기가 올바르지 않습니다.')
        body = json.loads(handler.rfile.read(length).decode('utf-8'))
        request, condition, limits = parse_chat(body)
        # [NEW v14] Model is selected from the same config contract for all paths.
        from llm_profiles_v14 import profile_config
        cfg=profile_config(body.get('profile'))
    except (ValueError, TypeError, KeyError, UnicodeError) as error:
        return handler._json({'ok':False,'error':str(error)},400)
    if not AI_RUN_LOCK.acquire(blocking=False):
        return handler._json({'ok':False,'error':'다른 AI 작업이 진행 중입니다. 완료 후 다시 보내십시오.'},429)
    try:
        handler._headers(200,'application/x-ndjson; charset=utf-8')
        def send(kind=None, data=None):
            handler.wfile.write((json.dumps({'type':kind,'data':data},ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
            handler.wfile.flush()
        from AI import run_ai, json_ready
        # [NEW v17] Keep all synchronous LLM/config/training/solver work in a worker.
        import asyncio
        from async_runtime_v17 import run_ai_async
        try:
            # [NEW v17] Worker events stream through the existing single request writer.
            state = asyncio.run(run_ai_async(request=request,condition=condition,limits=limits,config=cfg,
                           event_sink=lambda e:send('event',json_ready(e))))
            send('result',chat_result(state))
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            send('error',{'error':str(error)})
    finally:
        AI_RUN_LOCK.release()
