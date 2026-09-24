import pytest
from app.models.files import UploadedFile
from app.models.user import User
from app.extensions import db

def test_uploaded_file_creation(init_database):
    """Test creating a file record in the database."""
    user = User.query.filter_by(username='testuser').first()
    
    file_record = UploadedFile(
        filename="report_2026.pdf",
        filepath="/uploads/report_2026.pdf",
        uploader_id=user.id,
        file_size=1024500
    )
    db.session.add(file_record)
    db.session.commit()

    saved_file = UploadedFile.query.filter_by(filename="report_2026.pdf").first()
    assert saved_file is not None
    assert saved_file.uploader.username == 'testuser'
    assert saved_file.file_size == 1024500
