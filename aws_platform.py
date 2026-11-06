"""AWS adapters for AgriMitra AI.

Local runs keep working with an in-memory store. Set the environment variables
from infrastructure/template.yaml to use DynamoDB, S3, Secrets Manager, and
Amazon Bedrock in ap-southeast-2.
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-southeast-2"

_memory = {"profiles": {}, "history": {}}
_secret_cache = None


def architecture():
    return {
        "status": "success",
        "platform": "AgriMitra AI on AWS",
        "region": "ap-southeast-2",
        "stack_overview": "Amazon S3 + CloudFront + API Gateway + Lambda + Amazon Bedrock + DynamoDB",
        "services": [
            {
                "service": "Amazon S3",
                "role": "Static website, reports, images, and agricultural datasets",
                "features": [
                    "Hosts the farmer dashboard for CloudFront.",
                    "Stores advisory reports and uploaded field images.",
                    "Holds reference datasets used by the decision engines.",
                ],
                "badge": "S3 static website and data lake",
                "icon": "hard-drive",
            },
            {
                "service": "Amazon CloudFront",
                "role": "CDN in front of the website and the API",
                "features": [
                    "Serves the dashboard from edge locations.",
                    "Routes /api/* to API Gateway without a separate frontend origin.",
                    "Redirects viewers to HTTPS.",
                ],
                "badge": "CloudFront distribution",
                "icon": "globe",
            },
            {
                "service": "Amazon Route 53",
                "role": "DNS for the optional custom domain",
                "features": [
                    "Alias record from the farmer-facing domain to CloudFront.",
                    "Created only when DomainName and HostedZoneId are supplied.",
                ],
                "badge": "Route 53 alias",
                "icon": "map",
            },
            {
                "service": "Amazon API Gateway",
                "role": "HTTPS API for weather, mandi, crop, and advisory calls",
                "features": [
                    "HTTP API in front of the Lambda decision engine.",
                    "Same routes the local Flask app exposes under /api.",
                ],
                "badge": "API Gateway HTTP API",
                "icon": "radio",
            },
            {
                "service": "AWS Lambda",
                "role": "Serverless decision engine",
                "features": [
                    "Runs crop, climate, and mandi calculations.",
                    "Scales for morning mandi traffic without a standing server.",
                ],
                "badge": "Lambda function",
                "icon": "server",
            },
            {
                "service": "Amazon Bedrock",
                "role": "LLM crop recommendations and farmer Q&A",
                "features": [
                    "Answers farmer questions in English, Telugu, Hindi, Tamil, and Kannada.",
                    "Falls back to the local agronomy rules when the model is not enabled.",
                ],
                "badge": "Bedrock Converse API",
                "icon": "sparkles",
            },
            {
                "service": "Amazon SageMaker",
                "role": "Optional custom price model",
                "features": [
                    "ml/price_model.py is the training and inference entry point.",
                    "The live API uses the built-in forecast until an endpoint is configured.",
                ],
                "badge": "SageMaker custom model, optional",
                "icon": "activity",
            },
            {
                "service": "Amazon DynamoDB",
                "role": "Farmer profiles, crop recommendations, and advisory history",
                "features": [
                    "Single table keyed by farmer id.",
                    "Stores profile records and each decision the API returns.",
                ],
                "badge": "DynamoDB on-demand",
                "icon": "database",
            },
            {
                "service": "Amazon Cognito",
                "role": "Farmer and admin login",
                "features": [
                    "User pool with farmer and admin groups.",
                    "Protects /api/farmer/* when COGNITO_USER_POOL_ID is set.",
                ],
                "badge": "Cognito user pool",
                "icon": "lock",
            },
            {
                "service": "Amazon CloudWatch",
                "role": "Logs, metrics, and the operations dashboard",
                "features": [
                    "Lambda and API Gateway logs.",
                    "Dashboard for errors, latency, and table activity.",
                ],
                "badge": "CloudWatch dashboard",
                "icon": "bar-chart",
            },
            {
                "service": "AWS X-Ray",
                "role": "Traces across API Gateway and Lambda",
                "features": [
                    "Active tracing on the decision function.",
                    "Shows weather, Bedrock, and DynamoDB time in one trace.",
                ],
                "badge": "X-Ray tracing",
                "icon": "share-2",
            },
            {
                "service": "AWS IAM",
                "role": "Least-privilege role for the decision function",
                "features": [
                    "DynamoDB, S3, Bedrock, Secrets Manager, and KMS only.",
                    "No long-lived keys inside the application.",
                ],
                "badge": "IAM execution role",
                "icon": "shield",
            },
            {
                "service": "AWS KMS",
                "role": "Encryption keys for data stores and secrets",
                "features": [
                    "Customer managed key for DynamoDB, S3, and Secrets Manager.",
                    "Automatic yearly rotation.",
                ],
                "badge": "KMS customer managed key",
                "icon": "key",
            },
            {
                "service": "AWS Secrets Manager",
                "role": "Weather and market API credentials",
                "features": [
                    "Holds OpenWeather and IMD keys outside the source tree.",
                    "Read at runtime by the Lambda function.",
                ],
                "badge": "Secrets Manager",
                "icon": "eye-off",
            },
        ],
    }


def _plain(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def _table():
    name = os.environ.get("DYNAMODB_TABLE")
    if not name:
        return None
    import boto3

    return boto3.resource("dynamodb", region_name=REGION).Table(name)


def _summary(path, body):
    if not isinstance(body, dict):
        return {}
    keep = {"path": path}
    for key in ("status", "crop", "language", "powered_by"):
        if key in body and not isinstance(body[key], (dict, list)):
            keep[key] = body[key]
    reply = body.get("reply")
    if isinstance(reply, str):
        keep["reply_excerpt"] = reply[:400]
    best = body.get("best_mandi")
    if isinstance(best, dict):
        keep["best_mandi"] = best.get("mandi_name") or best.get("name")
    recs = body.get("top_recommendations")
    if isinstance(recs, list):
        keep["crops"] = [item.get("crop") for item in recs[:3] if isinstance(item, dict)]
    return keep


def record_decision(path, request_body, response_body):
    """Save a recommendation or advisory. Never raises to the request path."""
    try:
        farmer_id = "anonymous"
        if isinstance(request_body, dict) and request_body.get("farmer_id"):
            farmer_id = str(request_body["farmer_id"])
        item = {
            "pk": f"FARMER#{farmer_id}",
            "sk": f"DECISION#{_now()}#{path}",
            "farmer_id": farmer_id,
            "record_type": "decision",
            "path": path,
            "summary": _summary(path, response_body),
            "created_at": _now(),
        }
        table = _table()
        if table is not None:
            table.put_item(Item=item)
            storage = "dynamodb"
        else:
            _memory["history"].setdefault(farmer_id, []).append(item)
            storage = "memory"
        report_key = f"advisories/{farmer_id}/{item['sk'].replace('#', '_')}.json"
        stored_report = put_report(report_key, {"request": request_body, "summary": item["summary"]})
        return {"storage": storage, "report": stored_report}
    except Exception as exc:
        logger.warning("Decision was not stored: %s", exc)
        return {"storage": "skipped", "error": str(exc)}


def save_profile(profile):
    farmer_id = str(profile.get("farmer_id") or "").strip()
    if not farmer_id:
        raise ValueError("farmer_id is required")
    item = {
        "pk": f"FARMER#{farmer_id}",
        "sk": "PROFILE",
        "farmer_id": farmer_id,
        "record_type": "profile",
        "name": profile.get("name", ""),
        "phone": profile.get("phone", ""),
        "state": profile.get("state", ""),
        "district": profile.get("district", ""),
        "language": profile.get("language", "en"),
        "updated_at": _now(),
    }
    table = _table()
    if table is not None:
        table.put_item(Item=item)
        storage = "dynamodb"
    else:
        _memory["profiles"][farmer_id] = item
        storage = "memory"
    return {"storage": storage, "profile": item}


def get_profile(farmer_id):
    table = _table()
    if table is not None:
        result = table.get_item(Key={"pk": f"FARMER#{farmer_id}", "sk": "PROFILE"})
        return _plain(result.get("Item"))
    return _memory["profiles"].get(farmer_id)


def list_history(farmer_id, limit=20):
    table = _table()
    if table is not None:
        from boto3.dynamodb.conditions import Key

        result = table.query(
            KeyConditionExpression=Key("pk").eq(f"FARMER#{farmer_id}") & Key("sk").begins_with("DECISION#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        return _plain(result.get("Items", []))
    rows = list(_memory["history"].get(farmer_id, []))
    rows.reverse()
    return rows[:limit]


def put_report(key, payload):
    body = json.dumps(payload, default=str).encode("utf-8")
    bucket = os.environ.get("REPORTS_BUCKET")
    if not bucket:
        return {"storage": "inline", "key": key}
    import boto3

    extra = {"ContentType": "application/json"}
    kms_key = os.environ.get("KMS_KEY_ID")
    if kms_key:
        extra["ServerSideEncryption"] = "aws:kms"
        extra["SSEKMSKeyId"] = kms_key
    boto3.client("s3", region_name=REGION).put_object(Bucket=bucket, Key=key, Body=body, **extra)
    return {"storage": "s3", "bucket": bucket, "key": key}


def weather_credentials():
    """Load market and weather API keys from Secrets Manager when configured."""
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    arn = os.environ.get("WEATHER_SECRET_ARN")
    if not arn:
        _secret_cache = {}
        return _secret_cache
    import boto3

    raw = boto3.client("secretsmanager", region_name=REGION).get_secret_value(SecretId=arn)
    _secret_cache = json.loads(raw.get("SecretString") or "{}")
    return _secret_cache


def bedrock_reply(query, language):
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        return None
    import boto3

    names = {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada"}
    system = (
        "You are AgriMitra AI, an agronomist for Indian smallholder farmers. "
        f"Reply in {names.get(language, 'English')}. "
        "Cover climate risk, crop choice, mandi selling, and fertilizer with short practical steps. "
        "The PMFBY crop insurance helpline is 1800-180-1551 and claims should be filed within 72 hours."
    )
    response = boto3.client("bedrock-runtime", region_name=REGION).converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": query}]}],
        inferenceConfig={"maxTokens": 700, "temperature": 0.3},
    )
    parts = response.get("output", {}).get("message", {}).get("content", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    return text or None


def verify_cognito_token(token):
    pool_id = os.environ.get("COGNITO_USER_POOL_ID")
    if not pool_id:
        return None
    import jwt
    from jwt import PyJWKClient

    region = REGION
    url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"
    signing_key = PyJWKClient(url).get_signing_key_from_jwt(token)
    audience = os.environ.get("COGNITO_APP_CLIENT_ID")
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        options={"verify_aud": bool(audience)},
    )


def fetch_openweather(lat, lon):
    """Return an Open-Meteo shaped forecast when an OpenWeather key is configured."""
    secret = {}
    if os.environ.get("OPENWEATHER_API_KEY"):
        secret["OPENWEATHER_API_KEY"] = os.environ["OPENWEATHER_API_KEY"]
    else:
        try:
            secret = weather_credentials()
        except Exception:
            logger.warning("Weather secret could not be read")
            return None
    key = secret.get("OPENWEATHER_API_KEY")
    if not key:
        return None
    try:
        import requests

        current = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "units": "metric", "appid": key},
            timeout=4,
        )
        forecast = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "units": "metric", "appid": key},
            timeout=4,
        )
        if current.status_code != 200 or forecast.status_code != 200:
            return None
        now = current.json()
        days = {}
        for row in forecast.json().get("list", []):
            day = row["dt_txt"][:10]
            bucket = days.setdefault(day, {"temps": [], "rain": 0.0, "pop": 0, "code": 1})
            bucket["temps"].append(row["main"]["temp"])
            bucket["rain"] += row.get("rain", {}).get("3h", 0.0)
            bucket["pop"] = max(bucket["pop"], int(row.get("pop", 0) * 100))
            bucket["code"] = _ow_code(row["weather"][0]["id"])
        ordered = list(days.items())[:7]
        return {
            "current": {
                "temperature_2m": now["main"]["temp"],
                "relative_humidity_2m": now["main"]["humidity"],
                "precipitation": now.get("rain", {}).get("1h", 0.0),
                "weather_code": _ow_code(now["weather"][0]["id"]),
                "wind_speed_10m": now["wind"]["speed"] * 3.6,
            },
            "daily": {
                "time": [day for day, _ in ordered],
                "weather_code": [info["code"] for _, info in ordered],
                "temperature_2m_max": [round(max(info["temps"]), 1) for _, info in ordered],
                "temperature_2m_min": [round(min(info["temps"]), 1) for _, info in ordered],
                "precipitation_sum": [round(info["rain"], 1) for _, info in ordered],
                "precipitation_probability_max": [info["pop"] for _, info in ordered],
            },
        }
    except Exception:
        logger.warning("OpenWeather request failed")
        return None


def _ow_code(code):
    if code == 800:
        return 0
    if code == 801:
        return 1
    if code == 802:
        return 2
    if code in (803, 804):
        return 3
    if 200 <= code < 300:
        return 95
    if 300 <= code < 400:
        return 51
    if code in (500, 501):
        return 61
    if 502 <= code < 600:
        return 65
    if 600 <= code < 700:
        return 71
    if 700 <= code < 800:
        return 45
    return 1
