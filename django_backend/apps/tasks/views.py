from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Task, Tag, TaskTemplate, TaskStatus, TaskPriority

# Import Kafka event publishers
from .producer import (
    publish_task_created,
    publish_task_updated,
    publish_task_deleted,
    publish_task_status_changed,
    publish_task_completed,
    publish_task_priority_changed,
    publish_task_archived,
    publish_tag_created,
    publish_tag_updated,
    publish_tag_deleted,
    publish_template_created,
    publish_template_updated,
    publish_template_deleted
)


@login_required
def task_list(request):
    """List all tasks for the user with SSR"""
    # Base queryset
    user_tasks = Task.objects.filter(
        assigned_to=request.user,
        is_archived=False
    ).select_related('created_by').prefetch_related('tags', 'assigned_to')
    
    # Handle POST actions
    if request.method == 'POST':
        action = request.POST.get('action')
        task_id = request.POST.get('task_id')
        
        if action == 'mark_done' and task_id:
            try:
                task = Task.objects.get(id=task_id, assigned_to=request.user)
                old_status = task.status
                task.status = TaskStatus.DONE
                task.save()
                # Publish task completion event
                publish_task_completed(request.user.id, task.id, task.title)
                # Also publish status change event
                publish_task_status_changed(
                    request.user.id, 
                    task.id, 
                    task.title, 
                    old_status, 
                    TaskStatus.DONE
                )
                messages.success(request, f'Task "{task.title}" marked as completed!')
            except Task.DoesNotExist:
                messages.error(request, 'Task not found.')
        
        return redirect('tasks:task_list')
    
    # Apply filters
    filtered_tasks = user_tasks
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status and status in [choice[0] for choice in TaskStatus.choices]:
        filtered_tasks = filtered_tasks.filter(status=status)
    
    # Filter by priority if provided
    priority = request.GET.get('priority')
    if priority and priority in [choice[0] for choice in TaskPriority.choices]:
        filtered_tasks = filtered_tasks.filter(priority=priority)
    
    # Get task statistics (from all user tasks, not filtered)
    stats = {
        'total_tasks': user_tasks.count(),
        'todo_tasks': user_tasks.filter(status=TaskStatus.TODO).count(),
        'in_progress_tasks': user_tasks.filter(status=TaskStatus.IN_PROGRESS).count(),
        'blocked_tasks': user_tasks.filter(status=TaskStatus.BLOCKED).count(),
        'done_tasks': user_tasks.filter(status=TaskStatus.DONE).count(),
    }
    
    # Order tasks
    tasks = filtered_tasks.order_by('-created_at')
    
    context = {
        'tasks': tasks,
        'stats': stats,
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
        assigned_user_ids = request.POST.getlist('assigned_to')
        
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
            
            # Assign users
            if assigned_user_ids:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                valid_users = User.objects.filter(id__in=assigned_user_ids)
                task.assigned_to.set(valid_users)
                # Also add creator if not already assigned
                if not task.assigned_to.filter(id=request.user.id).exists():
                    task.assigned_to.add(request.user)
            else:
                # Assign to creator by default
                task.assigned_to.add(request.user)
            
            # Publish task creation event
            assigned_to_id = None
            if task.assigned_to.exists():
                assigned_to_id = task.assigned_to.first().id
            
            publish_task_created(
                request.user.id,
                task.id,
                task.title,
                task.description,
                task.priority,
                assigned_to_id
            )
            
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
        
        return redirect('tasks:tag_list')
    
    context = {
        'tags': tags,
    }
    
    return render(request, 'tags/tag_list.html', context)


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
                # Publish tag creation event
                publish_tag_created(request.user.id, tag.id, tag.name, tag.color)
                messages.success(request, f'Tag "{name}" created successfully!')
                return redirect('tasks:tag_list')
            else:
                messages.error(request, f'Tag "{name}" already exists.')
        else:
            messages.error(request, 'Tag name is required.')
    
    return render(request, 'tags/tag_create.html')


@login_required
def template_list(request):
    """List and manage task templates"""
    templates = TaskTemplate.objects.filter(
        created_by=request.user
    ).order_by('name')
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'templates/template_list.html', context)


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
            
            # Publish template creation event
            publish_template_created(
                request.user.id,
                template.id,
                template.name,
                description,
                priority
            )
            
            messages.success(request, 'Template created successfully!')
            return redirect('tasks:template_list')
        else:
            messages.error(request, 'Template name is required.')
    
    tags = Tag.objects.all().order_by('name')
    context = {
        'tags': tags,
        'priority_choices': TaskPriority.choices,
    }
    
    return render(request, 'templates/template_create.html', context)


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
    
    return render(request, 'templates/template_edit.html', context)


