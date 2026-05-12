import time, requests, re
from datetime import datetime

# ============================================================
# ★ 設定區
# ============================================================

TELEGRAM_BOT_TOKEN  = "8767029279:AAENwO-6tqdVvx6y680jiXVOKsqb8Yoz8ao"
TELEGRAM_CHAT_IDS   = [
    "920074908",      # 你
    "8625497046",     # Yichun Lin
]

LINE_CHANNEL_ACCESS_TOKEN = "rH/zH2kWyj2blWtDvblFO7DNR5uUTz4l3Gu8VZWVFBRtnbxJxggUPVVoVq5jceVTbVTfya7w4PCoUpPg2r/coi9F2y9wmIOkvF3Xs1WnEBCFjyfGKXzIrl7f44Y6uDzPrNUn/he0XdiCTaXlgJ6HqQdB04t89/1O/w1cDnyilFU="
LINE_USER_ID              = "U6eebd46b80f9addcf62d0da451b0d828"

WATCH_URL      = "https://www.marukyu-koyamaen.net/category/select/cid/312"
CHECK_INTERVAL = 60   # 每 60 秒檢查一次
LOG_INTERVAL   = 300  # 每 5 分鐘印一次狀態摘要

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/147.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9,zh-TW;q=0.8",
}

# ── Log ───────────────────────────────────────────────────

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "·", "OK": "✅", "ERR": "❌", "WARN": "⚠️", "BUY": "🎉", "HEAD": "━"}
    print(f"[{ts}] {icons.get(level,'·')} {msg}", flush=True)

# ── Telegram ──────────────────────────────────────────────

def send_telegram(message):
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
            r.raise_for_status()
            log(f"Telegram 已送出 ({chat_id})", "OK")
        except Exception as e:
            log(f"Telegram 失敗 ({chat_id}): {e}", "ERR")

# ── Line ──────────────────────────────────────────────────

def send_line(message):
    # 移除 HTML tag，Line 不支援 HTML
    import re
    plain = re.sub(r'<[^>]+>', '', message)
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "to": LINE_USER_ID,
                "messages": [{"type": "text", "text": plain}],
            },
            timeout=10
        )
        r.raise_for_status()
        log("Line 已送出", "OK")
    except Exception as e:
        log(f"Line 失敗: {e}", "ERR")

def notify(message):
    send_telegram(message)
    send_line(message)

# ── 取得商品數量 ───────────────────────────────────────────

def fetch_product_count():
    try:
        r = requests.get(WATCH_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text

        # 找 "抹茶 (N)" 的數字
        match = re.search(r'抹茶\s*\((\d+)\)', html)
        if match:
            return int(match.group(1))

        # 備用：找 "未発現商品" / "未发现商品"
        if "未发现商品" in html or "未發現商品" in html or "商品がありません" in html:
            return 0

        return None  # 無法判斷
    except Exception as e:
        log(f"fetch 失敗: {e}", "ERR")
        return None

# ── 主監控 ────────────────────────────────────────────────

def monitor():
    log("丸久小山園 抹茶 補貨監控啟動", "HEAD")
    log(f"監控網址: {WATCH_URL}")
    log(f"檢查間隔: {CHECK_INTERVAL} 秒")

    previous_count = None
    check_count    = 0
    start_time     = time.time()
    last_log       = 0
    notified       = False

    # 啟動時取得初始狀態並通知
    initial = fetch_product_count()
    previous_count = initial
    icon = "🟢" if initial and initial > 0 else "🔴"
    notify(
        f"🍵 抹茶補貨監控啟動\n\n"
        f"{icon} 丸久小山園 抹茶：{initial if initial is not None else '?'} 件\n\n"
        f"🔄 每 {CHECK_INTERVAL} 秒檢查一次\n"
        f"🔗 {WATCH_URL}"
    )



    while True:
        count = fetch_product_count()
        check_count += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if count is None:
            log("無法取得商品數量，下次重試", "WARN")
        else:
            icon = "🟢" if count > 0 else "🔴"
            log(f"{icon} 商品數量：{count} 件（第 {check_count} 次檢查）")

            # 補貨偵測：從 0 變成有商品
            if previous_count == 0 and count > 0 and not notified:
                log(f"補貨！商品數量：{count} 件", "BUY")
                notify(
                    f"🎉 補貨通知！\n\n"
                    f"🍵 丸久小山園 抹茶\n"
                    f"📦 商品數量：{count} 件\n\n"
                    f"🔗 {WATCH_URL}\n"
                    f"⏰ {now}"
                )
                notified = True

            # 如果又回到 0，重置通知狀態
            if count == 0:
                notified = False

            previous_count = count

        # 定期摘要
        if time.time() - last_log >= LOG_INTERVAL:
            elapsed = int(time.time() - start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            log(f"運行 {h:02d}:{m:02d}:{s:02d}  共檢查 {check_count} 次  目前商品數：{count if count is not None else '?'}")
            last_log = time.time()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor()
