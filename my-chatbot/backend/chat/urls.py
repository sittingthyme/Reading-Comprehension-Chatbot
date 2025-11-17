from django.urls import path
from .views import ChatAPIView
from . import views

urlpatterns = [
    path('chat/', ChatAPIView.as_view()), 
    path("start-conversation/", views.start_conversation, name="start_conversation"),
    path("save-message/", views.save_message, name="save_message"),
]
