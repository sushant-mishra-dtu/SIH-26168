import numpy as np, pandas as pd
A="data/IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/S (Driver A)/S1/S-S1.csv"
B="data/IO-VNBD/Synchronised V abd S datasets/Uncategorised IOVNB Dataset/S-Dataset/S-S1.csv"
for tag,p in (("categorised(Yaw/Pitch/Roll)",A),("uncategorised(X/Y/Z)",B)):
    df=pd.read_csv(p,encoding="latin-1",nrows=200000)
    df.columns=[c.strip() for c in df.columns]
    g=df.iloc[:,15:18].apply(pd.to_numeric,errors="coerce").to_numpy(float)
    gr=df.iloc[:,12:15].apply(pd.to_numeric,errors="coerce").to_numpy(float)  # gravity
    ori=pd.to_numeric(df.iloc[:,5],errors="coerce").to_numpy(float)   # gps orientation deg
    ok=np.isfinite(g).all(1)
    g=g[ok]
    print(f"\n{tag}  n={len(g)}")
    print("  gyro col names:", list(df.columns[15:18]))
    print("  gyro std  :", np.round(np.nanstd(g,0),5))
    print("  gravity mean:", np.round(np.nanmean(gr,0),3))
    # correlate each gyro col with GPS-heading rate (1 Hz -> resample by 10)
    o=ori[ok]
    dpsi=np.diff(np.unwrap(np.deg2rad(o[::10])))*1.0  # rad per 1 s
    for i in range(3):
        gi=g[::10,i][:-1]
        m=np.isfinite(gi)&np.isfinite(dpsi)
        if m.sum()>100:
            c=np.corrcoef(gi[m],dpsi[m])[0,1]
            print(f"   corr(gyro[{i}] , d(GPS heading)/dt) = {c:+.3f}")
