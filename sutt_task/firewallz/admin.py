from django.contrib import admin
from django.apps import apps
from django.db.models import Model

app_config = apps.get_app_config('firewallz')

for model in app_config.get_models():
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass