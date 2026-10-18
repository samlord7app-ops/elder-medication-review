'use strict';
const $=id=>document.getElementById(id), core=IntakeCore;
let token='',source=null,imageURL='',sheets=[],rows=[],approved=null,busy=false,revision=0;
let currentSerialId='';
let cloudPopup=null;
const pendingNames=new Map();
const VAULT_STORAGE_KEY='elder-pii-vault-v1';
const SEQ_STORAGE_KEY='elder-serial-seq-v1';

function message(s){$('status').textContent=s}

// === 本機個資流水號加密金庫 (AES-GCM 256-bit + SHA-256) ===
function nextSerialId(){
  const d=new Date();
  const ymd=[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('');
  let seqMap={};
  try{seqMap=JSON.parse(localStorage.getItem(SEQ_STORAGE_KEY)||'{}')}catch(_){}
  const next=(seqMap[ymd]||0)+1;
  seqMap[ymd]=next;
  try{localStorage.setItem(SEQ_STORAGE_KEY,JSON.stringify(seqMap))}catch(_){}
  return `PT-${ymd}-${String(next).padStart(4,'0')}`;
}

async function deriveVaultKey(passphrase,saltBytes){
  const enc=new TextEncoder();
  const baseKey=await crypto.subtle.importKey('raw',enc.encode(passphrase||'elder-local-key'),'PBKDF2',false,['deriveKey']);
  return crypto.subtle.deriveKey(
    {name:'PBKDF2',salt:saltBytes,iterations:50000,hash:'SHA-256'},
    baseKey,
    {name:'AES-GCM',length:256},
    false,
    ['encrypt','decrypt']
  );
}

function toHex(buf){return [...new Uint8Array(buf)].map(b=>b.toString(16).padStart(2,'0')).join('')}
function fromHex(hex){const arr=new Uint8Array(hex.length/2);for(let i=0;i<arr.length;i++)arr[i]=parseInt(hex.slice(i*2,i*2+2),16);return arr}

async function encryptPiiEntry(serialId,piiObj,passphrase){
  const enc=new TextEncoder();
  const rawJson=JSON.stringify(piiObj);
  const hashBuf=await crypto.subtle.digest('SHA-256',enc.encode(`${piiObj.name||''}|${piiObj.nationalId||''}|${piiObj.mrn||''}`));
  const sha256=toHex(hashBuf).slice(0,16).toUpperCase();
  const salt=crypto.getRandomValues(new Uint8Array(12));
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const key=await deriveVaultKey(passphrase,salt);
  const cipherBuf=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,enc.encode(rawJson));
  let vault=[];
  try{vault=JSON.parse(localStorage.getItem(VAULT_STORAGE_KEY)||'[]')}catch(_){}
  vault=vault.filter(v=>v.serialId!==serialId);
  vault.unshift({
    serialId,
    createdAt:new Date().toISOString().slice(0,19).replace('T',' '),
    sha256,
    salt:toHex(salt),
    iv:toHex(iv),
    cipher:toHex(cipherBuf)
  });
  localStorage.setItem(VAULT_STORAGE_KEY,JSON.stringify(vault.slice(0,5000)));
  return {serialId,sha256};
}

async function decryptVaultList(passphrase){
  let vault=[];
  try{vault=JSON.parse(localStorage.getItem(VAULT_STORAGE_KEY)||'[]')}catch(_){}
  const dec=new TextDecoder();
  const results=[];
  for(const item of vault){
    try{
      const key=await deriveVaultKey(passphrase,fromHex(item.salt));
      const plainBuf=await crypto.subtle.decrypt({name:'AES-GCM',iv:fromHex(item.iv)},key,fromHex(item.cipher));
      const pii=JSON.parse(dec.decode(plainBuf));
      results.push({...item,decrypted:true,pii});
    }catch(_){
      results.push({...item,decrypted:false,pii:{name:'[密碼不符或加密保護中]',nationalId:'***',mrn:'***'}});
    }
  }
  return results;
}

