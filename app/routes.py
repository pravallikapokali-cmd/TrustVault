from flask import Blueprint

main = Blueprint('main', _name_)

@main.route('/')
def home():
    return "Welcome to TrustVault - Secure Document Sharing Platform"
