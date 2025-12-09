from django.urls import path
from .views import ChatAPIView, conversation_audit
from . import views

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("start-conversation/", views.start_conversation, name="start_conversation"),
    path("save-message/", views.save_message, name="save_message"),
    path("audit/<uuid:conversation_id>/", conversation_audit, name="conversation_audit"),
]