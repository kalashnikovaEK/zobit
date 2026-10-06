// [NEW v27] Current UI transplanted onto the uploaded 700-case version.
// [NEW v28] Open navigation must remain above floating user and graph windows.
(()=>{const style=document.createElement('style');style.textContent='.menu-v23{z-index:2147483647!important}';document.head.append(style);})();
// [NEW v23] Hierarchical navigation reuses existing nodes and calculation handlers.
(()=>{
 const $=id=>document.getElementById(id),results=$('studioResultsV21'),brand=document.querySelector('.studio-brand');
 if(!results||!brand)return;
 const style=document.createElement('style');style.textContent=`
 .studio-brand{display:flex;align-items:center;gap:10px}.menu-toggle-v23{padding:5px 10px;font-size:14px;background:#1a304a;color:#dce8f5}
 .menu-v23{position:fixed;top:52px;left:12px;width:min(330px,calc(100vw - 24px));max-height:calc(100dvh - 64px);overflow:auto;z-index:90;background:#101d2f;border:1px solid #466580;border-radius:12px;padding:14px;box-shadow:0 16px 40px #0009}
 .menu-v23[hidden],.view-v23[hidden]{display:none!important}.menu-v23 details{margin:0 0 10px;padding:8px 0}.menu-v23 button{display:block;width:100%;text-align:left;background:transparent;color:#b8c5d6;font-size:13px;padding:9px 12px;margin:3px 0;border-radius:7px}.menu-v23 button[aria-current=true]{background:#23465c;color:#55dfbf}
 .view-heading-v23{font-size:16px;margin:8px 0 12px;color:#dce7f4}.view-v23>.card{margin-bottom:12px}.menu-v23 summary{font-size:15px}.menu-note-v23{color:#97a9bf;font-size:12px;margin:0 0 10px}
 `;document.head.append(style);
 const toggle=document.createElement('button');toggle.type='button';toggle.className='menu-toggle-v23';toggle.textContent='☰';toggle.setAttribute('aria-label','목록');toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls','studioMenuV23');brand.prepend(toggle);
 const menu=document.createElement('nav');menu.id='studioMenuV23';menu.className='menu-v23';menu.hidden=true;menu.setAttribute('aria-label','화면 목록');document.body.append(menu);
 const groups=[['시각화',[
 ['process','물리 계산 결과 & 3D 공정 뷰어',$('vizPanelV20')],
 ['live','계산 결과 & 실시간 시각화',$('liveViewV19')],
 ['history','온도 & 경화',$('tempChart').closest('.card')],
 ['depth','시간 탐색 & 내부온도 직육면체',$('tvCuboid').closest('section')]
 ]],['사용자',[
 ['candidates','검증 후보 비교',$('candidateChoiceV14').closest('section')],
 ['measured','실측 경계 이력 계산',$('measuredFileV14').closest('section')],
 ['review','현재 결과 검토 기록',$('reviewerV14').closest('section')]
 ]]];
 const heading=document.createElement('h2');heading.className='view-heading-v23';results.querySelector('.studio-tools').after(heading);
 const pages=[],buttons=[];
 function showMenu(open=null){menu.hidden=!open;toggle.setAttribute('aria-expanded',String(!!open));}
 function select(key=null){
  for(const page of pages)page.el.hidden=page.key!==key;
  for(const button of buttons)button.el.setAttribute('aria-current',String(button.key===key));
  heading.textContent=pages.find(p=>p.key===key).title;results.scrollTop=0;
  // Stop existing playback before leaving a view; keep data and open graph windows.
  if($('vizPauseV20'))$('vizPauseV20').click();for(const id of ['livePlayV19','tvPlay'])if($(id)&&$(id).textContent==='일시정지')$(id).click();
  requestAnimationFrame(()=>{if(window.Plotly)results.querySelectorAll('.js-plotly-plot').forEach(p=>{if(p.offsetWidth)try{Promise.resolve(Plotly.Plots.resize(p)).catch(()=>{});}catch(_){}});});
 }
 for(const [title,items] of groups){const group=document.createElement('details');group.open=true;const summary=document.createElement('summary');summary.textContent=title;group.append(summary);menu.append(group);
  for(const [key,label,node] of items){if(!node)continue;const page=document.createElement('div');page.className='view-v23';page.id='viewV23-'+key;page.append(node);results.append(page);pages.push({key,title:label,el:page});
   const button=document.createElement('button');button.type='button';button.textContent=label;button.setAttribute('aria-controls',page.id);button.onclick=()=>{select(key);showMenu(false);};group.append(button);buttons.push({key,el:button});}
 }
 toggle.onclick=()=>showMenu(menu.hidden);menu.addEventListener('keydown',e=>{if(e.key==='Escape'){showMenu(false);toggle.focus();}});
 document.addEventListener('pointerdown',e=>{if(!menu.hidden&&!menu.contains(e.target)&&!toggle.contains(e.target))showMenu(false);});
 select('process');
})();

