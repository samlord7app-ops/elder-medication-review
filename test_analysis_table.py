import unittest
from analysis_table import rows

class AnalysisTableTests(unittest.TestCase):
    def result(self, checks):
        return {'input':'Gabapentin','ingredient':'gabapentin','status':'needs_clinical_context','reason':'待確認','clinicalChecks':checks}
    def check(self, **kw):
        return dict(id='BEERS-T6-GABAPENTIN',source='beers',title='腎功能相關風險',status='potential_risk',missing=[],note='',**kw)
    def test_original_clause_and_branch_are_distinguished(self):
        a=rows([self.result([self.check()])])[0]
        self.assertIn('Beers 2023 表 6',a['criterion'])
        self.assertIn('系統分支',a['criterion'])
        self.assertIn('勿自行停藥',a['recommendation'])
        c=self.check();c.update(id='STOPP-B9-K',source='stopp-start')
        self.assertIn('STOPP v3 B9',rows([self.result([c])])[0]['criterion'])
    def test_unknowns_do_not_claim_risk_confirmed(self):
        c=self.check();c.update(status='insufficient_data',missing=['CrCl'])
        a=rows([self.result([c])])[0]
        self.assertIn('CrCl',a['recommendation']);self.assertIn('不能判定',a['recommendation'])
        c['status']='source_unverified'
        self.assertIn('尚未形成有效臨床結論',rows([self.result([c])])[0]['recommendation'])
    def test_every_medication_has_a_row(self):
        a=rows([self.result([])])[0]
        self.assertEqual(a['drug'],'Gabapentin');self.assertEqual(a['ruleId'],'')
        self.assertIn('人工評估',a['recommendation'])

if __name__=='__main__':unittest.main()
