from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from apps.tasks.models import Task, TaskStatus, TaskPriority


def landing_page(request):
    """Landing page for non-authenticated users"""
    print(request.user)
    if request.user.is_authenticated:
        return dashboard(request)
    return render(request, "landing.html")


@login_required
def dashboard(request):
    """Dashboard for authenticated users"""
    user = request.user
    
    # Get user's tasks statistics
    user_tasks = Task.objects.filter(assigned_to=user, is_archived=False)
    
    stats = {
        'total_tasks': user_tasks.count(),
        'todo_tasks': user_tasks.filter(status=TaskStatus.TODO).count(),
        'in_progress_tasks': user_tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
        'blocked_tasks': user_tasks.filter(status=TaskStatus.BLOCKED).count(),
        'done_tasks': user_tasks.filter(status=TaskStatus.DONE).count(),
    }
    
    # Get recent tasks
    recent_tasks = user_tasks.order_by('-updated_at')[:5]
    
    # Get tasks by priority
    priority_stats = {
        'urgent': user_tasks.filter(priority=TaskPriority.URGENT).count(),
        'high': user_tasks.filter(priority=TaskPriority.HIGH).count(),
        'medium': user_tasks.filter(priority=TaskPriority.MEDIUM).count(),
        'low': user_tasks.filter(priority=TaskPriority.LOW).count(),
    }
    
    context = {
        'stats': stats,
        'recent_tasks': recent_tasks,
        'priority_stats': priority_stats,
    }
    
    return render(request, "dashboard.html", context)
