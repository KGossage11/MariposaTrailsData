from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from flask_cors import CORS
from github import Github
import json
import os
import bcrypt
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)

# === AUTH CONFIG ===
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")  # bcrypt hash
JWT_SECRET = os.getenv("JWT_SECRET")  # secret for signing tokens
JWT_EXPIRATION_HOURS = 4

if not ADMIN_PASSWORD_HASH:
    print("WARNING: ADMIN_PASSWORD_HASH not set!")
if not JWT_SECRET:
    print("WARNING: JWT_SECRET not set!")

# === GITHUB CONFIG ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")
FILE_PATH = "data.json"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

repo = Github(GITHUB_TOKEN).get_repo(REPO)

# ----------------------------------------------------------
# AUTH MIDDLEWARE
# ----------------------------------------------------------

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401

        token = auth_header.split(" ")[1]

        try:
            jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return func(*args, **kwargs)

    return wrapper

# ----------------------------------------------------------
# LOGIN ENDPOINT
# ----------------------------------------------------------

@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    password = data.get("password")

    if not password:
        return jsonify({"error": "Password required"}), 400

    try:
        # Compare plaintext password to stored bcrypt hash
        if not bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH.encode()):
            return jsonify({"error": "Invalid password"}), 401
    except Exception as e:
        return jsonify({"error": f"Hash comparison failed: {str(e)}"}), 500

    # Create JWT token
    exp = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    token = jwt.encode({"exp": exp, "role": "admin"}, JWT_SECRET, algorithm="HS256")

    return jsonify({"token": token})

# ----------------------------------------------------------
# PUBLIC ROUTES (unchanged)
# ----------------------------------------------------------

@app.route('/')
def home():
    return "Mariposa Trails API is running!"

@app.route('/data', methods=['GET'])
def get_trails():
    try:
        file_content = repo.get_contents(FILE_PATH)
        data = json.loads(file_content.decoded_content.decode())
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/version', methods=['GET'])
def get_version():
    try:
        version_file = repo.get_contents("version.json")
        version_data = json.loads(version_file.decoded_content.decode())
        return jsonify(version_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------
# PROTECTED UPDATE ROUTE (same logic, auth added)
# ----------------------------------------------------------

@app.route('/update', methods=['POST'])
@require_auth
def update_trails():
    try:
        # Parse trails metadata from form
        trails_json = request.form.get('trails')
        if not trails_json:
            return jsonify({"error": "Missing trails metadata"}), 400
        try:
            new_trails = json.loads(trails_json)
        except Exception as e:
            return jsonify({"error": f"Invalid trails JSON: {str(e)}"}), 400
        if not isinstance(new_trails, list):
            return jsonify({"error": "Expected a list of trails"}), 400

        # Save uploaded files and upload to GitHub
        for t_index, trail in enumerate(new_trails):
            for p_index, post in enumerate(trail.get('posts', [])):
                # Handle images
                image_files = []
                i = 0
                while True:
                    field_name = f"trail{t_index}_post{p_index}_image{i}"
                    if field_name in request.files:
                        file = request.files[field_name]
                        filename = secure_filename(file.filename)
                        save_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(save_path)
                        github_upload_path = f"uploads/{filename}"
                        try:
                            try:
                                existing_file = repo.get_contents(github_upload_path)
                                with open(save_path, "rb") as f:
                                    repo.update_file(
                                        github_upload_path,
                                        f"Update {filename}",
                                        f.read(),
                                        existing_file.sha
                                    )
                            except Exception:
                                with open(save_path, "rb") as f:
                                    repo.create_file(
                                        github_upload_path,
                                        f"Add {filename}",
                                        f.read()
                                    )
                        except Exception as e:
                            print(f"Error uploading {filename} to GitHub: {e}")
                        image_files.append(github_upload_path)
                        i += 1
                    else:
                        break
                if image_files:
                    post['images'] = image_files

                # Handle audio
                audio_files = []
                i = 0
                while True:
                    field_name = f"trail{t_index}_post{p_index}_audio{i}"
                    if field_name in request.files:
                        file = request.files[field_name]
                        filename = secure_filename(file.filename)
                        save_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(save_path)
                        github_upload_path = f"uploads/{filename}"
                        try:
                            try:
                                existing_file = repo.get_contents(github_upload_path)
                                with open(save_path, "rb") as f:
                                    repo.update_file(
                                        github_upload_path,
                                        f"Update {filename}",
                                        f.read(),
                                        existing_file.sha
                                    )
                            except Exception:
                                with open(save_path, "rb") as f:
                                    repo.create_file(
                                        github_upload_path,
                                        f"Add {filename}",
                                        f.read()
                                    )
                        except Exception as e:
                            print(f"Error uploading {filename} to GitHub: {e}")
                        audio_files.append(github_upload_path)
                        i += 1
                    else:
                        break
                if audio_files:
                    post['audio'] = audio_files

        # Increment version
        try:
            version_file = repo.get_contents("version.json")
            version_data = json.loads(version_file.decoded_content.decode())
            current_version = version_data.get("version", 0)
            new_version = current_version + 1
            repo.update_file(
                "version.json",
                f"Increment version to {new_version}",
                json.dumps({"version": new_version}, indent=2),
                version_file.sha
            )
        except Exception:
            new_version = 1
            repo.create_file(
                "version.json",
                "Create version.json",
                json.dumps({"version": new_version}, indent=2)
            )

        # Overwrite data.json
        for trail in new_trails:
            trail["version"] = new_version
            for post in trail.get("posts", []):
                post["version"] = new_version

        content_str = json.dumps(new_trails, indent=2)
        commit_message = f"Admin page update via Flask API (v{new_version})"

        try:
            file_content = repo.get_contents(FILE_PATH)
            repo.update_file(FILE_PATH, commit_message, content_str, file_content.sha)
        except Exception:
            repo.create_file(FILE_PATH, commit_message, content_str)

        return jsonify({"success": True, "message": "GitHub data.json updated!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)
