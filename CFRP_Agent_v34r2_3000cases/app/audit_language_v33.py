# [NEW v33] Reproduce both shipped corpora without changing their expected meanings.
import json,sys
from pathlib import Path
from AI import validate_spec,validate_request_grounding
from AI_guard import review_request

def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    root=Path(__file__).resolve().parent.parent
    rows=[]
    for name in ['CFRP_Language_Audit_v33.json','CFRP_Holdout_v33.json']:
        data=json.loads((root/'docs'/name).read_text(encoding='utf-8'))
        for case in data['cases']:
            try:
                spec=validate_spec(case['spec']);validate_request_grounding(case['request'],case['spec'],spec)
                verdict=review_request(case['request'],spec)
                actual='pass' if verdict['status']=='passed' else 'reject';issues=verdict['issues']
            except Exception as error:actual='reject';issues=[str(error)]
            rows.append({'corpus':name,'id':case['id'],'request':case['request'],'expected':case['expected'],'actual':actual,'matched':actual==case['expected'],'issues':issues})
    print(json.dumps({'total':len(rows),'matched':sum(r['matched'] for r in rows),'false_accepts':sum(not r['matched'] and r['expected']=='reject' for r in rows),'mismatches':[r for r in rows if not r['matched']]},ensure_ascii=False,indent=2))
    return 0 if all(r['matched'] for r in rows) else 1

if __name__=='__main__':raise SystemExit(main())
