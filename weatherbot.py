import logging
import requests
import json
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from apscheduler.schedulers.background import BackgroundScheduler

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Ваш API ключ OpenWeatherMap
OWM_API_KEY = 'ваш_ключ'
TOKEN = 'ваш_токен'

# Функция для старта бота
def start(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("Погода сейчас", callback_data="current_weather")],
        [InlineKeyboardButton("Почасовой прогноз", callback_data="hourly_forecast")],
        [InlineKeyboardButton("Недельный прогноз", callback_data="weekly_forecast")],
        [InlineKeyboardButton("Подписаться на уведомления", callback_data="subscribe")]
    ]
    update.message.reply_text("Добро пожаловать! Выберите опцию:", reply_markup=InlineKeyboardMarkup(buttons))

# Функция для получения почасового прогноза
def get_hourly_forecast(city: str):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OWM_API_KEY}&units=metric"
    response = requests.get(url)
    data = json.loads(response.text)
    forecast = ""
    for item in data['list'][:8]:  # 8 записей по 3 часа
        time = item['dt_txt'].split()[1][:5]
        temp = item['main']['temp']
        forecast += f"{time} → {temp}°C\n"
    return forecast

# Функция для получения недельного прогноза
def get_weekly_forecast(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude=hourly,minutely&appid={OWM_API_KEY}&units=metric"
    response = requests.get(url)
    data = json.loads(response.text)
    weekly_forecast = ""
    for day in data['daily']:
        date = datetime.fromtimestamp(day['dt']).strftime('%Y-%m-%d')
        temp = day['temp']['day']
        weekly_forecast += f"{date}: {temp}°C\n"
    return weekly_forecast

# Функция для генерации изображения с погодой
def generate_weather_image(city: str, data: dict) -> BytesIO:
    icon_code = data['weather'][0]['icon']
    icon_url = f"http://openweathermap.org/img/wn/{icon_code}@4x.png"
    icon_response = requests.get(icon_url)
    weather_icon = Image.open(BytesIO(icon_response.content))

    img = Image.new('RGB', (800, 600), color=(73, 109, 137))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 40)

    draw.text((50, 50), f"Погода в {city}", font=font, fill=(255, 255, 255))
    img.paste(weather_icon, (50, 150), weather_icon)

    details = (
        f"Температура: {data['main']['temp']}°C\n"
        f"Ощущается как: {data['main']['feels_like']}°C\n"
        f"Влажность: {data['main']['humidity']}%\n"
        f"Ветер: {data['wind']['speed']} м/с"
    )
    draw.multiline_text((300, 150), details, font=font, fill=(255, 255, 255), spacing=20)

    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer

# Функция для получения UV-индекса
def get_uv_index(lat, lon):
    uv_url = f"http://api.openweathermap.org/data/2.5/uvi?lat={lat}&lon={lon}&appid={OWM_API_KEY}"
    response = requests.get(uv_url)
    data = json.loads(response.text)
    return data['value']

# Функция для отправки уведомлений
def send_daily_notifications(context: CallbackContext):
 # Логика отправки уведомлений пользователям
    users = get_subscribed_users()  # Получите список подписанных пользователей
    for user_id in users:
        context.bot.send_message(chat_id=user_id, text="Не забудьте проверить прогноз погоды на сегодня!")

# Функция для обработки нажатий кнопок
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "current_weather":
        city = "Москва"  # Замените на логику выбора города
        weather_data = get_weather_data(city)  # Получите данные о погоде
        image = generate_weather_image(city, weather_data)
        context.bot.send_photo(chat_id=query.message.chat_id, photo=image)
    elif query.data == "hourly_forecast":
        city = "Москва"  # Замените на логику выбора города
        forecast = get_hourly_forecast(city)
        query.edit_message_text(text=f"Почасовой прогноз:\n{forecast}")
    elif query.data == "weekly_forecast":
        lat, lon = 55.7558, 37.6173  # Замените на логику получения координат
        forecast = get_weekly_forecast(lat, lon)
        query.edit_message_text(text=f"Недельный прогноз:\n{forecast}")
    elif query.data == "subscribe":
        subscribe_user(query.message.chat_id)
        query.edit_message_text(text="Вы подписались на ежедневные уведомления!")

# Функция для получения данных о погоде
def get_weather_data(city: str):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OWM_API_KEY}&units=metric"
    response = requests.get(url)
    return json.loads(response.text)

# Функция для подписки пользователя на уведомления
def subscribe_user(user_id):
    # Логика сохранения user_id в БД
    pass

# Основная функция
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Запуск планировщика
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_notifications, 'cron', hour=8)
    scheduler.start()

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
