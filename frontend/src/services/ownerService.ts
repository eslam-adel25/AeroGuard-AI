import api from "./api";

export interface OwnerCustomerSummary {
  customer_profile_id: string;
  user_id: string;
  full_name: string;
  phone: string | null;
  organization: string | null;
  registration_date: string | null;
  last_updated: string | null;
  is_verified: boolean;
  workflow_status: string;
  account_status: string;
}

export interface OwnerCustomerList {
  items: OwnerCustomerSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface OwnerCustomerDetails extends OwnerCustomerSummary {
  username: string;
  email: string;
  password: string;
  max_camera_count: number | null;
  owner_notes: string | null;
}

export interface OwnerCustomerConfiguration {
  max_camera_count: number | null;
  owner_notes: string | null;
}

export interface OwnerCustomerActivation {
  max_camera_count: number | null;
}

export type OwnerQueue = "unread" | "under-review" | "customers";

export const ownerService = {
  listCustomers: (
    queue: OwnerQueue,
    params: { search?: string; limit?: number; offset?: number } = {},
  ) => {
    const path = {
      unread: "/owner/requests/unread",
      "under-review": "/owner/requests/under-review",
      customers: "/owner/customers",
    }[queue];
    return api.get<OwnerCustomerList>(path, { params });
  },
  getCustomer: (profileId: string) =>
    api.get<OwnerCustomerDetails>(`/owner/customers/${profileId}`),
  updateConfiguration: (
    profileId: string,
    configuration: OwnerCustomerConfiguration,
  ) =>
    api.patch<OwnerCustomerDetails>(
      `/owner/customers/${profileId}/configuration`,
      configuration,
    ),
  transition: (
    profileId: string,
    action: "under-review" | "activate" | "deactivate" | "reactivate",
    activation?: OwnerCustomerActivation,
  ) =>
    api.post<OwnerCustomerDetails>(
      `/owner/customers/${profileId}/${action}`,
      activation,
    ),
};
