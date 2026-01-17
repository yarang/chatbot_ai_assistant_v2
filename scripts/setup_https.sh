#!/bin/bash

#############################################
# HTTPS 자동 설정 스크립트
# Ubuntu 24.04용
# Nginx + Let's Encrypt + FastAPI
#############################################

set -e

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 설정 변수
PROJECT_DIR="/home/ubuntu/works/chatbot_ai_assistant_v2"
DOMAIN=""
EMAIL=""
SERVICE_NAME="chatbot_ai_assistant"
FASTAPI_PORT=8000
NGINX_CONF="/etc/nginx/sites-available/$SERVICE_NAME"
SYSTEMD_SERVICE="/etc/systemd/system/$SERVICE_NAME.service"

# 도메인 확인
if [ -z "$DOMAIN" ]; then
    read -p "도메인을 입력하세요 (예: example.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        log_error "도메인이 입력되지 않았습니다."
        exit 1
    fi
fi

# 이메일 확인
if [ -z "$EMAIL" ]; then
    read -p "Let's Encrypt 알림용 이메일을 입력하세요: " EMAIL
    if [ -z "$EMAIL" ]; then
        log_error "이메일이 입력되지 않았습니다."
        exit 1
    fi
fi

log_info "HTTPS 설정 시작..."
log_info "도메인: $DOMAIN"
log_info "이메일: $EMAIL"
log_info "프로젝트 경로: $PROJECT_DIR"

# 1단계: 시스템 업데이트 및 필수 패키지 설치
log_info "필수 패키지 설치 중..."
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx ufw python3-venv python3-pip

# 2단계: 방화벽 설정
log_info "방화벽 설정 중..."
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw --force enable

# 3단계: 프로젝트 의존성 설치
log_info "Python 의존성 설치 중..."
cd "$PROJECT_DIR"
if [ ! -d "venv" ]; then
    log_info "가상 환경 생성 중..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4단계: systemd 서비스 생성
log_info "systemd 서비스 생성 중..."
sudo tee "$SYSTEMD_SERVICE" > /dev/null <<EOF
[Unit]
Description=Chatbot AI Assistant FastAPI Service
After=network.target

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$FASTAPI_PORT main:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5단계: Nginx 설정 (HTTP only, 먼저)
log_info "Nginx 설정 생성 중..."
sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:$FASTAPI_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Telegram webhook endpoint
    location /webhook {
        proxy_pass http://127.0.0.1:$FASTAPI_PORT/webhook;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 사이트 활성화
sudo ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/"
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx 설정 테스트
log_info "Nginx 설정 테스트 중..."
sudo nginx -t

# 6단계: systemd 서비스 시작
log_info "FastAPI 서비스 시작 중..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Nginx 재시작
sudo systemctl restart nginx

# 7단계: DNS 확인 안내
log_warn "=========================================="
log_warn "중요: DNS 설정 확인 필요"
log_warn "=========================================="
log_warn "다음 DNS 레코드가 설정되어 있는지 확인하세요:"
log_warn "  $DOMAIN         → (서버 공인 IP)"
log_warn "  www.$DOMAIN     → (서버 공인 IP)"
log_warn ""
read -p "DNS 설정이 완료되었나요? (y/n): " dns_confirmed

if [ "$dns_confirmed" != "y" ] && [ "$dns_confirmed" != "Y" ]; then
    log_warn "DNS 설정 완료 후 다시 실행해주세요."
    log_warn "스크립트를 종료합니다."
    exit 0
fi

# 8단계: Let's Encrypt SSL 인증서 발급
log_info "Let's Encrypt SSL 인증서 발급 중..."
sudo certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email --redirect

# 9단계: SSL 자동 갱신 설정 (이미 certbot이 자동으로 설정함)
log_info "SSL 인증서 자동 갱신 설정 확인..."
sudo certbot renew --dry-run

# 10단계: 완료
log_info "=========================================="
log_info "HTTPS 설정 완료!"
log_info "=========================================="
log_info "접속 가능한 URL:"
log_info "  - https://$DOMAIN"
log_info "  - https://www.$DOMAIN"
log_info ""
log_info "서비스 상태 확인:"
log_info "  sudo systemctl status $SERVICE_NAME"
log_info ""
log_info "서비스 로그 확인:"
log_info "  sudo journalctl -u $SERVICE_NAME -f"
log_info ""
log_info "Nginx 로그 확인:"
log_info "  sudo tail -f /var/log/nginx/access.log"
log_info "  sudo tail -f /var/log/nginx/error.log"
