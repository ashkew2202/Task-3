from django import template

register = template.Library()
@register.filter(name="zip_lists")
def zip_lists(a, b):
    try:
        return zip(a, b)
    except Exception:
        return []