import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename
from app.models import Document
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}


def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@main.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        file = request.files.get('document')

        if not file or file.filename == '':
            flash('Please select a document.')
            return redirect(url_for('main.upload'))

        if not allowed_file(file.filename):
            flash('File type not allowed.')
            return redirect(url_for('main.upload'))

        original_name = secure_filename(file.filename)

        if not original_name:
            flash('Invalid filename.')
            return redirect(url_for('main.upload'))

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        upload_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            stored_name
        )

        try:
            file.save(upload_path)

            document = Document(
                filename=stored_name,
                original_filename=original_name,
                owner_id=session['user_id']
            )

            db.session.add(document)
            db.session.commit()

            flash('Document uploaded successfully!')
            return redirect(url_for('main.dashboard'))

        except Exception:
            db.session.rollback()

            if os.path.exists(upload_path):
                os.remove(upload_path)

            flash('Upload failed. Please try again.')
            return redirect(url_for('main.upload'))

    return render_template('upload.html')
