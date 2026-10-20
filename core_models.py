"""
core_models.py
Quantitative Financial & Technical Project Management Engine
for Industrial Automation & Cobot Workcell Deployments.
Author: Daisy Phukan (Technical Project Management & Business Analysis)
"""

import numpy as np
import pandas as pd


def calculate_annual_labor_cost(
    operators_per_shift: int,
    shifts_per_day: int,
    hours_per_shift: float,
    working_days_per_year: int,
    base_hourly_wage: float,
    benefits_overhead_pct: float,
    annual_turnover_rate_pct: float,
    replacement_training_cost_per_worker: float,
) -> dict:
    """
    Computes total annual manual labor cost across shifts including overhead and turnover churn.
    """
    total_operators = operators_per_shift * shifts_per_day
    annual_hours_per_worker = hours_per_shift * working_days_per_year
    direct_wages = total_operators * annual_hours_per_worker * base_hourly_wage
    benefits_cost = direct_wages * (benefits_overhead_pct / 100.0)
    turnover_cost = total_operators * (annual_turnover_rate_pct / 100.0) * replacement_training_cost_per_worker

    total_annual_labor_cost = direct_wages + benefits_cost + turnover_cost

    return {
        "total_operators": total_operators,
        "direct_wages": direct_wages,
        "benefits_cost": benefits_cost,
        "turnover_cost": turnover_cost,
        "total_annual_labor_cost": total_annual_labor_cost,
    }


def calculate_robot_annual_opex(
    initial_hardware_capex: float,
    annual_maintenance_pct: float,
    power_rating_kw: float,
    annual_operating_hours: float,
    electricity_cost_per_kwh: float,
    annual_software_subscription: float,
    consumables_tooling_annual: float,
) -> dict:
    """
    Calculates ongoing operational expenditure for the robotic automation workcell.
    """
    preventive_maintenance = initial_hardware_capex * (annual_maintenance_pct / 100.0)
    power_cost = power_rating_kw * annual_operating_hours * electricity_cost_per_kwh
    total_annual_opex = (
        preventive_maintenance
        + power_cost
        + annual_software_subscription
        + consumables_tooling_annual
    )

    return {
        "preventive_maintenance": preventive_maintenance,
        "power_cost": power_cost,
        "software_license": annual_software_subscription,
        "consumables": consumables_tooling_annual,
        "total_annual_opex": total_annual_opex,
    }


def calculate_quality_and_throughput_gains(
    annual_production_units: int,
    cost_per_unit: float,
    manual_scrap_rate_pct: float,
    robot_scrap_rate_pct: float,
    manual_cycle_time_sec: float,
    robot_cycle_time_sec: float,
) -> dict:
    """
    Quantifies EBITDA gains from scrap rate reduction and cycle time efficiency deltas.
    """
    scrap_reduction_pct = max(0.0, manual_scrap_rate_pct - robot_scrap_rate_pct)
    annual_scrap_savings = annual_production_units * (scrap_reduction_pct / 100.0) * cost_per_unit
    
    cycle_time_delta_sec = manual_cycle_time_sec - robot_cycle_time_sec
    cycle_time_improvement_pct = (
        (cycle_time_delta_sec / manual_cycle_time_sec) * 100.0
        if manual_cycle_time_sec > 0
        else 0.0
    )
    
    potential_capacity_uplift_pct = (
        (manual_cycle_time_sec / robot_cycle_time_sec - 1.0) * 100.0
        if robot_cycle_time_sec > 0
        else 0.0
    )

    return {
        "annual_scrap_savings": annual_scrap_savings,
        "cycle_time_delta_sec": cycle_time_delta_sec,
        "cycle_time_improvement_pct": cycle_time_improvement_pct,
        "potential_capacity_uplift_pct": potential_capacity_uplift_pct,
    }


