import numpy
import pandas as pd

def MACRS_Schedule(years):
    if years == 5:
        return [0.2000, 0.3200, 0.1920, 0.1152, 0.1152, 0.0576]
    if years == 7:
        return [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446]
    if years != 5 or years != 7:
        raise ValueError('input argument can only be 5 or 7')

def calculate_PV_prod_annual_timeseries(y1_PV_prod_scenario, Analysis_period,
                                        PV_degradation_rate):
    PV_production = []
    for i in range(0, Analysis_period):
        prod = y1_PV_prod_scenario * ((1-PV_degradation_rate/100)**i)
        PV_production.append(prod)
    return PV_production


def calculate_annual_cashflow(amount, Analysis_period, escalation_rate):
    cashflow = []
    for i in range(1, Analysis_period+1):
        bill = -amount * ((1+escalation_rate/100)**i)
        cashflow.append(bill)
    return cashflow


def calculate_PV_OM_cashflow_series(amount, escalation_rate, PV_kw, Analysis_period):
    cashflow = []
    for i in range(1, Analysis_period+1):
        cost = -amount * ((1+escalation_rate/100)**i) * PV_kw
        cashflow.append(cost)
    return cashflow


def calculate_bess_replace_cashflow_series(year, cost_per_kw, BESS_power_kw, Analysis_period):
    cashflow = []
    for i in range(1, Analysis_period+1):
        if i == year:
            cost = - (cost_per_kw * BESS_power_kw)
            cashflow.append(cost)
        else:
            cashflow.append(0*-1)
    return cashflow

def payback_period(cum_cashflow):
    array = numpy.array(cum_cashflow)
    if array[len(array)-1] > 0:
        final_full_year = list(array).index(max(array[array < 0]))
        fractional_yr = array[final_full_year] / \
            (array[final_full_year]-array[final_full_year + 1])
        period = final_full_year + fractional_yr
        return period
    else:
        return '>10'


def calculate_utility_avoided_energy_cost(bau_load, net_load_profile):
    lmp = pd.read_csv('all_dispatch - lmp.csv').iloc[:,1].to_list()
    lmp = [a/1000 for a in lmp ]

    bau_cost = [a*b for a, b in zip(lmp,list(bau_load))]
    optimal_cost =[a*b for a, b in zip(lmp,list(net_load_profile))]
    return sum(bau_cost)-sum(optimal_cost)

def calculate_utility_avoided_td_cost(df):
    status_during_grid_peak = list(df[df['Start Datetime (hb)']=='8/19/2022 15:00'].values.flatten())[1:] 
    reduction = status_during_grid_peak[0]+(status_during_grid_peak[1]-status_during_grid_peak[2])+status_during_grid_peak[3]
    return 71*reduction 


def calculate_bill(hourly_profile_annual, rate_class):
    df = hourly_profile_annual
    df['Time Stamp'] = pd.to_datetime(df.iloc[:,0] )
    df['Total Load (kW)'] = df.iloc[:,1]
    df['month'] = df['Time Stamp'].dt.month
    df['day_of_month'] = df['Time Stamp'].dt.day
    df['day_of_week']= df['Time Stamp'].dt.dayofweek
    df['hour_of_day'] = df['Time Stamp'].dt.hour
    tariff = pd.read_csv('evergy_tou_tariff.csv', converters={'Day':str}) 

    if rate_class == 'time_of_use':
        monthly_bills = []
        for i in df.month.unique():

            temp = pd.DataFrame(df[df.month==i],
                                columns = ['day_of_month',
                                           'day_of_week',
                                           'hour_of_day',
                                           'Total Load (kW)'])
            temp = temp.pivot(index= ['day_of_month','day_of_week'],
                              columns = 'hour_of_day',
                              values = 'Total Load (kW)' )
            temp = temp.reset_index()

            daily_bills = []
            for j in temp.day_of_month.unique():
     
                load = temp[temp.day_of_month ==j]
                if load.day_of_week.values[0] <= 4:
                    price = tariff[(tariff.Day =='Weekday') &(tariff.Month == i)].iloc[:,2:].values[0].tolist()
                if load.day_of_week.values[0] > 4:
                    price = tariff[(tariff.Day =='Weekend') &(tariff.Month == i)].iloc[:,2:].values[0].tolist()
              
                price = [float(x) for x in price]
                hourly_kw = load.iloc[:,2:].values[0].tolist()
                hourly_kw = [float(x) for x in hourly_kw]
                

                bill = [a*b for a,b in zip(hourly_kw,price)]
                
                daily_bills.append(sum(bill))
                monthly_bill = sum(daily_bills)
            monthly_bills.append(monthly_bill)


    if rate_class == 'general_service':
        df = hourly_profile_annual
        kwh_consumption_per_month = df.groupby(['month']).sum().iloc[:,0:1].reset_index()
        monthly_bills = []
        for i in range(0,12):
            kwh = kwh_consumption_per_month.iloc[i,1]
            if (i>=1 & i <=5) or (i>=10 & i<=12): # winter months
                if (kwh <= 600):
                    bill = kwh * 0.0986
                if ((kwh > 600) and (kwh <= 1000)):
                    bill = 600*0.0986 + (kwh-600)*0.0755
                if (kwh > 1000):
                    bill = 600*0.0986+400*0.0755+(kwh-1000)*0.070629

            if (i>5 and i <10):#summer months
                if (kwh <= 600):
                    bill = kwh * 0.1056
                if ((kwh > 600) and (kwh <= 1000)):
                    bill = 600*0.1056 + (kwh-600)*0.1121
                if (kwh > 1000):
                    bill = 600*0.1056+400*0.1121+(kwh-1000)*0.1193657
            monthly_bills.append(bill)

    if rate_class == 'net_metering':
        df = hourly_profile_annual
        kwh_consumption_per_month = df.groupby(['month']).sum().iloc[:,0:1].reset_index()
        monthly_bills = []
        for i in range(0,12):
            kwh = kwh_consumption_per_month.iloc[i,1]
            if (i>=1 & i <=5) or (i>=10 & i<=12): # winter months
                if (kwh <= 500):
                    bill = kwh * 0.07313
                if ((kwh > 500) and (kwh <= 900)):
                    bill = 500*0.07313 + (kwh-500)*0.07313
                if (kwh > 900):
                    bill = 500*0.0986+400*0.07313+(kwh-900)*0.059777

            if (i>5 and i <10):#summer months
                if (kwh <= 500):
                    bill = kwh * 0.07313
                if ((kwh > 500) and (kwh <= 900)):
                    bill = 500*0.07313 + (kwh-500)*0.07313
                if (kwh > 900):
                    bill = 500*0.1056+400*0.1121+(kwh-900)*0.080667
            monthly_bills.append(bill)

    return sum(monthly_bills)+(14.25*12) # 14.24 is fixed monthly charge


