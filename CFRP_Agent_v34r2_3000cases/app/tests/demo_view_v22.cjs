// [NEW v22] Contract test of demo geometry against real stored solver cells.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const r=JSON.parse(fs.readFileSync(__dirname+'/../artifacts/physics_fixture_v20.json'));
const c={window:{}};vm.createContext(c);
vm.runInContext(fs.readFileSync(__dirname+'/../stack_view_v14.js','utf8'),c);
vm.runInContext(fs.readFileSync(__dirname+'/../demo_view_v22.js','utf8'),c);
let extent=3;for(let i=0;i<r.series.t.length;i++)for(const v of r.field.T_part[i])extent=Math.max(extent,Math.abs(v-r.series.T_air[i]));
for(const mode of ['difference','temperature','cure']){
 for(const i of [0,Math.floor(r.series.t.length/2),r.series.t.length-1]){
  const p=c.window.buildDemoPlotV22(r,i,'선택안',mode,mode==='cure'?[0,1]:[-extent,extent]);
  assert.equal(p.data.length,6);assert.equal(p.data[2].name,'진공백');assert(p.data[4].x.length>0);assert.equal(p.layout.scene.annotations.length,6);
  const mesh=p.data[0],n=r.field.z_part.length;
  for(let q=0;q<n;q++){const raw=mode==='cure'?r.field.alpha_part[i][n-1-q]:r.field.T_part[i][n-1-q];const expected=mode==='difference'?raw-r.series.T_air[i]:raw;for(let j=0;j<8;j++)assert.equal(mesh.intensity[q*8+j],expected);}
  assert(mesh.cmin<=mesh.cmax);if(mode==='difference'){assert.equal(mesh.cmin,-Math.ceil(extent));assert.equal(mesh.cmax,Math.ceil(extent));assert(mesh.colorbar.ticktext.includes('0 공기와 같음'));}
  assert(p.layout.annotations[0].text.includes('해석값(측정 아님)'));assert(p.layout.scene.annotations.some(x=>x.text.includes('Invar')));
 }
}
const i=r.series.t.findIndex(t=>t>=137),p=c.window.buildDemoPlotV22(r,i,'선택안','difference',[-extent,extent]);assert(new Set(p.data[0].intensity).size>1);
console.log('PASS: six demo traces, bag/ply/material labels, per-cell temperature and cure mapping, unclipped common scale, nonuniform section at 137 min');
