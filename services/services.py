import base64
from hashlib import pbkdf2_hmac
from os import urandom

import jwt

from database.models import Token
from data.constants import SECRET_KEY
from .errors import ServerProcessError


HASH_ITERS = 390000


def hash_password(str_password: str, salt: bytes) -> bytes:
    """Хеширование пароля str_password с переданной солью salt"""

    hashed_password = pbkdf2_hmac(
        'sha256',
        str_password.encode(),
        salt,
        HASH_ITERS
    )
    return hashed_password


def check_password(password_to_check: str, real_encode_password: str) -> bool:
    """Проверка строкового пароля password_to_check на совпадение в паролем из БД real_encode_password"""

    # достаём из пароля из БД строковый вид байтов соли и верного пароля
    _, _, str_salt, str_password = real_encode_password.split('$')
    # декодируем строковый вид байтов соли и верного пароля в байтовый вид
    bytes_salt = base64.b64decode(str_salt)
    bytes_password = base64.b64decode(str_password)

    # хешируем строковый пароль для проверки
    hashed_password_to_check = hash_password(str_password=password_to_check, salt=bytes_salt)

    # проверяем на равенство захешированные пароли
    if hashed_password_to_check == bytes_password:
        return True
    return False


def make_password(str_password: str) -> str:
    """Создаём строку с солью и захешированным паролем в строковом виде"""

    # создаём соль - псевдослучайный набор байт
    salt = urandom(16)
    # хешируем пароль с созданной солью
    hashed_password = hash_password(str_password=str_password, salt=salt)

    # кодируем байтовый вид соли и захешированного пароля в строковый вид
    str_salt = base64.b64encode(salt).decode()
    str_hashed_password = base64.b64encode(hashed_password).decode()

    # объединяем всё в одну строку
    password_to_db = f'pbkdf2_sha256${HASH_ITERS}${str_salt}${str_hashed_password}'
    return password_to_db


def remove_token(token: str) -> None:
    """Удаление токена из БД"""

    token_obj = Token.query().filter_by(token=token).first()

    if not token_obj:
        raise ServerProcessError('Cannot process the token.')

    try:
        Token.delete(pk=token_obj.id)
    except Exception:
        raise ServerProcessError('Cannot delete the token.')


def check_token_in_db(token: str) -> bool:
    """Проверка токена на наличие в БД"""

    token_obj = Token.query().filter_by(token=token).first()
    return bool(token_obj)


def check_token_expired(token: str) -> bool:
    """Проверка, истёк ли токен"""

    try:
        # декодируем токен
        jwt.decode(jwt=token, key=SECRET_KEY, algorithms='HS256')
        return False
    except jwt.exceptions.ExpiredSignatureError:
        return True
