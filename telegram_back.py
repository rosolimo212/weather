# coding: utf-8
import numpy as np
import pandas as pd

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

import os
current_dir = os.path.abspath(os.getcwd())
parent_dir = os.path.dirname(current_dir)

import sys
sys.path.append(current_dir)

import weth_api as wa
import data_load as dl
import gpt

# getting credles
forecast_settings = dl.read_yaml_config('config.yaml', section='api.weatherapi.com')
base_url = forecast_settings['url']
method = forecast_settings['method']
forecast_api_key = forecast_settings['api_key']

gpt_settings = dl.read_yaml_config('config.yaml', section='gpt')
gpt_api_key = gpt_settings['API_KEY']
gpt_catalog_id = gpt_settings['CATALOG_ID']

telegram_settings = dl.read_yaml_config('config.yaml', section='telgram_test_bot')
telegram_api_token = telegram_settings['token']
admin_chat_id = 249792088

postres_settings = dl.read_yaml_config('config.yaml', section='logging')


def make_event_log(message, event_name, params):
    user = message.from_user.username
    user_id = message.from_user.id

    import datetime
    now = datetime.datetime.now()

    log_lst = [now, user_id, user, event_name, params]
    log_df = pd.DataFrame([log_lst])
    log_df.columns = ['event_time', 'user_id', 'user_name', 'event_name', 'parameters']
    print(log_df)
    # dl.insert_data(log_df, 'tl', 'events')


hello_message = """Привет! Этот бот поможет тебе одеться по погоде! 
Для начала, пожалуйста, введи или выбери название твоего города
Можно напечатать название города вручную или отправить геопозицию
"""
check_message = """Мы получили локацию. Ближайшая доступная метеостанция находится в локакции {city} """
option_message = """Доступные сейчас для локации {city} опции:
"""
finish_message = """'ОК' возвращает вас в главное меню
"""
error_message = """К сожалению, в данный момент мы не может забрать прогноз по указанному вами городу, попробуйте ввести как-то по-другому"""
get_weather_message = """Прогноз погоды на ближайшие часы для локации {city} найден!
"""
get_gpt_message = """
Рекомендации из прогноза формулируются, это должно занять пару секунд
"""

# about buttons
def make_answer_buttons(buttons_lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_lst:
        item = types.KeyboardButton(button)
        markup.add(item)
    
    return markup 

# Определяем состояния
class Form(StatesGroup):
    waiting_for_city = State()  # Ожидание ввода города
    waiting_for_option = State()  # Ожидание выбора опции в главном меню

# Инициализация бота и диспетчера
 # Замените на ваш токен
bot = Bot(token=telegram_api_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    markup = make_answer_buttons([
        'Москва',
        'Санкт-Петербург',
                            ])
    markup.add(types.KeyboardButton("Отправить геопозицию 📍", request_location=True))
    await state.finish()  
    await state.set_state(Form.waiting_for_city) 
    await message.answer(hello_message, reply_markup=markup)

@dp.message_handler(content_types=['text', 'location'], state=Form.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    # если геопозиция непустая, то записываем её
    if message.location is not None:
        city = str(message.location.latitude) + ', ' + str(message.location.longitude)
    # иначе - берём тест из сообщения пользователя
    else:   
        city = message.text  # Получаем город от пользователя
    
    await state.update_data(city=city)  # Запоминаем город в состоянии
    make_event_log(message, event_name='city_select', params={'city': city, 'state': 'main'})

    gwd = wa.get_weth_data(forecast_api_key, base_url, method, city, 2)
    if gwd != '':
        await state.update_data(gwd=gwd)
        await show_main_menu(message, state)
    else:
        markup = make_answer_buttons([
        'Москва',
        'Санкт-Петербург'
                            ])
        await message.answer(error_message, reply_markup=markup)


@dp.message_handler(state=Form.waiting_for_option)
async def process_option(message: types.Message, state: FSMContext):
    user_data = await state.get_data()  # Получаем данные пользователя
    city = user_data.get("city")  # Извлекаем город
    gwd = user_data.get("gwd")

    markup = make_answer_buttons([
    'Что надеть по погоде прямо сейчас?',
    'Какая сейчас температура?',
    'Дождь будет?',
                        ])
    make_event_log(message, event_name='main_menu_load', params={'state': 'main'})

    if message.text.lower() == 'Что надеть по погоде прямо сейчас?'.lower():
        make_event_log(message, event_name='option_select', params={'option': 1, 'state': 'main'})
        result = await general_process(gwd, message)
    elif message.text.lower() == 'Какая сейчас температура?'.lower():
        make_event_log(message, event_name='option_select', params={'option': 2, 'state': 'main'})
        result = await direct_process(gwd, message)
    elif message.text.lower() == 'Дождь будет?'.lower():
        make_event_log(message, event_name='option_select', params={'option': 3, 'state': 'main'})
        result = await indirect_process(gwd, message)
    else:
        await message.answer(option_message.format(city=gwd['location']['name']), reply_markup=markup)
        return

    markup = make_answer_buttons([
    'Ok',
                        ])
    await message.answer(result)  # Отправляем результат пользователю
    await message.answer(finish_message, reply_markup=markup)
    await state.set_state(Form.waiting_for_option)  # Сохраняем состояние ожидания опции

@dp.message_handler(lambda message: message.text.lower() == "Ok", state=Form.waiting_for_option)
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await show_main_menu(message, state)

async def show_main_menu(message: types.Message, state: FSMContext):
    user_data = await state.get_data()  # Получаем данные пользователя
    city = user_data.get("city")
    gwd = user_data.get("gwd")
    await message.answer(check_message.format(city=gwd['location']['name']))
    markup = make_answer_buttons([
    'Что надеть по погоде прямо сейчас?',
    'Какая сейчас температура?',
    'Дождь будет?',
                        ])
    await message.answer(option_message.format(city=gwd['location']['name']), reply_markup=markup)
    await state.set_state(Form.waiting_for_option)  # Устанавливаем состояние ожидания опции

async def general_process(gwd, message):
    df = wa.load_weth_data_to_df(gwd)
    await message.answer(get_weather_message.format(city=df['place'].values[0]))
    forec_message = wa.get_txt_for_forecast(df)
    await message.answer(get_gpt_message)
    gpt_answer = gpt.send_message(API_KEY=gpt_api_key, CATALOG_ID=gpt_catalog_id, text=forec_message)
    make_event_log(message, event_name='back_response', params={'response': gpt_answer, type: 'gpt', 'state': 'main'})

    return gpt_answer

async def direct_process(gwd, message):
    df = wa.load_weth_data_to_df(gwd)
    forec_message = wa.get_txt_for_forecast(df, metrics=[0,1], is_templ=0)
    make_event_log(message, event_name='back_response', params={'response': forec_message, type: 'forecast', 'state': 'main'})

    return forec_message

async def indirect_process(gwd, message):
    df = wa.load_weth_data_to_df(gwd)
    forec_message = wa.get_txt_for_forecast(df, metrics=[9], is_templ=0)
    make_event_log(message, event_name='back_response', params={'response': forec_message, type: 'forecast', 'state': 'main'})

    return forec_message

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
