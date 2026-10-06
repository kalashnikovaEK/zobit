// [NEW v13] Chat on the existing HTML dashboard. All AI text uses textContent.
(() => {
  const panel=document.createElement('section');panel.className='card';panel.id='aiChatPanel';
  panel.style.marginBottom='18px';
  panel.innerHTML='<h2>AI 공정 채팅 · 선택한 로컬 모델</h2><p class="sub">현재 공정 입력과 제약을 기준으로 실행합니다. 각 요청에 목표와 수치를 명시해 주세요.</p><div id="chatHistory" aria-live="polite" style="max-height:280px;overflow:auto"></div><form id="chatForm"><label for="chatInput">자연어 요청</label><textarea id="chatInput" maxlength="4000" rows="3" required style="width:100%;background:#081522;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:12px;font:inherit" placeholder="AS4/8552 두께 10mm, 최고온도 200도 이하에서 승온속도·유지온도·유지시간 모두 최적화해서 공정시간을 최소화해줘"></textarea><div class="actions"><button type="submit" id="chatSend" class="primary">AI에게 보내기</button><button type="button" id="chatClear" class="secondary">대화 지우기</button></div></form><details><summary>AI 실행·검증 로그</summary><pre id="chatLog" class="raw"></pre></details><details><summary>해석과 적용 조건</summary><pre id="chatResult" class="raw"></pre></details>';
  document.querySelector('.layout > section:last-child').prepend(panel);
  let busy=false,revision=0;
  function message(role,text){const p=document.createElement('p');p.style.whiteSpace='pre-wrap';p.style.padding='10px';p.style.borderRadius='8px';p.style.background=role==='사용자'?'#183447':'#0b1928';p.textContent=role+' · '+text;$('chatHistory').appendChild(p);$('chatHistory').scrollTop=$('chatHistory').scrollHeight;return p;}
  function lock(value){busy=value;for(const id of ['chatInput','chatSend','chatClear','runBtn' /* [NEW v34] Freeze natural-language input during extraction. */,'resetBtn','loadJsonBtn','modelProfile','measuredRunV14','candidateChoiceV14'])if($(id))$(id).disabled=value;document.querySelectorAll('#simForm input:not(#jsonFileInput),#simForm select').forEach(el=>el.disabled=value);/* [NEW v14] No candidate choices before a verified response. */if(!value&&$('candidateChoiceV14'))$('candidateChoiceV14').disabled=!(window.hasCandidatesV14&&window.hasCandidatesV14());}
  // If a manual calculation/import starts later, never paint a stale chat result over it.
  $('simForm').addEventListener('input',()=>revision++);
  $('simForm').addEventListener('change',()=>revision++);
  $('simForm').addEventListener('submit',()=>revision++);
  $('resetBtn').addEventListener('click',()=>revision++);
  $('jsonFileInput').addEventListener('change',()=>revision++);
  $('chatClear').addEventListener('click',()=>{if(busy)return;$('chatHistory').replaceChildren();$('chatLog').textContent='';$('chatResult').textContent='';});
  $('chatForm').addEventListener('submit',async e=>{
    e.preventDefault();if(busy)return;
    const request=$('chatInput').value.trim();if(!request)return;
    const token=++revision;let acquired=false;message('사용자',request);const reply=message('AI','요청을 검증하고 있습니다…');
    $('chatLog').textContent='';$('chatResult').textContent='';
    try{
      if($('runBtn').disabled)throw new Error('물리 계산이 진행 중입니다. 완료 후 보내십시오.');
      const inputs=payload();lock(true);acquired=true;if(window.clearCandidatesV14)window.clearCandidatesV14();invalidateResults('AI 요청 실행 중…');
      const response=await fetch(API_BASE+'/api/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(window.chatBodyV34?window.chatBodyV34({request,inputs,profile:window.selectedModelProfileV14?window.selectedModelProfileV14():'gemma2'}):{request,inputs,profile:window.selectedModelProfileV14?window.selectedModelProfileV14():'gemma2'}) /* [NEW v34] */ /* [NEW v14] */});
      if(!response.ok){const body=await response.json();throw new Error(body.error||'AI 연결 실패');}
      const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',finished=false;
      function line(text){if(!text.trim())return;const item=JSON.parse(text);
        if(item.type==='event'){$('chatLog').textContent+=item.data.phase+' · '+item.data.status+'\n'+JSON.stringify(item.data.detail)+'\n';return;}
        if(item.type==='error')throw new Error(item.data.error);
        if(item.type==='result'){
          finished=true;const r=item.data;reply.textContent='AI · '+r.answer;
          $('chatResult').textContent=JSON.stringify({...r,display:undefined,baseline_display:undefined,candidate_displays:undefined},null,2);
          if(token!==revision){setStatus('입력이 변경되어 AI 그래프를 적용하지 않았습니다.','error');return;}
          // [NEW v14] Candidate selector receives every verified result and baseline.
          // [NEW v34] Only show confirmation UI for the exact guarded preview.
          if(r.status==='confirmation_required' && window.showChatPreviewV34){window.showChatPreviewV34(r);setStatus(' 해석 확인 대기 · 아직 계산하지 않았습니다.','run');return;}
          if(window.clearChatPreviewV34)window.clearChatPreviewV34();
          if(window.acceptCandidatesV14)window.acceptCandidatesV14(r);
          if(r.display){awaitPlot(r);}else{setStatus(r.status==='needs_clarification'?'요청을 구체적으로 적어 다시 보내십시오.':'AI 결과 표시 차단 · 채팅과 로그를 확인하십시오.','error');}
        }
      }
      function awaitPlot(r){
        latest=r.display;renderSummary(latest);renderCharts(latest);
        // [NEW v13] Optimizer fractions must remain valid for the original manual form.
        for(const [k,v] of Object.entries(latest.condition))if($(k)){$(k).value=v;$(k).step='any';}
        for(const [k,id] of Object.entries(LIMIT_IDS))$(id).value=r.limits[k];
        $('badges').appendChild(badge(r.display_source==='verified_recommendation'?'AI 물리 검증 통과 추천':'기준 계산만 표시 · 추천 없음',r.display_source==='verified_recommendation'?'good':'warn'));
        setStatus(r.display_source==='verified_recommendation'?'AI 검증 완료 · 첫 추천의 실제 물리 이력을 표시했습니다.':'기준 물리 이력 표시 · 추천 여부는 채팅 결과를 확인하십시오.','run');
      }
      while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true});let newline;while((newline=buffer.indexOf('\n'))>=0){line(buffer.slice(0,newline));buffer=buffer.slice(newline+1);}}
      buffer+=decoder.decode();if(buffer.trim())line(buffer);if(!finished)throw new Error('AI 응답이 완료되기 전에 연결이 종료되었습니다.');
    }catch(error){reply.textContent='AI · 실행 실패: '+error.message;if(acquired&&token===revision)invalidateResults('AI 실행 실패 · 이전 그래프 무효');else if(!acquired)setStatus(error.message,'error');}
    finally{if(acquired)lock(false);}
  });
})();

