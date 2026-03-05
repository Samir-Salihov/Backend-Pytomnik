from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/kanban/(?P<board_id>\w+)/$', consumers.KanbanRealtimeConsumer.as_asgi()),
]