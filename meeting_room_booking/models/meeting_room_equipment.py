from odoo import fields, models


class MeetingRoomEquipment(models.Model):
    _name = "meeting.room.equipment"
    _description = "Meeting Room Equipment"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    room_ids = fields.Many2many("meeting.room", string="Meeting Rooms")
