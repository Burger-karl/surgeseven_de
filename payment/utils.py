# payment/utils.py
import logging
from django.db import transaction
from .paystack_client import PaystackClient
import requests

logger = logging.getLogger(__name__)

class PaymentProcessor:
    @staticmethod
    def safe_verify_transaction(reference, max_retries=3):
        """
        Safely verify transaction with retry logic and comprehensive logging
        """
        for attempt in range(max_retries):
            try:
                response = PaystackClient.verify_transaction(reference)
                
                if response.get('status'):
                    transaction_data = response['data']
                    
                    logger.info(
                        f"Transaction verification successful - "
                        f"Reference: {reference}, "
                        f"Amount: {transaction_data.get('amount')}, "
                        f"Status: {transaction_data.get('status')}"
                    )
                    
                    return {
                        'success': True,
                        'data': transaction_data,
                        'message': 'Verification successful'
                    }
                else:
                    logger.warning(
                        f"Transaction verification failed - "
                        f"Reference: {reference}, "
                        f"Attempt: {attempt + 1}, "
                        f"Error: {response.get('message')}"
                    )
                    
                    if attempt == max_retries - 1:
                        return {
                            'success': False,
                            'error': response.get('message', 'Verification failed'),
                            'should_retry': False
                        }
                    
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error during verification - "
                    f"Reference: {reference}, "
                    f"Attempt: {attempt + 1}, "
                    f"Error: {str(e)}"
                )
                
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': 'Network error during verification',
                        'should_retry': True
                    }