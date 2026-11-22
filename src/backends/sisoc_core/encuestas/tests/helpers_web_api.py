"""Shared helpers of the encuestas web API tests: a web-ready actor with a real session and form posts."""

import secrets
from urllib.parse import urlencode

from django.contrib.auth.models import Permission, User
from django.test import Client

FORM = "application/x-www-form-urlencoded"


def make_actor(username, codenames):
    secret = secrets.token_urlsafe(24)
    user = User.objects.create_user(
        username=username,
        password=secret,
        first_name="Ana",
        last_name="Gestora",
        email=f"{username}@example.invalid",
    )
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="encuestas", codename__in=codenames
        )
    )
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.dni = f"{secrets.randbelow(10**7) + 10**7}"
    profile.cuil = "20123456786"
    profile.save()
    client = Client(enforce_csrf_checks=True, REMOTE_ADDR="203.0.113.42")
    assert client.get("/api/web/login/").status_code == 200
    response = client.post(
        "/api/web/login/",
        urlencode({"username": username, "password": secret}),
        content_type=FORM,
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert response.status_code == 200
    return user, client


def send(client, path, data=None, *, csrf=True):
    headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if csrf else {}
    return client.post(
        path, urlencode(data or {}, doseq=True), content_type=FORM, **headers
    )


def multipart(client, path, data):
    return client.post(path, data, HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
