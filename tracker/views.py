from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseServerError
from django.contrib import messages
from booking.models import Truck
from .models import Geofence
from .services import get_tracker_data, send_truck_command
import logging

logger = logging.getLogger(__name__)

def is_client_or_truck_owner(user):
    return user.user_type in ["client", "truck_owner"]


@method_decorator(login_required, name='dispatch')
class TrackingDashboardView(View):
    """
    Class-Based View for real-time tracking dashboard with role-based access
    """
    template_name = "tracker/tracking_dashboard.html"

    def get(self, request, truck_id):
        try:
            truck = get_object_or_404(Truck, id=truck_id, tracker_id__isnull=False)
            
            # Check access permissions
            if not self._check_access(request.user, truck):
                return HttpResponseForbidden("You do not have access to this truck.")

            tracker_data = get_tracker_data(truck.tracker_id, request.user)

            context = {
                "truck": truck,
                "truck_id": truck.id,  # Explicitly pass truck_id
                "tracker_data": tracker_data if tracker_data else None,
                "is_admin": request.user.is_staff
            }
            return render(request, self.template_name, context)
        except Exception as e:
            logger.error(f"Error in TrackingDashboardView: {str(e)}")
            return HttpResponseServerError("An error occurred while loading the tracking dashboard")

    def _check_access(self, user, truck):
        """Helper method to check access permissions"""
        if user.is_staff:
            return True
        if user.user_type == "truck_owner" and truck.owner == user:
            return True
        if user.user_type == "client" and truck.bookings.filter(client=user).exists():
            return True
        return False


@method_decorator(login_required, name='dispatch')
class FetchTrackingDataView(View):
    """
    AJAX endpoint for real-time tracking data with role-based filtering
    """
    def get(self, request, truck_id):
        try:
            truck = Truck.objects.get(id=truck_id, tracker_id__isnull=False)
        except Truck.DoesNotExist:
            return JsonResponse({"error": "Truck not found or not assigned a tracker"}, status=404)

        # Check access permissions
        if not self._check_access(request.user, truck):
            return JsonResponse({"error": "Unauthorized access"}, status=403)

        tracker_data = get_tracker_data(truck.tracker_id, request.user)

        if tracker_data and "error" not in tracker_data:
            response_data = {
                "latitude": tracker_data.get("latitude"),
                "longitude": tracker_data.get("longitude"),
                "speed": tracker_data.get("speed", 0),
                "last_updated": tracker_data.get("last_updated"),
            }
            
            # Add additional fields for admin users
            if request.user.is_staff:
                response_data.update({
                    "status": tracker_data.get("status"),
                    "alarm": tracker_data.get("alarm"),
                    "voltage": tracker_data.get("voltage"),
                    "gps_satellites": tracker_data.get("gps_satellites"),
                    "is_moving": tracker_data.get("moving", 0)
                })
            
            return JsonResponse(response_data)

        return JsonResponse({"error": tracker_data.get("error", "Unable to fetch tracking data")}, status=500)

    def _check_access(self, user, truck):
        """Helper method to check access permissions"""
        if user.is_staff:
            return True
        if user.user_type == "truck_owner" and truck.owner == user:
            return True
        if user.user_type == "client" and truck.bookings.filter(client=user).exists():
            return True
        return False
        

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from booking.models import Truck


@method_decorator(staff_member_required, name='dispatch')
class AssignTrackerView(View):
    """
    Admin view to assign tracker IDs to trucks with pagination.
    """
    template_name = "tracker/assign_tracker.html"

    def get(self, request):
        """
        Display a paginated list of trucks.
        """
        trucks = Truck.objects.all().order_by("-id")  # Get all trucks
        paginator = Paginator(trucks, 10)  # Show 10 trucks per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {"page_obj": page_obj})

    def post(self, request):
        """
        Assigns a tracker ID to a selected truck.
        """
        truck_id = request.POST.get("truck_id")
        tracker_id = request.POST.get("tracker_id")

        if not truck_id or not tracker_id:
            return redirect("assign-tracker")

        truck = get_object_or_404(Truck, id=truck_id)

        # Ensure tracker ID is unique
        if Truck.objects.filter(tracker_id=tracker_id).exists():
            return redirect("assign-tracker")

        truck.tracker_id = tracker_id
        truck.save()

        return redirect("assign-tracker")


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.views import View
from django.contrib import messages
from .services import send_truck_command
from booking.models import Truck


@method_decorator(staff_member_required, name='dispatch')
class RemoteControlView(View):
    """
    Admin-only view to lock/unlock a truck.
    """
    template_name = "tracker/remote_control.html"

    def get(self, request):
        trucks = Truck.objects.exclude(tracker_id=None)
        return render(request, self.template_name, {"trucks": trucks})

    def post(self, request):
        truck_id = request.POST.get("truck_id")
        action = request.POST.get("action")  # lock or unlock

        truck = get_object_or_404(Truck, id=truck_id, tracker_id__isnull=False)
        result = send_truck_command(truck.tracker_id, action)

        if "error" in result:
            messages.error(request, f"Failed to {action} truck: {result['error']}")
        else:
            messages.success(request, f"Truck {action} successful!")

        return redirect("remote-control")


@method_decorator(staff_member_required, name='dispatch')
class GeofenceView(View):
    """
    Admin-only view to manage geofences.
    """
    template_name = "tracker/geofence.html"

    def get(self, request):
        geofences = Geofence.objects.all()
        return render(request, self.template_name, {"geofences": geofences})

    def post(self, request):
        name = request.POST.get("name")
        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        radius = request.POST.get("radius")

        Geofence.objects.create(name=name, latitude=latitude, longitude=longitude, radius=radius)
        return redirect("geofence")
