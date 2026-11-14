"""可复现构建脚本：生成 dist/setup.exe 与便携版 ZIP。

    python installer/build.py

依赖：Inno Setup 6（winget install --id JRSoftware.InnoSetup）。
也可用环境变量 ISCC_PATH 指定 ISCC.exe 位置。
不使用任何 Web 技术：只有 Windows 原生安装器编译器 + Python 标准库。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "installer" / "_build"
ZIP_NAME = "PluginShell-1.1.0-portable.zip"
# Inno Setup 警告：名为 setup.exe 的程序会被 Windows 应用兼容性 shim 处理，
# 有 DLL 劫持面。保留用户要求的名字，同时提供推荐名的同一份副本。
ALIAS_NAME = "PluginShell-1.1.0-setup.exe"

EXCLUDE_DIRS = {".git", "dist", "installer", "__pycache__", ".venv", "release"}
EXCLUDE_FILES = {"enabled.json", "setup-manifest.txt", "*.pyc"}


def find_iscc() -> Path | None:
    override = os.environ.get("ISCC_PATH")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override))
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files_x86 = os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)"
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe")
    candidates += [
        Path(program_files_x86) / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def clean_pycache() -> None:
    for path in ROOT.rglob("__pycache__"):
        if path.is_dir() and DIST not in path.parents:
            shutil.rmtree(path, ignore_errors=True)


def iter_project_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        if path.name in EXCLUDE_FILES or path.suffix == ".pyc":
            continue
        yield relative, path


def build_portable_zip() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    output = DIST / ZIP_NAME
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, path in iter_project_files():
            archive.write(path, str(Path("PluginShell") / relative))
    print(f"PORTABLE_ZIP {output} ({output.stat().st_size} bytes)")
    return output


def build_setup_exe() -> Path | None:
    iscc = find_iscc()
    if iscc is None:
        print("ISCC_NOT_FOUND: 请先安装 Inno Setup 6")
        print("  winget install --id JRSoftware.InnoSetup --silent")
        return None
    BUILD.mkdir(parents=True, exist_ok=True)
    template = (ROOT / "installer" / "setup.iss.template").read_text(encoding="utf-8")
    script = BUILD / "setup.iss"
    script.write_text(
        template.replace("@@SRC@@", str(ROOT)).replace("@@OUT@@", str(DIST)),
        encoding="utf-8-sig",
    )
    print(f"ISCC {iscc}")
    result = subprocess.run([str(iscc), str(script)], capture_output=True, text=True)
    message = (result.stdout + result.stderr).strip()
    if message:
        print(message[-4000:])
    exe = DIST / "setup.exe"
    if result.returncode != 0 or not exe.is_file():
        print(f"ISCC_FAILED returncode={result.returncode}")
        return None
    print(f"SETUP_EXE {exe} ({exe.stat().st_size} bytes)")
    alias = DIST / ALIAS_NAME
    shutil.copyfile(exe, alias)
    print(f"SETUP_ALIAS {alias}（推荐用于分发，避开 setup.exe 的 Windows 兼容层 shim）")
    return exe


def main() -> int:
    clean_pycache()
    build_portable_zip()
    exe = build_setup_exe()
    if exe is None:
        return 1
    manifest = DIST / "setup-manifest.txt"
    if manifest.is_file():
        lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"MANIFEST_ENTRIES {len(lines)}")
    print("BUILD_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
