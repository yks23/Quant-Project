# 下载与本地部署指南

本指南面向第一次接手项目的组员。无需数据库账号、不用购买接口，也不需要启动网页或服务端。
本指南保留多数据源的下载选择；运行本次两个因子请先看[RUN.md](RUN.md)。原始大文件从公开上游获取，不再分发。
2026-11-02起，研究模块在`study/`；下文数据目录均以`study/`为起点。多数据源目录是早期接手约定，主实验的确切归档路径以RUN指南为准。

## 1. 先选哪套数据

优先下载 **F.I.R.E.**：它有复权价格、成交量、换手和市值，适合同时研究下跌路径和市场广度。
若想先熟悉 Qlib，或者核对第一套数据下的结果，下载固定版本的 **investment_data**。
不需要一次把三套都下载。**Zenodo** 仅作为轻量的价格探索备选，不能替代包含成交和规模信息的主数据。

## 2. 准备本地工作目录和环境

从 `https://github.com/yks23/Quant-Project` clone 仓库；没有 Git 的同学也可以在 GitHub 页面点击 Code → Download ZIP，再解压到自己的项目目录。
仓库根目录包含`README.md`、`study/`和`slides/`；本指南位于`docs/`。以下研究数据路径以`study/`为起点，不是某位组员机器上的固定绝对路径。

本次研究采用 Python 3.12 独立虚拟环境，固定依赖见`study/requirements-tested.txt`。备选数据源可能另有兼容要求；不要混用系统 Python 和其他项目的依赖。
Windows 可用原生 Python，Qlib 安装遇到编译问题时优先考虑 WSL；Mac 和 Linux 可直接使用终端。

