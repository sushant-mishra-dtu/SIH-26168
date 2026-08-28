import sys, glob, os
import numpy as np, pandas as pd

W=50; AVAR=0.05; GNORM=0.02
def runs(mask):
    idx=np.flatnonzero(np.diff(np.concatenate(([0],mask.astype(np.int8),[0]))))
    return list(zip(idx[0::2],idx[1::2]))

rows=[]
for p in sorted(glob.glob(sys.argv[1])):
    b=os.path.basename(p)
    if b.upper().startswith("V-"): continue
    try:
        df=pd.read_csv(p,encoding="latin-1",low_memory=False)
    except Exception as e:
        print("ERR",b,e); continue
    if df.shape[1]<24: print("COLS",b,df.shape); continue
    a=df.iloc[:,9:12].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    g=df.iloc[:,15:18].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    t=pd.to_numeric(df.iloc[:,7],errors="coerce").to_numpy(float)
    v=pd.to_numeric(df.iloc[:,3],errors="coerce").to_numpy(float)
    ok=np.isfinite(a).all(1)&np.isfinite(g).all(1)&np.isfinite(t)
    a,g,t,v=a[ok],g[ok],t[ok],v[ok]
    n=len(t)
    if n<2*W: continue
    med_dt=float(np.median(np.diff(t)))/1000.0
    s1=np.cumsum(np.vstack([np.zeros(3),a]),axis=0); s2=np.cumsum(np.vstack([np.zeros(3),a*a]),axis=0)
    mean=(s1[W:]-s1[:-W])/W; var=(s2[W:]-s2[:-W])/W-mean**2
    gn=np.linalg.norm(g,axis=1); gs=np.cumsum(np.concatenate(([0.0],gn)))
    gm=(gs[W:]-gs[:-W])/W
    st=(var.max(1)<AVAR)&(gm<GNORM)
    rr=runs(st)
    if rr:
        durs=np.array([(e-s+W-1) for s,e in rr])*med_dt
        k=int(np.argmax(durs))
        s,e=rr[k]; lo,hi=s,e+W-1
        vm=np.nanmax(v[lo:hi]) if np.isfinite(v[lo:hi]).any() else float("nan")
        rows.append((b,n,med_dt,n*med_dt/60,durs[k]/60,durs.sum()/60,len(rr),lo,hi,vm))
    else:
        rows.append((b,n,med_dt,n*med_dt/60,0,0,0,-1,-1,float("nan")))

rows.sort(key=lambda r:-r[4])
print(f"{'file':16s} {'n':>8s} {'dt':>6s} {'dur_min':>8s} {'longest_min':>11s} {'total_min':>9s} {'nruns':>5s} {'lo':>8s} {'hi':>8s} {'maxGPSkmh':>9s}")
for r in rows:
    print(f"{r[0]:16s} {r[1]:8d} {r[2]:6.3f} {r[3]:8.1f} {r[4]:11.2f} {r[5]:9.1f} {r[6]:5d} {r[7]:8d} {r[8]:8d} {r[9]:9.2f}")
