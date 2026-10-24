import time
import requests
import pandas as pd
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# -------------------------------------------------------------
# بيانات البوت وتليغرام الخاصة بك
# -------------------------------------------------------------
TELEGRAM_TOKEN = "8630854974:AAHWPeRpHIw7SdzoiGjEh1Qub3eQ5puXrcE"
CHAT_ID = "2107579721"

# تتبع العملات لمنع التكرار
alerted_levels = {}

# سيرفر وهمي صغير لرضا منصة Render وتجنب خطأ البورت
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

def run_fake_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

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
    return [
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

def get_daily_key_level(symbol):
    try:
        binance_symbol = symbol.replace("USD", "USDT")
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
            
        c1 = df.iloc[-4]
        c2 = df.iloc[-3]
        c3 = df.iloc[-2]
        avg_body = df['body_size'].mean()
        
        is_large = (c1['body_size'] > avg_body * 0.8) and (c2['body_size'] > avg_body * 0.8)
        
        if c1['close'] > c1['open'] and c2['close'] > c2['open'] and c3['close'] < c3['open'] and is_large:
            return {"type": "BULLISH_REVERSAL", "level": c3['open']}
            
        if c1['close'] < c1['open'] and c2['close'] < c2['open'] and c3['close'] > c3['open'] and is_large:
            return {"type": "BEARISH_REVERSAL", "level": c3['open']}
            
        return None
    except Exception:
        return None

def check_hourly_breakout(symbol):
    pattern = get_daily_key_level(symbol)
    if not pattern:
        return None
        
    key_level = pattern["level"]
    binance_symbol = symbol.replace("USD", "USDT")
    
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

    if prev_price <= key_level and current_price > key_level:
        alerted_levels[cache_key] = True
        return f"🚀 **اختراق صعودي على فريم الساعة!**\n📌 العملة: `{symbol}`\n🟠 مستوى الزخم اليومي: `{key_level}`\n📈 السعر: `{current_price}`"
               
    elif prev_price >= key_level and current_price < key_level:
        alerted_levels[cache_key] = True
        return f"⚠️ **كسر هبوطي على فريم الساعة!**\n📌 العملة: `{symbol}`\n🟠 مستوى الزخم اليومي: `{key_level}`\n📉 السعر: `{current_price}`"
               
    return None

def main():
    # تشغيل السيرفر الوهمي في الخلفية لترضى عنه منصة Render
    server_thread = threading.Thread(target=run_fake_server, daemon=True)
    server_thread.start()
    
    print("بدء المراقبة الذكية لـ 62 زوجاً على فريم الساعة...")
    send_telegram_message("🤖 *تم تشغيل البوت بنجاح ومراقبة الـ 62 عملة مفعلة الآن!*")
    
    symbols = get_usd_symbols()
    
    while True:
        for symbol in symbols:
            try:
                alert = check_hourly_breakout(symbol)
                if alert:
                    send_telegram_message(alert)
                time.sleep(1)
            except Exception as e:
                print(f"خطأ في فحص {symbol}: {e}")
        time.sleep(300)

if __name__ == "__main__":
    main()
