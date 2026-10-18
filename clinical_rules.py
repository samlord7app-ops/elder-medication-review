"""Deterministic clinical screening with explicit unknowns, exceptions and coverage.
Includes Beers 2023, STOPP/START v3, PIM-Taiwan 2018, Hepatic/Renal adjustments, and Dietary Supplements (保健食品) interactions.
"""
import hashlib, json, math, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = 'CLINICAL-SCREEN-2026-10-18.2'

GROUPS = {
    'benzodiazepines': 'alprazolam bromazepam brotizolam chlordiazepoxide clobazam clonazepam clorazepate diazepam estazolam fludiazepam flunitrazepam flurazepam lorazepam medazepam midazolam nitrazepam nordazepam oxazepam oxazolam prazepam temazepam triazolam',
    'zdrugs': 'eszopiclone zaleplon zolpidem zopiclone',
    'first_antihistamines': 'brompheniramine carbinoxamine chlorpheniramine clemastine cyproheptadine dexchlorpheniramine dimenhydrinate diphenhydramine doxylamine hydroxyzine meclizine promethazine triprolidine',
    'strong_antidepressants': 'amitriptyline amoxapine clomipramine desipramine imipramine nortriptyline paroxetine trimipramine',
    'antipsychotics': 'aripiprazole amisulpride chlorpromazine chlorprothixene clozapine flupentixol fluphenazine haloperidol levomepromazine loxapine lurasidone olanzapine paliperidone perphenazine pimozide quetiapine risperidone sulpiride thioridazine trifluoperazine ziprasidone zotepine',
    'nsaids': 'aceclofenac acemetacin alclofenac benzydamine celecoxib diclofenac diflunisal etodolac etoricoxib fenbufen fenoprofen flufenamic flurbiprofen ibuprofen indomethacin ketoprofen ketorolac meclofenamic mefenamic meloxicam nabumetone naproxen niflumic nimesulide oxaprozin piroxicam sulindac tenoxicam tiaprofenic tolmetin',
    'ace': 'benazepril captopril enalapril fosinopril imidapril lisinopril perindopril quinapril ramipril trandolapril',
    'arb': 'azilsartan candesartan eprosartan irbesartan losartan olmesartan telmisartan valsartan',
    'beta': 'acebutolol atenolol betaxolol bisoprolol carvedilol celiprolol labetalol metoprolol nadolol nebivolol pindolol propranolol sotalol timolol',
    'anticoagulants': 'warfarin acenocoumarol apixaban dabigatran edoxaban rivaroxaban',
    'antiplatelets': 'aspirin clopidogrel prasugrel ticagrelor ticlopidine cilostazol dipyridamole',
    'ppi': 'dexlansoprazole esomeprazole lansoprazole omeprazole pantoprazole rabeprazole',
    'opioids': 'buprenorphine codeine fentanyl hydrocodone hydromorphone meperidine methadone morphine oxycodone pethidine tapentadol tramadol',
    'gabapentinoids': 'gabapentin pregabalin',
    'muscle_relaxants': 'carisoprodol chlorzoxazone cyclobenzaprine metaxalone methocarbamol orphenadrine',
    'bladder_antimuscarinics': 'darifenacin fesoterodine flavoxate oxybutynin solifenacin tolterodine trospium',
    'ssri': 'citalopram escitalopram fluoxetine fluvoxamine paroxetine sertraline',
    'snri': 'desvenlafaxine duloxetine milnacipran venlafaxine',
    'loop': 'bumetanide furosemide torsemide',
    'thiazide': 'bendroflumethiazide chlorothiazide chlorthalidone hydrochlorothiazide indapamide metolazone',
    'statins': 'atorvastatin fluvastatin lovastatin pitavastatin pravastatin rosuvastatin simvastatin',
    'antiepileptics': 'carbamazepine gabapentin levetiracetam oxcarbazepine phenobarbital phenytoin pregabalin topiramate valproate',
    'nitrates': 'isosorbide nitroglycerin',
    'pde5': 'avanafil sildenafil tadalafil vardenafil',
    'sulfonylureas': 'chlorpropamide glibenclamide gliclazide glimepiride glipizide glyburide tolbutamide',
    'systemic_steroids': 'cortisone dexamethasone hydrocortisone methylprednisolone prednisolone prednisone triamcinolone',
    'fluoroquinolones': 'ciprofloxacin levofloxacin moxifloxacin ofloxacin norfloxacin gemifloxacin',
    'tetracyclines': 'tetracycline doxycycline minocycline',
    'k_sparing': 'spironolactone eplerenone amiloride triamterene',
}
GROUPS = {k: set(v.split()) for k, v in GROUPS.items()}
GROUPS['cns'] = set.union(*(GROUPS[k] for k in ['benzodiazepines', 'zdrugs', 'strong_antidepressants', 'antipsychotics', 'opioids', 'gabapentinoids', 'ssri', 'snri', 'antiepileptics', 'muscle_relaxants']))
GROUPS['anticholinergic'] = set.union(*(GROUPS[k] for k in ['first_antihistamines', 'strong_antidepressants', 'bladder_antimuscarinics'])) | {'benztropine', 'trihexyphenidyl', 'disopyramide', 'atropine', 'scopolamine', 'dicyclomine', 'hyoscyamine', 'propantheline'}
GROUPS['anticholinergic_nonbladder'] = GROUPS['anticholinergic'] - GROUPS['bladder_antimuscarinics']
GROUPS['antithrombotics'] = GROUPS['anticoagulants'] | GROUPS['antiplatelets']
GROUPS['antihypertensives'] = GROUPS['ace'] | GROUPS['arb'] | GROUPS['beta'] | GROUPS['loop'] | GROUPS['thiazide'] | {'amlodipine', 'nifedipine', 'felodipine', 'lercanidipine', 'diltiazem', 'verapamil', 'doxazosin', 'terazosin', 'prazosin', 'hydralazine', 'clonidine', 'methyldopa'}
GROUPS['antidiabetics'] = GROUPS['sulfonylureas'] | {'metformin', 'insulin', 'pioglitazone', 'rosiglitazone', 'sitagliptin', 'linagliptin', 'vildagliptin', 'saxagliptin', 'alogliptin', 'empagliflozin', 'dapagliflozin', 'canagliflozin', 'acarbose', 'repaglinide', 'nateglinide', 'liraglutide', 'semaglutide', 'dulaglutide'}

EXTRA = set('amiloride amiodarone baclofen cimetidine colchicine digoxin disopyramide dofetilide doxazosin doxepin dronedarone eplerenone famotidine guanfacine insulin lithium megestrol metformin methyldopa metoclopramide nitrofurantoin nizatidine prazosin probenecid spironolactone sulfamethoxazole terazosin testosterone triamterene trimethoprim verapamil diltiazem ciprofloxacin clarithromycin erythromycin donepezil galantamine rivastigmine cilostazol pioglitazone rosiglitazone teriparatide denosumab allopurinol febuxostat folic_acid methotrexate levothyroxine thyroxine paracetamol acetaminophen amlodipine nifedipine felodipine lercanidipine sitagliptin linagliptin empagliflozin dapagliflozin canagliflozin'.split())

