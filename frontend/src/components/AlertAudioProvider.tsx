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
  type AlertAudioContextValue,
  type AlarmState,
} from "./AlertAudioContext";

const FIRE_ALARM_AUDIO = "/sounds/fire_alarm.mp3";
const SECURITY_ALARM_AUDIO = "/sounds/security_alarm.mp3";
const TRIPWIRE_SILENCE_STORAGE_KEY = "aeroguard.tripwire-silenced-events";

const tripwireKey = (cameraId: string, zoneId: string) =>
  JSON.stringify([cameraId, zoneId]);

const parseTripwireKey = (key: string): [string, string] | null => {
  try {
    const parsed: unknown = JSON.parse(key);
    if (
      Array.isArray(parsed) &&
      parsed.length === 2 &&
      typeof parsed[0] === "string" &&
      typeof parsed[1] === "string"
    ) {
      return [parsed[0], parsed[1]];
    }
  } catch {
    return null;
  }
  return null;
};

const loadSilencedTripwireEvents = () => {
  try {
    const stored = window.sessionStorage.getItem(TRIPWIRE_SILENCE_STORAGE_KEY);
    if (!stored) {
      return {};
    }
    const parsed: unknown = JSON.parse(stored);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsed).filter(
        (entry): entry is [string, string] =>
          typeof entry[1] === "string" && parseTripwireKey(entry[0]) !== null,
      ),
    );
  } catch (error) {
    console.error("Failed to load silenced Tripwire events:", error);
    return {};
  }
};

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
  const [tripwireAlarmStates, setTripwireAlarmStates] = useState<
    Record<string, Record<string, { event_id: string }>>
  >({});
  const [silencedTripwireEvents, setSilencedTripwireEvents] = useState<
    Record<string, string>
  >(loadSilencedTripwireEvents);
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

  const silenceTripwireAlarm = useCallback(
    (cameraId: string, zoneId: string) => {
      const eventId = tripwireAlarmStates[cameraId]?.[zoneId]?.event_id;
      if (!eventId) {
        return;
      }
      setSilencedTripwireEvents((current) => ({
        ...current,
        [tripwireKey(cameraId, zoneId)]: eventId,
      }));
    },
    [tripwireAlarmStates],
  );

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
      } else if (message.event === "tripwire_alarm_state") {
        const { camera_id: cameraId, zone_id: zoneId } = message.data;
        const key = tripwireKey(cameraId, zoneId);
        if (message.data.active && message.data.event_id) {
          const eventId = message.data.event_id;
          setTripwireAlarmStates((current) => {
            if (current[cameraId]?.[zoneId]?.event_id === eventId) {
              return current;
            }
            return {
              ...current,
              [cameraId]: {
                ...current[cameraId],
                [zoneId]: { event_id: eventId },
              },
            };
          });
          setSilencedTripwireEvents((current) => {
            if (!current[key] || current[key] === eventId) {
              return current;
            }
            const next = { ...current };
            delete next[key];
            return next;
          });
        } else {
          setTripwireAlarmStates((current) => {
            if (!current[cameraId]?.[zoneId]) {
              return current;
            }
            const cameraStates = { ...current[cameraId] };
            delete cameraStates[zoneId];
            const next = { ...current };
            if (Object.keys(cameraStates).length > 0) {
              next[cameraId] = cameraStates;
            } else {
              delete next[cameraId];
            }
            return next;
          });
          setSilencedTripwireEvents((current) => {
            if (!(key in current)) {
              return current;
            }
            const next = { ...current };
            delete next[key];
            return next;
          });
        }
      } else if (message.event === "tripwire_alarm_snapshot") {
        const states = Object.fromEntries(
          Object.entries(message.data.states).flatMap(
            ([cameraId, cameraStates]) => {
              const activeStates = Object.fromEntries(
                Object.entries(cameraStates)
                  .filter(([, state]) => state.active && state.event_id)
                  .map(([zoneId, state]) => [
                    zoneId,
                    { event_id: state.event_id },
                  ]),
              );
              return Object.keys(activeStates).length > 0
                ? [[cameraId, activeStates]]
                : [];
            },
          ),
        );
        setTripwireAlarmStates(states);
        setSilencedTripwireEvents((current) =>
          Object.fromEntries(
            Object.entries(current).filter(([key, eventId]) => {
              const parsedKey = parseTripwireKey(key);
              return (
                parsedKey !== null &&
                states[parsedKey[0]]?.[parsedKey[1]]?.event_id === eventId
              );
            }),
          ),
        );
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

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        TRIPWIRE_SILENCE_STORAGE_KEY,
        JSON.stringify(silencedTripwireEvents),
      );
    } catch (error) {
      console.error("Failed to persist silenced Tripwire events:", error);
    }
  }, [silencedTripwireEvents]);

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
    securityRequired ||= Object.entries(tripwireAlarmStates).some(
      ([cameraId, zones]) =>
        Object.entries(zones).some(
          ([zoneId, alarm]) =>
            silencedTripwireEvents[tripwireKey(cameraId, zoneId)] !==
            alarm.event_id,
        ),
    );

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
    silencedTripwireEvents,
    tripwireAlarmStates,
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

  const value = useMemo<AlertAudioContextValue>(
    () => ({
      alarmStateByCamera,
      mutedCameraIds,
      tripwireAlarmStates: Object.fromEntries(
        Object.entries(tripwireAlarmStates).map(([cameraId, zones]) => [
          cameraId,
          Object.fromEntries(
            Object.entries(zones).map(([zoneId, alarm]) => [
              zoneId,
              {
                ...alarm,
                silenced:
                  silencedTripwireEvents[tripwireKey(cameraId, zoneId)] ===
                  alarm.event_id,
              },
            ]),
          ),
        ]),
      ),
      toggleCameraMute,
      silenceTripwireAlarm,
      setAlertSoundsEnabled: updateAlertSoundsEnabled,
    }),
    [
      alarmStateByCamera,
      mutedCameraIds,
      tripwireAlarmStates,
      silencedTripwireEvents,
      toggleCameraMute,
      silenceTripwireAlarm,
      updateAlertSoundsEnabled,
    ],
  );

  return (
    <AlertAudioContext.Provider value={value}>
      {children}
    </AlertAudioContext.Provider>
  );
};
