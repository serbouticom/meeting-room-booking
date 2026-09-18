from datetime import datetime, timedelta

import psycopg2

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


class TestMeetingRoomBooking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                mail_create_nolog=True,
                mail_notrack=True,
                no_reset_password=True,
            )
        )
        cls.room = cls.env["meeting.room"].create({"name": "Test Room", "capacity": 4})
        cls.room_approval = cls.env["meeting.room"].create(
            {
                "name": "Approval Room",
                "capacity": 8,
                "requires_approval": True,
                "responsible_id": cls.env.user.id,
            }
        )
        cls.t0 = datetime(2030, 1, 7, 9, 0, 0)

    def _booking(self, **kwargs):
        vals = {
            "name": "Weekly sync",
            "room_id": self.room.id,
            "start": self.t0,
            "stop": self.t0 + timedelta(hours=1),
        }
        vals.update(kwargs)
        return self.env["meeting.room.booking"].create(vals)

    def test_reference_from_sequence(self):
        booking = self._booking()
        self.assertNotEqual(booking.reference, "New")
        self.assertTrue(booking.reference.startswith("MRB/"))

    def test_duration_is_computed_in_hours(self):
        booking = self._booking(stop=self.t0 + timedelta(hours=2, minutes=30))
        self.assertEqual(booking.duration, 2.5)

    def test_submit_without_approval_confirms(self):
        booking = self._booking()
        booking.action_submit()
        self.assertEqual(booking.state, "confirmed")

    def test_submit_with_approval_needs_approve(self):
        booking = self._booking(room_id=self.room_approval.id)
        booking.action_submit()
        self.assertEqual(booking.state, "to_approve")
        booking.action_approve()
        self.assertEqual(booking.state, "confirmed")

    def test_overlapping_booking_is_refused(self):
        first = self._booking()
        first.action_submit()
        self.assertEqual(first.state, "confirmed")
        overlap = self._booking(
            start=self.t0 + timedelta(minutes=30),
            stop=self.t0 + timedelta(minutes=90),
        )
        with self.assertRaises(ValidationError):
            overlap.action_submit()

    def test_adjacent_booking_is_allowed(self):
        first = self._booking()
        first.action_submit()
        following = self._booking(
            start=self.t0 + timedelta(hours=1),
            stop=self.t0 + timedelta(hours=2),
        )
        following.action_submit()
        self.assertEqual(following.state, "confirmed")

    def test_draft_bookings_do_not_block(self):
        self._booking()
        other = self._booking()
        self.assertEqual(other.state, "draft")

    def test_recurrence_generates_linked_occurrences(self):
        booking = self._booking(
            recurrency=True,
            repeat_interval=1,
            repeat_unit="weeks",
            repeat_until=(self.t0 + timedelta(days=21)).date(),
        )
        occurrences = booking.recurrence_booking_ids
        self.assertEqual(len(occurrences), 3)
        self.assertEqual(booking.recurrence_id, booking)
        self.assertEqual(
            occurrences.sorted("start").mapped("start"),
            [self.t0 + timedelta(weeks=n) for n in (1, 2, 3)],
        )
        self.assertFalse(any(occurrences.mapped("recurrency")))

    def test_capacity_warning(self):
        booking = self.env["meeting.room.booking"].new(
            {"room_id": self.room.id, "attendees_count": 10}
        )
        warning = booking._onchange_attendees_count()
        self.assertTrue(warning and "warning" in warning)

    def test_non_manager_cannot_approve_foreign_room(self):
        booking = self._booking(room_id=self.room_approval.id)
        booking.action_submit()
        user = new_test_user(
            self.env,
            login="mrb_plain_user",
            groups="meeting_room_booking.group_meeting_room_user",
        )
        with self.assertRaises(UserError):
            booking.with_user(user).action_approve()

    @mute_logger("odoo.sql_db")
    def test_start_after_stop_is_refused(self):
        with self.assertRaises(psycopg2.IntegrityError), self.env.cr.savepoint():
            self._booking(stop=self.t0 - timedelta(hours=1))
