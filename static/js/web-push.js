/* Web Push 客戶端
 * --------------------------------------------------
 * 注意：本檔案為「純靜態」JS，不含 Jinja 模板語法。
 * 必要設定改由 HTML 提供：
 *   <meta name="vapid-public-key" content="...">  (可選)
 *   <meta name="csrf-token" content="...">         (建議)
 * 端點：
 *   GET  /notifications/api/vapid-public-key  → { publicKey }
 *   POST /notifications/subscribe              ← subscription JSON
 *   POST /notifications/unsubscribe            ← { endpoint }
 */

(function () {
  "use strict";

  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? (el.getAttribute("content") || "").trim() : "";
  }

  function urlBase64ToUint8Array(base64String) {
    if (!base64String) return new Uint8Array();
    var padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    var base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    var rawData = window.atob(base64);
    var output = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; i++) {
      output[i] = rawData.charCodeAt(i);
    }
    return output;
  }

  var webPush = {
    isSupported: ("Notification" in window) && ("serviceWorker" in navigator) && ("PushManager" in window),
    vapidPublicKey: getMeta("vapid-public-key"),

    async fetchVapidKey() {
      if (this.vapidPublicKey) return this.vapidPublicKey;
      try {
        var resp = await fetch("/notifications/api/vapid-public-key", { credentials: "same-origin" });
        if (!resp.ok) return "";
        var data = await resp.json();
        this.vapidPublicKey = data.publicKey || "";
        return this.vapidPublicKey;
      } catch (e) {
        return "";
      }
    },

    async init() {
      if (!this.isSupported) return false;
      if (Notification.permission === "default") {
        await this.requestPermission();
      }
      return Notification.permission === "granted";
    },

    async requestPermission() {
      try {
        var permission = await Notification.requestPermission();
        return permission === "granted";
      } catch (e) {
        console.error("Permission request failed:", e);
        return false;
      }
    },

    async subscribe() {
      if (!this.isSupported) return null;
      try {
        var key = await this.fetchVapidKey();
        if (!key) {
          console.warn("VAPID public key 未設定，無法訂閱推送。");
          return null;
        }
        var registration = await navigator.serviceWorker.ready;
        var subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(key),
        });
        await this.saveSubscription(subscription);
        return subscription;
      } catch (e) {
        console.error("Subscribe failed:", e);
        return null;
      }
    },

    async unsubscribe() {
      try {
        var registration = await navigator.serviceWorker.ready;
        var subscription = await registration.pushManager.getSubscription();
        if (subscription) {
          await subscription.unsubscribe();
          await this.removeSubscription(subscription.endpoint);
        }
        return true;
      } catch (e) {
        console.error("Unsubscribe failed:", e);
        return false;
      }
    },

    async checkSubscription() {
      try {
        var registration = await navigator.serviceWorker.ready;
        var subscription = await registration.pushManager.getSubscription();
        return !!subscription;
      } catch (e) {
        return false;
      }
    },

    async saveSubscription(subscription) {
      var resp = await fetch("/notifications/subscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getMeta("csrf-token"),
        },
        credentials: "same-origin",
        body: JSON.stringify(subscription),
      });
      return resp.ok;
    },

    async removeSubscription(endpoint) {
      var resp = await fetch("/notifications/unsubscribe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getMeta("csrf-token"),
        },
        credentials: "same-origin",
        body: JSON.stringify({ endpoint: endpoint }),
      });
      return resp.ok;
    },
  };

  window.webPush = webPush;

  // 註冊 Service Worker（若可用）
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker
        .register("/static/js/sw.js", { scope: "/" })
        .catch(function (err) {
          console.warn("Service Worker 註冊失敗：", err);
        });
    });
  }

  // 啟用 / 停用按鈕（id="pushToggleBtn"）
  window.togglePushSubscription = async function () {
    var btn = document.getElementById("pushToggleBtn");
    if (!btn) return;
    btn.disabled = true;
    var originalLabel = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 處理中...';
    try {
      var subscribed = await webPush.checkSubscription();
      if (subscribed) {
        await webPush.unsubscribe();
        btn.innerHTML = '<i class="fas fa-bell"></i> 啟用通知';
        btn.classList.remove("btn-success");
        btn.classList.add("btn-outline-primary");
      } else {
        await webPush.subscribe();
        btn.innerHTML = '<i class="fas fa-bell-slash"></i> 取消訂閱';
        btn.classList.remove("btn-outline-primary");
        btn.classList.add("btn-success");
      }
    } catch (e) {
      console.error(e);
      btn.innerHTML = originalLabel;
    } finally {
      btn.disabled = false;
    }
  };
})();
