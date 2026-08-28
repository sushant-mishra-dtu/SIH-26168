import sys, glob, os
import numpy as np, pandas as pd

def load_raw(p):
    df = pd.read_csv(p, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    return df

def cols(df):
    m = {}
    for c in df.columns:
        lc = c.lower()
        if lc.startswith("accelerometer x"): m["ax"]=c
        elif lc.startswith("accelerometer y"): m["ay"]=c
        elif lc.startswith("accelerometer z"): m["az"]=c
        elif lc.startswith("gyroscope yaw"): m["gz"]=c
        elif lc.startswith("gyroscope pitch"): m["gy"]=c
        elif lc.startswith("gyroscope roll"): m["gx"]=c
        elif lc.startswith("time since start"): m["t"]=c
        elif lc.startswith("gps speed"): m["v"]=c
    return m

def runs(mask):
    """yield (start, end_exclusive) of True runs"""
    idx = np.flatnonzero(np.diff(np.concatenate(([0], mask.view(np.int8), [0]))))
    return list(zip(idx[0::2], idx[1::2]))

W = 50  # 5 s at 10 Hz
AVAR = 0.05
GNORM = 0.02

for p in sorted(glob.glob(sys.argv[1])):
    try:
        df = load_raw(p)
    except Exception as e:
        print("ERR", os.path.basename(p), e); continue
    m = cols(df)
    if not all(k in m for k in ("ax","ay","az","gx","gy","gz","t")):
        print("SKIP", os.path.basename(p), sorted(m)); continue
    a = df[[m["ax"],m["ay"],m["az"]]].to_numpy(float)
    g = df[[m["gx"],m["gy"],m["gz"]]].to_numpy(float)
    t = pd.to_numeric(df[m["t"]], errors="coerce").to_numpy(float)
    ok = np.isfinite(a).all(1) & np.isfinite(g).all(1) & np.isfinite(t)
    a,g,t = a[ok],g[ok],t[ok]
    n = len(t)
    if n < W*2: print("TINY", os.path.basename(p), n); continue
    dt = np.diff(t)/1000.0
    med_dt = float(np.median(dt))
    # rolling variance per axis via cumsum
    s1 = np.cumsum(np.vstack([np.zeros(3), a]), axis=0)
    s2 = np.cumsum(np.vstack([np.zeros(3), a*a]), axis=0)
    mean = (s1[W:]-s1[:-W])/W
    var = (s2[W:]-s2[:-W])/W - mean**2
    gn = np.linalg.norm(g,axis=1)
    gs = np.cumsum(np.concatenate(([0.0], gn)))
    gmean = (gs[W:]-gs[:-W])/W
    st = (var.max(1) < AVAR) & (gmean < GNORM)
    rr = runs(st)
    if not rr:
        best = (0,0); dur=0.0
    else:
        durs = [(e-s+W-1)*med_dt for s,e in rr]
        k = int(np.argmax(durs)); best = rr[k]; dur = durs[k]
    tot = sum((e-s+W-1) for s,e in rr)*med_dt
    print(f"{os.path.basename(p):18s} n={n:8d} dt={med_dt:.4f}s dur={n*med_dt/60:7.1f}min  longest_stat={dur/60:7.2f}min  total_stat={tot/60:7.1f}min  nruns={len(rr)}")
