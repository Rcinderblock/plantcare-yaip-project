const API_BASE = "/api";
const state = {
  user: null,
  species: [],
  plants: [],
  tasks: [],
  logs: [],
  collections: [],
  stats: null,
  authMode: "login",
  pendingSpeciesId: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const STAT_CARDS = [
  {
    key: "users",
    label: "садоводов с нами",
  },
  {
    key: "plants",
    label: "растений под уходом",
  },
  {
    key: "care_logs",
    label: "записей ухода",
  },
  {
    key: "species",
    label: "видов в каталоге",
  },
];

const TASK_LABELS = {
  water: "Полив",
  fertilize: "Удобрение",
  repot: "Пересадка",
  prune: "Обрезка",
};

const LOCATION_LABELS = {
  indoor: "Комната",
  balcony: "Балкон",
};

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);

const formatDate = (value) => {
  if (!value) return "не указано";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
};

const todayIso = () => new Date().toISOString().slice(0, 10);
const truncateText = (value, maxLength) => {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength).trim()}…` : text;
};

function showMessage(id, text, isError = false) {
  const node = document.getElementById(id);
  if (!node) return;
  node.textContent = text || "";
  node.classList.toggle("error", Boolean(isError));
}

function collectApiMessages(value, prefix = "") {
  if (!value) return [];
  if (typeof value === "string") return [prefix ? `${prefix}: ${value}` : value];
  if (Array.isArray(value)) return value.flatMap((item) => collectApiMessages(item, prefix));
  if (typeof value === "object") {
    return Object.entries(value).flatMap(([key, nested]) => collectApiMessages(nested, key));
  }
  return [String(value)];
}

function formatApiError(payload, status) {
  const messages = collectApiMessages(payload);
  return messages.length ? messages.join("; ") : `Ошибка HTTP ${status}`;
}

function normalizeApiPath(path) {
  if (!path) return path;
  if (path.startsWith("http")) {
    const url = new URL(path);
    return `${url.pathname.replace(/^\/api/, "")}${url.search}`;
  }
  return path.replace(/^\/api/, "");
}

async function api(path, options = {}, retry = true) {
  const normalizedPath = normalizeApiPath(path);
  const headers = new Headers(options.headers || {});
  let body = options.body;

  if (body && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${normalizedPath}`, {
    ...options,
    body,
    headers,
    credentials: "include",
  });
  const text = await response.text();
  const contentType = response.headers.get("content-type") || "";
  const payload = text && contentType.includes("application/json") ? JSON.parse(text) : text;

  const canRefresh =
    response.status === 401 &&
    retry &&
    !normalizedPath.startsWith("/auth/token/") &&
    normalizedPath !== "/auth/register/";

  if (canRefresh) {
    await refreshSession();
    return api(normalizedPath, options, false);
  }

  if (!response.ok) {
    throw new Error(formatApiError(payload, response.status));
  }

  return payload;
}

async function refreshSession() {
  const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    state.user = null;
    renderSession();
    throw new Error("Сессия истекла, войдите заново.");
  }
}

async function fetchAll(path) {
  const items = [];
  let url = path;
  while (url) {
    const data = await api(url);
    if (Array.isArray(data)) return data;
    items.push(...data.results);
    url = data.next;
  }
  return items;
}

function setActivePage(page) {
  const privatePages = new Set(["plants", "calendar", "profile"]);
  const nextPage = privatePages.has(page) && !state.user ? "auth" : page;
  const hero = $("#hero-section");
  if (hero) hero.hidden = nextPage !== "dashboard";
  $$(".page").forEach((node) => node.classList.toggle("active", node.id === `${nextPage}-page`));
  $$("[data-nav]").forEach((node) => node.classList.toggle("active", node.dataset.nav === nextPage));
  history.replaceState(null, "", `#${nextPage}`);
  return nextPage;
}