async function renderVaultView(){
  const wrap=$('vault-table-wrap');
  if(!wrap)return;
  const pass=$('vault-unlock-pass')?.value||'elder-local-key';
  const items=await decryptVaultList(pass);
  wrap.replaceChildren();
  if(!items.length){
    $('vault-status').textContent='本機加密金庫目前尚無個資對照紀錄。';
    return;
  }
  const unlockedCount=items.filter(x=>x.decrypted).length;
  $('vault-status').textContent=`共 ${items.length} 筆加密流水號紀錄（已成功解鎖 ${unlockedCount} 筆）。此對照表僅存於本機，不會上傳雲端。`;
  const tbl=document.createElement('table');
  const trH=document.createElement('tr');
  for(const h of ['加密流水號 (serialId)','建立時間','姓名（本機解密）','身分證字號（本機解密）','病歷號（本機解密）','SHA-256 特徵雜湊']){
    const th=document.createElement('th');th.textContent=h;trH.append(th);
  }
  tbl.append(trH);
  for(const item of items){
    const tr=document.createElement('tr');
    for(const v of [item.serialId,item.createdAt,item.pii.name||'—',item.pii.nationalId||'—',item.pii.mrn||'—',item.sha256]){
      const td=document.createElement('td');td.textContent=v;tr.append(td);
    }
    tbl.append(tr);
  }
  wrap.append(tbl);
}

async function encodeCurrentSerial(autoTriggered=false){
  const name=$('pii-name')?.value.trim()||'';
  const nationalId=$('pii-id')?.value.trim()||'';
  const mrn=$('pii-mrn')?.value.trim()||'';
  const pass=$('vault-passphrase')?.value||'elder-local-key';
  if(!currentSerialId)currentSerialId=nextSerialId();
  await encryptPiiEntry(currentSerialId,{name:name||'未提供姓名（匿名個案）',nationalId,mrn},pass);
  if($('current-serial-badge'))$('current-serial-badge').textContent=currentSerialId;
  if($('record-serial-display'))$('record-serial-display').value=currentSerialId;
  if($('pii-status')){
    $('pii-status').textContent=name||nationalId||mrn
      ?`✅ 已將病人個資（姓名：${name||'無'}／證號：${nationalId?'已遮罩加密':'無'}／病歷號：${mrn||'無'}）以 AES-GCM 加密綁定至流水號 ${currentSerialId}。`
      :`✅ 已產生本機加密流水號 ${currentSerialId}（無明文個資）。`;
  }
  if(!autoTriggered)invalidate();
  return currentSerialId;
}

function populateDetectedPii(parsedRows){
  let found=0;
  for(const r of parsedRows){
    if(r.pii){
      found++;
      if(r.pii.type==='name'&&$('pii-name')&&!$('pii-name').value)$('pii-name').value=r.pii.raw;
      if(r.pii.type==='nationalId'&&$('pii-id')&&!$('pii-id').value)$('pii-id').value=r.pii.raw;
      if(r.pii.type==='mrn'&&$('pii-mrn')&&!$('pii-mrn').value)$('pii-mrn').value=r.pii.raw;
    }
  }
  if(found>0){
    encodeCurrentSerial(true);
  }
}

function selectionSummary(){
  const counts={medication:0,supplement:0,age:0,lab:0,diagnosis:0};
  for(const r of rows)if(r.selected&&r.kind in counts)counts[r.kind]++;
  $('selection-summary').textContent=`目前勾選：藥品 ${counts.medication} 項、保健食品 ${counts.supplement} 項、年齡 ${counts.age} 項、檢驗（肝腎功能等） ${counts.lab} 項、診斷 ${counts.diagnosis} 項。必須勾選至少一項藥品或保健食品。`;
  return counts;
}

