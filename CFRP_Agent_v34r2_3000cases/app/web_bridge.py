# [NEW v04] JSON bridge between the browser UI and the existing physical solver.
"""Browser-safe serialization for the CFRP physical model; public arguments default to None."""
import json
import math
import numpy as np
from core import DEFAULT, BOUNDS, FEATURES, LIMITS, MATERIAL, MODEL_HASH, PHYSICS_STATUS, simulate, judge


def _finite_number(value=None, name=None):
    if isinstance(value, bool):
        raise ValueError(f'{name or "value"} must be numeric')
    x=float(value)
    if not math.isfinite(x):
        raise ValueError(f'{name or "value"} must be finite')
    return x


def browser_config(config=None):
    """Return only the documented inputs that the HTML UI may edit."""
    _=config
    bd=MATERIAL['boundary'];tm=MATERIAL['tool'];ini=MATERIAL['initial']
    return {
        'model_version':MATERIAL['version'],
        'model_hash':MODEL_HASH,
        'features':FEATURES,
        'defaults':dict(DEFAULT),
        'training_bounds':{k:list(v) for k,v in BOUNDS.items()},
        'limits':dict(LIMITS),
        'physics_status':dict(PHYSICS_STATUS),
        'solver_defaults':{
            'tool_thickness_mm':float(tm['thickness_mm']),
            'h_top':float(bd['h_top']),
            'contact_h':float(bd['contact_h']),
            'contact_h_cooldown':bd['contact_h_cooldown'],
            'tool_outer_bc':str(bd['tool_outer_bc']),
            'tool_outer_h':float(bd['tool_outer_h']),
            'cool_rate':float(ini['cool_rate']),
            'release_temperature_c':float(ini['release_temperature_c'])
        },
        'units':{
            'ramp1':'°C/min','T1':'°C','hold1':'min','ramp2':'°C/min','T2':'°C','hold2':'min','thickness':'mm',
            'tool_thickness_mm':'mm','h_top':'W/(m²·K)','contact_h':'W/(m²·K)','contact_h_cooldown':'W/(m²·K)',
            'tool_outer_h':'W/(m²·K)','cool_rate':'°C/min','release_temperature_c':'°C'
        }
    }


def _parse_payload(payload=None):
    p=dict(payload or {})
    allowed={'condition','options','limits'}
    extra=set(p)-allowed
    if extra:
        raise ValueError('Unknown request fields: '+','.join(sorted(extra)))
    condition=dict(p.get('condition') or {})
    options=dict(p.get('options') or {})
    limits=dict(LIMITS);limits.update(p.get('limits') or {})
    # Keep the web surface explicit rather than forwarding arbitrary solver knobs.
    allowed_options={'tool_thickness_mm','h_top','contact_h','contact_h_cooldown','tool_outer_bc','tool_outer_h','cool_rate','release_temperature_c'}
    extra_options=set(options)-allowed_options
    if extra_options:
        raise ValueError('Unknown web solver options: '+','.join(sorted(extra_options)))
    for key in ['tool_thickness_mm','h_top','contact_h','tool_outer_h','cool_rate','release_temperature_c']:
        if key in options and options[key] is not None:
            options[key]=_finite_number(options[key],key)
    if 'contact_h_cooldown' in options:
        if options['contact_h_cooldown'] in ('',None): options['contact_h_cooldown']=None
        else: options['contact_h_cooldown']=_finite_number(options['contact_h_cooldown'],'contact_h_cooldown')
    if 'tool_outer_bc' in options:
        options['tool_outer_bc']=str(options['tool_outer_bc']).strip().lower()
    for key in LIMITS:
        limits[key]=_finite_number(limits[key],key)
    return condition,options,limits


def _rowwise(values=None):
    return np.asarray(values,dtype=float).tolist()


def simulate_payload(payload=None):
    """Apply browser inputs to core.simulate and return plot-ready JSON data."""
    condition,options,limits=_parse_payload(payload)
    result=simulate(condition,options)
    # [NEW v14] All browser-displayed arrays pass independent integrity checks.
    from integrity_v14 import verify_result
    verify_result(result)
    decision=judge(result['summary'],limits)
    mid=len(result['z'])//2
    out={
        'condition':result['condition'],
        'options':result['options'],
        'summary':result['summary'],
        'decision':decision,
        'outside_training_domain':result['outside_training_domain'],
        'external_validation_passed':result['external_validation_passed'],
        'physics_status':result['physics_status'],
        'model_version':result['model_version'],
        'model_hash':result['model_hash'],
        'series':{
            't':_rowwise(result['t']),
            'T_air':_rowwise(result['T_air']),
            'T_part_top_surface':_rowwise(result['T_part_top_surface']),
            'T_part_center':_rowwise(result['T'][:,mid]),
            'T_part_bottom_surface':_rowwise(result['T_part_bottom_surface']),
            'T_tool_interface_surface':_rowwise(result['T_tool_interface_surface']),
            'T_tool_outer_surface':_rowwise(result['T_tool_outer_surface']),
            'alpha_top_cell':_rowwise(result['alpha'][:,0]),
            'alpha_center_cell':_rowwise(result['alpha'][:,mid]),
            'alpha_bottom_cell':_rowwise(result['alpha'][:,-1]),
            'alpha_min':_rowwise(result['alpha'].min(axis=1)),
            'q_contact':_rowwise(result['q_contact'])
        },
        'field':{
            'z_part':_rowwise(result['z']),
            'z_tool':_rowwise(result['z_tool']),
            'T_part':_rowwise(result['T']),
            'alpha_part':_rowwise(result['alpha']),
            'T_tool':_rowwise(result['T_tool'])
        }
    }
    # [NEW v14] Bind human review to this exact server result.
    from review_store_v14 import register_display
    return register_display(out)


def dumps_payload(payload=None):
    return json.dumps(simulate_payload(payload),ensure_ascii=False,separators=(',',':'))
