import resend
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Configure Resend
resend.api_key = settings.RESEND_API_KEY

def send_otp_email(to_email, otp_code, subject="Your Verification Code"):
    """
    Send OTP email with HTML template using Resend
    Returns True if successful, False otherwise
    """
    try:
        # Render HTML template with context
        html_content = render_to_string(
            'users/email/otp_email.html',  # Fixed path - removed 'templates/'
            {
                'otp_code': otp_code,
                'current_year': timezone.now().year,
                'email': to_email
            }
        )
        
        # Plain text fallback
        plain_text_content = f"""
        Your SurgeSeven Verification Code

        Hello,

        Your verification code is: {otp_code}

        This code will expire in 10 minutes. Please don't share it with anyone.

        If you didn't request this code, please ignore this email.

        Best regards,
        SurgeSeven Team
        """
        
        # Create email parameters
        params = {
            "from": f"SurgeSeven <{settings.DEFAULT_FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "text": plain_text_content,
            "reply_to": settings.DEFAULT_REPLY_TO_EMAIL,  # Optional
        }
        
        # Send email using Resend
        response = resend.Emails.send(params)
        
        # Log successful email sending
        logger.info(f"OTP email sent successfully to {to_email}. Resend ID: {response['id']}")
        return True
        
    except Exception as e:
        # Handle all Resend errors
        logger.error(f"Resend error sending OTP to {to_email}: {str(e)}")
        return False
        
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Unexpected error sending OTP to {to_email}: {str(e)}")
        return False


def send_welcome_email(to_email, username):
    """
    Send welcome email after successful registration
    """
    try:
        html_content = render_to_string(
            'users/email/welcome_email.html',
            {
                'username': username,
                'current_year': timezone.now().year,
                'site_url': settings.SITE_URL  # Add this to your settings
            }
        )
        
        plain_text_content = f"""
        Welcome to SurgeSeven, {username}!

        🎉 Your account has been successfully created and verified!

        We're excited to have you join our community of clients who trust us for their logistics and delivery needs.

        GET STARTED:
        • Complete your profile for faster booking
        • Book your first delivery in just a few clicks
        • Track your shipments in real-time
        • Manage all your deliveries from one dashboard

        Ready to begin? Visit: {settings.SITE_URL}

        NEED HELP?
        Our support team is always ready to assist you:
        📧 Email: support@surgesevenltd.com
        📞 Phone: +234-XXX-XXXX-XXX

        Best regards,
        The SurgeSeven Team

        ---
        SurgeSeven Ltd.
        123 Business District, Lagos, Nigeria
        © {timezone.now().year} SurgeSeven Ltd. All rights reserved.
        """
        
        params = {
            "from": f"SurgeSeven <{settings.DEFAULT_FROM_EMAIL}>",
            "to": [to_email],
            "subject": f"🚀 Welcome to SurgeSeven, {username}!",
            "html": html_content,
            "text": plain_text_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Welcome email sent to {to_email}. Resend ID: {response['id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {to_email}: {str(e)}")
        return False
    

def send_password_reset_email(to_email, reset_token, reset_url):
    """
    Send password reset email
    """
    try:
        html_content = render_to_string(
            'users/email/password_reset.html',
            {
                'reset_url': reset_url,
                'reset_token': reset_token,
                'current_year': timezone.now().year
            }
        )
        
        plain_text_content = f"""
        Password Reset Request

        You requested to reset your password. Use the following token:

        Reset Token: {reset_token}

        Or click this link: {reset_url}

        This link will expire in 1 hour.

        If you didn't request this, please ignore this email.

        Best regards,
        SurgeSeven Team
        """
        
        params = {
            "from": f"SurgeSeven <{settings.DEFAULT_FROM_EMAIL}>",
            "to": [to_email],
            "subject": "Reset Your SurgeSeven Password",
            "html": html_content,
            "text": plain_text_content,
        }
        
        response = resend.Emails.send(params)
        logger.info(f"Password reset email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending password reset email to {to_email}: {str(e)}")
        return False