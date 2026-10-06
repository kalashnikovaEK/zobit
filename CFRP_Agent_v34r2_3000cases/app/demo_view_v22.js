// [NEW v22] viz3d_demo display transplanted onto current verified solver arrays.
// Demo constants: cut-away front 30%, thickness x4, 0.18 mm illustrative ply spacing.
(() => {
/* [NEW v29] Visual palette only. */   const BG='#ffffff',INK='#334155',MUTED='#64748B';
  const fmt=(v=null,d=null)=>Number(v).toFixed(d===null?1:d);
  window.initializeDemoModeV22=()=>{const el=document.getElementById('vizModeV20');if(el)el.value='difference';};
  window.buildDemoPlotV22=(r=null,i=null,label=null,mode=null,range=null)=>{
    const g=v3dCachedGeometryV14(r),s=r.series,f=r.field,air=s.T_air[i],center=s.T_part_center[i];
    const L=V3D.L,W=V3D.W,M=V3D.M,Y0=g.Y0;
    const values=(mode==='cure'?f.alpha_part[i]:f.T_part[i].map(v=>mode==='difference'?v-air:v)).slice().reverse();
    // Keep a common, whole-history scale for baseline and selected result. Never clip data.
    let lo=range[0],hi=range[1];if(mode==='difference'){const extent=Math.ceil(Math.max(3,Math.abs(lo),Math.abs(hi)));lo=-extent;hi=extent;}
    const cbar={title:{text:mode==='cure'?'경화도 α':mode==='difference'?'공기 대비 온도차 °C':'온도 °C',side:'top'},thickness:12,len:.56,y:.42,outlinewidth:0,ticklabelposition:'outside bottom',x:.86,xanchor:'left',tickfont:{color:MUTED,size:11}};
    if(mode==='difference'){cbar.tickvals=[lo,lo/2,0,hi/2,hi];cbar.ticktext=[`${lo} 덜 데워짐`,`${lo/2}`,'0 공기와 같음',`+${hi/2}`,`+${hi} 공기보다 높음`];}
    const light={ambient:.78,diffuse:.5,specular:.06,roughness:.9,fresnel:.05};
    const zt=g.H+.35,zb=g.tool+.02,gg=3,ss=14;
    const alpha=f.alpha_part[i],hz=[g.tool+.02,g.tool+g.th/2,g.H-.02];
    const sensors=mode==='cure'?[alpha.at(-1),alpha[Math.floor(alpha.length/2)],alpha[0]]:[s.T_part_bottom_surface[i],center,s.T_part_top_surface[i]];
    const sensorText=sensors.map((v,q)=>`${['A 하면','B 중앙','C 상면'][q]} ${mode==='cure'?'α ':''}${fmt(v,mode==='cure'?3:1)}${mode==='cure'?'':'°C'}`);
    const traces=[
      {type:'mesh3d',x:g.comp.x,y:g.comp.y,z:g.comp.z,i:g.comp.i,j:g.comp.j,k:g.comp.k,intensity:g.comp.layer.map(q=>values[q]),intensitymode:'vertex',colorscale:mode==='cure'?V3D.CURE:mode==='difference'?V3D.DEV:'Turbo',cmin:lo,cmax:hi,flatshading:true,hoverinfo:'skip',colorbar:cbar,lighting:light,lightposition:{x:-200,y:-1200,z:900},name:'CFRP'},
      {type:'mesh3d',x:g.toolm.x,y:g.toolm.y,z:g.toolm.z,i:g.toolm.i,j:g.toolm.j,k:g.toolm.k,intensity:g.toolm.layer.map(()=>0),intensitymode:'vertex',colorscale:[[0,V3D.GRAY],[1,V3D.GRAY]],cmin:0,cmax:1,showscale:false,flatshading:true,hoverinfo:'skip',lighting:light,name:'Invar'},
      {type:'mesh3d',x:[-gg,L+gg,L+gg,-gg,-ss,L+ss,L+ss,-ss],y:[Y0,Y0,W+gg,W+gg,Y0,Y0,W+ss,W+ss],z:[zt,zt,zt,zt,zb,zb,zb,zb],i:[0,0,1,1,2,2,3,3],j:[1,2,5,6,6,7,7,4],k:[2,3,6,2,7,3,4,0],color:'#cfe2fb',opacity:.13,flatshading:true,hoverinfo:'skip',lighting:{ambient:.9,diffuse:.2},name:'진공백'},
      {type:'scatter3d',...g.lines,mode:'lines',line:{color:'rgba(9,19,35,.9)',width:2.5},hoverinfo:'skip',showlegend:false},
      {type:'scatter3d',...g.plies,mode:'lines',line:{color:'rgba(9,19,35,.22)',width:1},hoverinfo:'skip',showlegend:false},
/* [NEW v29] Visual palette only. */       {type:'scatter3d',x:[L*.5,L*.5,L*.5],y:[Y0-1,Y0-1,Y0-1],z:hz,mode:'markers',marker:{size:4.5,color:'#fff',line:{width:1.5,color:'#ffffff'}},hovertext:sensorText,hoverinfo:'text',showlegend:false}
    ];
    const notes=[
      {x:L+M,y:W+M,z:g.tool+g.th*.5,text:`CFRP ${g.th} mm (≈${Math.round(g.th/V3D.PLY)} plies)`,showarrow:false,xanchor:'left',xshift:10,font:{color:INK,size:12}},
      {x:L+M,y:W+M,z:g.tool*.5,text:`Invar 금형 ${g.tool} mm`,showarrow:false,xanchor:'left',xshift:10,font:{color:MUTED,size:12}},
      {x:L*.78,y:W,z:g.H+.35,text:'진공백 · 오토클레이브 공기',showarrow:true,arrowcolor:MUTED,ax:30,ay:-34,font:{color:MUTED,size:11}},
/* [NEW v29] Visual palette only. */       ...hz.map((z,q)=>({x:L*.5,y:Y0-1,z,text:sensorText[q],showarrow:true,arrowcolor:'#334155',arrowwidth:1.2,arrowhead:0,ax:-120,ay:[34,0,-34][q],bgcolor:'rgba(248,250,252,.96)',bordercolor:'#DCE4EE',borderpad:3,font:{color:'#334155',size:12}}))
    ];
    const hid={visible:false,showbackground:false,showgrid:false,zeroline:false,showspikes:false},xr=L+2*M,yr=(W+M)-Y0,k=1.7/xr,dv=center-air;
    const status=`<b>${label} · ${fmt(s.t[i])} min</b> · 공기 ${fmt(air)}°C · 중앙 ${fmt(center)}°C (공기 대비 ${dv>=0?'+':'−'}${fmt(Math.abs(dv))})<br><span style='color:${MUTED};font-size:11px'>CFRP ${g.th} mm · 최저 α ${fmt(s.alpha_min[i],3)} · 해석값(측정 아님) · 1D 해석의 평판 투영 · 두께 ×4</span>`;
    const layout={paper_bgcolor:BG,font:{color:INK},margin:{l:0,r:0,t:56,b:10},showlegend:false,uirevision:'v22-demo-camera',
      annotations:[{xref:'paper',yref:'paper',x:0,y:1,xanchor:'left',yanchor:'bottom',text:status,showarrow:false,align:'left',font:{size:12.5}}],
      scene:{xaxis:{range:[-M-2,L+M+2],...hid},yaxis:{range:[Y0-4,W+M+2],...hid},zaxis:{range:[0,g.H*1.04+.5],...hid},aspectmode:'manual',aspectratio:{x:xr*k,y:(yr+6)*k,z:Math.max(g.H,1)*V3D.EX*k},camera:{eye:{x:.8,y:-1.4,z:1},up:{x:0,y:0,z:1},center:{x:.02,y:.04,z:-.14}},annotations:notes,bgcolor:BG,dragmode:'orbit',domain:{x:[0,.84],y:[0,1]}}};
    return {data:traces,layout};
  };
})();
