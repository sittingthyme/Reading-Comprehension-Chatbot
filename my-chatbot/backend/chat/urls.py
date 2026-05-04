from django.urls import path
from .views import ChatAPIView, conversation_audit
from . import views
from . import study_views

urlpatterns = [
    path("chat/", ChatAPIView.as_view(), name="chat"),
    path("start-conversation/", views.start_conversation, name="start_conversation"),
    path("save-message/", views.save_message, name="save_message"),
    path("audit/<uuid:conversation_id>/", conversation_audit, name="conversation_audit"),
    path("study/register/", study_views.study_register, name="study_register"),
    path("study/login/", study_views.study_login, name="study_login"),
    path("study/progress/", study_views.study_progress, name="study_progress"),
    path("study/session/start/", study_views.study_session_start, name="study_session_start"),
    path("study/session/heartbeat/", study_views.study_heartbeat, name="study_heartbeat"),
    path(
        "study/session/reading-questionnaire/",
        study_views.study_reading_questionnaire,
        name="study_reading_questionnaire",
    ),
    path(
        "study/session/survey-definition/",
        study_views.study_survey_definition,
        name="study_survey_definition",
    ),
    path(
        "study/session/caiq-panas/",
        study_views.study_caiq_panas_submit,
        name="study_caiq_panas_submit",
    ),
    path("study/session/complete/", study_views.study_session_complete, name="study_session_complete"),
    path("study/session/exit/", study_views.study_session_exit, name="study_session_exit"),
]