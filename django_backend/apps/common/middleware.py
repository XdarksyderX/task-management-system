from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
import urllib.parse

from .auth import CookieJWTAuthentication
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

class CookieJWTHTTPMiddleware(MiddlewareMixin):
    """
    Django HTTP middleware for JWT authentication from cookies.
    Used for regular HTTP requests.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.auth = CookieJWTAuthentication()
    
    def process_request(self, request):
        """
        Authenticate user from JWT token in cookies or headers.
        """
        try:
            result = self.auth.authenticate(request)
            if result:
                user, validated_token = result
                request.user = user
                request.auth = validated_token
            else:
                request.user = AnonymousUser()
        except Exception:
            request.user = AnonymousUser()


class CookieJWTWebSocketMiddleware(BaseMiddleware):
	def __init__(self, inner):
		super().__init__(inner)
		self.auth = CookieJWTAuthentication()

	async def __call__(self, scope, receive, send):
		try:
			jwt_token = await self.get_token(scope)
			if jwt_token:
				user = await self.get_user_from_token(jwt_token)
			else:
				user = AnonymousUser()
		except Exception:
			user = AnonymousUser()

		scope['user'] = user
		return await super().__call__(scope, receive, send)

	async def get_token(self, scope):
		"""
		Extracts the JWT token from cookies, query string, or headers.
		"""
		if scope['type'] == 'websocket':
			query_string = scope.get('query_string', b'').decode('utf-8')
			query_params = urllib.parse.parse_qs(query_string)
			token = query_params.get('token', [None])[0]
			if token:
				return token
		headers = dict(scope.get('headers', []))
		cookie_header = headers.get(b'cookie', b'').decode('utf-8')
		if cookie_header:
			cookies = {k.strip(): v for k, v in (c.split('=', 1) for c in cookie_header.split(';') if '=' in c)}
			token = cookies.get('access_token')
			if token:
				return token
		auth_header = headers.get(b'authorization', b'').decode('utf-8')
		if auth_header.startswith('Bearer '):
			return auth_header.split(' ')[1]

		return None

	@database_sync_to_async
	def get_user_from_token(self, token):
		"""
		Authenticates the user based on the provided token.
		"""
		try:
			validated_token = self.auth.get_validated_token(token)
			return self.auth.get_user(validated_token)
		except Exception:
			return AnonymousUser()


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
		'/auth/login/',
		'/auth/register/',
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
			login_url = '/auth/login/'
			if request.path != '/':
				query_params = urlencode({'next': request.get_full_path()})
				login_url = f"{login_url}?{query_params}"
			
			return HttpResponseRedirect(login_url)
		
		return None

