# 插件安装目录

壳子启动时扫描本目录下的**一级子目录**，每个子目录必须：

- 目录名 == `manifest.json` 中的 `id`
- 内含 `manifest.json` 与 `entry` 指向的 Python 文件

初始为空 —— 这正是"未安装插件时空壳启动"的验收状态。
请勿手工往这里放业务代码；用「插件管理 → 安装文件夹…」或
`python tools/plugin_cli.py install <文件夹>` 安装，卸载时会删除对应子目录。
