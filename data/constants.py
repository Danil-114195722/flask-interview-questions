import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path

from sqlalchemy import create_engine
from flask import Flask


load_dotenv()


BASEDIR = Path(__file__).parent.parent

# строка подключения к БД
SQLITE_DB = f"sqlite:///{BASEDIR}/db.sqlite3"
# создаем движок SqlAlchemy
ENGINE = create_engine(SQLITE_DB, pool_size=20, max_overflow=10)

JWT_EXPIRE = timedelta(minutes=5)
SECRET_KEY = os.getenv('SECRET_KEY')
IP_OR_DOMAIN = "http://127.0.0.1:5000"

app = Flask(__name__, template_folder=f"{BASEDIR}/templates")
