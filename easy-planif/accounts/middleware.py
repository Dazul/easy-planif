from django.shortcuts import redirect
from django.urls import resolve, Resolver404


class RequirePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(
            request.user,
            "must_change_password",
            False,
        ):
            allowed_names = {
                "password_change",
                "password_change_done",
                "logout",
            }
            try:
                current_name = resolve(request.path_info).view_name
            except Resolver404:
                current_name = None

            if current_name not in allowed_names:
                return redirect("password_change")

        return self.get_response(request)
