"""Does inference survive a backend that only fails when it runs?

Run from a villa ink-detection tree root. Prints one JSON object describing what
maybe_compile_model returns and what the first two forwards do.
"""

from __future__ import annotations

import json
import logging

import torch

from koine_machines.inference import infer


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def main() -> None:
    capture = _Capture()
    infer.LOGGER.addHandler(capture)
    infer.LOGGER.setLevel(logging.INFO)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(0)
    eager = torch.nn.Conv3d(1, 1, 3, padding=1).eval().to(device)
    sample = torch.zeros(1, 1, 8, 16, 16, device=device)
    with torch.inference_mode():
        expected = eager(sample).clone()

    result: dict[str, object] = {"tree": infer.__file__, "device": device}
    try:
        import triton  # noqa: F401
        result["triton"] = "present"
    except Exception:
        result["triton"] = "absent"

    # compile disabled must hand back exactly the model it was given
    passthrough = infer.maybe_compile_model(eager, enabled=False, mode="reduce-overhead")
    result["disabled_returns_same_object"] = passthrough is eager

    wrapped = infer.maybe_compile_model(eager, enabled=True, mode="reduce-overhead")
    result["returned_type"] = type(wrapped).__name__

    for index in (1, 2):
        try:
            with torch.inference_mode():
                out = wrapped(sample)
            result[f"forward_{index}"] = "ok"
            result[f"forward_{index}_matches_eager"] = bool(torch.equal(out, expected))
        except Exception as exc:  # noqa: BLE001 - the failure is the datum
            result[f"forward_{index}"] = f"RAISED {type(exc).__name__}: {str(exc).splitlines()[0][:110]}"

    result["warnings"] = [m for m in capture.messages if "compile" in m.lower()]
    # .eval()/.to() must still reach the real model through the wrapper
    result["wrapper_is_module"] = isinstance(wrapped, torch.nn.Module)
    result["wrapper_params"] = sum(1 for _ in wrapped.parameters()) if isinstance(wrapped, torch.nn.Module) else None
    result["eager_params"] = sum(1 for _ in eager.parameters())
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
