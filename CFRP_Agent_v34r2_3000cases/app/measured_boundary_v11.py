# [NEW v11] Optional measured-boundary path. Existing nominal path stays intact.
"""Same composite/tool FVM equations, with separate measured air/mould inputs.
No extrapolation; integrate until the final observation, not an assumed release.
The solver is copied from core._solve_tool to preserve the existing nominal path.
"""
import math
import numpy as np
from core import (njit,normalize,MATERIAL,FEATURES,TARGETS,MODEL_HASH,PHYSICS_STATUS,
                  _rate,_composite_props,kinetic_vector,MATERIAL_THERMAL_HR,ood)


def validate_history(boundary_history=None):
    if isinstance(boundary_history,dict):
        if set(boundary_history)!={'time_min','air_c','tool_c'}:
            raise ValueError('Measured history requires exactly time_min, air_c, tool_c')
        try: h=np.column_stack([boundary_history[k] for k in ['time_min','air_c','tool_c']]).astype(float)
        except (TypeError,ValueError) as e: raise ValueError('Invalid measured history columns') from e
    else:
        try: h=np.asarray(boundary_history,dtype=float)
        except (TypeError,ValueError) as e: raise ValueError('Invalid measured history') from e
    if h.ndim!=2 or h.shape[1]!=3 or h.shape[0]<2 or not np.isfinite(h).all():
        raise ValueError('Measured history must contain >=2 finite rows: time_min, air_c, tool_c')
    if h[0,0]!=0 or not np.all(np.diff(h[:,0])>0) or h[-1,0]>1440:
        raise ValueError('Measured history must start at zero, increase strictly and end within 1440 min')
    if np.any(h[:,1:]<-50) or np.any(h[:,1:]>300):
        raise ValueError('Measured temperatures must be between -50 and 300 C')
    return np.ascontiguousarray(h)


