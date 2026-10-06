# [NEW v33] Independent request evidence; never approves LLM-invented values.
import hashlib
import json
import math
import re
from pathlib import Path

SEARCH = ['ramp1', 'T1', 'hold1', 'ramp2', 'T2', 'hold2']
NUM = r'[+-]?(?:\d+(?:[.,]\d+)?)(?:e[+-]?\d+)?'
UNIT = r'(?:마이크로미터|밀리미터|센티미터|켈빈|minutes?|seconds?|hours?|퍼센트|미터|시간|도씨|°c|℃|mm|cm|μm|µm|um|min|sec|hr|분|초|도|c|k|m|%)'
LABEL = r'(?:[12]차(?:유지온도|온도|유지시간|승온속도|승온)|ramp[12]|hold[12]|t[12]|thickness|두께|tmax|t_limit|최고온도|최대온도|delta_tmax|온도편차|온도차|최종경화도|최소경화도|경화도|final_doc|유지시간)'
KEYS = {'두께':'thickness','thickness':'thickness','최고온도':'Tmax','최대온도':'Tmax','tmax':'Tmax','t_limit':'Tmax','온도편차':'delta_Tmax','온도차':'delta_Tmax','delta_tmax':'delta_Tmax','최종경화도':'final_DoC','최소경화도':'final_DoC','경화도':'final_DoC','final_doc':'final_DoC'}


def compact(request=None):
    text = re.sub(r'\s+', '', request or '').lower()
    for pattern, value in [
        (r'(?:첫번째|첫째|제1|1단계)', '1차'),
        (r'(?:두번째|둘째|제2|2단계)', '2차'),
        (r'(?:최고내부온도|내부최고온도|최대내부온도|내부최대온도|피크온도|maximumtemperature|peaktemperature)', '최고온도'),
        (r'(?:온도차이|temperaturedifference|temperaturespread)', '온도편차'),
        (r'(?:최대온도편차|최대온도차)', '온도편차'),
        (r'(?:전체공정소요시간|공정소요시간|cycletime|사이클타임)', '공정시간'),
        (r'(?:승온율|가열속도)', '승온속도'),
        (r'섭씨(?=[+\-\d])', ''),
        (r'한시간', '1시간'), (r'십밀리미터', '10밀리미터')]:
        text = re.sub(pattern, value, text)
    return text


def key_for(label=None, stage=None):
    if label in KEYS: return KEYS[label]
    if re.fullmatch(r'ramp[12]|hold[12]', label): return label
    if re.fullmatch(r't[12]', label): return label.upper()
    match = re.match(r'([12])차(.*)', label)
    if match: stage, label = match.groups()
    if label == '유지시간' and stage: return 'hold'+stage
    if label in ('유지온도','온도') and stage: return 'T'+stage
    if label in ('승온속도','승온') and stage: return 'ramp'+stage
    return None


def convert(value=None, unit=None, key=None):
    value = float(value.replace(',', '.'))
    if not math.isfinite(value): raise ValueError('유한한 수치가 필요합니다.')
    u = (unit or '').lower()
    if key == 'thickness':
        factors={'':1,'mm':1,'밀리미터':1,'cm':10,'센티미터':10,'m':1000,'미터':1000,'μm':.001,'µm':.001,'um':.001,'마이크로미터':.001}
        if u not in factors: raise ValueError('두께 단위는 mm/cm/m/μm입니다.')
        return value*factors[u]
    if key.startswith('hold'):
        factors={'':1,'min':1,'minute':1,'minutes':1,'분':1,'시간':60,'hour':60,'hours':60,'hr':60,'초':1/60,'sec':1/60,'second':1/60,'seconds':1/60}
        if u not in factors: raise ValueError('유지시간 단위는 분/시간/초입니다.')
        return value*factors[u]
    if key=='final_DoC':
        if u not in ('','%','퍼센트'): raise ValueError('경화도 단위는 비율 또는 %입니다.')
        return value/100 if u else value
    if u not in ('','°c','℃','도','도씨','c','k','켈빈'): raise ValueError('온도/승온속도 단위를 확인하십시오.')
    return value-273.15 if key in ('T1','T2','Tmax') and u in ('k','켈빈') else value


