import time
import requests
import pandas as pd

# -------------------------------------------------------------
# بيانات البوت وتليغرام الخاصة بك
# -------------------------------------------------------------
TELEGRAM_TOKEN = "8630854974:AAHWPeRpHIw7SdzoiGjEh1Qub3eQ5puXrcE"
CHAT_ID = "2107579721"

# تتبع العملات التي تم إرسال تنبيه لها لمنع التكرار المستمر
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
    # قائمة الـ 62 زوجاً المقترنة بـ USD المتاحة على منصة Breakout
    breakout_symbols = [
        "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "ADAUSD", 
        "AVAXUSD", "DOGEUSD", "DOTUSD", "LINKUSD", "UNIUSD",
        "LTCUSD", "BCHUSD", "NEARUSD", "MATICUSD", "ATOMUSD",
        "ETCUSD", "ICPUSD", "XLMUSD", "APTUSD", "QNTUSD",
        "ALGOUSD", "GRTUSD", "FTMUSD", "SANDUSD", "MANAUSD",
        "AXSUSD", "THETAUSD", "EGLDUSD", "XTZUSD", "CHZUSD",
        "ARBUSD", "OPUSD", "SUIUSD", "SEIUSD", "TIAUSD", 
        "INJUSD", "RENDERUSD", "FILUSD", "AAVEUSD", "MKRUSD", 
        "CRVUSD", "SNXUSD", "COMPUSD", "ENJUSD", "BATUSD", 
        "ZECUSD", "DASHUSD", "KSMUSD", "1INCHUSD", "SUSHIUSD", 
        "OCEANUSD", "GALAUSD", "KAVAUSD", "ROSEUSD", "IMXUSD", 
        "LDOUSD", "RPLUSD", "FXSUSD", "PEPEUSD", "SHIBUSD", 
        "FLOKIUSD", "ARUSD"
    ]
    return breakout_symbols

# جلب بيانات فريم يومي لتحديد مستوى النمط (الخط البرتقالي / بداية شمعة الانعكاس)
def get_daily_key_level(symbol):
    try:
        # استخدام بيانات كراكن أو بينانس للرموز المتوافقة مع USD
        binance_symbol = symbol.replace("USD", "USDT") # كبديل متوافق لجلـب الكلاينز بدقة
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1d&limit=10"
        response = requests.get(url)
        if response.status_code != 200:
            return None
            
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
            
        c1 = df.iloc[-4] # شمعة الزخم الأولى
        c2 = df.iloc[-3] # شمعة الزخم الثانية
        c3 = df.iloc[-2] # الشمعة المعاكسة (التصحيحية)
        avg_body = df['body_size'].mean()
        
        # شروط الزخم اليومي (شمعتان كبيرتان نسبياً)
        is_large = (c1['body_size'] > avg_body * 0.8) and (c2['body_size'] > avg_body * 0.8)
        
        # صاعد ثم شمعة حمراء معاكسة
        if c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] < c3['open'] and is_large:
            return {"type": "BULLISH_REVERSAL", "level": c3['open']}
            
        # هابط ثم شمعة خضراء معاكسة
        if c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] > c3['open'] and is_large:
            return {"type": "BEARISH_REVERSAL", "level": c3['open']}
            
        return None
    except Exception:
        return None

# فحص الاختراق على فريم الساعة (1h) لمستوى اليومي المحدد
def check_hourly_breakout(symbol):
    pattern = get_daily_key_level(symbol)
    if not pattern:
        return None
        
    key_level = pattern["level"]
    binance_symbol = symbol.replace("USD", "USDT")
    
    # جلب شمعات فريم الساعة
    url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1h&limit=5"
    response = requests.get(url)
    if response.status_code != 200:
        return None
        
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    
    current_price = df.iloc[-1]['close']
    prev_price = df.iloc[-2]['close']
    
    cache_key = f"{symbol}_{key_level}"
    if cache_key in alerted_levels:
        return None

    # التحقق من الاختراق على فريم الساعة
    if prev_price <= key_level and current_price > key_level:
        alerted_levels[cache_key] = True
        return f"🚀 **اختراق صعودي على فريم الساعة!**\n" \
               f"📌 العملة: `{symbol}`\n" \
               f"🟠 مستوى الزخم اليومي المخترق (بداية شمعة الانعكاس): `{key_level}`\n" \
               f"📈 السعر الحالي: `{current_price}`"
               
    elif prev_price >= key_level and current_price < key_level:
        alerted_levels[cache_key] = True
        return f"⚠️ **كسر هبوطي على فريم الساعة!**\n" \
               f"📌 العملة: `{symbol}`\n" \
               f"🟠 مستوى الزخم اليومي المكسور (بداية شمعة الانعكاس): `{key_level}`\n" \
               f"📉 السعر الحالي: `{current_price}`"
               
    return None

def main():
    print("بدء المراقبة الذكية لـ 62 زوجاً على فريم الساعة...")
    send_telegram_message("🤖 *تم تحديث البوت لمراقبة الـ 62 عملة المتاحة على Breakout بناءً على استراتيجية الفريم اليومي والساعة.*")
    
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
        
        # إعادة الفحص كل 5 دقائق
        time.sleep(300)

if __name__ == "__main__":
    main()