function previewFeedback(text,error=false){
  const node=$('preview-feedback');
  node.textContent=text;
  node.className=error?'preview-error':'preview-success';
  node.setAttribute('role',error?'alert':'status');
  node.focus({preventScroll:true});
  node.scrollIntoView({block:'center',behavior:'smooth'});
}

function identityHints(div,result){
  if(result.strengthMatch){
    const note=document.createElement("p");
    note.className=result.strengthMatch.status==="matched"?"muted":"risk";
    note.textContent="品項含量："+result.strengthMatch.requested+"；"+result.strengthMatch.note;
    div.append(note);
  }
  if(result.catalogMatches?.length){
    const detail=document.createElement('details');
    const summary=document.createElement('summary');
    summary.textContent='查看目錄品項／歷史狀態（最多 10 筆）';
    detail.append(summary);
    for(const item of result.catalogMatches){
      const line=document.createElement('p');
      line.textContent=[item.source,item.code,item.chineseName,item.englishName,item.form,item.status].join(' · ');
      detail.append(line);
    }
    div.append(detail);
  }
  if(result.identitySource){
    const source=document.createElement('p');
    source.className='muted';
    source.textContent='辨識來源：'+result.identitySource;
    div.append(source);
  }
  for(const name of result.suggestions||[]){
    const button=document.createElement('button');
    button.textContent='選用候選 '+name;
    button.onclick=()=>{
      const candidates=rows.filter(r=>(r.kind==='medication'||r.kind==='supplement')&&r.value.trim()===result.input);
      if(candidates.length!==1)return message('候選對應不唯一，請直接在人工校對區修正藥名。');
      pendingNames.set(candidates[0],name);
      invalidate(true);
      $('batch-status').textContent='已暫選 '+pendingNames.size+' 項藥名修正，請繼續選其他藥品，最後一次套用。';
      message('已暫選 '+name+'，尚未套用或重新送出。');
    };
    div.append(button);
  }
}

function invalidate(keepResults=false){
  selectionSummary();
  $("preview-feedback").textContent="欄位已變更，核對勾選後請重新產生預覽。";
  $("preview-feedback").className="muted";
  window.dispatchEvent(new Event("review-invalidated"));
  revision++;
  approved=null;
  $('payload').textContent='資料已變更，請重新產生預覽。';
  $('confirm').checked=false;
  $('confirm').disabled=true;
  $('send').disabled=true;
  if($('open-cloud-window'))$('open-cloud-window').disabled=true;
  if(keepResults){
    $('batch-status').textContent='有待套用修正；以下為舊結果，請全部修正後重新送出。';
  }else{
    pendingNames.clear();
    $('results').textContent='等待新的確認與評估。';
    $('batch-status').textContent='可逐項選擇候選，再一次套用全部修正。';
  }
}

$('apply-names').onclick=()=>{
  if(busy)return;
  if(!pendingNames.size)return message('請先選擇要修正的候選藥名。');
  const edits=[...pendingNames].filter(([r])=>rows.includes(r));
  if(!edits.length)return message('來源已變更，請重新選擇候選。');
  if(edits.some(([,name])=>core.privacy.test(name)||!name.trim()||name.length>100))return message('候選包含疑似個資或超過 100 字，請改用人工校正。');
  if(!window.confirm('請對照原始處方，一次確認以下修正：\n'+edits.map(([r,name])=>r.value+' → '+name).join('\n')+'\n套用後仍需重新預覽並確認送出。'))return;
  for(const [r,name]of edits){r.value=name;r.selected=true}
  invalidate();
  render();
  message('已一次套用 '+edits.length+' 項藥名修正，尚未重傳；請產生預覽並統一確認。');
};

$('select-meds').onclick=()=>{
  if(busy)return;
  let count=0;
  for(const r of rows)if((r.kind==='medication'||r.kind==='supplement')&&r.value.trim()&&!core.privacy.test(r.value)){r.selected=true;count++}
  invalidate();
  render();
  message('已選取 '+count+' 項藥品／保健食品，可將不需要的項目取消勾選。');
};

