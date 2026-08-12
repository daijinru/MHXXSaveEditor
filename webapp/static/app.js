/* MHXX AI Research Studio — 前端逻辑(原生 JS,无依赖) */
"use strict";

const $ = (sel) => document.querySelector(sel);

let offsets = [];
let constants = {};
let hexOffset = 0;
let hexLength = 0x200;
let changedBytes = new Set(); // 相对磁盘的修改偏移

const api = {
  async get(path) {
    const r = await fetch(path);
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `GET ${path} 失败 (${r.status})`);
    return data;
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `POST ${path} 失败 (${r.status})`);
    return data;
  },
};

/* ============ 状态栏 ============ */
async function refreshStatus() {
  try {
    const s = await api.get("/api/save/status");
    const el = $("#saveStatus");
    if (s.loaded) {
      el.textContent = `已加载 (${(s.size / 1048576).toFixed(2)} MB)${s.path ? " · " + s.path.split(/[\\/]/).pop() : ""}`;
      el.className = "status loaded";
    } else {
      el.textContent = "未加载";
      el.className = "status";
    }
    return s;
  } catch (e) {
    $("#saveStatus").textContent = "服务异常: " + e.message;
    $("#saveStatus").className = "status error";
    return { loaded: false };
  }
}

/* ============ 偏移表 ============ */
async function loadOffsets() {
  try {
    offsets = await api.get("/api/offsets");
    renderOffsets(offsets);
  } catch (e) {
    $("#offsetList").innerHTML = `<div class="hint">偏移表加载失败: ${e.message}</div>`;
  }
}
function renderOffsets(list) {
  const box = $("#offsetList");
  box.innerHTML = "";
  for (const o of list) {
    const el = document.createElement("div");
    el.className = "offset-item";
    el.dataset.offset = o.offset;
    const desc = o.comment ? `<div class="desc">${escapeHtml(o.comment)}</div>` : "";
    el.innerHTML = `
      <div style="flex:1;min-width:0">
        <div style="display:flex;justify-content:space-between;gap:6px">
          <span class="name">${escapeHtml(o.name)}</span>
          <span class="addr">0x${o.offset.toString(16).toUpperCase().padStart(2, "0")}</span>
        </div>${desc}
      </div>`;
    el.addEventListener("click", () => {
      gotoOffset(o.offset);
      document.querySelectorAll(".offset-item").forEach(x => x.classList.remove("active"));
      el.classList.add("active");
    });
    box.appendChild(el);
  }
}
$("#offsetSearch").addEventListener("input", (e) => {
  const kw = e.target.value.toLowerCase();
  renderOffsets(offsets.filter(o =>
    o.name.toLowerCase().includes(kw) || o.comment.toLowerCase().includes(kw)));
});

/* ============ 常量表 ============ */
async function loadConstTables() {
  try {
    const list = await api.get("/api/constants");
    renderConstList(list);
  } catch (e) {
    $("#constList").innerHTML = `<div class="hint">常量表加载失败: ${e.message}</div>`;
  }
}
function renderConstList(list) {
  const box = $("#constList");
  box.innerHTML = "";
  for (const t of list) {
    const el = document.createElement("div");
    el.className = "const-item";
    el.textContent = `${t.name} (${t.count})`;
    el.addEventListener("click", () => showConstTable(t.name));
    box.appendChild(el);
  }
}
$("#constSearch").addEventListener("input", async (e) => {
  const kw = e.target.value.toLowerCase();
  if (!kw) { loadConstTables(); return; }
  const list = await api.get("/api/constants");
  renderConstList(list.filter(t => t.name.toLowerCase().includes(kw)));
});
async function showConstTable(name) {
  const { values } = await api.get("/api/constants/" + name);
  const rows = values.map((v, i) => `<tr><td>${i}</td><td>${escapeHtml(String(v))}</td></tr>`).join("");
  $("#constList").innerHTML = `
    <div style="display:flex;justify-content:space-between;padding:4px">
      <b style="font-family:var(--mono);font-size:11px">${name}</b>
      <button class="btn small" id="constBack">← 返回</button>
    </div>
    <table style="width:100%;border-collapse:collapse">
      <tr><th style="text-align:left;width:50px">ID</th><th style="text-align:left">名称</th></tr>${rows}
    </table>`;
  $("#constBack").addEventListener("click", loadConstTables);
  // 表头渲染样式
  const style = document.createElement("style");
  style.textContent = "#constList table{border-collapse:collapse;width:100%;font-size:11px;font-family:var(--mono)} #constList td,#constList th{border:1px solid var(--border);padding:2px 6px}";
  boxstyle(style);
}
function boxstyle(s) { document.head.appendChild(s); }

