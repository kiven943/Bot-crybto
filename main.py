import time
import requests
import pandas as pd

# -------------------------------------------------------------
# بيانات البوت وتليغرام الخاصة بك
# -------------------------------------------------------------
TELEGRAM_TOKEN = "8630854974:AAHWPeRpHIw7SdzoiGjEh1Qub3eQ5puXrcE"
CHAT_ID = "2107579721"

# تتبع العملات التي تم إرسال تنبيه لها لتجنب تكرار الإزعاج لنفس المستوى
alerted_levels = {}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"خطأ أثناء إرسال الرسالة: {e}")

def get_usd_symbols():
    try:
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url).json()
        usd_symbols = []
        for symbol_info in response['symbols']:
            symbol = symbol_info['symbol']
            if symbol.endswith("USD") or symbol.endswith("USDT"):
                usd_symbols.append(symbol)
        return usd_symbols[:40] # جلب عينة قوية من العملات
    except Exception as e:
        print(f"خطأ في جلب قائمة العملات: {e}")
        return ["BTCUSD", "ETHUSD", "SOLUSD", "PEPEUSDT"]

# جلب بيانات فريم يومي لتحديد مستوى النمط
def get_daily_key_level(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=10"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['open'] = df['open'].astype(float)
    df['close'] = df['close'].astype(float)
    df['body_size'] = (df['close'] - df['open']).abs()
    
    if len(df) < 5:
        return None
        
    c1, c2, c3 = df.iloc[-4], df.iloc[-3], df.iloc[-2]
    avg_body = df['body_size'].mean()
    
    # شروط الزخم اليومي
    is_large = (c1['body_size'] > avg_body * 0.8) and (c2['body_size'] > avg_body * 0.8)
    
    # صاعد ثم شمعة حمراء
    if c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] < c3['open'] and is_large:
        return {"type": "BULLISH_REVERSAL", "level": c3['open']}
        
    # هابط ثم شمعة خضراء
    if c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] > c3['open'] and is_large:
        return {"type": "BEARISH_REVERSAL", "level": c3['open']}
        
    return None

# فحص الاختراق على فريم الساعة (1h)
def check_hourly_breakout(symbol):
    pattern = get_daily_key_level(symbol)
    if not pattern:
        return None
        
    key_level = pattern["level"]
    
    # جلب شمعات فريم الساعة
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=5"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    
    current_price = df.iloc[-1]['close']
    prev_price = df.iloc[-2]['close']
    
    # مفتاح التتبع لمنع التكرار المستمر لنفس السعر
    cache_key = f"{symbol}_{key_level}"
    if cache_key in alerted_levels:
        return None

    # التحقق من الاختراق على فريم الساعة
    # إذا كان السعر عبر المستوى صعوداً أو هبوطاً في شمعة الساعة الأخيرة
    if prev_price <= key_level and current_price > key_level:
        alerted_levels[cache_key] = True
        return f"🚀 **اختراق صعودي على فريم الساعة!**\n" \
               f"📌 العملة: `{symbol}`\n" \
               f"🟠 مستوى الزخم اليومي المخترق: `{key_level}`\n" \
               f"📈 السعر الحالي: `{current_price}`"
               
    elif prev_price >= key_level and current_price < key_level:
        alerted_levels[cache_key] = True
        return f"⚠️ **كسر هبوطي على فريم الساعة!**\n" \
               f"📌 العملة: `{symbol}`\n" \
               f"🟠 مستوى الزخم اليومي المكسور: `{key_level}`\n" \
               f"📉 السعر الحالي: `{current_price}`"
               
    return None

def main():
    print("بدء المراقبة الذكية على فريم الساعة لاختراق مستويات اليومي...")
    send_telegram_message("🤖 *تم تفعيل بوت مراقبة الاختراقات على فريم الساعة بناءً على الزخم اليومي.*")
    
    symbols = get_usd_symbols()
    
    while True:
        for symbol in symbols:
            try:
                alert = check_hourly_breakout(symbol)
                if alert:
                    send_telegram_message(alert)
                    print(f"تم إرسال إشعار اختراق للعملة: {symbol}")
                time.sleep(1)
            except Exception as e:
                print(f"خطأ في فحص {symbol}: {e}")
        
        # فحص السوق كل 5 دقائق على فريم الساعة
        time.sleep(300)

if __name__ == "__main__":
    main()
