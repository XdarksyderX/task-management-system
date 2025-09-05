from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import Http404


@login_required
def team_list(request):
    """View for displaying the team list template"""
    return render(request, 'teams/team_list.html')


@login_required
def team_detail(request, team_id):
    """View for displaying team detail template"""
    context = {
        'team_id': team_id
    }
    return render(request, 'teams/team_detail.html', context)


@login_required
def team_edit(request, team_id):
    """View for displaying team edit template"""
    context = {
        'team_id': team_id
    }
    return render(request, 'teams/team_edit.html', context)
