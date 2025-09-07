"""
JWT utilities for RSA key management and JWKS generation.

This module provides utilities for:
- Loading RSA public/private keys
- Generating JWKS (JSON Web Key Set)
- JWT token validation with RSA
"""
import json 
import base64 
from pathlib import Path 
from cryptography .hazmat .primitives import serialization 
from cryptography .hazmat .primitives .asymmetric import rsa 
from django .conf import settings 
import hashlib 


class RSAKeyManager :
    """Manager for RSA keys used in JWT signing and verification."""

    def __init__ (self ):
        self .keys_dir =Path (settings .BASE_DIR )/'config'/'keys'
        self .private_key_path =self .keys_dir /'jwt_private_key.pem'
        self .public_key_path =self .keys_dir /'jwt_public_key.pem'


        self ._private_key =None 
        self ._public_key =None 
        self ._kid =None 

    def get_private_key (self ):
        """Load and return the private RSA key."""
        if self ._private_key is None :
            if not self .private_key_path .exists ():
                raise FileNotFoundError (f"Private key not found at {self .private_key_path }")

            with open (self .private_key_path ,'rb')as key_file :
                self ._private_key =serialization .load_pem_private_key (
                key_file .read (),
                password =None 
                )
        return self ._private_key 

    def get_public_key (self ):
        """Load and return the public RSA key."""
        if self ._public_key is None :
            if not self .public_key_path .exists ():
                raise FileNotFoundError (f"Public key not found at {self .public_key_path }")

            with open (self .public_key_path ,'rb')as key_file :
                self ._public_key =serialization .load_pem_public_key (
                key_file .read ()
                )
        return self ._public_key 

    def get_private_key_pem (self ):
        """Get private key as PEM string."""
        private_key =self .get_private_key ()
        return private_key .private_bytes (
        encoding =serialization .Encoding .PEM ,
        format =serialization .PrivateFormat .PKCS8 ,
        encryption_algorithm =serialization .NoEncryption ()
        ).decode ('utf-8')

    def get_public_key_pem (self ):
        """Get public key as PEM string."""
        public_key =self .get_public_key ()
        return public_key .public_bytes (
        encoding =serialization .Encoding .PEM ,
        format =serialization .PublicFormat .SubjectPublicKeyInfo 
        ).decode ('utf-8')

    def get_key_id (self ):
        """Generate a unique key ID (kid) for this key pair."""
        if self ._kid is None :

            public_key_pem =self .get_public_key_pem ()
            key_hash =hashlib .sha256 (public_key_pem .encode ()).hexdigest ()
            self ._kid =key_hash [:16 ]
        return self ._kid 

    def get_jwk (self ):
        """Generate JWK (JSON Web Key) for the public key."""
        public_key =self .get_public_key ()


        public_numbers =public_key .public_numbers ()


        def int_to_base64url (value ):

            byte_length =(value .bit_length ()+7 )//8 
            value_bytes =value .to_bytes (byte_length ,byteorder ='big')
            return base64 .urlsafe_b64encode (value_bytes ).decode ('utf-8').rstrip ('=')

        n =int_to_base64url (public_numbers .n )
        e =int_to_base64url (public_numbers .e )

        return {
        "kty":"RSA",
        "use":"sig",
        "alg":"RS256",
        "kid":self .get_key_id (),
        "n":n ,
        "e":e 
        }

    def get_jwks (self ):
        """Generate JWKS (JSON Web Key Set) containing the public key."""
        return {
        "keys":[self .get_jwk ()]
        }



rsa_key_manager =RSAKeyManager ()


def get_rsa_private_key ():
    """Get the RSA private key for JWT signing."""
    return rsa_key_manager .get_private_key_pem ()


def get_rsa_public_key ():
    """Get the RSA public key for JWT verification."""
    return rsa_key_manager .get_public_key_pem ()


def get_jwks ():
    """Get the JWKS (JSON Web Key Set) for public key distribution."""
    return rsa_key_manager .get_jwks ()


def get_key_id ():
    """Get the key ID for the current RSA key pair."""
    return rsa_key_manager .get_key_id ()