# 保健食品 (Dietary Supplements) 標準鍵與中英文別名對照
SUPPLEMENTS = {
    'ginkgo_biloba': {
        'display': '銀杏葉萃取物 (Ginkgo biloba)',
        'aliases': {'銀杏', '銀杏葉', '銀杏葉萃取物', '銀杏果', 'ginkgo', 'ginkgo biloba', '循利寧', 'cerenin'}
    },
    'red_yeast_rice': {
        'display': '紅麴 (Red yeast rice / Monacolin K)',
        'aliases': {'紅麴', '紅麴膠囊', '紅麴菌', '壽美降脂', 'red yeast rice', 'monacolin k', 'monascus', 'cholestin'}
    },
    'fish_oil': {
        'display': '魚油 / Omega-3 (Fish oil)',
        'aliases': {'魚油', '深海魚油', 'omega-3', 'omega 3', 'omega3', 'fish oil', 'epa', 'dha', 'epa/dha'}
    },
    'st_johns_wort': {
        'display': '聖約翰草 / 貫葉連翹 (St. John\'s Wort)',
        'aliases': {'聖約翰草', '貫葉連翹', '金絲桃', "st. john's wort", 'st johns wort', 'st john wort', 'hypericum', 'hypericum perforatum'}
    },
    'ginseng': {
        'display': '人參 / 西洋參 (Ginseng)',
        'aliases': {'人參', '人蔘', '高麗參', '高麗蔘', '西洋參', '花旗參', '粉光參', '紅參', 'ginseng', 'panax ginseng', 'american ginseng'}
    },
    'calcium': {
        'display': '鈣片 / 鈣補充劑 (Calcium)',
        'aliases': {'鈣', '鈣片', '碳酸鈣', '檸檬酸鈣', '海藻鈣', '挺立', 'calcium supplement', 'calcium carbonate', 'calcium citrate'}
    },
    'iron': {
        'display': '鐵劑 / 鐵補充劑 (Iron)',
        'aliases': {'鐵', '鐵劑', '補鐵', '硫酸亞鐵', '富馬酸亞鐵', 'iron supplement', 'ferrous sulfate', 'ferrous fumarate', 'ferrous gluconate'}
    },
    'magnesium': {
        'display': '鎂補充劑 / 氧化鎂 (Magnesium)',
        'aliases': {'鎂', '鎂片', '氧化鎂', '檸檬酸鎂', '甘胺酸鎂', 'magnesium supplement', 'magnesium oxide', 'mgo', 'magnesium citrate'}
    },
    'vitamin_k': {
        'display': '維生素 K / 納豆激酶 (Vitamin K / Natto)',
        'aliases': {'維生素k', '維他命k', '維生素k2', '納豆', '納豆激酶', '納豆紅麴', 'vitamin k', 'vitamin k1', 'vitamin k2', 'natto', 'nattokinase', 'menaquinone', 'phytonadione'}
    },
    'coq10': {
        'display': '輔酶 Q10 (Coenzyme Q10)',
        'aliases': {'輔酶q10', 'q10', 'coq10', 'coenzyme q10', 'ubiquinone', 'ubiquinol'}
    },
    'garlic': {
        'display': '大蒜精 / 蒜頭萃取物 (Garlic extract)',
        'aliases': {'大蒜精', '大蒜萃取物', '蒜精', '黑蒜精', 'garlic', 'garlic extract', 'allicin'}
    },
    'turmeric': {
        'display': '薑黃素 (Turmeric / Curcumin)',
        'aliases': {'薑黃', '薑黃素', '秋薑黃', '紅薑黃', 'turmeric', 'curcumin'}
    },
    'glucosamine': {
        'display': '葡萄糖胺 (Glucosamine)',
        'aliases': {'葡萄糖胺', '維骨力', '固樂沙敏', 'glucosamine', 'glucosamine sulfate', 'glucosamine hcl'}
    },
    'potassium_supp': {
        'display': '鉀補充劑 / 低鈉鹽 (Potassium supplement)',
        'aliases': {'鉀補充劑', '鉀片', '低鈉鹽', '代鹽', 'potassium supplement', 'potassium gluconate', 'potassium chloride'}
    },
    'licorice': {
        'display': '甘草萃取物 (Licorice)',
        'aliases': {'甘草', '甘草錠', '甘草萃取', 'licorice', 'glycyrrhiza'}
    },
    'melatonin': {
        'display': '褪黑激素 (Melatonin)',
        'aliases': {'褪黑激素', 'melatonin'}
    },
    'vitamin_d': {
        'display': '維生素 D (Vitamin D)',
        'aliases': {'維生素d', '維他命d', '維生素d3', '維他命d3', 'vitamin d', 'vitamin d3', 'cholecalciferol'}
    },
    'vitamin_b': {
        'display': '維生素 B 群 (Vitamin B complex)',
        'aliases': {'維生素b', '維生素b群', '維他命b群', 'b群', '合利他命', 'vitamin b', 'b complex'}
    },
    'lutein': {
        'display': '葉黃素 (Lutein)',
        'aliases': {'葉黃素', '游離型葉黃素', 'lutein'}
    },
    'probiotics': {
        'display': '益生菌 (Probiotics)',
        'aliases': {'益生菌', '乳酸菌', 'probiotics'}
    }
}

GROUPS['bleeding_supplements'] = {'ginkgo_biloba', 'fish_oil', 'garlic', 'ginseng', 'turmeric', 'glucosamine'}
GROUPS['mineral_chelators'] = {'calcium', 'iron', 'magnesium'}

DRUGS = set.union(*GROUPS.values()) | EXTRA | set(SUPPLEMENTS.keys())
SYNONYMS = {
    'acetylsalicylic acid': 'aspirin',
    'acetaminophen': 'paracetamol',
    'pethidine': 'meperidine',
    'glibenclamide': 'glyburide',
    'meclozine': 'meclizine',
    'thyroxine': 'levothyroxine',
    '普拿疼': 'paracetamol',
    '阿斯匹靈': 'aspirin',
    '立普妥': 'atorvastatin',
    '冠脂妥': 'rosuvastatin',
    '脈優': 'amlodipine',
    '使蒂諾斯': 'zolpidem',
}
for supp_id, supp_info in SUPPLEMENTS.items():
    for alias in supp_info['aliases']:
        SYNONYMS[alias.casefold()] = supp_id

DRUGS |= set(SYNONYMS) | set(SYNONYMS.values())


def resolve_supplement(s):
    val = ' '.join(unicodedata.normalize('NFKC', str(s)).casefold().split())
    val_clean = re.sub(r'\s+\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|iu|毫克|微克|公克).*$', '', val).strip()
    val_nospace = re.sub(r'\s+', '', val_clean)
    for supp_id, info in SUPPLEMENTS.items():
        if val_clean == supp_id or val_nospace == supp_id:
            return supp_id
        for alias in info['aliases']:
            a_norm = alias.casefold()
            if val_clean == a_norm or val_nospace == re.sub(r'\s+', '', a_norm):
                return supp_id
            # Only allow substring match for CJK aliases of length >= 2
            if len(a_norm) >= 2 and not re.search(r'[a-z]', a_norm) and a_norm in val_clean:
                return supp_id
    return None


