"""Regression checks for exact ties and overlapping annotation-region boxes."""
from pathlib import Path
import sys

import numpy as np
import tifffile
import zarr

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from eval_fixed_threshold_ft import best_threshold, score


def test_lowest_threshold_wins_an_exact_f1_tie():
    positive=np.zeros(256,dtype=np.int64)
    negative=positive.copy()
    positive[200]=1
    negative[0]=24
    assert best_threshold(positive,negative)==1


def test_each_pixel_is_counted_once_when_region_boxes_overlap(tmp_path):
    segment='synthetic'
    folder=tmp_path/segment
    folder.mkdir()
    mask=np.zeros((1,9,9),dtype=np.uint8)
    mask[0,1,1:8]=1; mask[0,7,1:8]=1
    mask[0,1:8,1]=1; mask[0,1:8,7]=1
    mask[0,4,4]=1
    labels=np.zeros_like(mask); labels[0,4,4]=1
    assert mask.sum()==25
    for kind,array in [('supervision_mask',mask),('inklabels',labels)]:
        group=zarr.open_group(str(folder/f'{segment}_{kind}.zarr'),mode='w')
        group.create_dataset('0',data=array,chunks=(1,9,9))
    prediction=np.zeros((9,9),dtype=np.uint8); prediction[4,4]=200
    path=tmp_path/'prediction.tif'
    tifffile.imwrite(path,prediction)
    result=score(dict(scroll='synthetic',arm='base',seed=42,segment=segment,
                      prediction=str(path),labels=str(folder),expected_pixels=26,
                      expected_ink=2,prior_oracle_f1=1.,prior_oracle_threshold=1))
    assert result['pixels']==25 and result['ink']==1
    assert result['legacy_pixels']==26 and result['legacy_ink']==2
    assert result['duplicate_pixel_counts']==result['duplicate_ink_counts']==1
    assert result['positive_hist'][200]==1
    assert result['legacy_positive_hist'][200]==2
