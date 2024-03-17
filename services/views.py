import time
from os import listdir, mkdir, remove
from datetime import datetime

from flask import render_template, request, make_response, url_for
from sqlalchemy.exc import IntegrityError

from data.constants import BASEDIR, IP_OR_DOMAIN, app
from database.models import User, Category
from .errors import PermissionsDenied, ServerProcessError
from .services import (make_password, check_password, get_user_from_request,
                       check_token_in_db, check_token_expired, remove_token,
                       upload_questions_to_db)


AUTH_REQUIRED_ENDPOINTS = ['/categories', '/questions', '/load_excel']
AUTH_HEADER_PREFIX = 'bearer'


@app.before_request
def check_auth_token():
    # получаем из запроса часть URL без протокола и домена/ip
    relative_url = request.url.removeprefix(IP_OR_DOMAIN)

    # достаём из куков токен авторизации юзера
    auth_cookie = request.cookies.get('Authorization')

    # если для эндпоинта требуется авторизация
    if relative_url in AUTH_REQUIRED_ENDPOINTS:
        # если юзер не авторизован
        if not auth_cookie:
            return render_template(
                "error_page.html",
                status=401,
                desc='Ресурс заблокирован! Требуется авторизация',
                url=url_for('login'),
                url_text='Вход'
            )
            # raise PermissionsDenied('Auth credentials were not provided! This resource require auth token.')

        auth_creds = auth_cookie.split(' ')
        # проверка кол-ва слов в куки авторизации
        if len(auth_creds) != 2:
            raise PermissionsDenied('Invalid auth credentials were provided! Length of auth cookie is not equal 2.')

        prefix, token = auth_creds
        if prefix.lower() != AUTH_HEADER_PREFIX:
            raise PermissionsDenied('Invalid auth credentials were provided!')

        # проверка токена на наличие в БД
        if not check_token_in_db(token=token):
            return render_template(
                "error_page.html",
                status=401,
                desc='Ресурс заблокирован! Требуется авторизация',
                url=url_for('login'),
                url_text='Вход'
            )
            # raise PermissionsDenied('Invalid auth credentials were provided! Token was not found in DB.')

        # проверка токена на то, истёк ли он или нет
        if check_token_expired(token=token):
            # создаём ответ со страницей ошибки
            response = make_response(render_template(
                "error_page.html",
                status=401,
                desc='Срок сессии аккаунта истёк! Требуется повторный вход в аккаунт',
                url=url_for('login'),
                url_text='Войти'
            ))
            # удаляем из БД токен авторизации юзера
            try:
                remove_token(token=token)
            except ServerProcessError:
                return render_template(
                    "error_page.html",
                    status=500,
                    desc='Ошибка сервера.',
                    url=url_for('index'),
                    url_text='Вернуться на главную'
                )
            # удаляем из куки токен авторизации юзера
            response.set_cookie('Authorization', max_age=0)
            return response
            # raise PermissionsDenied('Token is expired! Re-authorization required.')

    # если юзер уже авторизирован, но просится на ресурсы входа/регистрации
    elif auth_cookie and relative_url in ['/login', '/registr']:
        return render_template(
            "error_page.html",
            status=409,
            desc='Вы уже вошли в аккаунт! Если вам нужно войти в другой аккаунт, то вначале выйдите из текущего',
            url=url_for('index'),
            url_text='Вернуться на главную'
        )
        # raise AlreadyAuthenticated('You already authenticated!')


@app.route("/", methods=["GET", "POST"])
def index():
    # запрашивается выход из аккаунта
    if request.method == "POST":
        # создаём ответ
        response = make_response(render_template("index.html", logout=True, auth=False))
        # получаем куки авторизации
        auth_cookie = request.cookies.get('Authorization')

        # если был отправлен повторный POST запрос для logout
        if not auth_cookie:
            return response

        # удаляем из БД токен авторизации юзера
        auth_token = auth_cookie.split(' ')[-1]
        try:
            remove_token(token=auth_token)
        except ServerProcessError:
            return render_template(
                "error_page.html",
                status=500,
                desc='Ошибка сервера.',
                url=url_for('index'),
                url_text='Вернуться на главную'
            )

        # удаляем из куки токен авторизации юзера
        response.set_cookie('Authorization', max_age=0)
        return response

    # если в куках есть токен авторизации, то выводим страницу по шаблону для авторизированного юзера
    if request.cookies.get('Authorization'):
        return render_template("index.html", auth=True)
    # иначе - выводим страницу по шаблону для НЕ авторизированного юзера
    return render_template("index.html", auth=False)


