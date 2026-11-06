"""API Gateway proxy entry point for the Flask decision engine."""

import base64
import sys
from io import BytesIO

from app import app


def handler(event, context):
    method, path, query, headers, body = _unpack(event)
    environ = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path or "/",
        "QUERY_STRING": query,
        "SERVER_NAME": headers.get("host", "agrimitra.local"),
        "SERVER_PORT": "443",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.input": BytesIO(body),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body)),
    }
    content_type = headers.get("content-type")
    if content_type:
        environ["CONTENT_TYPE"] = content_type
    for key, value in headers.items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value

    captured = {}

    def start_response(status, response_headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    try:
        text = payload.decode("utf-8")
        encoded = False
    except UnicodeDecodeError:
        text = base64.b64encode(payload).decode("ascii")
        encoded = True

    code = int(captured.get("status", "500 Internal Server Error").split()[0])
    response_headers = {key: value for key, value in captured.get("headers", [])}
    return {
        "statusCode": code,
        "headers": response_headers,
        "body": text,
        "isBase64Encoded": encoded,
    }


def _unpack(event):
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    request_context = event.get("requestContext") or {}
    if "http" in request_context:
        method = request_context["http"].get("method", "GET")
        path = event.get("rawPath") or "/"
        query = event.get("rawQueryString") or ""
    else:
        method = event.get("httpMethod", "GET")
        path = event.get("path") or "/"
        params = event.get("queryStringParameters") or {}
        query = "&".join(f"{k}={v}" for k, v in params.items())
    raw_body = event.get("body") or ""
    if event.get("isBase64Encoded") and raw_body:
        body = base64.b64decode(raw_body)
    else:
        body = raw_body.encode("utf-8")
    return method, path, query, headers, body
