from flask import render_template, request

from data.constants import IP_OR_DOMAIN, app
from database.models import User, DBSession


@app.before_request
def check_auth_token():
    print(request)
    print(request.__dict__)
    print('FFFFFFFFFFFFFFFFFFFFFF')
    print(request.headers)
    print('DDDDDDDDDDDDDDDDDDDDDD')
    print(request.access_control_request_headers)
    print(request.url.removeprefix(IP_OR_DOMAIN))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/registr", methods=["GET", "POST"])
def registr():
    if request.method == "POST":
        request_username = request.form['username']
        request_password = request.form['password']

        new_user = User.create(username=request_username, password=request_password)
        print('new_user', new_user)

        return render_template("registr.html", registr=True, username=new_user.username)
    return render_template("registr.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/logout")
def logout():
    return render_template("index.html")
