"""一键运行全部自动化验收： python tools/verify.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def main() -> int:
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"), pattern="test_*.py", top_level_dir=str(ROOT)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("\n验收结果:", "全部通过" if result.wasSuccessful() else "存在失败")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
