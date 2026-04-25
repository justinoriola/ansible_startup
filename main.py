import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from validation_handler import ValidationHandler
from file_handler import FileHandler
from playbook_handler import PlaybookHandler
from notification_handler import NotificationHandler

# === Load environment variables ===
os.environ['ANSIBLE_HOST_KEY_CHECKING'] = 'False'  # Disable SSH key checking for Ansible
MY_NUMBER = "whatsapp:" + os.getenv('MY_NUMBER')

# === Initialize Flask app and handlers ===
app = Flask(__name__)
file_handler = FileHandler()
notification_handler = NotificationHandler()
playbook_handler = PlaybookHandler()


@app.route('/epg_deploy/R5T_0MrK9', methods=['POST'])
def epg_deploy():
    """
    Accepts EPG deployment data and triggers the Ansible playbook.
    """
    # === Check if the request is authorized ===
    if not ValidationHandler.is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON", "details": str(e)}), 400

    # === Check requirement for spreadsheet or payload data ===
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Empty or malformed JSON payload"}), 400

    # === Log the received payload for debugging ===
    # print("Received payload:\n", json.dumps(data, indent=2))

    # Extract the payload from the data
    payload = data.get("payload")

    # If payload is a dictionary and not the string "spreadsheet", extract it
    if isinstance(payload, dict):
        data = payload

    # If payload is explicitly the string "spreadsheet", load data from the spreadsheet source
    elif payload == "spreadsheet":
        data = file_handler.aci_spreadsheet_directory[-1]  # Use the latest spreadsheet data

    try:
        # === Deploy EPG ===
        result = playbook_handler.run_ansible_playbook(data)
        if not result or result[0] != 0:
            raise RuntimeError(f"Ansible playbook execution failed")

        # === Update spreadsheet data if payload is a dictionary ===
        if isinstance(payload, dict):
            file_handler.update_spreadsheet_data(data)

        # === Compose message send notification after successful deployment ===
        message = notification_handler.compose_deployment_report_message(data=data)
        content_variables = notification_handler.get_content_variables(data)
        test_aci_content_sid = "HX7fa17c029ae3f32ab865bbb3cfd77eaa"

        # === Send WhatsApp message notification ===
        if message:
            try:
                notification_handler.send_whatsapp_message(
                    MY_NUMBER,
                    message,
                    content_sid=test_aci_content_sid,
                    content_variables=content_variables
                )
            except Exception as e:
                print(f"Failed to send WhatsApp message: {e}")

        return jsonify({"message": "EPG deployment succeeded"}), 200
    except Exception as e:
        return jsonify({
            "error": "EPG deployment failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
