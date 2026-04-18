# Phase 12 — `to-wav` 영상→WAV 추출

## 사용자 시점

```bash
voxprep to-wav input.mp4 --output-dir ./raw_audio
voxprep to-wav ./videos/ --output-dir ./raw_audio   # 디렉토리 내 전체 변환
```

## 구현 범위

- ffmpeg subprocess 호출로 영상/오디오 → WAV(PCM s16le, 44100Hz, mono) 변환
- 단일 파일 또는 디렉토리(재귀) 지원
- 지원 입력 포맷: mp4, mkv, webm, mp3, m4a, flac, ogg 등 ffmpeg이 디코딩 가능한 모든 포맷
- `--sample-rate` 옵션 (기본 44100)
- ffmpeg 미설치 시 친절한 에러 메시지

## 참조

- `/Users/eboshi/Desktop/Code/playground/utils/extract_wav.py` — 기존 스크립트, 이식 대상
- SETUP_GUIDE.md의 ffmpeg 변환 예시: `ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 1 output.wav`

## ODP 관점

- 얇은 CLI 어댑터 + subprocess 호출. 새 도메인 객체 없음.
