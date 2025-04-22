import random
import string
from typing import Optional

def generate_random_otp(length: int = 6) -> str:
    """
    Generates a random OTP of the specified length.
    
    Args:
        length (int): Length of the OTP. Default is 6.
    
    Returns:
        str: The generated OTP.
    """
    if length <= 0:
        raise ValueError("OTP length must be greater than 0.")
    
    otp = ''.join(random.choices(string.digits, k=length))  # Generates a 6-digit OTP
    return otp