$('unselect-meds').onclick=()=>{
  if(busy)return;
  rows.forEach(r=>{if(r.kind==='medication'||r.kind==='supplement')r.selected=false});
  invalidate();
  render();
  message('已取消全部藥品與保健食品選取。');
};

if($('select-all-clinical')){
  $('select-all-clinical').onclick=()=>{
    if(busy)return;
    let count=0;
    for(const r of rows){
      if(r.kind!=='skip'&&r.value.trim()&&!core.privacy.test(r.value)){
        r.selected=true;
        count++;
      }
    }
    invalidate();
    render();
    message(`已全選 ${count} 項臨床欄位（含藥品、保健食品、年齡、肝腎功能檢驗與診斷）。`);
  };
}

for(const btn of document.querySelectorAll('.quick-add')){
  btn.onclick=()=>{
    if(busy)return;
    rows.push({kind:btn.dataset.kind,value:btn.dataset.val,selected:true});
    invalidate();
    render();
    message(`已新增候選欄位：${btn.dataset.val}`);
  };
}

if($('encrypt-serial-btn')){
  $('encrypt-serial-btn').onclick=()=>encodeCurrentSerial(false);
}

if($('load-demo-case')){
  $('load-demo-case').onclick=async()=>{
    if(busy)return;
    clear();
    const demoText=[
      '姓名：王大明',
      '身分證字號：A123456789',
      '病歷號：8810293',
      '年齡：78',
      '藥品：Warfarin 5 mg',
      '藥品：Lipitor 10 mg',
      '藥品：Metformin 500 mg',
      '藥品：Zolpidem 10 mg',
      '保健食品：銀杏葉萃取物',
      '保健食品：紅麴',
      '檢驗：eGFR,38,mL/min/1.73m2',
      '檢驗：ALT,135,U/L',
      '診斷：心房顫動',
      '診斷：高血壓'
    ].join('\n');
    $('raw').value=demoText;
    rows=core.parse(demoText);
    populateDetectedPii(rows);
    for(const r of rows)if(r.kind!=='skip')r.selected=true;
    invalidate();
    render();
    message('已載入高齡處方＋保健食品＋肝腎功能＋個資示範案例！姓名、身分證與病歷號已自動提取並編碼為本機加密流水號。');
  };
}

async function request(path,body){
  const r=await fetch(path,{method:'POST',headers:{'X-Local-Token':token,'Content-Type':body instanceof Blob?'application/octet-stream':'application/json'},body:body instanceof Blob?body:JSON.stringify(body),credentials:'omit',cache:'no-store',redirect:'error'});
  const data=await r.json();
  if(!r.ok)throw Error(data.error||'本機處理失敗');
  return data;
}

function render(){
  const parent=$('candidates');
  parent.replaceChildren();
  rows.forEach((r,i)=>{
    const div=document.createElement('div');
    div.className='candidate';
    const check=document.createElement('input');
    check.type='checkbox';
    check.checked=r.selected;
    check.ariaLabel='確認這一項';
    check.onchange=()=>{r.selected=check.checked;invalidate()};
    const kind=document.createElement('select');
    for(const [k,label] of [['skip','略過'],['medication','藥品'],['supplement','保健食品'],['lab','檢驗／檢查(肝腎等)'],['diagnosis','診斷'],['age','年齡']]){
      const o=document.createElement('option');
      o.value=k;
      o.textContent=label;
      kind.append(o);
    }
    kind.value=r.kind;
    kind.onchange=()=>{r.kind=kind.value;r.selected=false;check.checked=false;invalidate();render()};
    const value=document.createElement('input');
    value.type='text';
    value.value=r.value;
    value.maxLength=200;
    value.ariaLabel='校正後的欄位值';
    value.oninput=()=>{r.value=value.value;r.selected=false;check.checked=false;invalidate()};
    const remove=document.createElement('button');
    remove.textContent='×';
    remove.ariaLabel='刪除這一項';
    remove.onclick=()=>{rows.splice(i,1);invalidate();render()};
    div.append(check,kind,value,remove);
    if(r.kind==='lab'){
      const note=document.createElement('span');
      note.className='details';
      note.textContent='格式：項目,數值,單位（例：eGFR,38,mL/min/1.73m2 或 ALT,135,U/L）';
      div.append(note);
    }
    renderClinicalFields(div,r);
    parent.append(div);
  });
}

