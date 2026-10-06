# [NEW v14] Deterministic integrity checks over all arrays consumed by dashboards.
import math
import numpy as np
from core import MODEL_HASH,LIMITS,FEATURES,judge


def verify_result(result=None,measured=None):
    # [NEW v17] Explicitly reject missing calculation objects, not nested nulls.
    from async_runtime_v17 import require_result
    require_result(result, 'physical calculation')
    if result['model_hash']!=MODEL_HASH:raise ValueError('모델 해시 불일치')
    t=np.asarray(result['t'],float);T=np.asarray(result['T'],float);a=np.asarray(result['alpha'],float)
    z=np.asarray(result['z'],float);tool=np.asarray(result['T_tool'],float);zt=np.asarray(result['z_tool'],float)
    if t.ndim!=1 or len(t)<2 or not np.isfinite(t).all() or not np.all(np.diff(t)>0):raise ValueError('시간 이력 오류')
    for arr,cols,label in [(T,len(z),'CFRP'),(a,len(z),'경화도'),(tool,len(zt),'금형')]:
        if arr.shape!=(len(t),cols) or not np.isfinite(arr).all():raise ValueError(label+' 배열 크기/유한성 오류')
    if z.ndim!=1 or zt.ndim!=1 or not all(np.isfinite(x).all() and np.all(np.diff(x)>0) for x in (z,zt)):raise ValueError('깊이 좌표 오류')
    th=result['condition']['thickness'];opt=result['options']
    expected=(np.arange(len(z))+.5)*th/len(z)
    expected_tool=th+(np.arange(len(zt))+.5)*opt['tool_thickness_mm']/len(zt)
    if not np.allclose(z,expected) or not np.allclose(zt,expected_tool):raise ValueError('격자와 두께 조건 불일치')
    if len(z)!=opt['nz'] or len(zt)!=opt['tool_nz']:raise ValueError('격자 옵션 불일치')
    if np.any(a<0) or np.any(a>1) or np.any(np.diff(a,axis=0)<-1e-10):raise ValueError('경화도 범위/단조성 오류')
    vectors={}
    for key in ('T_air','q_contact','T_part_top_surface','T_part_bottom_surface','T_tool_interface_surface','T_tool_outer_surface'):
        arr=np.asarray(result[key],float)
        if arr.shape!=t.shape or not np.isfinite(arr).all():raise ValueError(key+' 표시 이력 오류')
        vectors[key]=arr
    s=result['summary']
    for key,value in s.items():
        if value is None:
            if measured and key in ('cycle_time','hold_end_DoC'):continue
            raise ValueError(key+' 요약 누락')
        if isinstance(value,(int,float,np.number)) and not math.isfinite(float(value)):raise ValueError(key+' 비유한 요약')
    if not math.isclose(float(a[-1].min()),s['final_DoC'],abs_tol=1e-6):raise ValueError('최종 경화도 요약 불일치')
    temperatures=np.column_stack([T,vectors['T_part_top_surface'],vectors['T_part_bottom_surface']])
    gradients=np.ptp(temperatures,axis=1)
    checks=[('Tmax',float(temperatures.max())),('delta_Tmax',float(gradients.max())),
            ('tool_Tmax',float(max(tool.max(),vectors['T_tool_interface_surface'].max(),vectors['T_tool_outer_surface'].max()))),
            ('interface_delta_Tmax',float(np.abs(vectors['T_part_bottom_surface']-vectors['T_tool_interface_surface']).max())),
            ('contact_flux_abs_max',float(np.abs(vectors['q_contact']).max()))]
    for key,lower in checks:
        if s[key]+1e-5<lower:raise ValueError(key+' 요약이 저장 이력보다 작음')
    if np.any(temperatures>300+1e-6) or np.any(tool>300+1e-6):raise ValueError('모델 유효 온도 범위 초과')
    if not 0<=s['peak_time']<=t[-1]+1e-6:raise ValueError('최고온도 시점 오류')
    if measured:
        if not math.isclose(s['observation_duration_min'],float(t[-1]),abs_tol=1e-6):raise ValueError('관측기간 요약 불일치')
        if s['cycle_time'] is not None and not 0<=s['cycle_time']<=t[-1]:raise ValueError('실측 종료시간 범위 오류')
    elif not math.isclose(float(t[-1]),s['cycle_time'],abs_tol=1e-6):raise ValueError('공정시간 요약 불일치')
    return {'status':'passed','controller':'deterministic_v14','external_physics_certification':False}


def verify_state(state=None,contract=None):
    from AI import goal_score
    locked=contract['payload'];base=state['physical'];verify_result(base)
    # [NEW v14] Freeze implicit thermal defaults as well as explicitly configured mesh settings.
    from web_bridge import browser_config
    expected={**browser_config()['solver_defaults'],'nz':31,'tool_nz':21,'dt':2.,'save_seconds':30.,'heat_scale':1.,**locked['options']}
    if base['options']!=expected:raise ValueError('전체 기준 물리 옵션이 실행 계약과 다름')
    opt=state.get('optimization')
    if opt is None:return
    if opt['baseline']['condition']!=base['condition'] or opt['baseline']['summary']!=base['summary']:raise ValueError('최적화 기준 결과 불일치')
    scores=[];seen=set()
    for rec in opt['recommendations']:
        r=rec['result'];verify_result(r)
        if r['options']!=base['options']:raise ValueError('기준/후보 전체 물리 옵션 불일치')
        key=tuple(rec['condition'][k] for k in FEATURES)
        if key==tuple(locked['condition'][k] for k in FEATURES) or key in seen:raise ValueError('기준 또는 중복 조건을 추천함')
        seen.add(key)
        expected=100*(base['summary']['cycle_time']-r['summary']['cycle_time'])/base['summary']['cycle_time']
        if not math.isclose(rec['time_change_percent'],expected,abs_tol=1e-6):raise ValueError('시간 단축률 불일치')
        if rec['decision']!=judge(r['summary'],locked['limits']):raise ValueError('후보 제약 판정 불일치')
        scores.append(goal_score(r['summary'],locked['target'],base['summary'],locked['limits'],opt['objective_weights']))
    if scores!=sorted(scores):raise ValueError('목표별 추천 순서 불일치')


def finalize_legacy(state=None,limits=None):
    lim={**LIMITS,**(limits or {})};base=state['physical'];verify_result(base)
    for rec in (state.get('optimization') or {}).get('recommendations',[]):
        verify_result(rec['result'])
        if not judge(rec['result']['summary'],lim)['feasible']:raise ValueError('검증 실패 추천')
    state['llm_raw_answer_untrusted']=state.get('answer')
    s=base['summary'];state['answer']=f"검증된 기준 물리 계산: Tmax {s['Tmax']:.2f}°C, 최대 편차 {s['delta_Tmax']:.2f}°C, 최종 최저 경화도 {s['final_DoC']:.4f}, 공정시간 {s['cycle_time']:.2f}분. 외부 실험 검증 전입니다."
    recs=(state.get('optimization') or {}).get('recommendations',[])
    state['answer']+=f' 물리 재검증 추천 {len(recs)}개.'
    state['result_guard']={'status':'passed','controller':'deterministic_v14','llm_numeric_answer_used':False}
