"""
Custom JWT token serializers with RSA support.

This module provides custom JWT token classes that support both RSA and HMAC signing.
"""
import hashlib 
from rest_framework_simplejwt .tokens import RefreshToken ,AccessToken 
from rest_framework_simplejwt .serializers import TokenObtainPairSerializer 
from django .conf import settings 


def get_key_id ():
    """Generate a consistent key ID from the RSA public key."""
    from cryptography .hazmat .primitives import serialization 
    from django .conf import settings 

    try :

        with open (settings .SIMPLE_JWT_PUBLIC_KEY_PATH ,'rb')as f :
            public_key_pem =f .read ()


        key_hash =hashlib .sha256 (public_key_pem ).hexdigest ()
        return key_hash [:16 ]
    except Exception :
        return "default-kid"


class CustomAccessToken (AccessToken ):
    """Custom access token that includes kid in header."""

    @classmethod 
    def for_user (cls ,user ):
        """Override to add kid to header."""
        token =super ().for_user (user )

        if hasattr (token ,'token')and token .token is not None :
            token .token .header ['kid']=get_key_id ()
        return token 


class CustomRefreshToken (RefreshToken ):
    """Custom refresh token that includes kid in header."""

    @classmethod 
    def for_user (cls ,user ):
        """Override to add kid to header."""
        token =super ().for_user (user )

        if hasattr (token ,'token')and token .token is not None :
            token .token .header ['kid']=get_key_id ()
        return token 

    @property 
    def access_token (self ):
        """Returns an access token created from this refresh token."""
        access =CustomAccessToken ()
        access .set_exp ()
        access .set_iat ()
        access .set_jti ()


        access .payload .update ({
        'user_id':self .payload ['user_id'],
        'token_type':'access',
        })

        return access 


class CustomTokenObtainPairSerializer (TokenObtainPairSerializer ):
    """Custom token serializer that uses our custom tokens."""

    token_class =CustomRefreshToken 

    @classmethod 
    def get_token (cls ,user ):
        """Override to use our custom token class."""
        return cls .token_class .for_user (user )

    def validate (self ,attrs ):
        """Override to use custom tokens."""
        data =super ().validate (attrs )
        return data 

        return data 

    @classmethod 
    def get_token (cls ,user ):
        """Get custom refresh token for user."""
        return cls .token_class .for_user (user )
