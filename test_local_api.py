import io, json, unittest
from unittest.mock import patch
from openpyxl import Workbook
from local_api import evaluate, excel_rows

class LocalTests(unittest.TestCase):
    def setUp(self):
        self.source_patch=patch('clinical_rules.approved_sources',return_value={'beers','stopp-start','pim-taiwan'});self.source_patch.start();self.addCleanup(self.source_patch.stop)
    def payload(self): return dict(age=78, medications=['Valium','Metformin','unknown'],labs=[dict(name='eGFR',value=45,unit='mL/min/1.73m2')],diagnoses=['高血壓'])
    def test_results(self):
        r=evaluate(self.payload())
        self.assertEqual([x['status'] for x in r['results']],['potentially_inappropriate','not_covered','unrecognized'])
        self.assertFalse(r['clinicalUseReady'])
        self.assertIn('CrCl 與 eGFR 不互相代用',r['limitations'][1])
    def test_brand_and_typo(self):
        p=self.payload();p['medications']=['Diazepame','Lipitor','Ｄｉａｚｅｐａｍ','zzzzzzzzzzzz']
        results=evaluate(p)['results']
        self.assertEqual(results[0]['status'],'unrecognized')
        self.assertIsNone(results[0]['ingredient'])
        self.assertIn('diazepam',results[0]['suggestions'])
        self.assertEqual(results[1]['ingredient'],'atorvastatin')
        self.assertEqual(results[1]['status'],'not_covered')
        self.assertIn('Pfizer',results[1]['identitySource'])
        self.assertEqual(results[2]['ingredient'],'diazepam')
        self.assertEqual(results[3]['suggestions'],[])
    def test_reject_identifiers_and_extra_fields(self):
        for field in ['name','patientId','rawText','fileName']:
            p=self.payload();p[field]='test'
            with self.assertRaises(ValueError): evaluate(p)
        for value in ['A123456789','姓名：測試','test@example.com','0912345678']:
            p=self.payload();p['medications']=[value]
            with self.assertRaises(ValueError): evaluate(p)
        p=self.payload();p['labs'][0]['patientId']='hidden'
        with self.assertRaises(ValueError): evaluate(p)
    def test_numeric_validation(self):
        for age in [64,121,True,None,'78']:
            p=self.payload();p['age']=age
            with self.assertRaises(ValueError): evaluate(p)
        p=self.payload();p['labs'][0]['value']=float('nan')
        with self.assertRaises(ValueError): evaluate(p)
    def test_excel_no_formula_execution(self):
        wb=Workbook();ws=wb.active;ws.title='Private sheet name'
        ws.append(['藥品','年齡','檢驗']);ws.append(['Valium',78,'=1+1']);stream=io.BytesIO();wb.save(stream)
        result=excel_rows(stream.getvalue())
        self.assertNotIn('Private sheet name',json.dumps(result))
        self.assertEqual(result['sheets'][0]['rows'][1],['Valium','78','[公式略過，請人工輸入]'])

if __name__=='__main__': unittest.main()
