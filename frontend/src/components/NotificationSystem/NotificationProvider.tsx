import React, { useMemo, useSyncExternalStore } from "react";
import {
  NotificationContext,
  notificationStore,
} from "./NotificationContext.ts";
import { NotificationRenderer } from "./NotificationComponents.tsx";

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const snapshot = useSyncExternalStore(
    notificationStore.subscribe,
    notificationStore.getSnapshot,
    notificationStore.getSnapshot,
  );

  const value = useMemo(
    () => ({
      toasts: snapshot.toasts,
      activeConfirmation: snapshot.activeConfirmation,
      addToast: notificationStore.addToast,
      updateToast: notificationStore.updateToast,
      dismissToast: notificationStore.dismissToast,
      confirm: notificationStore.confirm,
      closeConfirmation: notificationStore.closeConfirmation,
    }),
    [snapshot],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
      <NotificationRenderer />
    </NotificationContext.Provider>
  );
};
