# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required, user_passes_test
# from django.contrib.admin.views.decorators import staff_member_required
# from django.views import View
# from django.utils.decorators import method_decorator
# from django.http import JsonResponse, HttpResponseForbidden
# from booking.models import Truck
# from .services import get_tracker_data
# from .models import Geofence

# def is_client_or_truck_owner(user):
#     return user.user_type in ["client", "truck_owner"]


# @method_decorator(login_required, name='dispatch')
# class TrackingDashboardView(View):
#     """
#     Class-Based View for real-time tracking dashboard.
#     """
#     template_name = "tracker/tracking_dashboard.html"

#     def get(self, request, truck_id):
#         truck = get_object_or_404(Truck, id=truck_id, tracker_id__isnull=False)
        
#         # Check if the user has access to the truck
#         if request.user.user_type == "truck_owner" and truck.owner != request.user:
#             return HttpResponseForbidden("You do not have access to this truck.")
#         elif request.user.user_type == "client" and not truck.bookings.filter(client=request.user).exists():
#             return HttpResponseForbidden("You do not have access to this truck.")

#         tracker_data = get_tracker_data(truck.tracker_id, request.user)

#         context = {
#             "truck": truck,
#             "tracker_data": tracker_data if tracker_data else None
#         }
#         return render(request, self.template_name, context)


# @method_decorator(login_required, name='dispatch')
# class FetchTrackingDataView(View):
#     """
#     AJAX Class-Based View to fetch real-time tracking data for a truck.
#     """
#     def get(self, request, truck_id):
#         try:
#             truck = Truck.objects.get(id=truck_id, tracker_id__isnull=False)
#         except Truck.DoesNotExist:
#             return JsonResponse({"error": "Truck not found or not assigned a tracker"}, status=404)

#         # Check if the user has access to the truck
#         if request.user.user_type == "truck_owner" and truck.owner != request.user:
#             return JsonResponse({"error": "Unauthorized access"}, status=403)
#         elif request.user.user_type == "client" and not truck.bookings.filter(client=request.user).exists():
#             return JsonResponse({"error": "Unauthorized access"}, status=403)

#         tracker_data = get_tracker_data(truck.tracker_id, request.user)

#         if tracker_data and "error" not in tracker_data:
#             return JsonResponse({
#                 "latitude": tracker_data.get("latitude"),
#                 "longitude": tracker_data.get("longitude"),
#                 "speed": tracker_data.get("speed", 0),
#                 "last_updated": tracker_data.get("arrivedtime"),
#             })

#         return JsonResponse({"error": "Unable to fetch tracking data"}, status=500)
        

# from django.shortcuts import render, get_object_or_404, redirect
# from django.views import View
# from django.utils.decorators import method_decorator
# from django.contrib.admin.views.decorators import staff_member_required
# from django.core.paginator import Paginator
# from booking.models import Truck


# @method_decorator(staff_member_required, name='dispatch')
# class AssignTrackerView(View):
#     """
#     Admin view to assign tracker IDs to trucks with pagination.
#     """
#     template_name = "tracker/assign_tracker.html"

#     def get(self, request):
#         """
#         Display a paginated list of trucks.
#         """
#         trucks = Truck.objects.all().order_by("-id")  # Get all trucks
#         paginator = Paginator(trucks, 10)  # Show 10 trucks per page
#         page_number = request.GET.get("page")
#         page_obj = paginator.get_page(page_number)

#         return render(request, self.template_name, {"page_obj": page_obj})

#     def post(self, request):
#         """
#         Assigns a tracker ID to a selected truck.
#         """
#         truck_id = request.POST.get("truck_id")
#         tracker_id = request.POST.get("tracker_id")

#         if not truck_id or not tracker_id:
#             return redirect("assign-tracker")

#         truck = get_object_or_404(Truck, id=truck_id)

#         # Ensure tracker ID is unique
#         if Truck.objects.filter(tracker_id=tracker_id).exists():
#             return redirect("assign-tracker")

#         truck.tracker_id = tracker_id
#         truck.save()

#         return redirect("assign-tracker")


# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
# from django.contrib.admin.views.decorators import staff_member_required
# from django.views import View
# from django.contrib import messages
# from .services import send_truck_command
# from booking.models import Truck


# @method_decorator(staff_member_required, name='dispatch')
# class RemoteControlView(View):
#     """
#     Admin-only view to lock/unlock a truck.
#     """
#     template_name = "tracker/remote_control.html"

#     def get(self, request):
#         trucks = Truck.objects.exclude(tracker_id=None)
#         return render(request, self.template_name, {"trucks": trucks})

#     def post(self, request):
#         truck_id = request.POST.get("truck_id")
#         action = request.POST.get("action")  # lock or unlock

#         truck = get_object_or_404(Truck, id=truck_id, tracker_id__isnull=False)
#         result = send_truck_command(truck.tracker_id, action)

#         if "error" in result:
#             messages.error(request, f"Failed to {action} truck: {result['error']}")
#         else:
#             messages.success(request, f"Truck {action} successful!")

#         return redirect("remote-control")


# @method_decorator(staff_member_required, name='dispatch')
# class GeofenceView(View):
#     """
#     Admin-only view to manage geofences.
#     """
#     template_name = "tracker/geofence.html"

#     def get(self, request):
#         geofences = Geofence.objects.all()
#         return render(request, self.template_name, {"geofences": geofences})

#     def post(self, request):
#         name = request.POST.get("name")
#         latitude = request.POST.get("latitude")
#         longitude = request.POST.get("longitude")
#         radius = request.POST.get("radius")

#         Geofence.objects.create(name=name, latitude=latitude, longitude=longitude, radius=radius)
#         return redirect("geofence")
