from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, FileField, IntegerField, BooleanField, EmailField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, ValidationError, Email
from flask_wtf.file import FileAllowed
import os

class LoginForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    remember_me = BooleanField('Beni Hatırla')
    submit = SubmitField('Giriş Yap')

class RegisterForm(FlaskForm):
    first_name = StringField('Ad', validators=[DataRequired()])
    last_name = StringField('Soyad', validators=[DataRequired()])
    email = StringField('E-posta', validators=[DataRequired(), Email()])
    password = PasswordField('Şifre', validators=[DataRequired()])
    password2 = PasswordField('Şifre Tekrar', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Kayıt Ol')

class PaperSubmissionForm(FlaskForm):
    title = StringField('Makale Başlığı', validators=[DataRequired(), Length(min=5, max=200)])
    authors = StringField('Yazarlar', validators=[DataRequired(), Length(min=5, max=500)])
    email = EmailField('E-posta Adresi', validators=[DataRequired(), Email()])
    institution = StringField('Kurum', validators=[DataRequired(), Length(min=5, max=200)])
    paper_file = FileField('PDF Dosyası', validators=[DataRequired(), FileAllowed(['pdf'], 'Sadece PDF dosyaları yüklenebilir!')])
    submit = SubmitField('Makaleyi Gönder')

    def validate_paper_file(self, field):
        if not field.data:
            raise ValidationError('Lütfen bir dosya seçin.')
        filename = field.data.filename
        if not filename.lower().endswith('.pdf'):
            raise ValidationError('Sadece PDF dosyaları kabul edilmektedir.')

class ReviewForm(FlaskForm):
    technical_quality = SelectField('Teknik Kalite', choices=[
        ('1', '1 - Çok Zayıf'),
        ('2', '2 - Zayıf'),
        ('3', '3 - Orta'),
        ('4', '4 - İyi'),
        ('5', '5 - Çok İyi')
    ], validators=[DataRequired()])
    
    methodology = SelectField('Metodoloji', choices=[
        ('1', '1 - Çok Zayıf'),
        ('2', '2 - Zayıf'),
        ('3', '3 - Orta'),
        ('4', '4 - İyi'),
        ('5', '5 - Çok İyi')
    ], validators=[DataRequired()])
    
    contribution = SelectField('Katkı', choices=[
        ('1', '1 - Çok Zayıf'),
        ('2', '2 - Zayıf'),
        ('3', '3 - Orta'),
        ('4', '4 - İyi'),
        ('5', '5 - Çok İyi')
    ], validators=[DataRequired()])
    
    presentation = SelectField('Sunum', choices=[
        ('1', '1 - Çok Zayıf'),
        ('2', '2 - Zayıf'),
        ('3', '3 - Orta'),
        ('4', '4 - İyi'),
        ('5', '5 - Çok İyi')
    ], validators=[DataRequired()])
    
    recommendation = SelectField('Öneri', choices=[
        ('Kabul', 'Kabul'),
        ('Küçük Düzeltmelerle Kabul', 'Küçük Düzeltmelerle Kabul'),
        ('Büyük Düzeltmelerle Kabul', 'Büyük Düzeltmelerle Kabul'),
        ('Red', 'Red')
    ], validators=[DataRequired()])
    
    comments = TextAreaField('Genel Değerlendirme', validators=[DataRequired()])
    confidential_comments = TextAreaField('Editöre Özel Notlar')
    submit = SubmitField('Değerlendirmeyi Kaydet')

class TrackPaperForm(FlaskForm):
    tracking_id = StringField('Takip Numarası', validators=[DataRequired()])
    email = StringField('E-posta', validators=[DataRequired()])
    submit = SubmitField('Sorgula')

class AnonymousPaperSubmissionForm(FlaskForm):
    title = StringField('Makale Başlığı', validators=[DataRequired()])
    authors = StringField('Yazarlar', validators=[DataRequired()])
    email = StringField('E-posta', validators=[DataRequired()])
    paper_file = FileField('PDF Dosyası', validators=[DataRequired(), FileAllowed(['pdf'], 'Sadece PDF dosyaları yüklenebilir!')])
    submit = SubmitField('Makale Gönder')

    def validate_paper_file(self, field):
        if not field.data:
            raise ValidationError('Lütfen bir dosya seçin.')
        filename = field.data.filename
        if not filename.lower().endswith('.pdf'):
            raise ValidationError('Sadece PDF dosyaları kabul edilmektedir.')

class MessageForm(FlaskForm):
    email = EmailField('E-posta Adresi', validators=[DataRequired(), Email()])
    tracking_number = StringField('Takip Numarası', validators=[DataRequired()])
    message = TextAreaField('Mesajınız', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Mesaj Gönder') 