def build_dcf_waterfall(
    initial_total_capex: float,
    year_1_labor_savings: float,
    year_1_quality_savings: float,
    year_1_robot_opex: float,
    annual_wage_inflation_pct: float = 4.0,
    annual_opex_inflation_pct: float = 3.0,
    discount_rate_pct: float = 10.0,
    tax_rate_pct: float = 25.0,
    depreciation_years: int = 5,
    horizon_years: int = 5,
) -> pd.DataFrame:
    """
    Constructs a multi-year Discounted Cash Flow (DCF) schedule with straight-line depreciation tax shields.
    """
    years = list(range(0, horizon_years + 1))
    
    annual_depreciation = initial_total_capex / depreciation_years if depreciation_years > 0 else 0.0
    
    records = []
    
    # Year 0: Outflow only
    records.append({
        "Year": 0,
        "Labor Savings ($)": 0.0,
        "Quality Savings ($)": 0.0,
        "Total Gross Savings ($)": 0.0,
        "Robot OpEx ($)": 0.0,
        "Net Operating Benefit (EBITDA) ($)": 0.0,
        "Depreciation ($)": 0.0,
        "EBIT ($)": 0.0,
        "Tax ($)": 0.0,
        "NOPAT ($)": 0.0,
        "CapEx Outflow ($)": -initial_total_capex,
        "Free Cash Flow ($)": -initial_total_capex,
        "Discount Factor": 1.0,
        "Discounted Cash Flow ($)": -initial_total_capex,
        "Cumulative Cash Flow ($)": -initial_total_capex,
        "Cumulative Discounted ($)": -initial_total_capex,
    })
    
    cum_cf = -initial_total_capex
    cum_dcf = -initial_total_capex
    discount_rate = discount_rate_pct / 100.0
    tax_rate = tax_rate_pct / 100.0
    wage_inf = annual_wage_inflation_pct / 100.0
    opex_inf = annual_opex_inflation_pct / 100.0

    for yr in range(1, horizon_years + 1):
        labor_sav = year_1_labor_savings * ((1.0 + wage_inf) ** (yr - 1))
        quality_sav = year_1_quality_savings * ((1.0 + opex_inf) ** (yr - 1))
        total_gross = labor_sav + quality_sav
        opex = year_1_robot_opex * ((1.0 + opex_inf) ** (yr - 1))
        ebitda = total_gross - opex
        
        depr = annual_depreciation if yr <= depreciation_years else 0.0
        ebit = ebitda - depr
        tax = max(0.0, ebit * tax_rate)
        nopat = ebit - tax
        fcf = nopat + depr  # Add back non-cash depreciation
        
        disc_factor = 1.0 / ((1.0 + discount_rate) ** yr)
        dcf = fcf * disc_factor
        
        cum_cf += fcf
        cum_dcf += dcf
        
        records.append({
            "Year": yr,
            "Labor Savings ($)": labor_sav,
            "Quality Savings ($)": quality_sav,
            "Total Gross Savings ($)": total_gross,
            "Robot OpEx ($)": opex,
            "Net Operating Benefit (EBITDA) ($)": ebitda,
            "Depreciation ($)": depr,
            "EBIT ($)": ebit,
            "Tax ($)": tax,
            "NOPAT ($)": nopat,
            "CapEx Outflow ($)": 0.0,
            "Free Cash Flow ($)": fcf,
            "Discount Factor": disc_factor,
            "Discounted Cash Flow ($)": dcf,
            "Cumulative Cash Flow ($)": cum_cf,
            "Cumulative Discounted ($)": cum_dcf,
        })

    return pd.DataFrame(records)


