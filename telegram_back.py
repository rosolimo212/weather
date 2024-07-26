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
import gpt

# getting credles
forecast_settings = wa.read_yaml_config('config.yaml', section='api.weatherapi.com')
base_url = forecast_settings['url']
method = forecast_settings['method']
forecast_api_key = forecast_settings['api_key']

gpt_settings = wa.read_yaml_config('config.yaml', section='gpt')
gpt_api_key = gpt_settings['api_key']

telegram_settings = wa.read_yaml_config('config.yaml', section='telgram_test_bot')
admin_chat_id = 249792088

# about buttons
def make_answer_buttons(buttons_lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_lst:
        item = types.KeyboardButton(button)
        markup.add(item)
    
    return markup 

# main logic
class Form(StatesGroup):
    waiting_for_city = State()  
    waiting_for_option = State() 


bot = Bot(token=telegram_settings['token']) 
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    markup = make_answer_buttons([
         'Москва',
         'Тбилиси'
                                ])
    await Form.waiting_for_city.set()
    await message.answer("Этот бот можете тебе с погодой! Для начала, пожалуйста, введи или выбери название твоего города.", reply_markup=markup)
    

@dp.message_handler(state=Form.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    city = message.text
    await state.update_data(city=city) 
    markup = make_answer_buttons([
         'Что надеть по погоде прямо сейчас?',
         'Какая сейчас температура',
         'Дождь будет?'
                                ])
    await message.answer(f"Вы выбрали город: {city}. Основные опции перед вами", reply_markup=markup)
    await Form.waiting_for_option.set() 

@dp.message_handler(state=Form.waiting_for_option)
async def process_option(message: types.Message, state: FSMContext):
    user_data = await state.get_data()  
    city = user_data.get("city") 

    if message.text == "Что надеть по погоде прямо сейчас?":
        # await message.answer(f"Запускаем общий процесс для города {city}...")
        
        await general_process(message, city)
    elif message.text == "2":
        await message.answer(f"Запускаем прямой процесс для города {city}...")
        
        await direct_process(city)
    elif message.text == "3":
        await message.answer(f"Запускаем косвенный процесс для города {city}...")
        
        await indirect_process(city)
    else:
        await message.answer("""К сожалению, что-то пошло не так: такой команды нет.
Возможно, произошла ошибка в самой игре. 
Возможно, вы использовали неожиданную текстовую команду.
Возвращайтесь в главное меню и попробуйте снова.
Если проблема повторяется, нажмите /start""")


    await state.finish()  # Завершаем состояние после обработки выбора

async def general_process(message, city):
    # Логика общего процесса
    await bot.send_message(admin_chat_id, f"Запущен общий процесс для города {city}.")
    gwd = wa.get_weth_data(forecast_api_key, base_url, method, '55.752539, 37.808001', 7)
    df = wa.load_weth_data_to_df(gwd)
    forec_txt = """
    Дай, пожалуйста, пару рекомендаций как одеться семье по погоде.
    Я пришлю тебе показатели прогноза, а ты кратко расскажешь, как лучше одеться:
    сначала рекомендации для взрослых,
    потом - рекомендации ребёнку 3-5 лет, если они отличаются от рекомендации для взрослых
    Обобщать и писать про всякие закономерности не нужно, только рекомендации кратко и по делу, каждая рекомендация в отдельном абзаце
    По прогнозу погоды в моей местности ожидаются следующие показатели: \n
    """
    msg = wa.get_txt_for_forecast(df, forec_txt)
    answ = gpt.send_message(gpt_api_key, msg, model='gpt-4o-mini')
    # await bot.send_message(admin_chat_id, f"Запущен общий процесс для города {city}.")
    await message.answer(answ)


async def direct_process(city):
    # Логика прямого процесса
    await bot.send_message(admin_chat_id, f"Запущен прямой процесс для города {city}.")  # Замените на ваш ID чата

async def indirect_process(city):
    # Логика косвенного процесса
    await bot.send_message(admin_chat_id, f"Запущен косвенный процесс для города {city}.")  # Замените на ваш ID чата

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
