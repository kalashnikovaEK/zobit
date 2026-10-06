# [NEW v12] Independent deterministic controller. No LLM scores or self-approval.
"""Request evidence -> frozen execution contract -> output integrity gate.

Policy/customization and conservative limitations: AI_GUARD_GUIDE.md.
This checks software contracts; it does not certify the underlying physics.
"""
import copy
import hashlib
import json
import math
import re
import numpy as np
from core import ROOT, FEATURES, TARGETS, LIMITS, MODEL_HASH, normalize, judge


def digest(value=None):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode('utf-8')).hexdigest()


def load_policy():
    policy = json.loads((ROOT / 'config/ai_guard_policy.json').read_text(encoding='utf-8'))
    if policy['version'] != 'v12' or set(policy['aliases']) != set(FEATURES + list(LIMITS)):
        raise ValueError('AI guard 정책 필드/버전이 올바르지 않습니다.')
    if not isinstance(policy['max_request_length'], int) or not 1 <= policy['max_request_length'] <= 4000:
        raise ValueError('AI guard 요청 길이 정책이 올바르지 않습니다.')
    for names in policy['aliases'].values():
        if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names):
            raise ValueError('AI guard 별칭은 비어 있지 않은 문자열 목록이어야 합니다.')
    for key in ('unsupported_pattern', 'complex_pattern'):
        re.compile(policy[key])
    return policy


def quantities(request=None, policy=None):
    text = re.sub(r'\s+', '', request)
    # [NEW v14] Do not silently treat C/hour or C/second as C/min.
    rate_issue=bool(re.search(r'(?:°C|℃|C|도)(?:/|per)(?:hour|hr|h(?!old)|시간|sec|s(?!pread)|초)|(?:시간|초)당',text,re.I))
    found, spans, issues = {}, [], []
    # [NEW v14] Reject every unknown rate denominator, not just known hour/second forms.
    denominators=re.findall(r'(?:°C|℃|C|도)(?:/|per)([A-Za-z]+|[가-힣]+)',text,re.I)
    rate_issue=rate_issue or any(not (d.lower() in ('min','minute','minutes') or d.startswith('분')) for d in denominators)
    if rate_issue:issues.append('승온속도는 °C/min 또는 °C/분으로 환산하여 명시하십시오. 다른 분모 단위는 자동 적용하지 않습니다.')
    number = r'(-?\d+(?:\.\d+)?)'
    units = r'(°C|℃|켈빈|mm|cm|min|hour|퍼센트|분|시간|도|C|K|%)?'
    for key, aliases in policy['aliases'].items():
        alias = '|'.join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
        pattern = rf'(?:{alias})(?:은|는|을|를|이|가|:|=|상한|제한|최소|최대)*{number}{units}'
        matches = list(re.finditer(pattern, text, re.I))
        if key == 'thickness' and not matches:
            matches = list(re.finditer(number + r'(mm|cm)', text, re.I))
        values = []
        for match in matches:
            value, unit = float(match.group(1)), (match.group(2) or '').lower()
            if key in ('Tmax', 'T1', 'T2') and unit in ('k', '켈빈'):
                value -= 273.15
            # [NEW v17] Independent unit checks.
            if key == 'thickness' and unit == 'cm':
                value *= 10
            if key in ('hold1', 'hold2') and unit in ('시간', 'hour'):
                value *= 60
            if key == 'final_DoC' and unit in ('%', '퍼센트'):
                value /= 100
            allowed = {'Tmax': {'', '°c', '℃', 'c', 'k', '켈빈', '도'},
                       'T1': {'', '°c', '℃', 'c', 'k', '켈빈', '도'},
                       'T2': {'', '°c', '℃', 'c', 'k', '켈빈', '도'},
                       'delta_Tmax': {'', '°c', '℃', 'c', 'k', '켈빈', '도'},
                       'thickness': {'', 'mm', 'cm'}, 'hold1': {'', '분', 'min', '시간', 'hour'},
                       'hold2': {'', '분', 'min', '시간', 'hour'},
                       'final_DoC': {'', '%', '퍼센트'}, 'ramp1': {'', '°c', 'c', '℃'},
                       'ramp2': {'', '°c', 'c', '℃'}}
            if unit not in allowed[key]:
                issues.append(key + ': 단위를 확인해야 합니다.')
            values.append(value)
            spans.append(match.span())
        if values:
            if any(not math.isclose(v, values[0], abs_tol=1e-6) for v in values):
                issues.append(key + ': 서로 다른 값이 함께 지정되었습니다.')
            else:
                found[key] = values[0]
    # Unparsed numeric clauses are not automatically trusted or ignored.
    cleaned = list(text)
    for start, end in spans:
        cleaned[start:end] = ' ' * (end - start)
    rest = re.sub(r'AS4[/_]8552|AS4|8552|[12]차|ramp[12]|hold[12]|T[12]', '', ''.join(cleaned), flags=re.I)
    if re.search(r'\d', rest):
        issues.append('어느 변수에 적용되는지 규칙으로 확인할 수 없는 숫자가 있습니다.')
    return found, issues


