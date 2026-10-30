# 重现本次研究

研究不需要数据库账号、服务器或API key。原始数据只在本地；GitHub保存代码、说明、聚合结果、图和报告。

## 1. 安装

用Python 3.12创建独立虚拟环境，预留15GB磁盘。全量运行建议16GB或更多内存。
以下命令在项目根目录逐条执行；Windows将激活命令换成`.venv\Scripts\Activate.ps1`。

```bash
git clone https://github.com/yks23/Quant-Project.git
cd Quant-Project
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tested.txt
```

`requirements-tested.txt`记录本次实测版本；`requirements.txt`允许兼容版本，重新运行应保存自己的实际版本。

## 2. 下载同一份公开行情

在仓库根目录执行。网络断开时可重新执行，`-C -`从已有文件继续下载。

```bash
mkdir -p data
curl -L --fail --retry 3 -C - -o data/AStockData.tar.gz https://github.com/fire-institute/fire/releases/download/marketdata/AStockData.tar.gz
```

浏览器也可以打开[固定发布页](https://github.com/fire-institute/fire/releases/tag/marketdata)，点击`AStockData.tar.gz`，放到本项目`data/`。
文件应为1,396,296,954字节。`results/run_manifest.json`记录本次实际文件SHA-256；运行前可用下列命令严格核对：

```bash
python -c "import json; from src.data import sha256; expected=json.load(open('results/run_manifest.json'))['data_archive_sha256']; actual=sha256('data/AStockData.tar.gz'); assert actual==expected, (actual, expected); print('SHA-256 verified')"
```

上游release可修改；摘要不一致时不要直接把清单改成新摘要，先核查数据版本，保留旧实验结果。

## 3. 执行测试和全量计算

```bash
python -m unittest discover -s tests -v
python run_study.py --extract
python postprocess.py
python build_report.py
```

第一次运行用`--extract`选择性解压所需的十个Feather字段，只接受白名单普通文件，不执行归档内容。
再次运行时可省略`--extract`。所有文件由pandas直接读取；不调用`firefin.fetch_data`，因为核查上游实现发现无效字段存在随机数据回退，不能用于研究。

`run_study.py`依次进行字段校验、因子计算、账户模拟、控制排序、回归和风险模型构建。每个账户会输出进度。
`postprocess.py`汇总留出期辅助检验、RF敏感性和结果完整性；`build_report.py`从这些CSV生成图、中文PDF及Markdown。
命令会重建本地聚合结果，想比较新方案时先保存原结果或新建分支，不覆盖固定方案冒充同一实验。

中文PDF需要支持中文的TrueType字体。macOS默认读取Arial Unicode；其他系统可设置字体文件路径：

```bash
export CHINESE_FONT=/absolute/path/to/chinese-font.ttf
python build_report.py
```

完成后打开`reports/factor_study_report.pdf`；Markdown版在相同目录。报告不需要启动网页。

## 4. 结果文件

- `results/performance.csv`：所有主/辅助proxy、成本及分组的绩效。
- `results/daily_portfolio_returns.csv`：可复画曲线的日收益，无原始个股价格。
- `results/alpha_local_proxy.csv`：CAPM、FF3、Carhart4三模型结构的月频Alpha与检验。
- `results/double_sort_by_period.csv`、`double_sort_spreads_by_period.csv`：独立双重排序。
- `results/incremental_by_period.csv`、`breadth_by_period.csv`：控制后的路径与广度检验。
- `results/data_audit.json`、`data_fields.csv`、`coverage_daily.csv`：数据覆盖及质量。
- `results/integrity_checks.json`、`run_manifest.json`：检查与复现收据。
- `data/processed/`：本地形成日个股分数与账户路径，默认不上传。

## 5. 资产定价口径

本次程序按`PROXY_MODELS.md`构造本地FF式代理，不能把文件名中的FF3理解为已取得官方标准序列。
RF主假设为年化1.5%，0%/3%敏感性不改变选股。外部北大因子入口在[这里](https://www.gsm.pku.edu.cn/finvc/info/1027/1147.htm)，下载可能需要人工验证码。
使用外部序列时必须先核实RF、单位、模型列和月份，单独输出标准序列表；不得插值2024、改用美股因子或把验证码HTML当作Excel。
