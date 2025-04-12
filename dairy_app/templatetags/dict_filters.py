# Custom template tags for dictionary lookups
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using the key
    Usage: {{ my_dict|get_item:key_var }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)

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