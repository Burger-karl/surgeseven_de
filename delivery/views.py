from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from delivery.models import DeliverySchedule, DeliveryHistory

# Create your views here.

@method_decorator(login_required, name='dispatch')
class ActiveDeliveryView(ListView):
    model = DeliverySchedule
    template_name = 'delivery/active_delivery_list.html'
    context_object_name = 'active_deliveries'

    def get_queryset(self):
        # Filter only non-delivered deliveries
        return DeliverySchedule.objects.filter(
            client=self.request.user,
            booking__payment_completed=True,
            status__in=['pending', 'in_transit']
        ).select_related('booking')



@method_decorator(login_required, name='dispatch')
class DeliveryHistoryView(ListView):
    model = DeliveryHistory
    template_name = 'delivery/delivery_history_list.html'
    context_object_name = 'delivery_histories'

    def get_queryset(self):
        # Filter to show only deliveries marked as delivered
        return DeliveryHistory.objects.filter(
            client=self.request.user,
            status='delivered'
        ).select_related('booking')



# For AdminUser

from django.views.generic import ListView, UpdateView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from delivery.models import DeliverySchedule

# Custom decorator to check if the user is an admin
def admin_required(user):
    return user.is_staff  # or use user.is_superuser if you want only superusers to have access

@method_decorator([login_required, user_passes_test(admin_required)], name='dispatch')
class AdminDeliveryScheduleListView(ListView):
    model = DeliverySchedule
    template_name = 'delivery/admin_delivery_schedule_list.html'
    context_object_name = 'delivery_schedules'

    def get_queryset(self):
        # Filter for deliveries with completed payments
        return DeliverySchedule.objects.filter(
            booking__payment_completed=True
        ).select_related('booking', 'client')

@method_decorator([login_required, user_passes_test(admin_required)], name='dispatch')
class UpdateDeliveryScheduleStatusView(UpdateView):
    model = DeliverySchedule
    fields = ['status']
    template_name = 'delivery/update_delivery_status.html'
    context_object_name = 'delivery_schedule'
    success_url = reverse_lazy('admin_delivery_schedule_list')

    def get_object(self, queryset=None):
        # Get the specific delivery schedule by its ID
        return get_object_or_404(DeliverySchedule, pk=self.kwargs['pk'])

    def form_valid(self, form):
        # You can add additional logic here if needed
        return super().form_valid(form)
