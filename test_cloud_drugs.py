import unittest
from unittest.mock import patch
import cloud_drugs as c

class CloudDrugTests(unittest.TestCase):
    def test_private_payloads_rejected_before_network(self):
        bad=[{'medications':['Lipitor'],'consent':True,'age':78},
             {'medications':['Lipitor'],'consent':False},
             {'medications':['Lipitor','姓名：測試'],'consent':True},
             {'medications':['A123456789'],'consent':True},
             {'medications':['patient John'],'consent':True},
             {'medications':['Lipitor\nJohn Smith'],'consent':True}]
        with patch.object(c,'get_json') as network:
            for p in bad:
                with self.subTest(p=p),self.assertRaises(ValueError):c.lookup(p)
            network.assert_not_called()
    def test_taiwan_names_and_codes_not_sent_to_rxnav(self):
        with patch.object(c,'get_json') as network:
            r=c.lookup({'medications':['立普妥','B022886100','Lipitor BID'],'consent':True})
            self.assertTrue(all(x['status']=='unsupported' for x in r['results']));network.assert_not_called()
    def test_candidates_require_properties_and_preserve_compounds(self):
        responses=[{'approximateGroup':{'candidate':[{'rxcui':'123','rank':'1'},{'rxcui':'123','rank':'1'}]}},
                   {'properties':{'rxcui':'123','name':'Example combination','tty':'SCD'}},
                   {'relatedGroup':{'conceptGroup':[{'tty':'IN','conceptProperties':[{'name':'ingredient A'},{'name':'ingredient B'}]}]}}]
        with patch.object(c,'get_json',side_effect=responses) as network,patch.object(c.time,'sleep'):
            r=c.lookup({'medications':['Example'],'consent':True})['results'][0]
            self.assertEqual(r['status'],'candidates');self.assertEqual(r['candidates'][0]['ingredients'],['ingredient A','ingredient B'])
            self.assertEqual(network.call_count,3)
    def test_ten_letter_generic_is_not_taiwan_code(self):
        with patch.object(c,'get_json',return_value={'approximateGroup':{}}) as network:
            c.lookup({'medications':['Metoprolol'],'consent':True});network.assert_called_once()
    def test_failure_does_not_leak_error_or_auto_match(self):
        with patch.object(c,'get_json',side_effect=OSError('secret raw body')):
            r=c.lookup({'medications':['Lipitor'],'consent':True})['results'][0]
            self.assertEqual(r['status'],'unavailable');self.assertEqual(r['candidates'],[]);self.assertNotIn('secret',r['message'])

if __name__=='__main__':unittest.main()
