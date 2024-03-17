import base64
from hashlib import pbkdf2_hmac
from os import urandom

import jwt
import pandas as pd
from flask import Request

from database.models import Token, User, Category, Question
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


def get_user_from_request(request: Request) -> User:
    _, token = request.cookies.get('Authorization').split(' ')
    decoded_token = jwt.decode(jwt=token, key=SECRET_KEY, algorithms='HS256')

    user = User.query().filter_by(id=decoded_token['id']).first()
    return user


def upload_questions_to_db(path_to_file: str, user_id: int) -> dict:
    xls = pd.ExcelFile(path_to_file)

    # добавляем в словарь ключи-листы и значения-датафреймы
    dataframe_dict = {
        sheet_name.strip(): pd.read_excel(xls, sheet_name, index_col=0)
        for sheet_name in xls.sheet_names
    }

    # словарь с информацией о кол-ве обработанных вопросов
    total_result_dict = {key: {"всего": 0, "успешно": 0} for key in dataframe_dict.keys()}

    # цикл по листам
    for category, df in dataframe_dict.items():
        category_obj = Category.query().filter_by(name=category, user_id=user_id).first()
        if not category_obj:
            category_obj = Category.create(name=category, user_id=user_id)

        # цикл по строкам в листе
        for index, question_row in df.iterrows():
            # прибавляем 1 к общему кол-ву обработанных вопросов
            total_result_dict[category]["всего"] += 1

            dict_row_data = question_row.to_dict()
            # достаём нужные данные из словаря строки
            client_name = dict_row_data.get('ФИО')
            job_place = dict_row_data.get('Место работы/учёбы')
            job_title = dict_row_data.get('Должность/курс')
            question_text = dict_row_data.get('Вопрос')

            # если какие-то данные отсутствуют, то не добавляем в БД
            if None in [client_name, job_place, job_title, question_text]:
                continue

            try:
                # добавляем вопрос в БД
                Question.create(
                    category_id=category_obj.id,
                    client_name=client_name,
                    job_place=job_place,
                    job_title=job_title,
                    question_text=question_text,
                )
                # прибавляем 1 к общему кол-ву успешно обработанных вопросов
                total_result_dict[category]["успешно"] += 1
            except Exception as error:
                # print(error)
                raise error

    return total_result_dict
