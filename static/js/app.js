const API = "/api/trades";
let currentStatus = "";
let searchTerm = "";

const el = (id) => document.getElementById(id);

// ---------- Yükləmə ----------
async function loadStats() {
  const r = await fetch("/api/stats");
  const s = await r.json();
  const pnl = s.total_pnl || 0;
  const pnlEl = el("statPnl");
  pnlEl.textContent = (pnl >= 0 ? "+" : "") + pnl.toLocaleString();
  pnlEl.style.color = pnl > 0 ? "var(--green)" : pnl < 0 ? "var(--red)" : "var(--text)";
  el("statWin").textContent = s.win_rate + "%";
  el("statCounts").textContent = `${s.closed_trades} / ${s.open_trades}`;
  el("statPf").textContent = s.profit_factor != null ? s.profit_factor : "—";
}

async function loadTrades() {
  const params = new URLSearchParams();
  if (currentStatus) params.set("status", currentStatus);
  if (searchTerm) params.set("symbol", searchTerm);
  const r = await fetch(`${API}?${params}`);
  const trades = await r.json();
  renderTrades(trades);
  loadStats();
}

function fmt(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 8 });
}

function renderTrades(trades) {
  const list = el("tradesList");
  const empty = el("emptyState");
  list.innerHTML = "";
  if (!trades.length) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  trades.forEach((t) => {
    const card = document.createElement("div");
    card.className = "trade-card";

    const img = t.has_image
      ? `<img class="trade-img" src="${API}/${t.id}/image" alt="chart" onclick="openLightbox('${API}/${t.id}/image')" />`
      : `<div class="trade-img no-img"></div>`;

    let pnlBlock = "";
    if (t.status === "CLOSED" && t.pnl !== null) {
      const cls = t.pnl >= 0 ? "pos" : "neg";
      const sign = t.pnl >= 0 ? "+" : "";
      pnlBlock = `<div class="pnl-row">
        <span class="pnl ${cls}">${sign}${fmt(t.pnl)}</span>
        <span class="pnl-pct ${cls}">${sign}${t.pnl_pct}%</span>
      </div>`;
    } else {
      pnlBlock = `<div class="pnl-row"><span class="pnl" style="color:var(--yellow);font-size:15px">Açıq pozisiya</span></div>`;
    }

    card.innerHTML = `
      ${img}
      <div class="trade-body">
        <div class="trade-top">
          <div class="sym-wrap">
            <span class="sym">${t.symbol}</span>
            <span class="dir ${t.direction}">${t.direction}</span>
          </div>
          <span class="badge ${t.status}">${t.status === "OPEN" ? "AÇIQ" : "BAĞLI"}</span>
        </div>
        <div class="trade-rows">
          <span class="k">Giriş</span><span class="v">${fmt(t.entry_price)}</span>
          <span class="k">Çıxış</span><span class="v">${fmt(t.exit_price)}</span>
          <span class="k">Həcm</span><span class="v">${fmt(t.quantity)}</span>
          <span class="k">Tarix</span><span class="v">${t.trade_date ? t.trade_date.slice(0, 10) : "—"}</span>
        </div>
        ${pnlBlock}
        ${t.strategy ? `<div class="strategy-tag"># ${t.strategy}</div>` : ""}
        ${t.notes ? `<div class="notes">${escapeHtml(t.notes)}</div>` : ""}
        <div class="card-actions">
          <button class="btn btn-ghost small" onclick="editTrade(${t.id})">Düzəliş</button>
          <button class="btn btn-ghost small" onclick="deleteTrade(${t.id})">Sil</button>
        </div>
      </div>`;
    list.appendChild(card);
  });
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- Modal ----------
function openModal(title = "Yeni Trade") {
  el("modalTitle").textContent = title;
  el("modal").classList.remove("hidden");
}
function closeModal() {
  el("modal").classList.add("hidden");
  el("tradeForm").reset();
  el("tradeId").value = "";
  el("imagePreviewWrap").classList.add("hidden");
  el("imagePreview").src = "";
}

el("openFormBtn").onclick = () => {
  closeModal();
  // bugünkü tarixi default qoy
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  el("trade_date").value = now.toISOString().slice(0, 16);
  openModal("Yeni Trade");
};
el("closeModal").onclick = closeModal;
el("cancelBtn").onclick = closeModal;
el("modal").onclick = (e) => { if (e.target === el("modal")) closeModal(); };

// Şəkil preview
el("image").onchange = (e) => {
  const f = e.target.files[0];
  if (f) {
    el("imagePreview").src = URL.createObjectURL(f);
    el("imagePreviewWrap").classList.remove("hidden");
  }
};
el("removeImageBtn").onclick = () => {
  el("image").value = "";
  el("imagePreview").src = "";
  el("imagePreviewWrap").classList.add("hidden");
  el("tradeForm").dataset.removeImage = "true";
};

// ---------- Submit ----------
el("tradeForm").onsubmit = async (e) => {
  e.preventDefault();
  const id = el("tradeId").value;
  const fd = new FormData(el("tradeForm"));
  if (el("tradeForm").dataset.removeImage === "true" && !el("image").files.length) {
    fd.set("remove_image", "true");
  }
  const url = id ? `${API}/${id}` : API;
  el("saveBtn").disabled = true;
  el("saveBtn").textContent = "Saxlanılır...";
  try {
    const r = await fetch(url, { method: "POST", body: fd });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      alert("Xəta: " + (err.error || r.status));
    } else {
      closeModal();
      loadTrades();
    }
  } finally {
    el("saveBtn").disabled = false;
    el("saveBtn").textContent = "Yadda saxla";
    delete el("tradeForm").dataset.removeImage;
  }
};

// ---------- Edit / Delete ----------
async function editTrade(id) {
  const r = await fetch(`${API}/${id}`);
  const t = await r.json();
  closeModal();
  el("tradeId").value = t.id;
  el("symbol").value = t.symbol;
  el("direction").value = t.direction;
  el("entry_price").value = t.entry_price;
  el("exit_price").value = t.exit_price ?? "";
  el("quantity").value = t.quantity;
  el("status").value = t.status;
  el("strategy").value = t.strategy ?? "";
  el("notes").value = t.notes ?? "";
  if (t.trade_date) el("trade_date").value = t.trade_date.slice(0, 16);
  if (t.has_image) {
    el("imagePreview").src = `${API}/${id}/image`;
    el("imagePreviewWrap").classList.remove("hidden");
  }
  openModal("Trade-i düzəlt");
}

async function deleteTrade(id) {
  if (!confirm("Bu trade silinsin?")) return;
  await fetch(`${API}/${id}`, { method: "DELETE" });
  loadTrades();
}

// ---------- Lightbox ----------
function openLightbox(src) {
  el("lightboxImg").src = src;
  el("lightbox").classList.remove("hidden");
}
el("lightbox").onclick = () => el("lightbox").classList.add("hidden");

// ---------- Filtrlər ----------
document.querySelectorAll(".chip").forEach((c) => {
  c.onclick = () => {
    document.querySelectorAll(".chip").forEach((x) => x.classList.remove("active"));
    c.classList.add("active");
    currentStatus = c.dataset.status;
    loadTrades();
  };
});
let searchTimer;
el("searchInput").oninput = (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { searchTerm = e.target.value; loadTrades(); }, 300);
};

// ---------- Başlat ----------
loadTrades();
