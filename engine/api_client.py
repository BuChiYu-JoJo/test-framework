# -*- coding: utf-8 -*-
import json as _json
import urllib.request
import urllib.parse

class ApiResponse:
    def __init__(self, resp):
        if hasattr(resp, "status"):
            self.status_code = resp.status
            self._body = resp.read()
            self.headers = dict(resp.headers)
        elif hasattr(resp, "code"):
            self.status_code = resp.code
            self._body = resp.read()
            self.headers = {}
        else:
            self.status_code = 0
            self._body = b""
            self.headers = {}
    @property
    def text(self):
        return self._body.decode("utf-8", errors="replace")
    @property
    def ok(self):
        return 200 <= self.status_code < 300
    def json(self):
        try:
            return _json.loads(self._body)
        except Exception:
            raise ValueError("not json: " + self.text[:200])

class ApiClient:
    def __init__(self, base_url="", timeout=30000, headers=None, retry=0, retry_delay=1.0):
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout
        self.default_headers = headers or {"Content-Type": "application/json", "Accept": "application/json"}
        self.retry = retry
        self.retry_delay = retry_delay
        self._auth_token = None
    def _url(self, url):
        if url.startswith(("http://", "https://")):
            return url
        return (self.base_url + "/" + url.lstrip("/")) if self.base_url else url
    def _do(self, method, url, **kw):
        h = dict(self.default_headers)
        h.update(kw.pop("headers", {}) or {})
        if self._auth_token:
            h["Authorization"] = "Bearer " + self._auth_token
        body = None
        if method in ("POST", "PUT", "PATCH"):
            bdy = kw.pop("json", None)
            if bdy is not None:
                body = _json.dumps(bdy).encode("utf-8")
        req = urllib.request.Request(self._url(url), data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout / 1000.0) as r:
                return ApiResponse(r)
        except urllib.error.HTTPError as e:
            return ApiResponse(e)
        except urllib.error.URLError as e:
            raise TimeoutError("network error: " + str(e.reason))
    def get(self, url, params=None, **kw):
        if params:
            q = urllib.parse.urlencode(params)
            url = (url + "?" + q) if "?" not in url else (url + "&" + q)
        return self._do("GET", url, **kw)
    def post(self, url, json=None, **kw):
        return self._do("POST", url, json=json, **kw)
    def put(self, url, json=None, **kw):
        return self._do("PUT", url, json=json, **kw)
    def delete(self, url, **kw):
        return self._do("DELETE", url, **kw)
    def set_auth(self, token):
        self._auth_token = token
    def assert_status(self, resp, expected):
        if resp.status_code != expected:
            raise AssertionError("expected " + str(expected) + " got " + str(resp.status_code))

_default_client = None
def get_client(base_url="", **kw):
    global _default_client
    if _default_client is None:
        _default_client = ApiClient(base_url, **kw)
    return _default_client
