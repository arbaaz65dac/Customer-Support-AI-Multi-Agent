import { useCallback, useEffect, useEffectEvent, useState } from "react";
import { apiRequest } from "../api/client";
import {
  createTicket,
  getMyTickets,
  getTicket,
  replyToTicket,
} from "../api/tickets";

export default function TicketCenter({ customer }) {
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [orders, setOrders] = useState([]);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [orderId, setOrderId] = useState("");
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadTickets = useCallback(async () => {
    try {
      const result = await getMyTickets(customer.token);
      setTickets(result);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Unable to load support tickets.");
    } finally {
      setLoading(false);
    }
  }, [customer.token]);

  const loadTicketData = useEffectEvent(() => {
    void loadTickets();
    apiRequest("/api/orders", { token: customer.token })
      .then(setOrders)
      .catch((requestError) => setError(requestError.message));
  });

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) loadTicketData();
    });
    return () => { active = false; };
  }, [customer.id, customer.token]);

  async function openTicket(ticketId) {
    setError("");
    try {
      setSelected(await getTicket(ticketId, customer.token));
    } catch (requestError) {
      setError(requestError.message || "Unable to load ticket details.");
    }
  }

  async function handleCreate(event) {
    event.preventDefault();
    if (submitting) return;
    setError("");
    setNotice("");
    setSubmitting(true);
    try {
      const ticket = await createTicket(
        {
          subject: subject.trim(),
          description: description.trim(),
          ...(orderId ? { order_id: Number(orderId) } : {}),
        },
        customer.token,
      );
      setSubject("");
      setDescription("");
      setOrderId("");
      setNotice(`Ticket #${ticket.id} created with status ${ticket.status}.`);
      setSelected(await getTicket(ticket.id, customer.token));
      await loadTickets();
    } catch (requestError) {
      setError(requestError.message || "Unable to create your ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReply(event) {
    event.preventDefault();
    if (!selected || !reply.trim() || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      setSelected(await replyToTicket(selected.id, reply.trim(), customer.token));
      setReply("");
      await loadTickets();
    } catch (requestError) {
      setError(requestError.message || "Unable to send your reply.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="customer-center">
      <header className="center-heading">
        <div>
          <span className="eyebrow">CUSTOMER CARE</span>
          <h2>My support tickets</h2>
          <p>Raise a request and follow replies from the support team.</p>
        </div>
        {selected && (
          <button type="button" className="secondary-button" onClick={() => setSelected(null)}>
            Back to tickets
          </button>
        )}
      </header>
      {error && <p className="chat-error" role="alert">{error}</p>}
      {notice && <p className="form-message success" role="status">{notice}</p>}
      {selected ? (
        <article className="ticket-detail card-panel">
          <div className="panel-title-row">
            <div><span className="eyebrow">TICKET #{selected.id}</span><h3>{selected.subject}</h3></div>
            <span className={`order-status status-${selected.status}`}>{selected.status.replace(/_/g, " ")}</span>
          </div>
          <p>{selected.description}</p>
          {selected.order_id && <p className="muted-copy">Related order #{selected.order_id}</p>}
          <div className="ticket-replies">
            <h4>Conversation</h4>
            {(selected.replies || []).length === 0 ? <p className="muted-copy">No replies yet.</p> :
              selected.replies.map((item) => (
                <div className="ticket-reply" key={item.id}>
                  <p>{item.message}</p><small>{new Date(item.created_at).toLocaleString("en-IN")}</small>
                </div>
              ))}
          </div>
          <form className="ticket-reply-form" onSubmit={handleReply}>
            <label htmlFor="ticket-reply">Add a reply</label>
            <textarea id="ticket-reply" value={reply} maxLength={5000} onChange={(event) => setReply(event.target.value)} required />
            <button className="send-button" disabled={submitting || !reply.trim()}>{submitting ? "Sending…" : "Send reply"}</button>
          </form>
        </article>
      ) : (
        <div className="ticket-layout">
          <form className="ticket-create card-panel" onSubmit={handleCreate}>
            <h3>Create a ticket</h3>
            <label htmlFor="ticket-subject">Subject</label>
            <input id="ticket-subject" value={subject} maxLength={200} onChange={(event) => setSubject(event.target.value)} minLength={3} required />
            <label htmlFor="ticket-order">Related order (optional)</label>
            <select id="ticket-order" value={orderId} onChange={(event) => setOrderId(event.target.value)}>
              <option value="">Not related to an order</option>
              {orders.map((order) => <option key={order.id} value={order.id}>Order #{order.id} · {order.status}</option>)}
            </select>
            <label htmlFor="ticket-description">Describe the issue</label>
            <textarea id="ticket-description" value={description} maxLength={5000} onChange={(event) => setDescription(event.target.value)} minLength={5} required />
            <button className="send-button" disabled={submitting}>{submitting ? "Creating…" : "Create ticket"}</button>
          </form>
          <div className="ticket-list">
            <h3>Recent tickets</h3>
            {loading ? <p role="status">Loading tickets…</p> : tickets.length === 0 ?
              <p className="muted-copy">You have not created any tickets yet.</p> :
              tickets.map((ticket) => (
                <button className="ticket-list-row card-panel" key={ticket.id} onClick={() => void openTicket(ticket.id)}>
                  <span><strong>#{ticket.id} · {ticket.subject}</strong><small>Updated {new Date(ticket.created_at).toLocaleDateString("en-IN")}</small></span>
                  <span className={`order-status status-${ticket.status}`}>{ticket.status.replace(/_/g, " ")}</span>
                </button>
              ))}
          </div>
        </div>
      )}
    </section>
  );
}
