(function(root){
const privacy=/[A-Za-z][1289]\d{8}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|09\d{8}|姓名|身[份分]證|病歷|住址|電話|出生|聯絡|patient\s*name|patient\s*id|mrn/i;
const serialPattern=/^PT-\d{8}-\d{4}(?:-[A-Z0-9]{4,8})?$/;

function extractPrivacyFields(line){
  const s=line.trim();
  let m;
  if(m=s.match(/^(?:姓名|病人姓名|患者姓名|patient\s*name)\s*[:：]?\s*(.+)$/i))return {type:'name',label:'姓名',raw:m[1].trim()};
  if(m=s.match(/^(?:身[份分]證(?:字號|號)?|id|national\s*id)\s*[:：]?\s*([A-Za-z][1289]\d{8})$/i))return {type:'nationalId',label:'身分證字號',raw:m[1].trim()};
  if(m=s.match(/\b([A-Za-z][1289]\d{8})\b/))return {type:'nationalId',label:'身分證字號',raw:m[1].trim()};
  if(m=s.match(/^(?:病歷號(?:碼)?|病歷|mrn|chart\s*no|patient\s*id)\s*[:：]?\s*([A-Za-z0-9_-]+)$/i))return {type:'mrn',label:'病歷號',raw:m[1].trim()};
  if(privacy.test(s))return {type:'other_pii',label:'其他疑似個資',raw:s};
  return null;
}

function parse(raw){
  return raw.split(/\r?\n/).filter(x=>x.trim()).map(line=>{
    const s=line.trim();
    const pii=extractPrivacyFields(s);
    if(pii)return {kind:'skip',value:'[疑似識別資訊，已排除]',selected:false,pii};
    let m;
    if(m=s.match(/^(?:年齡|age)\s*[:：]?\s*(\d{1,3})\s*(?:歲)?$/i))return {kind:'age',value:m[1],selected:false};
    if(m=s.match(/^(?:保健食品|保健品|營養品|健康食品|supplement)\s*[:：]\s*(.+)$/i))return {kind:'supplement',value:m[1].trim(),selected:false};
    if(m=s.match(/^(?:藥品|用藥|處方|medication|drug)\s*[:：]\s*(.+)$/i))return {kind:'medication',value:m[1].trim(),selected:false};
    if(m=s.match(/^(?:診斷|疾病|病史|diagnosis)\s*[:：]\s*(.+)$/i))return {kind:'diagnosis',value:m[1].trim(),selected:false};
    if(m=s.match(/^(?:檢驗|檢查|肝腎功能|腎功能|肝功能|lab)\s*[:：]\s*(.+)$/i))return {kind:'lab',value:m[1].trim(),selected:false};
    return {kind:'skip',value:s,selected:false};
  });
}

function medication(name,details){
  if(!details||!Object.values(details).some(v=>v!==null&&v!==undefined&&v!==''&&v!=='unknown'))return name;
  const med={name};
  for(const k of ['dailyDoseMg','durationDays'])if(details[k]!==null&&details[k]!==undefined){
    if(typeof details[k]!=='number'||!Number.isFinite(details[k])||details[k]<0||details[k]>1e6)throw Error('每日劑量／療程格式錯誤。');
    med[k]=details[k];
  }
  for(const [key,allowed]of [
    ['route',['unknown','oral','parenteral','topical','ophthalmic','vaginal','transdermal','sublingual','inhaled']],
    ['formulation',['unknown','immediate_release','extended_release']],
    ['indication',['unknown','insomnia','hypertension','atrial_fibrillation','heart_failure','epilepsy','severe_anxiety','alcohol_withdrawal','rem_sleep_behavior','procedural','schizophrenia','bipolar','primary_prevention','secondary_prevention','gastroprotection','erosive_esophagitis','barrett','zollinger_ellison','other']]
  ])if(details[key]){
    if(!allowed.includes(details[key]))throw Error('藥品臨床欄位格式錯誤。');
    med[key]=details[key];
  }
  return med;
}

function payload(rows,options={}){
  const p={age:null,medications:[],labs:[],diagnoses:[]};
  const supplements=[];
  let ages=0;
  for(const row of rows.filter(r=>r.selected&&r.kind!=='skip')){
    const s=row.value.trim();
    if(!s||s.length>200||privacy.test(s))throw Error('所選欄位為空、過長或含疑似個資，請修正。');
    if(row.kind==='age'){
      if(!/^\d+$/.test(s)||+s<65||+s>120)throw Error('年齡需為 65–120 歲整數。');
      p.age=+s;
      ages++;
    }else if(row.kind==='medication'){
      if(s.length>100)throw Error('藥名最多 100 字。');
      p.medications.push(medication(s,row.clinical));
    }else if(row.kind==='supplement'){
      if(s.length>100)throw Error('保健食品名稱最多 100 字。');
      supplements.push(medication(s,row.clinical));
    }else if(row.kind==='diagnosis'){
      if(s.length>100)throw Error('診斷最多 100 字。');
      p.diagnoses.push(s);
    }else if(row.kind==='lab'){
      const parts=s.split(/[,，\t]/).map(x=>x.trim());
      if(parts.length!==3||!parts[0]||!parts[2]||!parts[1]||!Number.isFinite(Number(parts[1])))throw Error('檢驗格式：項目,數值,單位。例如 eGFR,45,mL/min/1.73m2 或 ALT,135,U/L');
      if(parts[0].length>60||parts[2].length>30||Math.abs(Number(parts[1]))>1e6)throw Error('檢驗欄位超出允許範圍。');
      p.labs.push({name:parts[0],value:Number(parts[1]),unit:parts[2]});
    }else throw Error('不支援的欄位類型。');
  }
  if(ages>1)throw Error('已勾選多個年齡。每次僅能評估一位個案，請只保留一個年齡。');
  if(!p.medications.length&&!supplements.length)throw Error('請至少確認一項藥品或保健食品。');
  if(supplements.length)p.supplements=supplements;
  if(options.serialId){
    if(!serialPattern.test(options.serialId))throw Error('加密流水號格式錯誤。');
    p.serialId=options.serialId;
  }
  if(Object.values(p).some(v=>Array.isArray(v)&&v.length>100))throw Error('每類最多 100 項。');
  return p;
}

const api={privacy,serialPattern,extractPrivacyFields,parse,payload};
if(typeof module!=='undefined')module.exports=api;else root.IntakeCore=api;
})(globalThis);
