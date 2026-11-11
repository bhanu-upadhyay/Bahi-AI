import {
  DashboardSummary,
  Invoice,
  InvoiceUploadResponse,
  InvoiceValidationResponse,
  Department,
  Vendor,
  PurchaseOrder,
  GoodsReceipt,
  Budget,
  Approval,
  Payment,
  FraudAlert,
  AuditLog,
  User,
} from "../types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${url}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message =
      errorBody.detail?.message ||
      (Array.isArray(errorBody.detail?.errors) ? errorBody.detail.errors.join("; ") : null) ||
      errorBody.detail ||
      `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export const api = {
  // Base URL
  baseUrl: API_BASE_URL,

  // Dashboard
  getDashboardSummary: (): Promise<DashboardSummary> => fetchJson<DashboardSummary>("/dashboard/summary"),

  // Invoices
  getInvoices: (params?: {
    status?: string;
    approval_status?: string;
    payment_status?: string;
    department_id?: number;
    search?: string;
  }): Promise<Invoice[]> => {
    const query = new URLSearchParams();
    if (params?.status) query.append("status", params.status);
    if (params?.approval_status) query.append("approval_status", params.approval_status);
    if (params?.payment_status) query.append("payment_status", params.payment_status);
    if (params?.department_id) query.append("department_id", params.department_id.toString());
    if (params?.search) query.append("search", params.search);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return fetchJson<Invoice[]>(`/invoices${qs}`);
  },

  getInvoiceById: (id: number): Promise<Invoice> => fetchJson<Invoice>(`/invoices/${id}`),

  createInvoice: (data: Partial<Invoice>): Promise<Invoice> =>
    fetchJson<Invoice>("/invoices", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 2: Upload, Review & Validation
  uploadInvoice: async (file: File, departmentId?: number): Promise<InvoiceUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    if (departmentId) {
      formData.append("department_id", departmentId.toString());
    }

    const res = await fetch(`${API_BASE_URL}/invoices/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Upload failed with status ${res.status}`);
    }

    return res.json();
  },

  reviewInvoice: (id: number, data: Partial<Invoice>): Promise<Invoice> =>
    fetchJson<Invoice>(`/invoices/${id}/review`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  validateInvoice: (id: number): Promise<InvoiceValidationResponse> =>
    fetchJson<InvoiceValidationResponse>(`/invoices/${id}/validate`, {
      method: "POST",
    }),

  getInvoiceExtraction: (id: number): Promise<any> =>
    fetchJson<any>(`/invoices/${id}/extraction`),

  getDocumentUrl: (id: number): string => `${API_BASE_URL}/invoices/${id}/document`,

  // Departments
  getDepartments: (): Promise<Department[]> => fetchJson<Department[]>("/departments"),

  // Vendors
  getVendors: (search?: string): Promise<Vendor[]> => {
    const qs = search ? `?search=${encodeURIComponent(search)}` : "";
    return fetchJson<Vendor[]>(`/vendors${qs}`);
  },
  getVendorById: (id: number): Promise<Vendor> => fetchJson<Vendor>(`/vendors/${id}`),

  // Purchase Orders
  getPurchaseOrders: (): Promise<PurchaseOrder[]> => fetchJson<PurchaseOrder[]>("/purchase-orders"),
  getPurchaseOrderById: (id: number): Promise<PurchaseOrder> => fetchJson<PurchaseOrder>(`/purchase-orders/${id}`),

  // Goods Receipts
  getGoodsReceipts: (): Promise<GoodsReceipt[]> => fetchJson<GoodsReceipt[]>("/goods-receipts"),
  getGoodsReceiptById: (id: number): Promise<GoodsReceipt> => fetchJson<GoodsReceipt>(`/goods-receipts/${id}`),

  // Budgets
  getBudgets: (fiscal_year?: string): Promise<Budget[]> => {
    const qs = fiscal_year ? `?fiscal_year=${encodeURIComponent(fiscal_year)}` : "";
    return fetchJson<Budget[]>(`/budgets${qs}`);
  },

  // Approvals
  getApprovals: (status?: string): Promise<Approval[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return fetchJson<Approval[]>(`/approvals${qs}`);
  },

  actOnApproval: (
    approvalId: number,
    data: { status: "APPROVED" | "REJECTED"; comments?: string; approver_id?: number }
  ): Promise<Approval> =>
    fetchJson<Approval>(`/approvals/${approvalId}/action`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Payments
  getPayments: (status?: string): Promise<Payment[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return fetchJson<Payment[]>(`/payments${qs}`);
  },

  simulatePayment: (paymentId: number): Promise<Payment> =>
    fetchJson<Payment>(`/payments/${paymentId}/simulate`, {
      method: "POST",
    }),

  // Fraud Alerts
  getFraudAlerts: (status?: string): Promise<FraudAlert[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return fetchJson<FraudAlert[]>(`/fraud-alerts${qs}`);
  },

  resolveFraudAlert: (alertId: number, status: "RESOLVED" | "DISMISSED"): Promise<FraudAlert> =>
    fetchJson<FraudAlert>(`/fraud-alerts/${alertId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  // Audit Logs
  getAuditLogs: (entity_type?: string): Promise<AuditLog[]> => {
    const qs = entity_type ? `?entity_type=${encodeURIComponent(entity_type)}` : "";
    return fetchJson<AuditLog[]>(`/audit-logs${qs}`);
  },

  // Users
  getUsers: (): Promise<User[]> => fetchJson<User[]>("/users"),
};
