# [NEW v01] Independent implementation. No teammate source imported.
"""1D finite-volume heat/cure solver; public arguments default to None."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
try:
    from runtime_v17 import safe_njit as njit  # [NEW v17] Isolated native probe / Python fallback.
except ImportError:
    def njit(*args, **kwargs):
        return lambda fn: fn

ROOT = Path(__file__).resolve().parent
MATERIAL = json.loads((ROOT / 'config/material.json').read_text(encoding='utf-8'))
MODEL_HASH = hashlib.sha256((ROOT / 'config/material.json').read_bytes()).hexdigest()
# [NEW v01] Fingerprint source as well as parameters to prevent stale dataset reuse.
MODEL_HASH = hashlib.sha256((ROOT / 'config/material.json').read_bytes()+Path(__file__).read_bytes()).hexdigest()
# [NEW v11] Include measured-boundary implementation in the reproducibility fingerprint.
MODEL_HASH = hashlib.sha256((ROOT / 'config/material.json').read_bytes()+Path(__file__).read_bytes()+(ROOT/'measured_boundary_v11.py').read_bytes()).hexdigest()
FEATURES = ['ramp1','T1','hold1','ramp2','T2','hold2','thickness']
TARGETS = ['Tmax','delta_Tmax','final_DoC','cycle_time']
DEFAULT = dict(zip(FEATURES,[2.,110.,60.,2.,180.,120.,10.]))
# Manufacturer thermal-cycle ranges; thickness is our provisional demo domain.
# [NEW v03] Tool/contact domain is implemented; exact Li-2020 reproduction remains intentionally false because kinetics/property mixing differs and experimental validation is pending.
PHYSICS_STATUS = {'kinetics':'NCAMP model 15 implemented','heat_source':'resin-mass-basis source implemented','thermal_domain':'1D composite + 10 mm Invar tool','boundary_model':'top convection + explicit composite/tool contact + configurable tool outer boundary','reference_geometry_boundary_match':True,'reference_model_match':False}
BOUNDS = dict(zip(FEATURES,[(1.,3.),(105.,115.),(55.,65.),(1.,3.),(175.,185.),(115.,125.),(2.,30.)]))
LIMITS = {'Tmax':195., 'delta_Tmax':20., 'final_DoC':0.90}

def normalize(condition=None, enforce_domain=None):
    c = dict(DEFAULT)
    if condition is not None:
        extra=set(condition)-set(FEATURES)
        if extra: raise ValueError('Unknown input fields: '+','.join(sorted(extra)))
        c.update(condition)
    for k in FEATURES:
        if isinstance(c[k],bool): raise ValueError(k+' must be a number')
        c[k]=float(c[k])
        if not math.isfinite(c[k]): raise ValueError(k+' must be finite')
    if not (0.1<=c['ramp1']<=10 and 0.1<=c['ramp2']<=10): raise ValueError('Ramp must be 0.1–10 C/min')
    if not (25<c['T1']<c['T2']<=200): raise ValueError('Require 25 < T1 < T2 <= 200 C')
    if not (0<=c['hold1']<=300 and 0<=c['hold2']<=300): raise ValueError('Hold must be 0–300 min')
    if not 1<=c['thickness']<=60: raise ValueError('Thickness must be 1–60 mm')
    if enforce_domain and ood(c): raise ValueError('Outside training domain: '+str(ood(c)))
    return c

def ood(condition=None):
    return [k for k,(lo,hi) in BOUNDS.items() if not lo<=condition[k]<=hi]

def cycle(condition=None):
    c=normalize(condition)
    # [NEW v02] Use configured initial temperature instead of a duplicated hard-coded value.
    T0=float(MATERIAL['initial']['temperature_c'])
    t1=(c['T1']-T0)/c['ramp1']; t2=t1+c['hold1']
    t3=t2+(c['T2']-c['T1'])/c['ramp2']; t4=t3+c['hold2']
    t5=t4+(c['T2']-T0)/MATERIAL['initial']['cool_rate']
    return np.array([0,t1,t2,t3,t4,t5]),np.array([T0,c['T1'],c['T1'],c['T2'],c['T2'],T0])

@njit(cache=True)
def _rate(a=None, T=None, p=None):
    # NCAMP p7: xc1 in harmonic series with xi2+xc2 (=2000), plus xe.
    a=min(max(a,0.),1.)
    rc=p[0]*math.exp(-p[1]/(8.314462618*(T+273.15)))*(1-a)**p[2]*(a+p[3])**p[4]
    re=p[5]*math.exp(-p[6]/(8.314462618*(T+273.15)))*(1-a)**p[7]*a**p[8]
    rk=rc*2000/(rc+2000)+re
    tg=p[16]+p[18]*a*(p[17]-p[16])/(1-(1-p[18])*a)
    bf=p[12]+(p[13]-p[12])*min(max((tg-p[14])/(p[15]-p[14]),0.),1.)
    free=p[11]*(T-tg)+bf
    if free<=0: return 0.
    rd=p[9]*math.exp(max(-700.,-p[10]/free))
    return rk*rd/(rk+rd+1e-300)

def kinetic_vector():
    return np.array([MATERIAL['kinetics'][k] for k in ['Kc','Ec','lc','bc','nc','Ke','Ee','le','ne','kd','B','af','b1','b2','Tgb1','Tgb2','Tg0','Tginf','lambda']])

def cure_rate(alpha=None, temperature=None):
    return _rate(float(alpha),float(temperature),kinetic_vector())

@njit(cache=True)
def _solve(c=None,p=None,thermal=None,nz=None,dt=None,save_dt=None,heat_scale=None,initial=None):
    r1,t1,h1,r2,t2,h2,th=c
    # [NEW v03] Legacy solver retained for regression provenance; remove duplicated 25 C literal.
    T0,alpha0,cool_rate,release_c=initial
    ends=np.array([(t1-T0)/r1,(t1-T0)/r1+h1,(t1-T0)/r1+h1+(t2-t1)/r2,(t1-T0)/r1+h1+(t2-t1)/r2+h2])*60
    rho,cp,k,h_top,h_bottom,qr=thermal
    # [NEW v02] Initial/cooling/release values are supplied from material config.
    dz=th/1000/nz
    D=k/(rho*cp); q=qr/(rho*cp)*heat_scale
    gtop=1/(1/h_top+dz/(2*k)); gbot=1/(1/h_bottom+dz/(2*k))
    cool=cool_rate/60
    max_t=ends[3]+(t2-T0)/cool+7200
    capacity=int(max_t/save_dt)+5
    times=np.empty(capacity); temps=np.empty((capacity,nz)); alphas=np.empty((capacity,nz)); airs=np.empty(capacity)
    T=np.full(nz,T0); a=np.full(nz,alpha0)
    t=0.; next_save=0.; saved=0; peak=T0; gradient=0.; peak_time=0.; overshoot=0.; min_hold=0.; fail=False
    lower=np.empty(nz); upper=np.empty(nz); diag=np.empty(nz); rhs=np.empty(nz)
    while t<=max_t:
        if t<=ends[0]: air=T0+r1*t/60
        elif t<=ends[1]: air=t1
        elif t<=ends[2]: air=t1+r2*(t-ends[1])/60
        elif t<=ends[3]: air=t2
        else: air=max(T0,t2-cool*(t-ends[3]))
        hi=T.max(); lo=T.min()
        if hi>peak: peak=hi;peak_time=t/60
        gradient=max(gradient,hi-lo);overshoot=max(overshoot,hi-air)
        # [NEW v01] Include reconstructed boundary-face temperatures, not mesh-dependent cell extrema alone.
        face_top=T[0]+gtop*(air-T[0])*dz/(2*k)
        face_bottom=T[-1]+gbot*(air-T[-1])*dz/(2*k)
        gradient=max(gradient,max(hi,face_top,face_bottom)-min(lo,face_top,face_bottom))
        done=t>=ends[3] and hi<=release_c
        fail=hi>300 or not math.isfinite(hi)
        if t>=next_save-1e-8 or done or fail:
            times[saved]=t/60;temps[saved]=T;alphas[saved]=a;airs[saved]=air;saved+=1;next_save=t+save_dt
        if done or fail: break
        step=dt
        for event in ends:
            if event>t+1e-8: step=min(step,event-t)
        nt=t+step
        if nt<=ends[0]: nair=T0+r1*nt/60
        elif nt<=ends[1]: nair=t1
        elif nt<=ends[2]: nair=t1+r2*(nt-ends[1])/60
        elif nt<=ends[3]: nair=t2
        else: nair=max(T0,t2-cool*(nt-ends[3]))
        rr=D*step/dz**2
        for j in range(nz):
            rate=_rate(a[j],T[j],p)
            da0=min(rate*step,1-a[j])
            da=min(0.5*step*(rate+_rate(a[j]+da0,T[j]+q*da0,p)),1-a[j])
            a[j]+=da
            lower[j]=-rr;upper[j]=-rr;diag[j]=1+2*rr;rhs[j]=T[j]+q*da
        bt=gtop*step/(rho*cp*dz);bb=gbot*step/(rho*cp*dz)
        lower[0]=0.;diag[0]=1+rr+bt;rhs[0]+=bt*nair
        upper[nz-1]=0.;diag[nz-1]=1+rr+bb;rhs[nz-1]+=bb*nair
        for j in range(1,nz):
            factor=lower[j]/diag[j-1];diag[j]-=factor*upper[j-1];rhs[j]-=factor*rhs[j-1]
        T[nz-1]=rhs[nz-1]/diag[nz-1]
        for j in range(nz-2,-1,-1): T[j]=(rhs[j]-upper[j]*T[j+1])/diag[j]
        t=nt
        if abs(t-ends[3])<1e-7: min_hold=a.min()
    # [NEW v01] Numba-compatible flag conversion.
    return times[:saved],temps[:saved],alphas[:saved],airs[:saved],np.array([peak,gradient,a.min(),t/60,peak_time,overshoot,min_hold,1.0 if fail else 0.0,ends[3]/60])


# [NEW v03] Numba-safe NCAMP resin heat-of-reaction constant used by the active hybrid thermal model.
MATERIAL_THERMAL_HR = float(MATERIAL['thermal']['Hr'])


# [NEW v03] Li-2020 through-thickness transport functions, with the team-theory mass-weighted cp correction.
@njit(cache=True)
def _composite_props(T=None, tp=None):
    rho_f,rho_r,Vf,kr0,krT,kf0,kfT,cpr0,cprT,cpf0,cpfT=tp
    rho=Vf*rho_f+(1.-Vf)*rho_r
    cpr=cpr0+cprT*T
    cpf=cpf0+cpfT*T
    cp=(Vf*rho_f*cpf+(1.-Vf)*rho_r*cpr)/rho
    kr=kr0+krT*T
    kf=kf0+kfT*T
    B=2.*(kr/kf-1.)
    x=math.sqrt(Vf/math.pi)
    if abs(B)<1e-10:
        k=kr
    else:
        rad2=max(1e-12,1.-B*B*Vf/math.pi)
        rad=math.sqrt(rad2)
        den=1.+B*x
        if abs(den)<1e-12: den=1e-12 if den>=0 else -1e-12
        k=kr*((1.-2.*x)+(math.pi-4./rad*math.atan(rad/den))/B)
    return rho,max(cp,1.),max(k,1e-6)

# [NEW v03] Composite + Invar finite-volume solver. The v02 composite-only _solve remains above for provenance.
@njit(cache=True)
def _solve_tool(c=None,p=None,transport=None,tool=None,boundary=None,nz=None,ntool=None,dt=None,save_dt=None,heat_scale=None,initial=None):
    r1,t1,h1,r2,t2,h2,th=c
    T0,alpha0,cool_rate,release_c=initial
    ends=np.array([(t1-T0)/r1,(t1-T0)/r1+h1,(t1-T0)/r1+h1+(t2-t1)/r2,(t1-T0)/r1+h1+(t2-t1)/r2+h2])*60.
    tool_th_mm,rho_m,cp_m,k_m=tool
    h_top,h_contact,h_contact_cool,h_tool,bc_mode=boundary
    dzc=th/1000./nz; dzt=tool_th_mm/1000./ntool
    n=nz+ntool
    qr=(1.-transport[2])*transport[1]*MATERIAL_THERMAL_HR
    cool=cool_rate/60.
    max_t=ends[3]+(t2-T0)/cool+7200.
    capacity=int(max_t/save_dt)+5
    times=np.empty(capacity); temps=np.empty((capacity,nz)); alphas=np.empty((capacity,nz)); airs=np.empty(capacity)
    tooltemps=np.empty((capacity,ntool)); qcontacts=np.empty(capacity)
    topfaces=np.empty(capacity); bottomfaces=np.empty(capacity); toolifaces=np.empty(capacity); toolouter=np.empty(capacity)
    T=np.full(n,T0); a=np.full(nz,alpha0)
    t=0.; next_save=0.; saved=0
    peak=T0; gradient=0.; peak_time=0.; overshoot=0.; min_hold=0.; fail=False
    tool_peak=T0; interface_jump_max=0.; contact_flux_abs_max=0.
    lower=np.empty(n); upper=np.empty(n); diag=np.empty(n); rhs=np.empty(n)
    kcomp=np.empty(nz); cpcomp=np.empty(nz); rhocomp=np.empty(nz)
    while t<=max_t:
        if t<=ends[0]: air=T0+r1*t/60.
        elif t<=ends[1]: air=t1
        elif t<=ends[2]: air=t1+r2*(t-ends[1])/60.
        elif t<=ends[3]: air=t2
        else: air=max(T0,t2-cool*(t-ends[3]))
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
            face_outer=air
        elif int(bc_mode)==1:
            gouter=1./(dzt/(2.*k_m)+1./h_tool) if h_tool>0. else 0.
            qouter=gouter*(air-T[n-1])
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
        done=t>=ends[3] and domain_hi<=release_c
        fail=domain_hi>300. or T[nz:].max()>300. or not math.isfinite(domain_hi) or not math.isfinite(T[nz:].max())
        if t>=next_save-1e-8 or done or fail:
            times[saved]=t/60.;temps[saved]=T[:nz];alphas[saved]=a;airs[saved]=air;tooltemps[saved]=T[nz:]
            qcontacts[saved]=qint;topfaces[saved]=face_top;bottomfaces[saved]=face_bottom;toolifaces[saved]=face_tool;toolouter[saved]=face_outer
            saved+=1;next_save=t+save_dt
        if done or fail: break
        step=dt
        for event in ends:
            if event>t+1e-8: step=min(step,event-t)
        nt=t+step
        if nt<=ends[0]: nair=T0+r1*nt/60.
        elif nt<=ends[1]: nair=t1
        elif nt<=ends[2]: nair=t1+r2*(nt-ends[1])/60.
        elif nt<=ends[3]: nair=t2
        else: nair=max(T0,t2-cool*(nt-ends[3]))
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
            gout=2.*k_m/dzt;bb=step*gout/(rho_m*cp_m*dzt);diag[n-1]+=bb;rhs[n-1]+=bb*nair
        elif int(bc_mode)==1:
            gout=1./(dzt/(2.*k_m)+1./h_tool) if h_tool>0. else 0.;bb=step*gout/(rho_m*cp_m*dzt);diag[n-1]+=bb;rhs[n-1]+=bb*nair
        # Thomas solve.
        for j in range(1,n):
            factor=lower[j]/diag[j-1];diag[j]-=factor*upper[j-1];rhs[j]-=factor*rhs[j-1]
        T[n-1]=rhs[n-1]/diag[n-1]
        for j in range(n-2,-1,-1): T[j]=(rhs[j]-upper[j]*T[j+1])/diag[j]
        t=nt
        if abs(t-ends[3])<1e-7: min_hold=a.min()
    return (times[:saved],temps[:saved],alphas[:saved],airs[:saved],tooltemps[:saved],qcontacts[:saved],topfaces[:saved],bottomfaces[:saved],toolifaces[:saved],toolouter[:saved],
            np.array([peak,gradient,a.min(),t/60.,peak_time,overshoot,min_hold,1.0 if fail else 0.0,ends[3]/60.,tool_peak,interface_jump_max,contact_flux_abs_max]))

def simulate(condition=None,options=None,boundary_history=None):
    # [NEW v11] Optional boundary-history dispatch; nominal behavior is preserved.
    if boundary_history is not None:
        from measured_boundary_v11 import simulate_measured
        return simulate_measured(condition,options,boundary_history)
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
    tool=np.array([tool_th,tm['rho'],tm['cp'],tm['k']],dtype=float);boundary=np.array([top_h,contact,cool_contact,tool_h,bc_map[bc_name]],dtype=float)
    initial=np.array([MATERIAL['initial']['temperature_c'],MATERIAL['initial']['alpha'],finite_option('cool_rate',MATERIAL['initial']['cool_rate']),finite_option('release_temperature_c',MATERIAL['initial']['release_temperature_c'])],dtype=float)
    if initial[2]<=0 or not (initial[0]<=initial[3]<=c['T2']): raise ValueError('Invalid cooling/release option')
    out=_solve_tool(np.array([c[k] for k in FEATURES]),kinetic_vector(),transport,tool,boundary,nz,ntool,dt,save,heat_scale,initial)
    # [NEW v17] Missing solver return is an explicit calculation error.
    from async_runtime_v17 import require_result
    require_result(out, "_solve_tool")
    t,T,a,air,Ttool,qcontact,Ttop,Tbottom,Ttoolface,Ttoolouter,s=out
    if s[7] or not np.isfinite(T).all() or not np.isfinite(Ttool).all(): raise ValueError('Model validity guard: >300 C or nonfinite state; no recommendation')
    if max(T[-1].max(),Ttop[-1],Tbottom[-1])>initial[3]+1e-6: raise ValueError('Cooling did not reach the component release target')
    summary=dict(zip(TARGETS,map(float,s[:4])))
    summary.update(peak_time=float(s[4]),air_excess=float(s[5]),hold_end_DoC=float(s[6]),hold_end_time=float(s[8]),tool_Tmax=float(s[9]),interface_delta_Tmax=float(s[10]),contact_flux_abs_max=float(s[11]))
    opts={'nz':nz,'tool_nz':ntool,'dt':dt,'save_seconds':save,'heat_scale':heat_scale,'tool_thickness_mm':tool_th,'h_top':top_h,'contact_h':contact,'contact_h_cooldown':None if cool_contact<0 else cool_contact,'tool_outer_bc':bc_name,'tool_outer_h':tool_h,'cool_rate':float(initial[2]),'release_temperature_c':float(initial[3])}
    return {'condition':c,'t':t,'z':(np.arange(nz)+.5)*c['thickness']/nz,'T':T,'alpha':a,'T_air':air,
            'z_tool':c['thickness']+(np.arange(ntool)+.5)*tool_th/ntool,'T_tool':Ttool,'q_contact':qcontact,
            'T_part_top_surface':Ttop,'T_part_bottom_surface':Tbottom,'T_tool_interface_surface':Ttoolface,'T_tool_outer_surface':Ttoolouter,
            'summary':summary,'model_hash':MODEL_HASH,'model_version':MATERIAL['version'],'outside_training_domain':ood(c),'external_validation_passed':False,'physics_status':PHYSICS_STATUS,'options':opts}

def judge(summary=None,limits=None):
    lim=dict(LIMITS);lim.update(limits or {})
    if set(lim)!=set(LIMITS) or not all(math.isfinite(float(v)) for v in lim.values()): raise ValueError('Invalid limits')
    if not (25<float(lim['Tmax'])<=300 and 0<float(lim['delta_Tmax'])<=200 and 0<float(lim['final_DoC'])<=1): raise ValueError('Invalid limits')
    checks={'temperature':summary['Tmax']<=lim['Tmax'],'uniformity':summary['delta_Tmax']<=lim['delta_Tmax'],'cure':summary['final_DoC']>=lim['final_DoC']}
    return {'checks':checks,'feasible':all(checks.values()),'limits':lim,'label':'내부 시연 기준 충족' if all(checks.values()) else '내부 시연 기준 미충족','qualification':'외부 검증 전 — 실제 공정 적합 판정 아님'}