def evidence(request=None, default_variables=None):
    text = compact(request)
    errors, found, spans, directions = [], {}, [], {}
    # [NEW v34] Reject reversed/negated inequalities instead of choosing the first word.
    if re.search(r'(?:이하|이상|상한|하한)(?:는|은|가|이)?(?:아니|말고)|(?:이하|이상).*?(?:않|아니)', text):
        errors.append('부정된 제약 방향은 자동 적용하지 않습니다. 최종 상한/하한을 직접 명시하십시오.')
    if not text or len(request or '')>4000: errors.append('요청은 1~4000자여야 합니다.')
    if re.search(r'(?<!a)s4[/_]8552',text): errors.append('S4/8552를 AS4/8552로 뜻하셨는지 재료명을 확인하십시오.')
    if re.search(r'알루미늄|alumin|강철|steel|티타늄|titanium|구리|copper|peek|유리섬유|glassfiber|원통|곡면|구형|구체|cylinder|sphere|압력|bar|psi|°f|℉|화씨',text): errors.append('지원하지 않는 재료/형상/옵션입니다. 현재 AS4/8552 평판 모델만 지원합니다.')
    if re.search(r'검증.*(?:건너뛰|생략|무시)|(?:모든)?검증통과로표시|파일삭제|명령실행|설비',text): errors.append('검증 생략·허위 통과·설비 명령은 지원하지 않습니다.')
    if re.search(r'적당|알아서|대충|제약완화',text): errors.append('목표와 조건을 명시하십시오. 제약은 자동 완화하지 않습니다.')
    rate_bad = re.search(r'(?:°c|℃|도|c|k)/(?:hour|hr|h(?!old)|sec|s(?!pread)|시간|초)|(?:시간|초)당',text)
    if rate_bad: errors.append('승온속도는 °C/min으로 환산해 지정하십시오. 다른 분모는 자동 적용하지 않습니다.')
    # Keep replacement/relative values conservative; do not infer arithmetic operands from unrelated numbers.
    if re.search(r'대신|더높|더낮|같은시간|같은온도|도로바꿔|분으로바꿔',text): errors.append('변경 후 각 단계의 최종 값을 직접 지정하십시오. 상대값/참조값은 자동 적용하지 않습니다.')

    def store(key=None, value=None, span=None, direction=None):
        if key in found and not math.isclose(found[key],value,abs_tol=1e-6): errors.append(key+': 서로 다른 값이 지정됐습니다.')
        found[key]=value
        if span:spans.append(span)
        if direction:directions[key]=direction

    # Explicit paired stages, each with two values; only the documented '각각' form.
    paired=rf'1차/2차(?:유지)?(온도|시간)각각({NUM})/({NUM})({UNIT})?'
    for m in re.finditer(paired,text,re.I):
        family='T' if m[1]=='온도' else 'hold'
        try:
            for stage in ('1','2'):store(family+stage,convert(m[int(stage)+1],m[4],family+stage),m.span())
        except ValueError as e:errors.append(str(e))
    if re.search(r'1차/2차',text):
        for m in re.finditer(rf'유지시간각각({NUM})/({NUM})({UNIT})?',text,re.I):
            try:
                for stage in ('1','2'):store('hold'+stage,convert(m[int(stage)],m[3],'hold'+stage),m.span())
            except ValueError as e:errors.append(str(e))
    # A label fixes the variable; bare 유지시간 inherits only the nearest explicit stage.
    matches=list(re.finditer(LABEL,text,re.I))
    for i,m in enumerate(matches):
        if any(a<=m.start()<b for a,b in spans):continue
        stage_matches=list(re.finditer(r'([12])차',text[:m.start()]))
        stage=stage_matches[-1][1] if stage_matches else None
        key=key_for(m[0],stage)
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        tail=text[m.end():end]
        # Only grammatical connectors may separate a label and its number.
        q=re.match(rf'(?:은|는|을|를|이|가|:|=|상한|제한|최소|최대|분당)*({NUM})({UNIT})?',tail,re.I)
        if not q:continue
        if key is None:errors.append('유지시간의 단계를 1차/2차로 지정하십시오.');continue
        span=(m.start(),m.end()+q.end())
        unit=q[2] or ''
        suffix=tail[q.end():]
        try:
            if key.startswith('hold') and re.match(rf'({NUM})(분|min)',suffix) and unit in ('시간','hour','hours','hr'):
                extra=re.match(rf'({NUM})(분|min)',suffix);value=convert(q[1],unit,key)+float(extra[1]);span=(span[0],span[1]+extra.end())
            elif key.startswith('hold') and re.match(r':\d{2}',suffix):
                errors.append('시간 콜론 표기는 모호합니다. 90분처럼 단위를 명시하십시오.');continue
            else:value=convert(q[1],unit,key)
            if key.startswith('ramp'):
                denom=re.match(r'/(\w+)',suffix)
                if denom and not re.match(r'(?:minutes?|min|분)(?:으로|로|계산|$)',denom[1]): errors.append('승온속도 분모는 min/분이어야 합니다.')
            direction=None
            if key in ('Tmax','delta_Tmax','final_DoC'):
                if re.search(r'미만|초과|[<>]',suffix): errors.append(key+': 엄격한 미만/초과 제약은 현재 지원하지 않습니다. 이하/이상을 사용하십시오.')
                lower=bool(re.match(r'(?:이상|보다높|보다크|넘어|넘게|atleast|above|over|이하가아니라)',suffix))
                upper=bool(re.match(r'(?:이하|보다낮|보다작|atmost|below|넘지|를넘지|를초과하지)',suffix))
                direction='lower' if lower else 'upper' if upper else 'lower' if key=='final_DoC' else 'upper'
                if (key=='final_DoC' and direction!='lower') or (key!='final_DoC' and direction!='upper'):errors.append(key+': 요청한 제약 방향은 지원하지 않습니다. 온도는 상한, 경화도는 하한만 지원합니다.')
            store(key,value,span,direction)
        except ValueError as e:errors.append(key+': '+str(e))
    # Reversed thickness order (10mm 두께) remains unambiguous.
    if 'thickness' not in found:
        for m in re.finditer(rf'({NUM})(mm|cm|μm|µm|um|m)(?:두께)',text):
            store('thickness',convert(m[1],m[2],'thickness'),m.span())
    # Explicit '1차에서 60분 유지' form.
    for m in re.finditer(rf'([12])차에서({NUM})({UNIT})유지',text,re.I):
        try:store('hold'+m[1],convert(m[2],m[3],'hold'+m[1]),m.span())
        except ValueError as e:errors.append(str(e))
    cleaned=list(text)
    for a,b in spans:cleaned[a:b]=' '*(b-a)
    rest=''.join(cleaned)
    rest=re.sub(r'as4[/_]8552|as4|8552|[12]차|ramp[12]|hold[12]|t[12]', '',rest)
    if re.search(r'\d',rest):errors.append('단계/변수에 연결되지 않은 숫자가 있습니다. 각 변수의 최종 값을 명시하십시오.')
    if re.search(r'두께.*(?:또는|혹은)|온도.*(?:또는|혹은)',text):errors.append('대안 값 중 적용할 하나를 지정하십시오.')
    # Remove negated objectives and quantity clauses before deciding the action/goal.
    goal_text=''.join(cleaned)
    goal_text=re.sub(r'(?:최고온도|온도편차|공정시간)(?:를|을)?(?:줄이지|최소화하지|낮추지)(?:말고|마|않고)', '',goal_text)
    goal_text=re.sub(r'최소경화도','경화도',goal_text)
    goal_text=re.sub(r'(?:[12]차)?유지시간','유지길이',goal_text)
    goals=[]
    terms=[('minimize_time',r'공정시간|총시간|사이클시간|(?<!유지)시간'),('minimize_peak',r'최고온도|최대온도|(?<![a-z_])tmax'),('minimize_spread',r'온도편차|온도차|delta_tmax')]
    optimizing=bool(re.search(r'최적|찾|최소화|최소$|줄여|줄이는|단축|낮춰|낮추|가장낮|가장작|가장짧|minimize',goal_text))
    if re.search(r'최소화|최소',goal_text) and re.search(r'공정시간|최고온도|온도편차|tmax|delta_tmax',goal_text):optimizing=True
    action='optimize_cycle' if optimizing else 'predict_process' if '예측' in goal_text else 'simulate_process'
    if not optimizing and not re.search(r'계산|분석|시뮬|simulate|경화|예측|보여',goal_text):errors.append('계산/예측/최적화 작업을 명시하십시오.')
    if optimizing:
        for target,term in terms:
            if re.search(term,goal_text):goals.append(target)
        if re.search(r'균형|절충|balanced',goal_text):target='balanced'
        elif re.search(r'우선',goal_text):
            priority=re.search(r'(공정시간|최고온도|온도편차)(?:를|을)?우선',goal_text)
            target={'공정시간':'minimize_time','최고온도':'minimize_peak','온도편차':'minimize_spread'}.get(priority[1]) if priority else None
            if target is None:errors.append('우선할 목표를 명시하십시오.')
        elif len(goals)==1:target=goals[0]
        else:target=None;errors.append('단일 최적화 목표 또는 균형/절충을 명시하십시오.')
    else:target=None
    # Parse clauses independently so fixed mentions do not broaden the change set.
    selected, fixed=[],[]
    # [NEW v34] Separate comma-linked change/fixed clauses; retain numeric decimals and joint stages.
    scope_text = scope_clauses_v34(text)
    for clause in re.split(r'[.;。\n]|나머지',scope_text):
        is_fixed=bool(re.search(r'고정|변경하지|바꾸지|제외|현재값|그대로|유지해',clause))
        bucket=fixed if is_fixed else selected
        for m in re.finditer(r'ramp[12]|hold[12]|t[12]',clause):bucket.append(m[0].upper() if m[0].startswith('t') else m[0])
        for term,prefix in [('승온속도','ramp'),('유지온도','T'),('유지시간','hold')]:
            for m in re.finditer(term,clause):
                before=clause[max(0,m.start()-20):m.start()]
                stages=['1','2']
                joint=re.search(r'1차(?:와|및|,|/|하고)2차$',before)
                single=re.search(r'([12])차$',before)
                if single and not joint:stages=[single[1]]
                bucket.extend(prefix+s for s in stages)
    selected=list(dict.fromkeys(selected));fixed=list(dict.fromkeys(fixed))
    if set(selected)&set(fixed):errors.append('같은 변수를 변경과 고정으로 함께 지정했습니다.')
    variables=selected or [v for v in (default_variables or SEARCH) if v not in fixed]
    if optimizing and not variables:errors.append('최적화할 변수가 없습니다.')
    return {'quantities_canonical':found,'expected_action':action,'expected_target':target,'expected_search_variables':variables,'fixed_variables':fixed,'constraint_directions':directions,'issues':list(dict.fromkeys(errors))}


