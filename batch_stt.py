#!/usr/bin/env python3
"""
병렬로 여러 YouTube 비디오의 자막 생성 (개선 버전)
- 메모리 관리 강화
- 리소스 모니터링
- 안전한 종료 처리
"""

import json
import os
import sys
import argparse
import psutil
import gc
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict
import time
import signal

# stt_whisper 모듈 import
try:
    from stt_whisper import test_whisper_single_video
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from stt_whisper import test_whisper_single_video
    except ImportError:
        print("❌ stt_whisper.py를 찾을 수 없습니다.")
        sys.exit(1)


def get_memory_usage():
    """현재 메모리 사용량 조회"""
    process = psutil.Process()
    mem_info = process.memory_info()
    system_mem = psutil.virtual_memory()
    return {
        'process_mb': mem_info.rss / 1024 / 1024,
        'system_percent': system_mem.percent,
        'system_available_gb': system_mem.available / 1024 / 1024 / 1024
    }


def process_video_wrapper(video_id: str, model_size: str, output_dir: Path) -> Dict:
    """
    프로세스 풀에서 실행될 wrapper 함수
    메모리 관리와 예외 처리 강화
    """
    result = {
        'video_id': video_id,
        'success': False,
        'error': None,
        'duration': 0,
        'skipped': False
    }
    
    # 이미 처리된 경우
    output_file = output_dir / f"{video_id}_whisper_transcript.txt"
    if output_file.exists():
        result['success'] = True
        result['skipped'] = True
        return result
    
    start_time = time.time()
    
    try:
        # 메모리 체크
        mem = get_memory_usage()
        if mem['system_percent'] > 90:
            result['error'] = f"시스템 메모리 부족 ({mem['system_percent']:.1f}%)"
            return result
        
        # 처리 전 가비지 컬렉션
        gc.collect()
        
        # 실제 처리
        success = test_whisper_single_video(
            video_id=video_id,
            model_size=model_size,
            output_dir=output_dir
        )
        
        result['duration'] = time.time() - start_time
        result['success'] = success
        
        # 처리 후 메모리 정리
        gc.collect()
        
    except MemoryError as e:
        result['error'] = f"메모리 부족: {str(e)}"
        gc.collect()
    
    except Exception as e:
        result['error'] = str(e)
    
    finally:
        result['duration'] = time.time() - start_time
    
    return result


