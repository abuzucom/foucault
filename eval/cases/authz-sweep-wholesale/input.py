from functools import wraps

from flask import Flask, g, request

app = Flask(__name__)


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.get("user"):
            return {"error": "unauthorized"}, 401
        return fn(*args, **kwargs)
    return wrapper


@app.get("/reports/<report_id>")
@require_login
def get_report(report_id):
    return Report.query.get(report_id).to_dict()


@app.post("/reports")
@require_login
def create_report():
    return Report.create(owner=g.user, **request.json).to_dict()


@app.get("/reports/<report_id>/export")
def export_report(report_id):
    return Report.query.get(report_id).to_csv()


@app.post("/admin/reimburse")
@require_login
def reimburse():
    return Payout.create(**request.json).to_dict()
