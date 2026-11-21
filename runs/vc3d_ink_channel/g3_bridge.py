"""Minimal VC3D agent-bridge client (newline-delimited JSON-RPC 2.0 over the bridge's local socket).

    python3 g3_bridge.py METHOD '{"param": ...}'      # one call, prints the result
    python3 g3_bridge.py --wait-job METHOD '{...}'    # call, then poll job.status until it ends

The socket path comes from the discovery record VC3D writes under ~/.vc3d/agent_bridge/.
"""
import glob
import json
import os
import socket
import sys
import time


def socket_path() -> str:
    records = sorted(glob.glob(os.path.expanduser("~/.vc3d/agent_bridge/*")), key=os.path.getmtime)
    for rec in reversed(records):
        try:
            data = json.load(open(rec))
        except Exception:
            continue
        path = data.get("path") or data.get("socketPath") or data.get("fullServerName")
        if path:
            return path
    return "/tmp/g3bridge"


class Bridge:
    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(socket_path())
        self.buf = b""
        self.next_id = 1

    def call(self, method, params=None, timeout=600):
        rid = self.next_id
        self.next_id += 1
        msg = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self.sock.sendall((json.dumps(msg) + "\n").encode())
        self.sock.settimeout(timeout)
        while True:
            while b"\n" not in self.buf:
                chunk = self.sock.recv(1 << 20)
                if not chunk:
                    raise RuntimeError("bridge closed")
                self.buf += chunk
            line, self.buf = self.buf.split(b"\n", 1)
            reply = json.loads(line)
            if reply.get("id") == rid:
                return reply

    def wait_job(self, reply, poll=2.0, timeout=1800):
        result = reply.get("result") or {}
        job = result.get("jobId") or result.get("job", {}).get("id") if isinstance(result, dict) else None
        if not job:
            return reply
        t0 = time.time()
        while time.time() - t0 < timeout:
            status = self.call("job.status", {"jobId": job})
            res = status.get("result") or {}
            state = res.get("state") or res.get("status")
            if state not in ("queued", "running", "pending", None):
                return status
            if "error" in status:
                return status
            time.sleep(poll)
        return {"error": f"job {job} timed out"}


if __name__ == "__main__":
    args = sys.argv[1:]
    wait = args and args[0] == "--wait-job"
    if wait:
        args = args[1:]
    method = args[0]
    params = json.loads(args[1]) if len(args) > 1 else None
    b = Bridge()
    out = b.call(method, params)
    if wait and "result" in out:
        out = {"call": out, "final": b.wait_job(out)}
    print(json.dumps(out, indent=1, ensure_ascii=False)[:20000])