@njit(cache=True)
def _solve_measured(c=None,p=None,transport=None,tool=None,boundary=None,nz=None,ntool=None,dt=None,save_dt=None,heat_scale=None,initial=None,history=None):
    r1,t1,h1,r2,t2,h2,th=c
    T0,alpha0,cool_rate,release_c=initial
    ends=np.array([(t1-T0)/r1,(t1-T0)/r1+h1,(t1-T0)/r1+h1+(t2-t1)/r2,(t1-T0)/r1+h1+(t2-t1)/r2+h2])*60.
    tool_th_mm,rho_m,cp_m,k_m=tool
    h_top,h_contact,h_contact_cool,h_tool,bc_mode=boundary
    dzc=th/1000./nz; dzt=tool_th_mm/1000./ntool
    n=nz+ntool
    qr=(1.-transport[2])*transport[1]*MATERIAL_THERMAL_HR
    cool=cool_rate/60.
    max_t=history[-1,0]*60.
    capacity=int(max_t/save_dt)+5
    times=np.empty(capacity); temps=np.empty((capacity,nz)); alphas=np.empty((capacity,nz)); airs=np.empty(capacity)
    tooltemps=np.empty((capacity,ntool)); qcontacts=np.empty(capacity)
    topfaces=np.empty(capacity); bottomfaces=np.empty(capacity); toolifaces=np.empty(capacity); toolouter=np.empty(capacity)
    T=np.full(n,.5*(history[0,1]+history[0,2])); a=np.full(nz,alpha0)
    t=0.; next_save=0.; saved=0
    peak=float(T[0]); gradient=0.; peak_time=0.; overshoot=0.; min_hold=0.; fail=False
    tool_peak=float(T[0]); interface_jump_max=0.; contact_flux_abs_max=0.
    lower=np.empty(n); upper=np.empty(n); diag=np.empty(n); rhs=np.empty(n)
    kcomp=np.empty(nz); cpcomp=np.empty(nz); rhocomp=np.empty(nz)
    while t<=max_t:
        air=np.interp(t/60.,history[:,0],history[:,1])
        mould=np.interp(t/60.,history[:,0],history[:,2])
        # Current-step properties and reconstructed physical surfaces.
        for j in range(nz):
            rr,cc,kk=_composite_props(T[j],transport);rhocomp[j]=rr;cpcomp[j]=cc;kcomp[j]=kk
        gtop=1./(1./h_top+dzc/(2.*kcomp[0])) if h_top>0. else 0.
        hc=h_contact_cool if (h_contact_cool>=0. and t>ends[3]) else h_contact
        gint=0.
        if hc>0.: gint=1./(dzc/(2.*kcomp[nz-1])+1./hc+dzt/(2.*k_m))
        qtop=gtop*(air-T[0])
        face_top=T[0]+qtop*dzc/(2.*kcomp[0])
        qint=gint*(T[nz-1]-T[nz])
        face_bottom=T[nz-1]-qint*dzc/(2.*kcomp[nz-1])
        face_tool=T[nz]+qint*dzt/(2.*k_m)
        if int(bc_mode)==0:
            face_outer=mould
        elif int(bc_mode)==1:
            gouter=1./(dzt/(2.*k_m)+1./h_tool) if h_tool>0. else 0.
            qouter=gouter*(mould-T[n-1])
            face_outer=T[n-1]+qouter*dzt/(2.*k_m)
        else:
            face_outer=T[n-1]
        hi=T[:nz].max();lo=T[:nz].min()
        domain_hi=max(hi,face_top,face_bottom);domain_lo=min(lo,face_top,face_bottom)
        if domain_hi>peak: peak=domain_hi;peak_time=t/60.
        gradient=max(gradient,domain_hi-domain_lo);overshoot=max(overshoot,domain_hi-air)
        tool_peak=max(tool_peak,T[nz:].max(),face_tool,face_outer)
        interface_jump_max=max(interface_jump_max,abs(face_bottom-face_tool))
        contact_flux_abs_max=max(contact_flux_abs_max,abs(qint))
        done=t>=max_t-1e-8
        fail=domain_hi>300. or T[nz:].max()>300. or not math.isfinite(domain_hi) or not math.isfinite(T[nz:].max())
        if t>=next_save-1e-8 or done or fail:
            times[saved]=t/60.;temps[saved]=T[:nz];alphas[saved]=a;airs[saved]=air;tooltemps[saved]=T[nz:]
            qcontacts[saved]=qint;topfaces[saved]=face_top;bottomfaces[saved]=face_bottom;toolifaces[saved]=face_tool;toolouter[saved]=face_outer
            saved+=1;next_save=t+save_dt
        if done or fail: break
        step=dt
        for event in ends:
            if event>t+1e-8: step=min(step,event-t)
        step=min(step,max_t-t)
        for knot in history[:,0]:
            event=knot*60.
            if event>t+1e-8: step=min(step,event-t)
        nt=t+step
        nair=np.interp(nt/60.,history[:,0],history[:,1])
        nmould=np.interp(nt/60.,history[:,0],history[:,2])
        # Re-evaluate conductances using old-step temperatures; backward Euler is implicit in T, semi-implicit in properties.
        for j in range(n):
            lower[j]=0.;upper[j]=0.;diag[j]=1.;rhs[j]=T[j]
        # Cure and volumetric reaction heat in composite cells only.
        for j in range(nz):
            rate=_rate(a[j],T[j],p)
            qcoef=qr/(rhocomp[j]*cpcomp[j])*heat_scale
            da0=min(rate*step,1.-a[j])
            da=min(.5*step*(rate+_rate(a[j]+da0,T[j]+qcoef*da0,p)),1.-a[j])
            a[j]+=da;rhs[j]+=qcoef*da
        # Composite internal faces.
        for j in range(nz-1):
            g=1./(dzc/(2.*kcomp[j])+dzc/(2.*kcomp[j+1]))
            bj=step*g/(rhocomp[j]*cpcomp[j]*dzc); bk=step*g/(rhocomp[j+1]*cpcomp[j+1]*dzc)
            diag[j]+=bj;upper[j]-=bj;diag[j+1]+=bk;lower[j+1]-=bk
        # Top air/composite boundary.
        bt=step*gtop/(rhocomp[0]*cpcomp[0]*dzc)
        diag[0]+=bt;rhs[0]+=bt*nair
        # Composite/tool contact resistance.
        if gint>0.:
            bc=step*gint/(rhocomp[nz-1]*cpcomp[nz-1]*dzc);bm=step*gint/(rho_m*cp_m*dzt)
            diag[nz-1]+=bc;upper[nz-1]-=bc;diag[nz]+=bm;lower[nz]-=bm
        # Tool internal conduction.
        gm=k_m/dzt
        for j in range(nz,n-1):
            bj=step*gm/(rho_m*cp_m*dzt)
            diag[j]+=bj;upper[j]-=bj;diag[j+1]+=bj;lower[j+1]-=bj
        # Tool outer surface: 0 prescribed, 1 convective, 2 adiabatic.
        if int(bc_mode)==0:
            gout=2.*k_m/dzt;bb=step*gout/(rho_m*cp_m*dzt);diag[n-1]+=bb;rhs[n-1]+=bb*nmould
        elif int(bc_mode)==1:
            gout=1./(dzt/(2.*k_m)+1./h_tool) if h_tool>0. else 0.;bb=step*gout/(rho_m*cp_m*dzt);diag[n-1]+=bb;rhs[n-1]+=bb*nmould
        # Thomas solve.
        for j in range(1,n):
            factor=lower[j]/diag[j-1];diag[j]-=factor*upper[j-1];rhs[j]-=factor*rhs[j-1]
        T[n-1]=rhs[n-1]/diag[n-1]
        for j in range(n-2,-1,-1): T[j]=(rhs[j]-upper[j]*T[j+1])/diag[j]
        t=nt
        if abs(t-ends[3])<1e-7: min_hold=a.min()
    return (times[:saved],temps[:saved],alphas[:saved],airs[:saved],tooltemps[:saved],qcontacts[:saved],topfaces[:saved],bottomfaces[:saved],toolifaces[:saved],toolouter[:saved],
            np.array([peak,gradient,a.min(),t/60.,peak_time,overshoot,min_hold,1.0 if fail else 0.0,ends[3]/60.,tool_peak,interface_jump_max,contact_flux_abs_max]))


