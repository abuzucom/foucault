import json

from flask import Flask, jsonify, request

from billing import orders, provisioning

app = Flask(__name__)


@app.route("/webhooks/payments", methods=["POST"])
def payment_webhook():
    event = json.loads(request.data)
    kind = event["type"]
    if kind == "payment_succeeded":
        orders.mark_paid(event["order_id"])
    elif kind == "subscription_created":
        provisioning.activate(event["customer_email"])
    return jsonify({"received": True})