function setAuthMode(mode) {
  state.authMode = mode === "register" ? "register" : "login";
  const isRegister = state.authMode === "register";
  const title = $("#auth-title");
  if (title) title.textContent = isRegister ? "Создание аккаунта" : "Вход в аккаунт";
  $$("[data-auth-tab]").forEach((node) => {
    node.classList.toggle("active", node.dataset.authTab === state.authMode);
    node.setAttribute("aria-selected", String(node.dataset.authTab === state.authMode));
  });
  $$("[data-auth-panel]").forEach((node) => {
    node.hidden = node.dataset.authPanel !== state.authMode;
  });
  showMessage("auth-message", "");
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.dataset.theme = isDark ? "dark" : "light";
  const toggle = $("#theme-toggle");
  if (toggle) toggle.setAttribute("aria-checked", String(isDark));
  localStorage.setItem("plantcare_theme", isDark ? "dark" : "light");
}

function initTheme() {
  const savedTheme = localStorage.getItem("plantcare_theme");
  const preferredTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  applyTheme(savedTheme || preferredTheme);
}

function renderSession() {
  const label = $("#session-label");
  const loginButton = $("#login-open-button");
  const logoutButton = $("#logout-button");
  if (state.user) {
    label.textContent = `Вы вошли как ${state.user.username}`;
    loginButton.hidden = true;
    logoutButton.hidden = false;
  } else {
    label.textContent = "Гость";
    loginButton.hidden = false;
    logoutButton.hidden = true;
  }
}

function renderStats() {
  const grid = $("#stats-grid");
  if (!state.stats) {
    grid.innerHTML = `<div class="empty">Показатели скоро появятся.</div>`;
    return;
  }
  grid.innerHTML = STAT_CARDS.map((item) => `
    <article class="stat-card">
      <strong>${Number(state.stats[item.key] ?? 0)}</strong>
      <span>${item.label}</span>
    </article>
  `).join("");
}

