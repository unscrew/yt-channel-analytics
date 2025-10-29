#!/usr/bin/env python3
"""
YouTube Channel Data Collector
Collects videos, transcripts, engagement stats, and comments from YouTube channels.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class YouTubeDataCollector:
    """YouTube channel data collector."""
    
    def __init__(self, api_key: str, max_workers: int = 5):
        """Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key
            max_workers: Number of parallel workers for transcript fetching
        """
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.max_workers = max_workers
        self.request_delay = 0.5  # Delay between requests to avoid rate limiting
    
    def get_channel_info(self, channel_id: str) -> Dict[str, str]:
        """Get channel information including custom URL/handle.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with channel_id and channel_slug
        """
        try:
            response = self.youtube.channels().list(
                part='snippet',
                id=channel_id
            ).execute()
            
            if response.get('items'):
                snippet = response['items'][0]['snippet']
                custom_url = snippet.get('customUrl', '').replace('@', '').replace('/', '')
                
                # Use custom URL as slug, fallback to channel title, then channel ID
                if custom_url:
                    channel_slug = custom_url
                else:
                    # Sanitize channel title for use as filename
                    channel_slug = snippet['title'].replace(' ', '_').replace('/', '_')
                    # Remove special characters
                    import re
                    channel_slug = re.sub(r'[^\w\-_]', '', channel_slug)
                
                logger.info(f"채널 정보: {snippet['title']}")
                logger.info(f"채널 슬러그: {channel_slug}")
                
                return {
                    'channel_id': channel_id,
                    'channel_slug': channel_slug,
                    'channel_title': snippet['title']
                }
        except HttpError as e:
            logger.error(f"채널 정보 가져오기 실패: {e}")
        
        # Fallback to channel ID
        return {
            'channel_id': channel_id,
            'channel_slug': channel_id,
            'channel_title': channel_id
        }
    
    def get_channel_id(self, channel_input: str) -> Optional[str]:
        """Get channel ID from URL or validate existing ID.
        
        Args:
            channel_input: Channel URL or ID
            
        Returns:
            Channel ID or None if not found
        """
        logger.info(f"채널 ID 확인 중: {channel_input}")
        
        # If it looks like a channel ID already
        if channel_input.startswith('UC') and len(channel_input) == 24:
            return channel_input
        
        # Extract from URL patterns
        if 'youtube.com' in channel_input or 'youtu.be' in channel_input:
            if '/channel/' in channel_input:
                channel_id = channel_input.split('/channel/')[-1].split('/')[0].split('?')[0]
                return channel_id
            elif '/@' in channel_input or '/c/' in channel_input or '/user/' in channel_input:
                # Need to resolve custom URL to channel ID
                username = channel_input.split('/')[-1].split('?')[0].replace('@', '')
                try:
                    request = self.youtube.search().list(
                        part='snippet',
                        q=username,
                        type='channel',
                        maxResults=1
                    )
                    response = request.execute()
                    if response.get('items'):
                        return response['items'][0]['snippet']['channelId']
                except HttpError as e:
                    logger.error(f"채널 ID 조회 실패: {e}")
        
        return channel_input
    
    def fetch_channel_videos(self, channel_id: str, channel_slug: str, min_duration_seconds: int = 60) -> List[Dict]:
        """Fetch all long-form videos from a channel (excludes Shorts).
        
        Args:
            channel_id: YouTube channel ID
            min_duration_seconds: Minimum video duration in seconds (default: 60, filters out Shorts which are < 60s)
            
        Returns:
            List of video metadata dictionaries
        """
        logger.info(f"채널 {channel_id}의 롱폼 비디오 목록 가져오는 중...")
        logger.info(f"필터: {min_duration_seconds}초 이상의 비디오만 수집")
        videos = []
        
        try:
            # Get the uploads playlist ID
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channel_response.get('items'):
                logger.error(f"채널을 찾을 수 없습니다: {channel_id}")
                return videos
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            logger.info(f"업로드 플레이리스트 ID: {uploads_playlist_id}")
            
            # Fetch all videos from the uploads playlist
            next_page_token = None
            video_count = 0
            shorts_filtered = 0
            
            while True:
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                # Collect video IDs to fetch durations
                video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
                
                # Fetch video details including duration
                if video_ids:
                    videos_response = self.youtube.videos().list(
                        part='contentDetails,snippet',
                        id=','.join(video_ids)
                    ).execute()
                    
                    for video_item in videos_response.get('items', []):
                        # Parse ISO 8601 duration (e.g., PT1M30S = 1 min 30 sec)
                        duration_str = video_item['contentDetails']['duration']
                        duration_seconds = self._parse_duration(duration_str)
                        
                        # Filter out Shorts (videos under min_duration_seconds)
                        if duration_seconds >= min_duration_seconds:
                            video_data = {
                                'video_id': video_item['id'],
                                'title': video_item['snippet']['title'],
                                'description': video_item['snippet']['description'],
                                'published_at': video_item['snippet']['publishedAt'],
                                'thumbnail': video_item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                                'duration_seconds': duration_seconds,
                                'duration_formatted': self._format_duration(duration_seconds)
                            }
                            videos.append(video_data)
                            video_count += 1
                        else:
                            shorts_filtered += 1
                            logger.debug(f"Shorts 필터링: {video_item['snippet']['title']} ({duration_seconds}초)")
                
                logger.info(f"롱폼 비디오 {video_count}개 수집됨... (Shorts {shorts_filtered}개 제외)")
                
                next_page_token = playlist_response.get('nextPageToken')
                if not next_page_token:
                    break
                
                time.sleep(self.request_delay)
            
            # Sort by published date (newest first)
            videos.sort(key=lambda x: x['published_at'], reverse=True)
            logger.info(f"총 {len(videos)}개의 롱폼 비디오를 가져왔습니다. (Shorts {shorts_filtered}개 제외됨)")
            
        except HttpError as e:
            logger.error(f"비디오 목록 가져오기 실패: {e}")
        
        return videos
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds.
        
        Args:
            duration_str: ISO 8601 duration string (e.g., PT1H2M30S)
            
        Returns:
            Duration in seconds
        """
        import re
        
        # Remove 'PT' prefix
        duration_str = duration_str.replace('PT', '')
        
        # Extract hours, minutes, seconds
        hours = re.search(r'(\d+)H', duration_str)
        minutes = re.search(r'(\d+)M', duration_str)
        seconds = re.search(r'(\d+)S', duration_str)
        
        total_seconds = 0
        if hours:
            total_seconds += int(hours.group(1)) * 3600
        if minutes:
            total_seconds += int(minutes.group(1)) * 60
        if seconds:
            total_seconds += int(seconds.group(1))
        
        return total_seconds
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def save_videos_list(self, channel_slug: str, videos: List[Dict]) -> str:
        """Save videos list to file.
        
        Args:
            channel_slug: Channel slug/handle for filename
            videos: List of video metadata
            
        Returns:
            Path to saved file
        """
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        filename = f"data/{channel_slug}_videos.json"
        logger.info(f"비디오 목록을 {filename}에 저장 중...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 비디오 목록 저장 완료: {filename}")
        return filename
    
    def fetch_transcript(self, video_id: str) -> Optional[str]:
        """Fetch Korean transcript for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Transcript text or None if not available
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Create an instance of the API
            api = YouTubeTranscriptApi()
            
            # Get transcript list for the video
            transcript_list = api.list(video_id)
            
            # Find Korean transcript using find_transcript method
            korean_transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
            
            # Fetch the transcript data
            transcript_data = korean_transcript.fetch()
            full_text = '\n'.join([entry['text'] for entry in transcript_data])
            logger.info(f"✓ 비디오 {video_id} 한국어 자막 수집 완료")
            return full_text
            
        except NoTranscriptFound:
            logger.warning(f"⚠ 비디오 {video_id} 한국어 자막 없음")
            return None
        except TranscriptsDisabled:
            logger.warning(f"⚠ 비디오 {video_id} 자막 비활성화됨")
            return None
        except Exception as e:
            error_msg = str(e).lower()
            if 'subtitle' in error_msg or 'transcript' in error_msg or 'caption' in error_msg or 'no transcript' in error_msg:
                logger.warning(f"⚠ 비디오 {video_id} 한국어 자막 없음")
            else:
                logger.error(f"✗ 비디오 {video_id} 자막 가져오기 실패: {e}")
            return None
    
    def fetch_transcripts_parallel(self, channel_slug: str, videos: List[Dict]):
        """Fetch transcripts for all videos in parallel.
        
        Args:
            channel_slug: Channel slug/handle for directory name
            videos: List of video metadata
        """
        logger.info(f"병렬 프로세스로 자막 수집 시작 (워커: {self.max_workers})...")
        
        # Create output directory
        transcript_dir = f"data/{channel_slug}_transcripts"
        os.makedirs(transcript_dir, exist_ok=True)
        
        total_videos = len(videos)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_video = {
                executor.submit(self.fetch_transcript, video['video_id']): video
                for video in videos
            }
            
            # Process completed tasks
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                video_id = video['video_id']
                completed += 1
                
                try:
                    transcript = future.result()
                    if transcript:
                        transcript_file = os.path.join(transcript_dir, f"{video_id}_transcript.txt")
                        with open(transcript_file, 'w', encoding='utf-8') as f:
                            f.write(transcript)
                    
                    logger.info(f"진행률: {completed}/{total_videos} ({completed*100//total_videos}%)")
                    
                except Exception as e:
                    logger.error(f"비디오 {video_id} 처리 중 오류: {e}")
                
                # Rate limiting
                time.sleep(self.request_delay)
        
        logger.info(f"✓ 자막 수집 완료: {transcript_dir}/")
    
    def fetch_video_stats(self, video_id: str) -> Optional[Dict]:
        """Fetch engagement statistics for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary of engagement stats
        """
        try:
            response = self.youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()
            
            if response.get('items'):
                stats = response['items'][0]['statistics']
                engagement_data = {
                    'video_id': video_id,
                    'view_count': int(stats.get('viewCount', 0)),
                    'like_count': int(stats.get('likeCount', 0)),
                    'comment_count': int(stats.get('commentCount', 0)),
                    'favorite_count': int(stats.get('favoriteCount', 0)),
                    'collected_at': datetime.now().isoformat()
                }
                logger.info(f"✓ 비디오 {video_id} 참여도 통계 수집 완료")
                return engagement_data
            
        except HttpError as e:
            logger.error(f"✗ 비디오 {video_id} 통계 가져오기 실패: {e}")
        
        return None
    
    def fetch_all_video_stats(self, channel_slug: str, videos: List[Dict]):
        """Fetch engagement stats for all videos.
        
        Args:
            channel_slug: Channel slug/handle for directory name
            videos: List of video metadata
        """
        logger.info("비디오 참여도 통계 수집 중...")
        
        # Create output directory
        stats_dir = f"data/{channel_slug}_engagement_stats"
        os.makedirs(stats_dir, exist_ok=True)
        
        for idx, video in enumerate(videos, 1):
            video_id = video['video_id']
            stats = self.fetch_video_stats(video_id)
            
            if stats:
                stats_file = os.path.join(stats_dir, f"{video_id}_stats.json")
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"진행률: {idx}/{len(videos)} ({idx*100//len(videos)}%)")
            time.sleep(self.request_delay)
        
        logger.info(f"✓ 참여도 통계 수집 완료: {stats_dir}/")
    
    def fetch_video_comments(self, video_id: str) -> List[str]:
        """Fetch comments for a video (text only, no author metadata).
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of comment texts
        """
        comments = []
        
        try:
            next_page_token = None
            
            while True:
                response = self.youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page_token,
                    textFormat='plainText'
                ).execute()
                
                for item in response.get('items', []):
                    comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    comments.append(comment_text)
                    
                    # Get replies if any
                    if item['snippet']['totalReplyCount'] > 0:
                        try:
                            replies_response = self.youtube.comments().list(
                                part='snippet',
                                parentId=item['snippet']['topLevelComment']['id'],
                                maxResults=100,
                                textFormat='plainText'
                            ).execute()
                            
                            for reply in replies_response.get('items', []):
                                reply_text = reply['snippet']['textDisplay']
                                comments.append(reply_text)
                        except HttpError:
                            pass
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                
                time.sleep(self.request_delay)
            
            logger.info(f"✓ 비디오 {video_id} 댓글 {len(comments)}개 수집 완료")
            
        except HttpError as e:
            if 'commentsDisabled' in str(e):
                logger.warning(f"⚠ 비디오 {video_id} 댓글 비활성화됨")
            else:
                logger.error(f"✗ 비디오 {video_id} 댓글 가져오기 실패: {e}")
        
        return comments
    
    def fetch_all_comments(self, channel_slug: str, videos: List[Dict]):
        """Fetch comments for all videos.
        
        Args:
            channel_slug: Channel slug/handle for directory name
            videos: List of video metadata
        """
        logger.info("비디오 댓글 수집 중...")
        
        # Create output directory
        comments_dir = f"data/{channel_slug}_comments"
        os.makedirs(comments_dir, exist_ok=True)
        
        for idx, video in enumerate(videos, 1):
            video_id = video['video_id']
            comments = self.fetch_video_comments(video_id)
            
            comments_file = os.path.join(comments_dir, f"{video_id}_comments.json")
            with open(comments_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_id': video_id,
                    'comment_count': len(comments),
                    'comments': comments
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"진행률: {idx}/{len(videos)} ({idx*100//len(videos)}%)")
        
        logger.info(f"✓ 댓글 수집 완료: {comments_dir}/")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='YouTube 채널 데이터 수집 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python youtube_data_collector.py "https://www.youtube.com/@channelname"
  python youtube_data_collector.py UC1234567890 --skip-comments
  
환경변수:
  YOUTUBE_API_KEY를 .env 파일에 설정하거나 --api-key로 직접 전달
        """
    )
    parser.add_argument(
        'channel',
        help='YouTube 채널 URL 또는 ID'
    )
    parser.add_argument(
        '--api-key',
        help='YouTube Data API v3 키 (기본값: 환경변수 YOUTUBE_API_KEY)',
        default=os.getenv('YOUTUBE_API_KEY')
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='병렬 처리 워커 수 (기본값: 5)'
    )
    parser.add_argument(
        '--min-duration',
        type=int,
        default=60,
        help='최소 비디오 길이(초) - Shorts 필터링용 (기본값: 60)'
    )
    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='기존 비디오 목록 파일을 무시하고 새로 가져오기'
    )
    parser.add_argument(
        '--skip-transcripts',
        action='store_true',
        help='자막 수집 건너뛰기'
    )
    parser.add_argument(
        '--skip-stats',
        action='store_true',
        help='참여도 통계 수집 건너뛰기'
    )
    parser.add_argument(
        '--skip-comments',
        action='store_true',
        help='댓글 수집 건너뛰기'
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        logger.error("❌ API 키가 필요합니다!")
        logger.error("다음 중 하나를 수행하세요:")
        logger.error("  1. .env 파일에 YOUTUBE_API_KEY=your_key 추가")
        logger.error("  2. --api-key 옵션 사용")
        logger.error("  3. 환경변수 설정: export YOUTUBE_API_KEY=your_key")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("YouTube 채널 데이터 수집 시작")
    logger.info("=" * 60)
    
    # Initialize collector
    collector = YouTubeDataCollector(args.api_key, args.max_workers)
    
    # Get channel ID
    channel_id = collector.get_channel_id(args.channel)
    if not channel_id:
        logger.error("유효한 채널 ID를 찾을 수 없습니다.")
        sys.exit(1)
    
    logger.info(f"채널 ID: {channel_id}")
    
    # Get channel info including slug
    channel_info = collector.get_channel_info(channel_id)
    channel_slug = channel_info['channel_slug']
    
    logger.info(f"파일명에 사용될 슬러그: {channel_slug}")
    
    # Step 1: Fetch videos
    logger.info("\n[1/4] 비디오 목록 수집")
    
    # Check if videos JSON already exists
    videos_file = f"data/{channel_slug}_videos.json"
    if os.path.exists(videos_file) and not args.force_refresh:
        logger.info(f"✓ 기존 비디오 목록 파일 발견: {videos_file}")
        logger.info("API 호출을 건너뛰고 기존 파일을 사용합니다.")
        logger.info("(새로 가져오려면 --force-refresh 옵션 사용)")
        try:
            with open(videos_file, 'r', encoding='utf-8') as f:
                videos = json.load(f)
            logger.info(f"✓ {len(videos)}개의 비디오 정보를 로드했습니다.")
        except Exception as e:
            logger.error(f"파일 로드 실패: {e}")
            logger.info("API를 통해 새로 가져옵니다...")
            videos = collector.fetch_channel_videos(channel_id, channel_slug, min_duration_seconds=args.min_duration)
            collector.save_videos_list(channel_slug, videos)
    else:
        if args.force_refresh and os.path.exists(videos_file):
            logger.info("--force-refresh 옵션으로 기존 파일을 무시하고 새로 가져옵니다.")
        logger.info(f"롱폼 비디오만 수집 ({args.min_duration}초 이상)")
        videos = collector.fetch_channel_videos(channel_id, channel_slug, min_duration_seconds=args.min_duration)
        if not videos:
            logger.error("비디오를 찾을 수 없습니다.")
            sys.exit(1)
        collector.save_videos_list(channel_slug, videos)
    
    if not videos:
        logger.error("비디오 목록이 비어있습니다.")
        sys.exit(1)
    
    # Step 2: Fetch transcripts
    if not args.skip_transcripts:
        logger.info("\n[2/4] 한국어 자막 수집")
        collector.fetch_transcripts_parallel(channel_slug, videos)
    else:
        logger.info("\n[2/4] 자막 수집 건너뜀")
    
    # Step 3: Fetch engagement stats
    if not args.skip_stats:
        logger.info("\n[3/4] 참여도 통계 수집")
        collector.fetch_all_video_stats(channel_slug, videos)
    else:
        logger.info("\n[3/4] 참여도 통계 수집 건너뜀")
    
    # Step 4: Fetch comments
    if not args.skip_comments:
        logger.info("\n[4/4] 댓글 수집")
        collector.fetch_all_comments(channel_slug, videos)
    else:
        logger.info("\n[4/4] 댓글 수집 건너뜀")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 모든 데이터 수집 완료!")
    logger.info(f"📁 수집된 데이터 위치: ./data/{channel_slug}_*")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()