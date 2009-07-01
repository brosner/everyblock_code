#!/usr/bin/env python
from django.core.management import execute_manager
import settings_devel

if __name__ == "__main__":
    execute_manager(settings_devel)
