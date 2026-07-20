import { createContext } from "react";

export type ToastType = "success" | "info" | "warning" | "error" | "loading";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description: string;
  duration?: number;
  createdAt: number;
}

export interface ConfirmationOptions {
  id: string;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  type?: "warning" | "danger" | "info";
  onConfirm: () => void | Promise<void>;
  onCancel?: () => void;
}

export interface NotificationContextType {
  toasts: Toast[];
  activeConfirmation: ConfirmationOptions | null;
  addToast: (
    type: ToastType,
    title: string,
    description: string,
    duration?: number,
  ) => string;
  updateToast: (
    id: string,
    updates: Partial<Omit<Toast, "id" | "createdAt">>,
  ) => void;
  dismissToast: (id: string) => void;
  confirm: (options: Omit<ConfirmationOptions, "id">) => void;
  closeConfirmation: () => void;
}

interface NotificationStoreSnapshot {
  toasts: Toast[];
  activeConfirmation: ConfirmationOptions | null;
}

type NotificationListener = () => void;

let notificationState: NotificationStoreSnapshot = {
  toasts: [],
  activeConfirmation: null,
};

const notificationListeners = new Set<NotificationListener>();

const notifyListeners = () => {
  notificationListeners.forEach((listener) => listener());
};

const cloneToast = (toast: Toast): Toast => ({ ...toast });

const cloneConfirmation = (
  confirmation: ConfirmationOptions | null,
): ConfirmationOptions | null => {
  if (!confirmation) return null;
  return { ...confirmation };
};

const addToast = (
  type: ToastType,
  title: string,
  description: string,
  duration?: number,
) => {
  const id = Math.random().toString(36).substring(2, 9);

  let finalDuration = duration;
  if (finalDuration === undefined) {
    switch (type) {
      case "success":
        finalDuration = 3000;
        break;
      case "info":
        finalDuration = 4000;
        break;
      case "warning":
        finalDuration = 5000;
        break;
      case "error":
        finalDuration = 8000;
        break;
      case "loading":
        finalDuration = undefined;
        break;
    }
  }

  const newToast: Toast = {
    id,
    type,
    title,
    description,
    duration: finalDuration,
    createdAt: Date.now(),
  };

  notificationState = {
    ...notificationState,
    toasts: [newToast, ...notificationState.toasts].slice(0, 4),
  };

  notifyListeners();
  return id;
};

const updateToast = (
  id: string,
  updates: Partial<Omit<Toast, "id" | "createdAt">>,
) => {
  notificationState = {
    ...notificationState,
    toasts: notificationState.toasts.map((toast) => {
      if (toast.id !== id) return toast;

      let updatedDuration = updates.duration;
      if (updatedDuration === undefined && updates.type) {
        switch (updates.type) {
          case "success":
            updatedDuration = 3000;
            break;
          case "info":
            updatedDuration = 4000;
            break;
          case "warning":
            updatedDuration = 5000;
            break;
          case "error":
            updatedDuration = 8000;
            break;
          case "loading":
            updatedDuration = undefined;
            break;
        }
      }

      return {
        ...toast,
        ...updates,
        duration:
          updatedDuration !== undefined ? updatedDuration : toast.duration,
      };
    }),
  };

  notifyListeners();
};

const dismissToast = (id: string) => {
  notificationState = {
    ...notificationState,
    toasts: notificationState.toasts.filter((toast) => toast.id !== id),
  };

  notifyListeners();
};

const confirm = (options: Omit<ConfirmationOptions, "id">) => {
  const id = Math.random().toString(36).substring(2, 9);
  notificationState = {
    ...notificationState,
    activeConfirmation: {
      ...options,
      id,
    },
  };

  notifyListeners();
};

const closeConfirmation = () => {
  notificationState = {
    ...notificationState,
    activeConfirmation: null,
  };

  notifyListeners();
};

export const notificationStore = {
  subscribe(listener: NotificationListener) {
    notificationListeners.add(listener);
    return () => {
      notificationListeners.delete(listener);
    };
  },
  getSnapshot(): NotificationStoreSnapshot {
    return {
      toasts: notificationState.toasts.map(cloneToast),
      activeConfirmation: cloneConfirmation(
        notificationState.activeConfirmation,
      ),
    };
  },
  addToast,
  updateToast,
  dismissToast,
  confirm,
  closeConfirmation,
  getContextValue(): NotificationContextType {
    return {
      toasts: notificationState.toasts.map(cloneToast),
      activeConfirmation: cloneConfirmation(
        notificationState.activeConfirmation,
      ),
      addToast,
      updateToast,
      dismissToast,
      confirm,
      closeConfirmation,
    };
  },
};

export const NotificationContext = createContext<
  NotificationContextType | undefined
>(undefined);
