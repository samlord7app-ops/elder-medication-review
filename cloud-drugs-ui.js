'use strict';
(()=>{
 let approvedNames=null,sourceRows=[],staging=false;
 const status=text=>{$('cloud-status').textContent=text};
 function reset(){approvedNames=null;sourceRows=[];$('cloud-consent').checked=false;$('cloud-consent').disabled=true;$('cloud-send').disabled=true;$('cloud-payload').textContent='欄位已變更，請重新建立雲端送出藥名清單。';if(!staging)$('cloud-results').replaceChildren()}
 window.addEventListener('review-invalidated',reset);
 $('cloud-preview').onclick=()=>{try{
  if(busy)throw Error('本機處理中，請稍後再建立清單。');
  sourceRows=rows.filter(r=>r.selected&&r.kind==='medication');
  if(!sourceRows.length||sourceRows.length>5)throw Error('請先在人工校對勾選 1–5 項藥品；其他欄位不會加入雲端清單。');
  const names=sourceRows.map(r=>r.value.trim());
  if(names.some(n=>!n||n.length>100||core.privacy.test(n)||/[\r\n]/.test(n)))throw Error('清單有空白、過長或疑似個資欄位，未送出。');
  approvedNames={medications:names,consent:true};$('cloud-payload').textContent=JSON.stringify({destination:'https://rxnav.nlm.nih.gov',medications:names},null,2);$('cloud-consent').checked=false;$('cloud-consent').disabled=false;$('cloud-send').disabled=true;$('cloud-results').replaceChildren();status('請先對照清單，確認全部都是藥品名稱。尚未連線查詢。');
 }catch(e){reset();status(e.message)}};
 $('cloud-consent').onchange=()=>{$('cloud-send').disabled=!approvedNames||!$('cloud-consent').checked||busy||!token};
 $('cloud-send').onclick=async()=>{
  if(!approvedNames||!$('cloud-consent').checked||busy)return;
  const revisionAtSend=revision,refs=[...sourceRows],names=[...approvedNames.medications],body={medications:names,consent:true};busy=true;$('cloud-send').disabled=true;$('cloud-preview').disabled=true;status('僅將清單中的藥名送往 NLM RxNav，正在取得候選…');
  try{
   const response=await request('/api/cloud/drugs',body);
   if(revision!==revisionAtSend)return status('核對欄位已變更，已捨棄雲端舊結果。請重新建立清單。');
   $('cloud-results').replaceChildren();
   response.results.forEach((result,index)=>{
    const box=document.createElement('div');box.className='result';const title=document.createElement('strong');title.textContent=result.input;box.append(title);const note=document.createElement('p');note.textContent=result.message||(result.candidates.length?'請核對候選。':'未找到候選，仍需人工確認。');box.append(note);
    for(const candidate of result.candidates){const line=document.createElement('p');line.textContent=`${candidate.name}｜RxCUI ${candidate.rxcui}｜成分：${candidate.ingredients.join(' + ')||'未取得'}｜相似順位 ${candidate.rank}（非正確機率）`;box.append(line);
     if(candidate.ingredients.length===1&&candidate.strengthMatch!=='unverified'){const ingredient=candidate.suggestedName||candidate.ingredients[0];const button=document.createElement('button');button.textContent=(candidate.strengthMatch?'暫選藥名與含量 ':'暫選成分 ')+ingredient;button.onclick=()=>{
      const row=refs[index];if(busy||!rows.includes(row)||row.value.trim()!==names[index])return status('原始欄位已變更，請重新核對。');
      if(ingredient.length>100||core.privacy.test(ingredient))return status('候選格式不適合直接套用，請人工核對。');
      staging=true;invalidate(true);staging=false;pendingNames.set(row,ingredient);$('batch-status').textContent='已暫選 '+pendingNames.size+' 項修正。請對照處方確認成分、強度及途徑，再按「一次套用全部藥名修正」。';status('已暫選成分，尚未改動欄位。請按第 05 區的「一次套用全部藥名修正」，再重新預覽及本機評估。');
     };box.append(button)}else{const warning=document.createElement('p');warning.textContent='複方、成分不明或含量格式未確認：不提供一鍵替換，請藥師核對所有成分、強度與劑型後在人工校對區處理。';box.append(warning)}
    }$('cloud-results').append(box);
   });status('雲端藥名候選已回傳，尚未自動套用或執行臨床評估。請核對後暫選。');
  }catch(e){status(e.message)}finally{busy=false;$('cloud-preview').disabled=false;$('cloud-consent').checked=false;$('cloud-send').disabled=true}
 };
})();
