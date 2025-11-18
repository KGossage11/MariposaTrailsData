from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from flask_cors import CORS
from github import Github
import json
import os

app = Flask(__name__)
CORS(app)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")
FILE_PATH = "data.json"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

repo = Github(GITHUB_TOKEN).get_repo(REPO)

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



@app.route('/update', methods=['POST'])
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

        # Save uploaded files, upload to GitHub, and update metadata
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
                        # Upload to GitHub uploads/ folder
                        github_upload_path = f"uploads/{filename}"
                        try:
                            # Check if file exists in repo
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
                                # File does not exist, create it
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
                        # Upload to GitHub uploads/ folder
                        github_upload_path = f"uploads/{filename}"
                        try:
                            # Check if file exists in repo
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
                                # File does not exist, create it
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

        # Increment version number
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
            # If version.json doesn't exist yet
            new_version = 1
            repo.create_file(
                "version.json",
                "Create version.json",
                json.dumps({"version": new_version}, indent=2)
            )

        # Fetch JSON from github
        try:
            file_content = repo.get_contents(FILE_PATH)
            existing_data = json.loads(file_content.decoded_content.decode())
        except Exception:
            # If no data yet
            existing_data = []

        trail_map = {t["name"]: t for t in existing_data}

        for new_trail in new_trails:
            trail_name = new_trail["name"]
            new_trail["version"] = new_version

            if trail_name in trail_map:
                existing_trail = trail_map[trail_name]

                # add new post to existing trail
                existing_posts = existing_trail.get("posts", [])
                existing_post_ids = {p["postID"] for p in existing_posts}

                for post in new_trail.get("posts", []):
                    if post["postID"] not in existing_post_ids:
                        post["version"] = new_version
                        existing_posts.append(post)

                existing_trail["posts"] = existing_posts
                existing_trail["version"] = new_version

            else:
                # for new trail
                for post in new_trail.get("posts", []):
                    post["version"] = new_version
                trail_map[trail_name] = new_trail

        # append new trails
        combined_data = list(trail_map.values())

        # update github file
        content_str = json.dumps(combined_data, indent=2)
        commit_message = f"Admin page update via Flask API (v{new_version})"

        if 'file_content' in locals():
            # Update existing file
            repo.update_file(FILE_PATH, commit_message, content_str, file_content.sha)
        else:
            # Create new file
            repo.create_file(FILE_PATH, commit_message, content_str)

        return jsonify({"success": True, "message": "GitHub data.json updated!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
if __name__ == '__main__':
    app.run(debug=True)