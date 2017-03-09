from unittest.case import TestCase
from mixer.main import mixer
from mixer.backend.django import mixer as dmixer
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import patch

from valhalla.userrequests.models import Request, UserRequest, Window
from valhalla.userrequests.state_changes import (
    get_request_state_from_pond_blocks, update_request_state, aggregate_request_states,
    update_request_states_from_pond_blocks
)


class PondMolecule:
    complete = bool
    failed = bool
    request_number = int
    tracking_number = int

    def _to_dict(self):
        return {'complete': self.complete, 'failed': self.failed, 'request_number': self.request_number,
                'tracking_number': self.tracking_number}


class PondBlock:
    start = datetime
    end = datetime
    canceled = bool
    molecules = list

    def _to_dict(self):
        return {'start': self.start.isoformat(), 'end': self.end.isoformat(), 'canceled': self.canceled,
                'molecules': [m._to_dict() for m in self.molecules]}


class TestStateFromPonBlocks(TestCase):
    def test_pond_blocks_all_molecules_complete(self):
        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=True)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now-timedelta(minutes=20))._to_dict()]

        initial_state = 'INITIAL'

        pond_state = get_request_state_from_pond_blocks(initial_state, pond_blocks)
        self.assertEqual(pond_state, 'COMPLETED')

    def test_pond_blocks_not_complete_or_failed_use_initial(self):
        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now+timedelta(minutes=20))._to_dict()]

        initial_state = 'INITIAL'
        pond_state = get_request_state_from_pond_blocks(initial_state, pond_blocks)
        self.assertEqual(pond_state, initial_state)

    def test_pond_blocks_in_past_failed(self):
        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now-timedelta(minutes=20))._to_dict()]

        initial_state = 'INITIAL'
        pond_state = get_request_state_from_pond_blocks(initial_state, pond_blocks)
        self.assertEqual(pond_state, 'FAILED')

    def test_pond_blocks_failed(self):
        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        molecules.append(mixer.blend(PondMolecule, compelte=False, failed=True))
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now+timedelta(minutes=20))._to_dict()]

        initial_state = 'INITIAL'
        pond_state = get_request_state_from_pond_blocks(initial_state, pond_blocks)
        self.assertEqual(pond_state, 'FAILED')

    def test_pond_blocks_in_future_use_initial(self):
        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        molecules.append(mixer.blend(PondMolecule, compelte=False, failed=True))
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now + timedelta(minutes=30),
                                   end=now+timedelta(minutes=40))._to_dict()]

        initial_state = 'INITIAL'
        pond_state = get_request_state_from_pond_blocks(initial_state, pond_blocks)
        self.assertEqual(pond_state, initial_state)


