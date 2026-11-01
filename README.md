# Quant-Project

量化投资策略小组作业：用公开 A 股日频数据研究下跌路径、市场广度与短期反转。

## 从这里开始

1. [完整研究报告 PDF](reports/integrated_research_report.pdf) · [Markdown](reports/integrated_research_report.md)：从Motivation、Setup、Methods到结果解释，整合两轮证据，含目录和公式。
2. [第一轮原始报告 PDF](reports/factor_study_report.pdf) · [可搜索Markdown](reports/factor_study_report.md)。
3. [一页运行指南](RUN.md)：下载固定数据、测试、全量计算和生成报告。
4. [固定研究方案](PROTOCOL.md) · [风险模型口径](PROXY_MODELS.md) · [结果表](results/)。
5. [HANDOFF.md](HANDOFF.md)说明研究设计；[SETUP.md](SETUP.md)保留多数据源自然语言部署指南。
6. [二轮机制与执行诊断 PDF](reports/mechanism_execution_supplement.pdf) · [Markdown](reports/mechanism_execution_supplement.md)：指标拆解、强控制、入场前后标签、逐年冻结预测、固定半量调仓及pre讲述提纲。

二轮研究使用已查看的2022-2024样本，全部标为探索性，不重命名为新留出检验。2025年1-4月只作短期时间扩展。新增指标未证明稳定预测增量；PATH多头半量调仓净年化均值改善1.48个百分点，但复合年收益仍为-2.03%。原报告保留不变。

```bash
git clone https://github.com/yks23/Quant-Project.git
cd Quant-Project
```

本仓库包含Python计算程序、单元测试、聚合结果和报告，不需要启动服务器。通过公开HTTPS地址直接clone，无需配置GitHub SSH密钥。原始数据需从公开上游单独下载。

## 两个研究问题

- **下跌路径：** 累计跌幅相近时，一天暴跌与连续阴跌是否具有不同的后续反转？
- **市场广度：** 个股下跌信号在普跌与局部下跌状态下，预测能力是否不同？

## 评估内容

- 全部可观察合格沪深A股的Q1-Q5；次日开盘、五日调仓的现金账户模拟。
- CAPM、FF3、Carhart4模型结构的Alpha比较，**本地FF式代理，非官方因子序列**。
- 2015-2020开发、2021验证、2022-2024固定留出；两个主检验Holm校正。
- 普通反转基线、相近跌幅内路径排序、规模/价格/非流动性独立双重排序、增量回归。
- 单边0/10/30bp成本、替代proxy、分时期及RF假设敏感性。

方案冻结提交为`a5f6d25`，在读取策略结果前提交。固定方向不随结果调整；本研究允许零结果。
“全市场”仅指数据内全部符合条件的历史记录，退市完整性与财务point-in-time未经官方主表认证。
多空组合是假设可借券的研究指标，不是已验证可交易的新Alpha。

## 留出期结论

2022-2024固定方向、单边10bp：PATH多空年化均值为-2.91%，BREADTH为-24.51%；两个主假设均未通过正Alpha检验。
PATH零成本年化均值为12.45%，显示高换手成本的重要性。报告同时保留不支持假设的结果，不事后翻转方向。
本地四因子年化Alpha分别为+0.67%与-27.92%，Holm校正p分别为0.921与0.002；后者是负Alpha，不是支持原假设。

完整口径、滞价持仓边界和增量检验见PDF；15项单元测试及结果验证记录在[verification.json](results/verification.json)。

## 文件与数据

运行收据和实际数据摘要见[run_manifest.json](results/run_manifest.json)，数据来源见[data/README.md](data/README.md)。
公开仓库不镜像原始行情、个股分数和账户明细；本地`data/processed/`保留这些中间数据供复核。
行情包的公开下载不等于获得再分发授权，软件许可证不替代数据许可。
