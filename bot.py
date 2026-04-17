import requests
import json
import time
import os

# ==================== НАСТРОЙКИ ====================
TELEGRAM_TOKEN = "8599966680:AAEvmeZh6Pzkmm47UVRnBRBZxa0nm9AYWvY"
TELEGRAM_CHAT_ID = "8146180029"

MIN_PRICE = 100       # Снизил порог, чтобы точно поймать данные
MAX_PRICE = 10000      
DISCOUNT_PERCENT = 10 
CURRENCY = 5          
HISTORY_FILE = "db_prices.json"
# ===================================================

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.get(url, params=params, timeout=15)
    except:
        pass

def main():
    print("🚀 Старт проверки...")
    
    # Загружаем историю
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = {}

    # Запрос к Steam
    url = f"https://steamcommunity.com/market/search/render/?query=&start=0&count=100&search_descriptions=0&sort_column=popular&sort_dir=desc&appid=730&norender=1&currency={CURRENCY}&l=russian"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        items = response.json().get('results', [])
    except Exception as e:
        print(f"❌ Ошибка Steam: {e}")
        return

    if not items:
        print("❌ Steam не вернул список предметов. Возможно, временный бан по IP.")
        return

    print(f"📦 Получено предметов: {len(items)}")
    
    found_deals = 0
    for item in items:
        h_name = item['hash_name']
        r_name = item.get('name', h_name)
        # У Steam цена в копейках (целое число)
        raw_price = item.get('sell_price')
        if not raw_price: continue
        
        price = int(raw_price) / 100
        
        # Печатаем в логи для отладки
        print(f"Проверка: {r_name} - {price} руб.")

        if MIN_PRICE <= price <= MAX_PRICE:
            if h_name not in history:
                history[h_name] = []
            
            # Анализ (если есть история)
            if len(history[h_name]) >= 3:
                avg_price = sum(history[h_name]) / len(history[h_name])
                if price <= avg_price * (1 - DISCOUNT_PERCENT / 100):
                    money_after_tax = avg_price * 0.85
                    profit = money_after_tax - price
                    if profit > 0:
                        roi = (profit / price) * 100
                        msg = f"🔥 *ВЫГОДА!* \n📦 {r_name}\n💰 Цена: {price}\n📉 Скидка: {round((1-price/avg_price)*100)}%\n📈 Профит: {round(profit)}р"
                        send_telegram_msg(msg)
                        found_deals = 1

            history[h_name].append(price)
            history[h_name] = history[h_name][-50:]

    # Сохраняем файл
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Данные сохранены в {HISTORY_FILE}. Сделок найдено: {found_deals}")
    send_telegram_msg("🤖 Проверка завершена, база данных обновлена.")

if __name__ == "__main__":
    main()
