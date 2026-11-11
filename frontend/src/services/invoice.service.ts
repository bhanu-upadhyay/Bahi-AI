import { api } from "./api";

export const invoiceService = {
  getAll: api.getInvoices,
  getById: api.getInvoiceById,
  create: api.createInvoice,
};

