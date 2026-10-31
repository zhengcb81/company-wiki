import ctypes, ctypes.wintypes as wt, json, os, sys, importlib.metadata as im

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", wt.DWORD), ("dwMemoryLoad", wt.DWORD),
                ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64)]

st = MEMORYSTATUSEX(); st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
G = 1024 ** 3
out = {
    "python": sys.executable,
    "python_version": sys.version.split()[0],
    "mem_load_pct": st.dwMemoryLoad,
    "avail_phys_GB": round(st.ullAvailPhys / G, 2),
    "total_phys_GB": round(st.ullTotalPhys / G, 2),
    "avail_commit_GB": round(st.ullAvailPageFile / G, 2),
}
for pkg in ("rapidocr", "onnxruntime", "torch", "transformers", "accelerate",
            "safetensors", "tokenizers", "pillow", "huggingface_hub", "numpy"):
    try:
        out[f"pkg_{pkg}"] = im.version(pkg)
    except im.PackageNotFoundError:
        out[f"pkg_{pkg}"] = None
print(json.dumps(out, indent=1))
print("HF_HOME=" + str(os.environ.get("HF_HOME")))
hub_dir = os.path.join(os.environ.get("USERPROFILE", ""), ".cache", "huggingface", "hub")
if os.path.isdir(hub_dir):
    names = sorted(os.listdir(hub_dir))
    print("HF_HUB_ENTRIES=" + json.dumps(names))
    total = 0
    for root, _dirs, files in os.walk(hub_dir):
        for f in files:
            try: total += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    print("HF_HUB_TOTAL_GB=" + str(round(total / G, 3)))
else:
    print("HF_HUB_DIR=absent")
