from rest_framework.permissions import BasePermission

class IsSelfOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user and (request.user.is_staff or obj.id == request.user.id)


class IsTeamAdmin(BasePermission):
    """
    Permission class that only allows team admins to perform certain actions
    """
    def has_object_permission(self, request, view, obj):
        # obj is the Team instance
        return request.user and (
            request.user.is_staff or 
            obj.created_by == request.user
        )