class TestRequestState(TestCase):
    def test_request_state_complete(self):
        request = dmixer.blend(Request, state='COMPLETED')

        molecules = mixer.cycle(4).blend(PondMolecule)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules)._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)
        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'COMPLETED')

    def test_request_state_pond_state_complete(self):
        request = dmixer.blend(Request, state='PENDING')

        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        complete_molecules = mixer.cycle(4).blend(PondMolecule, complete=True, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules)._to_dict(),
                       mixer.blend(PondBlock, molecules=complete_molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)

        request.refresh_from_db()
        self.assertTrue(state_changed)
        self.assertEqual(request.state, 'COMPLETED')

    def test_request_state_pond_state_initial_state_expired(self):
        request = dmixer.blend(Request, state='WINDOW_EXPIRED')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)

        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'WINDOW_EXPIRED')

    def test_request_state_pond_state_initial_state_canceled(self):
        request = dmixer.blend(Request, state='CANCELED')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)

        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'CANCELED')

    def test_request_state_pond_state_initial_state_pending(self):
        request = dmixer.blend(Request, state='PENDING')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, canceled=False, start=now - timedelta(minutes=30),
                                   end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, False)

        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'PENDING')

    def test_request_state_pond_state_initial_state_pending_ur_expired(self):
        request = dmixer.blend(Request, state='PENDING')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)

        request.refresh_from_db()
        self.assertTrue(state_changed)
        self.assertEqual(request.state, 'WINDOW_EXPIRED')

    def test_request_state_pond_state_failed_initial_state_expired(self):
        request = dmixer.blend(Request, state='WINDOW_EXPIRED')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=True)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, True)

        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'WINDOW_EXPIRED')

    def test_request_state_pond_state_failed_initial_state_canceled(self):
        request = dmixer.blend(Request, state='CANCELED')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=True)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, False)

        request.refresh_from_db()
        self.assertFalse(state_changed)
        self.assertEqual(request.state, 'CANCELED')

    def test_request_state_pond_state_failed(self):
        request = dmixer.blend(Request, state='PENDING')

        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=True)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now + timedelta(minutes=30))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules)._to_dict()]

        state_changed = update_request_state(request, pond_blocks, False)

        request.refresh_from_db()
        self.assertTrue(state_changed)
        self.assertEqual(request.state, 'PENDING')

    def test_request_state_pond_state_failed_2(self):
        request = dmixer.blend(Request, state='PENDING')


        now = timezone.now()
        molecules = mixer.cycle(4).blend(PondMolecule, complete=False, failed=False)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict(),
                       mixer.blend(PondBlock, molecules=molecules, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        state_changed = update_request_state(request, pond_blocks, False)
        request.refresh_from_db()
        self.assertTrue(state_changed)
        self.assertEqual(request.state, 'PENDING')


class TestAggregateRequestStates(TestCase):
    def test_many_all_complete(self):
        request_states = ['COMPLETED', 'COMPLETED', 'COMPLETED']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'COMPLETED')

    def test_many_any_pending(self):
        request_states = ['COMPLETED', 'CANCELED', 'PENDING']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'PENDING')

    def test_many_expired_and_complete(self):
        request_states = ['WINDOW_EXPIRED', 'COMPLETED', 'WINDOW_EXPIRED']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'COMPLETED')

    def test_many_canceled_and_complete(self):
        request_states = ['CANCELED', 'COMPLETED', 'CANCELED']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'COMPLETED')

    def test_many_all_canceled(self):
        request_states = ['CANCELED', 'CANCELED', 'CANCELED']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'CANCELED')

    def test_many_all_expired(self):
        request_states = ['WINDOW_EXPIRED', 'WINDOW_EXPIRED', 'WINDOW_EXPIRED']
        ur = dmixer.blend(UserRequest, operator='MANY')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'WINDOW_EXPIRED')

    def test_oneof_any_completed(self):
        request_states = ['WINDOW_EXPIRED', 'COMPLETED', 'PENDING']
        ur = dmixer.blend(UserRequest, operator='ONEOF')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'COMPLETED')

    def test_oneof_pending_and_expired(self):
        request_states = ['WINDOW_EXPIRED', 'PENDING', 'PENDING']
        ur = dmixer.blend(UserRequest, operator='ONEOF')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'PENDING')

    def test_oneof_all_expired(self):
        request_states = ['WINDOW_EXPIRED', 'WINDOW_EXPIRED', 'WINDOW_EXPIRED']
        ur = dmixer.blend(UserRequest, operator='ONEOF')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'WINDOW_EXPIRED')

    def test_oneof_all_canceled(self):
        request_states = ['CANCELED', 'CANCELED', 'CANCELED']
        ur = dmixer.blend(UserRequest, operator='ONEOF')
        dmixer.cycle(3).blend(Request, state=(state for state in request_states), user_request=ur)

        aggregate_state = aggregate_request_states(ur)

        self.assertEqual(aggregate_state, 'CANCELED')


