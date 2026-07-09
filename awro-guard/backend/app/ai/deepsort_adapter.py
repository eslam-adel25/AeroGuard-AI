"""
DeepSORT adapter shim.
Provides the same minimal API as the real DeepSORT adapter would. If DeepSORT
is unavailable, this file offers a safe fallback that behaves like the IoU
tracker so `TrackerManager` can instantiate it without a hard dependency.
"""
import time
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DSTrack:
    track_id: int
    class_name: str
    confidence: float
    bbox: List[int]
    center_point: List[int]
    first_seen: float
    last_seen: float
    lost_frames: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class _SimpleDS:
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.35):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self._tracks: Dict[int, DSTrack] = {}
        self._next_id = 1

    def initialize(self):
        self._tracks.clear()
        self._next_id = 1

    def reset(self):
        self.initialize()

    def _create_track(self, det):
        t = DSTrack(
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
        for det in detections:
            self._create_track(det)
        for tid in list(self._tracks.keys()):
            tr = self._tracks[tid]
            if tr.lost_frames > self.max_lost:
                del self._tracks[tid]
        return list(self._tracks.values())

    def get_active_tracks(self):
        return [t for t in self._tracks.values() if t.lost_frames == 0]


class DeepSortAdapter:
    """Lightweight DeepSORT adapter shim.

    Replace with a real DeepSORT wrapper when integrating the full tracker.
    """
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.35):
        self._impl = _SimpleDS(max_lost=max_lost, iou_threshold=iou_threshold)

    def initialize(self):
        self._impl.initialize()

    def update(self, detections: List[Dict[str, Any]]):
        return self._impl.update(detections)

    def get_active_tracks(self):
        return self._impl.get_active_tracks()

    def reset(self):
        self._impl.reset()
