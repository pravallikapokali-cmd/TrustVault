import os
from flask import Flask
from app.models import db


def create_app():
    app = Flask(_name_)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'dev-secret-key-change-before-deployment'
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'sqlite:///trustvault.db'
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    # Register routes
    from app.routes import main
    app.register_blueprint(main)

    return app
