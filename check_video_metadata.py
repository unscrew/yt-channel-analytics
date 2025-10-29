#!/usr/bin/env python3
"""
Quick script to fetch all available metadata for a YouTube video
"""

import os
import sys
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

def get_video_metadata(video_id, api_key):
    """Fetch all available metadata for a video."""
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Request all available parts
    request = youtube.videos().list(
        part='snippet,contentDetails,statistics,status,topicDetails,player,localizations,recordingDetails',
        id=video_id
    )
    response = request.execute()
    
    if not response.get('items'):
        print(f"❌ 비디오를 찾을 수 없습니다: {video_id}")
        return None
    
    return response['items'][0]

if __name__ == '__main__':
    # Get API key from environment
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("❌ YOUTUBE_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # Get video ID from command line or use default
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
    else:
        # Default test video
        video_id = input("비디오 ID를 입력하세요 (예: dQw4w9WgXcQ): ").strip()
    
    print(f"\n🔍 비디오 메타데이터 가져오는 중: {video_id}\n")
    print("=" * 80)
    
    metadata = get_video_metadata(video_id, api_key)
    
    if metadata:
        # Print formatted JSON
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 80)
        print("📊 주요 필드 요약:")
        print("=" * 80)
        
        # Snippet
        if 'snippet' in metadata:
            snippet = metadata['snippet']
            print("\n[SNIPPET - 기본 정보]")
            print(f"  제목: {snippet.get('title', 'N/A')}")
            print(f"  채널: {snippet.get('channelTitle', 'N/A')}")
            print(f"  게시일: {snippet.get('publishedAt', 'N/A')}")
            print(f"  카테고리 ID: {snippet.get('categoryId', 'N/A')}")
            print(f"  태그: {snippet.get('tags', [])[:5]}...")  # First 5 tags
            print(f"  설명 길이: {len(snippet.get('description', ''))} 글자")
        
        # Content Details
        if 'contentDetails' in metadata:
            content = metadata['contentDetails']
            print("\n[CONTENT DETAILS - 콘텐츠 상세]")
            print(f"  길이: {content.get('duration', 'N/A')}")
            print(f"  화질: {content.get('definition', 'N/A')}")
            print(f"  자막 여부: {content.get('caption', 'N/A')}")
            print(f"  라이선스: {content.get('licensedContent', 'N/A')}")
        
        # Statistics
        if 'statistics' in metadata:
            stats = metadata['statistics']
            print("\n[STATISTICS - 통계]")
            print(f"  조회수: {stats.get('viewCount', 'N/A'):,}")
            print(f"  좋아요: {stats.get('likeCount', 'N/A'):,}")
            print(f"  댓글 수: {stats.get('commentCount', 'N/A'):,}")
        
        # Status
        if 'status' in metadata:
            status = metadata['status']
            print("\n[STATUS - 상태]")
            print(f"  공개 상태: {status.get('privacyStatus', 'N/A')}")
            print(f"  업로드 상태: {status.get('uploadStatus', 'N/A')}")
            print(f"  라이선스: {status.get('license', 'N/A')}")
        
        # Topic Details
        if 'topicDetails' in metadata:
            topics = metadata['topicDetails']
            print("\n[TOPIC DETAILS - 주제]")
            print(f"  토픽 카테고리: {topics.get('topicCategories', [])}")
        
        print("\n" + "=" * 80)
        print("✅ 완료!")
        print(f"💾 저장하려면: python {sys.argv[0]} {video_id} > video_metadata.json")
        print("=" * 80)