from django.urls import path
from . import views
urlpatterns = [
    path('register/', views.register_player, name='register_player'),
    path('player/login/', views.login_player, name='login_player'),
    path('player/logout/', views.logout_player, name='logout_player'),
    path('', views.home),
    path('player/details/', views.player_details, name="player_details"),
    path('player/dashboard/', views.player_dashboard, name='player_dashboard'),
    path('player/sports_registration/', views.register_for_sports, name='sports_registration'),
    path('player/make_base_payment/', views.make_base_payment, name="make_base_payment"),
    path('player/make_sports_payment/<uuid:tp_id>/', views.make_sports_payment, name="make_sport_payment"),
    path('player/print_receipt/<uuid:team_player_id>/', views.print_receipt, name="print_receipt"),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    # path('player/print_receipt/<uuid:payment_id>/', views.print_receipt, name="print_receipt"),
    # path('player/profile/', views.player_profile, name='player_profile'),
]