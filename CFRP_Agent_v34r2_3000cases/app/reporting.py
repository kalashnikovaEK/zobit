# [NEW v01] Deterministic reports; approval state is attached to the exact run hash.
import hashlib
import json
from datetime import datetime,timezone
import numpy as np
from core import MATERIAL,MODEL_HASH,TARGETS

def plain(value=None):
    # [NEW v14] Separate large solver histories from narrative/report hashes.
    if isinstance(value,dict):
        from exports_v14 import trim_history
        value=trim_history(value)
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items() if k not in ('models','result','T','alpha','T_air','t','z')}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    return value

def run_hash(payload=None):
    return hashlib.sha256(json.dumps(plain(payload),sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def generate_report(run=None,approval=None):
    p=plain(run);rid=run_hash(p)
    approval=approval or {'status':'pending','scope':'simulation review only'}
    if approval.get('run_hash') not in (None,rid):raise ValueError('Approval belongs to a different run')
    lines=['# CFRP 공정 분석 보고서 v01','',f'- 생성: {datetime.now(timezone.utc).isoformat()}',f'- 실행 ID: {rid}',f'- 모델: {MATERIAL["version"]}',f'- 모델 해시: {MODEL_HASH}',f'- 검토 상태: {approval.get("status","pending")}','- 적용범위: 시뮬레이션 시연 검토. 실제 설비 운전 승인 아님.','- 외부 실험 검증: 미완료','', '## 계산 결과 및 도구 실행 기록','```json',json.dumps(p,ensure_ascii=False,indent=2),'```','','## 가정과 한계']
    lines += ['- '+x for x in MATERIAL['assumptions']]
    lines += ['','## 근거']+['- '+s['id']+' p.'+s['pages']+': '+s['url'] for s in MATERIAL['sources']]
    return '\n'.join(lines)