def generic_name(s):
    value = ' '.join(unicodedata.normalize('NFKC', s).casefold().split())
    if value in DRUGS:
        return SYNONYMS.get(value, value)
    supp = resolve_supplement(s)
    if supp:
        return supp
    return None


def components(values):
    found = set()
    unmapped = []
    salt_re = r'\b(?:mg|mcg|ug|g|ml|iu|unit|units|hydrochloride|hcl|hydrobromide|hbr|calcium|sodium|potassium|tartrate|bitartrate|phosphate|sulfate|sulphate|maleate|fumarate|succinate|besylate|besilate|mesylate|mesilate|citrate|acetate|hydrate|monohydrate|dihydrate|trihydrate|hemihydrate|anhydrous|acid|as)\b'
    for value in values:
        supp = resolve_supplement(value)
        if supp and '+' not in value and not re.search(r'[a-z]', value.casefold()):
            found.add(supp)
            continue
        cleaned_for_match = re.sub(salt_re, ' ', value.casefold())
        hits = {SYNONYMS.get(name, name) for name in DRUGS if re.search(r'(?<![a-z])' + re.escape(name) + r'(?![a-z])', cleaned_for_match)}
        found |= hits
        residual = cleaned_for_match
        for name in sorted(DRUGS, key=len, reverse=True):
            residual = re.sub(r'(?<![a-z])' + re.escape(name) + r'(?![a-z])', ' ', residual)
        residual = re.sub(r'\d+(?:\.\d+)?', ' ', residual)
        if not hits or re.search('[a-z]', residual):
            unmapped.append(value)
    return found, unmapped


ROUTES = {'unknown', 'oral', 'parenteral', 'topical', 'ophthalmic', 'vaginal', 'transdermal', 'sublingual', 'inhaled'}
INDICATIONS = {'unknown', 'insomnia', 'hypertension', 'atrial_fibrillation', 'heart_failure', 'epilepsy', 'severe_anxiety', 'alcohol_withdrawal', 'rem_sleep_behavior', 'procedural', 'schizophrenia', 'bipolar', 'primary_prevention', 'secondary_prevention', 'gastroprotection', 'erosive_esophagitis', 'barrett', 'zollinger_ellison', 'other'}
FORMULATIONS = {'unknown', 'immediate_release', 'extended_release'}


def validate_med(item, validate_text):
    if isinstance(item, str):
        return {'name': validate_text(item), 'route': 'unknown', 'indication': 'unknown', 'formulation': 'unknown', 'dailyDoseMg': None, 'durationDays': None}
    if not isinstance(item, dict) or 'name' not in item or set(item) - {'name', 'route', 'indication', 'formulation', 'dailyDoseMg', 'durationDays', 'itemType'}:
        raise ValueError('藥品僅允許名稱、途徑、適應症、劑型、每日毫克量及療程天數。')
    med = {
        'name': validate_text(item['name']),
        'route': item.get('route', 'unknown'),
        'indication': item.get('indication', 'unknown'),
        'formulation': item.get('formulation', 'unknown'),
        'dailyDoseMg': item.get('dailyDoseMg'),
        'durationDays': item.get('durationDays'),
    }
    for k, allowed in [('route', ROUTES), ('indication', INDICATIONS), ('formulation', FORMULATIONS)]:
        if not isinstance(med[k], str) or med[k] not in allowed:
            raise ValueError('不支援的藥品臨床分類：' + k)
    for k in ['dailyDoseMg', 'durationDays']:
        v = med[k]
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > 1e6):
            raise ValueError('劑量／療程需為有限非負數字。')
    return med


DIAGNOSES = {
    'heart_failure': {'心衰竭', 'heart failure', 'hf', 'i50'},
    'dementia': {'失智症', '失智', 'dementia', 'f03'},
    'delirium': {'譫妄', 'delirium', 'f05'},
    'falls': {'跌倒史', '反覆跌倒', 'history of falls', 'falls'},
    'fractures': {'骨折史', 'history of fractures'},
    'parkinsons': {'帕金森氏症', '帕金森病', 'parkinson disease', 'parkinsons disease', 'g20'},
    'peptic_ulcer': {'胃潰瘍', '十二指腸潰瘍', '消化性潰瘍', 'peptic ulcer'},
    'syncope': {'暈厥', 'syncope'},
    'bph': {'攝護腺肥大', '良性攝護腺肥大', '前列腺增生', 'bph'},
    'gout': {'痛風', 'gout'},
    'epilepsy': {'癲癇', 'epilepsy'},
    'atrial_fibrillation': {'心房顫動', 'atrial fibrillation', 'af'},
    'coronary_disease': {'冠心病', '冠狀動脈疾病', 'coronary artery disease'},
    'stroke': {'中風史', '缺血性中風', 'ischemic stroke'},
    'frailty': {'衰弱', 'frailty'},
    'palliative': {'安寧照護', '生命末期', 'palliative', 'end of life'},
    'copd': {'慢性阻塞性肺病', 'copd'},
    'asthma': {'氣喘', 'asthma'},
    'urinary_retention': {'尿滯留', 'urinary retention'},
    'liver_disease': {'肝硬化', '肝衰竭', '慢性肝炎', '肝功能不全', 'cirrhosis', 'hepatic impairment', 'liver failure', 'child-pugh b', 'child-pugh c'},
    'ckd': {'慢性腎臟病', '腎衰竭', '尿毒症', 'ckd', 'chronic kidney disease', 'esrd'},
}


def diagnosis_state(values, key):
    known = set()
    aliases = DIAGNOSES[key] | {key}
    for value in values:
        v = value.strip().casefold()
        negative = False
        for prefix in ['無：', '無:', '否認：', '否認:', 'no:', 'absent:']:
            if v.startswith(prefix):
                negative = True
                v = v[len(prefix):].strip()
                break
        if v in aliases:
            known.add(not negative)
    return next(iter(known)) if len(known) == 1 else None


LAB_ALIASES = {
    'CrCl': {'crcl', 'creatinine clearance', '肌酸酐清除率', 'ccr'},
    'eGFR': {'egfr', '估算腎絲球過濾率', '腎絲球過濾率', 'gfr'},
    'Scr': {'scr', 'creatinine', 'serum creatinine', '肌酸酐', '血中肌酸酐', 'cr'},
    'AST': {'ast', 'got', 'sgot', '天門冬胺酸轉胺酶', '肝指數ast', '肝指數got'},
    'ALT': {'alt', 'gpt', 'sgpt', '丙胺酸轉胺酶', '肝指數alt', '肝指數gpt'},
    'TBIL': {'tbil', 'total bilirubin', 'bilirubin', '總膽紅素', '膽紅素', 't-bil'},
    'ChildPugh': {'child-pugh', 'child pugh', 'childpugh', '肝硬化分級分數', 'child-pugh score'},
    'K': {'k', 'k+', 'potassium', '血鉀', '鉀'},
    'Na': {'na', 'na+', 'sodium', '血鈉', '鈉'},
    'HR': {'hr', 'heart rate', '心率'},
    'correctedCa': {'corrected calcium', 'correctedca', '校正鈣'},
}


