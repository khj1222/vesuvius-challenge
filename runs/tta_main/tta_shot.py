"""Copy direction priors through TTA: main today vs this PR. CPU, no weights, no download."""
import importlib.util, math, sys
import torch

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

MAIN = load("tta_main", r"D:/shots/tmp/displacement_tta_main.py")                 # origin/main 4b3c728
PR   = load("tta_pr",   r"D:/vw10/vesuvius/src/vesuvius/neural_tracing/inference/displacement_tta.py")

class ReturnPriors:              # "model" whose displacement is its own two input direction priors
    def __call__(self, x): return x[:, 2:8]
fwd = lambda m, x, *_: m(x)

def run(mod, x, mode, starts):
    kw = dict(transform_mode=mode, tta_batch_size=1)
    if starts is not None: kw["input_vector_channel_starts"] = starts
    return mod.run_model_tta(ReturnPriors(), x, False, torch.float32, fwd, **kw)

print(f"  torch={torch.__version__}  device=cpu  input=[1,8,5,5,5]  channels: 0 volume, 1 cond, 2:5 +n (z,y,x), 5:8 -n (z,y,x)")
# 1. one constant unit normal, what every prior voxel of a flat sheet looks like
n = torch.tensor([1.0, 2.0, 3.0]) / math.sqrt(14.0)
x = torch.zeros(1, 8, 5, 5, 5)
x[:, 0] = torch.rand(5, 5, 5); x[:, 1] = 1.0
x[:, 2:5] = n.view(1, 3, 1, 1, 1); x[:, 5:8] = -n.view(1, 3, 1, 1, 1)
print("\n  1) constant prior n = (1,2,3)/sqrt(14) = (%.3f, %.3f, %.3f), model returns its input priors, mirror TTA x8" % tuple(n.tolist()))
for label, mod, starts in (("main", MAIN, None), ("this PR", PR, (2, 5))):
    out = run(mod, x, "mirror", starts)
    v = out[0, 0:3, 2, 2, 2].tolist()
    err = float((out - x[:, 2:8]).abs().max())
    print(f"     {label:8s} merged +n at the centre voxel = ({v[0]:+.3f}, {v[1]:+.3f}, {v[2]:+.3f})   max |merged - input| = {err:.2e}")
print("     -> on main the eight variants disagree about which way the sheet faces and the merge cancels them out")

# 2. random priors, both modes, both trees; legacy call on the PR tree must equal main exactly
torch.manual_seed(205); x = torch.randn(1, 8, 5, 5, 5); saved = x.clone()
print("\n  2) random priors (seed 205), max |merged - input priors|")
print(f"     {'mode':8s} {'variants':>8s}   {'main':>10s}   {'this PR':>10s}   {'PR, no starts (legacy)':>24s}")
for mode in ("mirror", "rotate3"):
    nvar = len(PR.TTA_FLIP_COMBOS) if mode == "mirror" else len(PR.TTA_ROTATE3_PERMS)
    a = run(MAIN, x, mode, None); b = run(PR, x, mode, (2, 5)); c = run(PR, x, mode, None)
    ea = float((a - x[:, 2:8]).abs().max()); eb = float((b - x[:, 2:8]).abs().max())
    same = torch.equal(a, c)
    print(f"     {mode:8s} {nvar:8d}   {ea:10.3e}   {eb:10.3e}   {('identical to main' if same else 'DIFFERS'):>24s}")
print(f"     input tensor unchanged by TTA: {torch.equal(x, saved)}")
