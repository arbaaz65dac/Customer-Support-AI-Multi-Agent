import { apiRequest } from "./client";

export function getMyRefundRequests(token) {
  return apiRequest("/api/refund-requests", { token });
}

export function createRefundRequest(request, token) {
  return apiRequest("/api/refund-requests", {
    method: "POST",
    body: request,
    token,
  });
}

export function getAdminRefundRequests(token) {
  return apiRequest("/api/admin/refund-requests", { token });
}

export function reviewRefundRequest(requestId, review, token) {
  return apiRequest(`/api/admin/refund-requests/${requestId}`, {
    method: "PATCH",
    body: review,
    token,
  });
}