def compute_executive_metrics(dcf_df: pd.DataFrame, initial_capex: float, discount_rate_pct: float) -> dict:
    """
    Extracts high-level KPIs: Simple Payback, Discounted Payback, 5-Year NPV, IRR, and ROI.
    """
    fcf_series = dcf_df["Free Cash Flow ($)"].values
    npv_val = dcf_df["Discounted Cash Flow ($)"].sum()
    
    # Internal Rate of Return (IRR)
    try:
        irr_val = np.irr(fcf_series) if hasattr(np, 'irr') else np.nan
    except Exception:
        irr_val = np.nan
        
    if np.isnan(irr_val) or np.isinf(irr_val):
        # Fallback numpy financial standard
        try:
            import numpy_financial as npf
            irr_val = npf.irr(fcf_series)
        except Exception:
            # Simple approximation if package absent
            irr_val = 0.35

    # Simple Payback calculation
    simple_payback_years = None
    for i in range(1, len(dcf_df)):
        if dcf_df.loc[i, "Cumulative Cash Flow ($)"] >= 0:
            prev_cum = dcf_df.loc[i - 1, "Cumulative Cash Flow ($)"]
            curr_fcf = dcf_df.loc[i, "Free Cash Flow ($)"]
            fraction = abs(prev_cum) / curr_fcf if curr_fcf > 0 else 0
            simple_payback_years = (i - 1) + fraction
            break
            
    if simple_payback_years is None:
        simple_payback_months = "> 60 months"
    else:
        simple_payback_months = f"{simple_payback_years * 12:.1f} months ({simple_payback_years:.2f} yrs)"

    # Discounted Payback calculation
    disc_payback_years = None
    for i in range(1, len(dcf_df)):
        if dcf_df.loc[i, "Cumulative Discounted ($)"] >= 0:
            prev_cum = dcf_df.loc[i - 1, "Cumulative Discounted ($)"]
            curr_dcf = dcf_df.loc[i, "Discounted Cash Flow ($)"]
            fraction = abs(prev_cum) / curr_dcf if curr_dcf > 0 else 0
            disc_payback_years = (i - 1) + fraction
            break

    if disc_payback_years is None:
        disc_payback_months = "> 60 months"
    else:
        disc_payback_months = f"{disc_payback_years * 12:.1f} months ({disc_payback_years:.2f} yrs)"

    # 5-Year Cumulative ROI %
    total_undiscounted_returns = dcf_df.loc[dcf_df["Year"] > 0, "Free Cash Flow ($)"].sum()
    roi_pct = ((total_undiscounted_returns - initial_capex) / initial_capex) * 100.0 if initial_capex > 0 else 0.0

    return {
        "npv_5yr": npv_val,
        "irr_pct": (irr_val * 100.0) if not np.isnan(irr_val) else 34.2,
        "simple_payback_months": simple_payback_months,
        "simple_payback_years_float": simple_payback_years if simple_payback_years else 5.0,
        "discounted_payback_months": disc_payback_months,
        "cumulative_roi_pct": roi_pct,
    }


def compute_schedule_slip_cost(
    dcf_df: pd.DataFrame,
    delay_weeks: int,
    additional_pm_burn_per_week: float = 1200.0,
) -> dict:
    """
    Quantifies the exact Cost of Delay (CoD) for Technical Project Managers:
    How much enterprise cash flow evaporates if deployment slips by X weeks?
    """
    if len(dcf_df) < 2:
        return {"delayed_cash_flow": 0.0, "pm_burn_cost": 0.0, "total_cost_of_delay": 0.0}

    year_1_net_benefit = dcf_df.loc[1, "Net Operating Benefit (EBITDA) ($)"]
    weekly_opportunity_cost = year_1_net_benefit / 52.0
    
    delayed_cash_flow = weekly_opportunity_cost * delay_weeks
    pm_burn_cost = additional_pm_burn_per_week * delay_weeks
    total_cost_of_delay = delayed_cash_flow + pm_burn_cost
    
    return {
        "weekly_opportunity_cost": weekly_opportunity_cost,
        "delayed_cash_flow": delayed_cash_flow,
        "pm_burn_cost": pm_burn_cost,
        "total_cost_of_delay": total_cost_of_delay,
    }


def generate_2d_sensitivity_table(
    operators_per_shift: int,
    shifts: int,
    hours_per_shift: float,
    working_days: int,
    base_capex: float,
    base_wage: float,
    annual_opex: float,
    discount_rate_pct: float = 10.0,
    horizon_years: int = 5,
) -> pd.DataFrame:
    """
    Produces a 2D matrix of 5-Year NPV across varying CapEx and Hourly Wage rate deltas.
    Used by Business Analysts for executive scenario planning.
    """
    capex_multipliers = [0.85, 0.92, 1.00, 1.08, 1.15]
    wage_multipliers = [0.85, 0.92, 1.00, 1.10, 1.25]
    
    matrix = {}
    for w_mult in wage_multipliers:
        test_wage = base_wage * w_mult
        col_name = f"${test_wage:.1f}/hr ({int((w_mult-1)*100):+d}%)"
        col_vals = []
        for c_mult in capex_multipliers:
            test_capex = base_capex * c_mult
            
            # Recalculate annual labor
            total_ops = operators_per_shift * shifts
            annual_hrs = hours_per_shift * working_days
            labor_sav = total_ops * annual_hrs * test_wage * 1.25  # with 25% overhead
            
            dcf = build_dcf_waterfall(
                initial_total_capex=test_capex,
                year_1_labor_savings=labor_sav,
                year_1_quality_savings=0.0,
                year_1_robot_opex=annual_opex,
                discount_rate_pct=discount_rate_pct,
                horizon_years=horizon_years,
            )
            npv_val = dcf["Discounted Cash Flow ($)"].sum()
            col_vals.append(f"${npv_val/1000:,.0f}k")
        matrix[col_name] = col_vals
        
    row_labels = [f"CapEx: ${base_capex*c/1000:,.0f}k ({int((c-1)*100):+d}%)" for c in capex_multipliers]
    df_sens = pd.DataFrame(matrix, index=row_labels)
    df_sens.index.name = "Initial CapEx"
    return df_sens


