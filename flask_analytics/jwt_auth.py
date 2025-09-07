import os, json, time
import httpx, jwt
from jwt import PyJWKClient
from flask import request, abort, g
from redis import Redis

ISS = os.getenv("JWT_ISSUER")
JWKS = os.getenv("JWT_JWKS_URL")
REDIS_URL = os.getenv("ANALYTICS_REDIS_URL")
JWKS_TTL = int(os.getenv("JWT_JWKS_TTL", "900"))

_r = Redis.from_url(REDIS_URL) if REDIS_URL else None


def _decode_rs256(token: str) -> dict:
    try:
        jwk_client = PyJWKClient(JWKS, cache_keys=True)
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
    except Exception:
        try:
            import httpx

            response = httpx.get(JWKS)
            jwks = response.json()
            if jwks.get("keys"):
                first_key = jwks["keys"][0]
                from jwt.algorithms import RSAAlgorithm

                signing_key = RSAAlgorithm.from_jwk(first_key)
            else:
                raise Exception("No keys found in JWKS")
        except Exception as e2:
            raise e2

    decoded = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        options={"require": ["exp", "iat"], "verify_aud": False, "verify_iss": False},
        leeway=30,
    )
    return decoded


def jwt_required(fn):
    def inner(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            abort(401)

        token = auth.split(" ", 1)[1]
        try:
            claims = _decode_rs256(token)
        except Exception:
            try:
                import httpx

                response = httpx.get(JWKS)
                jwks = response.json()
                if jwks.get("keys"):
                    first_key = jwks["keys"][0]
                    from jwt.algorithms import RSAAlgorithm

                    signing_key = RSAAlgorithm.from_jwk(first_key)
                    claims = jwt.decode(
                        token,
                        signing_key,
                        algorithms=["RS256"],
                        options={
                            "require": ["exp", "iat"],
                            "verify_aud": False,
                            "verify_iss": False,
                        },
                        leeway=30,
                    )
                else:
                    abort(401)
            except Exception:
                abort(401)

        g.user_id = claims.get("user_id") or claims.get("sub")
        g.is_staff = bool(claims.get("is_staff") or claims.get("staff", False))
        g.scopes = claims.get("scope") or claims.get("scopes") or []

        if not g.user_id:
            abort(401)
        return fn(*args, **kwargs)

    inner.__name__ = fn.__name__
    return inner
