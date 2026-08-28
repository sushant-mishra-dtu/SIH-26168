import csv, os, numpy as np, pandas as pd
from collections import defaultdict
man="data/manifest/io_vnbd.csv"
rows=list(csv.DictReader(open(man,encoding="utf-8")))
s=[r for r in rows if r["stream"]=="S-"]
bysha=defaultdict(list)
for r in s: bysha[r["sha256"]].append(r["path"])
print("S- rows:",len(s)," unique sha:",len(bysha))
# pick canonical path per sha: prefer sync-categorised > sync-uncategorised > unsync
def rank(p):
    if "Categorised IOVNB Dataset" in p and "unsync" not in p: return 0
    if "Uncategorised IOVNB Dataset" in p: return 1
    return 2
uniq={sha:sorted(ps,key=rank)[0] for sha,ps in bysha.items()}
print("unique files:",len(uniq))
W=50;AVAR=0.05;GNORM=0.02;MIN_S=120.0
def runs(m):
    i=np.flatnonzero(np.diff(np.concatenate(([0],m.astype(np.int8),[0]))))
    return list(zip(i[0::2],i[1::2]))
out=[]
for sha,rel in sorted(uniq.items(), key=lambda kv: kv[1]):
    p=os.path.join("data",rel)
    try: df=pd.read_csv(p,encoding="latin-1",low_memory=False)
    except Exception as e: print("ERR",rel,e); continue
    if df.shape[1]<24: continue
    a=df.iloc[:,9:12].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    g=df.iloc[:,15:18].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    t=pd.to_numeric(df.iloc[:,7],errors="coerce").to_numpy(float)
    ok=np.isfinite(a).all(1)&np.isfinite(g).all(1)&np.isfinite(t)
    a,g,t=a[ok],g[ok],t[ok]
    if len(t)<2*W: continue
    dts=np.diff(t)/1000.0; med=float(np.median(dts))
    s1=np.cumsum(np.vstack([np.zeros(3),a]),0); s2=np.cumsum(np.vstack([np.zeros(3),a*a]),0)
    mu=(s1[W:]-s1[:-W])/W; var=(s2[W:]-s2[:-W])/W-mu**2
    gn=np.linalg.norm(g,1 if False else 2,axis=1); gs=np.cumsum(np.concatenate(([0.0],gn)))
    gm=(gs[W:]-gs[:-W])/W
    st=(var.max(1)<AVAR)&(gm<GNORM)
    for a0,b0 in runs(st):
        lo,hi=a0,b0+W-1
        dur=(hi-lo)*med
        if dur>=MIN_S:
            seg_dt=np.diff(t[lo:hi])/1000.0
            gap=float(seg_dt.max()) if len(seg_dt) else 0.0
            out.append((os.path.basename(rel),lo,hi,hi-lo,med,dur,gap,rel))
out.sort(key=lambda r:-r[5])
print(f"\n{'file':14s} {'lo':>7s} {'hi':>7s} {'n':>6s} {'dt':>6s} {'dur_s':>8s} {'maxgap_s':>8s}")
for r in out: print(f"{r[0]:14s} {r[1]:7d} {r[2]:7d} {r[3]:6d} {r[4]:6.3f} {r[5]:8.1f} {r[6]:8.3f}")
print("\ntotal segments >=120s:",len(out), " total duration min:", round(sum(r[5] for r in out)/60,1))
