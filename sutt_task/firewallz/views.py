from django.shortcuts import render
from .models import Player, TeamPlayer, Event, Team, College, Sport, BasePayment, Transaction, BASE_PAYMENT_AMOUNT, SPORT_PAYMENT_AMOUNT, SportPayment
from django import forms
from django.http import HttpResponseRedirect
from .forms import PlayerRegistrationForm, UserRegistrationForm, PlayerLoginForm, SportsRegistrationForm, AdminLoginForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from .tables import TeamPlayerTable 
from django_tables2 import RequestConfig
from django.contrib import messages
import random
from django.db.models import Count, Q

########################## AUTHENTICATION STUFF ############################

def register_player(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = authenticate(request, username=form.cleaned_data['email'], password=form.cleaned_data['password1'])
            if user is not None:
                login(request, user)
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
def player_dashboard(request):
    player = Player.objects.filter(auth_user=request.user).first()
    team_players = TeamPlayer.objects.filter(player=player).select_related("team__captain", "team__college")
    rows = []
    for team_player in team_players:
        for event in team_player.events.all():
            rows.append({
                "event": event,
                "team_player": team_player,
            })
    table = TeamPlayerTable(rows)
    # To setup pagination of the table
    RequestConfig(request, paginate={"per_page": 2}).configure(table)
    return render(request, 'player_dashboard.html', {'table': table})

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
        print(payment)
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

    print(team_player_id)
    player = Player.objects.filter(auth_user=request.user).first()
    print(player)
    if not player:
        return HttpResponseRedirect('/firewallz/player/login/')

    try:
        team_player = TeamPlayer.objects.get(static_id=team_player_id)
        print(team_player)
    except TeamPlayer.DoesNotExist:
        messages.error(request, "Team player not found or you don't have permission.")
        return HttpResponseRedirect('/firewallz/player/dashboard/')

    sport_payment = SportPayment.objects.filter(team_player=team_player, transaction_status='SUCCESS').first()
    print(sport_payment)
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
    # aggregate TeamPlayer counts
    team_player_stats = TeamPlayer.objects.aggregate(
        pcr_approved_players=Count('static_id', filter=Q(status='pcr_approved', player__is_coach=False)),
        pcr_approved_coaches=Count('static_id', filter=Q(status='pcr_approved', player__is_coach=True)),
        firewallz_approved_players=Count('static_id', filter=Q(status='firewallz_approved', player__is_coach=False)),
        firewallz_approved_coaches=Count('static_id', filter=Q(status='firewallz_approved', player__is_coach=True)),
    )
    pcr_approved_players = team_player_stats.get('pcr_approved_players', 0)
    pcr_approved_coaches = team_player_stats.get('pcr_approved_coaches', 0)
    firewallz_approved_players = team_player_stats.get('firewallz_approved_players', 0)
    firewallz_approved_coaches = team_player_stats.get('firewallz_approved_coaches', 0)

    player_stats = Player.objects.aggregate(total_players=Count('static_id', filter=Q(is_coach=False)))
    total_players = player_stats.get('total_players', 0)
    total_teams = Team.objects.aggregate(total_teams=Count('static_id')).get('total_teams', 0)
    total_colleges = College.objects.aggregate(total_colleges=Count('static_id')).get('total_colleges', 0)
    context = {
        'total_players': total_players,
        'total_teams': total_teams,
        'total_colleges': total_colleges,
        'pcr_approved_players': pcr_approved_players,
        'pcr_approved_coaches': pcr_approved_coaches,
        'firewallz_approved_players': firewallz_approved_players,
        'firewallz_approved_coaches': firewallz_approved_coaches,
    }
    return render(request, 'admin_dashboard.html', context)

def home(request):
    return render(request, 'home.html')