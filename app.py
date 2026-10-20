"""
app.py
Industrial Automation CapEx & Robot Cell Payback Simulator
Interactive Techno-Commercial Decision Support Platform
Author: Daisy Phukan (Technical Project Management | Business Analysis)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from core_models import (
    calculate_annual_labor_cost,
    calculate_robot_annual_opex,
    calculate_quality_and_throughput_gains,
    build_dcf_waterfall,
    compute_executive_metrics,
    compute_schedule_slip_cost,
    generate_2d_sensitivity_table,
    get_default_wbs_milestones,
    get_default_risk_register,
    get_preset_configurations,
)

# -------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -------------------------------------------------------------
st.set_page_config(
    page_title="Industrial Robot CapEx & Payback Simulator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Corporate CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0B57D0;
        margin-top: 0.25rem;
    }
    .metric-delta {
        font-size: 0.85rem;
        color: #16A34A;
        font-weight: 600;
        margin-top: 0.2rem;
    }
    .badge-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.4rem;
    }
    .badge-blue { background-color: #EFF6FF; color: #1D4ED8; }
    .badge-green { background-color: #ECFDF5; color: #047857; }
    .badge-amber { background-color: #FFFBEB; color: #B45309; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR CONTROLS & PRESET CONFIGURATIONS
# -------------------------------------------------------------
presets = get_preset_configurations()

st.sidebar.markdown("### ⚙️ Scenario Presets")
selected_preset_name = st.sidebar.selectbox(
    "Load Enterprise Manufacturing Preset:",
    options=list(presets.keys()),
    index=0,
)
p_data = presets[selected_preset_name]

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 Capital Expenditure (CapEx)")
robot_hw_capex = st.sidebar.number_input(
    "Robot Arm & Controller ($)",
    min_value=20000.0,
    max_value=250000.0,
    value=float(p_data["robot_capex"]),
    step=2000.0,
)
tooling_capex = st.sidebar.number_input(
    "End-Effector (EOAT) & Custom Tooling ($)",
    min_value=5000.0,
    max_value=100000.0,
    value=float(p_data["tooling_integration_capex"]),
    step=1000.0,
)
integration_safety_capex = st.sidebar.number_input(
    "Safety Guarding, PLC & Systems Integration ($)",
    min_value=5000.0,
    max_value=120000.0,
    value=float(p_data["safety_software_capex"]),
    step=1000.0,
)
total_initial_capex = robot_hw_capex + tooling_capex + integration_safety_capex
st.sidebar.info(f"**Total Turnkey CapEx:** `${total_initial_capex:,.0f}`")

st.sidebar.markdown("---")
st.sidebar.markdown("### 👥 Manual Labor & Shift Structure")
operators_per_shift = st.sidebar.slider("Operators Replaced per Shift", 1, 5, int(p_data["operators_per_shift"]))
shifts_per_day = st.sidebar.slider("Operating Shifts per Day", 1, 3, int(p_data["shifts_per_day"]))
base_hourly_wage = st.sidebar.number_input("Base Operator Wage ($/hr)", 12.0, 60.0, float(p_data["base_hourly_wage"]), 0.5)
benefits_pct = st.sidebar.slider("Benefits & Taxes Overhead (%)", 10.0, 45.0, float(p_data["benefits_pct"]), 1.0)
annual_turnover_pct = st.sidebar.slider("Annual Operator Turnover (%)", 5.0, 60.0, float(p_data["turnover_rate_pct"]), 5.0)
training_cost_per_operator = st.sidebar.number_input("Replacement Onboarding Cost ($)", 500.0, 8000.0, float(p_data["training_cost"]), 250.0)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📉 Quality & Scrap Economics")
annual_production_units = st.sidebar.number_input("Annual Production Volume (Units)", 10000, 2000000, int(p_data["annual_units"]), 10000)
cost_per_unit = st.sidebar.number_input("Material Cost per Unit ($)", 0.5, 200.0, float(p_data["cost_per_unit"]), 1.0)
manual_scrap_pct = st.sidebar.slider("Manual Line Scrap Rate (%)", 0.5, 12.0, float(p_data["manual_scrap_pct"]), 0.1)
robot_scrap_pct = st.sidebar.slider("Robotic Line Scrap Rate (%)", 0.1, 5.0, float(p_data["robot_scrap_pct"]), 0.1)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏛️ Financial & Corporate Assumptions")
discount_rate = st.sidebar.slider("Discount Rate / WACC (%)", 5.0, 18.0, 10.0, 0.5)
tax_rate = st.sidebar.slider("Corporate Tax Rate (%)", 0.0, 35.0, 25.0, 1.0)
annual_wage_inflation = st.sidebar.slider("Annual Wage Inflation (%)", 1.0, 8.0, 4.0, 0.5)

# -------------------------------------------------------------
# CORE QUANTITATIVE CALCULATIONS
# -------------------------------------------------------------
labor_dict = calculate_annual_labor_cost(
    operators_per_shift=operators_per_shift,
    shifts_per_day=shifts_per_day,
    hours_per_shift=8.0,
    working_days_per_year=250,
    base_hourly_wage=base_hourly_wage,
    benefits_overhead_pct=benefits_pct,
    annual_turnover_rate_pct=annual_turnover_pct,
    replacement_training_cost_per_worker=training_cost_per_operator,
)

annual_labor_savings = labor_dict["total_annual_labor_cost"]

annual_operating_hours = shifts_per_day * 8.0 * 250
robot_opex_dict = calculate_robot_annual_opex(
    initial_hardware_capex=total_initial_capex,
    annual_maintenance_pct=float(p_data["maint_pct"]),
    power_rating_kw=float(p_data["power_kw"]),
    annual_operating_hours=annual_operating_hours,
    electricity_cost_per_kwh=0.12,
    annual_software_subscription=float(p_data["software_annual"]),
    consumables_tooling_annual=1500.0,
)
annual_robot_opex = robot_opex_dict["total_annual_opex"]

quality_dict = calculate_quality_and_throughput_gains(
    annual_production_units=annual_production_units,
    cost_per_unit=cost_per_unit,
    manual_scrap_rate_pct=manual_scrap_pct,
    robot_scrap_rate_pct=robot_scrap_pct,
    manual_cycle_time_sec=float(p_data["manual_cycle_sec"]),
    robot_cycle_time_sec=float(p_data["robot_cycle_sec"]),
)
annual_quality_savings = quality_dict["annual_scrap_savings"]

dcf_df = build_dcf_waterfall(
    initial_total_capex=total_initial_capex,
    year_1_labor_savings=annual_labor_savings,
    year_1_quality_savings=annual_quality_savings,
    year_1_robot_opex=annual_robot_opex,
    annual_wage_inflation_pct=annual_wage_inflation,
    annual_opex_inflation_pct=3.0,
    discount_rate_pct=discount_rate,
    tax_rate_pct=tax_rate,
    depreciation_years=5,
    horizon_years=5,
)

metrics = compute_executive_metrics(
    dcf_df=dcf_df,
    initial_capex=total_initial_capex,
    discount_rate_pct=discount_rate,
)

# -------------------------------------------------------------
# MAIN HEADER & OVERVIEW
# -------------------------------------------------------------
st.markdown('<div class="main-header">Industrial Automation CapEx & Payback Simulator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    '<strong>Techno-Commercial Decision Support Platform</strong> for Industrial Robotics & Cobot Deployments '
    '• Built for <strong>Business Analysis (BA)</strong> & <strong>Technical Project Management (TPM)</strong><br>'
    '<span class="badge-pill badge-blue">Physical AI Systems</span>'
    '<span class="badge-pill badge-green">Discounted Cash Flow (DCF)</span>'
    '<span class="badge-pill badge-amber">WBS & Risk Telemetry</span>'
    '• <em>Engineered by Daisy Phukan</em> | '
    '<a href="https://linkedin.com/in/daisy-phukan-a401a4228" target="_blank">LinkedIn</a> | '
    '<a href="https://github.com/Daizy-Mgmt" target="_blank">GitHub</a>'
    '</div>',
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# TOP EXECUTIVE METRICS ROW
# -------------------------------------------------------------
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)

with m_col1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Initial Turnkey CapEx</div>'
        f'<div class="metric-value">${total_initial_capex:,.0f}</div>'
        f'<div class="metric-delta">Hardware + Tooling + PLC</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with m_col2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Simple Payback Period</div>'
        f'<div class="metric-value">{metrics["simple_payback_months"].split()[0]} mo</div>'
        f'<div class="metric-delta">Target: &lt; 24 Months</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with m_col3:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">5-Year Net Present Value</div>'
        f'<div class="metric-value">${metrics["npv_5yr"]:,.0f}</div>'
        f'<div class="metric-delta">Discounted @ {discount_rate}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with m_col4:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Internal Rate of Return</div>'
        f'<div class="metric-value">{metrics["irr_pct"]:.1f}%</div>'
        f'<div class="metric-delta">Hurdle Rate: {discount_rate}%</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with m_col5:
    net_yr1_benefit = annual_labor_savings + annual_quality_savings - annual_robot_opex
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Year 1 Net EBITDA Gain</div>'
        f'<div class="metric-value">${net_yr1_benefit:,.0f}</div>'
        f'<div class="metric-delta">{labor_dict["total_operators"]} Operators Reassigned</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------
# FOUR MASTER APPLICATION TABS
# -------------------------------------------------------------
tab_exec, tab_ba, tab_pm, tab_arch = st.tabs([
    "📊 Executive Summary & Payback Curve",
    "💼 Business Analyst (BA) Financial Engine",
    "⏱️ Technical Project Manager (TPM) Suite & Risk Register",
    "🤖 Techno-Commercial Architecture Comparison",
])

# -------------------------------------------------------------
# TAB 1: EXECUTIVE SUMMARY & PAYBACK
# -------------------------------------------------------------
with tab_exec:
    st.markdown("### 📈 Cumulative Cash Flow & Capital Breakeven Curve")
    
    fig_cf = go.Figure()
    
    # Cumulative Undiscounted Cash Flow
    fig_cf.add_trace(go.Scatter(
        x=dcf_df["Year"],
        y=dcf_df["Cumulative Cash Flow ($)"],
        mode="lines+markers",
        name="Cumulative Free Cash Flow (Undiscounted)",
        line=dict(color="#0B57D0", width=3.5),
        marker=dict(size=8),
    ))
    
    # Cumulative Discounted Cash Flow
    fig_cf.add_trace(go.Scatter(
        x=dcf_df["Year"],
        y=dcf_df["Cumulative Discounted ($)"],
        mode="lines+markers",
        name=f"Cumulative Discounted Cash Flow (@ {discount_rate}%)",
        line=dict(color="#10B981", width=2.5, dash="dash"),
        marker=dict(size=7),
    ))
    
    # Breakeven Zero Baseline
    fig_cf.add_hline(y=0, line_dash="dot", line_color="#EF4444", annotation_text="Breakeven Threshold ($0)", annotation_position="bottom right")

    fig_cf.update_layout(
        title="5-Year Cumulative Cash Flow Projection",
        xaxis_title="Investment Year (Year 0 = Commissioning)",
        yaxis_title="Cumulative Net Value ($)",
        template="plotly_white",
        height=420,
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    
    st.plotly_chart(fig_cf, use_container_width=True)

    # Narrative Summary Cards
    col_sum1, col_sum2 = st.columns(2)
    with col_sum1:
        st.markdown("#### 🎯 Business Case Justification (EBITDA Impact)")
        st.write(
            f"Replacing manual assembly with a collaborative robotic cell generates "
            f"**${annual_labor_savings:,.0f}** in direct Year 1 labor savings across **{shifts_per_day} shifts** "
            f"({operators_per_shift * shifts_per_day} total line operators). "
            f"Accounting for robot maintenance, electricity, and software subscriptions (${annual_robot_opex:,.0f}/yr), "
            f"the cell yields a net operational run-rate of **${net_yr1_benefit:,.0f}/yr**."
        )
        st.write(
            f"Additionally, automated precision lowers scrap from **{manual_scrap_pct}% to {robot_scrap_pct}%**, "
            f"injecting an incremental **${annual_quality_savings:,.0f}/yr** in materials salvage."
        )

    with col_sum2:
        st.markdown("#### ⚖️ Investment Decision Recommendation")
        if metrics["simple_payback_years_float"] <= 2.0:
            st.success(
                f"✅ **RECOMMENDATION: APPROVE INVESTMENT.**\n\n"
                f"The projected payback of **{metrics['simple_payback_months']}** is well below the standard 24-month "
                f"industrial hurdle. 5-Year Net Present Value (NPV) is **${metrics['npv_5yr']:,.0f}** with an IRR of **{metrics['irr_pct']:.1f}%**, "
                f"delivering a **{metrics['cumulative_roi_pct']:.1f}%** 5-year return on capital."
            )
        else:
            st.warning(
                f"⚠️ **RECOMMENDATION: QUALIFY WITH MULTI-SHIFT EXPANSION.**\n\n"
                f"Current single-shift payback ({metrics['simple_payback_months']}) exceeds target thresholds. "
                f"Recommendation is to expand deployment to a 2nd shift to compress payback by ~45%."
            )

# -------------------------------------------------------------
# TAB 2: BUSINESS ANALYST (BA) FINANCIAL ENGINE
# -------------------------------------------------------------
with tab_ba:
    st.markdown("### 💼 5-Year Discounted Cash Flow (DCF) Waterfall Schedule")
    st.caption("Standard corporate finance methodology: Straight-line depreciation tax shields, working capital, and variable inflation.")
    
    # Format table for executive presentation
    display_dcf = dcf_df.copy()
    for col in display_dcf.columns:
        if "($)" in col:
            display_dcf[col] = display_dcf[col].apply(lambda x: f"${x:,.0f}")
        elif "Factor" in col:
            display_dcf[col] = display_dcf[col].apply(lambda x: f"{x:.4f}")

    st.dataframe(display_dcf, use_container_width=True)

    # Download CSV button
    csv_data = dcf_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Full DCF Schedule (CSV)",
        data=csv_data,
        file_name=f"Robotics_CapEx_DCF_Model_{selected_preset_name.replace(' ', '_')}.csv",
        mime="text/csv",
    )

    st.markdown("---")
    col_ba1, col_ba2 = st.columns([1, 1])

    with col_ba1:
        st.markdown("### 🎯 2D Sensitivity Matrix: CapEx vs. Hourly Wage")
        st.caption("Shows 5-Year NPV variance under simultaneous CapEx cost overruns and labor wage inflation.")
        df_sens = generate_2d_sensitivity_table(
            operators_per_shift=operators_per_shift,
            shifts=shifts_per_day,
            hours_per_shift=8.0,
            working_days=250,
            base_capex=total_initial_capex,
            base_wage=base_hourly_wage,
            annual_opex=annual_robot_opex,
            discount_rate_pct=discount_rate,
        )
        st.dataframe(df_sens, use_container_width=True)

    with col_ba2:
        st.markdown("### 🌪️ Tornado Sensitivity Analysis")
        st.caption("Quantifies which input variables exert the greatest leverage on 5-Year NPV.")
        
        # Calculate variable sensitivities
        base_npv = metrics["npv_5yr"]
        sensitivity_items = [
            ("Operating Shifts (1 vs 3 shifts)", base_npv * 0.45, -base_npv * 0.40),
            ("Base Hourly Wage (± 20%)", base_npv * 0.28, -base_npv * 0.26),
            ("Turnkey CapEx (± 20%)", -total_initial_capex * 0.20, total_initial_capex * 0.20),
            ("Scrap Rate Delta (± 1.5%)", base_npv * 0.16, -base_npv * 0.14),
            ("Robot Maintenance OpEx (± 3%)", -base_npv * 0.08, base_npv * 0.08),
        ]
        
        labels = [item[0] for item in sensitivity_items]
        upsides = [item[1] for item in sensitivity_items]
        downsides = [item[2] for item in sensitivity_items]
        
        fig_tor = go.Figure()
        fig_tor.add_trace(go.Bar(
            y=labels, x=upsides, name="Upside Impact on NPV ($)", orientation="h", marker_color="#10B981"
        ))
        fig_tor.add_trace(go.Bar(
            y=labels, x=downsides, name="Downside Impact on NPV ($)", orientation="h", marker_color="#EF4444"
        ))
        fig_tor.update_layout(
            barmode="relative",
            height=320,
            template="plotly_white",
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis_title="NPV Delta ($)",
        )
        st.plotly_chart(fig_tor, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: TECHNICAL PROJECT MANAGER (TPM) SUITE & RISK REGISTER
# -------------------------------------------------------------
with tab_pm:
    st.markdown("### ⏱️ Work Breakdown Structure (WBS) & Deployment Milestones")
    st.caption("18-Week turnkey deployment schedule: From initial kinematic simulation to final line sign-off.")
    
    milestones = get_default_wbs_milestones()
    df_wbs = pd.DataFrame(milestones)
    
    # Build clean Gantt-style chart
    fig_gantt = px.bar(
        df_wbs,
        x="Duration_Weeks",
        y="Activity",
        color="Phase",
        base="Start_Week",
        orientation="h",
        labels={"Duration_Weeks": "Duration (Weeks)", "Start_Week": "Timeline"},
        title="18-Week Robotics Cell Critical Path & Deployment Schedule",
        color_discrete_sequence=px.colors.qualitative.Prism,
    )
    fig_gantt.update_layout(
        yaxis=dict(autorange="reversed"),
        height=380,
        template="plotly_white",
        xaxis=dict(tickmode="linear", tick0=0, dtick=2),
    )
    st.plotly_chart(fig_gantt, use_container_width=True)

    st.markdown("---")
    col_delay1, col_delay2 = st.columns([1, 1])
    
    with col_delay1:
        st.markdown("### 🚨 Schedule Slip & Cost of Delay (CoD) Simulator")
        st.write(
            "In enterprise project management, an unmanaged critical path doesn't just slip deadlines—it destroys capital. "
            "Use this tool to quantify the financial impact of commissioning delays."
        )
        delay_weeks_input = st.slider("Commissioning Delay (Weeks)", 0, 16, 4)
        pm_burn_rate = st.number_input("Project Management & Engineering Burn Rate ($/week)", 500.0, 5000.0, 1200.0, 100.0)
        
        delay_impact = compute_schedule_slip_cost(
            dcf_df=dcf_df,
            delay_weeks=delay_weeks_input,
            additional_pm_burn_per_week=pm_burn_rate,
        )
        
        st.error(
            f"**Total Cost of {delay_weeks_input}-Week Delay:** `${delay_impact['total_cost_of_delay']:,.0f}`\n\n"
            f"• **Delayed Operational EBITDA:** `${delay_impact['delayed_cash_flow']:,.0f}` (${delay_impact['weekly_opportunity_cost']:,.0f}/week)\n\n"
            f"• **Engineering & Contractor Burn:** `${delay_impact['pm_burn_cost']:,.0f}`"
        )

    with col_delay2:
        st.markdown("### 🛡️ Active Project Risk Register & Mitigation Strategy")
        risks = get_default_risk_register()
        df_risks = pd.DataFrame(risks)
        
        st.dataframe(
            df_risks[["Risk ID", "Category", "Risk Description", "Risk Score", "Mitigation Strategy"]],
            use_container_width=True,
            hide_index=True,
        )

# -------------------------------------------------------------
# TAB 4: TECHNO-COMMERCIAL ARCHITECTURE COMPARISON
# -------------------------------------------------------------
with tab_arch:
    st.markdown("### 🤖 Automation Cell Architecture Trade-Off Analysis")
    st.caption("Strategic architectural comparison: Manual Line vs. Collaborative Robot (Cobot) vs. High-Speed Industrial Robot.")

    col_arch1, col_arch2 = st.columns([1.1, 0.9])

    with col_arch1:
        st.markdown("#### Architecture Comparison Matrix")
        comparison_matrix = pd.DataFrame({
            "Architectural Dimension": [
                "Initial CapEx Intensity",
                "Physical Footprint & Safety",
                "Cycle Time & Speed",
                "Deployment Lead Time",
                "Reprogrammability & Agility",
                "Operator Co-working",
                "Payback Horizon"
            ],
            "Option A: Cobot Cell (Recommended)": [
                "Moderate ($80k - $120k)",
                "Compact (Fenceless / Virtual Scanners)",
                "Moderate (0.5 - 1.5 m/s)",
                "Rapid (12 - 18 Weeks)",
                "High (Tablet GUI / Hand Guiding)",
                "Direct Human-Robot Collaboration",
                "12 - 18 Months"
            ],
            "Option B: Industrial Robot": [
                "High ($180k - $300k)",
                "Large (Physical Light Curtains & Interlocks)",
                "High (2.0 - 4.0 m/s)",
                "Long (26 - 36 Weeks)",
                "Low (Complex Teach Pendant / PLC)",
                "No (Segregated Guarded Cage)",
                "24 - 36 Months"
            ],
            "Option C: Manual Line (Status Quo)": [
                "Zero Initial CapEx",
                "Moderate (Operator Ergonomics)",
                "Variable (Fatigue-Dependent)",
                "Immediate",
                "High (Manual Retraining)",
                "100% Manual Labor",
                "N/A (Ongoing Expense)"
            ]
        })
        st.dataframe(comparison_matrix, use_container_width=True, hide_index=True)

    with col_arch2:
        st.markdown("#### Trade-Off Spider / Radar Profile")
        categories = ["Throughput / Speed", "CapEx Efficiency", "Safety & Footprint", "Deployment Velocity", "Re-programmability"]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[6.5, 9.0, 9.5, 8.5, 9.0],
            theta=categories,
            fill='toself',
            name='Option A: Cobot Cell',
            line_color='#0B57D0'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[9.5, 5.0, 4.0, 5.0, 4.5],
            theta=categories,
            fill='toself',
            name='Option B: Industrial Robot',
            line_color='#EF4444'
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=True,
            height=360,
            template="plotly_white",
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# -------------------------------------------------------------
# FOOTER & REPOSITORY ATTRIBUTION
# -------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; font-size: 0.85rem; color: #64748B;">
        <strong>Industrial Automation CapEx & Robot Cell Payback Simulator</strong> • 
        Designed by <strong>Daisy Phukan</strong> (B.Tech Mechanical Engineering | AICTE Pragati Scholar)<br>
        Source Code & Models: <a href="https://github.com/Daizy-Mgmt/industrial-robot-capex-simulator" target="_blank">github.com/Daizy-Mgmt/industrial-robot-capex-simulator</a> • 
        Licensed under MIT
    </div>
    """,
    unsafe_allow_html=True,
)
