(function () {
  // ---- 알림 드롭다운 ----
  const bellBtn = document.getElementById("notif-bell-btn");
  const panel = document.getElementById("notif-panel");
  const panelBody = document.getElementById("notif-panel-body");
  const badge = document.getElementById("notif-badge");

  function renderNotifications(items) {
    if (!items.length) {
      panelBody.innerHTML = '<p class="muted">알림이 없습니다.</p>';
      return;
    }
    panelBody.innerHTML = items
      .slice(0, 8)
      .map(
        (n) => `
        <div class="notif-item ${n.is_read ? "" : "unread"}">
          <strong>${n.title}</strong>
          <p>${n.message}</p>
          <span class="muted">${n.created_at.replace("T", " ").slice(0, 16)}</span>
        </div>`
      )
      .join("");
  }

  async function openNotifications() {
    panel.hidden = false;
    bellBtn.setAttribute("aria-expanded", "true");
    try {
      const res = await fetch("/api/me/notifications");
      const body = await res.json();
      renderNotifications(body.data || []);
    } catch (err) {
      panelBody.innerHTML = '<p class="muted">알림을 불러오지 못했습니다.</p>';
    }
    if (badge) {
      badge.hidden = true;
      badge.textContent = "0";
    }
    fetch("/api/me/notifications/mark-read", { method: "POST" }).catch(() => {});
  }

  function closeNotifications() {
    panel.hidden = true;
    bellBtn.setAttribute("aria-expanded", "false");
  }

  if (bellBtn && panel) {
    bellBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      if (panel.hidden) {
        openNotifications();
      } else {
        closeNotifications();
      }
    });
    document.addEventListener("click", (event) => {
      if (!panel.hidden && !panel.contains(event.target) && event.target !== bellBtn) {
        closeNotifications();
      }
    });
  }

  // ---- 서비스 다중 선택 배치 바 ----
  const multiForm = document.getElementById("multi-select-form");
  const batchBar = document.querySelector("[data-batch-bar]");
  const batchCount = document.querySelector("[data-batch-count]");

  function updateBatchBar() {
    if (!multiForm || !batchBar) return;
    const checked = multiForm.querySelectorAll('input[name="service_ids"]:checked').length;
    batchCount.textContent = checked;
    batchBar.hidden = checked === 0;
  }

  if (multiForm) {
    multiForm.addEventListener("change", (event) => {
      if (event.target.name === "service_ids") updateBatchBar();
    });
    updateBatchBar();
  }
})();
