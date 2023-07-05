import numpy
import pandas as pd
from helpers import *


def third_party_model_proforma(BESS_capital_cost_case, BESS_Federal_ITC, rate_class, data):
    outputs = []
    ## 1) load data
    # financials
    Analysis_period = 10 
    Nominal_OM_cost_escalation_rate = 2.5  # % /year
    Nominal_electric_utility_cost_escalation_rate = 2  # % /year
    Nominal_thirdparty_discount_rate = 6.8  # % /year
    Nominal_Host_discount_rate = 10.18  # % /year
    Thirdparty_owner_Federal_income_tax_rate = 28  # (%)
    Host_Federal_income_tax_rate = 26  # (% )
    PV_capacity_kw = 7  # kw
    PV_degradation_rate = 0.5  # pct_per_yr

    PV_installed_cost_per_kw = 0 
    PV_OM_cost_per_kw_yr = 0 
    PV_Federal_ITC = 0  
    BESS_power_kw = 6  # kw
    BESS_energy_capacity_kwh = 19.4  # kwh
    BESS_installed_cost_per_kw = 0
    BESS_OM_cost = 100 #source: NREL ATB 2021 data for 5kW-20kWh battery


    # MACRS
    PV_federal_deprication_yrs = 5  # macrs
    PV_federal_depreciation_bonus_fraction = 1  # macrs
    BESS_federal_deprication_yrs = 7
    BESS_federal_bonus_fraction = 1

    if BESS_capital_cost_case == 'low':
        BESS_installed_cost_per_kwh = 727
    elif BESS_capital_cost_case == 'high':
        BESS_installed_cost_per_kwh = 1041
    else:
        raise ValueError('only can be low or high')

    BESS_replacement_cost_per_kwh = 0 
    BESS_replacement_cost_per_kw = 0

    BESS_replacement_year = 10
    program_participant_count = 100 #evergy btm pilot
    avoided_dist_cost_per_kw_yr = 71 

    #=============================================================================================
    bau_load = data['LOAD: Site Load Original Load (kW)'].values
    net_load_profile = data['Net Grid Import (kW)'].values
    export_kwh = data['PV Grid Export (kW)'].values

    outputs.append(sum(bau_load)) ### 'BAU load, kWh (annual)
    outputs.append(sum(net_load_profile)) # 'Import from Grid


    if 'PV: solar1 Electric Generation (kW)'in data:
        PV_gen_profile =  data['PV: solar1 Electric Generation (kW)'].values
        y1_PV_prod_bau = 0
        y1_PV_prod_scenario = sum(PV_gen_profile)
        outputs.append(y1_PV_prod_scenario) ####'PV Generation, kWh(annual, year 1)'
        PV_annual_elec_prod_kWh = calculate_PV_prod_annual_timeseries(y1_PV_prod_scenario = y1_PV_prod_scenario,
                                                                      Analysis_period = Analysis_period,
                                                                      PV_degradation_rate = PV_degradation_rate)
        PV_avg_optim_elec_prod_kWh = sum(
            PV_annual_elec_prod_kWh)/len(PV_annual_elec_prod_kWh)
    else:
        outputs.append(0) #'PV Generation, kWh(annual, year 1)'

    outputs.append(sum(export_kwh)) #'Net-Metered, KWh (annual, year 1)'
    ######################################################################################################

    avoided_lmp_cost = calculate_utility_avoided_energy_cost(bau_load, net_load_profile)
    avoided_lmp_cost = program_participant_count*avoided_lmp_cost
    avoided_lmp_cost_cashflow = calculate_annual_cashflow(amount= -1*avoided_lmp_cost,
                                                          Analysis_period = Analysis_period,
                                                          escalation_rate = 2.5) 
    discounted_avoided_lmp_cashflow = []
    for i in range(0, Analysis_period):
        amount = avoided_lmp_cost_cashflow[i] / \
            (1+Nominal_thirdparty_discount_rate/100)**i
        discounted_avoided_lmp_cashflow.append(amount)

    NPV_of_avoided_lmp_cost = sum(discounted_avoided_lmp_cashflow)

    outputs.append(NPV_of_avoided_lmp_cost) ###############
    # 8/19/2022 15:00 is the SPP peak occurance time

    avoided_td_cost = calculate_utility_avoided_td_cost(data[['Start Datetime (hb)',
                                                              'BATTERY: es Power (kW)',
                                                              'LOAD: Site Load Original Load (kW)',
                                                              'Net Grid Import (kW)',
                                                              'PV Grid Export (kW)']])
    avoided_td_cost =program_participant_count*avoided_td_cost
    outputs.append(avoided_td_cost/avoided_dist_cost_per_kw_yr) # calculated peak append
    avoided_td_cost_cashflow = calculate_annual_cashflow(amount= -1*avoided_td_cost,
                                                      Analysis_period = Analysis_period,
                                                      escalation_rate = 2.5) # 27 oct 2021
    discounted_avoided_td_cost_cashflow = []
    for i in range(0, Analysis_period):
        amount = avoided_td_cost_cashflow[i] / \
            (1+Nominal_thirdparty_discount_rate/100)**i
        discounted_avoided_td_cost_cashflow.append(amount)

    NPV_of_avoided_td_cost = sum(discounted_avoided_td_cost_cashflow)
    outputs.append(NPV_of_avoided_td_cost) ###############

    #============================================================================================================

    # 2. third-party owner calculations

    # 2a) capital cost
    PV_initial_cost = PV_capacity_kw * PV_installed_cost_per_kw
    BESS_initial_cost = (BESS_energy_capacity_kwh * BESS_installed_cost_per_kwh) + \
        (BESS_power_kw*BESS_installed_cost_per_kw)
    Total_initial_capital_cost = (PV_initial_cost + BESS_initial_cost)*program_participant_count

    # 2b) operating expenses
    PV_OM_cost_cashflow = calculate_PV_OM_cashflow_series(PV_OM_cost_per_kw_yr,
                                                          Nominal_OM_cost_escalation_rate,
                                                          PV_capacity_kw*program_participant_count,
                                                          Analysis_period)

    BESS_OM_cost_cashflow = calculate_PV_OM_cashflow_series(BESS_OM_cost*program_participant_count,
                                                      Nominal_OM_cost_escalation_rate,
                                                      1,
                                                      Analysis_period)

    BESS_kW_replacement_cost_cashflow = calculate_bess_replace_cashflow_series(BESS_replacement_year,
                                                                               BESS_replacement_cost_per_kw,
                                                                               BESS_power_kw*program_participant_count,
                                                                               Analysis_period)

    BESS_kWh_replacement_cost_cashflow = calculate_bess_replace_cashflow_series(BESS_replacement_year,
                                                                                BESS_replacement_cost_per_kwh,
                                                                                BESS_energy_capacity_kwh*program_participant_count,
                                                                                Analysis_period)

    total_operating_expense_cashflow = [a+b+c+d for a, b, c, d in zip(PV_OM_cost_cashflow,
                                                                      BESS_OM_cost_cashflow,
                                                                      BESS_kW_replacement_cost_cashflow,
                                                                      BESS_kWh_replacement_cost_cashflow)]
    Tax_deductible_operating_expenses = [
        x if Thirdparty_owner_Federal_income_tax_rate > 0 else 0 for x in total_operating_expense_cashflow]

    # 2c) capital depreciation
    PV_federal_depreication = MACRS_Schedule(years=5)  # years = 5 or 7
    PV_federal_depreication.extend(list(numpy.zeros((Analysis_period-1)-5)))
    BESS_federal_depreciation = MACRS_Schedule(years=7)
    BESS_federal_depreciation.extend(list(numpy.zeros((Analysis_period-1)-7)))

    PV_federal_ITC_basis = PV_initial_cost*program_participant_count
    PV_depriciation_bonus_basis = PV_federal_ITC_basis*(1 - 0.5*(PV_Federal_ITC/100))
    PV_depriciation_basis =PV_depriciation_bonus_basis*0


    PV_depreciation_amount_cashflow = [
        PV_depriciation_basis*PV_federal_depreication[0]+PV_depriciation_bonus_basis]
    PV_depreciation_amount_cashflow.extend(
        list(numpy.zeros(Analysis_period-1))) 

    BESS_federal_ITC_basis = BESS_initial_cost*program_participant_count
    BESS_depriciation_bonus_basis = BESS_federal_ITC_basis * \
        (1 - 0.5*(BESS_Federal_ITC/100))
    BESS_depriciation_basis = BESS_depriciation_bonus_basis*0

    BESS_depreciation_amount_cashflow = [
        BESS_depriciation_basis*BESS_federal_depreciation[0]+BESS_depriciation_bonus_basis]
    BESS_depreciation_amount_cashflow.extend(list(numpy.zeros(Analysis_period-1)))

    Total_depriciation_cashflow = [a+b for a, b in zip(PV_depreciation_amount_cashflow,
                                                       BESS_depreciation_amount_cashflow)]

    # 2d) Tax benefits calculation
    PV_income_tax_savings = []
    for i in range(0, Analysis_period):
        amount = (-1*PV_OM_cost_cashflow[i]+PV_depreciation_amount_cashflow[i]
                  )*Thirdparty_owner_Federal_income_tax_rate/100
        PV_income_tax_savings.append(amount)

    # federal investment tax
    PV_federal_ITC_amount_cashflow = [PV_federal_ITC_basis*PV_Federal_ITC/100]
    PV_federal_ITC_amount_cashflow.extend(list(numpy.zeros(Analysis_period-1)))

    BESS_federal_ITC_amount_cashflow = [BESS_federal_ITC_basis*BESS_Federal_ITC/100]
    BESS_federal_ITC_amount_cashflow.extend(list(numpy.zeros(Analysis_period-1)))

    Total_federal_ITC_cashflow = [a+b for a, b in zip(PV_federal_ITC_amount_cashflow,
                                                      BESS_federal_ITC_amount_cashflow)]

    # 2e) Total cash flows
    # (i)
    Upfront_capital_cost = [Total_initial_capital_cost]
    Upfront_capital_cost.extend(list(numpy.zeros(Analysis_period)))
    Upfront_capital_cost = [element * -1 for element in Upfront_capital_cost]

    # (ii)
    Operating_expense_after_tax_cashflow = [0]
    for i in range(1, Analysis_period+1):
        amount = (total_operating_expense_cashflow[i-1] - Tax_deductible_operating_expenses[i-1]) + \
            Tax_deductible_operating_expenses[i-1] * \
            (1-Thirdparty_owner_Federal_income_tax_rate/100)
        Operating_expense_after_tax_cashflow.append(amount)
    # (iii)
    Depreciation_tax_shield_cashflow = [0]
    for i in range(1, Analysis_period+1):
        amount = Total_depriciation_cashflow[i-1] * \
            (Thirdparty_owner_Federal_income_tax_rate/100)
        Depreciation_tax_shield_cashflow.append(amount)
    # (iv)
    Investment_tax_credit_cashflow = Total_federal_ITC_cashflow
    Investment_tax_credit_cashflow.insert(0, 0)

    # (v) = (i+ii+iii+iv)
    free_cashflow_before_income = [a+b+c+d for a, b, c, d in zip(Upfront_capital_cost,
                                                                 Operating_expense_after_tax_cashflow,
                                                                 Depreciation_tax_shield_cashflow,
                                                                 Investment_tax_credit_cashflow)]
    discounted_cash_flow = []
    for i in range(0, Analysis_period+1):
        amount = free_cashflow_before_income[i] / \
            ((1+Nominal_thirdparty_discount_rate/100)**i)
        discounted_cash_flow.append(amount)

    # (vi)

    Third_party_onwer_net_present_cost = sum(discounted_cash_flow)


    # (vii)
    capital_recovery_factor = ((Nominal_thirdparty_discount_rate/100)*(1+Nominal_thirdparty_discount_rate/100)**Analysis_period) / \
        (-1+(1+Nominal_thirdparty_discount_rate/100)**Analysis_period) / \
        (1-Thirdparty_owner_Federal_income_tax_rate/100)

    # (viii)


    income_from_host_per_year = 50*12*program_participant_count #50$/per month 

    income_from_host_cashflow = [0]
    for i in range(1, Analysis_period+1):
        income_from_host_cashflow.append(income_from_host_per_year)


    income_from_host_after_tax_cashflow = [0]
    for i in range(1, Analysis_period+1):
        amount = income_from_host_cashflow[i]
        income_from_host_after_tax_cashflow.append(amount)

    discounted_income_from_host_cash_flow = [0]
    for i in range(1, Analysis_period+1):
        amount = income_from_host_after_tax_cashflow[i] / \
            ((1+Nominal_thirdparty_discount_rate/100)**i)
        discounted_income_from_host_cash_flow.append(amount)

    NPV_income_from_host = sum(discounted_income_from_host_cash_flow)

    lmp_benefit_cashflow = [0]
    for i in range(1, Analysis_period+1):
        lmp_benefit_cashflow.append(avoided_lmp_cost_cashflow[i-1])

    td_capacity_benefit_cashflow = [0]
    for i in range(1, Analysis_period+1):
        td_capacity_benefit_cashflow.append(avoided_td_cost_cashflow[i-1])

    total_benefit_cashflow =[a+b+c for a, b, c in zip(income_from_host_cashflow,
                                                      lmp_benefit_cashflow,
                                                      td_capacity_benefit_cashflow)]

    benefit_after_tax_cashflow = [0]
    for i in range(1, Analysis_period+1):
        amount = total_benefit_cashflow[i]
        benefit_after_tax_cashflow.append(amount)

    discounted_benefit_cash_flow = [0]
    for i in range(1, Analysis_period+1):
        amount = benefit_after_tax_cashflow[i] / \
            ((1+Nominal_thirdparty_discount_rate/100)**i)
        discounted_benefit_cash_flow.append(amount)

    benefit_NPV = sum(discounted_benefit_cash_flow)

    free_cash_flow_after_income = [Upfront_capital_cost[0]]
    for i in range(1, Analysis_period+1):
        amount = free_cashflow_before_income[i] + benefit_after_tax_cashflow[i]
        free_cash_flow_after_income.append(amount)

    Cumulative_free_cash_flow_after_income = [sum(
        free_cash_flow_after_income[0:x:1]) for x in range(0, len(free_cash_flow_after_income)+1)][1:]

    payback = payback_period(cum_cashflow=Cumulative_free_cash_flow_after_income)

    #==========================================================================================================

    # 3) host cashflow-  actual operation years (yr 1 to yr 10) data

    y1_elec_bill_bau = calculate_bill(hourly_profile_annual = data[['Start Datetime (hb)','LOAD: Site Load Original Load (kW)']], rate_class = rate_class)
    y1_elec_bill_optimal = calculate_bill(data[['Start Datetime (hb)','Net Grid Import (kW)']], rate_class = rate_class)
    y1_optimal_export_credit = y1_optimal_export_credit = calculate_export_credit(hourly_profile_annual = data[['Start Datetime (hb)','PV Grid Export (kW)']], rate_class = rate_class)   # calculate_export_credit()

    outputs.append(y1_elec_bill_bau) #######
    outputs.append(y1_elec_bill_bau- y1_elec_bill_optimal) ######
    outputs.append(y1_optimal_export_credit) ################


    # (i)
    bau_bill_cashflow = calculate_annual_cashflow(y1_elec_bill_bau,
                                                  Analysis_period,
                                                  Nominal_electric_utility_cost_escalation_rate)
    # (ii)
    optim_bill_cashflow_before_export_credits = calculate_annual_cashflow(y1_elec_bill_optimal,
                                                                          Analysis_period,
                                                                          Nominal_electric_utility_cost_escalation_rate)
    # (iii)
    optim_export_credit_cashflow = calculate_annual_cashflow(y1_optimal_export_credit,
                                                             Analysis_period,
                                                             Nominal_electric_utility_cost_escalation_rate)
    # (iv)
    payment_to_third_party_owner_cashflow = []
    for i in range(0, Analysis_period):
        amount = (-1)*600
        payment_to_third_party_owner_cashflow.append(amount)

    # (v)
    bau_case_free_cashflow = bau_bill_cashflow
    optimal_case_free_cashflow = [a+b+c for a, b, c in zip(optim_bill_cashflow_before_export_credits,
                                                           optim_export_credit_cashflow,
                                                           payment_to_third_party_owner_cashflow)]

    # (vi)
    net_bill_savings = [a-b for a, b in zip(optimal_case_free_cashflow,
                                            bau_case_free_cashflow)]

    tax_deductible_cost_savings = net_bill_savings

    # (vii)
    net_savings_after_tax_cashflow = []
    for i in range(0, Analysis_period):
        amount = tax_deductible_cost_savings[i]*(1-Host_Federal_income_tax_rate/100)
        net_savings_after_tax_cashflow.append(amount)

    discounted_net_savings_cashflow = []
    for i in range(1, Analysis_period+1):
        amount = net_savings_after_tax_cashflow[i-1] / \
            (1+Nominal_Host_discount_rate/100)**i
        discounted_net_savings_cashflow.append(amount)

    NPV_of_savings_by_host = sum(discounted_net_savings_cashflow)

    #===========================================================================================================

    outputs.append(-1*Third_party_onwer_net_present_cost)
    outputs.append(0)
    outputs.append(NPV_income_from_host)
    outputs.append(payback)
    outputs.append(NPV_of_savings_by_host)

    return outputs


