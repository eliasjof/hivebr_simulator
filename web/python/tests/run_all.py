"""Plain test runner:  python3 web/python/tests/run_all.py [substring]"""
import contextlib
import importlib
import io
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness  # noqa: E402,F401  (sets up sys.path)


def main(argv):
    pattern = argv[0] if argv else ""
    passed, failed = 0, []
    for path in sorted(HERE.glob("test_*.py")):
        mod = importlib.import_module(path.stem)
        for name in dir(mod):
            if not name.startswith("test_") or pattern not in f"{path.stem}.{name}":
                continue
            t0 = time.time()
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    getattr(mod, name)()
            except Exception:
                failed.append(f"{path.stem}.{name}")
                print(f"FAIL {path.stem}.{name}\n{traceback.format_exc()}\n--- captured stdout ---\n{buf.getvalue()[-1500:]}")
            else:
                passed += 1
                print(f"ok   {path.stem}.{name}  ({time.time() - t0:.1f}s)")
    print(f"\n{passed} passed, {len(failed)} failed")
    for f in failed:
        print("  FAILED:", f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