// [NEW v34] Explicit confirmation of the exact server-stored interpretation.
(() => {
 const box=document.createElement('section');box.id='chatPreviewV34';box.hidden=true;
 const title=document.createElement('h3');title.textContent='실행 전 해석 확인';
 const text=document.createElement('pre');text.className='raw';text.style.maxHeight='420px';
 const run=document.createElement('button');run.type='button';run.className='primary';run.textContent='해석 확인 · 계산 실행';
 const cancel=document.createElement('button');cancel.type='button';cancel.className='secondary';cancel.textContent='취소 · 요청 수정';
 box.append(title,text,run,cancel);$('chatForm').after(box);
 let pending=null,armed=false;
 const snapshot=()=>JSON.stringify({request:$('chatInput').value.trim(),inputs:payload(),profile:window.selectedModelProfileV14?window.selectedModelProfileV14():'gemma2'});
 window.clearChatPreviewV34=()=>{pending=null;armed=false;box.hidden=true;};
 window.showChatPreviewV34=r=>{pending={token:r.confirmation_token,snapshot:snapshot()};box.hidden=false;
 const p=r.preview;
 text.textContent='작업: '+p.action+'\n목표: '+p.target+'\n재료: '+p.material+'\n변경 변수: '+(p.change_labels.join(', ')||'없음')+'\n고정 변수: '+p.fixed_variables.join(', ')+'\n적용 수치 (°C, min, mm, °C/min):\n'+JSON.stringify(p.condition,null,2)+'\n제약: 최고온도 ≤ '+p.limits.Tmax+' °C / 온도편차 ≤ '+p.limits.delta_Tmax+' °C / 최종경화도 ≥ '+p.limits.final_DoC+'\n\n원문과 다르면 취소하고 요청을 수정하십시오.';
 };
 window.chatBodyV34=body=>{if(armed&&pending&&pending.snapshot===snapshot()){const token=pending.token;window.clearChatPreviewV34();return {...body,confirmation_token:token};}window.clearChatPreviewV34();return body;};
 run.addEventListener('click',()=>{if(!pending||pending.snapshot!==snapshot()){window.clearChatPreviewV34();setStatus('입력이 바뀌었습니다. 다시 요청하십시오.','error');return;}if($('chatSend').disabled)return;armed=true;$('chatForm').requestSubmit();});
 cancel.addEventListener('click',()=>{window.clearChatPreviewV34();$('chatInput').focus();});
 for(const id of ['chatInput','simForm','modelProfile'])if($(id))for(const event of ['input','change'])$(id).addEventListener(event,window.clearChatPreviewV34);
 for(const id of ['chatClear','resetBtn','loadJsonBtn','runBtn'])if($(id))$(id).addEventListener('click',window.clearChatPreviewV34);
})();
