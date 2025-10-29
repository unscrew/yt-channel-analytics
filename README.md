# YouTube Video Preference Predictor

YouTube 채널의 비디오 선호도를 예측하는 트랜스포머 기반 머신러닝 프로젝트

## 📋 프로젝트 목표

트랜스포머(Transformer)를 실전 프로젝트에 활용하여 YouTube 비디오의 선호도를 예측

**주요 기능:**
- YouTube 채널 데이터 자동 수집
- 멀티모달 데이터 분석 (텍스트 + 메타데이터)
- 트랜스포머 기반 선호도 예측 모델

## 🎯 예측 목표

입력: 비디오 메타데이터 (제목, 설명, 초기 지표 등)  
출력: 선호도 레벨 (High / Medium / Low)

## 🚀 Quick Start

### 1. 환경 설정

**자동 설정 (추천):**
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

**수동 설정:**
```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. API 키 설정

`.env` 파일을 생성하고 YouTube API 키를 입력하세요:

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 API 키 입력
```

**YouTube API 키 발급:**
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성
3. "YouTube Data API v3" 활성화
4. API 키 생성
5. `.env` 파일에 추가

### 3. 데이터 수집

```bash
# 기본 사용법
python youtube_data_collector.py "https://www.youtube.com/@channelname"

# 또는 채널 ID 직접 입력
python youtube_data_collector.py "UC1234567890"

# 특정 데이터만 수집
python youtube_data_collector.py "@channelname" --skip-transcripts
python youtube_data_collector.py "@channelname" --skip-comments

# 최소 비디오 길이 설정 (Shorts 필터링)
python youtube_data_collector.py "@channelname" --min-duration 300  # 5분 이상만

# 기존 데이터 새로고침
python youtube_data_collector.py "@channelname" --force-refresh
```

## 📊 수집되는 데이터

### 자동 수집:
- ✅ **비디오 메타데이터**: 제목, 설명, 게시일, 썸네일, 길이
- ✅ **참여도 통계**: 조회수, 좋아요, 댓글 수
- ✅ **댓글**: 모든 댓글 텍스트
- ✅ **자막**: 한국어 자막 (있는 경우)

### 자동 필터링:
- 🚫 **Shorts 제외**: 60초 미만 비디오 자동 필터링
- 📁 **채널별 폴더**: 채널 slug 기반 파일명/폴더명

## 📁 프로젝트 구조

```
youtube-channel-predictor/
├── venv/                               # 가상환경 (git 제외)
├── data/                               # 수집된 데이터
│   ├── ChannelName_videos.json       # 비디오 목록
│   ├── ChannelName_transcripts/       # 자막 파일들
│   ├── ChannelName_engagement_stats/  # 참여도 통계
│   └── ChannelName_comments/          # 댓글 데이터
├── models/                             # 학습된 모델 (예정)
├── notebooks/                          # Jupyter notebooks (예정)
├── src/                                # 소스코드 (예정)
│   ├── labeling.py                    # 데이터 라벨링
│   ├── feature_extraction.py         # Feature 추출
│   ├── model.py                       # 트랜스포머 모델
│   └── train.py                       # 학습 파이프라인
├── youtube_data_collector.py          # 데이터 수집 스크립트
├── check_video_metadata.py            # 메타데이터 확인 도구
├── requirements.txt                    # Python 패키지 목록
├── setup_venv.sh                      # 가상환경 설정 스크립트
├── .env                               # 환경변수 (git 제외)
├── .env.example                       # 환경변수 템플릿
├── .gitignore                         # Git 제외 파일
└── README.md                          # 이 파일
```

## 🔧 주요 기능

### 1. 스마트 캐싱
기존에 수집한 비디오 목록이 있으면 API 호출을 건너뛰고 재사용합니다.
```bash
# 첫 실행: API에서 데이터 가져오기
python youtube_data_collector.py "@channel"

# 두 번째 실행: 캐시된 데이터 사용 (빠름!)
python youtube_data_collector.py "@channel"

# 강제 새로고침
python youtube_data_collector.py "@channel" --force-refresh
```

### 2. Shorts 자동 필터링
60초 미만의 YouTube Shorts는 자동으로 제외됩니다.
```bash
# 기본: 60초 이상만
python youtube_data_collector.py "@channel"

# 커스텀: 5분 이상만
python youtube_data_collector.py "@channel" --min-duration 300
```