@patch('valhalla.userrequests.state_changes.modify_ipp_time_from_requests')
class TestUpdateRequestStates(TestCase):
    def setUp(self):
        self.ur = dmixer.blend(UserRequest, operator='MANY', state='PENDING')
        self.requests = dmixer.cycle(3).blend(Request, user_request=self.ur, state='PENDING')

    def test_many_requests_expire_after_last_window(self, modify_mock):
        now = timezone.now()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now-timedelta(days=1))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[0].id, tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[1].id, tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]), start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        for req in self.requests:
            req.refresh_from_db()
            self.assertEqual(req.state, 'WINDOW_EXPIRED')
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'WINDOW_EXPIRED')

    def test_many_requests_complete_and_expired(self, modify_mock):
        now = timezone.now()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now-timedelta(days=1))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[0].id, tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[1].id, tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]), start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['COMPLETED', 'WINDOW_EXPIRED', 'WINDOW_EXPIRED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_many_requests_complete_and_failed(self, modify_mock):
        now = timezone.now()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now+timedelta(days=1))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[0].id, tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[1].id, tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]), start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['COMPLETED', 'COMPLETED', 'PENDING']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'PENDING')

    def test_many_requests_window_expired_and_failed(self, modify_mock):
        now = timezone.now()
        self.requests[0].state = 'WINDOW_EXPIRED'
        self.requests[0].save()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now+timedelta(days=1))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[0].id, tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[1].id, tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]), start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['WINDOW_EXPIRED', 'PENDING', 'PENDING']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'PENDING')

    def test_many_requests_complete_and_complete(self, modify_mock):
        now = timezone.now()
        self.requests[0].state = 'COMPLETED'
        self.requests[0].save()
        self.requests[1].state = 'COMPLETED'
        self.requests[1].save()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now+timedelta(days=1))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['COMPLETED', 'COMPLETED', 'COMPLETED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_many_requests_complete_and_window_expired(self, modify_mock):
        now = timezone.now()
        self.requests[0].state = 'COMPLETED'
        self.requests[0].save()
        self.requests[1].state = 'COMPLETED'
        self.requests[1].save()
        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now-timedelta(days=1))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['COMPLETED', 'COMPLETED', 'WINDOW_EXPIRED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_many_requests_window_expired_to_completed(self, modify_mock):
        now = timezone.now()
        for req in self.requests:
            req.state = 'WINDOW_EXPIRED'
            req.save()

        self.ur.state = 'WINDOW_EXPIRED'
        self.ur.save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now-timedelta(days=1))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['WINDOW_EXPIRED', 'WINDOW_EXPIRED', 'COMPLETED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_many_requests_canceled_to_completed(self, modify_mock):
        now = timezone.now()
        for req in self.requests:
            req.state = 'CANCELED'
            req.save()

        self.ur.state = 'CANCELED'
        self.ur.save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now-timedelta(days=2), end=now-timedelta(days=1))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['CANCELED', 'CANCELED', 'COMPLETED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_oneof_requests_complete_one_and_done(self, modify_mock):
        now = timezone.now()
        self.ur.operator = 'ONEOF'
        self.ur.save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                              end=now + timedelta(days=1))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[0].id,
                                          tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[1].id,
                                          tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[2].id,
                                          tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]),
                                           start=now - timedelta(minutes=30), end=now + timedelta(minutes=20),
                                           canceled=False)
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['COMPLETED', 'PENDING', 'PENDING']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_oneof_requests_fail_and_window_expired(self, modify_mock):
        now = timezone.now()
        self.ur.operator = 'ONEOF'
        self.ur.save()
        self.requests[0].state = 'WINDOW_EXPIRED'
        self.requests[0].save()
        self.requests[1].state = 'WINDOW_EXPIRED'
        self.requests[1].save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                              end=(e for e in [now - timedelta(days=1), now - timedelta(days=1), now + timedelta(days=1)]))
        molecules1 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[0].id,
                                          tracking_number=self.ur.id)
        molecules2 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[1].id,
                                          tracking_number=self.ur.id)
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=False, failed=True, request_number=self.requests[2].id,
                                          tracking_number=self.ur.id)
        pond_blocks = mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]),
                                           start=now - timedelta(minutes=30), end=now - timedelta(minutes=20),
                                           canceled=False)
        pond_blocks = [pb._to_dict() for pb in pond_blocks]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['WINDOW_EXPIRED', 'WINDOW_EXPIRED', 'PENDING']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'PENDING')

    def test_oneof_requests_window_expired_to_completed(self, modify_mock):
        now = timezone.now()
        self.ur.operator = 'ONEOF'
        self.ur.save()
        for req in self.requests:
            req.state = 'WINDOW_EXPIRED'
            req.save()

        self.ur.state = 'WINDOW_EXPIRED'
        self.ur.save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                              end=(e for e in [now - timedelta(days=1), now - timedelta(days=1), now + timedelta(days=1)]))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['WINDOW_EXPIRED', 'WINDOW_EXPIRED', 'COMPLETED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    def test_oneof_requests_canceled_to_completed(self, modify_mock):
        now = timezone.now()
        self.ur.operator = 'ONEOF'
        self.ur.save()
        for req in self.requests:
            req.state = 'CANCELED'
            req.save()

        self.ur.state = 'CANCELED'
        self.ur.save()

        dmixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                              end=(e for e in [now - timedelta(days=1), now - timedelta(days=1), now + timedelta(days=1)]))
        molecules3 = mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[2].id, tracking_number=self.ur.id)
        pond_blocks = [mixer.blend(PondBlock, molecules=molecules3, start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))._to_dict()]

        update_request_states_from_pond_blocks(pond_blocks)

        request_states = ['CANCELED', 'CANCELED', 'COMPLETED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')