def calculate_export_credit(hourly_profile_annual, rate_class):
    df = hourly_profile_annual
    df['Time Stamp'] = pd.to_datetime(df.iloc[:,0] )
    df['Total Load (kW)'] = df.iloc[:,1]
    df['month'] = df['Time Stamp'].dt.month
    df['day_of_month'] = df['Time Stamp'].dt.day
    df['day_of_week']= df['Time Stamp'].dt.dayofweek
    df['hour_of_day'] = df['Time Stamp'].dt.hour
    #print(df)
    tariff = pd.read_csv('evergy_tou_tariff.csv', converters={'Day':str}) # reminder: tou tariff

    if rate_class == 'time_of_use':
        monthly_bills = []
        for i in df.month.unique():
  
            temp = pd.DataFrame(df[df.month==i],
                                columns = ['day_of_month',
                                           'day_of_week',
                                           'hour_of_day',
                                           'Total Load (kW)'])
            temp = temp.pivot(index= ['day_of_month','day_of_week'],
                              columns = 'hour_of_day',
                              values = 'Total Load (kW)' )
            temp = temp.reset_index()

            daily_bills = []
            for j in temp.day_of_month.unique():
                
                load = temp[temp.day_of_month ==j]
                if load.day_of_week.values[0] <= 4:
                    price = tariff[(tariff.Day =='Weekday') &(tariff.Month == i)].iloc[:,2:].values[0].tolist()
                if load.day_of_week.values[0] > 4:
                    price = tariff[(tariff.Day =='Weekend') &(tariff.Month == i)].iloc[:,2:].values[0].tolist()
                
                price = [float(x) for x in price]
                hourly_kw = load.iloc[:,2:].values[0].tolist()
                hourly_kw = [float(x) for x in hourly_kw]
                

                bill = [a*b for a,b in zip(hourly_kw,price)]
                
                daily_bills.append(sum(bill))
                monthly_bill = sum(daily_bills)
            monthly_bills.append(monthly_bill)


    if rate_class == 'general_service':
        df = hourly_profile_annual
        kwh_consumption_per_month = df.groupby(['month']).sum().iloc[:,0:1].reset_index()
        monthly_bills = []
        for i in range(0,12):
            kwh = kwh_consumption_per_month.iloc[i,1]
            if (i>=1 & i <=5) or (i>=10 & i<=12): # winter months
                if (kwh <= 600):
                    bill = kwh * 0.0986
                if ((kwh > 600) and (kwh <= 1000)):
                    bill = 600*0.0986 + (kwh-600)*0.0755
                if (kwh > 1000):
                    bill = 600*0.0986+400*0.0755+(kwh-1000)*0.070629

            if (i>5 and i <10):#summer months
                if (kwh <= 600):
                    bill = kwh * 0.1056
                if ((kwh > 600) and (kwh <= 1000)):
                    bill = 600*0.1056 + (kwh-600)*0.1121
                if (kwh > 1000):
                    bill = 600*0.1056+400*0.1121+(kwh-1000)*0.1193657
            monthly_bills.append(bill)

    if rate_class == 'net_metering':
        df = hourly_profile_annual
        kwh_consumption_per_month = df.groupby(['month']).sum().iloc[:,0:1].reset_index()
        monthly_bills = []
        for i in range(0,12):
            kwh = kwh_consumption_per_month.iloc[i,1]
            if (i>=1 & i <=5) or (i>=10 & i<=12): # winter months
                if (kwh <= 500):
                    bill = kwh * 0.07313
                if ((kwh > 500) and (kwh <= 900)):
                    bill = 500*0.07313 + (kwh-500)*0.07313
                if (kwh > 900):
                    bill = 500*0.0986+400*0.07313+(kwh-900)*0.059777

            if (i>5 and i <10):#summer months
                if (kwh <= 500):
                    bill = kwh * 0.07313
                if ((kwh > 500) and (kwh <= 900)):
                    bill = 500*0.07313 + (kwh-500)*0.07313
                if (kwh > 900):
                    bill = 500*0.1056+400*0.1121+(kwh-900)*0.080667
            monthly_bills.append(bill)

    return sum(monthly_bills)