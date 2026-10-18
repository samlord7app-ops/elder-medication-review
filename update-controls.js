'use strict';
(function(){
let checkId='',timer=null,checking=false;const el=id=>document.getElementById(id);
function status(s){el('update-status').textContent=s}
function draw(job){
 const labels={same:'相同',changed:'內容有變動',new:'本機尚未收錄',error:'檢查失敗'};el('update-items').replaceChildren();
 for(const item of job.items||[]){const label=document.createElement('label');label.className='check';const check=document.createElement('input');check.type='checkbox';check.value=item.id;check.dataset.updateSource='1';check.disabled=job.state!=='checked'||!['changed','new'].includes(item.status);const text=document.createElement('span');text.textContent=item.title+'：'+labels[item.status]+(item.message?' · '+item.message:'')+(item.status==='changed'?'（SHA-256 不同，需確認內容／版本）':'');if(item.changes){text.textContent+='；新增 '+item.changes.addedKeys+' 組、移除 '+item.changes.removedKeys+' 組、內容異動 '+item.changes.changedKeys+' 組（依藥品及生效期間等鍵分組）；列數 '+item.changes.localRows+' → '+item.changes.remoteRows}label.append(check,text);el('update-items').append(label)}
 el('check-updates').disabled=['checking','updating'].includes(job.state);el('apply-updates').disabled=job.state!=='checked'||!(job.items||[]).some(i=>['changed','new'].includes(i.status));
 if(job.state==='checking')status('正在逐一下載公開來源檢查…已完成 '+job.items.length+'／8。個案資料不會傳送。');
 else if(job.state==='checked'){const changed=job.items.filter(i=>['changed','new'].includes(i.status)).length,errors=job.items.filter(i=>i.status==='error').length;status('檢查完成：'+changed+' 項可更新，'+errors+' 項失敗。'+(errors?'失敗來源無法判斷是否最新。':'')+'請自行選擇要更新的來源；尚未修改本機資料。')}
 else if(job.state==='updating')status('正在驗證、建立新索引並備份舊版本，請暫停評估…');
 else if(job.state==='updated')status('更新完成。舊資料保存於 '+job.archive+'。請重新整理頁面，查看新目錄筆數；臨床規則未自動啟用。');
 else status(job.message||job.state);
 if(['checking','updating'].includes(job.state)){timer=setTimeout(poll,3000)}else{checking=false;timer=null}
}
async function call(path,body){const session=await fetch('/api/session',{cache:'no-store',credentials:'omit'}).then(r=>r.json());const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Local-Token':session.token},body:JSON.stringify(body),credentials:'omit',redirect:'error'});const d=await r.json();if(!r.ok)throw Error(d.error);return d}
async function poll(){try{const r=await fetch('/api/reference/check/'+checkId,{cache:'no-store',credentials:'omit'});const d=await r.json();if(!r.ok)throw Error(d.error);draw(d)}catch(e){checking=false;status('無法取得檢查狀態：'+e.message+'。請先重試取得狀態，勿重複套用更新。');el('resume-update-status').hidden=false}}
el('check-updates').onclick=async()=>{if(checking)return;checking=true;el('check-updates').disabled=true;status('開始檢查公開資料…');try{const d=await call('/api/reference/check',{});checkId=d.id;draw(d)}catch(e){checking=false;el('check-updates').disabled=false;status(e.message)}};
el('resume-update-status').onclick=()=>{if(checkId){el('resume-update-status').hidden=true;poll()}};
el('apply-updates').onclick=async()=>{const ids=[...document.querySelectorAll('[data-update-source]:checked')].map(x=>x.value);if(!ids.length)return status('請先勾選要更新的來源。');if(!window.confirm('確認更新所選 '+ids.length+' 項公開資料？舊版本將先集中備份到「已不參考」資料夾；不會更新臨床規則。'))return;el('apply-updates').disabled=true;try{const d=await call('/api/reference/update',{checkId,sources:ids});checking=true;draw(d)}catch(e){status('無法開始更新：'+e.message);el('apply-updates').disabled=false}};
fetch('/api/reference/latest',{cache:'no-store',credentials:'omit'}).then(r=>r.json()).then(d=>{if(d.id&&!checkId){checkId=d.id;checking=['checking','updating'].includes(d.state);draw(d)}}).catch(()=>{});
})();
