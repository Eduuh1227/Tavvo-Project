# Catalog, publishing and image boundary

All administrative resources take the restaurant UUID from the URL, authorize the active membership, set the PostgreSQL transaction-local tenant scope and filter by that same restaurant. Client payloads cannot move a category, product, image or table to another restaurant. Product/category and image/product ownership is also enforced by composite database foreign keys in `core` migrations.

The public menu requires an active restaurant, a published non-archived category, and a published non-archived product. Unavailable products remain visible with `is_available=false`; they are not implicitly unpublished. Administrative DELETE on products/categories archives them. Archiving a category hides the full branch immediately without destroying products. Images on archived products remain private until explicitly deleted. Public responses and image responses use `Cache-Control: no-store` so publication changes are not hidden by an application cache.

Managers may manage their own catalog, settings and tables, and read domains and audit records. Staff may read catalog/tables and change availability through the separate `/availability/` action. Tavvo administrators must complete MFA and may manage restaurants, memberships, settings and domain associations; they need an explicit restaurant membership to edit its catalog.

## Images

`POST /v1/restaurants/{restaurant_id}/products/{product_id}/images/` takes multipart fields `file` and optional `sort_order`. JPEG, PNG and WebP are decoded and re-encoded; metadata and appended content are discarded. Limits are 5 MiB encoded size and 20 million pixels. File names and client MIME types are never trusted. Objects receive random names below `restaurants/{restaurant_id}/products/{product_id}/` in a private S3 bucket. Database rows store only the object reference and metadata.

Authenticated downloads use `/v1/restaurants/{restaurant_id}/images/{image_id}/`. Public downloads use `/v1/public/restaurants/{slug}/images/{image_id}/` and recheck the entire publication chain. The application never returns object keys or permanent public bucket URLs. The bucket must remain private; do not add a public-read policy.

Deleting an image first removes the database reference transactionally and schedules S3 deletion after commit. A failed object deletion is logged; the unreferenced object remains inaccessible through the API. Failed metadata creation attempts to delete the newly uploaded object. Transaction failures after upload can also leave private orphan objects. Use the reconciliation command to inspect objects unreferenced for at least 24 hours and delete them explicitly:

```console
python manage.py reconcile_images --restaurant-id <UUID>
python manage.py reconcile_images --restaurant-id <UUID> --delete
```

## Domains and QR codes

`GET /v1/public/resolve/?hostname=...` resolves only verified domains associated with active restaurants. Unknown or pending hostnames fail without a fallback. Hostname normalization rejects protocols, paths and ports and stores lower-case IDNA. Only a Tavvo administrator can create, verify, change or remove a domain; verification in this MVP means an operator has checked DNS control outside the application. The API does not automate DNS ownership verification or certificate provisioning. Changing a verified hostname resets its state to pending.

An optional `hostname` query on a public restaurant request must resolve to that restaurant. Explicit slug routes remain public by design. Custom frontends must resolve their hostname and fail closed before loading a menu. A public hostname or QR code grants no administrative access.

Tables expose stable public codes composed of a restaurant UUID routing hint and a random 192-bit suffix. `/v1/public/qr/{code}/` resolves only active restaurants and active tables. `/v1/restaurants/{restaurant_id}/tables/{id}/qr/?format=svg` (or `png`) generates an image containing the public site's `/q/{code}` URL. Renaming a table or changing a restaurant slug leaves printed codes valid; deactivating the table invalidates resolution immediately.
