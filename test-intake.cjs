const assert=require('node:assert/strict');const core=require('./intake-core');
const rows=core.parse('姓名：測試\n藥品：Valium\n年齡：78\n檢驗：eGFR,45,mL/min/1.73m2\n診斷：高血壓\n其他文字');
assert(rows.every(x=>!x.selected));assert.equal(rows[0].kind,'skip');assert(!rows[0].value.includes('測試'));
rows.forEach(r=>r.selected=r.kind!=='skip');const p=core.payload(rows);
assert.deepEqual(Object.keys(p),['age','medications','labs','diagnoses']);assert.equal(p.age,78);assert.equal(p.labs[0].value,45);
assert.throws(()=>core.payload([...rows,{kind:'age',value:'79',selected:true}]));
assert.throws(()=>core.payload([...rows,{kind:'medication',value:'A123456789',selected:true}]));
assert.throws(()=>core.payload([...rows,{kind:'lab',value:'eGFR,,mL/min',selected:true}]));
console.log('PASS: candidate exclusion, manual selection, request allowlist, age ambiguity, identifiers, numeric values');
