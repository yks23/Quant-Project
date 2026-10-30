import unittest
import numpy as np
import pandas as pd

from src.factors import compute, quantiles
from src.backtest import simulate, equal_weight
from src.statistics import hac_mean, model_alpha


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.days = pd.bdate_range("2020-01-01", periods=80)

    def panel(self):
        rng = np.random.default_rng(10)
        close = pd.DataFrame(100*np.exp(np.cumsum(rng.normal(0,.01,(80,10)),axis=0)),index=self.days)
        return close, close*0+100, close*0+10

    def test_no_future_signal_leak(self):
        c,v,m = self.panel()
        first = compute(c,v,m,warmup=10)
        changed = c.copy()
        changed.iloc[50:] *= 3
        second = compute(changed,v,m,warmup=10)
        for key in ["PATH","BREADTH","PATH_HHI","BREADTH_VW"]:
            pd.testing.assert_frame_equal(first[key].iloc[:50],second[key].iloc[:50])

    def test_loss_concentration_endpoints(self):
        returns = np.zeros((80,2))
        returns[-5:,0] = -.01
        returns[-1,1] = -.05
        c = pd.DataFrame(100*np.exp(returns.cumsum(axis=0)),index=self.days)
        out = compute(c,c*0+1,c*0+1,warmup=10)
        self.assertAlmostEqual(out["PATH"].iloc[-1,0],.2,places=6)
        self.assertAlmostEqual(out["PATH"].iloc[-1,1],1,places=6)

    def test_ties_not_split(self):
        q = quantiles(pd.DataFrame([[1,1,1,1,1],[np.nan,2,3,4,5]]))
        self.assertEqual(q.iloc[0].nunique(),1)
        self.assertEqual(q.iloc[1,0],0)

    def test_next_open_execution(self):
        c = pd.DataFrame({"a":[10,20,20,20]},index=self.days[:4])
        w = c*0+1
        bt = simulate(c,c,w,[0],self.days[1],self.days[3],cost_bps=0,limit=10)
        self.assertAlmostEqual(bt["return"].sum(),0)

    def test_blocked_buy_keeps_cash(self):
        c = pd.DataFrame({"a":[10,12,12,12]},index=self.days[:4])
        bt = simulate(c,c,c*0+1,[0],self.days[1],self.days[3],cost_bps=10,limit=.095)
        self.assertEqual(bt.cash_weight.min(),1)
        self.assertEqual(bt.blocked_buy.sum(),1)

    def test_costs_and_cash(self):
        c = pd.DataFrame({"a":[10]*4},index=self.days[:4])
        w = c*0+1
        bt = simulate(c,c,w,[0],self.days[1],self.days[3],cost_bps=10)
        self.assertAlmostEqual(bt.nav.iloc[-1],1/1.001)
        self.assertTrue((bt.cash_weight >= -1e-10).all())

    def test_missing_mark_is_not_liquidation(self):
        c = pd.DataFrame({"a":[10,10,np.nan,11]},index=self.days[:4])
        bt = simulate(c,c,c*0+1,[0],self.days[1],self.days[3],cost_bps=0)
        self.assertAlmostEqual(bt.nav.iloc[-1],1.1)
        self.assertEqual(bt.stale_weight.iloc[1],1)

    def test_blocked_sell_remains_held(self):
        c = pd.DataFrame({"a":[10,10,8,8]},index=self.days[:4])
        w = pd.DataFrame({"a":[1,0,0,0]},index=self.days[:4])
        bt = simulate(c,c,w,[0,1],self.days[1],self.days[3],cost_bps=0)
        self.assertEqual(bt.blocked_sell.sum(),1)
        self.assertEqual(bt.holdings.iloc[-1],1)

    def test_empty_portfolio(self):
        c,_,_ = self.panel()
        w = equal_weight(c<0)
        bt = simulate(c,c,w,[1],self.days[2],self.days[-1])
        self.assertEqual(bt.nav.iloc[-1],1)

    def test_alpha_does_not_subtract_rf_from_spread(self):
        rng=np.random.default_rng(1)
        idx=pd.period_range("2000-01",periods=100,freq="M")
        f=pd.DataFrame(rng.normal(0,.02,(100,4)),index=idx,columns=["MKT","SMB","HML","MOM"])
        f["RF"] = .003
        y=.001+f.MKT*.5+f.SMB*.3
        alpha=model_alpha(y,f,long_short=True)[1]["alpha_month"]
        self.assertAlmostEqual(alpha,.001,places=10)
        self.assertAlmostEqual(model_alpha(y+.003,f)[1]["alpha_month"],.001,places=10)


if __name__ == "__main__":
    unittest.main()
