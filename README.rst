===================
Meeting Room Booking
===================

Book meeting rooms from a shared calendar with:

* **Conflict detection** – two overlapping bookings for the same room are rejected
  (only ``To Approve`` and ``Confirmed`` bookings block a slot; drafts do not).
* **Approval workflow** – ``Draft`` → ``To Approve`` → ``Confirmed`` (or
  ``Rejected`` / ``Cancelled``). Rooms flagged *Requires Approval* route requests
  to their *Responsible* user through an activity; other rooms confirm on submit.
* **Capacity & equipment** – each room has a seat capacity and a list of
  equipment (projector, video conference, ...). A warning is shown when the
  expected attendee count exceeds the room capacity.
* **Recurring bookings** – repeat every N days / weeks / months until a given
  date. Occurrences are generated on creation and linked to the root booking.

Configuration
=============

*Meeting Rooms ‣ Configuration ‣ Meeting Rooms* / *Equipment* (Manager only).

Security
========

* **User** – reads every booking (to see availability), creates and manages their
  own bookings, approves/rejects bookings for rooms they are responsible for.
* **Manager** – full access to rooms, equipment and every booking.
