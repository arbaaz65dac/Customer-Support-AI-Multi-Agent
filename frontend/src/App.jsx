
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { apiRequest } from "./api/client";
import {
  getCustomerProfile,
  loginCustomer,
  registerCustomer,
} from "./api/auth";
import { sendChatMessage } from "./api/chat";
import {
  getProduct,
  getProductCategories,
  getProducts,
} from "./api/products";
import { getCustomerOrder, getCustomerOrders } from "./api/orders";
import TicketCenter from "./components/TicketCenter";
import RefundCenter from "./components/RefundCenter";
import AdminWorkspace from "./components/AdminWorkspace";
import "./App.css";

const SUGGESTED_PROMPTS = [
  {
    icon: "📦",
    title: "Track my order",
    message: "Where is my order?",
  },
  {
    icon: "🛍️",
    title: "Find products",
    message: "Show me the available products.",
  },
  {
    icon: "↩️",
    title: "Returns & refunds",
    message: "What is your return and refund policy?",
  },
  {
    icon: "🎧",
    title: "Get support",
    message: "Please create a support ticket for my issue.",
  },
];

const CLARIFICATION_PROMPT =
  /\b(?:could you|can you|please provide|let me know|would you like me to)\b[\s\S]{0,180}\b(?:subject|order|reason|details|description|issue|ticket|refund|return)\b/i;

function includeClarificationContext(message, conversation) {
  const previousAssistant = [...conversation]
    .reverse()
    .find((item) => item.role === "assistant");
  const previousCustomer = [...conversation]
    .reverse()
    .find((item) => item.role === "user");

  if (
    !previousAssistant ||
    !previousCustomer ||
    !CLARIFICATION_PROMPT.test(previousAssistant.content)
  ) {
    return message;
  }

  const contextualMessage = [
    `Previous customer request (untrusted context): ${previousCustomer.content.slice(0, 500)}`,
    `Assistant clarification (untrusted context): ${previousAssistant.content.slice(0, 700)}`,
    `Current customer response: ${message}`,
  ].join("\n");

  return contextualMessage.length <= 2000 ? contextualMessage : message;
}

