# apps/users/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from utils.exceptions import APIException
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Глобальный обработчик ошибок для всего API
    Логирует всё + возвращает красивый JSON формат
    
    Обрабатывает:
    1. Кастомные исключения из apps.exceptions (APIException)
    2. DRF исключения (ValidationError, AuthenticationFailed, и т.д.)
    3. Стандартные Django исключения
    4. Неожиданные ошибки (500)
    """
    
    view_name = context.get('view', 'unknown_view').__class__.__name__
    request = context.get('request')
    method = request.method if request else 'UNKNOWN'
    path = request.path if request else 'unknown_path'
    
    # Обработка кастомных исключений (APIException)
    if isinstance(exc, APIException):
        logger.warning(
            f"[{method} {path}] {exc.code}: {exc.message}",
            extra={'view': view_name, 'status_code': exc.status_code}
        )
        
        response_data = {
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }
        
        if hasattr(exc, 'details') and exc.details:
            response_data["error"]["details"] = exc.details
        
        return Response(response_data, status=exc.status_code)
    
    # Обработка DRF исключений (ValidationError, AuthenticationFailed и т.д.)
    response = exception_handler(exc, context)
    
    if response is not None:
        # Логируем в зависимости от кода ошибки
        if response.status_code >= 500:
            logger.error(
                f"[{method} {path}] HTTP {response.status_code}: {exc}",
                exc_info=True,
                extra={'view': view_name}
            )
        else:
            logger.warning(
                f"[{method} {path}] HTTP {response.status_code}: {exc}",
                extra={'view': view_name}
            )
        
        # Преобразуем ответ в единый формат
        custom_data = {
            "success": False,
            "error": {
                "code": f"HTTP_{response.status_code}",
                "message": _get_error_message(response.status_code),
                "details": response.data
            }
        }
        
        response.data = custom_data
        return response
    
    # Обработка неожиданных ошибок (500)
    logger.critical(
        f"[{method} {path}] Unhandled exception: {exc}",
        exc_info=True,
        extra={'view': view_name}
    )
    
    response = Response({
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Внутренняя ошибка сервера. Администратор уведомлён.",
        }
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response


def _get_error_message(status_code):
    """Получает человекочитаемое сообщение по коду ошибки HTTP"""
    messages = {
        400: "Некорректные данные в запросе",
        401: "Требуется аутентификация",
        403: "Доступ запрещён",
        404: "Ресурс не найден",
        405: "Метод не разрешён",
        409: "Конфликт данных",
        413: "Файл слишком большой",
        429: "Слишком много запросов",
        500: "Внутренняя ошибка сервера",
        502: "Неверный ответ от сервера",
        503: "Сервис недоступен",
    }
    return messages.get(status_code, "Ошибка при обработке запроса")