@login_required
def template_delete(request, pk):
    """Delete a task template"""
    template = get_object_or_404(TaskTemplate, pk=pk)
    
    # Check permissions - user should be creator or admin
    if not (template.created_by == request.user or request.user.is_staff):
        messages.error(request, 'You do not have permission to delete this template.')
        return redirect('tasks:template_list')
    
    if request.method == 'POST':
        template_name = template.name
        template_id = template.id
        template.delete()
        # Publish template deletion event
        publish_template_deleted(request.user.id, template_id, template_name)
        messages.success(request, 'Template deleted successfully!')
        return redirect('tasks:template_list')
    
    context = {
        'template': template,
    }
    
    return render(request, 'templates/template_delete.html', context)


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
    
    if request.method == 'POST':
        # Capture original values for change tracking
        original_title = task.title
        original_description = task.description
        original_priority = task.priority
        original_status = task.status
        
        # Update task fields
        new_title = request.POST.get('title', task.title)
        new_description = request.POST.get('description', task.description)
        new_priority = request.POST.get('priority', task.priority)
        new_status = request.POST.get('status', task.status)
        
        task.title = new_title
        task.description = new_description
        task.priority = new_priority
        task.status = new_status
        
        # Handle estimated hours
        estimated_hours = request.POST.get('estimated_hours')
        if estimated_hours:
            try:
                task.estimated_hours = float(estimated_hours)
            except ValueError:
                pass
        
        # Handle due date
        due_date = request.POST.get('due_date')
        if due_date:
            from django.utils import timezone
            from datetime import datetime
            try:
                naive_datetime = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                task.due_date = timezone.make_aware(naive_datetime)
            except ValueError:
                pass
        else:
            task.due_date = None
        
        # Save task
        task.save()
        
        # Update tags
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            task.tags.set(tag_ids)
        else:
            task.tags.clear()
        
        # Update assigned users
        assigned_user_ids = request.POST.getlist('assigned_to')
        if assigned_user_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            valid_users = User.objects.filter(id__in=assigned_user_ids)
            task.assigned_to.set(valid_users)
        else:
            # If no users assigned, keep creator assigned
            task.assigned_to.set([request.user])
        
        # Publish events for changes
        changes = {}
        if original_title != new_title:
            changes['title'] = {'old': original_title, 'new': new_title}
        if original_description != new_description:
            changes['description'] = {'old': original_description, 'new': new_description}
        if original_priority != new_priority:
            changes['priority'] = {'old': original_priority, 'new': new_priority}
            # Also publish specific priority change event
            publish_task_priority_changed(
                request.user.id, task.id, task.title, original_priority, new_priority
            )
        if original_status != new_status:
            changes['status'] = {'old': original_status, 'new': new_status}
            # Also publish specific status change event
            publish_task_status_changed(
                request.user.id, task.id, task.title, original_status, new_status
            )
            # If task was completed, publish completion event
            if new_status == TaskStatus.DONE and original_status != TaskStatus.DONE:
                publish_task_completed(request.user.id, task.id, task.title)
        
        # Publish general update event if there were changes
        if changes:
            publish_task_updated(request.user.id, task.id, task.title, changes)
        
        messages.success(request, 'Task updated successfully!')
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
        task_title = task.title
        task_id = task.id
        task.is_archived = True
        task.save()
        # Publish task archival event
        publish_task_archived(request.user.id, task_id, task_title)
        messages.success(request, 'Task deleted successfully!')
        return redirect('tasks:task_list')
    
    context = {
        'task': task,
    }
    
    return render(request, 'tasks/task_delete.html', context)
