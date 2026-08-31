"""The cache must still hit when nothing changed, and after a byte-identical copy."""
import json, shutil, tempfile, time
from pathlib import Path
from koine_machines.data.ink_dataset import InkDataset

SRC = Path("D:/vesuvius-challenge/data/ink_9um/labels/annotarget/disagreemin/phercparis4-w00")
REAL = Path("D:/vesuvius-challenge/configs/ink9um_at_disagreemin_s42.json")

def cfg(labels, out):
    c = json.loads(REAL.read_text(encoding="utf-8"))
    c["datasets"][0]["segments_path"] = str(labels); c["out_dir"] = str(out); return c

def timed(c):
    t0 = time.perf_counter(); d = InkDataset(c, do_augmentations=False)
    return len(d.patches), round(time.perf_counter() - t0, 2)

work = Path(tempfile.mkdtemp(prefix="f4hit."))
labels = work / "labels"; labels.mkdir()
shutil.copytree(SRC, labels / SRC.name)
out = work / "run"; out.mkdir()

n1, t1 = timed(cfg(labels, out))
n2, t2 = timed(cfg(labels, out))
# a byte-identical copy of the tree must fingerprint the same, so a copied corpus still hits
labels2 = work / "labels_copy"; labels2.mkdir()
shutil.copytree(SRC, labels2 / SRC.name)
out2 = work / "run2"; out2.mkdir()
n3, t3 = timed(cfg(labels2, out2))
n4, t4 = timed(cfg(labels2, out2))
print(json.dumps({
    "first_discovery": {"patches": n1, "seconds": t1},
    "second_same_tree": {"patches": n2, "seconds": t2, "cache_hit": t2 < t1 / 2 and n2 == n1},
    "copied_tree_first": {"patches": n3, "seconds": t3},
    "copied_tree_second": {"patches": n4, "seconds": t4, "cache_hit": t4 < t3 / 2 and n4 == n3},
}, indent=1))
shutil.rmtree(work, ignore_errors=True)
