"""Create fictional screenshot data in the disposable test instance."""
import os
from django.conf import settings
from django.contrib.auth.models import Group, User
from stock.models import StockLocation
from users.models import RuleSet, UserProfile

assert settings.DATABASES['default']['NAME'] == 'freezer_test'
operator, _ = User.objects.get_or_create(username='demo')
operator.set_password(os.environ['FREEZER_DEMO_PASSWORD'])
operator.save()
UserProfile.objects.get_or_create(user=operator)
group, _ = Group.objects.get_or_create(name='Demo operators')
for role in ('stock_location', 'stock', 'part'):
    RuleSet.objects.update_or_create(group=group, name=role, defaults={'can_view': True, 'can_add': role == 'stock_location'})
operator.groups.add(group)
parent = None
for name in ('Demo Freezer', 'Shelf 1', 'Rack A'):
    parent, _ = StockLocation.objects.get_or_create(name=name, parent=parent, defaults={'structural': True})
for name in ('Slot 01', 'Slot 02', 'Slot 03'):
    slot, _ = StockLocation.objects.get_or_create(name=name, parent=parent, defaults={'structural': True})
    print(name, slot.pk)
