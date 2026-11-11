-- Bahi-AI PostgreSQL Database Schema
-- Auto-generated for Phase 1


CREATE TABLE departments (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE vendors (
	id SERIAL NOT NULL, 
	vendor_code VARCHAR(50) NOT NULL, 
	legal_name VARCHAR(200) NOT NULL, 
	contact_person VARCHAR(150) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50) NOT NULL, 
	address TEXT NOT NULL, 
	tax_identifier VARCHAR(100) NOT NULL, 
	bank_account_last_four VARCHAR(4) NOT NULL, 
	bank_name VARCHAR(150) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE budgets (
	id SERIAL NOT NULL, 
	department_id INTEGER NOT NULL, 
	fiscal_year VARCHAR(20) NOT NULL, 
	allocated_amount NUMERIC(14, 2) NOT NULL, 
	committed_amount NUMERIC(14, 2) NOT NULL, 
	spent_amount NUMERIC(14, 2) NOT NULL, 
	available_amount NUMERIC(14, 2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_dept_fiscal_year UNIQUE (department_id, fiscal_year), 
	CONSTRAINT chk_budget_allocated_nonnegative CHECK (allocated_amount >= 0), 
	CONSTRAINT chk_budget_committed_nonnegative CHECK (committed_amount >= 0), 
	CONSTRAINT chk_budget_spent_nonnegative CHECK (spent_amount >= 0), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT
)

;


CREATE TABLE users (
	id SERIAL NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	department_id INTEGER, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL
)

;


CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(100) NOT NULL, 
	old_values JSON, 
	new_values JSON, 
	ip_address VARCHAR(50), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)

;


CREATE TABLE purchase_orders (
	id SERIAL NOT NULL, 
	po_number VARCHAR(50) NOT NULL, 
	vendor_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	issue_date DATE NOT NULL, 
	expected_delivery_date DATE, 
	total_amount NUMERIC(14, 2) NOT NULL, 
	tax_amount NUMERIC(14, 2) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	created_by INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendors (id) ON DELETE RESTRICT, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT, 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE goods_receipts (
	id SERIAL NOT NULL, 
	grn_number VARCHAR(50) NOT NULL, 
	purchase_order_id INTEGER NOT NULL, 
	received_by INTEGER NOT NULL, 
	received_date DATE NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id) ON DELETE RESTRICT, 
	FOREIGN KEY(received_by) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE invoices (
	id SERIAL NOT NULL, 
	invoice_number VARCHAR(100) NOT NULL, 
	normalized_invoice_number VARCHAR(100) NOT NULL, 
	vendor_id INTEGER NOT NULL, 
	purchase_order_id INTEGER, 
	department_id INTEGER NOT NULL, 
	invoice_date DATE NOT NULL, 
	due_date DATE NOT NULL, 
	subtotal NUMERIC(14, 2) NOT NULL, 
	tax_amount NUMERIC(14, 2) NOT NULL, 
	total_amount NUMERIC(14, 2) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	document_path VARCHAR(500), 
	original_filename VARCHAR(255), 
	extraction_status VARCHAR(50) NOT NULL, 
	processing_status VARCHAR(50) NOT NULL, 
	approval_status VARCHAR(50) NOT NULL, 
	payment_status VARCHAR(50) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_vendor_normalized_invoice UNIQUE (vendor_id, normalized_invoice_number), 
	FOREIGN KEY(vendor_id) REFERENCES vendors (id) ON DELETE RESTRICT, 
	FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id) ON DELETE SET NULL, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT
)

;


CREATE TABLE purchase_order_lines (
	id SERIAL NOT NULL, 
	purchase_order_id INTEGER NOT NULL, 
	line_number INTEGER NOT NULL, 
	item_description TEXT NOT NULL, 
	quantity NUMERIC(10, 2) NOT NULL, 
	unit_price NUMERIC(14, 2) NOT NULL, 
	tax_rate NUMERIC(5, 2) NOT NULL, 
	total_amount NUMERIC(14, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders (id) ON DELETE CASCADE
)

;


CREATE TABLE agent_execution_logs (
	id SERIAL NOT NULL, 
	invoice_id INTEGER, 
	agent_name VARCHAR(100) NOT NULL, 
	execution_status VARCHAR(50) NOT NULL, 
	input_summary TEXT, 
	output_summary TEXT, 
	error_message TEXT, 
	execution_duration NUMERIC(10, 4), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
)

;


CREATE TABLE approvals (
	id SERIAL NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	approver_id INTEGER NOT NULL, 
	approval_level INTEGER NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	comments TEXT, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE, 
	FOREIGN KEY(approver_id) REFERENCES users (id) ON DELETE RESTRICT
)

;


CREATE TABLE fraud_alerts (
	id SERIAL NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	alert_type VARCHAR(100) NOT NULL, 
	severity VARCHAR(50) NOT NULL, 
	description TEXT NOT NULL, 
	risk_score NUMERIC(5, 2) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	resolved_by INTEGER, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE SET NULL
)

;


CREATE TABLE goods_receipt_lines (
	id SERIAL NOT NULL, 
	goods_receipt_id INTEGER NOT NULL, 
	purchase_order_line_id INTEGER NOT NULL, 
	quantity_ordered NUMERIC(10, 2) NOT NULL, 
	quantity_received NUMERIC(10, 2) NOT NULL, 
	quantity_accepted NUMERIC(10, 2) NOT NULL, 
	quantity_rejected NUMERIC(10, 2) NOT NULL, 
	notes TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(goods_receipt_id) REFERENCES goods_receipts (id) ON DELETE CASCADE, 
	FOREIGN KEY(purchase_order_line_id) REFERENCES purchase_order_lines (id) ON DELETE RESTRICT
)

;


CREATE TABLE invoice_lines (
	id SERIAL NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	line_number INTEGER NOT NULL, 
	description TEXT NOT NULL, 
	quantity NUMERIC(10, 2) NOT NULL, 
	unit_price NUMERIC(14, 2) NOT NULL, 
	tax_rate NUMERIC(5, 2) NOT NULL, 
	line_total NUMERIC(14, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
)

;


CREATE TABLE payments (
	id SERIAL NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	payment_reference VARCHAR(100) NOT NULL, 
	scheduled_date DATE NOT NULL, 
	payment_date DATE, 
	amount NUMERIC(14, 2) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	payment_method VARCHAR(50) NOT NULL, 
	external_reference VARCHAR(100), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
)

;

