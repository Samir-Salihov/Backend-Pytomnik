"""
Админ-views для функционала загрузки фотографий.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from .photo_uploader import process_photo_uploads, extract_photo_files_from_archive


@login_required
@require_http_methods(["GET", "POST"])
def bulk_photo_upload(request):
    """
    Страница для загрузки нескольких фотографий студентов одновременно.
    Поддерживает drag-and-drop, выбор файлов и загрузку ZIP-архива папки.
    """
    # NOTE: currently allowing any authenticated user to access this view.
    # If you want to restrict to staff/admin roles, restore an explicit
    # role check here (e.g. request.user.is_staff or request.user.is_admin_role).
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('photos')
        archive_file = request.FILES.get('photos_archive')

        archive_files = []
        if archive_file:
            try:
                archive_files = extract_photo_files_from_archive(archive_file)
            except ValueError as exc:
                return JsonResponse({
                    'success': False,
                    'message': str(exc)
                }, status=400)

        files_to_process = [*uploaded_files, *archive_files]

        if not files_to_process:
            return JsonResponse({
                'success': False,
                'message': 'Не выбрано ни одного файла'
            }, status=400)

        # Обрабатываем загруженные файлы
        results = process_photo_uploads(files_to_process)

        return JsonResponse({
            'success': True,
            'results': results,
            'summary': {
                'total': len(files_to_process),
                'matched': len(results['matched']),
                'overwritten': len(results['overwritten']),
                'unmatched': len(results['unmatched']),
                'errors': len(results['errors'])
            }
        })
    
    return render(request, 'admin/students/bulk_photo_upload.html', {
        'title': 'Массовая загрузка фотографий студентов'
    })
