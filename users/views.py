from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.views import View
from django.views.generic import FormView, DetailView, ListView
from django.urls import reverse_lazy
from .forms import RegisterForm, LoginForm, OTPForm, ForgotPasswordForm, ResetPasswordForm, ProfileForm, AdminUserCreationForm
from .models import User, OTP, PasswordResetToken, Profile, Referral
from subscriptions.models import SubscriptionPlan, UserSubscription
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .utils import generate_random_otp
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Create your views here.

def is_admin(user):
    return user.is_authenticated and user.is_superuser


OTP_EXPIRATION_MINUTES = 10


class RegisterView(View):
    form_class = RegisterForm
    template_name = 'users/register.html'
    
    def get(self, request, *args, **kwargs):
        referral_code = request.GET.get('ref')  # Get referral code from URL
        form = self.form_class(initial={'referral_code': referral_code})  # Pass referral code to form
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            user_data = {
                'email': form.cleaned_data['email'],
                'username': form.cleaned_data['username'],
                'password1': form.cleaned_data['password1'],
                'password2': form.cleaned_data['password2'],
                'user_type': form.cleaned_data['user_type'],
                'referral_code': form.cleaned_data['referral_code']  # Add referral code to user_data
            }

            # Set is_staff and is_superuser flags for admin users
            if user_data['user_type'] == 'admin':
                user_data['is_staff'] = True
                user_data['is_superuser'] = True

            # Store user data in session until verification
            request.session['user_data'] = user_data

            # Generate and send OTP
            otp = get_random_string(length=6, allowed_chars='0123456789')
            request.session['otp'] = otp
            send_mail(
                'Verify your email',
                f'Your OTP is {otp}',
                'from@example.com',
                [user_data['email']],
            )
            messages.success(request, "An OTP has been sent to your email for verification.")
            return redirect('verify-email')
        return render(request, self.template_name, {'form': form})
        

class VerifyEmailView(FormView):
    form_class = OTPForm
    template_name = 'users/verify_email.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        otp = form.cleaned_data.get('otp')
        session_otp = self.request.session.get('otp')
        if otp == session_otp:
            user_data = self.request.session.get('user_data')
            if not user_data:
                form.add_error(None, 'User data not found. Please register again.')
                return self.form_invalid(form)

            # Create user in the database now
            user = User.objects.create_user(
                email=user_data['email'],
                username=user_data['username'],
                password=user_data['password1'],
                user_type=user_data['user_type'],
                is_verified=True,
                is_active=True  # Activate after verification
            )

            # Assign free subscription if user is a client
            if user.user_type == 'client':
                free_plan = SubscriptionPlan.objects.get(name='free')
                UserSubscription.objects.create(
                    user=user,
                    plan=free_plan,
                    is_active=False,
                    subscription_status='inactive'
                )

            # Handle referral logic
            referral_code = user_data.get('referral_code')
            if referral_code:
                try:
                    referrer = User.objects.get(referral_code=referral_code)
                    # Create the Referral object
                    Referral.objects.create(referrer=referrer, referred_user=user)
                    # Credit the referrer with #1000
                    referrer.credits += 1000
                    referrer.save()
                    messages.success(self.request, f"Referral successful! {referrer.email} has been credited with #1000.")
                except User.DoesNotExist:
                    messages.warning(self.request, "Invalid referral code. Proceeding without referral.")

            # Clear session data
            del self.request.session['user_data']
            del self.request.session['otp']

            messages.success(self.request, "Your email has been verified! You can now log in.")
            return super().form_valid(form)
        else:
            form.add_error('otp', 'Invalid OTP')
            return self.form_invalid(form)       
                             

@method_decorator(login_required, name='dispatch')
class ReferralView(View):
    """
    View for displaying the referral link/code for authenticated users.
    """
    template_name = 'users/referral.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        referral_link = user.generate_referral_link()  # Generate the referral link
        referral_code = user.referral_code  # Get the referral code

        context = {
            'referral_link': referral_link,
            'referral_code': referral_code,
        }
        return render(request, self.template_name, context)


