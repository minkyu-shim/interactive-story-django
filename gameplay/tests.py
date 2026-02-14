from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StoryReport


class StoryReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reporter', password='pw123456')
        self.story_id = 99
        self.report_url = reverse('report_story', kwargs={'story_id': self.story_id})

    def test_report_requires_login(self):
        response = self.client.get(self.report_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    @patch('gameplay.views.get_story_details', return_value={'id': 99, 'title': 'Sample Story'})
    def test_submit_report_creates_row(self, _mock_story_details):
        self.client.login(username='reporter', password='pw123456')
        response = self.client.post(self.report_url, {
            'reason': StoryReport.Reason.SPAM,
            'details': 'Looks like spam links.',
        })

        self.assertEqual(response.status_code, 302)
        report = StoryReport.objects.get(user=self.user, story_id=self.story_id)
        self.assertEqual(report.reason, StoryReport.Reason.SPAM)
        self.assertEqual(report.status, StoryReport.Status.OPEN)
        self.assertEqual(report.story_title_snapshot, 'Sample Story')

    @patch('gameplay.views.get_story_details', return_value={'id': 99, 'title': 'Sample Story'})
    def test_resubmit_updates_existing_report(self, _mock_story_details):
        self.client.login(username='reporter', password='pw123456')

        self.client.post(self.report_url, {
            'reason': StoryReport.Reason.SPAM,
            'details': 'First report.',
        })
        self.client.post(self.report_url, {
            'reason': StoryReport.Reason.OTHER,
            'details': 'Updated report details.',
        })

        self.assertEqual(StoryReport.objects.filter(user=self.user, story_id=self.story_id).count(), 1)
        report = StoryReport.objects.get(user=self.user, story_id=self.story_id)
        self.assertEqual(report.reason, StoryReport.Reason.OTHER)
        self.assertEqual(report.details, 'Updated report details.')


class StoryReportModerationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='admin_user', password='pw123456', is_staff=True)
        self.normal = User.objects.create_user(username='normal_user', password='pw123456')
        self.report_owner = User.objects.create_user(username='report_owner', password='pw123456')
        self.report = StoryReport.objects.create(
            user=self.report_owner,
            story_id=101,
            story_title_snapshot='Moderation Target Story',
            reason=StoryReport.Reason.ABUSE,
            details='Offensive language in the content.',
        )
        self.list_url = reverse('moderation_reports')
        self.update_url = reverse('moderation_report_update', kwargs={'report_id': self.report.id})

    def test_moderation_list_requires_login(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_moderation_list_forbidden_for_non_staff(self):
        self.client.login(username='normal_user', password='pw123456')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_staff_can_view_moderation_list(self):
        self.client.login(username='admin_user', password='pw123456')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report Moderation')
        self.assertContains(response, 'Moderation Target Story')

    def test_staff_can_resolve_report(self):
        self.client.login(username='admin_user', password='pw123456')
        response = self.client.post(self.update_url, {
            f'r{self.report.id}-status': StoryReport.Status.RESOLVED,
            f'r{self.report.id}-admin_note': 'Checked and handled.',
            'next': self.list_url,
        })
        self.assertEqual(response.status_code, 302)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, StoryReport.Status.RESOLVED)
        self.assertEqual(self.report.resolved_by, self.staff)
        self.assertIsNotNone(self.report.resolved_at)
        self.assertEqual(self.report.admin_note, 'Checked and handled.')

    def test_staff_setting_in_review_clears_resolved_fields(self):
        self.report.status = StoryReport.Status.RESOLVED
        self.report.resolved_by = self.staff
        self.report.resolved_at = self.report.created_at
        self.report.save(update_fields=['status', 'resolved_by', 'resolved_at'])

        self.client.login(username='admin_user', password='pw123456')
        self.client.post(self.update_url, {
            f'r{self.report.id}-status': StoryReport.Status.IN_REVIEW,
            f'r{self.report.id}-admin_note': 'Reopened for review.',
            'next': self.list_url,
        })
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, StoryReport.Status.IN_REVIEW)
        self.assertIsNone(self.report.resolved_by)
        self.assertIsNone(self.report.resolved_at)

    def test_status_filter_redirect_tracks_updated_status(self):
        self.client.login(username='admin_user', password='pw123456')
        response = self.client.post(self.update_url, {
            f'r{self.report.id}-status': StoryReport.Status.IN_REVIEW,
            f'r{self.report.id}-admin_note': 'Moved to in review.',
            'next': f'{self.list_url}?status={StoryReport.Status.OPEN}',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'status={StoryReport.Status.IN_REVIEW}', response.url)
