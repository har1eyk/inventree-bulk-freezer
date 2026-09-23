# Upstream provenance

Based on `inventree-bulk-plugin` 1.5.2, released by wolflu05 under MIT.
Upstream repository: https://github.com/wolflu05/inventree-bulk-plugin
Exact source commit: `16b9455ee32d5c97edd85f70285754276eb905d6` (tag `1.5.2`).
The original MIT license is retained in LICENSE.

This independently packaged fork is `inventree-bulk-freezer`, version `1.5.2.post2`.
It retains the upstream Python module, plugin slug, and migration history.
Install **either** this distribution or the upstream distribution, never both.
Fork maintainer: Harley King (https://github.com/har1eyk).
Public repository: https://github.com/har1eyk/inventree-bulk-freezer
PyPI distribution: https://pypi.org/project/inventree-bulk-freezer/

Additions: freezer-box panel and atomic endpoint, CSV runner, portable templates,
native role and API-token checks, standard CSRF checks, sandboxed Jinja templates,
and acceptance tests. Generic schema generation is restricted to superusers;
freezer operators need stock-location view and add roles. Template writes require
staff or superuser status. OAuth tokens are not accepted by these endpoints.
