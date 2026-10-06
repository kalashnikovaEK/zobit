// [NEW v13] Time inspection and cuboid projection of the SAME verified 1D solver arrays.
(()=>{
  let result=null,timer=null;
  const el=id=>document.getElementById(id);
  const panel=document.createElement('section');panel.className='card';panel.style.marginTop='14px';
  panel.innerHTML=`<h2>시간 탐색 · 내부온도 직육면체</h2>
  <p class="sub">위 시간 슬라이더와 함께 움직입니다. 직육면체는 1D 두께 계산의 3D 투영이며, 평면 300 × 200 mm는 표시용이고 두께는 ×4 확대합니다. 적층수는 0.18 mm 가정의 예시이며 A/B/C는 해석값입니다. 공기보다 높은 온도는 발열뿐 아니라 냉각 지연으로도 발생합니다.</p>
  <div class="actions"><button id="tvPrev" class="secondary">이전</button><button id="tvPlay" class="secondary">재생</button><button id="tvNext" class="secondary">다음</button></div>
  <label for="tvMinute">확인할 시간 [min] — 가까운 저장 시점으로 이동</label><input id="tvMinute" type="number" step="any" min="0">
  <div id="tvValues" class="raw" aria-live="polite">계산 결과를 기다립니다.</div>
  <div class="grid" style="margin:12px 0"><div class="field"><label for="tvField">색상 표시</label><select id="tvField"><option value="temperature">공기 대비 온도차 [°C]</option><option value="cure">경화도 α</option></select></div>
  <div class="field"><label for="tvCut">내부 단면 노출</label><select id="tvCut"><option value="full">전체 두께</option><option value="cut">선택 깊이 위쪽 제거</option></select></div></div>
  <label for="tvDepth">확인할 두께 셀</label><input id="tvDepth" type="range" min="0" max="1" step="1"><div id="tvCell" class="timebox">—</div>
  <div id="tvCuboid" class="chart wide" style="height:480px"></div>`;
  el('heatmapChart').after(panel);
  const controls=['tvPrev','tvPlay','tvNext','tvMinute','tvField','tvCut','tvDepth'];
  function stop(){if(timer)clearInterval(timer);timer=null;el('tvPlay').textContent='재생';}
  function clear(){stop();result=null;controls.forEach(id=>el(id).disabled=true);el('timeSlider').disabled=true;el('tvValues').textContent='현재 계산 결과가 없습니다.';el('tvCell').textContent='—';if(window.Plotly)Plotly.purge('tvCuboid');}
  function index(){return Number(el('timeSlider').value);}
  function move(i){if(!result)return;i=Math.max(0,Math.min(result.series.t.length-1,i));el('timeSlider').value=i;renderProfile(result,i);show(i);}
  function show(i){if(!result)return;const s=result.series,f=result.field,t=s.t[i],cell=Number(el('tvDepth').value);
    el('tvMinute').value=t;el('timeLabel').textContent=t.toFixed(2)+' min';
    el('tvValues').textContent=`시간 ${t.toFixed(2)} min\n공기 ${s.T_air[i].toFixed(2)} °C · 상면 ${s.T_part_top_surface[i].toFixed(2)} °C\n중앙 ${s.T_part_center[i].toFixed(2)} °C · 하면 ${s.T_part_bottom_surface[i].toFixed(2)} °C\n최저 경화도 ${s.alpha_min[i].toFixed(4)} · 접촉 열유속 ${s.q_contact[i].toFixed(2)} W/m²`;
    el('tvCell').textContent=`깊이 ${f.z_part[cell].toFixed(3)} mm · 내부온도 ${f.T_part[i][cell].toFixed(2)} °C · 경화도 ${f.alpha_part[i][cell].toFixed(4)}`;
/* [NEW v29] Visual palette only. */     for(const id of ['tempChart','cureChart','contactChart','heatmapChart'])if(el(id).data)Plotly.relayout(id,{shapes:[{type:'line',xref:'x',yref:'paper',x0:t,x1:t,y0:0,y1:1,line:{color:'#2563EB',width:2,dash:'dot'}}]});
    // [NEW v14] Use cached v09b geometry before constructing the legacy fallback mesh.
    if(window.renderStackViewV14){window.renderStackViewV14(result,i);if(window.renderComparisonV14)window.renderComparisonV14(result,i);return;}
    const cure=el('tvField').value==='cure',values=cure?f.alpha_part[i]:f.T_part[i],n=values.length,th=result.condition.thickness;
    const mesh={type:'mesh3d',x:[],y:[],z:[],i:[],j:[],k:[],intensity:[],text:[],hovertemplate:'%{text}<extra></extra>',flatshading:true,colorscale:cure?'Viridis':'Turbo',cmin:cure?0:Math.min(...f.T_part.flat()),cmax:cure?1:Math.max(...f.T_part.flat()),colorbar:{title:{text:cure?'α':'°C'}},name:'CFRP'};
    const faces=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]];
    for(let j=el('tvCut').value==='cut'?cell:0;j<n;j++){const base=mesh.x.length,z0=j*th/n,z1=(j+1)*th/n;
      mesh.x.push(0,100,100,0,0,100,100,0);mesh.y.push(0,0,70,70,0,0,70,70);mesh.z.push(z0,z0,z0,z0,z1,z1,z1,z1);
      for(let k=0;k<8;k++){mesh.intensity.push(values[j]);mesh.text.push(`시간 ${t.toFixed(2)} min<br>깊이 ${f.z_part[j].toFixed(3)} mm<br>온도 ${f.T_part[i][j].toFixed(2)} °C<br>경화도 ${f.alpha_part[i][j].toFixed(4)}`);}
      for(const face of faces){mesh.i.push(base+face[0]);mesh.j.push(base+face[1]);mesh.k.push(base+face[2]);}
    }
    // [NEW v14] Render v09b CFRP + Invar + bag geometry in this inspector.
    if(window.renderStackViewV14){window.renderStackViewV14(result,i);return;}
/* [NEW v29] Visual palette only. */     Plotly.react('tvCuboid',[mesh],{paper_bgcolor:'#ffffff',font:{color:'#334155'},margin:{l:0,r:0,t:40,b:0},title:{text:`${t.toFixed(2)} min · 1D 결과의 3D 투영`,font:{size:15}},uirevision:'v13-cuboid',scene:{xaxis:{title:'표시 길이'},yaxis:{title:'표시 너비'},zaxis:{title:'깊이 [mm]',autorange:'reversed'},aspectmode:'manual',aspectratio:{x:1.5,y:1,z:.6},camera:{eye:{x:1.6,y:-1.8,z:1.1}}}},plotCfg);
  }
  window.updateTemperatureView=(r=null,i=null)=>{stop();result=r;if(!r)return clear();controls.forEach(id=>el(id).disabled=false);el('timeSlider').disabled=false;el('tvMinute').max=r.series.t.at(-1);el('tvDepth').max=r.field.z_part.length-1;el('tvDepth').value=Math.floor(r.field.z_part.length/2);show(i===null?index():i);};
  window.clearTemperatureView=clear;
  el('timeSlider').addEventListener('input',()=>{stop();show(index());});
  el('tvPrev').addEventListener('click',()=>{stop();move(index()-1);});el('tvNext').addEventListener('click',()=>{stop();move(index()+1);});
  el('tvMinute').addEventListener('input',()=>{stop();if(result&&Number.isFinite(Number(el('tvMinute').value)))move(nearestIndex(result.series.t,Number(el('tvMinute').value)));});
  for(const id of ['tvDepth','tvField','tvCut'])el(id).addEventListener('input',()=>show(index()));
  el('tvPlay').addEventListener('click',()=>{if(timer)return stop();if(!result)return;if(index()>=result.series.t.length-1)move(0);el('tvPlay').textContent='일시정지';timer=setInterval(()=>{if(!result||index()>=result.series.t.length-1)return stop();move(index()+1);},300);});
  clear();if(latest)window.updateTemperatureView(latest,index());
})();
