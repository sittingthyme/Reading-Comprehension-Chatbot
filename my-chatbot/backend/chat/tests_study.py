import json
import secrets

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import Conversation, Participant, StudySession, SurveyResponse
from .study_credentials import validate_pin_pair
from .study_services import (
    bootstrap_study_sessions,
    refresh_session_availability,
    validate_likert,
    comprehension_provided,
)


def _register_payload(code, display_name="Kid", pin="1234"):
    return json.dumps(
        {
            "enrollmentCode": code,
            "displayName": display_name,
            "pin": pin,
            "pinConfirm": pin,
        }
    )


@override_settings(
    STUDY_CODES_PERSONALIZED="TEST-P",
    STUDY_CODES_GENERIC="TEST-G",
    STUDY_START_DATE="1990-01-01",
    STUDY_TIMEZONE="UTC",
    STUDY_TOTAL_WEEKS=2,
    STUDY_PROFILE_PERSONALIZED_MAX_SESSION_MINUTES=20,
    STUDY_PROFILE_GENERIC_MAX_SESSION_MINUTES=20,
    STUDY_PIN_MIN_LENGTH=4,
    STUDY_PIN_MAX_LENGTH=6,
    STUDY_LOGIN_CODE_LENGTH=10,
    STUDY_ROTATE_TOKEN_ON_LOGIN=True,
)
class StudyApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_invalid_code(self):
        r = self.client.post(
            "/api/study/register/",
            data=_register_payload("BAD"),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_register_requires_pin(self):
        r = self.client.post(
            "/api/study/register/",
            data=json.dumps({"enrollmentCode": "TEST-P"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_register_bootstrap_and_sequential_unlock(self):
        r = self.client.post(
            "/api/study/register/",
            data=_register_payload("TEST-P"),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        token = data["authToken"]
        self.assertTrue(token)
        self.assertTrue(data.get("loginCode"))

        p = Participant.objects.get(auth_token=token)
        self.assertEqual(p.condition, Participant.Condition.PERSONALIZED)
        self.assertEqual(p.login_code, data["loginCode"])
        self.assertEqual(StudySession.objects.filter(participant=p).count(), 6)

        r2 = self.client.get(
            "/api/study/progress/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(r2.status_code, 200)
        prog = json.loads(r2.content)
        self.assertEqual(prog["focusSlotIndex"], 1)
        self.assertEqual(prog["focusStatus"], "available")

    def test_start_complete_unlocks_next(self):
        r = self.client.post(
            "/api/study/register/",
            data=_register_payload("TEST-G"),
            content_type="application/json",
        )
        token = json.loads(r.content)["authToken"]
        prog = json.loads(
            self.client.get(
                "/api/study/progress/", HTTP_AUTHORIZATION=f"Bearer {token}"
            ).content
        )
        sid = prog["focusSessionId"]

        r_start = self.client.post(
            "/api/study/session/start/",
            data=json.dumps(
                {
                    "studySessionId": sid,
                    "userName": "A",
                    "character": "default",
                    "initialMessage": "Hello.",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(r_start.status_code, 200)

        r_read = self.client.post(
            "/api/study/session/reading-questionnaire/",
            data=json.dumps(
                {
                    "studySessionId": sid,
                    "endReason": "completed_content",
                    "likert": {"rapport": 4, "closeness": 3, "flow": 5},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(r_read.status_code, 200)

        defn = json.loads(
            self.client.get(
                f"/api/study/session/survey-definition/?studySessionId={sid}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            ).content
        )
        self.assertEqual(defn["surveyVersion"], "full")
        self.assertEqual(len(defn["items"]), 29)

        answers = [{"itemId": it["itemId"], "value": 3} for it in defn["items"]]
        r_caiq = self.client.post(
            "/api/study/session/caiq-panas/",
            data=json.dumps({"studySessionId": sid, "answers": answers}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(r_caiq.status_code, 200, r_caiq.content)

        ss_done = StudySession.objects.get(id=sid)
        self.assertEqual(ss_done.survey_scores.get("version"), "full")
        self.assertEqual(ss_done.survey_scores.get("caiqTotalMean"), 3.0)
        self.assertEqual(ss_done.survey_scores.get("panasPositiveMean"), 3.0)
        self.assertEqual(ss_done.survey_scores.get("panasNegativeMean"), 3.0)
        self.assertEqual(ss_done.survey_scores.get("overallAffect"), 0.0)

        prog2 = json.loads(
            self.client.get(
                "/api/study/progress/", HTTP_AUTHORIZATION=f"Bearer {token}"
            ).content
        )
        self.assertEqual(prog2["focusSlotIndex"], 2)
        self.assertEqual(SurveyResponse.objects.filter(study_session_id=sid).count(), 29)

    def test_reading_only_does_not_unlock(self):
        r = self.client.post(
            "/api/study/register/",
            data=_register_payload("TEST-P"),
            content_type="application/json",
        )
        token = json.loads(r.content)["authToken"]
        prog = json.loads(
            self.client.get(
                "/api/study/progress/", HTTP_AUTHORIZATION=f"Bearer {token}"
            ).content
        )
        sid = prog["focusSessionId"]
        self.client.post(
            "/api/study/session/start/",
            data=json.dumps(
                {
                    "studySessionId": sid,
                    "userName": "A",
                    "character": "default",
                    "initialMessage": "Hi.",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.client.post(
            "/api/study/session/reading-questionnaire/",
            data=json.dumps(
                {
                    "studySessionId": sid,
                    "endReason": "completed_content",
                    "likert": {"rapport": 4, "closeness": 3, "flow": 5},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        prog2 = json.loads(
            self.client.get(
                "/api/study/progress/", HTTP_AUTHORIZATION=f"Bearer {token}"
            ).content
        )
        self.assertEqual(prog2["focusSlotIndex"], 1)

    def test_session_complete_deprecated(self):
        r = self.client.post(
            "/api/study/session/complete/",
            data=json.dumps({"studySessionId": "00000000-0000-0000-0000-000000000000"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 410)

    def test_slot3_requires_comprehension(self):
        p = Participant.objects.create(
            condition=Participant.Condition.GENERIC,
            auth_token=secrets.token_urlsafe(32),
            enrollment_code_used="TEST-G",
        )
        bootstrap_study_sessions(p)
        for ss in StudySession.objects.filter(participant=p):
            ss.status = StudySession.Status.COMPLETED
            ss.save()
        third = StudySession.objects.get(participant=p, week_index=1, slot_index=3)
        third.status = StudySession.Status.AVAILABLE
        third.save()
        refresh_session_availability(p)
        third.refresh_from_db()
        self.assertEqual(third.status, StudySession.Status.AVAILABLE)

        convo = Conversation.objects.create(
            user_name="A",
            character="default",
            participant=p,
        )
        third.conversation = convo
        third.status = StudySession.Status.IN_PROGRESS
        third.started_at = timezone.now()
        third.last_activity_at = timezone.now()
        third.save()

        r = self.client.post(
            "/api/study/session/reading-questionnaire/",
            data=json.dumps(
                {
                    "studySessionId": str(third.id),
                    "endReason": "completed_content",
                    "likert": {"rapport": 4, "closeness": 3, "flow": 5},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {p.auth_token}",
        )
        self.assertEqual(r.status_code, 400)

        r_ok = self.client.post(
            "/api/study/session/reading-questionnaire/",
            data=json.dumps(
                {
                    "studySessionId": str(third.id),
                    "endReason": "completed_content",
                    "likert": {"rapport": 4, "closeness": 3, "flow": 5},
                    "comprehension": {"main_response": "I understood the plot."},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {p.auth_token}",
        )
        self.assertEqual(r_ok.status_code, 200)

        defn = json.loads(
            self.client.get(
                f"/api/study/session/survey-definition/?studySessionId={third.id}",
                HTTP_AUTHORIZATION=f"Bearer {p.auth_token}",
            ).content
        )
        self.assertEqual(defn["surveyVersion"], "mini")
        answers = [{"itemId": it["itemId"], "value": 4} for it in defn["items"]]
        r_c = self.client.post(
            "/api/study/session/caiq-panas/",
            data=json.dumps({"studySessionId": str(third.id), "answers": answers}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {p.auth_token}",
        )
        self.assertEqual(r_c.status_code, 200)
        self.assertEqual(SurveyResponse.objects.filter(study_session=third).count(), 10)
        third.refresh_from_db()
        self.assertEqual(third.survey_scores.get("version"), "mini")
        self.assertEqual(third.survey_scores.get("overallAffectMini"), 0.0)

    def test_wall_lock_rejects_save_message(self):
        p = Participant.objects.create(
            condition=Participant.Condition.GENERIC,
            auth_token=secrets.token_urlsafe(32),
            enrollment_code_used="TEST-G",
        )
        bootstrap_study_sessions(p)
        ss = StudySession.objects.get(participant=p, week_index=1, slot_index=1)
        convo = Conversation.objects.create(
            user_name="A",
            character="default",
            participant=p,
        )
        ss.conversation = convo
        ss.status = StudySession.Status.IN_PROGRESS
        ss.started_at = timezone.now() - timezone.timedelta(minutes=25)
        ss.last_activity_at = timezone.now()
        ss.save()

        r = self.client.post(
            "/api/save-message/",
            data=json.dumps(
                {
                    "conversationId": str(convo.id),
                    "sender": "user",
                    "content": "hi",
                    "meta": {},
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {p.auth_token}",
        )
        self.assertEqual(r.status_code, 403)
        body = json.loads(r.content)
        self.assertTrue(body.get("sessionLocked"))

    def test_login_success_and_token_rotation(self):
        reg = self.client.post(
            "/api/study/register/",
            data=_register_payload("TEST-G", pin="9876"),
            content_type="application/json",
        )
        self.assertEqual(reg.status_code, 200)
        reg_data = json.loads(reg.content)
        old_token = reg_data["authToken"]
        lc = reg_data["loginCode"]

        log = self.client.post(
            "/api/study/login/",
            data=json.dumps({"loginCode": lc, "pin": "9876"}),
            content_type="application/json",
        )
        self.assertEqual(log.status_code, 200)
        log_data = json.loads(log.content)
        self.assertNotEqual(log_data["authToken"], old_token)

        prog = self.client.get(
            "/api/study/progress/",
            HTTP_AUTHORIZATION=f"Bearer {log_data['authToken']}",
        )
        self.assertEqual(prog.status_code, 200)

    def test_login_wrong_pin(self):
        reg = self.client.post(
            "/api/study/register/",
            data=_register_payload("TEST-G"),
            content_type="application/json",
        )
        lc = json.loads(reg.content)["loginCode"]
        r = self.client.post(
            "/api/study/login/",
            data=json.dumps({"loginCode": lc, "pin": "9999"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_login_unknown_code(self):
        r = self.client.post(
            "/api/study/login/",
            data=json.dumps({"loginCode": "ZZZZZZZZZZ", "pin": "1234"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)


@override_settings(STUDY_PIN_MIN_LENGTH=4, STUDY_PIN_MAX_LENGTH=6)
class StudyValidationTests(TestCase):
    def test_pin_validation(self):
        self.assertIsNone(validate_pin_pair("1234", "1234"))
        self.assertIsNotNone(validate_pin_pair("1234", "1235"))
        self.assertIsNotNone(validate_pin_pair("12ab", "12ab"))

    def test_likert_validator(self):
        self.assertTrue(
            validate_likert({"rapport": 1, "closeness": 5, "flow": 3})
        )
        self.assertFalse(validate_likert({"rapport": 6, "closeness": 1, "flow": 1}))
        self.assertFalse(validate_likert({}))

    def test_comprehension_provided(self):
        self.assertTrue(comprehension_provided({"a": "text"}))
        self.assertFalse(comprehension_provided({"a": ""}))
        self.assertFalse(comprehension_provided({}))
