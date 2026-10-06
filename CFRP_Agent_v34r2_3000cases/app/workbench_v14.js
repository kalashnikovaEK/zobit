// [NEW v14] Model selection/health UI; chat requests remain independent.
(()=>{
 const section=document.createElement('section');section.className='card';section.style.marginBottom='14px';
 section.innerHTML='<h2>로컬 모델 선택</h2><label for="modelProfile">Ollama 모델</label><select id="modelProfile"><option value="gemma2">Gemma2</option></select><button id="modelHealth" type="button" class="secondary" style="margin-top:10px">연결 확인</button><pre id="modelHealthResult" class="raw">설치된 Ollama 모델을 선택하십시오.</pre><p class="sub">각 채팅 요청은 독립적으로 해석합니다. 이전 대화에 생략한 수치는 자동 추론하지 않습니다. 검사 통과는 소프트웨어 계약과 내부 시연 제약에 대한 판정입니다.</p>';
 $('aiChatPanel').before(section);
 window.selectedModelProfileV14=()=>$('modelProfile').value;
 fetch(API_BASE+'/api/models').then(x=>x.json()).then(b=>{if(!b.ok)throw new Error(b.error);$('modelProfile').replaceChildren();for(const [id,p] of Object.entries(b.data)){const o=document.createElement('option');o.value=id;o.textContent=p.label+' · '+p.model;$('modelProfile').appendChild(o);}}).catch(e=>$('modelHealthResult').textContent=e.message);
 $('modelHealth').onclick=async()=>{try{const b=await (await fetch(API_BASE+'/api/model-health',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:window.selectedModelProfileV14()})})).json();$('modelHealthResult').textContent=JSON.stringify(b.data||b,null,2);}catch(e){$('modelHealthResult').textContent=e.message;}};
 $('modelProfile').onchange=()=>invalidateResults('모델 선택 변경 · 다시 실행하십시오.');
})();

