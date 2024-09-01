import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "logsheet.settings")

import django

django.setup()
import sys
from project.harvest import sync_harvest_data

from django.utils import timezone
import time

start_time = time.time()

try:
    sync_harvest_data(int(sys.argv[1]))
except IndexError:
    sync_harvest_data()

print(f'{timezone.now().isoformat()} | Synced Harvest data in {time.time() - start_time :.2f} seconds.')
