import csv, os, numpy as np, pandas as pd
from collections import defaultdict
rows=list(csv.DictReader(open("data/manifest/io_vnbd.csv",encoding="utf-8")))
bysha=defaultdict(list)
for r in rows:
    if r["stream"]=="S-": bysha[r["sha256"]].append(r["path"])
def rank(p):
    if "Categorised IOVNB Dataset" in p and "unsync" not in p: return 0
    if "Uncategorised IOVNB Dataset" in p: return 1
    return 2
uniq={s:sorted(p,key=rank)[0] for s,p in bysha.items()}
W=100  # 10 s
GNORM=0.02          # rad/s  (strict: vehicle not rotating)
GVAR_MAX = 0.05     # accel variance -- LOOSE, allows engine idle vibration
MIN_S=120.0
def runs(m):
    i=np.flatnonzero(np.diff(np.concatenate(([0],m.astype(np.int8),[0]))))
    return list(zip(i[0::2],i[1::2]))
out=[]
for sha,rel in sorted(uniq.items(),key=lambda kv:kv[1]):
    p=os.path.join("data",rel)
    try: df=pd.read_csv(p,encoding="latin-1",low_memory=False)
    except Exception: continue
    if df.shape[1]<24: continue
    a=df.iloc[:,9:12].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    g=df.iloc[:,15:18].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    t=pd.to_numeric(df.iloc[:,7],errors="coerce").to_numpy(float)
    v=pd.to_numeric(df.iloc[:,3],errors="coerce").to_numpy(float)
    ok=np.isfinite(a).all(1)&np.isfinite(g).all(1)&np.isfinite(t)
    a,g,t,v=a[ok],g[ok],t[ok],v[ok]
    if len(t)<2*W: continue
    med=float(np.median(np.diff(t)))/1000.0
    if not (0.05<med<0.2): continue    # 10 Hz files only
    vv=pd.Series(v).ffill().fillna(99).to_numpy()
    gn=np.linalg.norm(g,axis=2-1)
    gs=np.cumsum(np.concatenate(([0.0],gn))); gm=(gs[W:]-gs[:-W])/W
    vs=np.cumsum(np.concatenate(([0.0],vv))); vm=(vs[W:]-vs[:-W])/W
    st=(gm<GNORM)&(vm<0.5)
    for a0,b0 in runs(st):
        lo,hi=a0,b0+W-1
        dur=(hi-lo)*med
        if dur<MIN_S: continue
        seg=np.diff(t[lo:hi])/1000.0
        out.append((os.path.basename(rel),lo,hi,hi-lo,med,dur,float(seg.max()),float((seg<=0).mean()),
                    float(np.max(np.var(a[lo:hi],axis=0))), float(np.max(np.abs(v[lo:hi][np.isfinite(v[lo:hi])])) if np.isfinite(v[lo:hi]).any() else -1), rel))
out.sort(key=lambda r:-r[5])
print(f"{'file':14s} {'lo':>7s} {'hi':>7s} {'n':>6s} {'dur_s':>8s} {'gapmax':>7s} {'dup%':>6s} {'a_var':>8s} {'vmax':>6s}")
for r in out: print(f"{r[0]:14s} {r[1]:7d} {r[2]:7d} {r[3]:6d} {r[5]:8.1f} {r[6]:7.2f} {r[7]*100:6.1f} {r[8]:8.4f} {r[9]:6.2f}")
print("\nn segments >=180s:",len(out),"total min:",round(sum(r[5] for r in out)/60,1))
