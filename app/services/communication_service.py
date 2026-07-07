import os
from datetime import datetime
from flask import current_app

class CommunicationService:
    @staticmethod
    def log_communication(channel, recipient, message):
        """
        Helper to log SMS/Email communications to a local file for demonstration.
        """
        try:
            log_dir = os.path.join(current_app.config['BASE_DIR'], 'app', 'static', 'uploads')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'communication_logs.txt')
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{channel.upper()}] To: {recipient} | Message: {message}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging communication: {e}")
        
        # Print to terminal console
        print(f"\n--- MOCK {channel.upper()} SENT ---")
        print(f"To: {recipient}")
        print(f"Message: {message}")
        print("---------------------------\n")

    @staticmethod
    def send_mock_email(to_email, subject, body):
        """
        Simulate sending an email.
        """
        message = f"Subject: {subject} | Body: {body}"
        CommunicationService.log_communication('email', to_email, message)

    @staticmethod
    def send_mock_sms(to_phone, message):
        """
        Simulate sending an SMS.
        """
        CommunicationService.log_communication('sms', to_phone, message)
