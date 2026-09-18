{
    "name": "Meeting Room Booking",
    "version": "17.0.1.0.0",
    "summary": "Book meeting rooms with conflict detection, approval workflow and recurring bookings.",
    "description": """
Meeting Room Booking
====================

Manage the shared calendar of your meeting rooms:

* Conflict detection - overlapping bookings for the same room are refused.
* Approval workflow - Draft / To Approve / Confirmed / Rejected / Cancelled,
  with per-room approval routed to a responsible user.
* Capacity & equipment - seats and equipment per room, capacity warning.
* Recurring bookings - repeat every N days / weeks / months until a date.

See the full description with screenshots on the app page.
""",
    "category": "Human Resources",
    "author": "Serbouti Med Amine",
    "maintainer": "Serbouti Med Amine",
    "website": "https://www.serbouti.dev",
    "support": "serbouti.com@gmail.com",
    "license": "OPL-1",
    "price": 13.00,
    "currency": "EUR",
    "images": [
        "static/description/banner.png",
    ],
    "depends": [
        "mail",
    ],
    "data": [
        # - Security -----------------------------------------------------------
        "security/meeting_room_booking_security.xml",
        "security/ir.model.access.csv",
        # - Data ---------------------------------------------------------------
        "data/meeting_room_booking_data.xml",
        # - Views ------------------------------------------------------------
        "views/meeting_room_equipment_views.xml",
        "views/meeting_room_views.xml",
        "views/meeting_room_booking_views.xml",
        "views/meeting_room_booking_menus.xml",
    ],
    "demo": [
        "demo/meeting_room_demo.xml",
    ],
    "application": True,
    "installable": True,
}
