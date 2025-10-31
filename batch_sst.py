#!/usr/bin/env python3
"""
병렬로 여러 YouTube 비디오의 자막 생성
data/chimchakman_official_videos.json 에서 video_id 읽어서 처리
"""

import json
import os
import sys
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict
import time

# stt_whisper 모듈 import
try:
    from stt_whisper import test_whisper_single_video
except ImportError:
    # 현재 디렉토리에서 import
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from stt_whisper import test_whisper_single_video
    except ImportError:
        print("❌ stt_whisper.py를 찾을 수 없습니다.")
        print("   batch_whisper.py와 stt_whisper.py를 같은 디렉토리에 두세요.")
        sys.exit(1)


class BatchWhisperProcessor:
    """배치 Whisper 처리기"""
    
    def __init__(
        self, 
        videos_json: str = "data/chimchakman_official_videos.json",
        output_dir: str = "data/chimchakman_official_transcripts",
        model_size: str = "base",
        max_workers: int = 2
    ):
        """
        초기화
        
        Args:
            videos_json: 비디오 목록 JSON 파일
            output_dir: 출력 디렉토리
            model_size: Whisper 모델 크기
            max_workers: 최대 병렬 프로세스 수 (기본값: 2)
        """
        self.videos_json = Path(videos_json)
        self.output_dir = Path(output_dir)
        self.model_size = model_size
        self.max_workers = max_workers
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_video_ids(self) -> List[str]:
        """videos.json에서 video_id 목록 로드"""
        
        if not self.videos_json.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {self.videos_json}")
            return []
        
        try:
            with open(self.videos_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 데이터 구조에 따라 video_id 추출
            video_ids = []
            
            if isinstance(data, list):
                # 리스트 형태: [{"video_id": "..."}, ...]
                for item in data:
                    if isinstance(item, dict) and 'video_id' in item:
                        video_ids.append(item['video_id'])
                    elif isinstance(item, str):
                        video_ids.append(item)
            
            elif isinstance(data, dict):
                # 딕셔너리 형태
                if 'videos' in data:
                    # {"videos": [{"video_id": "..."}, ...]}
                    for item in data['videos']:
                        if isinstance(item, dict) and 'video_id' in item:
                            video_ids.append(item['video_id'])
                        elif isinstance(item, str):
                            video_ids.append(item)
                elif 'video_ids' in data:
                    # {"video_ids": ["...", "..."]}
                    video_ids = data['video_ids']
            
            print(f"✓ {len(video_ids)}개 비디오 ID 로드됨")
            return video_ids
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            return []
        except Exception as e:
            print(f"❌ 파일 로드 오류: {e}")
            return []
    
    def is_already_processed(self, video_id: str) -> bool:
        """이미 처리된 비디오인지 확인"""
        output_file = self.output_dir / f"{video_id}_whisper_transcript.txt"
        return output_file.exists()
    
    def process_single_video(self, video_id: str) -> Dict:
        """
        단일 비디오 처리 (직접 함수 호출)
        
        Args:
            video_id: 비디오 ID
            
        Returns:
            처리 결과 딕셔너리
        """
        result = {
            'video_id': video_id,
            'success': False,
            'error': None,
            'duration': 0
        }
        
        # 이미 처리된 경우 건너뛰기
        if self.is_already_processed(video_id):
            print(f"⏭️  건너뜀: {video_id} (이미 처리됨)")
            result['success'] = True
            result['skipped'] = True
            return result
        
        print(f"🔄 처리 중: {video_id}")
        start_time = time.time()
        
        try:
            # stt_whisper.py의 함수 직접 호출
            success = test_whisper_single_video(
                video_id=video_id,
                model_size=self.model_size,
                output_dir=self.output_dir
            )
            
            result['duration'] = time.time() - start_time
            result['success'] = success
            
            if success:
                print(f"✅ 완료: {video_id} ({result['duration']:.1f}초)")
            else:
                print(f"❌ 실패: {video_id}")
        
        except KeyboardInterrupt:
            # Ctrl+C 처리
            print(f"\n⚠️  중단됨: {video_id}")
            result['error'] = "User interrupted"
            raise
        
        except Exception as e:
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            print(f"❌ 오류: {video_id} - {e}")
        
        return result
    
    def process_batch(self, video_ids: List[str] = None) -> Dict:
        """
        배치 처리 (순차)
        
        Args:
            video_ids: 처리할 비디오 ID 목록 (None이면 전체)
            
        Returns:
            처리 결과 통계
        """
        if video_ids is None:
            video_ids = self.load_video_ids()
        
        if not video_ids:
            print("❌ 처리할 비디오가 없습니다.")
            return {}
        
        print("\n" + "="*80)
        print(f"🚀 배치 Whisper 처리 시작")
        print("="*80)
        print(f"  총 비디오: {len(video_ids)}개")
        print(f"  모델: whisper-{self.model_size}")
        print(f"  출력: {self.output_dir}")
        print("="*80 + "\n")
        
        # 통계 초기화
        stats = {
            'total': len(video_ids),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        # 순차 처리
        for i, video_id in enumerate(video_ids, 1):
            print(f"\n[{i}/{len(video_ids)}] ", end="")
            
            try:
                result = self.process_single_video(video_id)
                
                if result.get('skipped'):
                    stats['skipped'] += 1
                elif result['success']:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                    if result.get('error'):
                        stats['errors'].append({
                            'video_id': video_id,
                            'error': result['error']
                        })
            
            except KeyboardInterrupt:
                print("\n\n⚠️  사용자가 중단했습니다.")
                break
            
            except Exception as e:
                stats['failed'] += 1
                stats['errors'].append({
                    'video_id': video_id,
                    'error': str(e)
                })
                print(f"❌ 예외 발생: {video_id} - {e}")
        
        # 최종 통계
        total_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("✨ 배치 처리 완료!")
        print("="*80)
        print(f"  ✅ 성공: {stats['success']}개")
        print(f"  ⏭️  건너뜀: {stats['skipped']}개")
        print(f"  ❌ 실패: {stats['failed']}개")
        print(f"  📊 총: {stats['total']}개")
        print(f"  ⏱️  소요 시간: {total_time/60:.1f}분")
        
        if stats['failed'] > 0:
            print(f"\n❌ 실패한 비디오 ({stats['failed']}개):")
            for error in stats['errors'][:10]:  # 최대 10개만 표시
                print(f"  - {error['video_id']}: {error['error'][:100]}")
            if len(stats['errors']) > 10:
                print(f"  ... 외 {len(stats['errors']) - 10}개")
        
        print("="*80 + "\n")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='병렬로 여러 YouTube 비디오의 자막 생성',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 실행
  python batch_whisper.py
  
  # 다른 JSON 파일 사용
  python batch_whisper.py --videos my_videos.json
  
  # 모델 크기 변경
  python batch_whisper.py --model small
  
  # 특정 비디오만 처리
  python batch_whisper.py --video-ids 15TdCFjSzCk QFCLUZWNtQs
        """
    )
    
    parser.add_argument(
        '--videos',
        default='data/chimchakman_official_videos.json',
        help='비디오 목록 JSON 파일 경로'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/chimchakman_official_transcripts',
        help='출력 디렉토리'
    )
    
    parser.add_argument(
        '--model',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='base',
        help='Whisper 모델 크기 (기본값: base)'
    )
    
    parser.add_argument(
        '--video-ids',
        nargs='+',
        help='특정 비디오 ID만 처리 (공백으로 구분)'
    )
    
    args = parser.parse_args()
    
    # 프로세서 생성
    processor = BatchWhisperProcessor(
        videos_json=args.videos,
        output_dir=args.output_dir,
        model_size=args.model,
        max_workers=1  # 순차 처리
    )
    
    # 처리할 비디오 ID 결정
    if args.video_ids:
        video_ids = args.video_ids
        print(f"📋 커맨드라인에서 {len(video_ids)}개 비디오 ID 제공됨")
    else:
        video_ids = None  # 전체 처리
    
    # 배치 처리 실행
    try:
        stats = processor.process_batch(video_ids)
        
        # 종료 코드
        if stats and stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  프로그램이 중단되었습니다.")
        sys.exit(130)


if __name__ == '__main__':
    main()