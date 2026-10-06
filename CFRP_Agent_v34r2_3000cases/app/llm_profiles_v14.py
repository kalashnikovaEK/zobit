# [NEW v14] Explicit local-model profiles. No model downloads or automatic fallback.
import copy
import json
from core import ROOT


def profiles():
    data=json.loads((ROOT/'config/llm_profiles_v14.json').read_text(encoding='utf-8'))
    return copy.deepcopy(data['profiles'])


def profile_config(profile=None,config=None):
    from AI import load_config
    if profile in (None,'ollama'):
        return load_config(config)
    choices=profiles()
    if profile not in choices:
        raise ValueError('지원하지 않는 로컬 모델 프로필입니다.')
    base=load_config(config)
    base['model']=choices[profile]['model']
    return load_config(base)


def prepare_ollama_payload(payload=None):
    # Qwen3 accepts a top-level think flag; keep thinking separate from JSON output.
    if str(payload.get('model','')).lower().startswith('qwen3'):
        payload['think']=False
    return payload
