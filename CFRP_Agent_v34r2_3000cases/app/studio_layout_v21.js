// [NEW v21] Presentation only: reparent existing nodes; keep solver results and event handlers.
(() => {
  // [NEW v27] Preserve historical layout; independent UI takes precedence.
  if(window.useFloatingStudioV22)return;
  const main=document.querySelector('main'),layout=document.querySelector('.layout');
  if(!main||!layout||!$('vizPanelV20'))return;
  document.body.classList.add('studioV21');
  const viewer=layout.children[1],controls=$('simForm').closest('section');
  viewer.classList.add('studioViewerV21');
  const sidebar=document.createElement('section');sidebar.className='studioSidebarV21';layout.appendChild(sidebar);
  const node=(tag=null,html=null)=>{const el=document.createElement(tag);if(html!==null)el.innerHTML=html;return el;};
  const toolbar=node('header',`<div class="studioBrandV21"><strong>CFRP Process Studio</strong><small>문헌 기반 열·경화 시뮬레이션 · 물리 계산 결과 뷰어</small></div><span class="studioVersionV21">v21 · Windows / Python 3.14</span><button id="studioRunV21" class="primary" type="button">▶ 시뮬레이션 실행</button><button id="studioExportV21" class="secondary" type="button">입력 JSON 내보내기</button>`);
  toolbar.className='studioToolbarV21';main.prepend(toolbar);
  $('studioRunV21').onclick=()=>{if(!$('runBtn').disabled)$('runBtn').click();};
  $('studioExportV21').onclick=()=>$('saveJsonBtn').click();
  const syncRun=()=>{$('studioRunV21').disabled=$('runBtn').disabled;$('studioRunV21').textContent=$('runBtn').disabled?'계산 진행 중…':'▶ 시뮬레이션 실행';};
  new MutationObserver(syncRun).observe($('runBtn'),{attributes:true,attributeFilter:['disabled']});syncRun();

  // [NEW v21] Sidebar tabs retain the original forms, IDs, and event listeners.
  const sideTabs=node('div',`<button id="studioInputTabV21" type="button" role="tab" aria-controls="studioInputPaneV21">공정 입력</button><button id="studioAiTabV21" type="button" role="tab" aria-controls="studioAiPaneV21">AI 어시스턴트</button>`);
  sideTabs.className='studioTabsV21';sideTabs.setAttribute('role','tablist');sidebar.appendChild(sideTabs);
  const inputPane=node('div'),aiPane=node('div');inputPane.id='studioInputPaneV21';aiPane.id='studioAiPaneV21';
  for(const p of [inputPane,aiPane]){p.setAttribute('role','tabpanel');sidebar.appendChild(p);}
  inputPane.appendChild(controls);
  const model=$('modelProfile').closest('section'),chat=$('aiChatPanel'),candidate=$('candidateChoiceV14').closest('section');
  for(const el of [model,chat,candidate])aiPane.appendChild(el);
  function chooseSide(mode=null){const ai=mode==='ai';inputPane.hidden=ai;aiPane.hidden=!ai;$('studioInputTabV21').setAttribute('aria-selected',String(!ai));$('studioAiTabV21').setAttribute('aria-selected',String(ai));}
  $('studioInputTabV21').onclick=()=>chooseSide('input');$('studioAiTabV21').onclick=()=>chooseSide('ai');chooseSide('input');
  const disclosure=(title=null,el=null)=>{const d=node('details'),s=node('summary');s.textContent=title;d.append(s,el);inputPane.appendChild(d);};
  disclosure('실측 경계 이력 재현',$('measuredFileV14').closest('section'));
  disclosure('현재 결과 검토 기록',$('reviewerV14').closest('section'));
  const oldCard=$('tempChart').closest('.card'),raw=$('raw').closest('details');inputPane.appendChild(raw);
  const footer=oldCard.querySelector('.footer-note');if(footer)inputPane.appendChild(footer);
  const scope=node('p');scope.className='file-note';scope.textContent='외부 실험 검증 미완료 · 현재 결과는 내부 시연용 해석값입니다.';inputPane.appendChild(scope);

  // [NEW v21] Exactly one chart per view, including the 3D baseline selector.
  const tabs=node('nav');tabs.className='studioTabsV21';tabs.setAttribute('aria-label','결과 시각화 선택');
  const primary=[['temperature','온도 이력'],['cure','경화 이력'],['profile','두께 단면'],['heatmap','2D 온도장'],['three','3D 공정']];
  const buttons=new Map();
  for(const [key,label] of primary){const b=node('button');b.type='button';b.textContent=label;b.id='studioTabV21-'+key;b.setAttribute('aria-controls','studioViewV21-'+key);b.onclick=()=>select(key);tabs.appendChild(b);buttons.set(key,b);}
  const extra=node('select',`<option value="">추가 보기</option><option value="flux">접촉 열유속</option><option value="svg">SVG 단면</option><option value="depth">깊이 탐색 3D</option><option value="comparison">기준·선택 비교 이력</option>`);extra.id='studioExtraV21';extra.setAttribute('aria-label','추가 시각화');extra.onchange=()=>{if(extra.value)select(extra.value);};tabs.appendChild(extra);
  const badgeRow=$('badges');badgeRow.after(tabs);
  const surface=node('section');surface.className='card';tabs.after(surface);
  const heading=node('div',`<h2 id="studioTitleV21">3D 공정</h2><span class="badge">물리 계산 결과</span>`);heading.className='studioHeadingV21';surface.appendChild(heading);
  const note=node('p');note.id='studioNoteV21';note.className='studioViewNoteV21';surface.appendChild(note);
  const pages=new Map(),chartIds=['tempChart','cureChart','profileChart','heatmapChart','contactChart','vizResultV20','vizBaseV20','tvCuboid','comparisonChartV14'];
  const viewList=[...primary,['flux','접촉 열유속'],['svg','SVG 단면'],['depth','깊이 탐색 3D'],['comparison','기준·선택 비교 이력']];
  for(const [key] of viewList){const p=node('div');p.id='studioViewV21-'+key;p.hidden=true;surface.appendChild(p);pages.set(key,p);}
  for(const [key,id] of [['temperature','tempChart'],['cure','cureChart'],['heatmap','heatmapChart'],['flux','contactChart']])pages.get(key).appendChild($(id));
  pages.get('profile').append($('timeSlider').closest('.profile-tools'),$('profileChart'));
  const viz=$('vizPanelV20');pages.get('three').appendChild(viz);viz.querySelector('h2').hidden=true;
  const sideSelect=node('select',`<option value="selected">현재 선택안</option><option value="baseline">AI 기준안</option>`);sideSelect.id='studio3dChoiceV21';sideSelect.setAttribute('aria-label','표시할 3D 결과');viz.querySelector('.actions').appendChild(sideSelect);
  const noBaseline=node('p');noBaseline.className='raw';noBaseline.textContent='AI 기준안이 없습니다. 현재 선택안을 확인하십시오.';viz.appendChild(noBaseline);
  const live=$('liveViewV19');pages.get('svg').appendChild(live);live.querySelector('h2').hidden=true;
  // Duplicate SVG charts stay in the DOM for existing update/clear functions.
  $('liveHistoryV19').hidden=true;$('liveHeatmapV19').hidden=true;
  pages.get('depth').appendChild($('tvCuboid').closest('section'));
  pages.get('comparison').appendChild($('comparisonChartV14'));
  const comparisonEmpty=node('p');comparisonEmpty.className='raw';comparisonEmpty.textContent='AI 검증 후보가 생성되면 비교 이력을 표시합니다.';pages.get('comparison').appendChild(comparisonEmpty);
  const archive=node('div');archive.hidden=true;archive.id='studioArchiveV21';viewer.appendChild(archive);archive.append(oldCard,$('baselineStackV14'));
  // The old comparison caption describes an archived duplicate; retain it with that duplicate.
  const caption=candidate.querySelector('p.sub');if(caption)archive.appendChild(caption);
  const navigation=node('div',`<span id="studioPageV21"></span><button id="studioPrevV21" class="secondary" type="button">← 이전 뷰</button><button id="studioNextV21" class="secondary" type="button">다음 뷰 →</button>`);navigation.className='studioNavigationV21';surface.appendChild(navigation);
  let active='three',resizeTimer=null;
  const notes={temperature:'공기·복합재·금형의 계산 온도 이력',cure:'상면·중앙·금형측 셀과 최저 경화도 이력',profile:'시간 슬라이더로 저장 시점의 온도·경화도 단면 확인',heatmap:'가로: 시간 · 세로: 실제 CFRP 두께 셀 · 색: 온도',three:'현재 선택안 또는 AI 기준안 중 하나의 3D 표시',flux:'복합재에서 금형으로 전달되는 접촉 열유속',svg:'WebGL 없이 같은 물리 계산 배열의 단면 확인',depth:'저장 시간·깊이 셀·내부 단면 선택',comparison:'기준안과 선택안의 중앙 온도·최저 경화도 비교'};
  function resize(){if(!window.Plotly||!Plotly.Plots)return;for(const id of chartIds){const el=$(id);if(el.data&&el.getClientRects().length)Promise.resolve(Plotly.Plots.resize(el)).catch(()=>{});
// [NEW v21] Card heading already names the chart; avoid title/legend overlap.
if(el.data&&el.getClientRects().length&&['tempChart','cureChart','profileChart','heatmapChart','contactChart'].includes(id)){
const axes={tempChart:['시간 [min]','온도 [°C]'],cureChart:['시간 [min]','경화도 α'],profileChart:['온도 [°C]','상면 기준 깊이 [mm]'],heatmapChart:['시간 [min]','CFRP 두께 위치 [mm]'],contactChart:['시간 [min]','열유속 [W/m²]']}[id];
Plotly.relayout(el,{'title.text':'','legend.y':1.12,'margin.t':75,'xaxis.title':{text:axes[0]},'yaxis.title':{text:axes[1]}}).catch(()=>{});
if(id==='profileChart')Plotly.relayout(el,{'xaxis2.title':{text:'경화도 α'}}).catch(()=>{});
}}}
  function scheduleResize(){clearTimeout(resizeTimer);resizeTimer=setTimeout(resize,80);}
  function single3d(){const hasBase=window.hasCandidatesV14&&window.hasCandidatesV14(),wantBase=sideSelect.value==='baseline';$('vizBaseV20').hidden=!wantBase||!hasBase;$('vizResultV20').hidden=wantBase;noBaseline.hidden=!wantBase||!!hasBase;}
  sideSelect.onchange=()=>{single3d();scheduleResize();};
  // A result refresh may reset the baseline visibility; restore the single-view choice.
  new MutationObserver(()=>{single3d();scheduleResize();}).observe($('vizKpiV20'),{childList:true,characterData:true,subtree:true});
  new MutationObserver(()=>{comparisonEmpty.hidden=!$('comparisonChartV14').hidden;scheduleResize();}).observe($('comparisonChartV14'),{attributes:true,attributeFilter:['hidden']});
  function stopPlayback(){if($('vizPauseV20'))$('vizPauseV20').click();for(const id of ['livePlayV19','tvPlay'])if($(id).textContent==='일시정지')$(id).click();}
  function select(key=null){if(!pages.has(key))return;stopPlayback();active=key;for(const [k,p] of pages)p.hidden=k!==key;for(const [k,b] of buttons)b.setAttribute('aria-selected',String(k===key));extra.value=primary.some(x=>x[0]===key)?'':key;const index=viewList.findIndex(x=>x[0]===key);$('studioTitleV21').textContent=viewList[index][1];note.textContent=notes[key];$('studioPageV21').textContent=`${index+1} / ${viewList.length}`;single3d();scheduleResize();}
  $('studioPrevV21').onclick=()=>select(viewList[(viewList.findIndex(x=>x[0]===active)+viewList.length-1)%viewList.length][0]);
  $('studioNextV21').onclick=()=>select(viewList[(viewList.findIndex(x=>x[0]===active)+1)%viewList.length][0]);
  window.selectStudioViewV21=select;
  window.refreshStudioLayoutV21=()=>{single3d();comparisonEmpty.hidden=!$('comparisonChartV14').hidden;scheduleResize();};
  window.addEventListener('resize',scheduleResize);
  select('three');comparisonEmpty.hidden=!$('comparisonChartV14').hidden;
})();
