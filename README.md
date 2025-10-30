# YouTube Channel Predictor

YouTube 채널의 비디오 선호도를 예측하는 트랜스포머 기반 머신러닝 프로젝트

## 📋 프로젝트 목표

트랜스포머(Transformer)를 실전 프로젝트에 활용하여 YouTube 비디오의 선호도를 예측합니다.

**주요 기능:**
- YouTube 채널 데이터 자동 수집
- 멀티모달 데이터 분석 (텍스트 + 메타데이터)
- 트랜스포머 기반 선호도 예측 모델

## 🔍 유틸리티 도구

### 📹 비디오 메타데이터 확인
```bash
# 특정 비디오의 모든 메타데이터 확인
python check_video_metadata.py J3OBgAIcPeA

# JSON 파일로 저장
python check_video_metadata.py VIDEO_ID > metadata.json
```

### 🎤 Whisper로 자막 생성 (STT)

음성을 텍스트로 변환하여 비디오 내용 분석

```bash
# 단일 비디오 테스트
python test_whisper.py H5lz6_hqCNw

# 다른 모델 사용 (더 정확)
python test_whisper.py VIDEO_ID --model small

# 모델 크기: tiny, base, small, medium, large
```

**설치:**
```bash
pip install openai-whisper yt-dlp

# ffmpeg 필요
brew install ffmpeg              # Mac
sudo apt-get install ffmpeg      # Ubuntu
```

**출력:** `{VIDEO_ID}_whisper_transcript.txt`

### 🧹 STT 자막 노이즈 제거

Whisper가 생성한 자막에서 반복, 말더듬 등 제거

```bash
# 노이즈 제거
python denoise_stt.py H5lz6_hqCNw_whisper_transcript.txt

# 강력 모드 (추임새까지 제거)
python denoise_stt.py input.txt --aggressive

# 조용히 실행
python denoise_stt.py input.txt --quiet
```

**출력:** `{입력파일명}_denoised.txt`

**제거되는 노이즈:**
- 반복 감탄사 (아... 아... 아...)
- 연속 반복 단어 (이거 이거 이거)
- 과도한 추임새 (네네네네)
- 말더듬 (저.. 저는)

### 🔑 키워드 추출

정제된 자막에서 의미있는 키워드 추출

#### **방법 1: 간단한 버전 (추천, Java 불필요)** ⭐

```bash
# Java 불필요, 빠르고 확실
python extract_keywords_simple.py input_denoised.txt

# 키워드 개수 조정
python extract_keywords_simple.py input.txt --top 15

# JSON 저장
python extract_keywords_simple.py input.txt --output keywords.json
```

**특징:**
- ✅ 의존성 없음 (Java 불필요)
- ✅ 항상 작동
- ✅ 빠른 속도
- ⚠️ 정확도 중간

#### **방법 2: 정확한 버전 (KoNLPy 형태소 분석)** ⭐⭐⭐⭐⭐

```bash
# 형태소 분석으로 더 정확한 명사 추출
python extract_keywords_contextual.py input_denoised.txt

# 키워드 개수 조정
python extract_keywords_contextual.py input.txt --top 15

# JSON 저장
python extract_keywords_contextual.py input.txt --output keywords.json
```

**특징:**
- ✅ 형태소 분석 (명사 정확히 추출)
- ✅ 고유명사 우선 처리
- ✅ 빈도 + 의미 기반
- ⚠️ Java 필요 (아래 참조)

#### **Java 설치 (KoNLPy용)**

KoNLPy는 Java가 필요합니다. 없으면 자동으로 간단한 방법으로 전환됩니다.

**Mac:**
```bash
# Homebrew로 설치
brew install openjdk@11

# 시스템 링크
sudo ln -sfn \
  $(brew --prefix)/opt/openjdk@11/libexec/openjdk.jdk \
  /Library/Java/JavaVirtualMachines/openjdk-11.jdk

# 환경변수 설정 (zsh)
echo 'export JAVA_HOME="$(brew --prefix)/opt/openjdk@11"' >> ~/.zshrc
echo 'export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 확인
java -version
```

**Ubuntu/Linux:**
```bash
# Java 설치
sudo apt-get update
sudo apt-get install default-jdk

# 확인
java -version
```

**설치 후:**
```bash
# KoNLPy 설치
pip install konlpy

# 다시 실행 (이제 형태소 분석 사용!)
python extract_keywords_contextual.py input.txt
```

#### **전체 워크플로우 예시**

```bash
# 1. Whisper로 자막 생성
python test_whisper.py H5lz6_hqCNw

# 2. 노이즈 제거
python denoise_stt.py H5lz6_hqCNw_whisper_transcript.txt

# 3. 키워드 추출 (간단)
python extract_keywords_simple.py H5lz6_hqCNw_whisper_transcript_denoised.txt

# 또는: 키워드 추출 (정확 - Java 있으면)
python extract_keywords_contextual.py H5lz6_hqCNw_whisper_transcript_denoised.txt
```

