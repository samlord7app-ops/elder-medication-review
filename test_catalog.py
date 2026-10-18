import unittest, sqlite3,tempfile,json
from pathlib import Path
from unittest.mock import patch
import catalog
from local_api import evaluate

class CatalogTests(unittest.TestCase):
    def test_real_import(self):
        if not catalog.PATH.exists(): self.skipTest('Run import_public_data.py --from-bundle first')
        self.assertGreater(catalog.metadata()['productCount'],200000)
        for name in ['衛署藥輸字第022886號','B022886100','立普妥　膜衣錠10毫克','LIPITOR FILM-COATED TABLETS 10MG']:
            with self.subTest(name=name):
                r=catalog.lookup(name);self.assertTrue(r['matched']);self.assertEqual(r['ingredients'],['atorvastatin'])
                p=dict(age=78,medications=[name],labs=[],diagnoses=[])
                self.assertEqual(evaluate(p)['results'][0]['ingredient'],'atorvastatin')
    def test_ambiguous_and_combination(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.sqlite';db=sqlite3.connect(path)
            db.executescript('CREATE TABLE products(id INTEGER,source TEXT,code TEXT,zh TEXT,en TEXT,ingredients TEXT,status TEXT,form TEXT); CREATE TABLE aliases(name TEXT,display TEXT,product INTEGER);')
            for i,ing in enumerate([['A'],['B'],['A','B']],1):
                db.execute('INSERT INTO products VALUES(?,?,?,?,?,?,?,?)',(i,'test',str(i),'test','test',json.dumps(ing),'historical','tablet'))
                db.execute('INSERT INTO aliases VALUES(?,?,?)',('same' if i<3 else 'combo','test',i))
            db.commit();db.close()
            with patch.object(catalog,'PATH',path):
                self.assertTrue(catalog.lookup('same')['ambiguous'])
                self.assertEqual(catalog.lookup('combo')['ingredients'],['A','B'])
                self.assertFalse(catalog.lookup('nonexistent')['matched'])
    def test_no_guess_of_combination(self):
        self.assertNotEqual(catalog.canonical('DIAZEPAM + OTHER 5 MG'),'diazepam')
    def test_topical_not_oral_rule(self):
        identity={'matched':True,'ingredients':['diphenhydramine'],'products':[{'form':'乳膏劑'}]}
        with patch.object(catalog,'lookup',return_value=identity):
            r=evaluate(dict(age=78,medications=['test cream'],labs=[],diagnoses=[]))
            self.assertEqual(r['results'][0]['status'],'needs_clinical_context')

if __name__=='__main__':unittest.main()
