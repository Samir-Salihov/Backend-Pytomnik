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
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Student

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}


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

    extracted_files = []

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

                content_type = mimetypes.guess_type(basename)[0] or 'application/octet-stream'
                extracted_files.append(
                    SimpleUploadedFile(
                        name=basename,
                        content=file_bytes,
                        content_type=content_type,
                    )
                )
    except zipfile.BadZipFile as exc:
        raise ValueError('Неверный ZIP-архив') from exc
    finally:
        archive_file.seek(0)

    if not extracted_files:
        raise ValueError('В ZIP-архиве не найдено изображений')

    return extracted_files


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
    """
    results = {
        'matched': [],
        'unmatched': [],
        'errors': [],
        'overwritten': [],
    }

    last_uploaded_filename_by_student = {}
    
    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        
        # Извлекаем ФИО из названия файла
        fio_from_file = extract_full_name_from_filename(filename)
        norm_file_fio = normalize_name(fio_from_file)
        
        if not norm_file_fio:
            results['unmatched'].append({
                'filename': filename,
                'reason': 'Не удалось извлечь ФИО из названия'
            })
            continue
        
        # Ищем студента с совпадающим ФИО
        try:
            # Формируем варианты нормализованного ФИО из имени файла
            parts = [p for p in re.split(r"[\s,_\-\.]+", fio_from_file.lower()) if p]
            candidates = set()
            if parts:
                candidates.add(''.join(parts))
            if len(parts) >= 2:
                candidates.add(parts[0] + parts[1])
                candidates.add(parts[1] + parts[0])
            if len(parts) >= 3:
                candidates.add(parts[0] + parts[1] + parts[2])
                candidates.add(parts[1] + parts[0] + parts[2])

            # Логируем для отладки
            logger.debug(f"photo_upload: файл='{filename}' ФИО='{fio_from_file}' нормализованное='{norm_file_fio}' кандидаты={list(candidates)}")

            # Проверяем всех студентов (нормализуем их ФИО) и пытаемся найти соответствие
            # Собираем ВСЕХ совпадающих студентов (может быть несколько с одинаковым ФИО)
            students = Student.objects.all()
            matched_students = []

            for student in students:
                # Собираем ФИО студента из полей модели
                student_full_name = ' '.join([p for p in [getattr(student, 'last_name', '') or '', getattr(student, 'first_name', '') or '', getattr(student, 'patronymic', '') or ''] if p])
                norm_student_fio = normalize_name(student_full_name)

                # Логируем для диагностики
                # Если найдём точное совпадение с любым кандидатом — добавляем в список
                if norm_student_fio in candidates:
                    matched_students.append(student)
                    logger.debug(f"photo_upload: совпадение по кандидату student_id={student.id} full_name='{student_full_name}'")
                    continue

                # Дополнительная гибкая проверка: все части присутствуют в ФИО студента
                if parts and all(p in norm_student_fio for p in parts):
                    matched_students.append(student)
                    logger.debug(f"photo_upload: частичное совпадение student_id={student.id} full_name='{student_full_name}'")

            if not matched_students:
                logger.warning(f"photo_upload: студент не найден для файла '{filename}'")

                results['unmatched'].append({
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
                    results['overwritten'].append({
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

                    results['matched'].append(matched_item)
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

                    results['matched'].append(matched_item)
                    last_uploaded_filename_by_student[matched_student.id] = filename
        
        except Exception as e:
            results['errors'].append({
                'filename': filename,
                'error': str(e)
            })
    
    return results
