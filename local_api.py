"""Loopback-only import and medication review. No patient logging or external requests."""
import io, json, os, re, secrets, socket, subprocess, tempfile, zipfile, unicodedata
from difflib import get_close_matches
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import catalog
import clinical_rules as clinical
import reference_updates

ROOT = Path(__file__).resolve().parent
TOKEN = secrets.token_urlsafe(32)
PORT = 18743
ORIGIN = f'http://127.0.0.1:{PORT}'
MAX_BYTES = 10 * 1024 * 1024
ALIASES = {'diazepam':'diazepam','valium':'diazepam','zolpidem':'zolpidem','stilnox':'zolpidem', 'diphenhydramine':'diphenhydramine','metformin':'metformin'}
ALIASES.update({'lipitor':'atorvastatin','atorvastatin':'atorvastatin'})
DRUG_SOURCES = {'atorvastatin':'Lipitor = atorvastatin calcium；Pfizer 仿單 https://labeling.pfizer.com/ShowLabeling.aspx?format=PDF&id=587'}

def normalize_med(value):
    return re.sub(r'\s','',unicodedata.normalize('NFKC',value)).lower()

def suggestions(value):
    key=normalize_med(value)
    # Suggestions never resolve the ingredient or trigger a clinical rule.
    if not re.fullmatch('[a-z]{5,40}',key): return []
    matches=get_close_matches(key,sorted(ALIASES),n=3,cutoff=0.82)
    return list(dict.fromkeys(ALIASES[m] for m in matches))
PRIVACY = re.compile(r'[A-Za-z][12]\d{8}|[A-Za-z][89]\d{8}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:09\d{8})|姓名|身[份分]證|病歷|住址|電話|出生|聯絡|patient\s*name|patient\s*id|mrn',re.I)

def text(v, limit=100):
    if not isinstance(v,str) or not v.strip() or len(v)>limit or PRIVACY.search(v):
        raise ValueError('欄位格式錯誤或含疑似識別資料，請刪除個資並確認內容。')
    return v.strip()

def evaluate(p):
    if not isinstance(p,dict) or set(p) != {'age','medications','labs','diagnoses'}:
        raise ValueError('只允許 age、medications、labs、diagnoses 四種欄位。')
    age=p['age']
    if isinstance(age,bool) or not isinstance(age,int) or not 65<=age<=120:
        raise ValueError('年齡須為 65–120 歲整數。')
    for key in ['medications','labs','diagnoses']:
        if not isinstance(p[key],list) or len(p[key])>100: raise ValueError('每類最多 100 項。')
    med_models=[clinical.validate_med(m,text) for m in p['medications']]
    meds=[m['name'] for m in med_models]
    diagnoses=[text(d) for d in p['diagnoses']]
    labs=[]
    for lab in p['labs']:
        if not isinstance(lab,dict) or set(lab)!={'name','value','unit'}: raise ValueError('檢驗欄位僅允許 name/value/unit。')
        name=text(lab['name'],60);unit=text(lab['unit'],30)
        value=lab['value']
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not -1e6<=value<=1e6: raise ValueError('檢驗值須為有限數字。')
        labs.append({'name':name,'value':value,'unit':unit})
    if not meds: raise ValueError('至少需要一項已確認藥品。')
    resolved=[]
    for med in med_models:
        name=med['name'];generic=ALIASES.get(normalize_med(name)) or clinical.generic_name(name);identity=None
        if generic:
            ingredients={generic};unmapped=[];display=generic
        else:
            identity=catalog.lookup(name)
            raw=identity['ingredients'] if identity and identity.get('matched') else []
            ingredients,unmapped=clinical.components(raw);display=' + '.join(sorted(ingredients)+unmapped) or None
        route=med['route']
        if route=='unknown' and identity and identity.get('matched'):
            forms=[item['form'] for item in identity['products']]
            inferred=set()
            for form in forms:
                if re.search('外用|乳膏|軟膏|凝膠|洗劑',form):inferred.add('topical')
                elif re.search('眼用|眼藥|眼膏',form):inferred.add('ophthalmic')
                elif re.search('注射|輸注',form):inferred.add('parenteral')
                elif re.search('陰道',form):inferred.add('vaginal')
                elif re.search('口服|錠|膠囊|糖漿|內服',form):inferred.add('oral')
                else:inferred.add('unknown')
            if len(inferred)==1:route=inferred.pop()
        resolved.append({**med,'route':route,'ingredients':ingredients,'unmapped':unmapped,'display':display,'identity':identity})
    active=set().union(*(m['ingredients'] for m in resolved));approved_sources=clinical.approved_sources();results=[]
    for med in resolved:
        identity=med['identity'];display=med['display'];checks=clinical.assess(med,labs,diagnoses,active,approved_sources)
        hits=[r for r in checks if r['status']=='potential_risk'];missing=[r for r in checks if r['status'] in ['insufficient_data','source_unverified']];exceptions=[r for r in checks if r['status']=='exception_requires_review']
        state='potentially_inappropriate' if hits else 'needs_clinical_context' if missing else 'exception_requires_review' if exceptions else 'not_covered' if display and not checks else 'no_rule_hit' if display else 'ambiguous' if identity and identity.get('ambiguous') else 'unrecognized'
        reason='；'.join(r['title'] for r in hits) if hits else '缺少必要資料或此規則文獻版本未確認，不能判定。' if missing else '符合可能的適應症例外，需臨床覆核；不等同安全。' if exceptions else '已辨識成分，但目前沒有涵蓋此藥的可執行規則；不能判定適當。' if display and not checks else '僅表示已執行條件未命中；完整準則尚未實作，不能視為安全。' if display else '藥名未辨識或同名成分不一致，請核對原始處方。'
        hints=list(dict.fromkeys(suggestions(med['name'])+(identity.get('suggestions',[]) if identity else [])))[:5] if not display else []
        results.append({'input':med['name'],'ingredient':display,'catalogMatches':identity.get('products',[]) if identity else [],'suggestions':hints,'identitySource':'TFDA／健保署本機公開目錄（含歷史品項），請核對規格與途徑' if identity and identity.get('matched') else DRUG_SOURCES.get(display),'status':state,'category':'條件式用藥篩檢' if hits else None,'reason':reason,'source':'；'.join(r['id'] for r in hits) or None,'clinicalChecks':checks,'unmappedIngredients':med['unmapped'],'clinicalInput':{k:med[k] for k in ['route','dailyDoseMg','durationDays','indication','formulation']}})
    coverage=clinical.coverage()
    return {'version':clinical.VERSION,'clinicalUseReady':False,'fullAutomation':False,'results':results,'catalog':catalog.metadata(),'coverage':{k:v for k,v in coverage.items() if k!='rules'},'context':{'age':age,'labCount':len(labs),'diagnosisCount':len(diagnoses)},'limitations':['已啟用 '+str(coverage['executableRuleCount'])+' 個條件式分支；不等同三套準則完整自動判讀，尚未經機構臨床驗證。','未列出的診斷視為未知；CrCl 與 eGFR 不互相代用；檢驗時效與病史完整性需人工確認。','START 處方遺漏、未編碼條件與例外仍需人工覆核；不得依本工具自行停藥或改劑量。']}

