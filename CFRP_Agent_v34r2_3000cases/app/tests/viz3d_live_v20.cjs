// [NEW v20] Contract tests for physics arrays, comparison frames and stale render cancellation.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const fixture=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2])):{condition:{thickness:10},options:{tool_thickness_mm:10},summary:{Tmax:120,delta_Tmax:5,final_DoC:.9,cycle_time:2,peak_time:1},series:{t:[0,1,2],T_air:[25,100,90],T_part_center:[25,120,100],T_part_top_surface:[25,115,99],T_part_bottom_surface:[25,105,98],alpha_min:[0,.8,.9]},field:{z_part:[2,5,8],T_part:[[25,25,25],[115,120,105],[99,100,98]],alpha_part:[[0,0,0],[.85,.9,.8],[.95,.92,.9]],T_tool:[[25,25],[100,98],[90,89]]}};
const nodes=new Map(),plots=new Map(),frames=new Map();let tick=null;
class Node {constructor(){this.style={};this.value='0';}set innerHTML(s){for(const m of s.matchAll(/id="([^"]+)"/g))nodes.set(m[1],new Node());}after(){}addEventListener(){}on(){} }
const $=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)};
const c={document:{createElement:()=>new Node()},$,latest:fixture,window:null,plotCfg:{},clearTemperatureView(){},acceptCandidatesV14(){},clearCandidatesV14(){},nearestIndex:(a,x)=>a.reduce((b,v,i)=>Math.abs(v-x)<Math.abs(a[b]-x)?i:b,0),setInterval:f=>{tick=f;return 1},clearInterval:()=>tick=null};c.window=c;
c.Plotly={purge:id=>{plots.delete(id);frames.delete(id)},newPlot:async(id,data,layout)=>{plots.set(id,{data,layout})},addFrames:async(id,f)=>frames.set(id,f),animate:async(id,n)=>{const f=frames.get(id).find(x=>x.name===n[0]);plots.set(id,f)}};
vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/../stack_view_v14.js','utf8'),c);vm.runInContext(fs.readFileSync(__dirname+'/../viz3d_live_v20.js','utf8'),c);
const flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 $('vizModeV20').value='temperature';c.renderViz3DLiveV20(fixture);await flush();
 assert(frames.get('vizResultV20').length<=60);assert(plots.get('vizResultV20').layout.annotations[0].text.includes('측정 아님'));
 const f=frames.get('vizResultV20')[0];assert.equal(f.data[0].intensity[0],fixture.field.T_part[0].at(-1));
 $('vizTimeV20').value=0;$('vizTimeV20').oninput();await flush();assert.equal(plots.get('vizResultV20').data[0].intensity[0],fixture.field.T_part[0].at(-1));
 $('vizModeV20').value='cure';$('vizModeV20').onchange();await flush();assert.equal(frames.get('vizResultV20')[0].data[0].cmax,1);
 const base=JSON.parse(JSON.stringify(fixture));base.series.t=base.series.t.map(x=>x*2);base.summary.cycle_time=null;
 c.acceptCandidatesV14({baseline_display:base,candidate_displays:[fixture]});c.renderViz3DLiveV20(fixture);await flush();
 assert(!$('vizBaseV20').hidden);assert($('vizKpiV20').textContent.includes('공정시간 — min'));assert.equal(frames.get('vizBaseV20').length,frames.get('vizResultV20').length);
 const last=frames.get('vizResultV20').at(-1);assert.equal(last.data[0].intensity[0],fixture.field.alpha_part.at(-1).at(-1));
 $('vizRestartV20').onclick();assert(tick);c.clearTemperatureView();await flush();assert.equal(tick,null);assert.equal(plots.size,0);
 // A pending old newPlot must not install frames after clear/new result.
 let release;const original=c.Plotly.newPlot;c.Plotly.newPlot=async(...args)=>{await new Promise(r=>release=r);return original(...args)};
 c.renderViz3DLiveV20(fixture);await flush();c.clearTemperatureView();release();await flush();assert.equal(plots.size,0);
 c.Plotly.newPlot=async()=>{throw Error('no WebGL')};c.renderViz3DLiveV20(fixture);await flush();assert($('vizStatusV20').textContent.includes('SVG'));
 console.log('PASS: physics cell mapping, ≤60 frames, cure, common comparison clock, held endpoint, measured null, playback cancellation, stale async render, WebGL fallback');
})().catch(e=>{console.error(e);process.exitCode=1});
