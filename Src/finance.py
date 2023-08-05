# -*- coding: utf-8 -*-
"""
Created on Wed Sep 22 10:36:00 2021

@author: 54651
"""

import numpy
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
from helpers import *
from Code.single_party import *
from Code.third_party import *
from datetime import datetime


def load_data(dispatch, technology, rate_class, files):
    if dispatch == 'ToU_arbitrage' and technology == 'BESS' and rate_class == 'time_of_use' :
        return pd.read_csv(files[0])
    if dispatch == 'ToU_arbitrage' and technology == 'BESS' and rate_class == 'general_service':
        return pd.read_csv(files[1])
    if dispatch == 'ToU_arbitrage' and technology == 'BESS_PV' and rate_class == 'net_metering':
        return pd.read_csv(files[2])
    if dispatch == 'LMP_arbitrage' and technology == 'BESS' and rate_class == 'time_of_use':
        return pd.read_csv(files[3])
    if dispatch == 'LMP_arbitrage' and technology == 'BESS' and rate_class == 'general_service':
        return pd.read_csv(files[4])
    if  dispatch == 'LMP_arbitrage' and technology == 'BESS_PV' and rate_class == 'net_metering':
        return pd.read_csv(files[5])
    if dispatch == 'DR' and technology == 'BESS' and rate_class == 'time_of_use':
        return pd.read_csv(files[6])
    if dispatch == 'DR' and technology == 'BESS' and rate_class == 'general_service':
        return pd.read_csv(files[7])
    if dispatch == 'DR' and technology == 'BESS_PV' and rate_class == 'net_metering':
        return pd.read_csv(files[8])

if __name__ == '__main__':
    scenario = pd.read_csv('all_dispatch - scenario.csv')
    all_outputs =[]

    for k in scenario.Scenario.unique():
        inputs = list(scenario[scenario.Scenario==k].values[0])
        BESS_capital_cost_case = inputs[6]
        BESS_Federal_ITC =  inputs[5]
        technology = inputs [4]
        rate_class = inputs[3]
        ownership = inputs [2]
        dispatch = inputs [1]

        files = ['all_dispatch - BESS_TOU_for_tou.csv', 
                'all_dispatch - BESS_ToU_for_rgs.csv', 
                'all_dispatch - PV_BESS_TOU_for_rgs.csv', 
                'all_dispatch - BESS_LMP_for_rgs_and_tou.csv', 
                'all_dispatch - BESS_LMP_for_rgs_and_tou.csv',
                'all_dispatch - PV_BESS_LMP_for_rgs.csv',
                'all_dispatch - BESS_DR_for_rgs_and_tou.csv', 
                'all_dispatch - BESS_DR_for_rgs_and_tou.csv',
                'all_dispatch - PV_BESS_DR_for_rgs.csv'] 

        data = load_data(dispatch, technology, rate_class, files)

        if ownership == 'customer':
            output = single_party_model_proforma(BESS_capital_cost_case, BESS_Federal_ITC, rate_class, data)
            all_outputs.append(output)
        elif ownership == 'utility':
            output = third_party_model_proforma(BESS_capital_cost_case, BESS_Federal_ITC, rate_class, data)
            all_outputs.append(output)
        else:
            raise ValueError('ownership only can be customer or utility')

    cols = ['Customer BAU Load, kWh (annual)',
            'Customer Import from Grid, kwh (annual, year 1)',
            'Customer PV Generation, kWh(annual, year 1)',
            'Customer Net-Metered, KWh (annual, year 1)',
            'NPV of Utility Avoided Energy Cost, $',
            'Utility Peak Reduction, kW',
            'NPV of Utility Avoided Capacity Cost, $',
            'Customer BAU Bill, $ (year 1)',
            'Customer Bill Reduction, $ (year 1)',
            'Customer Export Credit, $ (year 1)',
            'NPV of Utility Ownership Cost, $',
            'NPV of Customer Ownership Cost, $',
            'NPV of Utility Monthly Income from Host Customer, $',
            'Payback Period',
            'NPV of bill savings Host Customer, $']

    output_df = pd.DataFrame(all_outputs, columns = cols)
    results = pd.concat([scenario, output_df], axis = 1)

    now = datetime.now() # current date and time
    date_time = now.strftime("%m%d%Y%H%M%S")
    results.to_csv(f'{date_time}.csv')



