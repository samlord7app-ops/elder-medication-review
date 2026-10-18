'use strict';
(function(){
  const $=id=>document.getElementById(id);
  const PRIVACY=/[A-Za-z][1289]\d{8}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|09\d{8}|姓名|身[份分]證|病歷|住址|電話|出生|聯絡|patient\s*name|patient\s*id|mrn/i;
  const VERSION='CLOUD-CLINICAL-2026-10-18.2';

  const GROUPS={
    benzodiazepines:'alprazolam bromazepam brotizolam chlordiazepoxide clobazam clonazepam clorazepate diazepam estazolam fludiazepam flunitrazepam flurazepam lorazepam medazepam midazolam nitrazepam nordazepam oxazepam oxazolam prazepam temazepam triazolam'.split(' '),
    zdrugs:'eszopiclone zaleplon zolpidem zopiclone'.split(' '),
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
    k_sparing:'spironolactone eplerenone amiloride triamterene'.split(' '),
    sulfonylureas:'chlorpropamide glibenclamide gliclazide glimepiride glipizide glyburide tolbutamide'.split(' '),
    bleeding_supplements:'ginkgo_biloba fish_oil garlic ginseng turmeric glucosamine'.split(' '),
    mineral_chelators:'calcium iron magnesium'.split(' ')
  };
  GROUPS.cns=[...new Set([...GROUPS.benzodiazepines,...GROUPS.zdrugs,...GROUPS.strong_antidepressants,...GROUPS.antipsychotics,...GROUPS.opioids,...GROUPS.gabapentinoids,...GROUPS.ssri,...GROUPS.snri,...GROUPS.muscle_relaxants])];
  GROUPS.anticholinergic=[...new Set([...GROUPS.first_antihistamines,...GROUPS.strong_antidepressants,'benztropine','trihexyphenidyl','oxybutynin','tolterodine','solifenacin','flavoxate'])];
  GROUPS.antihypertensives=[...new Set([...GROUPS.ace,...GROUPS.arb,...GROUPS.beta,...GROUPS.loop,...GROUPS.thiazide,'amlodipine','nifedipine','felodipine','lercanidipine','diltiazem','verapamil','doxazosin','terazosin','prazosin'])];
  GROUPS.antidiabetics=[...new Set([...GROUPS.sulfonylureas,'metformin','insulin','pioglitazone','rosiglitazone','sitagliptin','linagliptin','vildagliptin','empagliflozin','dapagliflozin','acarbose','repaglinide'])];

  const SUPPLEMENTS={
    ginkgo_biloba:{display:'銀杏葉萃取物 (Ginkgo biloba)',aliases:['銀杏','銀杏葉','銀杏葉萃取物','銀杏果','ginkgo','ginkgo biloba','循利寧','cerenin']},
    red_yeast_rice:{display:'紅麴 (Red yeast rice / Monacolin K)',aliases:['紅麴','紅麴膠囊','紅麴菌','壽美降脂','red yeast rice','monacolin k','monascus']},
    fish_oil:{display:'魚油 / Omega-3 (Fish oil)',aliases:['魚油','深海魚油','omega-3','omega 3','omega3','fish oil','epa','dha']},
    st_johns_wort:{display:"聖約翰草 / 貫葉連翹 (St. John's Wort)",aliases:['聖約翰草','貫葉連翹','金絲桃',"st. john's wort",'st johns wort','hypericum']},
    ginseng:{display:'人參 / 西洋參 (Ginseng)',aliases:['人參','人蔘','高麗參','高麗蔘','西洋參','花旗參','粉光參','紅參','ginseng','panax ginseng']},
    calcium:{display:'鈣片 / 鈣補充劑 (Calcium)',aliases:['鈣','鈣片','碳酸鈣','檸檬酸鈣','海藻鈣','挺立','calcium','calcium carbonate','calcium citrate']},
    iron:{display:'鐵劑 / 鐵補充劑 (Iron)',aliases:['鐵','鐵劑','補鐵','硫酸亞鐵','富馬酸亞鐵','iron','ferrous sulfate','ferrous fumarate']},
    magnesium:{display:'鎂補充劑 / 氧化鎂 (Magnesium)',aliases:['鎂','鎂片','氧化鎂','檸檬酸鎂','甘胺酸鎂','magnesium','magnesium oxide','mgo']},
    vitamin_k:{display:'維生素 K / 納豆激酶 (Vitamin K / Natto)',aliases:['維生素k','維他命k','維生素k2','納豆','納豆激酶','納豆紅麴','vitamin k','vitamin k1','vitamin k2','natto','nattokinase']},
    coq10:{display:'輔酶 Q10 (Coenzyme Q10)',aliases:['輔酶q10','q10','coq10','coenzyme q10','ubiquinone','ubiquinol']},
    garlic:{display:'大蒜精 / 蒜頭萃取物 (Garlic extract)',aliases:['大蒜精','大蒜萃取物','蒜精','黑蒜精','garlic','garlic extract','allicin']},
    turmeric:{display:'薑黃素 (Turmeric / Curcumin)',aliases:['薑黃','薑黃素','秋薑黃','紅薑黃','turmeric','curcumin']},
    glucosamine:{display:'葡萄糖胺 (Glucosamine)',aliases:['葡萄糖胺','維骨力','固樂沙敏','glucosamine','glucosamine sulfate']},
    potassium_supp:{display:'鉀補充劑 / 低鈉鹽 (Potassium supplement)',aliases:['鉀補充劑','鉀片','低鈉鹽','代鹽','potassium supplement','potassium chloride']},
    licorice:{display:'甘草萃取物 (Licorice)',aliases:['甘草','甘草錠','甘草萃取','licorice','glycyrrhiza']},
    melatonin:{display:'褪黑激素 (Melatonin)',aliases:['褪黑激素','melatonin']},
    vitamin_d:{display:'維生素 D (Vitamin D)',aliases:['維生素d','維他命d','維生素d3','vitamin d','vitamin d3']},
    vitamin_b:{display:'維生素 B 群 (Vitamin B complex)',aliases:['維生素b','維生素b群','維他命b群','b群','合利他命','vitamin b','b complex']},
    lutein:{display:'葉黃素 (Lutein)',aliases:['葉黃素','游離型葉黃素','lutein']},
    probiotics:{display:'益生菌 (Probiotics)',aliases:['益生菌','乳酸菌','probiotics']}
  };

  const DRUG_ALIASES={
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

  function resolveItem(rawName,defaultType='medication'){
    const clean=String(rawName||'').replace(/\s+\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|iu|毫克|微克|公克).*$/i,'').trim();
    const low=clean.toLowerCase();
    for(const [k,info] of Object.entries(SUPPLEMENTS)){
      if(low===k||info.aliases.some(a=>low===a.toLowerCase()||(a.length>=2&&low.includes(a.toLowerCase())))){
        return {key:k,display:info.display,itemType:'supplement',source:'高齡常見保健食品與中西藥交互作用知識庫'};
      }
    }
    if(DRUG_ALIASES[low]){
      const k=DRUG_ALIASES[low];
      return {key:k,display:k,itemType:defaultType,source:'雲端高齡藥品成分標準字典'};
    }
    for(const [gName,list] of Object.entries(GROUPS)){
      for(const drug of list){
        if(low===drug||low.startsWith(drug+' ')){
          return {key:drug,display:drug,itemType:defaultType,source:'雲端高齡藥品成分標準字典'};
        }
      }
    }
    return {key:null,display:null,itemType:defaultType,source:null};
  }

  function findLab(labs,type){
    const aliases={
      CrCl:['crcl','creatinine clearance','肌酸酐清除率','ccr'],
      eGFR:['egfr','估算腎絲球過濾率','腎絲球過濾率','gfr'],
      Scr:['scr','creatinine','serum creatinine','肌酸酐','血中肌酸酐','cr'],
      AST:['ast','got','sgot','天門冬胺酸轉胺酶','肝指數ast','肝指數got'],
      ALT:['alt','gpt','sgpt','丙胺酸轉胺酶','肝指數alt','肝指數gpt'],
      TBIL:['tbil','total bilirubin','bilirubin','總膽紅素','膽紅素','t-bil'],
      ChildPugh:['child-pugh','child pugh','childpugh','肝硬化分級分數','child-pugh score'],
      K:['k','k+','potassium','血鉀','鉀'],
      Na:['na','na+','sodium','血鈉','鈉'],
      HR:['hr','heart rate','心率']
    }[type]||[];
    for(const l of labs||[]){
      if(aliases.includes(String(l.name||'').trim().toLowerCase()))return Number(l.value);
    }
    return null;
  }

  let currentPayload=null;
  let lastEvalResponse=null;
  let openerOrigin=null;

  function banner(msg,isError=false){
    const b=$('cloud-banner');
    b.textContent=msg;
    b.className=isError?'banner error':'banner';
  }

  function renderParsedSummary(p){
    const box=$('parsed-summary');
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
    banner(`已成功解析上傳資料（流水號：${p.serialId||'匿名'}，藥品 ${p.medications.length} 項、保健食品 ${p.supplements.length} 項、檢驗 ${p.labs.length} 項）。請按「執行高齡潛在不適當用藥與交互作用比對」。`);
    return p;
  }

  function fallbackCloudEvaluate(p){
    const allItems=[
      ...p.medications.map(m=>typeof m==='string'?{name:m,itemType:'medication'}:{...m,itemType:m.itemType||'medication'}),
      ...p.supplements.map(s=>typeof s==='string'?{name:s,itemType:'supplement'}:{...s,itemType:'supplement'})
    ];
    const resolved=allItems.map(item=>{
      const info=resolveItem(item.name,item.itemType);
      return {...item,key:info.key,display:info.display,itemType:info.itemType,identitySource:info.source};
    });
    const active=new Set(resolved.map(r=>r.key).filter(Boolean));
    const hasGroup=g=>GROUPS[g]&&GROUPS[g].some(x=>active.has(x));
    const egfr=findLab(p.labs,'eGFR');
    const crcl=findLab(p.labs,'CrCl');
    const scr=findLab(p.labs,'Scr');
    const alt=findLab(p.labs,'ALT');
    const ast=findLab(p.labs,'AST');
    const tbil=findLab(p.labs,'TBIL');
    const child=findLab(p.labs,'ChildPugh');
    const kVal=findLab(p.labs,'K');

    const results=resolved.map(item=>{
      const checks=[];
      const k=item.key;
      const addCheck=(id,source,title,note='')=>checks.push({id,source,title,note,status:'potential_risk',conditions:[],missing:[]});
      if(k){
        if(GROUPS.benzodiazepines.includes(k)){
          addCheck('BEERS-T2-BZD','beers','苯二氮平類：高齡認知受損、譫妄、跌倒及骨折高風險','不可自行驟停，需評估減藥計畫。');
          addCheck('PIM-TW-T1-BZD','pim-taiwan','苯二氮平類：高齡混亂與跌倒風險');
          if(tbil!==null&&tbil>2.0)addCheck('HEPATIC-BZD-LIVER','organ-safety','肝功能異常 (TBIL > 2.0 mg/dL) 使用經肝代謝 BZD 易誘發肝性腦病變');
        }
        if(GROUPS.zdrugs.includes(k)){
          addCheck('BEERS-T2-ZDRUG','beers','Z 類安眠藥：高齡譫妄、跌倒與骨折風險');
          addCheck('PIM-TW-T1-ZDRUG','pim-taiwan','非苯二氮平安眠藥：高齡跌倒與骨折風險');
        }
        if(GROUPS.first_antihistamines.includes(k)){
          addCheck('BEERS-T2-ANTIHIST','beers','第一代抗組織胺：強抗膽鹼、混亂與跌倒風險');
        }
        if(GROUPS.nsaids.includes(k)){
          if((crcl!==null&&crcl<30)||(egfr!==null&&egfr<30)||(scr!==null&&scr>1.5)){
            addCheck('RENAL-NSAID-EGFR','organ-safety','腎功能低下 (eGFR/CrCl < 30 或 Scr > 1.5) 使用 NSAID 具急性腎損傷高風險');
          }
          if(hasGroup('anticoagulants'))addCheck('STOPP-C10','stopp-start','NSAID 合併抗凝血藥：重大腸胃道出血風險');
        }
        if(k==='metformin'){
          if(egfr!==null&&egfr<30)addCheck('RENAL-METFORMIN-30','organ-safety','Metformin 於 eGFR < 30 mL/min/1.73m2 屬禁忌：乳酸中毒風險');
          else if(egfr!==null&&egfr<45)addCheck('RENAL-METFORMIN-45','organ-safety','Metformin 於 eGFR < 45 mL/min/1.73m2 需評估減量並密切監測腎功能');
        }
        if(k==='allopurinol'&&egfr!==null&&egfr<60){
          addCheck('RENAL-ALLOPURINOL','organ-safety','Allopurinol 於 eGFR < 60 需依腎功能調降劑量，預防嚴重皮膚不良反應');
        }
        if(k==='digoxin'&&egfr!==null&&egfr<50){
          addCheck('RENAL-DIGOXIN-EGFR','organ-safety','Digoxin 於 eGFR < 50 排泄減少，需減量並監測血中濃度');
        }
        if(GROUPS.statins.includes(k)){
          if(alt!==null&&alt>120)addCheck('HEPATIC-STATIN-ALT','organ-safety','Statin 合併 ALT (GPT) > 120 U/L（>3倍上限）：肝損傷風險需評估停藥或換藥');
          if(ast!==null&&ast>120)addCheck('HEPATIC-STATIN-AST','organ-safety','Statin 合併 AST (GOT) > 120 U/L（>3倍上限）：肝損傷風險需評估');
          if(active.has('red_yeast_rice'))addCheck('SUPP-STATIN-RYR','supplement-safety','處方 Statin 降血脂藥合併紅麴（含 Monacolin K）：重複用藥，大幅增加橫紋肌溶解症與肝毒性風險');
        }
        if(GROUPS.anticoagulants.includes(k)){
          if(hasGroup('bleeding_supplements'))addCheck('SUPP-ANTICOAG-BLEED','supplement-safety','口服抗凝血劑（如 Warfarin、DOAC）合併具抗血小板/抗凝作用之保健食品（銀杏/魚油/大蒜精/人參/薑黃/葡萄糖胺）：顯著增加出血風險');
          if(k==='warfarin'&&active.has('vitamin_k'))addCheck('SUPP-VITK-WARFARIN','supplement-safety','Warfarin 合併維生素 K 或納豆製品：直接拮抗抗凝血藥效，導致血栓風險');
        }
        if(k==='paracetamol'&&alt!==null&&alt>100){
          addCheck('HEPATIC-APAP-ALT','organ-safety','Acetaminophen 於肝指數異常 (ALT > 100 U/L) 需限制每日總劑量 (<2000 mg/day)');
        }
        if(['rivaroxaban','apixaban','edoxaban'].includes(k)&&child!==null&&child>=7){
          addCheck('HEPATIC-DOAC-CHILD','organ-safety','中重度肝硬化 (Child-Pugh >= 7) 使用 DOAC 出血與蓄積風險');
        }
        if(GROUPS.bleeding_supplements.includes(k)){
          if(hasGroup('anticoagulants'))addCheck('SUPP-BLEED-ANTICOAG','supplement-safety','具抗血小板/抗凝作用之保健食品（銀杏/魚油/大蒜精/人參/薑黃/葡萄糖胺）合併抗凝血劑：顯著增加出血風險');
          if(hasGroup('antiplatelets'))addCheck('SUPP-BLEED-ANTIPLATELET','supplement-safety','具抗血小板作用之保健食品合併抗血小板藥（Aspirin/Clopidogrel 等）：加成出血風險');
          if(hasGroup('nsaids'))addCheck('SUPP-BLEED-NSAID','supplement-safety','銀杏／魚油／大蒜精／人參合併 NSAID 止痛藥：增加胃腸道出血風險');
        }
        if(k==='red_yeast_rice'){
          if(hasGroup('statins'))addCheck('SUPP-RYR-STATIN','supplement-safety','紅麴（含 Monacolin K）合併處方 Statin 降血脂藥：重複用藥，大幅增加橫紋肌溶解症與肝毒性風險');
          if(alt!==null&&alt>80)addCheck('SUPP-RYR-ALT','supplement-safety','紅麴於肝功能異常 (ALT > 80 U/L) 使用可能惡化肝指數');
        }
        if(k==='vitamin_k'&&active.has('warfarin')){
          addCheck('SUPP-VITK-WARFARIN','supplement-safety','維生素 K 或納豆製品合併 Warfarin：直接拮抗 Warfarin 抗凝血藥效，導致血栓風險');
        }
        if(k==='st_johns_wort'){
          if(hasGroup('anticoagulants'))addCheck('SUPP-SJW-ANTICOAG','supplement-safety','聖約翰草強效誘導 CYP3A4/P-gp，合併抗凝血劑降低血中濃度與療效');
          if(hasGroup('ssri')||hasGroup('snri')||hasGroup('strong_antidepressants'))addCheck('SUPP-SJW-SEROTONIN','supplement-safety','聖約翰草合併抗憂鬱藥：引發血清素症候群高風險');
          if(hasGroup('statins'))addCheck('SUPP-SJW-STATIN','supplement-safety','聖約翰草合併 Statin：誘導代謝降低降膽固醇療效');
        }
        if(GROUPS.mineral_chelators.includes(k)){
          if(hasGroup('fluoroquinolones'))addCheck('SUPP-MINERAL-FQ','supplement-safety','鈣／鐵／鎂補充劑合併 Fluoroquinolone 抗生素：形成螯合物大幅降低吸收，須間隔 2-4 小時');
          if(hasGroup('tetracyclines'))addCheck('SUPP-MINERAL-TETRA','supplement-safety','鈣／鐵／鎂補充劑合併四環黴素類抗生素：螯合降低吸收，須間隔 2-4 小時');
          if(active.has('levothyroxine'))addCheck('SUPP-MINERAL-THYROID','supplement-safety','鈣／鐵／鎂補充劑合併甲狀腺素 (Levothyroxine)：減少吸收，須間隔 4 小時');
        }
        if(k==='magnesium'&&((egfr!==null&&egfr<30)||(crcl!==null&&crcl<30))){
          addCheck('SUPP-MGO-RENAL','supplement-safety','鎂補充劑／氧化鎂於腎功能低下 (eGFR/CrCl < 30) 易蓄積引發高血鎂症');
        }
        if(k==='coq10'&&active.has('warfarin')){
          addCheck('SUPP-COQ10-WARFARIN','supplement-safety','輔酶 Q10 合併 Warfarin 可能減弱抗凝血效果，需密切監測 INR');
        }
        if(k==='ginseng'&&hasGroup('antidiabetics')){
          addCheck('SUPP-GINSENG-DM','supplement-safety','人參／西洋參合併降血糖藥：可能加強降血糖作用，增加高齡低血糖風險');
        }
        if(k==='potassium_supp'&&(hasGroup('ace')||hasGroup('arb')||hasGroup('k_sparing')||(kVal!==null&&kVal>5.0))){
          addCheck('SUPP-KSUPP-RAAS','supplement-safety','鉀補充劑／低鈉代鹽合併 ACEI/ARB 或保鉀利尿劑：嚴重高血鉀風險');
        }
      }
      const status=checks.length?'potentially_inappropriate':k?'no_rule_hit':'unrecognized';
      const reason=checks.length?checks.map(c=>c.title).join('；'):k?'僅表示已執行條件未命中；完整準則尚未實作，不能視為安全。':'未辨識品項，請人工確認。';
      const analysis=checks.length?checks.map(c=>({
        drug:item.name,
        ingredient:item.display||'',
        criterion:c.source==='supplement-safety'?`保健食品／中西藥交互作用（${c.id}）`:c.source==='organ-safety'?`肝腎功能劑量與禁忌篩檢（${c.id}）`:`${c.source.toUpperCase()}（${c.id}）`,
        ruleId:c.id,
        source:c.source,
        status:'potential_risk',
        risk:c.title,
        recommendation:'請醫師／藥師覆核必要性、適應症及個別風險，評估是否停用保健品、調整劑量或錯開服用；勿自行停用處方藥。'+(c.note?' 補充：'+c.note:'')
      })):[{
        drug:item.name,
        ingredient:item.display||'',
        criterion:'無可對應的已命中條款',
        ruleId:'',
        source:'',
        status,
        risk:reason,
        recommendation:'請藥師確認藥品／保健食品成分與完整病史。'
      }];
      return {
        input:item.name,
        itemType:item.itemType,
        ingredient:item.display,
        identitySource:item.identitySource,
        status,
        category:checks.length?(item.itemType==='supplement'?'保健食品交互作用篩檢':'條件式用藥篩檢'):null,
        reason,
        source:checks.map(c=>c.id).join('；')||null,
        clinicalChecks:checks,
        analysis
      };
    });

    return {
      version:VERSION,
      serialId:p.serialId||null,
      sourceMode:'cloud-ui',
      clinicalUseReady:false,
      fullAutomation:false,
      results,
      context:{
        serialId:p.serialId||null,
        age:p.age??null,
        ageProvided:p.age!==null&&p.age!==undefined,
        medicationCount:p.medications.length,
        supplementCount:p.supplements.length,
        labCount:p.labs.length,
        diagnosisCount:p.diagnoses.length
      },
      limitations:[
        '雲端高齡用藥與保健食品安全性評估結果僅供醫療人員決策輔助，請回傳本機端進行儲存與藥師覆核。'
      ]
    };
  }

  async function runEvaluation(){
    try{
      const p=validateAndParseInput();
      let resData=null;
      // 若同源本機 API 存在且提供 token，優先使用完整後端引擎（含 29萬筆 TFDA/健保目錄與 115 條規則）
      try{
        const s=await fetch('/api/session',{cache:'no-store'});
        if(s.ok){
          const {token}=await s.json();
          const evalRes=await fetch('/api/evaluate',{
            method:'POST',
            headers:{'Content-Type':'application/json','X-Local-Token':token},
            body:JSON.stringify(p)
          });
          if(evalRes.ok){
            resData=await evalRes.json();
            resData.sourceMode='cloud-ui';
          }
        }
      }catch(_){}
      if(!resData)resData=fallbackCloudEvaluate(p);
      lastEvalResponse=resData;
      renderEvaluationResults(resData);
      $('cloud-return-btn').disabled=false;
      $('cloud-download-btn').disabled=false;
      banner(`高齡用藥與保健食品安全性評估完成（流水號：${resData.serialId||'匿名'}）。您可以點擊「將評估結果一鍵回傳至本機端 UI 儲存與統計」。`);
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
      ['評估引擎版本',data.version]
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
      const copyBar=document.createElement('div');
      copyBar.style.cssText='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px';
      const title=document.createElement('h3');
      title.style.margin='0';
      title.textContent='藥品與保健食品不適切性分析表';
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
          lines.push(`   - 判讀狀態：${row.status==='potential_risk'?'潛在風險，需覆核':row.status}`);
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
          row.status==='potential_risk'?'⚠️ 潛在風險':row.status,
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
          row.status==='potential_risk'?'⚠️ 潛在風險':row.status,
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

  $('cloud-eval-btn').onclick=runEvaluation;

  $('cloud-return-btn').onclick=()=>{
    if(!lastEvalResponse)return;
    const msg={type:'CLOUD_EVAL_RESULT',payload:lastEvalResponse};
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
      localStorage.setItem('elder-cloud-return-latest',JSON.stringify({timestamp:Date.now(),data:lastEvalResponse}));
      sent=true;
    }catch(_){}
    banner(sent?'✅ 已將評估結果（流水號：'+(lastEvalResponse.serialId||'匿名')+'）回傳至本機端 UI！請切回本機工作台確認並儲存。':'請點擊「下載評估結果 JSON」並於本機端匯入。');
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
        if(e.data.autoEvaluate)runEvaluation();
      }catch(err){
        banner(err.message,true);
      }
      setTimeout(syncFrameHeight,100);
    }
  });
})();
