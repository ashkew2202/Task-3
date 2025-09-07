import django_tables2 as tables
from .models import TeamPlayer
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SportPayment

class TeamPlayerTable(tables.Table):
    sport = tables.Column(accessor="event.sport.name", verbose_name="Sport")
    category = tables.Column(accessor="event.sport.gender", verbose_name="Category")
    captain_name = tables.Column(accessor="team_player.team.captain.name", verbose_name="Captain Name")
    college = tables.Column(accessor="team_player.team.college.name", verbose_name="College")
    status = tables.Column(accessor="team_player.status", verbose_name="Status")
    payment = tables.Column(empty_values=(), verbose_name="Payment Status", orderable=False)

    def render_payment(self, record: TeamPlayer):

        team_player = record.get("team_player")
        team_player_id = team_player.pk
        if not team_player_id:
            return ""

        # Try to find an existing payment for this team player
        payment_id = (
            SportPayment.objects
            .filter(team_player_id=team_player_id)
            .values_list("static_id", flat=True)
            .first()
        )

        if payment_id:
            url = reverse("print_receipt", args=[team_player_id])
            return mark_safe(
                f'<a class="btn btn-sm btn-outline-secondary" href="{url}" target="_blank">Print Receipt</a>'
            )
        else:
            url = reverse("make_sport_payment", args=[team_player_id])
            return mark_safe(
                f'<a class="btn btn-sm btn-primary" href="{url}">Make Payment</a>'
            )


    class Meta:
        # use a custom template that wraps the table in a Bootstrap "card" and applies dark styling
        template_name = "django_tables2/bootstrap4.html"
        # add Bootstrap dark/card-friendly classes to the table element
        attrs = {
            "class": "table table-sm table-dark table-hover table-borderless text-light",
            "thead": {"class": "thead-dark"},
            "th": {"class": "align-middle text-uppercase small font-weight-bold"},
        }
        row_attrs = {
            "class": "align-middle",
        }
        sequence = ("sport", "category", "captain_name", "college", "status")