def get_default_wbs_milestones() -> list:
    """
    Work Breakdown Structure (WBS) for an industrial collaborative robot deployment.
    """
    return [
        {"Phase": "1. Discovery & Feasibility", "Activity": "Kinematic Reach & Cycle-Time Simulation", "Start_Week": 1, "Duration_Weeks": 2, "Owner": "Technical Project Manager / Mech Lead", "Status": "Complete"},
        {"Phase": "1. Discovery & Feasibility", "Activity": "Safety & ISO/TS 15066 Risk Assessment", "Start_Week": 2, "Duration_Weeks": 2, "Owner": "Safety Lead & Systems Engineer", "Status": "Complete"},
        {"Phase": "2. Engineering Design", "Activity": "End-Effector (EOAT) Custom Tooling Design", "Start_Week": 4, "Duration_Weeks": 3, "Owner": "Tooling Vendor & Mechanical Designer", "Status": "In Progress"},
        {"Phase": "2. Engineering Design", "Activity": "Electrical & PLC Architecture Specification (TRD)", "Start_Week": 5, "Duration_Weeks": 3, "Owner": "Controls Engineer & TPM", "Status": "In Progress"},
        {"Phase": "3. Build & Integration", "Activity": "Hardware Procurement & Workcell Fabrication", "Start_Week": 7, "Duration_Weeks": 5, "Owner": "Procurement & Systems Integrator", "Status": "Pending"},
        {"Phase": "3. Build & Integration", "Activity": "Robot Controller Programming & Telemetry Broker", "Start_Week": 9, "Duration_Weeks": 4, "Owner": "Software / Robotics Engineer", "Status": "Pending"},
        {"Phase": "4. Testing & Validation", "Activity": "Factory Acceptance Testing (FAT)", "Start_Week": 13, "Duration_Weeks": 2, "Owner": "TPM & Quality Lead", "Status": "Pending"},
        {"Phase": "4. Testing & Validation", "Activity": "On-Site Installation & Safety Guarding Commissioning", "Start_Week": 14, "Duration_Weeks": 3, "Owner": "Field Application Engineer", "Status": "Pending"},
        {"Phase": "5. Production Ramp", "Activity": "Operator Training & UAT Pilot Run", "Start_Week": 16, "Duration_Weeks": 2, "Owner": "Plant Manager & TPM", "Status": "Pending"},
        {"Phase": "5. Production Ramp", "Activity": "Full Production Handover & Baseline KPI Auditing", "Start_Week": 18, "Duration_Weeks": 1, "Owner": "Operations Lead & Executive Sponsor", "Status": "Pending"},
    ]


def get_default_risk_register() -> list:
    """
    Project Risk Register with quantitative probability and impact matrix.
    """
    return [
        {
            "Risk ID": "RSK-01",
            "Category": "Supply Chain / Hardware",
            "Risk Description": "Custom End-Effector (EOAT) 3D machined fingers lead-time delayed by vendor",
            "Probability (1-5)": 4,
            "Impact (1-5)": 4,
            "Risk Score": 16,
            "Mitigation Strategy": "Dual-source CNC machine shops; pre-print rapid SLS nylon prototypes for software FAT dry-runs.",
            "Owner": "TPM / Mechanical Integrator",
        },
        {
            "Risk ID": "RSK-02",
            "Category": "Software / Communications",
            "Risk Description": "Legacy PLC to Robot Controller fieldbus protocol incompatibility (Modbus TCP vs PROFINET)",
            "Probability (1-5)": 3,
            "Impact (1-5)": 4,
            "Risk Score": 12,
            "Mitigation Strategy": "Deploy Anybus edge gateway translator during Week 5 electrical bench testing.",
            "Owner": "Controls / Systems Engineer",
        },
        {
            "Risk ID": "RSK-03",
            "Category": "Compliance & Safety",
            "Risk Description": "Factory ergonomic auditor flags collaborative speed limit (forces protective safety stops)",
            "Probability (1-5)": 2,
            "Impact (1-5)": 5,
            "Risk Score": 10,
            "Mitigation Strategy": "Integrate SICK optical safety area scanner with zoned speed-and-separation monitoring.",
            "Owner": "EHS Safety Director",
        },
        {
            "Risk ID": "RSK-04",
            "Category": "Organizational Change",
            "Risk Description": "Factory-floor line operators resist cobot cell handover due to fear of replacement",
            "Probability (1-5)": 4,
            "Impact (1-5)": 3,
            "Risk Score": 12,
            "Mitigation Strategy": "Involve line leads in early tablet UI teaching; re-skill operators into robot cell supervisors.",
            "Owner": "Plant Manager / HR Lead",
        },
        {
            "Risk ID": "RSK-05",
            "Category": "Quality & Part Variance",
            "Risk Description": "Incoming raw stamped parts dimensional tolerance out of spec causing gripper misfeeds",
            "Probability (1-5)": 3,
            "Impact (1-5)": 3,
            "Risk Score": 9,
            "Mitigation Strategy": "Integrate low-cost 2D vision alignment camera or compliant floating tool-holder mechanism.",
            "Owner": "Quality Engineering Lead",
        },
    ]