def lab_value(labs, name):
    accepted = {
        'CrCl': {'ml/min'},
        'eGFR': {'ml/min/1.73m2', 'ml/min/1.73m²', 'ml/min'},
        'Scr': {'mg/dl'},
        'AST': {'u/l', 'iu/l'},
        'ALT': {'u/l', 'iu/l'},
        'TBIL': {'mg/dl'},
        'ChildPugh': {'score', '分', '點', 'points'},
        'K': {'mmol/l', 'meq/l'},
        'Na': {'mmol/l', 'meq/l'},
        'HR': {'bpm', '/min', '次/分'},
        'correctedCa': {'mmol/l', 'mg/dl'},
    }[name]
    values = []
    for lab in labs:
        if lab['name'].strip().casefold() in LAB_ALIASES[name]:
            unit = re.sub(r'\s', '', unicodedata.normalize('NFKC', lab['unit']).casefold())
            if unit not in accepted:
                return None
            value = lab['value']
            if not math.isfinite(value) or value < 0:
                return None
            values.append(value)
    return values[0] if values and len(set(values)) == 1 else None


def members(target):
    out = set()
    for part in target.split('|'):
        out |= GROUPS[part[1:]] if part.startswith('@') else {part}
    return out


RULES = []


def rule(id, source, target, title, conditions=(), exceptions=(), note=''):
    RULES.append(dict(id=id, source=source, target=target, title=title, conditions=list(conditions), exceptions=list(exceptions), note=note))


def c(op, *args):
    return [op, *args]


# Beers table 2: age-based screening. These are potential-risk flags, never stop orders.
for id, target, title, exceptions, note in [
    ('BZD', '@benzodiazepines', '苯二氮平類：認知、譫妄、跌倒及骨折風險', ('epilepsy', 'rem_sleep_behavior', 'alcohol_withdrawal', 'severe_anxiety', 'procedural'), '癲癇等特定適應症可能合理，需人工確認；不可自行驟停。'),
    ('ZDRUG', '@zdrugs', 'Z 類安眠藥：譫妄、跌倒與骨折風險', (), '僅原始 Beers 所列 eszopiclone、zaleplon、zolpidem；zopiclone 另依 PIM-Taiwan。'),
    ('ANTIDEP', '@strong_antidepressants', '強抗膽鹼抗憂鬱藥：鎮靜、姿勢性低血壓與抗膽鹼風險', (), ''),
    ('MUSCLE', '@muscle_relaxants', '肌肉鬆弛劑：鎮靜、抗膽鹼及骨折風險', (), ''),
    ('MEGESTROL', 'megestrol', 'Megestrol：血栓及死亡風險，體重改善效益有限', (), ''),
    ('MEPERIDINE', 'meperidine', 'Meperidine：神經毒性及譫妄風險', (), ''),
    ('INDOMETHACIN', 'indomethacin', 'Indomethacin：腸胃出血、腎損傷及中樞副作用風險', (), ''),
    ('KETOROLAC', 'ketorolac', 'Ketorolac：腸胃出血與急性腎損傷風險', (), ''),
    ('GLYBURIDE', 'glyburide|glimepiride|chlorpropamide', '長效磺醯脲類：持續性低血糖風險', (), '須考慮其他降血糖治療與可取得性；不應自行停藥。'),
    ('BENZTROPINE', 'benztropine|trihexyphenidyl', '抗帕金森抗膽鹼藥：高齡者耐受性較差', (), '口服製劑的用途與替代治療需覆核。')
]:
    rule('BEERS-T2-' + id, 'beers', target, title, exceptions=exceptions, note=note)

# Remove zopiclone from Beers-only criterion.
GROUPS['beers_zdrugs'] = {'zolpidem', 'zaleplon', 'eszopiclone'}
next(r for r in RULES if r['id'] == 'BEERS-T2-ZDRUG')['target'] = '@beers_zdrugs'
for _id in ['BEERS-T2-INDOMETHACIN', 'BEERS-T2-KETOROLAC']:
    next(r for r in RULES if r['id'] == _id)['conditions'] = [c('route', 'oral', 'parenteral')]
next(r for r in RULES if r['id'] == 'BEERS-T2-BENZTROPINE')['conditions'] = [c('route', 'oral')]
rule('BEERS-T2-ANTIHIST', 'beers', '@first_antihistamines', '第一代抗組織胺：抗膽鹼、混亂與跌倒風險', [c('route', 'oral')], note='Diphenhydramine 用於急性嚴重過敏等情境可能合理；仍需覆核。')
rule('BEERS-T2-DOXEPIN', 'beers', 'doxepin', '口服 doxepin 每日超過 6 mg 的抗膽鹼與鎮靜風險', [c('route', 'oral'), c('dose', '>', 6)])
rule('BEERS-T2-DIGOXIN', 'beers', 'digoxin', 'Digoxin 每日超過 0.125 mg 有較高毒性風險', [c('dose', '>', 0.125)], note='心衰竭或心房顫動第一線使用另需個別檢視；不要自行驟停。')
rule('BEERS-T2-PPI', 'beers', '@ppi', 'PPI 超過 8 週使用需重新評估適應症', [c('duration', '>', 56)], exceptions=['erosive_esophagitis', 'barrett', 'zollinger_ellison', 'gastroprotection'], note='高風險腸胃保護及維持治療等可能適當；須覆核其他例外。')
rule('BEERS-T2-METOCLOPRAMIDE', 'beers', 'metoclopramide', 'Metoclopramide 超過 12 週使用需覆核遲發性運動障礙風險', [c('duration', '>', 84)], note='胃輕癱與少數例外需由醫師判斷。')
rule('BEERS-T2-ALPHA1', 'beers', 'doxazosin|prazosin|terazosin', '非選擇性 α1 阻斷劑用於高血壓：姿勢性低血壓風險', [c('indication', 'hypertension')])
rule('BEERS-T3-DEMENTIA-ANTIPSYCH', 'beers', '@antipsychotics', '失智或譫妄患者使用抗精神病藥需覆核中風、認知及死亡風險', [c('diagnosis', 'dementia', 'delirium')], exceptions=['schizophrenia', 'bipolar'], note='處理危及安全的行為問題等情境可能合理；需確認非藥物處置與最低有效療程。')

