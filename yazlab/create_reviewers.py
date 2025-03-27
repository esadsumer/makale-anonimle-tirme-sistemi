from app import app
from models import db, User, ExpertiseArea

def create_expertise_areas():
    with app.app_context():
        # Veritabanı tablolarını oluştur
        db.create_all()
        
        areas = [
            # Yapay Zeka ve Makine Öğrenimi
            ('Yapay Zeka ve Makine Öğrenimi', 'Derin öğrenme'),
            ('Yapay Zeka ve Makine Öğrenimi', 'Doğal dil işleme'),
            ('Yapay Zeka ve Makine Öğrenimi', 'Bilgisayarla görü'),
            ('Yapay Zeka ve Makine Öğrenimi', 'Generatif yapay zeka'),
            
            # İnsan-Bilgisayar Etkileşimi
            ('İnsan-Bilgisayar Etkileşimi', 'Beyin-bilgisayar arayüzleri'),
            ('İnsan-Bilgisayar Etkileşimi', 'Kullanıcı deneyimi tasarımı'),
            ('İnsan-Bilgisayar Etkileşimi', 'Artırılmış ve sanal gerçeklik'),
            
            # Büyük Veri ve Veri Analitiği
            ('Büyük Veri ve Veri Analitiği', 'Veri madenciliği'),
            ('Büyük Veri ve Veri Analitiği', 'Veri görselleştirme'),
            ('Büyük Veri ve Veri Analitiği', 'Veri işleme sistemleri'),
            ('Büyük Veri ve Veri Analitiği', 'Zaman serisi analizi'),
            
            # Siber Güvenlik
            ('Siber Güvenlik', 'Şifreleme algoritmaları'),
            ('Siber Güvenlik', 'Güvenli yazılım geliştirme'),
            ('Siber Güvenlik', 'Ağ güvenliği'),
            ('Siber Güvenlik', 'Kimlik doğrulama sistemleri'),
            ('Siber Güvenlik', 'Adli bilişim'),
            
            # Ağ ve Dağıtık Sistemler
            ('Ağ ve Dağıtık Sistemler', '5G ve yeni nesil ağlar'),
            ('Ağ ve Dağıtık Sistemler', 'Bulut bilişim'),
            ('Ağ ve Dağıtık Sistemler', 'Blockchain teknolojisi'),
            ('Ağ ve Dağıtık Sistemler', 'P2P ve merkeziyetsiz sistemler')
        ]
        
        created_areas = []
        for main_cat, sub_cat in areas:
            area = ExpertiseArea(main_category=main_cat, sub_category=sub_cat)
            db.session.add(area)
            created_areas.append(area)
        
        db.session.commit()
        return created_areas

def create_reviewers():
    with app.app_context():
        reviewers = [
            {
                'email': 'ai.reviewer@example.com',
                'password': 'reviewer123',
                'first_name': 'Ali',
                'last_name': 'Yılmaz',
                'institution': 'Kocaeli Üniversitesi',
                'expertise': ['Derin öğrenme', 'Doğal dil işleme', 'Generatif yapay zeka']
            },
            {
                'email': 'hci.reviewer@example.com',
                'password': 'reviewer123',
                'first_name': 'Ayşe',
                'last_name': 'Demir',
                'institution': 'Kocaeli Üniversitesi',
                'expertise': ['Beyin-bilgisayar arayüzleri', 'Kullanıcı deneyimi tasarımı', 'Veri görselleştirme']
            },
            {
                'email': 'data.reviewer@example.com',
                'password': 'reviewer123',
                'first_name': 'Mehmet',
                'last_name': 'Kaya',
                'institution': 'Kocaeli Üniversitesi',
                'expertise': ['Veri madenciliği', 'Veri işleme sistemleri', 'Zaman serisi analizi']
            },
            {
                'email': 'security.reviewer@example.com',
                'password': 'reviewer123',
                'first_name': 'Zeynep',
                'last_name': 'Şahin',
                'institution': 'Kocaeli Üniversitesi',
                'expertise': ['Şifreleme algoritmaları', 'Ağ güvenliği', 'Kimlik doğrulama sistemleri']
            },
            {
                'email': 'network.reviewer@example.com',
                'password': 'reviewer123',
                'first_name': 'Can',
                'last_name': 'Öztürk',
                'institution': 'Kocaeli Üniversitesi',
                'expertise': ['5G ve yeni nesil ağlar', 'Blockchain teknolojisi', 'Bulut bilişim']
            }
        ]
        
        for reviewer_data in reviewers:
            # Mevcut hakem kontrolü
            existing_reviewer = User.query.filter_by(email=reviewer_data['email']).first()
            if not existing_reviewer:
                reviewer = User(
                    email=reviewer_data['email'],
                    first_name=reviewer_data['first_name'],
                    last_name=reviewer_data['last_name'],
                    institution=reviewer_data['institution'],
                    role='reviewer'
                )
                reviewer.set_password(reviewer_data['password'])
                
                # Uzmanlık alanlarını ekle
                for expertise in reviewer_data['expertise']:
                    area = ExpertiseArea.query.filter_by(sub_category=expertise).first()
                    if area:
                        reviewer.expertise_areas.append(area)
                
                db.session.add(reviewer)
                print(f"Hakem oluşturuldu: {reviewer.email}")
            else:
                print(f"Hakem zaten mevcut: {reviewer_data['email']}")
        
        db.session.commit()

if __name__ == '__main__':
    print("Uzmanlık alanları oluşturuluyor...")
    create_expertise_areas()
    print("Hakemler oluşturuluyor...")
    create_reviewers()
    print("İşlem tamamlandı.") 