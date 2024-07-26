# coding: utf-8
import numpy as np
import pandas as pd

import requests

import io
import os
import json
import yaml

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import sys
sys.path.append(current_dir)

# import gpt


metric_dct = {
                'temp_c': 'температура', 
                'feelslike_c': 'воспринимаемая температура',
                'windchill_c': 'температура ветра',
                'heatindex_c': 'воспринимаемый индекс',
                # 'condition': 'погода',
                'wind_kph': 'скорость ветра',
                # 'wind_dir': 'направление ветра',
                'pressure_hg': 'давление',
                'precip_mm': 'уровень осадков',
                'humidity': 'влажность',
                'cloud': 'облачность',
                # 'will_it_rain': 'будет ли дождь',
                # 'will_it_snow': 'будет ли снег',
                'chance_of_rain': 'вероятность дождя',
                'chance_of_snow': 'вероятность снега',
                'uv': 'УФ-индекс',
}

def read_yaml_config(yaml_file: str, section: str) -> dict:
    """
    Reading yaml settings
    """
    with open(yaml_file, 'r') as yaml_stream:
        descriptor = yaml.full_load(yaml_stream)
        if section in descriptor:
            configuration = descriptor[section]
            return configuration
        else:
            print(f"Section {section} not find in the file '{yaml_file}'")

def get_weth_data(api_key, base_url, method, location, days):
    """
    Getting data from API json-like
    """
    url = base_url + method
    params = {
    'key': api_key,  
    'q': location,
    'days': days,
            }
    
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print('Error:', response.status_code)
        print(response.text)   
        data = ''
    else:
        data = response.json()

    return data

def load_weth_data_to_df(data):
    """
    Data preparation
    """
    df = pd.DataFrame()
    mibar_cf = 0.750061683 
    columns = [
                'time', 
                'time_epoch',
                'is_day',
                'temp_c', 
                'feelslike_c',
                'windchill_c',
                'heatindex_c',
                'condition',
                'wind_kph',
                'wind_dir',
                'pressure_hg',
                'precip_mm',
                'humidity',
                'cloud',
                'will_it_rain', 'will_it_snow',
                'chance_of_rain', 'chance_of_snow',
                'uv', 
                ]
    for day in range(len(data['forecast']['forecastday'])):
        df_buf = pd.DataFrame(data['forecast']['forecastday'][day]['hour']) 
        df = pd.concat([df, df_buf])

    # df['utc_time'] = pd.to_datetime(row['date_epoch'], unit='s', utc=True)

    df['condition'] = df['condition'].apply(lambda x: x['text'])
    df['pressure_hg'] = df['pressure_mb'] * mibar_cf

    df['time'] = pd.to_datetime(df['time'])

    df = df[columns]

    df['place'] = data['location']['name']
    df['region'] = data['location']['region']
    df['country'] = data['location']['country']
    df['lat'] = data['location']['lat']
    df['lon'] = data['location']['lon']

    return df

def linear(x, k, b, c) -> float:
    """
    linear approximation
    """
    return k * x + b


def calc_trends(work_df, x, y):
    """
    Finding trends: increasing, decreasing, flat
    """
    from scipy.optimize import curve_fit
    popt, pcov = curve_fit(linear, work_df[x], work_df[y], 
                        # bounds=[0, np.inf],
                        method='trf',  #'lm', 'trf', 'dogbox'
                        )
    res = ''
    if popt[0] >= 0.05:
        res = 1 
    elif popt[0] <= -0.05:
        res = -1
    else:
        res = 0
    return res

def calc_metric(work_df, x, y):
    """
    Metric from dataframe to text
    """
    min = np.min(work_df[y])
    max = np.max(work_df[y])
    mean = np.round(np.mean(work_df[y]),0)
    trend = calc_trends(work_df, x, y)

    txt = ''

    if trend == 1:
        txt = "В ближайшее время " + metric_dct[y] + " составит " + str(mean) + ": вырастет с " + str(min) + " до " + str(max) + '\n'
    elif trend == -1:
        txt = "В ближайшее время " + metric_dct[y] + " составит " + str(mean) + ": уменьшится с " + str(max) + " до " + str(min) + '\n'
    else:
        txt = "В ближайшее время " + metric_dct[y] + " составит " + str(mean) + " и практически не изменится"  + '\n'

    return txt

def get_txt_for_forecast(df, forec_txt, hours=4):
    import datetime 
    from datetime import timedelta

    now = datetime.datetime.now() 
    now_round = now.replace(minute=0, second=0, microsecond=0)
    forecast_finish = now_round + timedelta(hours=hours) 

    work_df = df[
        (df['time'] >= now_round) &
        (df['time'] < forecast_finish)
                ]
    work_df['hour'] = work_df.index

    for metric in list(metric_dct.keys()):
        forec_txt = forec_txt + calc_metric(work_df, 'hour', metric)

    return forec_txt