Mac/Linux 的基础环境命令如下，Windows 激活入口对应 `.venv\Scripts\Activate.ps1`：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
cd study
```

请先确认创建虚拟环境的 `python3` 版本。激活后所有安装统一用 `python -m pip`。
建议准备至少 15 GB 空闲磁盘，供压缩包、解压、缓存和研究输出使用；这是预留建议，不是测量出的解压大小。内存较小时先只加载少数字段和一年数据。

建议手动建立以下目录：

| 目录 | 放什么 |
| --- | --- |
| `data/raw/fire/` | F.I.R.E. 原始压缩包 |
| `data/raw/qlib/` | Qlib 原始压缩包及 manifest |
| `data/raw/zenodo/` | Zenodo 原始 HDF5 |
| `data/processed/` | 验收后统一的研究数据，保留原始数据不动 |
| `outputs/` | 图、表和数据验收报告 |

这些本地数据与输出目录已被 `.gitignore` 排除。完成第一次安装后，把依赖版本、Python 版本、操作系统、下载日期和数据文件 SHA-256 记到实验记录中。

## 3. F.I.R.E.：推荐的主数据候选

### 下载

打开 [AStockData.tar.gz 直接下载链接](https://github.com/fire-institute/fire/releases/download/marketdata/AStockData.tar.gz)，下载后放在 `data/raw/fire/`。
若直接链接失败，进入 [MarketData 发布页](https://github.com/fire-institute/fire/releases/tag/marketdata)，展开 Assets，点击 `AStockData.tar.gz`。不要下载 `bond_data.tar.gz`，也不要把 Source code ZIP 当成行情数据。

2026-10-30 查询 GitHub API 得到文件大小为 **1,396,296,954 字节**，约 1.40 GB。发布 tag 是 `marketdata`，对应行情 asset ID 是 `256635084`。
该发布 tag 可修改，上游未给出 SHA-256；因此同名文件不一定永远相同。下载后计算自己的 SHA-256，并让全组核对一致。

### 部署和加载

本研究改为直接读取归档中的真实Feather文件，不依赖`firefin`。若按本节旧目录下载，可执行：

```bash
python -m pip install -r requirements-tested.txt
python run_study.py --extract --archive data/raw/fire/AStockData.tar.gz
```

代码仅提取白名单字段，校验日期/代码对齐及缺失值。默认根目录为`data/extracted/fire_data/`。
2026-10-31核查上游`src/firefin/data/gateway.py`发现，无效字段可能返回随机合成数据，故不要把`fetch_data`返回矩阵直接当作真实行情。
直接用pandas的`read_feather`读取已核实文件，缺字段时停止，而不是补随机值。当前数据包保留了pandas日期索引；读取后显式转换为日期。

### 如何确认部署成功

应能显示日期范围、证券列名和少量非空价格，并检查开收盘、成交量矩阵是否对齐。文档描述的覆盖为 2015-01-01 至 2025-05-01，2509 行、5363 列，但需以实际文件为准。
价格矩阵的正值不能被错误转成字符串；零价不能用于收益计算。特别检查退市证券零值究竟出现在哪些日期。
详细字段和已知风险见 [数据说明](../study/data/README.md)。只有满足字段验收，才能开始比较因子结果。

## 4. investment_data：另一套公开量价数据

### 下载固定版本

进入 [2026-10-29 发布页](https://github.com/chenditc/investment_data/releases/tag/2026-10-29)，下载两个文件到 `data/raw/qlib/`：

- [qlib_bin.tar.gz](https://github.com/chenditc/investment_data/releases/download/2026-10-29/qlib_bin.tar.gz)：569,939,495 字节。
- [qlib_bin.manifest.json](https://github.com/chenditc/investment_data/releases/download/2026-10-29/qlib_bin.manifest.json)：511 字节。

全组使用相同固定版本，不使用持续变化的 `latest`。两个文件的 SHA-256 都保存在 [sources.json](../study/data/sources.json)；该记录来自 GitHub release API。

Mac 使用 `shasum -a 256 文件路径`，Linux 使用 `sha256sum 文件路径`，Windows PowerShell 使用 `Get-FileHash 文件路径 -Algorithm SHA256`。
输出摘要必须与清单对应文件的 `sha256` 字段完全一致。大小正确不代表内容正确；摘要不一致时停止加载，重新核实版本，不能直接修改清单使其通过。

### 解压并安装读取环境

建议为 Qlib 单独建虚拟环境，安装包名是 `pyqlib`，不是 `qlib`：

```bash
python -m pip install pyqlib
```

先用解压工具浏览压缩包内容。将包解压到新的空目录，例如 `data/raw/qlib/unpacked/`。
找到真正包含 `calendars`、`instruments`、`features` 三个子目录的位置；归档可能有一层 `qlib_bin` 父目录，不要把外层目录误当数据根目录。

在 Python 中用 `qlib.init` 初始化，把 `provider_uri` 设为这个实际数据根目录的绝对路径，`region` 设为 `qlib.constant.REG_CN`。
使用 `qlib.data.D` 的数据接口：先读取交易日历和历史全量股票池，再用 `D.features` 请求 `$open`、`$close`、`$volume`。
第一轮只取一只历史确有数据的股票和一个月，确认加载成功后再扩展。`all` 股票池是否存在，应检查包内 instruments 文件，而不是默认认定。

Qlib 的 `.bin` 不是 CSV；不要直接用 pandas 的 `read_csv` 打开。它的价格和成交量可能经过归一化，不是直接的人民币价格和原始股数。
读取方法参考 [Qlib Data API](https://qlib.readthedocs.io/en/latest/component/data.html)。Mac 遇到 OpenMP/LightGBM 相关报错时参考 [官方安装说明](https://github.com/microsoft/qlib#installation)，不要把包安装失败误认为数据损坏。

### 如何确认部署成功

应能读取交易日期、股票有效区间和非空行情。检查最后有效观测，而不是把未来交易日历当作已有行情。
市场广度需要历史有效股票池，不能只读取默认的 CSI300 策略样本。读取成功还不等于历史退市股票完整或所有交易约束已经处理。

## 5. Zenodo：轻量价格探索备选

打开 [公开数据集页面](https://zenodo.org/records/22234132)，下载 [A 股 HDF5 文件](https://zenodo.org/records/22234132/files/china_ashare_daily_prices_2005_2026.h5?download=1) 到 `data/raw/zenodo/`。
不要下载本题不需要的期货分钟文件；同时阅读页面上的 README、DATA_DICTIONARY 和 dataset_manifest。
发布者声明 A 股文件为 158,576,449 字节，SHA-256 已记录在 `data/sources.json`，用上一节的系统工具核对。

在独立环境安装 `h5py`、`numpy` 和 `pandas`，用 h5py 读取文件。内部数据路径是 `/date`、`/stock_code`、`/close`、`/previous_close`。
`date` 表示从 2000-01-01 开始的天数；股价矩阵行对应日期、列对应证券，缺失值是 NaN，不要填成零。
先读取小切片检查维度和日期。发布者声明矩阵为 5250 × 5385；仅价格矩阵就需要数百 MB 内存，转换和复制会进一步增加内存。

该源没有开盘、成交量、市值和交易状态；复权与退市口径、再分发授权仍不明确。适合练习指标计算，不作为严谨主结论的唯一依据。

## 6. 从加载成功到两个问题的最小测试

先把选定来源整理成对齐的日期 × 股票矩阵；保留原始文件，处理后的数据另存。不同来源不要直接拼成一条收益序列。
所有收益统一到小数口径，不要把百分数 5 当成收益 5.0。复权价格和原始价格不可混用；缺失和零价不能用于除法。

**问题一：下跌路径。** 对每只股票读取连续五个交易日的有效收益，计算累计收益和负收益集中度；从相近累计跌幅的股票中比较集中度高低组。公式、最后一天收益控制和其他混杂因素见 `HANDOFF.md`。

**问题三：市场广度。** 每个日期先确定有效交易股票，再计算下跌股票比例。停牌、缺失记录不算正常样本；同时保存每天的分母数量。比较不同市场状态下下跌信号的表现，而不是拿对所有股票相同的市场广度直接计算横截面 RankIC。

先用一个开发年度检查程序，再扩展样本。计划中的最终留出年份先不要看因子表现。部署成功的最低标准是能读取有效行情、解释缺失值、计算上述两个指标并检查人工样例，而不是已经出现正收益。

## 7. 遇到问题时

- 下载链接失败：回到对应发布页点击原始 asset；不要复制带临时签名的跳转 URL 作为长期地址。
- 下载速度慢：用浏览器或支持续传的下载器保留固定版本，结束后仍需校验摘要；不改用不明镜像。
- 解压失败：先检查大小与 SHA-256，确保不是 GitHub 错误网页或半个文件。
- 模块不存在：确认 Notebook 与终端使用相同虚拟环境，不要在另一个 Python 环境重复安装。
- 数据全空：检查实际数据根目录、证券代码格式、查询日期与字段名；不要先填充缺失值掩盖路径问题。
- 多人结果不一致：先比较文件 SHA-256、依赖版本、日期范围和股票池过滤，再比较因子算法。

## 8. 给下一位同学的交接记录

完成本地部署后，记录实际数据路径、原始文件 SHA-256、下载时间、环境版本、实际覆盖、缺失和零值规则，以及最小读取测试是否通过。
公开仓库只提交研究代码、说明和经审查的结果；不提交 token、私人绝对路径、原始行情或受限账号信息。
公开下载不等于可任意再发布数据，仓库的软件许可证也不代替上游数据授权。
