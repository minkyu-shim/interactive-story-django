from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StoryOwnership, StoryReport


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


class StoryGraphTests(TestCase):
    def setUp(self):
        self.story_id = 501
        self.owner = User.objects.create_user(username='owner_user', password='pw123456')
        self.staff = User.objects.create_user(username='staff_user', password='pw123456', is_staff=True)
        self.other = User.objects.create_user(username='other_user', password='pw123456')
        StoryOwnership.objects.create(user=self.owner, story_id=self.story_id)
        self.graph_url = reverse('story_graph', kwargs={'story_id': self.story_id})

    def _sample_story(self):
        return {
            'id': self.story_id,
            'title': 'Graph Sample',
            'start_node_id': 'start',
            'pages': [
                {
                    'id': 'start',
                    'title': 'Start',
                    'is_ending': False,
                    'text': 'Welcome node',
                    'choices': [
                        {'id': 1, 'text': 'Go next', 'next_page_id': 'mid'},
                        {'id': 2, 'text': 'Go broken', 'next_page_id': 'ghost'},
                    ],
                },
                {
                    'id': 'mid',
                    'title': 'Middle',
                    'is_ending': True,
                    'text': 'Ending node',
                    'choices': [],
                },
                {
                    'id': 'orphan',
                    'title': 'Orphan',
                    'is_ending': False,
                    'text': 'Unreachable node',
                    'choices': [],
                },
            ],
        }

    def test_graph_view_forbidden_for_non_owner_non_staff(self):
        self.client.login(username='other_user', password='pw123456')
        response = self.client.get(self.graph_url)
        self.assertEqual(response.status_code, 403)

    @patch('gameplay.views.get_story_details')
    def test_staff_can_access_graph_without_ownership(self, mock_get_story_details):
        mock_get_story_details.return_value = self._sample_story()
        self.client.login(username='staff_user', password='pw123456')
        response = self.client.get(self.graph_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Story Tree')

    @patch('gameplay.views.get_story_details')
    def test_graph_payload_marks_unreachable_and_broken(self, mock_get_story_details):
        mock_get_story_details.return_value = self._sample_story()
        self.client.login(username='owner_user', password='pw123456')
        response = self.client.get(self.graph_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['node_count'], 3)
        self.assertEqual(response.context['edge_count'], 2)
        self.assertEqual(response.context['unreachable_count'], 1)
        self.assertEqual(response.context['broken_edge_count'], 1)
        self.assertIn('orphan', response.context['unreachable_node_ids'])

        elements = response.context['graph_elements']
        self.assertTrue(any(item.get('classes') == 'missing' for item in elements))
        self.assertTrue(any(item.get('classes') == 'broken' for item in elements))


class ChoiceRollTests(TestCase):
    def setUp(self):
        self.story_id = 777
        self.node_id = 'start'
        self.url = reverse('choose_choice', kwargs={'story_id': self.story_id, 'node_id': self.node_id})

    @patch('gameplay.views.get_node')
    def test_choose_choice_without_roll_redirects_to_target(self, mock_get_node):
        mock_get_node.return_value = {
            'id': self.node_id,
            'choices': [
                {'id': 1, 'target_node': 'next_node', 'requires_roll': False},
            ],
        }
        response = self.client.post(self.url, {'choice_id': '1'})
        expected = reverse('play_node', kwargs={'story_id': self.story_id, 'node_id': 'next_node'})
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    @patch('gameplay.views.random.randint', return_value=6)
    @patch('gameplay.views.get_node')
    def test_choose_choice_roll_success_uses_primary_target(self, mock_get_node, _mock_randint):
        mock_get_node.return_value = {
            'id': self.node_id,
            'choices': [
                {'id': 2, 'target_node': 'treasure', 'requires_roll': True, 'roll_sides': 6, 'roll_required': 4},
            ],
        }
        response = self.client.post(self.url, {'choice_id': '2'})
        expected = reverse('play_node', kwargs={'story_id': self.story_id, 'node_id': 'treasure'})
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    @patch('gameplay.views.random.randint', return_value=1)
    @patch('gameplay.views.get_node')
    def test_choose_choice_roll_fail_uses_fail_target(self, mock_get_node, _mock_randint):
        mock_get_node.return_value = {
            'id': self.node_id,
            'choices': [
                {
                    'id': 3,
                    'target_node': 'treasure',
                    'requires_roll': True,
                    'roll_sides': 6,
                    'roll_required': 4,
                    'on_fail_target': 'pitfall',
                },
            ],
        }
        response = self.client.post(self.url, {'choice_id': '3'})
        expected = reverse('play_node', kwargs={'story_id': self.story_id, 'node_id': 'pitfall'})
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    @patch('gameplay.views.random.randint', return_value=1)
    @patch('gameplay.views.get_node')
    def test_choose_choice_roll_fail_without_fail_target_stays_on_node(self, mock_get_node, _mock_randint):
        mock_get_node.return_value = {
            'id': self.node_id,
            'choices': [
                {'id': 4, 'target_node': 'treasure', 'requires_roll': True, 'roll_sides': 6, 'roll_required': 4},
            ],
        }
        response = self.client.post(self.url, {'choice_id': '4'})
        expected = reverse('play_node', kwargs={'story_id': self.story_id, 'node_id': self.node_id})
        self.assertRedirects(response, expected, fetch_redirect_response=False)
