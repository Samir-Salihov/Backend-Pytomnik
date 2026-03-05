"""
Тесты для функционала массовой загрузки фотографий.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io
import zipfile

from .models import Student
from .photo_uploader import (
    normalize_name,
    extract_full_name_from_filename,
    process_photo_uploads,
    extract_photo_files_from_archive,
)


User = get_user_model()


class PhotoUploaderUtilsTest(TestCase):
    """Тесты для утилит обработки имён."""
    
    def test_normalize_name_basic(self):
        """Тест нормализации ФИО."""
        self.assertEqual(normalize_name('Иван Иванов'), 'иванивоов')
        self.assertEqual(normalize_name('  иван   иванов  '), 'иванивоов')
    
    def test_normalize_name_empty(self):
        """Тест нормализации пустого имени."""
        self.assertEqual(normalize_name(''), '')
        self.assertEqual(normalize_name(None), '')
    
    def test_extract_full_name_from_filename(self):
        """Тест извлечения имени из названия файла."""
        self.assertEqual(
            extract_full_name_from_filename('Иван Иванов Иванович.jpg'),
            'Иван Иванов Иванович'
        )
        self.assertEqual(
            extract_full_name_from_filename('  filename  .PNG'),
            'filename'
        )


class PhotoUploadProcessTest(TestCase):
    """Тесты для обработки загрузки фотографий."""
    
    def setUp(self):
        """Создаём test студентов."""
        self.student1 = Student.objects.create(
            first_name='Иван',
            last_name='Иванов',
            birth_date='2000-01-01',
            level='black',
            status='active',
            category='college',
            direction='asutp',
            subdivision='hr',
            address_actual='ул. Тестовая',
            address_registered='ул. Тестовая',
            phone_personal='70000000001',
            phone_parent='70000000002',
            fio_parent='Родитель'
        )
        
        self.student2 = Student.objects.create(
            first_name='Петр',
            last_name='Петров',
            birth_date='2001-01-01',
            level='red',
            status='active',
            category='college',
            direction='bim',
            subdivision='digital',
            address_actual='ул. Тестовая',
            address_registered='ул. Тестовая',
            phone_personal='70000000003',
            phone_parent='70000000004',
            fio_parent='Родитель'
        )
    
    def _create_test_image(self, filename='test.jpg'):
        """Создаёт тестовое изображение."""
        img = Image.new('RGB', (100, 100), color='red')
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return SimpleUploadedFile(filename, img_io.getvalue(), content_type='image/jpeg')

    def _create_test_image_bytes(self, color='red'):
        img = Image.new('RGB', (100, 100), color=color)
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return img_io.getvalue()

    def _create_test_zip(self, filename='photos.zip', members=None):
        if members is None:
            members = {}

        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
            for member_name, member_content in members.items():
                archive.writestr(member_name, member_content)

        zip_io.seek(0)
        return SimpleUploadedFile(filename, zip_io.read(), content_type='application/zip')
    
    def test_process_photo_uploads_matched(self):
        """Тест успешной загрузки фото с совпадением ФИО."""
        file = self._create_test_image('Иван Иванов.jpg')
        results = process_photo_uploads([file])
        
        self.assertEqual(len(results['matched']), 1)
        self.assertEqual(len(results['unmatched']), 0)
        self.assertEqual(len(results['errors']), 0)
        
        # Проверяем что фото было загружено
        self.student1.refresh_from_db()
        self.assertTrue(self.student1.photo.name)
    
    def test_process_photo_uploads_unmatched(self):
        """Тест обработки фото не найденного студента."""
        file = self._create_test_image('Неизвестный Студент.jpg')
        results = process_photo_uploads([file])
        
        self.assertEqual(len(results['matched']), 0)
        self.assertEqual(len(results['unmatched']), 1)
        self.assertEqual(len(results['errors']), 0)
    
    def test_process_photo_uploads_multiple(self):
        """Тест загрузки нескольких фотографий."""
        files = [
            self._create_test_image('Иван Иванов.jpg'),
            self._create_test_image('Петр Петров.jpg'),
            self._create_test_image('Неизвестный.jpg')
        ]
        
        results = process_photo_uploads(files)
        
        self.assertEqual(len(results['matched']), 2)
        self.assertEqual(len(results['unmatched']), 1)
        self.assertEqual(len(results['errors']), 0)

    def test_extract_photo_files_from_archive(self):
        """Тест извлечения фото из ZIP-архива папки."""
        archive = self._create_test_zip(
            members={
                'cats/Иван Иванов.jpg': self._create_test_image_bytes('red'),
                'cats/Петр Петров.jpg': self._create_test_image_bytes('blue'),
                'cats/readme.txt': b'ignore me',
            }
        )

        extracted_files = extract_photo_files_from_archive(archive)
        self.assertEqual(len(extracted_files), 2)

        results = process_photo_uploads(extracted_files)
        self.assertEqual(len(results['matched']), 2)
        self.assertEqual(len(results['unmatched']), 0)
        self.assertEqual(len(results['errors']), 0)

    def test_process_photo_uploads_reports_overwrite(self):
        """Тест отчёта о перезаписи фото у одного и того же студента."""
        files = [
            self._create_test_image('Иван Иванов.jpg'),
            self._create_test_image('Иван-Иванов.jpeg'),
        ]

        results = process_photo_uploads(files)

        self.assertEqual(len(results['matched']), 2)
        self.assertEqual(len(results['overwritten']), 1)
        overwrite = results['overwritten'][0]
        self.assertEqual(overwrite['full_name'], self.student1.full_name)
        self.assertEqual(overwrite['previous_filename'], 'Иван Иванов.jpg')
        self.assertEqual(overwrite['filename'], 'Иван-Иванов.jpeg')


class PhotoUploadAdminViewTest(TestCase):
    """Тесты для админ-view загрузки фотографий."""
    
    def setUp(self):
        """Создаём test пользователя и студента."""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        
        self.student = Student.objects.create(
            first_name='Иван',
            last_name='Иванов',
            birth_date='2000-01-01',
            level='black',
            status='active',
            category='college',
            direction='asutp',
            subdivision='hr',
            address_actual='ул. Тестовая',
            address_registered='ул. Тестовая',
            phone_personal='70000000001',
            phone_parent='70000000002',
            fio_parent='Родитель'
        )
        
        self.client = Client()
    
    def _create_test_image(self, filename='test.jpg'):
        """Создаёт тестовое изображение."""
        img = Image.new('RGB', (100, 100), color='blue')
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return SimpleUploadedFile(filename, img_io.getvalue(), content_type='image/jpeg')

    def _create_test_image_bytes(self, color='blue'):
        img = Image.new('RGB', (100, 100), color=color)
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        return img_io.getvalue()

    def _create_test_zip(self, filename='photos.zip', members=None):
        if members is None:
            members = {}

        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as archive:
            for member_name, member_content in members.items():
                archive.writestr(member_name, member_content)

        zip_io.seek(0)
        return SimpleUploadedFile(filename, zip_io.read(), content_type='application/zip')
    
    def test_view_get_requires_auth(self):
        """Тест что GET требует аутентификации."""
        response = self.client.get('/admin/students/bulk-photo-upload/')
        self.assertIn(response.status_code, [302, 403])  # Redirect або Forbidden
    
    def test_view_get_authenticated(self):
        """Тест что GET работает для аутентифицированного пользователя."""
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/students/bulk-photo-upload/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Загрузка фотографий', response.content.decode('utf-8'))
    
    def test_view_post_authenticated(self):
        """Тест POST запроса с загрузкой фото."""
        self.client.force_login(self.admin_user)
        
        file = self._create_test_image('Иван Иванов.jpg')
        response = self.client.post(
            '/admin/students/bulk-photo-upload/',
            {'photos': [file]},
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['matched'], 1)

    def test_view_post_archive_authenticated(self):
        """Тест POST запроса с ZIP-архивом фотографий."""
        self.client.force_login(self.admin_user)

        archive = self._create_test_zip(
            members={
                'folder/Иван Иванов.jpg': self._create_test_image_bytes('green')
            }
        )

        response = self.client.post(
            '/admin/students/bulk-photo-upload/',
            {'photos_archive': archive},
            content_type='multipart/form-data'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['matched'], 1)

    def test_view_post_reports_overwrite(self):
        """Тест что API возвращает информацию о перезаписи фото."""
        self.client.force_login(self.admin_user)

        file1 = self._create_test_image('Иван Иванов.jpg')
        file2 = self._create_test_image('Иван-Иванов.jpeg')

        response = self.client.post(
            '/admin/students/bulk-photo-upload/',
            {'photos': [file1, file2]},
            content_type='multipart/form-data'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['overwritten'], 1)
        self.assertEqual(len(data['results']['overwritten']), 1)
