from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from urllib.parse import urlencode
from apps.common.authentication import CookieJWTAuthentication


class JWTAuthFromCookieMiddleware(MiddlewareMixin):
	def process_request(self, request):
		if request.path.startswith('/api/'):
			return None
			
		if hasattr(request, 'user') and request.user.is_authenticated:
			return None

		auth = CookieJWTAuthentication()
		try:
			result = auth.authenticate(request)
			if result is not None:
				user, token = result
				request.user = user
			else:
				request.user = AnonymousUser()
		except Exception:
			request.user = AnonymousUser()
		
		return None


class LoginRequiredMiddleware(MiddlewareMixin):
	"""
	Middleware that requires authentication for specific paths
	and handles redirects with 'next' parameter.
	"""
	
	# Paths that require authentication
	PROTECTED_PATHS = [
		'/dashboard/',
		'/tasks/',
		'/users/',
	]
	
	# Paths that should be accessible without authentication
	EXEMPT_PATHS = [
		'/accounts/login/',
		'/accounts/register/',
		'/api/',
		'/admin/',
	]
	
	def process_request(self, request):
		# Skip if already authenticated
		if hasattr(request, 'user') and request.user.is_authenticated:
			return None
		
		# Check if path is exempt from authentication
		for exempt_path in self.EXEMPT_PATHS:
			if request.path.startswith(exempt_path):
				return None
		
		# Check if path requires authentication
		requires_auth = False
		for protected_path in self.PROTECTED_PATHS:
			if request.path.startswith(protected_path):
				requires_auth = True
				break
		
		if requires_auth:
			# Build login URL with next parameter
			login_url = '/accounts/login/'
			if request.path != '/':
				query_params = urlencode({'next': request.get_full_path()})
				login_url = f"{login_url}?{query_params}"
			
			return HttpResponseRedirect(login_url)
		
		return None

