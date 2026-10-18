'use strict';
(function(){
  const $=id=>document.getElementById(id);
  const PRIVACY=/[A-Za-z][1289]\d{8}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|09\d{8}|姓名|身[份分]證|病歷|住址|電話|出生|聯絡|patient\s*name|patient\s*id|mrn/i;
  const VERSION='CLOUD-API-2026-10-18.3';
  const CLOUD_DB_URLS=[
    'https://samlord7app-ops.github.io/elder-medication-review/cloud-rules-db.json',
    '/cloud-ui/cloud-rules-db.json',
    './cloud-rules-db.json'
  ];

  let cachedCloudDB=null;

  const FALLBACK_GROUPS={
    benzodiazepines:'alprazolam bromazepam brotizolam chlordiazepoxide clobazam clonazepam clorazepate diazepam estazolam fludiazepam flunitrazepam flurazepam lorazepam medazepam midazolam nitrazepam nordazepam oxazepam oxazolam prazepam temazepam triazolam'.split(' '),
    zdrugs:'eszopiclone zaleplon zolpidem zopiclone'.split(' '),
    beers_zdrugs:'eszopiclone zaleplon zolpidem'.split(' '),
    first_antihistamines:'brompheniramine carbinoxamine chlorpheniramine clemastine cyproheptadine dexchlorpheniramine dimenhydrinate diphenhydramine doxylamine hydroxyzine meclizine promethazine triprolidine'.split(' '),
    strong_antidepressants:'amitriptyline amoxapine clomipramine desipramine imipramine nortriptyline paroxetine trimipramine'.split(' '),
    antipsychotics:'aripiprazole amisulpride chlorpromazine chlorprothixene clozapine flupentixol fluphenazine haloperidol levomepromazine loxapine lurasidone olanzapine paliperidone perphenazine pimozide quetiapine risperidone sulpiride thioridazine trifluoperazine ziprasidone zotepine'.split(' '),
    nsaids:'aceclofenac acemetacin alclofenac benzydamine celecoxib diclofenac diflunisal etodolac etoricoxib fenbufen fenoprofen flufenamic flurbiprofen ibuprofen indomethacin ketoprofen ketorolac mefenamic meloxicam nabumetone naproxen nimesulide piroxicam sulindac tenoxicam'.split(' '),
    ace:'benazepril captopril enalapril fosinopril imidapril lisinopril perindopril quinapril ramipril trandolapril'.split(' '),
    arb:'azilsartan candesartan eprosartan irbesartan losartan olmesartan telmisartan valsartan'.split(' '),
    beta:'acebutolol atenolol betaxolol bisoprolol carvedilol celiprolol labetalol metoprolol nadolol nebivolol pindolol propranolol sotalol timolol'.split(' '),
    anticoagulants:'warfarin acenocoumarol apixaban dabigatran edoxaban rivaroxaban'.split(' '),
    antiplatelets:'aspirin clopidogrel prasugrel ticagrelor ticlopidine cilostazol dipyridamole'.split(' '),
    ppi:'dexlansoprazole esomeprazole lansoprazole omeprazole pantoprazole rabeprazole'.split(' '),
    opioids:'buprenorphine codeine fentanyl hydrocodone hydromorphone meperidine methadone morphine oxycodone pethidine tapentadol tramadol'.split(' '),
    gabapentinoids:'gabapentin pregabalin'.split(' '),
    muscle_relaxants:'carisoprodol chlorzoxazone cyclobenzaprine metaxalone methocarbamol orphenadrine'.split(' '),
    ssri:'citalopram escitalopram fluoxetine fluvoxamine paroxetine sertraline'.split(' '),
    snri:'desvenlafaxine duloxetine milnacipran venlafaxine'.split(' '),
    loop:'bumetanide furosemide torsemide'.split(' '),
    thiazide:'bendroflumethiazide chlorothiazide chlorthalidone hydrochlorothiazide indapamide metolazone'.split(' '),
    statins:'atorvastatin fluvastatin lovastatin pitavastatin pravastatin rosuvastatin simvastatin'.split(' '),
    fluoroquinolones:'ciprofloxacin levofloxacin moxifloxacin ofloxacin norfloxacin gemifloxacin'.split(' '),
    tetracyclines:'tetracycline doxycycline minocycline'.split(' '),
    macrolides:'azithromycin clarithromycin erythromycin roxithromycin'.split(' '),
    k_sparing:'spironolactone eplerenone amiloride triamterene'.split(' '),
    sulfonylureas:'chlorpropamide glibenclamide gliclazide glimepiride glipizide glyburide tolbutamide'.split(' '),
    bleeding_supplements:'ginkgo_biloba fish_oil garlic ginseng turmeric glucosamine'.split(' '),
    mineral_chelators:'calcium iron magnesium'.split(' ')
  };

  const EXTRA_DRUG_ALIASES={
    valium:'diazepam',diazepam:'diazepam',stilnox:'zolpidem',zolpidem:'zolpidem','使蒂諾斯':'zolpidem',
    diphenhydramine:'diphenhydramine',metformin:'metformin',glucophage:'metformin','庫魯化':'metformin',
    lipitor:'atorvastatin',atorvastatin:'atorvastatin','立普妥':'atorvastatin',
    crestor:'rosuvastatin',rosuvastatin:'rosuvastatin','冠脂妥':'rosuvastatin',
    norvasc:'amlodipine',amlodipine:'amlodipine','脈優':'amlodipine',
    aspirin:'aspirin',bokey:'aspirin','伯基':'aspirin','阿斯匹靈':'aspirin',
    warfarin:'warfarin',coumadin:'warfarin','可邁丁':'warfarin',
    plavix:'clopidogrel',clopidogrel:'clopidogrel','保栓通':'clopidogrel',
    xarelto:'rivaroxaban',rivaroxaban:'rivaroxaban','拜瑞妥':'rivaroxaban',
    eliquis:'apixaban',apixaban:'apixaban','艾必克凝':'apixaban',
    lixiana:'edoxaban',edoxaban:'edoxaban','里先安':'edoxaban',
    pradaxa:'dabigatran',dabigatran:'dabigatran','普栓達':'dabigatran',
    panadol:'paracetamol',acetaminophen:'paracetamol',paracetamol:'paracetamol','普拿疼':'paracetamol',
    digoxin:'digoxin',lanoxin:'digoxin','隆我心':'digoxin',
    allopurinol:'allopurinol',spironolactone:'spironolactone',aldactone:'spironolactone',
    baclofen:'baclofen',gabapentin:'gabapentin',pregabalin:'pregabalin',lyrica:'pregabalin',
    duloxetine:'duloxetine',cymbalta:'duloxetine',ciprofloxacin:'ciprofloxacin',levofloxacin:'levofloxacin',
    doxycycline:'doxycycline',levothyroxine:'levothyroxine',eltroxin:'levothyroxine','昂特欣':'levothyroxine',
    celecoxib:'celecoxib',celebrex:'celecoxib',diclofenac:'diclofenac',voltaren:'diclofenac',
    ibuprofen:'ibuprofen',naproxen:'naproxen',ketorolac:'ketorolac',indomethacin:'indomethacin',
    glimepiride:'glimepiride',amaryl:'glimepiride',glyburide:'glyburide',glibenclamide:'glyburide',
    omeprazole:'omeprazole',esomeprazole:'esomeprazole',nexium:'esomeprazole',pantoprazole:'pantoprazole',lansoprazole:'lansoprazole',
    tramadol:'tramadol',morphine:'morphine',fentanyl:'fentanyl',codeine:'codeine',
    quetiapine:'quetiapine',seroque:'quetiapine',risperidone:'risperidone',haloperidol:'haloperidol',olanzapine:'olanzapine',
    alprazolam:'alprazolam',xanax:'alprazolam',lorazepam:'lorazepam',ativan:'lorazepam',clonazepam:'clonazepam',estazolam:'estazolam',flunitrazepam:'flunitrazepam'
  };

  async function loadCloudDB(){
    if(cachedCloudDB)return cachedCloudDB;
    for(const url of CLOUD_DB_URLS){
      try{
        const r=await fetch(url,{cache:'no-store'});
        if(r.ok){
          cachedCloudDB=await r.json();
          return cachedCloudDB;
        }
      }catch(_){}
    }
    throw Error('無法連線至雲端臨床知識庫 API (cloud-rules-db.json)。請確認網路連線。');
  }

  function expandTarget(targetExpr,groups){
    const out=new Set();
    for(const part of String(targetExpr||'').split('|')){
      const p=part.trim();
      if(!p)continue;
      if(p.startsWith('@')){
        const g=groups[p.slice(1)]||FALLBACK_GROUPS[p.slice(1)]||[];
        for(const item of g)out.add(item);
      }else{
        out.add(p);
      }
    }
    return out;
  }

  function stripStrengthAndForm(rawName){
    let s=String(rawName||'').normalize('NFKC').trim();
    s=s.replace(/\s+\d+(?:\.\d+)?(?:\s*\/\s*\d+(?:\.\d+)?)?\s*(?:mg|mcg|ug|g|ml|iu|meq|mmol|%|毫克|微克|公克|毫升|國際單位)(?:\s*\/\s*(?:ml|l|tab|cap|錠|粒|毫升))?(?:\s+(?:tab|tablet|tablets|cap|capsule|capsules|inj|injection|sr|er|xr|cr|錠|膠囊|膜衣錠|緩釋錠|持續性藥效錠|注射液))?$/i,'').trim();
    s=s.replace(/\s+(?:tab|tablet|tablets|cap|capsule|capsules|oral|錠|膠囊|膜衣錠|緩釋錠)$/i,'').trim();
    return s;
  }

  function resolveItemWithDB(rawItem,defaultType,db){
    const obj=typeof rawItem==='string'?{name:rawItem}:rawItem||{};
    const rawName=String(obj.name||'').trim();
    const cleaned=stripStrengthAndForm(rawName);
    const low=cleaned.toLowerCase();
    const compact=low.replace(/\s+/g,'');

    const medModel={
      name:rawName,
      itemType:obj.itemType||defaultType||'medication',
      route:obj.route||'oral',
      dailyDoseMg:typeof obj.dailyDoseMg==='number'&&Number.isFinite(obj.dailyDoseMg)?obj.dailyDoseMg:null,
      durationDays:typeof obj.durationDays==='number'&&Number.isFinite(obj.durationDays)?obj.durationDays:null,
      indication:obj.indication||'unknown',
      formulation:obj.formulation||'unknown'
    };

    const supplements=db.supplements||{};
    for(const [suppKey,info] of Object.entries(supplements)){
      const aliases=info.aliases||[];
      if(low===suppKey||compact===suppKey||aliases.some(a=>{
        const al=String(a).toLowerCase();
        return low===al||compact===al.replace(/\s+/g,'')||(al.length>=2&&low.includes(al));
      })){
        return {
          ...medModel,
          itemType:'supplement',
          ingredients:[suppKey],
          display:info.display||suppKey,
          identitySource:`☁ 雲端保健食品與中西藥交互作用知識庫（${info.display||suppKey}）`
        };
      }
    }

    const syn={...(db.synonyms||{}),...EXTRA_DRUG_ALIASES};
    if(syn[low]||syn[compact]){
      const k=syn[low]||syn[compact];
      return {
        ...medModel,
        ingredients:[k],
        display:k,
        identitySource:'☁ 雲端高齡藥品成分標準字典 (Cloud Medication Dictionary)'
      };
    }

    const allDrugs=new Set(db.drugs||[]);
    for(const gList of Object.values(db.groups||FALLBACK_GROUPS)){
      for(const d of gList)allDrugs.add(d);
    }
    for(const d of allDrugs){
      if(low===d||low.startsWith(d+' ')){
        return {
          ...medModel,
          ingredients:[d],
          display:d,
          identitySource:'☁ 雲端高齡藥品成分標準字典 (Cloud Medication Dictionary)'
        };
      }
    }

    return {
      ...medModel,
      ingredients:[],
      display:null,
      identitySource:null
    };
  }

  function findLabWithDB(labs,measure,db){
    const acceptedUnits={
      CrCl:['ml/min'],
      eGFR:['ml/min/1.73m2','ml/min/1.73m²','ml/min'],
      Scr:['mg/dl'],
      AST:['u/l','iu/l'],
      ALT:['u/l','iu/l'],
      TBIL:['mg/dl'],
      ChildPugh:['score','分','點','points'],
      K:['mmol/l','meq/l'],
      Na:['mmol/l','meq/l'],
      HR:['bpm','/min','次/分'],
      correctedCa:['mmol/l','mg/dl']
    }[measure]||[];
    const aliases=((db.labAliases&&db.labAliases[measure])||[measure]).map(a=>String(a).toLowerCase());
    const values=[];
    for(const lab of labs||[]){
      const lname=String(lab.name||'').trim().toLowerCase();
      if(aliases.includes(lname)){
        const unit=String(lab.unit||'').normalize('NFKC').replace(/\s+/g,'').toLowerCase();
        if(acceptedUnits.length&&!acceptedUnits.includes(unit))return null;
        const val=Number(lab.value);
        if(!Number.isFinite(val)||val<0)return null;
        values.push(val);
      }
    }
    const unique=[...new Set(values)];
    return unique.length===1?unique[0]:null;
  }

  function diagnosisStateWithDB(diagnoses,key,db){
    const known=new Set();
    const rawAliases=(db.diagnoses&&db.diagnoses[key])||[];
    const aliases=new Set([...rawAliases.map(a=>String(a).toLowerCase()),String(key).toLowerCase()]);
    for(const raw of diagnoses||[]){
      let v=String(raw||'').trim().toLowerCase();
      let negative=false;
      for(const prefix of ['無：','無:','否認：','否認:','no:','absent:']){
        if(v.startsWith(prefix)){
          negative=true;
          v=v.slice(prefix.length).trim();
          break;
        }
      }
      if(aliases.has(v))known.add(!negative);
    }
    return known.size===1?[...known][0]:null;
  }

  const COMPARE={
    '<':(a,b)=>a<b,
    '<=':(a,b)=>a<=b,
    '>':(a,b)=>a>b,
    '>=':(a,b)=>a>=b
  };

  function evaluateCondition(spec,med,labs,diagnoses,active,db){
    const [op,...args]=spec;
    if(op==='dose'||op==='duration'){
      const val=med[op==='dose'?'dailyDoseMg':'durationDays'];
      const label=op==='dose'?'每日劑量 mg/day':'療程天數';
      return val===null||val===undefined?[null,label]:[COMPARE[args[0]](val,args[1]),label];
    }
    if(op==='route'){
      return med.route==='unknown'?[null,'給藥途徑']:[args.includes(med.route),'給藥途徑'];
    }
    if(op==='indication'){
      return med.indication==='unknown'?[null,'適應症']:[args.includes(med.indication),'適應症'];
    }
    if(op==='formulation_known'){
      return med.formulation==='unknown'?[null,'速放／緩釋型態']:[true,'速放／緩釋型態'];
    }
    if(op==='lab'){
      const [name,cmp,threshold]=args;
      const val=findLabWithDB(labs,name,db);
      return val===null?[null,`${name}（指定單位且無衝突的檢驗值）`]:[COMPARE[cmp](val,threshold),name];
    }
    if(op==='diagnosis'){
      const states=args.map(k=>diagnosisStateWithDB(diagnoses,k,db));
      if(states.includes(true))return [true,args.join('／')];
      if(states.includes(null))return [null,`${args.join('／')}（明確有或無）`];
      return [false,args.join('／')];
    }
    if(op==='co'){
      const targetSet=expandTarget(args[0],db.groups||FALLBACK_GROUPS);
      const hit=[...active].some(x=>targetSet.has(x));
      return [hit,'併用藥品／保健品'];
    }
    if(op==='count'){
      const targetSet=expandTarget(args[0],db.groups||FALLBACK_GROUPS);
      const count=[...active].filter(x=>targetSet.has(x)).length;
      return [COMPARE[args[1]](count,args[2]),'併用藥品數'];
    }
    return [null,'未知條件'];
  }

  function formatCriterion(ruleId,source){
    if(source==='beers'){
      const m=ruleId.match(/^BEERS-T(\d+)/);
      return `Beers 2023${m?' 表 '+m[1]:''}（系統分支 ${ruleId}）`;
    }
    if(source==='stopp-start'){
      const m=ruleId.match(/^STOPP-([A-M]\d+)/);
      return `STOPP v3 ${m?m[1]:ruleId}（系統分支 ${ruleId}）`;
    }
    if(source==='pim-taiwan'){
      const m=ruleId.match(/^PIM-TW-T(\d+)/);
      return `PIM-Taiwan 2018${m?' 表 '+m[1]:''}（系統分支 ${ruleId}）`;
    }
    if(source==='organ-safety')return `肝腎功能劑量與禁忌篩檢（${ruleId}）`;
    if(source==='supplement-safety')return `保健食品／中西藥交互作用（${ruleId}）`;
    return `${source}（${ruleId}）`;
  }

  function buildAnalysisRows(result){
    const checks=result.clinicalChecks||[];
    const relevant=checks.filter(c=>c.status!=='not_matched');
    if(!relevant.length){
      const st=result.status;
      const riskMsg=st==='no_rule_hit'
        ?'本次處方未觸發高齡潛在不適當用藥、肝腎功能門檻或併用交互作用警示。'
        :result.reason;
      const adviceMsg=st==='no_rule_hit'
        ?'目前已檢核之條件未命中；仍請藥師結合病人完整病史與臨床狀況覆核。'
        :'請藥師確認藥品／保健食品成分、規格與適用準則，另行人工評估。';
      return [{
        drug:result.input,
        ingredient:result.ingredient||'',
        criterion:st==='no_rule_hit'?'已檢核無觸發條款':'無可對應的已執行條款',
        ruleId:'',
        source:'',
        status:st,
        risk:riskMsg,
        recommendation:adviceMsg
      }];
    }
    return relevant.map(check=>{
      const st=check.status;
      const adviceMap={
        potential_risk:'請醫師／藥師覆核必要性、適應症及個別風險，評估是否調整、錯開服用或採替代治療；勿自行停藥。',
        insufficient_data:`先補齊並確認：${(check.missing||[]).join('、')}；資料不足，尚不能判定本條款。`,
        exception_requires_review:'請醫師／藥師確認例外適應症、效益與風險，並記錄覆核理由；不等同安全。'
      };
      let advice=adviceMap[st]||'請藥師人工覆核。';
      if(check.note)advice+=` 規則補充：${check.note}`;
      return {
        drug:result.input,
        ingredient:result.ingredient||'',
        criterion:formatCriterion(check.id,check.source),
        ruleId:check.id,
        source:check.source,
        status:st,
        risk:check.title,
        recommendation:advice
      };
    });
  }

  async function evaluateInCloud(p){
    const db=await loadCloudDB();
    const meds=Array.isArray(p.medications)?p.medications:[];
    const supps=Array.isArray(p.supplements)?p.supplements:[];
    const labs=Array.isArray(p.labs)?p.labs:[];
    const diagnoses=Array.isArray(p.diagnoses)?p.diagnoses:[];
    const age=p.age!==undefined&&p.age!==null?Number(p.age):null;

    const allResolved=[
      ...meds.map(m=>resolveItemWithDB(m,'medication',db)),
      ...supps.map(s=>resolveItemWithDB(s,'supplement',db))
    ];
    const active=new Set();
    for(const item of allResolved){
      for(const ing of item.ingredients)active.add(ing);
    }

    const results=allResolved.map(med=>{
      const checks=[];
      for(const r of db.rules||[]){
        const targetSet=expandTarget(r.target,db.groups||FALLBACK_GROUPS);
        if(!med.ingredients.some(ing=>targetSet.has(ing)))continue;
        const condResults=(r.conditions||[]).map(spec=>evaluateCondition(spec,med,labs,diagnoses,active,db));
        let status='potential_risk';
        let missing=[];
        if(condResults.some(([v])=>v===false)){
          status='not_matched';
        }else if((r.exceptions||[]).includes(med.indication)){
          status='exception_requires_review';
        }else if(condResults.some(([v])=>v===null)){
          status='insufficient_data';
          missing=condResults.filter(([v])=>v===null).map(([,lbl])=>lbl);
        }
        if(age===null&&status!=='not_matched'){
          missing.push('年齡未提供，需確認符合高齡準則適用族群（65 歲以上）');
          status='insufficient_data';
        }
        checks.push({
          id:r.id,
          source:r.source,
          title:r.title,
          note:r.note||'',
          conditions:r.conditions||[],
          missing,
          status
        });
      }

      const hits=checks.filter(c=>c.status==='potential_risk');
      const missingChecks=checks.filter(c=>c.status==='insufficient_data');
      const exceptions=checks.filter(c=>c.status==='exception_requires_review');
      const display=med.display;

      const state=hits.length?'potentially_inappropriate'
        :missingChecks.length?'needs_clinical_context'
        :exceptions.length?'exception_requires_review'
        :display&&!checks.length?'not_covered'
        :display?'no_rule_hit'
        :'unrecognized';

      const reason=hits.length?hits.map(c=>c.title).join('；')
        :missingChecks.length?'缺少必要臨床資料（如特定檢驗值或療程劑量），尚不能判定。'
        :exceptions.length?'符合可能的適應症例外，需臨床覆核；不等同安全。'
        :display&&!checks.length?'已辨識成分，但目前沒有涵蓋此品項的可執行規則。'
        :display?'僅表示已執行條件未命中；完整準則仍需藥師結合病史覆核。'
        :'藥名／保健食品未辨識，請核對原始處方。';

      const resObj={
        input:med.name,
        itemType:med.itemType,
        ingredient:display,
        identitySource:med.identitySource,
        status:state,
        category:hits.length?(med.itemType==='supplement'?'保健食品交互作用篩檢':'條件式用藥篩檢'):null,
        reason,
        source:hits.map(c=>c.id).join('；')||null,
        clinicalChecks:checks,
        clinicalInput:{
          route:med.route,
          dailyDoseMg:med.dailyDoseMg,
          durationDays:med.durationDays,
          indication:med.indication,
          formulation:med.formulation
        }
      };
      resObj.analysis=buildAnalysisRows(resObj);
      return resObj;
    });

    const bySource={};
    for(const s of db.sources||['beers','stopp-start','pim-taiwan','organ-safety','supplement-safety']){
      bySource[s]=(db.rules||[]).filter(r=>r.source===s).length;
    }

    return {
      version:db.version||VERSION,
      serialId:p.serialId||null,
      sourceMode:'cloud-api',
      clinicalUseReady:false,
      fullAutomation:false,
      results,
      coverage:{
        version:db.version||VERSION,
        executableRuleCount:(db.rules||[]).length,
        activeRuleCount:(db.rules||[]).length,
        verifiedSources:db.sources||['beers','stopp-start','pim-taiwan','organ-safety','supplement-safety'],
        bySource
      },
      context:{
        serialId:p.serialId||null,
        age,
        ageProvided:age!==null,
        medicationCount:meds.length,
        supplementCount:supps.length,
        labCount:labs.length,
        diagnosisCount:diagnoses.length,
        labs,
        diagnoses
      },
      limitations:[
        `☁ 雲端臨床知識庫 API（${(db.rules||[]).length} 條規則：Beers 2023、STOPP/START v3、PIM-Taiwan 2018、肝腎功能安全與保健食品交互作用）已完成雲端比對並回傳本機；所有提示皆須藥師／醫師人工覆核。`
      ]
    };
  }

  // Expose Cloud API globally for direct or iframe invocation
  window.ElderCloudAPI={
    evaluate:evaluateInCloud,
    loadDatabase:loadCloudDB
  };

  // Below is DOM binding when running inside cloud-ui/index.html
  if(!$('cloud-json-input'))return;

  let currentPayload=null;
  let lastEvalResponse=null;
  let openerOrigin=null;

  function banner(msg,isError=false){
    const b=$('cloud-banner');
    if(!b)return;
    b.textContent=msg;
    b.className=isError?'banner error':'banner';
  }

  function renderParsedSummary(p){
    const box=$('parsed-summary');
    if(!box)return;
    box.replaceChildren();
    const grid=document.createElement('div');
    grid.className='parsed-grid';
    const cards=[
      ['加密病人流水號',p.serialId||'未附流水號（匿名）'],
      ['病人年齡',p.age!==null&&p.age!==undefined?`${p.age} 歲`:'未提供（待確認）'],
      ['西藥處方數',`${(p.medications||[]).length} 項`],
      ['保健食品數',`${(p.supplements||[]).length} 項`],
      ['肝腎與臨床檢驗',`${(p.labs||[]).length} 項`],
      ['診斷／病史',`${(p.diagnoses||[]).length} 項`]
    ];
    for(const [k,v] of cards){
      const d=document.createElement('div');
      d.className='kv-card';
      const s=document.createElement('small');s.textContent=k;
      const st=document.createElement('strong');st.textContent=v;
      d.append(s,st);
      grid.append(d);
    }
    box.append(grid);

    const addPills=(title,items,cls)=>{
      if(!items.length)return;
      const lbl=document.createElement('small');
      lbl.style.fontWeight='600';
      lbl.textContent=title+'：';
      const wrap=document.createElement('div');
      wrap.className='tag-list';
      for(const txt of items){
        const span=document.createElement('span');
        span.className='pill '+cls;
        span.textContent=txt;
        wrap.append(span);
      }
      box.append(lbl,wrap);
    };

    addPills('解析出之藥品',(p.medications||[]).map(m=>typeof m==='string'?m:m.name),'');
    addPills('解析出之保健食品',(p.supplements||[]).map(s=>typeof s==='string'?s:s.name),'supp');
    addPills('解析出之檢驗檢查值（肝腎功能／電解質）',(p.labs||[]).map(l=>`${l.name}: ${l.value} ${l.unit}`),'lab');
    addPills('解析出之診斷',(p.diagnoses||[]),'');
  }

  function validateAndParseInput(){
    const raw=$('cloud-json-input').value.trim();
    if(!raw)throw Error('請先貼上或從本機上傳去識別化 JSON 資料封包。');
    const p=JSON.parse(raw);
    if(typeof p!=='object'||!p)throw Error('JSON 頂層結構須為物件。');
    if(PRIVACY.test(raw))throw Error('偵測到疑似真實姓名、身分證字號或病歷號等隱私資訊！請先在本機端完成流水號加密去識別化。');
    p.medications=Array.isArray(p.medications)?p.medications:[];
    p.supplements=Array.isArray(p.supplements)?p.supplements:[];
    p.labs=Array.isArray(p.labs)?p.labs:[];
    p.diagnoses=Array.isArray(p.diagnoses)?p.diagnoses:[];
    if(!p.medications.length&&!p.supplements.length)throw Error('至少需包含一項藥品或保健食品。');
    currentPayload=p;
    renderParsedSummary(p);
    banner(`已成功解析上傳資料（流水號：${p.serialId||'匿名'}，藥品 ${p.medications.length} 項、保健食品 ${p.supplements.length} 項、檢驗 ${p.labs.length} 項）。`);
    return p;
  }

  function sendResultBackToLocal(resData,requestId=null){
    const msg={type:'CLOUD_EVAL_RESULT',payload:resData,requestId};
    let sent=false;
    if(window.opener&&!window.opener.closed){
      window.opener.postMessage(msg,openerOrigin||'*');
      sent=true;
    }
    if(window.parent&&window.parent!==window){
      window.parent.postMessage(msg,openerOrigin||'*');
      sent=true;
    }
    try{
      localStorage.setItem('elder-cloud-return-latest',JSON.stringify({timestamp:Date.now(),data:resData}));
      sent=true;
    }catch(_){}
    return sent;
  }

  async function runEvaluation(autoReturn=true,requestId=null){
    try{
      const p=validateAndParseInput();
      const resData=await evaluateInCloud(p);
      lastEvalResponse=resData;
      renderEvaluationResults(resData);
      $('cloud-return-btn').disabled=false;
      $('cloud-download-btn').disabled=false;
      if(autoReturn){
        sendResultBackToLocal(resData,requestId);
      }
      banner(`☁ 雲端臨床知識庫（Beers / STOPP / PIM-Taiwan / 肝腎功能 / 保健品交互作用）比對完成（流水號：${resData.serialId||'匿名'}），已同步回傳結果至本機端！`);
    }catch(e){
      banner(e.message,true);
    }
  }

  function renderEvaluationResults(data){
    const kpiBox=$('cloud-eval-summary');
    kpiBox.hidden=false;
    kpiBox.replaceChildren();
    const riskCount=data.results.filter(r=>r.status==='potentially_inappropriate').length;
    const suppCount=data.results.filter(r=>r.itemType==='supplement').length;
    const kpis=[
      ['加密流水號',data.serialId||'匿名案件'],
      ['評估總品項數',`${data.results.length} 項（含保健品 ${suppCount} 項）`],
      ['潛在不適當／交互作用警示',`${riskCount} 項需覆核`],
      ['雲端知識庫版本',data.version]
    ];
    for(const [k,v] of kpis){
      const d=document.createElement('div');
      d.className='kv-card';
      const s=document.createElement('small');s.textContent=k;
      const st=document.createElement('strong');st.textContent=v;
      d.append(s,st);
      kpiBox.append(d);
    }

    const container=$('cloud-eval-results');
    container.replaceChildren();

    const wrap=$('cloud-analysis-wrap');
    wrap.replaceChildren();
    const allRows=data.results.flatMap(r=>r.analysis||[]);
    if(allRows.length){
      const statusLabels={
        potential_risk:'⚠️ 潛在風險，需覆核',
        insufficient_data:'資料不足，不能判定',
        exception_requires_review:'可能例外，需覆核',
        no_rule_hit:'已檢核無觸發條款'
      };
      const copyBar=document.createElement('div');
      copyBar.style.cssText='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px';
      const title=document.createElement('h3');
      title.style.margin='0';
      title.textContent='藥品與保健食品不適切性分析表（雲端知識庫 API 比對結果）';
      const btnWrap=document.createElement('div');
      btnWrap.style.cssText='display:flex;gap:8px;flex-wrap:wrap;align-items:center';
      const copyStatus=document.createElement('span');
      copyStatus.className='note';
      copyStatus.style.margin='0';

      const copySummaryBtn=document.createElement('button');
      copySummaryBtn.type='button';
      copySummaryBtn.className='button primary';
      copySummaryBtn.textContent='📋 複製臨床評估摘要（貼回處方系統）';
      copySummaryBtn.onclick=async()=>{
        const riskRows=allRows.filter(r=>r.status==='potential_risk'||r.status==='potentially_inappropriate');
        const target=riskRows.length?riskRows:allRows;
        const lines=['【藥品與保健食品不適切性評估結果】'];
        target.forEach((row,idx)=>{
          lines.push(`${idx+1}. 品項：${row.drug}${row.ingredient&&row.ingredient!==row.drug?`（${row.ingredient}）`:''}`);
          lines.push(`   - 對應條款：${row.criterion}`);
          lines.push(`   - 判讀狀態：${statusLabels[row.status]||row.status}`);
          lines.push(`   - 臨床風險：${row.risk}`);
          lines.push(`   - 臨床建議：${row.recommendation}`);
        });
        try{await navigator.clipboard.writeText(lines.join('\n'))}catch(_){}
        copyStatus.textContent='✅ 已複製臨床評估摘要！可直接貼回處方系統。';
      };

      const copyTsvBtn=document.createElement('button');
      copyTsvBtn.type='button';
      copyTsvBtn.className='button secondary';
      copyTsvBtn.textContent='📑 複製完整表格內容 (Excel/Word 格式)';
      copyTsvBtn.onclick=async()=>{
        const header=['品項／成分','對應準則或交互作用條款','判讀狀態','臨床風險與機轉','臨床覆核建議'].join('\t');
        const body=allRows.map(row=>[
          `${row.drug}${row.ingredient?' ('+row.ingredient+')':''}`,
          row.criterion,
          statusLabels[row.status]||row.status,
          row.risk,
          row.recommendation
        ].map(v=>String(v??'').replace(/[\r\n\t]+/g,' ')).join('\t'));
        try{await navigator.clipboard.writeText([header,...body].join('\n'))}catch(_){}
        copyStatus.textContent='✅ 已複製完整表格內容！';
      };

      btnWrap.append(copySummaryBtn,copyTsvBtn,copyStatus);
      copyBar.append(title,btnWrap);
      wrap.append(copyBar);

      const tbl=document.createElement('table');
      const trH=document.createElement('tr');
      for(const thText of ['品項／成分','對應準則或交互作用條款','判讀狀態','臨床風險與機轉','臨床覆核建議']){
        const th=document.createElement('th');th.textContent=thText;trH.append(th);
      }
      tbl.append(trH);
      for(const row of allRows){
        const tr=document.createElement('tr');
        if(row.status==='potential_risk'||row.status==='potentially_inappropriate')tr.style.background='#fff9f6';
        for(const cell of [
          `${row.drug}${row.ingredient?' ('+row.ingredient+')':''}`,
          row.criterion,
          statusLabels[row.status]||row.status,
          row.risk,
          row.recommendation
        ]){
          const td=document.createElement('td');td.textContent=cell;tr.append(td);
        }
        tbl.append(tr);
      }
      wrap.append(tbl);
    }
  }

  $('cloud-load-demo').onclick=()=>{
    const demo={
      serialId:'PT-20261018-0001',
      age:78,
      medications:['Warfarin 5 mg','Atorvastatin 10 mg','Metformin 500 mg','Zolpidem 10 mg'],
      supplements:['銀杏葉萃取物','紅麴膠囊','鈣片'],
      labs:[
        {name:'eGFR',value:38,unit:'mL/min/1.73m2'},
        {name:'ALT',value:135,unit:'U/L'}
      ],
      diagnoses:['心房顫動','高血壓','失眠']
    };
    $('cloud-json-input').value=JSON.stringify(demo,null,2);
    validateAndParseInput();
  };

  $('cloud-file-input').onchange=async e=>{
    const file=e.target.files[0];
    if(!file)return;
    try{
      $('cloud-json-input').value=await file.text();
      validateAndParseInput();
    }catch(err){
      banner('讀取 JSON 檔案失敗：'+err.message,true);
    }finally{
      e.target.value='';
    }
  };

  $('cloud-parse-btn').onclick=()=>{
    try{validateAndParseInput();}catch(e){banner(e.message,true);}
  };

  $('cloud-eval-btn').onclick=()=>runEvaluation(true,null);

  $('cloud-return-btn').onclick=()=>{
    if(!lastEvalResponse)return;
    const sent=sendResultBackToLocal(lastEvalResponse,null);
    banner(sent?'✅ 已將雲端評估結果（流水號：'+(lastEvalResponse.serialId||'匿名')+'）回傳至本機端 UI！':'請點擊「下載評估結果 JSON」並於本機端匯入。');
  };

  $('cloud-download-btn').onclick=()=>{
    if(!lastEvalResponse)return;
    const blob=new Blob([JSON.stringify(lastEvalResponse,null,2)],{type:'application/json'});
    const u=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=u;
    a.download=`雲端評估結果-${lastEvalResponse.serialId||'anonymous'}.json`;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(()=>URL.revokeObjectURL(u),1000);
  };

  function syncFrameHeight(){
    if(window.parent&&window.parent!==window){
      const h=document.documentElement.scrollHeight;
      window.parent.postMessage({type:'CLOUD_UI_HEIGHT',height:h},'*');
    }
  }
  window.addEventListener('load',syncFrameHeight);
  window.addEventListener('resize',syncFrameHeight);
  new MutationObserver(syncFrameHeight).observe(document.body,{childList:true,subtree:true});

  window.addEventListener('message',e=>{
    if(!e.data||typeof e.data!=='object')return;
    if(e.data.type==='LOCAL_DEIDENTIFIED_PAYLOAD'&&e.data.payload){
      openerOrigin=e.origin&&e.origin!=='null'?e.origin:'*';
      $('cloud-json-input').value=JSON.stringify(e.data.payload,null,2);
      try{
        validateAndParseInput();
        if(e.data.autoEvaluate)runEvaluation(true,e.data.requestId||null);
      }catch(err){
        banner(err.message,true);
      }
    }
  });
})();
