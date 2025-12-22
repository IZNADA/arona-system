# Arona Discord Bot (Minecraft Server Monitor)

블루아카이브 '아로나' 컨셉의 마인크래프트 서버 관리 봇입니다.
로컬 서버 프로세스를 감지하여 상태를 알려주고 공지사항을 전송합니다.

## ✨ 기능
- **서버 상태 확인** (`/상태`): 로컬에서 실행 중인 `server.jar` 프로세스를 감지합니다.
- **점검 공지** (`/점검시작`, `/점검종료`): 시작/종료 시간을 선택하여 채널에 공지합니다.
- **자동 알리미**: 서버가 켜지거나 꺼지면 자동으로 알림을 보냅니다.
- **채팅 청소** (`/채팅정리`): 채널의 메시지를 대량으로 삭제합니다.

## 🛠️ 설치 및 실행 방법

### 1. 필수 프로그램 설치
- Python 3.8 이상

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 설정 (.env)
`.env` 파일을 생성하고 다음 내용을 입력하세요.
```env
DISCORD_TOKEN=여기에_토큰_입력
MC_PROCESS_TARGET=server.jar (감지할 파일명)
```

### 4. 실행
```bash
python3 bot.py
```

## 📝 빌드 (EXE 만들기)
```bash
pyinstaller --onefile --name DiscordMCBot bot.py
```
