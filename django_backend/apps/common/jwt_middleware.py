"""
Middleware to configure JWT keys dynamically.
"""
from django .conf import settings 


class JWTKeyConfigurationMiddleware :
    """
    Middleware that ensures JWT keys are properly configured on first request.
    """

    _keys_configured =False 

    def __init__ (self ,get_response ):
        self .get_response =get_response 

    def __call__ (self ,request ):

        if not self ._keys_configured :
            self ._configure_jwt_keys ()

        response =self .get_response (request )
        return response 

    def _configure_jwt_keys (self ):
        """Configure JWT keys."""
        try :
            from apps .common .jwt_utils import get_rsa_private_key ,get_rsa_public_key 


            settings .SIMPLE_JWT ["SIGNING_KEY"]=get_rsa_private_key ()
            settings .SIMPLE_JWT ["VERIFYING_KEY"]=get_rsa_public_key ()

            print ("[JWT] Successfully configured with RSA keys using RS256")
            JWTKeyConfigurationMiddleware ._keys_configured =True 

        except (ImportError ,FileNotFoundError ,PermissionError )as e :
            print (f"[JWT] RSA keys not available ({e }), falling back to HS256")


            settings .SIMPLE_JWT ["ALGORITHM"]="HS256"
            settings .SIMPLE_JWT ["SIGNING_KEY"]=settings .SECRET_KEY 
            settings .SIMPLE_JWT ["VERIFYING_KEY"]=settings .SECRET_KEY 

            JWTKeyConfigurationMiddleware ._keys_configured =True 
