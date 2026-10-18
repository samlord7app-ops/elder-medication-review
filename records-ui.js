'use strict';
(()=>{
 const core=ReviewRecords,by=id=>document.getElementById(id),key='elder-review-records-v1';
 let records=[],pending=null,storageReady=true;
 const labels={potentially_inappropriate:'潛在不適當用藥／交互作用',needs_clinical_context:'資料不足／來源待確認',exception_requires_review:'可能例外，需覆核',not_covered:'規則未涵蓋',no_rule_hit:'條件未命中（非安全結論）',unrecognized:'未辨識',ambiguous:'品項有歧義'};
 const today=()=>{const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
 function notify(s){by('record-status').textContent=s}
 function persist(next){if(!storageReady)throw Error('既有紀錄無法讀取；請先備份或由維護者復原，避免覆蓋。');if(next.length>5000)throw Error('最多保存 5000 次評估；請先備份並依機構政策清理。');localStorage.setItem(key,JSON.stringify({format:'elder-review-records-v1',records:next}));records=next;render()}
 try{const saved=localStorage.getItem(key);if(saved)records=core.restore(JSON.parse(saved))}catch(e){storageReady=false;notify('無法讀取本機紀錄，已停止寫入以保護既有資料：'+e.message)}
 by('record-date').value=today();
 function filters(){return {from:by('filter-from').value,to:by('filter-to').value,serial:by('filter-serial')?.value.trim()||'',category:by('filter-category').value,status:by('filter-status').value,review:by('filter-review').value,drug:by('filter-drug').value.trim()}}
 function selected(){return core.select(records,filters())}
 function table(headers,rows){const t=el('table'),head=el('tr');headers.forEach(h=>head.append(el('th',h)));t.append(head);for(const row of rows){const tr=el('tr');for(const value of row){const td=el('td');if(value instanceof Node)td.append(value);else td.textContent=value;tr.append(td)}t.append(tr)}return t}
 function download(name,text,type){const u=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
 function render(){
  try{
   const list=selected(),summary=core.summarize(list);
   const rate=summary.evaluations?(summary.riskEvaluations/summary.evaluations*100).toFixed(1):'0.0';
   by('record-summary').textContent=`篩選後 ${summary.evaluations} 次評估 · ${summary.items} 個品項（含保健食品 ${summary.supplementItems||0} 項） · ${summary.riskEvaluations} 次有風險提示（${rate}%） · ${summary.riskItems} 個風險品項`;
   const kpiBox=by('record-kpis');
   if(kpiBox){
    kpiBox.replaceChildren();
    const cats=summary.categoryBreakdown||{};
    const kpiData=[
     ['區間評估總處方數',`${summary.evaluations} 筆`],
     ['潛在不適當／交互作用處方率',`${rate}% (${summary.riskEvaluations}/${summary.evaluations})`],
     ['Beers / STOPP / PIM-TW 命中',`${(cats['Beers']||0)+(cats['STOPP']||0)+(cats['PIM-Taiwan']||0)} 次`],
     ['肝腎功能安全警示數',`${cats['肝腎功能安全']||0} 次`],
     ['保健食品交互作用警示數',`${cats['保健食品交互作用']||0} 次`]
    ];
    for(const [k,v] of kpiData){
     const card=el('div');card.style.cssText='background:#f5faf7;border:1px solid #d5e6dc;border-radius:8px;padding:10px 12px';
     const sm=el('small',k);sm.style.display='block';sm.style.color='#5f786f';
     const st=el('strong',v);st.style.fontSize='16px';
     card.append(sm,st);kpiBox.append(card);
    }
   }
   by('record-groups').replaceChildren(table(['成分／藥名／保健食品','類別','出現次數','風險警示次數','未辨識／資料不足次數'],summary.groups.map(g=>[g.drug,g.itemType==='supplement'?'保健食品':'處方藥品',g.items,g.risk,g.unknown])));
   const entries=list.slice().sort((a,b)=>b.date.localeCompare(a.date)).map(r=>{
    const detail=el('details'),s=el('summary',r.items.length+' 項品項 · '+r.items.filter(i=>i.status==='potentially_inappropriate').length+' 項風險');detail.append(s);
    const analysis=r.items.flatMap(i=>(i.analysis||[]).map(a=>({...a,drug:i.name,ingredient:i.ingredient})));
    if(analysis.length){
     detail.append(renderAnalysisTable(analysis));
    }else{
     for(const i of r.items){
      const tag=i.itemType==='supplement'?'【保健食品】':'【藥品】';
      detail.append(el('p',`${tag}${i.name}${i.ingredient?' → '+i.ingredient:''}｜${labels[i.status]}：${i.reason}`));
     }
    }
    detail.append(el('small','規則版本：'+r.version+'；紀錄編號：'+r.id+(r.serialId?'；加密流水號：'+r.serialId:'')));
    const review=el('select');review.ariaLabel='覆核狀態 '+r.id;for(const value of core.reviews){const option=el('option',value);option.value=value;review.append(option)}review.value=r.review;review.onchange=()=>{try{persist(records.map(x=>x.id===r.id?{...x,review:review.value}:x));notify('覆核狀態已儲存在本機。')}catch(e){notify(e.message);render()}};
    const remove=el('button','刪除此筆');remove.onclick=()=>{if(window.confirm('只刪除此筆本機評估紀錄？請先確認已依需要備份。'))try{persist(records.filter(x=>x.id!==r.id));notify('已刪除此筆紀錄。')}catch(e){notify(e.message)}};
    return [r.date,r.serialId||'匿名未綁定',r.age??"未提供",detail,review,remove];
   });by('record-list').replaceChildren(table(['評估日期','加密流水號','年齡','藥品／保健品與規則快照','覆核狀態','操作'],entries));if(!list.length)by('record-list').append(el('p','沒有符合條件的紀錄。'));
   by('record-count').textContent='本機共 '+records.length+' 次評估；每次重評另計，不等同病人人數。';
  }catch(e){by('record-summary').textContent=e.message;by('record-groups').replaceChildren();by('record-list').replaceChildren()}
 }
 function categories(){const select=by('filter-category'),value=select.value;select.replaceChildren(el('option','全部規則類別'));select.firstChild.value='';for(const c of [...new Set(records.flatMap(r=>r.items.flatMap(i=>i.hits.map(h=>h.category))))].sort()){const option=el('option',c);option.value=c;select.append(option)}select.value=value}
 for(const [id,values]of [['filter-status',Object.entries(labels)],['filter-review',core.reviews.map(x=>[x,x])]])for(const [value,text]of values){const option=el('option',text);option.value=value;by(id).append(option)}
 for(const id of ['filter-from','filter-to','filter-serial','filter-category','filter-status','filter-review','filter-drug'])if(by(id))by(id).addEventListener('input',render);
 by('reset-filters').onclick=()=>{for(const id of ['filter-from','filter-to','filter-serial','filter-category','filter-status','filter-review','filter-drug'])if(by(id))by(id).value='';render()};
 function clearPending(){pending=null;by('save-record').disabled=true;by('record-consent').checked=false;by('save-status').textContent='完成評估後可儲存本次結果。'}
 window.addEventListener('review-invalidated',clearPending);
 window.addEventListener('review-evaluated',event=>{try{pending=core.snapshot(event.detail,today(),crypto.randomUUID());by('record-date').value=today();if(by('record-serial-display'))by('record-serial-display').value=pending.serialId||'';by('record-consent').checked=false;by('save-record').disabled=true;by('save-status').textContent='評估完成。確認日期與本機保存內容後，可儲存本次結果。'}catch(e){clearPending();by('save-status').textContent=e.message}});
 by('record-consent').onchange=()=>{by('save-record').disabled=!pending||!by('record-consent').checked||!storageReady};
 by('save-record').onclick=()=>{try{if(!pending||!by('record-consent').checked)return;const serialVal=by('record-serial-display')?.value.trim()||pending.serialId;const nextObj={...pending,date:by('record-date').value};if(serialVal)nextObj.serialId=serialVal;const record=core.checked(nextObj);persist([...records,record]);categories();clearPending();by('save-status').textContent='已儲存至本機紀錄，可前往「02 評估紀錄、區間搜尋與評鑑彙整統計」查看。同一份結果不會重複儲存。';notify('已新增評估紀錄。')}catch(e){by('save-status').textContent='未儲存：'+e.message}};
 by('export-details').onclick=()=>{try{const rows=[['評估編號','加密流水號','日期','年齡','覆核狀態','類型','品項名稱','辨識成分','評估狀態','原因','規則類別','命中規則','品項含量核對','規則版本']];for(const r of selected())for(const i of r.items)rows.push([r.id,r.serialId||'匿名',r.date,r.age??"未提供",r.review,i.itemType==='supplement'?'保健食品':'藥品',i.name,i.ingredient,labels[i.status],i.reason,[...new Set(i.hits.map(h=>h.category))].join('；'),i.hits.map(h=>h.id).join('；'),i.strengthMatch?i.strengthMatch.requested+'；'+i.strengthMatch.note:'未提供品項含量',r.version]);download('用藥與保健品評估明細-'+today()+'.csv',core.csv(rows),'text/csv;charset=utf-8');notify('已匯出目前篩選條件內的明細。')}catch(e){notify(e.message)}};
 by('export-summary').onclick=()=>{try{const f=filters(),s=core.summarize(selected());const cats=s.categoryBreakdown||{};download('評鑑用藥彙整統計-'+today()+'.csv',core.csv([['起日','迄日','流水號篩選','規則類別','藥品篩選','結果篩選','覆核篩選','評估總處方數','有風險處方數','風險處方比率(%)','總品項數','保健食品項目數','風險品項數','Beers命中數','STOPP命中數','PIM-Taiwan命中數','肝腎功能安全命中數','保健食品交互作用命中數'],[f.from,f.to,f.serial,f.category,f.drug,f.status,f.review,s.evaluations,s.riskEvaluations,s.evaluations?(s.riskEvaluations/s.evaluations*100).toFixed(1):'0.0',s.items,s.supplementItems||0,s.riskItems,cats['Beers']||0,cats['STOPP']||0,cats['PIM-Taiwan']||0,cats['肝腎功能安全']||0,cats['保健食品交互作用']||0],[],['成分／藥名／保健食品','類型','品項出現數','風險項目數','未辨識／資料不足項目數'],...s.groups.map(g=>[g.drug,g.itemType==='supplement'?'保健食品':'藥品',g.items,g.risk,g.unknown])]),'text/csv;charset=utf-8');notify('已匯出評鑑彙整統計報表。')}catch(e){notify(e.message)}};
 by('export-analysis').onclick=()=>{try{const rows=[['評估日期','評估編號','加密流水號','年齡','覆核狀態','品項','成分','對應條款','系統分支','判讀狀態','臨床風險／主題','建議','規則版本']];for(const r of selected())for(const i of r.items){const analysis=i.analysis?.length?i.analysis:[{criterion:i.hits.map(h=>h.source).join('；')||'舊版無條款快照',ruleId:i.hits.map(h=>h.id).join('；'),status:i.status,risk:i.reason,recommendation:'舊版紀錄，請人工覆核原始規則。'}];for(const a of analysis)rows.push([r.date,r.id,r.serialId||'匿名',r.age??"未提供",r.review,i.name,i.ingredient,a.criterion,a.ruleId,a.status,a.risk,a.recommendation+(i.strengthMatch?' 品項含量核對：'+i.strengthMatch.requested+'；'+i.strengthMatch.note:''),r.version])}download('藥品與保健品不適切性分析表-'+today()+'.csv',core.csv(rows),'text/csv;charset=utf-8');notify('已匯出目前篩選範圍的藥品與保健品不適切性分析表。')}catch(e){notify(e.message)}};
 by('backup-records').onclick=()=>{if(!storageReady)return notify('請先復原無法讀取的本機紀錄。');download('本機評估備份-'+today()+'.json',JSON.stringify({format:'elder-review-records-v1',records},null,2),'application/json');notify('已下載全部紀錄備份，請保存在未同步的安全位置。')};
 by('restore-records').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>20*1024*1024)throw Error('備份最多 20 MB。');const data=JSON.parse(await file.text());if(data&&Array.isArray(data.results)&&data.context){const snap=core.snapshot(data,today(),crypto.randomUUID());persist([...records,snap]);categories();render();notify('已直接匯入單筆雲端高齡用藥評估結果 JSON！');return;}const imported=data.format===1?core.legacy(data):core.restore(data);const existing=new Set(records.map(r=>r.id)),fresh=imported.filter(r=>{if(existing.has(r.id))return false;existing.add(r.id);return true});if(!fresh.length)return notify('沒有可新增的紀錄，重複編號已略過。');if(!window.confirm(`將新增 ${fresh.length} 次評估至本機，既有紀錄保留。舊版紀錄不會重新套用新版規則。請確認此檔不含病人識別資料。`))return;persist([...records,...fresh]);categories();render();notify('已匯入 '+fresh.length+' 次評估；未上傳檔案或內容。')}catch(error){notify('未匯入：'+error.message)}finally{e.target.value=''}};
 for(const button of document.querySelectorAll('[data-workspace]'))button.onclick=()=>{const target=button.dataset.workspace;by('evaluation-view').hidden=target!=='evaluation';by('records-view').hidden=target!=='records';if(by('vault-view'))by('vault-view').hidden=target!=='vault';for(const b of document.querySelectorAll('[data-workspace]'))b.setAttribute('aria-pressed',String(b===button));if(target==='records'){categories();render()}if(target==='vault'&&typeof renderVaultView==='function'){renderVaultView()}window.scrollTo(0,0)};
 window.addEventListener('storage',e=>{if(e.key===key){storageReady=false;by('save-record').disabled=true;notify('其他分頁已變更紀錄，請重新整理本頁再操作，避免覆蓋。')}});
 categories();render();
})();
