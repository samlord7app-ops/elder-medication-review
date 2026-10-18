"""Explicit public-data updater; never invoked by clinical requests."""
import urllib.request, json, hashlib, zipfile, io, csv, sqlite3, re, sys
from pathlib import Path
from datetime import datetime
from catalog import norm
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'public_reference'
URLS={'tfda':'https://data.fda.gov.tw/data/opendata/export/36/csv','nhi':'https://info.nhi.gov.tw/api/iode0000s01/Dataset?rId=A21030000I-E41001-001'}
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'MedicationLocalReferenceImporter/1.0'})
    return urllib.request.urlopen(req,timeout=120).read()
def parts(s): return sorted(set(x.strip().upper() for x in re.split(r';;|;',s or '') if x.strip()))
def unpack_bundle():
    with zipfile.ZipFile(DEST/'public-catalog.zip') as z:
        manifest=json.loads(z.read('catalog-manifest.json'))
        for name in ['tfda.csv','nhi.csv']:
            content=z.read(name)
            expected=next(s['sha256'] for s in manifest['sources'] if s['id']==name[:-4])
            if hashlib.sha256(content).hexdigest()!=expected: raise ValueError('Public bundle checksum mismatch')
            (DEST/name).write_bytes(content)
def build(destination=None):
    dest=Path(destination) if destination else DEST
    dest.mkdir(exist_ok=True);tmp=dest/'catalog-building.sqlite'
    if tmp.exists(): tmp.unlink()
    db=sqlite3.connect(tmp);db.executescript('CREATE TABLE products(id INTEGER PRIMARY KEY,source TEXT,code TEXT,zh TEXT,en TEXT,ingredients TEXT,status TEXT,form TEXT); CREATE TABLE aliases(name TEXT,display TEXT,product INTEGER);')
    manifest={'status':'imported','importedAt':datetime.now().astimezone().isoformat(),'license':'政府資料開放授權條款第1版；來源各資料集頁面','sources':[],'clinicalRules':'Only 3 demo rules; literature not activated'}
    for source in ['tfda','nhi']:
        path=dest/(source+'.csv');count=0;unique=set()
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            expected=['許可證字號','主成分略述'] if source=='tfda' else ['藥品代號','成分']
            if not all(k in (reader.fieldnames or []) for k in expected): raise ValueError('Unexpected '+source+' columns')
            for r in reader:
                count+=1
                if source=='tfda':
                    code,zh,en,ingredients,status,form=(r.get(k,'').strip() for k in ['許可證字號','中文品名','英文品名','主成分略述','註銷狀態','劑型'])
                    status='註銷狀態：'+(status or '未標示註銷')+'；有效日期：'+r.get('有效日期','')
                else:
                    code,zh,en,ingredients,form=(r.get(k,'').strip() for k in ['藥品代號','藥品中文名稱','藥品英文名稱','成分','劑型'])
                    status='給付起迄：'+r.get('有效起日','').strip()+'–'+r.get('有效迄日','').strip()+'；'+r.get('單複方','')
                ing=parts(ingredients);signature=(code,zh,en,tuple(ing),status,form)
                if signature in unique: continue
                unique.add(signature)
                pid=db.execute('INSERT INTO products(source,code,zh,en,ingredients,status,form) VALUES(?,?,?,?,?,?,?)',(source,code,zh,en,json.dumps(ing,ensure_ascii=False),status,form)).lastrowid
                for alias in set([code,zh,en]+ing):
                    if alias: db.execute('INSERT INTO aliases VALUES(?,?,?)',(norm(alias),alias,pid))
        manifest['sources'].append({'id':source,'url':URLS[source],'datasetUrl':'https://data.gov.tw/dataset/'+('9122' if source=='tfda' else '23715'),'rawRows':count,'distinctProducts':len(unique),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fileDate':'download snapshot; not a claim of current validity'})
    db.executescript('CREATE INDEX aliases_name ON aliases(name); CREATE INDEX aliases_product ON aliases(product);');db.commit()
    manifest['productCount']=db.execute('SELECT COUNT(*) FROM products').fetchone()[0];manifest['aliasCount']=db.execute('SELECT COUNT(*) FROM aliases').fetchone()[0];db.close()
    tmp.replace(dest/'catalog.sqlite')
    (dest/'catalog-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=True))
if __name__=='__main__':
    DEST.mkdir(exist_ok=True)
    if '--from-bundle' in sys.argv:
        unpack_bundle()
    if '--download' in sys.argv:
        for source,url in URLS.items():
            raw=get(url)
            if source=='tfda':
                if raw[:2]!=b'PK': raise ValueError('TFDA download is not ZIP')
                (DEST/'tfda.zip').write_bytes(raw);z=zipfile.ZipFile(io.BytesIO(raw));content=z.read(z.namelist()[0])
            else: content=raw
            if b'<html' in content[:300].lower(): raise ValueError('Download returned HTML')
            (DEST/(source+'.csv')).write_bytes(content)
    build()
