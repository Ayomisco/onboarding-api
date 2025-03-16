from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Delete all users from the database"

    def handle(self, *args, **kwargs):
        confirm = input(
            "⚠️ Are you sure you want to delete all users? (yes/no): ")
        if confirm.lower() != "yes":
            self.stdout.write(self.style.WARNING(
                "Aborted! No users were deleted."))
            return

        user_count = User.objects.count()
        if user_count == 0:
            self.stdout.write(self.style.WARNING("No users found."))
            return

        User.objects.filter(is_superuser=False).delete()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Successfully deleted {user_count} users!"))
