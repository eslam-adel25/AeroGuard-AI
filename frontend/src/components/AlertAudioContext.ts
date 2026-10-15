import { createContext } from "react";

export type AlarmState = {
  active: boolean;
  sources: string[];
};

export type AlertAudioContextValue = {
  alarmStateByCamera: Record<string, AlarmState>;
  mutedCameraIds: Record<string, boolean>;
  toggleCameraMute: (cameraId: string) => void;
  setAlertSoundsEnabled: (enabled: boolean) => void;
};

export const AlertAudioContext =
  createContext<AlertAudioContextValue | null>(null);