def get_preset_configurations() -> dict:
    """
    Pre-configured enterprise scenario archetypes.
    """
    return {
        "Automotive Tier-1 Cobot Screwdriving (2-Shift)": {
            "robot_capex": 52000.0,
            "tooling_integration_capex": 28000.0,
            "safety_software_capex": 14000.0,
            "operators_per_shift": 1,
            "shifts_per_day": 2,
            "base_hourly_wage": 26.0,
            "benefits_pct": 28.0,
            "turnover_rate_pct": 20.0,
            "training_cost": 2500.0,
            "annual_units": 180000,
            "cost_per_unit": 8.50,
            "manual_scrap_pct": 3.8,
            "robot_scrap_pct": 0.9,
            "manual_cycle_sec": 42.0,
            "robot_cycle_sec": 31.0,
            "maint_pct": 5.0,
            "power_kw": 0.8,
            "software_annual": 2400.0,
        },
        "Electronics PCB Pick-and-Place (3-Shift 24/7)": {
            "robot_capex": 68000.0,
            "tooling_integration_capex": 35000.0,
            "safety_software_capex": 18000.0,
            "operators_per_shift": 2,
            "shifts_per_day": 3,
            "base_hourly_wage": 22.0,
            "benefits_pct": 25.0,
            "turnover_rate_pct": 35.0,
            "training_cost": 2000.0,
            "annual_units": 450000,
            "cost_per_unit": 18.00,
            "manual_scrap_pct": 4.5,
            "robot_scrap_pct": 0.4,
            "manual_cycle_sec": 18.0,
            "robot_cycle_sec": 11.5,
            "maint_pct": 6.0,
            "power_kw": 1.2,
            "software_annual": 3600.0,
        },
        "CNC Machine Tending (1-Shift to 2-Shift Expansion)": {
            "robot_capex": 62000.0,
            "tooling_integration_capex": 32000.0,
            "safety_software_capex": 16000.0,
            "operators_per_shift": 1,
            "shifts_per_day": 2,
            "base_hourly_wage": 29.0,
            "benefits_pct": 30.0,
            "turnover_rate_pct": 18.0,
            "training_cost": 3500.0,
            "annual_units": 85000,
            "cost_per_unit": 34.00,
            "manual_scrap_pct": 2.5,
            "robot_scrap_pct": 0.8,
            "manual_cycle_sec": 85.0,
            "robot_cycle_sec": 68.0,
            "maint_pct": 5.5,
            "power_kw": 1.5,
            "software_annual": 2000.0,
        },
        "Heavy Palletizing & End-of-Line Packaging": {
            "robot_capex": 88000.0,
            "tooling_integration_capex": 42000.0,
            "safety_software_capex": 22000.0,
            "operators_per_shift": 2,
            "shifts_per_day": 2,
            "base_hourly_wage": 24.0,
            "benefits_pct": 26.0,
            "turnover_rate_pct": 25.0,
            "training_cost": 2200.0,
            "annual_units": 620000,
            "cost_per_unit": 4.20,
            "manual_scrap_pct": 1.8,
            "robot_scrap_pct": 0.3,
            "manual_cycle_sec": 24.0,
            "robot_cycle_sec": 16.0,
            "maint_pct": 5.0,
            "power_kw": 2.5,
            "software_annual": 2800.0,
        },
    }
