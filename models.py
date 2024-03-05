from base import app, db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)

    def __init__(self, username: str) -> None:
        self.username = username

    def __repr__(self) -> str:
        return f'<User {self.username}>'


def create_user(username: str) -> User:
    # Create user with the provided input.
    new_user = User(username=username)

    # Actually add this user to the database
    db.session.add(new_user)
    # Save all pending changes to the database
    db.session.commit()

    return new_user


if __name__ == "__main__":
    # Run this file directly to create the database tables.
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
    print("Done!")
