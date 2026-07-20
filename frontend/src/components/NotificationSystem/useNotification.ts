import { useContext, useSyncExternalStore } from "react";
import {
  NotificationContext,
  notificationStore,
} from "./NotificationContext.ts";
import type { Toast } from "./NotificationContext.ts";

export const useNotification = () => {
  const context = useContext(NotificationContext);
  const state = useSyncExternalStore(
    notificationStore.subscribe,
    notificationStore.getSnapshot,
    notificationStore.getSnapshot,
  );

  const value = context ?? {
    toasts: state.toasts,
    activeConfirmation: state.activeConfirmation,
    addToast: notificationStore.addToast,
    updateToast: notificationStore.updateToast,
    dismissToast: notificationStore.dismissToast,
    confirm: notificationStore.confirm,
    closeConfirmation: notificationStore.closeConfirmation,
  };

  return {
    toasts: value.toasts,
    activeConfirmation: value.activeConfirmation,
    dismissToast: value.dismissToast,
    closeConfirmation: value.closeConfirmation,
    confirm: value.confirm,

    toast: {
      success: (title: string, description: string, duration?: number) =>
        value.addToast("success", title, description, duration),
      info: (title: string, description: string, duration?: number) =>
        value.addToast("info", title, description, duration),
      warning: (title: string, description: string, duration?: number) =>
        value.addToast("warning", title, description, duration),
      error: (title: string, description: string, duration?: number) =>
        value.addToast("error", title, description, duration),
      loading: (title: string, description: string) =>
        value.addToast("loading", title, description),
      update: (id: string, updates: Partial<Omit<Toast, "id" | "createdAt">>) =>
        value.updateToast(id, updates),
      dismiss: (id: string) => value.dismissToast(id),
    },
  };
};
