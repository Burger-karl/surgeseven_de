import requests
import datetime
import hashlib
from django.conf import settings
from django.utils import timezone
from .models import Tracker, TrackingEvent, TrackerToken
from booking.models import Truck
from django.core.cache import cache

ITRACKSAFEX_API_URL = "https://web.itracksafe.com/webapi"
ITRACKSAFEX_USERNAME = "Surge Seven"
ITRACKSAFEX_PASSWORD = "Surge#7"

def md5_hash(text):
    """Generate MD5 hash of a string"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def get_or_refresh_token(user):
    """
    Get a valid token from the database or login to get a new one
    """
    # Check for existing valid token (not older than 23 hours as per API docs)
    existing_token = TrackerToken.objects.filter(
        user=user,
        updated_at__gte=timezone.now() - timezone.timedelta(hours=23)
    ).first()
    
    if existing_token:
        return existing_token.token
    
    # Login to get new token
    encrypted_password = md5_hash(ITRACKSAFEX_PASSWORD)
    login_payload = {
        "type": "USER",
        "from": "web",
        "username": ITRACKSAFEX_USERNAME,
        "password": encrypted_password,
        "browser": "SurgeSevenWebApp"
    }
    
    try:
        response = requests.post(
            f"{ITRACKSAFEX_API_URL}?action=login",
            json=login_payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == 0:
            token = data.get("token") or "6c1f1207c35d97a744837a19663ecdbe"
            # Save or update token
            TrackerToken.objects.update_or_create(
                user=user,
                defaults={'token': token}
            )
            return token
    except Exception as e:
        print(f"Error getting tracker token: {e}")
    
    return None


def get_tracker_data(tracker_id, user):
    cache_key = f"tracker_data_{tracker_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    token = get_or_refresh_token(user)
    if not token:
        return {"error": "Unable to authenticate with tracking service"}
    
    try:
        truck = Truck.objects.get(tracker_id=tracker_id)
        tracker, _ = Tracker.objects.get_or_create(truck=truck)
    except Truck.DoesNotExist:
        return {"error": "Truck not found"}
    
    payload = {"deviceids": [tracker_id], "lastquerypositiontime": 0}
    
    try:
        response = requests.post(
            f"{ITRACKSAFEX_API_URL}?action=lastposition&token={token}",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != 0:
            return {"error": data.get("cause", "Unknown error from tracking service")}
        
        records = data.get("records", [])
        if not records:
            return {"error": "No tracking data available"}
        
        latest = records[0]
        
        # Handle timestamp conversion safely
        def safe_convert_timestamp(ts):
            try:
                if ts and isinstance(ts, (int, float)):
                    # Convert milliseconds to seconds
                    return datetime.datetime.fromtimestamp(ts/1000.0, timezone.get_current_timezone())
                return None
            except (ValueError, OSError):
                return None
        
        last_updated = safe_convert_timestamp(latest.get('updatetime') or latest.get('arrivedtime'))
        
        transformed_data = {
            'latitude': latest.get('callat') or latest.get('latitude'),
            'longitude': latest.get('callon') or latest.get('longitude'),
            'speed': latest.get('speed', 0),
            'last_updated': last_updated,
            'status': 'online' if latest.get('moving', 0) == 1 else 'offline',
            'moving': latest.get('moving', 0) == 1,
            'voltage': latest.get('voltagev'),
            'gps_satellites': latest.get('gpsvalidnum'),
            'accuracy': latest.get('radius', 0),
            'course': latest.get('course'),
            'altitude': latest.get('altitude', 0),
            'strstatus': latest.get('strstatus', ''),
            'alarm': latest.get('alarm', 0),
            'alarm2': latest.get('alarm2', 0),
            'parkduration': latest.get('parkduration', 0),
            'accduration': latest.get('accduration', 0)
        }
        
        # Basic validation
        if None in (transformed_data['latitude'], transformed_data['longitude']):
            return {"error": "Invalid coordinates received"}
            
        # Update tracker with transformed data
        tracker.last_latitude = transformed_data['latitude']
        tracker.last_longitude = transformed_data['longitude']
        tracker.speed = transformed_data['speed']
        tracker.last_updated = transformed_data['last_updated']
        tracker.save()
        
        # Create event
        TrackingEvent.objects.create(
            tracker=tracker,
            event_type="position_update",
            latitude=transformed_data['latitude'],
            longitude=transformed_data['longitude'],
            speed=transformed_data['speed'],
            timestamp=transformed_data['last_updated'] or timezone.now()
        )
        
        # Prepare response
        response_data = transformed_data.copy()
        
        # For non-staff users, only include basic fields
        if not user.is_staff:
            response_data = {
                k: v for k, v in response_data.items() 
                if k in ['latitude', 'longitude', 'speed', 'last_updated', 'status']
            }

        cache.set(cache_key, response_data, 30)
        return response_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"error": "Unable to connect to tracking service"}
    except Exception as e:
        logger.error(f"Error processing tracker data: {e}")
        return {"error": "Unable to process tracking data"}
    
def send_truck_command(tracker_id, user, action):
    """
    Send lock/unlock command to a truck
    """
    token = get_or_refresh_token(user)
    if not token:
        return {"error": "Unable to authenticate with tracking service"}
    
    # Determine command based on action
    if action == "lock":
        cmdcode = "TYPE_SERVER_SET_RELAY_OIL"
        params = ["1"]
    elif action == "unlock":
        cmdcode = "TYPE_SERVER_SET_RELAY_OIL"
        params = ["0"]
    else:
        return {"error": "Invalid action"}
    
    payload = {
        "deviceid": tracker_id,
        "cmdcode": cmdcode,
        "params": params,
        "cmdpwd": "zhuyi"  # Fixed password from docs
    }
    
    try:
        response = requests.post(
            f"{ITRACKSAFEX_API_URL}?action=sendcmd&token={token}",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == 6:  # CMD_SEND_CONFIRMED
            return {"success": True, "message": f"Truck {action} successful"}
        else:
            return {"error": data.get("cause", "Command failed")}
    except Exception as e:
        print(f"Error sending truck command: {e}")
        return {"error": "Unable to send command to tracker"}