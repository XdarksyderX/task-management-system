from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.users.models import Team
from apps.tasks.models import Tag, Task, TaskAssignment, Comment, TaskTemplate
import random
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=25,
            help='Number of users to create'
        )
        parser.add_argument(
            '--tasks',
            type=int,
            default=100,
            help='Number of tasks to create'
        )

    def handle(self, *args, **options):
        self.stdout.write('🌱 Starting database seeding...')

        users = self.create_users(options['users'])
        teams = self.create_teams(users)
        tags = self.create_tags()
        templates = self.create_task_templates(users)
        tasks = self.create_tasks(users, teams, tags, options['tasks'])
        self.create_comments(tasks, users)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Seed data created successfully!\n'
                f'Users: {len(users)}\n'
                f'Teams: {len(teams)}\n'
                f'Tags: {len(tags)}\n'
                f'Task Templates: {len(templates)}\n'
                f'Tasks: {len(tasks)}\n\n'
                f'Admin user: admin / admin123\n'
                f'Regular users: [username] / password123\n\n'
                f'Sample users created:\n' +
                '\n'.join([f'- {user.username} (password123)' for user in users[1:6]])
            )
        )

    def create_users(self, num_users):
        self.stdout.write('Creating users...')

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

        users = []

        # Create admin user
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
            self.stdout.write(f'Created admin user: {admin.username}')

        users.append(admin)

        # Create regular users
        for i in range(num_users):
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

        return users

    def create_teams(self, users):
        self.stdout.write('Creating teams...')

        DEPARTMENTS = [
            'Engineering', 'Product', 'Design', 'Marketing', 'Sales', 'HR',
            'Finance', 'Operations', 'Support', 'QA', 'DevOps', 'Security'
        ]

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

        return teams

    def create_tags(self):
        self.stdout.write('Creating tags...')

        TAGS = [
            'frontend', 'backend', 'database', 'api', 'ui', 'ux', 'mobile',
            'web', 'security', 'performance', 'testing', 'documentation',
            'bug', 'feature', 'enhancement', 'urgent', 'low-priority'
        ]

        tags = []
        for tag_name in TAGS:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            tags.append(tag)

        return tags

    def create_task_templates(self, users):
        self.stdout.write('Creating task templates...')

        TASK_TEMPLATES = [
            'Bug Fix', 'Feature Implementation', 'Code Review', 'Testing',
            'Documentation', 'Refactoring', 'Performance Optimization', 'Security Audit'
        ]

        templates = []

        for template_name in TASK_TEMPLATES:
            template, created = TaskTemplate.objects.get_or_create(
                name=template_name,
                defaults={
                    'template': {
                        'title': template_name,
                        'description': f'Template for {template_name.lower()}',
                        'estimated_hours': random.randint(1, 16),
                        'priority': random.choice(['low', 'medium', 'high', 'urgent'])
                    },
                    'created_by': random.choice(users)
                }
            )
            templates.append(template)

        return templates

    def create_tasks(self, users, teams, tags, num_tasks):
        self.stdout.write('Creating tasks...')

        TASK_STATUSES = ['todo', 'in_progress', 'blocked', 'done']
        TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent']

        tasks = []

        for i in range(num_tasks):
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
                assigned_team=random.choice(teams) if random.random() > 0.3 else None,
                is_archived=random.random() > 0.9
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

        return tasks

    def create_comments(self, tasks, users):
        self.stdout.write('Creating comments...')

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
