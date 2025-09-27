from locale import strcoll
import requests

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import sys
sys.path.append(current_dir)

import weth_api as wa
import data_load as dl

# settings = dl.read_yaml_config('config.yaml', section='gpt')
# api_key = settings['api_key']
# catalog_id = settings['catalog_id']

def send_message(
    text: str,
    API_KEY: str,
    CATALOG_ID: str,
    role: str = "user",
    temperature: float = 0.4,
    max_tokens: int = 8000,
):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "x-folder-id": CATALOG_ID,
        "Content-Type": "application/json"
    }

    data = {
        "modelUri": f"gpt://{CATALOG_ID}/yandexgpt-lite",
        "messages": [
            {"role": role, "text": text}
        ],
        "temperature": temperature,
        "maxTokens": max_tokens
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        answer = response.json()['result']['alternatives'][0]['message']['text']

    except Exception as e:
        print("🚫 Status code:", response.status_code)
        print(str(e))
        answer = "YandexGPT не отвечает"

    return answer