import type { DetectionOverlayWSData } from "../services/socket";

export type DetectionOverlay = DetectionOverlayWSData & {
  receivedAt: number;
  acceptedAt: number;
};

export type CoverLayout = {
  scale: number;
  offsetX: number;
  offsetY: number;
};

export const calculateCoverLayout = (
  naturalWidth: number,
  naturalHeight: number,
  displayWidth: number,
  displayHeight: number,
): CoverLayout | null => {
  if (
    naturalWidth <= 0 ||
    naturalHeight <= 0 ||
    displayWidth <= 0 ||
    displayHeight <= 0
  ) {
    return null;
  }

  const scale = Math.max(
    displayWidth / naturalWidth,
    displayHeight / naturalHeight,
  );
  return {
    scale,
    offsetX: Math.max(0, (naturalWidth * scale - displayWidth) / 2),
    offsetY: Math.max(0, (naturalHeight * scale - displayHeight) / 2),
  };
};

export const mapNormalizedPointToCover = (
  point: [number, number],
  naturalWidth: number,
  naturalHeight: number,
  layout: CoverLayout,
): [number, number] => [
  point[0] * naturalWidth * layout.scale - layout.offsetX,
  point[1] * naturalHeight * layout.scale - layout.offsetY,
];

export const acceptDetectionOverlay = (
  current: DetectionOverlay | null,
  incoming: DetectionOverlayWSData,
  selectedCameraId: string | null,
  receivedAt: number,
): DetectionOverlay | null => {
  if (!selectedCameraId || incoming.camera_id !== selectedCameraId) {
    return null;
  }
  if (
    current?.camera_id === incoming.camera_id &&
    current.frame_sequence > incoming.frame_sequence
  ) {
    return current;
  }
  return { ...incoming, receivedAt, acceptedAt: performance.now() };
};
