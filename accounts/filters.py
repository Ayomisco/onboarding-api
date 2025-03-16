import django_filters
from accounts.models import User  # Import your User model


class UserFilter(django_filters.FilterSet):
    """
    Filters users by username, email, gender, location, and phone_number.
    """
    username = django_filters.CharFilter(lookup_expr="icontains")
    email = django_filters.CharFilter(lookup_expr="icontains")
    gender = django_filters.ChoiceFilter(choices=User.GENDER_CHOICES)
    location = django_filters.CharFilter(lookup_expr="icontains")
    phone_number = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = User
        fields = ['username', 'email', 'gender', 'location', 'phone_number']