// [NEW v14] Baseline/candidate comparison, measured reconstruction and exact-run review.
(()=>{
 let candidates=null;
 const card=document.createElement('section');card.className='card';card.style.marginBottom='14px';
 card.innerHTML='<h2>검증 후보 비교</h2><label for="candidateChoiceV14">표시할 조건</label><select id="candidateChoiceV14" disabled><option>추천 결과 대기</option></select><pre id="candidateSummaryV14" class="raw">기준 대비 최고온도·편차·경화도·시간을 함께 비교합니다.</pre><div id="comparisonChartV14" class="chart wide"></div><div id="baselineStackV14" class="chart wide" style="height:420px"></div><p class="sub">아래 모델은 같은 물리 시각의 기준안입니다. 후보는 시간·깊이 탐색 모델에 표시됩니다. 색 범위는 두 결과의 전체 이력에 공통입니다. 먼저 종료된 결과는 마지막 저장 상태를 표시합니다.</p>';
 $('aiChatPanel').after(card);
 function clearCandidates(){candidates=null;/* [NEW v19] Empty comparisons should not occupy blank chart space. */for(const id of ['comparisonChartV14','baselineStackV14'])$(id).hidden=true;$('candidateChoiceV14').disabled=true;$('candidateChoiceV14').replaceChildren(new Option('추천 결과 대기',''));$('candidateSummaryV14').textContent='현재 후보 결과가 없습니다.';if(window.Plotly)for(const id of ['comparisonChartV14','baselineStackV14'])Plotly.purge(id);}
 function selectCandidate(){if(!candidates)return;const k=Number($('candidateChoiceV14').value),r=k<0?candidates.baseline_display:candidates.candidate_displays[k];
  invalidateResults('선택한 검증 조건을 표시합니다.');latest=r;
  for(const [name,value] of Object.entries(r.condition))if($(name)){$(name).value=value;$(name).step='any';}
  for(const [name,id] of Object.entries(LIMIT_IDS))$(id).value=candidates.limits[name];
  renderSummary(r);renderCharts(r);showComparison(r,Number($('timeSlider').value));setStatus('검증 결과 선택 완료 · 검토는 선택한 결과 해시에 연결됩니다.','run');
 }
 function showComparison(r,i){if(!candidates||!candidates.baseline_display||!window.Plotly)return;const base=candidates.baseline_display,tm=r.series.t[i],bi=nearestIndex(base.series.t,tm);
  let dev=3;for(const x of [base,r])dev=Math.max(dev,v3dCachedGeometryV14(x).dev);
  window.renderStackViewV14(base,bi,'baselineStackV14',dev);window.renderStackViewV14(r,i,'tvCuboid',dev);
  const rows=['Tmax','delta_Tmax','final_DoC','cycle_time'].map(key=>`${key}: 기준 ${base.summary[key]} → 선택 ${r.summary[key]}`);
  $('candidateSummaryV14').textContent='목표: '+(candidates.target||'계산')+'\n'+rows.join('\n')+'\n기준 제약 충족: '+base.decision.feasible+' · 선택 제약 충족: '+r.decision.feasible;
  const lines=[];for(const [x,label,color] of [[base,'기준','#55dfbf'],[r,'선택','#ffb56b']])lines.push({x:x.series.t,y:x.series.T_part_center,name:label+' 중앙 °C',mode:'lines',line:{color}},{x:x.series.t,y:x.series.alpha_min,name:label+' 최저 α',mode:'lines',yaxis:'y2',line:{color,dash:'dot'}});
  Plotly.react('comparisonChartV14',lines,{...layoutBase,xaxis:{title:'공통 시간 [min]'},yaxis:{title:'중앙 온도 [°C]'},yaxis2:{title:'최저 α',overlaying:'y',side:'right',range:[0,1]},margin:{l:55,r:55,t:25,b:45},shapes:[{type:'line',xref:'x',yref:'paper',x0:tm,x1:tm,y0:0,y1:1,line:{color:'#fff',dash:'dot'}}]},plotCfg);
 }
 window.hasCandidatesV14=()=>!!candidates;
 window.clearCandidatesV14=clearCandidates;
 window.acceptCandidatesV14=r=>{clearCandidates();/* [NEW v34r2] No comparison menu for baseline-only calculations. */if(!r||r.display_source==='baseline_only'||!Array.isArray(r.candidate_displays)||!r.candidate_displays.length)return;if(!r.baseline_display)return;candidates=r;/* [NEW v19] Show comparisons only when a baseline exists. */for(const id of ['comparisonChartV14','baselineStackV14'])$(id).hidden=false;const select=$('candidateChoiceV14');select.replaceChildren();for(let i=-1;i<(r.candidate_displays||[]).length;i++){const o=document.createElement('option');o.value=i;o.textContent=i<0?'기준안':`물리 검증 후보 ${i+1}`;select.appendChild(o);}select.value=r.candidate_displays.length?'0':'-1';select.disabled=false;};
 window.renderComparisonV14=showComparison;
 $('candidateChoiceV14').onchange=selectCandidate;
 // [NEW v19] Start without empty chart frames.
 clearCandidates();
 // Manual edits invalidate comparisons; candidate selection itself uses already verified data.
 for(const event of ['input','change','submit'])$('simForm').addEventListener(event,clearCandidates);
 $('resetBtn').addEventListener('click',clearCandidates);$('jsonFileInput').addEventListener('change',clearCandidates);$('modelProfile').addEventListener('change',clearCandidates);
 const measured=document.createElement('section');measured.className='card';measured.style.marginTop='14px';
 measured.innerHTML='<h2>실측 경계 이력 재현</h2><p class="sub">JSON 또는 CSV의 time_min, air_c, tool_c를 업로드합니다. 실측 금형 외면은 prescribed가 필요합니다. 관측 종료까지 재현하며 미래 공정 최적화에는 사용하지 않습니다. 냉각 종료가 관측되지 않으면 공정시간은 —로 표시합니다.</p><input id="measuredFileV14" type="file" accept=".json,.csv"><button id="measuredRunV14" type="button" class="secondary">실측 이력 계산</button><pre id="measuredStatusV14" class="raw">실측 초기 부품온도가 없으면 첫 공기·금형온도의 평균을 사용합니다.</pre>';
 $('heatmapChart').after(measured);
 $('measuredRunV14').onclick=async()=>{let token=null,snapshot=null;try{if($('runBtn').disabled)throw new Error('진행 중인 계산이 끝난 후 실행하십시오.');const file=$('measuredFileV14').files[0];if(!file)throw new Error('실측 경계 파일을 선택하십시오.');if(file.size>800000)throw new Error('파일은 800 kB 이하이어야 합니다.');const text=await file.text();let history,observations;
  if(file.name.toLowerCase().endsWith('.csv')){const lines=text.trim().split(/\r?\n/),headers=lines.shift().trim().split(',').map(s=>s.trim());if(headers.join(',')!=='time_min,air_c,tool_c')throw new Error('CSV 열 순서는 time_min,air_c,tool_c 입니다.');history=lines.map(line=>{const cells=line.split(',');if(cells.length!==3||cells.some(c=>!c.trim()))throw new Error('CSV 빈 값 또는 열 오류');return cells.map(Number);});}
  else{const value=JSON.parse(text);if(value.boundary_history){if(Object.keys(value).some(k=>!['boundary_history','observations'].includes(k)))throw new Error('허용되지 않는 JSON 필드');history=value.boundary_history;observations=value.observations;}else history=value;}
  const inputs=payload();snapshot=JSON.stringify(inputs);clearCandidates();invalidateResults('실측 이력 재현 중…');token=runGenerationV14;activeManualRunV14=token;$('runBtn').disabled=true;$('measuredRunV14').disabled=true;
  const body=await (await fetch(API_BASE+'/api/measured',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inputs,boundary_history:history,observations})})).json();
  if(token!==runGenerationV14||snapshot!==JSON.stringify(payload()))return;if(!body.ok)throw new Error(body.error);latest=body.data;renderSummary(latest);renderCharts(latest);$('badges').appendChild(badge('실측 경계 재현 · 미래 예측 아님','warn'));$('measuredStatusV14').textContent=JSON.stringify({summary:latest.summary,qualification:latest.qualification,diagnostic:latest.observation_diagnostic},null,2);setStatus('실측 관측기간의 경계 조건부 재현 완료','run');
 }catch(error){$('measuredStatusV14').textContent=error.message;}finally{if(activeManualRunV14===token){activeManualRunV14=null;$('runBtn').disabled=false;}$('measuredRunV14').disabled=false;}};
 const review=document.createElement('section');review.className='card';review.style.marginTop='14px';
 review.innerHTML='<h2>현재 결과 검토 기록</h2><label for="reviewerV14">검토자</label><input id="reviewerV14" maxlength="100"><div class="actions"><button id="reviewDoneV14" type="button" class="secondary">시연 결과 검토 완료</button><button id="reviewHoldV14" type="button" class="secondary">보류</button><button id="reviewExportV14" type="button" class="secondary" disabled>기록 저장</button></div><pre id="reviewStatusV14" class="raw">검토 대기 · 설비 운전 승인이 아닙니다.</pre>';
 measured.after(review);let record=null;
 window.invalidateReviewV14=()=>{record=null;$('reviewExportV14').disabled=true;$('reviewStatusV14').textContent='현재 결과 검토 대기';};
 async function submit(status){try{if(!latest||!latest.run_id_v14)throw new Error('현재 입력값의 검증 결과를 먼저 계산하십시오.');const expected=latest.run_id_v14;const body=await (await fetch(API_BASE+'/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({run_id:expected,reviewer:$('reviewerV14').value,status})})).json();if(!body.ok)throw new Error(body.error);if(!latest||latest.run_id_v14!==expected)return;record=body.data;$('reviewStatusV14').textContent=JSON.stringify(record,null,2);$('reviewExportV14').disabled=false;}catch(e){$('reviewStatusV14').textContent=e.message;}}
 $('reviewDoneV14').onclick=()=>submit('reviewed_demo_only');$('reviewHoldV14').onclick=()=>submit('held');$('reviewExportV14').onclick=()=>{if(!record)return;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));a.download='cfrp_review_v14.json';a.click();URL.revokeObjectURL(a.href);};
})();