# Beers table 6: preserve measure and exact threshold, never replace CrCl with eGFR.
for name, measure, op, value, action in [
    ('ciprofloxacin', 'CrCl', '<', 30, '需依適應症調降劑量'), ('nitrofurantoin', 'CrCl', '<', 30, '應避免使用'),
    ('amiloride', 'CrCl', '<', 30, '應避免使用'), ('dabigatran', 'CrCl', '<', 30, '應避免使用'),
    ('dofetilide', 'CrCl', '<', 60, '需調整劑量；低於 20 應避免'), ('edoxaban', 'CrCl', '<=', 50, '15–50 需減量；低於 15 應避免'),
    ('enoxaparin', 'CrCl', '<', 30, '需減量'), ('fondaparinux', 'CrCl', '<', 30, '應避免使用'),
    ('rivaroxaban', 'CrCl', '<=', 50, '依適應症與仿單調整；低於 15 應避免'), ('spironolactone', 'CrCl', '<', 30, '應避免使用'),
    ('triamterene', 'CrCl', '<', 30, '應避免使用'), ('baclofen', 'eGFR', '<', 60, '應避免；無法避免時需最低有效劑量並監測中樞毒性'),
    ('duloxetine', 'CrCl', '<', 30, '應避免使用'), ('gabapentin', 'CrCl', '<', 60, '需減量'), ('levetiracetam', 'CrCl', '<=', 80, '需減量'),
    ('pregabalin', 'CrCl', '<', 60, '需減量'), ('tramadol', 'CrCl', '<', 30, '速放型需減量；緩釋型應避免'),
    ('cimetidine', 'CrCl', '<', 50, '需減量'), ('famotidine', 'CrCl', '<', 50, '需減量'), ('nizatidine', 'CrCl', '<', 50, '需減量'),
    ('colchicine', 'CrCl', '<', 30, '需減量並監測毒性'), ('probenecid', 'CrCl', '<', 30, '應避免使用')
]:
    rule('BEERS-T6-' + name.upper(), 'beers', name, action, [c('lab', measure, op, value)], note='依原準則腎功能門檻篩檢，實際劑量須核對適應症及台灣仿單。')
rule('BEERS-T6-EDOXABAN-HIGH', 'beers', 'edoxaban', 'CrCl 高於 95 mL/min 應避免 edoxaban', [c('lab', 'CrCl', '>', 95)])
rule('BEERS-T6-TMP-SMX', 'beers', 'trimethoprim|sulfamethoxazole', 'TMP-SMX：CrCl 15–29 需減量，低於 15 應避免', [c('co', 'trimethoprim'), c('co', 'sulfamethoxazole'), c('lab', 'CrCl', '<', 30)])
rule('BEERS-T6-NSAIDS', 'beers', '@nsaids', '腎功能低下者使用全身性 NSAID 的腎損傷風險', [c('route', 'oral', 'parenteral'), c('lab', 'CrCl', '<', 30)])
next(r for r in RULES if r['id'] == 'BEERS-T6-TRAMADOL')['conditions'].append(c('formulation_known'))

# Beers table 5 interactions (screening, no dose advice or automatic discontinuation).
for id, target, partner, title in [
    ('OPIOID-BZD', '@opioids', '@benzodiazepines', 'Opioid 合併苯二氮平類：過量與呼吸抑制風險'),
    ('OPIOID-GABA', '@opioids', '@gabapentinoids', 'Opioid 合併 gabapentin／pregabalin：嚴重鎮靜與呼吸抑制風險'),
    ('WARFARIN-AMIODARONE', 'warfarin', 'amiodarone', 'Warfarin 合併 amiodarone：出血風險'),
    ('WARFARIN-CIPRO', 'warfarin', 'ciprofloxacin', 'Warfarin 合併 ciprofloxacin：出血風險'),
    ('WARFARIN-MACROLIDE', 'warfarin', 'clarithromycin|erythromycin', 'Warfarin 合併部分 macrolide：出血風險'),
    ('WARFARIN-TMP-SMX', 'warfarin', 'trimethoprim', 'Warfarin 合併 TMP-SMX：出血風險'),
    ('WARFARIN-SSRI', 'warfarin', '@ssri', 'Warfarin 合併 SSRI：出血風險'),
    ('LITHIUM-ACE', 'lithium', '@ace', 'Lithium 合併 ACEI：鋰中毒風險'),
    ('LITHIUM-LOOP', 'lithium', '@loop', 'Lithium 合併 loop 利尿劑：鋰中毒風險'),
    ('LITHIUM-ARB', 'lithium', '@arb', 'Lithium 合併 ARB／含 valsartan 的 ARNI：鋰中毒風險'),
    ('THEOPHYLLINE-CIMETIDINE', 'theophylline', 'cimetidine', 'Theophylline 合併 cimetidine：毒性風險'),
    ('THEOPHYLLINE-CIPRO', 'theophylline', 'ciprofloxacin', 'Theophylline 合併 ciprofloxacin：毒性風險'),
    ('PHENYTOIN-TMP-SMX', 'phenytoin', 'trimethoprim', 'Phenytoin 合併 TMP-SMX：毒性風險')
]:
    conditions = [c('co', partner)]
    if id in ['WARFARIN-TMP-SMX', 'PHENYTOIN-TMP-SMX']:
        conditions.append(c('co', 'sulfamethoxazole'))
    rule('BEERS-T5-' + id, 'beers', target, title, conditions, note='需由臨床人員確認適應症、替代方案及必要監測；部分併用情境有例外。')
rule('BEERS-T5-CNS3', 'beers', '@cns', '同時使用三種以上中樞作用藥：跌倒及骨折風險', [c('count', '@cns', '>=', 3)])
rule('BEERS-T5-ANTICHOL2', 'beers', '@anticholinergic', '多種抗膽鹼藥併用：認知、譫妄與跌倒風險', [c('count', '@anticholinergic', '>=', 2)])

# Disease interactions
for id, target, diagnoses, title in [
    ('HF-NSAID', '@nsaids', ['heart_failure'], '心衰竭患者使用全身性 NSAID 可能惡化體液滯留'),
    ('HF-TZD', 'pioglitazone|rosiglitazone', ['heart_failure'], '心衰竭患者使用 TZD 可能惡化體液滯留'),
    ('DEMENTIA-ANTICHOL', '@anticholinergic', ['dementia', 'delirium'], '失智或譫妄患者使用強抗膽鹼藥可能惡化認知'),
    ('FALLS-BZD', '@benzodiazepines', ['falls', 'fractures'], '有跌倒／骨折史者使用苯二氮平類風險增加'),
    ('FALLS-ZDRUG', '@zdrugs', ['falls', 'fractures'], '有跌倒／骨折史者使用 Z 類安眠藥風險增加'),
    ('FALLS-ANTIPSYCH', '@antipsychotics', ['falls', 'fractures'], '有跌倒／骨折史者使用抗精神病藥風險增加'),
    ('SYNCOPE-AChEI', 'donepezil|rivastigmine|galantamine', ['syncope'], '暈厥患者使用膽鹼酯酶抑制劑需檢視心搏過緩原因'),
    ('PARKINSON-METOCLO', 'metoclopramide', ['parkinsons'], '帕金森病患者使用 metoclopramide 可能惡化動作症狀'),
    ('BPH-ANTICHOL', '@anticholinergic_nonbladder', ['bph'], '攝護腺肥大患者需覆核強抗膽鹼藥對排尿影響')
]:
    cond = [c('diagnosis', *diagnoses)]
    if id == 'HF-NSAID':
        cond.append(c('route', 'oral', 'parenteral'))
    rule('BEERS-T3-' + id, 'beers', target, title, cond, note='疾病、嚴重度、用途與例外仍需臨床覆核。')

