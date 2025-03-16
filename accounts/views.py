from django.contrib.auth import authenticate
from django.utils.timezone import now
import requests
from rest_framework import status, generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP
from .serializers import (
    RegistrationSerializer, OTPRequestSerializer, OTPVerificationSerializer,
    GeneralOTPVerificationSerializer, LoginSerializer, LogoutSerializer
)
from .emails import send_otp_email_task, send_welcome_email_task
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from accounts.filters import UserFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from .serializers import UserSerializer
from django.shortcuts import get_object_or_404


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=RegistrationSerializer, responses={201: "User registered successfully"})
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp_instance = OTP.objects.create(user=user)
            send_otp_email_task(user.email,user.first_name, otp_instance.code)
            return Response({"message": "User registered successfully. Check your email for OTP."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=OTPRequestSerializer, responses={200: "OTP sent successfully"})
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            otp_instance = OTP.objects.create(user=user)
            send_otp_email_task(user.email,user.first_name, otp_instance.code)
            return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=OTPVerificationSerializer, responses={200: "Account activated successfully"})
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            user.is_active = True
            user.save()
            send_welcome_email_task(user.email, user.first_name)

            return Response({"message": "Account activated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GeneralOTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=GeneralOTPVerificationSerializer, responses={200: "OTP verified successfully"})
    def post(self, request):
        serializer = GeneralOTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: "Login successful"})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={200: "Logout successful"})
    def post(self, request):
        serializer = LogoutSerializer(
            data=request.data, context={"request": request})
        if serializer.is_valid():
            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetLocationAPIView(APIView):
    """
    API to fetch and store user location based on IP address.
    
    **Note**: 
    - This endpoint is **protected** (only logged-in users can access it).
    - The frontend/mobile app **must authenticate** the user first before calling this.
    """
    permission_classes = [
        IsAuthenticated]  # Ensure only logged-in users can access this

    @extend_schema(
        summary="Get User Location",
        description="Fetches user's location using their IP address and updates their profile.",
        responses={200: "User location details"},
        tags=["User Location"]
    )
    def get(self, request):
        # Get the correct client IP
        ip = request.META.get("HTTP_X_FORWARDED_FOR")
        if ip:
            ip = ip.split(",")[0]  # Get the first IP in case of multiple
        else:
            # Fallback to Google DNS IP
            ip = request.META.get("REMOTE_ADDR", "8.8.8.8")

        try:
            # Fetch location data using ipinfo.io
            response = requests.get(f"https://ipinfo.io/{ip}/json").json()
            print("📍 API Response:", response)  # Debugging

            if response.get("bogon", False) or "country" not in response:
                return Response({"error": "Could not retrieve location"}, status=400)

            # Extract lat/lon from 'loc' field
            loc = response.get("loc", ",").split(",")
            latitude, longitude = loc if len(loc) == 2 else ("", "")

            location_data = {
                "country": response.get("country", ""),
                "region": response.get("region", ""),
                "city": response.get("city", ""),
                "lat": latitude,
                "lon": longitude,
                "ip": response.get("ip", ip),
            }

            if request.user.is_authenticated:
                # Update user's location field
                user = request.user
                user.location = f"{location_data['city']}, {location_data['country']}"
                user.save(update_fields=["location"])

            return Response(location_data, status=200)

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching location: {e}")
            return Response({"error": "Location service unavailable"}, status=500)

class GetUserByUsernameAPIView(RetrieveAPIView):
    """
    API to fetch a user by their username.

    **Note:** Only authenticated users can access this endpoint.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"

    @extend_schema(
        summary="Get User by Username",
        description="Retrieve user details using their username.",
        responses={200: UserSerializer},
        tags=["Users"]
    )
    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        serializer = self.get_serializer(user)
        return Response(serializer.data)


class UserPagination(PageNumberPagination):
    page_size = 10  # Default items per page
    page_size_query_param = "page_size"
    max_page_size = 50  # Maximum items per page


class GetAllUsersAPIView(ListAPIView):
    """
    API to list all users with filtering and pagination.
    
    **Filters Available:**
    - `username` (contains)
    - `email` (contains)
    - `gender` (Male/Female/Not Say)
    - `location` (contains)
    - `phone_number` (contains)
    
    **Pagination:**  
    - Default page size: 10  
    - Customize with `?page=2&size=5`
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("-id")
    pagination_class = UserPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

    @extend_schema(
        summary="Get All Users with Filters & Pagination",
        description="List all users with filtering options for username, email, gender, location, and phone_number.",
        responses={200: UserSerializer(many=True)},
        tags=["Users"]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
