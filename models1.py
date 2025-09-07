from django.db import models
import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


GENDER_CHOICES = [("Male", "Male"), ("Female", "Female")]

SPORTS_GENDER_CHOICES = [("Male", "Male"), ("Female", "Female"), ("Mixed", "Mixed")]

PLAYER_STATUS_CHOICES = [
    ("pcr_confirmed", "PCr Confirmed"),
    ("pcr_unconfirmed", "PCr Unconfirmed"),
]

TEAM_PLAYER_STATUS_CHOICES = [
    ("pcr_approved", "PCr Approved"),
    ("pcr_unapproved", "PCr Unapproved"),
]

SPORTS_NAMES = [
    ("SKATING", "SKATING"),
    ("ULTIMATE FRISBEE", "ULTIMATE FRISBEE"),
    ("CRICKET", "CRICKET"),
    ("FOOTBALL", "FOOTBALL"),
    ("SNOOKER", "SNOOKER"),
    ("ATHLETICS", "ATHLETICS"),
    ("BADMINTON", "BADMINTON"),
    ("HOCKEY", "HOCKEY"),
    ("SQUASH", "SQUASH"),
    ("TENNIS", "TENNIS"),
    ("TABLE TENNIS", "TABLE TENNIS"),
    ("VOLLEYBALL", "VOLLEYBALL"),
    ("CHESS", "CHESS"),
    ("CARROM", "CARROM"),
    ("POWER LIFTING", "POWER LIFTING"),
    ("8BALL", "8BALL"),
    ("HANDBALL", "HANDBALL"),
    ("SWIMMING", "SWIMMING"),
    ("BASKETBALL", "BASKETBALL"),
    ("TAEKWONDO", "TAWKWONDO"),
]

ARRIVAL_ROUTE_CHOICES = [
    ("LHU -> PLI", "LHU -> PLI"),
    ("IGI -> PLI", "IGI -> PLI"),
]


def college_logo_path(instance, filename):
    return (
        f"college_logos/{str(uuid.uuid4()).replace('-', '')}.{filename.split('.')[-1]}"
    )


def sports_image_path(instance, filename):
    return (
        f"sports_images/{str(uuid.uuid4()).replace('-', '')}.{filename.split('.')[-1]}"
    )


def sports_icon_path(instance, filename):
    return (
        f"sports_icons/{str(uuid.uuid4()).replace('-', '')}.{filename.split('.')[-1]}"
    )


def events_icon_path(instance, filename):
    return (
        f"subevent_icons/{str(uuid.uuid4()).replace('-', '')}.{filename.split('.')[-1]}"
    )


class NonDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class NonDeletedAndPlayingManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False, is_playing=True)


class Sport(models.Model):
    """
    Represents a Sport (mainly kept for metadata purposes for listings in the website)
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    name = models.CharField(max_length=30, blank=False, null=False)
    gender = models.CharField(choices=SPORTS_GENDER_CHOICES, max_length=10)
    is_active = models.BooleanField(default=True)
    rulebook_link = models.URLField(null=True, blank=True)
    max_players = models.PositiveIntegerField(default=1)
    min_players = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to=sports_image_path, null=True, blank=True)
    app_icon = models.ImageField(upload_to=sports_icon_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} {self.gender}"

    class Meta:
        verbose_name = "Sport"
        verbose_name_plural = "Sports"
        indexes = [models.Index(fields=["is_deleted"])]
        unique_together = (("name", "gender"),)


class Event(models.Model):
    """
    Represents an event for a specific Sport
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    name = models.CharField(max_length=30, blank=True, null=False)
    sport = models.ForeignKey(
        "firewallz.Sport", on_delete=models.CASCADE, related_name="events"
    )
    is_two_team_event = models.BooleanField(default=False)
    is_playerwise = models.BooleanField(default=False)
    icon = models.ImageField(upload_to=events_icon_path, null=True, blank=True)

    def __str__(self):
        if not self.name:
            return f"{self.sport}"

        return f"{self.sport} - {self.name}"

    class Meta:
        unique_together = (("sport", "name"),)


