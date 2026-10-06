// [NEW v14] v09b HTML geometry imported into the time/depth inspector.
/* [NEW v29] Visual palette only. */ const V3D={L:300,W:200,M:22,EX:4,PLY:.18,SEC:.3,MIN_DEV:3,BG:'#ffffff',INK:'#334155',MUTED:'#64748B',GRAY:'#6b7789',
 DEV:[[0,'#1d4f9a'],[.22,'#4f86d6'],[.42,'#b9cbe4'],[.5,'#e4e7ec'],[.58,'#f2c6a2'],[.78,'#ec7f3f'],[1,'#c2361a']],
 CURE:[[0,'#14294a'],[.3,'#1b4f8f'],[.55,'#2f73c9'],[.78,'#5d9ae6'],[.92,'#9cc2f0'],[1,'#dbe9fb']],geo:null};
const V3D_FACES=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]];
function v3dBoxes(edges,x0,x1,y0,y1){const m={x:[],y:[],z:[],i:[],j:[],k:[],layer:[]};
 for(let li=0;li<edges.length-1;li++){const z0=edges[li],z1=edges[li+1],n=m.x.length;m.x.push(x0,x1,x1,x0,x0,x1,x1,x0);m.y.push(y0,y0,y1,y1,y0,y0,y1,y1);m.z.push(z0,z0,z0,z0,z1,z1,z1,z1);for(let q=0;q<8;q++)m.layer.push(li);for(const [a,b,c] of V3D_FACES){m.i.push(n+a);m.j.push(n+b);m.k.push(n+c);}}return m;}
function v3dGeometry(r){const th=r.condition.thickness,tool=r.options.tool_thickness_mm||0,nz=r.field.T_part[0].length,nt=r.field.T_tool[0].length,H=th+tool,L=V3D.L,W=V3D.W,M=V3D.M,Y0=W*V3D.SEC;
 const comp=[];for(let q=0;q<=nz;q++)comp.push(tool+th*q/nz);const tl=[];for(let q=0;q<=nt;q++)tl.push(tool*q/nt);
 let m=V3D.MIN_DEV;const air=r.series.T_air;r.field.T_part.forEach((row,t)=>row.forEach(v=>{m=Math.max(m,Math.abs(v-air[t]))}));r.field.T_tool.forEach((row,t)=>row.forEach(v=>{m=Math.max(m,Math.abs(v-air[t]))}));m=Math.ceil(m);
 const lx=[],ly=[],lz=[];const box=(x0,x1,y0,y1,z0,z1)=>{for(const zz of [z0,z1]){lx.push(x0,x1,x1,x0,x0,null);ly.push(y0,y0,y1,y1,y0,null);lz.push(zz,zz,zz,zz,zz,null);}for(const [cx,cy] of [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]){lx.push(cx,cx,null);ly.push(cy,cy,null);lz.push(z0,z1,null);}};
 box(0,L,Y0,W,tool,H);if(tool>0)box(-M,L+M,Y0,W+M,0,tool);
 const step=V3D.PLY*Math.max(1,Math.round(1/V3D.PLY)),px=[],py=[],pz=[];for(let h=tool+step;h<H-step*.5;h+=step){px.push(0,L,null);py.push(Y0-.4,Y0-.4,null);pz.push(h,h,null);}
 return {th,tool,H,nz,nt,Y0,dev:m,comp:v3dBoxes(comp,0,L,Y0,W),toolm:v3dBoxes(tl,-M,L+M,Y0,W+M),lines:{x:lx,y:ly,z:lz},plies:{x:px,y:py,z:pz}};}