function clear(){
  invalidate();
  source=null;
  sheets=[];
  rows=[];
  currentSerialId='';
  if($('pii-name'))$('pii-name').value='';
  if($('pii-id'))$('pii-id').value='';
  if($('pii-mrn'))$('pii-mrn').value='';
  if($('current-serial-badge'))$('current-serial-badge').textContent='尚未產生（將於預覽時自動編碼）';
  if($('record-serial-display'))$('record-serial-display').value='';
  $('raw').value='';
  $('file').value='';
  $('image').hidden=true;
  $('image').removeAttribute('src');
  if(imageURL)URL.revokeObjectURL(imageURL);
  imageURL='';
  $('sheetPanel').hidden=true;
  $('table').replaceChildren();
  $('mapping').replaceChildren();
  $('extract').disabled=true;
  render();
  message('已清除本次資料；未儲存原文或核對資料。');
}

function choose(file){
  if(busy)return message('本機處理中，請稍後再換檔。');
  if(!file)return;
  if(file.size>10*1024*1024)return message('檔案不得超過 10 MB。');
  const excel=/\.xlsx$/i.test(file.name),image=/^image\/(png|jpeg|bmp)$/.test(file.type);
  if(!excel&&!image)return message('請選擇 .xlsx 或 PNG/JPEG/BMP 圖片。');
  clear();
  source={blob:file,type:excel?'excel':'image'};
  if(image){imageURL=URL.createObjectURL(file);$('image').src=imageURL;$('image').hidden=false}
  $('extract').disabled=!token;
  message('來源已在本機載入；檔名不會傳送。請按「在本機擷取」。');
}

$('file').onchange=e=>choose(e.target.files[0]);
document.addEventListener('paste',e=>{
  const item=[...e.clipboardData.items].find(x=>x.type.startsWith('image/'));
  if(item){e.preventDefault();choose(item.getAsFile())}
});
$('clear').onclick=()=>{if(!busy)clear();else message('請等待本機處理完成後再清除。')};

$('extract').onclick=async()=>{
  if(!source||busy)return;
  busy=true;
  $('extract').disabled=true;
  message('正在本機擷取，原始內容不對外傳輸…');
  try{
    const d=await request('/api/extract/'+source.type,source.blob);
    invalidate();
    if(source.type==='image'){
      $('raw').value=d.text;
      rows=core.parse(d.text);
      populateDetectedPii(rows);
      render();
      message('OCR 完成（'+d.language+'）。個資已自動轉入加密區，請逐項對照圖片校正藥名、保健食品與檢驗值。');
    }else{
      sheets=d.sheets;
      $('sheet').replaceChildren();
      sheets.forEach((s,i)=>{
        const o=document.createElement('option');
        o.value=i;
        o.textContent='工作表 '+(i+1);
        $('sheet').append(o);
      });
      $('sheetPanel').hidden=false;
      showSheet();
      message('Excel 已於本機解析。請選擇資料欄位（藥品、保健食品、年齡、檢驗或個資加密），再產生候選。');
    }
  }catch(e){message(e.message)}finally{busy=false;$('extract').disabled=false}
};

