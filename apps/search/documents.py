# apps/students/documents.py
from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.fields import TextField, IntegerField, KeywordField
from django_elasticsearch_dsl.registries import registry
from apps.students.models import Student

@registry.register_document
class StudentDocument(Document):
    full_name = TextField(
        analyzer='russian',  # русская морфология
        fields={'raw': KeywordField()}  # для сортировки
    )
    phone_personal = TextField()
    telegram = TextField()
    subdivision = TextField(analyzer='russian')
    direction = TextField(analyzer='russian')
    fio_parent = TextField(analyzer='russian')

    class Index:
        name = 'students'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }

    class Django:
        model = Student
        fields = [
            'id',
            'level',
            'status',
            'category',
        ]

    def get_queryset(self):
        return Student.objects.all()

    def prepare_full_name(self, instance):
        return instance.full_name

    def prepare_age(self, instance):
        return instance.age