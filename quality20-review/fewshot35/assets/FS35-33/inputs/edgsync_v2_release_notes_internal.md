# EdgeSync Pro v2.0.0 Internal Release Notes

## 1. Authentication & Security
- **Removed**: Legacy PIN-based authentication.
- **Added**: mTLS (Mutual TLS) certificate authentication. Device certificates must be placed in `/etc/edgsync/certs/device.pem` and the corresponding CA in `/etc/edgsync/certs/ca.pem`.
- **Known Issue**: mTLS handshake will fail with TLS error if the device system time deviates from the server time by more than 5 minutes. Ensure NTP is strictly configured.

## 2. API Changes
- **Deprecated & Removed**: `POST /api/v1/sync` is completely removed in v2.0.
- **New Endpoint**: Use `POST /api/v2/devices/{device_id}/sync`.
- **Payload Limits**: Maximum records per request reduced from 1000 (v1) to 500 (v2) to optimize memory footprint on edge devices.

## 3. Synchronization Mechanism
- **Changed**: Switched from full-overwrite to incremental-merge sync based on timestamps and record hashes.
- **Impact**: If device time is inaccurate, older records might overwrite newer ones on the server, appearing as "data loss". Time synchronization is critical.

## 4. Offline Queue Management
- **Added**: Priority levels for offline queues. Payload accepts `priority` field with values `HIGH` or `NORMAL`.
- **Behavior**: When network restores, `HIGH` priority records are uploaded first.
- **Configuration**: Default `max_queue_size` reduced from 10000 to 5000. Must be explicitly increased in `edgsync.conf` if high-throughput offline scenarios are expected.

## 5. Logging & Storage
- **Changed**: Default log directory moved from `/var/log/` to `/var/log/edgsync/`.
- **Warning**: Default log level is `INFO`. If set to `DEBUG`, it will rapidly consume disk space and cause device reboots due to I/O blocking. Monitor disk usage.