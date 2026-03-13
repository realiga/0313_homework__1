from newsapi import NewsApiClient
from googletrans import Translator

# 1. 초기 설정
newsapi = NewsApiClient(api_key='3653d9c1918a4c9d8c0ba6e16ea0c4ac') # 여기에 키 입력!
translator = Translator()

# 2. 미국(us)의 기술(technology) 뉴스 가져오기
top_headlines = newsapi.get_top_headlines(category='technology', language='en', country='us')

print("--- 🌍 오늘의 글로벌 IT 뉴스 ---")

# 3. 뉴스 5개만 뽑아서 번역하기
articles = top_headlines['articles'][:5]

for i, article in enumerate(articles, 1):
    title_en = article['title']
    
    # 영어 제목을 한국어로 번역
    try:
        title_ko = translator.translate(title_en, src='en', dest='ko').text
    except:
        title_ko = "번역 오류 (다시 시도해 주세요)"
        
    print(f"{i}. [영문] {title_en}")
    print(f"   [한글] {title_ko}")
    print(f"   🔗 링크: {article['url']}\n")