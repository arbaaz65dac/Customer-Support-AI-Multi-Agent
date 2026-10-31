import { apiRequest } from "./client";

export function getMyTickets(token) {
  return apiRequest("/api/support-tickets", { token });
}

export function getTicket(ticketId, token) {
  return apiRequest(`/api/support-tickets/${ticketId}`, { token });
}

export function createTicket(ticket, token) {
  return apiRequest("/api/support-tickets", {
    method: "POST",
    body: ticket,
    token,
  });
}

export function replyToTicket(ticketId, message, token) {
  return apiRequest(`/api/support-tickets/${ticketId}/replies`, {
    method: "POST",
    body: { message },
    token,
  });
}
