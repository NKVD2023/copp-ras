import pytest
import datetime
from app.models.report import ReportTemplate, ReportDraft, ReportSubmission
from app.models.user import User
from app.extensions import db

def test_create_report_template(init_database):
    """Test creating a new report template."""
    template = ReportTemplate(
        name="Annual Feedback 2026",
        short_name="fb_2026",
        deadline=datetime.date(2026, 12, 31),
        is_published=True,
        schema={"fields": [{"name": "rating", "type": "number"}]}
    )
    db.session.add(template)
    db.session.commit()

    retrieved = ReportTemplate.query.filter_by(short_name="fb_2026").first()
    assert retrieved is not None
    assert retrieved.name == "Annual Feedback 2026"
    assert retrieved.is_published is True

def test_report_draft_creation(init_database):
    """Test creating a draft for a specific user and template."""
    user = User.query.filter_by(username='testuser').first()
    
    template = ReportTemplate(name="Test Template", deadline=datetime.date(2026, 10, 10), is_published=True, schema={})
    db.session.add(template)
    db.session.commit()

    draft = ReportDraft(template_id=template.id, user_id=user.id, data={"rating": 5})
    db.session.add(draft)
    db.session.commit()

    saved_draft = ReportDraft.query.filter_by(user_id=user.id, template_id=template.id).first()
    assert saved_draft is not None
    assert saved_draft.data["rating"] == 5

def test_report_submission(init_database):
    """Test submitting a completed report."""
    user = User.query.filter_by(username='testuser').first()
    template = ReportTemplate.query.filter_by(name="Test Template").first()
    if not template:
        template = ReportTemplate(name="Test Template", deadline=datetime.date(2026, 10, 10), is_published=True, schema={})
        db.session.add(template)
        db.session.commit()

    submission = ReportSubmission(template_id=template.id, user_id=user.id, data={"rating": 10})
    db.session.add(submission)
    db.session.commit()

    saved_submission = ReportSubmission.query.filter_by(user_id=user.id, template_id=template.id).first()
    assert saved_submission is not None
    assert saved_submission.data["rating"] == 10
    assert saved_submission.is_revision is False
