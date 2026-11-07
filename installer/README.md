# 安装器 / setup.exe

本目录负责产出 **原生 Windows 安装程序**，全部使用本地工具，不依赖 Web 技术。

## 产物

| 文件 | 说明 |
| --- | --- |
| `dist/setup.exe` | Inno Setup 6 生成的标准安装向导（选择目录 → 释放文件 → 快捷方式 → 开始菜单 → 注册卸载项） |
| `dist/PluginShell-1.0.0-portable.zip` | 免安装便携版，解压后用 `python run.py` 启动 |
| `dist/setup-manifest.txt` | ISCC 生成的文件清单，便于核对打包内容 |

## 构建

```bash
winget install --id JRSoftware.InnoSetup --silent   # 首次，安装 Inno Setup 6
python installer/build.py
```

`build.py` 会自动查找 `ISCC.exe`（用户级 `LOCALAPPDATA\Programs\Inno Setup 6`、
`Program Files (x86)` 等），也支持 `ISCC_PATH` 环境变量指定。
它把 `setup.iss.template` 中的 `@@SRC@@` / `@@OUT@@` 替换成本机绝对路径后交给 ISCC 编译，
因此换台机器也能直接构建，不需要手改脚本。

## 目录

```
installer/
├── README.md              本文件
├── build.py                可复现构建脚本（zip + setup.exe）
├── setup.iss.template      Inno Setup 脚本模板（纯 ASCII，避免系统代码页问题）
├── staging/
│   ├── Launch.cmd          安装后的启动器：检查 Python / PySide6，再运行 run.py
│   ├── INFO.txt            安装向导里显示的说明页
│   └── INSTALL-CN.txt      安装后附带的中文说明
└── _build/setup.iss        构建时生成，可删除
```

## 安装包的行为与边界

- 默认安装到 `%LOCALAPPDATA%\PluginShell`，`PrivilegesRequired=lowest`，**不需要管理员权限**。
- 打包的是**项目文件**（core / sdk / ui / sample_plugins / tests / tools / README / requirements），
  不预装任何插件 —— 安装后首次启动依然是「请安装插件」的空壳状态。
- 不捆绑 Python 运行时与 PySide6：`Launch.cmd` 首次启动会执行
  `pip install -r requirements.txt`（一次联网）。内核、CLI、测试无此依赖。
- 提供标准 Windows 卸载项（设置 → 应用 → 已安装的应用 → PluginShell），
  也可用 `unins000.exe /VERYSILENT` 静默卸载。
- 桌面快捷方式默认不勾选；开始菜单快捷方式始终创建，可用 `/NOICONS` 关闭。

## 验证（静默安装到临时目录）

```bash
dist/setup.exe /VERYSILENT /NOICONS /DIR="D:\temp\ps-test" /LOG="D:\temp\ps-install.log"
D:\temp\ps-test\unins000.exe /VERYSILENT
```
