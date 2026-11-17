(function () {
  "use strict";
  const API = "/api/v1";
  const $ = (id) => document.getElementById(id);

  const els = {
    prompt: $("prompt"), enhance: $("enhance"), resolution: $("resolution"),
    duration: $("duration"), generateBtn: $("generateBtn"),
    statusBox: $("statusBox"), statusText: $("statusText"),
    statusPct: $("statusPct"), progressBar: $("progressBar"),
    errorBox: $("errorBox"), resultCard: $("resultCard"),
    resultVideo: $("resultVideo"), downloadBtn: $("downloadBtn"),
    regenBtn: $("regenBtn"), historyList: $("historyList"),
    historyCount: $("historyCount"),
  };

  const STATUS_LABEL = { queued: "排队中…", processing: "生成中…", succeeded: "完成", failed: "失败" };

  async function api(path, options) {
    const resp = await fetch(API + path, options);
    if (!resp.ok) {
      let msg = "请求失败 (" + resp.status + ")";
      try { const e = await resp.json(); msg = e.message || msg; } catch (_) {}
      throw new Error(msg);
    }
    if (resp.status === 204) return null;
    return resp.json();
  }

  function showError(msg) {
    els.errorBox.textContent = msg;
    els.errorBox.classList.remove("hidden");
  }
  function clearError() { els.errorBox.classList.add("hidden"); }

  function showStatus(status, progress) {
    els.statusBox.classList.remove("hidden");
    els.statusText.textContent = STATUS_LABEL[status] || status;
    const pct = Math.max(0, Math.min(100, progress || 0));
    els.statusPct.textContent = pct + "%";
    els.progressBar.style.width = pct + "%";
  }

  function showResult(task) {
    els.resultCard.classList.remove("hidden");
    if (task.video_url) {
      els.resultVideo.src = task.video_url;
      els.downloadBtn.href = task.video_url;
    }
  }

  async function poll(taskId) {
    for (;;) {
      const task = await api("/generations/" + taskId);
      showStatus(task.status, task.progress);
      if (task.status === "succeeded") {
        showResult(task);
        clearError();
        els.generateBtn.disabled = false;
        els.generateBtn.textContent = "生成视频";
        loadHistory();
        return;
      }
      if (task.status === "failed") {
        const detail = task.error && (task.error.message || task.error.code) || "生成失败";
        showError("生成失败：" + detail);
        els.generateBtn.disabled = false;
        els.generateBtn.textContent = "重新生成";
        loadHistory();
        return;
      }
      await new Promise((r) => setTimeout(r, 1200));
    }
  }

  async function generate() {
    clearError();
    const prompt = els.prompt.value.trim();
    if (!prompt) { showError("请先输入视频描述"); return; }
    els.generateBtn.disabled = true;
    els.generateBtn.textContent = "提交中…";
    els.resultCard.classList.add("hidden");
    try {
      const body = {
        prompt: prompt,
        enhance: els.enhance.checked,
        resolution: els.resolution.value,
        duration: parseInt(els.duration.value, 10),
      };
      const created = await api("/generations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      showStatus("queued", 0);
      await poll(created.task_id);
    } catch (e) {
      showError(e.message);
      els.generateBtn.disabled = false;
      els.generateBtn.textContent = "生成视频";
    }
  }

  async function loadHistory() {
    try {
      const data = await api("/generations?page=1&page_size=20");
      els.historyCount.textContent = data.total;
      if (!data.items.length) {
        els.historyList.innerHTML = '<div class="empty">还没有记录，先生成一个吧</div>';
        return;
      }
      els.historyList.innerHTML = data.items.map(function (t) {
        const badge = '<span class="badge ' + t.status + '">' + (STATUS_LABEL[t.status] || t.status) + "</span>";
        const cover = t.cover_url
          ? '<img class="thumb" src="' + t.cover_url + '" alt="" />'
          : '<div class="thumb"></div>';
        const canPlay = t.status === "succeeded" && t.video_url
          ? ' data-video="' + t.video_url + '" style="cursor:pointer"' : "";
        return '<div class="history-item"' + canPlay + '>' + cover +
          '<div class="hi-body"><div class="hi-prompt">' + escapeHtml(t.prompt) + "</div>" +
          '<div class="hi-meta">' + (t.created_at || "").replace("T", " ").replace("Z", "") + " · " + badge + "</div></div>" +
          '<button class="del" data-del="' + t.id + '" title="删除">×</button></div>';
      }).join("");
    } catch (e) { /* keep quiet on history load failure */ }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  els.generateBtn.addEventListener("click", generate);
  els.regenBtn.addEventListener("click", function () {
    els.resultCard.classList.add("hidden");
    els.prompt.focus();
  });
  els.historyList.addEventListener("click", async function (e) {
    const del = e.target.getAttribute("data-del");
    if (del) {
      try { await api("/generations/" + del, { method: "DELETE" }); loadHistory(); }
      catch (err) { showError(err.message); }
      return;
    }
    const item = e.target.closest("[data-video]");
    if (item) {
      els.resultVideo.src = item.getAttribute("data-video");
      els.downloadBtn.href = item.getAttribute("data-video");
      els.resultCard.classList.remove("hidden");
      els.resultCard.scrollIntoView({ behavior: "smooth" });
    }
  });

  loadHistory();
})();
