from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.students.models import Student, LevelByMonth
from apps.export.services import generate_excel_stream
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class ExportIntegrationTests(TestCase):
    def setUp(self):
        # create superuser to bypass permissions
        self.user = User.objects.create_superuser(username='admin', password='pass123', email='admin@example.com')
        # assign explicit admin role in addition to superuser flag to satisfy permission class
        self.user.role = 'admin'
        self.user.save()
        self.client = APIClient()
        # issue a JWT and attach to client
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_export_endpoint_filename_and_format(self):
        # directly exercise the view class using a factory request so we don't
        # have to worry about URLconf prefixes or authentication complications.
        from rest_framework.test import APIRequestFactory
        from apps.export.views import ExportStudentsExcelView

        from rest_framework.test import APIRequestFactory, force_authenticate
        factory = APIRequestFactory()
        request = factory.get(reverse('export'))
        # attach the user for authentication
        force_authenticate(request, user=self.user)
        view = ExportStudentsExcelView.as_view()
        resp = view(request)
        self.assertEqual(resp.status_code, 200)
        disp = resp['Content-Disposition']
        self.assertIn('attachment', disp)
        self.assertIn('export_data_', disp)
        self.assertTrue(disp.endswith('.xlsx"') or disp.endswith('.csv"'))


    def test_generate_excel_cell_coloring(self):
        # create a student with a specific level and a calendar entry
        student = Student.objects.create(
            first_name='Test',
            last_name='User',
            category='college',
            level='yellow',
            status='active',
        )
        # add a calendar level fired and none (use update_or_create to avoid duplicates)
        LevelByMonth.objects.update_or_create(student=student, year=2023, month=1, defaults={'level':'yellow'})
        LevelByMonth.objects.update_or_create(student=student, year=2023, month=2, defaults={'level':'fired'})

        wb = generate_excel_stream()
        ws = wb.active
        self.assertEqual(ws.title, 'Коты')
        # locate the row by name
        found = False
        for row in ws.iter_rows(min_row=2):
            if row[0].value == 'User Test':  # last + first
                found = True
                # current level column moved due to leading № column
                level_cell = row[6]
                self.assertEqual(level_cell.fill.fgColor.rgb.upper(), '00FFFF00')
                # first calendar column is after base headers later; locate index
                break
        self.assertTrue(found, "Exported workbook did not contain the student row")
