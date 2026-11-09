import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'trustvault-development-key'
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trustvault.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        from app import models
        db.create_all()

    from app.routes import main
    app.register_blueprint(main)

    return app