/* ============ Hex 查看器 ============ */
async function loadHex() {
  const s = await refreshStatus();
  if (!s.loaded) { $("#hexView").innerHTML = `<div class="hint">请先打开存档文件</div>`; return; }
  try {
    const data = await api.get(`/api/save/hex?offset=${hexOffset}&length=${hexLength}`);
    renderHex(data);
  } catch (e) {
    $("#hexView").innerHTML = `<div class="hint">${escapeHtml(e.message)}</div>`;
  }
}
function renderHex(data) {
  $("#hexInfo").textContent = `偏移 0x${data.offset.toString(16).toUpperCase()} ~ 0x${(data.offset + data.length).toString(16).toUpperCase()}`;
  const box = $("#hexView");
  box.innerHTML = "";
  for (const row of data.rows) {
    const div = document.createElement("div");
    div.className = "hex-row";
    const bytes = row.hex.split(" ").map((b, i) => {
      const off = row.addr + i;
      const cls = changedBytes.has(off) ? "hex-byte changed" : "hex-byte";
      return `<span class="${cls}" data-offset="${off}" data-val="${b}">${b}</span>`;
    }).join(" ");
    div.innerHTML = `<span class="hex-addr">0x${row.addr.toString(16).toUpperCase().padStart(8, "0")}</span>
      <span class="hex-bytes">${bytes}</span>
      <span class="hex-ascii">${escapeHtml(row.ascii)}</span>`;
    box.appendChild(div);
  }
}
// 点击字节 = 打 1 字节补丁(改为 FF,方便快速实验)
$("#hexView").addEventListener("click", async (e) => {
  const t = e.target.closest(".hex-byte");
  if (!t) return;
  const off = parseInt(t.dataset.offset, 10);
  const oldVal = t.dataset.val;
  if (!confirm(`将偏移 0x${off.toString(16).toUpperCase()} 的字节 ${oldVal} 改为 FF?`)) return;
  try {
    await api.post("/api/save/patch", { offset: off, hex: "FF" });
    changedBytes.add(off);
    loadHex();
  } catch (err) { alert(err.message); }
});

function gotoOffset(off) {
  hexOffset = Math.max(0, off - (off % 16));
  $("#gotoOffset").value = "0x" + off.toString(16);
  loadHex();
}
$("#btnGoto").addEventListener("click", () => {
  const v = parseInt($("#gotoOffset").value, 0);
  if (!isNaN(v)) gotoOffset(v);
});
$("#gotoOffset").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#btnGoto").click(); });
$("#btnRefresh").addEventListener("click", () => {
  hexLength = parseInt($("#viewLength").value, 0) || 0x200;
  loadHex();
});
$("#btnPatch").addEventListener("click", async () => {
  const off = parseInt($("#patchOffset").value, 0);
  const hex = $("#patchHex").value.trim();
  if (isNaN(off) || !hex) { alert("请输入偏移和 hex 字节"); return; }
  try {
    const r = await api.post("/api/save/patch", { offset: off, hex });
    for (let i = 0; i < r.length; i++) changedBytes.add(off + i);
    alert(`已打补丁: 0x${r.old_hex} → 0x${r.new_hex} @ 0x${off.toString(16).toUpperCase()}`);
    loadHex();
  } catch (e) { alert(e.message); }
});
$("#btnDiff").addEventListener("click", async () => {
  const s = await refreshStatus();
  if (!s.loaded) return;
  const data = await api.get(`/api/save/diff?offset=0&length=${s.size}`);
  changedBytes = new Set(data.changes.map(c => c.offset));
  alert(`与磁盘对比: ${data.count} 处修改\n(绿色/黄色高亮 = 已修改字节)`);
  loadHex();
});

/* ============ 数值解析 ============ */
$("#btnParse").addEventListener("click", async () => {
  const off = parseInt($("#parseOffset").value, 0);
  const type = $("#parseType").value;
  if (isNaN(off)) { alert("请输入偏移"); return; }
  try {
    const n = { u8: 1, u16: 2, u32: 4, i32: 4, float: 4, str: 32 }[type];
    const { bytes } = await api.get(`/api/save/bytes?offset=${off}&length=${n}`);
    let out = "";
    const hex = bytes.map(b => b.toString(16).toUpperCase().padStart(2, "0")).join(" ");
    if (type === "u8") out = bytes[0];
    else if (type === "u16") out = bytes[0] | (bytes[1] << 8);
    else if (type === "u32") out = (bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24)) >>> 0;
    else if (type === "i32") out = (bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24));
    else if (type === "float") { const buf = new ArrayBuffer(4); new Uint8Array(buf).set(bytes); out = new Float32Array(buf)[0]; }
    else out = String.fromCharCode(...bytes.filter(b => b >= 32 && b < 127));
    const el = $("#parseResult");
    el.innerHTML = `<b>0x${off.toString(16).toUpperCase()}</b> [${type}]<br>hex: ${hex}<br>值: <b style="color:var(--accent)">${escapeHtml(String(out))}</b>`;
  } catch (e) { alert(e.message); }
});

