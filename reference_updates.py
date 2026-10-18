"""User-triggered public-reference checks; no access to patient payloads."""
import copy, csv, hashlib, io, json, os, shutil, threading, time, urllib.request, uuid, zipfile
from pathlib import Path
from datetime import datetime
from import_public_data import DEST, URLS, get, build

LOCK=threading.Lock();JOBS={};UPDATING=False
SOURCES=[
 {'id':'tfda','title':'TFDA 藥品許可證','file':'tfda.csv','url':URLS['tfda'],'kind':'tfda'},
 {'id':'nhi','title':'健保署藥品品項','file':'nhi.csv','url':URLS['nhi'],'kind':'csv'},
 {'id':'beers','title':'Beers 2023 原文 PDF','file':'beers-2023-paper.pdf','url':'https://geriatrictoolkit.missouri.edu/drug/Beers-Criteria-AGS-2023.pdf','kind':'pdf'},
 {'id':'stopp','title':'STOPP/START v3 原文','file':'stopp-start-v3.xml','url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10447584/fullTextXML','kind':'xml'},
 {'id':'stopp-appendix','title':'STOPP/START v3 準則附件','file':'stopp-start-v3-appendix.pdf','url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10447584/supplementaryFiles','kind':'supplement'},
 {'id':'pim-taiwan','title':'PIM-Taiwan 2018 原文','file':'pim-taiwan-2018.xml','url':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6779000/fullTextXML','kind':'xml'},
 {'id':'lipitor','title':'DailyMed Lipitor 仿單','file':'lipitor-label.html','url':'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a60cc18b-0631-4cf0-b021-9f52224ece65','kind':'html'},
 {'id':'ocr','title':'Microsoft OCR 文件','file':'windows-ocr.html','url':'https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine?view=winrt-20348','kind':'html'}]
def digest(data):return hashlib.sha256(data).hexdigest()
def now():return datetime.now().astimezone().isoformat()
def save_report(job):
    path=DEST/'latest-check.json';tmp=DEST/'latest-check-writing.json'
    tmp.write_text(json.dumps(snapshot(job),ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def snapshot(job):
    return {k:copy.deepcopy(v) for k,v in job.items() if k!='stage'}
def csv_changes(old,new,source):
    def records(raw):
        rows={};count=0
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            count+=1
            cols=['許可證字號','中文品名','英文品名'] if source=='tfda' else ['藥品代號','有效起日','有效迄日']
            key=tuple((row.get(k) or '').strip() for k in cols)
            rows.setdefault(key,set()).add(digest(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()))
        return rows,count
    a,ac=records(old) if old else ({},0);b,bc=records(new)
    return {'localRows':ac,'remoteRows':bc,'addedKeys':len(b.keys()-a.keys()),'removedKeys':len(a.keys()-b.keys()),'changedKeys':sum(a[k]!=b[k] for k in a.keys()&b.keys())}
def status(check_id):
    with LOCK:
        if check_id not in JOBS: raise ValueError('檢查工作不存在；服務重啟後請重新檢查。')
        return snapshot(JOBS[check_id])
def latest():
    with LOCK:return snapshot(next(reversed(JOBS.values()))) if JOBS else None
def download(source):
    started=time.monotonic();chunks=[];total=0
    req=urllib.request.Request(source['url'],headers={'User-Agent':'MedicationLocalReferenceChecker/1.0'})
    with urllib.request.urlopen(req,timeout=20) as response:
        while True:
            if time.monotonic()-started>90:raise TimeoutError('此來源下載超過 90 秒，請稍後重試')
            chunk=response.read1(256*1024)
            if not chunk:break
            total+=len(chunk)
            if total>150*1024*1024:raise ValueError('公開來源檔案超過 150 MB 上限')
            chunks.append(chunk)
    data=b''.join(chunks);kind=source['kind']
    if kind in ['tfda','supplement']:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist())>200*1024*1024:raise ValueError('公開壓縮檔過大')
            name=z.namelist()[0] if kind=='tfda' else '41999_2023_777_MOESM1_ESM.pdf'
            data=z.read(name)
    if kind in ['pdf','supplement'] and not data.startswith(b'%PDF'):raise ValueError('來源未回傳 PDF')
    if kind=='xml':
        import xml.etree.ElementTree as ET
        if ET.fromstring(data).tag!='article':raise ValueError('來源未回傳論文 XML')
    if kind in ['tfda','csv']:
        text=data.decode('utf-8-sig')
        if ('許可證字號' if kind=='tfda' else '藥品代號') not in text.splitlines()[0]:raise ValueError('來源 CSV 欄位不符')
    if kind=='html' and (len(data)<1000 or b'captcha' in data[:10000].lower()):raise ValueError('來源可能回傳錯誤或驗證頁')
    return data
def start_check():
    with LOCK:
        if UPDATING or any(j['state']=='checking' for j in JOBS.values()):raise ValueError('已有檢查或更新進行中。')
        check_id=uuid.uuid4().hex;stage=DEST/'update-staging'/check_id;stage.mkdir(parents=True)
        JOBS[check_id]={'id':check_id,'state':'checking','startedAt':now(),'items':[],'stage':str(stage)}
    threading.Thread(target=run_check,args=(check_id,),daemon=True).start()
    return status(check_id)
def run_check(check_id):
    for source in SOURCES:
        item={k:source[k] for k in ['id','title','file','url']}
        try:
            data=download(source);local=DEST/source['file'];new_hash=digest(data)
            item.update(localHash=digest(local.read_bytes()) if local.exists() else None,remoteHash=new_hash,bytes=len(data))
            item['status']='new' if not local.exists() else 'same' if item['localHash']==new_hash else 'changed'
            if source['id'] in ['tfda','nhi'] and item['status']!='same':item['changes']=csv_changes(local.read_bytes() if local.exists() else None,data,source['id'])
            (Path(JOBS[check_id]['stage'])/source['file']).write_bytes(data)
        except Exception as e:item.update(status='error',message='無法檢查：'+str(e))
        with LOCK:JOBS[check_id]['items'].append(item)
    with LOCK:
        JOBS[check_id].update(state='checked',checkedAt=now());save_report(JOBS[check_id])
def start_update(check_id,ids):
    global UPDATING
    with LOCK:
        job=JOBS.get(check_id)
        if not job or job['state']!='checked' or UPDATING:raise ValueError('請先完成檢查，且不得重複套用。')
        available={i['id'] for i in job['items'] if i['status'] in ['new','changed']}
        if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or not set(ids)<=available:raise ValueError('只能選擇本次檢查有變動或新增的來源。')
        UPDATING=True;job.update(state='updating',selected=ids)
    threading.Thread(target=run_update,args=(check_id,ids),daemon=True).start()
    return status(check_id)
def run_update(check_id,ids):
    global UPDATING
    job=JOBS[check_id];stage=Path(job['stage']);archive=DEST/'已不參考'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+check_id[:8]);changed=[]
    try:
        selected=[s for s in SOURCES if s['id'] in ids]
        for s in selected:
            item=next(i for i in job['items'] if i['id']==s['id'])
            local=DEST/s['file'];old=digest(local.read_bytes()) if local.exists() else None
            if old!=item['localHash'] or digest((stage/s['file']).read_bytes())!=item['remoteHash']:raise ValueError('資料自檢查後已變動，請重新檢查。')
        files=[s['file'] for s in selected]
        if set(ids)&{'tfda','nhi'}:
            for name in ['tfda.csv','nhi.csv']:
                if name not in files:shutil.copy2(DEST/name,stage/name)
            build(stage) # complete validation and new index before replacing anything
            with zipfile.ZipFile(stage/'public-catalog.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
                for name in ['tfda.csv','nhi.csv','catalog-manifest.json']:z.write(stage/name,name)
            files+=['catalog.sqlite','catalog-manifest.json','public-catalog.zip']
        for s in selected:
            if s['kind']=='xml':
                import xml.etree.ElementTree as ET
                root=ET.parse(stage/s['file']).getroot();base=Path(s['file']).stem
                text='\n'.join(' '.join(e.itertext()) for e in root.findall('.//article-title')+root.findall('.//abstract')+root.findall('.//body')+root.findall('.//permissions'))
                (stage/(base+'.txt')).write_text(text,encoding='utf-8');files.append(base+'.txt')
                (stage/(base+'-tables.json')).write_text(json.dumps([{'id':t.get('id'),'text':' '.join(t.itertext())} for t in root.findall('.//table-wrap')],ensure_ascii=False,indent=2),encoding='utf-8');files.append(base+'-tables.json')
        for manifest_name in ['literature-manifest.json','extra-manifest.json']:
            path=DEST/manifest_name
            if not path.exists():continue
            records=json.loads(path.read_text(encoding='utf-8'));modified=False
            for record in records:
                match=next((s for s in selected if s['file']==record.get('file')),None)
                if match:
                    data=(stage/match['file']).read_bytes();record.update(status='downloaded',retrievedAt=now(),sha256=digest(data),url=match['url']);modified=True
            if modified:(stage/manifest_name).write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');files.append(manifest_name)
        record={'checkId':check_id,'updatedAt':now(),'selected':ids,'items':[i for i in job['items'] if i['id'] in ids],'note':'Only public reference files updated; clinical rules unchanged.'}
        (stage/'last-update.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');files.append('last-update.json')
        archive.mkdir(parents=True)
        # Copy all old files into a single archive before any replacement.
        existed={name:(DEST/name).exists() for name in files}
        for name in files:
            if existed[name]:shutil.copy2(DEST/name,archive/name)
        (archive/'archive-record.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            for name in files:os.replace(stage/name,DEST/name);changed.append(name)
        except Exception:
            for name in reversed(changed):
                if existed[name]:shutil.copy2(archive/name,DEST/name)
                else:(DEST/name).unlink(missing_ok=True)
            raise
        with LOCK:job.update(state='updated',updatedAt=now(),archive=str(archive.relative_to(DEST.parent)))
    except Exception as e:
        with LOCK:job.update(state='update_failed',message='更新失敗，原資料保留／已復原：'+str(e))
    finally:
        with LOCK:
            UPDATING=False
            try:save_report(job)
            except OSError:pass

def restore_report():
    path=DEST/'latest-check.json'
    if not path.exists():return
    try:
        import re
        job=json.loads(path.read_text(encoding='utf-8'));check_id=job.get('id','')
        if not re.fullmatch('[0-9a-f]{32}',check_id) or job.get('state') not in ['checked','updated','update_failed']:return
        if not isinstance(job.get('items'),list):return
        job['stage']=str(DEST/'update-staging'/check_id);JOBS[check_id]=job
    except (OSError,ValueError):pass

restore_report()
