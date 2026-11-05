import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  acceptDetectionOverlay,
  calculateCoverLayout,
  mapNormalizedPointToCover,
} from "./detectionOverlay.ts";

const overlay = (camera_id, frame_sequence, detections = []) => ({
  camera_id,
  frame_sequence,
  capture_timestamp_ns: 123,
  frame_width: 1920,
  frame_height: 1080,
  draw_settings: { font_scale: 0.4, line_thickness: 2, padding: 3 },
  detections,
});

describe("original detection overlay receiver", () => {
  it("preserves the full detection metadata and accepts empty updates", () => {
    const incoming = overlay("camera-a", 5, [
      {
        track_id: "1",
        identity_id: 7,
        class_name: "person",
        confidence: 0.9,
        bbox: [100, 120, 400, 900],
        label: "ID:007 Person",
        status: "NORMAL",
        display_label: "Person",
        box_color_bgr: [0, 255, 0],
        box_color_rgb: [0, 255, 0],
        text_color_rgb: [0, 0, 0],
      },
      {
        track_id: "2",
        identity_id: null,
        class_name: "car",
        confidence: 0.85,
        bbox: [500, 300, 900, 800],
        label: "ID:000 Car\nRESTRICTED AREA",
        status: "DANGER",
        display_label: "RESTRICTED_AREA",
        box_color_bgr: [0, 0, 255],
        box_color_rgb: [255, 0, 0],
        text_color_rgb: [255, 255, 255],
      },
    ]);

    assert.deepEqual(
      acceptDetectionOverlay(null, incoming, "camera-a", 456),
      { ...incoming, receivedAt: 456 },
    );
    assert.deepEqual(
      acceptDetectionOverlay(
        { ...incoming, receivedAt: 456 },
        overlay("camera-a", 6),
        "camera-a",
        789,
      )?.detections,
      [],
    );
  });

  it("rejects other cameras and out-of-order frames", () => {
    const current = { ...overlay("camera-a", 5), receivedAt: 456 };

    assert.equal(
      acceptDetectionOverlay(current, overlay("camera-b", 6), "camera-a", 789),
      null,
    );
    assert.equal(
      acceptDetectionOverlay(current, overlay("camera-a", 4), "camera-a", 789),
      current,
    );
  });
});

describe("original detection overlay cover mapping", () => {
  it("maps source points through object-fit cover crop offsets", () => {
    const layout = calculateCoverLayout(1920, 1080, 800, 600);
    assert.ok(layout);

    const center = mapNormalizedPointToCover(
      [0.5, 0.5],
      1920,
      1080,
      layout,
    );
    const topLeft = mapNormalizedPointToCover(
      [0, 0],
      1920,
      1080,
      layout,
    );

    assert.deepEqual(center, [400, 300]);
    assert.ok(Math.abs(topLeft[0] - -133.33333333333337) < 0.001);
    assert.equal(topLeft[1], 0);
    assert.equal(calculateCoverLayout(0, 1080, 800, 600), null);
  });
});
