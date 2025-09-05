"""
Views for JWT and JWKS endpoints.

This module provides views for:
- JWKS (JSON Web Key Set) endpoint
- JWT public key distribution
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .jwt_utils import get_jwks


@api_view(['GET'])
@permission_classes([AllowAny])
def jwks_endpoint(request):
    """
    JWKS (JSON Web Key Set) endpoint for public key distribution.
    
    This endpoint provides the public keys used to verify JWT tokens.
    It follows the RFC 7517 standard for JSON Web Key Sets.
    
    Returns:
        JSON response containing the public keys in JWKS format
    """
    try:
        jwks_data = get_jwks()
        return JsonResponse(jwks_data, safe=False)
    except Exception as e:
        return JsonResponse(
            {
                "error": "Unable to generate JWKS",
                "detail": str(e)
            }, 
            status=500
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def public_key_endpoint(request):
    """
    Public key endpoint for JWT verification.
    
    Alternative endpoint that returns the public key in PEM format
    for applications that don't support JWKS.
    
    Returns:
        JSON response containing the public key in PEM format
    """
    try:
        from .jwt_utils import get_rsa_public_key, get_key_id
        
        return JsonResponse({
            "public_key": get_rsa_public_key(),
            "key_id": get_key_id(),
            "algorithm": "RS256",
            "use": "sig"
        })
    except Exception as e:
        return JsonResponse(
            {
                "error": "Unable to get public key",
                "detail": str(e)
            }, 
            status=500
        )
