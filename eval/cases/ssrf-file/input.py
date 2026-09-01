import requests
from flask import request, jsonify


def fetch_preview():
    url = request.args.get("url")
    resp = requests.get(url, timeout=5)
    return jsonify({"status": resp.status_code, "body": resp.text[:2000]})