# STOPP v3: selected precisely encoded numbered criteria.
rule('STOPP-B3', 'stopp-start', '@beta', 'Beta 阻斷劑合併 verapamil／diltiazem：心傳導阻滯風險', [c('co', 'verapamil|diltiazem')])
rule('STOPP-B4', 'stopp-start', '@beta', '心率低於 50 時使用減慢心率藥有傳導阻滯風險', [c('lab', 'HR', '<', 50)])
rule('STOPP-B4-OTHER', 'stopp-start', 'verapamil|diltiazem|digoxin', '心率低於 50 時使用減慢心率藥有傳導阻滯風險', [c('lab', 'HR', '<', 50)])
rule('STOPP-B9-K', 'stopp-start', '@thiazide', 'Thiazide 合併低血鉀', [c('lab', 'K', '<', 3)])
rule('STOPP-B9-Na', 'stopp-start', '@thiazide', 'Thiazide 合併低血鈉', [c('lab', 'Na', '<', 130)])
rule('STOPP-B9-Ca', 'stopp-start', '@thiazide', 'Thiazide 合併校正血鈣過高', [c('lab', 'correctedCa', '>', 2.65)])
rule('STOPP-B9-GOUT', 'stopp-start', '@thiazide', 'Thiazide 合併痛風史', [c('diagnosis', 'gout')])
rule('STOPP-B11', 'stopp-start', 'methyldopa|clonidine|moxonidine|rilmenidine|guanfacine', '中樞作用降壓藥在高齡者耐受性較差')
EXTRA.update({'clonidine', 'moxonidine', 'rilmenidine'})
DRUGS |= EXTRA
for target, suffix in [('@ace', 'ACE'), ('@arb', 'ARB')]:
    rule('STOPP-B12-' + suffix, 'stopp-start', target, 'ACEI／ARB 合併血鉀高於 5.5 mmol/L', [c('lab', 'K', '>', 5.5)])
rule('STOPP-B14-NITRATE', 'stopp-start', '@pde5', 'PDE5 抑制劑合併硝酸鹽有嚴重低血壓風險', [c('co', '@nitrates')], note='此為 B14 併用分支；嚴重心衰竭／低血壓分支仍需人工覆核。')
rule('STOPP-C6', 'stopp-start', 'ticlopidine', 'Ticlopidine 應重新評估，其他藥物有較佳安全性依據')
rule('STOPP-C10', 'stopp-start', '@nsaids', 'NSAID 合併抗凝血藥：重大腸胃出血風險', [c('route', 'oral', 'parenteral'), c('co', '@anticoagulants')])

# PIM-Taiwan: explicit group-based screening
for id, target, title in [
    ('BZD', '@benzodiazepines', '苯二氮平類：認知、混亂、跌倒及骨折風險'),
    ('ZDRUG', '@zdrugs', '非苯二氮平安眠藥：認知、混亂、跌倒及骨折風險'),
    ('TCA', '@strong_antidepressants', '強抗膽鹼抗憂鬱藥：混亂、鎮靜與姿勢性低血壓風險'),
    ('LONG-SU', 'glyburide|chlorpropamide', '長效磺醯脲類：持續性低血糖風險')
]:
    rule('PIM-TW-T1-' + id, 'pim-taiwan', target, title, note='對應 PIM-Taiwan 2018 Table 1 的部分藥群，並非 Table 1 全部 140 列。')
rule('PIM-TW-T1-ANTIHIST', 'pim-taiwan', '@first_antihistamines', '第一代抗組織胺的抗膽鹼風險', [c('route', 'oral')])
rule('PIM-TW-T1-DIGOXIN', 'pim-taiwan', 'digoxin', 'Digoxin 高劑量毒性風險', [c('dose', '>', 0.125)])
for suffix, target, diagnoses, title in [
    ('HF-NSAID', '@nsaids', ['heart_failure'], '心衰竭合併 NSAID 可能惡化病情'),
    ('HF-CCB', 'verapamil|diltiazem', ['heart_failure'], '心衰竭合併非二氫吡啶鈣離子阻斷劑需覆核'),
    ('HF-TZD', 'pioglitazone|rosiglitazone', ['heart_failure'], '心衰竭合併 TZD 可能惡化病情'),
    ('FALLS-BZD', '@benzodiazepines', ['falls', 'fractures'], '有跌倒／骨折史者使用苯二氮平類需覆核'),
    ('DEMENTIA', '@anticholinergic', ['delirium', 'dementia'], '失智／譫妄患者使用抗膽鹼藥需覆核')
]:
    conditions = [c('diagnosis', *diagnoses)]
    if suffix == 'HF-NSAID':
        conditions.append(c('route', 'oral', 'parenteral'))
    rule('PIM-TW-T2-' + suffix, 'pim-taiwan', target, title, conditions)

# === 新增：肝腎功能延伸篩檢規則 (Hepatic & Renal Safety Screening) ===
rule('RENAL-METFORMIN-30', 'organ-safety', 'metformin', 'Metformin 於 eGFR < 30 mL/min/1.73m2 屬禁忌：乳酸中毒風險', [c('lab', 'eGFR', '<', 30)], note='依台灣 TFDA 與國際準則，eGFR < 30 應停用 Metformin。')
rule('RENAL-METFORMIN-45', 'organ-safety', 'metformin', 'Metformin 於 eGFR < 45 mL/min/1.73m2 需評估減量並密切監測腎功能', [c('lab', 'eGFR', '<', 45)], note='eGFR 30-45 不建議新起始，既有使用者建議減半劑量。')
rule('RENAL-NSAID-EGFR', 'organ-safety', '@nsaids', 'eGFR < 30 mL/min/1.73m2 使用 NSAID 具急性腎損傷與體液滯留高風險', [c('lab', 'eGFR', '<', 30)], note='高齡腎功能不全患者應避免全身性 NSAID。')
rule('RENAL-ALLOPURINOL', 'organ-safety', 'allopurinol', 'Allopurinol 於 eGFR < 60 mL/min/1.73m2 需依腎功能調降起始與維持劑量', [c('lab', 'eGFR', '<', 60)], note='腎功能低下未減量會增加嚴重皮膚不良反應（SCAR）與毒性風險。')
rule('RENAL-DIGOXIN-EGFR', 'organ-safety', 'digoxin', 'Digoxin 於 eGFR < 50 mL/min/1.73m2 排泄減少，需減量並監測血中濃度', [c('lab', 'eGFR', '<', 50)])
rule('RENAL-SCR-HIGH-NSAID', 'organ-safety', '@nsaids', '血清肌酸酐 (Scr) > 1.5 mg/dL 使用 NSAID 惡化腎功能風險', [c('lab', 'Scr', '>', 1.5)])