#### **예상 결과**

```
✨ 최종 키워드 Top 10:
 1. 테라     [brand  ] 빈도:14  점수: 33.6
 2. 탄산     [topic  ] 빈도: 7  점수:  8.4
 3. 맥주     [topic  ] 빈도: 2  점수:  4.8
 4. 넉살     [person ] 빈도: 5  점수: 12.0
 5. 침착맨    [person ] 빈도: 3  점수:  7.2
 6. 와이프    [person ] 빈도: 2  점수:  4.8
 7. 소맥     [topic  ] 빈도: 4  점수:  9.6
 8. 광고     [topic  ] 빈도: 3  점수:  7.2
 9. 게임     [topic  ] 빈도: 2  점수:  4.8
10. ASMR    [topic  ] 빈도: 3  점수:  7.2

🏷️ 발견된 고유명사:
  brands : 테라, 참이슬
  persons: 침착맨, 넉살, 와이프
  topics : 게임, 맥주, 광고, 방송
```

### 📊 키워드 추출 방법 비교

| 방법 | Java | KoNLPy | 정확도 | 속도 | 추천 |
|------|------|--------|--------|------|------|
| `extract_keywords_simple.py` | ❌ | ❌ | ⭐⭐⭐ | 빠름 | 시작할 때 |
| `extract_keywords_contextual.py` (Java 없이) | ❌ | ❌ | ⭐⭐⭐ | 빠름 | Java 설치 전 |
| `extract_keywords_contextual.py` (Java 있음) | ✅ | ✅ | ⭐⭐⭐⭐⭐ | 중간 | 최종 사용 |
| `extract_keywords.py` (다중 방법) | ✅ | ✅ | ⭐⭐ | 느림 | ❌ 비추천 |

**권장 순서:**
1. 처음: `extract_keywords_simple.py` 사용
2. Java 설치 후: `extract_keywords_contextual.py` 사용
3. `extract_keywords.py`는 사용 안 함 (결과 부정확)
sudo ln -sfn $(brew --prefix)/opt/openjdk@11/libexec/openjdk.jdk \
  /Library/Java/JavaVirtualMachines/openjdk-11.jdk

# 환경변수 설정
echo 'export JAVA_HOME="$(brew --prefix)/opt/openjdk@11"' >> ~/.zshrc
source ~/.zshrc

# 2. KoNLPy 설치
pip install konlpy

# 3. 확인
python -c "from konlpy.tag import Okt; print('OK')"
```

**Ubuntu:**
```bash
# Java 설치
sudo apt-get install default-jdk

# KoNLPy
pip install konlpy
```

**방법 3: 다중 방법 통합 (실험용)**
```bash
# Hugging Face, KeyBERT, YAKE 등 6가지 방법 통합
python extract_keywords.py input.txt --top 30
```

**필요 패키지:**
```bash
pip install transformers torch keybert yake scikit-learn konlpy
```

### 📊 전체 워크플로우

```bash
# 1. 비디오 메타데이터 확인
python check_video_metadata.py VIDEO_ID

# 2. 자막 생성 (Whisper)
python test_whisper.py VIDEO_ID

# 3. 노이즈 제거
python denoise_stt.py VIDEO_ID_whisper_transcript.txt

# 4. 키워드 추출
python extract_keywords_simple.py VIDEO_ID_whisper_transcript_denoised.txt

# 또는 정확한 버전 (KoNLPy)
python extract_keywords_contextual.py VIDEO_ID_whisper_transcript_denoised.txt
```

**예시:**
```bash
python test_whisper.py H5lz6_hqCNw
python denoise_stt.py H5lz6_hqCNw_whisper_transcript.txt
python extract_keywords_simple.py H5lz6_hqCNw_whisper_transcript_denoised.txt
```

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
├── test_whisper.py                    # Whisper STT 테스트
├── extract_keywords.py                # 키워드 추출 (다중 방법)
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

**데이터 수집:**
- `google-api-python-client`: YouTube Data API
- `youtube-transcript-api`: 자막 수집
- `python-dotenv`: 환경변수 관리

**트랜스포머 & ML:**
- `transformers`: Hugging Face 트랜스포머 모델
- `torch`: PyTorch (딥러닝 프레임워크)
- `scikit-learn`: 머신러닝

**키워드 추출:**
- `keybert`: BERT 기반 키워드 추출
- `yake`: 통계 기반 키워드 추출
- `konlpy`: 한국어 형태소 분석

**음성 인식 (선택):**
- `openai-whisper`: Whisper STT 모델
- `yt-dlp`: YouTube 다운로더

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