def excel_rows(raw):
    from openpyxl import load_workbook
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist())>40*1024*1024 or len(z.infolist())>2000: raise ValueError('工作簿解壓後過大。')
    wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=False,keep_links=False)
    try:
        sheets=[];total=0
        for ws in wb.worksheets:
            if ws.sheet_state!='visible': continue
            if (ws.max_row or 0)>2001 or (ws.max_column or 0)>50:
                raise ValueError('工作表範圍過大，請先移除多餘列欄。')
            rows=[]
            for r in ws.iter_rows():
                values=[]
                for cell in r:
                    if cell.column>50: raise ValueError('最多支援 50 欄，請縮小匯入範圍。')
                    v=cell.value
                    if cell.data_type=='f': v='[公式略過，請人工輸入]'
                    values.append(str(v)[:500] if v is not None else '')
                if any(values): rows.append(values);total+=1
                if total>2000: raise ValueError('最多支援 2000 列，請先拆分工作簿。')
            sheets.append({'rows':rows}) # sheet names may contain identifiers; omit
        return {'sheets':sheets}
    finally: wb.close()

def ocr(raw):
    if os.name!='nt': raise ValueError('此 OCR 需 Windows；請使用本機已安裝的 OCR 或手動整理文字。')
    base=Path(os.environ['LOCALAPPDATA'])/'Temp'
    with tempfile.TemporaryDirectory(prefix='ya-ocr-',dir=base) as folder:
        path=Path(folder)/'image.png';path.write_bytes(raw)
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(ROOT/'windows_ocr.ps1'),str(path)],capture_output=True,timeout=60,creationflags=0x08000000)
        if result.returncode: raise ValueError('本機 OCR 無法讀取：請確認 Windows OCR 語言套件、圖片格式與大小，或改用手動輸入。')
        return json.loads(result.stdout.decode('utf-8-sig'))

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,code,data,kind='application/json; charset=utf-8'):
        body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if isinstance(data,(dict,list)) else data
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; img-src blob: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers();self.wfile.write(body)
    def valid_host(self): return self.headers.get('Host')==f'127.0.0.1:{PORT}'
    def do_GET(self):
        if not self.valid_host(): return self.send(403,{'error':'Host rejected'})
        if self.path=='/api/clinical/registry':return self.send(200,clinical.source_registry())
        if self.path=='/api/clinical/coverage':return self.send(200,clinical.coverage())
        if self.path=='/api/session': return self.send(200,{'token':TOKEN,'mode':'loopback-only'})
        if self.path=='/api/catalog':
            result=catalog.metadata()
            literature=ROOT/'public_reference'/'literature-manifest.json'
            result['literature']=json.loads(literature.read_text(encoding='utf-8')) if literature.exists() else []
            extra=ROOT/'public_reference'/'extra-manifest.json'
            result['extraReferences']=json.loads(extra.read_text(encoding='utf-8')) if extra.exists() else []
            result['localReferences']=[key for key,file in {'beers':'beers-2023-paper.pdf','stopp-start':'stopp-start-v3-appendix.pdf','pim-taiwan':'pim-taiwan-2018.txt'}.items() if (ROOT/'public_reference'/file).exists()]
            approvals=ROOT/'public_reference'/'reference-approvals.json'
            result['referenceApprovals']=json.loads(approvals.read_text(encoding='utf-8')) if approvals.exists() else []
            for approval in result['referenceApprovals']:
                path=ROOT/'public_reference'/approval['file']
                approval['currentVersionApproved']=path.exists() and reference_updates.digest(path.read_bytes())==approval['sha256']
            return self.send(200,result)
        if self.path=='/api/reference/latest':return self.send(200,reference_updates.latest() or {})
        if self.path.startswith('/api/reference/check/'):
            try:return self.send(200,reference_updates.status(self.path.rsplit('/',1)[-1]))
            except ValueError as e:return self.send(404,{'error':str(e)})
        references={'/reference/beers':'beers-2023-paper.pdf','/reference/stopp-start':'stopp-start-v3-appendix.pdf','/reference/pim-taiwan':'pim-taiwan-2018.txt'}
        if self.path in references:
            path=ROOT/'public_reference'/references[self.path]
            if not path.exists(): return self.send(404,{'error':'Reference not downloaded'})
            return self.send(200,path.read_bytes(),'application/pdf' if path.suffix=='.pdf' else 'text/plain; charset=utf-8')
        files={'/':'intake.html','/intake.html':'intake.html','/intake.js':'intake.js','/intake.css':'intake.css','/intake-core.js':'intake-core.js','/update-controls.js':'update-controls.js'}
        files['/clinical-ui.js']='clinical-ui.js'
        name=files.get(self.path)
        if not name: return self.send(404,{'error':'Not found'})
        kind='text/html; charset=utf-8' if name.endswith('html') else 'text/css; charset=utf-8' if name.endswith('css') else 'text/javascript; charset=utf-8'
        self.send(200,(ROOT/name).read_bytes(),kind)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin')!=ORIGIN or self.headers.get('X-Local-Token')!=TOKEN:
            return self.send(403,{'error':'僅接受本機工作台確認的請求。'})
        if self.path not in ['/api/extract/excel','/api/extract/image','/api/evaluate','/api/reference/check','/api/reference/update']: return self.send(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>MAX_BYTES: return self.send(413,{'error':'檔案或請求必須在 10 MB 以內。'})
            self.connection.settimeout(20)
            raw=self.rfile.read(size)
            if len(raw)!=size: raise ValueError('資料不完整。')
            if self.path=='/api/reference/check':
                if json.loads(raw)!={}:raise ValueError('檢查更新不接受任何個案資料。')
                return self.send(202,reference_updates.start_check())
            if self.path=='/api/reference/update':
                p=json.loads(raw)
                if not isinstance(p,dict) or set(p)!={'checkId','sources'} or not isinstance(p['checkId'],str):raise ValueError('更新只接受 checkId 與 sources。')
                return self.send(202,reference_updates.start_update(p['checkId'],p['sources']))
            if reference_updates.UPDATING:return self.send(409,{'error':'公開資料更新中，請完成後再評估。'})
            if self.path=='/api/extract/excel': result=excel_rows(raw)
            elif self.path=='/api/extract/image': result=ocr(raw)
            else: result=evaluate(json.loads(raw))
            self.send(200,result)
        except ValueError as e: self.send(400,{'error':str(e) if not isinstance(e,json.JSONDecodeError) else 'JSON 格式錯誤。'})
        except Exception: self.send(400,{'error':'本機處理失敗，請確認檔案格式或本機元件。原始內容不會寫入日誌。'})

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address = False
    def server_bind(self):
        if os.name=='nt': self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

if __name__=='__main__':
    if not catalog.PATH.exists() and (catalog.PATH.parent/'public-catalog.zip').exists():
        import import_public_data
        import_public_data.unpack_bundle()
        print('Building public offline catalog; this may take a few minutes.',flush=True)
        import_public_data.build()
    server=LocalServer(('127.0.0.1',PORT),Handler)
    print(f'Local-only review workstation: {ORIGIN} (Ctrl+C to stop)',flush=True)
    server.serve_forever()
