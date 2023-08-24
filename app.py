from flask import Flask, request, send_file, g
import os
from werkzeug.exceptions import HTTPException
import hashlib
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

UPLOAD_DIR = "store"
USERS = {"alice": "password", "bob": "password"}
OWNERS = {}


def get_file_path(hash):
    return os.path.join(UPLOAD_DIR, hash[:2], hash)


class CustomHTTPException(HTTPException):
    def __init__(self, description, status_code):
        self.description = description
        self.code = status_code
        super().__init__(description)


@auth.verify_password
def verify_password(username, password):
    if username in USERS and USERS[username] == password:
        return username


@app.route("/upload/", methods=["POST"])
@auth.login_required
def upload():
    file = request.files["file"]
    if file.filename == "":
        raise CustomHTTPException("No sended file!", 400)

    file_content = file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    subfolder = file_hash[:2]
    os.makedirs(os.path.join(UPLOAD_DIR, subfolder), exist_ok=True)
    filepath = get_file_path(file_hash)

    with open(filepath, "wb") as f:
        f.write(file_content)
    username = g.flask_httpauth_user
    if username not in OWNERS:
        OWNERS[username] = [file_hash]
    else:
        OWNERS[username].append(file_hash)

    return file_hash


@app.route("/delete/<string:file_hash>", methods=["DELETE"])
@auth.login_required
def delete_file(file_hash):
    file_path = get_file_path(file_hash)

    if os.path.exists(file_path):
        username = g.flask_httpauth_user
        if username in OWNERS and file_hash in OWNERS[username]:
            os.remove(file_path)
            OWNERS[username].remove(file_hash)
            return "File deleted\n"
        else:
            raise CustomHTTPException("You don't have permission to delete this file", 403)
    else:
        raise CustomHTTPException("File not found", 404)


@app.route("/download", methods=["GET"])
def download_file():
    file_hash = request.args.get("file_hash")
    if not file_hash:
        raise CustomHTTPException("Missing file_hash in query parameters", 400)

    file_path = get_file_path(file_hash)
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        raise CustomHTTPException("File not found", 404)


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(debug=True)