### 3. 채널 Slug 기반 파일명
읽기 쉬운 파일명으로 저장됩니다.
```
Before: UC1234567890_videos.json
After:  ChimChakMan_Official_videos.json
```

### 4. 병렬 처리
자막 수집 시 멀티스레딩으로 빠르게 처리합니다.
```bash
# 워커 수 조정
python youtube_data_collector.py "@channel" --max-workers 10
```

## 🔍 유틸리티 도구

### 비디오 메타데이터 확인
```bash
# 특정 비디오의 모든 메타데이터 확인
python check_video_metadata.py VIDEO_ID

# JSON 파일로 저장
python check_video_metadata.py VIDEO_ID > metadata.json
```

## 🤖 모델링 (예정)

### Phase 1: 데이터 라벨링
- 참여도 지표 기반 자동 라벨링
- High / Medium / Low 분류

### Phase 2: Feature 추출
- **텍스트**: BERT 임베딩 (제목, 설명, 댓글)
- **메타데이터**: 조회수, 좋아요, 길이, 게시 시간 등

### Phase 3: 트랜스포머 모델
```python
입력:
├─ 텍스트 (BERT로 인코딩)
│  ├─ 제목
│  ├─ 설명
│  └─ 댓글 요약
└─ 메타데이터
   ├─ 비디오 길이
   ├─ 게시 시간 (요일, 시간대)
   └─ 초기 참여도 지표

모델: 멀티모달 트랜스포머
├─ BERT Encoder (텍스트)
├─ MLP Encoder (메타데이터)
├─ Fusion Layer
└─ Classification Head

출력: 선호도 (High / Medium / Low)
```

## 📦 Dependencies

주요 패키지:
- `google-api-python-client`: YouTube Data API
- `youtube-transcript-api`: 자막 수집
- `python-dotenv`: 환경변수 관리
- `transformers`: 트랜스포머 모델 (예정)
- `torch`: PyTorch (예정)
- `scikit-learn`: 머신러닝 (예정)

전체 목록은 `requirements.txt` 참조

## 🎓 학습 리소스

### YouTube API
- [YouTube Data API v3 문서](https://developers.google.com/youtube/v3)
- [API 할당량](https://developers.google.com/youtube/v3/getting-started#quota): 10,000 units/day (무료)

### 트랜스포머
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [KLUE BERT](https://huggingface.co/klue/bert-base): 한국어 BERT 모델

## ⚠️ 주의사항

### API 할당량
- 하루 10,000 units 제한
- 비디오 목록 조회: 1 unit
- 댓글 조회: 1 unit
- 통계 조회: 1 unit

### 자막 수집
- 자막이 없는 비디오는 경고와 함께 건너뜁니다
- 자막 비활성화된 비디오는 수집 불가
- 한국어 자막만 수집 (다른 언어 필요시 코드 수정)

### 저장 공간
- 비디오 150개 기준: ~500MB-1GB
- 자막, 댓글 포함 시 더 증가 가능

## 🔄 워크플로우

```mermaid
graph LR
    A[YouTube 채널] --> B[데이터 수집]
    B --> C[전처리 & 라벨링]
    C --> D[Feature 추출]
    D --> E[모델 학습]
    E --> F[예측 & 분석]
```

## 🐛 트러블슈팅

### "youtube_transcript_api 에러"
```bash
pip uninstall youtube-transcript-api -y
pip install youtube-transcript-api --upgrade
```

### "API 키 오류"
`.env` 파일이 제대로 설정되었는지 확인:
```bash
cat .env
# YOUTUBE_API_KEY=your_actual_key 확인
```

### "가상환경 활성화 안됨"
```bash
# 확인
which python
# venv 경로가 나와야 함

# 재활성화
source venv/bin/activate
```

## 📈 프로젝트 진행 상황

- [x] 프로젝트 구조 설계
- [x] 데이터 수집 파이프라인
- [x] 캐싱 시스템
- [x] Shorts 필터링
- [x] 자막 수집
- [x] 댓글 수집
- [x] 참여도 통계 수집
- [ ] 데이터 라벨링 스크립트
- [ ] Feature 추출 파이프라인
- [ ] 트랜스포머 모델 구현
- [ ] 학습 파이프라인
- [ ] 평가 & 분석 도구
- [ ] 웹 데모 (선택)

## 🤝 Contributing

이 프로젝트는 트랜스포머 학습을 위한 개인 프로젝트입니다.

## 📝 License

MIT License