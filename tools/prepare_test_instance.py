"""Enable plugin integrations in the disposable test database only."""
from django.conf import settings
from django.utils.text import slugify
from common.models import InvenTreeSetting
from plugin.models import PluginConfig
from plugin.registry import registry

assert settings.DATABASES['default']['NAME'] == 'freezer_test'
# InvenTree treats shell/migrate as read-only during registry startup. On a
# fresh database, register discovered built-ins too so discovery can finish.
for plugin_class in registry.collect_plugins():
    key = slugify(getattr(plugin_class, 'SLUG', None) or plugin_class.NAME)
    PluginConfig.objects.get_or_create(key=key)

PluginConfig.objects.update_or_create(key='inventree-bulk-plugin', defaults={'active': True})
for key in ('ENABLE_PLUGINS_APP', 'ENABLE_PLUGINS_URL', 'ENABLE_PLUGINS_INTERFACE'):
    InvenTreeSetting.set_setting(key, True)
