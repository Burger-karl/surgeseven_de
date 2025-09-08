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