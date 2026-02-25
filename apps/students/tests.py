from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from utils import student_utils
from apps.students.models import (
    KVAZAR_RANK_CHOICES, CATEGORY_CHOICES, LEVEL_CHOICES, STATUS_CHOICES
)
from apps.students.serializers import (
    StudentCreateSerializer, StudentUpdateSerializer, StudentDetailSerializer
)
from apps.students.models import Student


class ChoiceMappingTests(TestCase):
    def test_map_choice_value_key(self):
        self.assertEqual(
            student_utils.map_choice_value('asutp', student_utils.DIRECTION_CHOICES),
            'asutp'
        )

    def test_map_choice_value_label(self):
        self.assertEqual(
            student_utils.map_choice_value('Промышленная автоматика', student_utils.DIRECTION_CHOICES),
            'asutp'
        )

    def test_map_choice_value_case_and_spaces(self):
        self.assertEqual(
            student_utils.map_choice_value(' промышленная автоматика ', student_utils.DIRECTION_CHOICES),
            'asutp'
        )

    def test_map_choice_value_unknown(self):
        self.assertIsNone(
            student_utils.map_choice_value('суперсекретный', student_utils.DIRECTION_CHOICES)
        )


class SerializerChoiceInputTests(TestCase):
    def setUp(self):
        # minimal data used for student creation
        self.base_data = {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'birth_date': '2000-01-01',
            'phone_personal': '71234567890',
            'level': 'black',
            'status': 'active',
            'category': 'college',
            'direction': 'asutp',
            'subdivision': 'hr',
            'address_actual': 'улица Пушкина, дом 1',
            'address_registered': 'ул. Ленина, д.2',
            'phone_parent': '79876543210',
            'fio_parent': 'Петров П.П.',
        }

    def test_create_with_labels(self):
        data = self.base_data.copy()
        # put labels instead of internal codes
        data.update(
            {
                'direction': 'Промышленная автоматика',
                'subdivision': 'Управление HR',
                'category': 'Колледжисты',
                'level': 'Чёрный',
                'status': 'Активные',
                'kvazar_rank': 'Сержант',
            }
        )
        serializer = StudentCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        student = serializer.save()
        self.assertEqual(student.direction, 'asutp')
        self.assertEqual(student.subdivision, 'hr')
        self.assertEqual(student.category, 'college')
        self.assertEqual(student.level, 'black')
        self.assertEqual(student.status, 'active')
        self.assertEqual(student.kvazar_rank, 'sergeant')

    def test_detail_serializer_includes_kvazar_display(self):
        # ensure the explicitly-declared read-only field is included
        from datetime import date
        s = Student.objects.create(
            first_name='X', last_name='Y', birth_date=date(2000, 1, 1),
            phone_personal='70000000000', level='black', status='active',
            category='college', direction='asutp', subdivision='hr',
            address_actual='a', address_registered='b',
            phone_parent='71111111111', fio_parent='P',
            kvazar_rank='sergeant',
        )
        ser = StudentDetailSerializer(s)
        self.assertIn('kvazar_rank_display', ser.data)
        # display value should match human label
        self.assertEqual(ser.data['kvazar_rank_display'], 'Сержант')

    def test_update_with_labels(self):
        student = Student.objects.create(
            **{
                **self.base_data,
                'created_by': None,
                'updated_by': None,
            }
        )
        update_data = {'direction': 'Промышленная автоматика', 'level': 'Красный'}
        serializer = StudentUpdateSerializer(student, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.direction, 'asutp')
        self.assertEqual(updated.level, 'red')

    def test_photo_field_unrestricted(self):
        # ensure serializer does not enforce size/extension constraints
        from django.core.files.uploadedfile import SimpleUploadedFile

        data = self.base_data.copy()
        # choose a long but reasonable filename (<=255 bytes)
        long_name = 'a' * 200 + '.png'
        # build a tiny 1×1 PNG using Pillow so it is definitely valid
        from PIL import Image
        import io
        img_io = io.BytesIO()
        Image.new('RGB', (1, 1), color='white').save(img_io, format='PNG')
        img_io.seek(0)
        dummy = SimpleUploadedFile(long_name, img_io.read(), content_type='image/png')
        data['photo'] = dummy
        serializer = StudentCreateSerializer(data=data)
        # it should be valid even though the file is large and name is long
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        student = serializer.save()
        # name may be truncated or modified by storage backend, but
        # photo field should be populated nonetheless
        self.assertTrue(student.photo.name)

    def test_medical_file_unrestricted(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.students.serializers import MedicalFileCreateSerializer
        from apps.students.models import MedicalFile

        # create student to attach file to
        student = Student.objects.create(
            **{
                **self.base_data,
                'created_by': None,
                'updated_by': None,
            }
        )
        # generate small valid image as before
        from PIL import Image
        import io
        img_io = io.BytesIO()
        Image.new('RGB', (1, 1), color='white').save(img_io, format='PNG')
        img_io.seek(0)
        file = SimpleUploadedFile('x' * 200 + '.png', img_io.read(), content_type='image/png')
        serializer = MedicalFileCreateSerializer(data={'file': file, 'description': 'test'}, context={'request': None, 'student': student})
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        med = serializer.save()
        self.assertTrue(med.file.name)

    def test_client_upload_does_not_crash(self):
        """Using the test client exercises Django's multipart parser.

        Previously we set FILE_UPLOAD_MAX_MEMORY_SIZE = None which raised a
        TypeError during request parsing.  This test posts a small file and
        ensures the framework doesn't return a 500 status.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile
        import sys

        # sanity check on settings type
        self.assertIsInstance(settings.FILE_UPLOAD_MAX_MEMORY_SIZE, int)
        self.assertIsInstance(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, int)

        user = get_user_model().objects.create_user(username='tester', password='pass')
        self.client.force_login(user)
        student = Student.objects.create(
            **{**self.base_data, 'created_by': None, 'updated_by': None}
        )
        big_file = SimpleUploadedFile('big.bin', b'a' * (1024 * 1024 * 3))
        url = reverse('medical-file-create', args=[student.pk])
        response = self.client.post(url, {'file': big_file, 'description': 'ok'})
        # should not crash; anything except server error is acceptable
        self.assertNotEqual(response.status_code, 500)


class AdminImportTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='admin', password='pass', email='a@b.com')
        self.admin.role = 'admin'
        self.admin.save()
        self.client.force_login(self.admin)

    def _make_excel(self, rows):
        import pandas as pd
        from io import BytesIO

        df = pd.DataFrame(rows)
        buf = BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        return buf

    def test_import_creates_new_and_updates_existing(self):
        """Uploading a sheet should upsert based on full name."""
        # start with a file containing two students with same name but different categories
        buf1 = self._make_excel([
            {'ФИО': 'Иванов Иван', 'Категория': 'Колледжисты', 'Личный телефон': '33'},
            {'ФИО': 'Иванов Иван', 'Категория': 'Патриоты', 'Личный телефон': '77'},
        ])
        from django.core.files.uploadedfile import SimpleUploadedFile
        upload1 = SimpleUploadedFile('first.xlsx', buf1.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        url = reverse('admin:students_import_excel')
        resp = self.client.post(url, {'excel_file': upload1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Student.objects.count(), 2)
        college = Student.objects.get(last_name='Иванов', first_name='Иван', category='college')
        patriot = Student.objects.get(last_name='Иванов', first_name='Иван', category='patriot')
        self.assertEqual(college.phone_personal, '33')
        self.assertEqual(patriot.phone_personal, '77')

        # import a new sheet updating only the college entry and adding a new person
        buf2 = self._make_excel([
            {'ФИО': 'Иванов Иван', 'Категория': 'Колледжисты', 'Личный телефон': '4444'},
            {'ФИО': 'Сергеев Сергей', 'Категория': 'Колледжисты', 'Личный телефон': '5555'},
        ])
        upload2 = SimpleUploadedFile('second.xlsx', buf2.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp2 = self.client.post(url, {'excel_file': upload2})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(Student.objects.count(), 3)
        college.refresh_from_db()
        patriot.refresh_from_db()
        self.assertEqual(college.phone_personal, '4444')
        # патриот не должен был измениться
        self.assertEqual(patriot.phone_personal, '77')
        sergey = Student.objects.get(last_name='Сергеев', first_name='Сергей')
        self.assertEqual(sergey.phone_personal, '5555')


class AdminDeleteAllTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='admin', password='pass', email='a@b.com')
        self.admin.role = 'admin'
        self.admin.save()
        self.client.force_login(self.admin)

    def test_delete_all_students(self):
        # create a couple of students
        Student.objects.create(first_name='A', last_name='B', category='college', status='active')
        Student.objects.create(first_name='C', last_name='D', category='college', status='active')
        self.assertEqual(Student.objects.count(), 2)
        url = reverse('admin:students_delete_all')
        # POST should remove all and redirect to changelist
        response = self.client.post(url, {})
        self.assertRedirects(response, reverse('admin:students_student_changelist'))
        self.assertEqual(Student.objects.count(), 0)

    def test_changelist_contains_modal_markup(self):
        # ensure the JS-driven modal exists and buttons have correct attributes
        change_url = reverse('admin:students_student_changelist')
        response = self.client.get(change_url)
        self.assertContains(response, 'id="delete-modal"')
        self.assertContains(response, 'id="delete-all-btn"')
        # confirm and cancel buttons should be present with proper types and classes
        self.assertContains(response, 'id="confirm-delete"')
        self.assertContains(response, 'class="action-btn import-btn confirm-btn"')
        self.assertContains(response, 'type="button"')
        self.assertContains(response, 'id="cancel-delete"')
        self.assertContains(response, 'class="action-btn cancel-btn"')
        # overlay click handler comment should be in script (regression check)
        self.assertContains(response, 'overlay clicked - blast')
