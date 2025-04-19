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
    return [(i, item) for i, item in enumerate(value)]

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