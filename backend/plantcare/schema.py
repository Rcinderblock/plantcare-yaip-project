from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "plantcare.authentication.CookieJWTAuthentication"
    name = "cookieJwtAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.JWT_ACCESS_COOKIE,
            "description": "JWT access token stored in an HttpOnly cookie.",
        }
