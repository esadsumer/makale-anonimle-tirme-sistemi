from app import app
from models import db, User

def create_admin():
    with app.app_context():
        # Mevcut admin kontrolü
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                institution='Kocaeli Üniversitesi',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin kullanıcısı oluşturuldu")
            print("E-posta: admin@example.com")
            print("Şifre: admin123")
        else:
            print("Admin kullanıcısı zaten mevcut")

if __name__ == '__main__':
    create_admin() 