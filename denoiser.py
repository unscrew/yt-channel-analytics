#!/usr/bin/env python3
"""
STT Transcript 노이즈 제거 스크립트
Whisper 등 음성인식 결과물 정제
"""

import argparse
import re
import os


def remove_repeated_interjections(text: str) -> str:
    """
    반복되는 감탄사/추임새 제거
    예: "아... 아... 아..." → "아"
    """
    # 1. 점으로 연결된 반복 (아..., 어..., 음...)
    text = re.sub(r'([아어음오우에]\.\.\.\s*){2,}', r'\1', text)
    
    # 2. 같은 감탄사 연속 반복
    text = re.sub(r'\b([아어음오우에])\s+\1(\s+\1)+\b', r'\1', text)
    
    return text


def remove_repeated_words(text: str) -> str:
    """
    같은 단어 연속 반복 제거
    예: "이거 이거 이거" → "이거"
    """
    # 2-3회 연속 반복 (2글자 이상 단어만)
    text = re.sub(r'\b(\w{2,})(\s+\1){1,}\b', r'\1', text)
    
    return text


def remove_filler_words_excessive(text: str) -> str:
    """
    과도한 추임새 제거
    예: "네네네네" → "네"
    """
    fillers = ['네네', '응응', '어어', '음음', '그치그치', '맞아맞아']
    
    for filler in fillers:
        # 연속 반복 찾기
        pattern = f'({re.escape(filler)})+'
        text = re.sub(pattern, filler, text)
    
    return text


def remove_stuttering(text: str) -> str:
    """
    말더듬 패턴 제거
    예: "저.. 저는" → "저는"
    """
    # 단어 시작 반복 (첫 글자 또는 첫 음절 반복)
    text = re.sub(r'\b(\w{1,2})\.\.\s+\1(\w+)', r'\1\2', text)
    
    return text


def clean_punctuation(text: str) -> str:
    """
    구두점 정리
    """
    # 연속된 마침표/쉼표 정리
    text = re.sub(r'\.{4,}', '...', text)
    text = re.sub(r',{2,}', ',', text)
    
    # 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    
    return text


def remove_noise_patterns(text: str) -> str:
    """
    STT 특유의 노이즈 패턴 제거
    """
    # 1. 의미없는 짧은 반복
    text = re.sub(r'\b(\w)\s+\1\s+\1\b', r'\1', text)
    
    # 2. 괄호 안의 소음 표기 제거
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    
    # 3. 타임스탬프 제거 (있을 경우)
    text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    
    return text


def normalize_spacing(text: str) -> str:
    """
    띄어쓰기 정규화
    """
    # 여러 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    
    # 문장 시작/끝 공백 제거
    text = text.strip()
    
    # 줄바꿈 정리
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text


def preserve_metadata(text: str) -> tuple:
    """
    메타데이터 분리 및 보존
    (Video ID, Title, Model 등)
    """
    lines = text.split('\n')
    metadata_lines = []
    content_start = 0
    
    for i, line in enumerate(lines):
        # 메타데이터 패턴 감지
        if ':' in line and i < 10:
            if any(key in line for key in ['Video ID', 'Title', 'Model', 'Duration']):
                metadata_lines.append(line)
                content_start = i + 1
            elif line.strip() == '-' * len(line.strip()):
                metadata_lines.append(line)
                content_start = i + 1
                break
    
    metadata = '\n'.join(metadata_lines)
    content = '\n'.join(lines[content_start:])
    
    return metadata, content


def denoise_transcript(text: str, aggressive: bool = False) -> str:
    """
    종합 노이즈 제거 파이프라인
    
    Args:
        text: 입력 텍스트
        aggressive: True면 더 강력한 제거 (추임새까지)
    
    Returns:
        정제된 텍스트
    """
    # 메타데이터 분리
    metadata, content = preserve_metadata(text)
    
    # 노이즈 제거 파이프라인
    content = remove_repeated_interjections(content)
    content = remove_repeated_words(content)
    content = remove_filler_words_excessive(content)
    content = remove_stuttering(content)
    content = remove_noise_patterns(content)
    content = clean_punctuation(content)
    content = normalize_spacing(content)
    
    # aggressive 모드: 추임새 단어도 제거
    if aggressive:
        fillers_to_remove = [
            r'\b아\s+', r'\b어\s+', r'\b음\s+', r'\b으\s+',
            r'\b그\s+', r'\b이제\s+', r'\b좀\s+', r'\b뭐\s+'
        ]
        for pattern in fillers_to_remove:
            content = re.sub(pattern, '', content)
        content = normalize_spacing(content)
    
    # 메타데이터 복원
    if metadata:
        return metadata + '\n\n' + content
    else:
        return content


def process_file(input_file: str, aggressive: bool = False, verbose: bool = True):
    """
    파일 처리 및 저장
    """
    # 입력 파일 읽기
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            original_text = f.read()
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        return None
    
    original_length = len(original_text)
    
    if verbose:
        print(f"\n📄 입력: {input_file}")
        print(f"✓ 원본 길이: {original_length:,} 글자")
    
    # 노이즈 제거
    denoised_text = denoise_transcript(original_text, aggressive)
    denoised_length = len(denoised_text)
    
    # 출력 파일명 생성
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_denoised.txt"
    
    # 저장
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(denoised_text)
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return None
    
    # 결과 출력
    if verbose:
        removed = original_length - denoised_length
        reduction_pct = (removed / original_length * 100) if original_length > 0 else 0
        
        print(f"✓ 정제 후 길이: {denoised_length:,} 글자")
        print(f"✓ 제거된 노이즈: {removed:,} 글자 ({reduction_pct:.1f}%)")
        print(f"💾 출력: {output_file}")
        
        # 샘플 비교
        print("\n" + "=" * 80)
        print("📊 Before/After 비교 (처음 200자):")
        print("=" * 80)
        
        # 메타데이터 제거하고 비교
        _, original_content = preserve_metadata(original_text)
        _, denoised_content = preserve_metadata(denoised_text)
        
        print("\n[Before]")
        print(original_content[:200].strip())
        print("\n[After]")
        print(denoised_content[:200].strip())
        print("\n" + "=" * 80)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='STT 자막 노이즈 제거 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python denoise_stt.py H5lz6_hqCNw_whisper_transcript.txt
  python denoise_stt.py input.txt --aggressive
  python denoise_stt.py input.txt --quiet
  
제거되는 노이즈:
  ✓ 반복 감탄사 (아... 아... 아...)
  ✓ 연속 반복 단어 (이거 이거 이거)
  ✓ 과도한 추임새 (네네네네)
  ✓ 말더듬 (저.. 저는)
  ✓ 불필요한 공백/구두점
  
출력:
  {입력파일명}_denoised.txt
        """
    )
    
    parser.add_argument(
        'input_file',
        help='입력 STT 자막 파일'
    )
    
    parser.add_argument(
        '--aggressive',
        '-a',
        action='store_true',
        help='강력 모드 (추임새 단어도 제거)'
    )
    
    parser.add_argument(
        '--quiet',
        '-q',
        action='store_true',
        help='조용히 실행 (결과만 출력)'
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        print("=" * 80)
        print("🧹 STT 자막 노이즈 제거")
        print("=" * 80)
    
    output_file = process_file(
        args.input_file,
        aggressive=args.aggressive,
        verbose=not args.quiet
    )
    
    if output_file:
        if not args.quiet:
            print("\n✅ 완료!")
        else:
            print(output_file)
    else:
        print("\n❌ 실패!")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())