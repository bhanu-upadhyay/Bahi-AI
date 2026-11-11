export type UserRole =
  | "VENDOR"
  | "HOD"
  | "PROCUREMENT_OFFICER"
  | "FINANCE_OFFICER"
  | "FINANCE_ADMIN";

export interface User {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  department_id?: number | null;
  is_active: boolean;
  created_at: string;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Vendor {
  id: number;
  vendor_code: string;
  legal_name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  tax_identifier: string;
  bank_account_last_four: string;
  bank_name: string;
  is_active: boolean;
  created_at: string;
}

export interface PurchaseOrderLine {
  id: number;
  purchase_order_id: number;
  line_number: number;
  item_description: string;
  quantity: string | number;
  unit_price: string | number;
  tax_rate: string | number;
  total_amount: string | number;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  vendor_id: number;
  department_id: number;
  issue_date: string;
  expected_delivery_date?: string | null;
  total_amount: string | number;
  tax_amount: string | number;
  status: string;
  created_by: number;
  created_at: string;
  lines?: PurchaseOrderLine[];
  vendor?: Vendor;
  department?: Department;
}

export interface GoodsReceiptLine {
  id: number;
  goods_receipt_id: number;
  purchase_order_line_id: number;
  quantity_ordered: string | number;
  quantity_received: string | number;
  quantity_accepted: string | number;
  quantity_rejected: string | number;
  notes?: string | null;
}

export interface GoodsReceipt {
  id: number;
  grn_number: string;
  purchase_order_id: number;
  received_by: number;
  received_date: string;
  status: string;
  notes?: string | null;
  created_at: string;
  lines?: GoodsReceiptLine[];
  receiver?: User;
}

export interface InvoiceLine {
  id: number;
  invoice_id: number;
  line_number: number;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  tax_rate: string | number;
  line_total: string | number;
}

export interface Approval {
  id: number;
  invoice_id: number;
  approver_id: number;
  approval_level: number;
  status: "PENDING" | "APPROVED" | "REJECTED";
  comments?: string | null;
  decided_at?: string | null;
  created_at: string;
  approver?: User;
}

export interface Payment {
  id: number;
  invoice_id: number;
  payment_reference: string;
  scheduled_date: string;
  payment_date?: string | null;
  amount: string | number;
  status: "SCHEDULED" | "PROCESSING" | "COMPLETED" | "FAILED" | "CANCELLED";
  payment_method: string;
  external_reference?: string | null;
  created_at: string;
}

export interface FraudAlert {
  id: number;
  invoice_id: number;
  alert_type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
  risk_score: string | number;
  status: "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "DISMISSED";
  resolved_by?: number | null;
  resolved_at?: string | null;
  created_at: string;
  resolver?: User;
}

export interface Invoice {
  id: number;
  invoice_number: string;
  normalized_invoice_number: string;
  vendor_id?: number | null;
  purchase_order_id?: number | null;
  department_id?: number | null;
  invoice_date?: string | null;
  due_date?: string | null;
  subtotal?: string | number | null;
  tax_amount: string | number;
  total_amount?: string | number | null;
  currency: string;
  description?: string | null;
  tax_identifier?: string | null;
  document_path?: string | null;
  original_filename?: string | null;
  file_hash?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  raw_text?: string | null;
  ocr_method?: string | null;
  confidence_score?: string | number | null;
  extraction_metadata?: any;
  extraction_status: string;
  processing_status: string;
  approval_status: string;
  payment_status: string;
  created_at: string;
  updated_at: string;
  vendor?: Vendor;
  department?: Department;
  lines?: InvoiceLine[];
  purchase_order?: PurchaseOrder;
  approvals?: Approval[];
  payments?: Payment[];
  fraud_alerts?: FraudAlert[];
}

export interface InvoiceUploadResponse {
  invoice_id: number;
  invoice_number: string;
  original_filename: string;
  file_hash: string;
  file_size: number;
  mime_type: string;
  ocr_method?: string | null;
  confidence_score?: string | number | null;
  processing_status: string;
  extraction_status: string;
  is_duplicate: boolean;
  duplicate_warning?: string | null;
  duplicate_invoice_id?: number | null;
  extracted_data?: any;
}

export interface InvoiceValidationResponse {
  success: boolean;
  invoice_id: number;
  processing_status: string;
  message: string;
  invoice: Invoice;
}

export interface Budget {
  id: number;
  department_id: number;
  fiscal_year: string;
  allocated_amount: string | number;
  committed_amount: string | number;
  spent_amount: string | number;
  available_amount: string | number;
  created_at: string;
  updated_at: string;
  department?: Department;
}

export interface DepartmentBudgetSummary {
  department_id: number;
  department_name: string;
  department_code: string;
  allocated_amount: string | number;
  committed_amount: string | number;
  spent_amount: string | number;
  available_amount: string | number;
  utilization_percentage: number;
}

export interface DashboardSummary {
  total_invoices: number;
  pending_approvals: number;
  invoices_under_review: number;
  exceptions_detected: number;
  total_payable_amount: string | number;
  scheduled_payments_amount: string | number;
  total_budget_allocated: string | number;
  total_budget_spent: string | number;
  total_budget_committed: string | number;
  total_budget_available: string | number;
  overall_budget_utilization: number;
  department_budgets: DepartmentBudgetSummary[];
  workflow_status_counts: Record<string, number>;
  recent_invoices: Invoice[];
  recent_audit_activity: AuditLog[];
  recent_fraud_alerts: FraudAlert[];
}

export interface AuditLog {
  id: number;
  user_id?: number | null;
  action: string;
  entity_type: string;
  entity_id: string;
  old_values?: any;
  new_values?: any;
  ip_address?: string | null;
  created_at: string;
  user?: User;
}
