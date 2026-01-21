from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import AnalyticsSnapshot
from apps.students.models import CATEGORY_CHOICES, Student


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request):
        snapshot = AnalyticsSnapshot.get_or_create_snapshot()
        active_total = Student.objects.filter(status='active').exclude(level='fired').count() or 1
        students_by_level = []
        for level, count in snapshot.distribution_by_level.items():
            if isinstance(count, dict):
                count = count.get('count', 0)
            count = int(count) if count else 0
            percentage = round(count / active_total * 100, 1) if active_total > 0 else 0.0
            students_by_level.append({
                "level": level,
                "display_name": level.capitalize(),
                "count": count,
                "percentage": percentage
            })
        total = snapshot.total_students or 1
        students_by_status = [
            {
                "status": status,
                "display_name": status.capitalize(),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for status, count in snapshot.distribution_by_status.items()
        ]
        students_by_category = [
            {
                "category": category,
                "display_name": dict(CATEGORY_CHOICES).get(category, category.capitalize()),
                "count": count,
                "percentage": round(count / total * 100, 1)
            }
            for category, count in snapshot.distribution_by_category.items()
        ]
        return Response({
            "success": True,
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
        }, status=200)

class LevelDistributionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    def get(self, request):
        snapshot = AnalyticsSnapshot.get_or_create_snapshot()
        active_total = Student.objects.filter(status='active').exclude(level='fired').count() or 1
        levels = [
            {
                "level": level,
                "display_name": level.capitalize(),
                "count": int(count) if not isinstance(count, dict) else count.get('count', 0),
                "percentage": round((int(count) if not isinstance(count, dict) else count.get('count', 0)) / active_total * 100, 1)
            }
            for level, count in snapshot.distribution_by_level.items()
        ]
        return Response({
            "success": True,
            "levels": levels,
            "total_active": active_total
        }, status=200)