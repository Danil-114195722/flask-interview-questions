from pathlib import Path

from sqlalchemy import create_engine
from flask import Flask


# строка подключения к БД
SQLITE_DB = "sqlite:///db.sqlite3"
# создаем движок SqlAlchemy
ENGINE = create_engine(SQLITE_DB)

BASEDIR = Path(__file__).parent.parent

app = Flask(__name__, template_folder=f"{BASEDIR}/templates")