function showSheet(){
  invalidate();
  rows=[];
  render();
  const data=sheets[Number($('sheet').value)]?.rows||[];
  const width=Math.max(0,...data.map(r=>r.length));
  $('table').replaceChildren();
  const table=document.createElement('table');
  data.slice(0,12).forEach(r=>{
    const tr=document.createElement('tr');
    r.forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});
    table.append(tr);
  });
  $('table').append(table);
  $('mapping').replaceChildren();
  for(let i=0;i<width;i++){
    const label=document.createElement('label');
    label.textContent='第 '+(i+1)+' 欄（'+(data[0]?.[i]||'無標題').slice(0,25)+'）';
    const select=document.createElement('select');
    select.dataset.column=i;
    for(const [v,t]of [
      ['skip','略過'],
      ['medication','藥品'],
      ['supplement','保健食品'],
      ['age','年齡'],
      ['diagnosis','診斷'],
      ['lab','檢驗：項目,數值,單位'],
      ['pii_name','病人姓名（轉本機流水號加密）'],
      ['pii_id','身分證字號（轉本機流水號加密）'],
      ['pii_mrn','病歷號（轉本機流水號加密）']
    ]){
      const o=document.createElement('option');
      o.value=v;
      o.textContent=t;
      select.append(o);
    }
    select.onchange=()=>{rows=[];invalidate();render()};
    label.append(select);
    $('mapping').append(label);
  }
}

$('sheet').onchange=showSheet;
$('mapRows').onclick=async()=>{
  const data=sheets[Number($('sheet').value)]?.rows||[];
  rows=[];
  let hasPii=false;
  for(const select of $('mapping').querySelectorAll('select')){
    if(select.value==='skip')continue;
    for(const r of data.slice(1)){
      const value=r[Number(select.dataset.column)]?.trim();
      if(!value)continue;
      if(select.value==='pii_name'){if($('pii-name'))$('pii-name').value=value;hasPii=true;continue}
      if(select.value==='pii_id'){if($('pii-id'))$('pii-id').value=value;hasPii=true;continue}
      if(select.value==='pii_mrn'){if($('pii-mrn'))$('pii-mrn').value=value;hasPii=true;continue}
      rows.push({
        kind:core.privacy.test(value)?'skip':select.value,
        value:core.privacy.test(value)?'[疑似識別資訊，已排除]':value,
        selected:false
      });
    }
  }
  if(hasPii)await encodeCurrentSerial(true);
  invalidate();
  render();
  message('已產生 '+rows.length+' 項候選（第一列視為標題略過）。若含個資欄位已自動編碼為本機流水號。');
};

$('raw').oninput=()=>{rows=[];invalidate();render()};
$('parse').onclick=()=>{
  rows=core.parse($('raw').value);
  populateDetectedPii(rows);
  invalidate();
  render();
  message('已產生候選並偵測個資欄位；所有臨床欄位需人工選取與校正。');
};
$('add').onclick=()=>{rows.push({kind:'skip',value:'',selected:false});invalidate();render()};

$('preview').onclick=async()=>{
  if(busy)return previewFeedback('本機處理中，請待完成後再產生預覽。',true);
  try{
    if(!rows.length)throw Error('尚未產生候選欄位。請先擷取來源，並按「由文字產生候選」或「依欄位產生候選」，再核對並勾選。');
    if(($('pii-name')?.value.trim()||$('pii-id')?.value.trim()||$('pii-mrn')?.value.trim())&&!currentSerialId){
      await encodeCurrentSerial(true);
    }
    const opts=currentSerialId?{serialId:currentSerialId}:{};
    approved=core.payload(rows,opts);
    $('payload').textContent=JSON.stringify(approved,null,2);
    $('confirm').checked=false;
    $('confirm').disabled=false;
    $('send').disabled=true;
    if($('open-cloud-window'))$('open-cloud-window').disabled=true;
    selectionSummary();
    $('preview-feedback').textContent='已成功完成去識別化並產生上傳封包預覽。請核對下方 04 區的內容，再勾選確認。';
    $('preview-feedback').className='preview-success';
    message('預覽已產生，尚未傳送。請核對 04 區 JSON，再勾選確認。');
    $('payload').focus({preventScroll:true});
    $('preview-panel').scrollIntoView({block:'start',behavior:'smooth'});
  }catch(e){
    invalidate();
    $('payload').textContent='無法產生預覽：'+e.message;
    previewFeedback(e.message,true);
    message(e.message);
  }
};

