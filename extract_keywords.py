#!/usr/bin/env python3
"""
다중 방법을 활용한 종합 키워드 추출
- Hugging Face Pipelines (NER, Zero-shot)
- KeyBERT (BERT 기반)
- YAKE (통계 기반)
- TF-IDF (전통적 방법)
"""

import argparse
import json
from typing import List, Dict, Tuple
from collections import Counter
import re


def extract_with_hf_ner(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """Hugging Face NER 파이프라인"""
    try:
        from transformers import pipeline
        print("  🤗 Hugging Face NER...")
        
        ner = pipeline("ner", aggregation_strategy="simple")
        
        chunks = [text[i:i+512] for i in range(0, len(text), 512)][:10]
        
        entities = {}
        for chunk in chunks:
            try:
                results = ner(chunk)
                for entity in results:
                    word = entity['word'].strip()
                    if len(word) > 1:
                        entities[word] = max(entities.get(word, 0), entity['score'])
            except:
                continue
        
        sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)
        return sorted_entities[:top_n]
    except Exception as e:
        print(f"    ⚠️ NER 실패: {e}")
        return []


def extract_with_hf_zeroshot(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """Hugging Face Zero-shot Classification"""
    try:
        from transformers import pipeline
        print("  🤗 Hugging Face Zero-shot...")
        
        classifier = pipeline("zero-shot-classification")
        
        candidate_labels = [
            "게임", "마인크래프트", "먹방", "음식", "일상", "브이로그",
            "여행", "리뷰", "뉴스", "스포츠", "음악", "교육", "코미디"
        ]
        
        text_truncated = text[:512]
        result = classifier(text_truncated, candidate_labels, multi_label=True)
        
        return list(zip(result['labels'], result['scores']))[:top_n]
    except Exception as e:
        print(f"    ⚠️ Zero-shot 실패: {e}")
        return []


def extract_with_keybert(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """KeyBERT"""
    try:
        from keybert import KeyBERT
        print("  🔑 KeyBERT...")
        
        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(
            text, keyphrase_ngram_range=(1, 2), top_n=top_n, use_maxsum=True
        )
        return keywords
    except ImportError:
        print("    ⚠️ KeyBERT 미설치 (pip install keybert)")
        return []
    except Exception as e:
        print(f"    ⚠️ KeyBERT 실패: {e}")
        return []


def extract_with_yake(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """YAKE"""
    try:
        import yake
        print("  📊 YAKE...")
        
        kw_extractor = yake.KeywordExtractor(lan="ko", n=2, top=top_n)
        keywords = kw_extractor.extract_keywords(text)
        keywords = [(kw, 1/(score+0.001)) for kw, score in keywords]
        return keywords
    except ImportError:
        print("    ⚠️ YAKE 미설치 (pip install yake)")
        return []
    except Exception as e:
        print(f"    ⚠️ YAKE 실패: {e}")
        return []


def extract_with_tfidf(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """TF-IDF"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from konlpy.tag import Okt
        print("  📈 TF-IDF...")
        
        okt = Okt()
        nouns = okt.nouns(text)
        if not nouns:
            return []
        
        vectorizer = TfidfVectorizer(max_features=top_n*2, ngram_range=(1,2))
        tfidf = vectorizer.fit_transform([' '.join(nouns)])
        
        scores = tfidf.toarray()[0]
        names = vectorizer.get_feature_names_out()
        keywords = sorted(zip(names, scores), key=lambda x: x[1], reverse=True)
        return keywords[:top_n]
    except ImportError:
        print("    ⚠️ sklearn/konlpy 미설치")
        return []
    except Exception as e:
        print(f"    ⚠️ TF-IDF 실패: {e}")
        return []


def extract_with_frequency(text: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """빈도"""
    print("  🔢 빈도 분석...")
    words = re.findall(r'[가-힣]{2,}', text)
    stopwords = {'있는', '없는', '한다', '있다', '하는', '그것', '이것'}
    words = [w for w in words if w not in stopwords]
    counts = Counter(words)
    max_c = max(counts.values()) if counts else 1
    return [(w, c/max_c) for w, c in counts.most_common(top_n)]


def combine_keywords(all_keywords: Dict, top_n: int = 20) -> List[Dict]:
    """결과 결합"""
    print("\n🔗 결과 결합 중...")
    
    weights = {
        'hf_ner': 1.0, 'hf_zeroshot': 1.0, 'keybert': 1.2,
        'yake': 0.9, 'tfidf': 0.8, 'frequency': 0.5
    }
    
    scores = {}
    sources = {}
    
    for method, keywords in all_keywords.items():
        weight = weights.get(method, 1.0)
        for keyword, score in keywords:
            kw_lower = keyword.lower()
            scores[kw_lower] = scores.get(kw_lower, 0) + score * weight
            sources.setdefault(kw_lower, []).append(method)
    
    sorted_kws = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    return [{
        'keyword': kw,
        'score': float(sc),
        'sources': sources[kw],
        'source_count': len(sources[kw])
    } for kw, sc in sorted_kws[:top_n]]


def extract_keywords_comprehensive(file_path: str, top_n: int = 20) -> Dict:
    """종합 추출"""
    print(f"\n📄 파일: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        return None
    
    print(f"✓ 텍스트 길이: {len(text):,} 글자\n")
    print("🔍 다중 방법으로 키워드 추출...\n")
    
    all_keywords = {}
    
    for name, func in [
        ('hf_ner', extract_with_hf_ner),
        ('hf_zeroshot', extract_with_hf_zeroshot),
        ('keybert', extract_with_keybert),
        ('yake', extract_with_yake),
        ('tfidf', extract_with_tfidf),
        ('frequency', extract_with_frequency)
    ]:
        kws = func(text, top_n)
        if kws:
            all_keywords[name] = kws
            print(f"    ✓ {len(kws)}개")
    
    if not all_keywords:
        print("⚠️  키워드 추출 실패")
        return None
    
    combined = combine_keywords(all_keywords, top_n)
    
    return {
        'file': file_path,
        'text_length': len(text),
        'methods_used': list(all_keywords.keys()),
        'keywords_by_method': {
            m: [{'keyword': k, 'score': float(s)} for k, s in kws]
            for m, kws in all_keywords.items()
        },
        'combined_keywords': combined
    }


def main():
    parser = argparse.ArgumentParser(
        description='다중 방법 종합 키워드 추출',
        epilog="""
예시:
  python extract_keywords.py input.txt
  python extract_keywords.py input.txt --top 30 --output out.json

방법: HF NER, HF Zero-shot, KeyBERT, YAKE, TF-IDF, 빈도
패키지: pip install transformers torch keybert yake scikit-learn konlpy
        """
    )
    
    parser.add_argument('input_file')
    parser.add_argument('--top', type=int, default=20)
    parser.add_argument('--output')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎯 종합 키워드 추출")
    print("=" * 80)
    
    result = extract_keywords_comprehensive(args.input_file, args.top)
    if not result:
        return
    
    print("\n" + "=" * 80)
    print("📊 최종 키워드:")
    print("=" * 80)
    
    for i, item in enumerate(result['combined_keywords'], 1):
        print(f"{i:2d}. {item['keyword']:25s} "
              f"({item['score']:6.3f}) "
              f"[{item['source_count']}개: {', '.join(item['sources'])}]")
    
    print("\n" + "=" * 80)
    print("🔍 방법별 상세:")
    print("=" * 80)
    
    for method, kws in result['keywords_by_method'].items():
        print(f"\n{method}:")
        for i, k in enumerate(kws[:5], 1):
            print(f"  {i}. {k['keyword']:20s} ({k['score']:.3f})")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 저장: {args.output}")
    
    print("\n" + "=" * 80)
    print(f"✅ 완료! ({len(result['methods_used'])}개 방법 사용)")
    print("=" * 80)


if __name__ == '__main__':
    main()