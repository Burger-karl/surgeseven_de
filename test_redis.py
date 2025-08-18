# import os
# import redis
# import sys
# import ssl
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# def main():
#     print("Testing Redis Cloud connection...")
    
#     # Get environment variables
#     host = os.environ.get('REDIS_HOST')
#     port = os.environ.get('REDIS_PORT')
#     password = os.environ.get('REDIS_PASSWORD')
#     db = os.environ.get('REDIS_DB', '0')
    
#     # Validate environment variables
#     if not host:
#         print("❌ REDIS_HOST environment variable is not set!")
#         return 1
        
#     if not port:
#         print("❌ REDIS_PORT environment variable is not set!")
#         return 1
        
#     if not password:
#         print("❌ REDIS_PASSWORD environment variable is not set!")
#         return 1
    
#     print(f"Host: {host}")
#     print(f"Port: {port}")
#     print(f"DB: {db}")
    
#     try:
#         # Create Redis connection with modern SSL handling
#         r = redis.Redis(
#             host=host,
#             port=int(port),
#             password=password,
#             db=int(db),
#             ssl=True,
#             ssl_cert_reqs=None,
#             ssl_ca_certs=None,
#             socket_connect_timeout=5,
#             socket_timeout=5
#         )
        
#         # Test connection
#         print("Sending PING...")
#         response = r.ping()
#         print(f"✅ PING response: {response}")
        
#         # Test set/get
#         print("Testing SET/GET...")
#         test_key = "surgeseven_test"
#         test_value = "hello-redis-cloud"
        
#         r.set(test_key, test_value, ex=10)
#         value = r.get(test_key)
        
#         if value and value.decode('utf-8') == test_value:
#             print(f"✅ GET response: {value.decode('utf-8')}")
#         else:
#             print(f"❌ GET failed: Expected '{test_value}', got '{value}'")
        
#         # Clean up
#         r.delete(test_key)
#         print("Test key deleted")
        
#         return 0
        
#     except redis.ConnectionError as e:
#         print(f"❌ Connection failed: {e}")
#     except redis.TimeoutError as e:
#         print(f"❌ Timeout error: {e}")
#     except redis.AuthenticationError as e:
#         print(f"❌ Authentication failed: {e}")
#         print("Please check your password")
#     except Exception as e:
#         print(f"❌ Unexpected error: {e}")
#         import traceback
#         traceback.print_exc()
    
#     return 1

# if __name__ == "__main__":
#     sys.exit(main())




import os
import redis
from dotenv import load_dotenv

# Load .env values
load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", 0))

try:
    r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    db=REDIS_DB,
    ssl=True,              # ✅ Enable TLS
    ssl_cert_reqs=None     # ✅ Avoid cert verification issues
)


    # Test connection
    r.set("test_key", "Hello Redis!")
    value = r.get("test_key").decode()
    print("✅ Connected successfully!")
    print("Stored value:", value)

except Exception as e:
    print("❌ Failed to connect:", e)
