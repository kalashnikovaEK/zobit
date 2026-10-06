// [NEW v27] Current UI transplanted onto the uploaded 700-case version.
// [NEW v22] Include the uploaded v21 3D process viewer.
// [NEW v21] Two independent scroll panes and multiple non-modal graph windows.
(()=>{
  const byId=id=>document.getElementById(id),main=document.querySelector('main'),layout=document.querySelector('.layout'),side=document.querySelector('.controls');
  const results=layout.querySelector(':scope > section:not(.controls)');if(!results)return;
  const style=document.createElement('style');style.textContent=`
  html,body{height:100%;overflow:hidden}main{height:100dvh;max-width:none;padding:10px 12px;margin:0;display:flex;flex-direction:column;gap:10px}
  main>.eyebrow,main>h1,main>p.sub{display:none}.studio-brand{flex:none;margin:0;padding:4px 3px;font-size:16px;font-weight:700;letter-spacing:.02em;color:#dce7f4}
  .layout,.layout.v20-compact{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:12px;align-items:stretch}
  .studio-results{grid-column:1;grid-row:1}.controls{grid-column:2;grid-row:1}.studio-results,.controls{height:100%;min-height:0;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable;padding:0 5px 16px}
  .v20-compact>.controls{display:block}.v20-compact .v20-fold{margin-bottom:14px}.studio-tools{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;color:var(--muted);font-size:12px}.studio-tools button{font-size:12px;padding:7px 10px}
  /* [NEW v24] The 3D renderer resets className; stable IDs keep the overlay inside its chart. */
  #vizResultV20,#vizBaseV20{position:relative!important}
  .studio-source{position:relative!important;cursor:pointer;height:230px!important}.studio-source>svg{height:100%!important}.studio-open{position:absolute;inset:0;z-index:5;background:transparent;padding:0;border-radius:10px;color:#fff;font-size:12px}
  .studio-open span{position:absolute;right:8px;bottom:8px;background:#143047ed;border:1px solid #3f657e;border-radius:7px;padding:5px 8px}.studio-open:hover{box-shadow:inset 0 0 0 2px var(--accent)}.studio-open:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}.studio-open:disabled{cursor:default;opacity:.4}
  .studio-window{position:fixed;display:flex;flex-direction:column;overflow:hidden;resize:both;min-width:280px;min-height:220px;max-width:calc(100vw - 12px);max-height:calc(100dvh - 50px);border:1px solid #466580;background:#0d1929;border-radius:12px;box-shadow:0 20px 65px #0009}
  .studio-window:focus-within{border-color:var(--accent)}.studio-window-bar{display:flex;align-items:center;gap:8px;flex:none;min-height:42px;padding:8px 10px;background:#1a3047;cursor:move;touch-action:none;user-select:none}
  .studio-window-title{flex:1;min-width:0;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.studio-window-bar button{font-size:12px;padding:4px 8px;background:#29465f;color:#e8eff8}.studio-window-bar button:focus-visible{outline:2px solid var(--accent)}
  .studio-window-state{flex:none;font-size:11px;color:#9fb0c5;padding:6px 12px;border-bottom:1px solid #29405b}.studio-window-body{flex:1;min-height:0;overflow:auto;padding:8px}.studio-window-plot{height:100%;min-height:160px}.studio-window-plot>svg{display:block;width:100%;height:100%}.studio-model-info{margin:0 0 12px;font-size:12px}.studio-model-info .notice{margin:0;font-size:12px}
  @media(max-width:900px){.layout,.layout.v20-compact{grid-template-columns:minmax(0,1fr) minmax(260px,40%)}}
  @media(max-width:600px){.layout,.layout.v20-compact{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1.1fr) minmax(0,1fr)}.studio-results{grid-column:1;grid-row:1}.controls{grid-column:1;grid-row:2;border-top:1px solid var(--line);padding-top:10px}}
  `;document.head.appendChild(style);
  results.classList.add('studio-results');results.id='studioResultsV21';side.id='studioSideV21';results.tabIndex=0;side.tabIndex=0;
  const brand=document.createElement('header');brand.className='studio-brand';brand.textContent='CFRP Process Studio';main.prepend(brand);document.title='CFRP Process Studio';
  const notice=main.querySelector(':scope > .notice');if(notice){const info=document.createElement('details');info.className='studio-model-info';const summary=document.createElement('summary');summary.textContent='모델 범위 · 검증 정보';info.append(summary,notice);results.append(info);}
  const tools=document.createElement('div');tools.className='studio-tools';const hint=document.createElement('span');hint.textContent='그래프를 클릭해 별도 창으로 보기 · 여러 창 비교 가능';const closeAll=document.createElement('button');closeAll.type='button';closeAll.className='secondary';closeAll.textContent='그래프 창 모두 닫기';tools.append(hint,closeAll);results.prepend(tools);
  const charts=[['liveSectionV19','CFRP 단면'],['liveHistoryV19','실시간 온도·경화 이력'],['liveHeatmapV19','실시간 두께 온도장'],['tempChart','온도 이력'],['cureChart','경화도 이력'],['contactChart','접촉 열유속'],['profileChart','두께방향 온도·경화도'],['heatmapChart','CFRP 온도장'],['comparisonChartV14','기준안·후보 비교'],['baselineStackV14','기준안 직육면체'],['tvCuboid','선택 시점 직육면체'],['vizResultV20','3D 공정 선택안'],['vizBaseV20','3D 공정 기준안']];
  const records=new Set(),buttons=[];let nextId=0,z=100,scheduled=null;
  const copy=value=>JSON.parse(JSON.stringify(value,(_,v)=>ArrayBuffer.isView(v)?Array.from(v):v));
  function available(source){return !!latest&&!!(source.data&&source.data.length||source.querySelector('svg'));}
  function front(record){record.panel.style.zIndex=++z;}
  function close(record){record.observer.disconnect();if(window.Plotly&&record.plot.data)Plotly.purge(record.plot);records.delete(record);record.panel.remove();}
  function clamp(record){const rect=record.panel.getBoundingClientRect();record.panel.style.left=Math.max(4,Math.min(rect.left,window.innerWidth-rect.width-4))+'px';record.panel.style.top=Math.max(42,Math.min(rect.top,window.innerHeight-70))+'px';}
  function render(record){const source=byId(record.source);if(!source||!available(source)){if(window.Plotly&&record.plot.data)Plotly.purge(record.plot);record.plot.replaceChildren();record.plot.textContent='입력이 변경되었거나 계산 결과가 없습니다. 다시 계산하세요.';record.state.textContent='현재 결과 무효';return;}
    // [NEW v22] The v20 process viewer has its own clock; keep its window label accurate.
    const t=byId(record.source.startsWith('viz')?'vizStatusV20':'timeLabel').textContent;record.state.textContent='현재 계산 결과 · '+t+' · 시간 이동과 함께 갱신';
    if(source.data&&window.Plotly){const config={...plotCfg,responsive:true};const newLayout=copy(source.layout||{});delete newLayout.width;delete newLayout.height;newLayout.autosize=true;newLayout.uirevision=latest.run_id_v14||latest.model_hash;
      if(!record.plot.data)record.plot.replaceChildren();Plotly.react(record.plot,copy(source.data),newLayout,config).catch(()=>{record.state.textContent='그래프 표시 실패 · 브라우저 3D 지원을 확인하세요.';});return;
    }
    const svg=source.querySelector('svg');if(svg){const clone=svg.cloneNode(true);clone.querySelectorAll('[id]').forEach(e=>e.id='studio-'+record.id+'-'+e.id);record.plot.replaceChildren(clone);return;}
  }
  function open(source=null,title=null){const node=byId(source);if(!node||!available(node))return;const id=++nextId,panel=document.createElement('section');panel.className='studio-window';panel.setAttribute('role','dialog');panel.setAttribute('aria-label',title+' 그래프 창 '+id);panel.id='studioWindowV21-'+id;panel.style.width=Math.min(680,window.innerWidth-16)+'px';panel.style.height=Math.min(460,window.innerHeight-65)+'px';panel.style.left=Math.min(36+(id%6)*36,Math.max(4,window.innerWidth-parseFloat(panel.style.width)-8))+'px';panel.style.top=60+(id%6)*25+'px';
    const bar=document.createElement('div');bar.className='studio-window-bar';bar.tabIndex=0;bar.setAttribute('aria-label',title+' 창 이동');const label=document.createElement('span');label.className='studio-window-title';label.textContent=title+' · '+id;const maximize=document.createElement('button');maximize.type='button';maximize.textContent='확대';maximize.setAttribute('aria-label',title+' 창 확대');const exit=document.createElement('button');exit.type='button';exit.textContent='닫기';exit.setAttribute('aria-label',title+' 창 닫기');bar.append(label,maximize,exit);
    const state=document.createElement('div');state.className='studio-window-state';const body=document.createElement('div');body.className='studio-window-body';const plot=document.createElement('div');plot.className='studio-window-plot';body.append(plot);panel.append(bar,state,body);document.body.append(panel);
    const record={id,panel,plot,state,source,observer:null};records.add(record);front(record);exit.onclick=()=>close(record);panel.addEventListener('pointerdown',()=>front(record));panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();close(record);}});
    bar.addEventListener('keydown',e=>{if(e.target!==bar||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const r=panel.getBoundingClientRect(),step=e.shiftKey?20:5;panel.style.left=r.left+(e.key==='ArrowLeft'?-step:e.key==='ArrowRight'?step:0)+'px';panel.style.top=r.top+(e.key==='ArrowUp'?-step:e.key==='ArrowDown'?step:0)+'px';clamp(record);front(record);});let restored=null;maximize.onclick=()=>{if(restored){Object.assign(panel.style,restored);restored=null;maximize.textContent='확대';}else{restored={left:panel.style.left,top:panel.style.top,width:panel.style.width,height:panel.style.height};Object.assign(panel.style,{left:'6px',top:'44px',width:window.innerWidth-12+'px',height:window.innerHeight-50+'px'});maximize.textContent='복원';}front(record);};
    bar.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;front(record);const rect=panel.getBoundingClientRect(),startX=e.clientX,startY=e.clientY;bar.setPointerCapture(e.pointerId);function move(event){panel.style.left=Math.max(4,Math.min(rect.left+event.clientX-startX,window.innerWidth-rect.width-4))+'px';panel.style.top=Math.max(42,Math.min(rect.top+event.clientY-startY,window.innerHeight-70))+'px';}function end(){bar.removeEventListener('pointermove',move);bar.removeEventListener('pointerup',end);bar.removeEventListener('pointercancel',end);}bar.addEventListener('pointermove',move);bar.addEventListener('pointerup',end);bar.addEventListener('pointercancel',end);});
    record.observer=new ResizeObserver(()=>{if(plot.data&&window.Plotly)try{Promise.resolve(Plotly.Plots.resize(plot)).catch(()=>{});}catch(_){}});record.observer.observe(body);render(record);exit.focus({preventScroll:true});
  }
  for(const [id,title] of charts){const source=byId(id);if(!source)continue;source.classList.add('studio-source');const button=document.createElement('button');button.type='button';button.className='studio-open';button.setAttribute('aria-label',title+' 별도 창 열기');const text=document.createElement('span');text.textContent='↗ '+title+' 열기';button.append(text);button.onclick=()=>open(id,title);source.append(button);buttons.push({source,button});}
  function sync(){scheduled=null;for(const entry of buttons){if(entry.button.parentElement!==entry.source)entry.source.append(entry.button);entry.button.disabled=!available(entry.source);}for(const record of records)render(record);}
  function schedule(){if(scheduled!==null)return;scheduled=setTimeout(sync,80);}
  new MutationObserver(schedule).observe(results,{childList:true,subtree:true,characterData:true});
  byId('status')&&new MutationObserver(schedule).observe(byId('status'),{childList:true,subtree:true,characterData:true});
  closeAll.onclick=()=>{for(const record of [...records])close(record);};window.addEventListener('resize',()=>{for(const record of records)clamp(record);});sync();
})();

// [NEW v34r2] Stable ID styles survive renderer className updates; hidden wins.
(()=>{
  const style=document.createElement('style');
  style.textContent='#studioResultsV21 #vizPanelV20 .chart-grid{display:block}#studioResultsV21 #vizBaseV20,#studioResultsV21 #vizResultV20{height:230px!important}#vizBaseV20[hidden],#vizResultV20[hidden]{display:none!important}';
  document.head.appendChild(style);
  if(window.syncSingleViewV34r2)window.syncSingleViewV34r2();
})();
