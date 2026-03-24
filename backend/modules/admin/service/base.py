from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt

SYSTEM_TIMEZONE = "Asia/Shanghai"


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode("utf-8")


class AdminServiceBase:
    def __init__(self, session: AsyncSession):
        self.session = session
