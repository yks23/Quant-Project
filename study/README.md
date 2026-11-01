# 可复现实验

这里是研究运行根目录。代码、冻结方案、CSV和报告整体从仓库根目录迁入，内部相对路径保持不变。

- [整合研究报告](reports/integrated_research_report.pdf)
- [原始实验报告](reports/factor_study_report.pdf)
- [机制与执行诊断](reports/mechanism_execution_supplement.pdf)
- [安装、数据下载与运行](../docs/RUN.md)
- [汇报 slides](../slides/dist/quant-study.pdf)

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `src/data.py` | 归档白名单、真实Feather读取、覆盖审计 |
| `src/factors.py` | PATH、BREADTH、REV及替代代理 |
| `src/backtest.py` | 现金与持仓、成交限制、费用、半量调仓 |
| `src/risk.py` | 本地市场、规模、价值、动量代理 |
| `src/statistics.py` | 收益统计、风险回归、HAC与多重检验 |
| `src/mechanisms.py` | 集中度、时点、同步性与前后标签 |

`run_study.py`执行原始研究，`run_mechanisms.py`执行机制诊断，`run_execution_extension.py`执行固定半量调仓对照。
`build_*.py`生成三份报告，`verify_*.py`检查计算与证据。

冻结方案保留在本目录：`PROTOCOL.md`、`PROXY_MODELS.md`、`EXPLORATION_PROTOCOL.md`、`EXECUTION_EXTENSION.md`。
这些文件属于既有研究证据，不因排版或目录偏好重写。生成器与证据的相对位置同样保留。

从仓库根目录运行`make test`和`make verify`即可；直接执行原命令时，先`cd study`。
