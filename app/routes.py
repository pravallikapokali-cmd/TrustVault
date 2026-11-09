
import os
import uuid

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session,
    abort, send_file
)
from werkzeug.utils import secure_filename

from app import db
from app.models import User, Document, DocumentAccess, AuditLog

main = Blueprint('main', __name__)

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'uploads'
)


@main.route('/')
def home():
    return render_template('index.html')


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

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('main.register'))

        user = User(username=username, email=email)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Registration failed.')
            return redirect(url_for('main.register'))

        flash('Registration successful! Please login.')
        return redirect(url_for('main.login'))

    return render_template('register.html')


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
            return redirect(url_for('main.dashboard'))

        flash('Invalid email or password.')

    return render_template('login.html')


@main.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('main.login'))


@main.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    return redirect(url_for('main.documents'))


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        file = request.files.get('document')

        if not file or not file.filename:
            flash('Please select a file.')
            return redirect(url_for('main.upload'))

        filename = secure_filename(file.filename)
        allowed = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}

        if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed:
            flash('File type not allowed.')
            return redirect(url_for('main.upload'))

        if request.content_length and request.content_length > 10 * 1024 * 1024:
            flash('File size must be below 10 MB.')
            return redirect(url_for('main.upload'))

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        stored_filename = str(uuid.uuid4()) + '_' + filename
        file_path = os.path.join(UPLOAD_FOLDER, stored_filename)

        try:
            file.save(file_path)

            document = Document(
                filename=stored_filename,
                original_filename=filename,
                owner_id=session['user_id']
            )

            db.session.add(document)
            db.session.flush()

            log = AuditLog(
                document_id=document.id,
                user_id=session['user_id'],
                action='Document uploaded'
            )

            db.session.add(log)
            db.session.commit()

        except Exception:
            db.session.rollback()
            if os.path.exists(file_path):
                os.remove(file_path)
            flash('Upload failed. Please try again.')
            return redirect(url_for('main.upload'))

        flash('Document uploaded successfully!')
        return redirect(url_for('main.documents'))

    return render_template('upload.html')


@main.route('/documents')
def documents():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    user_documents = Document.query.filter_by(
        owner_id=session['user_id']
    ).order_by(Document.uploaded_at.desc()).all()

    return render_template(
        'documents.html',
        documents=user_documents
    )


@main.route('/download/<int:document_id>')
def download_document(document_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    document = Document.query.get_or_404(document_id)
    user_id = session['user_id']
    user = User.query.get(user_id)

    is_owner = document.owner_id == user_id
    is_admin = user and getattr(user, 'role', None) == 'admin'

    access = DocumentAccess.query.filter_by(
        document_id=document_id,
        user_id=user_id
    ).first()

    has_permission = access and access.permission in [
        'view', 'download', 'edit'
    ]

    if not (is_owner or is_admin or has_permission):
        abort(403)

    file_path = os.path.join(UPLOAD_FOLDER, document.filename)

    if not os.path.isfile(file_path):
        abort(404)

    log = AuditLog(
        document_id=document.id,
        user_id=user_id,
        action='Document downloaded'
    )

    db.session.add(log)
    db.session.commit()

    return send_file(
        file_path,
        as_attachment=True,
        download_name=document.original_filename
    )


@main.route('/share/<int:document_id>', methods=['GET', 'POST'])
def share_document(document_id):
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    document = Document.query.get_or_404(document_id)
    user_id = session['user_id']
    current_user = User.query.get(user_id)

    if document.owner_id != user_id and (
        not current_user or getattr(current_user, 'role', None) != 'admin'
    ):
        abort(403)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        permission = request.form.get('permission', 'view')

        if permission not in ['view', 'download', 'edit']:
            abort(400)

        target_user = User.query.filter_by(email=email).first()

        if not target_user:
            flash('User not found.')
            return redirect(url_for(
                'main.share_document',
                document_id=document.id
            ))

        if target_user.id == user_id:
            flash('You already own this document.')
            return redirect(url_for('main.documents'))

        access = DocumentAccess.query.filter_by(
            document_id=document.id,
            user_id=target_user.id
        ).first()

        if access:
            access.permission = permission
        else:
            access = DocumentAccess(
                document_id=document.id,
                user_id=target_user.id,
                permission=permission
            )
            db.session.add(access)

        log = AuditLog(
            document_id=document.id,
            user_id=user_id,
            action='Document shared with ' + email
        )

        db.session.add(log)
        db.session.commit()

        flash('Document shared successfully!')
        return redirect(url_for('main.documents'))

    return render_template('share.html', document=document)


@main.route('/audit-logs')
def audit_logs():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    current_user = User.query.get(session['user_id'])

    if not current_user or getattr(current_user, 'role', None) != 'admin':
        abort(403)

    logs = AuditLog.query.order_by(
        AuditLog.timestamp.desc()
    ).all()

    return render_template('audit_logs.html', logs=logs)



