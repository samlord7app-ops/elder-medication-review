import unittest
from unittest.mock import patch
import med_strength as s
import catalog, cloud_drugs
from local_api import evaluate

class StrengthTests(unittest.TestCase):
    def test_mass_units_and_spacing(self):
        for a,b in [('Drug 0.5 mg','Drug 500 mcg'),('Drug 1 g','Drug 1000毫克'),('Drug 10MG','Drug10mg')]:
            self.assertEqual(s.parse(a)['signature'],s.parse(b)['signature'])
    def test_concentration_is_not_tablet_mass(self):
        self.assertEqual(s.parse('Drug 50mg/5mL')['signature'],s.parse('Drug 10 mg/mL')['signature'])
        self.assertNotEqual(s.parse('Drug 10 mg')['signature'],s.parse('Drug 10 mg/mL')['signature'])
    def test_combination_preserves_component_order(self):
        self.assertEqual(s.parse('Combo 875/125mg')['signature'],s.parse('Combo 875mg / 125mg')['signature'])
        self.assertNotEqual(s.parse('Combo 875/125mg')['signature'],s.parse('Combo 125/875mg')['signature'])
    def test_form_and_invalid_input(self):
        request=s.parse('Drug ER 10mg capsule')
        self.assertFalse(s.compatible(request,['Drug 10mg tablet']))
        self.assertTrue(s.compatible(request,['Drug XR 10mg capsule']))
        self.assertFalse(s.compatible(s.parse('Drug cream 10mg'),['Drug gel 10mg']))
        self.assertFalse(s.compatible(s.parse('Drug ointment 10mg'),['Drug cream 10mg']))
        self.assertIsNone(s.parse('Drug -5mg'));self.assertIsNone(s.parse('Drug 0mg'))
    def test_real_catalog_strength_and_wrong_strength(self):
        if not catalog.PATH.exists():self.skipTest('Public index not built')
        for name in ['Lipitor 10mg','立普妥 10毫克','Diazepam 5 mg']:
            with self.subTest(name=name):
                result=catalog.lookup(name)
                self.assertTrue(result['matched']);self.assertEqual(result['strengthMatch']['status'],'matched')
        self.assertFalse(catalog.lookup('Lipitor 999mg')['matched'])
        self.assertFalse(catalog.lookup('Lipitor 10mg capsule')['matched'])
    def test_strength_not_daily_dose(self):
        if not catalog.PATH.exists():self.skipTest('Public index not built')
        result=evaluate({'age':78,'medications':['Lipitor 10mg'],'labs':[],'diagnoses':[]})['results'][0]
        self.assertEqual(result['ingredient'],'atorvastatin');self.assertIsNone(result['clinicalInput']['dailyDoseMg'])
        self.assertEqual(result['strengthMatch']['requested'],'10mg')
    def test_cloud_filters_wrong_strength_and_preserves_suggested_name(self):
        responses=[{'approximateGroup':{'candidate':[{'rxcui':'1'},{'rxcui':'2'}]}},
                   {'properties':{'rxcui':'1','name':'atorvastatin 20 MG Oral Tablet [Lipitor]','tty':'SBD'}},
                   {'properties':{'rxcui':'2','name':'atorvastatin 10 MG Oral Tablet [Lipitor]','tty':'SBD'}},
                   {'relatedGroup':{'conceptGroup':[{'tty':'IN','conceptProperties':[{'name':'atorvastatin'}]}]}}]
        with patch.object(cloud_drugs,'get_json',side_effect=responses),patch.object(cloud_drugs.time,'sleep'):
            result=cloud_drugs.lookup({'medications':['Lipitor 10mg'],'consent':True})['results'][0]
            self.assertEqual(len(result['candidates']),1)
            self.assertEqual(result['candidates'][0]['suggestedName'],'Lipitor 10mg tablet')

if __name__=='__main__':unittest.main()