/* ============ 实验记录 ============ */
async function loadExperiments() {
  try {
    const { experiments } = await api.get("/api/experiments");
    const box = $("#expList");
    if (!experiments.length) { box.innerHTML = `<div class="hint">暂无实验</div>`; return; }
    box.innerHTML = "";
    for (const e of experiments) {
      const el = document.createElement("div");
      el.className = "exp-item";
      el.innerHTML = `<div class="t">${escapeHtml(e.title)}</div><div class="m">${e.modified}</div>`;
      el.addEventListener("click", () => {
        window.open(`/api/experiments/${e.file}`, "_blank");
      });
      box.appendChild(el);
    }
  } catch (e) { /* 忽略 */ }
}
$("#btnNewExp").addEventListener("click", () => { $("#expModal").hidden = false; });
$("#btnExpCancel").addEventListener("click", () => { $("#expModal").hidden = true; });
$("#btnExpSubmit").addEventListener("click", async () => {
  const body = {
    title: $("#expTitle").value,
    hypothesis: $("#expHypo").value,
    method: $("#expMethod").value,
    evidence: $("#expEvidence").value,
    conclusion: $("#expConcl").value,
  };
  if (!body.title) { alert("请输入标题"); return; }
  try {
    await api.post("/api/experiment", body);
    $("#expModal").hidden = true;
    ["expTitle", "expHypo", "expMethod", "expEvidence", "expConcl"].forEach(id => $("#" + id).value = "");
    loadExperiments();
    alert("实验记录已创建");
  } catch (e) { alert(e.message); }
});

/* ============ 知识库 ============ */
async function loadKnowledge() {
  try {
    const md = await fetch("/api/knowledge/known-offsets").then(r => r.text());
    $("#knowledgeBox").innerHTML = renderMarkdown(md);
  } catch (e) {
    $("#knowledgeBox").innerHTML = `<div class="hint">知识库加载失败: ${e.message}</div>`;
  }
}
function renderMarkdown(md) {
  // 极简 markdown 渲染:标题/表格/代码/段落
  const lines = md.split("\n");
  let html = "", inTable = false, inCode = false;
  const tableRows = [];
  for (const line of lines) {
    if (line.startsWith("```")) {
      inCode = !inCode;
      html += inCode ? "<pre>" : "</pre>";
      continue;
    }
    if (inCode) { html += escapeHtml(line) + "\n"; continue; }
    if (line.startsWith("|")) {
      tableRows.push(line);
      continue;
    }
    if (tableRows.length) { html += renderTable(tableRows); tableRows.length = 0; }
    if (/^# /.test(line)) html += `<h3>${escapeHtml(line.slice(2))}</h3>`;
    else if (/^## /.test(line)) html += `<h4>${escapeHtml(line.slice(3))}</h4>`;
    else if (/^>/.test(line)) html += `<div style="color:var(--muted);border-left:3px solid var(--border);padding-left:8px;margin:4px 0">${escapeHtml(line.slice(1))}</div>`;
    else if (line.trim()) html += `<p>${escapeHtml(line)}</p>`;
  }
  if (tableRows.length) html += renderTable(tableRows);
  return html;
}
function renderTable(rows) {
  const cells = rows.map(r => r.split("|").slice(1, -1).map(c => `<td>${escapeHtml(c.trim())}</td>`).join(""));
  return `<table>${cells.join("</tr><tr>")}</table>`;
}
function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ============ 文件加载 / 保存 ============ */
$("#fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const buf = new Uint8Array(await file.arrayBuffer());
  let b64 = "";
  const CH = 0x8000;
  for (let i = 0; i < buf.length; i += CH) {
    b64 += String.fromCharCode(...buf.subarray(i, i + CH));
  }
  b64 = btoa(b64);
  try {
    const r = await api.post("/api/save/upload", { name: file.name, data_b64: b64 });
    changedBytes.clear();
    alert(`存档已加载: ${r.slots.length} 个角色槽位 (${r.size.toLocaleString()} 字节)`);
    loadHex(); loadExperiments();
  } catch (err) { alert(err.message); refreshStatus(); }
  e.target.value = "";
});

$("#btnSave").addEventListener("click", async () => {
  try {
    const r = await api.post("/api/save/write", {});
    changedBytes.clear();
    alert(`已保存到:\n${r.path}`);
    loadHex();
  } catch (e) { alert(e.message); }
});

/* ============ 初始化 ============ */
(async function init() {
  await refreshStatus();
  loadOffsets();
  loadConstTables();
  loadHex();
  loadExperiments();
  loadKnowledge();
})();
