from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Flask backend is running!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)