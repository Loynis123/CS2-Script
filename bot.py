import requests
import json
import time
import os

# ==================== НАСТРОЙКИ ====================
# Впиши свои данные сюда
TELEGRAM_TOKEN = "8599966680:AAEvmeZh6Pzkmm47UVRnBRBZxa0nm9AYWvY"
TELEGRAM_CHAT_ID = "8146180029"

# Параметры фильтрации
MIN_PRICE = 500       # Минимальная цена (руб)
MAX_PRICE = 5000      # Максимальная цена (руб)
DISCOUNT_PERCENT = 10 # Порог скидки в %
CURRENCY = 5          # 5 = Рубли (RUB)

# Файл базы данных (будет храниться в твоем репозитории)
HISTORY_FILE = "db_prices.json"
# ===================================================

def send_telegram_msg(text):
    """Отправляет уведомление в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"Не удалось отправить в Telegram: {e}")

def get_market_data():
    """Загружает данные со Steam (на русском языке)"""
    # Добавлен параметр &l=russian для получения названий на русском
    url = f"https://steamcommunity.com/market/search/render/?query=&start=0&count=100&search_descriptions=0&sort_column=popular&sort_dir=desc&appid=730&norender=1&currency={CURRENCY}&l=russian"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            print(f"Steam ответил кодом: {response.status_code}")
    except Exception as e:
        print(f"Ошибка сети при запросе к Steam: {e}")
    return []

def analyze_item(hash_name, russian_name, current_price, history):
    """Считает окупаемость и ищет выгоду"""
    if hash_name not in history:
        history[hash_name] = []
    
    history[hash_name].append(current_price)
    history[hash_name] = history[hash_name][-50:] # Ограничиваем историю

    # Если есть хотя бы 3 записи, можно считать среднюю
    if len(history[hash_name]) >= 3:
        # Средняя цена без учета текущей аномалии
        avg_price = sum(history[hash_name][:-1]) / (len(history[hash_name]) - 1)
        
        # Условие падения цены
        if current_price <= avg_price * (1 - DISCOUNT_PERCENT / 100):
            # Steam берет ~15% комиссии при продаже
            money_after_sale = avg_price * 0.85
            profit = money_after_sale - current_price
            
            # Если мы в плюсе даже после комиссии
            if profit > 0:
                roi = (profit / current_price) * 100
                
                msg = (
                    f"🔥 *ВЫГОДНОЕ ПРЕДЛОЖЕНИЕ*\n"
                    f"📦 *{russian_name}*\n\n"
                    f"💰 Цена сейчас: `{current_price} руб.`\n"
                    f"📊 Обычно стоит: `{round(avg_price, 2)} руб.`\n"
                    f"📉 Падение на: *{round((1 - current_price/avg_price)*100, 1)}%*\n\n"
                    f"💵 *Твой профит:* `{round(profit, 2)} руб.`\n"
                    f"📈 *Окупаемость (ROI):* `+{round(roi, 1)}%`"
                )
                return msg, history
    return None, history

def main():
    print("🚀 Запуск разовой проверки...")
    
    # Загружаем историю из файла
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except:
                history = {}
    else:
        history = {}

    items = get_market_data()
    if not items:
        print("❌ Данные от Steam не получены.")
        return

    deals_found = 0
    for item in items:
        h_name = item['hash_name']        # Для ключа в базе (англ)
        r_name = item.get('name', h_name) # Для сообщения (рус)
        price = int(item['sell_price']) / 100
        
        if MIN_PRICE <= price <= MAX_PRICE:
            msg, history = analyze_item(h_name, r_name, price, history)
            if msg:
                send_telegram_msg(msg)
                deals_found += 1

    # Сохраняем обновленную историю
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Проверка завершена. Найдено сделок: {deals_found}")

if __name__ == "__main__":
    main()
