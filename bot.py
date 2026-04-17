import requests
import json
import time
import os

# ==================== НАСТРОЙКИ ====================
TELEGRAM_TOKEN = "8599966680:AAEvmeZh6Pzkmm47UVRnBRBZxa0nm9AYWvY"
TELEGRAM_CHAT_ID = "8146180029"

MIN_PRICE = 500       
MAX_PRICE = 5000      
DISCOUNT_PERCENT = 10 
CURRENCY = 5          
HISTORY_FILE = "db_prices.json"
# ===================================================

def send_telegram_msg(text):
    """Отправляет уведомление в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            print("--- Сообщение успешно отправлено в Telegram ---")
        else:
            print(f"--- Ошибка Telegram: {response.status_code} ({response.text}) ---")
    except Exception as e:
        print(f"--- Ошибка сети при отправке в Telegram: {e} ---")

def get_market_data():
    """Загружает данные со Steam (на русском языке)"""
    url = f"https://steamcommunity.com/market/search/render/?query=&start=0&count=100&search_descriptions=0&sort_column=popular&sort_dir=desc&appid=730&norender=1&currency={CURRENCY}&l=russian"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json().get('results', [])
            print(f"Успешно получено {len(data)} предметов от Steam")
            return data
        else:
            print(f"Steam ответил ошибкой: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при связи со Steam: {e}")
    return []

def main():
    print(f"🚀 Запуск скрипта в {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ТЕСТОВЫЙ СИГНАЛ: Бот напишет тебе, что он жив
    # (Потом эту строчку можно будет удалить, чтобы не спамить каждый час)
    send_telegram_msg("🔄 GitHub Action запустил проверку рынка...")

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
        return

    deals_found = 0
    checked_count = 0

    for item in items:
        h_name = item['hash_name']        
        r_name = item.get('name', h_name) 
        price = int(item['sell_price']) / 100
        
        if MIN_PRICE <= price <= MAX_PRICE:
            checked_count += 1
            
            if h_name not in history:
                history[h_name] = []
            
            # Логика анализа
            if len(history[h_name]) >= 3:
                avg_price = sum(history[h_name]) / len(history[h_name])
                
                if price <= avg_price * (1 - DISCOUNT_PERCENT / 100):
                    money_after_sale = avg_price * 0.85
                    profit = money_after_sale - price
                    
                    if profit > 0:
                        roi = (profit / price) * 100
                        msg = (
                            f"🔥 *ВЫГОДНОЕ ПРЕДЛОЖЕНИЕ*\n"
                            f"📦 *{r_name}*\n\n"
                            f"💰 Цена сейчас: `{price} руб.`\n"
                            f"📊 Обычно стоит: `{round(avg_price, 2)} руб.`\n"
                            f"📉 Падение на: *{round((1 - price/avg_price)*100, 1)}%*\n\n"
                            f"💵 *Твой профит:* `{round(profit, 2)} руб.`\n"
                            f"📈 *ROI:* `+{round(roi, 1)}%`"
                        )
                        send_telegram_msg(msg)
                        deals_found += 1
            
            # Добавляем цену в историю ПОСЛЕ анализа
            history[h_name].append(price)
            history[h_name] = history[h_name][-50:]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
        
    print(f"✅ Проверено подходящих скинов: {checked_count}")
    print(f"✅ Найдено выгодных сделок: {deals_found}")

if __name__ == "__main__":
    main()
