"""Enable plugin integrations in the disposable test database only."""
from django.conf import settings
from common.models import InvenTreeSetting
from plugin.models import PluginConfig

assert settings.DATABASES['default']['NAME'] == 'freezer_test'
PluginConfig.objects.update_or_create(key='inventree-bulk-plugin', defaults={'active': True})
for key in ('ENABLE_PLUGINS_APP', 'ENABLE_PLUGINS_URL', 'ENABLE_PLUGINS_INTERFACE'):
    InvenTreeSetting.set_setting(key, True)
