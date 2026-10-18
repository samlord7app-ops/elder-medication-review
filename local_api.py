"""Loopback-only import and medication review. No patient logging or external requests."""
import io, json, os, re, secrets, socket, subprocess, tempfile, zipfile, unicodedata
from difflib import get_close_matches
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
RULES = {
 'diazepam': ('苯二氮平類', '高齡者可能增加認知障礙、譫妄、跌倒及骨折風險；部分適應症有例外，需臨床覆核。'),
 'zolpidem': ('非苯二氮平類安眠藥', '可能增加譫妄、跌倒、骨折及急診／住院風險，需評估效益與替代處置。'),
 'diphenhydramine': ('第一代抗組織胺（口服）', '強抗膽鹼作用可能增加混亂、口乾及便秘；須確認劑型及例外適應症。')}
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
    meds=[text(m) for m in p['medications']]
    diagnoses=[text(d) for d in p['diagnoses']]
    labs=[]
    for lab in p['labs']:
        if not isinstance(lab,dict) or set(lab)!={'name','value','unit'}: raise ValueError('檢驗欄位僅允許 name/value/unit。')
        name=text(lab['name'],60);unit=text(lab['unit'],30)
        value=lab['value']
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not -1e6<=value<=1e6: raise ValueError('檢驗值須為有限數字。')
        labs.append({'name':name,'value':value,'unit':unit})
    if not meds: raise ValueError('至少需要一項已確認藥品。')
    results=[]
    for med in meds:
        ingredient=ALIASES.get(normalize_med(med))
        rule=RULES.get(ingredient)
        results.append({'input':med,'ingredient':ingredient,'suggestions':suggestions(med) if not ingredient else [],'identitySource':DRUG_SOURCES.get(ingredient),'status':'potentially_inappropriate' if rule else 'no_rule_hit' if ingredient else 'unrecognized','category':rule[0] if rule else None,'reason':rule[1] if rule else '已辨識成分，但未命中有限示範規則；不代表用藥安全或適當。' if ingredient else '字典未收錄或拼字／OCR 有誤。請核對原始處方；相似候選不能視為已確認成分。','source':'AGS Beers 2023 Table 2（部分示範摘要）' if rule else None})
    return {'version':'DEMO-2026-10-18.2','clinicalUseReady':False,'results':results,'context':{'age':age,'labCount':len(labs),'diagnosisCount':len(diagnoses)},'limitations':['只有五種成分辨識與三項風險示範，非完整臨床引擎。','檢驗與診斷本次僅接收及驗證，尚未用於條件式判讀。','未涵蓋劑量、療程、腎功能、交互作用及全部例外；請由醫師或藥師覆核。']}

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
        if self.path=='/api/session': return self.send(200,{'token':TOKEN,'mode':'loopback-only'})
        files={'/':'intake.html','/intake.html':'intake.html','/intake.js':'intake.js','/intake.css':'intake.css','/intake-core.js':'intake-core.js'}
        name=files.get(self.path)
        if not name: return self.send(404,{'error':'Not found'})
        kind='text/html; charset=utf-8' if name.endswith('html') else 'text/css; charset=utf-8' if name.endswith('css') else 'text/javascript; charset=utf-8'
        self.send(200,(ROOT/name).read_bytes(),kind)
    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin')!=ORIGIN or self.headers.get('X-Local-Token')!=TOKEN:
            return self.send(403,{'error':'僅接受本機工作台確認的請求。'})
        if self.path not in ['/api/extract/excel','/api/extract/image','/api/evaluate']: return self.send(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<=0 or size>MAX_BYTES: return self.send(413,{'error':'檔案或請求必須在 10 MB 以內。'})
            self.connection.settimeout(20)
            raw=self.rfile.read(size)
            if len(raw)!=size: raise ValueError('資料不完整。')
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
    server=LocalServer(('127.0.0.1',PORT),Handler)
    print(f'Local-only review workstation: {ORIGIN} (Ctrl+C to stop)',flush=True)
    server.serve_forever()
