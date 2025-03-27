from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Hakem-Alan ilişki tablosu
reviewer_expertise = db.Table('reviewer_expertise',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('area_id', db.Integer, db.ForeignKey('expertise_area.id'), primary_key=True)
)

# Makale-Alan ilişki tablosu
paper_categories = db.Table('paper_categories',
    db.Column('paper_id', db.Integer, db.ForeignKey('paper.id'), primary_key=True),
    db.Column('area_id', db.Integer, db.ForeignKey('expertise_area.id'), primary_key=True)
)

class ExpertiseArea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    main_category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'{self.main_category} - {self.sub_category}'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    institution = db.Column(db.String(100))
    role = db.Column(db.String(20))  # 'admin', 'reviewer'
    expertise_areas = db.relationship('ExpertiseArea', secondary=reviewer_expertise, lazy='subquery',
        backref=db.backref('reviewers', lazy=True))
    reviews = db.relationship('Review', backref='reviewer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Paper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    authors = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_file_path = db.Column(db.String(500))  # Orijinal dosya yolu
    tracking_number = db.Column(db.String(8), unique=True, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Beklemede')
    submitter_email = db.Column(db.String(120), nullable=False)
    institution = db.Column(db.String(200))  # Kurum bilgisi
    keywords = db.Column(db.String(500))  # Virgülle ayrılmış anahtar kelimeler
    categories = db.relationship('ExpertiseArea', secondary=paper_categories, lazy='subquery',
        backref=db.backref('papers', lazy=True))
    reviews = db.relationship('Review', backref='paper', lazy=True)
    messages = db.relationship('Message', backref='paper', lazy=True)

    def __repr__(self):
        return f'<Paper {self.title}>'

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    technical_quality = db.Column(db.Integer)
    methodology = db.Column(db.Integer)
    contribution = db.Column(db.Integer)
    presentation = db.Column(db.Integer)
    comments = db.Column(db.Text)
    recommendation = db.Column(db.String(50))
    confidential_comments = db.Column(db.Text)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Beklemede')  # Beklemede, Tamamlandı

    def __repr__(self):
        return f'<Review {self.id} for Paper {self.paper_id}>'

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    sender_email = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_from_author = db.Column(db.Boolean, default=True)
    is_read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Message {self.id}>' 