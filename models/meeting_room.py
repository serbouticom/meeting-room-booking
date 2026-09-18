from odoo import _, api, fields, models


class MeetingRoom(models.Model):
    _name = "meeting.room"
    _description = "Meeting Room"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    capacity = fields.Integer(default=1, help="Maximum number of people the room can seat.")
    location = fields.Char(help="Building, floor, wing, ...")
    color = fields.Integer(string="Color Index")
    equipment_ids = fields.Many2many("meeting.room.equipment", string="Equipment")
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsible",
        help="User allowed to approve or reject booking requests for this room.",
    )
    requires_approval = fields.Boolean(
        help="If enabled, submitted bookings must be approved before they are confirmed.",
    )
    description = fields.Html()
    booking_ids = fields.One2many("meeting.room.booking", "room_id", string="Bookings")
    booking_count = fields.Integer(compute="_compute_booking_count")

    _sql_constraints = [
        ("check_capacity_positive", "CHECK(capacity >= 0)", "The capacity cannot be negative."),
    ]

    @api.depends("booking_ids", "booking_ids.state")
    def _compute_booking_count(self):
        data = self.env["meeting.room.booking"]._read_group(
            [("room_id", "in", self.ids), ("state", "!=", "cancelled")],
            groupby=["room_id"],
            aggregates=["__count"],
        )
        mapped_counts = {room.id: count for room, count in data}
        for room in self:
            room.booking_count = mapped_counts.get(room.id, 0)

    def action_view_bookings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Bookings"),
            "res_model": "meeting.room.booking",
            "view_mode": "calendar,tree,form",
            "domain": [("room_id", "=", self.id)],
            "context": {"default_room_id": self.id},
        }
