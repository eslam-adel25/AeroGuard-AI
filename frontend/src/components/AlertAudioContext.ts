import { createContext } from "react";

export type AlarmState = {
  active: boolean;
  sources: string[];
};

export type TripwireAlarmState = {
  event_id: string;
  silenced: boolean;
};

export type AlertAudioContextValue = {
  alarmStateByCamera: Record<string, AlarmState>;
  mutedCameraIds: Record<string, boolean>;
  tripwireAlarmStates: Record<string, Record<string, TripwireAlarmState>>;
  toggleCameraMute: (cameraId: string) => void;
  silenceTripwireAlarm: (cameraId: string, zoneId: string) => void;
  setAlertSoundsEnabled: (enabled: boolean) => void;
};

export const AlertAudioContext =
  createContext<AlertAudioContextValue | null>(null);
