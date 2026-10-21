const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('C:/CodeCompass/CodeCompass-A-D05/app/A_D07_v3/app.js','utf8');
const accept=source.slice(source.indexOf('function accept('),source.indexOf('async function post('));
const result=vm.runInNewContext(`let renders=0; let state={id:'fixture',event_count:9,elapsed:20,status:'DONE'};function render(){renders++};${accept}
accept({id:'fixture',event_count:8,elapsed:30,status:'ACTIVE'});
accept({id:'fixture',event_count:9,elapsed:19,status:'ACTIVE'});
const staleRejected=renders===0&&state.status==='DONE';
accept({id:'fixture',event_count:10,elapsed:21,status:'FAILED'});
({staleRejected,newerAccepted:renders===1&&state.status==='FAILED'});`);
assert(result.staleRejected&&result.newerAccepted);
fs.writeFileSync('tmp/independent-audit/v3-js-final.json',JSON.stringify({passed:true,...result,scope:'isolated accept function, not browser verification'},null,2));
console.log(JSON.stringify(result));
