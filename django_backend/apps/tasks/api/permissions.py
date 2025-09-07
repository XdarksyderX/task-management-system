from rest_framework .permissions import BasePermission ,SAFE_METHODS 

class IsOwnerOrAssigneeOrAdmin (BasePermission ):
    def has_object_permission (self ,request ,view ,obj ):
        u =request .user 
        if not u or not u .is_authenticated :
            return False 
        if u .is_staff :
            return True 
        if request .method in SAFE_METHODS :
            return obj .created_by_id ==u .id or obj .assigned_to .filter (id =u .id ).exists ()
        return obj .created_by_id ==u .id 
