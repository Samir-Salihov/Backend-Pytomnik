from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import AnalyticsSnapshot
from apps.students.models import CATEGORY_CHOICES


class AnalyticsDashboardView(APIView):
    """
    Текущая аналитика (всегда актуальная через сигналы).
    fired НЕ считается уровнем/цветом.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        snapshot = AnalyticsSnapshot.get_or_create_snapshot()
        total = snapshot.total_students or 1  # защита от деления на 0

        # Уровни — без 'fired'
        students_by_level = [
            {
                "level": level,
                "display_name": level.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for level, count in snapshot.distribution_by_level.items()
        ]

        # Статусы
        students_by_status = [
            {
                "status": status,
                "display_name": status.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for status, count in snapshot.distribution_by_status.items()
        ]

        # Категории
        students_by_category = [
            {
                "category": category,
                "display_name": dict(CATEGORY_CHOICES).get(category, category.capitalize()),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for category, count in snapshot.distribution_by_category.items()
        ]

        data = {
            "total_students": snapshot.total_students,
            "active_students": snapshot.active_students,
            "fired_students": snapshot.fired_students,
            "called_hr_students": snapshot.called_hr_students,
            "new_students_total": snapshot.new_students_total,
            "level_changes_total": snapshot.level_changes_total,
            "students_by_level": students_by_level,
            "students_by_status": students_by_status,
            "students_by_category": students_by_category,
            "updated_at": snapshot.updated_at,
        }

        return Response({
            "success": True,
            "data": data
        }, status=200)


class LevelDistributionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        snapshot = AnalyticsSnapshot.get_or_create_snapshot()
        total = snapshot.total_students or 1

        levels = [
            {
                "level": level,
                "display_name": level.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for level, count in snapshot.distribution_by_level.items()
        ]

        return Response({
            "success": True,
            "levels": levels,
            "total": snapshot.total_students
        }, status=200)