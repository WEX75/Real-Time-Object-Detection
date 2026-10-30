# ADR-002: Zones, Rules and Client-Side Overlay

- **Status:** Accepted
- **Date:** 2026-10-30
- **Supersedes:** parts of ADR-001 (annotated JPEG response, per-detection persistence, deferred geofencing)

## Context

Vigilo turns the detection pipeline from ADR-001 into a product for cafes and
small shops: the user names the objects to look for, draws zones on the camera
image and attaches rules such as "objects left on table 1 with nobody there for
20 seconds". Building on ADR-001 as written raises four problems:

- The server draws boxes on every frame and sends the JPEG back. The video the
  user sees is only as fluid as detection (about 5 FPS on CPU), and every frame
  crosses the network twice.
- Drawing zones with the mouse needs a canvas over the live video anyway.
- Storing every detection at 5 FPS produces thousands of rows per minute that
  nobody reads.
- A fixed COCO model cannot detect an object the user just typed.

## Decision

1. **The browser draws the overlay.** The server answers each frame with JSON
   only. The browser shows the live `<video>` and a `<canvas>` on top of it with
   boxes, zones and zone states.
2. **Zones and rules are in scope now.** Zones are polygons in coordinates
   normalized to 0..1 of the frame, so no camera calibration is needed. A
   detection belongs to a zone when the bottom-center point of its box lies in
   the polygon (where an object touches the table, not where its top is).
   Three rule types: `presence`, `left_unattended`, `count_threshold`. Each zone
   has a state (FREE, OCCUPIED, NEEDS_CLEARING) driven by a state machine with
   timers and a 0.5 s debounce.
3. **Only events are persisted.** SQLite stores zone state changes and rule
   triggers/clears, plus the configuration (zones, rules, vocabulary). Raw
   detections are not stored.
4. **Open-vocabulary detector** (YOLO-World) behind a `Detector` interface, with
   `yolo11n.pt` as fallback and a fake implementation for tests.

Kept from ADR-001: binary JPEG frames from the client to `/ws/detect`.

## Alternatives considered

- **Keep server-side annotation.** Simple client, but the visible video is
  capped at detection speed and zone drawing still needs a client canvas.
- **Shapely for geometry.** Correct and fast, but a native dependency for a
  ray-casting function of twenty lines that we want to test ourselves.
- **Keep storing every detection.** Allows replaying history, but at a cost in
  disk and query time with no current use case; events carry what users act on.
- **Fine-tuned closed-vocabulary model.** Better accuracy on known classes, but
  needs training data and cannot follow a word typed during the demo.

## Consequences

- The client must map between video pixels and display pixels (`object-fit`),
  and the overlay can lag the video by one detection round trip.
- The WebSocket response shrinks to a small JSON message per frame.
- The rule engine is pure Python that takes detections and a timestamp, so it
  is tested with a fake clock and no model.
- The `events` table changes shape (zone, rule, kind, detail); old
  per-detection rows are not migrated.
- The open-vocabulary model downloads CLIP weights on first start; images need
  `git` and the `clip` package, and a cache volume avoids repeated downloads.
