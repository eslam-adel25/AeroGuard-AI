import axios, { AxiosHeaders } from "axios";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(
  /\/$/,
  "",
);

export interface ZoneCreateData {
  zone_name: string;
  zone_type: string;
  polygon_coords: [number, number][]; // مصفوفة من الإحداثيات [x, y]
}

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getStoredAuthToken = () => {
  const token = localStorage.getItem("ag_token");
  if (!token || token === "null" || token === "undefined") {
    localStorage.removeItem("ag_token");
    return null;
  }
  return token;
};

/**
 * نظام حماية الطلبات: إرفاق توكن JWT تلقائياً (صفحة 79)
 */
api.interceptors.request.use((config) => {
  const token = getStoredAuthToken();
  if (token) {
    const headers =
      config.headers instanceof AxiosHeaders
        ? config.headers
        : new AxiosHeaders(config.headers);

    headers.set("Authorization", `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

/**
 * واجهات البيانات (Interfaces) لضمان جودة الكود ومنع أخطاء any
 */
export interface ISystemSettings {
  organization_name: string;
  airport_name: string;
  language: string;
  timezone: string;
  system_name: string;
  detection_confidence: number;
  tracking_enabled: boolean;
  object_detection_enabled: boolean;
  face_detection_enabled: boolean;
  face_recognition_enabled: boolean;
  max_objects: number;
  enable_alert_sounds: boolean;
  alert_duration: number;
  min_alert_confidence: number;
  show_alert_labels: boolean;
  default_fps: number;
  recording_quality: string;
  frame_buffer: number;
  auto_reconnect: boolean;
  video_resolution: string;
  compression_enabled: boolean;
  jpeg_quality: number;
  jwt_expiration: number;
  session_timeout: number;
  // Performance / runtime
  gpu_enabled?: boolean;
  frame_skip?: number;
  // Phase 7 AI module toggles and thresholds
  loitering_enabled?: boolean;
  loitering_seconds?: number;
  crowd_density_enabled?: boolean;
  crowd_density_threshold?: number;
  abandoned_bag_enabled?: boolean;
  abandoned_bag_seconds?: number;
  wrong_direction_enabled?: boolean;
  wrong_direction_angle_threshold?: number;
  restricted_area_enabled?: boolean;
  fire_detection_enabled?: boolean;
  smoke_detection_enabled?: boolean;
}

export interface IUserProfile {
  user_id: string;
  full_name: string;
  username: string;
  email: string;
  phone?: string;
  organization?: string;
  profile_picture?: string;
  status: string;
  created_at: string;
  last_login?: string;
  role_id: string;

  role?: {
    role_name: string;
  };
}

export interface RegisterData {
  full_name: string;
  username: string;
  email: string;
  password: string;
  confirm_password?: string;
  phone: string;
  organization?: string;
}

export interface LoginData {
  username: string;
  password: string;
}

export const authService = {
  register: (data: RegisterData) =>
    api.post("/auth/register", {
      full_name: data.full_name,
      username: data.username,
      email: data.email,
      password: data.password,
      phone: data.phone,
      organization: data.organization,
    }),

  login: (data: LoginData) => api.post("/auth/login", data),

  verifyEmail: (token: string) =>
    api.get("/auth/verify", { params: { token } }),

  verifyOtp: (email: string, code: string) =>
    api.post("/auth/verify-otp", { email, code }),

  resendVerification: (email: string) =>
    api.post("/auth/resend-verification", { email }),

  logout: () => {
    localStorage.removeItem("ag_token");
    localStorage.removeItem("user");
  },
};

/**
 * خدمات المستخدمين والأدوار
 */
export const userService = {
  // ... الدوال السابقة ...
  getProfile: () => api.get("/users/profile"),
  updateProfile: (data: IUserProfile) => api.put("/users/profile", data),
  updatePassword: (data: Record<string, unknown>) =>
    api.post("/users/profile/password", data),
  uploadAvatar: (formData: FormData) =>
    api.post("/users/profile/avatar", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  changeEmail: (newEmail: string) =>
    api.post("/users/profile/change-email", { new_email: newEmail }),
  getActivity: () => api.get("/users/profile/activity"),
  getSessions: () => api.get("/users/profile/sessions"),
  logoutAllSessions: () => api.post("/users/profile/logout-all"),
};

/**
 * خدمات إدارة الكاميرات والرفع والمناطق المحظورة
 */
export const cameraService = {
  getAll: () => api.get("/cameras/"),

  // دالة شاملة لرفع الفيديو أو ربط البث الحي عبر FormData (صفحة 206)
  create: (formData: FormData) => api.post("/cameras/", formData),

  start: (id: string) => api.post(`/cameras/${id}/start`),

  getZones: (id: string) => api.get(`/cameras/${id}/zones`),

  delete: (id: string) => api.delete(`/cameras/${id}`),

  // تم استبدال any بـ ZoneCreateData لحل الخطأ الثاني
  addZone: (id: string, data: ZoneCreateData) =>
    api.post(`/cameras/${id}/zones`, data),
};

export const settingsService = {
  get: () => api.get("/settings/"),
  update: (data: ISystemSettings) => api.put("/settings/", data),
  reset: () => api.post("/settings/reset"),
};

/**
 * خدمات التقارير والإحصائيات (صفحة 128)
 
export const reportService = {
  getAnalytics: (filters: {
    start_date: string;
    end_date: string;
    camera_id: string;
  }) =>
    api.get("/analytics/daily", {
      params: filters,
    }),

  generateReport: (type: string) =>
    api.post("/reports/", { report_type: type }),

  getAllReports: () => api.get("/reports/"),
};*/

export const reportService = {
  getDashboard: (filters: {
    start_date: string;
    end_date: string;
    camera_id?: string;
  }) =>
    api.get("/reports/dashboard", {
      params: filters,
    }),

  generateReport: (payload: {
    start_date: string;
    end_date: string;
    camera_id?: string;
    title?: string;
    report_type?: string;
  }) => api.post("/reports/generate", payload),

  getAllReports: (params?: {
    limit?: number;
    offset?: number;
    query?: string;
    camera_id?: string;
    start_date?: string;
    end_date?: string;
  }) => api.get("/reports/", { params }),

  getReport: (report_id: string) => api.get(`/reports/${report_id}`),

  exportCsv: (report_id: string) =>
    api.get("/reports/export/csv", {
      params: { report_id },
      responseType: "blob",
    }),
  exportExcel: (report_id: string) =>
    api.get("/reports/export/excel", {
      params: { report_id },
      responseType: "blob",
    }),
  exportPdf: (report_id: string) =>
    api.get("/reports/export/pdf", {
      params: { report_id },
      responseType: "blob",
    }),

  deleteReport: (report_id: string) => api.delete(`/reports/${report_id}`),
};

export const aiService = {
  listEvents: (params?: {
    camera_id?: string;
    limit?: number;
    offset?: number;
  }) => api.get(`/ai/events`, { params }),
  getEvent: (event_id: string) => api.get(`/ai/events/${event_id}`),
  downloadScreenshot: (event_id: string) =>
    api.get(`/ai/events/${event_id}/screenshot`, { responseType: "blob" }),
};

export default api;
