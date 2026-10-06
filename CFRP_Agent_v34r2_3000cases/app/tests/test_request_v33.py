# [NEW v33] Integration tests for semantic evidence, retries, and actual locked physics.
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import AI
from AI_guard import review_request
from core import DEFAULT,FEATURES
from surrogate_store_v24 import get_trained_bundle_v24
from request_semantics_v33 import interpretation_context

class RequestV33Tests(unittest.TestCase):
    def test_peak_and_hold_scope(self):
        for request,variables,target in [('현재 공정에서 2차 승온속도만 조절해서 최고 내부온도를 최소화해줘. 나머지 조건은 유지해줘.',['ramp2'],'minimize_peak'),('현재 공정에서 1차와 2차 유지시간만 조절해서 최대 온도편차를 최소화해줘.',['hold1','hold2'],'minimize_spread')]:
            ev,spec=interpretation_context(request)
            self.assertFalse(ev['issues']);self.assertEqual(spec['search_variables'],variables);self.assertEqual(spec['target'],target)
            self.assertEqual(review_request(request,spec)['status'],'passed')
    def test_units_and_material_confirmation(self):
        request='AS4/8552 평판 두께 1cm, 1차 유지온도 383.15K, 유지시간 1시간, 2차 유지온도 453.15K, 유지시간 2시간으로 계산해줘. 승온속도는 현재 값을 사용해줘'
        ev,spec=interpretation_context(request)
        self.assertFalse(ev['issues']);self.assertEqual(spec['condition_patch'],{'thickness':10,'T1':110,'T2':180,'hold1':60,'hold2':120})
        with patch.object(AI,'simulate',side_effect=AssertionError('invalid request reached solver')):
            state=AI.run_ai(request=request.replace('AS4','S4'))
            self.assertEqual(state['status'],'needs_clarification')
    def test_inequality_and_wrong_scope(self):
        for request in ['최고온도 195도 이상에서 공정시간 최소화','온도편차 8도 이상에서 공정시간 최소화','최종경화도 95% 이하에서 공정시간 최소화']:
            self.assertTrue(interpretation_context(request)[0]['issues'])
        request='ramp2만 조절해서 최고온도 최소화'
        _,spec=interpretation_context(request);spec['search_variables']=['ramp1','ramp2']
        self.assertEqual(review_request(request,spec)['status'],'needs_review')
    def test_bounded_retry_without_silent_correction(self):
        request='2차 승온속도만 조절해서 최고 내부온도 최소화'
        _,correct=interpretation_context(request);wrong=copy.deepcopy(correct);wrong['limits_patch']={'Tmax':200}
        replies=[wrong,correct];calls=[]
        def transport(payload=None):
            calls.append(payload);return {'message':{'content':json.dumps(replies[len(calls)-1])}}
        parsed=AI.extract_request(request,transport=transport)
        self.assertEqual(len(calls),2);self.assertEqual(parsed,correct)
        self.assertIn('명시하지 않은 숫자',calls[1]['messages'][-1]['content'])
    def test_actual_physics_preserves_unselected_conditions(self):
        bundle=get_trained_bundle_v24();cfg=AI.load_config({'candidate_count':32,'top_k':2,'max_feedback_rounds':1})
        for request in ['2차 승온속도만 조절해서 최고 내부온도 최소화','1차와 2차 유지시간만 조절해서 최대 온도편차 최소화']:
            _,spec=interpretation_context(request)
            state=AI.run_ai(request=request,spec=spec,bundle=bundle,config=cfg)
            self.assertEqual(state['result_guard']['status'],'passed');self.assertGreater(state['optimization']['rechecked'],0)
            for item in state['optimization']['checked']:
                for key in FEATURES:
                    if key not in spec['search_variables']:self.assertEqual(item['condition'][key],DEFAULT[key])
    def test_request_specific_schema_preserves_numeric_gate(self):
        from request_semantics_v33 import constrained_schema
        request='ramp2만 조절해서 최고 내부온도 최소화'
        _,spec=interpretation_context(request)
        schema=json.loads((Path(__file__).resolve().parents[1]/'config/ai_request_schema.json').read_text(encoding='utf-8'))
        constrained=constrained_schema(schema,spec)
        self.assertEqual(constrained['properties']['action']['enum'],['optimize_cycle'])
        self.assertEqual(constrained['properties']['target']['enum'],['minimize_peak'])
        self.assertEqual(constrained['properties']['search_variables']['items']['enum'],['ramp2'])
        self.assertEqual(constrained['properties']['limits_patch']['properties'],{})
        self.assertEqual(len(schema['properties']['action']['enum']),3)
    def test_converted_request_actual_simulation(self):
        request='AS4/8552 평판 두께 1cm, 1차 유지온도 383.15K, 유지시간 1시간, 2차 유지온도 453.15K, 유지시간 2시간으로 계산해줘. 승온속도는 현재 값을 사용해줘'
        _,spec=interpretation_context(request)
        state=AI.run_ai(request=request,spec=spec)
        self.assertEqual(state['status'],'completed');self.assertEqual(state['result_guard']['status'],'passed')
        for key,value in spec['condition_patch'].items():self.assertEqual(state['condition'][key],value)
        for key in ('ramp1','ramp2'):self.assertEqual(state['condition'][key],DEFAULT[key])

if __name__=='__main__':unittest.main(verbosity=2)