class College(models.Model):
    """
    Represents a college in the reg system
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    name = models.CharField(max_length=100, unique=True, blank=False, null=False)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=50, blank=True, null=False)
    state = models.CharField(max_length=50, blank=True, null=False)
    representative = models.OneToOneField(
        "firewallz.Player",
        related_name="college_rep",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    pcr_notes = models.TextField(blank=True, null=True)
    logo = models.ImageField(
        upload_to=college_logo_path, verbose_name="College Logo", null=True, blank=True
    )
    letter_code = models.CharField(max_length=4, unique=True, null=True, blank=True)
    is_captains_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    is_deleted = models.BooleanField(default=False)
    is_form_visible = models.BooleanField(default=False)

    @property
    def coaches(self):
        return Player.objects.filter(college=self, is_coach=True)

    class Meta:
        verbose_name = "College"
        verbose_name_plural = "Colleges"
        indexes = [models.Index(fields=["is_deleted"])]

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        if self.representative and self != self.representative.college:
            raise ValidationError("Representative must belong to the college.")
        if self.representative and self.representative.is_coach:
            raise ValidationError("The college representative cannot be a coach.")
        if (
            self.representative
            and Team.objects.filter(captain=self.representative).exists()
        ):
            raise ValidationError("The college representative is already a captain.")
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Player(models.Model):
    """
    Represents a outstie player in the reg system
    (independent of UserProfile)
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    auth_user = models.OneToOneField(
        get_user_model(),
        related_name="player",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    name = models.CharField(verbose_name="Name")
    email = models.EmailField(verbose_name="Email", unique=True)
    phone_number = models.PositiveBigIntegerField(
        verbose_name="Phone Number",
        help_text="10 digit phone number without country code",
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)],
        null=False,
        blank=False,
    )
    photo = models.URLField("Photo URL", blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    college = models.ForeignKey(
        "firewallz.College", related_name="players", on_delete=models.CASCADE
    )
    status = models.CharField(choices=PLAYER_STATUS_CHOICES)
    is_coach = models.BooleanField(
        verbose_name="Is Coach?", default=False, help_text="Is the player a coach?"
    )
    verified_by_firewallz = models.BooleanField(
        verbose_name="Is Verified By Firewallz?", default=False
    )
    verified_by_controls = models.BooleanField(
        verbose_name="Is Verified By Controls?", default=False
    )
    is_onspot = models.BooleanField(default=False)
    pcr_discount = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(500)]
    )
    sports_if_coach = models.TextField(default=None, blank=True, null=True)
    num_emails_sent = models.IntegerField("Number of Payment Emails Sent", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    is_deleted = models.BooleanField(default=False)
    arrival_time = models.DateTimeField(null=True, blank=True, default=None)
    arrival_route = models.CharField(
        choices=ARRIVAL_ROUTE_CHOICES, blank=True, null=True, max_length=200
    )

    class Meta:
        verbose_name = "Player"
        verbose_name_plural = "Players"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["college"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.email} ({self.college.name})"

    @property
    def is_college_rep(self):
        return self.college.representative == self if self.college else False

    def clean(self):
        if self.status == "pcr_unconfirmed" and (
            self.verified_by_controls or self.verified_by_firewallz
        ):
            raise ValidationError(
                "Cannot be verified by controls or firewallz without being confirmed."
            )
        if self.verified_by_controls and not self.verified_by_firewallz:
            raise ValidationError(
                "Cannot be verified by controls without being verified by firewallz"
            )
        count = 0
        for team_player in TeamPlayer.objects.filter(player=self):
            count += team_player.events.all().count()  # TODO: OPTIMIZE
        if count > 5:
            raise ValidationError("Cannot register for more than 5 events.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Team(models.Model):
    """
    Represents a team for a specific sport, gender and college.
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    team_code = models.CharField(
        max_length=255,
        unique=True,
        help_text="A human-readable identifier for the team",
    )
    college = models.ForeignKey(
        "firewallz.College", on_delete=models.CASCADE, related_name="teams"
    )
    sport = models.ForeignKey(
        "firewallz.Sport", on_delete=models.CASCADE, related_name="teams"
    )
    captain = models.OneToOneField(
        "firewallz.Player",
        related_name="captain_of",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # team_players: reverse relation to TeamPlayer
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"
        indexes = [
            models.Index(fields=["sport"]),
            models.Index(fields=["college"]),
            models.Index(fields=["is_deleted"]),
        ]
        unique_together = (("sport", "college"),)

    @property
    def active_players(self):
        return self.team_players.filter(is_playing=True, is_deleted=False)

    @property
    def is_fully_unapproved(self):
        return not self.team_players.filter(
            status="pcr_approved", is_deleted=False
        ).exists()

    @property
    def is_fully_approved(self):
        return not self.team_players.filter(
            status="pcr_unapproved", is_deleted=False
        ).exists()

    @property
    def is_partially_approved(self):
        return not (self.is_fully_approved or self.is_fully_unapproved)

    def __str__(self):
        return f"{self.team_code} - {self.sport.name}"

    def clean(self):
        if self.captain:
            if self.college.representative == self.captain:
                raise ValidationError("College representative cannot be a captain")
            team_player = TeamPlayer.all_objects.filter(
                player=self.captain, team=self
            ).first()
            if team_player:
                team_player.is_playing = True
                team_player.save()
            else:
                raise ValidationError("TeamPlayer for captain doesn't exist")
        # number_teamplayers = TeamPlayer.all_objects_playing.filter(team=self).count()
        # if self.is_locked:
        #     min_required = self.sport.min_players
        #     if number_teamplayers < min_required:
        #         raise ValidationError("Player limit violation! Sport requires a minimum of {min_required} players!")
        #     max_required = self.sport.max_players
        #     if number_teamplayers > max_required:
        #         raise ValidationError("Player limit violation! Sport player limit exceeds the max of {max_required} players!")

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TeamPlayer(models.Model):
    """
    Represents a player in a team for a specific sport and a set of events for that sport.
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    player = models.ForeignKey(
        "firewallz.Player", related_name="team_players", on_delete=models.CASCADE
    )
    status = models.CharField(
        verbose_name="PCr Approval Status",
        choices=TEAM_PLAYER_STATUS_CHOICES,
        default="pcr_unapproved",
    )
    team = models.ForeignKey(
        "firewallz.Team", related_name="team_players", on_delete=models.CASCADE
    )
    events = models.ManyToManyField(
        Event,
        related_name="team_players",
        help_text="Events in this sport in which the player is participating",
    )  # a singular TeamPlayer can be part of multiple events in its sport (e.g., Athletics 200M and 400M)
    ## has been linked to the team but
    is_playing = models.BooleanField(
        verbose_name="Has Been Added To The Team?",
        default=False,
        help_text="Has this player been added to the team by the captain? Very important field.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = NonDeletedManager()
    playing_objects = NonDeletedAndPlayingManager()
    all_objects = models.Manager()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.player.name} - {self.team.team_code} ({self.team.sport.name})"

    class Meta:
        verbose_name = "Team Player"
        verbose_name_plural = "Team Players"
        indexes = [
            models.Index(fields=["player"]),
            models.Index(fields=["team"]),
            models.Index(fields=["is_playing"]),
            models.Index(fields=["is_deleted"]),
        ]

    @property
    def is_captain(self):
        return (
            self.team.captain == self.player
            if self.team and self.team.captain
            else False
        )

    @property
    def events_list(self):
        a = self.events.all()
        return ", ".join([event.name for event in a]) if len(a) > 0 else "None"

    # dummy property for now
    @property
    def is_paid_for(self):
        return self.sport_payment.filter(transaction_status="SUCCESS").exists()

    def clean(self):
        if (
            College.objects.filter(representative=self.player).exists()
            and self.is_captain
        ):
            raise ValidationError("College representative cannot be a captain")

        if self.player.is_coach:
            raise ValidationError("Coaches cannot join teams.")

        if self.events.exists():
            player_gender = self.player.gender
            player_events = self.events.all().select_related("sport")
            events_gender = set([i.sport.gender for i in player_events])
            events_gender = events_gender - set([player_gender, "Mixed"])
            if len(events_gender) != 0:
                raise ValidationError(
                    "Team Player's gender does not match the registered event type."
                )

        if self.is_captain and not self.is_playing:
            raise ValidationError("Captain must be playing in the team.")

        if self.player.college != self.team.college:
            raise ValidationError(
                "Selected Team's College does not match Player's College"
            )

        team_players = TeamPlayer.objects.filter(player=self.player).values_list("events__static_id", flat=True)
        if len(team_players) > 5:
            raise ValidationError("Cannot register for more than 5 events.")
        
        if self.status == "pcr_approved" and not self.is_playing:
            raise ValidationError("Cannot approve a player who is not playing in the team.")
        
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def soft_delete(self, using=None, keep_parents=False):
        type(self).all_objects.filter(pk=self.pk).update(is_deleted=True)

BASE_PAYMENT_AMOUNT = 1300
SPORT_PAYMENT_AMOUNT = 200
HALF_PAYMENT_AMOUNT = 1000

TXN_STATUS_CHOICES = [
    ("PENDING", "PENDING"),
    ("SUCCESS", "SUCCESS"),
    ("FAILED", "FAILED"),
    ("TIMEOUT", "TIMEOUT"),
]


class BasePayment(models.Model):
    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    player = models.ForeignKey(
        "firewallz.Player", related_name="base_payment", on_delete=models.PROTECT
    )
    amount = models.PositiveIntegerField(default=BASE_PAYMENT_AMOUNT)
    transaction = models.ForeignKey(
        "firewallz.Transaction",
        related_name="base_payment",
        on_delete=models.PROTECT,
    )
    transaction_status = models.CharField(choices=TXN_STATUS_CHOICES, default="PENDING")
    half_payment = models.BooleanField(default=False)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    class Meta:
        verbose_name = "Base Payment"
        verbose_name_plural = "Base Payments"
        indexes = [
            models.Index(fields=["player"]),
            models.Index(fields=["transaction"]),
            models.Index(fields=["transaction_status"]),
        ]

    def soft_delete(self):
        self.is_deleted = True
        self.save()
    def save(self, *args, **kwargs):
        # if this function is created with clean function, then update the bulk_create in views.py accordingly, for now I am saving simply
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Base Payment for {self.player.name} - Amount: {self.amount} - Status: {self.transaction_status}"


class SportPayment(models.Model):
    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    team_player = models.ForeignKey(
        "firewallz.TeamPlayer",
        related_name="sport_payment",
        on_delete=models.PROTECT,
    )
    amount = models.PositiveIntegerField(default=SPORT_PAYMENT_AMOUNT)
    transaction = models.ForeignKey(
        "firewallz.Transaction",
        related_name="sport_payment",
        on_delete=models.PROTECT,
    )
    transaction_status = models.CharField(choices=TXN_STATUS_CHOICES, default="PENDING")
    objects = NonDeletedManager()
    all_objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Sport Payment"
        verbose_name_plural = "Sport Payments"
        indexes = [
            models.Index(fields=["team_player"]),
            models.Index(fields=["transaction"]),
            models.Index(fields=["transaction_status"]),
        ]
    def soft_delete(self):
        self.is_deleted = True
        self.save()
    def save(self, *args, **kwargs):
        #     if this function is created with clean fcuntion, then update the bulk_create in views.py accordingly, for now I am saving simply
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment for {self.team_player.player.name} - Amount: {self.amount} - Status: {self.transaction_status}"


TXN_TYPE_CHOICES = [
    ("PCR", "PCR"),
    ("SWD", "SWD"),
    ("CR", "CR"),
    ("TEAM_CAPTAIN", "TEAM_CAPTAIN"),
    ("PLAYER", "PLAYER"),
]


class Transaction(models.Model):
    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    paid_for = models.ForeignKey(
        "firewallz.Player", related_name="transactions", on_delete=models.PROTECT
    )
    paid_by = models.ForeignKey(
        "firewallz.Player", related_name="transactions_by", on_delete=models.PROTECT
    )  # This will include the connection to CR, Team Captain or the Player themselves
    reference_no = models.CharField(max_length=100)
    checksum = models.CharField(max_length=255, null=True, blank=True)
    payment_url = models.TextField(null=True, blank=True)
    amount = models.PositiveIntegerField(default=0)
    applied_pcr_discount = models.PositiveIntegerField(default=0)
    metadata = models.TextField(null=True, blank=True)
    status = models.CharField(choices=TXN_STATUS_CHOICES, default="PENDING")
    type = models.CharField(choices=TXN_TYPE_CHOICES, max_length=20)
    objects = NonDeletedManager()
    all_objects = models.Manager()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["paid_for"]),
            models.Index(fields=["paid_by"]),
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
        ]
    def clean(self):
        if not self.is_deleted:
            if Transaction.objects.filter(
                reference_no=self.reference_no,
                paid_for=self.paid_for,
                is_deleted=False,
                status=self.status
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    "A non-deleted transaction with this reference_no and paid_for already exists."
                )
        super().clean()
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    def soft_delete(self):
        self.is_deleted = True
        self.save()
    def __str__(self):
        return f"Transaction {self.reference_no} for {self.paid_for.name} - Amount: {self.amount} - Status: {self.status}"
