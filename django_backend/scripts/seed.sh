#!/usr/bin/env bash
set -euo pipefail

echo "🌱 Starting database seeding..."

# Set Django settings
export DJANGO_SETTINGS_MODULE=config.settings

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a Django environment
if ! python -c "import django; django.setup()" 2>/dev/null; then
    print_error "Django is not properly configured. Make sure you're running this from the Django container."
    exit 1
fi

print_status "Creating seed data..."

python << 'EOF'
import os
import random
import django
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.users.models import Team
from apps.tasks.models import Tag, Task, TaskAssignment, Comment, TaskTemplate

User = get_user_model()

# Sample data
FIRST_NAMES = [
    'Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry',
    'Ivy', 'Jack', 'Kate', 'Liam', 'Mia', 'Noah', 'Olivia', 'Peter',
    'Quinn', 'Ryan', 'Sara', 'Tom', 'Uma', 'Victor', 'Wendy', 'Xavier',
    'Yara', 'Zoe', 'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
    'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
    'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'
]

DEPARTMENTS = [
    'Engineering', 'Product', 'Design', 'Marketing', 'Sales', 'HR',
    'Finance', 'Operations', 'Support', 'QA', 'DevOps', 'Security'
]

TASK_TEMPLATES = [
    'Bug Fix', 'Feature Implementation', 'Code Review', 'Testing',
    'Documentation', 'Refactoring', 'Performance Optimization', 'Security Audit'
]

TAGS = [
    'frontend', 'backend', 'database', 'api', 'ui', 'ux', 'mobile',
    'web', 'security', 'performance', 'testing', 'documentation',
    'bug', 'feature', 'enhancement', 'urgent', 'low-priority'
]

TASK_STATUSES = ['todo', 'in_progress', 'blocked', 'done']
TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent']

def create_users():
    print("Creating users...")
    users = []

    # Create admin user if it doesn't exist
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('admin123')
        admin.save()
        print(f"Created admin user: {admin.username}")

    users.append(admin)

    # Create regular users
    for i in range(25):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        username = f"{first_name.lower()}{last_name.lower()}{i}"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f"{username}@example.com",
                'first_name': first_name,
                'last_name': last_name,
                'display_name': f"{first_name} {last_name}"
            }
        )
        if created:
            user.set_password('password123')
            user.save()

        users.append(user)

    print(f"Created {len(users)} users")
    return users

def create_teams(users):
    print("Creating teams...")
    teams = []

    for dept in DEPARTMENTS:
        team_name = f"{dept} Team"
        team, created = Team.objects.get_or_create(
            name=team_name,
            defaults={
                'description': f"Team responsible for {dept.lower()} activities",
                'created_by': random.choice(users)
            }
        )

        if created:
            # Add random members to team
            num_members = random.randint(3, 8)
            team_members = random.sample(users, num_members)
            team.members.set(team_members)
            team.save()

        teams.append(team)

    print(f"Created {len(teams)} teams")
    return teams

def create_tags():
    print("Creating tags...")
    tags = []

    for tag_name in TAGS:
        tag, created = Tag.objects.get_or_create(name=tag_name)
        tags.append(tag)

    print(f"Created {len(tags)} tags")
    return tags

def create_task_templates(users):
    print("Creating task templates...")
    templates = []

    for template_name in TASK_TEMPLATES:
        template, created = TaskTemplate.objects.get_or_create(
            name=template_name,
            defaults={
                'template': {
                    'title': template_name,
                    'description': f'Template for {template_name.lower()}',
                    'estimated_hours': random.randint(1, 16),
                    'priority': random.choice(TASK_PRIORITIES)
                },
                'created_by': random.choice(users)
            }
        )
        templates.append(template)

    print(f"Created {len(templates)} task templates")
    return templates

def create_tasks(users, teams, tags):
    print("Creating tasks...")
    tasks = []

    # Create 100 tasks
    for i in range(100):
        creator = random.choice(users)
        task_title = f"Task {i+1}: {random.choice(['Implement', 'Fix', 'Update', 'Create', 'Optimize'])} {random.choice(['feature', 'bug', 'component', 'service', 'endpoint'])}"

        # Random due date within next 30 days
        due_date = timezone.now() + timedelta(days=random.randint(1, 30))

        task = Task.objects.create(
            title=task_title,
            description=f"Description for {task_title}",
            status=random.choice(TASK_STATUSES),
            priority=random.choice(TASK_PRIORITIES),
            due_date=due_date,
            estimated_hours=random.randint(1, 40),
            created_by=creator,
            assigned_team=random.choice(teams) if random.random() > 0.3 else None,  # 70% have assigned team
            is_archived=random.random() > 0.9  # 10% archived
        )

        # Add random tags (1-4 tags per task)
        num_tags = random.randint(1, 4)
        task_tags = random.sample(tags, num_tags)
        task.tags.set(task_tags)

        # Assign users to task
        if task.assigned_team:
            team_members = list(task.assigned_team.members.all())
            if team_members:
                num_assignees = random.randint(1, min(3, len(team_members)))
                assignees = random.sample(team_members, num_assignees)

                for assignee in assignees:
                    TaskAssignment.objects.create(
                        task=task,
                        user=assignee,
                        assigned_by=creator,
                        role_in_task=random.choice(['owner', 'collaborator'])
                    )

        # Add actual hours for completed tasks
        if task.status == 'done':
            task.actual_hours = task.estimated_hours * random.uniform(0.8, 1.5)
            task.save()

        tasks.append(task)

    print(f"Created {len(tasks)} tasks")
    return tasks

def create_comments(tasks, users):
    print("Creating comments...")
    comments = []

    for task in tasks:
        # 60% of tasks have comments
        if random.random() > 0.4:
            num_comments = random.randint(1, 5)

            for _ in range(num_comments):
                comment_body = random.choice([
                    "Working on this task now.",
                    "This looks good, just need to test it.",
                    "Found an issue, need to fix it.",
                    "Completed the implementation.",
                    "Need more information about this requirement.",
                    "This is blocked by another task.",
                    "Great progress on this feature!",
                    "Updated the code according to the latest standards."
                ])

                Comment.objects.create(
                    task=task,
                    author=random.choice(users),
                    body=comment_body
                )

    print("Comments created")

def main():
    print("Starting seed data creation...")

    users = create_users()
    teams = create_teams(users)
    tags = create_tags()
    templates = create_task_templates(users)
    tasks = create_tasks(users, teams, tags)
    create_comments(tasks, users)

    print("\n" + "="*50)
    print("SEED DATA CREATION COMPLETED!")
    print("="*50)
    print(f"Users: {len(users)}")
    print(f"Teams: {len(teams)}")
    print(f"Tags: {len(tags)}")
    print(f"Task Templates: {len(templates)}")
    print(f"Tasks: {len(tasks)}")
    print("\nAdmin user credentials:")
    print("Username: admin")
    print("Password: admin123")
    print("\nRegular users: password123")
    print("\nSample users created:")
    for i, user in enumerate(users[1:6]):  # Show first 5 regular users
        print(f"- {user.username} (password123)")

if __name__ == "__main__":
    main()
EOF

print_success "Seed data created successfully!"
print_status "Admin user: admin / admin123"
print_status "Regular users: [username] / password123"
print_status "You can now access the application at http://localhost:8000"
