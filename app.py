from flask import Flask, jsonify, request
from flask_cors import CORS
from github import Github
import json
import os


app = Flask(__name__)
CORS(app)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")
FILE_PATH = "data.json"

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO)

@app.route('/')
def home():
    return "Mariposa Trails API is running!"

@app.route('/data', methods=['GET'])
def get_trails():
    try:
        # Load local file if exists
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, 'r') as f:
                data = json.load(f)
        else:
            data = []
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update', methods=['POST'])
def update_trails():
    try:
        new_trails = request.get_json(force=True)
        if not isinstance(new_trails, list):
            return jsonify({"error": "Expected a list of trails"}), 400

        # --- Step 1: fetch existing JSON from GitHub ---
        try:
            file_content = repo.get_contents(FILE_PATH)
            existing_data = json.loads(file_content.decoded_content.decode())
        except Exception:
            # If file doesn't exist yet
            existing_data = []

        # --- Step 2: append new trails ---
        combined_data = existing_data + new_trails

        # --- Step 3: update the GitHub file ---
        content_str = json.dumps(combined_data, indent=2)
        commit_message = "Admin page update via Flask API"

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