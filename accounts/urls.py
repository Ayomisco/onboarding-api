from django.urls import path
from .views import (
    RegisterView, OTPRequestView, OTPVerifyView, GeneralOTPVerifyView,
    LoginView, LogoutView, GetLocationAPIView, GetUserByUsernameAPIView, GetAllUsersAPIView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('otp/request/', OTPRequestView.as_view(), name='otp-request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('otp/general-verify/', GeneralOTPVerifyView.as_view(),
         name='otp-general-verify'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('get-location/', GetLocationAPIView.as_view(), name='get-location'),

        path('users/<str:username>/', GetUserByUsernameAPIView.as_view(),
             name='get-user-by-username'),
        path('users/', GetAllUsersAPIView.as_view(), name='get-all-users'),


]
