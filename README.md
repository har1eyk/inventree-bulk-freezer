# InvenTree Bulk + Freezer Boxes

Create a freezer box and all of its positions in one step. Choose an empty rack slot, name your box, and preview the layout before creating it. For hundreds of boxes, use the included CSV importer.

| Layout | Position names | Total positions |
| --- | --- | --- |
| 9 × 9 (default) | A1–I9 | 81 |
| 10 × 10 | A1–J10 | 100 |

**Tested with InvenTree 1.3.2 and PostgreSQL 15.** Boxes and positions are ordinary InvenTree stock locations: they remain usable if you disable the plugin. This release creates empty locations; it does not register samples or print labels.

Maintained by [Harley King](https://github.com/har1eyk). Based on [InvenTree Bulk Plugin 1.5.2](https://github.com/wolflu05/inventree-bulk-plugin) by wolflu05, under the MIT license. [Upstream attribution](https://github.com/har1eyk/inventree-bulk-freezer/blob/main/UPSTREAM.md).

## Install

> **Install this package OR `inventree-bulk-plugin`, never both.** They share a plugin identity and database migration history. Back up your InvenTree database, media, and configuration before changing an existing installation.

These steps are for the person who administers your InvenTree server.

1. Install the pinned package in the Python environment used by **both the server and worker**:

   ```sh
   python -m pip install 'inventree-bulk-freezer==1.5.2.post2'
   ```

   For Docker, use your deployment's persistent plugin environment and add `inventree-bulk-freezer==1.5.2.post2` to its `plugins.txt`. Installing only inside a running container may be lost when it is recreated. If replacing the upstream package, uninstall `inventree-bulk-plugin` first in the same environment; keep its database tables.

2. Enable the InvenTree plugin framework. In **Admin Center**, enable **App**, **URL**, and **Interface** plugin integrations, then activate **InvenTree Bulk + Freezer Boxes**.
3. During your normal maintenance window, run migrations and collect static files using that environment, then restart the server and worker. From the official InvenTree container's application directory:

   ```sh
   python src/backend/InvenTree/manage.py migrate --noinput
   python src/backend/InvenTree/manage.py collectstatic --noinput
   ```

   For other deployments, use the path to your own `manage.py`.
4. Give operators the stock-location **view** and **add** permissions. Reload the browser page after enabling the plugin.

Enabling the plugin or restarting the server does not create any boxes. To remove the tools later, deactivate the plugin; leave the standard stock locations and template migration in place.

## Create your first box

### 1. Open the destination slot

Navigate to the stock location representing an **empty rack slot**. In its left sidebar, select **Create freezer box** under **Plugin Provided**. Check the full destination path.

![A demo rack slot with Create freezer box visible in the left sidebar](https://raw.githubusercontent.com/har1eyk/inventree-bulk-freezer/v1.5.2.post2/docs/images/01-find-panel.png)

*The tool is on the slot's location page. Reload the page if the plugin section is missing.*

### 2. Name the box and choose its layout

Enter a name such as `Demo_Box_01`. Keep **9 × 9** for 81 positions or choose **10 × 10** for 100 positions.

![The freezer-box form filled with Demo_Box_01 and the 9 by 9 layout](https://raw.githubusercontent.com/har1eyk/inventree-bulk-freezer/v1.5.2.post2/docs/images/02-name-layout.png)

*The displayed path tells you exactly where the box will be created.*

### 3. Preview, then create

Click **Preview**. Check the destination, box name, and grid, then click **Create freezer box**. Previewing does not change inventory.

![Preview showing the destination and all 81 positions from A1 through I9](https://raw.githubusercontent.com/har1eyk/inventree-bulk-freezer/v1.5.2.post2/docs/images/03-preview-grid.png)

*The box and every position are created together. A failed creation rolls back the whole box.*

### 4. Open the finished box

Click **Open box**, then **Sublocations** to see its positions. You can use these locations through InvenTree's normal stock workflows.

![The created Demo_Box_01 with its position sublocations in InvenTree](https://raw.githubusercontent.com/har1eyk/inventree-bulk-freezer/v1.5.2.post2/docs/images/04-created-positions.png)

*All positions start empty. The screenshots use fictional inventory in an isolated demo.*

## Create many boxes from a CSV

1. Copy the [sample CSV](https://github.com/har1eyk/inventree-bulk-freezer/blob/main/examples/boxes.csv). Use UTF-8 and these exact column names:

   ```csv
   box_name,rack_slot_id,layout
   Box_001,1001,9x9
   Box_002,1002,10x10
   ```

   Replace the example IDs with your actual empty slots. The number in `/web/stock/location/1001/` is the location ID. Assign each slot only once.

2. Set your server URL and API token in the environment. Use a token belonging to a user with stock-location view/add permissions; do not put the token in the CSV.

   ```sh
   export INVENTREE_URL=https://inventory.example.org
   # Set INVENTREE_TOKEN using your usual secret-management mechanism.
   ```

3. Run a **read-only preflight** and review the resolved paths and statuses:

   ```sh
   inventree-freezer-batch boxes.csv --report preview.csv
   ```

4. When every destination is correct, explicitly apply the batch:

   ```sh
   inventree-freezer-batch boxes.csv --apply --report results.csv
   ```

Every row must pass preflight before creation starts. Apply creates one box per transaction, saves the results after each request, and stops on the first error. The report includes box IDs and `created`, `skipped`, or `failed` statuses. If interrupted, rerun the same CSV: exact existing boxes are verified and skipped. Hundreds of boxes may take several minutes; timing depends on the size of the location tree.

The CLI requires Python 3.9 or later. You can also run it from a downloaded source checkout with `python -m inventree_bulk_plugin.batch ...`; this CLI needs only the Python standard library.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| No **Create freezer box** panel | Reload the page (⌘R on Mac; Ctrl+R on Windows/Linux). Check that the plugin and App/URL/Interface integrations are enabled and that your user has stock-location view/add permissions. |
| **Occupied slot** | Choose an empty slot. Stock or child locations count as occupied, even when the displayed stock count is zero. |
| **Already exists** | A box with the same name and exact layout is already there. It is left unchanged; this is a successful retry. |
| Existing box has a different or incomplete layout | Review it using ordinary InvenTree tools. This plugin never automatically resizes or repairs a box. |
| Request times out or a batch is interrupted | Run preflight again to reconcile server state. Creation may have completed before the response was lost. |

This workflow allows **one box per selected slot**. If a physical drawer holds several boxes, first create a separate child location for each box space, then choose one of those spaces. Ordinary InvenTree location editing can still change the hierarchy.

## More information

- [API and portable templates](https://github.com/har1eyk/inventree-bulk-freezer/blob/main/docs/api.md)
- [Development and tests](https://github.com/har1eyk/inventree-bulk-freezer/blob/main/docs/development.md)
- [Validation record](https://github.com/har1eyk/inventree-bulk-freezer/blob/main/VALIDATION.md)
- [Report a problem](https://github.com/har1eyk/inventree-bulk-freezer/issues)

The inherited advanced bulk generator is available to superusers. Its generic templates do not enforce the freezer workflow's occupancy or retry rules; use **Create freezer box** or the CSV importer for those guarantees.
