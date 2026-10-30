"""Render the computed evidence to a Chinese PDF and matching Markdown report."""

import os
from pathlib import Path
import json
from html import escape
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'.mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                               Spacer, PageBreak, Table, TableStyle, Image)
from reportlab.platypus.tableofcontents import TableOfContents

R=ROOT/'results'
P=ROOT/'reports'
G=P/'figures'
COLORS=['#415666','#2a9d8f','#c5a33c','#8a5c9b','#be4b45']


def pct(x):
    return f'{100*x:.2f}%' if pd.notna(x) else 'NA'


def num(x):
    return f'{x:.2f}' if pd.notna(x) else 'NA'


def prob(x):
    return '<0.001' if x<.001 else f'{x:.3f}' if pd.notna(x) else 'NA'


def read(name):
    return pd.read_csv(R/f'{name}.csv')


def plots():
    G.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.grid':True,'grid.alpha':.22,'savefig.dpi':170})
    returns=pd.read_csv(R/'daily_portfolio_returns.csv',index_col=0,parse_dates=True)
    cov=pd.read_csv(R/'coverage_daily.csv',index_col=0,parse_dates=True)
    sig=pd.read_csv(R/'signal_audit.csv',index_col=0,parse_dates=True)
    def finish(fig,name):
        fig.tight_layout(pad=1.1)
        fig.savefig(G/f'{name}.png',facecolor='white')
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.2,2.8))
    ax.plot(cov.index,cov.trading_records,label='Observable trading records',color=COLORS[0])
    ax.plot(sig.index,sig.eligible_n,label='Eligible (60 observations + 5-day signal)',color=COLORS[1])
    ax.set(ylabel='Number of stocks',title='Data coverage, not an official listing census')
    ax.legend(fontsize=8)
    finish(fig,'coverage')
    for name in ['PATH','BREADTH']:
        fig,ax=plt.subplots(figsize=(7.2,3.0))
        for q,col in zip(range(1,6),COLORS):
            ax.plot(returns.index,(1+returns[f'{name}_Q{q}_c10']).cumprod(),label=f'Q{q}',color=col,lw=1.15)
        ax.plot(returns.index,(1+returns.EW_c10).cumprod(),label='EW universe',color='black',ls='--',lw=1)
        ax.axvline(pd.Timestamp('2022-01-01'),color='#777777',ls=':',lw=1)
        ax.set(title=f'{name}: long-only quintiles, 10 bp per leg',ylabel='NAV (initial = 1)')
        ax.legend(ncol=6,fontsize=8)
        finish(fig,f'{name.lower()}_quintiles')
    fig,axes=plt.subplots(2,1,figsize=(7.2,4.8),sharex=True)
    for name,col in [('PATH_LS_c10',COLORS[4]),('BREADTH_LS_c10',COLORS[1]),
                     ('REV_LS_c10',COLORS[0]),('EW_c10','#111111')]:
        nav=(1+returns[name]).cumprod()
        label=name.replace('_LS_c10',' L/S').replace('EW_c10','EW market')
        axes[0].plot(nav.index,nav,label=label,color=col,lw=1.1)
        axes[1].plot(nav.index,nav/nav.cummax().clip(lower=1)-1,color=col,lw=1)
    axes[0].set(ylabel='Synthetic NAV',title='Long-short spreads and long-only EW benchmark')
    axes[0].legend(ncol=2,fontsize=8)
    axes[1].set(ylabel='Drawdown')
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    finish(fig,'spread_drawdown')
    d=read('double_sort_by_period')
    fig,axes=plt.subplots(1,3,figsize=(7.2,2.8))
    for ax,(factor,control,title) in zip(axes,[('LOSER_PATH','past_return','Losers: R5 x concentration'),
                                             ('PATH','size','PATH: size x score'),
                                             ('BREADTH','size','BREADTH: size x score')]):
        s=d[(d.factor==factor)&(d.control==control)&(d.period=='holdout')]
        mat=s.pivot(index='control_group',columns='quintile',values='mean')*100
        lim=max(float(np.nanmax(np.abs(mat.to_numpy()))),.01)
        ax.imshow(mat,cmap='RdYlGn',vmin=-lim,vmax=lim,aspect='auto')
        for i in range(3):
            for j in range(5):
                ax.text(j,i,f'{mat.iloc[i,j]:.2f}',ha='center',va='center',fontsize=7)
        ax.set(xticks=range(5),xticklabels=range(1,6),yticks=range(3),yticklabels=range(1,4),
               xlabel='Factor quintile',ylabel='Control tercile',title=title)
        ax.grid(False)
        ax.title.set_fontsize(8)
    fig.suptitle('2022-2024: mean next-open-to-next-open 5-day return (%)',fontsize=10)
    finish(fig,'double_sorts')
    fig,axes=plt.subplots(1,2,figsize=(7.2,2.7))
    perf=read('performance')
    for ax,period in zip(axes,['full','holdout']):
        for name,col in [('PATH',COLORS[4]),('BREADTH',COLORS[1])]:
            p=perf.set_index(['period','portfolio'])
            y=[p.loc[(period,f'{name}_LS_c{cost}'),'annual_mean'] for cost in [0,10,30]]
            ax.plot([0,10,30],y,'o-',label=name,color=col)
        ax.set(title=period,xlabel='One-way cost (bp)',ylabel='Annual mean L/S return')
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xticks([0,10,30])
        ax.legend(fontsize=8)
    finish(fig,'costs')
    return returns


