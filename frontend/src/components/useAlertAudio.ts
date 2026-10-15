import { useContext } from "react";
import { AlertAudioContext } from "./AlertAudioContext";

export const useAlertAudio = () => {
  const context = useContext(AlertAudioContext);
  if (!context) {
    throw new Error("useAlertAudio must be used within AlertAudioProvider");
  }
  return context;
};
