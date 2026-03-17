"""
Các tiện ích xác thực cho quản lý người dùng
"""
import bcrypt
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import User
from app.database import SessionLocal


def hash_password(password: str) -> str:
    """Hash mật khẩu bằng thuật toán bcrypt.
    
    Hàm này sử dụng bcrypt để hash mật khẩu với salt tự động. Bcrypt là một
    thuật toán hash một chiều an toàn, được thiết kế đặc biệt cho việc bảo vệ
    mật khẩu. Mỗi lần hash sẽ tạo ra một giá trị khác nhau do salt ngẫu nhiên.
    
    Args:
        password: Mật khẩu dạng plain text cần hash
    
    Returns:
        str: Mật khẩu đã được hash dạng string (bao gồm salt và hash)
    
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> len(hashed) > 50  # Bcrypt hash thường dài hơn 50 ký tự
        True
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Xác minh mật khẩu có khớp với hash đã lưu không.
    
    Hàm này so sánh mật khẩu plain text với hash đã lưu bằng cách hash lại
    mật khẩu với salt từ hash cũ và so sánh kết quả. Bcrypt tự động extract
    salt từ hash string.
    
    Args:
        password: Mật khẩu plain text cần kiểm tra
        hashed_password: Hash mật khẩu đã lưu trong database
    
    Returns:
        bool: True nếu mật khẩu khớp, False nếu không khớp
    
    Example:
        >>> hashed = hash_password("mypassword123")
        >>> verify_password("mypassword123", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Xác thực người dùng bằng tên đăng nhập và mật khẩu.
    
    Hàm này thực hiện quá trình xác thực đầy đủ:
    1. Tìm user theo username
    2. Kiểm tra user có active không
    3. Xác minh mật khẩu có khớp không
    4. Cập nhật thời gian đăng nhập cuối cùng
    
    Nếu bất kỳ bước nào thất bại, hàm sẽ trả về None.
    
    Args:
        db: Database session
        username: Tên đăng nhập của người dùng
        password: Mật khẩu plain text
    
    Returns:
        User | None: User object nếu xác thực thành công, None nếu thất bại
    
    Example:
        >>> user = authenticate_user(db, "admin", "password123")
        >>> if user:
        ...     print(f"Welcome {user.username}")
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    # Cập nhật lần đăng nhập cuối
    user.last_login = datetime.utcnow()
    db.commit()
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Lấy thông tin người dùng theo tên đăng nhập.
    
    Hàm này tìm kiếm user trong database theo username. Không thực hiện
    bất kỳ kiểm tra xác thực nào, chỉ đơn giản là query database.
    
    Args:
        db: Database session
        username: Tên đăng nhập cần tìm
    
    Returns:
        User | None: User object nếu tìm thấy, None nếu không tìm thấy
    
    Example:
        >>> user = get_user_by_username(db, "admin")
        >>> if user:
        ...     print(user.email)
    """
    return db.query(User).filter(User.username == username).first()


def create_user(
    db: Session,
    username: str,
    password: str,
    email: str = None,
    full_name: str = None,
    is_admin: bool = False
) -> User:
    """Tạo tài khoản người dùng mới trong hệ thống.
    
    Hàm này tạo một user mới với mật khẩu đã được hash. User mới sẽ được
    đặt is_active=True mặc định. Mật khẩu sẽ được hash bằng bcrypt trước
    khi lưu vào database.
    
    Args:
        db: Database session
        username: Tên đăng nhập (bắt buộc, phải unique)
        password: Mật khẩu plain text (sẽ được hash trước khi lưu)
        email: Email của người dùng (tùy chọn)
        full_name: Tên đầy đủ của người dùng (tùy chọn)
        is_admin: Có phải admin không (mặc định: False)
    
    Returns:
        User: User object đã được tạo và lưu vào database
    
    Raises:
        IntegrityError: Nếu username hoặc email đã tồn tại (unique constraint)
    
    Example:
        >>> user = create_user(
        ...     db,
        ...     username="john_doe",
        ...     password="secure_password",
        ...     email="john@example.com",
        ...     full_name="John Doe"
        ... )
        >>> print(user.id)
    """
    hashed_password = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        is_admin=is_admin,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, new_password: str) -> bool:
    """Thay đổi mật khẩu của người dùng.
    
    Hàm này cập nhật mật khẩu mới cho user. Mật khẩu mới sẽ được hash bằng
    bcrypt trước khi lưu. Cũng cập nhật updated_at timestamp.
    
    Args:
        db: Database session
        user: User object cần thay đổi mật khẩu
        new_password: Mật khẩu mới dạng plain text
    
    Returns:
        bool: True nếu thành công (luôn trả về True nếu không có exception)
    
    Raises:
        Exception: Nếu commit database thất bại
    
    Example:
        >>> user = get_user_by_username(db, "admin")
        >>> change_password(db, user, "new_secure_password")
        True
    """
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    return True

