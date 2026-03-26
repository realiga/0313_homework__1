import os
import asyncio
import time
import sys
import yfinance as yf
from gnews import GNews
import google.generativeai as genai
import telegram
from dotenv import load_dotenv

# 1. 환경 설정 및 키 로드
load_dotenv("API_Key.env")
KEYS = {
    "TG_TOKEN": os.getenv("TELEGRAM_TOKEN"),
    "CH_ID": os.getenv("CHAT_ID"),
    "GEMINI": os.getenv("GEMINI_API_KEY")
}

# 2. 엔진 설정 (1.5 시도 후 안되면 2.0으로 전환)
try:
    genai.configure(api_key=KEYS["GEMINI"])
    
    # 내 계정에서 가용한 모델 리스트 확보
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # 우선순위 설정
    priority_list = [
        'models/gemini-1.5-flash',      # 1순위 (할당량 넉넉함)
        'models/gemini-1.5-flash-8b',   # 2순위 (가장 가벼움)
        'models/gemini-2.0-flash',      # 3순위 (최신 모델)
        'models/gemini-1.5-pro'         # 4순위 (고성능)
    ]
    
    selected_model = None
    for target in priority_list:
        if target in available_models:
            selected_model = target
            break
            
    if not selected_model:
        selected_model = available_models[0] # 위 목록에 없으면 가용한 첫 모델 선택

    model = genai.GenerativeModel(selected_model)
    print(f"✅ AI 엔진 확정: {selected_model}")

except Exception as e:
    print(f"❌ 엔진 설정 치명적 오류: {e}")
    sys.exit()

# 3. 포트폴리오 데이터
my_portfolio = {
    '240810.KQ': [121100.00, 25, '원익IPS'],
    '015760.KS': [47538.00, 205, '한국전력'],
    '005380.KS': [529000.00, 8, '현대차'],
    '272210.KS': [125400.00, 37, '한화시스템'],
    '441640.KS': [12860.00, 500, 'KODEX미국배당'],
    'SCHD': [30.84, 200, 'SCHD'],
    'SOXL': [57.42, 35, 'SOXL'],
    'STRC': [100.12, 50, 'STRC']
}

async def get_realtime_rate():
    try:
        # history(period="1d")를 사용하는 것이 fast_info보다 안정적입니다.
        rate_data = yf.Ticker("USDKRW=X").history(period="1d")
        rate = rate_data['Close'].iloc[-1]
        print(f"💵 실시간 환율 적용: {rate:.2f}원")
        return rate
    except:
        return 1385.0

async def job():
    print(f"[{time.strftime('%H:%M:%S')}] 🏛️ AI 통합 브리핑 시스템 가동...")
    google_news = GNews(language='ko', country='KR', period='2d', max_results=3)
    usd_krw = await get_realtime_rate()

    analysis_results = ""
    total_asset = 0
    total_purchase = 0

    for ticker, info in my_portfolio.items():
        buy_p, qty, name = info
        try:
            # 주가 데이터 수집
            stock_hist = yf.Ticker(ticker).history(period="1d")
            curr_p = stock_hist['Close'].iloc[-1]
            profit_pct = ((curr_p - buy_p) / buy_p) * 100
            
            is_usd = ".KS" not in ticker and ".KQ" not in ticker
            total_asset += (curr_p * qty * (usd_krw if is_usd else 1))
            total_purchase += (buy_p * qty * (usd_krw if is_usd else 1))

            # 60초 안전 대기 (TPM/RPM 보호 및 IP 차단 방지)
            print(f"\n🔍 [{name}] 분석 준비 중...")
            for i in range(60, 0, -1):
                sys.stdout.write(f"\r⏳ API 안정화 대기 중... {i}초 남음  ")
                sys.stdout.flush()
                await asyncio.sleep(1)
            
            # 뉴스 데이터 다이어트 (70자 컷)
            news_list = google_news.get_news(name)
            clean_titles = ""
            if news_list:
                for n in news_list[:3]: # 뉴스 최대 3개
                    clean_titles += f"- {n['title'].strip()[:70]}...\n"
            else:
                clean_titles = "관련 뉴스 없음"

            # AI 분석 (1.5 Flash 우선 모드)
            prompt = f"종목:{name}\n최근뉴스:\n{clean_titles}\n위 내용을 바탕으로 투자 의견을 이모지 포함 한 줄로 아주 간결하게 작성해."
            response = model.generate_content(prompt)
            ai_comment = response.text.strip().replace('\n', ' ')

            status_emoji = "🔺" if profit_pct > 0 else "🔹"
            analysis_results += f"{status_emoji} *{name}* ({profit_pct:+.2f}%)\n   └ {ai_comment}\n\n"
            print(f"\n✅ {name} 분석 성공")

        except Exception as e:
            print(f"\n⚠️ {name} 오류: {e}")
            analysis_results += f"🔹 *{name}*\n   └ ⏳ 데이터 수집 지연\n\n"

    # 최종 리포트 합산 및 전송
    total_profit = total_asset - total_purchase
    total_profit_pct = (total_profit / total_purchase) * 100
    
    report = f"🏛️ *AI 투자 브리핑*\n"
    report += f"📅 분석 시각: {time.strftime('%Y-%m-%d %H:%M')}\n"
    report += f"💵 적용 환율: {usd_krw:.2f}원\n\n"
    report += analysis_results
    report += f"{'-'*25}\n"
    report += f"💰 *총 자산:* {int(total_asset):,}원\n"
    report += f"📈 *총 수익:* {int(total_profit):,}원 ({total_profit_pct:+.2f}%)\n"

    bot = telegram.Bot(token=KEYS["TG_TOKEN"])
    await bot.send_message(chat_id=KEYS["CHAT_ID"], text=report, parse_mode='Markdown')
    print("🚀 [성공] 텔레그램 리포트가 전송되었습니다!")

if __name__ == "__main__":
    asyncio.run(job())