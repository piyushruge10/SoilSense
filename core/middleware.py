from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse


class LoginRequiredMiddleware:
    """Require an authenticated session for every route except account entry points."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = {
            settings.LOGIN_URL,
            reverse("signup"),
            reverse("admin:login"),
            reverse("ingest"),
            # Offline support: must be reachable without a session so the
            # browser can register the service worker and show the offline page.
            reverse("service-worker"),
            reverse("manifest"),
            reverse("offline"),
        }
        self.static_url = settings.STATIC_URL

    def __call__(self, request):
        path = request.path_info
        static_prefix = (
            self.static_url
            if self.static_url.startswith("/")
            else f"/{self.static_url}"
        )
        is_static = bool(self.static_url) and path.startswith(static_prefix)
        if (
            not request.user.is_authenticated
            and path not in self.public_paths
            and not is_static
        ):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
