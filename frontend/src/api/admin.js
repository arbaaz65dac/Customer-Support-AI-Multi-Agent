import { apiRequest } from "./client";

export function getAdminDashboard(token) {
  return apiRequest("/api/admin/dashboard", { token });
}

export function getAdminCustomers(token) {
  return apiRequest("/api/customers/admin/all?limit=100", { token });
}

export function setCustomerActive(customerId, active, token) {
  return apiRequest(`/api/customers/admin/${customerId}/active`, {
    method: "PATCH",
    body: { active },
    token,
  });
}

export function getAdminOrders(token) {
  return apiRequest("/api/orders/admin/all?limit=100", { token });
}

export function setOrderStatus(orderId, status, token) {
  return apiRequest(`/api/orders/${orderId}/status`, {
    method: "PATCH",
    body: { status },
    token,
  });
}

export function getAdminTickets({ status = "", priority = "" } = {}, token) {
  const params = new URLSearchParams({ limit: "100" });
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);
  return apiRequest(`/api/support-tickets/admin/all?${params}`, { token });
}

export function updateAdminTicket(ticketId, changes, token) {
  return apiRequest(`/api/support-tickets/${ticketId}`, {
    method: "PATCH",
    body: changes,
    token,
  });
}

export function getAdmins(token) {
  return apiRequest("/api/customers/admin/all?limit=100", { token }).then(
    (customers) => customers.filter((customer) => customer.role === "admin"),
  );
}