function scrollToElement(selector) {
  const target = document.querySelector(selector);
  if (!target) return;
  requestAnimationFrame(() => target.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function updateHeroSummary(prefix = "") {
  const title = $("#hero-plant-title");
  const message = $("#health-message");
  if (!title || !message) return;

  const prefixText = prefix ? `${prefix} ` : "";
  if (state.user && state.plants.length) {
    const plant = state.plants[0];
    title.textContent = plant.nickname;
    message.textContent = `${prefixText}Следующий полив: ${formatDate(plant.next_watering_due)}. Откройте карточку ухода, чтобы увидеть погоду и записать действие.`;
    return;
  }

  title.textContent = "С чего начать";
  message.textContent = `${prefixText}Нажмите «Добавить в мой сад» на карточке вида ниже. Если нужного вида нет, добавьте его в разделе «Мой сад» через Wikipedia.`;
}

function speciesImageMarkup(species) {
  if (!species.image_url) {
    return `<div class="species-image-placeholder">${escapeHtml(species.name.slice(0, 1))}</div>`;
  }
  return `<img src="${escapeHtml(species.image_url)}" alt="${escapeHtml(species.name)}" loading="eager">`;
}

function renderSpecies() {
  const grid = $("#species-grid");
  if (!state.species.length) {
    grid.innerHTML = `<div class="empty">Каталог пока пуст. Скоро здесь появятся растения.</div>`;
    return;
  }
  grid.innerHTML = state.species.map((item) => `
    <article class="species-card">
      <div class="species-image">${speciesImageMarkup(item)}</div>
      <div class="species-card-body">
        <div>
          <h3>${escapeHtml(item.name)}</h3>
          <p class="latin-name">${escapeHtml(item.latin_name || "Латинское название не указано")}</p>
        </div>
        <p class="species-description">${escapeHtml(item.description || "Описание пока не заполнено.")}</p>
        <dl class="species-facts">
          <div><dt>Полив</dt><dd>${item.watering_interval_days} дн.</dd></div>
          <div><dt>Влажность</dt><dd>${item.humidity}%</dd></div>
          <div><dt>Питомцы</dt><dd>${item.pet_safe ? "Можно" : "Беречь"}</dd></div>
        </dl>
        <button class="button species-action" data-add-species="${item.id}">Добавить в мой сад</button>
      </div>
    </article>
  `).join("");
}

function selectSpeciesForPlant(speciesId) {
  setActivePage("plants");
  const select = $('#plant-form select[name="species"]');
  if (select) select.value = String(speciesId);
  $('#plant-form input[name="nickname"]')?.focus();
  showMessage("plants-message", "Вид выбран. Заполните имя растения и сохраните его в личный сад.");
}

function continueAfterAuth() {
  if (state.pendingSpeciesId) {
    const speciesId = state.pendingSpeciesId;
    state.pendingSpeciesId = null;
    selectSpeciesForPlant(speciesId);
    return;
  }
  setActivePage("plants");
}

function fillSelects() {
  const speciesOptions = [`<option value="">Выберите вид</option>`]
    .concat(state.species.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`))
    .join("");
  const plantOptions = [`<option value="">Выберите растение</option>`]
    .concat(state.plants.map((plant) => `<option value="${plant.id}">${escapeHtml(plant.nickname)}</option>`))
    .join("");

  const speciesSelect = $('#plant-form select[name="species"]');
  if (speciesSelect) speciesSelect.innerHTML = speciesOptions;

  const taskPlantSelect = $('#task-form select[name="plant"]');
  if (taskPlantSelect) taskPlantSelect.innerHTML = plantOptions;

  const collectionOptions = $("#collection-plant-options");
  if (collectionOptions) {
    collectionOptions.innerHTML = state.plants.length
      ? state.plants.map((plant) => `
          <label class="plant-choice">
            <input type="checkbox" name="plant_ids" value="${plant.id}">
            <span>
              <strong>${escapeHtml(plant.nickname)}</strong>
              <small>${escapeHtml(plant.species_detail.name)}</small>
            </span>
          </label>
        `).join("")
      : `<div class="empty-state compact"><span>Сначала добавьте растение в раздел «Мой сад».</span></div>`;
  }
}

function renderPlants() {
  fillSelects();
  const grid = $("#plants-grid");
  if (!state.user) {
    grid.innerHTML = `<div class="empty">Войдите, чтобы увидеть личные растения.</div>`;
    return;
  }
  if (!state.plants.length) {
    grid.innerHTML = `<div class="empty">Личных растений пока нет. Добавьте первое из каталога.</div>`;
    return;
  }
  grid.innerHTML = state.plants.map((plant) => `
    <article class="plant-card">
      <div class="plant-card-image">${speciesImageMarkup(plant.species_detail)}</div>
      <div class="plant-card-content">
        <div class="plant-card-head">
          <div>
            <h3>${escapeHtml(plant.nickname)}</h3>
            <p>${escapeHtml(plant.species_detail.name)} · ${LOCATION_LABELS[plant.location_type]}</p>
          </div>
          <span class="chip">${formatDate(plant.next_watering_due)}</span>
        </div>
        <p class="plant-note">${escapeHtml(plant.notes || "Заметок пока нет.")}</p>
        <button class="button primary" data-open-plant="${plant.id}">Открыть карточку ухода</button>
      </div>
    </article>
  `).join("");
}

function renderTasks() {
  fillSelects();
  const list = $("#tasks-list");
  if (!state.user) {
    list.innerHTML = `<div class="empty">Войдите, чтобы увидеть календарь.</div>`;
    return;
  }
  if (!state.tasks.length) {
    list.innerHTML = `<div class="empty">Задач пока нет.</div>`;
    return;
  }
  list.innerHTML = state.tasks.map((task) => `
    <div class="list-row">
      <div>
        <strong>${TASK_LABELS[task.task_type] || task.task_type} · ${escapeHtml(task.plant_name)}</strong>
        <div class="meta">Срок: ${formatDate(task.due_date)} · ${task.status}</div>
        ${task.notes ? `<div>${escapeHtml(task.notes)}</div>` : ""}
      </div>
      ${task.status !== "done" ? `<button class="button primary" data-complete-task="${task.id}">Выполнить</button>` : `<span class="chip">Выполнено</span>`}
    </div>
  `).join("");
}

function renderCollections() {
  const grid = $("#collections-grid");
  const profile = $("#profile-info");
  if (profile) {
    profile.textContent = state.user ? `Пользователь: ${state.user.username}. Email: ${state.user.email || "не указан"}.` : "Войдите, чтобы увидеть профиль.";
  }
  if (!state.user) {
    grid.innerHTML = `<div class="empty">Войдите, чтобы увидеть коллекции.</div>`;
    return;
  }
  if (!state.collections.length) {
    grid.innerHTML = `<div class="empty-state"><strong>Коллекций пока нет</strong><span>Создайте первую группу для своих растений.</span></div>`;
    return;
  }
  grid.innerHTML = state.collections.map((collection) => `
    <article class="collection-card">
      <h3>${escapeHtml(collection.name)}</h3>
      <p>${escapeHtml(collection.description || "Без описания")}</p>
      <div class="chips">
        ${collection.plants.length
          ? collection.plants.map((plant) => `<span class="chip">${escapeHtml(plant.nickname)}</span>`).join("")
          : `<span class="chip">Пустая коллекция</span>`}
      </div>
    </article>
  `).join("");
}

async function loadPublicData() {
  const [stats, species] = await Promise.all([
    api("/stats/"),
    fetchAll("/species/"),
  ]);
  state.stats = stats;
  state.species = species;
  renderStats();
  renderSpecies();
  fillSelects();
  updateHeroSummary();
}

async function loadPrivateData() {
  if (!state.user) {
    state.plants = [];
    state.tasks = [];
    state.logs = [];
    state.collections = [];
    renderPlants();
    renderTasks();
    renderCollections();
    updateHeroSummary();
    return;
  }
  const [plants, tasks, logs, collections] = await Promise.all([
    fetchAll("/plants/"),
    fetchAll("/care-tasks/"),
    fetchAll("/care-logs/"),
    fetchAll("/collections/"),
  ]);
  state.plants = plants;
  state.tasks = tasks;
  state.logs = logs;
  state.collections = collections;
  renderPlants();
  renderTasks();
  renderCollections();
  updateHeroSummary();
}

async function loadSession() {
  try {
    state.user = await api("/auth/me/");
  } catch {
    state.user = null;
  }
  renderSession();
}

async function loadEverything() {
  showMessage("plants-message", "");
  showMessage("calendar-message", "");
  showMessage("profile-message", "");
  try {
    await loadPublicData();
    await loadPrivateData();
  } catch (error) {
    $("#health-message").textContent = error.message;
  }
}

async function refreshRecommendations() {
  const button = $("#refresh-all-button");
  const previousText = button.textContent;
  button.disabled = true;
  button.textContent = "Обновляем...";
  $("#health-message").textContent = "Обновляем каталог, личный сад и рекомендации...";
  await loadEverything();
  const time = new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
  updateHeroSummary(`Обновлено в ${time}.`);
  button.disabled = false;
  button.textContent = previousText;
}

async function login(username, password) {
  const result = await api("/auth/token/", {
    method: "POST",
    body: { username, password },
  });
  state.user = result.user;
  renderSession();
  await loadPrivateData();
}

function renderEncyclopediaResults(payload) {
  const container = $("#encyclopedia-results");
  if (!payload.results.length) {
    container.innerHTML = `
      <div class="empty-state">
        <strong>Ничего не найдено</strong>
        <span>${escapeHtml(payload.message || "Попробуйте другое название растения.")}</span>
      </div>
    `;
    return;
  }

  const [primary, ...alternatives] = payload.results;
  container.innerHTML = `
    <article class="encyclopedia-primary">
      <div class="encyclopedia-image">
        ${primary.thumbnail_url
          ? `<img src="${escapeHtml(primary.thumbnail_url)}" alt="${escapeHtml(primary.title)}">`
          : `<div class="species-image-placeholder">${escapeHtml(primary.title.slice(0, 1))}</div>`}
      </div>
      <div>
        <span class="result-kicker">Лучшее совпадение</span>
        <h3>${escapeHtml(primary.title)}</h3>
        <p>${escapeHtml(truncateText(primary.extract, 1000))}</p>
        <a class="button primary inline-button" href="${escapeHtml(primary.source_url)}" target="_blank" rel="noreferrer">
          Читать в Wikipedia
        </a>
      </div>
    </article>
    ${alternatives.length ? `
      <section class="alternative-results">
        <h3>Другие варианты</h3>
        <div>
          ${alternatives.map((entry) => `
            <a href="${escapeHtml(entry.source_url)}" target="_blank" rel="noreferrer">
              <strong>${escapeHtml(entry.title)}</strong>
              <span>${escapeHtml(truncateText(entry.extract, 180))}</span>
            </a>
          `).join("")}
        </div>
      </section>
    ` : ""}
  `;
}

async function searchEncyclopedia(query) {
  showMessage("encyclopedia-message", "Ищем в Wikipedia...");
  $("#encyclopedia-results").innerHTML = `<div class="search-skeleton"></div>`;
  try {
    const payload = await api(`/encyclopedia/search/?q=${encodeURIComponent(query)}`);
    showMessage("encyclopedia-message", payload.available ? "" : payload.message, !payload.available);
    renderEncyclopediaResults(payload);
  } catch (error) {
    showMessage("encyclopedia-message", error.message, true);
    $("#encyclopedia-results").innerHTML = "";
  }
}

async function openPlant(plantId) {
  const detail = $("#plant-detail");
  const plant = state.plants.find((item) => item.id === Number(plantId));
  if (!plant) return;
  detail.hidden = false;
  detail.innerHTML = `
    <div class="section-title compact">
      <div>
        <p class="eyebrow">Карточка ухода</p>
        <h2>${escapeHtml(plant.nickname)}</h2>
      </div>
      <span class="badge">${escapeHtml(plant.species_detail.name)}</span>
    </div>
    <div class="two-columns">
      <div>
        <p>Место: ${LOCATION_LABELS[plant.location_type]}</p>
        <p>Последний полив: ${formatDate(plant.last_watered_at)}</p>
        <p>Следующий полив: ${formatDate(plant.next_watering_due)}</p>
        <p class="meta">${escapeHtml(plant.notes || "Заметок пока нет.")}</p>
      </div>
      <div id="weather-panel">Загружаем погодную подсказку...</div>
    </div>
    <div class="two-columns">
      <form class="form" id="detail-log-form">
        <h3>Записать уход</h3>
        <select name="task_type">
          <option value="water">Полив</option>
          <option value="fertilize">Удобрение</option>
          <option value="repot">Пересадка</option>
          <option value="prune">Обрезка</option>
        </select>
        <textarea name="notes" maxlength="1000" rows="3" placeholder="Комментарий"></textarea>
        <button class="button primary" type="submit">Сохранить запись</button>
      </form>
      <form class="form" id="detail-task-form">
        <h3>Добавить задачу</h3>
        <select name="task_type">
          <option value="water">Полив</option>
          <option value="fertilize">Удобрение</option>
          <option value="repot">Пересадка</option>
          <option value="prune">Обрезка</option>
        </select>
        <input name="due_date" type="date" value="${todayIso()}" required>
        <textarea name="notes" maxlength="1000" rows="3" placeholder="Заметки"></textarea>
        <button class="button primary" type="submit">Добавить задачу</button>
      </form>
    </div>
    <div class="two-columns">
      <div>
        <h3>Ближайшие задачи</h3>
        <div class="list" id="detail-tasks"></div>
      </div>
      <div>
        <h3>История ухода</h3>
        <div class="list" id="detail-logs"></div>
      </div>
    </div>
  `;
  $("#detail-log-form").addEventListener("submit", (event) => submitDetailLog(event, plant.id));
  $("#detail-task-form").addEventListener("submit", (event) => submitDetailTask(event, plant.id));
  renderPlantDetailLists(plant.id);
  await loadWeather(plant.id);
  detail.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderPlantDetailLists(plantId) {
  const tasks = state.tasks.filter((task) => task.plant === Number(plantId));
  const logs = state.logs.filter((log) => log.plant === Number(plantId));
  $("#detail-tasks").innerHTML = tasks.length
    ? tasks.map((task) => `<div class="list-row"><span>${TASK_LABELS[task.task_type]}: ${formatDate(task.due_date)} · ${task.status}</span></div>`).join("")
    : `<div class="empty">Задач пока нет.</div>`;
  $("#detail-logs").innerHTML = logs.length
    ? logs.map((log) => `<div class="list-row"><span>${formatDate(log.performed_at)} · ${TASK_LABELS[log.task_type]} ${escapeHtml(log.notes || "")}</span></div>`).join("")
    : `<div class="empty">История пока пуста.</div>`;
}

async function loadWeather(plantId) {
  const panel = $("#weather-panel");
  try {
    const recommendation = await api(`/weather/recommendation/?plant_id=${plantId}`);
    panel.innerHTML = `
      <h3>Погодная подсказка</h3>
      <p><strong>${escapeHtml(recommendation.weather_summary)}</strong></p>
      <p>${escapeHtml(recommendation.message)}</p>
      <div class="chips">
        <span class="chip">Температура: ${Number(recommendation.temperature_c).toFixed(1)} °C</span>
        <span class="chip">Влажность: ${recommendation.humidity_percent}%</span>
        <span class="chip">Осадки сегодня: ${Number(recommendation.precipitation_mm).toFixed(1)} мм</span>
        <span class="chip">${recommendation.rain_expected ? "Скоро дождь" : "Дождя не будет"}</span>
      </div>
    `;
  } catch (error) {
    panel.textContent = error.message;
  }
}

async function submitDetailLog(event, plantId) {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api("/care-logs/", {
      method: "POST",
      body: {
        plant: Number(plantId),
        task_type: form.get("task_type"),
        notes: form.get("notes"),
      },
    });
    await loadPrivateData();
    await openPlant(plantId);
    showMessage("plants-message", "Запись ухода сохранена.");
  } catch (error) {
    showMessage("plants-message", error.message, true);
  }
}

async function submitDetailTask(event, plantId) {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api("/care-tasks/", {
      method: "POST",
      body: {
        plant: Number(plantId),
        task_type: form.get("task_type"),
        due_date: form.get("due_date"),
        notes: form.get("notes"),
      },
    });
    await loadPrivateData();
    await openPlant(plantId);
    showMessage("plants-message", "Задача добавлена.");
  } catch (error) {
    showMessage("plants-message", error.message, true);
  }
}

async function completeTask(taskId) {
  try {
    await api(`/care-tasks/${taskId}/complete/`, { method: "POST" });
    await loadPrivateData();
    showMessage("calendar-message", "Задача отмечена выполненной.");
  } catch (error) {
    showMessage("calendar-message", error.message, true);
  }
}

function bindForms() {
  $("#encyclopedia-search-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    await searchEncyclopedia(String(form.get("query") || "").trim());
  });

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await login(form.get("username"), form.get("password"));
      showMessage("auth-message", "Вход выполнен.");
      continueAfterAuth();
    } catch (error) {
      showMessage("auth-message", error.message, true);
    }
  });

  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/auth/register/", {
        method: "POST",
        body: {
          username: form.get("username"),
          email: form.get("email"),
          password: form.get("password"),
        },
      });
      await login(form.get("username"), form.get("password"));
      showMessage("auth-message", "Регистрация выполнена.");
      continueAfterAuth();
    } catch (error) {
      showMessage("auth-message", error.message, true);
    }
  });

  $("#plant-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/plants/", {
        method: "POST",
        body: {
          species: Number(form.get("species")),
          nickname: form.get("nickname"),
          location_type: form.get("location_type"),
          planted_at: form.get("planted_at") || null,
          watering_interval_override: form.get("watering_interval_override")
            ? Number(form.get("watering_interval_override"))
            : null,
          notes: form.get("notes"),
        },
      });
      event.target.reset();
      await loadPrivateData();
      showMessage("plants-message", "Растение добавлено.");
    } catch (error) {
      showMessage("plants-message", error.message, true);
    }
  });

  $("#species-import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const query = String(form.get("query") || "").trim();
    showMessage("species-import-message", "Ищем растение в Wikipedia...");
    try {
      const result = await api("/species/from-encyclopedia/", {
        method: "POST",
        body: { query },
      });
      await loadPublicData();
      const speciesId = result.species.id;
      selectSpeciesForPlant(speciesId);
      event.target.reset();
      showMessage(
        "species-import-message",
        `${result.message} Вид «${result.species.name}» выбран в форме выше.`
      );
    } catch (error) {
      showMessage("species-import-message", error.message, true);
    }
  });

  $("#task-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      await api("/care-tasks/", {
        method: "POST",
        body: {
          plant: Number(form.get("plant")),
          task_type: form.get("task_type"),
          due_date: form.get("due_date"),
          notes: form.get("notes"),
        },
      });
      event.target.reset();
      $('#task-form input[name="due_date"]').value = todayIso();
      await loadPrivateData();
      showMessage("calendar-message", "Задача добавлена.");
    } catch (error) {
      showMessage("calendar-message", error.message, true);
    }
  });

  $("#import-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try {
      const result = await api("/import/plants/", { method: "POST", body: form });
      await loadPrivateData();
      showMessage("profile-message", `Импортировано: ${result.created_count}. Ошибок: ${result.errors.length}.`);
      event.target.reset();
      $("#import-file-name").textContent = "Файл не выбран";
    } catch (error) {
      showMessage("profile-message", error.message, true);
    }
  });

  $("#collection-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const plantIds = Array.from(event.target.querySelectorAll('input[name="plant_ids"]:checked'))
      .map((input) => Number(input.value));
    try {
      await api("/collections/", {
        method: "POST",
        body: {
          name: form.get("name"),
          description: form.get("description"),
          plant_ids: plantIds,
        },
      });
      event.target.reset();
      await loadPrivateData();
      showMessage("profile-message", "Коллекция создана.");
    } catch (error) {
      showMessage("profile-message", error.message, true);
    }
  });
}

function bindClicks() {
  document.addEventListener("click", async (event) => {
    const nav = event.target.closest("[data-nav]");
    if (nav) {
      event.preventDefault();
      const openedPage = setActivePage(nav.dataset.nav);
      if (openedPage === "auth" && nav.dataset.nav !== "auth") {
        setAuthMode("login");
        showMessage("auth-message", "Войдите или зарегистрируйтесь, чтобы создать личный сад и график ухода.");
      }
      if (nav.dataset.scrollTarget) {
        scrollToElement(nav.dataset.scrollTarget);
      }
      return;
    }

    const authTab = event.target.closest("[data-auth-tab]");
    if (authTab) {
      event.preventDefault();
      setAuthMode(authTab.dataset.authTab);
      return;
    }

    const addSpeciesButton = event.target.closest("[data-add-species]");
    if (addSpeciesButton) {
      const speciesId = addSpeciesButton.dataset.addSpecies;
      if (state.user) {
        selectSpeciesForPlant(speciesId);
      } else {
        state.pendingSpeciesId = speciesId;
        setAuthMode("login");
        setActivePage("auth");
        showMessage("auth-message", "Войдите или зарегистрируйтесь, и выбранный вид сразу откроется в форме добавления.");
      }
      return;
    }

    const plantButton = event.target.closest("[data-open-plant]");
    if (plantButton) {
      await openPlant(Number(plantButton.dataset.openPlant));
      return;
    }

    const taskButton = event.target.closest("[data-complete-task]");
    if (taskButton) {
      await completeTask(Number(taskButton.dataset.completeTask));
    }
  });

  $("#login-open-button").addEventListener("click", () => {
    setAuthMode("login");
    setActivePage("auth");
  });
  $("#refresh-all-button").addEventListener("click", refreshRecommendations);
  $("#reload-plants-button").addEventListener("click", loadPrivateData);
  $("#theme-toggle").addEventListener("click", () => {
    const currentTheme = document.documentElement.dataset.theme;
    applyTheme(currentTheme === "dark" ? "light" : "dark");
  });
  $('#import-form input[name="file"]').addEventListener("change", (event) => {
    $("#import-file-name").textContent = event.target.files?.[0]?.name || "Файл не выбран";
  });
  $("#logout-button").addEventListener("click", async () => {
    try {
      await api("/auth/logout/", { method: "POST" }, false);
    } finally {
      state.user = null;
      renderSession();
      await loadPrivateData();
      setActivePage("dashboard");
    }
  });
}

async function init() {
  initTheme();
  $('#task-form input[name="due_date"]').value = todayIso();
  bindClicks();
  bindForms();
  setAuthMode("login");
  renderSession();
  setActivePage((location.hash || "#dashboard").slice(1));
  await loadSession();
  await loadEverything();
}

init().catch((error) => {
  $("#health-message").textContent = error.message;
});
