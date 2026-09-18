from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


BLOCKING_STATES = ("to_approve", "confirmed")
MAX_RECURRENCE_OCCURRENCES = 200


class MeetingRoomBooking(models.Model):
    _name = "meeting.room.booking"
    _description = "Meeting Room Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start desc, id desc"

    name = fields.Char(string="Subject", required=True, tracking=True)
    reference = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
    )
    room_id = fields.Many2one(
        "meeting.room",
        string="Meeting Room",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(related="room_id.company_id", store=True, index=True)
    user_id = fields.Many2one(
        "res.users",
        string="Organizer",
        required=True,
        tracking=True,
        default=lambda self: self.env.user,
    )
    partner_ids = fields.Many2many("res.partner", string="Attendees")
    start = fields.Datetime(required=True, tracking=True, default=lambda self: fields.Datetime.now())
    stop = fields.Datetime(
        string="End",
        required=True,
        tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=1),
    )
    duration = fields.Float(
        compute="_compute_duration",
        inverse="_inverse_duration",
        store=True,
        readonly=False,
        help="Duration in hours.",
    )
    attendees_count = fields.Integer(string="Expected Attendees", default=1)
    capacity = fields.Integer(related="room_id.capacity")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("to_approve", "To Approve"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    description = fields.Html()
    color = fields.Integer(related="room_id.color")
    can_approve = fields.Boolean(compute="_compute_can_approve")

    # -- Recurrence (applied on creation) ------------------------------------
    recurrency = fields.Boolean(string="Recurrent")
    recurrence_id = fields.Many2one(
        "meeting.room.booking",
        string="Recurrence Root",
        copy=False,
        index=True,
        ondelete="set null",
    )
    recurrence_booking_ids = fields.One2many(
        "meeting.room.booking",
        "recurrence_id",
        string="Occurrences",
    )
    repeat_interval = fields.Integer(string="Repeat Every", default=1)
    repeat_unit = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
        ],
        string="Repeat Unit",
        default="weeks",
    )
    repeat_until = fields.Date(string="Repeat Until")

    _sql_constraints = [
        (
            "check_start_before_stop",
            "CHECK(start < stop)",
            "The end date must be later than the start date.",
        ),
        (
            "check_attendees_count",
            "CHECK(attendees_count >= 0)",
            "The number of attendees cannot be negative.",
        ),
        (
            "check_repeat_interval",
            "CHECK(repeat_interval >= 1)",
            "The repeat interval must be at least 1.",
        ),
    ]

    # -- Compute / onchange -------------------------------------------------

    @api.depends("start", "stop")
    def _compute_duration(self):
        for booking in self:
            if booking.start and booking.stop and booking.stop > booking.start:
                booking.duration = (booking.stop - booking.start).total_seconds() / 3600.0
            else:
                booking.duration = 0.0

    def _inverse_duration(self):
        for booking in self:
            if booking.start and booking.duration:
                booking.stop = booking.start + timedelta(hours=booking.duration)

    @api.depends("room_id.responsible_id")
    @api.depends_context("uid")
    def _compute_can_approve(self):
        is_manager = self.env.user.has_group("meeting_room_booking.group_meeting_room_manager")
        for booking in self:
            booking.can_approve = is_manager or booking.room_id.responsible_id == self.env.user

    @api.depends("reference", "name")
    def _compute_display_name(self):
        for booking in self:
            if booking.name:
                booking.display_name = f"{booking.reference} - {booking.name}"
            else:
                booking.display_name = booking.reference

    @api.onchange("attendees_count", "room_id")
    def _onchange_attendees_count(self):
        if self.room_id.capacity and self.attendees_count > self.room_id.capacity:
            return {
                "warning": {
                    "title": _("Capacity exceeded"),
                    "message": _(
                        "You expect %(count)s attendees but %(room)s only seats %(capacity)s.",
                        count=self.attendees_count,
                        room=self.room_id.display_name,
                        capacity=self.room_id.capacity,
                    ),
                },
            }
        return None

    # -- Constraints ------------------------------------------------------

    @api.constrains("start", "stop", "room_id", "state")
    def _check_booking_conflict(self):
        for booking in self:
            if booking.state not in BLOCKING_STATES:
                continue
            conflict = self.search(
                [
                    ("id", "!=", booking.id),
                    ("room_id", "=", booking.room_id.id),
                    ("state", "in", BLOCKING_STATES),
                    ("start", "<", booking.stop),
                    ("stop", ">", booking.start),
                ],
                limit=1,
            )
            if conflict:
                raise ValidationError(
                    _(
                        "%(room)s is already booked from %(start)s to %(stop)s (%(reference)s).",
                        room=booking.room_id.display_name,
                        start=fields.Datetime.to_string(conflict.start),
                        stop=fields.Datetime.to_string(conflict.stop),
                        reference=conflict.reference,
                    )
                )

    # -- CRUD ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference") or vals["reference"] == _("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("meeting.room.booking") or _("New")
        bookings = super().create(vals_list)
        for booking in bookings:
            if booking.recurrency and not booking.recurrence_id:
                booking._generate_recurrence()
        return bookings

    # -- Recurrence ----------------------------------------------------

    def _get_recurrence_step(self):
        self.ensure_one()
        return {
            "days": relativedelta(days=self.repeat_interval),
            "weeks": relativedelta(weeks=self.repeat_interval),
            "months": relativedelta(months=self.repeat_interval),
        }[self.repeat_unit]

    def _generate_recurrence(self):
        self.ensure_one()
        if not self.repeat_until or self.repeat_interval < 1:
            return
        self.recurrence_id = self.id
        step = self._get_recurrence_step()
        occurrences = []
        occurrence_start = self.start + step
        occurrence_stop = self.stop + step
        while (
            occurrence_start.date() <= self.repeat_until
            and len(occurrences) < MAX_RECURRENCE_OCCURRENCES
        ):
            occurrences.append(
                {
                    "name": self.name,
                    "room_id": self.room_id.id,
                    "user_id": self.user_id.id,
                    "partner_ids": [fields.Command.set(self.partner_ids.ids)],
                    "start": occurrence_start,
                    "stop": occurrence_stop,
                    "attendees_count": self.attendees_count,
                    "description": self.description,
                    "state": self.state,
                    "recurrency": False,
                    "recurrence_id": self.id,
                }
            )
            occurrence_start += step
            occurrence_stop += step
        if occurrences:
            self.create(occurrences)

    # -- Workflow ----------------------------------------------------

    def action_submit(self):
        for booking in self:
            if booking.state not in ("draft", "rejected"):
                continue
            if booking.room_id.requires_approval:
                booking.state = "to_approve"
                booking._notify_approver()
            else:
                booking.state = "confirmed"

    def action_approve(self):
        self._check_approver()
        self.filtered(lambda b: b.state == "to_approve").write({"state": "confirmed"})

    def action_reject(self):
        self._check_approver()
        self.filtered(lambda b: b.state == "to_approve").write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def _check_approver(self):
        if self.env.user.has_group("meeting_room_booking.group_meeting_room_manager"):
            return
        for booking in self:
            responsible = booking.room_id.responsible_id
            if not responsible:
                raise UserError(_("Only a Meeting Room Manager can approve bookings for %s.", booking.room_id.display_name))
            if responsible != self.env.user:
                raise UserError(
                    _(
                        "Only %(responsible)s or a Meeting Room Manager can approve bookings for %(room)s.",
                        responsible=responsible.display_name,
                        room=booking.room_id.display_name,
                    )
                )

    def _notify_approver(self):
        for booking in self:
            approver = booking.room_id.responsible_id
            if not approver:
                continue
            booking.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=_("Meeting room booking to approve"),
                note=_(
                    "%(user)s requested %(room)s from %(start)s to %(stop)s.",
                    user=booking.user_id.display_name,
                    room=booking.room_id.display_name,
                    start=fields.Datetime.to_string(booking.start),
                    stop=fields.Datetime.to_string(booking.stop),
                ),
                user_id=approver.id,
            )