class ResendOTPView(View):
    """
    View for resending OTP to a user's email.
    """

    def get(self, request, *args, **kwargs):
        """
        Renders the resend OTP page.
        """
        return render(request, 'users/resend_otp.html')

    def post(self, request, *args, **kwargs):
        """
        Handles the resend OTP request.
        """
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Email is required.")
            return redirect('resend-otp')

        try:
            user = get_object_or_404(User, email=email)  # Get user or return 404
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
            return redirect('resend-otp')

        # Generate a new OTP
        otp = generate_random_otp()  # Use the utility function
        otp_instance, created = OTP.objects.update_or_create(
            user=user,
            defaults={'otp': otp, 'created_at': timezone.now()}
        )

        # Send OTP via email
        try:
            send_mail(
                'Your OTP Code',
                f'Use this OTP to verify your email: {otp}',
                'from@example.com',
                [email],
                fail_silently=False,
            )
            messages.success(request, "OTP resent successfully.")
        except Exception as e:
            messages.error(request, f"Failed to send OTP. Error: {str(e)}")
            return redirect('resend-otp')

        return redirect('verify-email')
    

class LoginView(FormView):
    form_class = LoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('profile-create')  # Default success URL

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        user = authenticate(email=email, password=password)

        if user:
            if not user.is_verified:
                messages.error(self.request, "Account not verified. Please verify your email.")
                return redirect('login')

            login(self.request, user)
            messages.success(self.request, "Logged in successfully.")

            # Check if the user has a profile
            try:
                profile = user.profile
                # If the user has a profile, redirect to the dashboard or another page
                return redirect(self.get_success_url())
            except Profile.DoesNotExist:
                # If the user does not have a profile, redirect to the profile creation page
                return redirect('profile-create')

        messages.error(self.request, "Invalid credentials.")
        return redirect('login')


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Logged out successfully.")
        return redirect('login')


class ForgotPasswordView(View):
    def get(self, request, *args, **kwargs):
        form = ForgotPasswordForm()
        return render(request, 'users/forgot_password.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No user found with this email.")
                return redirect('forgot-password')

            token = get_random_string(length=20)
            expiry_date = timezone.now() + timedelta(hours=1)  # Token valid for 1 hour

            PasswordResetToken.objects.create(user=user, token=token, expiry_date=expiry_date)

            send_mail(
                'Password Reset Request',
                f'Use this token to reset your password: {token}. The token expires in 1 hour.',
                'from@example.com',
                [email],
                fail_silently=False,
            )

            messages.success(request, "Password reset token sent.")
            return redirect('reset-password')

        return render(request, 'users/forgot_password.html', {'form': form})


class ResetPasswordView(View):
    def get(self, request, *args, **kwargs):
        form = ResetPasswordForm()
        return render(request, 'users/reset_password.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data.get('token')
            new_password = form.cleaned_data.get('new_password')

            try:
                reset_token = PasswordResetToken.objects.get(token=token)
            except PasswordResetToken.DoesNotExist:
                messages.error(request, "Invalid or non-existent token.")
                return redirect('reset-password')

            if reset_token.expiry_date < timezone.now():
                messages.error(request, "Token has expired. Request a new one.")
                return redirect('reset-password')

            user = reset_token.user
            user.set_password(new_password)
            user.save()

            reset_token.delete()
            messages.success(request, "Password reset successful.")
            return redirect('login')

        return render(request, 'users/reset_password.html', {'form': form})


class ProfileCreateView(View):
    def get(self, request, *args, **kwargs):
        form = ProfileForm()
        return render(request, 'users/profile_create.html', {'form': form})

    def post(self, request, *args, **kwargs):
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Profile created successfully.")
            return redirect('profile')

        return render(request, 'users/profile_create.html', {'form': form})


class ProfileView(DetailView):
    model = Profile
    template_name = 'users/profile.html'
    context_object_name = 'profile'

    def get_object(self):
        # Get or create a profile for the user
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_exists'] = not self.object._state.adding  # Check if the profile was just created
        return context
    

class ProfileUpdateView(View):
    def get(self, request, *args, **kwargs):
        profile = request.user.profile
        form = ProfileForm(instance=profile)
        return render(request, 'users/profile_update.html', {'form': form})

    def post(self, request, *args, **kwargs):
        profile = request.user.profile
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')

        return render(request, 'users/profile_update.html', {'form': form})
    


# ADMIN

@user_passes_test(is_admin)
def admin_create_user(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.email} created successfully!')
            return redirect('admin_users_list')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'users/admin/create_user.html', {'form': form})


class AdminUserListView(ListView):
    model = User
    template_name = 'users/admin/users_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)
    

class AdminUserDetailView(DetailView):
    model = User
    template_name = 'users/admin/user_detail.html'
    context_object_name = 'user_detail'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.get_object()
        return context

@user_passes_test(is_admin)
def admin_delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        email = user.email
        user.delete()
        messages.success(request, f'User {email} deleted successfully!')
        return redirect('admin_users_list')
    return render(request, 'users/admin/confirm_delete.html', {'user': user})