from flask import render_template, request, make_response
from sqlalchemy.exc import IntegrityError

from data.constants import IP_OR_DOMAIN, app
from database.models import User
from .errors import PermissionsDenied, AlreadyAuthenticated, CreateEntityError, LoginError
from .services import make_password, check_password


AUTH_REQUIRED_ENDPOINTS = ['/categories', '/questions', 'load_excel/']


@app.before_request
def check_auth_token():
    # получаем из запроса часть URL без протокола и домена/ip
    relative_url = request.url.removeprefix(IP_OR_DOMAIN)

    # достаём из куков токен авторизации юзера
    auth_token = request.cookies.get('Authorization')
    # если для эндпоинта требуется авторизация
    if relative_url in AUTH_REQUIRED_ENDPOINTS:
        # если юзер не авторизован
        if not auth_token:
            raise PermissionsDenied('Auth credentials were not provided! This resource require auth token.')

        # проверка токена на наличие в БД
        # проверка токена на то, истёк ли он или нет

    # если юзер уже авторизирован, но просится на ресурсы входа/регистрации
    elif auth_token and relative_url in ['/login', '/registr']:
        raise AlreadyAuthenticated('You already authenticated!')


@app.route("/", methods=["GET", "POST"])
def index():
    # запрашивается выход из аккаунта
    if request.method == "POST":
        # создаём ответ
        response = make_response(render_template("index.html", logout=True, auth=False))
        # удаляем из БД токен авторизации юзера
        # auth_token = request.cookies.get('Authorization')
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
            raise CreateEntityError('User with such username already exists!')

        # создаём ответ и добавляем в куки токен авторизации юзера
        response = make_response(render_template(
            "registr.html",
            registr=True,
            username=new_user.username
        ))
        response.set_cookie('Authorization', f'Bearer new_user.token')
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
            raise LoginError('User with such username was not found!')

        # проверяем на совпадение введённый пароль и хешированный пароль юзера из БД
        if not check_password(password_to_check=request_password, real_encode_password=user.password):
            raise LoginError('Invalid username and password!')

        # создаём ответ и добавляем в куки токен авторизации юзера
        response = make_response(render_template(
            "login.html",
            login=True,
            username=user.username
        ))
        response.set_cookie('Authorization', 'Bearer new_user.token')
        return response
