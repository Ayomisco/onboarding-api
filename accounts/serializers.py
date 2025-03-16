from rest_framework import serializers
from django.utils.timezone import now
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP
from .emails import send_otp_email_task, send_welcome_email_task
import datetime
from django.utils.timezone import now
from django.contrib.auth.password_validation import validate_password


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, required=True,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True, required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name',
            'dob', 'gender', 'phone_number', 'location',
            'password', 'confirm_password'
        ]

    def validate_email(self, value):
        """ Ensure email is unique """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already taken.")
        return value

    def validate_username(self, value):
        """ Ensure username is unique """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_phone_number(self, value):
        """ Validate phone number format """
        if not value.isdigit() or len(value) not in [10, 11, 13]:
            raise serializers.ValidationError("Invalid phone number format.")
        return value

    def validate_dob(self, value):
        """ Ensure user is at least 18 years old """
        age = (now().date() - value).days // 365
        if age < 18:
            raise serializers.ValidationError(
                "You must be at least 18 years old to register.")
        return value

    def validate(self, data):
        """ Ensure passwords match and meet validation requirements """
        password = data.get('password')
        confirm_password = data.pop('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError(
                {"password": "Passwords do not match."})

        validate_password(password)  # Django's built-in password validation
        return data

    def create(self, validated_data):
        """ Create user and send OTP """
        user = User.objects.create_user(**validated_data)
        otp = OTP.objects.create(user=user)
        send_otp_email_task(user.email, user.first_name, otp.code)
        return user


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        data['user'] = user
        return data

    def create(self, validated_data):
        user = User.objects.get(email=validated_data['email'])
        otp = OTP.objects.create(user=user)
        send_otp_email_task(user.email, user.first_name, otp.code)
        return {'message': 'OTP sent successfully'}


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        otp = OTP.objects.filter(user=user, code=data['code']).order_by(
            '-created_at').first()
        if not otp:
            raise serializers.ValidationError("Invalid OTP.")

        user.is_active = True
        user.save()
        send_welcome_email_task(user.email, user.first_name)

        data['user'] = user  

        otp.delete()
        return data


class GeneralOTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        otp = OTP.objects.filter(user=user, code=data['code']).order_by(
            '-created_at').first()
        if not otp:
            raise serializers.ValidationError("Invalid OTP.")

        otp.delete()

        return {'message': 'OTP verified successfully'}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("Account is not activated.")

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class LogoutSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        otp = OTP.objects.filter(user=user, code=data['code']).order_by(
            '-created_at').first()
        if not otp:
            raise serializers.ValidationError("Invalid OTP.")

        otp.delete()
        return {'message': 'Logged out successfully'}


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    Includes all necessary fields for user retrieval.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'dob', 'gender', 'phone_number', 'location', 'is_active']
