# [NEW v14] Compact review output; full histories are a separate compressed artifact.
import io,json
import numpy as np
HISTORY_KEYS={'t','z','T','alpha','T_air','z_tool','T_tool','q_contact','T_part_top_surface','T_part_bottom_surface','T_tool_interface_surface','T_tool_outer_surface','boundary_history'}

def trim_history(value=None):
    if not isinstance(value,dict):return value
    return {k:v for k,v in value.items() if k not in HISTORY_KEYS}

def compact(value=None):
    if isinstance(value,dict):return {str(k):compact(v) for k,v in trim_history(value).items() if k not in ('models','report','llm_raw_answer_untrusted','result')}
    if isinstance(value,np.ndarray):return {'array_shape':list(value.shape),'storage':'histories.npz'}
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,(list,tuple)):return [compact(v) for v in value]
    return value

def history_archive(state=None):
    arrays={};results=[]
    if state.get('physical') is not None:results.append(('baseline',state['physical']))
    for i,rec in enumerate((state.get('optimization') or {}).get('recommendations',[])):results.append((f'candidate_{i+1}',rec['result']))
    for label,result in results:
        for key in HISTORY_KEYS:
            if key in result:arrays[label+'__'+key]=np.asarray(result[key])
    target=io.BytesIO();np.savez_compressed(target,**arrays);return target.getvalue()

def compact_report(state=None):
    from reporting import generate_report
    return generate_report(compact(state))
