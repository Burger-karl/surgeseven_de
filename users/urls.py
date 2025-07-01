from django.urls import path
from .views import (RegisterView, VerifyEmailView, 
    ResendOTPView, LoginView, LogoutView, 
    ForgotPasswordView, ResetPasswordView, 
    ProfileCreateView, ProfileView,
    ProfileUpdateView, ReferralView,
    admin_create_user, admin_delete_user,
    AdminUserListView, AdminUserDetailView,

)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('profile/create/', ProfileCreateView.as_view(), name='profile-create'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', ProfileUpdateView.as_view(), name='profile-update'),
    path('referral/', ReferralView.as_view(), name='referral'),
    

    # FOR ADMIN USER
    path('admin/users/create/', admin_create_user, name='admin_create_user'),
    path('admin/users/', AdminUserListView.as_view(), name='admin_users_list'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:pk>/delete/', admin_delete_user, name='admin_delete_user'),
    
]

