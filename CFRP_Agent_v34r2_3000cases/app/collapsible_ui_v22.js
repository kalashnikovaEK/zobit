// [NEW v27] Current UI transplanted onto the uploaded 700-case version.
// [NEW v22] Reuse the disclosure UI, replacing only the previous presentation.
window.useFloatingStudioV22=true;
// [NEW v20] Add disclosure/layout only, after all v19 extensions have initialized.
// Existing forms, models, candidates, measured histories, review and visualization keep their nodes/listeners.
(()=>{
  const byId=id=>document.getElementById(id),layout=document.querySelector('.layout'),sidebar=document.querySelector('.controls'),chat=byId('aiChatPanel');
  if(!layout||!sidebar||!chat)return;
  const style=document.createElement('style');style.textContent=`
  .layout{grid-template-columns:360px minmax(0,1fr)}.controls{position:static;padding:0;background:transparent;border:0;box-shadow:none;min-width:0}.layout>section{min-width:0}
  .v20-fold{margin:0 0 14px;border:1px solid var(--line);border-radius:14px;padding:0;background:var(--panel);overflow:hidden}
  .v20-fold>summary{list-style:none;margin:0;padding:16px;display:flex;align-items:center;gap:12px}.v20-fold>summary::-webkit-details-marker{display:none}
  .v20-fold>summary:before{content:'›';color:var(--accent);font-size:24px;transition:transform .15s}.v20-fold[open]>summary:before{transform:rotate(90deg)}
  .v20-fold>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-3px}.v20-title{flex:1;min-width:0}.v20-title strong{display:block;font-size:16px}
  .v20-caption,.v20-status{display:block;font-size:12px;font-weight:400;color:var(--muted);margin-top:5px;overflow-wrap:anywhere}.v20-hint{font-size:11px;color:var(--accent);white-space:nowrap}
  .v20-body{padding:0 16px 16px}.v20-body>h2{display:none}.controls #aiChatPanel{padding:0;margin:0!important;border:0;box-shadow:none;background:transparent}
  .v20-body .actions button{font-size:13px}.v20-body .file-note{line-height:1.7}.v20-model>section{padding:0;background:transparent;border:0;box-shadow:none;margin:0!important}.v20-model h2{display:none}
  .layout.v20-compact{grid-template-columns:minmax(0,1fr)}.v20-compact>.controls{display:grid;grid-template-columns:1fr 1fr;gap:14px}.v20-compact .v20-fold{margin-bottom:0}
  @media(max-width:1150px){.layout{grid-template-columns:minmax(0,1fr)}.controls{display:block}}
  @media(max-width:760px){.v20-compact>.controls{grid-template-columns:minmax(0,1fr)}}`;
  document.head.appendChild(style);
  const folds=[];let resizeFrame=null;
  function resize(){layout.classList.toggle('v20-compact',folds.length===2&&folds.every(f=>!f.open));if(resizeFrame!==null)cancelAnimationFrame(resizeFrame);
    resizeFrame=requestAnimationFrame(()=>{resizeFrame=null;if(!window.Plotly)return;document.querySelectorAll('.js-plotly-plot').forEach(p=>{if(!p.offsetWidth||!p.data)return;try{Promise.resolve(Plotly.Plots.resize(p)).catch(()=>{});}catch(_){}});});
  }
  function fold(parent,id,title,defaultOpen){
    const d=document.createElement('details');d.id=id;d.className='v20-fold';
    const summary=document.createElement('summary'),text=document.createElement('span'),heading=document.createElement('strong'),caption=document.createElement('span'),hint=document.createElement('span');
    text.className='v20-title';heading.id=id+'Title';heading.textContent=title;caption.id=id+'Caption';caption.className='v20-caption';hint.className='v20-hint';text.append(heading,caption);summary.append(text,hint);
    const body=document.createElement('div');body.className='v20-body';while(parent.firstChild)body.appendChild(parent.firstChild);d.append(summary,body);parent.appendChild(d);
    let saved=null;try{saved=localStorage.getItem('cfrp.v20.'+id);}catch(_){}d.open=saved===null?defaultOpen:saved==='open';hint.textContent=d.open?'접기':'펼치기';
    d.addEventListener('toggle',()=>{hint.textContent=d.open?'접기':'펼치기';try{localStorage.setItem('cfrp.v20.'+id,d.open?'open':'closed');}catch(_){}resize();});folds.push(d);return d;
  }
  const process=fold(sidebar,'processFoldV20','기본 공정 입력',false);
  const status=document.createElement('span');status.id='foldStatusV20';status.className='v20-status';process.querySelector('.v20-title').appendChild(status);
  sidebar.prepend(chat);const chatFold=fold(chat,'chatFoldV20','AI 채팅 · 로컬 모델',true);
  // Model configuration belongs to the request panel; preserve model selection/health handlers.
  const model=byId('modelProfile'),modelCard=model&&model.closest('section');
  if(modelCard){const settings=document.createElement('details');settings.className='v20-model';settings.id='modelSettingsV20';const title=document.createElement('summary');title.textContent='모델 선택 · 연결 확인';settings.append(title,modelCard);chatFold.querySelector('.v20-body').prepend(settings);}
  // Keep summary metrics first, followed by the v19 instant view, candidates and original plots.
  const results=layout.querySelector(':scope > section:last-child'),metrics=results.querySelector('.metrics');if(metrics)results.prepend(metrics);
  // [NEW v20] Keep current result qualification beside the summary metrics.
  if(metrics&&byId('badges'))metrics.after(byId('badges'));
  function setText(e,text){if(e.textContent!==text)e.textContent=text;}
  function conditionCaption(){const value=id=>{const e=byId(id);return e&&e.value!==''?Number(e.value).toLocaleString('ko-KR',{maximumFractionDigits:2}):'—';};
    setText(byId('processFoldV20Caption'),`두께 ${value('thickness')} mm · 1차 ${value('T1')}°C / ${value('hold1')}분 · 2차 ${value('T2')}°C / ${value('hold2')}분`);setText(status,byId('status').textContent);
  }
  function chatCaption(){const name=model&&model.selectedOptions.length?model.selectedOptions[0].textContent:'로컬 모델';setText(byId('chatFoldV20Title'),'AI 채팅 · '+name);
    const sending=byId('chatSend').disabled,history=byId('chatHistory').textContent;
    setText(byId('chatFoldV20Caption'),sending?'AI 실행 중 · 접어도 계속 진행합니다':history?'대화 유지됨 · 펼쳐서 결과 확인':'자연어로 공정을 분석하고 조건을 탐색하세요');
  }
  for(const event of ['input','change'])byId('simForm').addEventListener(event,conditionCaption);
  new MutationObserver(conditionCaption).observe(byId('status'),{childList:true,subtree:true,characterData:true});
  new MutationObserver(chatCaption).observe(chat,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['disabled']});
  if(model)model.addEventListener('change',chatCaption);
  conditionCaption();chatCaption();resize();
})();
