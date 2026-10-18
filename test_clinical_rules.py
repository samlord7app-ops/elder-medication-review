import unittest,math
from unittest.mock import patch
import clinical_rules as c
from local_api import evaluate
ALL={'beers','stopp-start','pim-taiwan'}
def med(name,**kw):return {**c.validate_med(name,lambda s:s),'ingredients':{name},**kw}
def lab(name,value,unit):return {'name':name,'value':value,'unit':unit}
def checks(name,labs=(),diagnoses=(),active=None,**kw):
    return {r['id']:r for r in c.assess(med(name,**kw),list(labs),list(diagnoses),active or {name},ALL)}
class ClinicalTests(unittest.TestCase):
    def test_each_executable_branch_can_trigger(self):
        for rule in c.RULES:
            name=sorted(c.members(rule['target']))[0];info={};labs=[];diagnoses=[];active={name}
            for spec in rule['conditions']:
                op,*args=spec
                if op=='lab':
                    measure,cmp,threshold=args;value=threshold-0.01 if cmp in ['<','<='] else threshold+0.01
                    unit={'CrCl':'mL/min','eGFR':'mL/min/1.73m2','K':'mmol/L','Na':'mmol/L','HR':'bpm','correctedCa':'mmol/L'}[measure];labs.append(lab(measure,value,unit))
                elif op in ['dose','duration']:info['dailyDoseMg' if op=='dose' else 'durationDays']=args[1]+1
                elif op=='route':info['route']=args[0]
                elif op=='indication':info['indication']=args[0]
                elif op=='formulation_known':info['formulation']='immediate_release'
                elif op=='diagnosis':diagnoses.append(args[0])
                elif op=='co':active.add(sorted(c.members(args[0]))[0])
                elif op=='count':active.update(sorted(c.members(args[0]))[:args[2]])
            with self.subTest(rule=rule['id']):self.assertEqual(checks(name,labs,diagnoses,active,**info)[rule['id']]['status'],'potential_risk')
    def test_renal_thresholds_all_single_drug_branches(self):
        rules=[r for r in c.RULES if r['id'].startswith('BEERS-T6-') and len(r['conditions'])==1 and r['conditions'][0][0]=='lab' and '|' not in r['target'] and not r['target'].startswith('@')]
        self.assertGreaterEqual(len(rules),20)
        for r in rules:
            _,measure,op,value=r['conditions'][0];unit='mL/min' if measure=='CrCl' else 'mL/min/1.73m2'
            for observed in [value-0.01,value,value+0.01]:
                with self.subTest(rule=r['id'],value=observed):
                    actual=checks(r['target'],[lab(measure,observed,unit)])[r['id']]['status']
                    self.assertEqual(actual,'potential_risk' if c.COMPARE[op](observed,value) else 'not_matched')
    def test_crcl_not_egfr(self):
        self.assertEqual(checks('gabapentin',[lab('eGFR',20,'mL/min/1.73m2')])['BEERS-T6-GABAPENTIN']['status'],'insufficient_data')
        self.assertEqual(checks('baclofen',[lab('CrCl',20,'mL/min')])['BEERS-T6-BACLOFEN']['status'],'insufficient_data')
    def test_wrong_units_and_conflicts(self):
        for values in [[lab('CrCl',20,'mg/dL')],[lab('CrCl',20,'mL/min'),lab('CrCl',90,'mL/min')],[lab('CrCl',float('nan'),'mL/min')]]:
            self.assertEqual(checks('nitrofurantoin',values)['BEERS-T6-NITROFURANTOIN']['status'],'insufficient_data')
    def test_tramadol_requires_release_form(self):
        self.assertEqual(checks('tramadol',[lab('CrCl',20,'mL/min')])['BEERS-T6-TRAMADOL']['status'],'insufficient_data')
        self.assertEqual(checks('tramadol',[lab('CrCl',20,'mL/min')],formulation='extended_release')['BEERS-T6-TRAMADOL']['status'],'potential_risk')
    def test_dose_boundary_and_route(self):
        for dose,expected in [(6,'not_matched'),(6.01,'potential_risk'),(None,'insufficient_data')]:
            self.assertEqual(checks('doxepin',dailyDoseMg=dose,route='oral')['BEERS-T2-DOXEPIN']['status'],expected)
        self.assertEqual(checks('doxepin',dailyDoseMg=10,route='topical')['BEERS-T2-DOXEPIN']['status'],'not_matched')
        self.assertEqual(checks('indomethacin',route='ophthalmic')['BEERS-T2-INDOMETHACIN']['status'],'not_matched')
    def test_duration_and_exception(self):
        self.assertEqual(checks('omeprazole',durationDays=56)['BEERS-T2-PPI']['status'],'not_matched')
        self.assertEqual(checks('omeprazole',durationDays=57)['BEERS-T2-PPI']['status'],'potential_risk')
        self.assertEqual(checks('omeprazole',durationDays=90,indication='barrett')['BEERS-T2-PPI']['status'],'exception_requires_review')
        self.assertEqual(checks('diazepam',indication='epilepsy')['BEERS-T2-BZD']['status'],'exception_requires_review')
    def test_diagnoses_absent_unknown_conflicting(self):
        id='BEERS-T3-HF-TZD'
        for ds,expected in [([], 'insufficient_data'),(['心衰竭'],'potential_risk'),(['無：心衰竭'],'not_matched'),(['心衰竭','無：心衰竭'],'insufficient_data')]:
            self.assertEqual(checks('pioglitazone',diagnoses=ds)[id]['status'],expected)
    def test_drug_combinations_and_deduplication(self):
        active={'morphine','diazepam','gabapentin'}
        r=checks('morphine',active=active);self.assertEqual(r['BEERS-T5-OPIOID-BZD']['status'],'potential_risk');self.assertEqual(r['BEERS-T5-CNS3']['status'],'potential_risk')
        self.assertEqual(checks('diazepam',active={'diazepam'})['BEERS-T5-CNS3']['status'],'not_matched')
        self.assertEqual(checks('warfarin',active={'warfarin','trimethoprim'})['BEERS-T5-WARFARIN-TMP-SMX']['status'],'not_matched')
    def test_electrolyte_boundary(self):
        self.assertEqual(checks('losartan',[lab('K',5.5,'mmol/L')])['STOPP-B12-ARB']['status'],'not_matched')
        self.assertEqual(checks('losartan',[lab('K',5.51,'mmol/L')])['STOPP-B12-ARB']['status'],'potential_risk')
        self.assertEqual(checks('hydrochlorothiazide',[lab('Na',129,'mmol/L')])['STOPP-B9-Na']['status'],'potential_risk')
    def test_source_version_unverified(self):
        r=c.assess(med('diazepam'),[],[],{'diazepam'},set())
        self.assertTrue(all(x['status']=='source_unverified' for x in r))
    def test_medication_schema_and_privacy_allowlist(self):
        for obj in [{'name':'digoxin','patientName':'x'},{'name':'digoxin','dailyDoseMg':True},{'name':'digoxin','dailyDoseMg':float('inf')},{'name':'digoxin','route':'cloud'}]:
            with self.assertRaises(ValueError):c.validate_med(obj,lambda s:s)
    def test_api_uses_labs_and_diagnoses(self):
        p={'age':78,'medications':[{'name':'digoxin','dailyDoseMg':0.25},'spironolactone','losartan'],'labs':[lab('CrCl',29,'mL/min'),lab('K',6,'mmol/L')],'diagnoses':['心衰竭']}
        with patch.object(c,'approved_sources',return_value=ALL):r=evaluate(p)
        self.assertEqual(r['results'][0]['status'],'potentially_inappropriate')
        self.assertTrue(any(x['id']=='BEERS-T6-SPIRONOLACTONE' and x['status']=='potential_risk' for x in r['results'][1]['clinicalChecks']))
        self.assertTrue(any(x['id']=='STOPP-B12-ARB' and x['status']=='potential_risk' for x in r['results'][2]['clinicalChecks']))
        self.assertFalse(r['fullAutomation']);self.assertFalse(r['clinicalUseReady'])
    def test_registry_integrity(self):
        ids=[r['id'] for r in c.RULES];self.assertEqual(len(ids),len(set(ids)))
        for r in c.RULES:self.assertTrue(c.members(r['target'])<=c.DRUGS)
        self.assertFalse(c.coverage()['fullAutomation'])
    def test_combination_never_drops_unknown_ingredient(self):
        known,unknown=c.components(['DIAZEPAM 5 MG + UNKNOWN_SUBSTANCE 10 MG'])
        self.assertEqual(known,{'diazepam'});self.assertTrue(unknown)
        known,unknown=c.components(['ATORVASTATIN CALCIUM (2:1) TRIHYDRATE'])
        self.assertEqual(known,{'atorvastatin'});self.assertEqual(unknown,[])
if __name__=='__main__':unittest.main()
