// [NEW v20] Physics Result Viewer. No LLM text or surrogate predictions enter this renderer.
(() => {
  let result=null,baseline=null,candidates=null,indices=[],timeline=[],position=0,timer=null;
  let revision=0,queue=Promise.resolve(),ready=false;
  const panel=document.createElement('section');panel.className='card';panel.id='vizPanelV20';
  panel.style.marginBottom='14px';
  panel.innerHTML=`<h2>물리 계산 결과 · 3D 공정 뷰어</h2>
  <div id="vizKpiV20" class="raw" aria-live="polite">계산 결과 대기</div>
  <div class="actions"><button id="vizRestartV20" class="secondary">처음부터 재생</button><button id="vizPlayV20" class="secondary">이어서 재생</button><button id="vizPauseV20" class="secondary">정지</button><button id="vizPeakV20" class="secondary">최고온도 시점</button>
  <select id="vizModeV20" style="width:auto" aria-label="3D 색상"><option value="temperature">온도 °C</option><option value="difference">공기 대비 ΔT °C</option><option value="cure">경화도 α</option></select></div>
  <label for="vizTimeV20">공통 시간 · 최대 60개 원본 저장 시점 (계산값 보간 없음)</label><input id="vizTimeV20" type="range" min="0" max="0" value="0" step="1">
  <div id="vizStatusV20" class="timebox">현재 계산 결과 없음</div>
  <div class="chart-grid" style="margin-top:12px"><div id="vizBaseV20" class="chart" style="height:500px" hidden></div><div id="vizResultV20" class="chart wide" style="height:500px"></div></div>
  <p class="file-note">1D 열·경화 계산을 300 × 200 mm 평판에 투영합니다. 두께 ×4 확대. A/B/C는 해석값이며 측정 센서가 아닙니다. 금형은 회색입니다. 먼저 종료된 안은 마지막 상태를 유지합니다. 외부 실험 검증 미완료.</p>`;
  $('aiChatPanel').after(panel);
  // [NEW v22] Match demo's default display without changing saved physical inputs.
  if(window.initializeDemoModeV22)window.initializeDemoModeV22();
  const controls=['vizRestartV20','vizPlayV20','vizPauseV20','vizPeakV20','vizModeV20','vizTimeV20'];
  const fmt=(v=null,d=null)=>v==null?'—':Number(v).toFixed(d==null?1:d);
  const kpi=(r=null)=>`Tmax ${fmt(r.summary.Tmax)} °C · ΔTmax ${fmt(r.summary.delta_Tmax)} °C · 최저 최종 α ${fmt(r.summary.final_DoC,4)} · 공정시간 ${fmt(r.summary.cycle_time)} min`;
  function sample(times=null,peak=null){const n=Math.min(60,times.length),set=new Set([0,times.length-1,nearestIndex(times,peak)]);for(let q=0;set.size<n&&q<n-1;q++)set.add(Math.round(q*(times.length-1)/Math.max(1,n-2)));return [...set].sort((a,b)=>a-b);}
  function limits(mode=null){let lo=Infinity,hi=-Infinity;for(const r of [baseline,result].filter(Boolean))for(let i=0;i<r.field.T_part.length;i++)for(const value of r.field.T_part[i]){const v=mode==='difference'?value-r.series.T_air[i]:value;lo=Math.min(lo,v);hi=Math.max(hi,v);}if(mode==='cure')return [0,1];if(mode==='difference'){const m=Math.max(3,Math.abs(lo),Math.abs(hi));return [-m,m];}return [lo,Math.max(lo+1,hi)];}
  function plot(r=null,i=null,label=null,mode=null,range=null){
    // [NEW v22] Independent demo renderer; original renderer remains as fallback.
    if(window.buildDemoPlotV22)return window.buildDemoPlotV22(r,i,label,mode,range);
    const g=v3dCachedGeometryV14(r),s=r.series,f=r.field,air=s.T_air[i],center=s.T_part_center[i];
    const vals=(mode==='cure'?f.alpha_part[i]:f.T_part[i].map(v=>mode==='difference'?v-air:v)).slice().reverse();
    const temps=[s.T_part_bottom_surface[i],center,s.T_part_top_surface[i]],ap=f.alpha_part[i];
    const sensor=mode==='cure'?[ap.at(-1),ap[Math.floor(ap.length/2)],ap[0]]:temps;
    const labels=sensor.map((v,q)=>`${['A 하면','B 중앙','C 상면'][q]} ${mode==='cure'?'α ':''}${fmt(v,mode==='cure'?3:1)}${mode==='cure'?'':'°C'}`);
    const z=[g.tool+.02,g.tool+g.th/2,g.H-.02];
    const traces=[{type:'mesh3d',x:g.comp.x,y:g.comp.y,z:g.comp.z,i:g.comp.i,j:g.comp.j,k:g.comp.k,intensity:g.comp.layer.map(q=>vals[q]),intensitymode:'vertex',flatshading:true,colorscale:mode==='cure'?V3D.CURE:mode==='difference'?V3D.DEV:'Turbo',cmin:range[0],cmax:range[1],colorbar:{title:{text:mode==='cure'?'α':mode==='difference'?'ΔT °C':'°C'},thickness:12,len:.6},hoverinfo:'skip',lighting:{ambient:.8,diffuse:.4},name:'CFRP'},
    {type:'mesh3d',x:g.toolm.x,y:g.toolm.y,z:g.toolm.z,i:g.toolm.i,j:g.toolm.j,k:g.toolm.k,color:V3D.GRAY,flatshading:true,showscale:false,hoverinfo:'skip',name:'Invar'},
    {type:'scatter3d',...g.lines,mode:'lines',line:{color:'#091323',width:2},hoverinfo:'skip'},
    {type:'scatter3d',x:[150,150,150],y:[g.Y0-1,g.Y0-1,g.Y0-1],z,mode:'markers',marker:{color:'#fff',size:4},text:labels,hoverinfo:'text'}];
    const status=`${label} · ${fmt(s.t[i])} min · 공기 ${fmt(air)}°C · 중앙 ${fmt(center)}°C (공기 대비 ${center-air>=0?'+':''}${fmt(center-air)}°C)<br>최저 α ${fmt(s.alpha_min[i],4)} · CFRP ${fmt(g.th)} mm · 해석값(측정 아님)`;
    const hid={visible:false,showbackground:false};
    const layout={paper_bgcolor:V3D.BG,font:{color:V3D.INK},margin:{l:0,r:0,t:70,b:0},showlegend:false,uirevision:'v20-camera',
      annotations:[{xref:'paper',yref:'paper',x:0,y:1.16,xanchor:'left',text:status,showarrow:false,align:'left',font:{size:11}}],
      scene:{xaxis:hid,yaxis:hid,zaxis:{...hid,range:[0,g.H*1.05]},aspectmode:'manual',aspectratio:{x:1.7,y:1,z:g.H*4/344*1.7},camera:{eye:{x:.8,y:-1.4,z:1},up:{x:0,y:0,z:1}},
        annotations:z.map((zz,q)=>({x:150,y:g.Y0-1,z:zz,text:labels[q],showarrow:true,ax:-80,ay:[32,0,-32][q],bgcolor:'#091323',font:{size:11,color:'#fff'}}))}};
    return {data:traces,layout};
  }
  function stop(){if(timer)clearInterval(timer);timer=null;}
  function failed(error=null){ready=false;stop();$('vizStatusV20').textContent='3D 표시 실패 · 아래 SVG 단면에서 같은 계산값을 확인하십시오.';for(const id of ['vizBaseV20','vizResultV20'])$(id).textContent='3D를 사용할 수 없습니다.';}
  function clear(){revision++;ready=false;stop();result=null;baseline=null;controls.forEach(id=>$(id).disabled=true);$('vizKpiV20').textContent='현재 계산 결과 없음';$('vizStatusV20').textContent='입력 변경 후 다시 계산하십시오.';/* [NEW v34r2] */syncSingleViewV34r2();queue=queue.catch(()=>{}).then(()=>{for(const id of ['vizBaseV20','vizResultV20'])if(window.Plotly)Plotly.purge(id);});}
  function update(r=null){/* [NEW v34r2] Preserve view choice across internal clear. */const choiceV34r2=document.getElementById?document.getElementById('vizChoiceV34r2'):null;const wantedV34r2=choiceV34r2&&choiceV34r2.value;clear();if(!r||r!==latest)return;result=r;baseline=candidates&&candidates.baseline_display;
    // [NEW v34r2] Compare only verified candidates from the current result set.
    if(!comparisonAvailableV34r2(r))baseline=null;
    const source=baseline&&baseline.series.t.at(-1)>r.series.t.at(-1)?baseline:r;
    indices=sample(source.series.t,r.summary.peak_time);timeline=indices.map(i=>source.series.t[i]);
    // [NEW v20] Keep the selected result's exact saved peak even when the baseline ends later.
    const peak=r.series.t[nearestIndex(r.series.t,r.summary.peak_time)];
    timeline=[...new Set([...timeline,peak])].sort((a,b)=>a-b);
    if(timeline.length>60){const drop=timeline.findIndex((t,i)=>i>0&&i<timeline.length-1&&t!==peak);timeline.splice(drop,1);}
    position=nearestIndex(timeline,peak);
    $('vizTimeV20').max=timeline.length-1;$('vizTimeV20').value=position;
    $('vizKpiV20').textContent=(baseline?'기준: '+kpi(baseline)+'\n선택: ':'')+kpi(r)+'\n계산 ID: '+(r.run_id_v14||r.model_hash||'물리 결과');
    $('vizBaseV20').hidden=!baseline;$('vizResultV20').className=baseline?'chart':'chart wide';
    // [NEW v34r2] Restore the active Studio single-view selection after refresh.
    if(baseline&&choiceV34r2)choiceV34r2.value=wantedV34r2; // [NEW v34r2]
    syncSingleViewV34r2();
    rebuild();
  }
  function rebuild(){const token=++revision;ready=false;stop();const r=result,b=baseline,mode=$('vizModeV20').value,range=limits(mode),items=[[r,'vizResultV20','선택안']];if(b)items.unshift([b,'vizBaseV20','기준안']);
    // [NEW v34r2] A simulation without recommendations is a calculation, not a selected candidate.
    if(!b)items[0][2]='계산 결과';
    queue=queue.catch(()=>{}).then(async()=>{if(token!==revision||r!==latest)return;
      for(const [x,id,label] of items){if(token!==revision)return;Plotly.purge(id);const initial=plot(x,nearestIndex(x.series.t,timeline[position]),label,mode,range);await Plotly.newPlot(id,initial.data,initial.layout,plotCfg);if(token!==revision)return;
        const frames=timeline.map((time,q)=>{const p=plot(x,nearestIndex(x.series.t,time),label,mode,range);return {name:'v20-'+q,data:p.data,layout:p.layout};});await Plotly.addFrames(id,frames);
        const node=$(id);if(node.on)node.on('plotly_webglcontextlost',()=>{if(token===revision)failed();});
      }
      if(token!==revision)return;ready=true;controls.forEach(id=>$(id).disabled=false);readout();
    }).catch(e=>{if(token===revision)failed(e);});
  }
  function readout(){if(!result)return;$('vizTimeV20').value=position;const i=nearestIndex(result.series.t,timeline[position]);$('vizStatusV20').textContent=`공통 시간 ${fmt(timeline[position])} min · 선택안 저장 시점 ${fmt(result.series.t[i])} min · 중앙 ${fmt(result.series.T_part_center[i])} °C · 최저 α ${fmt(result.series.alpha_min[i],4)}`;/* [NEW v34r2] */if(!baseline)$('vizStatusV20').textContent=$('vizStatusV20').textContent.replace('선택안 저장','계산 결과 저장');}
  // [NEW v34r2]
  function move(q=null){if(!ready||!result)return;position=Math.max(0,Math.min(timeline.length-1,q));readout();const token=revision,ids=baseline?['vizBaseV20','vizResultV20']:['vizResultV20'];const framePosition=position;queue=queue.catch(()=>{}).then(async()=>{if(token!==revision)return;await Promise.all(ids.map(id=>Plotly.animate(id,['v20-'+framePosition],{mode:'immediate',frame:{duration:0,redraw:true},transition:{duration:0}})));}).catch(e=>{if(token===revision)failed(e);});}
  function play(){stop();if(!ready)return;timer=setInterval(()=>{if(!ready||position>=timeline.length-1)return stop();move(position+1);},500);}
  $('vizRestartV20').onclick=()=>{move(0);play();};$('vizPlayV20').onclick=play;$('vizPauseV20').onclick=stop;
  $('vizPeakV20').onclick=()=>{stop();if(result)move(nearestIndex(timeline,result.summary.peak_time));};
  $('vizTimeV20').oninput=()=>{stop();move(Number($('vizTimeV20').value));};$('vizModeV20').onchange=()=>{if(result)rebuild();};
  // [NEW v20] Existing stale-response guards publish latest before calling this entry point.
  window.renderViz3DLiveV20=update;
  const oldClear=window.clearTemperatureView;window.clearTemperatureView=()=>{clear();if(oldClear)oldClear();};
  const oldAccept=window.acceptCandidatesV14;window.acceptCandidatesV14=(r=null)=>{candidates=r;if(oldAccept)oldAccept(r);};
  const oldCandidatesClear=window.clearCandidatesV14;window.clearCandidatesV14=()=>{candidates=null;if(oldCandidatesClear)oldCandidatesClear();};
  // [NEW v20] Manual form listeners in workbench hold their own function references.
  for(const event of ['input','change','submit'])$('simForm').addEventListener(event,()=>{candidates=null;});
  // [NEW v34r2] Keep baseline metadata for other consumers; filter it in this viewer.
  function sameResultV34r2(a=null,b=null){return !!a&&!!b&&(a===b||!!a.run_id_v14&&a.run_id_v14===b.run_id_v14);}
  function comparisonAvailableV34r2(r=null){
    const list=candidates&&candidates.candidate_displays;
    return !!baseline&&candidates.display_source!=='baseline_only'&&Array.isArray(list)&&list.length>0&&
      (sameResultV34r2(r,baseline)||list.some(x=>sameResultV34r2(x,r)))&& !sameResultV34r2(r,baseline);
  }
  function syncSingleViewV34r2(){
    if(!window.useFloatingStudioV22)return;
    let select=document.getElementById('vizChoiceV34r2');
    if(!select){
      select=document.createElement('select');select.id='vizChoiceV34r2';select.setAttribute('aria-label','표시할 3D 결과');
      select.innerHTML='<option value="result">계산 결과</option><option value="baseline">기준안</option>';
      panel.querySelector('.actions').appendChild(select);
      select.onchange=()=>{syncSingleViewV34r2();const node=$(select.value==='baseline'?'vizBaseV20':'vizResultV20');if(window.Plotly&&Plotly.Plots&&node.data)Promise.resolve(Plotly.Plots.resize(node)).catch(()=>{});};
    }
    select.options[0].textContent=baseline?'추천안':'계산 결과';select.options[1].disabled=!baseline;select.disabled=!result;
    if(!baseline)select.value='result';
    const showBase=!!baseline&&select.value==='baseline';
    $('vizBaseV20').hidden=!showBase;$('vizResultV20').hidden=showBase;
    for(const id of ['vizBaseV20','vizResultV20'])$(id).classList.add('studio-source','wide');
  }
  window.syncSingleViewV34r2=syncSingleViewV34r2;
  clear();if(latest)update(latest);
})();
