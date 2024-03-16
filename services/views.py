from flask import render_template, request, make_response

from data.constants import IP_OR_DOMAIN, app
from database.models import User
from .errors import PermissionsDenied, AlreadyAuthenticated


AUTH_REQUIRED_ENDPOINTS = ['/categories', '/questions', 'load_excel/']


@app.before_request
def check_auth_token():
    relative_url = request.url.removeprefix(IP_OR_DOMAIN)

    auth_token = request.cookies.get('Authorization')
    if relative_url in AUTH_REQUIRED_ENDPOINTS:
        if not auth_token:
            raise PermissionsDenied('Auth credentials were not provided! This resource require auth token.')
    elif auth_token and relative_url in ['/login', '/registr']:
        raise AlreadyAuthenticated('You already authenticated!')


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        response = make_response(render_template("index.html", logout=True, auth=False))
        response.set_cookie('Authorization', max_age=0)
        return response

    if request.cookies.get('Authorization'):
        return render_template("index.html", auth=True)
    return render_template("index.html", auth=False)


@app.route("/registr", methods=["GET", "POST"])
def registr():
    if request.method == "POST":
        request_username = request.form['username']
        request_password = request.form['password']

        new_user = User.create(username=request_username, password=request_password)
        print('new_user', new_user)

        response = make_response(render_template(
            "registr.html",
            registr=True,
            username=new_user.username
        ))
        response.set_cookie('Authorization', 'Bearer sample_instead_of_token')
        return response

    return render_template("registr.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        request_username = request.form['username']
        request_password = request.form['password']

        user = User.query().filter_by(username=request_username).first()
        print('user', user)

        response = make_response(render_template(
            "login.html",
            login=True,
            username=user.username
        ))
        response.set_cookie('Authorization', 'Bearer sample_instead_of_token')
        return response

    return render_template("login.html")
