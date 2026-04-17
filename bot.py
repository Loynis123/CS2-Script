import requests
import json
import time
import os
import sys

# ==========================================
# 1. ОСНОВНЫЕ НАСТРОЙКИ
# ==========================================
TELEGRAM_TOKEN = "8599966680:AAEvmeZh6Pzkmm47UVRnBRBZxa0nm9AYWvY"
TELEGRAM_CHAT_ID = "8146180029"

MIN_PRICE = 500       # Мин. цена (руб)
MAX_PRICE = 5000      # Макс. цена (руб)
DISCOUNT_PERCENT = 10 # Минимальный процент падения цены для сигнала
CHECK_INTERVAL = 3600 # Пауза между проверками (в секундах)

# ==========================================
# 2. НАСТРОЙКИ СЕТИ (ОБХОД БЛОКИРОВОК)
# ==========================================
# Если у тебя включен VPN на компьютере, оставь False.
# Если VPN нет и Telegram выдает таймаут, поставь True и найди бесплатный HTTPS прокси.
USE_PROXY = False
PROXIES = {
    "http": "http://188.132.221.32:8080",   # Пример: "http://188.132.221.32:8080"
    "https": "http://203.146.80.102:8080"
}

# ==========================================
# 3. ФУНКЦИИ БОТА
# ==========================================

def send_telegram_message(text):
    """Отправка сообщения с обработкой блокировок сети"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    
    try:
        if USE_PROXY:
            # Запрос через прокси сервер
            response = requests.get(url, params=params, proxies=PROXIES, timeout=20)
        else:
            # Обычный запрос
            response = requests.get(url, params=params, timeout=20)
            
        if response.status_code == 200:
            print("   [УСПЕХ] Уведомление доставлено в Telegram!")
            return True
        else:
            print(f"   [ОШИБКА] Telegram ответил кодом: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("   [КРИТИЧЕСКАЯ ОШИБКА] Таймаут. Провайдер блокирует Telegram.")
        print("   -> Включи VPN или настрой USE_PROXY = True.")
        return False
    except Exception as e:
        print(f"   [СБОЙ] Проблема с отправкой: {e}")
        return False

def get_steam_market_data():
    """Безопасный запрос к Торговой площадке Steam"""
    url = "https://steamcommunity.com/market/search/render/?query=&start=0&count=100&search_descriptions=0&sort_column=popular&sort_dir=desc&appid=730&norender=1&currency=5"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get('results', [])
        elif response.status_code == 429:
            print("   [ВНИМАНИЕ] Steam просит подождать (Слишком много запросов).")
        else:
            print(f"   [ОШИБКА] Steam недоступен. Код: {response.status_code}")
    except Exception as e:
        print(f"   [СЕТЬ] Ошибка подключения к Steam: {e}")
    return []

def analyze_and_save(item_name, current_price):
    """Сравнение цен и ведение локальной базы данных"""
    file_name = "db_prices.json"
    
    # Загружаем базу
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as file:
            try:
                history = json.load(file)
            except json.JSONDecodeError:
                history = {}
    else:
        history = {}

    # Обновляем историю предмета
    if item_name not in history:
        history[item_name] = []
    
    history[item_name].append(current_price)
    history[item_name] = history[item_name][-50:] # Храним только 50 цен

    # Сохраняем базу
    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

    # Ищем выгоду (если есть хотя бы 3 записи)
    if len(history[item_name]) >= 3:
        avg_price = sum(history[item_name][:-1]) / (len(history[item_name]) - 1)
        
        if current_price <= avg_price * (1 - DISCOUNT_PERCENT / 100):
            profit = current_price * 0.85 # Учет комиссии Steam 15%
            
            message = (
                f"🚨 *ПАДЕНИЕ ЦЕНЫ!*\n\n"
                f"🔫 Скин: `{item_name}`\n"
                f"💸 Цена сейчас: *{current_price} руб.*\n"
                f"📊 Средняя цена: *{round(avg_price, 2)} руб.*\n"
                f"📉 Скидка: *{round((1 - current_price/avg_price)*100, 1)}%*\n"
                f"💰 На баланс после комиссии: `{round(profit, 2)} руб.`"
            )
            return message
    return None

# ==========================================
# 4. ГЛАВНЫЙ ЦИКЛ ПРОГРАММЫ
# ==========================================

def start_bot():
    print("="*50)
    print("🤖 БОТ-АНАЛИТИК CS2 ЗАПУЩЕН")
    print("="*50)
    print("Проверка связи с Telegram...")
    
    if not send_telegram_message("✅ Скрипт запущен! Начинаю сбор данных."):
        print("\n❌ РАБОТА ОСТАНОВЛЕНА. Сначала реши проблему с блокировкой Telegram.")
        sys.exit()

    while True:
        print(f"\n[{time.strftime('%H:%M:%S')}] Запуск нового сканирования...")
        items = get_steam_market_data()
        
        if items:
            deals_found = 0
            for item in items:
                name = item['hash_name']
                price = int(item['sell_price']) / 100 # Копейки в рубли
                
                if MIN_PRICE <= price <= MAX_PRICE:
                    deal_message = analyze_and_save(name, price)
                    if deal_message:
                        print(f"   [!] Найдена сделка: {name}")
                        send_telegram_message(deal_message)
                        deals_found += 1
            
            print(f"[{time.strftime('%H:%M:%S')}] Сканирование завершено. Найдено аномалий: {deals_found}")
        
        print(f"💤 Пауза {CHECK_INTERVAL // 60} мин. Не закрывай консоль...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    start_bot()
