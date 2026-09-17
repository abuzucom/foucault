from flask import Flask, request

from accounts import generate_reset_token, send_reset_email

app = Flask(__name__)


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = request.form["email"]
    token = generate_reset_token(email)
    reset_url = "https://" + request.headers["Host"] + "/reset?token=" + token
    send_reset_email(email, reset_url)
    return "reset email sent"
