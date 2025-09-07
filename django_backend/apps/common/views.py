from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from apps.tasks.models import Task, TaskStatus, TaskPriority


def landing_page(request):
    """Landing page for non-authenticated users"""
    if request.user.is_authenticated:
        return dashboard(request)
    return render(request, "landing.html")


@login_required
def dashboard(request):
    """Dashboard for authenticated users"""
    user = request.user

    user_tasks = Task.objects.filter(assigned_to=user, is_archived=False)

    stats = {
        "total_tasks": user_tasks.count(),
        "todo_tasks": user_tasks.filter(status=TaskStatus.TODO).count(),
        "in_progress_tasks": user_tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
        "blocked_tasks": user_tasks.filter(status=TaskStatus.BLOCKED).count(),
        "done_tasks": user_tasks.filter(status=TaskStatus.DONE).count(),
    }

    recent_tasks = user_tasks.order_by("-updated_at")[:5]

    priority_stats = {
        "urgent": user_tasks.filter(priority=TaskPriority.URGENT).count(),
        "high": user_tasks.filter(priority=TaskPriority.HIGH).count(),
        "medium": user_tasks.filter(priority=TaskPriority.MEDIUM).count(),
        "low": user_tasks.filter(priority=TaskPriority.LOW).count(),
    }

    context = {
        "stats": stats,
        "recent_tasks": recent_tasks,
        "priority_stats": priority_stats,
    }

    return render(request, "dashboard.html", context)


@login_required
def analytics_index(request):
    """Analytics main page"""
    return render(request, "analytics/index.html")


@login_required
def analytics_dashboard(request):
    """Analytics dashboard with charts and metrics"""
    return render(request, "analytics/dashboard.html")


@login_required
def analytics_tasks_distribution(request):
    """Tasks distribution analytics"""
    return render(request, "analytics/tasks_distribution.html")


@login_required
def analytics_user_stats(request):
    """User statistics analytics"""
    return render(request, "analytics/user_stats.html")


@login_required
def analytics_team_performance(request):
    """Team performance analytics"""
    return render(request, "analytics/team_performance.html")


@login_required
def analytics_reports(request):
    """Reports generation and management"""
    return render(request, "analytics/reports.html")
