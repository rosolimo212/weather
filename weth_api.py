# coding: utf-8
import numpy as np
import pandas as pd

import requests

import io
import os
import json
import yaml

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

    df['condition'] = df['condition'].apply(lambda x: x['text'])
    df['pressure_hg'] = df['pressure_mb'] * mibar_cf

    df = df[columns]

    df['place'] = data['location']['name']
    df['region'] = data['location']['region']
    df['country'] = data['location']['country']
    df['lat'] = data['location']['lat']
    df['lon'] = data['location']['lon']

    return df