def review_request(request=None, spec=None, default_variables=None):
    # [NEW v33] Independent semantic gate; legacy implementation is retained below.
    from request_semantics_v33 import review
    if isinstance(spec, dict):
        return review(request, spec, default_variables)
    policy = load_policy()
    issues, evidence = [], {}
    text = re.sub(r'\s+', '', request or '')
    if not text or len(text) > policy['max_request_length']:
        issues.append('요청 길이를 확인하십시오.')
    if re.search(policy['unsupported_pattern'], text, re.I):
        issues.append('지원하지 않는 재료/형상 표현이 있어 확인이 필요합니다.')
    if re.search(policy['complex_pattern'], text, re.I):
        issues.append('부정·제외·고정 또는 지원 밖 명령은 구조화 입력으로 명확히 지정하십시오.')
    values, errors = quantities(request or '', policy)
    issues.extend(errors)
    patches = {**spec['condition_patch'], **spec['limits_patch']}
    for key in set(values) | set(patches):
        if key not in values or key not in patches or not math.isclose(values[key], patches[key], abs_tol=1e-6):
            issues.append(key + ': 사용자 근거와 AI의 적용값이 일치하지 않습니다.')
    evidence['quantities_canonical'] = values
    optimizing = bool(re.search(r'최적|찾|줄|단축|최소', text))
    predicting = bool(re.search(r'예측', text))
    # [NEW v17] Policy decisions use independent if statements.
    expected_action = 'simulate_process'
    if predicting and not optimizing:
        expected_action = 'predict_process'
    if optimizing:
        expected_action = 'optimize_cycle'
    evidence['expected_action'] = expected_action
    if not optimizing and not predicting and not re.search(r'계산|분석|시뮬|simulate|경화', text, re.I):
        issues.append('수행할 작업을 계산/분석/예측/최적화로 구체적으로 지정하십시오.')
    if spec['action'] != expected_action:
        issues.append('action: 요청한 작업과 AI가 선택한 도구가 다릅니다.')
    goals = []
    # [NEW v14] A search-variable mention of 유지시간 is not a time objective.
    time_goal=r'(?:공정시간|총시간|사이클시간|(?<!유지)시간)'
    if re.search(time_goal+r'.*(?:최소|줄|단축)|(?:최소|줄|단축).*'+time_goal, text):
        goals.append('minimize_time')
    if re.search(r'(?:최고온도|최대온도)(?:를|을|는)?(?:최소화|낮춰|낮추|줄여)', text):
        goals.append('minimize_peak')
    if re.search(r'(?:온도편차|온도차)(?:를|을|는)?(?:최소화|낮춰|낮추|줄여)', text):
        goals.append('minimize_spread')
    if optimizing:
        if len(goals) == 1:
            if spec['target'] != goals[0]:
                issues.append('target: 요청한 최적화 목표와 다릅니다.')
        # [NEW v17] Independent fallback goal check.
        if len(goals) != 1 and (not re.search(r'균형|절충|balanced', text, re.I) or spec['target'] != 'balanced'):
            issues.append('최적화 목표를 시간/최고온도/온도편차 중 하나 또는 균형으로 명시하십시오.')
    requested = []
    for term, variables in [('승온속도', ['ramp1', 'ramp2']), ('유지온도', ['T1', 'T2']),
                            ('유지시간', ['hold1', 'hold2'])]:
        if term in text:
            if '1차' + term in text and '2차' + term not in text:
                variables = variables[:1]
            # [NEW v17] Independent selection of the second stage.
            if '2차' + term in text and '1차' + term not in text:
                variables = variables[1:]
            requested.extend(variables)
    actual = spec['search_variables'] or default_variables
    if optimizing and requested and set(actual) != set(requested):
        issues.append('search_variables: 사용자가 지정한 변경 범위와 다릅니다.')
    evidence['expected_search_variables'] = requested or list(default_variables or [])
    return {'status': 'needs_review' if issues else 'passed', 'issues': issues, 'evidence': evidence,
            'request_hash': digest(request), 'spec_hash': digest(spec), 'policy_hash': digest(policy),
            'controller': 'deterministic_v12', 'model_confidence_used': False}


