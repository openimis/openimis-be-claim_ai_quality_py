import logging
from functools import lru_cache

from django.db import migrations
from core.models import RoleRight, Role

logger = logging.getLogger(__name__)

ROLE_RIGHT_ID = 112001
MANAGER_ROLE_IS_SYSTEM = 2  # By default right for report is assigned to Manager role


@lru_cache(maxsize=1)
def __get_role_owner() -> Role:
    return Role.objects.get(is_system=2, validity_to=None)


def __role_already_exists():
    sc = RoleRight.objects.filter(role__uuid=__get_role_owner().uuid, right_id=ROLE_RIGHT_ID)
    return sc.count() > 0


def create_role_right(apps, schema_editor):
    if schema_editor.connection.alias != 'default':
        return
    if __role_already_exists():
        logger.warning(F"Role right {ROLE_RIGHT_ID} already assigned for role {__get_role_owner().name}, skipping")
        return

    role_owner = Role.objects.get(is_system=2, validity_to=None)
    new_role = RoleRight(
        role=role_owner,
        right_id=ROLE_RIGHT_ID,
        audit_user_id=None,
    )
    new_role.save()

    # Your migration code goes here


class Migration(migrations.Migration):

    dependencies = [
        ('claim_ai_quality', '0002_claimaiqualitymutation')
    ]

    operations = [
        migrations.RunPython(create_role_right),
    ]
