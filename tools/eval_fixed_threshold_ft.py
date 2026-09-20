"""Re-score saved uint8 predictions with thresholds fit on separate segments.

Run calibration first, preserving its JSON, then evaluation. Input manifest records
specify scroll/arm/seed, segment, calibration or evaluation role, prediction TIFF,
label directory and previous pixel counts/oracle scores for reproduction checks.
No training, inference or threshold selection on evaluation labels is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import tifffile
import zarr
from eval_validation import find_regions, read_plane


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(8*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def key(record):
    return f"{record['scroll']}/{record['arm']}/{record['seed']}"


def sweep(pos,neg):
    tp=np.cumsum(pos[::-1],dtype=np.int64)[::-1]
    fp=np.cumsum(neg[::-1],dtype=np.int64)[::-1]
    denom=int(pos.sum())+tp+fp
    return tp,fp,np.divide(2*tp,denom,out=np.zeros(256,dtype=float),where=denom>0)


def best_threshold(pos,neg):
    # Integer cross-products give exact F1 ties, with the lowest threshold winning.
    tp,fp,_=sweep(pos,neg)
    p=int(pos.sum())
    best=0
    for i in range(1,256):
        den_i=p+int(tp[i])+int(fp[i]); den_b=p+int(tp[best])+int(fp[best])
        if int(tp[i])*den_b>int(tp[best])*den_i:
            best=i
    return best


def score(record):
    pred_path=Path(record['prediction'])
    raw=pred_path.read_bytes()
    pred_digest=hashlib.sha256(raw).hexdigest()
    pred=tifffile.imread(io.BytesIO(raw))
    del raw
    assert pred.ndim==2 and pred.dtype==np.uint8,(pred.shape,pred.dtype)
    segment=record['segment']; folder=Path(record['labels'])
    mask_group=zarr.open(str(folder/f'{segment}_supervision_mask.zarr'),mode='r')
    truth_group=zarr.open(str(folder/f'{segment}_inklabels.zarr'),mode='r')
    mask=mask_group['0']; truth=truth_group['0']
    assert pred.shape==mask.shape[1:]==truth.shape[1:]
    pos=np.zeros(256,dtype=np.int64); neg=np.zeros(256,dtype=np.int64)
    mask_hash=hashlib.sha256(); truth_hash=hashlib.sha256()
    # Count each labeled pixel once, independent of connected-component bounding boxes.
    for y in range(0,pred.shape[0],512):
        valid=np.asarray(mask[mask.shape[0]//2,y:y+512,:])>0
        ink=np.asarray(truth[truth.shape[0]//2,y:y+512,:])>0
        mask_hash.update(valid.tobytes()); truth_hash.update(ink.tobytes())
        crop=pred[y:y+512,:]
        pos+=np.bincount(crop[valid & ink],minlength=256)
        neg+=np.bincount(crop[valid & ~ink],minlength=256)
    n=int(pos.sum()+neg.sum()); p=int(pos.sum())
    legacy_pos=np.zeros(256,dtype=np.int64); legacy_neg=np.zeros(256,dtype=np.int64)
    regions,_=find_regions(mask_group)
    for region in regions:
        bbox=region['bbox']; y0,y1,x0,x1=bbox
        valid=read_plane(mask_group,bbox); ink=read_plane(truth_group,bbox)
        crop=pred[y0:y1,x0:x1]
        legacy_pos+=np.bincount(crop[valid & ink],minlength=256)
        legacy_neg+=np.bincount(crop[valid & ~ink],minlength=256)
    ln=int(legacy_pos.sum()+legacy_neg.sum()); lp=int(legacy_pos.sum())
    assert (ln,lp)==(record['expected_pixels'],record['expected_ink']),('legacy support changed',segment,ln,lp)
    assert np.all(legacy_pos>=pos) and np.all(legacy_neg>=neg),'Legacy must cover all unique pixels'
    legacy_best=best_threshold(legacy_pos,legacy_neg)
    _,_,legacy_f1=sweep(legacy_pos,legacy_neg)
    assert abs(float(legacy_f1[legacy_best])-record['prior_oracle_f1'])<=.000051,('legacy oracle mismatch',segment,key(record))
    assert abs(float(legacy_f1[record['prior_oracle_threshold']])-float(legacy_f1[legacy_best]))<1e-12
    best=best_threshold(pos,neg); tp,fp,f1=sweep(pos,neg)
    result={k:v for k,v in record.items() if k not in ('prediction','labels')}
    result.update(prediction_file=pred_path.name,prediction_sha256=pred_digest,
                  mask_sha256=mask_hash.hexdigest(),truth_sha256=truth_hash.hexdigest(),
                  positive_hist=pos.tolist(),negative_hist=neg.tolist(),pixels=n,ink=p,
                  oracle_threshold=best,oracle_f1=float(f1[best]),
                  legacy_positive_hist=legacy_pos.tolist(),legacy_negative_hist=legacy_neg.tolist(),
                  legacy_oracle_f1=float(legacy_f1[legacy_best]),legacy_pixels=ln,legacy_ink=lp,
                  duplicate_pixel_counts=ln-n,duplicate_ink_counts=lp-p)
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--phase',choices=['calibration','evaluation'],required=True)
    ap.add_argument('--calibration',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    records=[r for r in manifest['records'] if r['role']==args.phase]
    assert records
    out={'phase':args.phase,'manifest_sha256':file_sha(args.manifest),
         'runner_sha256':file_sha(__file__),'records':[]}
    if args.phase=='evaluation':
        assert args.calibration
        calibration=json.loads(args.calibration.read_text())
        assert calibration['phase']=='calibration'
        assert calibration['manifest_sha256']==out['manifest_sha256']
        out['calibration_runner_sha256']=calibration['runner_sha256']
        # Calibration v1 already counted unique pixels. Preserve its frozen thresholds;
        # the evaluation runner additionally reproduces legacy duplicated-box counts.
        for row in calibration['records']:
            assert row['pixels']==row['expected_pixels'] and row['ink']==row['expected_ink']
            assert best_threshold(np.array(row['positive_hist']),np.array(row['negative_hist']))==row['fixed_threshold']
        thresholds=calibration['thresholds']
        calibration_segments={r['segment'] for r in calibration['records']}
        assert not calibration_segments & {r['segment'] for r in records}
        out['calibration_sha256']=file_sha(args.calibration)
    else:
        thresholds={}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    for i,record in enumerate(records):
        result=score(record)
        k=key(record)
        if args.phase=='calibration':
            assert k not in thresholds,'Expected exactly one calibration segment per arm/seed'
            thresholds[k]=result['oracle_threshold']
        threshold=thresholds[k]
        tp,fp,f1=sweep(np.array(result['positive_hist']),np.array(result['negative_hist']))
        result.update(fixed_threshold=threshold,fixed_f1=float(f1[threshold]),
                      tp=int(tp[threshold]),fp=int(fp[threshold]))
        ltp,lfp,lf1=sweep(np.array(result['legacy_positive_hist']),np.array(result['legacy_negative_hist']))
        result.update(legacy_fixed_f1=float(lf1[threshold]),legacy_tp=int(ltp[threshold]),legacy_fp=int(lfp[threshold]))
        out['records'].append(result)
        out['complete']=len(out['records'])==len(records)
        out['thresholds']=thresholds
        args.out.write_text(json.dumps(out,indent=2)+'\n')
        print(f"{i+1}/{len(records)} {record['segment']} {k} threshold={threshold} F1={f1[threshold]:.6f}",flush=True)
    out['thresholds']=thresholds
    args.out.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':
    main()
