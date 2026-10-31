
import { apiRequest } from "./client";

/**
 * Sends a customer message to the authenticated support graph.
 *
 * The JWT token identifies the customer on the backend.
 * The backend decides which tools or agents to use.
 */
export function sendChatMessage(message, token) {
  return apiRequest("/api/support/ask", {
    method: "POST",
    body: { question: message },
    token,
  });
}
