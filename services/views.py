from flask import render_template

from data.constants import app


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/registr")
def registr():
    return render_template("registr.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/logout")
def logout():
    return render_template("index.html")
