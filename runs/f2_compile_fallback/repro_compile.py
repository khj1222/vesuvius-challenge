"""Does torch.compile raise where infer.py guards it, or later?"""
import json, torch, traceback

result = {"torch": torch.__version__, "cuda": torch.cuda.is_available()}
try:
    import triton  # noqa: F401
    result["triton"] = "present"
except Exception as e:
    result["triton"] = f"absent ({type(e).__name__})"

model = torch.nn.Conv3d(1, 1, 3, padding=1).eval()
if torch.cuda.is_available():
    model = model.cuda()

# 1. the call infer.py wraps in try/except
try:
    compiled = torch.compile(model, mode="reduce-overhead", fullgraph=False, dynamic=False)
    result["compile_call"] = "returned without raising"
except Exception as e:
    result["compile_call"] = f"RAISED {type(e).__name__}: {e}"
    compiled = None

# 2. the first forward, which infer.py does not guard
if compiled is not None:
    x = torch.zeros(1, 1, 8, 16, 16, device="cuda" if torch.cuda.is_available() else "cpu")
    try:
        with torch.inference_mode():
            compiled(x)
        result["first_forward"] = "ok"
    except Exception as e:
        result["first_forward"] = f"RAISED {type(e).__name__}: {str(e).splitlines()[0][:160]}"
        result["first_forward_frames"] = [
            l.strip() for l in traceback.format_exc().splitlines() if "File " in l
        ][-3:]
print(json.dumps(result, indent=1))
