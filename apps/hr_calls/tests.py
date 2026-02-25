from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.hr_calls.models import HrCall
from apps.hr_calls.serializers import HrFileCreateSerializer


class HrFileUploadTests(TestCase):
    def setUp(self):
        # superuser just for convenience; role set so permission checks pass
        self.user = get_user_model().objects.create_superuser(
            username='admin', password='pass', email='a@b.com'
        )
        self.user.role = 'admin'
        self.user.save()
        self.call = HrCall.objects.create(
            person_type='college', full_name='Тестовый колледжист',
            created_by=self.user
        )
        self.client.force_login(self.user)

    def test_serializer_unrestricted(self):
        """Serializer should accept arbitrarily large or oddly-named files."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        import io

        # create a tiny valid image but give it a long name
        img_io = io.BytesIO()
        Image.new('RGB', (1, 1), color='white').save(img_io, format='PNG')
        img_io.seek(0)
        long_name = 'a' * 200 + '.png'
        fileobj = SimpleUploadedFile(long_name, img_io.read(), content_type='image/png')

        from types import SimpleNamespace

        serializer = HrFileCreateSerializer(
            data={'file': fileobj, 'description': 'ok'},
            context={'request': SimpleNamespace(user=self.user), 'hr_call': self.call}
        )
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        hrfile = serializer.save()
        self.assertTrue(hrfile.file.name)

    def test_client_upload_does_not_crash(self):
        """Using the test client should never return a 500, even for large bodies."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        big_file = SimpleUploadedFile('big.bin', b'a' * (1024 * 1024 * 3))
        url = reverse('hr_file_create', args=[self.call.pk])
        response = self.client.post(url, {'file': big_file, 'description': 'test'})
        self.assertNotEqual(response.status_code, 500)
