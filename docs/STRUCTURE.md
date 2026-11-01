# 目录与迁移记录

## 2026-11-02 整理

整理前的Git提交：`46f31ae4b6e84977c1ad4941258c52660ff79321`。

仓库区分三种职责：`study/`保留可复现实验，`docs/`组织操作和交接，`slides/`组织展示。根目录只提供导航、构建入口和工具配置。

| 原位置 | 现位置 | 处理 |
| --- | --- | --- |
| `src/`、`tests/`、`config/` | `study/`下同名目录 | 原字节迁移 |
| `run_*.py`、`build_*.py`、`verify_*.py`及汇总脚本 | `study/` | 原字节迁移 |
| 四份冻结方案 | `study/` | 原字节迁移，保持证据指纹 |
| `results/`、`reports/` | `study/`下同名目录 | 原结果和报告保留 |
| `data/` | `study/data/` | 本地归档、解压文件及账户文件一起移动，继续忽略 |
| `requirements*.txt` | `study/` | 原字节迁移 |
| `RUN.md`、`SETUP.md`、`HANDOFF.md` | `docs/` | 更新运行起点和相对链接 |
| `project_context.md`、`IMPLEMENTATION_LOG.md` | `docs/` | 保留研究边界与历史记录 |
| `.venv/` | 不变 | 避免移动后破坏虚拟环境绝对路径 |
| `outputs/`、`.mplconfig/`、`__pycache__/` | `study/` | 已有临时产物保留，继续忽略 |

## 为什么不拆开旧研究脚本

整合报告绑定37个原始证据指纹，补充报告同时记录生成器和方案摘要。`study/`作为完整模块迁移，保留所有内部相对路径，避免为了改目录重写历史证据清单。研究计算入口仍然集中在该模块根目录，函数实现集中在`study/src/`。

这是文件组织和展示版本更新，不是新一次回测。三份PDF、数值CSV和冻结代码与整理前一致；`make verify`继续检查原证据。测试日志与核验收据可以刷新，历史数值结果不随之改写。新讲稿使用独立的图表和构建收据，不覆盖研究原图。

## 发布入口

根目录README负责导航。`slides/dist/`包含29页PDF、离线HTML和构建收据；`slides/quant-study.md`保留可编辑正文与讲者备注。参考资料、代码索引与构建命令放在仓库文档，投屏页面不展示页眉、来源脚注或文献编号。

更新后不再从仓库根目录直接执行旧的`run_study.py`等命令：先进入`study/`，或使用根目录Makefile中的核验入口。现有`.venv/`保持原位置，无需为了迁移重装环境。

## 日常维护

- 运行研究先进入`study/`，或使用根目录`make test`、`make verify`。
- 修改汇报只编辑`slides/quant-study.md`与主题，不手改导出的HTML/PDF。
- 新图写入`slides/assets/`，数据来源和SHA-256写入`slides/assets/manifest.json`。
- 新实验应另立方案和结果版本，不覆盖本轮固定证据。
- 行情、逐股分数、账户明细、环境、缓存及截图不提交；最终PDF/HTML和可复核的聚合数据保留。
