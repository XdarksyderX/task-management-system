from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Task, Tag, TaskTemplate, TaskStatus, TaskPriority


@login_required
def task_list(request):
    """List all tasks for the user"""
    tasks = Task.objects.filter(
        assigned_to=request.user,
        is_archived=False
    ).select_related('created_by').prefetch_related('tags', 'assigned_to')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status and status in [choice[0] for choice in TaskStatus.choices]:
        tasks = tasks.filter(status=status)
    
    # Filter by priority if provided
    priority = request.GET.get('priority')
    if priority and priority in [choice[0] for choice in TaskPriority.choices]:
        tasks = tasks.filter(priority=priority)
    
    context = {
        'tasks': tasks,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
        'current_status': status,
        'current_priority': priority,
    }
    
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create(request):
    """Create a new task"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', TaskPriority.MEDIUM)
        due_date = request.POST.get('due_date')
        estimated_hours = request.POST.get('estimated_hours', 0)
        tag_ids = request.POST.getlist('tags')
        
        if title:
            task = Task.objects.create(
                title=title,
                description=description,
                priority=priority,
                created_by=request.user,
                estimated_hours=float(estimated_hours) if estimated_hours else 0
            )
            
            if due_date:
                from django.utils import timezone
                from datetime import datetime
                try:
                    # Parse the datetime string and make it timezone-aware
                    naive_datetime = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                    task.due_date = timezone.make_aware(naive_datetime)
                    task.save()
                except ValueError:
                    # If parsing fails, skip setting due_date
                    pass
            
            # Add tags
            if tag_ids:
                task.tags.set(tag_ids)
            
            # Assign to creator by default
            task.assigned_to.add(request.user)
            
            messages.success(request, 'Task created successfully!')
            return redirect('tasks:task_list')
        else:
            messages.error(request, 'Title is required.')
    
    tags = Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
        'priority_choices': TaskPriority.choices,
    }
    
    return render(request, 'tasks/task_create.html', context)


@login_required
@login_required
def task_detail(request, pk):
    """View task details"""
    task = get_object_or_404(
        Task.objects.select_related('created_by', 'assigned_team', 'parent_task')
                   .prefetch_related('assigned_to', 'tags'),
        pk=pk
    )
    
    # Check if user has permission to view this task
    if not (task.assigned_to.filter(id=request.user.id).exists() or 
            task.created_by == request.user or 
            request.user.is_staff):
        return redirect('tasks:task_list')
    
    context = {
        'task': task,
    }
    
    return render(request, 'tasks/task_detail.html', context)


@login_required
def tag_list(request):
    """List and manage tags"""
    tags = Tag.objects.all().order_by('name')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            tag, created = Tag.objects.get_or_create(name=name)
            if created:
                messages.success(request, f'Tag "{name}" created successfully!')
            else:
                messages.info(request, f'Tag "{name}" already exists.')
        else:
            messages.error(request, 'Tag name is required.')
        
        return redirect('tag_list')
    
    context = {
        'tags': tags,
    }
    
    return render(request, 'tasks/tag_list.html', context)


@login_required
def tag_create(request):
    """Create a new tag"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        color = request.POST.get('color', '#667eea')
        
        if name:
            tag, created = Tag.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'color': color
                }
            )
            if created:
                messages.success(request, f'Tag "{name}" created successfully!')
                return redirect('tasks:tag_list')
            else:
                messages.error(request, f'Tag "{name}" already exists.')
        else:
            messages.error(request, 'Tag name is required.')
    
    return render(request, 'tasks/tag_create.html')


@login_required
def template_list(request):
    """List and manage task templates"""
    templates = TaskTemplate.objects.filter(
        created_by=request.user
    ).order_by('name')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'tasks/template_list.html', context)


@login_required
def template_create(request):
    """Create a new task template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', TaskPriority.MEDIUM)
        estimated_hours = request.POST.get('estimated_hours', 0)
        tag_ids = request.POST.getlist('tags')
        
        if name:
            template_data = {
                'title': f'[Template] {name}',
                'description': description,
                'priority': priority,
                'estimated_hours': float(estimated_hours) if estimated_hours else 0,
                'tags': list(tag_ids),
            }
            
            template = TaskTemplate.objects.create(
                name=name,
                template=template_data,
                created_by=request.user
            )
            
            messages.success(request, 'Template created successfully!')
            return redirect('template_list')
        else:
            messages.error(request, 'Template name is required.')
    
    tags = Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
        'priority_choices': TaskPriority.choices,
    }
    
    return render(request, 'tasks/template_create.html', context)


@login_required
def template_edit(request, pk):
    """Edit an existing task template"""
    template = get_object_or_404(TaskTemplate, pk=pk)
    
    # Check permissions - user should be creator or admin
    if not (template.created_by == request.user or request.user.is_staff):
        messages.error(request, 'You do not have permission to edit this template.')
        return redirect('tasks:template_list')
    
    context = {
        'template': template,
        'priority_choices': TaskPriority.choices,
    }
    
    return render(request, 'tasks/template_edit.html', context)


@login_required
def template_delete(request, pk):
    """Delete a task template"""
    template = get_object_or_404(TaskTemplate, pk=pk)
    
    # Check permissions - user should be creator or admin
    if not (template.created_by == request.user or request.user.is_staff):
        messages.error(request, 'You do not have permission to delete this template.')
        return redirect('tasks:template_list')
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Template deleted successfully!')
        return redirect('tasks:template_list')
    
    context = {
        'template': template,
    }
    
    return render(request, 'tasks/template_delete.html', context)


@login_required
def task_edit(request, pk):
    """Edit an existing task"""
    task = get_object_or_404(
        Task.objects.select_related('created_by')
                   .prefetch_related('tags', 'assigned_to'),
        pk=pk
    )
    
    # Check permissions - user should be creator or admin
    if not (task.created_by == request.user or request.user.is_staff):
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('tasks:task_detail', pk=task.id)
    
    tags = Tag.objects.all().order_by('name')
    context = {
        'task': task,
        'tags': tags,
        'status_choices': TaskStatus.choices,
        'priority_choices': TaskPriority.choices,
    }
    
    return render(request, 'tasks/task_edit.html', context)


@login_required
def task_delete(request, pk):
    """Delete (archive) a task"""
    task = get_object_or_404(Task, pk=pk)
    
    # Check permissions - user should be creator or admin
    if not (task.created_by == request.user or request.user.is_staff):
        messages.error(request, 'You do not have permission to delete this task.')
        return redirect('tasks:task_detail', pk=task.id)
    
    if request.method == 'POST':
        task.is_archived = True
        task.save()
        messages.success(request, 'Task deleted successfully!')
        return redirect('tasks:task_list')
    
    context = {
        'task': task,
    }
    
    return render(request, 'tasks/task_delete.html', context)