// [NEW v26] Adjustable right pane; independent of form disclosure state.
(()=>{
 const layout=document.querySelector('.layout'),side=document.getElementById('studioSideV21'),brand=document.querySelector('.studio-brand');if(!side)return;
 let width=360,collapsed=false,frame=null;
 try{const value=Number(localStorage.getItem('cfrp.side.width.v26'));if(value>=260)width=value;collapsed=localStorage.getItem('cfrp.side.closed.v26')==='true';}catch(_){}
 const style=document.createElement('style');style.textContent=`.layout.side-adjust-v26,.layout.side-adjust-v26.v20-compact{position:relative;grid-template-columns:minmax(0,1fr) var(--side-width-v26);gap:14px}.side-adjust-v26.side-closed-v26{grid-template-columns:minmax(0,1fr)!important}.side-closed-v26 #studioSideV21{display:none!important}.side-handle-v26{position:absolute;top:0;bottom:0;right:calc(var(--side-width-v26) + 2px);width:10px;cursor:col-resize;touch-action:none;border:0;background:#29405b66;border-radius:5px;z-index:8}.side-handle-v26:hover,.side-handle-v26:focus{background:#55dfbf88}.side-closed-v26 .side-handle-v26{display:none}.side-toggle-v26{margin-left:auto;padding:5px 10px;background:#1a304a;color:#dce8f5;font-size:12px}.studio-brand{flex-wrap:wrap}@media(max-width:600px){.layout.side-adjust-v26,.layout.side-adjust-v26.v20-compact{grid-template-columns:minmax(0,1fr);grid-template-rows:minmax(0,1.1fr) minmax(0,1fr)}.side-handle-v26{display:none}.side-adjust-v26.side-closed-v26{grid-template-rows:minmax(0,1fr)}}`;document.head.append(style);layout.classList.add('side-adjust-v26');
 const toggle=document.createElement('button');toggle.type='button';toggle.className='side-toggle-v26';toggle.setAttribute('aria-controls',side.id);brand.append(toggle);
 const handle=document.createElement('div');handle.className='side-handle-v26';handle.tabIndex=0;handle.setAttribute('role','separator');handle.setAttribute('aria-label','오른쪽 패널 폭 조절');handle.setAttribute('aria-orientation','vertical');layout.append(handle);
 function maximum(){return Math.max(260,Math.min(720,layout.clientWidth-260));}
 function refresh(){layout.style.setProperty('--side-width-v26',Math.max(260,Math.min(width,maximum()))+'px');layout.classList.toggle('side-closed-v26',collapsed);toggle.textContent=collapsed?'AI·입력 펼치기':'AI·입력 접기';toggle.setAttribute('aria-expanded',String(!collapsed));handle.setAttribute('aria-valuemin','260');handle.setAttribute('aria-valuemax',String(maximum()));handle.setAttribute('aria-valuenow',String(Math.max(260,Math.min(width,maximum()))));if(frame!==null)cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{frame=null;if(window.Plotly)layout.querySelectorAll('.js-plotly-plot').forEach(p=>{if(p.offsetWidth)try{Promise.resolve(Plotly.Plots.resize(p)).catch(()=>{});}catch(_){}});});}
 function save(){try{localStorage.setItem('cfrp.side.width.v26',String(width));localStorage.setItem('cfrp.side.closed.v26',String(collapsed));}catch(_){}}
 toggle.onclick=()=>{collapsed=!collapsed;refresh();save();};
 handle.addEventListener('pointerdown',e=>{e.preventDefault();const start=e.clientX,initial=Math.min(width,maximum());handle.setPointerCapture(e.pointerId);const move=v=>{width=Math.max(260,Math.min(maximum(),initial+start-v.clientX));refresh();},end=()=>{handle.removeEventListener('pointermove',move);handle.removeEventListener('pointerup',end);handle.removeEventListener('pointercancel',end);save();};handle.addEventListener('pointermove',move);handle.addEventListener('pointerup',end);handle.addEventListener('pointercancel',end);});
 handle.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();width=e.key==='Home'?260:e.key==='End'?maximum():Math.max(260,Math.min(maximum(),Math.min(width,maximum())+(e.key==='ArrowLeft'?20:-20)));refresh();save();});window.addEventListener('resize',refresh);refresh();
})();

