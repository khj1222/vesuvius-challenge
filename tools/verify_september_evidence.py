"""Independent arithmetic checks for September's saved audit results (stdlib only)."""
from pathlib import Path
import json
import math
import statistics

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'runs/september_evidence_audit'
EPS=.0000005001


def verify_bounds():
    d=json.loads((DATA/'pseudo_threshold_bounds.json').read_text())
    lower=[]; upper=[]
    for cell,truth in zip(d['per_cell'],d['saved_truth_inputs']):
        p=truth['ink_pixels']; n=truth['scored_pixels']-p
        def limits(index):
            recall=truth['sweep']['recall'][index]; precision=truth['sweep']['precision'][index]
            lo=max(0,recall-EPS)*p; hi=min(1,recall+EPS)*p
            return lo,hi,max(0,lo*(1/min(1,precision+EPS)-1)),min(n,hi*(1/max(0,precision-EPS)-1))
        threshold=cell['pseudo_threshold']; grid=truth['sweep']['threshold']
        a=max(i for i,t in enumerate(grid) if t<=threshold)
        b=min(i for i,t in enumerate(grid) if t>=threshold)
        best=truth['best_f1']['f1']
        if a==b:
            flo=max(0,truth['sweep']['f1'][a]-EPS); fhi=min(best,truth['sweep']['f1'][a]+EPS)
        else:
            low=limits(a); high=limits(b)
            flo=2*high[0]/(p+high[0]+low[3])
            fhi=min(best,2*low[1]/(p+low[1]+high[2]))
        lower.append(max(0,best-fhi)); upper.append(best-flo)
        assert math.isclose(lower[-1],cell['loss_lower'],abs_tol=1e-14)
        assert math.isclose(upper[-1],cell['loss_upper'],abs_tol=1e-14)
    assert len(lower)==30
    assert abs(statistics.mean(lower)-d['mean_loss_lower'])<1e-14
    assert abs(statistics.mean(upper)-d['mean_loss_upper'])<1e-14
    print('30 pseudo-threshold bounds independently reproduced.')


def verify_fixed_threshold():
    cal=json.loads((DATA/'fixed_threshold_calibration.json').read_text())
    ev=json.loads((DATA/'fixed_threshold_evaluation.json').read_text())
    assert ev['complete'] and len(cal['records'])==10 and len(ev['records'])==48
    assert ev['calibration_sha256']==__import__('hashlib').sha256((DATA/'fixed_threshold_calibration.json').read_bytes()).hexdigest()
    assert not {r['segment'] for r in cal['records']} & {r['segment'] for r in ev['records']}
    for r in cal['records']+ev['records']:
        ph=r['positive_hist']; nh=r['negative_hist']; k=f"{r['scroll']}/{r['arm']}/{r['seed']}"
        t=cal['thresholds'][k]
        tp=sum(ph[t:]); fp=sum(nh[t:]); p=sum(ph)
        f=2*tp/(p+tp+fp)
        assert r['fixed_threshold']==t and r['tp']==tp and r['fp']==fp
        assert abs(f-r['fixed_f1'])<1e-14
        assert sum(ph)+sum(nh)==r['pixels'] and p==r['ink']
        if r['role']=='calibration':
            for i in range(256):
                tpi=sum(ph[i:]); fpi=sum(nh[i:])
                assert tp*(p+tpi+fpi)>=tpi*(p+tp+fp)
                if i<t: assert tp*(p+tpi+fpi)>tpi*(p+tp+fp)
        else:
            lp=r['legacy_positive_hist']; ln=r['legacy_negative_hist']
            assert all(a>=b for a,b in zip(lp,ph)) and all(a>=b for a,b in zip(ln,nh))
            assert sum(lp)+sum(ln)==r['expected_pixels'] and sum(lp)==r['expected_ink']
            lf=2*sum(lp[t:])/(sum(lp)+sum(lp[t:])+sum(ln[t:]))
            assert abs(lf-r['legacy_fixed_f1'])<1e-14
    for seg in {r['segment'] for r in ev['records']}:
        rows=[r for r in ev['records'] if r['segment']==seg]
        assert len({(r['pixels'],r['ink'],r['mask_sha256'],r['truth_sha256']) for r in rows})==1
    print('58 histograms/supports checked; calibration thresholds and fixed F1 independently reproduced.')


if __name__=='__main__':
    verify_bounds()
    if (DATA/'fixed_threshold_evaluation.json').exists(): verify_fixed_threshold()
