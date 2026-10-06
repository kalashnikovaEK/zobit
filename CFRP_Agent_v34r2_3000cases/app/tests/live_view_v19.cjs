// [NEW v19] Exercise visible SVG output, shared timeline, nulls and invalidation.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const fixture=process.argv[2]?JSON.parse(fs.readFileSync(process.argv[2],'utf8')):{
 condition:{thickness:10},summary:{Tmax:120,delta_Tmax:5,final_DoC:.9,cycle_time:60,peak_time:1},
 series:{t:[0,1],T_air:[25,120],T_part_center:[25,110],T_part_top_surface:[25,115],T_part_bottom_surface:[25,105],T_tool_interface_surface:[25,100],T_tool_outer_surface:[25,98],alpha_min:[0,.9]},
 field:{z_part:[2,5,8],T_part:[[25,25,25],[115,110,105]],alpha_part:[[0,0,0],[.95,.92,.9]],T_tool:[[25,25],[100,98]]}};
const nodes=new Map();let ticks=null,cleared=0,moved=null;
class Node{
 constructor(){this.value='0';this.disabled=false;this.textContent='';this._html='';this.attrs={};this.style={};}
 set innerHTML(s){this._html=s;for(const m of s.matchAll(/id="([^"]+)"/g))nodes.set(m[1],new Node());}
 get innerHTML(){return this._html;}
 after(){}appendChild(){}replaceChildren(){this._html='';this.textContent='';}setAttribute(k,v){this.attrs[k]=v;}
 dispatchEvent(){moved=Number(this.value);context.moveLiveViewV19(fixture,moved);}
}
const $=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)};
const context={document:{createElement:()=>new Node(),head:new Node()},$,latest:null,window:null,Event:class{},
 nearestIndex:(a,x)=>a.reduce((best,v,i)=>Math.abs(v-x)<Math.abs(a[best]-x)?i:best,0),
 clearTemperatureView:()=>cleared++,setInterval:f=>{ticks=f;return 1},clearInterval:()=>ticks=null};context.window=context;
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../live_view_v19.js','utf8'),context);
context.updateLiveViewV19(fixture);
assert($('liveSectionV19').innerHTML.includes('<svg'));assert($('liveHeatmapV19').innerHTML.includes('<rect'));
assert($('liveReadoutV19').textContent.includes(fixture.series.T_part_center[context.nearestIndex(fixture.series.t,fixture.summary.peak_time)].toFixed(2)));
for(const id of ['liveSectionV19','liveHistoryV19','liveHeatmapV19'])assert(!/NaN|Infinity|undefined/.test($(id).innerHTML));
$('liveTimeV19').value='0';$('liveTimeV19').oninput();assert.equal(moved,0);
$('liveFieldV19').value='cure';$('liveFieldV19').onchange();assert($('liveSectionV19').innerHTML.includes('0.0 ~ 1.0'));
$('livePlayV19').onclick();assert(ticks);ticks();assert.equal(moved,1);
context.clearTemperatureView();assert.equal(ticks,null);assert.equal($('liveSectionV19').innerHTML,'');assert($('liveTimeV19').disabled);assert.equal(cleared,1);
const measured=process.argv[3]?JSON.parse(fs.readFileSync(process.argv[3],'utf8')):JSON.parse(JSON.stringify(fixture));measured.summary.cycle_time=null;
context.updateLiveViewV19(measured);assert($('liveSummaryV19').textContent.includes('공정시간 — min'));
console.log('PASS: solver arrays → SVG; peak frame, timeline, cure, playback, invalidation, measured null');

// [NEW v19] Simulate a rejected Plotly/WebGL render and require a visible explanation.
fixture.options=fixture.options||{tool_thickness_mm:10};
fixture.field.z_tool=fixture.field.z_tool||[11,15];
context.plotCfg={};context.Plotly={react:()=>Promise.reject(Error('WebGL failed')),purge(){}};
vm.runInContext(fs.readFileSync(__dirname+'/../stack_view_v14.js','utf8'),context);
context.renderStackViewV14(fixture,0);
setImmediate(()=>{assert($('tvCuboid').textContent.includes('3D 표시를 사용할 수 없습니다'));console.log('PASS: rejected 3D render shows fallback explanation');});
