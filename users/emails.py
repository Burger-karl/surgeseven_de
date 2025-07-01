# import os
# from pathlib import Path
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request

# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent

# SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# def get_gmail_credentials():
#     creds = None
#     token_path = os.path.join(BASE_DIR, 'token.json')
#     credentials_path = os.path.join(BASE_DIR, 'credentials.json')
    
#     if os.path.exists(token_path):
#         creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 credentials_path, SCOPES)
#             creds = flow.run_local_server(port=0)
        
#         with open(token_path, 'w') as token:
#             token.write(creds.to_json())
    
#     return creds


import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

def send_otp_email(to_email, otp_code, subject="Your Verification Code"):
    """
    Send OTP email with HTML template
    Returns True if successful, False otherwise
    """
    # Render HTML template with context
    html_content = render_to_string(
        'templates/users/email/otp_email.html',
        {
            'otp_code': otp_code,
            'current_year': timezone.now().year
        }
    )
    
    # Plain text fallback
    plain_text_content = f"Your verification code is: {otp_code}\n\n" \
                        "This code will expire in 10 minutes. Please don't share it with anyone."
    
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text_content
    )
    
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {e}")
        return False