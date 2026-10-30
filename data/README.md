# 公开数据源与下载

核对日期：2026-10-30。GitHub 两个数据包的文件大小和 Qlib 摘要已通过 release API 核实；这不等于行情质量已验收。

## 选型

| 数据 | 用途 | 已核实下载大小 | 重要边界 |
| --- | --- | --- | --- |
| F.I.R.E. | 两个问题的主数据候选，带规模、换手控制 | 1,396,296,954 bytes | 上游未提供 SHA-256；退市零值规则必须审计 |
| investment_data/Qlib | 重复计算与数据处理稳健性 | 569,939,495 bytes + 511-byte manifest | 固定 2026-10-29；不是微软官方原始数据集 |
| Zenodo A 股矩阵 | 价格路径、广度的探索性复核 | 发布者声明 158,576,449 bytes | 缺开盘、成交量、规模、交易状态；授权和复权口径待确认 |

## 具体地址

### F.I.R.E.

- [发布页](https://github.com/fire-institute/fire/releases/tag/marketdata)
- [AStockData.tar.gz](https://github.com/fire-institute/fire/releases/download/marketdata/AStockData.tar.gz)
- [字段表](https://fire-institute.github.io/fire/data/a-share/)
- [缺失及退市处理说明](https://fire-institute.github.io/fire/data/)

文档描述 2015-01-01 至 2025-05-01、2509 个日期、5363 列证券，不保证每只证券在所有日期都有数据。
优先读取 `close`、`open`、`volume`、`money`、`return_adj`、`market_cap_ashare`、`turnover_ratio`。
`open/close` 是文档中的后复权价格；`open_dr/close_dr` 是原始价格。必须独立检查 `return_adj` 的百分比单位。

退市证券有零值约定：需要确认零值仅影响退市后，还是损坏退市前历史。零价格不是合法行情，不能算成 -100% 收益。
若退市前历史也不可用，需更换主数据或明确研究对象仅为可观察股票样本；不能悄悄声称全市场无偏。

### investment_data / Qlib

- [固定 release](https://github.com/chenditc/investment_data/releases/tag/2026-10-29)
- [数据包](https://github.com/chenditc/investment_data/releases/download/2026-10-29/qlib_bin.tar.gz)
- [manifest](https://github.com/chenditc/investment_data/releases/download/2026-10-29/qlib_bin.manifest.json)
- [原始 Dolt 数据库](https://www.dolthub.com/repositories/chenditc/investment_data)
- [导出代码](https://github.com/chenditc/investment_data/blob/main/qlib/dump_all_to_qlib_source.py)
- [归一化代码](https://github.com/chenditc/investment_data/blob/main/qlib/normalize.py)

先检查包内 `calendars/`、`instruments/`、`features/`，读取全量历史证券并逐日过滤。不要用今天的 CSI300 成分倒推历史市场广度。
Qlib 价格经过处理，不能把归一化价格直接当成人民币成交价，也不能未经检查就由价格乘股数计算资金约束。
底层来自多个供应商，与 F.I.R.E. 的来源独立性未证实；两套结果一致不是独立市场验证。

### Zenodo

- [数据集 DOI](https://doi.org/10.5281/zenodo.22234132)
- [A 股 HDF5 文件](https://zenodo.org/records/22234132/files/china_ashare_daily_prices_2005_2026.h5?download=1)
- [数据字典](https://zenodo.org/records/22234132/files/DATA_DICTIONARY.md?download=1)
- [发布者 manifest](https://zenodo.org/records/22234132/files/dataset_manifest.json?download=1)

HDF5 内部路径：`/date`、`/stock_code`、`/close`、`/previous_close`。
日期编码为从 `2000-01-01` 开始的天数；发布者建议用 `log(close / previous_close)` 计算日收益。
这项建议本身不证明它是含分红总收益；公司行动、停牌及退市口径未核实，不能直接作为严格策略回测主源。

## 下载与校验

完整的自然语言步骤见 [本地部署指南](../SETUP.md)。本仓库不提供自编脚本。

用浏览器打开上述直接下载链接，下载完成后移入仓库的 `data/raw/fire/`、`data/raw/qlib/` 或 `data/raw/zenodo/`。
目录可以自己创建；这些目录是建议约定，不代表 clone 后已经存在数据文件。

使用系统 SHA-256 工具与 `sources.json` 中的值对照。有上游摘要的文件要严格一致；F.I.R.E. 只有大小与本地指纹，不能称为通过上游哈希验证。
先检查归档内容及磁盘空间，再解压到单独空目录，不覆盖已有实验数据。原始数据与处理后数据被 Git 忽略。

## 授权

这些是公开获取入口，不等于已确认可在本公开仓库再分发。软件的 Apache/BSD/MIT 许可不自动覆盖上游行情。
本仓库分享来源、版本、指纹与自编工具，不镜像原始行情文件，不包含账号、token 或网络学堂文件。
正式发表或镜像数据前，需要进一步确认数据使用及再分发条件。
