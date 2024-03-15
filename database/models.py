import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Session, relationship


# строка подключения к БД
SQLITE_DB = "sqlite:///db.sqlite3"
# создаем движок SqlAlchemy
ENGINE = sa.create_engine(SQLITE_DB)


class DBSession:
    """
        Контекстный менеджер для соединения с БД.
        При успехе: совершает коммит.
        При неудаче: делает откат изменений и выдаёт ошибку
    """

    def __enter__(self):
        self.session = Session(bind=ENGINE)
        return self.session

    def __exit__(self, *args, **kwargs):
        try:
            self.session.commit()
        except Exception as error:
            self.session.rollback()
            raise error
        finally:
            self.session.close()


class Base(DeclarativeBase):
    """Базовый класс для моделей"""

    @classmethod
    def create(cls, **kwargs):
        with DBSession() as db:
            new_object = cls(**kwargs)
            db.add(new_object)

    @classmethod
    def query(cls, *args, **kwargs):
        with DBSession() as db:
            return db.query(cls, *args, **kwargs)

    @classmethod
    def delete(cls, pk: int):
        with DBSession() as db:
            table_object = db.query(cls).filter_by(id=pk).first()
            db.delete(table_object)


class User(Base):
    __tablename__ = "user"

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    username = sa.Column(sa.String(50), unique=True)
    password = sa.Column(sa.String(255))

    tokens = relationship("Token", back_populates="token_user", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="question_user", cascade="all, delete-orphan")

    def __str__(self):
        return f"User {self.id}: {self.username}"


class Token(Base):
    __tablename__ = "token"

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"))
    token = sa.Column(sa.String(255))

    token_user = relationship("User", back_populates="tokens")

    def __str__(self):
        return f"Token {self.id} (user {self.user_id}): {self.token}"


class Category(Base):
    __tablename__ = "category"

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    name = sa.Column(sa.String(150), unique=True)

    category_questions = relationship("Question", back_populates="category")

    def __str__(self):
        return f"Category {self.id}: {self.name}"


class Question(Base):
    __tablename__ = "question"
    __table_args__ = (
        sa.Index('idx_question_user_category', 'user_id', 'category_id'),
    )

    id = sa.Column(sa.Integer, primary_key=True, index=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.id"))
    category_id = sa.Column(sa.Integer, sa.ForeignKey("category.id"))
    client_last_name = sa.Column(sa.String(150))
    client_first_name = sa.Column(sa.String(100))
    client_patron = sa.Column(sa.String(100), nullable=True)
    job_place = sa.Column(sa.String(255))
    job_title = sa.Column(sa.String(150))
    question_text = sa.Column(sa.Text)

    question_user = relationship("User", back_populates="questions")
    category = relationship("Category", back_populates="category_questions")

    def __str__(self):
        if len(qu_text := str(self.question_text)) > (max_len := 25):
            return f"Question {self.id} (user {self.user_id}, category {self.category_id}): {qu_text[:max_len]}..."
        else:
            return f"Question {self.id} (user {self.user_id}, category {self.category_id}): {qu_text}"


if __name__ == "__main__":
    try:
        # создаем таблицы
        Base.metadata.create_all(bind=ENGINE)
        print("База данных и таблицы созданы успешно!")
    except Exception as outer_error:
        raise outer_error
