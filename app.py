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

@app.route('/update', methods=['POST'])
def update_trails():
    try:
        new_trails = request.get_json(force=True)
        if not isinstance(new_trails, list):
            return jsonify({"error": "Expected a list of trails"}), 400

        # Fetch JSON from github
        try:
            file_content = repo.get_contents(FILE_PATH)
            existing_data = json.loads(file_content.decoded_content.decode())
        except Exception:
            # If no data yet
            existing_data = []

        # append new trails
        combined_data = existing_data + new_trails

        # update github file
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