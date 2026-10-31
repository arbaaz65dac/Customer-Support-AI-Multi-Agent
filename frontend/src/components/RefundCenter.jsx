import { useCallback, useEffect, useEffectEvent, useState } from "react";
import { apiRequest } from "../api/client";
import { createRefundRequest, getMyRefundRequests } from "../api/refunds";

export default function RefundCenter({ customer }) {
  const [orders, setOrders] = useState([]);
  const [requests, setRequests] = useState([]);
  const [orderId, setOrderId] = useState("");
  const [requestType, setRequestType] = useState("return");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadRequests = useCallback(async () => {
    try {
      const [refunds, customerOrders] = await Promise.all([
        getMyRefundRequests(customer.token),
        apiRequest("/api/orders", { token: customer.token }),
      ]);
      setRequests(refunds);
      setOrders(customerOrders);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Unable to load return requests.");
    } finally {
      setLoading(false);
    }
  }, [customer.token]);

  const refreshRequests = useEffectEvent(() => {
    void loadRequests();
  });

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) refreshRequests();
    });
    return () => { active = false; };
  }, [customer.id, customer.token]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    setNotice("");
    try {
      const result = await createRefundRequest(
        { order_id: Number(orderId), request_type: requestType, reason: reason.trim() },
        customer.token,
      );
      setNotice(`${requestType === "return" ? "Return" : "Refund"} request #${result.id} submitted for admin review.`);
      setReason("");
      await loadRequests();
    } catch (requestError) {
      setError(requestError.message || "Unable to submit your request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="customer-center">
      <header className="center-heading">
        <div><span className="eyebrow">ORDER SUPPORT</span><h2>Returns &amp; refunds</h2><p>Requests are checked against your order and the store policy; no payment is executed here.</p></div>
      </header>
      {error && <p className="chat-error" role="alert">{error}</p>}
      {notice && <p className="form-message success" role="status">{notice}</p>}
      <div className="ticket-layout">
        <form className="ticket-create card-panel" onSubmit={handleSubmit}>
          <h3>Request a return or refund</h3>
          <label htmlFor="refund-order">Order</label>
          <select id="refund-order" value={orderId} onChange={(event) => setOrderId(event.target.value)} required>
            <option value="">Choose one of your orders</option>
            {orders.map((order) => <option key={order.id} value={order.id}>Order #{order.id} · {order.status}</option>)}
          </select>
          <label htmlFor="refund-type">Request type</label>
          <select id="refund-type" value={requestType} onChange={(event) => setRequestType(event.target.value)}>
            <option value="return">Return</option><option value="refund">Refund</option>
          </select>
          <label htmlFor="refund-reason">Reason</label>
          <textarea id="refund-reason" value={reason} minLength={5} maxLength={5000} onChange={(event) => setReason(event.target.value)} required />
          <button className="send-button" disabled={submitting || !orderId}>{submitting ? "Submitting…" : "Submit for review"}</button>
        </form>
        <div className="ticket-list">
          <h3>Your requests</h3>
          {loading ? <p role="status">Loading requests…</p> : requests.length === 0 ?
            <p className="muted-copy">No return or refund requests yet.</p> :
            requests.map((request) => (
              <article className="refund-row card-panel" key={request.id}>
                <div><strong>Request #{request.id} · Order #{request.order_id}</strong><small>{request.request_type} · {new Date(request.created_at).toLocaleDateString("en-IN")}</small><p>{request.reason}</p></div>
                <span className={`order-status status-${request.status}`}>{request.status}</span>
                {request.review_note && <p className="muted-copy">Review: {request.review_note}</p>}
              </article>
            ))}
        </div>
      </div>
    </section>
  );
}
