# [NEW v11] Separate local AI layer; no changes to the existing physics or surrogate.
"""Ollama JSON extraction -> validated inputs -> surrogate -> mandatory physics.

Customization points are documented in AI_CUSTOMIZE.md, not hidden in comments.
All optional public inputs default to None. No global monkey-patching is used.
"""
import argparse
import copy
import json
import math
import re  # [NEW v11] Independent checks against explicitly written user values.
import sys  # [NEW v11] Windows CLI output uses UTF-8.
import time
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests
from core import ROOT, FEATURES, TARGETS, LIMITS, MATERIAL, normalize, judge, simulate, ood

ACTION_NAMES = ('simulate_process', 'predict_process', 'optimize_cycle')
TARGET_NAMES = ('minimize_time', 'minimize_peak', 'minimize_spread', 'balanced')
SEARCH_NAMES = tuple(k for k in FEATURES if k != 'thickness')
SPEC_KEYS = {'action', 'target', 'material', 'temperature_unit', 'condition_patch',
             'limits_patch', 'search_variables', 'needs_clarification', 'clarification_question'}


# [NEW v11] Configuration validation happens before contacting Ollama or running physics.
def finite_number(value=None, name=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: JSON 숫자여야 합니다.')
    if not math.isfinite(float(value)):
        raise ValueError(f'{name}: 유한한 숫자여야 합니다.')
    return float(value)


def bounded_integer(value=None, name=None, bounds=None):
    number = finite_number(value, name)
    low, high = bounds
    if not number.is_integer() or not low <= number <= high:
        raise ValueError(f'{name}: {low}~{high} 범위의 정수여야 합니다.')
    return int(number)


def resource_path(value=None):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('설정의 파일 경로는 문자열이어야 합니다.')
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('프롬프트/스키마 파일은 프로젝트 폴더 안에 두십시오.')
    return path


def load_config(config=None):
    defaults = json.loads((ROOT / 'config/ai_ollama.json').read_text(encoding='utf-8'))
    if config is None:
        cfg = defaults
    elif isinstance(config, dict):
        unknown = set(config) - set(defaults)
        if unknown:
            raise ValueError('알 수 없는 AI 설정: ' + ','.join(sorted(unknown)))
        cfg = {**defaults, **copy.deepcopy(config)}
    else:
        path = Path(config)
        cfg = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(cfg, dict) or set(cfg) != set(defaults):
            raise ValueError('AI 설정 파일의 필드가 config/ai_ollama.json 계약과 다릅니다.')
    if cfg.get('version') != 'v11':
        raise ValueError('AI 설정 version은 v11이어야 합니다.')
    address = cfg.get('base_url')
    parsed = urlparse(address) if isinstance(address, str) else None
    if not parsed or parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('base_url에는 Ollama 서버의 http(s) 주소와 포트만 넣으십시오.')
    if not isinstance(cfg.get('model'), str) or not cfg['model'].strip():
        raise ValueError('model에 ollama list의 모델명을 지정하십시오.')
    cfg['base_url'] = address.rstrip('/')
    cfg['timeout_seconds'] = bounded_integer(cfg['timeout_seconds'], 'timeout_seconds', (1, 600))
    for name, bounds in [('json_retries', (0, 2)), ('num_predict', (64, 4096)),
                         ('candidate_count', (1, 10000)), ('top_k', (1, 20)),
                         ('max_feedback_rounds', (1, 4)), ('recommendation_count', (1, 3))]:
        cfg[name] = bounded_integer(cfg[name], name, bounds)
    cfg['temperature'] = finite_number(cfg['temperature'], 'temperature')
    if not 0 <= cfg['temperature'] <= 2:
        raise ValueError('temperature는 0~2 범위여야 합니다.')
    variables = cfg['default_search_variables']
    if not isinstance(variables, list) or not variables or any(not isinstance(v, str) or v not in SEARCH_NAMES for v in variables) or len(set(variables)) != len(variables):
        raise ValueError('default_search_variables에 허용된 중복 없는 공정변수를 넣으십시오.')
    # Only mesh/time settings vary; material/boundary/reaction conditions match training.
    options = cfg['solver_options']
    if not isinstance(options, dict) or set(options) - {'nz', 'tool_nz', 'dt', 'save_seconds'}:
        raise ValueError('solver_options는 nz/tool_nz/dt/save_seconds만 허용합니다.')
    if 'nz' in options:
        nz = bounded_integer(options['nz'], 'nz', (5, 201))
        if nz % 2 == 0:
            raise ValueError('nz는 홀수여야 합니다.')
    if 'tool_nz' in options:
        bounded_integer(options['tool_nz'], 'tool_nz', (3, 201))
    dt = finite_number(options.get('dt', 2.0), 'dt')
    save = finite_number(options.get('save_seconds', 30.0), 'save_seconds')
    if not 0.1 <= dt <= 10 or not dt <= save <= 600:
        raise ValueError('dt는 0.1~10초, save_seconds는 dt~600초 범위여야 합니다.')
    weights = cfg['objective_weights']
    if not isinstance(weights, dict) or set(weights) != {'time', 'peak', 'spread'}:
        raise ValueError('objective_weights에는 time/peak/spread가 필요합니다.')
    weights = {k: finite_number(v, k) for k, v in weights.items()}
    if any(v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError('목적 가중치는 음수가 아니며 합이 0보다 커야 합니다.')
    cfg['objective_weights'] = {k: v / sum(weights.values()) for k, v in weights.items()}
    for name in ('prompt_file', 'schema_file'):
        resource_path(cfg[name])
    return copy.deepcopy(cfg)


def ollama_health(config=None):
    cfg = load_config(config)
    try:
        response = requests.get(cfg['base_url'] + '/api/tags', timeout=5)
        response.raise_for_status()
        models = [m['name'] for m in response.json().get('models', [])]
        available = cfg['model'] in models or (':' not in cfg['model'] and cfg['model'] + ':latest' in models)
        return {'ok': available, 'server_reachable': True, 'model': cfg['model'], 'models': models,
                'error': None if available else '설정 모델이 없습니다. ollama pull ' + cfg['model']}
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        return {'ok': False, 'server_reachable': False, 'model': cfg['model'], 'models': [],
                'error': 'Ollama 연결 확인 실패: ' + str(error)}


def validate_spec(spec=None):
    if not isinstance(spec, dict) or set(spec) != SPEC_KEYS:
        raise ValueError('AI JSON의 필수/허용 필드가 일치하지 않습니다.')
    if spec['action'] not in ACTION_NAMES or spec['target'] not in TARGET_NAMES:
        raise ValueError('지원하지 않는 action/target입니다.')
    if not isinstance(spec['material'], str) or not spec['material'].strip():
        raise ValueError('material은 문자열이어야 합니다.')
    if spec['temperature_unit'] not in ('C', 'K'):
        raise ValueError('temperature_unit은 C 또는 K여야 합니다.')
    if not isinstance(spec['needs_clarification'], bool):
        raise ValueError('needs_clarification은 boolean이어야 합니다.')
    question = spec['clarification_question']
    if question is not None and not isinstance(question, str):
        raise ValueError('clarification_question은 문자열 또는 null이어야 합니다.')
    variables = spec['search_variables']
    if not isinstance(variables, list) or any(not isinstance(v, str) or v not in SEARCH_NAMES for v in variables) or len(set(variables)) != len(variables):
        raise ValueError('search_variables에 지원하지 않는 변수/중복이 있습니다.')
    out = copy.deepcopy(spec)
    for field, allowed in [('condition_patch', set(FEATURES)), ('limits_patch', set(LIMITS))]:
        patch = out[field]
        if not isinstance(patch, dict) or set(patch) - allowed:
            raise ValueError(field + ': 알 수 없는 입력 필드입니다.')
        out[field] = {k: finite_number(v, field + '.' + k) for k, v in patch.items()}
    if out['temperature_unit'] == 'K':
        for key in ('T1', 'T2'):
            if key in out['condition_patch']:
                out['condition_patch'][key] -= 273.15
        if 'Tmax' in out['limits_patch']:
            out['limits_patch']['Tmax'] -= 273.15
    out['temperature_unit'] = 'C'
    if out['material'] != 'AS4_8552':
        out['needs_clarification'] = True
        out['clarification_question'] = '현재 물리 모델은 AS4/8552만 지원합니다. 이 재료를 사용하시겠습니까?'
    if out['needs_clarification'] and not (out['clarification_question'] or '').strip():
        raise ValueError('확인이 필요한 요청에는 clarification_question이 필요합니다.')
    return out


# [NEW v11] Gemma2 uses schema-constrained JSON; Python owns tool dispatch.
def extract_request(request=None, condition=None, limits=None, config=None, transport=None, event_sink=None):
    cfg = load_config(config)
    if not isinstance(request, str) or not request.strip() or len(request) > 4000:
        raise ValueError('요청은 1~4000자의 문자열이어야 합니다.')
    prompt = resource_path(cfg['prompt_file']).read_text(encoding='utf-8')
    schema = json.loads(resource_path(cfg['schema_file']).read_text(encoding='utf-8'))
    if not isinstance(schema, dict) or schema.get('type') != 'object':
        raise ValueError('schema_file은 JSON object 스키마여야 합니다.')
    # [NEW v11] Baseline numbers stay in Python; do not invite model copying into patches.
    context = {'request': request, 'missing_values': '미지정 숫자는 patch에 넣지 말고 빈 객체로 유지'}
    # [NEW v33] Supply only independently parsed evidence, never baseline guesses.
    from request_semantics_v33 import interpretation_context
    semantic_evidence, semantic_template = interpretation_context(request, cfg['default_search_variables'])
    if semantic_evidence['issues']:
        return {'action': semantic_evidence['expected_action'], 'target': semantic_evidence['expected_target'] or 'balanced', 'material': 'AS4_8552', 'temperature_unit': 'C', 'condition_patch': {}, 'limits_patch': {}, 'search_variables': [], 'needs_clarification': True, 'clarification_question': '; '.join(semantic_evidence['issues'])}
    context['independent_request_evidence_v33'] = semantic_template
    # [NEW v33] Request-specific JSON constraints prohibit unsupported task/scope fields.
    from request_semantics_v33 import constrained_schema
    schema = constrained_schema(schema, semantic_template)
    messages = [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(context, ensure_ascii=False, allow_nan=False)}]
    for attempt in range(cfg['json_retries'] + 1):
        payload = {'model': cfg['model'], 'messages': messages, 'format': schema, 'stream': False,
                   'options': {'temperature': cfg['temperature'], 'num_predict': cfg['num_predict']}}
        # [NEW v14] Qwen3 structured extraction explicitly requests non-thinking output.
        from llm_profiles_v14 import prepare_ollama_payload
        prepare_ollama_payload(payload)
        if event_sink:
            event_sink({'phase': 'interpretation', 'status': 'started', 'detail': {'attempt': attempt + 1, 'model': cfg['model']}})
        try:
            if transport is not None:
                response = transport(payload)
            else:
                http = requests.post(cfg['base_url'] + '/api/chat', json=payload, timeout=cfg['timeout_seconds'])
                if http.status_code != 200:
                    raise RuntimeError(f'Ollama HTTP {http.status_code}: 모델명과 서버 설정을 확인하십시오.')
                response = http.json()
        except requests.RequestException as error:
            raise RuntimeError('Ollama 통신 실패. ollama serve / 모델 다운로드 / base_url을 확인하십시오.') from error
        if not isinstance(response, dict) or response.get('error'):
            raise RuntimeError('Ollama 오류 응답: ' + str((response or {}).get('error') if isinstance(response, dict) else '응답 객체 형식 오류'))
        message = response.get('message')
        content = message.get('content') if isinstance(message, dict) else None
        try:
            if not isinstance(content, str) or len(content) > 32000:
                raise ValueError('Ollama message.content가 제한 내 문자열이 아닙니다.')
            spec = json.loads(content, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('비유한 JSON 숫자: ' + value)))
            validated = validate_spec(spec)
            validate_request_grounding(request, spec, validated)  # [NEW v11]
            # [NEW v12] Independent policy review; model cannot approve its own interpretation.
            if not validated['needs_clarification']:
                from AI_guard import review_request
                guard = review_request(request, validated, cfg['default_search_variables'])
                if event_sink:
                    event_sink({'phase': 'request_guard', 'status': guard['status'], 'detail': guard})
                if guard['status'] != 'passed':
                    # [NEW v33] One bounded JSON retry uses the exact independent mismatch.
                    if attempt < cfg['json_retries']:
                        raise ValueError('; '.join(guard['issues']))
                    validated['needs_clarification'] = True
                    validated['clarification_question'] = '요청 검증을 통과하지 못했습니다: ' + '; '.join(guard['issues']) + ' 값을 구체적으로 적어 다시 요청하십시오.'
            if event_sink:
                event_sink({'phase': 'interpretation', 'status': 'completed', 'detail': validated})
            return validated
        except (ValueError, TypeError) as error:
            if event_sink:
                event_sink({'phase': 'interpretation', 'status': 'retry' if attempt < cfg['json_retries'] else 'failed', 'detail': {'error': str(error)}})
            if attempt == cfg['json_retries']:
                raise ValueError('AI 구조화 응답 검사 실패: ' + str(error)) from error
            messages.append({'role': 'assistant', 'content': content if isinstance(content, str) else ''})
            messages.append({'role': 'user', 'content': '이전 JSON 검사가 실패했습니다: ' + str(error) + '. 동일 요청을 스키마에 맞춰 JSON만 다시 출력하십시오.'})
    raise RuntimeError('AI 추출을 완료하지 못했습니다.')


