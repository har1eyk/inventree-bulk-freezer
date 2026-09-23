# API and templates

`POST /plugin/inventree-bulk-plugin/bulkcreate?create=false` previews;
`create=true` creates. Send JSON:

```json
{"mode":"freezer_box","parent_id":1001,"box_name":"Box_001","layout":"9x9"}
```

Returns parent path, box name, layout, position names/count, box ID and URL, and
status `ready`, `created`, or `already_exists`. HTTP 201 means created, 200 means
preview or existing, 400 invalid input, 403 insufficient roles or CSRF failure,
404 missing parent, and 409 conflicting occupancy. Authentication failures return
401. Creation ignores arbitrary template fields and builds the selected layout
server-side. No automatic activation hook creates locations.

Two portable generic templates are included in `inventree_bulk_plugin/freezer_templates`.
Administrators can import them into upstream's advanced generator. That generic
route does **not** enforce freezer-slot occupancy or retry rules; use the freezer
panel/endpoint for those guarantees. Templates contain no lab-specific IDs.

