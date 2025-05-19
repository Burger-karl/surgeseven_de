# import requests
# from django.conf import settings

# ITRACKSAFEX_API_URL = "https://itracksafe.com/webapi"

# def create_tracker_account(username, password, usertype, multilogin=1):
#     """
#     Create a new account on the iTrackSafeX API.
#     """
#     payload = {
#         "action": "adduser",
#         "username": username,
#         "password": password,  # Password should be MD5 hashed
#         "usertype": usertype,
#         "multilogin": multilogin,
#     }

#     try:
#         response = requests.post(ITRACKSAFEX_API_URL, json=payload, timeout=10)
#         response.raise_for_status()  # Raise an exception for HTTP errors
#     except requests.RequestException as e:
#         print(f"Error creating tracker account: {e}")
#         return {"error": "API request failed"}

#     if response.status_code == 200:
#         data = response.json()
#         if data.get("status") == 0:
#             return data  # Return the created account data
#     return {"error": "Account creation failed"}