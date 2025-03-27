import fitz  # PyMuPDF
import re
import os
from PIL import Image
import io
import logging
import traceback

class PaperAnonymizer:
    def __init__(self, upload_folder, anonymized_folder):
        self.upload_folder = upload_folder
        self.anonymized_folder = anonymized_folder
        self.logger = logging.getLogger(__name__)
        
        # Dizinlerin varlığını kontrol et ve oluştur
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(anonymized_folder, exist_ok=True)

    def analyze_paper_content(self, file_path):
        """
        PDF dosyasından yazar bilgilerini tespit eder
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Dosya bulunamadı: {file_path}")
                return None
                
            doc = fitz.open(file_path)
            text = ""
            
            # Tüm sayfaların metnini al
            for page in doc:
                text += page.get_text()
            
            # Yazar bilgilerini tespit et
            author_info = {
                'names': [],
                'emails': [],
                'institutions': [],
                'images': []
            }
            
            # E-posta adreslerini bul
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text)
            author_info['emails'] = list(set(emails))
            
            # Kurum bilgilerini bul
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
            
            # Yazar isimlerini bul
            name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            names = re.findall(name_pattern, text)
            author_info['names'] = list(set(names))
            
            # Görüntüleri bul
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                for img in image_list:
                    author_info['images'].append({
                        'page': page_num,
                        'bbox': page.get_image_bbox(img)
                    })
            
            doc.close()
            return author_info
            
        except Exception as e:
            self.logger.error(f"Makale analizi hatası: {str(e)}")
            self.logger.error(f"Hata detayı: {traceback.format_exc()}")
            return None

    def blur_image(self, image_data, blur_radius=20):
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
            self.logger.error(f"Görüntü bulanıklaştırma hatası: {str(e)}")
            return image_data

    def anonymize_paper_content(self, file_path, author_info):
        """
        Makale içeriğini anonimleştirir
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Dosya bulunamadı: {file_path}")
                return None
                
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
                
                # Bölümleri ayır
                sections = text.split('\n\n')
                anonymized_sections = []
                
                for section in sections:
                    section_lower = section.lower()
                    # Bu bölümlerde anonimleştirme yapma
                    if any(keyword in section_lower for keyword in ['giriş', 'ilgili çalışmalar', 'referanslar', 'teşekkür']):
                        anonymized_sections.append(section)
                    else:
                        # Diğer bölümlerde anonimleştirme yap
                        anonymized_section = section
                        
                        # Yazar isimlerini değiştir
                        for name, ref in author_refs.items():
                            anonymized_section = re.sub(r'\b' + re.escape(name) + r'\b', ref, anonymized_section)
                        
                        # E-posta adreslerini değiştir
                        for email in author_info['emails']:
                            anonymized_section = re.sub(r'\b' + re.escape(email) + r'\b', 'author@example.com', anonymized_section)
                        
                        # Kurum bilgilerini değiştir (sadece yazar bilgileri bölümünde)
                        if 'yazar' in section_lower or 'author' in section_lower:
                            for institution in author_info['institutions']:
                                anonymized_section = re.sub(r'\b' + re.escape(institution) + r'\b', 'Institution', anonymized_section)
                        
                        anonymized_sections.append(anonymized_section)
                
                # Sayfayı güncelle
                new_page.insert_text((0, 0), '\n\n'.join(anonymized_sections))
                
                # Görüntüleri bulanıklaştır
                for img_info in author_info['images']:
                    if img_info['page'] == page_num:
                        img = page.get_images()[0]
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Görüntüyü bulanıklaştır
                        blurred_image = self.blur_image(image_bytes)
                        
                        # Bulanıklaştırılmış görüntüyü sayfaya ekle
                        new_page.insert_image(
                            rect=img_info['bbox'],
                            stream=blurred_image,
                            filename=f"blurred_image_{page_num}.png"
                        )
            
            # Anonimleştirilmiş dosyayı kaydet
            anonymized_path = os.path.join(self.anonymized_folder, os.path.basename(file_path))
            os.makedirs(self.anonymized_folder, exist_ok=True)
            
            output_doc.save(anonymized_path)
            output_doc.close()
            doc.close()
            
            if not os.path.exists(anonymized_path):
                self.logger.error(f"Anonimleştirilmiş dosya oluşturulamadı: {anonymized_path}")
                return None
                
            return anonymized_path
            
        except Exception as e:
            self.logger.error(f"Anonimleştirme hatası: {str(e)}")
            self.logger.error(f"Hata detayı: {traceback.format_exc()}")
            return None

    def process_paper(self, file_path):
        """Makaleyi anonimleştirir"""
        try:
            # Dosya varlığını kontrol et
            if not os.path.exists(file_path):
                self.logger.error(f"Dosya bulunamadı: {file_path}")
                return None

            # Dosya adını ve uzantısını ayır
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            # Anonimleştirilmiş dosya adını oluştur
            anonymized_filename = f"{name}_anonymized{ext}"
            anonymized_path = os.path.join(self.anonymized_folder, anonymized_filename)
            
            # Anonimleştirme klasörünün varlığını kontrol et
            if not os.path.exists(self.anonymized_folder):
                os.makedirs(self.anonymized_folder)
            
            # PDF dosyasını aç
            doc = fitz.open(file_path)
            output_doc = fitz.open()
            
            # Her sayfayı işle
            for page_num in range(len(doc)):
                page = doc[page_num]
                new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # Önce görüntüleri işle
                image_list = page.get_images()
                for img in image_list:
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            # Görüntüyü bulanıklaştır
                            blurred_image = self.blur_image(image_bytes)
                            if blurred_image:
                                # Bulanıklaştırılmış görüntüyü sayfaya ekle
                                new_page.insert_image(
                                    rect=page.get_image_bbox(img),
                                    stream=blurred_image,
                                    filename=f"blurred_image_{page_num}.png"
                                )
                    except Exception as e:
                        self.logger.error(f"Görüntü işleme hatası (sayfa {page_num}): {str(e)}")
                        continue
                
                # Sonra metni işle
                try:
                    text = page.get_text()
                    # Bölümleri ayır
                    sections = text.split('\n\n')
                    anonymized_sections = []
                    
                    for section in sections:
                        section_lower = section.lower()
                        # Bu bölümlerde anonimleştirme yapma
                        if any(keyword in section_lower for keyword in ['giriş', 'ilgili çalışmalar', 'referanslar', 'teşekkür']):
                            anonymized_sections.append(section)
                        else:
                            # Diğer bölümlerde anonimleştirme yap
                            anonymized_section = section
                            anonymized_section = self.replace_author_info(anonymized_section)
                            anonymized_sections.append(anonymized_section)
                    
                    # Sayfayı güncelle
                    new_page.insert_text((0, 0), '\n\n'.join(anonymized_sections))
                except Exception as e:
                    self.logger.error(f"Metin işleme hatası (sayfa {page_num}): {str(e)}")
                    continue
            
            # Anonimleştirilmiş dosyayı kaydet
            try:
                output_doc.save(anonymized_path)
                output_doc.close()
                doc.close()
                
                # Dosyanın başarıyla oluşturulduğunu kontrol et
                if not os.path.exists(anonymized_path):
                    self.logger.error(f"Anonimleştirilmiş dosya oluşturulamadı: {anonymized_path}")
                    return None
                
                self.logger.info(f"Makale başarıyla anonimleştirildi: {anonymized_path}")
                return anonymized_path
                
            except Exception as e:
                self.logger.error(f"Dosya kaydetme hatası: {str(e)}")
                return None
            
        except Exception as e:
            self.logger.error(f"Makale anonimleştirme hatası: {str(e)}")
            self.logger.error(f"Hata detayı: {traceback.format_exc()}")
            return None

    def replace_author_info(self, text):
        """Metindeki yazar bilgilerini değiştirir"""
        try:
            # E-posta adreslerini değiştir
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            text = re.sub(email_pattern, '*****', text)
            
            # Kurum bilgilerini değiştir
            institution_patterns = [
                r'Department of [^,]+',
                r'Faculty of [^,]+',
                r'University of [^,]+',
                r'Institute of [^,]+',
                r'[A-Z][a-z]+ University',
                r'[A-Z][a-z]+ Institute'
            ]
            
            for pattern in institution_patterns:
                text = re.sub(pattern, '*****', text)
            
            # Yazar isimlerini değiştir
            name_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
            names = re.findall(name_pattern, text)
            
            for i, name in enumerate(names, 1):
                text = re.sub(r'\b' + re.escape(name) + r'\b', f'Author_{i}', text)
            
            # Diğer hassas bilgileri değiştir
            sensitive_patterns = [
                r'\b\d{4}\b',  # Yıllar
                r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # Tarihler
                r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',  # Tarihler
                r'\b\d{1,2}-\d{1,2}-\d{4}\b',  # Tarihler
                r'\b\d{3}-\d{3}-\d{4}\b',  # Telefon numaraları
                r'\b\d{10}\b',  # 10 haneli numaralar
                r'\b[A-Z]{2,}\d{2,}\b',  # Kodlar
            ]
            
            for pattern in sensitive_patterns:
                text = re.sub(pattern, '*****', text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"Yazar bilgileri değiştirme hatası: {str(e)}")
            return text 