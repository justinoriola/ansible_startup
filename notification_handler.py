import locale
from twilio.rest import Client
from datetime import datetime
from twilio.http.http_client import TwilioHttpClient
import json
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv('.env')

# Set locale to US English (comma as thousands separator)
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


class NotificationHandler:

    def __init__(self):
        # declare instance objects to unpack environment variables
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        # Twilio test credentials
        self.twilio_test_account_sid = os.getenv('TWILIO_TEST_ACCOUNT_SID')
        self.twilio_test_auth = os.getenv('TWILIO_TEST_AUTH_TOKEN')
        self.twilio_test_whatsapp_number = "whatsapp:" + os.getenv('TWILIO_TEST_NUMBER')

        # Optional: Increase timeout
        self.http_client = TwilioHttpClient(timeout=60)  # 60 seconds timeout
        self.client = Client(self.twilio_account_sid, self.twilio_auth, http_client=self.http_client)

    @staticmethod
    def get_content_variables(data):
        """
        Returns a dictionary of content variables for quick reply messages.
        """
        return    {
            "1": f"{data.get('CONSUMED_EPG', 'N/A')}",
            "2": f"{data.get('PROVIDED_EPG', 'N/A')}",
            "3": f"{data.get('CONTRACT_NAME', 'N/A')}",
            "4": f"{data.get('SUBJECT_NAME', 'N/A')}",
            "5": f"{data.get('VZ_FILTER_NAME', 'N/A')}",
            "6": f"{data.get('IP_PROTOCOL', 'N/A')}",
            "7": f"{data.get('PORTS_FROM', 'N/A')}",
            "8": f"{data.get('PORTS_TO', 'N/A')}",
            "9": f"{data.get('ACTION', 'N/A')}",
            "10": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        }
    def log_time(self):
        date_time = datetime.now()
        log_time = (lambda dt: dt.strftime("[%d/%b/%Y %H:%M:%S]"))(date_time)
        return log_time

    def send_whatsapp_message(self, recipient, message, twilio_cred_flag=False, **kwargs):
        """
        Sends a WhatsApp message using Twilio API.

        - If `content_sid` and `content_variables` are provided, sends a template-based message.
        - Otherwise, sends a plain text message.
        - Falls back to test credentials if `twilio_cred_flag` is True.
        """

        try:
            # === Validate recipient ===
            if not isinstance(recipient, str) or not recipient.strip():
                raise ValueError(f"{self.log_time()} Recipient number is required and must be a non-empty string.")

            # === Validate message ===
            if not isinstance(message, str) or not message.strip():
                raise ValueError(f"{self.log_time()} Message is required and must be a non-empty string.")

            # === Use test credentials if flag is enabled ===
            if twilio_cred_flag:
                self.client = Client(self.twilio_test_account_sid, self.twilio_test_auth)
                from_number = self.twilio_test_whatsapp_number
            else:
                from_number = f"whatsapp:{self.twilio_whatsapp_number}"

            # === Unpack template parameters ===
            content_sid = kwargs.get("content_sid")
            content_variables = kwargs.get("content_variables", {})

            # === Send template-based message if both parameters are valid ===
            if content_sid and isinstance(content_sid, str) and isinstance(content_variables, dict):
                message_response = self.client.messages.create(
                    to=recipient,
                    from_=from_number,
                    content_sid=content_sid,
                    content_variables=json.dumps(content_variables),
                )
            else:
                # === Send plain message ===
                message_response = self.client.messages.create(
                    to=recipient,
                    from_=from_number,  # Twilio's WhatsApp sandbox number
                    content_sid=content_sid,
                    content_variables=content_variables,
                )
            print(f"{self.log_time()} Notification sent! Message SID: {message_response.sid}")

        except Exception as e:
            print(f"{self.log_time()} Failed to send message: {e}")
            return None

    @staticmethod
    def compose_deployment_report_message(**kwargs):
        """
        Composes a deployment report notification message after deployment completion.
        Expects deployment details as keyword arguments.
        Returns a formatted string report or None if an error occurs.
        """
        try:
            data = kwargs.get('data', {})
            if not data or not isinstance(data, dict):
                raise ValueError("No deployment data provided or invalid format")

            # Define deployment detail fields
            table_rows = [
                ("Consumer EPG", data.get('CONSUMED_EPG', "N/A")),
                ("Provider EPG", data.get('PROVIDED_EPG', "N/A")),
                ("Contract Name", data.get('CONTRACT_NAME', "N/A")),
                ("Subject", data.get('SUBJECT_NAME', "N/A")),
                ("Filter", data.get('VZ_FILTER_NAME', "N/A")),
                ("Protocol", data.get('IP_PROTOCOL', "N/A")),
                ("Port From", data.get('PORTS_FROM', "N/A")),
                ("Port To", data.get('PORTS_TO', "N/A")),
                ("Action", data.get('ACTION', "N/A")),
            ]

            # Build message lines
            lines = [
                "===================================",
                "Deployment Details:",
                "-----------------------------------",
            ]
            # === Format each row in the table ===
            for label, value in table_rows:
                lines.append(f"  - {label.ljust(20)}: {value}")

            # === Add summary and source information ===
            lines.extend([
                "===================================",
                "Source: ACI Automation System"
                f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
                "===================================",
            ])
            # === Add footer with contact information ===
            return "\n".join(lines)

        except Exception as e:
            print(f"Error composing deployment report message: {e}")
            return None