// [NEW v25] User sections open as independent windows with their original controls.
(()=>{
 const menu=document.getElementById('studioMenuV23');if(!menu)return;
 const openWindows=new Map();let z=2000;
 const style=document.createElement('style');style.textContent=`.user-window-v25{position:fixed;display:flex;flex-direction:column;left:20px;top:70px;width:min(660px,calc(100vw - 24px));height:min(500px,calc(100dvh - 90px));min-width:260px;min-height:200px;max-width:calc(100vw - 12px);max-height:calc(100dvh - 60px);resize:both;overflow:hidden;background:#0d1929;border:1px solid #466580;border-radius:12px;box-shadow:0 20px 65px #0009}.user-window-v25 .user-bar-v25{display:flex;gap:10px;align-items:center;padding:10px;background:#1a3047;cursor:move;touch-action:none}.user-bar-v25 strong{flex:1;font-size:14px}.user-bar-v25 button{padding:5px 10px;font-size:12px}.user-body-v25{overflow:auto;flex:1;min-height:0;padding:12px}.user-body-v25>.card{margin:0!important}.user-body-v25 .studio-source{position:relative!important}`;document.head.append(style);
 function resizePlots(panel=null){requestAnimationFrame(()=>{if(window.Plotly)panel.querySelectorAll('.js-plotly-plot').forEach(p=>{if(p.offsetWidth)try{Promise.resolve(Plotly.Plots.resize(p)).catch(()=>{});}catch(_){}});});}
 for(const key of ['candidates','measured','review']){
  const page=document.getElementById('viewV23-'+key),button=menu.querySelector('[aria-controls="'+page.id+'"]');
  button.addEventListener('click',event=>{
   event.preventDefault();event.stopImmediatePropagation();menu.hidden=true;document.querySelector('.menu-toggle-v23').setAttribute('aria-expanded','false');
   const current=openWindows.get(key);if(current){current.style.zIndex=++z;current.querySelector('button').focus();return;}
   const content=page.firstElementChild;if(!content)return;
   const panel=document.createElement('section');panel.className='user-window-v25';panel.setAttribute('role','dialog');panel.setAttribute('aria-label',button.textContent+' 창');panel.style.zIndex=++z;panel.style.left=Math.min(24+openWindows.size*24,Math.max(6,innerWidth-Math.min(660,innerWidth-24)-6))+'px';panel.style.top=70+openWindows.size*24+'px';
   const bar=document.createElement('div');bar.className='user-bar-v25';bar.tabIndex=0;const title=document.createElement('strong');title.textContent=button.textContent;const close=document.createElement('button');close.type='button';close.className='secondary';close.textContent='닫기';close.setAttribute('aria-label',button.textContent+' 창 닫기');bar.append(title,close);
   const body=document.createElement('div');body.className='user-body-v25';body.append(content);panel.append(bar,body);document.body.append(panel);openWindows.set(key,panel);
   const observer=new ResizeObserver(()=>resizePlots(panel));observer.observe(body);
   function shut(){observer.disconnect();page.append(content);panel.remove();openWindows.delete(key);button.focus({preventScroll:true});}
   close.onclick=shut;panel.addEventListener('pointerdown',()=>panel.style.zIndex=++z);panel.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();shut();}});
   function place(x=null,y=null){panel.style.left=Math.max(4,Math.min(x,innerWidth-panel.getBoundingClientRect().width-4))+'px';panel.style.top=Math.max(42,Math.min(y,innerHeight-60))+'px';}
   bar.addEventListener('keydown',e=>{if(e.target!==bar||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();const r=panel.getBoundingClientRect();place(r.x+(e.key==='ArrowLeft'?-10:e.key==='ArrowRight'?10:0),r.y+(e.key==='ArrowUp'?-10:e.key==='ArrowDown'?10:0));});
   bar.addEventListener('pointerdown',e=>{if(e.target.closest('button'))return;const r=panel.getBoundingClientRect(),x=e.clientX,y=e.clientY;bar.setPointerCapture(e.pointerId);const move=v=>place(r.x+v.clientX-x,r.y+v.clientY-y),end=()=>{bar.removeEventListener('pointermove',move);bar.removeEventListener('pointerup',end);bar.removeEventListener('pointercancel',end);};bar.addEventListener('pointermove',move);bar.addEventListener('pointerup',end);bar.addEventListener('pointercancel',end);});
   resizePlots(panel);close.focus({preventScroll:true});
  },true);
 }
})();
