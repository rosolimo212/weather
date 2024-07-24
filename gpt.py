import requests

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import sys
sys.path.append(current_dir)

import weth_api as wa

settings = wa.read_yaml_config('config.yaml', section='gpt')
api_key = settings['api_key']

def send_message(api_key, message, model='gpt-4o-mini'):
    """
    Send message to opeanai model and get the text of its response
    """
    url = 'https://api.openai.com/v1/chat/completions'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    data = {
        'model': model,
        'messages': [
            {'role': 'user', 'content': message}
        ],
    }

    response = requests.post(url, headers=headers, json=data)    

    res = ''

    if response.status_code == 200:
        res = response.json()['choices'][0]['message']['content']
    else:
        print('Error:', response.status_code)
        print(response.text)   

    return res