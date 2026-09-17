import os
import zipfile

from flask import Flask, request

from auth import login_required

app = Flask(__name__)
IMPORT_ROOT = os.path.realpath("/srv/imports")


@app.route("/import", methods=["POST"])
@login_required
def import_archive():
    archive = request.files["archive"]
    archive.save("/tmp/import.zip")
    with zipfile.ZipFile("/tmp/import.zip") as bundle:
        for info in bundle.infolist():
            dest = os.path.realpath(os.path.join(IMPORT_ROOT, info.filename))
            if dest.startswith(IMPORT_ROOT):
                bundle.extract(info, IMPORT_ROOT)
    return "imported"
