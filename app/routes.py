import os
from flask import Flask

def create_app():
    app = Flask(_name_)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'dev-secret-key-change-before-deployment'
    )

    return app
