import { api } from "./api";

export const paymentService = {
  getAll: api.getPayments,
  simulate: api.simulatePayment,
};

