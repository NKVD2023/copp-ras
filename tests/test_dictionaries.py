import pytest
from app.models.dictionaries import Dictionary
from app.models.department import Department
from app.extensions import db

def test_create_dictionary(init_database):
    """Test creating a list template (dictionary)."""
    dict_item = Dictionary(name="Cities", items=["Moscow", "Simferopol", "Yalta"])
    db.session.add(dict_item)
    db.session.commit()

    retrieved = Dictionary.query.filter_by(name="Cities").first()
    assert retrieved is not None
    assert len(retrieved.items) == 3
    assert "Yalta" in retrieved.items

def test_dictionary_department_relationship(init_database):
    """Test linking a dictionary to a specific department."""
    dept = Department(name="IT Department")
    db.session.add(dept)
    db.session.commit()

    dict_item = Dictionary(name="Hardware", items=["Laptop", "PC"], department_id=dept.id)
    db.session.add(dict_item)
    db.session.commit()

    retrieved_dict = Dictionary.query.filter_by(name="Hardware").first()
    assert retrieved_dict.department_id == dept.id
