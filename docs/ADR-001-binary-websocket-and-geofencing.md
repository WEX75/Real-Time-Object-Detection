# ADR-001: Binary WebSocket Frames and Future Geofencing

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

The browser camera produces image frames continuously. Sending them as JSON
base64 adds avoidable encoding overhead. Detection results also need to be
available as structured telemetry, and the application is expected to support
perimeter/geofencing analytics later.

## Decision

- Send camera frames to `/ws/detect` as binary JPEG WebSocket messages.
- Return a JSON telemetry message followed by a binary annotated JPEG for each
  processed frame.
- Persist each detected object in SQLite with its label, confidence, and
  creation time.
- Keep geofencing as a future extension. The current event schema deliberately
  does not claim location data that the camera client does not provide.

## Consequences

Binary frames avoid base64 expansion and keep video transport separate from
structured detections. A client must read the JSON response before the
corresponding annotated image. Geofencing will require an explicit source of
camera coordinates or configured zones and a schema migration.
