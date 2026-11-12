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
  status: "SCHEDULED" | "PROCESSING" | "COMPLETED" | "SETTLED" | "FAILED" | "CANCELLED" | string;
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

export interface InvoiceReviewPayload {
  vendor_id?: number;
  department_id?: number;
  purchase_order_id?: number;
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  subtotal?: string | number;
  tax_amount?: string | number;
  total_amount?: string | number;
  currency?: string;
  description?: string;
  tax_identifier?: string;
  cgst_amount?: string | number;
  sgst_amount?: string | number;
  igst_amount?: string | number;
  customer_name?: string;
  customer_gstin?: string;
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

// ==========================================
// Phase 3: Multi-Agent AI Automation Types
// ==========================================

export interface AgentExecutionLogResponse {
  id: number;
  invoice_id?: number | null;
  agent_name: string;
  execution_status: string;
  input_summary?: string | null;
  output_summary?: string | null;
  error_message?: string | null;
  execution_duration?: string | number | null;
  created_at: string;
}

export interface InvoiceUnderstandingResult {
  agent_name: string;
  status: "PASSED" | "WARNING" | "FAILED" | string;
  confidence_score: string | number;
  tax_type: string;
  math_reconciled: boolean;
  discrepancy_amount: string | number;
  missing_fields: string[];
  abnormalities: string[];
  summary: string;
  details?: Record<string, any>;
}

export interface VendorVerificationResult {
  agent_name: string;
  status: "VERIFIED" | "UNKNOWN_VENDOR" | "GSTIN_MISMATCH" | "INACTIVE_VENDOR" | "NAME_MISMATCH" | string;
  vendor_id?: number | null;
  vendor_code?: string | null;
  legal_name?: string | null;
  invoice_vendor_name?: string | null;
  invoice_gstin?: string | null;
  registered_gstin?: string | null;
  gstin_matched: boolean;
  is_active: boolean;
  has_bank_details: boolean;
  summary: string;
  reasons: string[];
}

export interface LineItemMatch {
  line_number: number;
  description: string;
  po_quantity?: string | number | null;
  grn_accepted_quantity?: string | number | null;
  invoice_quantity: string | number;
  po_unit_price?: string | number | null;
  invoice_unit_price: string | number;
  price_variance: string | number;
  quantity_variance: string | number;
  status: "MATCHED" | "PRICE_VARIANCE" | "QUANTITY_VARIANCE" | "UNMATCHED" | string;
}

export interface ThreeWayMatchingResult {
  agent_name: string;
  match_status: "FULL_MATCH" | "PARTIAL_MATCH" | "PRICE_VARIANCE" | "QUANTITY_VARIANCE" | "NO_PO" | "NO_GRN" | "DISCREPANCY" | string;
  po_number?: string | null;
  po_total?: string | number | null;
  invoice_total?: string | number | null;
  total_variance: string | number;
  grn_numbers: string[];
  line_matches: LineItemMatch[];
  discrepancies: string[];
  summary: string;
}

export interface RiskFactor {
  factor: string;
  score_impact: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
}

export interface FraudRiskResult {
  agent_name: string;
  risk_score: string | number;
  risk_category: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_factors: RiskFactor[];
  recommended_action: string;
  summary: string;
}

export interface ApprovalRecommendationResult {
  agent_name: string;
  recommendation: "APPROVE" | "REVIEW" | "REJECT" | string;
  confidence: string | number;
  executive_summary: string;
  key_reasons: string[];
  unresolved_issues: string[];
  action_checklist: string[];
}

export interface MultiAgentAnalysisReport {
  invoice_id: number;
  orchestrator_status: "COMPLETED" | "FAILED" | "PARTIAL" | string;
  recommendation: "APPROVE" | "REVIEW" | "REJECT" | string;
  risk_score: string | number;
  risk_category: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  understanding: InvoiceUnderstandingResult;
  vendor_verification: VendorVerificationResult;
  matching: ThreeWayMatchingResult;
  fraud_risk: FraudRiskResult;
  approval_recommendation: ApprovalRecommendationResult;
  execution_logs: AgentExecutionLogResponse[];
  unresolved_issues: string[];
  analyzed_at: string;
}

// ==========================================
// Phase 4: ERP Integration & Accounting Types
// ==========================================

export interface ChartOfAccount {
  id: number;
  account_code: string;
  account_name: string;
  account_type: "ASSET" | "LIABILITY" | "EQUITY" | "REVENUE" | "EXPENSE" | string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  debit_balance?: string | number;
  credit_balance?: string | number;
  net_balance?: string | number;
}

export interface AccountMapping {
  id: number;
  mapping_type: string;
  entity_id?: number | null;
  expense_category?: string | null;
  debit_account_id: number;
  credit_account_id?: number | null;
  description?: string | null;
  is_active: boolean;
  debit_account?: ChartOfAccount;
  credit_account?: ChartOfAccount;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryLine {
  id: number;
  journal_entry_id: number;
  line_number: number;
  account_id: number;
  account_code?: string;
  account_name?: string;
  account_type?: string;
  description: string;
  debit_amount: string | number;
  credit_amount: string | number;
  department_id?: number | null;
  vendor_id?: number | null;
}

export interface JournalEntry {
  id: number;
  entry_number: string;
  invoice_id?: number | null;
  posting_date: string;
  accounting_period: string;
  description: string;
  total_debit: string | number;
  total_credit: string | number;
  is_balanced: boolean;
  status: "POSTED" | "REVERSED" | "DRAFT" | string;
  reversal_of_id?: number | null;
  erp_document_reference?: string | null;
  created_by?: number | null;
  created_at: string;
  lines?: JournalEntryLine[];
}

export interface TrialBalanceAccount {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: string;
  debit_total: string | number;
  credit_total: string | number;
  net_debit: string | number;
  net_credit: string | number;
}

export interface TrialBalanceResponse {
  accounting_period?: string | null;
  as_of_date: string;
  accounts: TrialBalanceAccount[];
  total_debit: string | number;
  total_credit: string | number;
  is_balanced: boolean;
}

export interface PostingEligibilityCheck {
  check_name: string;
  passed: boolean;
  message: string;
  severity: "ERROR" | "WARNING" | "INFO";
}

export interface PostingEligibilityResponse {
  invoice_id: number;
  eligible: boolean;
  human_approved: boolean;
  already_posted: boolean;
  checks: PostingEligibilityCheck[];
  blocking_reasons: string[];
  warnings: string[];
}

export interface ERPPosting {
  id: number;
  invoice_id: number;
  journal_entry_id?: number | null;
  erp_adapter: string;
  erp_document_reference: string;
  idempotency_key: string;
  status: "PENDING" | "QUEUED" | "SYNCING" | "SYNCED" | "FAILED" | "RETRY_PENDING" | string;
  posted_at?: string | null;
  error_message?: string | null;
  response_payload?: any;
  journal_entry?: JournalEntry;
  created_at: string;
  updated_at: string;
}

export interface ERPSyncLog {
  id: number;
  erp_posting_id?: number | null;
  invoice_id?: number | null;
  action: string;
  status: string;
  request_payload?: any;
  response_payload?: any;
  error_details?: string | null;
  duration_ms?: number | null;
  created_at: string;
}

export interface ERPConnectionStatus {
  adapter_name: string;
  connection_type: string;
  is_connected: boolean;
  latency_ms: number;
  supported_features: string[];
  active_postings_count: number;
  pending_sync_count: number;
  failed_sync_count: number;
  system_time: string;
  notice: string;
}

export interface InvoicePaymentBalance {
  invoice_id: number;
  invoice_number: string;
  total_invoiced_amount: string | number;
  total_paid_amount: string | number;
  outstanding_balance: string | number;
  is_fully_paid: boolean;
  payment_status: string;
  payments: Array<{
    id: number;
    reference: string;
    amount: number;
    status: string;
    method: string;
    scheduled_date: string;
    payment_date?: string | null;
  }>;
}

export interface PaymentPreparationRequest {
  invoice_id: number;
  amount: number | string;
  scheduled_date: string;
  payment_method?: string;
  comments?: string;
}

export interface PaymentPreparationResponse {
  payment_id: number;
  invoice_id: number;
  payment_reference: string;
  amount: string | number;
  scheduled_date: string;
  payment_method: string;
  status: string;
  remaining_balance_after: string | number;
  message: string;
}
