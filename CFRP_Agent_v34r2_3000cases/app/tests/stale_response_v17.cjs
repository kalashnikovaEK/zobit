// [NEW v17] Execute the unchanged page's run() with a delayed response.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../interactive.html','utf8');
const source=html.slice(html.indexOf('async function run(){'),html.indexOf('async function loadDefaults(){'));
let input={thickness:10},release,started;
const gate=new Promise(r=>started=r);
const controls={runBtn:{disabled:false}};
const context={latest:null,window:{clearCandidatesV14(){}},runGenerationV14:0,activeManualRunV14:null,
 $:id=>controls[id],payload:()=>input,setStatus(){},renderSummary(){throw Error('Stale summary painted')},renderCharts(){throw Error('Stale chart painted')},
 invalidateResults(){context.runGenerationV14++;context.latest=null},API_BASE:'',
 fetch:()=>{started();return new Promise(r=>release=()=>r({ok:true,json:async()=>({ok:true,data:{summary:{Tmax:185}}})}))}};
vm.createContext(context);vm.runInContext(source,context);
(async()=>{const task=context.run();await gate;input={thickness:12};context.invalidateResults();release();await task;assert.equal(context.latest,null);assert.equal(controls.runBtn.disabled,false);console.log('PASS: delayed old response discarded; button released');})().catch(e=>{console.error(e);process.exit(1)});
