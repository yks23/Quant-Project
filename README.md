# Quant-Project

**同样的跌幅，不同的过程：A股短期反转的信息增量与执行边界。**

量化投资策略小组作业。使用公开日频行情，检验下跌集中度、市场广度与短期反转，并区分预测增量和成本后的收益。

当前汇报为 **29页 Marp**：26页主讲、3页附录，覆盖 Motivation、公式、方法、数据导入、回测验证与结论。采用简洁数学讲义风格，不设页眉、来源脚注或正文文献编号；参考资料留在仓库说明中。

## 阅读入口

| 想做什么 | 打开这里 |
| --- | --- |
| 直接汇报 | [29页 PDF](slides/dist/quant-study.pdf) · [离线 HTML](slides/dist/quant-study.html) |
| 修改讲稿 | [Markdown 源稿](slides/quant-study.md) · [构建与讲述说明](slides/README.md) |
| 阅读完整研究 | [整合报告 PDF](study/reports/integrated_research_report.pdf) · [Markdown](study/reports/integrated_research_report.md) |
| 安装、下载、复现 | [运行指南](docs/RUN.md) |
| 查看实际结果 | [第一轮结果](study/results/) · [机制与执行诊断](study/results/exploration/) |
| 了解文件结构 | [目录与迁移说明](docs/STRUCTURE.md) |

PDF可直接阅读、投屏或打印。HTML需要下载后或clone到本地打开；GitHub文件页展示源文件，不是在线放映。成品无需安装Python、Node.js或启动服务器。

## 目录

```text
Quant-Project/
├── README.md                阅读入口
├── Makefile                 测试、核验与构建入口
├── package.json             固定版本的 Marp 工具链
├── docs/                    复现说明、交接资料、整理记录
├── slides/                  数学讲义风格的汇报
│   ├── quant-study.md       可编辑源稿，含逐页讲者备注
│   ├── theme/               宋体、衬线公式、细线表格主题
│   ├── assets/              从既有 CSV 重绘的展示图
│   ├── scripts/             构建、图表和版面核验
│   └── dist/                可直接使用的 PDF 与离线 HTML
└── study/                   自包含、可复核的研究模块
    ├── src/                 数据、因子、账户、风险模型与统计
    ├── tests/               27 项研究单元测试
    ├── config/              固定方案与证据指纹
    ├── data/                数据说明；本地行情和中间文件不入库
    ├── results/             聚合结果及运行收据
    ├── reports/             三份研究报告与原图
    ├── run_*.py             两轮研究和执行扩展
    ├── build_*.py           报告生成
    └── verify_*.py          研究结果与证据核验
```

`study/`整体迁移自原仓库根目录，计算代码、冻结方案、数值结果和三份报告均保留原字节。内部相对路径不变，因此原来的37项证据指纹继续有效。新展示材料只读取既有结果，不重跑或调整策略；测试日志和核验收据按本次检查刷新。

## 快速使用

### 获取项目

```bash
git clone https://github.com/yks23/Quant-Project.git
cd Quant-Project
```

已有工作副本先确认本地改动，再同步远端。旧版根目录中的研究命令现在需要先进入`study/`；下列命令均从仓库根目录执行。

### 修改汇报

编辑[slides/quant-study.md](slides/quant-study.md)，修改配色、字体或间距则编辑[主题](slides/theme/lecture.css)。安装Node.js 18+和Chrome、Edge或Firefox后执行：

```bash
npm ci
npm run slides
```

输出覆盖`slides/dist/quant-study.pdf`和`quant-study.html`。PDF已嵌入中文字体；其他机器重新构建时需要安装中文字体。浏览器版可离线放映，源稿中的逐页讲者备注保留。

### 核验或复现研究

使用Python 3.12安装固定依赖，先核验已提交的聚合结果与报告，无需下载完整行情：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r study/requirements-tested.txt
make test
make verify
```

全量行情的下载和计算在[运行指南](docs/RUN.md)，不需要数据库账号或 API key。

| 操作 | 根目录命令 | 是否需要原始行情 |
| --- | --- | --- |
| 研究单元测试 | `make test` | 否 |
| 三份报告及证据核验 | `make verify` | 否 |
| 从固定CSV重绘展示图 | `make figures` | 否 |
| 导出PDF与HTML | `npm run slides` | 否 |
| 导出后检查版面与离线播放 | `npm run slides:check` | 否，需本机Chromium浏览器 |
| 核对讲稿数字与迁移结果 | `python slides/scripts/verify_content.py` | 否，需保留Git历史 |

`make figures`只更新展示图，不改变研究结果。全量回测命令见运行指南，会重建研究输出，修改方案前应另立结果版本。

## 数据与版本

主研究使用固定的F.I.R.E.公开行情包，字段、下载入口和实际摘要见[数据说明](study/data/README.md)。仓库只提交代码、聚合结果、图表、报告和Marp成品。

原始行情、逐股分数、账户中间文件、虚拟环境、Node依赖和临时截图保留在本地并由`.gitignore`排除。数据可公开获取不等于获得再分发授权。

[展示核验记录](slides/qa/README.md)提供29页版面、30个分组Alpha单元格和原文件迁移检查；研究原始证据收据保存在`study/results/`。

## 结论口径

2022-2024原固定留出期，PATH合成多空年化算术均值从零成本的 **12.45%** 降为单边10bp后的 **-2.91%**；BREADTH零成本即为 **-10.71%**。两个正Alpha主假设均未获支持。CAPM、FF3和Carhart4采用本地FF式代理，不是官方因子序列。

后续探索拆分集中度、发生时点和市场同步性，未发现稳定五日预测增量。固定半量调仓使PATH多头净年化均值改善 **1.48个百分点**，但CAGR仍为 **-2.03%**。这轮使用已查看样本，不把它称为新的独立留出检验。

本项目的贡献是测量辨析、增量对照和执行核算，不宣称发现两个可交易新Alpha。原始行情不随仓库再分发；历史退市完整性、财务PIT、真实融券及冲击成本仍构成解释边界。