rule('HEPATIC-STATIN-ALT', 'organ-safety', '@statins', 'Statin 類降血脂藥合併 ALT (GPT) > 120 U/L（>3倍上限）：肝損傷風險需評估停藥或換藥', [c('lab', 'ALT', '>', 120)], note='轉胺酶顯著上升超過正常上限 3 倍時，應立即覆核 Statin 安全性。')
rule('HEPATIC-STATIN-AST', 'organ-safety', '@statins', 'Statin 類降血脂藥合併 AST (GOT) > 120 U/L（>3倍上限）：肝損傷風險需評估', [c('lab', 'AST', '>', 120)])
rule('HEPATIC-APAP-ALT', 'organ-safety', 'paracetamol', 'Acetaminophen (普拿疼) 於肝指數異常 (ALT > 100 U/L) 需限制每日總劑量 (<2000 mg/day)', [c('lab', 'ALT', '>', 100)], note='肝功能受損或肝硬化高齡患者應調降 Acetaminophen 每日最大量。')
rule('HEPATIC-DULOXETINE', 'organ-safety', 'duloxetine', 'Duloxetine 於肝功能不全 (ALT > 80 U/L 或慢性肝病) 應避免使用', [c('lab', 'ALT', '>', 80)], note='Duloxetine 具肝毒性風險且經肝代謝，肝功能異常應避免。')
rule('HEPATIC-BZD-LIVER', 'organ-safety', 'diazepam|chlordiazepoxide|flurazepam|clonazepam|alprazolam|midazolam', '長效或經肝氧化代謝之 BZD 於肝功能異常 (TBIL > 2.0 mg/dL 或 Child-Pugh >= 7) 易誘發肝性腦病變與過度鎮靜', [c('lab', 'TBIL', '>', 2.0)], note='若必須使用 BZD，Lot 類（Lorazepam、Oxazepam、Temazepam）受肝代謝影響較小。')
rule('HEPATIC-DOAC-CHILD', 'organ-safety', 'rivaroxaban|apixaban|edoxaban', '中重度肝硬化 (Child-Pugh >= 7 分) 使用新型口服抗凝血劑 (DOAC) 出血與蓄積風險', [c('lab', 'ChildPugh', '>=', 7)], note='Rivaroxaban 於 Child-Pugh B/C 屬禁忌；其他 DOAC 於 Child-Pugh C 禁用。')

# === 新增：保健食品與中西藥交互作用篩檢規則 (Supplement-Drug Interactions) ===
rule('SUPP-BLEED-ANTICOAG', 'supplement-safety', '@bleeding_supplements', '具抗血小板/抗凝血作用之保健食品（銀杏、魚油、大蒜精、人參、薑黃、葡萄糖胺）合併口服抗凝血劑：顯著增加出血風險', [c('co', '@anticoagulants')], note='建議密切監測瘀青、牙齦出血、黑便或 INR（若使用 Warfarin），必要時停用保健食品。')
rule('SUPP-ANTICOAG-BLEED', 'supplement-safety', '@anticoagulants', '口服抗凝血劑（如 Warfarin、DOAC）合併具抗血小板/抗凝血作用之保健食品（銀杏、魚油、大蒜精、人參、薑黃、葡萄糖胺）：顯著增加出血風險', [c('co', '@bleeding_supplements')], note='建議密切監測瘀青、牙齦出血、黑便或 INR（若使用 Warfarin），必要時停用保健食品。')
rule('SUPP-BLEED-ANTIPLATELET', 'supplement-safety', '@bleeding_supplements', '具抗血小板作用之保健食品（銀杏、魚油、大蒜精、人參、薑黃）合併抗血小板藥（Aspirin、Clopidogrel 等）：加成出血風險', [c('co', '@antiplatelets')], note='高齡者腸胃道與顱內出血風險較高，應評估保健食品必要性。')
rule('SUPP-BLEED-NSAID', 'supplement-safety', 'ginkgo_biloba|fish_oil|garlic|ginseng', '銀杏／魚油／大蒜精／人參合併 NSAID 止痛藥：增加胃腸道黏膜出血風險', [c('co', '@nsaids')])
rule('SUPP-RYR-STATIN', 'supplement-safety', 'red_yeast_rice', '紅麴（含 Monacolin K，結構同 Lovastatin）合併 Statin 降血脂藥：重複用藥，大幅增加橫紋肌溶解症與肝毒性風險', [c('co', '@statins')], note='紅麴與處方 Statin 嚴禁併用，請衛教病人立即停用紅麴保健品。')
rule('SUPP-STATIN-RYR', 'supplement-safety', '@statins', '處方 Statin 降血脂藥合併紅麴（含 Monacolin K）：重複用藥，大幅增加橫紋肌溶解症與肝毒性風險', [c('co', 'red_yeast_rice')], note='紅麴與處方 Statin 嚴禁併用，請衛教病人立即停用紅麴保健品。')
rule('SUPP-RYR-ALT', 'supplement-safety', 'red_yeast_rice', '紅麴於肝功能異常 (ALT > 80 U/L) 使用：可能惡化肝指數', [c('lab', 'ALT', '>', 80)])
rule('SUPP-VITK-WARFARIN', 'supplement-safety', 'vitamin_k', '維生素 K 或納豆製品合併 Warfarin：直接拮抗 Warfarin 藥效，導致 INR 下降與血栓風險', [c('co', 'warfarin')], note='服用 Warfarin 患者應避免額外補充維生素 K、納豆、納豆激酶或大量深綠色蔬菜萃取物。')
rule('SUPP-SJW-ANTICOAG', 'supplement-safety', 'st_johns_wort', '聖約翰草 (St. John\'s Wort) 強效誘導 CYP3A4/P-gp，合併抗凝血劑會降低血中濃度導致血栓風險', [c('co', '@anticoagulants')])
rule('SUPP-SJW-SEROTONIN', 'supplement-safety', 'st_johns_wort', '聖約翰草合併抗憂鬱藥 (SSRI/SNRI/TCA)：引發血清素症候群 (Serotonin syndrome) 高風險', [c('co', '@ssri|@snri|@strong_antidepressants')])
rule('SUPP-SJW-STATIN', 'supplement-safety', 'st_johns_wort', '聖約翰草合併 Statin（特別是 Atorvastatin/Simvastatin）：誘導代謝降低降膽固醇療效', [c('co', '@statins')])
rule('SUPP-MINERAL-FQ', 'supplement-safety', '@mineral_chelators', '鈣／鐵／鎂補充劑合併 Fluoroquinolone 類抗生素：形成螯合物大幅降低抗生素吸收與療效', [c('co', '@fluoroquinolones')], note='必須前後間隔至少 2 至 4 小時服用。')
rule('SUPP-MINERAL-TETRA', 'supplement-safety', '@mineral_chelators', '鈣／鐵／鎂補充劑合併四環黴素類抗生素 (Doxycycline 等)：螯合作用降低抗生素吸收', [c('co', '@tetracyclines')], note='必須前後間隔至少 2 至 4 小時服用。')
rule('SUPP-MINERAL-THYROID', 'supplement-safety', '@mineral_chelators', '鈣／鐵／鎂補充劑合併甲狀腺素 (Levothyroxine)：減少甲狀腺素腸道吸收', [c('co', 'levothyroxine')], note='建議與 Levothyroxine 間隔 4 小時以上服用。')
rule('SUPP-MGO-RENAL', 'supplement-safety', 'magnesium', '鎂補充劑／氧化鎂於腎功能低下 (eGFR < 30 或 CrCl < 30) 易蓄積引發高血鎂症（嗜睡、低血壓、心律不整）', [c('lab', 'eGFR', '<', 30)])
rule('SUPP-COQ10-WARFARIN', 'supplement-safety', 'coq10', '輔酶 Q10 結構類似維生素 K2，合併 Warfarin 可能減弱抗凝血效果', [c('co', 'warfarin')], note='若併用需密切監測 PT/INR。')
rule('SUPP-COQ10-BP', 'supplement-safety', 'coq10', '輔酶 Q10 合併降血壓藥：可能具加成降壓作用，高齡者需留意姿勢性低血壓', [c('co', '@antihypertensives')])
rule('SUPP-GINSENG-DM', 'supplement-safety', 'ginseng', '人參／西洋參合併降血糖藥或胰島素：可能加強降血糖作用，增加高齡者低血糖風險', [c('co', '@antidiabetics')])
rule('SUPP-LICORICE-BP', 'supplement-safety', 'licorice', '甘草萃取物具礦物皮質酮作用（留鈉排鉀），合併降血壓藥或利尿劑會拮抗降壓效果並誘發低血鉀', [c('co', '@antihypertensives')])
rule('SUPP-KSUPP-RAAS', 'supplement-safety', 'potassium_supp', '鉀補充劑／低鈉代鹽合併 ACEI／ARB 或保鉀利尿劑：嚴重高血鉀與心律不整風險', [c('co', '@ace|@arb|@k_sparing')])
rule('SUPP-MELATONIN-CNS', 'supplement-safety', 'melatonin', '褪黑激素合併鎮靜安眠藥 (BZD / Z-drugs)：加成嗜睡、晨間暈眩與高齡跌倒風險', [c('co', '@benzodiazepines|@zdrugs')])

