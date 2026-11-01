import itertools
import unittest

import numpy as np
import pandas as pd

from src.mechanisms import (loss_geometry, leave_one_out_breadth, conditional_groups,
                            standardized, period_mask, past_training_rows)
from src.backtest import simulate


class MechanismTests(unittest.TestCase):
    def test_concentration_is_permutation_invariant(self):
        r = [-.04, -.02, -.01, .01, .005]
        for order in itertools.permutations(r):
            g = loss_geometry(np.array(order)[:, None], np.full((5, 1), .5))
            self.assertAlmostEqual(g["C"][0], 4 / 7)

    def test_recency_distinguishes_order(self):
        r = np.zeros((5, 2))
        r[0, 0] = r[-1, 1] = -.05
        g = loss_geometry(r, np.full((5, 2), .5))
        np.testing.assert_allclose(g["C"], [1, 1])
        np.testing.assert_allclose(g["RECENT"], [0, 1])

    def test_sync_uses_alignment_not_common_level(self):
        r = np.zeros((5, 2))
        r[0, 0] = r[-1, 1] = -.05
        b = np.repeat(np.array([.9, .5, .5, .5, .1])[:, None], 2, axis=1)
        g = loss_geometry(r, b)
        np.testing.assert_allclose(g["SYNC"], [.4, -.4])
        np.testing.assert_allclose(loss_geometry(r, b + .03)["SYNC"], g["SYNC"])

    def test_breadth_removes_self_and_missing(self):
        r = np.array([[-.1, .1, -.2, np.nan], [-.1, .1, -.2, .1]])
        active = np.ones_like(r, dtype=bool)
        active[1, 2] = False
        b = leave_one_out_breadth(r, active)
        np.testing.assert_allclose(b[0], [.5, 1, .5, 2 / 3])
        np.testing.assert_allclose(b[1], [0, .5, 1 / 3, .5])

    def test_zero_loss_is_undefined_not_fabricated(self):
        g = loss_geometry(np.ones((5, 2)), np.full((5, 2), .5))
        self.assertTrue(all(np.isnan(v).all() for v in g.values()))

    def test_geometry_does_not_read_later_rows(self):
        rng = np.random.default_rng(17)
        r = rng.normal(size=(10, 8))
        b = rng.uniform(size=(10, 8))
        before = loss_geometry(r[:5], b[:5])
        r[5:] = -999
        b[5:] = 999
        after = loss_geometry(r[:5], b[:5])
        for key in before:
            np.testing.assert_allclose(before[key], after[key])

    def test_residual_is_orthogonal_without_future_outcome(self):
        rng = np.random.default_rng(27)
        controls = pd.DataFrame(rng.normal(size=(1000, 3)))
        f = controls[0] * 2 + rng.normal(size=1000)
        r5 = pd.Series(-rng.uniform(size=1000))
        strata, groups, residual = conditional_groups(f, controls, r5)
        np.testing.assert_allclose(controls.to_numpy().T @ residual, 0, atol=1e-10)
        self.assertEqual(set(strata), set(range(1, 11)))
        self.assertEqual(set(groups), set(range(1, 6)))

    def test_cross_period_labels_are_excluded(self):
        f = pd.DataFrame({"date": pd.to_datetime(["2024-12-20", "2024-12-30"]),
                          "label_end": pd.to_datetime(["2024-12-27", "2025-01-08"])})
        self.assertEqual(period_mask(f, "2024-01-01", "2024-12-31").tolist(), [True, False])
        self.assertEqual(len(past_training_rows(f, 2025)), 1)

    def test_standardization_is_formed_sample_only(self):
        frame = pd.DataFrame({"x": [1., 2., 3., 4., 100.]})
        z = standardized(frame)
        self.assertAlmostEqual(z.x.mean(), 0)
        self.assertAlmostEqual(z.x.std(), 1)

    def test_partial_execution_changes_shares_not_return_scaling(self):
        days = pd.bdate_range("2020-01-01", periods=4)
        price = pd.DataFrame({"a": [10., 10., 10., 10.]}, index=days)
        bt = simulate(price, price, price * 0 + 1, [0, 1], days[1], days[-1],
                      cost_bps=0, rebalance_fraction=.5)
        np.testing.assert_allclose(bt.cash_weight, [.5, .25, .25])
        np.testing.assert_allclose(bt.turnover, [.5, .25, 0])

    def test_partial_execution_fees_are_paid(self):
        days = pd.bdate_range("2020-01-01", periods=4)
        price = pd.DataFrame({"a": [10., 10., 10., 10.]}, index=days)
        bt = simulate(price, price, price * 0 + 1, [0], days[1], days[-1],
                      cost_bps=10, rebalance_fraction=.5)
        self.assertAlmostEqual(bt.fees.iloc[0], .5 / 1.001 * .001)
        self.assertAlmostEqual(bt.nav.iloc[-1], 1 - .5 / 1.001 * .001)

    def test_partial_rebalance_range(self):
        with self.assertRaises(ValueError):
            simulate(None, None, None, [], None, None, rebalance_fraction=0)


if __name__ == "__main__":
    unittest.main()
