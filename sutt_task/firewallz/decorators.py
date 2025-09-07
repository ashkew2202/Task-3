from functools import wraps
from django.http import JsonResponse
from django.utils.decorators import available_attrs
from django.conf import settings
from django.contrib.auth import get_user
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(g, 'user', None)
        if not user or user.role != 'admin':
            return JsonResponse({'error': 'Admin access required'}, status=403)
        return f(*args, **kwargs)
    return decorated_function

def player_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(g, 'user', None)
        if not user or user.role != 'player':
            return JsonResponse({'error': 'Player access required'}, status=403)
        return f(*args, **kwargs)
    return decorated_function