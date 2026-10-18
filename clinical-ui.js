/* Clinical fields contain no identifiers and are included in the final preview. */
function formatAnalysisForClipboard(rows, onlyRisk = false) {
 const labels = {
  potential_risk: '潛在風險，需覆核',
  insufficient_data: '資料不足，不能判定',
  source_unverified: '來源未確認，不能判定',
  exception_requires_review: '可能例外，需覆核',
  not_matched: '本條件未命中（非安全結論）'
 };
 const filtered = onlyRisk ? rows.filter(r => r.status === 'potential_risk' || r.status === 'potentially_inappropriate') : rows;
 const targetRows = filtered.length ? filtered : rows;
 const lines = ['【藥品與保健食品不適切性評估結果】'];
 targetRows.forEach((row, idx) => {
  const itemLabel = row.drug + (row.ingredient && row.ingredient !== row.drug ? `（${row.ingredient}）` : '');
  const statusLabel = labels[row.status] || clinicalStatusLabel(row.status);
  lines.push(`${idx + 1}. 品項：${itemLabel}`);
  lines.push(`   - 對應條款：${row.criterion || '無'}`);
  lines.push(`   - 判讀狀態：${statusLabel}`);
  lines.push(`   - 臨床風險：${row.risk || '無'}`);
  lines.push(`   - 臨床建議：${row.recommendation || '無'}`);
 });
 return lines.join('\n');
}

function formatAnalysisTSV(rows) {
 const labels = {
  potential_risk: '潛在風險，需覆核',
  insufficient_data: '資料不足，不能判定',
  source_unverified: '來源未確認，不能判定',
  exception_requires_review: '可能例外，需覆核',
  not_matched: '本條件未命中（非安全結論）'
 };
 const header = ['品項／成分', '對應準則／交互作用條款', '判讀狀態', '臨床風險／條款主題', '建議與待補資料'].join('\t');
 const body = rows.map(row => [
  row.drug + (row.ingredient ? '／' + row.ingredient : ''),
  row.criterion,
  labels[row.status] || clinicalStatusLabel(row.status),
  row.risk,
  row.recommendation
 ].map(v => String(v ?? '').replace(/[\r\n\t]+/g, ' ')).join('\t'));
 return [header, ...body].join('\n');
}

async function copyTextWithFeedback(text, statusNode, successMsg) {
 try {
  await navigator.clipboard.writeText(text);
  if (statusNode) statusNode.textContent = successMsg;
 } catch (_) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.append(ta);
  ta.select();
  document.execCommand('copy');
  ta.remove();
  if (statusNode) statusNode.textContent = successMsg;
 }
}

function renderAnalysisTable(rows, results = []) {
 const box = document.createElement('div');
 box.className = 'analysis-table';
 const headBar = document.createElement('div');
 headBar.style.cssText = 'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:8px';
 const title = document.createElement('h3');
 title.style.margin = '0';
 title.textContent = '藥品與保健食品不適切性分析表';

 const btnGroup = document.createElement('div');
 btnGroup.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:center';
 const copyNote = document.createElement('span');
 copyNote.className = 'muted';
 copyNote.setAttribute('role', 'status');

 const copyClinicalBtn = document.createElement('button');
 copyClinicalBtn.type = 'button';
 copyClinicalBtn.className = 'primary';
 copyClinicalBtn.style.margin = '0';
 copyClinicalBtn.textContent = '📋 複製臨床評估摘要（貼回處方系統）';
 copyClinicalBtn.onclick = () => copyTextWithFeedback(
  formatAnalysisForClipboard(rows, true),
  copyNote,
  '✅ 已複製臨床評估摘要！可直接 Ctrl+V 貼回處方評估系統。'
 );

 const copyTableBtn = document.createElement('button');
 copyTableBtn.type = 'button';
 copyTableBtn.style.margin = '0';
 copyTableBtn.textContent = '📑 複製完整表格內容 (Excel/Word 格式)';
 copyTableBtn.onclick = () => copyTextWithFeedback(
  formatAnalysisTSV(rows),
  copyNote,
  '✅ 已複製完整表格內容！可直接貼上至 Excel、Word 或處方評估表。'
 );

 btnGroup.append(copyClinicalBtn, copyTableBtn, copyNote);
 headBar.append(title, btnGroup);
 box.append(headBar);

 const note = document.createElement('p');
 note.className = 'muted';
 note.textContent = '每列對應一個藥品／保健食品規則分支（含 Beers 2023、STOPP v3、PIM-Taiwan 2018、肝腎功能劑量調整與中西藥保健品交互作用）。以下為篩檢提示，建議需經醫師／藥師個別覆核。';
 box.append(note);

 // 若有未辨識藥品提供候選修正按鈕，整合於表格上方提示列
 const suggestionResults = (results || []).filter(r => r.suggestions && r.suggestions.length);
 if (suggestionResults.length && typeof selectSuggestionCandidate === 'function') {
  const sugBar = document.createElement('div');
  sugBar.className = 'notice';
  sugBar.style.marginBottom = '10px';
  const sugLabel = document.createElement('span');
  sugLabel.textContent = '未辨識藥名相似候選修正：';
  sugBar.append(sugLabel);
  for (const r of suggestionResults) {
   for (const name of r.suggestions) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.style.margin = '4px 6px 0 0';
    btn.textContent = `${r.input} → 選用候選 ${name}`;
    btn.onclick = () => selectSuggestionCandidate(r.input, name);
    sugBar.append(btn);
   }
  }
  box.append(sugBar);
 }

 const scroll = document.createElement('div');
 scroll.className = 'record-scroll';
 const table = document.createElement('table');
 const header = document.createElement('tr');
 for (const text of ['品項／成分', '對應準則／交互作用條款', '判讀狀態', '臨床風險／條款主題', '建議與待補資料']) {
  const th = document.createElement('th');
  th.textContent = text;
  header.append(th);
 }
 table.append(header);
 const labels = {
  potential_risk: '⚠️ 潛在風險，需覆核',
  insufficient_data: '資料不足，不能判定',
  source_unverified: '來源未確認，不能判定',
  exception_requires_review: '可能例外，需覆核',
  not_matched: '本條件未命中（非安全結論）'
 };
 for (const row of rows) {
  const tr = document.createElement('tr');
  tr.dataset.analysisStatus = row.status;
  if (row.status === 'potential_risk' || row.status === 'potentially_inappropriate') {
   tr.style.background = '#fff9f6';
  }
  for (const text of [
   row.drug + (row.ingredient ? '／' + row.ingredient : ''),
   row.criterion,
   labels[row.status] || clinicalStatusLabel(row.status),
   row.risk,
   row.recommendation
  ]) {
   const td = document.createElement('td');
   td.textContent = text;
   tr.append(td);
  }
  table.append(tr);
 }
 scroll.append(table);
 box.append(scroll);
 return box;
}

function renderClinicalFields(div, row) {
 if (row.kind !== 'medication' && row.kind !== 'supplement') return;
 const box = document.createElement('div');
 box.className = 'clinical-fields';
 row.clinical = row.clinical || {};
 for (const [key, title, placeholder] of [['dailyDoseMg', '每日總量（mg/day）', '未知留空'], ['durationDays', '已使用天數', '未知留空']]) {
  const label = document.createElement('label');
  label.textContent = title;
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = 'any';
  input.placeholder = placeholder;
  input.value = row.clinical[key] ?? '';
  input.dataset.clinical = key;
  input.oninput = () => {
   row.clinical[key] = input.value === '' ? null : Number(input.value);
   row.selected = false;
   invalidate();
   renderClinicalSelection();
  };
  label.append(input);
  box.append(label);
 }
 for (const [key, title, options] of [
  ['route', '給藥途徑', [['unknown', '未知'], ['oral', '口服'], ['parenteral', '注射'], ['topical', '外用'], ['ophthalmic', '眼用'], ['vaginal', '陰道用'], ['transdermal', '經皮貼片'], ['sublingual', '舌下'], ['inhaled', '吸入']]],
  ['formulation', '釋放型態', [['unknown', '未知'], ['immediate_release', '速放型'], ['extended_release', '緩釋型']]],
  ['indication', '適應症', [['unknown', '未知'], ['insomnia', '失眠'], ['hypertension', '高血壓'], ['atrial_fibrillation', '心房顫動'], ['heart_failure', '心衰竭'], ['epilepsy', '癲癇'], ['severe_anxiety', '嚴重焦慮'], ['alcohol_withdrawal', '酒精戒斷'], ['rem_sleep_behavior', 'REM 睡眠行為障礙'], ['procedural', '處置／麻醉'], ['schizophrenia', '思覺失調'], ['bipolar', '雙相情緒障礙'], ['primary_prevention', '初級預防'], ['secondary_prevention', '次級預防'], ['gastroprotection', '腸胃保護（需覆核必要性）'], ['erosive_esophagitis', '糜爛性食道炎'], ['barrett', 'Barrett 食道'], ['zollinger_ellison', 'Zollinger–Ellison'], ['other', '其他（需人工覆核）']]]
 ]) {
  const label = document.createElement('label');
  label.textContent = title;
  const select = document.createElement('select');
  select.dataset.clinical = key;
  for (const [value, text] of options) {
   const option = document.createElement('option');
   option.value = value;
   option.textContent = text;
   select.append(option);
  }
  select.value = row.clinical[key] || 'unknown';
  select.onchange = () => {
   row.clinical[key] = select.value;
   row.selected = false;
   invalidate();
   renderClinicalSelection();
  };
  label.append(select);
  box.append(label);
 }
 const note = document.createElement('small');
 note.textContent = '未知請留空，不可將單顆含量誤當每日總量。修改後請重新勾選／全選並確認。';
 box.append(note);
 const detail = document.createElement('details');
 detail.style.gridColumn = '1 / -1';
 detail.style.marginTop = '5px';
 detail.open = Boolean(row.clinicalOpen);
 detail.ontoggle = () => { row.clinicalOpen = detail.open; };
 const summary = document.createElement('summary');
 summary.textContent = '臨床條件：劑量／療程／途徑／適應症（可展開補填）';
 detail.append(summary, box);
 div.append(detail);
}

