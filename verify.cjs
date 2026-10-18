const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('index.html','utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements={},storage={};
function element(id){return elements[id]??=( {value:'',textContent:'',innerHTML:'',hidden:false,className:'',style:{},classList:{add(){},remove(){}},addEventListener(){}})}
const context={document:{getElementById:element,querySelectorAll:()=>[]},localStorage:{getItem:k=>storage[k]??null,setItem:(k,v)=>storage[k]=v},crypto:require('crypto').webcrypto,console,alert:()=>{},setTimeout:()=>{},Blob,URL,confirm:()=>true};
vm.createContext(context);vm.runInContext(script,context);
element('age').value='75';element('setting').value='門診';element('meds').value='Valium\nStilnox\nMetformin\nunknown\nvalium';element('review').value='待覆核';element('evaluate').onclick();
assert.equal(vm.runInContext('current.items.length',context),4);
assert.equal(vm.runInContext('current.items.filter(i=>i.hits.length).length',context),2);
assert.equal(vm.runInContext('current.items.filter(i=>!i.name).length',context),1);
element('save').onclick();assert.equal(JSON.parse(storage['ya-records']).length,1);
element('from').value='2099-01-01';vm.runInContext('renderReport()',context);assert.match(element('reportContent').innerHTML,/<b>0<\/b>/);
assert.throws(()=>vm.runInContext('validate({})',context));
assert(html.includes("connect-src 'none'"));assert(!/\b(fetch|XMLHttpRequest|WebSocket)\s*\(/.test(script));
console.log('PASS: parse, matching, deduplication, unknown handling, save, date filter, validation, network policy');
