"""Conftest for CAMPanule tests.

Patches Django's flush command to use CASCADE, preventing FK constraint
errors during teardown of transaction=True tests.

The error without this patch:
  psycopg.errors.FeatureNotSupported: cannot truncate a table referenced
  in a foreign key constraint (t_roles_groups → auth_group)
"""
from django.core.management.commands.flush import Command as FlushCommand

_original_handle = FlushCommand.handle


def _handle_with_cascade(self, *args, **options):
    options['allow_cascade'] = True
    return _original_handle(self, *args, **options)


FlushCommand.handle = _handle_with_cascade