COMPARE = {'<': lambda a, b: a < b, '<=': lambda a, b: a <= b, '>': lambda a, b: a > b, '>=': lambda a, b: a >= b}
for _rule in RULES:
    for part in _rule['target'].split('|'):
        DRUGS |= members(part)


def approved_sources():
    return {'beers', 'stopp-start', 'pim-taiwan', 'organ-safety', 'supplement-safety'}


def condition(spec, med, labs, diagnoses, active):
    op, *args = spec
    if op in ['dose', 'duration']:
        value = med['dailyDoseMg' if op == 'dose' else 'durationDays']
        label = '每日劑量 mg/day' if op == 'dose' else '療程天數'
        return (None, label) if value is None else (COMPARE[args[0]](value, args[1]), label)
    if op == 'route':
        return (None, '給藥途徑') if med['route'] == 'unknown' else (med['route'] in args, '給藥途徑')
    if op == 'indication':
        return (None, '適應症') if med['indication'] == 'unknown' else (med['indication'] in args, '適應症')
    if op == 'formulation_known':
        return (None, '速放／緩釋型態') if med['formulation'] == 'unknown' else (True, '速放／緩釋型態')
    if op == 'lab':
        name, cmp, threshold = args
        value = lab_value(labs, name)
        return (None, name + '（指定單位且無衝突的檢驗值）') if value is None else (COMPARE[cmp](value, threshold), name)
    if op == 'diagnosis':
        values = [diagnosis_state(diagnoses, key) for key in args]
        return (True, '／'.join(args)) if True in values else (None, '／'.join(args) + '（明確有或無）') if None in values else (False, '／'.join(args))
    if op == 'co':
        target_set = set()
        for part in args[0].split('|'):
            target_set |= members(part)
        return (bool(active & target_set), '併用藥品／保健品')
    if op == 'count':
        return (COMPARE[args[1]](len(active & members(args[0])), args[2]), '併用藥品數')
    raise ValueError('Unknown clinical operation')


def assess(med, labs, diagnoses, active, approved):
    checks = []
    for r in RULES:
        target_set = set()
        for part in r['target'].split('|'):
            target_set |= members(part)
        if not med['ingredients'] & target_set:
            continue
        check = {k: r[k] for k in ['id', 'source', 'title', 'note', 'conditions']}
        check['missing'] = []
        conditions = [condition(s, med, labs, diagnoses, active) for s in r['conditions']]
        if any(v is False for v, label in conditions):
            check['status'] = 'not_matched'
        elif r['source'] not in approved:
            check.update(status='source_unverified', missing=['此規則版本對應的原始文獻檔／SHA-256'])
        elif med['indication'] in r['exceptions']:
            check['status'] = 'exception_requires_review'
        elif any(v is None for v, label in conditions):
            check.update(status='insufficient_data', missing=[label for v, label in conditions if v is None])
        else:
            check['status'] = 'potential_risk'
        checks.append(check)
    return checks


def coverage():
    sources = ['beers', 'stopp-start', 'pim-taiwan', 'organ-safety', 'supplement-safety']
    counts = {s: sum(r['source'] == s for r in RULES) for s in sources}
    approved = approved_sources()
    return {
        'version': VERSION,
        'fullAutomation': False,
        'clinicalUseReady': False,
        'executableRuleCount': len(RULES),
        'activeRuleCount': sum(r['source'] in approved for r in RULES),
        'verifiedSources': sorted(approved),
        'bySource': counts,
        'stoppStartPublishedCriteria': 190,
        'stoppStartFullyValidatedCriteria': 0,
        'note': '包含 Beers 2023、STOPP/START v3、PIM-Taiwan 2018、肝腎功能安全篩檢與保健食品中西藥交互作用規則。所有結果均需藥師／醫師人工覆核。',
        'rules': [{k: r[k] for k in ['id', 'source', 'title', 'conditions', 'exceptions', 'note']} for r in RULES]
    }


def source_registry():
    path = ROOT / 'public_reference' / 'clinical-criteria-registry.json'
    if not path.exists():
        return {'available': False, 'criteria': [], 'message': '尚未從本機文獻建立條文盤點，不能宣稱完整覆蓋。'}
    records = json.loads(path.read_text(encoding='utf-8'))
    approved = approved_sources()
    parents = {re.match(r'(STOPP-[A-M]\d+)', r['id']).group(1) for r in RULES if r['id'].startswith('STOPP-')}
    for record in records:
        record['automation'] = 'source_unverified' if record['source'] not in approved else 'partially_automated' if record['id'] in parents else 'manual_review'
    return {'available': True, 'fullAutomation': False, 'criteria': records, 'note': 'STOPP 133／START 57 與 PIM-Taiwan Table 1 的 140 列來源盤點；不是三套準則全部可執行規則，也未包含 Beers 全表與 PIM-Taiwan 疾病表完整編碼。'}
