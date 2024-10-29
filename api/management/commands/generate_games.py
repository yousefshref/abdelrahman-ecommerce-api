from django.core.management.base import BaseCommand
from api.models import Game, CustomUser, Category
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Generate random game accounts'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=10, help='Number of game accounts to create')

    def handle(self, *args, **kwargs):
        fake = Faker()
        count = kwargs['count']
        categories = Category.objects.all()
        users = CustomUser.objects.all()

        if not categories.exists() or not users.exists():
            self.stdout.write(self.style.ERROR('You need at least one Category and one User in the database.'))
            return

        for _ in range(count):
            # Choose a random user and category
            user = random.choice(users)
            category = random.choice(categories)

            # Generate random game data
            game = Game(
                seller=user,
                image=fake.image_url(),
                name=fake.word(),
                account_username_or_id=fake.user_name(),
                account_level=random.randint(1, 100),
                account_description=fake.text(max_nb_chars=200),
                category=category,
                price=random.randint(10, 1000),
                # offer_price=random.choice([random.randint(5, 999), None]),
                is_sold=fake.boolean(),
            )
            game.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {count} game accounts.'))
