# [NEW v14] Observed-boundary reconstruction is separate from nominal AI optimization.
import numpy as np
from core import simulate
from web_bridge import _parse_payload
from measured_boundary_v11 import validate_history
from integrity_v14 import verify_result
from chat_bridge import serialize_verified
from review_store_v14 import register_display

def reconstruct(body=None):
    if not isinstance(body,dict) or set(body)-{'inputs','boundary_history','observations'} or not {'inputs','boundary_history'}<=set(body):raise ValueError('inputs와 boundary_history가 필요합니다.')
    condition,options,limits=_parse_payload(body['inputs'])
    history=validate_history(body['boundary_history'])
    if len(history)>10000:raise ValueError('실측 경계는 최대 10000행입니다.')
    if options.get('tool_outer_bc','prescribed')!='prescribed':raise ValueError('실측 tool_c는 금형 외면 지정온도(prescribed)가 필요합니다.')
    result=simulate(condition,options,boundary_history=history)
    guard=verify_result(result,True)
    display=serialize_verified(result,limits)
    for key in ('boundary_input_kind','qualification','cycle_time_kind','initial_temperature_basis'):display[key]=result[key]
    display['result_guard']=guard
    observations=body.get('observations')
    if observations is not None:
        if not isinstance(observations,dict) or set(observations)!={'time_min','center_c'}:raise ValueError('observations: time_min/center_c가 필요합니다.')
        tm=np.asarray(observations['time_min'],float);actual=np.asarray(observations['center_c'],float)
        if tm.ndim!=1 or actual.shape!=tm.shape or not len(tm) or not np.isfinite(tm).all() or not np.isfinite(actual).all() or np.any(tm<0) or np.any(tm>history[-1,0]) or np.any(np.diff(tm)<=0):raise ValueError('관측값은 이력 범위 안의 유한한 증가 시간이어야 합니다.')
        residual=np.interp(tm,result['t'],result['T'][:,len(result['z'])//2])-actual
        display['observation_diagnostic']={'n':len(tm),'rmse_c':float(np.sqrt(np.mean(residual**2))),'max_abs_error_c':float(np.abs(residual).max()),'independent_validation':False,'qualification':'Uploaded observations only; independence and calibration reuse are not established'}
    return register_display(display)