def freeze_contract(condition=None, limits=None, variables=None, options=None, target=None):
    contract = copy.deepcopy({'condition': normalize(condition), 'limits': limits,
                              'variables': variables, 'options': options, 'target': target,
                              'model_hash': MODEL_HASH})
    return {'payload': contract, 'hash': digest(contract)}


def review_results(state=None, contract=None):
    issues = []
    # [NEW v17] Invalid outer contracts must return a Guard verdict, including None.
    contract_hash = contract.get('hash') if isinstance(contract, dict) else None
    try:
        if not isinstance(state, dict) or not isinstance(contract, dict):
            raise ValueError('결과 상태와 실행 계약은 객체여야 합니다. None 결과를 차단합니다.')
        locked = contract['payload']
        if digest(locked) != contract['hash']:
            raise ValueError('실행 계약이 변경되었습니다.')
        if state['condition'] != locked['condition'] or state['limits'] != locked['limits']:
            raise ValueError('기준 조건/제약이 실행 중 변경되었습니다.')
        physics = state['physical']

        def check_result(result=None):
            if result['model_hash'] != locked['model_hash']:
                raise ValueError('물리 모델 해시가 다릅니다.')
            if any(result['options'].get(k) != v for k, v in locked['options'].items()):
                raise ValueError('계산 옵션이 실행 계약과 다릅니다.')
            t, T, alpha = (np.asarray(result[k], dtype=float) for k in ('t', 'T', 'alpha'))
            if t.ndim != 1 or len(t) < 2 or T.shape != alpha.shape or T.ndim != 2 or T.shape[0] != len(t):
                raise ValueError('물리 이력 배열 크기가 올바르지 않습니다.')
            if not all(np.isfinite(a).all() for a in (t, T, alpha)) or not (np.diff(t) > 0).all() or (alpha < 0).any() or (alpha > 1).any():
                raise ValueError('물리 이력 범위/유한성/시간 순서가 올바르지 않습니다.')
            summary = result['summary']
            if not all(math.isfinite(float(summary[k])) for k in TARGETS):
                raise ValueError('물리 요약값이 비유한 수치입니다.')
            if not math.isclose(t[-1], summary['cycle_time'], abs_tol=1e-6) or not math.isclose(alpha[-1].min(), summary['final_DoC'], abs_tol=1e-6):
                raise ValueError('물리 이력과 요약의 시간/경화도가 다릅니다.')
            if T.max() > summary['Tmax'] + 1e-6:
                raise ValueError('온도 이력보다 낮은 최고온도가 보고되었습니다.')

        check_result(physics)
        if physics['condition'] != locked['condition']:
            raise ValueError('기준 물리 결과의 공정값이 다릅니다.')
        opt = state.get('optimization')
        if opt is not None:
            if opt['limits'] != locked['limits'] or opt['target'] != locked['target'] or set(opt['search_variables']) != set(locked['variables']):
                raise ValueError('최적화 목표/제약/탐색변수가 변경되었습니다.')
            for rec in opt['recommendations']:
                result = rec['result']
                check_result(result)
                if rec['condition'] != result['condition'] or rec['actual'] != result['summary']:
                    raise ValueError('추천값과 물리 검증 결과가 일치하지 않습니다.')
                normalize(rec['condition'], True)
                if any(rec['condition'][k] != locked['condition'][k] for k in FEATURES if k not in locked['variables']):
                    raise ValueError('고정해야 할 공정변수가 변경되었습니다.')
                if not judge(result['summary'], locked['limits'])['feasible']:
                    raise ValueError('통과라고 표시된 추천이 실제 제약을 위반합니다.')
                if not rec['decision']['feasible']:
                    raise ValueError('탈락 후보가 추천 목록에 포함됐습니다.')
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        issues.append(str(error))
    # [NEW v14] Full display-array and recommendation integrity, independent of LLM output.
    if not issues:
        try:
            from integrity_v14 import verify_state
            verify_state(state,contract)
        except (ValueError,KeyError,TypeError,IndexError,OverflowError) as error:issues.append(str(error))
    return {'status': 'blocked' if issues else 'passed', 'issues': issues,
            'contract_hash': contract_hash,  # [NEW v17] Safe even for absent contracts. 'controller': 'deterministic_v12',
            'external_physics_certification': False}