# [NEW v11] Guard common unit/material hallucinations before any physics/tool dispatch.
def validate_request_grounding(request=None, raw_spec=None, validated=None):
    # [NEW v33] Compare field-specific canonical units instead of any request number.
    from request_semantics_v33 import grounding
    if isinstance(validated, dict):
        return grounding(request, validated)
    text = re.sub(r'AS4\s*[/_]\s*8552|AS4|8552', '', request, flags=re.I)
    values = [float(v) for v in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?', text)]
    # [NEW v12] Korean words immediately before a number must not hide that number.
    values.extend(float(v) for v in re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?', text))
    grounded = {converted for value in values for converted in
                (value, value * 10, value * 60, value / 100, value - 273.15, value + 273.15)}
    for field in ('condition_patch', 'limits_patch'):
        for key, value in raw_spec[field].items():
            if not any(math.isclose(value, candidate, abs_tol=1e-6) for candidate in grounded):
                raise ValueError(f'{field}.{key}: 사용자가 명시하지 않은 숫자를 추가했습니다. 미지정 필드는 생략하십시오.')
    kelvin = re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:K\b|켈빈)', request, flags=re.I)
    celsius = re.findall(r'(-?\d+(?:\.\d+)?)\s*(?:°?\s*C\b|℃|도|섭씨)', request, flags=re.I)
    absolute = [validated['condition_patch'][k] for k in ('T1', 'T2') if k in validated['condition_patch']]
    if 'Tmax' in validated['limits_patch']:
        absolute.append(validated['limits_patch']['Tmax'])
    if kelvin and not celsius and not re.search(r'편차|온도차|차이|delta', request, re.I):
        converted = [float(v) - 273.15 for v in kelvin]
        if any(not any(math.isclose(v, k, abs_tol=1e-6) for k in converted) for v in absolute):
            raise ValueError('요청의 절대온도는 K입니다. temperature_unit=K로 원래 수치를 넣거나 정확히 C로 환산하십시오.')
    unsupported = re.search(r'알루미늄|alumin(?:um|ium)|강철|steel|티타늄|titanium|유리섬유|glass\s*fiber', request, re.I)
    if unsupported and not validated['needs_clarification']:
        raise ValueError('지원하지 않는 재료가 명시되었습니다. needs_clarification=true와 확인 질문을 출력하십시오.')
    # [NEW v11] An explicitly requested full search cannot silently omit hold temperatures.
    compact = re.sub(r'\s+', '', request)
    if all(term in compact for term in ('승온속도', '유지온도', '유지시간', '모두')):
        if set(validated['search_variables']) != set(SEARCH_NAMES):
            raise ValueError('승온속도·유지온도·유지시간 모두 요청했습니다. search_variables는 ramp1,T1,hold1,ramp2,T2,hold2 전체여야 합니다.')


def merge_inputs(spec=None, condition=None, limits=None):
    c = normalize(condition)
    c.update(spec['condition_patch'])
    c = normalize(c)
    lim = dict(LIMITS)
    if limits is not None:
        if not isinstance(limits, dict) or set(limits) - set(LIMITS):
            raise ValueError('기준 limits 필드가 올바르지 않습니다.')
        lim.update({k: finite_number(v, k) for k, v in limits.items()})
    lim.update(spec['limits_patch'])
    # Validate limit ranges before any expensive calculation.
    judge({'Tmax': 25.0, 'delta_Tmax': 0.0, 'final_DoC': 1.0}, lim)
    return c, lim


def goal_score(summary=None, target=None, baseline=None, limits=None, weights=None):
    if target == 'minimize_time':
        return float(summary['cycle_time'])
    if target == 'minimize_peak':
        return float(summary['Tmax'])
    if target == 'minimize_spread':
        return float(summary['delta_Tmax'])
    return (weights['time'] * summary['cycle_time'] / baseline['cycle_time'] +
            weights['peak'] * summary['Tmax'] / limits['Tmax'] +
            weights['spread'] * summary['delta_Tmax'] / limits['delta_Tmax'])


# [NEW v11] Separate objective-aware optimizer; legacy optimizer.py remains byte-identical.
def optimize_ai(condition=None, bundle=None, limits=None, target=None, search_variables=None,
                config=None, event_sink=None, baseline=None):
    from pipeline import sample_conditions, predict_batch
    cfg = load_config(config)
    c = normalize(condition, True)
    lim = dict(LIMITS)
    lim.update(limits or {})
    judge({'Tmax': 25.0, 'delta_Tmax': 0.0, 'final_DoC': 1.0}, lim)
    target = target or 'minimize_time'
    if target not in TARGET_NAMES:
        raise ValueError('지원하지 않는 최적화 목표입니다.')
    variables = cfg['default_search_variables'] if search_variables is None else search_variables
    if not isinstance(variables, list) or not variables or any(v not in SEARCH_NAMES for v in variables) or len(set(variables)) != len(variables):
        raise ValueError('최적화할 변수를 올바르게 지정하십시오.')
    start = time.perf_counter()
    base = baseline if baseline is not None else simulate(c, cfg['solver_options'])
    # [NEW v17] Stop missing tool results before indexing.
    from async_runtime_v17 import require_result
    require_result(base, "base")
    if base['condition'] != c or any(base['options'].get(k) != v for k, v in cfg['solver_options'].items()):
        raise ValueError('기준 계산의 조건/격자 옵션이 후보 계산과 다릅니다.')
    checked, valid, feedback = [], [], []
    screened = 0
    margins = {'Tmax': 0.0, 'delta_Tmax': 0.0, 'final_DoC': 0.0}  # [NEW v11]
    seen = {tuple(c[k] for k in FEATURES)}

    def emit(phase=None, status=None, detail=None):
        if event_sink:
            event_sink({'phase': phase, 'status': status, 'detail': detail})

    for round_index in range(cfg['max_feedback_rounds']):
        emit('candidate_search', 'started', {'round': round_index + 1, 'variables': variables})
        sampled = sample_conditions(cfg['candidate_count'], 42 + round_index, c['thickness'])
        candidates, batch_seen = [], set()
        for sample in sampled:
            candidate = dict(c)
            candidate.update({k: sample[k] for k in variables})
            key = tuple(candidate[k] for k in FEATURES)
            if key not in seen and key not in batch_seen:
                candidates.append(candidate)
                batch_seen.add(key)
        if not candidates:
            feedback.append({'round': round_index + 1, 'action': 'no_new_candidates', 'rechecked': 0})
            continue
        emit('surrogate', 'started', {'round': round_index + 1, 'candidate_count': len(candidates)})
        predictions = predict_batch(candidates, bundle)
        if predictions.shape != (len(candidates), len(TARGETS)) or not np.isfinite(predictions).all():
            raise ValueError('대리모델 예측의 크기/유한값이 올바르지 않습니다.')
        screened += len(candidates)
        # [NEW v11] Conservative observed-error screening; actual limits never change.
        penalty = (np.maximum(predictions[:, 0] + margins['Tmax'] - lim['Tmax'], 0) / 5 +
                   np.maximum(predictions[:, 1] + margins['delta_Tmax'] - lim['delta_Tmax'], 0) / 5 +
                   np.maximum(lim['final_DoC'] - (predictions[:, 2] - margins['final_DoC']), 0) / .01)
        scores = np.array([goal_score(dict(zip(TARGETS, map(float, row))), target,
                                     base['summary'], lim, cfg['objective_weights']) for row in predictions])
        # Predicted violation is the primary key; the requested objective is secondary.
        selected = np.lexsort((scores, penalty))[:cfg['top_k']]
        emit('surrogate', 'completed', {'screened': len(candidates), 'selected': len(selected)})
        for index in selected:
            candidate = candidates[int(index)]
            seen.add(tuple(candidate[k] for k in FEATURES))
            candidate_id = f'r{round_index + 1}-c{int(index)}'
            predicted = dict(zip(TARGETS, map(float, predictions[int(index)])))
            emit('physics_validation', 'started', {'candidate_id': candidate_id, 'condition': candidate})
            item = {'condition': candidate, 'predicted': predicted, 'feedback_round': round_index + 1,
                    'candidate_id': candidate_id, 'baseline_candidate': False}
            try:
                result = simulate(candidate, cfg['solver_options'])
                # [NEW v17] Stop missing tool results before indexing.
                from async_runtime_v17 import require_result
                require_result(result, "result")
                decision = judge(result['summary'], lim)
                actual = result['summary']
                errors = {k: actual[k] - predicted[k] for k in TARGETS}
                # [NEW v11] Carry worst observed unsafe residual into the next batch.
                for name in ('Tmax', 'delta_Tmax'):
                    margins[name] = max(margins[name], errors[name], 0.0)
                margins['final_DoC'] = max(margins['final_DoC'], -errors['final_DoC'], 0.0)
                item.update({'actual': actual, 'decision': decision, 'result': result, 'prediction_error': errors})
                if decision['feasible']:
                    valid.append(item)
                emit('physics_validation', 'accepted' if decision['feasible'] else 'rejected',
                     {'candidate_id': candidate_id, 'actual': actual, 'checks': decision['checks'], 'prediction_error': errors})
            except ValueError as error:
                item.update({'decision': {'feasible': False}, 'error': str(error)})
                emit('physics_validation', 'rejected', {'candidate_id': candidate_id, 'error': str(error)})
            checked.append(item)
        action = 'accept_candidates' if valid else ('resample_same_constraints' if round_index + 1 < cfg['max_feedback_rounds'] else 'stop_no_feasible_candidate')
        feedback.append({'round': round_index + 1, 'screened': len(candidates), 'rechecked': len(selected),
                         'physics_feasible_nonbaseline': len(valid), 'action': action,
                         'screening_margins': dict(margins)})  # [NEW v11]
        emit('feedback', 'completed', {'round': round_index + 1, 'action': action, 'limits': lim,
                                       'screening_margins': dict(margins),  # [NEW v11]
                                       'message': '물리 검증 오차로 예측 필터를 보정했습니다. 실제 제약을 유지합니다.'})
        if valid:
            break
    valid.sort(key=lambda item: goal_score(item['actual'], target, base['summary'], lim, cfg['objective_weights']))
    recommendations = valid[:cfg['recommendation_count']]
    for item in recommendations:
        item['time_change_percent'] = 100 * (base['summary']['cycle_time'] - item['actual']['cycle_time']) / base['summary']['cycle_time']
    return {'baseline': base, 'checked': checked, 'recommendations': recommendations, 'limits': lim,
            'screened': screened, 'rechecked': len(checked), 'feedback_rounds': feedback,
            'target': target, 'search_variables': list(variables), 'objective_weights': cfg['objective_weights'],
            'status': '물리 검증 통과 후보' if recommendations else '조건 만족 후보 없음 — 제약 유지 후 종료',
            'seconds': time.perf_counter() - start, 'external_validation_passed': False,
            'scope': 'development demonstration; best among physics-checked candidates, not a global optimum'}


def json_ready(value=None):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items() if k != 'models'}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    return value