class ReportDoc(BaseDocTemplate):
    def __init__(self,path,**kwargs):
        super().__init__(str(path),pagesize=A4,leftMargin=1.8*cm,rightMargin=1.8*cm,
                         topMargin=1.7*cm,bottomMargin=1.6*cm,**kwargs)
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='main',
                    leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='body',frames=frame,onPage=self.page_header))

    def page_header(self,canvas,doc):
        canvas.setTitle('A股下跌路径与市场广度：两个因子的计算和检验')
        canvas.setAuthor('Quant-Project')
        canvas.setFont('CN',8)
        canvas.setFillColor(colors.HexColor('#657079'))
        if doc.page>1:
            canvas.drawString(self.leftMargin,A4[1]-1.0*cm,'QUANT-PROJECT  /  A股短期反转研究')
        canvas.drawString(self.leftMargin,.85*cm,'公开数据研究  |  2026-10-31  |  非投资建议')
        canvas.drawRightString(A4[0]-self.rightMargin,.85*cm,str(doc.page))

    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and getattr(flowable,'toc_key',None):
            key=flowable.toc_key
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,0,False)
            self.notify('TOCEntry',(0,flowable.getPlainText(),self.page,key))


class Report:
    def __init__(self):
        candidates=[os.environ.get('CHINESE_FONT',''),'/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc']
        font=next((x for x in candidates if x and Path(x).exists()),None)
        if not font:
            raise ValueError('Set CHINESE_FONT to a Chinese-capable TrueType font file.')
        pdfmetrics.registerFont(TTFont('CN',font))
        self.styles={
            'body':ParagraphStyle('Body',fontName='CN',fontSize=10.1,leading=15.4,spaceAfter=8,wordWrap='CJK'),
            'small':ParagraphStyle('Small',fontName='CN',fontSize=8.3,leading=11.4,spaceAfter=6,wordWrap='CJK',textColor=colors.HexColor('#43505b')),
            'h1':ParagraphStyle('H1',fontName='CN',fontSize=17,leading=23,spaceAfter=14,wordWrap='CJK'),
            'h2':ParagraphStyle('H2',fontName='CN',fontSize=11.6,leading=17,spaceBefore=7,spaceAfter=7,wordWrap='CJK',textColor=colors.HexColor('#176b60')),
            'title':ParagraphStyle('Title',fontName='CN',fontSize=24,leading=34,spaceAfter=18,wordWrap='CJK'),
            'table':ParagraphStyle('Cell',fontName='CN',fontSize=8,leading=11.5,wordWrap='CJK'),
        }
        self.story=[]
        self.markdown=[]
        self.count=0

    def p(self,text,style='body'):
        self.story.append(Paragraph(escape(text).replace('\n','<br/>'),self.styles[style]))
        self.markdown.append(text+'\n')

    def section(self,title):
        self.story.append(PageBreak())
        self.count+=1
        p=Paragraph(escape(title),self.styles['h1'])
        p.toc_key=f'section{self.count}'
        self.story.append(p)
        self.markdown.append(f'## {title}\n')

    def h2(self,text):
        self.p(text,'h2')

    def table(self,df,widths=None):
        frame=df.fillna('NA').astype(str)
        data=[[Paragraph(escape(str(x)),self.styles['table']) for x in row]
              for row in [frame.columns.tolist()]+frame.values.tolist()]
        widths=widths or [17.4*cm/len(frame.columns)]*len(frame.columns)
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6eeec')),
                               ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#5f7a71')),
                               ('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#9aa6a1')),
                               ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f7')]),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),
                               ('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),
                               ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        self.story.extend([t,Spacer(1,9)])
        self.markdown.append(frame.to_markdown(index=False)+'\n')

    def figure(self,name,caption,width=17.2*cm):
        from PIL import Image as PILImage
        path=G/f'{name}.png'
        with PILImage.open(path) as im:
            height=width*im.height/im.width
        self.story.append(Image(str(path),width=width,height=height))
        self.p(caption,'small')
        self.markdown.append(f'![{caption}](figures/{name}.png)\n')

    def finish(self):
        ReportDoc(P/'factor_study_report.pdf').multiBuild(self.story)
        (P/'factor_study_report.md').write_text('\n'.join(self.markdown),encoding='utf-8')


def main():
    returns=plots()
    perf=read('performance')
    alphas=read('alpha_local_proxy')
    data=json.loads((R/'data_audit.json').read_text())
    check=json.loads((R/'integrity_checks.json').read_text())
    manifest=json.loads((R/'run_manifest.json').read_text())
    inc=read('incremental_by_period')
    bstate=read('breadth_by_period')
    ds=read('double_sort_spreads_by_period')
    diag=read('execution_diagnostics')
    fields=read('data_fields')
    def stat(name,period='full'):
        return perf[(perf.portfolio==name)&(perf.period==period)].iloc[0]
    def alpha(name,period='holdout',model='Carhart4'):
        return alphas[(alphas.portfolio==name)&(alphas.period==period)&(alphas.model==model)].iloc[0]
    def perf_table(names,period):
        rows=[]
        for name in names:
            p=stat(name,period)
            rows.append([name.replace('_c10',''),pct(p.annual_mean),pct(p.cagr),num(p.sharpe),pct(p.max_drawdown)])
        return pd.DataFrame(rows,columns=['组合','年化均值','年化复利','Sharpe','最大回撤'])
    verdicts={}
    for name in ['PATH','BREADTH']:
        a=alpha(f'{name}_LS_c10')
        passed=a.alpha_annual>0 and a.p_holm_two_primary<.05
        verdicts[name]='通过正Alpha主检验' if passed else '未通过正Alpha主检验'
    doc=Report()
    doc.story.append(Spacer(1,24))
    doc.p('A股下跌路径与市场广度','title')
    doc.p('两个因子的计算、交易模拟与资产定价检验','h1')
    doc.p('研究区间：2015-04-01至2024-12-31\n固定留出区间：2022-2024\n数据：F.I.R.E.公开A股日频面板\n主成本：单边10bp；全市场有效样本五分组')
    doc.h2('核心结论')
    for name,label in [('PATH','路径集中度'),('BREADTH','市场广度状态')]:
        p=stat(f'{name}_LS_c10','holdout')
        a=alpha(f'{name}_LS_c10')
        doc.p(f'{label}（{name}）：留出期多空年化均值{pct(p.annual_mean)}，'
              f'四因子年化Alpha {pct(a.alpha_annual)}，HAC t={num(a.t)}，'
              f'两主检验Holm校正p={prob(a.p_holm_two_primary)}；{verdicts[name]}。')
    doc.p('以上Alpha使用本研究按事前规则重建的本地FF式风险因子代理，'
          '已运行CAPM、FF3和Carhart四因子模型结构；结果不等同于使用官方标准因子序列。'
          '固定年化1.5%的RF属于假设，报告同时给出0%和3%的敏感性。')
    doc.p('报告保留所有预设方向、窗口与成本结果，包括不支持假设的证据。'
          '多空收益是100%多头与100%空头的研究组合，未计融券费及保证金，不构成可执行收益承诺。','small')
    doc.p(f'复现版本：{manifest["code_commit"][:12]}\n方案冻结提交：a5f6d25；实现澄清见PROTOCOL.md。','small')

    doc.section('目录与课程要求对应')
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle('TOC',fontName='CN',fontSize=9.7,leading=19,spaceBefore=2,wordWrap='CJK')]
    doc.story.append(toc)
    doc.story.append(Spacer(1,12))
    doc.p('阅读顺序：先看核心结论，再看样本、执行口径和主检验；原始假设是否成立主要由双重排序与增量回归回答。','small')
    doc.markdown.append('目录：数据与样本；固定方案；因子定义；PATH；BREADTH；多空；模型；原问题；增量；稳健性；质量；复现。\n')

    doc.section('1. 数据组成与样本边界')
    doc.p(f'本次读取真实Feather文件，原始字段覆盖{fields.iloc[0]["start"]}至{fields.iloc[0]["end"]}，'
          f'{data["n_dates"]}个日期、{data["n_securities"]}个沪深A股代码。'
          f'研究收益序列包含{check["trade_days"]}个交易日，首末有效股票数为'
          f'{check["eligible_at_first_date"]}与{check["eligible_at_last_date"]}。')
    doc.table(pd.DataFrame([
        ['量价','open、close、volume、money','调整开收盘用于收益与成交；成交额用于Amihud'],
        ['原始价格','close_dr','原价分组控制，不用于与复权价混算收益'],
        ['规模与价值','market_cap_ashare、circulating_market_cap_ashare、pb_ratio','规模控制、加权广度和本地风险模型'],
        ['校验字段','return_adj、turnover_ratio','收益单位核对；换手字段留作数据审计'],
    ],columns=['类别','读取字段','用途']),[2.1*cm,7.7*cm,7.6*cm])
    doc.figure('coverage','图1：真实可观察记录与策略有效股票数。它不是完整历史上市证券普查。')
    doc.p(f'全零或完全缺失代码：{data["all_zero_or_missing_securities"]}；'
          f'最后正价早于数据末日的代码：{data["histories_ending_before_last_date"]}。'
          '缺少权威历史上市/退市名单，不能据此证明无幸存者偏差。'
          '本文“全市场五分组”指公开数据内满足事前条件的全部沪深A股，不是官方全A股总体。','small')

    doc.section('2. 事前固定方案与成交时间线')
    doc.table(pd.DataFrame([
        ['窗口','过去5个交易日；每5个交易日形成一次组合'],
        ['准入','沪深A股代码；累计60个正价观察；有效5日收益；形成日正价且有成交量'],
        ['形成与入场','t收盘后计算信号；t+1开盘调仓；按当天收盘估值'],
        ['分组','所有合格股票同日独立排序Q1至Q5；平均秩处理同分，不按代码拆分'],
        ['账户','各组等权目标；先卖后买；拒绝买入留现金、拒绝卖出继续持有'],
        ['成交代理','相对上日调整收盘，开盘涨幅>=9.5%不买、跌幅<=-9.5%不卖'],
        ['交易成本','主情景单边10bp；0bp及30bp只作敏感性，含两腿成本'],
        ['基准','同一合格股票池、同一调仓规则与成本的等权多头EW'],
        ['样本划分','2015-2020开发、2021验证、2022-2024固定留出；不挑参数'],
        ['主假设','两个留出期Q5-Q1的正四因子Alpha，双侧p做Holm两重校正'],
    ],columns=['项目','固定口径']),[2.6*cm,14.8*cm])
    doc.h2('不使用次日结果决定今天买谁')
    doc.p('股票池和分数只读取t及以前的值。未来开盘缺失的股票不会从t的入选名单中事后剔除。'
          '不能成交时账户保留现金或旧持仓；缺失收盘时按最后正价估值，并记录滞价资金占比。'
          '调仓间隔五个交易日，买入日没有再次卖出新买份额。')
    doc.p('正价但全天零成交的记录只用于判定订单执行失败，不回改选股；未成交买入不重新分配权重。'
          '全天正成交量不能保证开盘成交。数据验收后发现的停牌延续报价及对应修正记录在IMPLEMENTATION_LOG.md。','small')
    doc.p('该成交代理无法精确区分ST、主板、创业板和科创板的不同限制，亦没有盘口排队、手数与资金容量模型。'
          '调整价格构成分数股研究账户。9.5%规则只是保守假设，并非历史法规复刻。')
    doc.p('冻结方案在读取策略结果前提交，但所有年份均属于历史回测；“留出”表示本次没有利用该段收益调整规则，不等于真实未来投资验证。','small')

    doc.section('3. 因子定义与行为金融假设')
    doc.h2('PATH：相同五日跌幅，损失集中程度是否重要？')
    doc.p('令r为调整收盘价的日对数收益，R5为最近五日r之和。loss=max(-r,0)，gain=max(r,0)。'
          '当R5<0时，PATH=max(loss)/sum(loss)；当R5>0时，PATH=-max(gain)/sum(gain)；R5=0时取0。')
    doc.p('五天等量下跌得到0.2；全部负收益集中一天得到1。上涨股票使用对称负号，使所有合格股票都能五分组。'
          '这个扩展混合了反转方向与路径特征；原始问题另在下跌股票内部控制累计跌幅检验。替代proxy将最大份额换为份额平方和HHI。')
    doc.p('行为假设：集中的负面冲击更容易吸引注意、激活损失厌恶或触发集中卖压，若价格短暂偏离估值，可能随后反弹。'
          '相反，渐进下跌也可能反映信息扩散和慢速价格调整。集中下跌可能是基本面永久恶化，因而方向不必然成立。')
    doc.h2('BREADTH：市场共同下跌是否改变反转状态？')
    doc.p('每日b为有效交易股票中收益为负的比例，平盘真实交易记录保留在分母；B为最近五日b的平均。'
          'BREADTH=(2B-1)×(-R5)。B>0.5时按反转排序；B<0.5时按动量排序；B=0.5时同分。')
    doc.p('B对同日个股相同，正的公共倍数不会改变横截面排序。因此本定义明确使用以0.5为中心的状态切换，'
          '不把公共市场指标伪装成独立个股信息。普通REV=-R5是必需基线；替代proxy用上一日流通市值加权的下跌比例。')
    doc.p('行为假设：普跌可能与共同悲观、注意力冲击或流动性收缩相关；局部下跌可能更贴近个股信息。'
          '但普跌也可能反映系统性风险，收益差不直接识别非理性。增量检验控制过去市场收益与波动。')
    doc.p('最接近文献之一为Da、Gurun和Warachka（2014）的信息连续性与动量研究。'
          '本作业定位于短窗A股扩展和增量信息检验，不主张首次发现“路径效应”或“状态效应”。参考文献见末节。','small')

    for section,name,cn in [(4,'PATH','路径因子'),(5,'BREADTH','市场广度状态因子')]:
        doc.section(f'{section}. {cn}：全市场Q1至Q5')
        doc.figure(f'{name.lower()}_quintiles',f'图：{name}五组净值，单边10bp；虚线为等权样本基准，竖线为留出期起点。')
        rows=[]
        for q in range(1,6):
            key=f'{name}_Q{q}_c10'
            p=stat(key)
            a=alpha(key,'full')
            rows.append([f'Q{q}',pct(p.annual_mean),pct(p.annual_excess),pct(p.annual_vs_market),pct(a.alpha_annual),num(a.t)])
        doc.table(pd.DataFrame(rows,columns=['分组','年化收益','超RF','超EW','四因子α','α的t']))
        doc.p('表：全样本年化算术均值；超RF使用1.5%年化代理，超EW为相同日期收益差。'
              '本地FF式四因子Alpha只覆盖风险因子共同可用月份，与全样本年化收益不完全同区间。','small')
        rows=[]
        for q in range(1,6):
            key=f'{name}_Q{q}_c10'
            rows.append([f'Q{q}']+[pct(alpha(key,'full',m).alpha_annual) for m in ['CAPM','FF3','Carhart4']]
                         +[pct(alpha(key,'holdout').alpha_annual)])
        doc.table(pd.DataFrame(rows,columns=['分组','CAPM α','FF3 α','Carhart4 α','留出Carhart4 α']))
        doc.p('本地FF式代理模型。三模型使用相同月份，防止把样本变化当作Alpha变化。全部t、p、载荷与样本数见results/alpha_local_proxy.csv。','small')
        if name=='BREADTH':
            doc.p(f'全收益区间内，五日平均下跌比例高于0.5的日期占{pct(check["breadth_above_half_fraction"])}。'
                  '只有状态变号时排序方向才改变；因子大小本身不改变组内等权仓位。','small')

    doc.section('6. 多空收益、基准与最大回撤')
    doc.figure('spread_drawdown','图：100%多头、100%空头的日收益差复利；EW是100%多头基准，敞口不同，不按净值高低直接判断优劣。')
    doc.table(perf_table(['PATH_LS_c10','BREADTH_LS_c10','REV_LS_c10','EW_c10'],'full'))
    doc.p('年化均值=日均收益×252；年化复利按252个交易日折算；Sharpe对多头扣RF、对零净敞口多空直接使用收益。'
          '最大回撤以初始净值1为历史高点候选。费用按实际成交金额收取；空头腿不能因“减去净多头收益”而错误获得费用返还。','small')
    doc.p('多空曲线是每日两腿收益差的复利指数，隐含持续维持两腿名义比例；它不是具备融券借贷、保证金追缴和借券召回处理的真实融资账户。','small')

    doc.section('7. CAPM、FF3和四因子Alpha比较')
    doc.p('月度回归：多头收益减RF = α + β×风险因子 + ε；多空收益不重复扣RF。'
          'CAPM含MKT，FF3再含SMB与HML，Carhart4再含MOM。因子与策略均由日收益复利聚合到月度；'
          'HAC采用3阶、有限样本修正，年化α=12×月截距。')
    rows=[]
    for period,title in [('full','共同全样本'),('holdout','2022-2024')]:
        for name in ['PATH','BREADTH']:
            for model in ['CAPM','FF3','Carhart4']:
                a=alpha(f'{name}_LS_c10',period,model)
                rows.append([title,name,model,pct(a.alpha_annual),num(a.t),prob(a.p),int(a.n_months)])
    doc.table(pd.DataFrame(rows,columns=['区间','因子','模型','年化α','t','p','月份']))
    a0=alpha('PATH_LS_c10','full')
    doc.p(f'本地FF式代理的共同完整区间为{a0.start}至{a0.end}。'
          'MKT为滞后一日市值加权股票收益减RF；SMB/HML用6月规模和上年12月正PB倒数形成2×3组合，7月生效。'
          'MOM按252至21个交易日前的累计收益与规模形成2×3组合，每月更新。','small')
    doc.p('价值模型缺少历史账面权益公告版本认证，采用滞后PB快照，不能证明严格point-in-time。'
          '没有2014年12月数据，因此不补造2015年价值因子；风险因子不扣策略交易费。'
          '本地因子定义与公开标准序列并不完全相同，本次Alpha结论限定在上述构建口径内。','small')
    doc.table(pd.DataFrame([[n,prob(alpha(f'{n}_LS_c10').p_holm_two_primary),verdicts[n]] for n in ['PATH','BREADTH']],
                           columns=['留出主假设','Holm校正p','正Alpha结论']))

    doc.section('8. 回到原问题：相近跌幅内比较路径')
    doc.p('仅保留过去五日R5<0的形成日股票。独立形成R5三组和负收益集中度五组，'
          '在每个跌幅档内比较Q5-Q1。事件收益为t+1开盘至t+6开盘的五日收益，形成日间隔五个交易日。')
    doc.figure('double_sorts','图：留出期独立双重排序均值，单位为五日收益百分比。左图回答原路径问题，另两图控制规模。')
    rows=[]
    for period,title in [('full','全样本'),('holdout','留出')]:
        for _,r in ds[(ds.factor=='LOSER_PATH')&(ds.period==period)].iterrows():
            rows.append([title,int(r.control_group),pct(r['mean']),num(r.t),prob(r.p),int(r.n)])
    doc.table(pd.DataFrame(rows,columns=['区间','R5档','集中-分散','HAC t','p','形成期']))
    doc.p('R5档1的累计跌幅更深，档3较浅；三分组仍有组内跌幅差，故另做连续控制回归。'
          '这里的事件收益不扣成本、不处理成交拒绝，仅用于检验信息关系；投资表现以现金账户回测为准。'
          '缺失未来开盘只从事件统计中缺测，不回改当时选股名单；formed_n和observed_n可在明细核查。','small')

    doc.section('9. 增量信息与经济解释的检验')
    doc.h2('PATH：控制普通反转、最后一日冲击与个股特征')
    rows=[]
    for period,title in [('full','全样本'),('holdout','留出')]:
        sub=inc[inc.period==period].set_index('variable')
        for name in ['PATH','R5','R1','vol20','size','price','illiquidity']:
            r=sub.loc[name]
            rows.append([title,name,pct(r['mean']),num(r.t),prob(r.p)])
    doc.table(pd.DataFrame(rows,columns=['区间','解释变量','五日系数','HAC t','p']))
    doc.p('每个形成日把解释变量按1%/99%缩尾并标准化，再对未来五日收益回归；系数跨期均值采用HAC(2)。'
          '系数表示解释变量增加一个当日标准差的收益关系。回归仅使用同时具备控制变量与标签的记录，不代表所有组合持仓。','small')
    doc.h2('BREADTH：控制历史市场收益和波动')
    rows=[]
    for period,title in [('full','全样本'),('holdout','留出')]:
        r=bstate[(bstate.period==period)&(bstate.variable=='breadth')].iloc[0]
        rows.append([title,pct(r['mean']*.1),num(r.t),prob(r.p),int(r.n)])
    doc.table(pd.DataFrame(rows,columns=['区间','广度+10pp的收益差','HAC t','p','形成期']))
    doc.p('被解释变量为普通反转REV的未来五日Q5-Q1；解释变量为形成日B、过去五日市场平均收益、20日市场波动。'
          '不能在同日横截面同时放入BREADTH和R5并期待独立识别，因为二者当日成比例。'
          '该条件相关回归与行为金融解释相容与否，均不能单独证明恐慌、注意力或因果关系。','small')

    doc.section('10. 规模、价格与流动性独立排序')
    doc.p('各控制变量在当日有效股票中独立三分组，主因子独立五分组，取交集后计算未来五日收益。'
          '规模为总A股市值，价格为原始收盘价，Amihud代理为过去20日|日对数收益|/成交额的均值。'
          '下表固定展示2022-2024，不从不同控制档位中选最优结果。')
    rows=[]
    names={'size':'规模','price':'价格','illiquidity':'非流动性'}
    for factor in ['PATH','BREADTH']:
        for control in names:
            sub=ds[(ds.factor==factor)&(ds.control==control)&(ds.period=='holdout')].sort_values('control_group')
            rows.append([factor,names[control]]+[f'{pct(r["mean"])} ({num(r.t)})' for _,r in sub.iterrows()])
    doc.table(pd.DataFrame(rows,columns=['因子','控制','低档差额(t)','中档差额(t)','高档差额(t)']))
    doc.p('单元格为五日Q5-Q1均值与HAC(2)的t值。低到高指控制变量，而不是因子得分。'
          '每个5×3单元的均值、p、形成股票数与可观测标签数保存在double_sort_by_period.csv；'
          '表中高低差并不能替代完整收益曲线或执行成本检验。')
    doc.h2('如何读取这些结果')
    doc.p('若收益仅存在于小市值、低价或高非流动性档，应把结论限定到该类股票，并考虑风险补偿与交易摩擦。'
          '若各档方向一致，也仅提供该控制维度下的稳健性证据。行业、ST与公告事件没有历史认证数据，'
          '因此不能声称已排除所有混杂解释。')
    doc.h2('机制解释的可证伪边界')
    doc.p('路径集中度并不等于“恐慌”：它也捕捉涨跌停、公告和基本面跳变。'
          '市场广度并不等于“情绪”：它也反映宏观共同风险。'
          '本次通过收益、控制排序与条件回归检验预测关联；要识别机制，还需新闻、公告时点或外生资金冲击证据。')

    doc.section('11. 子时期、成本与替代proxy')
    rows=[]
    for period,title in [('development','2015-2020'),('validation','2021'),('holdout','2022-2024')]:
        for name in ['PATH','BREADTH','REV']:
            p=stat(f'{name}_LS_c10',period)
            rows.append([title,name,pct(p.annual_mean),num(p.sharpe),pct(p.max_drawdown)])
    doc.table(pd.DataFrame(rows,columns=['区间','因子','年化均值','Sharpe','最大回撤']))
    doc.figure('costs','图：固定0、10、30bp单边成本，不按结果选择成本档位。')
    rows=[]
    for name in ['PATH','PATH_HHI','BREADTH','BREADTH_VW','REV']:
        p=stat(f'{name}_LS_c10','holdout')
        a=alpha(f'{name}_LS_c10')
        rows.append([name,pct(p.annual_mean),pct(a.alpha_annual),num(a.t)])
    doc.table(pd.DataFrame(rows,columns=['固定proxy','留出年化均值','本地四因子α','α的t']))
    doc.p('替代proxy是辅助证据，未纳入两个主假设的Holm检验族，不据此选择获胜版本。年度明细见annual_performance.csv。','small')

    doc.section('12. 数据审计、RF敏感性与实现验证')
    doc.p(f'return_adj与调整价格收益核对后单位为{data["return_adj_inferred_unit"]}；'
          f'绝对差中位数{data["return_price_median_abs_difference"]:.3g}，99%分位{data["return_price_p99_abs_difference"]:.3g}。'
          f'超过30%绝对日收益的观察有{data["abs_daily_return_over_30pct_count"]}条，未因收益好坏删除。')
    rows=[]
    for factor in ['PATH','BREADTH']:
        for q in [1,5]:
            r=diag[diag.portfolio==f'{factor}_Q{q}_c10'].iloc[0]
            rows.append([f'{factor} Q{q}',num(r.holdings),pct(r.turnover*252),pct(r.cash_weight),pct(r.max_stale_weight)])
    doc.table(pd.DataFrame(rows,columns=['主组合','平均持股数','年化双边换手','平均现金','最大滞价资金']))
    doc.p('换手为买入加卖出成交额/净值，属于双边口径；成本按该成交额计。'
          '延续最后正价可避免按未来缺失先删除股票，但无法恢复未知退市清算损失；较小滞价比例也不证明退市历史完整。','small')
    sens=read('rf_sensitivity')
    rows=[]
    for name in ['PATH_LS_c10','BREADTH_LS_c10','PATH_Q5_c10','BREADTH_Q5_c10']:
        subset=sens[(sens.portfolio==name)&(sens.model=='Carhart4')].sort_values('rf_assumption')
        rows.append([name.replace('_c10','')]+[pct(x) for x in subset.alpha_annual])
    doc.table(pd.DataFrame(rows,columns=['留出组合','RF=0% α','RF=1.5% α','RF=3% α']))
    doc.h2('自动验证覆盖')
    doc.p('单元测试验证：未来价格改动不影响过去信号、集中度0.2和1端点、同分处理、'
          '次日开盘入场不赚取入场前跳空、拒买留现金、拒卖保留持仓、缺价延续估值、费用及现金约束、'
          '空组合、两腿费用、市场广度与反转排序的代数关系、多空Alpha不重复扣RF。')
    doc.p('全量结果检查：所有组合日收益有限、日收益大于-100%、日期无重复、字段对齐、平均现金非负。'
          '机器可读检查结果在integrity_checks.json。测试使用合成小样例验证代码；报告收益全部来自下载的真实行情文件。','small')

    doc.section('13. 结论、局限与展示重点')
    for name,label in [('PATH','路径问题'),('BREADTH','广度问题')]:
        a=alpha(f'{name}_LS_c10')
        doc.h2(f'{label}：{verdicts[name]}')
        doc.p(f'固定方向的留出期本地四因子年化Alpha为{pct(a.alpha_annual)}，'
              f'Holm校正p={prob(a.p_holm_two_primary)}。'
              '该检验回答所定义组合的风险调整收益，不单独回答行为机制是否成立。')
    r=inc[(inc.period=='holdout')&(inc.variable=='PATH')].iloc[0]
    b=bstate[(bstate.period=='holdout')&(bstate.variable=='breadth')].iloc[0]
    doc.p(f'增量层面：留出PATH横截面系数为{pct(r["mean"])}/标准差（t={num(r.t)}，p={prob(r.p)}）；'
          f'广度每提高10个百分点，条件反转差额改变{pct(b["mean"]*.1)}（t={num(b.t)}，p={prob(b.p)}）。'
          '应与下跌样本双重排序合并解读，不能把全市场PATH的收益直接归因于“暴跌比阴跌更反弹”。')
    doc.h2('本次工作支持的表述')
    doc.p('我们固定两个小问题，下载并审计公开日频面板，建立可追溯的因子与成交账户，'
          '完成五分组、三种风险模型结构、普通反转对照、独立控制排序、增量回归和成本/时期敏感性。'
          '结果与方向均完整保留。工作量体现在可复核的测量和反证，而不是因子搜索数量。')
    doc.h2('影响结论的主要边界')
    doc.p('数据是一个公开来源，历史退市及财务point-in-time未经权威主表认证；'
          '股票池是可观察样本。风险模型使用本地FF式代理和假设RF，尚不是官方序列复核。'
          '交易模拟没有精确ST/板块限价、盘口、容量、融券成本。'
          '因此结果应称为课程实证研究，而不是已证实可交易的新Alpha。')
    doc.h2('课堂汇报建议')
    doc.p('按“为什么同跌幅可能不同 → 定义和反例 → 数据及次日成交 → 五组及普通反转基线 → '
          '原问题增量检验 → 风险调整和成本 → 能说什么、不能说什么”展开。'
          '先解释广度的公共变量陷阱，再展示状态调节，能直接说明研究设计的必要性。')

    doc.section('14. 复现、文件索引与参考资料')
    doc.p('在仓库根目录使用Python 3.12和独立虚拟环境，按RUN.md下载固定资产、校验SHA-256，再运行：')
    doc.p('python -m pip install -r requirements.txt\npython -m unittest discover -s tests -v\n'
          'python run_study.py --extract\npython postprocess.py\npython build_report.py','small')
    doc.table(pd.DataFrame([
        ['config/study.json、PROTOCOL.md','窗口、样本划分、主假设与固定方向'],
        ['src/data.py、src/factors.py','真实字段校验与两个因子的计算'],
        ['src/backtest.py、src/risk.py','现金账户与本地风险模型构建'],
        ['results/daily_portfolio_returns.csv','所有固定proxy、成本和分组的日收益'],
        ['results/alpha_local_proxy.csv','三个模型的Alpha、载荷、t/p及月份'],
        ['results/double_sort_by_period.csv','控制排序完整单元格与样本数'],
        ['results/run_manifest.json','真实数据SHA-256、代码提交与环境'],
        ['reports/factor_study_report.pdf','本报告；相邻Markdown可直接搜索'],
    ],columns=['文件','作用']),[8.3*cm,9.1*cm])
    doc.p(f'本次数据包SHA-256：\n{manifest["data_archive_sha256"]}','small')
    refs=[
        ('F.I.R.E.数据与字段说明','https://fire-institute.github.io/fire/data/a-share/'),
        ('固定公开数据资产','https://github.com/fire-institute/fire/releases/tag/marketdata'),
        ('北大中国市场因子与技术文档入口（官方序列复核候选）','https://www.gsm.pku.edu.cn/finvc/info/1027/1147.htm'),
        ('Da, Gurun, Warachka (2014), Frog in the Pan: Continuous Information and Momentum','https://doi.org/10.1093/rfs/hhu003'),
        ('Reversals and the Returns to Liquidity Provision','https://www.nber.org/papers/w30917'),
        ('Positive feedback trading, the T+1 rule, and asymmetric return reversals in China','https://doi.org/10.1016/j.econmod.2026.107783'),
    ]
    for title,url in refs:
        doc.story.append(Paragraph(f'{escape(title)}<br/><link href="{escape(url)}" color="#176b60">{escape(url)}</link>',doc.styles['small']))
        doc.markdown.append(f'- [{title}]({url})\n')
    doc.finish()
    print(f'Written {P}/factor_study_report.pdf and matching Markdown',flush=True)


if __name__=='__main__':
    main()