$('confirm').onchange=()=>{
  const ok=$('confirm').checked&&approved&&token&&!busy;
  $('send').disabled=!ok;
  if($('open-cloud-window'))$('open-cloud-window').disabled=!($('confirm').checked&&approved&&!busy);
};

function selectSuggestionCandidate(inputName,suggestedName){
  const candidates=rows.filter(r=>(r.kind==='medication'||r.kind==='supplement')&&r.value.trim()===inputName);
  if(candidates.length!==1)return message('候選對應不唯一，請直接在人工校對區修正藥名。');
  pendingNames.set(candidates[0],suggestedName);
  invalidate(true);
  $('batch-status').textContent='已暫選 '+pendingNames.size+' 項藥名修正，請繼續選其他藥品，最後一次套用。';
  message('已暫選 '+suggestedName+'，尚未套用或重新送出。');
}

function displayEvaluationResult(d,sourceLabel='本機與雲端同步評估'){
  if(d.serialId&&$('record-serial-display'))$('record-serial-display').value=d.serialId;
  $('results').replaceChildren(renderAnalysisTable(d.results.flatMap(r=>r.analysis||[]),d.results));
  const note=document.createElement('p');
  note.className='muted';
  note.textContent=(d.serialId?`加密流水號：${d.serialId} · `:'')+d.version+' · '+(d.limitations||[]).join(' ');
  $('results').append(note);
  window.dispatchEvent(new CustomEvent("review-evaluated",{detail:d}));
  message(`${sourceLabel}已完成回傳，可點擊表格右上角「複製臨床評估摘要」貼回處方系統，或於下方儲存至本機紀錄。`);
}

function sendPayloadToCloudFrame(payloadObj,autoEvaluate=true){
  const frame=$('cloud-ui-frame');
  if(frame&&frame.contentWindow){
    frame.contentWindow.postMessage({type:'LOCAL_DEIDENTIFIED_PAYLOAD',payload:payloadObj,autoEvaluate},'*');
  }
}

$('send').onclick=async()=>{
  if(!approved||!$('confirm').checked||busy)return;
  window.dispatchEvent(new Event("review-invalidated"));
  const rev=revision;
  const body=JSON.parse(JSON.stringify(approved));
  busy=true;
  $('send').disabled=true;
  message('正在將加密去識別化封包上傳至評估引擎與雲端高齡用藥安全評估 UI…');
  try{
    sendPayloadToCloudFrame(body,true);
    const d=await request('/api/evaluate',body);
    if(rev!==revision)return message('資料已變更，已捨棄舊結果；請重新確認。');
    displayEvaluationResult(d,'高齡用藥與保健食品安全性評估');
  }catch(e){
    message(e.message);
  }finally{
    busy=false;
    $('confirm').checked=false;
    $('send').disabled=true;
    if($('open-cloud-window'))$('open-cloud-window').disabled=true;
  }
};

if($('open-cloud-window')){
  $('open-cloud-window').onclick=()=>{
    if(!approved||!$('confirm').checked)return;
    const body=JSON.parse(JSON.stringify(approved));
    cloudPopup=window.open('/cloud-ui/index.html','ElderCloudEvalUI','width=1280,height=860');
    const timer=setInterval(()=>{
      if(!cloudPopup||cloudPopup.closed){clearInterval(timer);return}
      cloudPopup.postMessage({type:'LOCAL_DEIDENTIFIED_PAYLOAD',payload:body,autoEvaluate:true},'*');
    },600);
    setTimeout(()=>clearInterval(timer),3500);
    message('已開啟「雲端高齡病人用藥安全評估 UI」視窗並傳送加密去識別化資料。於雲端視窗點擊回傳即可自動同步回本機！');
  };
}