// [NEW v14] Cache both comparison geometries; optional render targets preserve inspector API.
const geometryCacheV14=new WeakMap();
function v3dCachedGeometryV14(r){if(!geometryCacheV14.has(r))geometryCacheV14.set(r,v3dGeometry(r));return geometryCacheV14.get(r);}
window.renderStackViewV14=function(r,i,target=null,sharedDev=null){if(!r||!r.field||!r.field.T_tool)return;const g=v3dCachedGeometryV14(r); /* [NEW v14] cache geometry per result */const f=($('tvField').value==='cure'?'alpha':'T');const s=r.series,air=s.T_air[i];
 const L=V3D.L,W=V3D.W,M=V3D.M,Y0=g.Y0;
 const compVals=(f==='alpha'?r.field.alpha_part[i].slice():r.field.T_part[i].map(v=>v-air)).reverse();
 const scale=f==='alpha'?V3D.CURE:V3D.DEV,cmin=f==='alpha'?0:-(sharedDev||g.dev),cmax=f==='alpha'?1:(sharedDev||g.dev),m=sharedDev||g.dev;
 const tA=s.T_part_bottom_surface[i],tB=s.T_part_center[i],tC=s.T_part_top_surface[i],ap=r.field.alpha_part[i],amid=Math.floor(ap.length/2);
 const sensorTxt=f==='alpha'?[`A 하면 α ${ap[ap.length-1].toFixed(3)}`,`B 중앙 α ${ap[amid].toFixed(3)}`,`C 상면 α ${ap[0].toFixed(3)}`]:[`A 하면 ${tA.toFixed(1)}°C`,`B 중앙 ${tB.toFixed(1)}°C`,`C 상면 ${tC.toFixed(1)}°C`];
 const hz=[g.tool+.02,g.tool+g.th/2,g.H-.02];
 const cbar=f==='alpha'?{title:{text:'경화도 α',side:'top'},thickness:12,len:.56,y:.42,outlinewidth:0,ticklabelposition:'outside bottom',x:.86,xanchor:'left'}
  :{title:{text:'공기 대비 온도차 °C',side:'top'},thickness:12,len:.56,y:.42,outlinewidth:0,ticklabelposition:'outside bottom',x:.86,xanchor:'left',tickvals:[-m,-m/2,0,m/2,m],ticktext:[`−${m} 공기보다 낮음`,`−${m/2}`,'0 공기와 같음',`+${m/2}`,`+${m} 공기보다 높음`]};
 const light={ambient:.78,diffuse:.5,specular:.06,roughness:.9,fresnel:.05};
 const zt=g.H+.35,zb=g.tool+.02,gg=3,ss=14;
 // [NEW v14] Depth cut exposes the selected cell and all cells below it.
 const cell=Number($("tvDepth").value),cut=$("tvCut").value==="cut";
 const edges=Array.from({length:g.nz-cell+1},(_,q)=>g.tool+g.th*q/g.nz);
 const visible=cut?v3dBoxes(edges,0,L,Y0,W):g.comp;
 const traces=[
  {type:'mesh3d',x:visible.x,y:visible.y,z:visible.z,i:visible.i,j:visible.j,k:visible.k,intensity:visible.layer.map(q=>compVals[q]),intensitymode:'vertex',colorscale:scale,cmin,cmax,flatshading:true,hoverinfo:'skip',colorbar:{...cbar,tickfont:{color:V3D.MUTED,size:11}},lighting:light,lightposition:{x:-200,y:-1200,z:900},name:'CFRP'},
  {type:'mesh3d',x:g.toolm.x,y:g.toolm.y,z:g.toolm.z,i:g.toolm.i,j:g.toolm.j,k:g.toolm.k,intensity:g.toolm.layer.map(()=>0),colorscale:[[0,V3D.GRAY],[1,V3D.GRAY]],cmin:0,cmax:1,showscale:false,flatshading:true,hoverinfo:'skip',lighting:light,name:'Invar'},
  {type:'mesh3d',x:[-gg,L+gg,L+gg,-gg,-ss,L+ss,L+ss,-ss],y:[Y0,Y0,W+gg,W+gg,Y0,Y0,W+ss,W+ss],z:[zt,zt,zt,zt,zb,zb,zb,zb],i:[0,0,1,1,2,2,3,3],j:[1,2,5,6,6,7,7,4],k:[2,3,6,2,7,3,4,0],color:'#cfe2fb',opacity:.13,flatshading:true,hoverinfo:'skip',lighting:{ambient:.9,diffuse:.2},name:'진공백'},
  {type:'scatter3d',...g.lines,mode:'lines',line:{color:'rgba(9,19,35,.9)',width:2.5},hoverinfo:'skip',showlegend:false},
  {type:'scatter3d',...g.plies,mode:'lines',line:{color:'rgba(9,19,35,.22)',width:1},hoverinfo:'skip',showlegend:false},
  {type:'scatter3d',x:[L*.5,L*.5,L*.5],y:[Y0-1,Y0-1,Y0-1],z:hz,mode:'markers',marker:{size:4.5,color:'#fff',line:{width:1.5,color:'#091323'}},hovertext:sensorTxt,hoverinfo:'text',showlegend:false}];
 // [NEW v14] Hide scenery and outlines above the cut plane; selected cell remains highlighted.
 if(cut){traces[2].visible=false;traces[3].visible=false;traces[4].visible=false;traces[5].visible=false;}
 const depthZ=g.H-r.field.z_part[cell];
 traces.push({type:"scatter3d",x:[0,L],y:[Y0-1,Y0-1],z:[depthZ,depthZ],mode:"lines",line:{color:"#55dfbf",width:5},name:"선택 셀",showlegend:false});
 const notes=[{x:L+M,y:W+M,z:g.tool+g.th*.5,text:`CFRP ${g.th} mm (≈${Math.round(g.th/V3D.PLY)} plies)`,showarrow:false,xanchor:'left',xshift:10,font:{color:V3D.INK,size:12}},
  {x:L+M,y:W+M,z:g.tool*.5,text:`Invar 금형 ${g.tool} mm`,showarrow:false,xanchor:'left',xshift:10,font:{color:V3D.MUTED,size:12}},
  {x:L*.78,y:W,z:g.H+.35,text:'진공백 · 오토클레이브 공기',showarrow:true,arrowcolor:V3D.MUTED,ax:30,ay:-34,font:{color:V3D.MUTED,size:11}},
/* [NEW v29] Visual palette only. */   ...hz.map((z,q)=>({x:L*.5,y:Y0-1,z,text:sensorTxt[q],showarrow:true,arrowcolor:'#334155',arrowwidth:1.2,arrowhead:0,ax:-120,ay:[34,0,-34][q],bgcolor:'rgba(248,250,252,.96)',bordercolor:'#DCE4EE',borderpad:3,font:{color:'#334155',size:12}}))];
 const hid={visible:false,showbackground:false,showgrid:false,zeroline:false,showspikes:false};
 const xr=L+2*M,yr=(W+M)-Y0,k=1.7/xr,amin=Math.min(...ap),dv=tB-air;
 if(!target||target==='tvCuboid')$('timeLabel').textContent=`${s.t[i].toFixed(1)} min · 공기 ${air.toFixed(1)}°C · 중앙 ${tB.toFixed(1)}°C (공기 대비 ${dv>=0?'+':'−'}${Math.abs(dv).toFixed(1)}) · 최저 α ${amin.toFixed(3)}`;
 // [NEW v19] A failed 3D render must explain the empty area.
 const targetId=target||'tvCuboid';
 const failed=()=>{const node=$(targetId);Plotly.purge(node);node.textContent='3D 표시를 사용할 수 없습니다. 위의 실시간 2D 단면에서 같은 계산값을 확인하십시오.';};
/* [NEW v29] Visual palette only. */  let rendered;try{rendered=Plotly.react(targetId,traces,{paper_bgcolor:V3D.BG,font:{color:'#334155'},margin:{l:0,r:0,t:10,b:0},showlegend:false,uirevision:'keep-camera',
  scene:{xaxis:{range:[-M-2,L+M+2],...hid},yaxis:{range:[Y0-4,W+M+2],...hid},zaxis:{range:[0,g.H*1.04+.5],...hid},aspectmode:'manual',aspectratio:{x:xr*k,y:(yr+6)*k,z:Math.max(g.H,1)*V3D.EX*k},
   camera:{eye:{x:.8,y:-1.4,z:1.0},up:{x:0,y:0,z:1},center:{x:.02,y:.04,z:-.14}},annotations:notes,bgcolor:V3D.BG,dragmode:'orbit',domain:{x:[0,.84],y:[0,1]}}},plotCfg);}catch(error){failed();return;}
 Promise.resolve(rendered).then(()=>{const node=$(targetId);if(node.on&&!node.webglWarningV19){node.webglWarningV19=true;node.on('plotly_webglcontextlost',failed);}}).catch(failed);}