def review(request=None, spec=None, default_variables=None):
    ev=evidence(request,default_variables)
    issues=list(ev['issues'])
    values=ev['quantities_canonical'];patches={**spec['condition_patch'],**spec['limits_patch']}
    for key in set(values)|set(patches):
        if key not in values or key not in patches or not math.isclose(values[key],patches[key],abs_tol=1e-6):issues.append(key+': 요청의 값/단위와 AI 적용값이 일치하지 않습니다. 명시하지 않은 숫자를 추가할 수 없습니다.')
    if spec['material']!='AS4_8552':issues.append('지원하지 않는 재료입니다. AS4/8552 확인이 필요합니다.')
    if spec['action']!=ev['expected_action']:issues.append('action: 요청 작업과 AI 도구가 다릅니다.')
    if ev['expected_action']=='optimize_cycle':
        if ev['expected_target'] is not None and spec['target']!=ev['expected_target']:issues.append('target: 요청 목표와 AI 목표가 다릅니다.')
        actual=spec['search_variables'] or default_variables or SEARCH
        if set(actual)!=set(ev['expected_search_variables']):issues.append('search_variables: 변경 범위와 다릅니다. 허용 변수: '+','.join(ev['expected_search_variables']))
    def digest(value=None):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return {'status':'needs_review' if issues else 'passed','issues':list(dict.fromkeys(issues)),'evidence':ev,'request_hash':digest(request),'spec_hash':digest(spec),'policy_hash':digest({'version':'v33','search':SEARCH,'module_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}),'controller':'deterministic_v33','model_confidence_used':False}


def grounding(request=None, validated=None):
    ev=evidence(request)
    if any('지원하지 않는 재료' in issue for issue in ev['issues']) and not validated['needs_clarification']:raise ValueError('지원하지 않는 재료/형상/옵션입니다. 확인이 필요합니다.')
    # [NEW v33] Ambiguous inputs are rejected by the request gate with a clarification.
    if ev['issues']:return
    values=ev['quantities_canonical']
    for field in ('condition_patch','limits_patch'):
        for key,value in validated[field].items():
            if key not in values:raise ValueError(field+'.'+key+': 사용자가 명시하지 않은 숫자 또는 단계가 모호합니다.')
            if not math.isclose(value,values[key],abs_tol=1e-6):raise ValueError(field+'.'+key+': 요청의 단위 변환값과 다릅니다.')


def interpretation_context(request=None, default_variables=None):
    ev=evidence(request,default_variables)
    if ev['issues']:
        return ev,None
    template={'action':ev['expected_action'],'target':ev['expected_target'] or 'balanced','material':'AS4_8552','temperature_unit':'C','condition_patch':{k:v for k,v in ev['quantities_canonical'].items() if k not in ('Tmax','delta_Tmax','final_DoC')},'limits_patch':{k:v for k,v in ev['quantities_canonical'].items() if k in ('Tmax','delta_Tmax','final_DoC')},'search_variables':ev['expected_search_variables'] if ev['expected_action']=='optimize_cycle' else [],'needs_clarification':False,'clarification_question':None}
    return ev,template


def constrained_schema(schema=None, template=None):
    # [NEW v33] Constrain only independently proven fields, then still verify output.
    result=json.loads(json.dumps(schema))
    properties=result['properties']
    for key in ('action','target','material','temperature_unit'):
        properties[key]['enum']=[template[key]]
    for key in ('condition_patch','limits_patch'):
        allowed=template[key]
        properties[key]['properties']={name:{'type':'number'} for name in allowed}
        properties[key]['required']=list(allowed)
    variables=template['search_variables']
    properties['search_variables'].update(minItems=len(variables),maxItems=len(variables))
    if variables:properties['search_variables']['items']['enum']=variables
    return result


# [NEW v34] No global replacements of numeric clauses or joint-stage lists.
def scope_clauses_v34(text=None):
    scope = re.sub(r'1차,(?=2차)', '1차와', text or '')
    return re.sub(r'(?<!\d),|,(?!\d)', '.', scope)
