import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MutableRefObject,
  type ReactNode,
} from "react";
import { settingsService } from "../services/api";
import { createSocket, type WSMessage } from "../services/socket";
import {
  AlertAudioContext,
  type AlarmState,
} from "./AlertAudioContext";

const FIRE_ALARM_AUDIO = "/sounds/fire_alarm.mp3";
const SECURITY_ALARM_AUDIO = "/sounds/security_alarm.mp3";

const createLoopingAudio = (src: string) => {
  const audio = new Audio(src);
  audio.loop = true;
  audio.preload = "auto";
  audio.volume = 0.75;
  audio.crossOrigin = "anonymous";
  audio.addEventListener("error", () => {
    console.error(`Failed to load alert audio: ${src}`);
  });
  return audio;
};

const isFireAlarmSource = (sources: string[]) =>
  sources.some((source) => /^(fire|flame|smoke)$/i.test(source.trim()));

const isSecurityAlarmSource = (sources: string[]) =>
  sources.some(
    (source) =>
      source.trim() !== "" && !/^(fire|flame|smoke)$/i.test(source.trim()),
  );

export const AlertAudioProvider = ({ children }: { children: ReactNode }) => {
  const [alarmStateByCamera, setAlarmStateByCamera] = useState<
    Record<string, AlarmState>
  >({});
  const [mutedCameraIds, setMutedCameraIds] = useState<Record<string, boolean>>(
    {},
  );
  const [alertSoundsEnabled, setAlertSoundsEnabled] = useState(true);
  const settingsVersionRef = useRef(0);
  const fireAlarmAudioRef = useRef<HTMLAudioElement | null>(null);
  const securityAlarmAudioRef = useRef<HTMLAudioElement | null>(null);
  const firePlayAttemptRef = useRef(0);
  const securityPlayAttemptRef = useRef(0);
  const firePlayPendingRef = useRef(false);
  const securityPlayPendingRef = useRef(false);

  const toggleCameraMute = useCallback((cameraId: string) => {
    setMutedCameraIds((current) => ({
      ...current,
      [cameraId]: !current[cameraId],
    }));
  }, []);

  const clearCameraMute = useCallback((cameraId: string) => {
    setMutedCameraIds((current) => {
      if (!current[cameraId]) {
        return current;
      }
      const next = { ...current };
      delete next[cameraId];
      return next;
    });
  }, []);

  const updateAlertSoundsEnabled = useCallback((enabled: boolean) => {
    settingsVersionRef.current += 1;
    setAlertSoundsEnabled(enabled);
  }, []);

  const handleMessage = useCallback(
    (message: WSMessage) => {
      if (message.event === "alarm_state") {
        const state = {
          active: message.data.active,
          sources: message.data.sources ?? [],
        };
        setAlarmStateByCamera((current) => ({
          ...current,
          [message.data.camera_id]: state,
        }));
        if (!state.active) {
          clearCameraMute(message.data.camera_id);
        }
      } else if (message.event === "alarm_state_snapshot") {
        const states = Object.fromEntries(
          Object.entries(message.data.states).map(([cameraId, state]) => [
            cameraId,
            { active: state.active, sources: state.sources ?? [] },
          ]),
        );
        setAlarmStateByCamera(states);
        setMutedCameraIds((current) =>
          Object.fromEntries(
            Object.entries(current).filter(
              ([cameraId, isMuted]) => isMuted && states[cameraId]?.active,
            ),
          ),
        );
      } else if (
        message.event === "camera_status" &&
        message.data.status === "Offline"
      ) {
        setAlarmStateByCamera((current) => ({
          ...current,
          [message.data.camera_id]: { active: false, sources: [] },
        }));
        clearCameraMute(message.data.camera_id);
      } else if (message.event === "socket_disconnected") {
        setAlarmStateByCamera({});
      }
    },
    [clearCameraMute],
  );

  useEffect(() => {
    let mounted = true;
    const settingsVersion = settingsVersionRef.current;
    const socket = createSocket(handleMessage);
    void settingsService
      .get()
      .then((response) => {
        if (mounted && settingsVersionRef.current === settingsVersion) {
          setAlertSoundsEnabled(response.data?.enable_alert_sounds ?? true);
        }
      })
      .catch((error) => {
        console.error("Failed to load alert sound setting:", error);
      });

    return () => {
      mounted = false;
      socket.close();
    };
  }, [handleMessage]);

  const stopAudio = useCallback(
    (
      audioRef: MutableRefObject<HTMLAudioElement | null>,
      attemptRef: MutableRefObject<number>,
      pendingRef: MutableRefObject<boolean>,
    ) => {
      attemptRef.current += 1;
      pendingRef.current = false;
      const audio = audioRef.current;
      if (!audio) {
        return;
      }
      if (!audio.paused) {
        audio.pause();
      }
      audio.currentTime = 0;
    },
    [],
  );

  const playAudio = useCallback(
    (
      audioRef: MutableRefObject<HTMLAudioElement | null>,
      attemptRef: MutableRefObject<number>,
      pendingRef: MutableRefObject<boolean>,
      src: string,
    ) => {
      if (!audioRef.current) {
        audioRef.current = createLoopingAudio(src);
      }
      const audio = audioRef.current;
      if (audio.paused && !pendingRef.current) {
        pendingRef.current = true;
        const attempt = ++attemptRef.current;
        audio.currentTime = 0;
        void audio
          .play()
          .then(() => {
            if (attemptRef.current === attempt) {
              pendingRef.current = false;
            }
          })
          .catch((error: unknown) => {
            if (attemptRef.current === attempt) {
              pendingRef.current = false;
              console.error(`Failed to play alert audio: ${src}`, error);
            }
          });
      }
    },
    [],
  );

  useEffect(() => {
    let fireRequired = false;
    let securityRequired = false;

    Object.entries(alarmStateByCamera).forEach(([cameraId, alarm]) => {
      if (!alarm.active || mutedCameraIds[cameraId]) {
        return;
      }
      fireRequired ||= isFireAlarmSource(alarm.sources);
      securityRequired ||= isSecurityAlarmSource(alarm.sources);
    });

    if (alertSoundsEnabled && fireRequired) {
      playAudio(
        fireAlarmAudioRef,
        firePlayAttemptRef,
        firePlayPendingRef,
        FIRE_ALARM_AUDIO,
      );
    } else {
      stopAudio(
        fireAlarmAudioRef,
        firePlayAttemptRef,
        firePlayPendingRef,
      );
    }

    if (alertSoundsEnabled && securityRequired) {
      playAudio(
        securityAlarmAudioRef,
        securityPlayAttemptRef,
        securityPlayPendingRef,
        SECURITY_ALARM_AUDIO,
      );
    } else {
      stopAudio(
        securityAlarmAudioRef,
        securityPlayAttemptRef,
        securityPlayPendingRef,
      );
    }
  }, [
    alarmStateByCamera,
    alertSoundsEnabled,
    mutedCameraIds,
    playAudio,
    stopAudio,
  ]);

  useEffect(
    () => () => {
      stopAudio(fireAlarmAudioRef, firePlayAttemptRef, firePlayPendingRef);
      stopAudio(
        securityAlarmAudioRef,
        securityPlayAttemptRef,
        securityPlayPendingRef,
      );
      if (fireAlarmAudioRef.current) {
        fireAlarmAudioRef.current.src = "";
        fireAlarmAudioRef.current = null;
      }
      if (securityAlarmAudioRef.current) {
        securityAlarmAudioRef.current.src = "";
        securityAlarmAudioRef.current = null;
      }
    },
    [stopAudio],
  );

  const value = useMemo(
    () => ({
      alarmStateByCamera,
      mutedCameraIds,
      toggleCameraMute,
      setAlertSoundsEnabled: updateAlertSoundsEnabled,
    }),
    [
      alarmStateByCamera,
      mutedCameraIds,
      toggleCameraMute,
      updateAlertSoundsEnabled,
    ],
  );

  return (
    <AlertAudioContext.Provider value={value}>
      {children}
    </AlertAudioContext.Provider>
  );
};
