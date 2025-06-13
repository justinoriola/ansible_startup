import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from yaml_file_handler import YamlFileHandler
from playbook_handler import PlaybookHandler

# === Load environment variables ===
load_dotenv('.env')
FLASK_API_KEY = os.environ.get('FLASK_API_KEY')
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'  # Disable SSH key checking for Ansible

# === Initialize Flask app and handlers ===
app = Flask(__name__)
yaml_handler = YamlFileHandler()
playbook_handler = PlaybookHandler()

def is_authorized(req):
    """Validate the incoming request's API key."""
    return req.headers.get("X-API-KEY") == FLASK_API_KEY

@app.route('/epg_deploy', methods=['POST'])
def epg_deploy():
    """
    Accepts EPG deployment data and triggers the Ansible playbook.
    """
    # === Check if the request is authorized ===
    if not is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON", "details": str(e)}), 400

    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Empty or malformed JSON payload"}), 400

    # === Log the received payload for debugging ===
    print("Received payload:\n", json.dumps(data, indent=2))

    try:
        playbook_handler.run_ansible_playbook(data)
        return jsonify({"message": "EPG deployment succeeded"}), 200
    except Exception as e:
        return jsonify({"error": "Ansible playbook execution failed", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
