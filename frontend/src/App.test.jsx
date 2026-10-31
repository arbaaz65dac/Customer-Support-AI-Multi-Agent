import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { apiRequest } from "./api/client";
import { sendChatMessage } from "./api/chat";

vi.mock("./api/auth", () => ({
  getCustomerProfile: vi.fn(),
  loginCustomer: vi.fn(),
  registerCustomer: vi.fn(),
}));

vi.mock("./api/chat", () => ({
  sendChatMessage: vi.fn(),
}));

vi.mock("./api/products", () => ({
  getProduct: vi.fn(),
  getProductCategories: vi.fn().mockResolvedValue([]),
  getProducts: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

vi.mock("./api/orders", () => ({
  getCustomerOrder: vi.fn(),
  getCustomerOrders: vi.fn().mockResolvedValue([]),
}));

vi.mock("./components/AdminWorkspace", () => ({
  default: () => <h1>Admin workspace</h1>,
}));

vi.mock("./components/TicketCenter", () => ({
  default: () => <h1>Ticket center</h1>,
}));

vi.mock("./components/RefundCenter", () => ({
  default: () => <h1>Refund center</h1>,
}));

function setSession(role = "customer") {
  sessionStorage.setItem("access_token", "test-token");
  sessionStorage.setItem("customer_id", "17");
  sessionStorage.setItem("customer_name", "Test User");
  sessionStorage.setItem("customer_role", role);
}

function renderApp(path = "/customer/chat") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("application access and chat workflows", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    globalThis.fetch = vi.fn(async (url) => {
      if (String(url).endsWith("/health")) {
        return new Response(JSON.stringify({ message: "Connected" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify({ detail: "Not authenticated" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    });
    sendChatMessage.mockResolvedValue({
      answer: "I found a matching product.",
      products: [],
      citations: [],
    });
  });

  it("redirects unauthenticated visitors to login", async () => {
    renderApp("/customer/orders");

    expect(
      await screen.findByRole("heading", { name: "Sign in to your account" }),
    ).toBeInTheDocument();
  });

  it("toggles the login password between hidden and visible", async () => {
    const user = userEvent.setup();
    renderApp("/login");

    const password = await screen.findByLabelText("Password");
    expect(password).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(password).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: "Hide password" }));
    expect(password).toHaveAttribute("type", "password");
  });

  it("blocks a customer from admin routes", async () => {
    setSession("customer");
    renderApp("/admin/dashboard");

    expect(await screen.findByRole("textbox", { name: "Your message" }))
      .toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Admin workspace" }))
      .not.toBeInTheDocument();
  });

  it("allows an admin to open the admin workspace", async () => {
    setSession("admin");
    renderApp("/admin/dashboard");

    expect(await screen.findByRole("heading", { name: "Admin workspace" }))
      .toBeInTheDocument();
  });

  it("clears the session and redirects after a 401 response", async () => {
    setSession("customer");
    renderApp();

    await screen.findByRole("textbox", { name: "Your message" });
    await act(async () => {
      await expect(apiRequest("/private", { token: "expired-token" }))
        .rejects.toThrow("Not authenticated");
    });

    expect(await screen.findByRole("heading", { name: "Sign in to your account" }))
      .toBeInTheDocument();
    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(sessionStorage.getItem("customer_id")).toBeNull();
  });

  it("prevents duplicate chat submissions while a request is pending", async () => {
    setSession("customer");
    let resolveChat;
    sendChatMessage.mockImplementation(
      () => new Promise((resolve) => { resolveChat = resolve; }),
    );
    const user = userEvent.setup();
    renderApp();

    const input = await screen.findByRole("textbox", { name: "Your message" });
    await user.type(input, "Find wireless headphones");
    const submit = screen.getByRole("button", { name: "Send message" });
    await user.click(submit);
    await user.click(submit);

    expect(sendChatMessage).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolveChat({ answer: "Here are some headphones.", products: [], citations: [] });
    });
    expect(await screen.findByText("Here are some headphones."))
      .toBeInTheDocument();
  });

  it("shows a chat error and restores the unsent message", async () => {
    setSession("customer");
    sendChatMessage.mockRejectedValue(new Error("Assistant unavailable"));
    const user = userEvent.setup();
    renderApp();

    const input = await screen.findByRole("textbox", { name: "Your message" });
    await user.type(input, "Where is my order?");
    await user.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByRole("alert"))
      .toHaveTextContent("Assistant unavailable");
    expect(input).toHaveValue("Where is my order?");
  });
});
