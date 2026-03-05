"""
Сервис для обработки массовой загрузки фотографий студентов.
Сопоставляет файлы по ФИО студентов.
"""
import logging
from PIL import Image
from io import BytesIO
import os
import re
import zipfile
import mimetypes
from collections import defaultdict
from itertools import permutations
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Student

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
MAX_RESULT_DETAILS = 300


def normalize_name(name):
    """Нормализует ФИО для сравнения (без пробелов, в нижнем регистре)."""
    if not name:
        return ''
    return ''.join(name.strip().lower().split())


def extract_full_name_from_filename(filename):
    """Извлекает ФИО из названия файла (без расширения)."""
    # Удаляем расширение
    name_without_ext = os.path.splitext(filename)[0]
    return name_without_ext.strip()


def is_image_filename(filename):
    """Проверяет, что файл является изображением по расширению."""
    if not filename:
        return False
    extension = os.path.splitext(filename)[1].lower()
    return extension in IMAGE_EXTENSIONS


def extract_photo_files_from_archive(archive_file):
    """
    Извлекает изображения из ZIP-архива и возвращает их как uploaded-файлы.

    В архиве могут быть вложенные папки — для сопоставления используется
    только имя файла (без пути).
    """
    if not archive_file:
        return []

    archive_name = getattr(archive_file, 'name', '')
    if os.path.splitext(archive_name)[1].lower() != '.zip':
        raise ValueError('Поддерживаются только ZIP-архивы')

    return list(iter_photo_files_from_archive(archive_file))


def iter_photo_files_from_archive(archive_file):
    """
    Итерирует изображения из ZIP-архива без загрузки всего архива в память.
    """
    if not archive_file:
        return

    archive_name = getattr(archive_file, 'name', '')
    if os.path.splitext(archive_name)[1].lower() != '.zip':
        raise ValueError('Поддерживаются только ZIP-архивы')

    found_images = False

    try:
        archive_file.seek(0)
        with zipfile.ZipFile(archive_file) as zip_ref:
            for member in zip_ref.infolist():
                if member.is_dir():
                    continue

                basename = os.path.basename(member.filename)
                if not basename or not is_image_filename(basename):
                    continue

                file_bytes = zip_ref.read(member)
                if not file_bytes:
                    continue

                found_images = True
                content_type = mimetypes.guess_type(basename)[0] or 'application/octet-stream'
                yield SimpleUploadedFile(
                    name=basename,
                    content=file_bytes,
                    content_type=content_type,
                )
    except zipfile.BadZipFile as exc:
        raise ValueError('Неверный ZIP-архив') from exc
    finally:
        archive_file.seek(0)

    if not found_images:
        raise ValueError('В ZIP-архиве не найдено изображений')


def _tokenize_name(name):
    return [p for p in re.split(r"[\s,_\-\.]+", (name or '').lower()) if p]


def _build_student_indexes():
    students_by_id = {}
    exact_name_index = defaultdict(list)
    token_to_student_ids = defaultdict(set)

    students = Student.objects.only('id', 'last_name', 'first_name', 'patronymic')
    for student in students:
        student_full_name = ' '.join([
            p for p in [
                getattr(student, 'last_name', '') or '',
                getattr(student, 'first_name', '') or '',
                getattr(student, 'patronymic', '') or ''
            ] if p
        ])

        norm_student_fio = normalize_name(student_full_name)
        if norm_student_fio:
            exact_name_index[norm_student_fio].append(student)

        tokens = _tokenize_name(student_full_name)
        students_by_id[student.id] = student
        for token in set(tokens):
            token_to_student_ids[token].add(student.id)

    return students_by_id, exact_name_index, token_to_student_ids


def _build_name_candidates(fio_from_file):
    parts = _tokenize_name(fio_from_file)
    candidates = set()

    if parts:
        candidates.add(''.join(parts))

        if len(parts) <= 3:
            for perm in permutations(parts):
                candidates.add(''.join(perm))

    return parts, candidates


def _append_result_item(results, key, item):
    results['stats'][key] += 1
    if len(results[key]) < MAX_RESULT_DETAILS:
        results[key].append(item)
    else:
        results['truncated'][key] += 1


