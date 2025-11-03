#!/usr/bin/env python3
"""
오디오 캐시 정리 스크립트
transcript가 있는 비디오의 오디오 파일만 삭제
"""

from pathlib import Path
import os


def cleanup_processed_audio():
    """
    처리 완료된 비디오의 오디오 파일 삭제
    (transcript 있으면 오디오 삭제)
    """
    
    audio_dir = Path("data/tmp")
    transcript_dir = Path("data/chimchakman_official_transcripts")
    
    if not audio_dir.exists():
        print("❌ data/tmp 디렉토리가 없습니다.")
        return
    
    if not transcript_dir.exists():
        print("❌ transcript 디렉토리가 없습니다.")
        return
    
    print("="*80)
    print("🧹 오디오 캐시 정리")
    print("="*80)
    
    # 모든 오디오 파일
    audio_files = list(audio_dir.glob("*.mp3"))
    print(f"\n총 오디오 파일: {len(audio_files)}개")
    
    deleted = 0
    kept = 0
    saved_space = 0
    
    for audio_file in audio_files:
        # 비디오 ID 추출
        video_id = audio_file.stem
        
        # transcript 파일 확인
        transcript_file = transcript_dir / f"{video_id}_whisper_transcript.txt"
        
        if transcript_file.exists():
            # transcript 있으면 오디오 삭제
            file_size = audio_file.stat().st_size
            audio_file.unlink()
            deleted += 1
            saved_space += file_size
            print(f"✓ 삭제: {audio_file.name} ({file_size / (1024*1024):.1f} MB)")
        else:
            # transcript 없으면 보존 (처리 중이거나 실패)
            kept += 1
    
    # 결과 요약
    print("\n" + "="*80)
    print("✨ 정리 완료!")
    print("="*80)
    print(f"  🗑️  삭제됨: {deleted}개")
    print(f"  📁 보존됨: {kept}개 (미처리)")
    print(f"  💾 절약된 공간: {saved_space / (1024*1024*1024):.2f} GB")
    print("="*80)


def cleanup_all_audio():
    """
    모든 오디오 파일 삭제 (강제)
    """
    
    audio_dir = Path("data/tmp")
    
    if not audio_dir.exists():
        print("❌ data/tmp 디렉토리가 없습니다.")
        return
    
    print("="*80)
    print("⚠️  모든 오디오 파일 삭제 (강제)")
    print("="*80)
    
    confirm = input("\n정말 모든 오디오 파일을 삭제하시겠습니까? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("취소되었습니다.")
        return
    
    audio_files = list(audio_dir.glob("*.mp3"))
    total_size = sum(f.stat().st_size for f in audio_files)
    
    for audio_file in audio_files:
        audio_file.unlink()
    
    print(f"\n✓ {len(audio_files)}개 파일 삭제됨")
    print(f"  💾 절약된 공간: {total_size / (1024*1024*1024):.2f} GB")


def show_audio_stats():
    """
    오디오 캐시 통계 표시
    """
    
    audio_dir = Path("data/tmp")
    transcript_dir = Path("data/chimchakman_official_transcripts")
    
    if not audio_dir.exists():
        print("❌ data/tmp 디렉토리가 없습니다.")
        return
    
    audio_files = list(audio_dir.glob("*.mp3"))
    total_size = sum(f.stat().st_size for f in audio_files)
    
    # 처리 완료된 것 vs 미처리
    processed = 0
    unprocessed = 0
    
    for audio_file in audio_files:
        video_id = audio_file.stem
        transcript_file = transcript_dir / f"{video_id}_whisper_transcript.txt"
        
        if transcript_file.exists():
            processed += 1
        else:
            unprocessed += 1
    
    print("="*80)
    print("📊 오디오 캐시 통계")
    print("="*80)
    print(f"\n총 오디오 파일: {len(audio_files)}개")
    print(f"  ✅ 처리 완료: {processed}개 (삭제 가능)")
    print(f"  ⏳ 미처리: {unprocessed}개 (보존 필요)")
    print(f"\n총 용량: {total_size / (1024*1024*1024):.2f} GB")
    
    if processed > 0:
        can_save = sum(
            (audio_dir / f"{(transcript_dir / f.name).stem}.mp3").stat().st_size
            for f in transcript_dir.glob("*.txt")
            if (audio_dir / f"{f.stem.replace('_whisper_transcript', '')}.mp3").exists()
        )
        print(f"  💾 삭제 가능 공간: {can_save / (1024*1024*1024):.2f} GB")
    
    print("="*80)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'clean':
            # 처리 완료된 것만 삭제
            cleanup_processed_audio()
        
        elif command == 'clean-all':
            # 모든 오디오 삭제 (강제)
            cleanup_all_audio()
        
        elif command == 'stats':
            # 통계만 표시
            show_audio_stats()
        
        else:
            print("❌ 잘못된 명령어")
            print("\n사용법:")
            print("  python cleanup_audio.py stats      # 통계 보기")
            print("  python cleanup_audio.py clean      # 처리 완료된 오디오 삭제")
            print("  python cleanup_audio.py clean-all  # 모든 오디오 삭제 (강제)")
    
    else:
        print("🧹 오디오 캐시 정리 스크립트")
        print("\n사용법:")
        print("  python cleanup_audio.py stats      # 통계 보기")
        print("  python cleanup_audio.py clean      # 처리 완료된 오디오 삭제")
        print("  python cleanup_audio.py clean-all  # 모든 오디오 삭제 (강제)")
        print("\n예시:")
        print("  # 1. 먼저 통계 확인")
        print("  python cleanup_audio.py stats")
        print("\n  # 2. 처리 완료된 것만 삭제")
        print("  python cleanup_audio.py clean")