#!/usr/bin/env python3
"""
한글 감정 분석 테스트
댓글의 긍정/부정 판단 테스트
"""

import json
from pathlib import Path
from typing import List, Dict
from transformers import pipeline
from collections import Counter


def test_sentiment_models():
    """여러 한글 감정 분석 모델 테스트"""
    
    # 테스트 댓글 (당신이 제공한 실제 댓글들)
    test_comments = [
        "클래스 체인지의 경우 레벨이 1로 돌아가서 레벨업하면서 스탯을 올릴수도 있지만 클래스 체인지 즉시 주요스탯이 8정도 올라갑니다.",
        "침투부 광고스킵안하기 3회차 : 역시나 광고가 나오지 않았다",
        "이게 영걸전보다 재미없어요",
        "너무 재밌어요! 최고!",
        "진짜 별로네요",
        "감사합니다 좋은 영상",
        "이건 진짜 최악이다",
        "유익한 정보 감사합니다",
    ]
    
    print("\n" + "="*60)
    print("🇰🇷 한글 감정 분석 모델 테스트")
    print("="*60 + "\n")
    
    # 추천 모델들
    models = [
        "beomi/kcbert-base",           # KcBERT (가장 유명)
        "matthewburke/korean_sentiment", # 한글 특화
        "cardiffnlp/twitter-roberta-base-sentiment-latest", # 다국어 (영어 기반)
    ]
    
    for model_name in models:
        print(f"\n📊 모델: {model_name}")
        print("-" * 60)
        
        try:
            # 감정 분석 파이프라인 로드
            if "kcbert" in model_name:
                analyzer = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    tokenizer=model_name,
                    device=-1  # CPU 사용
                )
            else:
                analyzer = pipeline(
                    "sentiment-analysis",
                    model=model_name,
                    device=-1
                )
            
            # 각 댓글 분석
            results = analyzer(test_comments)
            
            # 결과 출력
            for comment, result in zip(test_comments, results):
                emoji = "😊" if result['label'] in ['POSITIVE', 'LABEL_0'] else "😞"
                score = result['score']
                
                print(f"{emoji} [{result['label']:8s}] {score:.2%} | {comment[:50]}...")
            
            # 통계
            labels = [r['label'] for r in results]
            counter = Counter(labels)
            print(f"\n📈 통계: {dict(counter)}")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
    
    print("\n" + "="*60)


def analyze_comment_file(filepath: str):
    """실제 댓글 JSON 파일 분석"""
    
    print("\n" + "="*60)
    print("📄 실제 댓글 파일 분석")
    print("="*60 + "\n")
    
    # JSON 파일 로드
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
        return
    
    comments = data.get('comments', [])
    
    if not comments:
        print("❌ 댓글이 없습니다.")
        return
    
    print(f"📊 총 {len(comments)}개 댓글 분석 중...\n")
    
    # KcBERT 모델 사용 (한글 최적)
    try:
        analyzer = pipeline(
            "sentiment-analysis",
            model="beomi/kcbert-base",
            device=-1
        )
        
        # 댓글 텍스트만 추출
        texts = [c['text'] for c in comments]
        
        # 감정 분석
        results = analyzer(texts)
        
        # 결과 출력
        positive = 0
        negative = 0
        
        for comment, result in zip(comments, results):
            emoji = "😊" if result['label'] == 'POSITIVE' else "😞"
            
            if result['label'] == 'POSITIVE':
                positive += 1
            else:
                negative += 1
            
            print(f"{emoji} {result['label']:8s} ({result['score']:.1%}) | {comment['text'][:60]}...")
        
        # 최종 통계
        total = len(comments)
        print("\n" + "-"*60)
        print(f"\n✨ 감정 분석 결과:")
        print(f"  😊 긍정: {positive}개 ({positive/total:.1%})")
        print(f"  😞 부정: {negative}개 ({negative/total:.1%})")
        print(f"  📊 긍정 비율: {positive/total:.1%}")
        
        # Engagement 점수 계산
        sentiment_score = (positive / total) * 100
        print(f"\n  💯 Sentiment Score: {sentiment_score:.1f}/100")
        
    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        import traceback
        traceback.print_exc()


def quick_test():
    """빠른 테스트 (설치 확인)"""
    
    print("\n🔧 빠른 설치 확인 테스트\n")
    
    try:
        from transformers import pipeline
        print("✅ transformers 설치됨")
        
        # 간단한 테스트
        analyzer = pipeline("sentiment-analysis", model="beomi/kcbert-base")
        result = analyzer("너무 재밌어요!")[0]
        
        print(f"✅ 모델 로드 성공")
        print(f"   테스트: '너무 재밌어요!' → {result['label']} ({result['score']:.1%})")
        
        return True
        
    except ImportError:
        print("❌ transformers 미설치")
        print("   설치: pip install transformers torch")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # 빠른 테스트 먼저
    if not quick_test():
        print("\n⚠️  먼저 필요한 패키지를 설치해주세요:")
        print("   pip install transformers torch")
        sys.exit(1)
    
    # 모델 비교 테스트
    test_sentiment_models()
    
    # 실제 파일이 제공되면 분석
    if len(sys.argv) > 1:
        analyze_comment_file(sys.argv[1])
    else:
        print("\n💡 실제 댓글 파일 분석하려면:")
        print("   python test_sentiment_korean.py data/chimchakman_official_comments/ZSrodkQDhWE_comments.json")