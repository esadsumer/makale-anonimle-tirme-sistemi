from app import app
from models import db

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Veritabanı başarıyla oluşturuldu")

if __name__ == "__main__":
    init_db() 