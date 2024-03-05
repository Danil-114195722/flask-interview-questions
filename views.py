from flask import render_template

from base import app


@app.route("/")
def index():
    print('hello world')
    return render_template("index.html")