function renderClinicalSelection() {
 document.querySelectorAll('#candidates .candidate').forEach((div, i) => {
  const check = div.querySelector('input[type=checkbox]');
  if (check) check.checked = rows[i].selected;
 });
}

function renderClinicalChecks(div, result) {
 const labels = { potential_risk: '風險提示（需覆核）', insufficient_data: '資料不足', source_unverified: '來源版本未確認', exception_requires_review: '可能例外，需覆核', not_matched: '此條件未命中' };
 const detail = document.createElement('details');
 const summary = document.createElement('summary');
 summary.textContent = '條件式規則檢核：' + (result.clinicalChecks || []).length + ' 個分支';
 detail.append(summary);
 for (const check of result.clinicalChecks || []) {
  const p = document.createElement('p');
  p.textContent = check.id + ' · ' + labels[check.status] + '：' + check.title + ((check.conditions || []).length ? '；條件：' + check.conditions.map(clinicalCondition).join(' 且 ') : '') + (check.missing.length ? '；缺少：' + check.missing.join('、') : '') + (check.note ? '；' + check.note : '');
  detail.append(p);
 }
 if (result.unmappedIngredients?.length) {
  const p = document.createElement('p');
  p.textContent = '尚未映射至規則的成分：' + result.unmappedIngredients.join('、');
  detail.append(p);
 }
 div.append(detail);
}

function clinicalCondition(spec) {
 const [op, ...args] = spec;
 if (op === 'lab') return args[0] + ' ' + args[1] + ' ' + args[2] + (args[0] === 'CrCl' ? ' mL/min' : args[0] === 'eGFR' ? ' mL/min/1.73m2' : '');
 if (op === 'dose') return '每日總量 ' + args[0] + ' ' + args[1] + ' mg/day';
 if (op === 'duration') return '療程 ' + args[0] + ' ' + args[1] + ' 天';
 if (op === 'diagnosis') return '診斷符合 ' + args.join('／');
 if (op === 'route') return '途徑為 ' + args.map(x => ({ oral: '口服', parenteral: '注射' }[x] || x)).join('／');
 if (op === 'formulation_known') return '速放／緩釋型態已確認';
 if (op === 'co') return '併用 ' + args[0];
 if (op === 'count') return args[0] + ' 藥品數 ' + args[1] + ' ' + args[2];
 return args.join('／');
}

function clinicalStatusLabel(status) {
 return {
  potentially_inappropriate: '風險提示，需臨床覆核',
  needs_clinical_context: '資料不足／來源待確認',
  exception_requires_review: '可能適應症例外，需覆核',
  not_covered: '已辨識，但規則尚未涵蓋',
  no_rule_hit: '僅已執行條件未命中，非安全結論',
  unrecognized: '未辨識，需確認品項',
  ambiguous: '同名品項有歧義，需人工確認'
 }[status] || '需臨床覆核';
}

(async () => {
 try {
  const db = window.ElderCloudAPI && typeof window.ElderCloudAPI.loadDatabase === 'function'
   ? await window.ElderCloudAPI.loadDatabase()
   : await fetch('/cloud-ui/cloud-rules-db.json', { cache: 'no-store' }).then(r => r.json());
  const rules = db.rules || [];
  const countBy = src => rules.filter(r => r.source === src).length;
  const section = document.createElement('section');
  const h = document.createElement('h2');
  h.textContent = '☁ 雲端臨床知識庫 API 連線狀態（免下載至本機電腦）';
  section.append(h);
  const note = document.createElement('p');
  note.className = 'notice';
  note.textContent = `雲端知識庫（${db.version || 'CLOUD-API'}）已連線，共提供 ${rules.length} 個雲端條件式篩檢分支：beers（Beers 2023）${countBy('beers')} 條、stopp-start（STOPP v3）${countBy('stopp-start')} 條、pim-taiwan（PIM-Taiwan 2018）${countBy('pim-taiwan')} 條、organ-safety（肝腎功能）${countBy('organ-safety')} 條、supplement-safety（保健食品交互作用）${countBy('supplement-safety')} 條。所有規則皆存於雲端，不佔本機記憶體與硬碟空間。`;
  section.append(note);
  const detail = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = '檢視雲端 API 規則清單及必要條件（共 ' + rules.length + ' 條）';
  detail.append(summary);
  const list = document.createElement('div');
  list.style.maxHeight = '280px';
  list.style.overflow = 'auto';
  for (const r of rules) {
   const p = document.createElement('p');
   p.textContent = r.id + ' [' + r.source + ']：' + r.title + ((r.conditions || []).length ? '；條件：' + r.conditions.map(clinicalCondition).join(' 且 ') : '') + (r.note ? '；' + r.note : '');
   list.append(p);
  }
  detail.append(list);
  section.append(detail);
  document.getElementById('status').after(section);
 } catch (_) {}
})();
