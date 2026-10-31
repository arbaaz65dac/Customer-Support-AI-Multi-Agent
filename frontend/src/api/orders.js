
import { apiRequest } from "./client";

/**
 * Fetch orders belonging to the authenticated customer.
 * The backend identifies the customer from the JWT token.
 */
export function getCustomerOrders(token) {
  return apiRequest("/api/orders", {
    method: "GET",
    token,
  });
}

export function getCustomerOrder(orderId, token) {
  return apiRequest(`/api/orders/${orderId}`, { token });
}
