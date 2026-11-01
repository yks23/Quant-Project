# Marp 汇报讲义

**同样的跌幅，不同的过程：A股短期反转的信息增量与执行边界。**

- [PDF成品](dist/quant-study.pdf)：可以投屏或直接打印，含书签。
- [离线HTML](dist/quant-study.html)：浏览器直接打开，图片和公式已嵌入。
- [Markdown源稿](quant-study.md)：逐页正文与讲者备注。
- [主题](theme/lecture.css)：白底、宋体/衬线、细线表格和公式，无装饰性卡片。

## 如何讲

29页，其中主讲26页，附录3页。完整讲述约20-25分钟；时间较紧时可合并公式与实现验证页，附录只在问答时使用。
投屏页面不设页眉、来源脚注或文献编号，只保留页码。资料链接、代码路径和构建说明留在本文件与仓库中；样本时期、成本、收益口径和探索性质保留在相应正文中。

| 页码 | 内容 | 讲述重心 |
| --- | --- | --- |
| 1-3 | Motivation | 同一终点为什么可能遗漏过程信息；两个研究问题 |
| 4-7 | 定义与方法 | PATH与BREADTH究竟测量什么；如何区分排序、增量和执行 |
| 8-10 | 数据 | 公开包、导入流程、过滤条件和证据分期 |
| 11-13 | 账户与统计 | 只在信号后入场、按成交额收费、本地风险代理 |
| 14-18 | 固定验证 | 分组、曲线、Alpha、费用分解、切换假设诊断 |
| 19-23 | 探索性诊断 | C/RECENT/SYNC、强基线、入场前后、冻结预测、半量调仓 |
| 24-26 | 验证与结论 | 对账和测试、解释边界、三项有证据的贡献 |
| 27-29 | 附录 | 指标、分组Alpha、字段与稳健性 |

讲者备注写在每页Markdown的HTML注释中。用Marp的HTML演讲者模式可查看备注；普通投屏画面只展示正文。

## 构建

在仓库根目录执行，Node.js 18+；PDF导出另需Chrome、Edge或Firefox：

```bash
npm ci
npm run slides
```

构建会核对图表输入的SHA-256，把图像嵌入离线HTML，并导出PDF。若图表脚本或证据变动，先核查是否需要新研究版本，再重新生成图：

```bash
source .venv/bin/activate
make figures
npm run slides
npm run slides:check
```

`slides:check`用本机Chrome检查每页内容边界、数学错误、图片加载和离线播放；可通过`BROWSER_PATH`指定Chromium浏览器路径。页面截图只在本地`slides/qa/rendered/`，不入库。

主稿使用MathJax公式，不需要安装LaTeX。宋体优先使用macOS的Songti SC，其他平台回退到Noto Serif CJK SC或SimSun；PDF已嵌入字体。重新构建前需确保本机安装中文字体。

配置依据：[Marp CLI](https://github.com/marp-team/marp-cli#readme)、[Marpit主题](https://marpit.marp.app/theme-css)。`allowLocalFiles`仅用于本仓库可信Markdown的本地构建，不用于陌生文件。

## 证据关系

讲稿只整合既有研究，不产生新回测。六张SVG展示图由[make_figures.py](scripts/make_figures.py)从固定聚合表生成；`assets/manifest.json`记录输入与图像摘要，`dist/manifest.json`记录源稿、主题和导出产物摘要。

完整计算说明在[docs/RUN.md](../docs/RUN.md)，原三份报告在[study/reports/](../study/reports/)。展示收益统一标注时期、成本、算术/复利、事件/账户，以及本地风险代理。重复使用2022-2024的新增分析均标为探索性。

## 资料索引（不投屏）

1. Da, Gurun & Warachka. *Frog in the Pan: Continuous Information and Momentum*. 工作论文版本，2011。 [原文](https://business.uq.edu.au/sites/default/files/events/files/mitch-warachka-paper.pdf)
2. Da, Liu & Schaumburg. *Decomposing Short-Term Return Reversal*. FRBNY Staff Report 513，2011。 [论文页](https://www.newyorkfed.org/research/staff_reports/sr513.html)
3. Nagel. *Evaporating Liquidity*. NBER Working Paper 17653，2011。 [原文](https://www.nber.org/system/files/working_papers/w17653/w17653.pdf)
4. de Groot, Huij & Zhou. *Another Look at Trading Costs and Short-Term Reversal Profits*. JBF 36(2)，2012。 [工作论文](https://repub.eur.nl/pub/25718/AnotherLook_2011.pdf)
5. F.I.R.E. [A股字段文档](https://fire-institute.github.io/fire/data/a-share/) · [公开行情发布页](https://github.com/fire-institute/fire/releases/tag/marketdata)
6. [Quant-Project](https://github.com/yks23/Quant-Project)：代码、聚合结果、原始报告及本讲稿。

原幻灯片中的来源脚注已移出投屏页面。数值出处：`study/results/performance.csv`、`alpha_local_proxy.csv`、`daily_portfolio_returns.csv`、`breadth_by_period.csv`以及`study/results/exploration/`中的费用、机制、预测与执行结果。图表逐文件来源和摘要继续保存在`assets/manifest.json`。
