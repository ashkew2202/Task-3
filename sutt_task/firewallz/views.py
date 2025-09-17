from django.shortcuts import render
from .models import Group, Player, TeamPlayer, Event, Team, College, Sport, BasePayment, Transaction, BASE_PAYMENT_AMOUNT, SPORT_PAYMENT_AMOUNT, SportPayment
from django import forms
from django.http import HttpResponseRedirect
from .forms import PlayerRegistrationForm, UserRegistrationForm, PlayerLoginForm, SportsRegistrationForm, AdminLoginForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from .tables import TeamPlayerTable 
from django_tables2 import RequestConfig
from django.contrib import messages
import random
from django.db.models import Count, Q, Prefetch
from .models import UserProfile
from collections import defaultdict

########################## AUTHENTICATION STUFF ############################

def register_player(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(request, username=form.data['email'], password=form.cleaned_data['password1'])
            if user is not None:
                login(request, user)
                userprof, created = UserProfile.objects.get_or_create(
                    auth_user=user,
                    defaults={
                        'name': form.cleaned_data.get('name', ''),
                        'phone_number': form.cleaned_data.get('phone_number', ''),
                        'email': form.data['email'],
                        'gender': form.cleaned_data.get('gender', '')
                    }
                )
                userprof.save()
            return HttpResponseRedirect('/firewallz/player/details/')  # redirect to player dashboard
    else:
        form = UserRegistrationForm()
    return render(request, 'register_player.html', {'form': form})


def login_player(request):
    if request.method == 'POST':
        form = PlayerLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is None:
                form.add_error(None, 'Invalid email or password.')
            # Ensure that the user is a player not an admin
            elif user.user_type != "player":
                form.add_error(None, 'You are not authorized to login as a Player.')
            else:
                login(request, user)
                return HttpResponseRedirect('/firewallz/player/dashboard/')
    else:
        form = PlayerLoginForm()
    return render(request, 'login_player.html', {'form': form})

def logout_player(request):
    request.session.flush()
    return HttpResponseRedirect('/firewallz/player/login/')

def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            try:
                user = form.cleaned_data.get('user')
                if user:
                    login(request, user)
                    return HttpResponseRedirect('/firewallz/admin/dashboard/')
                else:
                    form.add_error(None, 'Invalid admin credentials.')
            except Exception as e:
                form.add_error(f'An error occured while logging in {str(e)}')
    else:
        form = AdminLoginForm()
    return render(request, 'admin_login.html', {'form': form})

def admin_logout(request):
    request.session.flush()
    return HttpResponseRedirect('/firewallz/')


########################### PLAYER FUNCTIONALITY ##############################


@login_required(login_url="/firewallz/player/login")
def player_details(request):
    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.save()
                return HttpResponseRedirect('/firewallz/player/dashboard/')
            except Exception as e:
                form.add_error(None, f'An error occurred while saving the player: {str(e)}')
    else:
        form =PlayerRegistrationForm(user=request.user)
    return render(request, 'player_details.html', {'form': form})

@login_required(login_url="/firewallz/player/login")
def player_profile(request):
    userprof = Player.objects.filter(auth_user=request.user).first()
    return render(request, 'player_profile.html', {'player': userprof})

@login_required(login_url="/firewallz/player/login")
def edit_profile(request):
    player = Player.objects.filter(auth_user=request.user).first()
    if not player:
        messages.error(request, 'Player profile not found.')
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        phone = (request.POST.get('phone_number') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()

        # Enforce unique email if changed
        if email and email != request.user.email:
            UserModel = request.user.__class__
            if UserModel.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, 'This email is already in use by another account.')
                return HttpResponseRedirect('/firewallz/player/profile/')
        else:
            player.name = name
            player.phone_number = phone
            request.user.email = email
            if hasattr(request.user, 'username'):
                request.user.username = email  # if email is used as username
            request.user.save()
            player.save()
            messages.success(request, 'Profile updated successfully.')
            return HttpResponseRedirect('/firewallz/player/profile/')

    return HttpResponseRedirect('/firewallz/player/profile/')

@login_required(login_url="/firewallz/player/login")
def player_dashboard(request):
    team_players = TeamPlayer.objects.filter(player__auth_user=request.user).select_related("team__captain", "team__college")
    rows = []
    for team_player in team_players:
        for event in team_player.events.all():
            rows.append({
                "event": event,
                "team_player": team_player,
                "team_player_id": team_player.pk,
                "team": team_player.team,
                "college": team_player.player.college,
                "sport": team_player.team.sport,
                "status": team_player.status,
                "is_paid": SportPayment.objects.filter(team_player=team_player, transaction_status='SUCCESS').exists(),
            })
    return render(request, 'player_dashboard.html', {'rows': rows})

@login_required(login_url="/firewallz/player/login")
def view_team_members(request, team_id):
    optimized_team = (
        Team.objects
        .filter(pk=team_id)
        .select_related('college', 'sport', 'captain')
        .prefetch_related(
        Prefetch(
            TeamPlayer._meta.get_field('team').remote_field.get_accessor_name(),
            queryset=TeamPlayer.objects.select_related('player'),
            to_attr='prefetched_teamplayers'
        )
        )
        .first()
    )
    normal_team_players = []
    coach_team_player = None
    captain_team_player = None
    if optimized_team:
        for tp in optimized_team.prefetched_teamplayers:
            if tp.player.is_coach:
                coach_team_player = tp
            elif optimized_team.captain_id and tp.player_id == optimized_team.captain_id:
                captain_team_player = tp
            else:
                normal_team_players.append(tp)
        context = {'team': optimized_team, 'team_players': normal_team_players, 'captain': captain_team_player, 'coach': coach_team_player}
        return render(request,'view_team_members.html',context)
    messages.error(request, "Team not found.")
    return HttpResponseRedirect('/firewallz/player/dashboard/')

@login_required(login_url="/firewallz/player/login")
def register_for_sports(request):
    player = Player.objects.filter(auth_user=request.user).first()
    base_payment = BasePayment.objects.filter(player=player).first()
    if not base_payment:
        return render(request, 'sports_registration.html', {'show_payment_button': True})
    if request.method == 'POST':
        form = SportsRegistrationForm(request.POST)
        if form.is_valid():
            selected_event = form.cleaned_data['sport']
            if TeamPlayer.objects.filter(player=player, events__sport=selected_event).exists():
                form.add_error(None, 'You are already enrolled in this sport.')
                return render(request, 'sports_registration.html', {'form': form})
            event = Event.objects.filter(sport=selected_event).first()
            if player.is_coach:
                form.add_error(None, 'Coaches cannot register for sports as players.')
                return render(request, 'sports_registration.html', {'form': form})
            if not event:
                event = Event.objects.create(sport=selected_event)
            if selected_event.gender != player.gender:
                form.add_error(None, 'You cannot register for a sport with a different gender category.')
                return render(request, 'sports_registration.html', {'form': form})
            current_count = TeamPlayer.objects.filter(events=event, player__college=player.college).count()

            if current_count >= selected_event.max_players:
                form.add_error(None, 'Your college has already fulfilled the required number of participants for this sport.')
            else:
                
                team, created = Team.objects.get_or_create(
                    college=player.college,
                    sport=selected_event
                )
                team.save()
                team_player, created = TeamPlayer.objects.get_or_create(player=player, team=team,is_playing=True, status='pcr_approved')
                team_player.events.add(event)
                team_player.save()
                team.save()
                
                
                return HttpResponseRedirect('/firewallz/player/dashboard/')
            return HttpResponseRedirect('/firewallz/player/dashboard/')
    else:
        form = SportsRegistrationForm()

    return render(request, 'sports_registration.html', {'form': form})

@login_required(login_url="/firewallz/player/login")
def make_base_payment(request):
    player = Player.objects.filter(auth_user=request.user).first()
    if not player:
        return HttpResponseRedirect('/firewallz/player/login/')

    if BasePayment.objects.filter(player=player).exists():
        return HttpResponseRedirect('/firewallz/player/sports_registration')
    try:
        ref_no=random.randint(10000000000000000, 99999999999999999)
        transaction = Transaction.objects.create(
            paid_by=player,
            paid_for=player,
            amount=BASE_PAYMENT_AMOUNT,
            reference_no=str(ref_no),
            type="PLAYER",
        )
        transaction.save()
        payment, created = BasePayment.objects.get_or_create(player=player, transaction=transaction)
        if transaction:
            # Check if the transaction is successful or not
            payment.transaction_status = "SUCCESS"
            transaction.status = "SUCCESS"
            if hasattr(payment, 'transaction'):
                payment.transaction = transaction
            payment.save()
            return HttpResponseRedirect('/firewallz/player/sports_registration/')
        else:
            # Transaction creation failed -->>> mark payment as failed and show an error
            payment.transaction_status = "FAILED"
            if hasattr(payment, 'transaction'):
                payment.transaction = None
            payment.save()
            messages.error(request, 'Transaction failed. Please try again.')
            return HttpResponseRedirect('/firewallz/player/sports_registration/')
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseRedirect('/firewallz/player/sports_registration/')

@login_required(login_url="/firewallz/player/login")
def make_sports_payment(request, tp_id):
    player = Player.objects.filter(auth_user=request.user).first()
    if not player:
        return HttpResponseRedirect('/firewallz/player/login/')

    try:
        team_player = TeamPlayer.objects.get(pk=tp_id, player=player)
    except TeamPlayer.DoesNotExist:
        messages.error(request, "Team player not found or you don't have permission.")
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    events_count = team_player.events.count()
    if events_count == 0:
        messages.error(request, "No events registered for this team player.")
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    total_amount = events_count * SPORT_PAYMENT_AMOUNT

    try:
        ref_no = random.randint(10000000000000000, 99999999999999999)
        transaction = Transaction.objects.create(
            paid_by=player,
            paid_for=player,
            amount=total_amount,
            reference_no=str(ref_no),
            type="PLAYER",
        )
        transaction.status = "SUCCESS"
        transaction.save()

        # Create SportPayment tied to this TeamPlayer and transaction
        sport_payment, created = SportPayment.objects.get_or_create(
            team_player=team_player,
            transaction=transaction,
            amount=total_amount,
        )
        if transaction.status == "SUCCESS":
            sport_payment.transaction_status = 'SUCCESS'
            sport_payment.save()

        context = {
            "amount": total_amount,
            "transaction_ref": transaction.reference_no,
            "transaction_id": transaction.id,
            "team_player_id": team_player.id,
            "events_count": events_count,
            "sport_payment_id": sport_payment.id,
        }
        return render(request, "process_payment.html", context)
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseRedirect('/firewallz/player/dashboard/')
    
@login_required(login_url="/firewallz/player/login")
def print_receipt(request, team_player_id):

    player = Player.objects.filter(auth_user=request.user).first()
    if not player:
        return HttpResponseRedirect('/firewallz/player/login/')

    try:
        team_player = TeamPlayer.objects.get(static_id=team_player_id)
    except TeamPlayer.DoesNotExist:
        messages.error(request, "Team player not found or you don't have permission.")
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    sport_payment = SportPayment.objects.filter(team_player=team_player, transaction_status='SUCCESS').first()
    if not sport_payment:
        messages.error(request, "No successful payment found for this team player.")
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    context = {
        "player": player,
        "team_player": team_player,
        "sport_payment": sport_payment,
        "transaction": sport_payment.transaction,
    }
    return render(request, 'print_receipt.html', context)


######################### FIREWALLZ ADMIN FUNCTIONALITY ##########################

@login_required(login_url="/firewallz/admin/login")
def admin_dashboard(request):
    # TeamPlayer now only holds players (not coaches)
    team_player_stats = TeamPlayer.objects.aggregate(
        pcr_approved_players=Count('static_id', filter=Q(player__status='pcr_confirmed')),
        firewallz_approved_players=Count('static_id', filter=Q(player__verified_by_firewallz=True)),
    )
    pcr_approved_players = team_player_stats.get('pcr_approved_players', 0)
    firewallz_approved_players = team_player_stats.get('firewallz_approved_players', 0)

    player_stats = Player.objects.aggregate(
        total_players=Count('static_id', filter=Q(is_coach=False)),
        total_coaches=Count('static_id', filter=Q(is_coach=True)),
        firewallz_approved_coaches=Count('static_id', filter=Q(is_coach=True, verified_by_firewallz=True))
    )
    total_players = player_stats.get('total_players', 0)
    total_teams = Team.objects.aggregate(total_teams=Count('static_id')).get('total_teams', 0)
    total_colleges = College.objects.aggregate(total_colleges=Count('static_id')).get('total_colleges', 0)
    pcr_approved_coaches = Player.objects.filter(is_coach=True, status='pcr_confirmed').count()
    firewallz_approved_coaches = player_stats.get('firewallz_approved_coaches', 0)
    context = {
        'total_players': total_players,
        'total_teams': total_teams,
        'total_colleges': total_colleges,
        'pcr_approved_players': pcr_approved_players,
        'pcr_approved_coaches': pcr_approved_coaches,
        'firewallz_approved_players': firewallz_approved_players,
        'firewallz_approved_coaches': firewallz_approved_coaches,
        'total_coaches': player_stats.get('total_coaches', 0),
    }
    return render(request, 'admin_dashboard.html', context)

@login_required(login_url="/firewallz/admin/login")
def pcr_approved_players(request):
    team_players = TeamPlayer.objects.filter(status='pcr_approved', player__is_coach=False)
    approved_teamplayers = []
    for team_player in team_players:
        if any(team_player.player == player.player for player in approved_teamplayers):
            continue
        approved_teamplayers.append(team_player)
    return render(request,"pcr_approved_players.html",{"team_players": approved_teamplayers})
    # Coaches are no longer TeamPlayers; show all coaches (adjust if a PCR flag is later added)

@login_required(login_url="/firewallz/admin/login")
def pcr_approved_coaches(request):    
    
    approved_coaches = Player.objects.filter(is_coach=True, status='pcr_confirmed')
    payments = BasePayment.objects.filter(player__in=approved_coaches)
    payment_statuses = []
    for payment in payments:
        if payment is None:
            payment_statuses.append(False)
        else: 
            payment_statuses.append(True)
    return render(request, 'pcr_approved_coaches.html', {'approved_coaches': approved_coaches, 'payment_statuses': payment_statuses})

@login_required(login_url="/firewallz/admin/login")
def firewallz_approved_players(request):
    players = Player.objects.filter(verified_by_firewallz = True, is_coach=False)
    teams_data = list()
    for player in players:
        teams = TeamPlayer.objects.filter(player=player)
        teams_data.append(teams)
        
    return render(request, 'firewallz_approved_players.html', {'players': players, 'team_list': teams_data})
@login_required(login_url="/firewallz/admin/login")
def firewallz_approved_coaches(request):
    approved_coaches = (
        Player.objects
        .filter(is_coach=True, verified_by_firewallz=True)
        .select_related('college', 'auth_user')
        .order_by('college__name', 'name')
    )
    return render(request, 'firewallz_approved_coaches.html', {'approved_coaches': approved_coaches})
@login_required(login_url="/firewallz/admin/login")
def team_list(request):
    # TeamPlayer now only stores actual players (not coaches)
    teamplayer_accessor = TeamPlayer._meta.get_field('team').remote_field.get_accessor_name()
    teams = (
        Team.objects
        .select_related('college', 'sport', 'captain')
        .prefetch_related(
            Prefetch(
                teamplayer_accessor,
                queryset=TeamPlayer.objects.select_related('player').filter(player__is_coach=False),
                to_attr='all_teamplayers'
            ),
        )
    )
    for team in teams:
        team.coaches = []  # Coaches no longer linked via TeamPlayer
    return render(request, 'team_list.html', {'teams': teams})

@login_required(login_url="/firewallz/admin/login")
def college_list(request):
    colleges = College.objects.all().order_by('name')
    return render(request, 'college_list.html', {'colleges': colleges})

@login_required(login_url="/firewallz/admin/login")
def players_per_college(request, college_id):
    try:
        college = College.objects.get(pk=college_id)
    except College.DoesNotExist:
        messages.error(request, "College not found.")
        return HttpResponseRedirect('/firewallz/admin/colleges/')
    players = (
        Player.objects
        .filter(college=college, is_coach=False)
        .select_related('college', 'auth_user')
        .order_by('name')
    )
    return render(request, 'players_per_college.html', {
        'college': college,
        'players': players,
        'player_count': players.count(),
    })

@login_required(login_url="/firewallz/admin/login")
def group_list(request):
    groups = Group.objects.all()
    return render(request, 'group_list.html', {'groups': groups})

@login_required(login_url="/firewallz/admin/login")
def create_group(request):
    if request.method == 'GET':
        return render(request, 'create_group.html')
    if request.method == 'POST':
        group_name = request.POST.get('group_name', '').strip()
        if group_name:
            if Group.objects.filter(name__iexact=group_name).exists():
                messages.error(request, "A group with this name already exists.")
            else:
                Group.objects.create(name=group_name)
                messages.success(request, f"Group '{group_name}' created successfully.")
                return HttpResponseRedirect('/firewallz/admin/groups/')
        else:
            messages.error(request, "Group name cannot be empty.")
    return render(request, 'create_group.html')

@login_required(login_url="/firewallz/admin/login")
def approve_player(request, player_id):
    try:
        player = Player.objects.get(pk=player_id)
        if player.verified_by_firewallz != True:
            player.verified_by_firewallz = True
            player.save()
            messages.success(request, f"Player {player.name} approved successfully.")
        else:
            messages.info(request, f"Player {player.name} is already approved.")
    except Player.DoesNotExist:
        messages.error(request, "Player not found.")
    return HttpResponseRedirect('/firewallz/admin/firewallz_approved_players/')

@login_required(login_url="/firewallz/admin/login")
def view_team_members_admin(request, team_id):
    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        messages.error(request, "Team not found.")
        return HttpResponseRedirect('/firewallz/admin/teams/')
    team_players = TeamPlayer.objects.filter(team=team)
    return render(request, 'view_team_members_admin.html', {'team': team, 'team_players': team_players})

@login_required(login_url="/firewallz/admin/login")
def approve_team(request, team_id):
    try:
        team = Team.objects.get(pk=team_id)
        if team.is_verified_by_firewallz != True:
            team_players = TeamPlayer.objects.filter(team=team)
            for team_player in team_players:
                if team_player.player.verified_by_firewallz != True:
                    messages.error(request, f"Cannot approve team. Player {team_player.player.name} is not approved yet.")
                    return  HttpResponseRedirect('/firewallz/admin/teams/')
            team.is_verified_by_firewallz = True
            team.save()
            messages.success(request, f"Team for {team.college.name} - {team.sport.name} approved successfully.")
        else:
            messages.info(request, f"Team for {team.college.name} - {team.sport.name} is already approved.")
            return HttpResponseRedirect("/firewallz/admin/teams/")
    except Team.DoesNotExist:
        messages.error(request, f"Team with {team_id} does not exist")
    return HttpResponseRedirect("/firewallz/admin/teams/")

@login_required(login_url="/firewallz/admin/login")
def mark_player_as_paid(request, player_id):
    player = Player.objects.get(pk=player_id)

    if BasePayment.objects.filter(player=player).exists():
        messages.info(request, f"Base payment already exists for {player.name}.")
        if player.is_coach:
            return HttpResponseRedirect('/firewallz/admin/pcr_approved_coaches/')
        else:
            return HttpResponseRedirect('/firewallz/admin/pcr_approved_players/')

    try:
        ref_no = random.randint(10**17, 10**18 - 1)
        transaction = Transaction.objects.create(
            paid_by=player,
            paid_for=player,
            amount=BASE_PAYMENT_AMOUNT,
            reference_no=str(ref_no),
            type="PLAYER",
            status="SUCCESS"
        )
        BasePayment.objects.create(
            player=player,
            transaction=transaction,
            transaction_status="SUCCESS"
        )
        messages.success(request, f"Base payment recorded for {player.name}.")
    except Exception as e:
        messages.error(request, f"Error creating base payment: {e}")
    if player.is_coach:
        return HttpResponseRedirect('/firewallz/admin/pcr_approved_coaches/')
    else:
        return HttpResponseRedirect('/firewallz/admin/pcr_approved_players/')

def home(request):
    return render(request, 'home.html')