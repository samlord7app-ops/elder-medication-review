"""Offline-only exact product lookup. No network code."""
import json, re, sqlite3, unicodedata
from pathlib import Path
from contextlib import closing
PATH=Path(__file__).resolve().parent/'public_reference'/'catalog.sqlite'
def norm(s): return re.sub(r'\s','',unicodedata.normalize('NFKC',s)).casefold()
def canonical(s):
    value=re.sub(r'\s+',' ',s.strip().upper())
    value=re.sub(r'\s+\d+(?:\.\d+)?\s*(?:MG|MCG|G|毫克)$','',value)
    known={'DIAZEPAM':'diazepam','ZOLPIDEM':'zolpidem','ZOLPIDEM TARTRATE':'zolpidem','DIPHENHYDRAMINE':'diphenhydramine','DIPHENHYDRAMINE HYDROCHLORIDE':'diphenhydramine','DIPHENHYDRAMINE HCL':'diphenhydramine','METFORMIN':'metformin','METFORMIN HYDROCHLORIDE':'metformin','METFORMIN HCL':'metformin','ATORVASTATIN':'atorvastatin','ATORVASTATIN (CALCIUM)':'atorvastatin','ATORVASTATIN CALCIUM':'atorvastatin','ATORVASTATIN CALCIUM (2:1) TRIHYDRATE':'atorvastatin'}
    return known.get(value,value)
def lookup(value):
    if not PATH.exists(): return None
    key=norm(value)
    with closing(sqlite3.connect(f'{PATH.as_uri()}?mode=ro',uri=True)) as db:
        rows=db.execute('SELECT DISTINCT p.source,p.code,p.zh,p.en,p.ingredients,p.status,p.form FROM products p JOIN aliases a ON a.product=p.id WHERE a.name=? LIMIT 101',(key,)).fetchall()
        if not rows:
            candidates=[]
            if len(key)>=3 and not re.fullmatch(r'[a-zA-Z0-9]{10}',key):
                candidates=[r[0] for r in db.execute('SELECT DISTINCT display FROM aliases WHERE name LIKE ? ESCAPE "!" LIMIT 5',('%'+key.replace('!','!!').replace('%','!%').replace('_','!_')+'%',))]
            return {'matched':False,'suggestions':candidates}
    signatures={tuple(sorted(set(canonical(i) for i in json.loads(r[4])))) for r in rows}
    if len(rows)>100 or len(signatures)!=1 or not next(iter(signatures),()):
        return {'matched':False,'ambiguous':True,'suggestions':list(dict.fromkeys(r[2] or r[3] for r in rows))[:5]}
    return {'matched':True,'ingredients':list(next(iter(signatures))),'products':[dict(zip(['source','code','chineseName','englishName','ingredients','status','form'],r)) for r in rows[:10]],'suggestions':[]}
def metadata():
    path=PATH.parent/'catalog-manifest.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'not_imported','productCount':0}
