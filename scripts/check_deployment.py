"""Smoke-test a deployed same-origin app using a caller-owned driver account."""
import argparse
import getpass
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    origin = args.url.rstrip("/")
    if not origin.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
        raise SystemExit("Use the HTTPS deployment URL or local loopback.")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(path, body=None):
        headers = {}
        if body is not None:
            token = json.loads(opener.open(origin + "/api/v1/auth/csrf", timeout=90).read())["csrf_token"]
            headers = {"Content-Type": "application/json", "X-CSRF-Token": token}
        response = opener.open(urllib.request.Request(origin + path, data=json.dumps(body).encode() if body is not None else None, headers=headers), timeout=90)
        raw = response.read()
        return json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") and raw else raw
    ready = request("/api/v1/ready")
    assert ready["status"] == "ready" and ready["prediction"] == "ready"
    assert b"<html" in request("/sign-in").lower()
    assert b"<html" in request("/app/session").lower()
    password = getpass.getpass("Driver password (hidden): ")
    logged_in = False
    try:
        assert request("/api/v1/auth/login", {"email": args.email, "password": password})["user"]["role"] == "driver"
        logged_in = True
        assert request("/api/v1/auth/me")["user"]["email"] == args.email
        stations = request("/api/v1/chargers?q=HAMILTON%20%232")["items"]
        station = next(item for item in stations if item["station_key"] == "PALO ALTO CA / HAMILTON #2")
        guidance = request(f"/api/v1/chargers/{station['id']}/guidance?port_type=Level%201")
        assert guidance["available"] and "probability" not in guidance
        assert request("/api/v1/sessions/current")["server_time"]
        assert request("/api/v1/queue")["server_time"]
        try:
            request("/api/v1/research/model")
        except urllib.error.HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("Driver could access research metadata")
        print(json.dumps({"ready": True, "same_origin_routes": True, "driver_login": True, "original_model_advisory": True, "research_restricted": True, "operational_records_changed": False}))
    finally:
        if logged_in:
            request("/api/v1/auth/logout", {})


if __name__ == "__main__":
    main()
