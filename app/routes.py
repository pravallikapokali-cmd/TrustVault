from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)
from app.models import db, User

main = Blueprint('main', _name_)


# Home page
@main.route('/')
def home():
    return render_template('index.html')


# User Registration
@main.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('Please fill all fields.')
            return redirect(url_for('main.register'))

        if len(password) < 8:
            flash('Password must contain at least 8 characters.')
            return redirect(url_for('main.register'))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('main.register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Registration failed. Please try again.')
            return redirect(url_for('main.register'))

        flash('Registration successful! Please login.')
        return redirect(url_for('main.login'))

    return render_template('register.html')


# User Login
@main.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username

            flash('Login successful!')
            return redirect(url_for('main.home'))

        flash('Invalid email or password.')

    return render_template('login.html')


# User Logout
@main.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('main.login'))


@main.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    return render_template(
        'dashboard.html',
        username=session.get('username')
    )
