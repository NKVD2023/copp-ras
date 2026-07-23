from app import create_app
from app.models import ReportTemplate

app = create_app()
with app.app_context():
    templates = ReportTemplate.query.all()
    print("Found templates:", len(templates))
