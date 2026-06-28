"use client";

import { useEffect } from "react";

export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const isLocalhost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
    if (window.location.protocol !== "https:" && !isLocalhost) return;

    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // PWA install still works with the manifest; registration can fail in private modes.
      });
    });
  }, []);

  return null;
}
