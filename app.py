from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

# Path to local JSON file (in the repo)
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

@app.route('/')
def home():
    return "Mariposa Trails API is running!"

@app.route('/debug-path')
def debug_path():
    return {"current_dir": os.getcwd(), "data_file": DATA_FILE, "exists": os.path.exists(DATA_FILE)}

@app.route('/data', methods=['GET'])
def get_trails():
    try:
        with open(DATA_FILE, 'r') as file:
            data = json.load(file)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)