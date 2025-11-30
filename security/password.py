from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password[:72])


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password[:72], password_hash)
