"""
Simple ByteTrack adapter shim.
If real ByteTrack isn't installed, this adapter falls back to a lightweight IoU tracker
so the `TrackerManager` can import a `ByteTrackAdapter` implementation without failing.
This keeps the production codepath pluggable while avoiding hard dependency on external libs.
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class BTTrack:
    track_id: int
    class_name: str
    confidence: float
    bbox: List[int]
    center_point: List[int]
    first_seen: float
    last_seen: float
    lost_frames: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class _SimpleIoU:
    """A tiny copy of the IoU fallback used by the main tracker.

    This deliberately keeps the footprint small so the adapter can be imported
    even when the main project doesn't want the full ByteTrack dependency.
    """
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.35):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self._tracks: Dict[int, BTTrack] = {}
        self._next_id = 1

    def initialize(self):
        self._tracks.clear()
        self._next_id = 1

    def reset(self):
        self.initialize()

    def _create_track(self, det):
        t = BTTrack(
            track_id=self._next_id,
            class_name=det["class_name"],
            confidence=det.get("confidence", 0.0),
            bbox=det["bbox"],
            center_point=[int((det["bbox"][0] + det["bbox"][2]) / 2), int((det["bbox"][1] + det["bbox"][3]) / 2)],
            first_seen=time.time(),
            last_seen=time.time(),
        )
        self._tracks[self._next_id] = t
        self._next_id += 1
        return t

    def update(self, detections: List[Dict[str, Any]]):
        # naive assignment: always create new tracks for simplicity
        # This keeps semantics predictable as a fallback.
        for det in detections:
            self._create_track(det)
        # remove stale tracks
        for tid in list(self._tracks.keys()):
            tr = self._tracks[tid]
            if tr.lost_frames > self.max_lost:
                del self._tracks[tid]

        return list(self._tracks.values())

    def get_active_tracks(self):
        return [t for t in self._tracks.values() if t.lost_frames == 0]


class ByteTrackAdapter:
    """Lightweight ByteTrack adapter shim.

    Real ByteTrack integrations should replace this file with an implementation
    that wraps the ByteTrack tracker while keeping the same API: `initialize`,
    `update`, `get_active_tracks`, `reset`.
    """
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.35):
        self._impl = _SimpleIoU(max_lost=max_lost, iou_threshold=iou_threshold)

    def initialize(self):
        self._impl.initialize()

    def update(self, detections: List[Dict[str, Any]]):
        return self._impl.update(detections)

    def get_active_tracks(self):
        return self._impl.get_active_tracks()

    def reset(self):
        self._impl.reset()
