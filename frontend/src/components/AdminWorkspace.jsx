import { useCallback, useEffect, useEffectEvent, useState } from "react";
import {
  getAdminCustomers,
  getAdminDashboard,
  getAdminOrders,
  getAdminTickets,
  getAdmins,
  setCustomerActive,
  setOrderStatus,
  updateAdminTicket,
} from "../api/admin";
import { getAdminCustomer } from "../api/auth";
import {
  createProduct,
  deleteProduct,
  getAdminProducts,
  updateProduct,
} from "../api/products";
import { getTicket, replyToTicket } from "../api/tickets";
import { getAdminRefundRequests, reviewRefundRequest } from "../api/refunds";

const VIEWS = [
  ["dashboard", "Overview", "▦"],
  ["customers", "Customers", "♙"],
  ["products", "Products", "▣"],
  ["orders", "Orders", "▤"],
  ["tickets", "Tickets", "✉"],
  ["refunds", "Refunds", "↩"],
];
const ORDER_STATUSES = ["pending", "processing", "shipped", "delivered", "cancelled"];
const TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"];
const TICKET_PRIORITIES = ["low", "normal", "high", "urgent"];

function formatCurrency(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function AdminWorkspace({ customer, onLogout, activeView, navigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [ticketEdits, setTicketEdits] = useState(null);
  const [admins, setAdmins] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ticketReply, setTicketReply] = useState("");
  const [productForm, setProductForm] = useState(null);
  const token = customer.token;

  const loadView = useCallback(async (view = activeView) => {
    try {
      if (view === "dashboard") {
        setDashboard(await getAdminDashboard(token));
        setError("");
      }
      if (view === "customers") {
        setCustomers((await getAdminCustomers(token)).filter((person) => person.role === "customer"));
        setError("");
      }
      if (view === "products") {
        setProducts(await getAdminProducts({ limit: 100 }, token));
        setError("");
      }
      if (view === "orders") {
        setOrders(await getAdminOrders(token));
        setError("");
      }
      if (view === "tickets") {
        const [result, adminList] = await Promise.all([
          getAdminTickets({ status: statusFilter, priority: priorityFilter }, token),
          getAdmins(token),
        ]);
        setTickets(result);
        setAdmins(adminList);
      }
      if (view === "refunds") {
        setRefunds(await getAdminRefundRequests(token));
        setError("");
      }
    } catch (requestError) {
      setError(requestError.message || "Unable to load this admin view.");
    } finally {
      setLoading(false);
    }
  }, [activeView, priorityFilter, statusFilter, token]);

  const refreshView = useEffectEvent(() => {
    void loadView();
  });

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) refreshView();
    });
    return () => { active = false; };
  }, [activeView, priorityFilter, statusFilter, token]);

  async function handleSelectCustomer(id) {
    setError("");
    try {
      setSelectedCustomer(await getAdminCustomer(id, token));
    } catch (requestError) {
      setError(requestError.message || "Unable to load customer details.");
    }
  }

  async function handleToggleCustomer(person) {
    setSaving(true);
    setError("");
    try {
      const updated = await setCustomerActive(person.id, !person.active, token);
      setCustomers((previous) => previous.map((entry) => entry.id === updated.id ? updated : entry));
      if (selectedCustomer?.id === updated.id) setSelectedCustomer(updated);
      setNotice(`Customer ${updated.active ? "activated" : "deactivated"}.`);
    } catch (requestError) {
      setError(requestError.message || "Unable to update customer status.");
    } finally {
      setSaving(false);
    }
  }

  async function saveProduct(event) {
    event.preventDefault();
    if (saving || !productForm) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const data = {
        name: productForm.name.trim(),
        description: productForm.description.trim() || null,
        category: productForm.category.trim(),
        price: Number(productForm.price),
        stock: Number(productForm.stock),
        active: Boolean(productForm.active),
      };
      if (!data.name || !data.category || data.price <= 0 || data.stock < 0 || !Number.isInteger(data.stock)) {
        throw new Error("Enter a name, category, positive price, and whole-number stock.");
      }
      if (productForm.id) await updateProduct(productForm.id, data, token);
      else await createProduct(data, token);
      setProductForm(null);
      setNotice(productForm.id ? "Product updated." : "Product created.");
      await loadView("products");
    } catch (requestError) {
      setError(requestError.message || "Unable to save product.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteProduct(product) {
    if (!window.confirm(`Deactivate ${product.name}?`)) return;
    setError("");
    try {
      await deleteProduct(product.id, token);
      await loadView("products");
      setNotice("Product deactivated.");
    } catch (requestError) {
      setError(requestError.message || "Unable to deactivate product.");
    }
  }

  async function handleOrderStatus(orderId, status) {
    setError("");
    try {
      const updated = await setOrderStatus(orderId, status, token);
      setOrders((previous) => previous.map((order) => order.id === updated.id ? updated : order));
      setNotice(`Order #${orderId} updated.`);
    } catch (requestError) {
      setError(requestError.message || "Unable to update order.");
    }
  }

  async function openTicket(ticketId) {
    setError("");
    try {
      const detail = await getTicket(ticketId, token);
      setSelectedTicket(detail);
      setTicketEdits({
        status: detail.status,
        priority: detail.priority,
        assigned_admin_id: detail.assigned_admin_id,
      });
    } catch (requestError) {
      setError(requestError.message || "Unable to load ticket details.");
    }
  }

  async function handleTicketUpdate() {
    if (!selectedTicket || !ticketEdits) return;
    setSaving(true);
    setError("");
    try {
      await updateAdminTicket(selectedTicket.id, ticketEdits, token);
      const detail = await getTicket(selectedTicket.id, token);
      setSelectedTicket(detail);
      setTicketEdits({
        status: detail.status,
        priority: detail.priority,
        assigned_admin_id: detail.assigned_admin_id,
      });
      await loadView("tickets");
      setNotice("Ticket updated.");
    } catch (requestError) {
      setError(requestError.message || "Unable to update ticket.");
    } finally {
      setSaving(false);
    }
  }

  async function handleTicketReply(event) {
    event.preventDefault();
    if (!selectedTicket || !ticketReply.trim() || saving) return;
    setSaving(true);
    setError("");
    try {
      setSelectedTicket(await replyToTicket(selectedTicket.id, ticketReply.trim(), token));
      setTicketReply("");
      setNotice("Reply sent.");
      await loadView("tickets");
    } catch (requestError) {
      setError(requestError.message || "Unable to send reply.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRefundReview(request, status) {
    setError("");
    try {
      const updated = await reviewRefundRequest(
        request.id,
        { status, review_note: null },
        token,
      );
      setRefunds((previous) => previous.map((entry) => entry.id === updated.id ? updated : entry));
      setNotice(`Refund request #${request.id} ${status}.`);
    } catch (requestError) {
      setError(requestError.message || "Unable to review refund request.");
    }
  }

  const title = VIEWS.find(([id]) => id === activeView)?.[1] || "Overview";

  return (
    <main className="dashboard-page">
      <aside className="dashboard-sidebar">
        <div className="brand"><div className="brand-mark" aria-hidden="true">S</div><span>SupportSphere</span></div>
        <div className="sidebar-section">
          <span className="sidebar-label">ADMINISTRATION</span>
          {VIEWS.map(([id, label, icon]) => (
            <button type="button" className={`sidebar-link ${activeView === id ? "active" : ""}`} key={id} onClick={() => { setLoading(true); setSelectedTicket(null); setTicketEdits(null); setSelectedCustomer(null); navigate(id); }}>
              <span aria-hidden="true">{icon}</span>{label}
            </button>
          ))}
        </div>
        <div className="sidebar-bottom">
          <div className="customer-summary"><div className="customer-avatar">{customer.name.charAt(0).toUpperCase()}</div><div className="customer-details"><strong>{customer.name}</strong><span>Administrator</span></div></div>
          <button type="button" className="logout-button" onClick={onLogout}><span aria-hidden="true">↪</span>Sign out</button>
        </div>
      </aside>
      <section className="chat-workspace">
        <header className="dashboard-header"><div><h1>{title}</h1><p>Manage customer support operations.</p></div><div className="assistant-status">Admin workspace</div></header>
        <div className="admin-content">
          {error && <p className="chat-error" role="alert">{error}</p>}
          {notice && <p className="form-message success" role="status">{notice}</p>}
          {loading && <p role="status">Loading {title.toLowerCase()}…</p>}
          {!loading && activeView === "dashboard" && dashboard && (
            <section className="stats-grid" aria-label="Dashboard overview">
              {[
                ["Customers", dashboard.total_customers],
                ["Orders", dashboard.total_orders],
                ["Open tickets", dashboard.open_tickets],
                ["Revenue", formatCurrency(dashboard.revenue)],
                ["All tickets", dashboard.total_tickets],
                ["In progress", dashboard.in_progress_tickets],
                ["Resolved", dashboard.resolved_tickets],
              ].map(([label, value]) => <article className="stat-card card-panel" key={label}><span>{label}</span><strong>{value}</strong></article>)}
            </section>
          )}
          {!loading && activeView === "customers" && (
            <section className="admin-columns">
              <div className="admin-table-wrap card-panel">
                <h2>Customers</h2>
                <table><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead>
                  <tbody>{customers.map((person) => <tr key={person.id}>
                    <td><button className="text-button" type="button" onClick={() => void handleSelectCustomer(person.id)}>{person.name}</button></td><td>{person.email}</td><td>{person.role}</td><td>{person.active ? "Active" : "Inactive"}</td>
                    <td><button className="secondary-button" disabled={saving || person.id === customer.id} onClick={() => void handleToggleCustomer(person)}>{person.active ? "Deactivate" : "Activate"}</button></td>
                  </tr>)}</tbody>
                </table>
              </div>
              {selectedCustomer && <article className="card-panel detail-panel"><h3>Customer details</h3><dl><dt>Name</dt><dd>{selectedCustomer.name}</dd><dt>Email</dt><dd>{selectedCustomer.email}</dd><dt>Role</dt><dd>{selectedCustomer.role}</dd><dt>Status</dt><dd>{selectedCustomer.active ? "Active" : "Inactive"}</dd></dl></article>}
            </section>
          )}
          {!loading && activeView === "products" && (
            <section className="admin-table-wrap card-panel">
              <div className="panel-title-row"><h2>Products</h2><button className="send-button" onClick={() => setProductForm({ name: "", description: "", category: "", price: "", stock: 0, active: true })}>Add product</button></div>
              <table><thead><tr><th>Product</th><th>Category</th><th>Price</th><th>Stock</th><th>Active</th><th>Actions</th></tr></thead>
                <tbody>{products.map((product) => <tr key={product.id}><td>{product.name}</td><td>{product.category}</td><td>{formatCurrency(product.price)}</td><td>{product.stock}</td><td>{product.active ? "Yes" : "No"}</td><td className="table-actions"><button className="secondary-button" onClick={() => setProductForm({ ...product, price: String(product.price) })}>Edit</button>{product.active && <button className="secondary-button danger-button" onClick={() => void handleDeleteProduct(product)}>Deactivate</button>}{!product.active && <button className="secondary-button" onClick={() => void updateProduct(product.id, { ...product, active: true }, token).then(() => loadView("products")).catch((failure) => setError(failure.message))}>Reactivate</button>}</td></tr>)}</tbody>
              </table>
              {productForm && <div className="modal-backdrop" role="presentation"><form className="detail-modal card-panel admin-product-form" onSubmit={saveProduct}>
                <div className="panel-title-row"><h3>{productForm.id ? "Edit product" : "Create product"}</h3><button type="button" className="modal-close" onClick={() => setProductForm(null)} aria-label="Close">×</button></div>
                <label>Name<input required maxLength={150} value={productForm.name} onChange={(event) => setProductForm({ ...productForm, name: event.target.value })} /></label>
                <label>Description<textarea maxLength={5000} value={productForm.description || ""} onChange={(event) => setProductForm({ ...productForm, description: event.target.value })} /></label>
                <label>Category<input required maxLength={100} value={productForm.category} onChange={(event) => setProductForm({ ...productForm, category: event.target.value })} /></label>
                <label>Price (₹)<input type="number" min="0.01" step="0.01" required value={productForm.price} onChange={(event) => setProductForm({ ...productForm, price: event.target.value })} /></label>
                <label>Stock<input type="number" min="0" step="1" required value={productForm.stock} onChange={(event) => setProductForm({ ...productForm, stock: event.target.value })} /></label>
                <label className="checkbox-label"><input type="checkbox" checked={Boolean(productForm.active)} onChange={(event) => setProductForm({ ...productForm, active: event.target.checked })} /> Active</label>
                <button className="send-button" disabled={saving}>{saving ? "Saving…" : "Save product"}</button>
              </form></div>}
            </section>
          )}
          {!loading && activeView === "orders" && (
            <section className="admin-table-wrap card-panel"><h2>Orders</h2><table><thead><tr><th>Order</th><th>Customer</th><th>Items</th><th>Status</th><th>Update status</th></tr></thead>
              <tbody>{orders.map((order) => <tr key={order.id}><td>#{order.id}<small>{new Date(order.created_at).toLocaleDateString("en-IN")}</small></td><td>Customer #{order.customer_id}</td><td>{order.items?.map((item) => `${item.quantity} × ${item.product_name || `product #${item.product_id}`}`).join(", ")}</td><td>{order.status}</td><td><select value={order.status} onChange={(event) => void handleOrderStatus(order.id, event.target.value)}>{ORDER_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select></td></tr>)}</tbody>
            </table></section>
          )}
          {!loading && activeView === "tickets" && (
            <section className="admin-columns">
              <div className="admin-table-wrap card-panel">
                <div className="panel-title-row"><h2>Support tickets</h2><div className="filter-pair"><select aria-label="Filter tickets by status" value={statusFilter} onChange={(event) => { setLoading(true); setStatusFilter(event.target.value); }}><option value="">All statuses</option>{TICKET_STATUSES.map((status) => <option key={status}>{status}</option>)}</select><select aria-label="Filter tickets by priority" value={priorityFilter} onChange={(event) => { setLoading(true); setPriorityFilter(event.target.value); }}><option value="">All priorities</option>{TICKET_PRIORITIES.map((priority) => <option key={priority}>{priority}</option>)}</select></div></div>
                {tickets.map((ticket) => <button type="button" className="ticket-list-row card-panel" key={ticket.id} onClick={() => void openTicket(ticket.id)}><span><strong>#{ticket.id} · {ticket.subject}</strong><small>Customer #{ticket.customer_id} · {ticket.priority}</small></span><span className={`order-status status-${ticket.status}`}>{ticket.status.replace(/_/g, " ")}</span></button>)}
              </div>
              {selectedTicket && <article className="card-panel detail-panel">
                <span className="eyebrow">TICKET #{selectedTicket.id}</span><h3>{selectedTicket.subject}</h3><p>{selectedTicket.description}</p><p className="muted-copy">Customer #{selectedTicket.customer_id}</p>
                <div className="ticket-admin-controls"><label>Status<select value={ticketEdits?.status || selectedTicket.status} onChange={(event) => setTicketEdits((previous) => ({ ...previous, status: event.target.value }))}>{TICKET_STATUSES.map((status) => <option key={status}>{status}</option>)}</select></label><label>Priority<select value={ticketEdits?.priority || selectedTicket.priority} onChange={(event) => setTicketEdits((previous) => ({ ...previous, priority: event.target.value }))}>{TICKET_PRIORITIES.map((priority) => <option key={priority}>{priority}</option>)}</select></label><label>Assigned admin<select value={ticketEdits?.assigned_admin_id || ""} onChange={(event) => setTicketEdits((previous) => ({ ...previous, assigned_admin_id: event.target.value ? Number(event.target.value) : null }))}><option value="">Unassigned</option>{admins.map((admin) => <option key={admin.id} value={admin.id}>{admin.name}</option>)}</select></label><button type="button" className="send-button" disabled={saving} onClick={() => void handleTicketUpdate()}>{saving ? "Saving…" : "Save ticket changes"}</button></div>
                <div className="ticket-replies"><h4>Replies</h4>{(selectedTicket.replies || []).map((reply) => <div className="ticket-reply" key={reply.id}><p>{reply.message}</p><small>Author #{reply.author_id} · {new Date(reply.created_at).toLocaleString("en-IN")}</small></div>)}</div>
                <form className="ticket-reply-form" onSubmit={handleTicketReply}><label htmlFor="admin-ticket-reply">Reply to customer</label><textarea id="admin-ticket-reply" value={ticketReply} maxLength={5000} onChange={(event) => setTicketReply(event.target.value)} required /><button className="send-button" disabled={saving || !ticketReply.trim()}>{saving ? "Sending…" : "Send reply"}</button></form>
              </article>}
            </section>
          )}
          {!loading && activeView === "refunds" && (
            <section className="admin-table-wrap card-panel"><h2>Return &amp; refund requests</h2><table><thead><tr><th>Request</th><th>Customer</th><th>Order</th><th>Type</th><th>Reason</th><th>Status</th><th>Review</th></tr></thead><tbody>
              {refunds.map((request) => <tr key={request.id}><td>#{request.id}</td><td>#{request.customer_id}</td><td>#{request.order_id}</td><td>{request.request_type}</td><td>{request.reason}</td><td>{request.status}{request.review_note && <small>{request.review_note}</small>}</td><td>{request.status === "pending" ? <div className="table-actions"><button className="secondary-button" onClick={() => void handleRefundReview(request, "approved")}>Approve</button><button className="secondary-button danger-button" onClick={() => void handleRefundReview(request, "rejected")}>Reject</button></div> : "Reviewed"}</td></tr>)}
            </tbody></table></section>
          )}
        </div>
      </section>
    </main>
  );
}

export default AdminWorkspace;