# [NEW v11] Existing option contracts are retained on this separate measured path.
def simulate_measured(condition=None,options=None,boundary_history=None):
    history=validate_history(boundary_history)
    c=normalize(condition);opt=dict(options or {})
    # [NEW v07] Reject misspelled/unknown solver knobs and non-finite diagnostic options instead of silently changing the calculation.
    allowed_options={'nz','tool_nz','dt','save_seconds','heat_scale','tool_thickness_mm','contact_h','h_top','tool_outer_h','contact_h_cooldown','tool_outer_bc','cool_rate','release_temperature_c'}
    extra=set(opt)-allowed_options
    if extra: raise ValueError('Unknown solver options: '+','.join(sorted(extra)))
    def int_option(name=None,default=None):
        raw=opt.get(name,default)
        if isinstance(raw,bool): raise ValueError(name+' must be an integer')
        x=float(raw)
        if not math.isfinite(x) or not x.is_integer(): raise ValueError(name+' must be an integer')
        return int(x)
    def finite_option(name=None,default=None):
        raw=opt.get(name,default)
        if isinstance(raw,bool): raise ValueError(name+' must be a finite number')
        x=float(raw)
        if not math.isfinite(x): raise ValueError(name+' must be finite')
        return x
    nz=int_option('nz',31);ntool=int_option('tool_nz',21);dt=finite_option('dt',2.);save=finite_option('save_seconds',30.);heat_scale=finite_option('heat_scale',1.)
    if nz<5 or nz>201 or nz%2==0: raise ValueError('nz must be odd, 5–201')
    if ntool<3 or ntool>201: raise ValueError('tool_nz must be 3–201')
    if not 0.1<=dt<=10 or save<dt: raise ValueError('Require 0.1 <= dt <= 10 and save_seconds >= dt')
    if heat_scale<0: raise ValueError('heat_scale must be >= 0')
    m=MATERIAL['thermal'];tr=MATERIAL['composite_transport'];tm=MATERIAL['tool'];bd=MATERIAL['boundary']
    transport=np.array([m['rho_f'],m['rho_r'],m['Vf'],tr['resin_k_intercept'],tr['resin_k_slope_per_c'],tr['fiber_k_transverse_intercept'],tr['fiber_k_transverse_slope_per_c'],tr['resin_cp_intercept'],tr['resin_cp_slope_per_c'],tr['fiber_cp_intercept'],tr['fiber_cp_slope_per_c']],dtype=float)
    tool_th=finite_option('tool_thickness_mm',tm['thickness_mm']);contact=finite_option('contact_h',bd['contact_h']);top_h=finite_option('h_top',bd['h_top']);tool_h=finite_option('tool_outer_h',bd['tool_outer_h'])
    cool_contact=opt.get('contact_h_cooldown',bd['contact_h_cooldown']);cool_contact=-1. if cool_contact is None else finite_option('contact_h_cooldown',cool_contact)
    if tool_th<=0 or contact<0 or top_h<=0 or tool_h<0 or cool_contact<0 and cool_contact!=-1.: raise ValueError('Invalid tool/contact boundary option')
    bc_name=str(opt.get('tool_outer_bc',bd['tool_outer_bc'])).lower();bc_map={'prescribed':0.,'convective':1.,'adiabatic':2.}
    if bc_name not in bc_map: raise ValueError('tool_outer_bc must be prescribed, convective or adiabatic')
    # [NEW v11] A measured mould-surface temperature must be imposed as a surface, not treated as ambient.
    if bc_name!='prescribed': raise ValueError('Measured tool_c requires prescribed tool_outer_bc')
    tool=np.array([tool_th,tm['rho'],tm['cp'],tm['k']],dtype=float);boundary=np.array([top_h,contact,cool_contact,tool_h,bc_map[bc_name]],dtype=float)
    initial=np.array([MATERIAL['initial']['temperature_c'],MATERIAL['initial']['alpha'],finite_option('cool_rate',MATERIAL['initial']['cool_rate']),finite_option('release_temperature_c',MATERIAL['initial']['release_temperature_c'])],dtype=float)
    if initial[2]<=0 or not (initial[0]<=initial[3]<=c['T2']): raise ValueError('Invalid cooling/release option')
    out=_solve_measured(np.array([c[k] for k in FEATURES]),kinetic_vector(),transport,tool,boundary,nz,ntool,dt,save,heat_scale,initial,history)
    # [NEW v17] Reject a missing result, retaining legitimate summary nulls.
    from async_runtime_v17 import require_result
    require_result(out, "_solve_measured")
    t,T,a,air,Ttool,qcontact,Ttop,Tbottom,Ttoolface,Ttoolouter,s=out
    if s[7] or not np.isfinite(T).all() or not np.isfinite(Ttool).all(): raise ValueError('Model validity guard: >300 C or nonfinite state; no recommendation')

    summary=dict(zip(TARGETS,map(float,s[:4])))
    summary.update(peak_time=float(s[4]),air_excess=float(s[5]),hold_end_DoC=float(s[6]),hold_end_time=float(s[8]),tool_Tmax=float(s[9]),interface_delta_Tmax=float(s[10]),contact_flux_abs_max=float(s[11]))
    # [NEW v11] An unobserved nominal hold end must not look like measured zero cure.
    if t[-1]<s[8]: summary['hold_end_DoC']=None
    summary['observation_duration_min']=float(t[-1])
    released=(t>=s[8]) & (np.maximum(np.max(T,axis=1),np.maximum(Ttop,Tbottom))<=initial[3])
    summary['cycle_time']=float(t[np.flatnonzero(released)[0]]) if released.any() else None
    summary['release_reached']=bool(released.any())
    opts={'nz':nz,'tool_nz':ntool,'dt':dt,'save_seconds':save,'heat_scale':heat_scale,'tool_thickness_mm':tool_th,'h_top':top_h,'contact_h':contact,'contact_h_cooldown':None if cool_contact<0 else cool_contact,'tool_outer_bc':bc_name,'tool_outer_h':tool_h,'cool_rate':float(initial[2]),'release_temperature_c':float(initial[3])}
    return {'condition':c,'t':t,'z':(np.arange(nz)+.5)*c['thickness']/nz,'T':T,'alpha':a,'T_air':air,
            'z_tool':c['thickness']+(np.arange(ntool)+.5)*tool_th/ntool,'T_tool':Ttool,'q_contact':qcontact,
            'T_part_top_surface':Ttop,'T_part_bottom_surface':Tbottom,'T_tool_interface_surface':Ttoolface,'T_tool_outer_surface':Ttoolouter,
            'summary':summary,'model_hash':MODEL_HASH,'model_version':MATERIAL['version'],'outside_training_domain':ood(c),'external_validation_passed':False,'physics_status':PHYSICS_STATUS,'options':opts,'boundary_input_kind':'measured_history','qualification':'Boundary-conditioned reconstruction; not an independent process forecast','initial_temperature_c':float(.5*(history[0,1]+history[0,2])),'initial_temperature_basis':'Mean of first boundary readings; specimen initial temperature unavailable','boundary_history':history,'cycle_time_kind':'release_time_if_observed_else_none'}