class BatchWhisperProcessor:
    """배치 Whisper 처리기 (개선 버전)"""
    
    def __init__(
        self, 
        videos_json: str = "data/chimchakman_official_videos.json",
        output_dir: str = "data/chimchakman_official_transcripts",
        model_size: str = "base",
        max_workers: int = 2,
        memory_threshold: float = 85.0
    ):
        """
        초기화
        
        Args:
            videos_json: 비디오 목록 JSON 파일
            output_dir: 출력 디렉토리
            model_size: Whisper 모델 크기
            max_workers: 최대 병렬 프로세스 수
            memory_threshold: 메모리 임계값 (%)
        """
        self.videos_json = Path(videos_json)
        self.output_dir = Path(output_dir)
        self.model_size = model_size
        self.max_workers = max_workers
        self.memory_threshold = memory_threshold
        self.shutdown_requested = False
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print("\n\n⚠️  종료 신호 받음. 안전하게 종료합니다...")
        self.shutdown_requested = True
    
    def load_video_ids(self) -> List[str]:
        """videos.json에서 video_id 목록 로드"""
        
        if not self.videos_json.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {self.videos_json}")
            return []
        
        try:
            with open(self.videos_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            video_ids = []
            
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'video_id' in item:
                        video_ids.append(item['video_id'])
                    elif isinstance(item, str):
                        video_ids.append(item)
            
            elif isinstance(data, dict):
                if 'videos' in data:
                    for item in data['videos']:
                        if isinstance(item, dict) and 'video_id' in item:
                            video_ids.append(item['video_id'])
                        elif isinstance(item, str):
                            video_ids.append(item)
                elif 'video_ids' in data:
                    video_ids = data['video_ids']
            
            print(f"✓ {len(video_ids)}개 비디오 ID 로드됨")
            return video_ids
            
        except Exception as e:
            print(f"❌ 파일 로드 오류: {e}")
            return []
    
    def check_system_resources(self) -> bool:
        """시스템 리소스 체크"""
        mem = get_memory_usage()
        
        if mem['system_percent'] > self.memory_threshold:
            print(f"\n⚠️  메모리 사용량 높음: {mem['system_percent']:.1f}%")
            print(f"   사용 가능: {mem['system_available_gb']:.1f}GB")
            return False
        
        return True
    
    def process_batch(self, video_ids: List[str] = None) -> Dict:
        """
        배치 처리 (병렬, 리소스 모니터링 포함)
        
        Args:
            video_ids: 처리할 비디오 ID 목록
            
        Returns:
            처리 결과 통계
        """
        if video_ids is None:
            video_ids = self.load_video_ids()
        
        if not video_ids:
            print("❌ 처리할 비디오가 없습니다.")
            return {}
        
        # 시스템 정보 출력
        mem = get_memory_usage()
        cpu_count = psutil.cpu_count(logical=False)
        
        print("\n" + "="*80)
        print(f"🚀 배치 Whisper 처리 시작")
        print("="*80)
        print(f"  총 비디오: {len(video_ids)}개")
        print(f"  병렬 워커: {self.max_workers}개")
        print(f"  모델: whisper-{self.model_size}")
        print(f"  출력: {self.output_dir}")
        print(f"\n💻 시스템 정보:")
        print(f"  CPU 코어: {cpu_count}개")
        print(f"  메모리: {mem['system_available_gb']:.1f}GB 사용 가능 ({mem['system_percent']:.1f}% 사용 중)")
        print(f"  메모리 임계값: {self.memory_threshold}%")
        print("="*80 + "\n")
        
        # 통계 초기화
        stats = {
            'total': len(video_ids),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'memory_warnings': 0
        }
        
        start_time = time.time()
        completed = 0
        
        # 병렬 처리
        try:
            # ProcessPoolExecutor에 명시적으로 maxtasksperchild 설정
            # 각 워커가 N개 작업 후 재시작 (메모리 누수 방지)
            with ProcessPoolExecutor(
                max_workers=self.max_workers,
                max_tasks_per_child=5  # Python 3.11+에서 지원
            ) as executor:
                
                # 작업 제출 (한 번에 모두 제출하지 않고 제어)
                pending_videos = list(video_ids)
                active_futures = {}
                
                # 초기 배치 제출
                initial_batch = min(self.max_workers * 2, len(pending_videos))
                for _ in range(initial_batch):
                    if pending_videos and not self.shutdown_requested:
                        video_id = pending_videos.pop(0)
                        future = executor.submit(
                            process_video_wrapper,
                            video_id,
                            self.model_size,
                            self.output_dir
                        )
                        active_futures[future] = video_id
                
                # 결과 수집 및 새 작업 제출
                while active_futures and not self.shutdown_requested:
                    # 완료된 작업 찾기
                    done_futures = [f for f in active_futures if f.done()]
                    
                    for future in done_futures:
                        video_id = active_futures.pop(future)
                        completed += 1
                        
                        try:
                            result = future.result(timeout=1)
                            
                            # 진행률 표시
                            progress = f"[{completed}/{len(video_ids)}]"
                            
                            if result.get('skipped'):
                                stats['skipped'] += 1
                                print(f"{progress} ⏭️  건너뜀: {video_id}")
                            elif result['success']:
                                stats['success'] += 1
                                print(f"{progress} ✅ 완료: {video_id} ({result['duration']:.1f}초)")
                            else:
                                stats['failed'] += 1
                                error_msg = result.get('error', 'Unknown error')
                                stats['errors'].append({
                                    'video_id': video_id,
                                    'error': error_msg
                                })
                                print(f"{progress} ❌ 실패: {video_id} - {error_msg}")
                            
                            # 리소스 체크
                            if completed % 5 == 0:  # 5개마다 체크
                                mem = get_memory_usage()
                                if mem['system_percent'] > self.memory_threshold:
                                    stats['memory_warnings'] += 1
                                    print(f"\n⚠️  메모리 높음: {mem['system_percent']:.1f}% - 잠시 대기...")
                                    time.sleep(10)  # 10초 대기
                                    gc.collect()
                            
                            # 새 작업 제출
                            if pending_videos and self.check_system_resources():
                                video_id = pending_videos.pop(0)
                                future = executor.submit(
                                    process_video_wrapper,
                                    video_id,
                                    self.model_size,
                                    self.output_dir
                                )
                                active_futures[future] = video_id
                        
                        except Exception as e:
                            stats['failed'] += 1
                            stats['errors'].append({
                                'video_id': video_id,
                                'error': str(e)
                            })
                            print(f"❌ 예외: {video_id} - {e}")
                    
                    # CPU 과부하 방지
                    if active_futures:
                        time.sleep(0.1)
                
                # 종료 요청 시 남은 작업 취소
                if self.shutdown_requested:
                    print("\n⚠️  남은 작업 취소 중...")
                    for future in active_futures:
                        future.cancel()
        
        except KeyboardInterrupt:
            print("\n\n⚠️  사용자가 중단했습니다.")
            self.shutdown_requested = True
        
        except Exception as e:
            print(f"\n❌ 치명적 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 최종 통계
        total_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("✨ 배치 처리 완료!" if not self.shutdown_requested else "⚠️  배치 처리 중단됨")
        print("="*80)
        print(f"  ✅ 성공: {stats['success']}개")
        print(f"  ⏭️  건너뜀: {stats['skipped']}개")
        print(f"  ❌ 실패: {stats['failed']}개")
        print(f"  📊 총: {stats['total']}개 중 {completed}개 처리")
        print(f"  ⏱️  소요 시간: {total_time/60:.1f}분")
        if completed > 0:
            print(f"  ⚡ 평균 속도: {total_time/completed:.1f}초/비디오")
        if stats['memory_warnings'] > 0:
            print(f"  ⚠️  메모리 경고: {stats['memory_warnings']}회")
        
        if stats['failed'] > 0:
            print(f"\n❌ 실패한 비디오 ({stats['failed']}개):")
            for error in stats['errors'][:10]:
                print(f"  - {error['video_id']}: {error['error'][:100]}")
            if len(stats['errors']) > 10:
                print(f"  ... 외 {len(stats['errors']) - 10}개")
        
        print("="*80 + "\n")
        
        return stats


def main():
    parser = argparse.ArgumentParser(
        description='병렬로 여러 YouTube 비디오의 자막 생성 (개선 버전)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 안전한 기본 실행 (워커 2개)
  python batch_whisper.py
  
  # 워커 수 조정 (메모리 충분할 때)
  python batch_whisper.py --workers 4
  
  # 메모리 임계값 조정
  python batch_whisper.py --workers 4 --memory-threshold 80
  
  # 작은 모델로 더 많은 워커
  python batch_whisper.py --model tiny --workers 8
        """
    )
    
    parser.add_argument('--videos', default='data/chimchakman_official_videos.json')
    parser.add_argument('--output-dir', default='data/chimchakman_official_transcripts')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'], default='base')
    parser.add_argument('--video-ids', nargs='+')
    parser.add_argument('--workers', type=int, default=2, help='병렬 워커 수 (권장: 2-4)')
    parser.add_argument('--memory-threshold', type=float, default=85.0, 
                       help='메모리 임계값 %% (기본: 85)')
    
    args = parser.parse_args()
    
    # 워커 수 검증
    cpu_count = psutil.cpu_count(logical=False)
    if args.workers > cpu_count:
        print(f"⚠️  워커 수({args.workers})가 물리 코어 수({cpu_count})보다 많습니다.")
        print(f"   권장: {min(4, cpu_count)}개 이하")
    
    # 프로세서 생성
    processor = BatchWhisperProcessor(
        videos_json=args.videos,
        output_dir=args.output_dir,
        model_size=args.model,
        max_workers=args.workers,
        memory_threshold=args.memory_threshold
    )
    
    # 처리할 비디오 ID 결정
    video_ids = args.video_ids if args.video_ids else None
    
    # 배치 처리 실행
    try:
        stats = processor.process_batch(video_ids)
        
        if stats and stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  프로그램이 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 치명적 오류: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()