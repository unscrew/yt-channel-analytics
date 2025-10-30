 #!/usr/bin/env python3
"""
문맥 기반 키워드 추출 (한국어 STT 최적화)
LLM처럼 의미 단위로 키워드 추출
"""

import argparse
import json
from collections import Counter
import re
import os
import sys
import subprocess

# JAVA_HOME 자동 설정 (KoNLPy용)
def setup_java_home():
    """JAVA_HOME 자동 감지 및 설정"""
    if os.environ.get('JAVA_HOME'):
        return True
    
    java_home = None
    
    if sys.platform == 'darwin':  # Mac
        # 방법 1: /usr/libexec/java_home
        try:
            result = subprocess.run(['/usr/libexec/java_home'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                java_home = result.stdout.strip()
        except:
            pass
        
        # 방법 2: Homebrew 경로들
        if not java_home:
            homebrew_paths = [
                '/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home',
                '/opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home',
                '/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home',
                '/usr/local/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home',
                '/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home',
                '/Library/Java/JavaVirtualMachines/jdk-17.jdk/Contents/Home',
                '/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home',
            ]
            for path in homebrew_paths:
                if os.path.exists(path):
                    java_home = path
                    break
    
    elif sys.platform.startswith('linux'):  # Linux
        linux_paths = [
            '/usr/lib/jvm/java-21-openjdk-amd64',
            '/usr/lib/jvm/java-17-openjdk-amd64',
            '/usr/lib/jvm/java-11-openjdk-amd64',
            '/usr/lib/jvm/default-java',
        ]
        for path in linux_paths:
            if os.path.exists(path):
                java_home = path
                break
    
    if java_home:
        os.environ['JAVA_HOME'] = java_home
        return True
    
    return False

# Java 설정 시도
JAVA_AVAILABLE = setup_java_home()


def extract_metadata_and_content(text: str) -> tuple:
    """
    메타데이터와 본문 완전 분리
    """
    lines = text.split('\n')
    separator_found = False
    content_start = 0
    
    for i, line in enumerate(lines):
        if '-' * 10 in line:  # 구분선
            separator_found = True
            content_start = i + 1
            break
        if i > 10 and not separator_found:  # 메타데이터 없으면
            content_start = 0
            break
    
    content = '\n'.join(lines[content_start:])
    return content


def extract_nouns_with_konlpy(text: str) -> list:
    """
    형태소 분석으로 명사만 추출 (가장 정확)
    """
    if not JAVA_AVAILABLE:
        print("     ⚠️ Java 없음 - 간단한 패턴 사용")
        print("     💡 Java 설치: brew install openjdk@11")
        return None
    
    try:
        from konlpy.tag import Okt
        okt = Okt()
        nouns = okt.nouns(text)
        return [n for n in nouns if len(n) >= 2]
    except ImportError:
        print("     ⚠️ konlpy 없음 - 간단한 패턴으로 대체")
        print("     💡 설치: pip install konlpy")
        return None
    except Exception as e:
        print(f"     ⚠️ 형태소 분석 실패: {e}")
        print("     💡 Java 설치: brew install openjdk@11")
        return None


def extract_nouns_simple(text: str) -> list:
    """
    형태소 분석 없이 명사 추출 (백업)
    단순하고 관대한 방식
    """
    # 한글 단어 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}', text)
    
    # 전혀 필터링 안 함! 일단 모두 반환
    # (불용어 제거는 나중에 별도로)
    return words


def get_extended_stopwords() -> set:
    """
    확장된 불용어 사전 (한국어 구어체 특화)
    """
    return {
        # 지시어
        '이거', '그거', '저거', '이것', '그것', '저것', '이게', '그게', '저게',
        '여기', '거기', '저기', '이쪽', '그쪽', '저쪽', '요기', '거기서',
        
        # 대명사
        '나', '너', '저', '우리', '저희', '그', '이', '저', '누구', '뭐',
        '내가', '네가', '저가', '제가', '우리가', '저희가',
        
        # 접속사/부사
        '그리고', '그래서', '하지만', '그런데', '근데', '그럼', '그러면',
        '그냥', '좀', '막', '진짜', '정말', '너무', '되게', '엄청', '완전',
        '약간', '조금', '많이', '아주', '굉장히', '정말로',
        
        # 시간/순서
        '오늘', '어제', '내일', '지금', '이제', '나중', '먼저', '다음',
        '처음', '마지막', '언제', '항상', '가끔', '자주',
        
        # 동사 파생
        '되는', '하는', '한다', '했다', '할', '된', '했고', '하고',
        '있는', '없는', '있다', '없다', '이다', '아니다',
        
        # 형용사 파생
        '좋은', '나쁜', '크다', '작다', '많다', '적다',
        
        # 조사류
        '때문', '경우', '것', '거', '수', '등', '및', '때', '도', '만',
        
        # 감탄사/추임새
        '아니', '아니야', '아니요', '네', '예', '응', '어', '음', '오',
        '와', '우와', '헐', '대박',
        
        # 의문/확인
        '뭐', '뭔가', '어떻게', '왜', '어디', '언제',
        
        # 문장 연결
        '이렇게', '그렇게', '저렇게', '이런', '그런', '저런',
        
        # 기타 구어체
        '거의', '사실', '보통', '원래', '일단', '먼저', '다음',
        '말', '얘기', '이야기', '생각', '느낌', '같은', '같다',
        '하면', '하던', '했던', '할게', '할까', '하자',
        
        # 영어 메타데이터
        'video', 'title', 'model', 'whisper', 'base', 'id',
        'hqcnw', 'asmr'  # 이런 건 케이스별로 판단
    }


def filter_by_frequency_and_length(words: list, min_freq: int = 2, min_len: int = 2) -> Counter:
    """
    빈도와 길이로 필터링
    """
    word_counts = Counter(words)
    
    # 필터링
    filtered = {
        word: count 
        for word, count in word_counts.items()
        if count >= min_freq and len(word) >= min_len
    }
    
    return Counter(filtered)


def detect_named_entities_simple(text: str) -> dict:
    """
    간단한 고유명사 탐지
    """
    entities = {
        'brands': [],
        'persons': [],
        'products': [],
        'topics': []
    }
    
    text_lower = text.lower()
    
    # 브랜드/제품명 (대문자로 시작하거나 반복 등장)
    brand_patterns = {
        '테라': 'brands',
        '참이슬': 'brands',
        'whisper': 'products',
    }
    
    # 사람 (닉네임, 호칭)
    person_patterns = {
        '침착맨': 'persons',
        '넉살': 'persons',
        '넥살': 'persons',
        '와이프': 'persons',
    }
    
    # 토픽
    topic_patterns = {
        '게임': 'topics',
        '맥주': 'topics',
        '광고': 'topics',
        '방송': 'topics',
        '라이브': 'topics',
    }
    
    all_patterns = {**brand_patterns, **person_patterns, **topic_patterns}
    
    for pattern, category in all_patterns.items():
        if pattern in text_lower:
            entities[category].append(pattern)
    
    return entities


def rank_keywords_by_relevance(word_counts: Counter, entities: dict, text: str) -> list:
    """
    관련도 기반 키워드 랭킹
    """
    scored_keywords = []
    
    # 1. 고유명사는 우선순위 부여
    priority_words = set()
    for category in entities.values():
        priority_words.update(category)
    
    # 2. 각 단어에 점수 부여
    for word, freq in word_counts.items():
        score = freq
        
        # 고유명사 가산점
        if word in priority_words:
            score *= 2.0
        
        # 길이 가산점 (2-6글자가 적당)
        if 2 <= len(word) <= 6:
            score *= 1.2
        elif len(word) > 10:
            score *= 0.5
        
        # 합성어 판별 (띄어쓰기 없이 붙은 것)
        if len(word) > 6 and not any(char in word for char in '0123456789'):
            score *= 0.7  # 페널티
        
        scored_keywords.append((word, freq, score))
    
    # 점수순 정렬
    scored_keywords.sort(key=lambda x: x[2], reverse=True)
    
    return scored_keywords


def extract_keywords_contextual(text: str, top_n: int = 10, use_konlpy: bool = True) -> dict:
    """
    문맥 기반 키워드 추출 (메인 함수)
    """
    print("\n🔍 문맥 기반 키워드 추출 시작...\n")
    
    # 1. 메타데이터 제거
    print("  1️⃣ 메타데이터 제거...")
    content = extract_metadata_and_content(text)
    
    # 2. 명사 추출
    print("  2️⃣ 명사 추출 중...")
    if use_konlpy:
        nouns = extract_nouns_with_konlpy(content)
    else:
        nouns = None
    
    if not nouns:
        print("     → 간단한 패턴 사용")
        nouns = extract_nouns_simple(content)
    else:
        print(f"     ✓ {len(nouns)}개 명사 추출")
    
    # 3. 불용어 제거
    print("  3️⃣ 불용어 제거...")
    stopwords = get_extended_stopwords()
    filtered_nouns = [n for n in nouns if n not in stopwords]
    print(f"     ✓ {len(filtered_nouns)}개 남음")
    
    # 4. 빈도 필터링
    print("  4️⃣ 빈도 필터링...")
    word_counts = filter_by_frequency_and_length(filtered_nouns, min_freq=2)
    print(f"     ✓ {len(word_counts)}개 후보")
    
    # 5. 고유명사 탐지
    print("  5️⃣ 고유명사 탐지...")
    entities = detect_named_entities_simple(content)
    total_entities = sum(len(v) for v in entities.values())
    print(f"     ✓ {total_entities}개 발견")
    
    # 6. 관련도 기반 랭킹
    print("  6️⃣ 관련도 점수 계산...")
    ranked = rank_keywords_by_relevance(word_counts, entities, content)
    
    # 최종 결과
    final_keywords = []
    for word, freq, score in ranked[:top_n]:
        kw_type = 'topic'
        for cat, words in entities.items():
            if word in words:
                kw_type = cat.rstrip('s')  # brands -> brand
                break
        
        final_keywords.append({
            'keyword': word,
            'frequency': freq,
            'score': round(score, 2),
            'type': kw_type
        })
    
    return {
        'keywords': final_keywords,
        'entities': entities,
        'total_nouns': len(nouns),
        'filtered_nouns': len(filtered_nouns),
        'candidates': len(word_counts)
    }


def main():
    parser = argparse.ArgumentParser(
        description='문맥 기반 키워드 추출 (한국어 STT 최적화)',
        epilog="""
예시:
  python extract_keywords_contextual.py input_denoised.txt
  python extract_keywords_contextual.py input.txt --top 15 --no-konlpy
  python extract_keywords_contextual.py input.txt --output result.json
        """
    )
    
    parser.add_argument('input_file', help='입력 파일 (denoised 권장)')
    parser.add_argument('--top', type=int, default=10, help='키워드 개수')
    parser.add_argument('--no-konlpy', action='store_true', help='형태소 분석 안함')
    parser.add_argument('--output', help='JSON 출력')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎯 문맥 기반 키워드 추출")
    print("=" * 80)
    
    # 파일 읽기
    print(f"\n📄 파일: {args.input_file}")
    with open(args.input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"✓ 텍스트: {len(text):,} 글자")
    
    # 키워드 추출
    result = extract_keywords_contextual(
        text,
        top_n=args.top,
        use_konlpy=not args.no_konlpy
    )
    
    # 결과 출력
    print("\n" + "=" * 80)
    print(f"✨ 최종 키워드 Top {args.top}:")
    print("=" * 80)
    
    for i, kw in enumerate(result['keywords'], 1):
        print(f"{i:2d}. {kw['keyword']:15s} "
              f"[{kw['type']:8s}] "
              f"빈도:{kw['frequency']:2d}  "
              f"점수:{kw['score']:5.1f}")
    
    # 고유명사 요약
    if any(result['entities'].values()):
        print("\n" + "=" * 80)
        print("🏷️  발견된 고유명사:")
        print("=" * 80)
        for cat, words in result['entities'].items():
            if words:
                print(f"  {cat:12s}: {', '.join(words)}")
    
    # 통계
    print("\n" + "=" * 80)
    print("📊 추출 통계:")
    print("=" * 80)
    print(f"  전체 명사: {result['total_nouns']}개")
    print(f"  불용어 제거 후: {result['filtered_nouns']}개")
    print(f"  빈도 필터 후: {result['candidates']}개")
    print(f"  최종 키워드: {len(result['keywords'])}개")
    
    # JSON 저장
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 저장: {args.output}")
    
    print("\n" + "=" * 80)
    print("✅ 완료!")
    print("=" * 80)


if __name__ == '__main__':
    main()