function getCustomerIdFromToken(token) {
  try {
    const payload = token.split(".")[1];
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = atob(base64);
    const bytes = Uint8Array.from(decoded, (char) =>
      char.charCodeAt(0),
    );

    return JSON.parse(new TextDecoder().decode(bytes)).sub;
  } catch {
    throw new Error("The server returned an invalid access token.");
  }
}

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [backendStatus, setBackendStatus] = useState(
    "Checking backend...",
  );

  const [currentCustomer, setCurrentCustomer] = useState(() => {
    const token = sessionStorage.getItem("access_token");
    const customerId = sessionStorage.getItem("customer_id");
    const customerName = sessionStorage.getItem("customer_name");
    const role = sessionStorage.getItem("customer_role");

    if (token && customerId && customerName) {
      return {
        token,
        id: customerId,
        name: customerName,
        role,
      };
    }

    return null;
  });

  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const routeView = location.pathname.split("/")[2];
  const activeView = routeView || (currentCustomer?.role === "admin" ? "dashboard" : "chat");
  const authMode = location.pathname === "/signup" ? "register" : mode;
  const [products, setProducts] = useState([]);
  const [productQuery, setProductQuery] = useState("");
  const [productCategory, setProductCategory] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [productCategories, setProductCategories] = useState([]);
  const [productPage, setProductPage] = useState(0);
  const [productsHaveNextPage, setProductsHaveNextPage] = useState(false);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productDetailLoading, setProductDetailLoading] = useState(false);
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [orderStatusFilter, setOrderStatusFilter] = useState("all");
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderDetailLoading, setOrderDetailLoading] = useState(false);

  const filteredOrders = orders.filter((order) => {
    if (orderStatusFilter === "all") return true;
    return String(order.status || "unknown").toLowerCase() === orderStatusFilter;
  });

  const messagesEndRef = useRef(null);
  const chatRequestInFlightRef = useRef(false);
  const productsLoadedRef = useRef(false);
  const ordersLoadedRef = useRef(false);

  function routeForView(view, role = currentCustomer?.role) {
    const root = role === "admin" ? "/admin" : "/customer";
    return `${root}/${view === "chat" ? "chat" : view}`;
  }

  function goToView(view) {
    navigate(routeForView(view));
  }

  useEffect(() => {
    function expireSession() {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("customer_id");
      sessionStorage.removeItem("customer_name");
      sessionStorage.removeItem("customer_role");
      setCurrentCustomer(null);
      navigate("/login");
    }

    window.addEventListener("auth:unauthorized", expireSession);
    return () => window.removeEventListener("auth:unauthorized", expireSession);
  }, [navigate]);

  useEffect(() => {
    if (!currentCustomer?.token || currentCustomer.role) return;
    getCustomerProfile(currentCustomer.id, currentCustomer.token)
      .then((profile) => {
        sessionStorage.setItem("customer_role", profile.role);
        setCurrentCustomer((previous) =>
          previous ? { ...previous, role: profile.role } : previous,
        );
      })
      .catch(() => {
        sessionStorage.removeItem("access_token");
        sessionStorage.removeItem("customer_id");
        sessionStorage.removeItem("customer_name");
        sessionStorage.removeItem("customer_role");
        setCurrentCustomer(null);
      });
  }, [currentCustomer?.id, currentCustomer?.role, currentCustomer?.token]);

  useEffect(() => {
    apiRequest("/health")
      .then((data) =>
        setBackendStatus(data.message || "Connected"),
      )
      .catch(() => setBackendStatus("Backend unavailable"));
  }, []);

  useEffect(() => {
    getProductCategories()
      .then((result) => setProductCategories(Array.isArray(result) ? result : []))
      .catch(() => setProductCategories([]));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, chatLoading]);

  function changeMode(nextMode) {
    setMode(nextMode);
    navigate(nextMode === "register" ? "/signup" : "/login");
    setError("");
    setSuccess("");
    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    const normalizedEmail = email.trim();

    if (authMode === "register") {
      if (!name.trim()) {
        setError("Please enter your name.");
        return;
      }

      if (password.length < 8 || password.length > 128) {
        setError("Password must be between 8 and 128 characters.");
        return;
      }

      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }
    } else if (!password) {
      setError("Please enter your password.");
      return;
    }

    setLoading(true);

    try {
      if (authMode === "register") {
        await registerCustomer({
          name: name.trim(),
          email: normalizedEmail,
          password,
        });

        setSuccess("Account created. You can now sign in.");
        setMode("login");
        navigate("/login");
        setPassword("");
        setConfirmPassword("");
      } else {
        const result = await loginCustomer({
          email: normalizedEmail,
          password,
        });

        if (!result.access_token) {
          throw new Error(
            "The server did not return an access token.",
          );
        }

        const customerId = getCustomerIdFromToken(
          result.access_token,
        );

        if (!customerId) {
          throw new Error(
            "Could not identify the signed-in customer.",
          );
        }

        const profile = await getCustomerProfile(
          customerId,
          result.access_token,
        );
        const role = result.role || profile.role;
        if (role !== "admin" && role !== "customer") {
          throw new Error("The server returned an invalid account role.");
        }
        sessionStorage.setItem("access_token", result.access_token);
        sessionStorage.setItem("customer_id", String(profile.id));
        sessionStorage.setItem("customer_name", profile.name);
        sessionStorage.setItem("customer_role", role);

        setCurrentCustomer({
          token: result.access_token,
          id: String(profile.id),
          name: profile.name,
          role,
        });
        productsLoadedRef.current = false;
        ordersLoadedRef.current = false;
        navigate(role === "admin" ? "/admin/dashboard" : "/customer/chat");

        setMessages([]);
        setMessageInput("");
        setPassword("");
      }
    } catch (requestError) {
      setError(
        requestError.message ||
          "Something went wrong. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage(event, suggestedMessage) {
    event?.preventDefault();

    const message = (
      suggestedMessage ?? messageInput
    ).trim();

    if (
      !message ||
      chatLoading ||
      chatRequestInFlightRef.current ||
      !currentCustomer
    ) {
      return;
    }

    if (message.length > 2000) {
      setChatError("Messages must be 2000 characters or fewer.");
      return;
    }

    setChatError("");
    setMessageInput("");
    chatRequestInFlightRef.current = true;

    setMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
      },
    ]);

    setChatLoading(true);

    try {
      const result = await sendChatMessage(
        includeClarificationContext(message, messages),
        currentCustomer.token,
      );

      setMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            result.answer || "I couldn't generate a response.",
          citations: Array.isArray(result.citations)
            ? result.citations
            : [],
          products: Array.isArray(result.products)
            ? result.products
            : [],
        },
      ]);
    } catch (requestError) {
      setMessageInput(message);
      setChatError(
        requestError.message ||
          "Unable to reach the assistant. Please try again.",
      );
    } finally {
      chatRequestInFlightRef.current = false;
      setChatLoading(false);
    }
  }

  const handleSearchProducts = useCallback(async (event, requestedPage = 0) => {
    event?.preventDefault();
    setProductsLoading(true);
    setProductsError("");
    setProductPage(requestedPage);

    try {
      const result = await getProducts({
        query: productQuery,
        category: productCategory,
        minPrice,
        maxPrice,
        limit: 10,
        offset: requestedPage * 9,
      });
      const rows = Array.isArray(result) ? result : [];
      setProducts(rows.slice(0, 9));
      setProductsHaveNextPage(rows.length > 9);
    } catch (requestError) {
      setProductsError(
        requestError.message || "Unable to load products. Please try again.",
      );
      setProducts([]);
    } finally {
      productsLoadedRef.current = true;
      setProductsLoading(false);
    }
  }, [maxPrice, minPrice, productCategory, productQuery]);

  async function handleOpenProduct(productId) {
    setProductDetailLoading(true);
    setProductsError("");
    try {
      setSelectedProduct(await getProduct(productId));
    } catch (requestError) {
      setProductsError(requestError.message || "Unable to load product details.");
    } finally {
      setProductDetailLoading(false);
    }
  }

  async function handleOpenOrder(orderId) {
    if (String(selectedOrderId) === String(orderId)) {
      setSelectedOrderId(null);
      setSelectedOrder(null);
      return;
    }
    setOrderDetailLoading(true);
    setOrdersError("");
    try {
      const detail = await getCustomerOrder(orderId, currentCustomer.token);
      setSelectedOrder(detail);
      setSelectedOrderId(detail.id);
    } catch (requestError) {
      setOrdersError(requestError.message || "Unable to load this order.");
    } finally {
      setOrderDetailLoading(false);
    }
  }

  function openProducts() {
    if (activeView === "products") {
      void handleSearchProducts(null, 0);
    } else {
      goToView("products");
    }
  }

  const handleLoadOrders = useCallback(async () => {
    if (!currentCustomer) return;

    setOrdersLoading(true);
    setOrdersError("");

    try {
      const result = await getCustomerOrders(currentCustomer.token);
      setOrders(Array.isArray(result) ? result : []);
    } catch (requestError) {
      setOrdersError(
        requestError.message || "Unable to load your orders. Please try again.",
      );
      setOrders([]);
    } finally {
      ordersLoadedRef.current = true;
      setOrdersLoading(false);
    }
  }, [currentCustomer]);

  useEffect(() => {
    if (!currentCustomer?.token || currentCustomer.role !== "customer") return;
    if (activeView === "products" && !productsLoadedRef.current) {
      void handleSearchProducts(null, 0);
    }
    if (activeView === "orders" && !ordersLoadedRef.current) {
      void handleLoadOrders();
    }
  }, [
    activeView,
    currentCustomer?.id,
    currentCustomer?.role,
    currentCustomer?.token,
    handleLoadOrders,
    handleSearchProducts,
  ]);

  function openOrders() {
    if (activeView === "orders") {
      void handleLoadOrders();
    } else {
      goToView("orders");
    }
  }

  function openChat() {
    goToView("chat");
    setChatError("");
  }

  function handleLogout() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("customer_id");
    sessionStorage.removeItem("customer_name");
    sessionStorage.removeItem("customer_role");

    setCurrentCustomer(null);
    productsLoadedRef.current = false;
    ordersLoadedRef.current = false;
    setMessages([]);
    setMessageInput("");
    setChatError("");
    setError("");
    setSuccess("");
    setMode("login");
    navigate("/login");
  }

  const isPublicRoute = ["/", "/login", "/signup"].includes(location.pathname);
  const requestedRole = location.pathname.startsWith("/admin")
    ? "admin"
    : location.pathname.startsWith("/customer")
      ? "customer"
      : null;
  const allowedViews = currentCustomer?.role === "admin"
    ? ["dashboard", "customers", "products", "orders", "tickets", "refunds"]
    : ["chat", "products", "orders", "tickets", "refunds"];

  if (!currentCustomer && !isPublicRoute) {
    return <Navigate to="/login" replace />;
  }
  if (currentCustomer && !currentCustomer.role) {
    return <main className="auth-page" role="status">Loading your account…</main>;
  }
  if (currentCustomer && isPublicRoute) {
    return (
      <Navigate
        to={currentCustomer.role === "admin" ? "/admin/dashboard" : "/customer/chat"}
        replace
      />
    );
  }
  if (currentCustomer && !isPublicRoute && !requestedRole) {
    return (
      <Navigate
        to={currentCustomer.role === "admin" ? "/admin/dashboard" : "/customer/chat"}
        replace
      />
    );
  }
  if (currentCustomer && location.pathname === "/admin") {
    return <Navigate to="/admin/dashboard" replace />;
  }
  if (currentCustomer && location.pathname === "/customer") {
    return <Navigate to="/customer/chat" replace />;
  }
  if (currentCustomer && requestedRole && requestedRole !== currentCustomer.role) {
    return (
      <Navigate
        to={currentCustomer.role === "admin" ? "/admin/dashboard" : "/customer/chat"}
        replace
      />
    );
  }
  if (currentCustomer && requestedRole && !allowedViews.includes(routeView)) {
    return (
      <Navigate
        to={currentCustomer.role === "admin" ? "/admin/dashboard" : "/customer/chat"}
        replace
      />
    );
  }

  if (currentCustomer?.role === "admin") {
    return <AdminWorkspace customer={currentCustomer} onLogout={handleLogout} activeView={activeView} navigate={goToView} />;
  }

  if (currentCustomer) {
    return (
      <main className="dashboard-page">
        <aside className="dashboard-sidebar">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">
              S
            </div>
            <span>SupportSphere</span>
          </div>

          <div className="sidebar-section">
            <span className="sidebar-label">WORKSPACE</span>
            <button
              type="button"
              className={`sidebar-link ${activeView === "chat" ? "active" : ""}`}
              onClick={() => {
                openChat();
                setMessages([]);
                setChatError("");
              }}
            >
              <span aria-hidden="true">✦</span>
              New conversation
            </button>
            <button
              type="button"
              className={`sidebar-link ${activeView === "products" ? "active" : ""}`}
              onClick={openProducts}
            >
              <span aria-hidden="true">🛍️</span>
              Products
            </button>
            <button
              type="button"
              className={`sidebar-link ${activeView === "orders" ? "active" : ""}`}
              onClick={openOrders}
            >
              <span aria-hidden="true">📦</span>
              My Orders
            </button>
            <button type="button" className={`sidebar-link ${activeView === "tickets" ? "active" : ""}`} onClick={() => goToView("tickets")}>
              <span aria-hidden="true">🎫</span>
              My Tickets
            </button>
            <button type="button" className={`sidebar-link ${activeView === "refunds" ? "active" : ""}`} onClick={() => goToView("refunds")}>
              <span aria-hidden="true">↩</span>
              Returns &amp; refunds
            </button>
          </div>

          <div className="sidebar-bottom">
            <div className="customer-summary">
              <div className="customer-avatar">
                {currentCustomer.name.charAt(0).toUpperCase()}
              </div>
              <div className="customer-details">
                <strong>{currentCustomer.name}</strong>
                <span>Customer account</span>
              </div>
            </div>

            <button
              type="button"
              className="logout-button"
              onClick={handleLogout}
            >
              <span aria-hidden="true">↪</span>
              Sign out
            </button>
          </div>
        </aside>

        <section className="chat-workspace">
          <header className="dashboard-header">
            <div>
              <h1>
                {activeView === "products"
                  ? "Product catalogue"
                  : activeView === "orders"
                    ? "My Orders"
                    : activeView === "tickets"
                      ? "My support tickets"
                      : activeView === "refunds"
                        ? "Returns & refunds"
                        : "AI Support Assistant"}
              </h1>
              <p>
                {activeView === "products"
                  ? "Explore products and find what you need."
                  : activeView === "orders"
                    ? "View your purchases and check their current status."
                    : activeView === "tickets"
                      ? "Create a request and follow its replies."
                      : activeView === "refunds"
                        ? "Track return and refund requests for your orders."
                        : "Personalized help, whenever you need it."}
              </p>
            </div>

            <div className="assistant-status">
              <span className="status-dot" />
              {activeView === "chat" ? "AI assistant" : "Customer support"}
            </div>
          </header>

          <div className="chat-content">
            {activeView === "products" ? (
              <section className="products-view" aria-label="Product catalogue">
                <div className="products-heading">
                  <span className="eyebrow">SHOP WITH SUPPORTSPHERE</span>
                  <h2>Find your next favourite</h2>
                  <p>Search our active catalogue and filter by category or budget.</p>
                </div>

                <form className="product-filters" onSubmit={(event) => handleSearchProducts(event, 0)}>
                  <label className="product-search-field">
                    <span>Search products</span>
                    <input
                      type="search"
                      value={productQuery}
                      onChange={(event) => setProductQuery(event.target.value)}
                      placeholder="Try headphones or accessories"
                      maxLength={150}
                    />
                  </label>
                  <label className="product-search-field">
                    <span>Category</span>
                    <select
                      value={productCategory}
                      onChange={(event) => setProductCategory(event.target.value)}
                    >
                      <option value="">All categories</option>
                      {productCategories.map((category) => (
                          <option key={category} value={category}>{category}</option>
                        ))}
                    </select>
                  </label>
                  <label className="product-search-field">
                    <span>Minimum price (₹)</span>
                    <input type="number" min="0.01" step="0.01" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} placeholder="Any price" />
                  </label>
                  <label className="product-search-field">
                    <span>Maximum price (₹)</span>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      value={maxPrice}
                      onChange={(event) => setMaxPrice(event.target.value)}
                      placeholder="Any price"
                    />
                  </label>
                  <button className="send-button product-search-button" type="submit" disabled={productsLoading}>
                    {productsLoading ? "Searching…" : "Search"}
                  </button>
                </form>

                {productsError && <p className="chat-error" role="alert">{productsError}</p>}
                {productsLoading ? (
                  <p className="products-empty" role="status">Loading products…</p>
                ) : products.length > 0 ? (
                  <div className="product-grid">
                    {products.map((product) => (
                      <article className="product-card" key={product.id}>
                        <div className="product-card-top">
                          <span className="product-category">{product.category}</span>
                          <span className={`product-stock ${product.stock > 0 ? "in-stock" : "out-of-stock"}`}>
                            {product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}
                          </span>
                        </div>
                        <h3>{product.name}</h3>
                        <p className="product-description">{product.description || "No description available."}</p>
                        <div className="product-card-bottom">
                          <strong>₹{Number(product.price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                          <div className="product-actions">
                            <button type="button" className="product-ask-button" onClick={() => void handleOpenProduct(product.id)}>Details</button>
                            <button
                              type="button"
                              className="product-ask-button"
                              onClick={() => {
                                goToView("chat");
                                void handleSendMessage(null, `Tell me more about ${product.name}.`);
                              }}
                            >Ask AI <span aria-hidden="true">↗</span></button>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="products-empty">
                    <span aria-hidden="true">⌕</span>
                    <h3>No products found</h3>
                    <p>Try changing your search or removing a filter.</p>
                  </div>
                )}
                {products.length > 0 && (
                  <nav className="pagination-controls" aria-label="Product pages">
                    <button className="secondary-button" type="button" disabled={productPage === 0 || productsLoading} onClick={() => void handleSearchProducts(null, productPage - 1)}>Previous</button>
                    <span>Page {productPage + 1}</span>
                    <button className="secondary-button" type="button" disabled={!productsHaveNextPage || productsLoading} onClick={() => void handleSearchProducts(null, productPage + 1)}>Next</button>
                  </nav>
                )}
                {productDetailLoading && <p role="status">Loading product details…</p>}
                {selectedProduct && (
                  <div className="modal-backdrop" role="presentation" onClick={() => setSelectedProduct(null)}>
                    <article className="detail-modal card-panel" role="dialog" aria-modal="true" aria-labelledby="product-detail-title" onClick={(event) => event.stopPropagation()}>
                      <button className="modal-close" type="button" onClick={() => setSelectedProduct(null)} aria-label="Close product details">×</button>
                      <span className="product-category">{selectedProduct.category}</span>
                      <h3 id="product-detail-title">{selectedProduct.name}</h3>
                      <p>{selectedProduct.description || "No description available."}</p>
                      <strong>₹{Number(selectedProduct.price).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                      <p>{selectedProduct.stock > 0 ? `${selectedProduct.stock} in stock` : "Out of stock"}</p>
                    </article>
                  </div>
                )}
              </section>
            ) : activeView === "orders" ? (
              <section className="orders-view" aria-label="Order history">
                <div className="orders-heading">
                  <span className="eyebrow">YOUR PURCHASES</span>
                  <h2>Order history</h2>
                  <p>Keep track of your recent purchases and their status.</p>
                </div>

                {ordersError && (
                  <div className="chat-error" role="alert">
                    <span>{ordersError}</span>
                    <button type="button" onClick={handleLoadOrders}>
                      Try again
                    </button>
                  </div>
                )}

                {!ordersLoading && orders.length > 0 && (
                  <div className="order-filter-bar">
                    <label htmlFor="order-status-filter">Filter by status</label>
                    <select
                      id="order-status-filter"
                      value={orderStatusFilter}
                      onChange={(event) => setOrderStatusFilter(event.target.value)}
                    >
                      <option value="all">All orders ({orders.length})</option>
                      {[...new Set(
                        orders.map((order) => String(order.status || "unknown").toLowerCase()),
                      )].sort().map((status) => (
                        <option key={status} value={status}>
                          {status.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())}
                          {` (${orders.filter((order) => String(order.status || "unknown").toLowerCase() === status).length})`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {ordersLoading ? (
                  <div className="orders-empty" role="status">Loading your orders…</div>
                ) : orders.length === 0 && !ordersError ? (
                  <div className="orders-empty">
                    <span aria-hidden="true">📦</span>
                    <h3>No orders yet</h3>
                    <p>Your orders will appear here when you make a purchase.</p>
                    <button type="button" className="send-button" onClick={openProducts}>
                      Explore products
                    </button>
                  </div>
                ) : !ordersError && filteredOrders.length === 0 ? (
                  <div className="orders-empty">
                    <span aria-hidden="true">⌕</span>
                    <h3>No matching orders</h3>
                    <p>No orders match this status. Try another filter.</p>
                    <button type="button" className="send-button" onClick={() => setOrderStatusFilter("all")}>
                      Show all orders
                    </button>
                  </div>
                ) : (
                  <div className="orders-list">
                    {filteredOrders.map((order) => {
                      const statusValue = String(order.status || "unknown").toLowerCase();
                      const statusText = statusValue.replace(/_/g, " ");
                      const statusClass = statusValue.replace(/[^a-z0-9]+/g, "-");
                      const detailOrder = String(selectedOrderId) === String(order.id)
                        ? selectedOrder
                        : null;
                      const items = Array.isArray(detailOrder?.items)
                        ? detailOrder.items
                        : Array.isArray(order.items) ? order.items : [];
                      const orderTotal = items.reduce(
                        (total, item) => total + Number(item.unit_price || 0) * Number(item.quantity || 0),
                        0,
                      );
                      const isDetailsOpen = String(selectedOrderId) === String(order.id);
                      const formattedDate = order.created_at && !Number.isNaN(Date.parse(order.created_at))
                        ? new Date(order.created_at).toLocaleDateString("en-IN", {
                            day: "numeric", month: "short", year: "numeric",
                          })
                        : "Date unavailable";

                      return (
                        <article className="order-card" key={order.id}>
                          <div className="order-card-header">
                            <div>
                              <span className="order-label">ORDER</span>
                              <h3>#{order.id}</h3>
                            </div>
                            <span className={`order-status status-${statusClass}`}>
                              {statusText.replace(/\b\w/g, (char) => char.toUpperCase())}
                            </span>
                          </div>

                          <p className="order-date">Placed on {formattedDate}</p>

                          <div className="order-items">
                            {items.slice(0, isDetailsOpen ? items.length : 2).map((item, index) => {
                              const productName = item.product_name || item.product?.name || item.name ||
                                (item.product_id != null ? `Product #${item.product_id}` : `Item ${index + 1}`);
                              const lineTotal = Number(item.unit_price || 0) * Number(item.quantity || 0);
                              return (
                                <div className="order-item" key={item.id ?? `${order.id}-${index}`}>
                                  <span>
                                    <span className="order-product-name">{productName}</span>
                                    <span className="order-item-quantity"> × {item.quantity ?? 1}</span>
                                    {isDetailsOpen && item.unit_price != null && (
                                      <span className="order-item-unit-price"> · ₹{Number(item.unit_price).toLocaleString("en-IN", { maximumFractionDigits: 2 })} each</span>
                                    )}
                                  </span>
                                  <strong>₹{lineTotal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                                </div>
                              );
                            })}
                            {!isDetailsOpen && items.length > 2 && (
                              <p className="order-more-items">+ {items.length - 2} more item(s)</p>
                            )}
                            {isDetailsOpen && items.length === 0 && (
                              <p className="order-more-items">No item details are available for this order.</p>
                            )}
                          </div>

                          <div className="order-total">
                            <span>Order total</span>
                            <strong>₹{orderTotal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                          </div>

                          <div className="order-card-actions">
                            <button
                              type="button"
                              className="order-details-button"
                              aria-expanded={isDetailsOpen}
                              onClick={() => void handleOpenOrder(order.id)}
                              disabled={orderDetailLoading}
                            >
                              {orderDetailLoading && String(selectedOrderId) === String(order.id)
                                ? "Loading details…"
                                : isDetailsOpen ? "Hide details" : "View order details"}
                              <span aria-hidden="true">{isDetailsOpen ? " ↑" : " →"}</span>
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            ) : activeView === "tickets" ? (
              <TicketCenter customer={currentCustomer} />
            ) : activeView === "refunds" ? (
              <RefundCenter customer={currentCustomer} />
            ) : messages.length === 0 ? (
              <div className="chat-welcome">
                <div className="welcome-icon" aria-hidden="true">
                  ✦
                </div>
                <span className="eyebrow">YOUR SUPPORT SPACE</span>
                <h2>
                  Hi {currentCustomer.name.split(" ")[0]},
                  <br />
                  how can we help?
                </h2>
                <p>
                  Ask a question, look up a product, check an order,
                  or get help with a support issue.
                </p>

                <div className="suggested-prompts">
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      type="button"
                      className="prompt-card"
                      key={prompt.title}
                      disabled={chatLoading}
                      onClick={() =>
                        handleSendMessage(
                          null,
                          prompt.message,
                        )
                      }
                    >
                      <span aria-hidden="true">
                        {prompt.icon}
                      </span>
                      <strong>{prompt.title}</strong>
                      <span
                        className="prompt-arrow"
                        aria-hidden="true"
                      >
                        ↗
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="message-list" aria-live="polite">
                {messages.map((message) => (
                  <article
                    className={`chat-message ${message.role}`}
                    key={message.id}
                  >
                    <div className="message-avatar">
                      {message.role === "user"
                        ? currentCustomer.name
                            .charAt(0)
                            .toUpperCase()
                        : "✦"}
                    </div>
                    <div className="message-body">
                      <span className="message-author">
                        {message.role === "user"
                          ? "You"
                          : "SupportSphere AI"}
                      </span>

                      <div
                        className={`message-content ${
                          message.role === "assistant" ? "message-markdown" : "message-user-text"
                        }`}
                      >
                        {message.role === "assistant" ? (
                          <>
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                            {message.citations?.length > 0 && (
                              <section
                                className="message-citations"
                                aria-label="Policy sources"
                              >
                                <h3>Policy sources</h3>
                                <ul>
                                  {message.citations.map((citation, index) => (
                                    <li
                                      className="citation-card"
                                      key={`${citation.source}-${citation.version}-${index}`}
                                    >
                                      <strong>{citation.policy.replace(/_/g, " ")}</strong>
                                      <span>
                                        {citation.source}
                                        {citation.version
                                          ? ` · Version ${citation.version}`
                                          : ""}
                                        {citation.effective_date
                                          ? ` · Effective ${citation.effective_date}`
                                          : ""}
                                      </span>
                                      {citation.excerpt && (
                                        <blockquote>{citation.excerpt}</blockquote>
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </section>
                            )}
                            {message.products?.length > 0 && (
                              <section className="message-products" aria-label="Product results">
                                <h3>Matching products</h3>
                                <div className="message-product-grid">
                                  {message.products.map((product) => (
                                    <article className="message-product-card" key={product.id}>
                                      <div>
                                        <span>{product.category || "Product"}</span>
                                        <span className={product.stock > 0 ? "in-stock" : "out-of-stock"}>
                                          {product.stock > 0 ? `${product.stock} in stock` : "Out of stock"}
                                        </span>
                                      </div>
                                      <h4>{product.name}</h4>
                                      {product.description && <p>{product.description}</p>}
                                      <strong>₹{Number(product.price).toLocaleString("en-IN", {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2,
                                      })}</strong>
                                    </article>
                                  ))}
                                </div>
                              </section>
                            )}
                          </>
                        ) : (
                          <p>{message.content}</p>
                        )}
                      </div>
                    </div>
                  </article>
                ))}

                {chatLoading && (
                  <div
                    className="chat-message assistant"
                    role="status"
                    aria-label="Assistant is responding"
                  >
                    <div className="message-avatar">✦</div>
                    <div className="message-body">
                      <span className="message-author">
                        SupportSphere AI
                      </span>
                      <p className="typing-indicator">
                        Thinking<span>.</span><span>.</span><span>.</span>
                      </p>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            )}

            {chatError && (
              <div className="chat-error" role="alert">
                <span>{chatError}</span>
                <button
                  type="button"
                  onClick={() => setChatError("")}
                  aria-label="Dismiss error"
                >
                  ×
                </button>
              </div>
            )}
          </div>

          {activeView === "chat" && <div className="chat-composer-area">
            <form
              className="chat-composer"
              onSubmit={(event) => handleSendMessage(event)}
            >
              <textarea
                aria-label="Your message"
                placeholder="Ask anything about your order, products, or support..."
                value={messageInput}
                onChange={(event) =>
                  setMessageInput(event.target.value)
                }
                maxLength={2000}
                rows={2}
                disabled={chatLoading}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
              />

              <div className="composer-footer">
                <span>
                  AI responses may not always be accurate.
                  <span className="character-count">
                    {" "}
                    {messageInput.length}/2000
                  </span>
                </span>

                <button
                  type="submit"
                  className="send-button"
                  disabled={
                    chatLoading || !messageInput.trim()
                  }
                  aria-label="Send message"
                >
                  {chatLoading ? "…" : "↑"}
                </button>
              </div>
            </form>

            <p className="composer-disclaimer">
              SupportSphere · Customer support powered by AI
            </p>
          </div>}
        </section>
      </main>
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            S
          </div>
          <span>SupportSphere</span>
        </div>

        <div className="intro-copy">
          <span className="eyebrow">
            CUSTOMER CARE, REIMAGINED
          </span>
          <h1>
            Support that
            <br />
            understands you.
          </h1>
          <p>
            Get helpful answers, track orders, and resolve issues
            with your AI-powered customer support assistant.
          </p>

          <div className="feature-list">
            <div className="feature-item">
              <span className="feature-icon" aria-hidden="true">
                ✦
              </span>
              <div>
                <strong>AI-powered assistance</strong>
                <span>Get answers to everyday questions.</span>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-icon" aria-hidden="true">
                ↗
              </span>
              <div>
                <strong>Help when you need it</strong>
                <span>Manage orders and support requests.</span>
              </div>
            </div>
          </div>
        </div>

        <p className="intro-footer">
          A simpler way to get the help you need.
        </p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="mobile-brand">
            <div className="brand-mark" aria-hidden="true">
              S
            </div>
            <span>SupportSphere</span>
          </div>

          <div className="form-heading">
            <span className="eyebrow">
              {authMode === "login" ? "WELCOME BACK" : "GET STARTED"}
            </span>
            <h2>
              {authMode === "login"
                ? "Sign in to your account"
                : "Create your account"}
            </h2>
            <p>
              {authMode === "login"
                ? "Enter your details to continue to your support space."
                : "Create an account to access personalized support."}
            </p>
          </div>

          <div
            className="auth-tabs"
            role="tablist"
            aria-label="Authentication"
          >
            <button
              type="button"
              role="tab"
              aria-selected={authMode === "login"}
              className={
                authMode === "login" ? "auth-tab active" : "auth-tab"
              }
              onClick={() => changeMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={authMode === "register"}
              className={
                authMode === "register"
                  ? "auth-tab active"
                  : "auth-tab"
              }
              onClick={() => changeMode("register")}
            >
              Create account
            </button>
          </div>

          <form
            className="auth-form"
            onSubmit={handleSubmit}
            noValidate
          >
            {authMode === "register" && (
              <div className="form-field">
                <label htmlFor="name">Full name</label>
                <input
                  id="name"
                  type="text"
                  autoComplete="name"
                  placeholder="Your full name"
                  value={name}
                  maxLength={100}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  required
                />
              </div>
            )}

            <div className="form-field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="password">Password</label>
              <div className="password-input-wrap">
                <input
                  id="password"
                  type={passwordVisible ? "text" : "password"}
                  autoComplete={
                    authMode === "login"
                      ? "current-password"
                      : "new-password"
                  }
                  placeholder={
                    authMode === "login"
                      ? "Enter your password"
                      : "At least 8 characters"
                  }
                  value={password}
                  maxLength={128}
                  onChange={(event) =>
                    setPassword(event.target.value)
                  }
                  required
                />
                <button
                  className="password-visibility-button"
                  type="button"
                  aria-label={passwordVisible ? "Hide password" : "Show password"}
                  aria-pressed={passwordVisible}
                  onClick={() => setPasswordVisible((visible) => !visible)}
                >
                  {passwordVisible ? (
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                      <path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a15.7 15.7 0 0 1-3.2 4.1M6.2 6.2C3.5 8 2 12 2 12s3.6 7 10 7c1.4 0 2.7-.4 3.8-.9" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {authMode === "register" && (
              <div className="form-field">
                <label htmlFor="confirmPassword">
                  Confirm password
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Enter your password again"
                  value={confirmPassword}
                  maxLength={128}
                  onChange={(event) =>
                    setConfirmPassword(event.target.value)
                  }
                  required
                />
              </div>
            )}

            {error && (
              <p className="form-message error" role="alert">
                {error}
              </p>
            )}
            {success && (
              <p className="form-message success" role="status">
                {success}
              </p>
            )}

            <button
              className="submit-button"
              type="submit"
              disabled={loading}
            >
              {loading
                ? "Please wait..."
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
              {!loading && (
                <span aria-hidden="true"> →</span>
              )}
            </button>
          </form>

          <p className="auth-switch">
            {authMode === "login"
              ? "New here?"
              : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() =>
                changeMode(
                  authMode === "login" ? "register" : "login",
                )
              }
            >
              {authMode === "login"
                ? "Create an account"
                : "Sign in"}
            </button>
          </p>

          <div className="connection-status">
            <span
              className={
                backendStatus === "Backend unavailable"
                  ? "status-dot offline"
                  : "status-dot"
              }
              aria-hidden="true"
            />
            <span>Backend: {backendStatus}</span>
          </div>
        </div>

        <p className="panel-footer">
          Secure access · Customer support workspace
        </p>
      </section>
    </main>
  );
}

export default App;
