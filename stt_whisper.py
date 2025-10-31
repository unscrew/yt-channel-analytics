#!/usr/bin/env python3
"""
Whisper 트랜스포머로 YouTube 비디오 자막 생성
data/chimchakman_official_transcripts 에 저장
"""

import os
import sys
import argparse
from pathlib import Path

# 출력 디렉토리
OUTPUT_DIR = Path("data/chimchakman_official_transcripts")


def test_whisper_single_video(video_id, model_size="base", output_dir=OUTPUT_DIR):
    """
    단일 YouTube 비디오로 Whisper 테스트
    
    Args:
        video_id: YouTube 비디오 ID
        model_size: Whisper 모델 크기 (tiny, base, small, medium, large)
        output_dir: 출력 디렉토리
    """
    # 출력 디렉토리 생성
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("🎤 Whisper (Speech-to-Text Transformer)")
    print("=" * 80)
    print(f"\n비디오 ID: {video_id}")
    print(f"모델 크기: {model_size}")
    print(f"출력 디렉토리: {output_dir}")
    
    # Step 1: yt-dlp로 오디오 다운로드
    print("\n[1/3] 오디오 다운로드 중...")
    try:
        import yt_dlp
    except ImportError:
        print("❌ yt-dlp가 설치되지 않았습니다.")
        print("설치: pip install yt-dlp")
        return False
    
    output_audio = f"temp_{video_id}.mp3"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_audio.replace('.mp3', ''),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/watch?v={video_id}"
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
        print(f"✓ 다운로드 완료: {video_title}")
        print(f"  길이: {duration // 60}분 {duration % 60}초")
        
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        print("\n대안: ffmpeg가 설치되어 있는지 확인하세요")
        print("  Mac: brew install ffmpeg")
        print("  Ubuntu: sudo apt-get install ffmpeg")
        return False
    
    # Step 2: Whisper로 변환
    print("\n[2/3] Whisper로 자막 생성 중...")
    print(f"⏳ 모델 로딩 중... (처음엔 다운로드 시간 소요)")
    
    try:
        import whisper
    except ImportError:
        print("❌ Whisper가 설치되지 않았습니다.")
        print("설치: pip install openai-whisper")
        if os.path.exists(output_audio):
            os.remove(output_audio)
        return False
    
    try:
        # Whisper 모델 로드
        model = whisper.load_model(model_size)
        
        print(f"✓ 모델 로드 완료 ({model_size})")
        print("⏳ 음성 인식 중... (시간이 걸릴 수 있습니다)")
        
        # 음성 인식 수행
        result = model.transcribe(
            output_audio,
            language="ko",  # 한국어
            fp16=False  # CPU 호환
        )
        
        transcript = result["text"]
        
        print("✓ 변환 완료!")
        print(f"  감지된 언어: {result.get('language', 'unknown')}")
        print(f"  텍스트 길이: {len(transcript)} 글자")
        
    except Exception as e:
        print(f"❌ Whisper 변환 실패: {e}")
        if os.path.exists(output_audio):
            os.remove(output_audio)
        return False
    
    # Step 3: 결과 저장
    print("\n[3/3] 결과 저장...")
    
    output_file = output_dir / f"{video_id}_whisper_transcript.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Video ID: {video_id}\n")
        f.write(f"Title: {video_title}\n")
        f.write(f"Model: whisper-{model_size}\n")
        f.write("-" * 80 + "\n\n")
        f.write(transcript)
    
    print(f"✓ 저장 완료: {output_file}")
    
    # 정리: 임시 오디오 파일 삭제
    if os.path.exists(output_audio):
        os.remove(output_audio)
        print("✓ 임시 파일 삭제")
    
    # 결과 미리보기
    print("\n" + "=" * 80)
    print("📝 생성된 자막 미리보기:")
    print("=" * 80)
    preview = transcript[:500] + "..." if len(transcript) > 500 else transcript
    print(preview)
    print("\n" + "=" * 80)
    print(f"✅ 완료! 전체 내용: {output_file}")
    print("=" * 80)
    
    # 통계
    print(f"\n📊 통계:")
    print(f"  비디오 길이: {duration}초")
    print(f"  텍스트 길이: {len(transcript)}자")
    print(f"  단어 수: {len(transcript.split())}개")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Whisper로 YouTube 비디오 자막 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python stt_whisper.py 15TdCFjSzCk
  python stt_whisper.py QFCLUZWNtQs --model small
  
모델 크기 (크기 ↑ = 정확도 ↑, 속도 ↓):
  tiny   - 가장 빠름, 부정확 (39M params)
  base   - 빠름, 적당함 (74M) [기본값]
  small  - 중간 (244M)
  medium - 느림, 정확 (769M)
  large  - 가장 느림, 가장 정확 (1550M)
  
필요 패키지:
  pip install openai-whisper yt-dlp
  
ffmpeg 필요:
  Mac: brew install ffmpeg
  Ubuntu: sudo apt-get install ffmpeg
        """
    )
    
    parser.add_argument(
        'video_id',
        help='YouTube 비디오 ID (예: 15TdCFjSzCk)'
    )
    
    parser.add_argument(
        '--model',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='base',
        help='Whisper 모델 크기 (기본값: base)'
    )
    
    parser.add_argument(
        '--output-dir',
        default=OUTPUT_DIR,
        help=f'출력 디렉토리 (기본값: {OUTPUT_DIR})'
    )
    
    args = parser.parse_args()
    
    print("\n⚠️  주의사항:")
    print("  - 처음 실행 시 모델 다운로드로 시간이 걸립니다")
    print("  - CPU에서는 느릴 수 있습니다 (GPU 권장)")
    print("  - 20분 비디오 = CPU 30분~1시간, GPU 5~10분")
    print()
    
    success = test_whisper_single_video(args.video_id, args.model, args.output_dir)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()