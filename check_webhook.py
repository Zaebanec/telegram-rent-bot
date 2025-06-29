import requests
import os
from dotenv import load_dotenv

# Загружаем переменные из вашего .env файла
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Ошибка: Не удалось найти BOT_TOKEN в .env файле.")
    exit()

# Формируем URL для запроса информации о вебхуке
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"

try:
    # Отправляем запрос
    response = requests.get(url)
    response.raise_for_status()  # Проверяем, что ответ успешный (статус 2xx)
    
    # Печатаем результат в красивом виде
    data = response.json()
    print("="*50)
    print("ИНФОРМАЦИЯ О ВЕБХУКЕ:")
    print("="*50)
    if data.get("ok"):
        result = data.get("result", {})
        print(f"URL вебхука: {result.get('url', 'Не установлен')}")
        print(f"Ожидает обновлений: {result.get('pending_update_count', 0)}")
        if result.get('last_error_date'):
            import datetime
            error_time = datetime.datetime.fromtimestamp(result['last_error_date']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"!!! ПОСЛЕДНЯЯ ОШИБКА ДОСТАВКИ: {error_time}")
            print(f"!!! СООБЩЕНИЕ ОБ ОШИБКЕ: {result.get('last_error_message', 'Нет сообщения')}")
        else:
            print("Последних ошибок доставки нет.")
    else:
        print("Не удалось получить информацию. Ответ от API:")
        print(data)
    print("="*50)

except requests.exceptions.RequestException as e:
    print(f"Ошибка сети при запросе к Telegram API: {e}")