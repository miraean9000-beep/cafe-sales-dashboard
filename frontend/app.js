const $ = id => document.getElementById(id);
const cash = new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"});
const money = value => value == null ? "—" : cash.format(value);
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
const action = (text, run) => {
  const button = el("button", text, "secondary");
  button.type = "button";
  button.onclick = () => perform(run, button);
  return button;
};
import "./config.js";
const base = globalThis.API_BASE_URL || "";
let token = sessionStorage.getItem("wonder-token:" + base) || "";
let messages = [], sales = [], editing = null, chatting = false;
const notice = text => { $("notice").textContent = text; };

async function api(path, method = "GET", body) {
  const headers = {};
  if (token) headers.Authorization = "Bearer " + token;
  if (body) headers["Content-Type"] = "application/json";
  const response = await fetch(base + "/api" + path, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(120000),
  });
  if (!response.ok) {
    const {detail} = await response.json().catch(() => ({}));
    if (response.status === 401 && !$("access-dialog").open) openAccess();
    throw new Error(typeof detail === "string" ? detail : "요청에 실패했습니다 (" + response.status + ").");
  }
  return response.status === 204 ? null : response.json();
}

async function perform(run, button) {
  if (button) button.disabled = true;
  notice("");
  try {
    await run();
  } catch (error) {
    notice(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

function openAccess() {
  $("token").value = token;
  $("access-dialog").showModal();
}
$("access").onclick = openAccess;
$("close-dialog").onclick = () => $("access-dialog").close();
$("access-form").onsubmit = event => {
  event.preventDefault();
  token = $("token").value.trim();
  sessionStorage.setItem("wonder-token:" + base, token);
  $("access-dialog").close();
  perform(load);
};

function select(name) {
  for (const view of ["chat", "sales", "history"]) $(view).hidden = view !== name;
  document.querySelectorAll("[data-view]").forEach(button => {
    button.setAttribute("aria-pressed", button.dataset.view === name);
  });
}
document.querySelectorAll("[data-view]").forEach(button => {
  button.onclick = () => {
    select(button.dataset.view);
    if (button.dataset.view === "history") perform(refreshHistory);
  };
});

function renderMessages() {
  const nodes = messages.map(({role, content}) => {
    const message = el("div", null, "message " + role);
    message.append(el("strong", role === "user" ? "나" : "매출 비서"), document.createTextNode(content));
    return message;
  });
  if (!nodes.length) nodes.push(el("p", "최근 매출 추세나 최고 매출일을 물어보세요."));
  $("messages").replaceChildren(...nodes);
  $("messages").scrollTop = $("messages").scrollHeight;
}
$("new-chat").onclick = () => {
  messages = [];
  renderMessages();
  $("prompt").focus();
};
$("suggest").onclick = () => {
  $("prompt").value = "기록상 최근 7일 매출을 직전 7일과 비교해 줘.";
  $("prompt").focus();
};
$("question").onsubmit = event => {
  event.preventDefault();
  const question = $("prompt").value.trim();
  if (!question || chatting) return;
  if (messages.length >= 60) {
    notice("30회 답변을 받았습니다. 새 대화를 열어 주세요.");
    return;
  }
  perform(async () => {
    const previous = messages;
    messages = [...messages, {role:"user", content:question}];
    $("prompt").value = "";
    renderMessages();
    chatting = true;
    $("waiting").hidden = false;
    $("new-chat").disabled = true;
    try {
      const reply = await api("/chat", "POST", {messages});
      messages = reply.conversation.messages;
      notice("답변과 대화를 저장했습니다.");
    } catch (error) {
      messages = previous;
      if (!$("prompt").value) $("prompt").value = question;
      throw error;
    } finally {
      chatting = false;
      $("waiting").hidden = true;
      $("new-chat").disabled = false;
      renderMessages();
    }
  }, $("send"));
};

function renderChart(data) {
  const points = data.slice(-30);
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, 640, 260);
  $("chart-period").textContent = points.length ? points[0].date + " ~ " + points.at(-1).date : "표시할 매출 기록이 없습니다.";
  if (!points.length) return;
  const maximum = Math.max(1, ...points.map(point => point.value));
  ctx.font = "16px sans-serif";
  for (let step = 0; step <= 4; step++) {
    const y = 225 - step * 50;
    ctx.beginPath();
    ctx.strokeStyle = "#dedacf";
    ctx.moveTo(100, y);
    ctx.lineTo(630, y);
    ctx.stroke();
    ctx.fillStyle = "#6e6c60";
    ctx.fillText("$" + Math.round(maximum * step / 4).toLocaleString(), 4, y + 5);
  }
  ctx.beginPath();
  points.forEach((point, index) => {
    const x = 105 + 515 * index / Math.max(1, points.length - 1);
    const y = 225 - 200 * point.value / maximum;
    if (index) ctx.lineTo(x, y); else ctx.moveTo(x, y);
  });
  ctx.strokeStyle = "#304a38";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.lineWidth = 1;
  if (points.length === 1) {
    ctx.fillStyle = "#304a38";
    ctx.fillRect(103, 223 - 200 * points[0].value / maximum, 5, 5);
  }
}
function renderSummary(summary) {
  $("period").textContent = summary.count ? summary.start + " ~ " + summary.end + " · " + summary.count + "일 기록 · USD" : "매출 기록이 없습니다.";
  const metrics = [
    ["총매출", money(summary.total), "전체 기록 기간"],
    ["일평균", money(summary.average), "기록이 있는 날짜 기준"],
    ["최고 일매출", money(summary.maximum), summary.peak_date || "—"],
    ["최근 7일 추세", summary.change_percent == null ? summary.trend :
      new Intl.NumberFormat("ko-KR", {style:"percent", maximumFractionDigits:2, signDisplay:"exceptZero"}).format(summary.change_percent / 100),
      "직전 7일 대비"],
  ];
  $("metrics").replaceChildren(...metrics.map(([title, value, detail]) => {
    const card = el("div", null, "metric");
    card.append(el("span", title), el("strong", value), el("small", detail));
    return card;
  }));
  renderChart(summary.series);
}

function resetSale() {
  editing = null;
  $("sale-form").reset();
  $("save-sale").textContent = "추가";
  $("cancel").hidden = true;
}
$("cancel").onclick = resetSale;

async function refreshSales() {
  const [records, summary] = await Promise.all([api("/data"), api("/data/summary")]);
  sales = records;
  $("rows").replaceChildren(...sales.map(row => {
    const tr = el("tr");
    const controls = el("td");
    controls.append(action("수정", () => {
      editing = row.id;
      $("date").value = row.date;
      $("value").value = row.value;
      $("memo").value = row.memo;
      $("save-sale").textContent = "수정 저장";
      $("cancel").hidden = false;
      $("date").focus();
    }), action("삭제", async () => {
      if (!confirm(row.date + " 매출 기록을 삭제할까요?")) return;
      await api("/data/" + row.id, "DELETE");
      if (editing === row.id) resetSale();
      await refreshSales();
      notice("매출 기록을 삭제했습니다.");
    }));
    tr.append(el("td", row.date), el("td", money(row.value)), el("td", row.memo), controls);
    return tr;
  }));
  renderSummary(summary);
}
$("sale-form").onsubmit = event => {
  event.preventDefault();
  perform(async () => {
    await api(editing ? "/data/" + editing : "/data", editing ? "PUT" : "POST", {
      date:$("date").value, value:$("value").valueAsNumber, memo:$("memo").value,
    });
    resetSale();
    await refreshSales();
    notice("매출 기록을 저장했습니다.");
  }, $("save-sale"));
};
$("export").onclick = () => {
  const csv = ["date,value,memo", ...sales.map(row => {
    const memo = /^[\s]*[=+@-]|^[\t\r\n]/.test(row.memo) ? "'" + row.memo : row.memo;
    return [row.date, row.value.toFixed(2), '"' + memo.replaceAll('"', '""') + '"'].join(",");
  })].join("\r\n");
  const url = URL.createObjectURL(new Blob(["\ufeff", csv], {type:"text/csv;charset=utf-8"}));
  const link = el("a");
  link.href = url;
  link.download = "daily-sales.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

async function refreshHistory() {
  const history = await api("/conversations");
  $("history-list").replaceChildren(...history.map(row => {
    const item = el("li");
    const date = new Date(row.created_at).toLocaleString("ko-KR");
    item.append(action(row.title + " · " + date, async () => {
      if (chatting) throw new Error("현재 답변이 완료된 후 불러와 주세요.");
      const record = await api("/conversations/" + row.id);
      if (chatting) return;
      messages = record.messages;
      $("prompt").value = "";
      renderMessages();
      select("chat");
      notice("저장된 대화를 불러왔습니다.");
    }), action("삭제", async () => {
      if (!confirm("이 대화 기록을 삭제할까요?")) return;
      await api("/conversations/" + row.id, "DELETE");
      await refreshHistory();
      notice("대화 기록을 삭제했습니다.");
    }));
    return item;
  }));
  if (!history.length) $("history-list").append(el("li", "저장된 대화가 없습니다."));
}

async function load() {
  if (globalThis.WONDER_DEPLOYED && !base) {
    $("period").textContent = "매출 서버 연결 대기 중";
    notice("Render 백엔드가 연결되면 매출 조회와 채팅을 사용할 수 있습니다.");
    for (const button of document.querySelectorAll("button:not([data-view=chat])")) button.disabled = true;
    return;
  }
  const mode = await api("/status");
  $("mode").textContent = mode.ai ? "Claude 연결 설정됨" : mode.storage === "sqlite" ? "로컬 데모 · 정해진 요약 답변" : "Claude 설정 필요";
  await refreshSales();
  if (!$("history").hidden) await refreshHistory();
}
renderMessages();
perform(load);
