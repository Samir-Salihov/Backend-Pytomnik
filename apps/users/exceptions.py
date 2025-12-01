# apps/users/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Глобальный обработчик ошибок для всего API
    Логирует всё + возвращает красивый JSON
    """
    # Логируем полную ошибку
    logger.error(f"Ошибка в {context['view']}: {exc}", exc_info=True)

    # Получаем стандартный ответ DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Красивый формат для валидации и аутентификации
        custom_data = {
            "error": True,
            "message": "Ошибка в запросе",
            "details": response.data
        }
        if response.status_code == 401:
            custom_data["message"] = "Неверный логин или пароль"
        elif response.status_code == 400:
            custom_data["message"] = "Некорректные данные"
        elif response.status_code == 403:
            custom_data["message"] = "Доступ запрещён"

        response.data = custom_data

    else:
        # 500 ошибка — если DRF не поймал
        response = Response({
            "error": True,
            "message": "Внутренняя ошибка сервера. Администратор уведомлён.",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.critical(f"Критическая ошибка: {exc}", exc_info=True)

    return response