def process_photo_uploads(uploaded_files):
    """
    Обрабатывает загруженные файлы фотографий.
    Сопоставляет файлы со студентами по ФИО и сохраняет фото.
    
    Args:
        uploaded_files: список загруженных файлов (request.FILES.getlist(...))
    
    Returns:
        dict с информацией об обработке:
        - matched: список успешно обновлённых студентов
        - unmatched: список файлов, для которых не найден студент
        - errors: список ошибок при сохранении
        - overwritten: список перезаписей (если одному студенту загружено несколько файлов)
        - stats: полная статистика (включая элементы, не попавшие в detail-списки)
        - truncated: количество скрытых detail-элементов по каждой категории
    """
    results = {
        'matched': [],
        'unmatched': [],
        'errors': [],
        'overwritten': [],
        'stats': {
            'total': 0,
            'matched': 0,
            'unmatched': 0,
            'errors': 0,
            'overwritten': 0,
        },
        'truncated': {
            'matched': 0,
            'unmatched': 0,
            'errors': 0,
            'overwritten': 0,
        }
    }

    last_uploaded_filename_by_student = {}
    students_by_id, exact_name_index, token_to_student_ids = _build_student_indexes()

    try:
        iterator = iter(uploaded_files)
    except TypeError:
        iterator = iter([])

    for uploaded_file in iterator:
        results['stats']['total'] += 1
        filename = getattr(uploaded_file, 'name', '') or 'unknown_file'
        
        # Извлекаем ФИО из названия файла
        fio_from_file = extract_full_name_from_filename(filename)
        norm_file_fio = normalize_name(fio_from_file)
        
        if not norm_file_fio:
            _append_result_item(results, 'unmatched', {
                'filename': filename,
                'reason': 'Не удалось извлечь ФИО из названия'
            })
            continue
        
        # Ищем студента с совпадающим ФИО
        try:
            parts, candidates = _build_name_candidates(fio_from_file)

            # Логируем для отладки
            logger.debug(f"photo_upload: файл='{filename}' ФИО='{fio_from_file}' нормализованное='{norm_file_fio}' кандидаты={list(candidates)}")

            matched_student_ids = set()

            for candidate in candidates:
                for matched_student in exact_name_index.get(candidate, []):
                    matched_student_ids.add(matched_student.id)

            if not matched_student_ids and parts:
                token_sets = [token_to_student_ids.get(part, set()) for part in parts]
                if token_sets and all(token_sets):
                    matched_student_ids = set.intersection(*token_sets)

            matched_students = [students_by_id[student_id] for student_id in sorted(matched_student_ids)]

            if not matched_students:
                logger.warning(f"photo_upload: студент не найден для файла '{filename}'")

                _append_result_item(results, 'unmatched', {
                    'filename': filename,
                    'fio': fio_from_file,
                    'reason': 'Студент не найден'
                })
                continue
            
            # Обрабатываем все найденные студенты (может быть несколько с одинаковым ФИО)
            for matched_student in matched_students:
                student_full_name = ' '.join([p for p in [getattr(matched_student, 'last_name', '') or '', getattr(matched_student, 'first_name', '') or '', getattr(matched_student, 'patronymic', '') or ''] if p])
                previous_filename = last_uploaded_filename_by_student.get(matched_student.id)
                overwrite_warning = None

                if previous_filename:
                    overwrite_warning = f"Фото перезаписано: {previous_filename} → {filename}"
                    _append_result_item(results, 'overwritten', {
                        'student_id': matched_student.id,
                        'full_name': student_full_name,
                        'previous_filename': previous_filename,
                        'filename': filename,
                    })
                
                try:
                    # Проверяем, это ли изображение
                    uploaded_file.seek(0)
                    img = Image.open(uploaded_file)
                    img_format = img.format or 'JPEG'
                    
                    # Переразмеряем если нужно (макс 1920x1920)
                    max_size = (1920, 1920)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Сохраняем обработанное изображение
                    img_io = BytesIO()
                    img.save(img_io, format=img_format)
                    img_io.seek(0)
                    
                    # Сохраняем в модель
                    file_extension = os.path.splitext(filename)[1].lower()
                    if not file_extension:
                        file_extension = '.jpg'
                    safe_filename = f"{norm_file_fio}{file_extension}"
                    
                    matched_student.photo.save(
                        safe_filename,
                        ContentFile(img_io.getvalue()),
                        save=True
                    )
                    
                    logger.info(f"photo_upload: фото сохранено для student_id={matched_student.id}")
                    
                    matched_item = {
                        'student_id': matched_student.id,
                        'full_name': student_full_name,
                        'filename': filename
                    }

                    if overwrite_warning:
                        matched_item['warning'] = overwrite_warning

                    _append_result_item(results, 'matched', matched_item)
                    last_uploaded_filename_by_student[matched_student.id] = filename
                    
                except Exception as e:
                    # Ошибка при обработке изображения - просто копируем файл
                    uploaded_file.seek(0)
                    matched_student.photo.save(
                        os.path.basename(filename),
                        uploaded_file,
                        save=True
                    )
                    logger.info(f"photo_upload: фото сохранено без оптимизации student_id={matched_student.id}")
                    
                    matched_item = {
                        'student_id': matched_student.id,
                        'full_name': student_full_name,
                        'filename': filename,
                        'warning': 'Сохранено без оптимизации'
                    }

                    if overwrite_warning:
                        matched_item['warning'] = f"{matched_item['warning']}. {overwrite_warning}"

                    _append_result_item(results, 'matched', matched_item)
                    last_uploaded_filename_by_student[matched_student.id] = filename
        
        except Exception as e:
            _append_result_item(results, 'errors', {
                'filename': filename,
                'error': str(e)
            })
    
    return results