# [NEW v11] No unverified LLM numbers enter the final answer or the charts.
def run_ai(request=None, condition=None, bundle=None, limits=None, config=None,
           transport=None, memory=None, event_sink=None, spec=None, preview_only=None):  # [NEW v34]
    cfg = load_config(config)
    request = request or '현재 공정을 분석해줘'
    state = {'request': request, 'mode': 'ollama', 'model': cfg['model'], 'events': [], 'results': {},
             'trace': [], 'approval': 'pending', 'external_validation_passed': False,
             'status': 'running', 'memory_before': copy.deepcopy(memory or {})}

    def emit(event=None):
        ev = dict(event or {})
        ev.update({'sequence': len(state['events']) + 1, 'time_seconds': time.perf_counter(),
                   'tool': ev.get('phase', 'workflow'), 'output': ev.get('detail')})
        state['events'].append(ev)
        state['trace'].append({'phase': ev.get('phase'), 'status': ev.get('status'), 'detail': ev.get('detail')})
        if event_sink:
            event_sink(ev)

    try:
        parsed = validate_spec(spec) if spec is not None else extract_request(request, condition, limits, cfg, transport, emit)
        # [NEW v17] Direct spec calls undergo the same grounding and request Guard.
        if spec is not None:
            validate_request_grounding(request, spec, parsed)
            from AI_guard import review_request
            guard = review_request(request, parsed, cfg['default_search_variables'])
            emit({'phase': 'request_guard', 'status': guard['status'], 'detail': guard})
            if guard['status'] != 'passed':
                parsed['needs_clarification'] = True
                parsed['clarification_question'] = '요청 검증 실패: ' + '; '.join(guard['issues'])
        state['interpreted_request'] = parsed
        if parsed['needs_clarification']:
            state.update({'status': 'needs_clarification', 'answer': parsed['clarification_question'], 'plan': []})
            emit({'phase': 'clarification', 'status': 'required', 'detail': state['answer']})
            return state
        # [NEW v34] Web preview uses all v33 guards and stops before any tool calculation.
        if preview_only is True:
            from request_preview_v34 import make_preview
            return make_preview(request, parsed, condition, limits, cfg)
        c, lim = merge_inputs(parsed, condition, limits)
        variables = parsed['search_variables'] or cfg['default_search_variables']
        # [NEW v12] Snapshot is separate from mutable tool/state dictionaries.
        from AI_guard import freeze_contract, review_results
        execution_contract = freeze_contract(c, lim, variables, cfg['solver_options'], parsed['target'])
        state['execution_contract'] = copy.deepcopy(execution_contract)
        state.update({'condition': c, 'limits': lim, 'parsed_changes': parsed['condition_patch'],
                      'goal': parsed['target'], 'plan': ['명시 입력과 기준값 병합', '근거 조회', '기준 물리 계산'] +
                      (['대리모델 후보 평가', '후보 물리 재검증', '같은 제약으로 필요시 재탐색'] if parsed['action'] == 'optimize_cycle' else []) + ['검증 결과·그래프·보고서'],
                      'assumptions': {'condition_defaults_used': [k for k in FEATURES if k not in parsed['condition_patch']],
                                      'limits_preserved': [k for k in LIMITS if k not in parsed['limits_patch']]}})
        emit({'phase': 'planning', 'status': 'completed', 'detail': {'plan': state['plan'], 'condition': c, 'limits': lim, 'search_variables': variables, 'assumptions': state['assumptions']}})
        references = {'sources': MATERIAL['sources'], 'assumptions': MATERIAL['assumptions']}
        state['results']['search_reference'] = references
        emit({'phase': 'search_reference', 'status': 'completed', 'detail': references})
        emit({'phase': 'simulate_process', 'status': 'started', 'detail': c})
        physical = simulate(c, cfg['solver_options'])
        # [NEW v17] Stop missing tool results before indexing.
        from async_runtime_v17 import require_result
        require_result(physical, "physical")
        state['physical'] = physical
        state['results']['simulate_process'] = {'summary': physical['summary'], 'decision': judge(physical['summary'], lim)}
        emit({'phase': 'simulate_process', 'status': 'completed', 'detail': state['results']['simulate_process']})
        action = parsed['action']
        if action in ('predict_process', 'optimize_cycle'):
            outside = ood(c)
            if outside:
                state['results'][action] = {'status': 'blocked_outside_training_domain', 'fields': outside}
                state.update({'status': 'blocked', 'answer': '물리 계산은 완료했습니다. 학습범위 밖 항목으로 AI 예측/최적화를 중단했습니다: ' + ', '.join(outside)})
                emit({'phase': action, 'status': 'blocked', 'detail': state['results'][action]})
            else:
                from pipeline import train_surrogate, predict_process
                if bundle is None:
                    emit({'phase': 'surrogate_training', 'status': 'started', 'detail': '동봉된 개발 데이터로 학습합니다.'})
                    bundle = train_surrogate()
                    # [NEW v17] Stop missing tool results before indexing.
                    from async_runtime_v17 import require_result
                    require_result(bundle, "bundle")
                    emit({'phase': 'surrogate_training', 'status': 'completed', 'detail': bundle['report']})
                if action == 'optimize_cycle':
                    optimization = optimize_ai(c, bundle, lim, parsed['target'], variables, cfg, emit, physical)
                    # [NEW v17] Stop missing tool results before indexing.
                    from async_runtime_v17 import require_result
                    require_result(optimization, "optimization")
                    state['optimization'] = optimization
                    state['results'][action] = {'status': optimization['status'], 'recommendation_count': len(optimization['recommendations']), 'feedback_rounds': optimization['feedback_rounds']}
                    recs = optimization['recommendations']
                    if recs:
                        best = recs[0]
                        s = best['actual']
                        state['status'] = 'completed'
                        state['answer'] = f"물리 검증 통과 후보 {len(recs)}개. 첫 후보: {s['cycle_time']:.2f}분, Tmax {s['Tmax']:.2f}°C, 최대 편차 {s['delta_Tmax']:.2f}°C, 최저 최종 경화도 {s['final_DoC']:.4f}. 기준 대비 시간 단축률 {best['time_change_percent']:.2f}%입니다. 탐색·검증한 후보 중 결과이며 외부 실험 검증 전입니다."
                    else:
                        state.update({'status': 'no_feasible_candidate', 'answer': optimization['status']})
                else:
                    prediction = predict_process(c, bundle)
                    # [NEW v17] Stop missing tool results before indexing.
                    from async_runtime_v17 import require_result
                    require_result(prediction, "prediction")
                    state['results'][action] = prediction
                    errors = {k: physical['summary'][k] - prediction['summary'][k] for k in TARGETS}
                    emit({'phase': action, 'status': 'completed', 'detail': {'prediction': prediction, 'physics': physical['summary'], 'prediction_error': errors}})
                    state.update({'status': 'completed', 'answer': '대리모델 예측과 물리 계산을 비교했습니다. 그래프와 최종 판정은 물리 계산값을 사용합니다.'})
        else:
            state.update({'status': 'completed', 'answer': '기준 공정의 물리 계산과 제약 검사를 완료했습니다. 외부 실험 검증 전입니다.'})
        # [NEW v12] Final output gate runs before recommendation memory/report/UI release.
        final_guard = review_results(state, execution_contract)
        state['result_guard'] = final_guard
        emit({'phase': 'result_guard', 'status': final_guard['status'], 'detail': final_guard})
        if final_guard['status'] != 'passed':
            state.update({'status': 'blocked', 'answer': '결과 검증 실패로 추천과 그래프를 차단했습니다: ' + '; '.join(final_guard['issues'])})
            state.pop('physical', None)
            if state.get('optimization') is not None:
                state['optimization']['recommendations'] = []
                state['results']['optimize_cycle']['recommendation_count'] = 0
                state['results']['optimize_cycle']['status'] = 'blocked_by_result_guard'
        prior = dict(memory or {})
        history = list(prior.get('history') or [])[-4:]
        recs = (state.get('optimization') or {}).get('recommendations') or []
        history.append({'request': request, 'condition': c, 'status': state['status'],
                        'recommendation_count': len(recs), 'recommended_condition': recs[0]['condition'] if recs else None})
        state['memory'] = {**prior, 'current_condition': c, 'last_request': request, 'history': history,
                           'run_count': int(prior.get('run_count', 0)) + 1}
        emit({'phase': 'memory', 'status': 'completed', 'detail': {'run_count': state['memory']['run_count']}})
        emit({'phase': 'workflow', 'status': state['status'], 'detail': state['answer']})
        from reporting import generate_report
        state['report'] = generate_report(state)
        return state
    except Exception as error:
        emit({'phase': 'workflow', 'status': 'failed', 'detail': {'error': str(error)}})
        raise


def main():
    # [NEW v11] Avoid cp949 failures on Korean logs and the em dash in old labels.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Ollama Gemma2 CFRP AI v11')
    parser.add_argument('--request')
    parser.add_argument('--config')
    parser.add_argument('--health', action='store_true')
    parser.add_argument('--parse-only', action='store_true')
    parser.add_argument('--output')
    args = parser.parse_args()
    cfg = load_config(args.config)
    if args.health:
        result = ollama_health(cfg)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 1
    if not args.request:
        parser.error('--request를 입력하거나 --health를 사용하십시오.')

    def log(event=None):
        print('[AI v11] ' + json.dumps(json_ready(event), ensure_ascii=False), flush=True)

    if args.parse_only:
        result = extract_request(args.request, config=cfg, event_sink=log)
    else:
        result = run_ai(args.request, config=cfg, event_sink=log)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json_ready(result), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(json_ready(result if args.parse_only else {'status': result['status'], 'answer': result['answer']}), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
