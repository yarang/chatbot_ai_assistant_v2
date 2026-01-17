# HTTPS 설정 가이드

## 📋 개요

이 가이드는 Chatbot AI Assistant를 HTTPS로 배포하기 위한 자동화 스크립트 사용 방법을 설명합니다.

## ✅ 사전 요구사항

1. **서버**: Ubuntu 24.04 (또는 호환 가능한 Linux)
2. **도메인**: 이미 보유하고 있어야 함
3. **DNS 설정**: 도메인이 서버 IP를 pointing 해야 함
4. **서버 접근**: SSH 또는 직접 접근 가능
5. **포트**: 80, 443 포트가 열려 있어야 함

## 🚀 빠른 시작

### 1단계: 스크립트 실행

```bash
cd /home/ubuntu/works/chatbot_ai_assistant_v2/scripts
sudo ./setup_https.sh
```

### 2단계: 정보 입력

스크립트가 실행되면 다음 정보를 입력하세요:

1. **도메인**: 예: `example.com` 또는 `api.example.com`
2. **이메일**: Let's Encrypt 알림용 이메일

### 3단계: DNS 설정 확인

스크립트가 DNS 설정을 확인하면 다음 레코드가 설정되어 있는지 확인하세요:

```
example.com     →    (서버 공인 IP)
www.example.com →    (서버 공인 IP)
```

### 4단계: 완료

스크립트가 다음을 자동으로 설정합니다:

- ✅ Nginx 설치 및 설정
- ✅ Let's Encrypt SSL 인증서 발급
- ✅ FastAPI systemd 서비스 생성
- ✅ 방화벽 설정
- ✅ HTTPS 강제 리다이렉트

## 📁 생성되는 파일

### Nginx 설정
- `/etc/nginx/sites-available/chatbot_ai_assistant`
- 자동으로 사이트 활성화됨

### systemd 서비스
- `/etc/systemd/system/chatbot_ai_assistant.service`
- FastAPI 애플리케이션을 백그라운드 서비스로 실행

### SSL 인증서
- `/etc/letsencrypt/live/example.com/`
- 자동 갱신 설정됨 (매일)

## 🔧 서비스 관리

### 서비스 상태 확인
```bash
sudo systemctl status chatbot_ai_assistant
```

### 서비스 시작/중지/재시작
```bash
sudo systemctl start chatbot_ai_assistant
sudo systemctl stop chatbot_ai_assistant
sudo systemctl restart chatbot_ai_assistant
```

### 로그 확인
```bash
# 애플리케이션 로그
sudo journalctl -u chatbot_ai_assistant -f

# Nginx 접근 로그
sudo tail -f /var/log/nginx/access.log

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log
```

## 🌐 접속 URL

HTTPS 설정 완료 후 다음 URL로 접속 가능:

- `https://your-domain.com`
- `https://www.your-domain.com`

## 🔄 SSL 인증서 갱신

Let's Encrypt 인증서는 90일마다 갱신해야 합니다. 자동 갱신이 설정되어 있지만, 수동 갱신도 가능합니다:

```bash
sudo certbot renew
```

갱신 테스트:
```bash
sudo certbot renew --dry-run
```

## 📱 Telegram Webhook 업데이트

HTTPS 설정 후 Telegram webhook URL을 업데이트해야 합니다:

```bash
curl -F "url=https://your-domain.com/webhook" \
  https://api.telegram.org/bot{BOT_TOKEN}/setWebhook
```

## 🐛 문제 해결

### 1. SSL 인증서 발급 실패

**원인**: DNS 설정이 완료되지 않음

**해결**:
```bash
# DNS 설정 확인
nslookup your-domain.com

# 도메인이 서버 IP를 pointing하는지 확인
ping your-domain.com
```

### 2. 502 Bad Gateway

**원인**: FastAPI 서비스가 실행 중이 아님

**해결**:
```bash
# 서비스 상태 확인
sudo systemctl status chatbot_ai_assistant

# 서비스 시작
sudo systemctl start chatbot_ai_assistant
```

### 3. 포트 충돌

**원인**: 80/443 포트가 이미 사용 중

**해결**:
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep ':80'
sudo netstat -tlnp | grep ':443'

# 충돌하는 서비스 중지
sudo systemctl stop apache2  # Apache가 실행 중인 경우
```

## 🔒 방화벽 설정

방화벽이 활성화된 경우 필수 포트를 열어야 합니다:

```bash
# UFW 방화벽
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

## 📊 성능 최적화

### Gunicorn 워커 수 조정
서버 사양에 따라 워커 수를 조정하세요:

```bash
# systemd 서비스 파일 편집
sudo nano /etc/systemd/system/chatbot_ai_assistant.service

# 워커 수 변경 (기본: 4)
ExecStart=/path/to/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 main:app
```

### Nginx 캐시 설정
정적 파일 캐싱을 추가하여 성능을 향상시킬 수 있습니다.

## 🎯 다음 단계

1. ✅ HTTPS 접속 테스트
2. ✅ Telegram webhook 업데이트
3. ✅ 모니터링 설정
4. ✅ 백업 전략 수립

---

**문제 발생 시**: 스크립트 실행 로그를 확인하고 문제를 신고해주세요.
