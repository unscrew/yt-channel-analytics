# YouTube Video Preference Predictor

대중 선호도 예측을 위한 YouTube 비디오 데이터 수집 및 분석 시스템

## 📋 목차

- [개요](#개요)
- [기능](#기능)
- [설치](#설치)
- [사용법](#사용법)
  - [데이터 수집](#데이터-수집)
  - [자막 생성 (Whisper)](#자막-생성-whisper)
  - [댓글 백필](#댓글-백필)
  - [감정 분석](#감정-분석)
- [프로젝트 구조](#프로젝트-구조)
- [성능 최적화](#성능-최적화)

---

## 개요

YouTube 비디오의 선호도를 예측하기 위해 다음 데이터를 수집하고 분석합니다:

- **비디오 통계**: 조회수, 좋아요, 댓글 수
- **댓글 데이터**: 댓글 내용 및 감정 분석
- **자막 데이터**: Whisper STT로 생성한 transcript
- **키워드 추출**: 콘텐츠 주제 분석

최종 목표: **새 비디오의 대중 선호도를 % 단위로 예측**

---

## 기능

### ✅ 구현 완료
- YouTube 비디오 메타데이터 수집
- 통계 데이터 수집 (조회수, 좋아요, 댓글 수)
- 댓글 수집 및 백필
- Whisper 기반 자막 생성 (병렬 처리)
- 한글 감정 분석 (KcBERT)
- Shorts 필터링

### 🚧 진행 예정
- 키워드 추출 및 분석
- ML 모델 학습 (선호도 예측)
- 예측 시스템 구축

---

## 설치

### 1. 가상환경 생성 및 활성화

**자동 설정 (추천):**
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

**수동 설정:**
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 패키지 설치
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 API 키를 입력하세요:

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 API 키 입력
```

`.env` 파일 내용:
```
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### 3. ffmpeg 설치 (Whisper용)

```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

### 4. Whisper 설치

```bash
pip install openai-whisper yt-dlp
```

---

## 사용법

### 데이터 수집

#### 1. 비디오 목록 수집

```bash
python youtube_data_collector.py
```

**출력:**
- `data/chimchakman_official_videos.json` - 비디오 목록
- `data/chimchakman_official_stats/*.json` - 각 비디오 통계
- `data/chimchakman_official_comments/*.json` - 각 비디오 댓글

**설정 옵션:**
- `MIN_VIDEO_DURATION`: 최소 비디오 길이 (초) - Shorts 필터링
- `MAX_RESULTS`: 최대 수집 비디오 수

---

### 자막 생성 (Whisper)

#### 단일 비디오 테스트

```bash
# 기본 (base 모델)
python stt_whisper.py VIDEO_ID

# 다른 모델 사용
python stt_whisper.py VIDEO_ID --model small
```

**모델 크기:**
- `tiny` - 가장 빠름, 부정확 (39M params)
- `base` - 빠름, 적당함 (74M) **[기본값]**
- `small` - 중간 (244M)
- `medium` - 느림, 정확 (769M)
- `large` - 가장 느림, 가장 정확 (1550M)

#### 배치 처리 (병렬)

```bash
# 기본 (8개 병렬)
python batch_whisper.py

# workers 수 조정
python batch_whisper.py --workers 12

# 특정 비디오만
python batch_whisper.py --video-ids abc123 def456 ghi789

# 다른 모델 + workers
python batch_whisper.py --model small --workers 10
```

**Workers 수 권장:**

| 시스템 | 메모리 | 추천 Workers | 모델 |
|--------|--------|--------------|------|
| MacBook Air M1/M2 | 8GB | 2-3 | base |
| MacBook Air M1/M2 | 16GB | 4-6 | base/small |
| MacBook Pro M3 | 48GB | 12-16 | small |
| Intel Mac | 16GB | 2-4 | base |

**성능 예시 (M3 Max 48GB):**
```bash
# 보수적
python batch_whisper.py --workers 8
# → 5000개 비디오 ~10시간

# 추천 ⭐
python batch_whisper.py --workers 12
# → 5000개 비디오 ~7시간

# 공격적
python batch_whisper.py --workers 16
# → 5000개 비디오 ~5시간
```

**출력:**
- `data/chimchakman_official_transcripts/{video_id}_whisper_transcript.txt`

**주요 기능:**
- ✅ 자동 스킵: 이미 처리된 비디오는 건너뜀
- ✅ 병렬 처리: 여러 비디오 동시 처리
- ✅ 진행 표시: 실시간 진행률 출력
- ✅ 에러 복구: 실패해도 다음 비디오 계속 처리

---

### 댓글 백필

비어있는 댓글 필드를 YouTube API로 채웁니다:

```bash
python backfill_comments.py
```

**동작:**
1. `data/chimchakman_official_comments/` 의 모든 JSON 파일 스캔
2. `comments` 필드가 비어있는 파일 발견
3. YouTube API로 댓글 수집 (최대 100개)
4. 원본 파일 업데이트

**출력 예시:**
```
📁 23개 파일 검사 중...

📄 _-10RP0GhuM.json
  🔄 백필 중: _-10RP0GhuM
  ✅ 완료: 87개 댓글 추가됨

📄 abc123xyz.json
  ⏭️  이미 댓글 있음

==================================================
✨ 백필 완료!
  ✅ 백필됨: 15개
  ⏭️  건너뜀: 8개
  ❌ 실패: 0개
```

---

### 감정 분석

한글 댓글의 긍정/부정 감정을 분석합니다:

```bash
# 테스트
python test_sentiment_korean.py

# 실제 파일 분석
python test_sentiment_korean.py data/chimchakman_official_comments/VIDEO_ID_comments.json
```

**사용 모델:**
- `beomi/kcbert-base` - 한국어 특화 BERT 모델

**출력 예시:**
```
📊 총 3개 댓글 분석 중...

😊 POSITIVE (85.2%) | 너무 재밌어요! 최고!
😞 NEGATIVE (72.3%) | 이건 진짜 별로네요
😊 POSITIVE (91.5%) | 감사합니다 좋은 영상

✨ 감정 분석 결과:
  😊 긍정: 2개 (66.7%)
  😞 부정: 1개 (33.3%)
  💯 Sentiment Score: 66.7/100
```

---

## 프로젝트 구조

```
youtube-video-preference-predictor/
├── README.md
├── requirements.txt
├── .env                          # API 키 (gitignore)
├── .env.example                  # 환경변수 템플릿
│
├── data/
│   ├── chimchakman_official_videos.json          # 비디오 목록
│   ├── chimchakman_official_stats/               # 통계 데이터
│   │   └── {video_id}_stats.json
│   ├── chimchakman_official_comments/            # 댓글 데이터
│   │   └── {video_id}_comments.json
│   └── chimchakman_official_transcripts/         # 자막 데이터
│       └── {video_id}_whisper_transcript.txt
│
├── youtube_data_collector.py    # 비디오/통계/댓글 수집
├── stt_whisper.py               # 단일 비디오 자막 생성
├── batch_stt.py                 # 배치 자막 생성 (병렬)
├── backfill_comments.py         # 댓글 백필
├── test_sentiment_korean.py     # 감정 분석 테스트
│
└── (향후 추가 예정)
    ├── extract_keywords.py      # 키워드 추출
    ├── create_features.py       # ML Feature 생성
    ├── train_model.py           # 모델 학습
    └── predict.py               # 선호도 예측
```

---

## 성능 최적화

### Whisper 병렬 처리

**최적 Workers 수 찾기:**

```bash
# 시스템 정보 확인
python find_optimal_workers.py --info

# 실제 벤치마크 (3개 비디오로 테스트)
python find_optimal_workers.py video1 video2 video3 --workers 2 4 8 12
```

**일반 가이드:**

```bash
# 메모리 기준
Workers = (사용 가능 RAM - 8GB) / 2GB

# CPU 기준
Workers <= CPU 코어 수

# 예시
# 48GB RAM, 16코어 → 12-16 workers 추천
# 16GB RAM, 8코어  → 4-6 workers 추천
# 8GB RAM, 4코어   → 2-3 workers 추천
```

### 모델 선택

**정확도 vs 속도:**

| 모델 | 속도 | 정확도 | 메모리 | 추천 상황 |
|------|------|--------|--------|-----------|
| tiny | ⭐⭐⭐⭐⭐ | ⭐⭐ | 1GB | 테스트용 |
| base | ⭐⭐⭐⭐ | ⭐⭐⭐ | 2GB | 일반 사용 ⭐ |
| small | ⭐⭐⭐ | ⭐⭐⭐⭐ | 3GB | 정확도 중요 |
| medium | ⭐⭐ | ⭐⭐⭐⭐⭐ | 5GB | 최고 품질 |
| large | ⭐ | ⭐⭐⭐⭐⭐ | 10GB | 연구용 |

**추천:**
- 일반: `base` 모델 (기본값)
- 메모리 여유: `small` 모델 (더 정확)
- 속도 중요: `tiny` 모델

---

## 데이터 형식

### videos.json
```json
[
  {
    "video_id": "abc123",
    "title": "비디오 제목",
    "published_at": "2024-01-01T00:00:00Z",
    "duration": "PT15M30S"
  }
]
```

### stats.json
```json
{
  "video_id": "abc123",
  "view_count": 7277,
  "like_count": 29,
  "comment_count": 6,
  "favorite_count": 0,
  "collected_at": "2025-10-29T17:31:27.503171"
}
```

### comments.json
```json
{
  "video_id": "abc123",
  "comment_count": 3,
  "comments": [
    {
      "author": "@user123",
      "text": "댓글 내용",
      "likeCount": 5,
      "publishedAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### transcript.txt
```
Video ID: abc123
Title: 비디오 제목
Model: whisper-base
--------------------------------------------------------------------------------

자막 텍스트 내용이 여기에...
```

---

## 문제 해결

### ffmpeg 오류
```bash
# Mac
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### Whisper 메모리 부족
```bash
# Workers 수 줄이기
python batch_whisper.py --workers 2

# 더 작은 모델 사용
python batch_whisper.py --model tiny --workers 4
```

### YouTube API 할당량 초과
- 일일 할당량: 10,000 units
- 댓글 수집: 1 unit/request
- 비디오 정보: 1 unit/request
- 다음 날까지 대기 또는 API 키 추가

---

## 향후 계획

- [ ] 키워드 추출 (TF-IDF, KoNLPy)
- [ ] Feature Engineering
- [ ] ML 모델 학습 (XGBoost, Random Forest)
- [ ] 선호도 예측 시스템
- [ ] 웹 대시보드
- [ ] 실시간 모니터링

---

## 기여

이슈 및 PR 환영합니다!

## 라이선스

MIT License