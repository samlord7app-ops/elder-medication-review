"""Opt-in drug-name-only RxNav lookup; no clinical payload, logging or disk cache."""
import json, re, time, urllib.parse, urllib.request, urllib.error
import med_strength

BASE='https://rxnav.nlm.nih.gov/REST/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def validate(p):
    if not isinstance(p,dict) or set(p)!={'medications','consent'} or p['consent'] is not True:
        raise ValueError('雲端核對只接受已確認的藥名清單及同意確認，不接受年齡、診斷、檢驗或原始資料。')
    names=p['medications']
    if not isinstance(names,list) or not 1<=len(names)<=5:raise ValueError('每次雲端核對限 1–5 個藥名。')
    for name in names:
        if not isinstance(name,str) or not 2<=len(name.strip())<=100 or '\n' in name or '\r' in name:
            raise ValueError('請只提供單行藥名，最多 100 字。')
        if re.search(r'姓名|身[份分]證|病歷|電話|住址|出生|聯絡|patient|\bmrn\b|\bid\b|[A-Za-z][1289]\d{8}|@|https?://',name,re.I):
            raise ValueError('藥名含疑似識別資料或不允許內容，整批未送出雲端。')
        if re.search(r'\d{7,}',name) and not re.fullmatch(r'[A-Z]\d{9}',name):
            raise ValueError('藥名含過長數字，整批未送出雲端。')
    return [n.strip() for n in names]

def get_json(path,deadline):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise TimeoutError()
    request=urllib.request.Request(BASE+path,headers={'User-Agent':'ElderMedicationDrugNameLookup/1.0','Accept':'application/json'})
    opener=urllib.request.build_opener(NoRedirect)
    with opener.open(request,timeout=min(8,remaining)) as response:
        if response.geturl()!=BASE+path:raise ValueError('Unexpected destination')
        raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:raise ValueError('Oversized cloud response')
    return json.loads(raw)

def lookup(p):
    names=validate(p);deadline=time.monotonic()+50;results=[]
    for name in names:
        item={'input':name,'source':'NLM RxNav / RxNorm','status':'not_found','candidates':[]};results.append(item)
        requested_strength=med_strength.parse(name)
        if not re.fullmatch(r"[A-Za-z0-9 ()\[\].,+/%'\-]+",name) or not re.search('[A-Za-z]{3}',name) or (re.fullmatch('[A-Za-z0-9]{10}',name) and re.search(r'\d{4}',name)) or re.search(r'\b(BID|TID|QID|PRN|QD|QHS|Q\d+H)\b',name,re.I):
            item.update(status='unsupported',message='此來源不適合中文、台灣代碼或整段處方。此項未送到雲端；請使用本機 TFDA／健保目錄或只保留英文藥名。');continue
        try:
            raw=get_json('approximateTerm.json?'+urllib.parse.urlencode({'term':name,'maxEntries':3,'option':1}),deadline)
            seen=set()
            for candidate in raw.get('approximateGroup',{}).get('candidate',[]):
                rxcui=candidate.get('rxcui','')
                if not re.fullmatch(r'\d{1,12}',rxcui) or rxcui in seen:continue
                seen.add(rxcui)
                if len(seen)>3:break
                time.sleep(0.12)
                props=get_json(f'rxcui/{rxcui}/properties.json',deadline).get('properties') or {}
                label=props.get('name','')
                if props.get('rxcui')!=rxcui or not isinstance(label,str) or not label or len(label)>250:continue
                if requested_strength and not med_strength.compatible(requested_strength,[label]):continue
                ingredients=[label] if props.get('tty')=='IN' else []
                if not ingredients:
                    time.sleep(0.12)
                    related=get_json(f'rxcui/{rxcui}/related.json?tty=IN',deadline)
                    for group in related.get('relatedGroup',{}).get('conceptGroup',[]):
                        if group.get('tty')=='IN':ingredients.extend(v['name'] for v in group.get('conceptProperties',[]) if isinstance(v.get('name'),str) and 0<len(v['name'])<=100)
                ingredients=list(dict.fromkeys(ingredients))[:10]
                entry={'rxcui':rxcui,'name':label,'ingredients':ingredients,'rank':str(candidate.get('rank',''))[:20],'score':str(candidate.get('score',''))[:30]}
                if not requested_strength and re.search(r'\d',name):entry['strengthMatch']='unverified'
                if requested_strength:
                    entry['strengthMatch']='matched'
                    if len(ingredients)==1:
                        brand=re.search(r'\[([^\]]+)\]',label)
                        base=brand[1] if brand else ingredients[0]
                        forms=med_strength.parse(label)['forms']
                        topical=re.search(r'\b(cream|ointment|gel)\b',label,re.I)
                        suffix=' '.join({'extended':'ER','immediate':'IR','tablet':'tablet','capsule':'capsule','injection':'injection','topical':topical[1] if topical else 'topical'}[f] for f in sorted(forms))
                        entry['suggestedName']=(base+' '+requested_strength['display']+' '+suffix).strip()
                item['candidates'].append(entry)
            item['status']='candidates' if item['candidates'] else 'not_found'
            item['message']='候選不是已確認品項，請核對成分、強度及劑型；相似度不是正確機率。'
            if requested_strength and not item['candidates']:item['message']='未找到藥名、含量與指定劑型相符的雲端候選；不會改配其他含量。請人工核對或補完整藥名。'
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            item.update(status='unavailable',message='官方雲端來源連線或回應失敗；未將錯誤內容或藥名寫入日誌。可保留資料，稍後重試。',candidates=[])
    return {'source':'https://rxnav.nlm.nih.gov','scope':'English drug-name candidates only; not Taiwan code validation or clinical assessment','results':results}
