// [NEW v19] Immediate SVG visualization of verified solver arrays; no WebGL required.
(() => {
  let result=null,frame=0,timer=null;
  const panel=document.createElement('section');panel.className='card';panel.id='liveViewV19';
  panel.style.marginBottom='14px';
  panel.innerHTML=`<h2>계산 결과 · 실시간 시각화</h2>
  <p class="sub">AI·수동·실측 계산이 끝나면 자동 갱신합니다. 재생은 계산된 저장 시점을 순서대로 보여줍니다.</p>
  <div id="liveSummaryV19" class="badge-row" aria-live="polite">계산 결과 대기</div>
  <div class="actions"><button id="livePlayV19" class="secondary" type="button">재생</button><button id="livePeakV19" class="secondary" type="button">최고온도 시점</button>
  <select id="liveFieldV19" aria-label="단면 색상" style="width:auto"><option value="temperature">온도 °C</option><option value="difference">공기 대비 온도차 °C</option><option value="cure">경화도 α</option></select></div>
  <label for="liveTimeV19">시간 이동 · 기존 시간 탐색과 연동</label><input id="liveTimeV19" type="range" min="0" max="0" value="0" step="1">
  <div id="liveReadoutV19" class="raw">현재 계산 결과가 없습니다.</div>
  <div class="chart-grid" style="margin-top:12px"><div id="liveSectionV19"></div><div id="liveHistoryV19"></div></div>
  <div id="liveHeatmapV19" style="margin-top:12px"></div>
  <p class="file-note">단면은 실제 1D 두께 셀을 표시합니다. 금형은 회색으로 표시하며 셀 온도를 적습니다. 온도장은 저장 시점을 최대 120개로 줄여 표시합니다. 외부 실험 검증 전 결과입니다.</p>`;
  $('aiChatPanel').after(panel);
/* [NEW v29] Visual palette only. */   const style=document.createElement('style');style.textContent='#liveViewV19 svg{display:block;width:100%;height:auto;background:#ffffff;border:1px solid #E2E8F0;border-radius:10px}#liveViewV19 .chart-grid>div{min-width:0}#liveViewV19 [hidden]{display:none}';document.head.appendChild(style);
  const ids=['livePlayV19','livePeakV19','liveTimeV19','liveFieldV19'];
  const fmt=(v=null,d=null)=>v===null||v===undefined?'—':Number(v).toFixed(d===null?2:d);
  const svg=(body=null,w=null,h=null)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img">${body}</svg>`;
/* [NEW v29] Visual palette only. */   const text=(x=null,y=null,value=null)=>`<text x="${x}" y="${y}" fill="#334155" font-size="12">${value}</text>`;
/* [NEW v29] Visual palette only. */   const line=(x1=null,y1=null,x2=null,y2=null,color=null)=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color||'#E2E8F0'}"/>`;
  const rect=(x=null,y=null,w=null,h=null,color=null)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${color}"/>`;
  function bounds(r=null,mode=null){if(mode==='cure')return [0,1];let lo=Infinity,hi=-Infinity;for(let i=0;i<r.field.T_part.length;i++)for(const value of r.field.T_part[i]){const v=mode==='difference'?value-r.series.T_air[i]:value;lo=Math.min(lo,v);hi=Math.max(hi,v);}if(mode==='difference'){const m=Math.max(3,Math.abs(lo),Math.abs(hi));return [-m,m];}return [lo,Math.max(lo+1,hi)];}
  function color(v=null,range=null){const q=Math.max(0,Math.min(1,(v-range[0])/(range[1]-range[0])));return `hsl(${225*(1-q)},78%,${43+8*q}%)`;}
  function values(i=null){const mode=$('liveFieldV19').value;return mode==='cure'?result.field.alpha_part[i]:result.field.T_part[i].map(v=>mode==='difference'?v-result.series.T_air[i]:v);}
  let range=null;
  function section(){const f=result.field,s=result.series,vals=values(frame),n=vals.length,tool=f.T_tool[frame],nt=tool.length;let b=text(14,22,'CFRP 단면 · 상면 → 금형측');
    b+=text(14,42,`공기 ${fmt(s.T_air[frame])} °C · 두께 ${fmt(result.condition.thickness)} mm`);
    const top=60,height=220;
    for(let j=0;j<n;j++){const y=top+height*j/n;b+=rect(30,y,180,height/n+.2,color(vals[j],range));if(j===0||j===Math.floor(n/2)||j===n-1)b+=text(224,y+height/n/2+4,`${fmt(f.z_part[j])} mm / ${fmt(vals[j],$('liveFieldV19').value==='cure'?3:1)}`);}
    b+=text(30,300,`색 범위 ${fmt(range[0],1)} ~ ${fmt(range[1],1)} · 전체 이력 공통`);
    for(let j=0;j<nt;j++)b+=rect(30,312+42*j/nt,180,42/nt+.2,'#6b7789');
    b+=text(224,328,`금형 접촉 ${fmt(s.T_tool_interface_surface[frame],1)} °C`)+text(224,347,`금형 외면 ${fmt(s.T_tool_outer_surface[frame],1)} °C`);
    b+=text(14,377,'최저 경화도 α '+fmt(s.alpha_min[frame],4));$('liveSectionV19').innerHTML=svg(b,460,395);
  }
  function history(){const s=result.series,t=s.t,start=t[0],end=t.at(-1),dt=Math.max(1e-9,end-start);let min=Infinity,max=-Infinity;for(const row of [s.T_air,s.T_part_center])for(const v of row){min=Math.min(min,v);max=Math.max(max,v);}max=Math.max(min+1,max);const xx=v=>48+350*(v-start)/dt,yy=v=>270-210*(v-min)/(max-min);let b=text(14,22,'온도·경화 이력');
    for(let q=0;q<5;q++){const v=min+(max-min)*q/4,y=yy(v);b+=line(48,y,398,y)+text(6,y+4,fmt(v,0));}b+=text(12,44,'°C')+text(403,44,'α');
    for(let q=0;q<3;q++)b+=text(403,274-q*105,fmt(q/2,1));
/* [NEW v29] Visual palette only. */     for(const [row,c,cure] of [[s.T_air,'#97a9bf',false],[s.T_part_center,'#38825A',false],[s.alpha_min,'#B7791F',true]]){const points=row.map((v,i)=>`${xx(t[i])},${cure?270-210*v:yy(v)}`).join(' ');b+=`<polyline fill="none" stroke="${c}" stroke-width="2" points="${points}"/>`;}
/* [NEW v29] Visual palette only. */     b+=line(xx(t[frame]),56,xx(t[frame]),270,'#64748B')+text(48,293,fmt(start,1))+text(344,293,fmt(end,1)+' min');
    b+=text(14,324,'회색: 공기 · 녹색: 중앙 °C')+text(14,347,'주황: 최저 경화도 α (오른쪽 축)');$('liveHistoryV19').innerHTML=svg(b,460,395);
  }
  function heatmap(){const t=result.series.t,n=result.field.z_part.length,count=Math.min(120,t.length);let b=text(14,22,'시간 × 두께 온도장 · 선택한 색상');
    for(let q=0;q<count;q++){const i=Math.round(q*(t.length-1)/Math.max(1,count-1)),vals=values(i);for(let j=0;j<n;j++)b+=rect(60+800*q/count,42+150*j/n,800/count+.3,150/n+.3,color(vals[j],range));}
    b+=text(12,56,'상면')+text(12,189,'금형측')+text(60,215,fmt(t[0],1)+' min')+text(790,215,fmt(t.at(-1),1)+' min');
    b+='<line id="liveHeatCursorV19" x1="60" x2="60" y1="40" y2="193" stroke="white" stroke-width="2"/>';$('liveHeatmapV19').innerHTML=svg(b,920,238);
  }
  function show(){if(!result)return;const s=result.series;$('liveTimeV19').value=frame;$('liveReadoutV19').textContent=`시간 ${fmt(s.t[frame])} min · 공기 ${fmt(s.T_air[frame])} °C\n상면 ${fmt(s.T_part_top_surface[frame])} °C · 중앙 ${fmt(s.T_part_center[frame])} °C · 하면 ${fmt(s.T_part_bottom_surface[frame])} °C · 최저 α ${fmt(s.alpha_min[frame],4)}`;section();history();const c=$('liveHeatCursorV19');if(c){const x=60+800*frame/Math.max(1,s.t.length-1);c.setAttribute('x1',x);c.setAttribute('x2',x);}}
  function stop(){if(timer)clearInterval(timer);timer=null;$('livePlayV19').textContent='재생';}
  function clear(){stop();result=null;ids.forEach(id=>$(id).disabled=true);$('liveSummaryV19').textContent='현재 계산 결과 없음';$('liveReadoutV19').textContent='입력 변경 후 다시 계산하십시오.';for(const id of ['liveSectionV19','liveHistoryV19','liveHeatmapV19'])$(id).replaceChildren();}
  function move(i=null){if(!result)return;frame=Math.max(0,Math.min(result.series.t.length-1,i));$('timeSlider').value=frame;$('timeSlider').dispatchEvent(new Event('input'));show();}
  window.moveLiveViewV19=(r=null,i=null)=>{if(r!==result)return;frame=i;show();};
  window.updateLiveViewV19=(r=null)=>{clear();if(!r)return;result=r;frame=nearestIndex(r.series.t,r.summary.peak_time);range=bounds(r,$('liveFieldV19').value);ids.forEach(id=>$(id).disabled=false);$('liveTimeV19').max=r.series.t.length-1;const s=r.summary;$('liveSummaryV19').textContent=`최고 ${fmt(s.Tmax)} °C · ΔT ${fmt(s.delta_Tmax)} °C · 최저 α ${fmt(s.final_DoC,4)} · 공정시간 ${fmt(s.cycle_time,1)} min`;heatmap();show();};
  // [NEW v19] Reuse original invalidation, including manual edits and failed AI requests.
  const originalClear=window.clearTemperatureView;window.clearTemperatureView=()=>{clear();if(originalClear)originalClear();};
  $('liveTimeV19').oninput=()=>{stop();move(Number($('liveTimeV19').value));};
  $('livePeakV19').onclick=()=>{stop();if(result)move(nearestIndex(result.series.t,result.summary.peak_time));};
  $('liveFieldV19').onchange=()=>{if(!result)return;range=bounds(result,$('liveFieldV19').value);heatmap();show();};
  $('livePlayV19').onclick=()=>{if(timer)return stop();if(!result)return;if(frame>=result.series.t.length-1)move(0);$('livePlayV19').textContent='일시정지';timer=setInterval(()=>{if(!result||frame>=result.series.t.length-1)return stop();move(frame+1);},250);};
  clear();if(latest)window.updateLiveViewV19(latest);
})();
