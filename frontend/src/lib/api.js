import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const fmtEuro = (n) =>
  new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(n || 0);

export const fmtNum = (n, digits = 1) =>
  new Intl.NumberFormat("it-IT", { minimumFractionDigits: 0, maximumFractionDigits: digits }).format(n || 0);
