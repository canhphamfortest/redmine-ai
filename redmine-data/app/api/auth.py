"""
Các endpoint API xác thực
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import authenticate_user, get_user_by_username

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None
    full_name: str | None
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: UserResponse | None = None


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Xác thực người dùng với tên đăng nhập và mật khẩu.
    
    Endpoint này xác thực người dùng bằng cách so sánh mật khẩu đã hash
    với mật khẩu trong database. Nếu thành công, trả về thông tin người dùng.
    
    Args:
        request: LoginRequest chứa username và password
        db: Database session (dependency injection)
    
    Returns:
        LoginResponse: Dictionary chứa:
            - success: True nếu đăng nhập thành công, False nếu không (bool)
            - message: Thông báo kết quả (str)
            - user: Thông tin người dùng nếu thành công, None nếu thất bại (UserResponse | None)
    
    Note:
        - Mật khẩu được hash bằng bcrypt trước khi so sánh
        - Nếu xác thực thành công, last_login được cập nhật
        - Không trả về HTTPException, chỉ trả về success=False trong response
    """
    user = authenticate_user(db, request.username, request.password)
    
    if not user:
        return LoginResponse(
            success=False,
            message="Tên đăng nhập hoặc mật khẩu không đúng!",
            user=None
        )
    
    return LoginResponse(
        success=True,
        message="Đăng nhập thành công!",
        user=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_admin=user.is_admin,
            is_active=user.is_active
        )
    )


@router.get("/verify/{username}", response_model=UserResponse | None)
def verify_user(username: str, db: Session = Depends(get_db)):
    """Xác minh xem người dùng có tồn tại và đang hoạt động không.
    
    Endpoint này kiểm tra xem một người dùng có tồn tại trong database và
    đang active không. Được sử dụng để verify session hoặc khôi phục session.
    
    Args:
        username: Tên đăng nhập của người dùng cần verify (string)
        db: Database session (dependency injection)
    
    Returns:
        UserResponse: Thông tin người dùng nếu tồn tại và active
    
    Raises:
        HTTPException: HTTP 404 nếu người dùng không tồn tại hoặc không active
    
    Note:
        - Chỉ trả về user nếu is_active=True
        - Không cập nhật last_login (chỉ verify, không phải login)
    """
    user = get_user_by_username(db, username)
    
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active
    )


@router.get("/me/{username}", response_model=UserResponse)
def get_current_user_info(username: str, db: Session = Depends(get_db)):
    """Lấy thông tin người dùng theo tên đăng nhập.
    
    Endpoint này trả về thông tin đầy đủ của một người dùng dựa trên username.
    Khác với verify, endpoint này trả về user ngay cả khi không active.
    
    Args:
        username: Tên đăng nhập của người dùng (string)
        db: Database session (dependency injection)
    
    Returns:
        UserResponse: Thông tin đầy đủ của người dùng:
            - id: UUID của user (str)
            - username: Tên đăng nhập (str)
            - email: Email (str, optional)
            - full_name: Tên đầy đủ (str, optional)
            - is_admin: Có phải admin không (bool)
            - is_active: Có đang active không (bool)
    
    Raises:
        HTTPException: HTTP 404 nếu người dùng không tồn tại
    
    Note:
        - Trả về user ngay cả khi is_active=False
        - Không cập nhật last_login
    """
    user = get_user_by_username(db, username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        is_active=user.is_active
    )

