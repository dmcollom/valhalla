from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from valhalla.userrequests.models import UserRequest, Request
from valhalla.proposals.models import Proposal, Membership, TimeAllocation, Semester
from rest_framework.test import APITestCase

from mixer.backend.django import mixer
from unittest.mock import patch
from django.utils import timezone
from datetime import datetime
import copy

import valhalla.userrequests.signals.handlers # noqa


configdb_data = [
    {
        'code': 'tst',
        'enclosure_set': [
            {
                'code': 'doma',
                'telescope_set': [
                    {
                        'code': '1m0a',
                        'lat': -32.3805542,
                        'lon': 20.8100352,
                        'horizon': 15.0,
                        'ha_limit_pos': 4.6,
                        'ha_limit_neg': -4.6,
                        'instrument_set': [
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx01',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '1M0-SCICAM-SBIG',
                                        'name': '1M0-SCICAM-SBIG',
                                        'default_mode': {
                                            'binning': 2,
                                            'readout': 14.5,
                                        },
                                        'config_change_time': 0,
                                        'acquire_processing_time': 0,
                                        'acquire_exposure_time': 0,
                                        'front_padding': 90,
                                        'filter_change_time': 2,
                                        'fixed_overhead_per_exposure': 1,
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 35.0,
                                            },
                                            {
                                                'binning': 2,
                                                'readout': 14.5,
                                            },
                                            {
                                                'binning': 3,
                                                'readout': 11.5,
                                            },
                                        ]
                                    },
                                    'filters': 'air',
                                },
                                '__str__': 'tst.doma.1m0a.xx01-xx01',
                            },
                            {
                                'state': 'SCHEDULABLE',
                                'code': 'xx02',
                                'science_camera': {
                                    'camera_type': {
                                        'code': '2M0-FLOYDS-SCICAM',
                                        'name': '2M0-FLOYDS-SCICAM',
                                        'config_change_time': 30,
                                        'acquire_processing_time': 60,
                                        'acquire_exposure_time': 30,
                                        'front_padding': 240,
                                        'filter_change_time': 0,
                                        'fixed_overhead_per_exposure': 0.5,
                                        'default_mode': {
                                            'binning': 1,
                                            'readout': 25,
                                        },
                                        'mode_set': [
                                            {
                                                'binning': 1,
                                                'readout': 25,
                                            },
                                        ]
                                    },
                                    'filters': 'slit_1.2as,floyds_slit_default',
                                },
                                '__str__': 'tst.doma.1m0a.xx02-xx02',
                            },
                        ]
                    },
                ]
            },
        ]
    },
    {
        'code': 'non',
        'enclosure_set': [
            {
                'code': 'doma',
                'telescope_set': [
                    {
                        'code': '1m0a',
                        'lat': -32.3805542,
                        'lon': 20.8100352,
                        'horizon': 15.0,
                        'ha_limit_pos': 4.6,
                        'ha_limit_neg': -4.6,
                        'instrument_set': [
                        ]
                    },
                ]
            },
        ]
    },
]

generic_payload = {
    'proposal': 'temp',
    'group_id': 'test group',
    'operator': 'SINGLE',
    'ipp_value': 1.0,
    'observation_type': 'NORMAL',
    'requests': [{
        'target': {
            'name': 'fake target',
            'type': 'SIDEREAL',
            'dec': 20,
            'ra': 34.4,
        },
        'molecules': [{
            'type': 'EXPOSE',
            'instrument_name': '1M0-SCICAM-SBIG',
            'filter': 'air',
            'exposure_time': 100,
            'exposure_count': 1,
            'bin_x': 1,
            'bin_y': 1,
        }],
        'windows': [{
            'start': '2016-09-29T21:12:18Z',
            'end': '2016-10-29T21:12:19Z'
        }],
        'location': {
            'telescope_class': '1m0',
        },
        'constraints': {
            'max_airmass': 2.0,
            'min_lunar_distance': 30.0,
        }
    }]
}


class TestUserGetRequestApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User, is_staff=False, is_superuser=False)
        self.other_user = mixer.blend(User, is_staff=False, is_superuser=False)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.staff_user = mixer.blend(User, is_staff=True)

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_get_user_request_detail_unauthenticated(self):
        self.client.force_login(self.other_user)
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        result = self.client.get(reverse('api:user_requests-detail', args=(user_request.id,)))
        self.assertEqual(result.status_code, 404)

    def test_get_user_request_detail_authenticated(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:user_requests-detail', args=(user_request.id,)))
        self.assertContains(result, user_request.group_id)

    def test_get_user_request_list_unauthenticated(self):
        self.client.force_login(self.other_user)
        mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertEquals(result.status_code, 200)
        self.assertEquals(result.json(), [])

    def test_get_user_request_list_authenticated(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertContains(result, user_request.group_id)

    def test_get_user_request_list_staff(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup2")
        self.client.force_login(self.staff_user)
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertContains(result, user_request.group_id)


class TestUserPostRequestApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)
        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc)
                               )
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_unauthenticated(self):
        self.other_user = mixer.blend(User)
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('api:user_requests-list'), data=self.generic_payload)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_authenticated(self):
        response = self.client.post(reverse('api:user_requests-list'), data=self.generic_payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['group_id'], self.generic_payload['group_id'])

    def test_post_userrequest_wrong_proposal(self):
        bad_data = self.generic_payload.copy()
        bad_data['proposal'] = 'DoesNotExist'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_missing_data(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_molecules(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_requests(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_time_allocation_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['telescope_class'] = '2m0'
        bad_data['requests'][0]['molecules'][0]['telescope_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Time Allocation not found', str(response.content))

    def test_post_userrequest_not_enough_time_allocation_for_instrument(self):
        bad_data = self.generic_payload.copy()
        self.time_allocation_1m0.std_time_used = 99.99
        self.time_allocation_1m0.save()
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not have enough time allocated', str(response.content))

    def test_post_userrequest_bad_ipp(self):
        bad_data = self.generic_payload.copy()
        bad_data['ipp_value'] = 0.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_default_acquire_mode(self):
        bad_data = self.generic_payload.copy()
        # verify default acquire mode is 'optional' for non-floyds
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['requests'][0]['target']['acquire_mode'], 'OPTIONAL')

        # check that default acquire mode is 'on' for floyds
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['requests'][0]['target']['acquire_mode'], 'ON')

    def test_post_userrequest_single_must_have_one_request(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'].append(bad_data['requests'][0].copy())
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('must have exactly one child request', str(response.content))

    def test_post_userrequest_and_must_have_greater_than_one_request(self):
        bad_data = self.generic_payload.copy()
        bad_data['operator'] = 'AND'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('must have more than one child request', str(response.content))


class TestUserRequestIPP(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)

        semester = mixer.blend(
            Semester,
            id='2016B',
            start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )

        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.time_allocation_2m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='2m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['ipp_value'] = 1.5
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['group_id'] = 'ipp_request'

        self.generic_multi_payload = copy.deepcopy(self.generic_payload)
        self.second_request = copy.deepcopy(generic_payload['requests'][0])
        self.second_request['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        self.second_request['location']['telescope_class'] = '2m0'
        self.generic_multi_payload['requests'].append(self.second_request)

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def _build_user_request(self, ur_dict):
        response = self.client.post(reverse('api:user_requests-list'), data=ur_dict)
        self.assertEqual(response.status_code, 201)

        return UserRequest.objects.get(group_id=ur_dict['group_id'])

    def test_user_request_debit_ipp_on_creation(self):
        self.assertEqual(self.time_allocation_1m0.ipp_time_available, 5.0)

        ur = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=ur)
        self.assertEqual(response.status_code, 201)

        # verify that now that the object is saved, ipp has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)

    def test_user_request_credit_ipp_on_cancelation(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        user_request.state = 'CANCELED'
        user_request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # also verify that the child request state has changed to window_expired as well
        self.assertEqual(user_request.request_set.first().state, 'CANCELED')

    def test_user_request_credit_ipp_on_expiration(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        user_request.state = 'WINDOW_EXPIRED'
        user_request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # also verify that the child request state has changed to window_expired as well
        self.assertEqual(user_request.request_set.first().state, 'WINDOW_EXPIRED')

    def test_user_request_debit_ipp_on_creation_fail(self):
        self.assertEqual(self.time_allocation_1m0.ipp_time_available, 5.0)

        ur = self.generic_payload.copy()
        # ipp value that is too high, will be rejected
        ur['ipp_value'] = 100.0
        response = self.client.post(reverse('api:user_requests-list'), data=ur)
        self.assertEqual(response.status_code, 400)
        self.assertIn('TimeAllocationError', str(response.content))

        # verify that objects were not created by the send
        self.assertFalse(UserRequest.objects.filter(group_id='ipp_request').exists())

    def test_user_request_multi_credit_ipp_back_on_cancelation(self):
        ur = self.generic_multi_payload
        ur['operator'] = 'MANY'
        user_request = self._build_user_request(ur)
        # verify that now that both the TimeAllocation has been debited
        time_allocation_1m0 = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation_1m0.ipp_time_available, 5.0)
        time_allocation_2m0 = TimeAllocation.objects.get(pk=self.time_allocation_2m0.id)
        self.assertLess(time_allocation_2m0.ipp_time_available, 5.0)
        # now set one request to completed, then set the user request to unschedulable
        request = user_request.request_set.first()
        request.state = 'COMPLETED'
        request.save()
        user_request.state = 'WINDOW_EXPIRED'
        user_request.save()
        # now verify that time allocation 1 is still debited, but time allocation 2 has been credited back its time
        time_allocation_1m0 = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation_1m0.ipp_time_available, 5.0)
        time_allocation_2m0 = TimeAllocation.objects.get(pk=self.time_allocation_2m0.id)
        self.assertEqual(time_allocation_2m0.ipp_time_available, 5.0)


class TestRequestIPP(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)

        semester = mixer.blend(
            Semester,
            id='2016B',
            start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )

        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['ipp_value'] = 1.5
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['group_id'] = 'ipp_request'

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def _build_user_request(self, ur_dict):
        response = self.client.post(reverse('api:user_requests-list'), data=ur_dict)
        self.assertEqual(response.status_code, 201)

        return UserRequest.objects.get(group_id=ur_dict['group_id'])

    def test_request_debit_on_completion_after_expired(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        debitted_ipp_value = time_allocation.ipp_time_available
        self.assertLess(debitted_ipp_value, 5.0)
        # now change requests state to expired
        request = user_request.request_set.first()
        request.state = 'WINDOW_EXPIRED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # now set request to completed and see that ipp is debited once more
        request.state = 'COMPLETED'
        request.save()
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, debitted_ipp_value)

    @patch('valhalla.userrequests.state_changes.logger')
    def test_request_debit_on_completion_after_expired_not_enough_time(self, mock_logger):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        debitted_ipp_value = time_allocation.ipp_time_available
        self.assertLess(debitted_ipp_value, 5.0)
        # now change requests state to expired
        request = user_request.request_set.first()
        request.state = 'WINDOW_EXPIRED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # set the time allocation available to 0.01, then set to completed
        time_allocation.ipp_time_available = 0.01
        time_allocation.save()
        # now set request to completed and see that ipp debitted to 0
        request.state = 'COMPLETED'
        request.save()
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 0)
        # test that the log message was generated
        self.assertIn('Time available after debiting will be capped at 0',
                      mock_logger.warn.call_args[0][0])

    def test_request_credit_back_on_cancelation(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        # now change requests state to canceled
        request = user_request.request_set.first()
        request.state = 'CANCELED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)

    def test_request_credit_on_completion(self):
        payload = self.generic_payload.copy()
        payload['ipp_value'] = 0.5
        user_request = self._build_user_request(payload)
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # now change requests state to canceled
        request = user_request.request_set.first()
        request.state = 'COMPLETED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertGreater(time_allocation.ipp_time_available, 5.0)


class TestWindowApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_window_end_before_start(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['windows'][0]['end'] = '2016-09-28T21:12:18Z'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)


class TestSiderealTarget(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc)
                               )
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0
                                               )

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_no_ra(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['ra']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('ra', str(response.content))

    def test_post_userrequest_extra_ns_field(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['longascnode'] = 4.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        target = response.json()['requests'][0]['target']
        self.assertNotIn('longascnode', target)

    def test_post_userrequest_test_defaults(self):
        bad_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        target = response.json()['requests'][0]['target']
        self.assertEqual(target['proper_motion_ra'], 0.0)
        self.assertEqual(target['proper_motion_dec'], 0.0)
        self.assertEqual(target['parallax'], 0.0)
        self.assertEqual(target['coordinate_system'], 'ICRS')
        self.assertEqual(target['equinox'], 'J2000')
        self.assertEqual(target['epoch'], 2000.0)

    def test_post_userrequest_test_proper_motion_no_epoch(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['proper_motion_ra'] = 1.0
        bad_data['requests'][0]['target']['proper_motion_dec'] = 1.0
        # epoch defaults to 2000 so we should pass
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_test_proper_motion_with_epoch(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['proper_motion_ra'] = 1.0
        bad_data['requests'][0]['target']['proper_motion_dec'] = 1.0
        bad_data['requests'][0]['target']['epoch'] = 2001.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)


class TestNonSiderealTarget(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['requests'][0]['target'] = {
            'name': 'fake target',
            'type': 'NON_SIDEREAL',
            'scheme': 'MPC_MINOR_PLANET',
            # Non sidereal param
            'epochofel': 57660.0,
            'orbinc': 9.7942900,
            'longascnode': 122.8943400,
            'argofperih': 78.3278300,
            'perihdist': 1.0,
            'meandist': 0.7701170,
            'meananom': 165.6860400,
            'eccentricity': 0.5391962,
            'epochofperih': 57400.0,
        }

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_invalid_target_type(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['type'] = 'NOTATYPE'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_non_sidereal_target(self):
        good_data = self.generic_payload.copy()

        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_non_comet_eccentricity(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['eccentricity'] = 0.99

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('requires eccentricity to be lower', str(response.content))

    def test_post_userrequest_non_sidereal_mpc_comet(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['target']['eccentricity'] = 0.99
        good_data['requests'][0]['target']['scheme'] = 'MPC_COMET'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_non_sidereal_not_visible(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['eccentricity'] = 0.99
        bad_data['requests'][0]['target']['scheme'] = 'MPC_COMET'
        bad_data['requests'][0]['target']['perihdist'] = 5.0

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('did not fit into any visible intervals', str(response.content))

    def test_post_userrequest_non_sidereal_missing_fields(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['eccentricity']
        del bad_data['requests'][0]['target']['meandist']

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('eccentricity', str(response.content))
        self.assertIn('meandist', str(response.content))


class TestSatelliteTarget(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))

        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['requests'][0]['target'] = {
            'name': 'fake target',
            'type': 'SATELLITE',
            # satellite
            'altitude': 33.0,
            'azimuth': 2.0,
            'diff_pitch_rate': 3.0,
            'diff_roll_rate': 4.0,
            'diff_pitch_acceleration': 5.0,
            'diff_roll_acceleration': 0.99,
            'diff_epoch_rate': 22.0,
            'epoch': 2000.0,
        }

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_satellite_target(self):
        good_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_satellite_missing_fields(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['diff_epoch_rate']
        del bad_data['requests'][0]['target']['diff_pitch_acceleration']

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('diff_epoch_rate', str(response.content))
        self.assertIn('diff_pitch_acceleration', str(response.content))


class TestLocationApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))

        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_post_userrequest_all_location_info(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['site'] = 'tst'
        good_data['requests'][0]['location']['observatory'] = 'doma'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_observatory_no_site(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['observatory'] = 'doma'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_no_observatory(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['site'] = 'tst'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_observatory(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'tst'
        bad_data['requests'][0]['location']['observatory'] = 'domb'
        bad_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_site(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'bpl'
        bad_data['requests'][0]['location']['observatory'] = 'doma'
        bad_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_telescope(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'tst'
        bad_data['requests'][0]['location']['observatory'] = 'doma'
        bad_data['requests'][0]['location']['telescope'] = '1m0b'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)


class TestMoleculeApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_default_ag_mode_for_spectrograph(self):
        good_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        # check that without spectral instrument, these defaults are different
        self.assertEqual(molecule['ag_mode'], 'OPTIONAL')
        self.assertEqual(molecule['spectra_slit'], '')

        good_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        # now with spectral instrument, defaults have changed
        self.assertEqual(molecule['ag_mode'], 'ON')
        self.assertEqual(molecule['spectra_slit'], 'floyds_slit_default')

    def test_invalid_filter_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['filter'] = 'magic'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid filter', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_filter_not_necessary_for_type(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'][0]['type'] = 'ARC'
        del good_data['requests'][0]['molecules'][0]['filter']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_invalid_spectra_slit_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        del bad_data['requests'][0]['molecules'][0]['filter']
        bad_data['requests'][0]['molecules'][0]['spectra_slit'] = 'slit_really_small'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid spectra slit', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_invalid_binning_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['bin_x'] = 5
        bad_data['requests'][0]['molecules'][0]['bin_y'] = 5
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid binning', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_default_binning_for_instrument(self):
        good_data = self.generic_payload.copy()
        del good_data['requests'][0]['molecules'][0]['bin_x']
        del good_data['requests'][0]['molecules'][0]['bin_y']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        self.assertEqual(molecule['bin_x'], 2)
        self.assertEqual(molecule['bin_y'], 2)

    def test_must_set_both_binnings(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['molecules'][0]['bin_x']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Missing one of bin_x or bin_y', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_request_invalid_instrument_name(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = 'FAKE-INSTRUMENT'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid instrument name', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_request_invalid_instrument_name_for_location(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'non'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn("Invalid instrument name \\\'1M0-SCICAM-SBIG\\\' at site", str(response.content))
        self.assertEqual(response.status_code, 400)


class TestGetRequestApi(APITestCase):
    def setUp(self):
        self.configdb_patcher = patch('valhalla.common.configdb.ConfigDB._get_configdb_data')
        self.mock_configdb = self.configdb_patcher.start()
        self.mock_configdb.return_value = configdb_data

        self.time_patcher = patch('valhalla.userrequests.serializers.timezone.now')
        self.mock_now = self.time_patcher.start()
        self.mock_now.return_value = datetime(2016, 9, 1, tzinfo=timezone.utc)

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User, is_staff=False, is_superuser=False)
        self.staff_user = mixer.blend(User, is_staff=True)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal)

    def tearDown(self):
        self.configdb_patcher.stop()
        self.time_patcher.stop()

    def test_get_request_list_authenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:requests-list'))
        self.assertEquals(result.json()[0]['observation_note'], request.observation_note)

    def test_get_request_list_unauthenticated(self):
        mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        result = self.client.get(reverse('api:requests-list'))
        self.assertEquals(result.status_code, 403)

    def test_get_request_detail_authenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEquals(result.json()['observation_note'], request.observation_note)

    def test_get_request_detail_unauthenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEqual(result.status_code, 403)

    def test_get_request_list_staff(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote2')
        self.client.force_login(self.staff_user)
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEquals(result.json()['observation_note'], request.observation_note)