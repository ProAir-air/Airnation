from django import template

register = template.Library()

@register.filter
def format_duration(value):
    """Convert seconds to a string in 'D days, H hours, M minutes, S seconds' format."""
    days, remainder = divmod(value, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"


from django import template

register = template.Library()

@register.filter
def format_period(value):
    """Format period keys by replacing underscores with spaces and capitalizing."""
    return value.replace('_', ' ').title()


from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def format_time(seconds):
    if not seconds:
        return "0 seconds"
        
    try:
        seconds = float(seconds)
    except (ValueError, TypeError):
        return ""
        
    delta = timedelta(seconds=seconds)
    hours = delta.seconds // 3600 + delta.days * 24
    minutes = (delta.seconds % 3600) // 60
    seconds = delta.seconds % 60
    
    parts = []
    
    if hours > 0:
        parts.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
    if minutes > 0:
        parts.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
    if seconds > 0 and not hours:  # Only show seconds if less than an hour
        parts.append(f"{seconds} {'second' if seconds == 1 else 'seconds'}")
        
    return " ".join(parts)