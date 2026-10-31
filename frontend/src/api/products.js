
import { apiRequest } from "./client";

/**
 * Fetch products from the backend.
 *
 * Optional filters:
 * - query: search product names and descriptions
 * - category: filter by category
 * - max_price: maximum product price
 */
export function getProducts({
  query = "",
  category = "",
  minPrice = "",
  maxPrice = "",
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams();

  if (query.trim()) {
    params.set("query", query.trim());
  }

  if (category) {
    params.set("category", category);
  }

  if (minPrice !== "" && Number(minPrice) > 0) {
    params.set("min_price", minPrice);
  }

  if (maxPrice !== "" && Number(maxPrice) > 0) {
    params.set("max_price", maxPrice);
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));

  const queryString = params.toString();
  const path = queryString
    ? `/api/products?${queryString}`
    : "/api/products";

  return apiRequest(path);
}

export function getProduct(productId) {
  return apiRequest(`/api/products/${productId}`);
}

export function getProductCategories() {
  return apiRequest("/api/products/categories");
}

export function getAdminProducts({ query = "", limit = 50, offset = 0 } = {}, token) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (query.trim()) params.set("query", query.trim());
  return apiRequest(`/api/products/admin/all?${params}`, { token });
}

export function createProduct(product, token) {
  return apiRequest("/api/products", { method: "POST", body: product, token });
}

export function updateProduct(productId, product, token) {
  return apiRequest(`/api/products/${productId}`, { method: "PATCH", body: product, token });
}

export function deleteProduct(productId, token) {
  return apiRequest(`/api/products/${productId}`, { method: "DELETE", token });
}
