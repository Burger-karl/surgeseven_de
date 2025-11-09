from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.views import View
from django.views.generic import FormView, DetailView, ListView
from django.urls import reverse_lazy, reverse
from .forms import RegisterForm, LoginForm, OTPForm, ForgotPasswordForm, ResetPasswordForm, ProfileForm, AdminUserCreationForm
from .models import User, OTP, PasswordResetToken, Profile, Referral
from subscriptions.models import SubscriptionPlan, UserSubscription
from .emails import send_otp_email, send_welcome_email, send_password_reset_email
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .utils import generate_random_otp
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django_ratelimit.core import is_ratelimited
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def user_type_required(user_type):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated or request.user.user_type != user_type:
                raise PermissionDenied(f"Only {user_type}s can access this view.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def is_admin(user):
    return user.is_authenticated and user.is_superuser


OTP_EXPIRATION_MINUTES = 10

class RegisterView(View):
    form_class = RegisterForm
    template_name = 'users/register.html'
    
    def get(self, request, *args, **kwargs):
        referral_code = request.GET.get('ref')
        form = self.form_class(initial={'referral_code': referral_code})
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        # Fixed rate limiting - use the correct function signature
        if is_ratelimited(request, group='register', key='ip', rate='5/h', increment=True):
            messages.error(request, "Too many registration attempts. Please try again in an hour.")
            form = self.form_class()
            return render(request, self.template_name, {'form': form})
        
        form = self.form_class(request.POST)
        if form.is_valid():
            user_data = {
                'email': form.cleaned_data['email'],
                'username': form.cleaned_data['username'],
                'password1': form.cleaned_data['password1'],
                'password2': form.cleaned_data['password2'],
                'user_type': form.cleaned_data['user_type'],
                'referral_code': form.cleaned_data['referral_code']
            }

            if user_data['user_type'] == 'admin':
                user_data['is_staff'] = True
                user_data['is_superuser'] = True

            request.session['user_data'] = user_data
            otp = get_random_string(length=6, allowed_chars='0123456789')
            request.session['otp'] = otp
            request.session['otp_created_at'] = timezone.now().isoformat()
            
            # Send OTP using Resend
            email_sent = send_otp_email(
                to_email=user_data['email'],
                otp_code=otp,
                subject='Verify your SurgeSeven account'
            )

            if email_sent:
                messages.success(request, "An OTP has been sent to your email for verification.")
                return redirect('verify-email')
            else:
                logger.error(f"Failed to send OTP email to {user_data['email']}")
                messages.error(
                    request, 
                    "Failed to send OTP email. Please check your email address and try again."
                )
                return render(request, self.template_name, {'form': form})
                
        return render(request, self.template_name, {'form': form})


class VerifyEmailView(FormView):
    form_class = OTPForm
    template_name = 'users/verify_email.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        otp = form.cleaned_data.get('otp')
        session_otp = self.request.session.get('otp')
        otp_created_at = self.request.session.get('otp_created_at')
        
        # Check OTP expiration
        if otp_created_at:
            created_time = timezone.datetime.fromisoformat(otp_created_at)
            if timezone.now() - created_time > timedelta(minutes=OTP_EXPIRATION_MINUTES):
                messages.error(self.request, "OTP has expired. Please register again.")
                self._clear_session_data()
                return redirect('register')
        
        if otp == session_otp:
            user_data = self.request.session.get('user_data')
            if not user_data:
                messages.error(self.request, 'Session expired. Please register again.')
                return redirect('register')

            try:
                # Create user in the database now
                user = User.objects.create_user(
                    email=user_data['email'],
                    username=user_data['username'],
                    password=user_data['password1'],
                    user_type=user_data['user_type'],
                    is_verified=True,
                    is_active=True
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
                        Referral.objects.create(referrer=referrer, referred_user=user)
                        referrer.credits += 1000
                        referrer.save()
                        messages.success(self.request, f"Referral successful! {referrer.email} has been credited with #1000.")
                    except User.DoesNotExist:
                        messages.warning(self.request, "Invalid referral code. Proceeding without referral.")

                # Send welcome email
                send_welcome_email(user.email, user.username)

                # Clear session data
                self._clear_session_data()

                messages.success(self.request, "Your email has been verified! You can now log in.")
                logger.info(f"New user registered successfully: {user.email}")
                return super().form_valid(form)
                
            except Exception as e:
                logger.error(f"Error creating user during verification: {str(e)}")
                messages.error(self.request, "An error occurred during registration. Please try again.")
                return self.form_invalid(form)
                
        else:
            form.add_error('otp', 'Invalid OTP code. Please try again.')
            return self.form_invalid(form)

    def _clear_session_data(self):
        """Clear session data related to registration"""
        session_keys = ['user_data', 'otp', 'otp_created_at']
        for key in session_keys:
            if key in self.request.session:
                del self.request.session[key]
                

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
    def get(self, request, *args, **kwargs):
        return render(request, 'users/resend_otp.html')


    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Email is required.")
            return redirect('resend-otp')

        try:
            user = get_object_or_404(User, email=email)
        except User.DoesNotExist:
            messages.error(request, "User with this email does not exist.")
            return redirect('resend-otp')

        otp = generate_random_otp()
        otp_instance, created = OTP.objects.update_or_create(
            user=user,
            defaults={'otp': otp, 'created_at': timezone.now()}
        )

        # Send OTP using SendGrid
        email_sent = send_otp_email(
            to_email=email,
            otp_code=otp,
            subject='Your new verification code'
        )
        
        if email_sent:
            messages.success(request, "OTP resent successfully.")
            return redirect('verify-email')
        else:
            messages.error(request, "Failed to send OTP. Please try again.")
            return redirect('resend-otp')
        

class LoginView(FormView):
    form_class = LoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('client_home')  # Default fallback URL

    def get(self, request, *args, **kwargs):
        # Check for saved credentials if user wants to be remembered
        email = request.COOKIES.get('remembered_email', '')
        remember_me = bool(email)
        
        form = self.form_class(initial={
            'email': email,
            'remember_me': remember_me
        })
        
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        password = form.cleaned_data.get('password')
        remember_me = form.cleaned_data.get('remember_me', False)
        
        user = authenticate(email=email, password=password)

        if user:
            if not user.is_verified:
                messages.error(self.request, "Account not verified. Please verify your email.")
                return redirect('login')

            login(self.request, user)
            
            # Set session expiry based on remember_me
            if remember_me:
                # Set session to expire in 30 days
                self.request.session.set_expiry(60 * 60 * 24 * 30)
                
                # Set cookie to remember email
                response = redirect(self.get_success_url())
                response.set_cookie('remembered_email', email, max_age=60 * 60 * 24 * 30)
            else:
                # Browser-length session
                self.request.session.set_expiry(0)
                # Delete any existing remember cookie
                response = redirect(self.get_success_url())
                response.delete_cookie('remembered_email')

            messages.success(self.request, "Logged in successfully.")

            # Redirect based on user type
            if user.is_superuser or user.is_staff:
                return redirect('admin_home')
            elif user.user_type == 'truck_owner':
                return redirect('truck_owner_home')
            else:
                # Default to client home (you might want to check for client profile here)
                return redirect('client_home')

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
                # Don't reveal if email exists for security
                messages.success(request, "If your email exists in our system, you'll receive a password reset link.")
                return redirect('forgot-password')
            
            # Delete any existing tokens for this user
            PasswordResetToken.objects.filter(user=user).delete()
            
            # Create new token
            token = PasswordResetToken.objects.create(user=user)
            
            # Send password reset email
            reset_link = request.build_absolute_uri(
                reverse('reset-password', kwargs={'token': token.token})
            )
            
            send_password_reset_email(
                'Password Reset Request',
                f'Click this link to reset your password: {reset_link}\n\n'
                f'The link will expire in 1 hour.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            messages.success(request, "Password reset link sent to your email.")
            return redirect('login')

        return render(request, 'users/forgot_password.html', {'form': form})
    

class ResetPasswordView(View):
    def get(self, request, token, *args, **kwargs):
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            messages.error(request, "Invalid or expired password reset link.")
            return redirect('forgot-password')
            
        if reset_token.is_expired():
            reset_token.delete()
            messages.error(request, "Password reset link has expired.")
            return redirect('forgot-password')
            
        form = ResetPasswordForm()
        return render(request, 'users/reset_password.html', {'form': form, 'token': token})

    def post(self, request, token, *args, **kwargs):
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            try:
                reset_token = PasswordResetToken.objects.get(token=token)
            except PasswordResetToken.DoesNotExist:
                messages.error(request, "Invalid or expired password reset link.")
                return redirect('forgot-password')
                
            if reset_token.is_expired():
                reset_token.delete()
                messages.error(request, "Password reset link has expired.")
                return redirect('forgot-password')
                
            new_password = form.cleaned_data.get('new_password')
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            
            reset_token.delete()
            messages.success(request, "Password reset successful. You can now login with your new password.")
            return redirect('login')
            
        return render(request, 'users/reset_password.html', {'form': form, 'token': token})
    

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

@method_decorator([login_required, user_type_required('admin')], name='dispatch')
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