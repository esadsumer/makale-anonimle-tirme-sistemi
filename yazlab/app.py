from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
import re
import PyPDF2
import logging
from logging.handlers import RotatingFileHandler
from forms import LoginForm, RegisterForm, PaperSubmissionForm, ReviewForm, TrackPaperForm, AnonymousPaperSubmissionForm, MessageForm
from models import db, User, Paper, Review, ExpertiseArea, Message
from paper_anonymizer import PaperAnonymizer
from sqlalchemy.orm import joinedload
import io
from PIL import Image
import fitz  # PyMuPDF

# Logging ayarları
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli-anahtar-buraya'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///makale.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ANONYMIZED_FOLDER'] = 'anonymized'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['DEBUG'] = True

# Dizinleri oluştur
os.makedirs('uploads', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Logging configuration
file_handler = RotatingFileHandler('logs/academic_papers.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Academic Papers startup')

# PaperAnonymizer örneği oluştur
paper_anonymizer = PaperAnonymizer(app.config['UPLOAD_FOLDER'], app.config['ANONYMIZED_FOLDER'])

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('dashboard'))
        elif current_user.role == 'reviewer':
            return redirect(url_for('reviewer_dashboard_detail', reviewer_id=current_user.id))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            app.logger.info(f"Login attempt for email: {form.email.data}")
            user = User.query.filter_by(email=form.email.data).first()
            
            if user and user.check_password(form.password.data):
                if user.role == 'admin':
                    login_user(user, remember=form.remember_me.data)
                    app.logger.info(f"Successful admin login: {user.email}")
                    flash('Editör olarak giriş yaptınız!', 'success')
                    return redirect(url_for('dashboard'))
                elif user.role == 'reviewer':
                    login_user(user, remember=form.remember_me.data)
                    app.logger.info(f"Successful reviewer login: {user.email}")
                    flash('Hakem olarak giriş yaptınız!', 'success')
                    return redirect(url_for('reviewer_dashboard_detail', reviewer_id=user.id))
                else:
                    app.logger.warning(f"Login failed - Invalid role: {form.email.data}")
                    flash('Bu hesap için giriş yetkisi yok', 'danger')
            else:
                if not user:
                    app.logger.warning(f"Login failed - User not found: {form.email.data}")
                    flash('Geçersiz e-posta adresi', 'danger')
                else:
                    app.logger.warning(f"Login failed - Invalid password: {form.email.data}")
                    flash('Geçersiz şifre', 'danger')
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('Giriş yapılırken bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    
    return render_template('login.html', title='Giriş', form=form)

@app.route('/dashboard')
def dashboard():
    """Dashboard'u göster"""
    try:
        # Tüm makaleleri getir
        papers = Paper.query.order_by(Paper.submission_date.desc()).all()
        
        # İstatistikleri hesapla
        stats = {
            'total': len(papers),
            'pending': len([p for p in papers if p.status == 'Beklemede']),
            'accepted': len([p for p in papers if p.status == 'Kabul']),
            'rejected': len([p for p in papers if p.status == 'Red'])
        }
        
        return render_template('dashboard.html', 
                             papers=papers, 
                             stats=stats)
            
    except Exception as e:
        app.logger.error(f"Dashboard hatası: {str(e)}")
        return render_template('dashboard.html', 
                             papers=[], 
                             stats={'total': 0, 'pending': 0, 'accepted': 0, 'rejected': 0})

def blur_image(image_data, blur_radius=20):
    """Görüntüyü bulanıklaştırır"""
    try:
        # Görüntüyü PIL Image nesnesine dönüştür
        image = Image.open(io.BytesIO(image_data))
        
        # Görüntüyü bulanıklaştır (daha güçlü bulanıklık için)
        blurred_image = image.filter(Image.BLUR)
        # İkinci kez bulanıklaştır
        blurred_image = blurred_image.filter(Image.BLUR)
        # Üçüncü kez bulanıklaştır
        blurred_image = blurred_image.filter(Image.BLUR)
        
        # Bulanıklaştırılmış görüntüyü bytes'a dönüştür
        output = io.BytesIO()
        blurred_image.save(output, format=image.format or 'PNG')
        return output.getvalue()
    except Exception as e:
        app.logger.error(f"Görüntü bulanıklaştırma hatası: {str(e)}")
        return image_data

def analyze_paper_content(file_path):
    """
    PDF dosyasından yazar bilgilerini tespit eder
    """
    try:
        doc = fitz.open(file_path)
        text = ""
        
        # Tüm sayfaların metnini al
        for page in doc:
            text += page.get_text()
        
        # Yazar bilgilerini tespit et
        author_info = {
            'names': [],
            'emails': [],
            'institutions': []
        }
        
        # E-posta adreslerini bul
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        author_info['emails'] = list(set(emails))
        
        # Kurum bilgilerini bul (genellikle yazar isimlerinden sonra gelir)
        institution_patterns = [
            r'Department of [^,]+',
            r'Faculty of [^,]+',
            r'University of [^,]+',
            r'Institute of [^,]+',
            r'[A-Z][a-z]+ University',
            r'[A-Z][a-z]+ Institute'
        ]
        
        for pattern in institution_patterns:
            institutions = re.findall(pattern, text)
            author_info['institutions'].extend(institutions)
        
        # Yazar isimlerini bul (genellikle başlıktan sonra ve kurum bilgilerinden önce)
        name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        names = re.findall(name_pattern, text)
        author_info['names'] = list(set(names))
        
        doc.close()
        return author_info
        
    except Exception as e:
        app.logger.error(f"Makale analizi hatası: {str(e)}")
        return None

def anonymize_paper_content(file_path, author_info):
    """
    Makale içeriğini anonimleştirir
    """
    try:
        doc = fitz.open(file_path)
        output_doc = fitz.open()
        
        # Yazar referans kodları oluştur
        author_refs = {}
        for i, name in enumerate(author_info['names'], 1):
            author_refs[name] = f"Author_{i}"
        
        # Her sayfayı işle
        for page_num in range(len(doc)):
            page = doc[page_num]
            new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
            
            # Metni al
            text = page.get_text()
            
            # Yazar isimlerini değiştir
            for name, ref in author_refs.items():
                text = re.sub(r'\b' + re.escape(name) + r'\b', ref, text)
            
            # E-posta adreslerini değiştir
            for email in author_info['emails']:
                text = re.sub(r'\b' + re.escape(email) + r'\b', 'author@example.com', text)
            
            # Kurum bilgilerini değiştir
            for institution in author_info['institutions']:
                text = re.sub(r'\b' + re.escape(institution) + r'\b', 'Institution', text)
            
            # Sayfayı güncelle
            new_page.insert_text((0, 0), text)
        
        # Anonimleştirilmiş dosyayı kaydet
        anonymized_path = os.path.join(app.config['ANONYMIZED_FOLDER'], os.path.basename(file_path))
        os.makedirs(app.config['ANONYMIZED_FOLDER'], exist_ok=True)
        
        output_doc.save(anonymized_path)
        output_doc.close()
        doc.close()
        
        return anonymized_path
        
    except Exception as e:
        app.logger.error(f"Anonimleştirme hatası: {str(e)}")
        return None

@app.route('/submit_paper', methods=['GET', 'POST'])
def submit_paper():
    form = PaperSubmissionForm()
    if form.validate_on_submit():
        try:
            file = form.paper_file.data
            if not file or not file.filename.lower().endswith('.pdf'):
                flash('Lütfen geçerli bir PDF dosyası seçin.', 'danger')
                return redirect(request.url)
            
            # Benzersiz takip numarası oluştur
            tracking_number = generate_tracking_number()
            filename = secure_filename(file.filename)
            unique_filename = f"{tracking_number}_{filename}"
            
            # Dosyayı kaydet
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Dosyanın başarıyla kaydedildiğini kontrol et
            if not os.path.exists(file_path):
                flash('Dosya kaydedilirken bir hata oluştu.', 'danger')
                return redirect(request.url)
            
            # Makaleyi veritabanına kaydet
            paper = Paper(
                title=form.title.data,
                authors=form.authors.data,
                submitter_email=form.email.data,
                institution=form.institution.data,
                file_path=file_path,  # Orijinal dosya
                tracking_number=tracking_number,
                status='Beklemede',
                submission_date=datetime.utcnow()
            )
            
            db.session.add(paper)
            db.session.commit()
            
            flash(f'Makaleniz başarıyla yüklendi! Takip numaranız: {tracking_number}', 'success')
            return redirect(url_for('track_paper', tracking_number=tracking_number))
            
        except Exception as e:
            app.logger.error(f"Makale yükleme hatası: {str(e)}")
            flash('Makale yüklenirken bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
            return redirect(request.url)
    
    return render_template('submit_paper.html', form=form)

@app.route('/track_paper', methods=['GET', 'POST'])
def track_paper():
    form = TrackPaperForm()
    paper = None
    
    if form.validate_on_submit():
        try:
            # Makaleyi bul
            paper = Paper.query.filter_by(
                tracking_number=form.tracking_id.data,
                submitter_email=form.email.data
            ).first()
            
            if not paper:
                flash('Makale bulunamadı veya e-posta adresi eşleşmiyor.', 'error')
                return redirect(url_for('track_paper'))
            
            # Makale durumunu güncelle
            if paper.status == 'Beklemede':
                paper.status = 'İnceleniyor'
                paper.last_update = datetime.utcnow()
                db.session.commit()
                
        except Exception as e:
            app.logger.error(f"Makale sorgulama hatası: {str(e)}")
            flash('Makale sorgulanırken bir hata oluştu.', 'error')
            return redirect(url_for('track_paper'))
    
    return render_template('track_paper.html', form=form, paper=paper)

@app.route('/review_paper/<int:paper_id>', methods=['GET', 'POST'])
def review_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    form = ReviewForm()
    
    # Mevcut değerlendirmeyi kontrol et
    existing_review = Review.query.filter_by(paper_id=paper_id).first()
    
    # Eğer değerlendirme yoksa veya hakem atanmamışsa
    if not existing_review or not existing_review.reviewer_id:
        flash('Bu makale için henüz hakem atanmamış.', 'warning')
        return redirect(url_for('dashboard'))
    
    if existing_review and existing_review.technical_quality is not None:
        flash('Bu makale için zaten değerlendirme yapılmış.', 'warning')
        return redirect(url_for('reviewer_dashboard'))
    
    if form.validate_on_submit():
        try:
            review = existing_review
            
            # Form verilerini kaydet
            review.technical_quality = int(form.technical_quality.data)
            review.methodology = int(form.methodology.data)
            review.contribution = int(form.contribution.data)
            review.presentation = int(form.presentation.data)
            review.comments = form.comments.data
            review.recommendation = form.recommendation.data
            review.confidential_comments = form.confidential_comments.data
            review.review_date = datetime.now()
            
            db.session.commit()
            flash('Değerlendirmeniz başarıyla kaydedildi.', 'success')
            return redirect(url_for('reviewer_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Değerlendirme kaydedilirken hata: {str(e)}")
            flash('Değerlendirme kaydedilirken bir hata oluştu.', 'danger')
    
    return render_template('review_paper.html', form=form, paper=paper)

def generate_tracking_number():
    return str(uuid.uuid4())[:8].upper()

@app.route('/submit_anonymous', methods=['GET', 'POST'])
def submit_anonymous():
    form = AnonymousPaperSubmissionForm()
    if form.validate_on_submit():
        if 'paper_file' not in request.files:
            flash('Dosya bulunamadı', 'error')
            return redirect(request.url)
        
        file = form.paper_file.data
        if file.filename == '':
            flash('Dosya seçilmedi', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            tracking_number = generate_tracking_number()
            
            # Benzersiz dosya adı oluştur
            unique_filename = f"{tracking_number}_{filename}"
            
            # Dosyayı kaydet
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            
            # Makaleyi veritabanına kaydet
            paper = Paper(
                title=form.title.data,
                authors=form.authors.data,
                file_path=os.path.join(app.config['UPLOAD_FOLDER'], unique_filename),
                tracking_number=tracking_number,
                submitter_email=form.email.data
            )
            db.session.add(paper)
            db.session.commit()
            
            flash(f'Makaleniz başarıyla yüklendi. Takip numaranız: {tracking_number}', 'success')
            return redirect(url_for('track_paper'))
            
    return render_template('submit_anonymous.html', form=form)

@app.route('/paper/<int:paper_id>')
def paper_detail(paper_id):
    try:
        paper = Paper.query.get_or_404(paper_id)
        # Hakemleri ve ilgi alanlarını yükle
        reviewers = User.query.filter_by(role='reviewer').options(joinedload(User.expertise_areas)).all()
        # Mevcut hakemi bul
        current_reviewer = None
        if paper.reviews:
            current_reviewer = paper.reviews[0].reviewer
        return render_template('paper_detail.html', paper=paper, reviewers=reviewers, current_reviewer=current_reviewer)
    except Exception as e:
        app.logger.error(f"Makale detayı yüklenirken hata: {str(e)}")
        flash('Makale detayları yüklenirken bir hata oluştu.', 'error')
        return redirect(url_for('index'))

@app.route('/paper/<int:paper_id>/update_status', methods=['POST'])
def update_paper_status(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    new_status = request.form.get('status')
    
    if new_status:
        paper.status = new_status
        db.session.commit()
        flash('Makale durumu güncellendi', 'success')
    
    return redirect(url_for('paper_detail', paper_id=paper_id))

@app.route('/paper/<int:paper_id>/remove_reviewer/<int:reviewer_id>', methods=['POST'])
def remove_reviewer(paper_id, reviewer_id):
    paper = Paper.query.get_or_404(paper_id)
    review = Review.query.filter_by(paper_id=paper_id, reviewer_id=reviewer_id).first()
    
    if review:
        if review.technical_quality is not None:  # Değerlendirme yapılmışsa
            flash('Değerlendirme yapmış bir hakem kaldırılamaz.', 'warning')
        else:
            db.session.delete(review)
            db.session.commit()
            flash('Hakem başarıyla kaldırıldı.', 'success')
    
    return redirect(url_for('paper_detail', paper_id=paper_id))

def determine_paper_categories(keywords, areas):
    """Makale anahtar kelimelerine göre ilgili alanları belirler"""
    matched_areas = []
    
    # keywords None veya boş ise boş liste döndür
    if not keywords:
        return matched_areas
        
    keywords_lower = [k.strip().lower() for k in keywords.split(',')]
    
    area_keywords = {
        'Yapay Zeka ve Makine Öğrenimi': ['yapay zeka', 'ai', 'machine learning', 'derin öğrenme', 'deep learning', 
                                         'nlp', 'doğal dil işleme', 'bilgisayarla görü', 'computer vision', 
                                         'generatif', 'generative'],
        'İnsan-Bilgisayar Etkileşimi': ['hci', 'insan bilgisayar', 'beyin bilgisayar', 'bci', 'kullanıcı deneyimi', 
                                       'ux', 'ar', 'vr', 'artırılmış gerçeklik', 'sanal gerçeklik'],
        'Büyük Veri ve Veri Analitiği': ['büyük veri', 'big data', 'veri madenciliği', 'data mining', 
                                        'veri görselleştirme', 'visualization', 'hadoop', 'spark', 
                                        'zaman serisi', 'time series'],
        'Siber Güvenlik': ['güvenlik', 'security', 'şifreleme', 'encryption', 'cryptography', 
                          'ağ güvenliği', 'network security', 'kimlik doğrulama', 'authentication'],
        'Ağ ve Dağıtık Sistemler': ['ağ', 'network', '5g', 'bulut', 'cloud', 'blockchain', 
                                   'p2p', 'dağıtık', 'distributed']
    }
    
    # Ana kategorileri eşleştir
    matched_main_categories = set()
    for keyword in keywords_lower:
        for main_cat, cat_keywords in area_keywords.items():
            if any(kw in keyword for kw in cat_keywords):
                matched_main_categories.add(main_cat)
    
    # Alt kategorileri bul
    for area in areas:
        if area.main_category in matched_main_categories:
            area_sub_lower = area.sub_category.lower()
            if any(keyword in area_sub_lower or area_sub_lower in keyword 
                  for keyword in keywords_lower):
                matched_areas.append(area)
    
    return matched_areas

def find_matching_reviewers(paper_categories):
    """Makale kategorilerine uygun hakemleri bulur"""
    matching_reviewers = set()
    
    for category in paper_categories:
        # Bu kategoride uzmanlığı olan hakemleri bul
        reviewers = User.query.filter(
            User.role == 'reviewer',
            User.expertise_areas.any(ExpertiseArea.id == category.id)
        ).all()
        
        matching_reviewers.update(reviewers)
    
    return list(matching_reviewers)

@app.route('/assign_reviewer/<int:paper_id>', methods=['GET', 'POST'])
def assign_reviewer(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    reviewers = User.query.filter_by(role='reviewer').all()

    if request.method == 'POST':
        reviewer_id = request.form.get('reviewer_id')
        if not reviewer_id:
            flash('Lütfen bir hakem seçin.', 'warning')
            return redirect(url_for('paper_detail', paper_id=paper_id))
        
        reviewer = User.query.get(reviewer_id)
        if not reviewer:
            flash('Seçilen hakem bulunamadı.', 'danger')
            return redirect(url_for('paper_detail', paper_id=paper_id))
            
        # Eğer makaleye zaten bir hakem atanmışsa, onu kaldır
        existing_review = Review.query.filter_by(paper_id=paper_id).first()
        if existing_review:
            db.session.delete(existing_review)
        
        # Yeni hakemi ata
        review = Review(paper=paper, reviewer=reviewer)
        db.session.add(review)
        
        # Makale durumunu güncelle
        paper.status = 'Değerlendirmede'
        
        try:
            db.session.commit()
            flash(f'Hakem {reviewer.first_name} {reviewer.last_name} başarıyla atandı.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Hakem atama hatası: {str(e)}")
            flash('Hakem atama sırasında bir hata oluştu.', 'danger')
        
        return redirect(url_for('paper_detail', paper_id=paper_id))

    return render_template('assign_reviewer.html', paper=paper, reviewers=reviewers)

@app.route('/paper/<int:paper_id>/download')
def download_paper(paper_id):
    """Makaleyi indirme route'u"""
    try:
        paper = Paper.query.get_or_404(paper_id)
        
        # Dosya yolunu belirle
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                # Editörler orijinal dosyayı indirebilir
                file_path = paper.original_file_path or paper.file_path
            elif current_user.role == 'reviewer':
                # Hakemler sadece kendilerine atanan makaleleri indirebilir
                review = Review.query.filter_by(paper_id=paper_id, reviewer_id=current_user.id).first()
                if not review:
                    flash('Bu makale size atanmamış.', 'error')
                    return redirect(url_for('paper_detail', paper_id=paper_id))
                # Hakemler anonimleştirilmiş dosyayı indirebilir
                file_path = paper.file_path
            else:
                # Diğer kullanıcılar anonimleştirilmiş dosyayı indirebilir
                file_path = paper.file_path
        else:
            # Giriş yapmamış kullanıcılar anonimleştirilmiş dosyayı indirebilir
            file_path = paper.file_path
        
        if not file_path or not os.path.exists(file_path):
            flash('Makale dosyası bulunamadı.', 'error')
            return redirect(url_for('paper_detail', paper_id=paper_id))
        
        # Dosya adını al
        filename = os.path.basename(file_path)
        
        # Dosyayı gönder
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Makale indirme hatası: {str(e)}")
        flash('Makale indirilirken bir hata oluştu.', 'error')
        return redirect(url_for('paper_detail', paper_id=paper_id))

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        tracking_number = request.form.get('tracking_number')
        email = request.form.get('email')
        message_text = request.form.get('message')
        
        if not all([tracking_number, email, message_text]):
            flash('Lütfen tüm alanları doldurun.', 'error')
            return redirect(url_for('track_paper'))
        
        # Makaleyi bul
        paper = Paper.query.filter_by(tracking_number=tracking_number).first()
        if not paper:
            flash('Makale bulunamadı.', 'error')
            return redirect(url_for('track_paper'))
        
        # E-posta adresini kontrol et
        if paper.submitter_email != email:
            flash('Bu e-posta adresi makalenin gönderenine ait değil.', 'error')
            return redirect(url_for('track_paper'))
        
        # Yeni mesaj oluştur
        new_message = Message(
            paper_id=paper.id,
            sender_email=email,
            content=message_text,
            is_from_author=True
        )
        
        # Mesajı kaydet
        db.session.add(new_message)
        db.session.commit()
        
        flash('Mesajınız başarıyla gönderildi.', 'success')
        return redirect(url_for('track_paper'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Mesaj gönderilirken bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('track_paper'))

@app.route('/messages')
def messages():
    try:
        # Tüm mesajları getir
        messages = Message.query.order_by(Message.date.desc()).all()
        
        # Okunmamış mesajları okundu olarak işaretle
        for message in messages:
            if not message.is_read:
                message.is_read = True
        db.session.commit()
        
        return render_template('messages.html', messages=messages)
        
    except Exception as e:
        app.logger.error(f"Mesajlar yüklenirken hata: {str(e)}")
        flash('Mesajlar yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/reviewer_dashboard')
def reviewer_dashboard():
    """Hakem listesi sayfası"""
    try:
        # Hakem rolüne sahip kullanıcıları ve uzmanlık alanlarını getir
        reviewers = User.query.filter_by(role='reviewer')\
            .options(joinedload(User.expertise_areas))\
            .all()
        
        return render_template('reviewer_dashboard.html', 
                             reviewers=reviewers,
                             reviewer=None)
                             
    except Exception as e:
        app.logger.error(f"Hakem listesi yüklenirken hata: {str(e)}")
        flash('Hakem listesi yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('index'))

@app.route('/reviewer_dashboard/<int:reviewer_id>')
def reviewer_dashboard_detail(reviewer_id):
    """Hakem paneli detay sayfası"""
    try:
        # Hakemi ve uzmanlık alanlarını getir
        reviewer = User.query.filter_by(id=reviewer_id, role='reviewer')\
            .options(joinedload(User.expertise_areas))\
            .first_or_404()
        
        # Hakeme atanan makaleleri getir
        assigned_papers = Paper.query.join(Review, Paper.id == Review.paper_id)\
            .filter(Review.reviewer_id == reviewer_id)\
            .order_by(Paper.submission_date.desc()).all()
        
        # Değerlendirme durumlarına göre makaleleri ayır
        pending_reviews = []
        completed_reviews = []
        
        for paper in assigned_papers:
            review = next((r for r in paper.reviews if r.reviewer_id == reviewer_id), None)
            if review and review.technical_quality is not None:
                completed_reviews.append(paper)
            else:
                pending_reviews.append(paper)
        
        # Tüm hakemleri getir
        reviewers = User.query.filter_by(role='reviewer')\
            .options(joinedload(User.expertise_areas))\
            .all()
        
        return render_template('reviewer_dashboard.html',
                             pending_reviews=pending_reviews,
                             completed_reviews=completed_reviews,
                             reviewer=reviewer,
                             reviewers=reviewers)
                             
    except Exception as e:
        app.logger.error(f"Hakem paneli yüklenirken hata: {str(e)}")
        flash('Hakem paneli yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('index'))

@app.route('/revise_paper/<tracking_number>', methods=['GET', 'POST'])
def revise_paper(tracking_number):
    paper = Paper.query.filter_by(tracking_number=tracking_number).first_or_404()
    form = PaperSubmissionForm()
    
    if form.validate_on_submit():
        try:
            file = form.paper_file.data
            if not file or not file.filename.lower().endswith('.pdf'):
                flash('Lütfen geçerli bir PDF dosyası seçin.', 'danger')
                return redirect(request.url)
            
            # Yeni dosya adı oluştur
            filename = secure_filename(file.filename)
            unique_filename = f"{paper.tracking_number}_revised_{filename}"
            
            # Dosyayı kaydet
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Makaleyi güncelle
            paper.title = form.title.data
            paper.authors = form.authors.data
            paper.submitter_email = form.email.data
            paper.institution = form.institution.data
            paper.file_path = unique_filename
            paper.status = 'Revizyon Beklemede'
            paper.revision_date = datetime.utcnow()
            
            db.session.commit()
            
            flash('Revize edilmiş makaleniz başarıyla yüklendi.', 'success')
            return redirect(url_for('track_paper', tracking_number=paper.tracking_number))
            
        except Exception as e:
            app.logger.error(f"Paper revision error: {str(e)}")
            flash('Makale yüklenirken bir hata oluştu.', 'danger')
    
    # Form alanlarını mevcut makale bilgileriyle doldur
    form.title.data = paper.title
    form.authors.data = paper.authors
    form.email.data = paper.submitter_email
    form.institution.data = paper.institution
    
    return render_template('revise_paper.html', form=form, paper=paper)

@app.route('/paper/<int:paper_id>/download_original')
@login_required
def download_original_paper(paper_id):
    """Orijinal makaleyi indirme route'u"""
    try:
        paper = Paper.query.get_or_404(paper_id)
        
        # Sadece admin kullanıcılar orijinal makaleyi indirebilir
        if current_user.role != 'admin':
            flash('Bu işlem için yetkiniz yok.', 'danger')
            return redirect(url_for('paper_detail', paper_id=paper_id))
        
        # Orijinal dosya yolunu kontrol et
        if not paper.original_file_path or not os.path.exists(paper.original_file_path):
            flash('Orijinal makale dosyası bulunamadı.', 'error')
            return redirect(url_for('paper_detail', paper_id=paper_id))
        
        # Dosya adını al
        filename = os.path.basename(paper.original_file_path)
        
        # Orijinal dosyayı gönder
        return send_file(
            paper.original_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error(f"Orijinal makale indirme hatası: {str(e)}")
        flash('Makale indirilirken bir hata oluştu.', 'danger')
        return redirect(url_for('paper_detail', paper_id=paper_id))

@app.route('/paper/<int:paper_id>/anonymize', methods=['POST'])
@login_required
def anonymize_paper(paper_id):
    """Makaleyi anonimleştirme route'u"""
    try:
        paper = Paper.query.get_or_404(paper_id)
        
        # Sadece admin kullanıcılar makaleyi anonimleştirebilir
        if current_user.role != 'admin':
            flash('Bu işlem için yetkiniz yok.', 'danger')
            return redirect(url_for('paper_detail', paper_id=paper_id))
        
        # Makaleyi anonimleştir
        anonymized_file_path = paper_anonymizer.process_paper(paper.file_path)
        
        if anonymized_file_path:
            # Orijinal dosyayı sakla
            original_file_path = paper.file_path
            paper.original_file_path = original_file_path
            
            # Anonimleştirilmiş dosyayı ana dosya olarak ayarla
            paper.file_path = anonymized_file_path
            paper.last_update = datetime.utcnow()
            db.session.commit()
            
            flash('Makale başarıyla anonimleştirildi.', 'success')
        else:
            flash('Makale anonimleştirilirken bir hata oluştu.', 'danger')
        
        return redirect(url_for('paper_detail', paper_id=paper_id))
        
    except Exception as e:
        app.logger.error(f"Makale anonimleştirme hatası: {str(e)}")
        flash('Makale anonimleştirilirken bir hata oluştu.', 'danger')
        return redirect(url_for('paper_detail', paper_id=paper_id))

if __name__ == '__main__':
    try:
        with app.app_context():
            db.create_all()
            # Varsayılan admin kullanıcısını oluştur
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    role='admin',
                    institution='System'
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
            logger.info("Veritabanı tabloları oluşturuldu")
        logger.info("Flask uygulaması başlatılıyor...")
        app.run(debug=True, use_reloader=True)
    except Exception as e:
        logger.error(f"Uygulama başlatılırken hata oluştu: {str(e)}") 