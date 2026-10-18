"""Offline-only exact product lookup. No network code."""
import json, re, sqlite3, unicodedata
from pathlib import Path
from contextlib import closing
import med_strength
import clinical_rules
PATH=Path(__file__).resolve().parent/'public_reference'/'catalog.sqlite'
def norm(s): return re.sub(r'\s','',unicodedata.normalize('NFKC',s)).casefold()
SALT_SUFFIX_RE = re.compile(
    r'\b(?:HYDROCHLORIDE|HCL|HYDROBROMIDE|HBR|CALCIUM|SODIUM|POTASSIUM|MAGNESIUM|TARTRATE|BITARTRATE|'
    r'PHOSPHATE|SULFATE|SULPHATE|MALEATE|FUMARATE|SUCCINATE|BESYLATE|BESILATE|MESYLATE|MESILATE|'
    r'CITRATE|ACETATE|HYDRATE|MONOHYDRATE|DIHYDRATE|TRIHYDRATE|HEMIHYDRATE|ANHYDROUS|CLATHRATE|'
    r'CRYSTALLINE|MICRONIZED|PROPIONATE|VALERATE|BUTYRATE|DIPROPIONATE|FUROATE|ACETONIDE|'
    r'BROMIDE|CHLORIDE|IODIDE|NITRATE|GLUCONATE|LACTATE|SALICYLATE|BENZOATE|PAMOATE|EMBONATE|'
    r'OXALATE|MALATE|STEARATE|CARBONATE|BICARBONATE|DISODIUM|DIPOTASSIUM|CALCIUM\s*\(2:1\)|'
    r'\(SODIUM\)|\(CALCIUM\)|\(POTASSIUM\)|\(HCL\)|\(TARTRATE\)|\(MALEATE\)|\(SULFATE\)|\(2:1\))\b',
    re.I
)
def canonical(s):
    value=re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s).strip().upper())
    value=re.sub(r'\s+\d+(?:\.\d+)?\s*(?:MG|MCG|UG|G|ML|IU|毫克|微克|公克|公絲)$','',value)
    known={'DIAZEPAM':'diazepam','ZOLPIDEM':'zolpidem','ZOLPIDEM TARTRATE':'zolpidem','DIPHENHYDRAMINE':'diphenhydramine','DIPHENHYDRAMINE HYDROCHLORIDE':'diphenhydramine','DIPHENHYDRAMINE HCL':'diphenhydramine','METFORMIN':'metformin','METFORMIN HYDROCHLORIDE':'metformin','METFORMIN HCL':'metformin','ATORVASTATIN':'atorvastatin','ATORVASTATIN (CALCIUM)':'atorvastatin','ATORVASTATIN CALCIUM':'atorvastatin','ATORVASTATIN CALCIUM (2:1) TRIHYDRATE':'atorvastatin'}
    if value in known:
        return known[value]
    stripped=re.sub(r'[()\[\],]+',' ',SALT_SUFFIX_SUFFIX_CLEAN(value) if False else SALT_SUFFIX_RE.sub(' ',value))
    stripped=' '.join(stripped.split()).casefold()
    if stripped in clinical_rules.DRUGS:
        return clinical_rules.SYNONYMS.get(stripped,stripped)
    return value
def lookup(value):
    if not PATH.exists(): return None
    key=norm(value)
    strength=med_strength.parse(value)
    with closing(sqlite3.connect(f'{PATH.as_uri()}?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT DISTINCT p.source,p.code,p.zh,p.en,p.ingredients,p.status,p.form FROM products p JOIN aliases a ON a.product=p.id WHERE a.name=? LIMIT 101',(key,)).fetchall()
        if strength:
            prefix=norm(strength['baseText'])
            candidates=db.execute('SELECT DISTINCT p.source,p.code,p.zh,p.en,p.ingredients,p.status,p.form FROM products p JOIN aliases a ON a.product=p.id WHERE a.name>=? AND a.name<? LIMIT 5001',(prefix,prefix+'\uffff')).fetchall() if len(prefix)>=2 else []
            matches=[]
            for product in list(dict.fromkeys(rows+candidates)):
                if not med_strength.compatible(strength,[product[2],product[3]],product[6]):continue
                bases=[med_strength.parse(label) for label in [product[2],product[3]]]
                name_match=any(b and b['base']==strength['base'] for b in bases)
                ingredient_match=any(norm(canonical(i))==norm(canonical(strength['baseText'])) for i in json.loads(product[4]))
                if name_match or ingredient_match:matches.append(product)
            if len(candidates)>5000 or (len(rows)>100 and not key.startswith(prefix)):
                return {'matched':False,'ambiguous':True,'suggestions':[],'strengthMatch':{'status':'unverified','requested':strength['display'],'note':'相符候選過多，請提供完整商品名及劑型，不能確認含量。'}}
            rows=matches
            if not rows:
                return {'matched':False,'suggestions':[],'strengthMatch':{'status':'unverified','requested':strength['display'],'note':'未找到藥名、含量與指定劑型同時相符的目錄品項；不會改配其他含量。請人工確認或使用雲端候選核對。'}}
        if not rows:
            candidates=[]
            if len(key)>=3 and not re.fullmatch(r'[a-zA-Z0-9]{10}',key):
                candidates=[r[0] for r in db.execute('SELECT DISTINCT display FROM aliases WHERE name LIKE ? ESCAPE "!" LIMIT 5',('%'+key.replace('!','!!').replace('%','!%').replace('_','!_')+'%',))]
            return {'matched':False,'suggestions':candidates}
    signatures={tuple(sorted(set(canonical(i) for i in json.loads(r[4])))) for r in rows}
    if (not strength and len(rows)>100) or len(signatures)!=1 or not next(iter(signatures),()):
        return {'matched':False,'ambiguous':True,'suggestions':list(dict.fromkeys(r[2] or r[3] for r in rows))[:5]}
    result={'matched':True,'ingredients':list(next(iter(signatures))),'products':[dict(zip(['source','code','chineseName','englishName','ingredients','status','form'],r)) for r in rows[:10]],'suggestions':[]}
    if strength:result['strengthMatch']={'status':'matched','requested':strength['display'],'note':'已依目錄標示比對含量及指定劑型；可能仍有多個廠牌、代碼或歷史品項，請核對完整規格。單顆含量未當作每日總量。'}
    return result
def metadata():
    path=PATH.parent/'catalog-manifest.json'
    result=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'not_imported','productCount':0}
    result['clinicalRules']='See /api/clinical/coverage for executable branches and unsupported criteria; catalog count is not clinical rule coverage.'
    return result
