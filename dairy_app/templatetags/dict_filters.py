# Custom template tags for dictionary lookups
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using the key
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key, None)

@register.filter(name='enumerate')
def enumerate_list(value):
    """
    Returns a list of pairs (index, item) for each item in the list
    """
    return enumerate(value)

@register.filter(name='sub')
def subtract(value, arg):
    """
    Subtract the arg from the value.
    """
    try:
        return value - arg
    except (ValueError, TypeError):
        return value

@register.filter(name='month_name')
def get_month_name(month_number):
    """
    Return the name of the month for the given month number (1-12)
    """
    from calendar import month_name
    try:
        month = int(month_number)
        if 1 <= month <= 12:
            return month_name[month]
        return ""
    except (ValueError, TypeError):
        return ""

@register.filter
def sum_attr(obj_list, attr_name):
    """
    Template filter to sum up an attribute across a list of objects
    Usage: {{ object_list|sum_attr:'attribute_name' }}
    """
    try:
        return sum(getattr(obj, attr_name) for obj in obj_list)
    except (AttributeError, TypeError):
        try:
            return sum(obj[attr_name] for obj in obj_list)
        except (KeyError, TypeError):
            return 0