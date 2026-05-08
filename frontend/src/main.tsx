import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
if (typeof window !== "undefined" && (window as any).Telegram?.WebApp) {
  const tg = (window as any).Telegram.WebApp;
  tg.ready(); tg.expand();
  tg.setHeaderColor?.("#0d0d0d");
  tg.setBackgroundColor?.("#0d0d0d");
}
ReactDOM.createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
