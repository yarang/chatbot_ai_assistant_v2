from fastapi import Request, HTTPException, status
from core.config import get_settings
from itsdangerous import URLSafeTimedSerializer
import hashlib
import hmac
import time
from typing import Optional, Dict, Any

# Secret key for signing
settings = get_settings()
SECRET_KEY = settings.secret_key
serializer = URLSafeTimedSerializer(SECRET_KEY)

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    세션 쿠키에서 현재 사용자 정보를 가져옵니다.
    """
    session = request.cookies.get("session")
    if not session:
        return None
    try:
        data = serializer.loads(session, max_age=86400) # 1 day
        return data
    except Exception:
        return None

def get_current_user_required(request: Request) -> Dict[str, Any]:
    """
    로그인이 필요한 엔드포인트용 의존성.
    로그인하지 않은 경우 401 에러를 발생시킵니다.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user

def check_telegram_authorization(auth_data: Dict[str, Any], bot_token: str) -> bool:
    """
    Telegram Login Widget의 인증 데이터를 검증합니다.
    """
    check_hash = auth_data.get('hash')
    if not check_hash:
        return False
    auth_data_copy = auth_data.copy()
    if 'hash' in auth_data_copy:
        del auth_data_copy['hash']
    
    data_check_string = '\n'.join(sorted([f"{k}={v}" for k, v in auth_data_copy.items()]))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if hash != check_hash:
        return False
    if time.time() - int(auth_data['auth_date']) > 86400:
        return False
    return True

def create_session_token(user_data: Dict[str, Any]) -> str:
    """
    사용자 데이터로 세션 토큰을 생성합니다.
    """
    return serializer.dumps(user_data)
