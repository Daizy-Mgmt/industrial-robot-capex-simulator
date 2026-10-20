"""
test_models.py
Unit Test Suite for Industrial Automation CapEx & Robot Cell Payback Simulator.
Author: Daisy Phukan
"""

import unittest
import numpy as np
import pandas as pd
from core_models import (
    calculate_annual_labor_cost,
    calculate_robot_annual_opex,
    calculate_quality_and_throughput_gains,
    build_dcf_waterfall,
    compute_executive_metrics,
    compute_schedule_slip_cost,
    generate_2d_sensitivity_table,
    get_preset_configurations,
)


class TestIndustrialAutomationModels(unittest.TestCase):
    def setUp(self):
        self.preset = get_preset_configurations()["Automotive Tier-1 Cobot Screwdriving (2-Shift)"]

    def test_annual_labor_cost(self):
        # 1 op/shift * 2 shifts = 2 operators. 8 hrs * 250 days = 2000 hrs/yr.
        # Direct wages: 2 * 2000 * $25 = $100,000.
        # Benefits at 20%: $20,000.
        # Turnover at 10% on $2,000 training: 2 * 0.1 * 2000 = $400.
        # Total: $120,400.
        res = calculate_annual_labor_cost(
            operators_per_shift=1,
            shifts_per_day=2,
            hours_per_shift=8.0,
            working_days_per_year=250,
            base_hourly_wage=25.0,
            benefits_overhead_pct=20.0,
            annual_turnover_rate_pct=10.0,
            replacement_training_cost_per_worker=2000.0,
        )
        self.assertEqual(res["total_operators"], 2)
        self.assertAlmostEqual(res["direct_wages"], 100000.0)
        self.assertAlmostEqual(res["benefits_cost"], 20000.0)
        self.assertAlmostEqual(res["turnover_cost"], 400.0)
        self.assertAlmostEqual(res["total_annual_labor_cost"], 120400.0)

    def test_robot_annual_opex(self):
        # CapEx = $50,000, 5% maint = $2,500.
        # 1 kW * 4000 hrs * $0.15/kWh = $600.
        # Software = $2,000, Consumables = $1,000.
        # Total = $6,100.
        res = calculate_robot_annual_opex(
            initial_hardware_capex=50000.0,
            annual_maintenance_pct=5.0,
            power_rating_kw=1.0,
            annual_operating_hours=4000.0,
            electricity_cost_per_kwh=0.15,
            annual_software_subscription=2000.0,
            consumables_tooling_annual=1000.0,
        )
        self.assertAlmostEqual(res["preventive_maintenance"], 2500.0)
        self.assertAlmostEqual(res["power_cost"], 600.0)
        self.assertAlmostEqual(res["software_license"], 2000.0)
        self.assertAlmostEqual(res["consumables"], 1000.0)
        self.assertAlmostEqual(res["total_annual_opex"], 6100.0)

    def test_quality_and_throughput_gains(self):
        # 100,000 units * (5% - 2% = 3%) * $10 = $30,000 savings.
        # Manual cycle = 40s, Robot cycle = 30s. Delta = 10s. Improvement = 25%.
        res = calculate_quality_and_throughput_gains(
            annual_production_units=100000,
            cost_per_unit=10.0,
            manual_scrap_rate_pct=5.0,
            robot_scrap_rate_pct=2.0,
            manual_cycle_time_sec=40.0,
            robot_cycle_time_sec=30.0,
        )
        self.assertAlmostEqual(res["annual_scrap_savings"], 30000.0)
        self.assertAlmostEqual(res["cycle_time_delta_sec"], 10.0)
        self.assertAlmostEqual(res["cycle_time_improvement_pct"], 25.0)

    def test_dcf_waterfall_structure(self):
        dcf_df = build_dcf_waterfall(
            initial_total_capex=94000.0,
            year_1_labor_savings=110000.0,
            year_1_quality_savings=15000.0,
            year_1_robot_opex=7000.0,
            annual_wage_inflation_pct=4.0,
            annual_opex_inflation_pct=3.0,
            discount_rate_pct=10.0,
            tax_rate_pct=25.0,
            depreciation_years=5,
            horizon_years=5,
        )
        # 6 rows: Year 0 through Year 5
        self.assertEqual(len(dcf_df), 6)
        # Year 0 CapEx outflow
        self.assertEqual(dcf_df.loc[0, "CapEx Outflow ($)"], -94000.0)
        self.assertEqual(dcf_df.loc[0, "Free Cash Flow ($)"], -94000.0)
        # Depreciation = 94,000 / 5 = 18,800/yr
        for yr in range(1, 6):
            self.assertAlmostEqual(dcf_df.loc[yr, "Depreciation ($)"], 18800.0)
            self.assertGreater(dcf_df.loc[yr, "Free Cash Flow ($)"], 0.0)

    def test_executive_metrics(self):
        dcf_df = build_dcf_waterfall(
            initial_total_capex=100000.0,
            year_1_labor_savings=120000.0,
            year_1_quality_savings=20000.0,
            year_1_robot_opex=10000.0,
            annual_wage_inflation_pct=3.0,
            annual_opex_inflation_pct=2.5,
            discount_rate_pct=10.0,
            tax_rate_pct=25.0,
        )
        metrics = compute_executive_metrics(dcf_df, initial_capex=100000.0, discount_rate_pct=10.0)
        self.assertIn("npv_5yr", metrics)
        self.assertIn("irr_pct", metrics)
        self.assertIn("simple_payback_months", metrics)
        self.assertGreater(metrics["npv_5yr"], 0.0)
        self.assertGreater(metrics["irr_pct"], 15.0)
        self.assertLess(metrics["simple_payback_years_float"], 3.0)

    def test_schedule_slip_cost_of_delay(self):
        dcf_df = build_dcf_waterfall(
            initial_total_capex=100000.0,
            year_1_labor_savings=104000.0,
            year_1_quality_savings=0.0,
            year_1_robot_opex=4000.0,
        )
        # Net Year 1 EBITDA = 104,000 - 4,000 = 100,000
        # Weekly opportunity cost = 100,000 / 52 = ~1923.08
        res = compute_schedule_slip_cost(dcf_df, delay_weeks=4, additional_pm_burn_per_week=1000.0)
        self.assertAlmostEqual(res["weekly_opportunity_cost"], 100000.0 / 52.0, places=2)
        self.assertAlmostEqual(res["delayed_cash_flow"], (100000.0 / 52.0) * 4, places=2)
        self.assertAlmostEqual(res["pm_burn_cost"], 4000.0)
        self.assertAlmostEqual(res["total_cost_of_delay"], ((100000.0 / 52.0) * 4) + 4000.0, places=2)

    def test_sensitivity_table(self):
        sens_df = generate_2d_sensitivity_table(
            operators_per_shift=1,
            shifts=2,
            hours_per_shift=8.0,
            working_days=250,
            base_capex=94000.0,
            base_wage=26.0,
            annual_opex=6000.0,
        )
        self.assertEqual(sens_df.shape, (5, 5))
        self.assertEqual(sens_df.index.name, "Initial CapEx")

    def test_enterprise_presets(self):
        presets = get_preset_configurations()
        expected_presets = [
            "Automotive Tier-1 Cobot Screwdriving (2-Shift)",
            "Electronics PCB Pick-and-Place (3-Shift 24/7)",
            "CNC Machine Tending (1-Shift to 2-Shift Expansion)",
            "Heavy Palletizing & End-of-Line Packaging",
        ]
        for name in expected_presets:
            self.assertIn(name, presets)
            p = presets[name]
            self.assertGreater(p["robot_capex"], 0)
            self.assertGreater(p["shifts_per_day"], 0)
            self.assertGreater(p["base_hourly_wage"], 0)


if __name__ == "__main__":
    unittest.main()