@app.route("/registr", methods=["GET", "POST"])
def registr():
    if request.method == "GET":
        return render_template("registr.html")

    # запрашивается регистрация нового юзера
    elif request.method == "POST":
        # достаём из формы имя и пароль юзера
        request_username = request.form['username']
        request_password = request.form['password']
        # хешируем введённый пароль юзера
        hashed_password = make_password(str_password=request_password)

        # создаём нового юзера
        try:
            new_user = User.create(username=request_username, password=hashed_password)
        # если юзер с таким именем уже есть в БД
        except IntegrityError:
            return render_template(
                "error_page.html",
                status=400,
                desc='Пользователь с таким логином уже существует! Попробуйте использовать другой логин',
                url=url_for('registr'),
                url_text='Назад'
            )
            # raise CreateEntityError('User with such username already exists!')

        # создаём ответ и добавляем в куки токен авторизации юзера
        response = make_response(render_template(
            "registr.html",
            registr=True,
            username=new_user.username
        ))
        response.set_cookie('Authorization', f'Bearer {new_user.token}')
        return response


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # запрашивается вход существующего юзера
    if request.method == "POST":
        # достаём из формы имя и пароль юзера
        request_username = request.form['username']
        request_password = request.form['password']

        # достаём из БД юзера с введённым именем
        user = User.query().filter_by(username=request_username).first()
        # если юзер с введённым именем не найден
        if not user:
            return render_template(
                "error_page.html",
                status=400,
                desc='Неверный логин! Пользователя с таким логином не существует',
                url=url_for('login'),
                url_text='Назад'
            )
            # raise LoginError('User with such username was not found!')

        # проверяем на совпадение введённый пароль и хешированный пароль юзера из БД
        if not check_password(password_to_check=request_password, real_encode_password=user.password):
            return render_template(
                "error_page.html",
                status=400,
                desc='Неверный логин или пароль!',
                url=url_for('login'),
                url_text='Назад'
            )
            # raise LoginError('Invalid username and password!')

        # создаём ответ и добавляем в куки токен авторизации юзера
        response = make_response(render_template(
            "login.html",
            login=True,
            username=user.username
        ))
        response.set_cookie('Authorization', f'Bearer {user.token}')
        return response


@app.route("/load_excel", methods=["GET", "POST"])
def load_excel():
    if request.method == "GET":
        return render_template("load_excel.html")

    # отправка Excel-файла с вопросами
    if request.method == "POST":
        # достаём из формы Excel-файл
        request_file = request.files['excel_file']
        # получаем объект юзера из запроса
        user = get_user_from_request(request=request)

        now_time = datetime.now().strftime('%H_%M_%S')
        user_files_path = f'{BASEDIR}/files/user_{user.id}'

        # создаём каталог для файлов юзера, если такового нет
        if f'user_{user.id}' not in listdir(f'{BASEDIR}/files'):
            mkdir(user_files_path)

        # сохраняем файл
        full_file_path = f'{user_files_path}/{now_time}_{request_file.filename}'
        request_file.save(full_file_path)

        # добавления всех вопросов из загруженного Excel-файла в БД
        total_result_dict = upload_questions_to_db(path_to_file=full_file_path, user_id=user.id)

        # удаляем загруженный файл после добавления всех вопросов в БД
        remove(full_file_path)

        return render_template("load_excel.html", sent=True, total_result_dict=total_result_dict)


@app.route("/categories")
def categories():
    # получаем объект юзера из запроса
    user = get_user_from_request(request=request)

    categories_list = [(category.id, category.name) for category in user.categories]

    return render_template("get_categories.html", categories_list=categories_list)


@app.route("/questions/<category_id>")
def questions(category_id):
    category_obj = Category.query().filter_by(id=category_id).first()

    all_questions = category_obj.category_questions
    print(all_questions)

    return render_template("get_questions.html")
