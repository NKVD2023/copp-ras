import sqlite3
import os

DB_PATH = 'reports.db'

def upgrade():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add is_template to report_templates
        cursor.execute("ALTER TABLE report_templates ADD COLUMN is_template BOOLEAN DEFAULT 0")
        print("Successfully added 'is_template' to 'report_templates'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'is_template' already exists in 'report_templates'.")
        else:
            print(f"Error adding 'is_template': {e}")
            
    try:
        # Add is_archived to report_submissions
        cursor.execute("ALTER TABLE report_submissions ADD COLUMN is_archived BOOLEAN DEFAULT 0")
        print("Successfully added 'is_archived' to 'report_submissions'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'is_archived' already exists in 'report_submissions'.")
        else:
            print(f"Error adding 'is_archived': {e}")
    
    conn.commit()
    conn.close()
    print("Database upgrade finished.")

if __name__ == "__main__":
    upgrade()
