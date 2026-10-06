# [NEW v34] Replay the exact v24 diagnostic inputs through v34 extraction + preview.
import json,sys,copy
from pathlib import Path
from collections import Counter
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from AI import run_ai
cases=json.loads((Path(__file__).resolve().parent/'language_cases_100_v34.json').read_text())
counts=Counter()
for c in cases:
 try:
  with patch('AI.simulate',side_effect=AssertionError('unconfirmed physics')):
   state=run_ai(preview_only=True,request=c['request'],transport=lambda payload,s=c['spec']:{'message':{'content':json.dumps(s)}},config={'json_retries':0})
  status=state['status'];error=state.get('answer','') if status!='confirmation_required' else ''
 except (ValueError,TypeError) as e:status='blocked';error=str(e)
 c['v34_status']=status;c['v34_error']=error
 c['v34_auto_execution']=False
 counts[('normal_' if c['expected_pass'] else 'invalid_')+status]+=1
out=Path(__file__).resolve().parents[1]/'artifacts/language_replay_100_v34.json'
out.write_text(json.dumps({'counts':dict(counts),'llm':'mocked transport, not actual Ollama','physics':'not executed; preview gate tested','cases':cases},ensure_ascii=False,indent=2))
print(json.dumps(counts,ensure_ascii=False))
assert len(cases)==100
assert counts['normal_confirmation_required']==80
assert counts['invalid_blocked']+counts['invalid_needs_clarification']==20
assert all(not c['v34_auto_execution'] for c in cases)
