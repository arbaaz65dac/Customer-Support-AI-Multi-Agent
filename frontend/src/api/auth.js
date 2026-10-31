
import { apiRequest } from "./client";

/**
 * Register a new customer.
 * The backend hashes the password before storing it.
 */
export function registerCustomer({ name, email, password }) {
  return apiRequest("/api/customers", {
    method: "POST",
    body: { name, email, password },
  });
}

/**
 * Authenticate a customer and receive a JWT access token.
 */
export function loginCustomer({ email, password }) {
  return apiRequest("/api/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

/**
 * Fetch the authenticated customer's profile.
 */
export function getCustomerProfile(customerId, token) {
  return apiRequest(`/api/customers/${customerId}`, {
    method: "GET",
    token,
  });
}

export function getAdminCustomer(customerId, token) {
  return apiRequest(`/api/customers/admin/${customerId}`, { token });
}
