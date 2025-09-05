from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
import os
import json
from apps.tasks.models import Task, TaskStatus, TaskPriority
from apps.common.jwt_utils import create_jwt_token


def landing_page(request):
    """Landing page for non-authenticated users"""
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


# Analytics Views
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


# Analytics API Proxy
@csrf_exempt
@require_http_methods(["GET", "POST"])
def analytics_api_proxy(request, path):
    """Proxy requests to the analytics microservice"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    analytics_base_url = os.getenv("ANALYTICS_API_URL", "http://analytics:5000")
    
    # Create JWT token for the user
    try:
        token = create_jwt_token(request.user)
    except Exception as e:
        return JsonResponse({"error": f"Token creation failed: {str(e)}"}, status=500)
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Determine if this is analytics or reports based on request path
    if 'analytics' in request.path:
        url = f"{analytics_base_url}/api/v1/analytics/{path}"
    else:
        url = f"{analytics_base_url}/api/v1/reports/{path}"
    
    try:
        if request.method == "GET":
            response = requests.get(url, headers=headers, params=request.GET, timeout=30)
        elif request.method == "POST":
            body = request.body.decode('utf-8') if request.body else '{}'
            response = requests.post(url, headers=headers, data=body, timeout=30)
        
        # Return the response from analytics service
        if response.headers.get('content-type', '').startswith('application/json'):
            return JsonResponse(response.json(), status=response.status_code, safe=False)
        else:
            return HttpResponse(
                response.content,
                status=response.status_code,
                content_type=response.headers.get('content-type', 'application/octet-stream')
            )
            
    except requests.exceptions.RequestException as e:
        return JsonResponse(
            {"error": f"Analytics service unavailable: {str(e)}"}, 
            status=503
        )
