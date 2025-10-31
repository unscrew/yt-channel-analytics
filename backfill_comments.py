#!/usr/bin/env python3
"""
댓글 백필 스크립트
data/chimchakman_official_comments 디렉토리의 JSON 파일들을 검사하여
comments 필드가 비어있으면 YouTube API를 통해 댓글을 가져와서 채웁니다.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from googleapiclient.discovery import build
from dotenv import load_dotenv
import time

# 환경변수 로드
load_dotenv()


class CommentBackfiller:
    """댓글 백필 클래스"""
    
    def __init__(self, api_key: str, comments_dir: str = "data/chimchakman_official_comments"):
        """
        초기화
        
        Args:
            api_key: YouTube Data API v3 키
            comments_dir: 댓글 JSON 파일들이 있는 디렉토리
        """
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.comments_dir = Path(comments_dir)
        
    def load_json_file(self, filepath: Path) -> Dict:
        """JSON 파일 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_json_file(self, filepath: Path, data: Dict):
        """JSON 파일 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        """
        YouTube API로 댓글 가져오기
        
        Args:
            video_id: 비디오 ID
            max_results: 최대 댓글 수
            
        Returns:
            댓글 리스트
        """
        comments = []
        
        try:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                order="relevance",
                textFormat="plainText"
            )
            
            while request and len(comments) < max_results:
                response = request.execute()
                
                for item in response['items']:
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comment_data = {
                        'author': snippet['authorDisplayName'],
                        'text': snippet['textDisplay'],
                        'likeCount': snippet['likeCount'],
                        'publishedAt': snippet['publishedAt']
                    }
                    comments.append(comment_data)
                
                # 다음 페이지가 있으면 계속
                if 'nextPageToken' in response and len(comments) < max_results:
                    request = self.youtube.commentThreads().list(
                        part="snippet",
                        videoId=video_id,
                        maxResults=min(max_results - len(comments), 100),
                        pageToken=response['nextPageToken'],
                        order="relevance",
                        textFormat="plainText"
                    )
                else:
                    break
                    
                # API rate limit 고려하여 잠시 대기
                time.sleep(0.1)
                
        except Exception as e:
            print(f"  ⚠️  댓글 가져오기 실패: {e}")
            
        return comments
    
    def needs_backfill(self, data: Dict) -> bool:
        """
        백필이 필요한지 확인
        
        Args:
            data: JSON 데이터
            
        Returns:
            백필 필요 여부
        """
        # comments 필드가 없거나 비어있으면 백필 필요
        return 'comments' not in data or not data['comments']
    
    def backfill_file(self, filepath: Path) -> bool:
        """
        단일 파일 백필
        
        Args:
            filepath: JSON 파일 경로
            
        Returns:
            백필 성공 여부
        """
        try:
            # JSON 파일 로드
            data = self.load_json_file(filepath)
            
            # 백필이 필요한지 확인
            if not self.needs_backfill(data):
                return False
            
            video_id = data.get('video_id')
            if not video_id:
                print(f"  ⚠️  video_id 없음: {filepath.name}")
                return False
            
            print(f"  🔄 백필 중: {video_id}")
            
            # 댓글 가져오기
            comments = self.get_comments(video_id)
            
            # 데이터 업데이트
            data['comments'] = comments
            data['comment_count'] = len(comments)
            
            # 파일 저장
            self.save_json_file(filepath, data)
            
            print(f"  ✅ 완료: {len(comments)}개 댓글 추가됨")
            return True
            
        except Exception as e:
            print(f"  ❌ 오류: {filepath.name} - {e}")
            return False
    
    def backfill_all(self):
        """디렉토리 내 모든 파일 백필"""
        
        if not self.comments_dir.exists():
            print(f"❌ 디렉토리를 찾을 수 없습니다: {self.comments_dir}")
            return
        
        # JSON 파일 목록
        json_files = list(self.comments_dir.glob("*.json"))
        
        if not json_files:
            print(f"❌ JSON 파일을 찾을 수 없습니다: {self.comments_dir}")
            return
        
        print(f"\n📁 {len(json_files)}개 파일 검사 중...\n")
        
        backfilled = 0
        skipped = 0
        failed = 0
        
        for filepath in json_files:
            print(f"📄 {filepath.name}")
            
            result = self.backfill_file(filepath)
            
            if result is True:
                backfilled += 1
            elif result is False:
                skipped += 1
            else:
                failed += 1
            
            print()  # 빈 줄
        
        # 결과 요약
        print("=" * 50)
        print(f"\n✨ 백필 완료!")
        print(f"  ✅ 백필됨: {backfilled}개")
        print(f"  ⏭️  건너뜀: {skipped}개")
        print(f"  ❌ 실패: {failed}개")
        print(f"  📊 총: {len(json_files)}개\n")


def main():
    """메인 함수"""
    
    # API 키 확인
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("❌ YOUTUBE_API_KEY 환경변수를 설정해주세요.")
        print("   .env 파일에 YOUTUBE_API_KEY=your_key_here 추가")
        return
    
    # 백필러 생성 및 실행
    backfiller = CommentBackfiller(api_key)
    backfiller.backfill_all()


if __name__ == "__main__":
    main()