// 接收來自雲端高齡用藥安全評估 UI 回傳的評估結果與高度自適應
window.addEventListener('message',e=>{
  if(!e.data||typeof e.data!=='object')return;
  if(e.data.type==='CLOUD_EVAL_RESULT'&&e.data.payload){
    displayEvaluationResult(e.data.payload,'☁ 雲端高齡用藥安全評估 UI 回傳結果');
  }
  if(e.data.type==='CLOUD_UI_HEIGHT'&&typeof e.data.height==='number'){
    const frame=$('cloud-ui-frame');
    if(frame)frame.style.height=Math.max(480,e.data.height+24)+'px';
  }
});

// 金庫按鈕事件綁定
if($('vault-refresh-btn'))$('vault-refresh-btn').onclick=renderVaultView;
if($('vault-export-btn')){
  $('vault-export-btn').onclick=()=>{
    const raw=localStorage.getItem(VAULT_STORAGE_KEY)||'[]';
    const u=URL.createObjectURL(new Blob([raw],{type:'application/json'}));
    const a=document.createElement('a');
    a.href=u;
    a.download='本機加密流水號對照表備份.json';
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(()=>URL.revokeObjectURL(u),1000);
  };
}
if($('vault-clear-btn')){
  $('vault-clear-btn').onclick=()=>{
    if(window.confirm('確定要清空本機加密流水號對照表嗎？請確認已備份。')){
      localStorage.removeItem(VAULT_STORAGE_KEY);
      renderVaultView();
    }
  };
}

fetch('/api/session',{cache:'no-store',credentials:'omit',redirect:'error'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{token=d.token;message('本機服務已連線。請匯入單一個案處方／Excel／圖片，或點擊「載入高齡處方＋保健食品＋肝腎功能＋個資示範」。')}).catch(()=>message('請先啟動 local_api.py，並透過 http://127.0.0.1:18743 開啟此工作台。'));
fetch('/api/catalog',{cache:'no-store',credentials:'omit',redirect:'error'}).then(r=>r.json()).then(d=>{const section=document.createElement('section');const h=document.createElement('h2');h.textContent='本機資料庫與文獻匯入狀態';section.append(h);const text=document.createElement('p');text.className='muted';text.textContent=d.status==='imported'?`藥品目錄 ${d.productCount.toLocaleString()} 筆（含歷史異動），索引 ${d.aliasCount.toLocaleString()} 筆。匯入時間：${d.importedAt}。臨床條件篩檢（含 Beers、STOPP、PIM-Taiwan、肝腎功能及保健食品交互作用）已啟用。`:'尚未建立官方藥品索引，僅有內建高齡常用藥品與保健食品字典。';section.append(text);for(const s of d.sources||[]){const p=document.createElement('p');p.textContent=s.id.toUpperCase()+'：原始 '+s.rawRows.toLocaleString()+' 列，去重後 '+s.distinctProducts.toLocaleString()+' 筆。';section.append(p)}for(const [url,title]of [['/reference/beers','Beers 2023 本機原文 PDF'],['/reference/stopp-start','STOPP/START v3 本機準則附件'],['/reference/pim-taiwan','PIM-Taiwan 2018 本機全文（純文字）']]){const p=document.createElement('p');if((d.localReferences||[]).includes(url.split('/').pop())){const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noreferrer';a.textContent=title+((d.referenceApprovals||[]).some(r=>r.id===url.split('/').pop()&&r.currentVersionApproved)?'（已確認可匯入；部分條件已實作）':'（版本待確認）');p.append(a)}else{p.textContent=title+'：此裝置尚未下載，請執行文獻下載程式。'}section.append(p)}$('status').after(section)}).catch(()=>{});
