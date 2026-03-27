<template>
  <div ref="editorWrapRef" class="editor-wrap">
    <div class="toolbar">
      <span class="title">{{ workflowName }}</span>
      <button type="button" class="btn btn--ghost" @click="addTriggerNode">+ Триггер</button>
      <button type="button" class="btn btn--ghost" @click="addActionNode">+ Действие</button>
      <button type="button" class="btn btn--ghost" :disabled="!selectedNodeId" @click="deleteSelectedNode">Удалить выбранный</button>
      <button type="button" class="btn btn--ghost" @click="resetLayoutSizes">Сбросить размеры</button>
      <button type="button" class="btn" :disabled="saving || !saveUrl" @click="save">
        {{ saving ? "Сохранение…" : "Сохранить" }}
      </button>
      <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
    </div>
    <div class="work-area-wrap">
      <button
        type="button"
        class="resize-handle resize-handle--outer resize-handle--left"
        title="Изменить ширину рабочей области"
        @mousedown.prevent="startOuterResize('left', $event)"
      />
      <div class="work-area" :style="workAreaStyle">
      <div class="flow-host">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          fit-view-on-init
          class="flow"
          :min-zoom="0.2"
          :max-zoom="2"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="onPaneClick"
          @connect="onConnect"
          @connect-start="onConnectStart"
          @connect-end="onConnectEnd"
        >
          <Background pattern-color="#aaa" :gap="16" />
          <Controls />
        </VueFlow>
        <div
          v-if="createMenu.visible"
          class="create-menu"
          :style="{ left: `${createMenu.x}px`, top: `${createMenu.y}px` }"
        >
          <button type="button" class="btn btn--ghost btn--sm" @click="createNodeFromMenu('action')">Действие</button>
          <button type="button" class="btn btn--ghost btn--sm" @click="closeCreateMenu">Отмена</button>
        </div>
        <div
          v-if="edgeMenu.visible"
          class="create-menu"
          :style="{ left: `${edgeMenu.x}px`, top: `${edgeMenu.y}px` }"
        >
          <button type="button" class="btn btn--ghost btn--sm" @click="deleteEdgeFromMenu">Удалить</button>
          <button type="button" class="btn btn--ghost btn--sm" @click="closeEdgeMenu">Отмена</button>
        </div>
      </div>
      <button
        type="button"
        class="resize-handle resize-handle--inner"
        title="Изменить ширину панели настроек"
        @mousedown.prevent="startInnerResize($event)"
      />
      <aside class="side" :style="sideStyle">
        <h3>Настройка узла</h3>
        <p v-if="!selectedNodeId" class="hint">Выберите узел на схеме</p>
        <template v-else>
          <label class="field">
            <span>Название</span>
            <input v-model.trim="selectedLabel" type="text" />
          </label>
          <template v-if="isTriggerNode(selectedNode)">
            <label class="field">
              <span>Тип триггера</span>
              <select v-model="selectedTriggerType">
                <option value="webhook">Webhook</option>
                <option value="cron">Cron</option>
                <option value="email">Email (IMAP)</option>
              </select>
            </label>

            <template v-if="selectedTriggerType === 'cron'">
              <label class="field">
                <span>minute</span>
                <input v-model.trim="cronConfig.minute" type="text" placeholder="*/5" />
              </label>
              <label class="field">
                <span>hour</span>
                <input v-model.trim="cronConfig.hour" type="text" placeholder="*" />
              </label>
              <label class="field">
                <span>day_of_week</span>
                <input v-model.trim="cronConfig.day_of_week" type="text" placeholder="*" />
              </label>
              <label class="field">
                <span>day_of_month</span>
                <input v-model.trim="cronConfig.day_of_month" type="text" placeholder="*" />
              </label>
              <label class="field">
                <span>month_of_year</span>
                <input v-model.trim="cronConfig.month_of_year" type="text" placeholder="*" />
              </label>
              <p class="hint">Cron сработает только когда workflow активен.</p>
            </template>

            <template v-if="selectedTriggerType === 'email'">
              <label class="field">
                <span>IMAP host</span>
                <input v-model.trim="emailConfig.imap_host" type="text" placeholder="imap.example.com" />
              </label>
              <label class="field">
                <span>IMAP port</span>
                <input v-model.number="emailConfig.imap_port" type="number" min="1" max="65535" />
              </label>
              <label class="field">
                <span>Username</span>
                <input v-model.trim="emailConfig.username" type="text" placeholder="user@example.com" />
              </label>
              <label class="field">
                <span>Password</span>
                <input v-model.trim="emailConfig.password" type="password" placeholder="app password" />
              </label>
              <label class="field">
                <span>Mailbox</span>
                <input v-model.trim="emailConfig.mailbox" type="text" placeholder="INBOX" />
              </label>
              <label class="field">
                <span>Макс. писем за один опрос</span>
                <input v-model.number="emailConfig.max_messages" type="number" min="1" max="50" />
              </label>
              <p class="hint">По умолчанию: polling раз в 5 минут, поиск `UNSEEN`, после обработки помечает письма как Seen.</p>
            </template>

            <p v-if="selectedTriggerType === 'webhook'" class="hint">Webhook URL показывается на странице редактора.</p>
          </template>

          <template v-else>
            <label class="field">
              <span>Тип действия</span>
              <select v-model="selectedActionType">
                <option value="">Передать как есть</option>
                <option value="http">HTTP</option>
                <option value="telegram">Telegram</option>
                <option value="email">Email</option>
                <option value="sql">SQL</option>
                <option value="transform">Трансформация</option>
              </select>
            </label>
            <div class="field field--inline">
              <span>Режим настроек</span>
              <div class="segmented">
                <button type="button" class="segmented__btn" :class="{ 'segmented__btn--active': editorUiMode === 'simple' }" @click="setEditorUiMode('simple')">Простой</button>
                <button type="button" class="segmented__btn" :class="{ 'segmented__btn--active': editorUiMode === 'advanced' }" @click="setEditorUiMode('advanced')">Профи</button>
              </div>
            </div>
            <label class="field">
              <span>Merge policy (несколько входов)</span>
              <select v-model="selectedMergePolicy">
                <option value="auto">auto</option>
                <option value="dict_merge">dict merge (shallow)</option>
                <option value="last">last wins</option>
                <option value="list_concat">list concat</option>
                <option value="namespace">namespace by input id</option>
              </select>
            </label>
            <label class="field">
              <span>Поведение при ошибке</span>
              <select v-model="selectedOnErrorPolicy">
                <option value="stop">stop on error</option>
                <option value="continue">continue on error</option>
                <option value="pause">pause (resume later)</option>
              </select>
            </label>
            <template v-if="selectedActionType === 'http' && editorUiMode === 'simple'">
              <label class="field">
                <span>Куда отправлять (Webhook URL)</span>
                <input v-model.trim="selectedHttpUrl" type="url" placeholder="https://webhook.site/..." />
              </label>
              <p class="hint">Отправка всегда POST. В body уходит весь входящий payload.</p>
            </template>
            <label v-else-if="selectedActionType === 'http'" class="field">
              <span>HTTP URL</span>
              <input v-model.trim="selectedHttpUrl" type="url" placeholder="https://api.example.com/hook" />
            </label>
            <template v-if="selectedActionType === 'telegram' && editorUiMode === 'simple'">
              <label class="field">
                <span>Бот</span>
                <select v-model="selectedTelegramBotTokenVar">
                  <option value="">из Профиля (по умолчанию)</option>
                  <option v-for="k in variableKeys" :key="k" :value="k">{{ "{{" + k + "}" + "}" }}</option>
                </select>
              </label>
              <label class="field">
                <span>Кому отправить (Chat ID)</span>
                <input v-model.trim="selectedTelegramChatId" type="text" placeholder="-100123... или 12345" />
              </label>
              <label class="field">
                <span>Текст сообщения</span>
                <textarea v-model.trim="selectedTelegramText" rows="4" placeholder="Новый email: {subject} от {from}" />
              </label>
              <div class="field">
                <span>Быстрые вставки</span>
                <div class="chips">
                  <button type="button" class="chip" @click="insertTelegramToken('{subject}')">{subject}</button>
                  <button type="button" class="chip" @click="insertTelegramToken('{from}')">{from}</button>
                  <button type="button" class="chip" @click="insertTelegramToken('{text}')">{text}</button>
                  <button type="button" class="chip" @click="insertTelegramToken('{date}')">{date}</button>
                  <button type="button" class="chip" @click="insertTelegramToken('{payload}')">{payload}</button>
                </div>
              </div>
              <p class="hint">Поддерживаются {subject}/{from}/{text}/{date} (в т.ч. из email.*), а также {payload} целиком.</p>
            </template>
            <template v-else-if="selectedActionType === 'telegram'">
              <label class="field">
                <span>Bot token</span>
                <select v-model="selectedTelegramBotTokenVar">
                  <option value="">из Профиля (по умолчанию)</option>
                  <option v-for="k in variableKeys" :key="k" :value="k">{{ "{{" + k + "}" + "}" }}</option>
                </select>
              </label>
              <label class="field">
                <span>Chat ID (optional)</span>
                <input v-model.trim="selectedTelegramChatId" type="text" placeholder="-100123... или 12345" />
              </label>
              <label class="field">
                <span>Message</span>
                <input v-model.trim="selectedTelegramText" type="text" placeholder="Hello! payload={payload}" />
              </label>
              <p class="hint">Токен и default chat id берутся из Профиля.</p>
            </template>
            <template v-if="selectedActionType === 'email' && editorUiMode === 'simple'">
              <label class="field">
                <span>Кому</span>
                <input v-model.trim="selectedEmailTo" type="text" placeholder="user@example.com, other@example.com" />
              </label>
              <label class="field">
                <span>Тема</span>
                <input v-model.trim="selectedEmailSubject" type="text" placeholder="Новый email: {subject}" />
              </label>
              <label class="field">
                <span>Текст</span>
                <textarea v-model.trim="selectedEmailBody" rows="4" placeholder="От {from}, дата {date}" />
              </label>
              <p class="hint">Можно использовать {subject}/{from}/{text}/{date} и {payload}.</p>
            </template>
            <template v-else-if="selectedActionType === 'email'">
              <label class="field">
                <span>To</span>
                <input v-model.trim="selectedEmailTo" type="text" placeholder="user@example.com, other@example.com" />
              </label>
              <label class="field">
                <span>Subject</span>
                <input v-model.trim="selectedEmailSubject" type="text" placeholder="MiniZapier notification" />
              </label>
              <label class="field">
                <span>Body</span>
                <input v-model.trim="selectedEmailBody" type="text" placeholder="payload={payload}" />
              </label>
              <p class="hint">Отправка идёт через SMTP из .env (EMAIL_*). Можно использовать {payload}.</p>
            </template>
            <template v-if="selectedActionType === 'sql' && editorUiMode === 'simple'">
              <label class="field">
                <span>DSN из переменных</span>
                <select v-model="selectedSqlDsnVar">
                  <option value="">из Профиля (по умолчанию)</option>
                  <option v-for="k in variableKeys" :key="k" :value="k">{{ "{{" + k + "}" + "}" }}</option>
                </select>
              </label>
              <div class="field">
                <span>Быстрый шаблон запроса</span>
                <div class="chips">
                  <button type="button" class="chip" @click="applySqlPreset('ping')">Проверка БД</button>
                  <button type="button" class="chip" @click="applySqlPreset('raw_payload')">Посмотреть payload</button>
                  <button type="button" class="chip" @click="applySqlPreset('email_fields')">Поля email</button>
                </div>
              </div>
              <label class="field">
                <span>SQL (только SELECT)</span>
                <textarea v-model.trim="selectedSqlQuery" rows="4" placeholder="SELECT now() as ts" />
              </label>
              <label class="field">
                <span>Макс. строк</span>
                <input v-model.number="selectedSqlMaxRows" type="number" min="1" max="1000" />
              </label>
              <p class="hint">MVP ограничение: разрешены только SELECT-запросы.</p>
            </template>
            <template v-else-if="selectedActionType === 'sql'">
              <label class="field">
                <span>DSN из переменных (optional)</span>
                <select v-model="selectedSqlDsnVar">
                  <option value="">из Профиля (по умолчанию)</option>
                  <option v-for="k in variableKeys" :key="k" :value="k">{{ "{{" + k + "}" + "}" }}</option>
                </select>
              </label>
              <label class="field">
                <span>DSN override (optional)</span>
                <input v-model.trim="selectedSqlDsnOverride" type="text" placeholder="postgresql://user:pass@host:5432/db" />
              </label>
              <label class="field">
                <span>Query (SELECT only)</span>
                <input v-model.trim="selectedSqlQuery" type="text" placeholder="SELECT now() as ts" />
              </label>
              <label class="field">
                <span>Max rows</span>
                <input v-model.number="selectedSqlMaxRows" type="number" min="1" max="1000" />
              </label>
              <p class="hint">По умолчанию DSN берется из Профиля. Разрешены только SELECT-запросы.</p>
            </template>
            <template v-if="selectedActionType === 'transform' && editorUiMode === 'simple'">
              <div class="field">
                <span>Какие поля оставить</span>
                <div class="checks">
                  <label class="check"><input type="checkbox" :checked="hasTransformField('subject')" @change="toggleTransformField('subject', $event)" /> subject</label>
                  <label class="check"><input type="checkbox" :checked="hasTransformField('from')" @change="toggleTransformField('from', $event)" /> from</label>
                  <label class="check"><input type="checkbox" :checked="hasTransformField('text')" @change="toggleTransformField('text', $event)" /> text</label>
                  <label class="check"><input type="checkbox" :checked="hasTransformField('date')" @change="toggleTransformField('date', $event)" /> date</label>
                  <label class="check"><input type="checkbox" :checked="hasTransformField('message_id')" @change="toggleTransformField('message_id', $event)" /> message_id</label>
                </div>
              </div>
              <div class="field">
                <span>Постоянные поля (константы)</span>
                <div v-for="(row, idx) in transformConstantsRows" :key="`c-${idx}`" class="kv-row">
                  <input :value="row.key" type="text" placeholder="key" @input="updateTransformConstantKey(idx, $event.target.value)" />
                  <input :value="row.value" type="text" placeholder="value" @input="updateTransformConstantValue(idx, $event.target.value)" />
                  <button type="button" class="btn btn--ghost btn--sm" @click="removeTransformConstantRow(idx)">×</button>
                </div>
                <button type="button" class="btn btn--ghost btn--sm" @click="addTransformConstantRow">+ Добавить поле</button>
              </div>
              <p class="hint">Для сложных кейсов переключитесь в режим “Профи”.</p>
            </template>
            <template v-else-if="selectedActionType === 'transform'">
              <label class="field">
                <span>Pick keys (comma-separated)</span>
                <input v-model.trim="selectedTransformPickKeys" type="text" placeholder="subject,from,text,date или email.subject" />
              </label>
              <label class="field">
                <span>Constants JSON (optional)</span>
                <input v-model.trim="selectedTransformConstantsJson" type="text" placeholder='{"source":"minizapier"}' />
              </label>
              <p class="hint">Без eval: поддерживает top-level, nested path через точку и fallback из email.* для IMAP payload.</p>
            </template>
            <div class="card-lite">
              <div class="card-lite__title">Тест узла (без запуска workflow)</div>
              <label class="field">
                <span>Тестовый payload (JSON)</span>
                <textarea v-model="nodeTestInputRaw" rows="6" placeholder='{"email":{"subject":"Test","from":"user@example.com"}}' />
              </label>
              <div class="chips">
                <button type="button" class="chip" @click="applyNodeTestPreset('imap')">IMAP пример</button>
                <button type="button" class="chip" @click="applyNodeTestPreset('simple')">Простой пример</button>
                <button type="button" class="chip" @click="applyNodeTestPreset('empty')">Очистить</button>
              </div>
              <div class="btn-row">
                <button type="button" class="btn btn--ghost btn--sm" @click="runNodeTest">Проверить</button>
              </div>
              <p v-if="nodeTestError" class="hint hint--error">{{ nodeTestError }}</p>
              <label class="field">
                <span>Результат preview</span>
                <textarea :value="nodeTestOutputPretty" rows="8" readonly />
              </label>
              <p class="hint">Preview не отправляет запросы наружу, а показывает локально рассчитанный результат.</p>
            </div>
          </template>
        </template>
      </aside>
      </div>
      <button
        type="button"
        class="resize-handle resize-handle--outer resize-handle--right"
        title="Изменить ширину рабочей области"
        @mousedown.prevent="startOuterResize('right', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { VueFlow, useVueFlow } from "@vue-flow/core";
import { ref, onBeforeUnmount, onMounted, computed } from "vue";

const props = defineProps({
  workflowId: { type: Number, required: true },
  workflowName: { type: String, default: "" },
  initial: { type: Object, default: () => ({}) },
  saveUrl: { type: String, default: "" },
  userVariableKeys: { type: Array, default: () => [] },
});

const variableKeys = computed(() =>
  (Array.isArray(props.userVariableKeys) ? props.userVariableKeys : []).map((k) => String(k || "").toUpperCase())
);
const UI_MODE_LS_KEY = "minizapier:editor-ui-mode";
const editorUiMode = ref("simple");

const defaultNodes = () => [
  {
    id: "trigger-1",
    type: "input",
    position: { x: 80, y: 40 },
    data: {
      label: "Триггер (Webhook)",
      kind: "trigger",
      triggerType: "webhook",
      cronConfig: {
        minute: "*/5",
        hour: "*",
        day_of_week: "*",
        day_of_month: "*",
        month_of_year: "*",
      },
    },
  },
  {
    id: "action-1",
    position: { x: 80, y: 160 },
    data: {
      label: "Действие (HTTP)",
      kind: "action",
      actionType: "http",
      config: { url: "", continue_on_error: false },
    },
  },
];

const defaultEdges = () => [
  {
    id: "e-trigger-action",
    source: "trigger-1",
    target: "action-1",
  },
];

function mergeInitial(raw) {
  const n = raw?.nodes;
  const e = raw?.edges;
  if (Array.isArray(n) && n.length && Array.isArray(e)) {
    return { nodes: n, edges: e };
  }
  return {
    nodes: defaultNodes(),
    edges: defaultEdges(),
  };
}

const nodes = ref([]);
const edges = ref([]);
const saving = ref(false);
const saveMsg = ref("");
const selectedNodeId = ref("");
const selectedEdgeId = ref("");
const pendingSourceNodeId = ref("");
const createMenu = ref({ visible: false, x: 0, y: 0, flowX: 0, flowY: 0 });
const edgeMenu = ref({ visible: false, x: 0, y: 0, edgeId: "" });
const suppressPaneClickUntil = ref(0);
const nodeTestInputRaw = ref('{"email":{"subject":"Test","from":"user@example.com","text":"Hello","date":"2026-03-27T12:00:00Z"}}');
const nodeTestOutputPretty = ref("{}");
const nodeTestError = ref("");
const { project } = useVueFlow();
const editorWrapRef = ref(null);
const workAreaWidth = ref(null);
const sideWidth = ref(320);
const resizeState = ref({
  mode: "",
  startX: 0,
  startWorkAreaWidth: 0,
  startSideWidth: 320,
  outerDirection: "right",
});

const OUTER_MIN_WIDTH = 760;
const SIDE_MIN_WIDTH = 260;
const SIDE_MAX_WIDTH = 620;
const FLOW_MIN_WIDTH = 380;
const LS_WORK_AREA_WIDTH = "minizapier:work-area-width";
const LS_SIDE_WIDTH = "minizapier:side-width";

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function setEditorUiMode(mode) {
  const next = mode === "advanced" ? "advanced" : "simple";
  editorUiMode.value = next;
  try {
    localStorage.setItem(UI_MODE_LS_KEY, next);
  } catch (_) {
    // ignore storage issues
  }
}

const workAreaStyle = computed(() => ({
  width: workAreaWidth.value ? `${workAreaWidth.value}px` : "100%",
}));

const sideStyle = computed(() => ({
  width: `${sideWidth.value}px`,
}));

function getEditorWidth() {
  const el = editorWrapRef.value;
  if (!el) return 1280;
  return Math.max(OUTER_MIN_WIDTH, Math.floor(el.clientWidth));
}

function getMaxSideWidth(targetWorkAreaWidth) {
  const base = Number.isFinite(targetWorkAreaWidth) ? targetWorkAreaWidth : getEditorWidth();
  return Math.max(SIDE_MIN_WIDTH, Math.min(SIDE_MAX_WIDTH, base - FLOW_MIN_WIDTH));
}

function persistSizes() {
  try {
    localStorage.setItem(LS_WORK_AREA_WIDTH, String(workAreaWidth.value));
    localStorage.setItem(LS_SIDE_WIDTH, String(sideWidth.value));
  } catch (_) {
    // no-op for private mode / blocked storage
  }
}

function resetLayoutSizes() {
  const editorWidth = getEditorWidth();
  workAreaWidth.value = editorWidth;
  sideWidth.value = clamp(320, SIDE_MIN_WIDTH, getMaxSideWidth(editorWidth));
  persistSizes();
}

function beginResize(mode, event, outerDirection = "right") {
  resizeState.value = {
    mode,
    startX: event.clientX,
    startWorkAreaWidth: workAreaWidth.value || getEditorWidth(),
    startSideWidth: sideWidth.value,
    outerDirection,
  };
  window.addEventListener("mousemove", onResizeMove);
  window.addEventListener("mouseup", onResizeEnd);
}

function startOuterResize(direction, event) {
  beginResize("outer", event, direction);
}

function startInnerResize(event) {
  beginResize("inner", event);
}

function onResizeMove(event) {
  const st = resizeState.value;
  if (!st.mode) return;
  const dx = event.clientX - st.startX;
  if (st.mode === "outer") {
    const sign = st.outerDirection === "left" ? -1 : 1;
    const editorWidth = getEditorWidth();
    const next = clamp(st.startWorkAreaWidth + dx * sign, OUTER_MIN_WIDTH, editorWidth);
    workAreaWidth.value = next;
    sideWidth.value = clamp(sideWidth.value, SIDE_MIN_WIDTH, getMaxSideWidth(next));
    return;
  }
  const next = clamp(st.startSideWidth + dx, SIDE_MIN_WIDTH, getMaxSideWidth(workAreaWidth.value));
  sideWidth.value = next;
}

function onResizeEnd() {
  if (!resizeState.value.mode) return;
  resizeState.value.mode = "";
  window.removeEventListener("mousemove", onResizeMove);
  window.removeEventListener("mouseup", onResizeEnd);
  persistSizes();
}

const selectedNode = computed(() =>
  nodes.value.find((node) => node.id === selectedNodeId.value) || null
);

const selectedLabel = computed({
  get() {
    return selectedNode.value?.data?.label || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    selectedNode.value.data = {
      ...(selectedNode.value.data || {}),
      label: v,
    };
  },
});

const selectedActionType = computed({
  get() {
    return selectedNode.value?.data?.actionType || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    selectedNode.value.data = {
      ...(selectedNode.value.data || {}),
      actionType: v,
    };
  },
});

const selectedTriggerType = computed({
  get() {
    return selectedNode.value?.data?.triggerType || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    selectedNode.value.data = {
      ...(selectedNode.value.data || {}),
      triggerType: v,
    };
    if (v === "webhook") {
      selectedNode.value.data.label = "Триггер (Webhook)";
    }
    if (v === "cron") {
      selectedNode.value.data.label = "Триггер (Cron)";
    }
    if (v === "email") {
      selectedNode.value.data.label = "Триггер (Email/IMAP)";
      if (!selectedNode.value.data.emailConfig) {
        selectedNode.value.data.emailConfig = {
          imap_host: "",
          imap_port: 993,
          username: "",
          password: "",
          mailbox: "INBOX",
          max_messages: 5,
        };
      }
    }
  },
});

const cronConfig = computed({
  get() {
    if (!selectedNode.value) {
      return {
        minute: "*",
        hour: "*",
        day_of_week: "*",
        day_of_month: "*",
        month_of_year: "*",
      };
    }
    const d = selectedNode.value.data || {};
    if (!d.cronConfig) {
      d.cronConfig = {
        minute: "*",
        hour: "*",
        day_of_week: "*",
        day_of_month: "*",
        month_of_year: "*",
      };
    }
    return d.cronConfig;
  },
  set(v) {
    if (!selectedNode.value) return;
    selectedNode.value.data = {
      ...(selectedNode.value.data || {}),
      cronConfig: v,
    };
  },
});

const emailConfig = computed({
  get() {
    if (!selectedNode.value) {
      return {
        imap_host: "",
        imap_port: 993,
        username: "",
        password: "",
        mailbox: "INBOX",
        max_messages: 5,
      };
    }
    const d = selectedNode.value.data || {};
    if (!d.emailConfig) {
      d.emailConfig = {
        imap_host: "",
        imap_port: 993,
        username: "",
        password: "",
        mailbox: "INBOX",
        max_messages: 5,
      };
    }
    return d.emailConfig;
  },
  set(v) {
    if (!selectedNode.value) return;
    selectedNode.value.data = {
      ...(selectedNode.value.data || {}),
      emailConfig: v,
    };
  },
});

const selectedHttpUrl = computed({
  get() {
    return selectedNode.value?.data?.config?.url || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        url: v,
      },
    };
  },
});

const selectedOnErrorPolicy = computed({
  get() {
    const cfg = selectedNode.value?.data?.config || {};
    if (cfg.pause_on_error) return "pause";
    if (cfg.continue_on_error) return "continue";
    return "stop";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        continue_on_error: v === "continue",
        pause_on_error: v === "pause",
      },
    };
  },
});

const selectedMergePolicy = computed({
  get() {
    return selectedNode.value?.data?.config?.merge_policy || "auto";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        merge_policy: v || "auto",
      },
    };
  },
});

const selectedTelegramChatId = computed({
  get() {
    return selectedNode.value?.data?.config?.chat_id || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        chat_id: v,
      },
    };
  },
});

const selectedTelegramBotTokenVar = computed({
  get() {
    const raw = String(selectedNode.value?.data?.config?.bot_token || "").trim();
    const m = raw.match(/^\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$/);
    return m ? String(m[1] || "").toUpperCase() : "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    const key = String(v || "").trim().toUpperCase();
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        bot_token: key ? `{{${key}}}` : "",
      },
    };
  },
});

const selectedTelegramText = computed({
  get() {
    return selectedNode.value?.data?.config?.text || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        text: v,
      },
    };
  },
});

const selectedEmailTo = computed({
  get() {
    return selectedNode.value?.data?.config?.to || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        to: v,
      },
    };
  },
});

const selectedEmailSubject = computed({
  get() {
    return selectedNode.value?.data?.config?.subject || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        subject: v,
      },
    };
  },
});

const selectedEmailBody = computed({
  get() {
    return selectedNode.value?.data?.config?.body || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        body: v,
      },
    };
  },
});

const selectedSqlDsnOverride = computed({
  get() {
    return selectedNode.value?.data?.config?.dsn_override || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        dsn_override: v,
      },
    };
  },
});

const selectedSqlDsnVar = computed({
  get() {
    const raw = String(selectedNode.value?.data?.config?.dsn_override || "").trim();
    const m = raw.match(/^\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$/);
    return m ? String(m[1] || "").toUpperCase() : "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    const key = String(v || "").trim().toUpperCase();
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        dsn_override: key ? `{{${key}}}` : "",
      },
    };
  },
});

const selectedSqlQuery = computed({
  get() {
    return selectedNode.value?.data?.config?.query || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        query: v,
      },
    };
  },
});

const selectedSqlMaxRows = computed({
  get() {
    return selectedNode.value?.data?.config?.max_rows || 100;
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    const parsed = Number.isFinite(v) ? Number(v) : 100;
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        max_rows: parsed,
      },
    };
  },
});

const selectedTransformPickKeys = computed({
  get() {
    return selectedNode.value?.data?.config?.pick_keys || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        pick_keys: v,
      },
    };
  },
});

const selectedTransformConstantsJson = computed({
  get() {
    return selectedNode.value?.data?.config?.constants_json || "";
  },
  set(v) {
    if (!selectedNode.value) return;
    const prev = selectedNode.value.data || {};
    selectedNode.value.data = {
      ...prev,
      config: {
        ...(prev.config || {}),
        constants_json: v,
      },
    };
  },
});

function insertTelegramToken(token) {
  const current = String(selectedTelegramText.value || "");
  selectedTelegramText.value = current ? `${current} ${token}` : token;
}

function parseTransformFields() {
  const raw = String(selectedTransformPickKeys.value || "");
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function hasTransformField(field) {
  const f = String(field || "").trim();
  if (!f) return false;
  const fields = parseTransformFields();
  return fields.includes(f) || fields.includes(`email.${f}`);
}

function toggleTransformField(field, event) {
  const checked = !!event?.target?.checked;
  const f = String(field || "").trim();
  if (!f) return;
  const existing = parseTransformFields().filter((k) => k !== f && k !== `email.${f}`);
  if (checked) existing.push(f);
  selectedTransformPickKeys.value = existing.join(",");
}

function parseTransformConstantsRows() {
  const raw = String(selectedTransformConstantsJson.value || "").trim();
  if (!raw) return [];
  try {
    const obj = JSON.parse(raw);
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) return [];
    return Object.entries(obj).map(([key, value]) => ({ key, value: value == null ? "" : String(value) }));
  } catch (_) {
    return [];
  }
}

const transformConstantsRows = computed(() => parseTransformConstantsRows());

function writeTransformConstantsRows(rows) {
  const out = {};
  for (const row of rows) {
    const key = String(row?.key || "").trim();
    if (!key) continue;
    out[key] = String(row?.value || "");
  }
  selectedTransformConstantsJson.value = Object.keys(out).length ? JSON.stringify(out) : "";
}

function addTransformConstantRow() {
  const rows = parseTransformConstantsRows();
  rows.push({ key: "", value: "" });
  writeTransformConstantsRows(rows);
}

function removeTransformConstantRow(idx) {
  const rows = parseTransformConstantsRows();
  if (idx < 0 || idx >= rows.length) return;
  rows.splice(idx, 1);
  writeTransformConstantsRows(rows);
}

function updateTransformConstantKey(idx, value) {
  const rows = parseTransformConstantsRows();
  if (idx < 0 || idx >= rows.length) return;
  rows[idx].key = value;
  writeTransformConstantsRows(rows);
}

function updateTransformConstantValue(idx, value) {
  const rows = parseTransformConstantsRows();
  if (idx < 0 || idx >= rows.length) return;
  rows[idx].value = value;
  writeTransformConstantsRows(rows);
}

function applySqlPreset(kind) {
  if (kind === "ping") {
    selectedSqlQuery.value = "SELECT now() as ts";
    return;
  }
  if (kind === "raw_payload") {
    selectedSqlQuery.value = "SELECT '{payload}'::jsonb as payload";
    return;
  }
  if (kind === "email_fields") {
    selectedSqlQuery.value = "SELECT '{payload}'::jsonb->'email'->>'subject' as subject, '{payload}'::jsonb->'email'->>'from' as sender, '{payload}'::jsonb->'email'->>'date' as sent_at";
  }
}

function deepGet(obj, path) {
  const parts = String(path || "")
    .split(".")
    .map((p) => p.trim())
    .filter(Boolean);
  if (!parts.length) return undefined;
  let cur = obj;
  for (const part of parts) {
    if (!cur || typeof cur !== "object" || !(part in cur)) return undefined;
    cur = cur[part];
  }
  return cur;
}

function renderTemplateLocal(tmpl, payload) {
  const text = String(tmpl || "");
  return text.replace(/\{([A-Za-z_][A-Za-z0-9_.-]*)\}/g, (full, key) => {
    if (key === "payload") {
      return JSON.stringify(payload);
    }
    const direct = deepGet(payload, key);
    if (direct !== undefined) return String(direct ?? "");
    if (payload && typeof payload === "object" && payload.email && typeof payload.email === "object") {
      const emailVal = payload.email[key];
      if (emailVal !== undefined) return String(emailVal ?? "");
    }
    return full;
  });
}

function transformLocal(payload, config) {
  const base = payload && typeof payload === "object" ? payload : { value: payload };
  const pickKeys = String(config?.pick_keys || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  let out = {};
  if (pickKeys.length) {
    for (const key of pickKeys) {
      const v = deepGet(base, key);
      if (v !== undefined) {
        out[key] = v;
        continue;
      }
      if (base.email && typeof base.email === "object" && key in base.email) {
        out[key] = base.email[key];
      }
    }
  } else {
    out = { ...base };
  }
  const raw = String(config?.constants_json || "").trim();
  if (raw) {
    try {
      const constants = JSON.parse(raw);
      if (constants && typeof constants === "object" && !Array.isArray(constants)) {
        out = { ...out, ...constants };
      }
    } catch (_) {
      // ignore constants parse in preview; backend validates on execute
    }
  }
  return out;
}

function applyNodeTestPreset(kind) {
  if (kind === "imap") {
    nodeTestInputRaw.value = '{"email":{"subject":"Test","from":"user@example.com","text":"Hello mate","date":"2026-03-27T12:00:00Z","message_id":"<abc@local>"},"source":"imap"}';
    return;
  }
  if (kind === "simple") {
    nodeTestInputRaw.value = '{"subject":"Test","from":"user@example.com","text":"Hello","date":"2026-03-27"}';
    return;
  }
  nodeTestInputRaw.value = "{}";
}

function runNodeTest() {
  nodeTestError.value = "";
  nodeTestOutputPretty.value = "{}";
  try {
    const payload = JSON.parse(String(nodeTestInputRaw.value || "{}"));
    const kind = String(selectedActionType.value || "").trim().toLowerCase();
    const cfg = selectedNode.value?.data?.config || {};
    let result = {};
    if (kind === "transform") {
      result = transformLocal(payload, cfg);
    } else if (kind === "telegram") {
      result = {
        chat_id: cfg.chat_id || "",
        text: renderTemplateLocal(cfg.text || "", payload),
        note: "preview only: telegram API call is not executed",
      };
    } else if (kind === "email") {
      result = {
        to: cfg.to || "",
        subject: renderTemplateLocal(cfg.subject || "", payload),
        body: renderTemplateLocal(cfg.body || "", payload),
        note: "preview only: email sending is not executed",
      };
    } else if (kind === "http") {
      result = {
        method: "POST",
        url: cfg.url || "",
        body: payload,
        note: "preview only: HTTP request is not executed",
      };
    } else if (kind === "sql") {
      result = {
        query: renderTemplateLocal(cfg.query || "", payload),
        max_rows: cfg.max_rows || 100,
        note: "preview only: SQL query is not executed",
      };
    } else {
      result = payload;
    }
    nodeTestOutputPretty.value = JSON.stringify(result, null, 2);
  } catch (err) {
    nodeTestError.value = `Неверный JSON: ${err?.message || "ошибка парсинга"}`;
  }
}

function nextNodeId(prefix) {
  const used = new Set(nodes.value.map((n) => String(n.id)));
  let i = 1;
  while (used.has(`${prefix}-${i}`)) i += 1;
  return `${prefix}-${i}`;
}

function addTriggerNode() {
  const id = nextNodeId("trigger");
  nodes.value = [
    ...nodes.value,
    {
      id,
      type: "input",
      position: { x: 120, y: 80 + nodes.value.length * 30 },
      data: {
        label: "Триггер (Webhook)",
        kind: "trigger",
        triggerType: "webhook",
        cronConfig: {
          minute: "*/5",
          hour: "*",
          day_of_week: "*",
          day_of_month: "*",
          month_of_year: "*",
        },
      },
    },
  ];
  selectedNodeId.value = id;
}

function addActionNode() {
  const id = nextNodeId("action");
  nodes.value = [
    ...nodes.value,
    {
      id,
      position: { x: 320, y: 120 + nodes.value.length * 40 },
      data: {
        label: "Действие",
        kind: "action",
        actionType: "",
        config: { continue_on_error: false },
      },
    },
  ];
  selectedNodeId.value = id;
}

function deleteSelectedNode() {
  if (!selectedNodeId.value) return;
  const nodeId = selectedNodeId.value;
  nodes.value = nodes.value.filter((n) => n.id !== nodeId);
  edges.value = edges.value.filter((e) => e.source !== nodeId && e.target !== nodeId);
  selectedNodeId.value = "";
  selectedEdgeId.value = "";
  closeEdgeMenu();
}

function nextEdgeId(source, target) {
  const base = `e-${source}-${target}`;
  const used = new Set(edges.value.map((e) => String(e.id)));
  if (!used.has(base)) return base;
  let i = 1;
  while (used.has(`${base}-${i}`)) i += 1;
  return `${base}-${i}`;
}

function onConnect(params) {
  if (!params?.source || !params?.target) return;
  const edge = {
    id: nextEdgeId(params.source, params.target),
    source: params.source,
    target: params.target,
  };
  edges.value = [...edges.value, edge];
}

function onConnectStart(evt) {
  pendingSourceNodeId.value = evt?.nodeId || "";
}

function onConnectEnd(evt) {
  const isPane = evt?.target?.classList?.contains("vue-flow__pane");
  if (!isPane || !pendingSourceNodeId.value) {
    pendingSourceNodeId.value = "";
    return;
  }
  const host = document.querySelector(".flow-host");
  if (!host) {
    pendingSourceNodeId.value = "";
    return;
  }
  const rect = host.getBoundingClientRect();
  const x = Math.max(8, evt.clientX - rect.left);
  const y = Math.max(8, evt.clientY - rect.top);
  const flowPos = project({ x, y });
  createMenu.value = { visible: true, x, y, flowX: flowPos.x, flowY: flowPos.y };
  // connect-end may be followed by pane-click in the same gesture; keep menu open.
  suppressPaneClickUntil.value = Date.now() + 180;
}

function closeCreateMenu() {
  createMenu.value = { visible: false, x: 0, y: 0, flowX: 0, flowY: 0 };
  pendingSourceNodeId.value = "";
}

function closeEdgeMenu() {
  edgeMenu.value = { visible: false, x: 0, y: 0, edgeId: "" };
}

function createNodeFromMenu(kind) {
  if (!pendingSourceNodeId.value) return closeCreateMenu();
  const sourceId = pendingSourceNodeId.value;
  const nodeId = nextNodeId("action");
  const newNode = {
    id: nodeId,
    position: { x: createMenu.value.flowX, y: createMenu.value.flowY },
    data: {
      label: "Действие",
      kind: "action",
      actionType: "",
      config: { continue_on_error: false },
    },
  };
  nodes.value = [...nodes.value, newNode];
  edges.value = [
    ...edges.value,
    {
      id: nextEdgeId(sourceId, nodeId),
      source: sourceId,
      target: nodeId,
    },
  ];
  selectedNodeId.value = nodeId;
  closeCreateMenu();
}

function onNodeClick(evt) {
  selectedEdgeId.value = "";
  closeEdgeMenu();
  selectedNodeId.value = evt?.node?.id || "";
}

function onPaneClick() {
  if (Date.now() < suppressPaneClickUntil.value) return;
  closeCreateMenu();
  closeEdgeMenu();
  selectedNodeId.value = "";
  selectedEdgeId.value = "";
}

function onEdgeClick(event, edge) {
  closeCreateMenu();
  const edgeId = String(edge?.id || "");
  if (!edgeId) return;
  selectedNodeId.value = "";
  selectedEdgeId.value = edgeId;
  const host = document.querySelector(".flow-host");
  if (!host) return;
  const rect = host.getBoundingClientRect();
  const x = clamp((event?.clientX || rect.left + 80) - rect.left, 8, Math.max(8, rect.width - 120));
  const y = clamp((event?.clientY || rect.top + 40) - rect.top, 8, Math.max(8, rect.height - 40));
  edgeMenu.value = { visible: true, x, y, edgeId };
}

function deleteEdgeFromMenu() {
  const edgeId = String(edgeMenu.value.edgeId || "");
  if (!edgeId) return closeEdgeMenu();
  edges.value = edges.value.filter((e) => String(e.id) !== edgeId);
  if (selectedEdgeId.value === edgeId) selectedEdgeId.value = "";
  closeEdgeMenu();
}

function deleteSelectedEdge() {
  const edgeId = String(selectedEdgeId.value || "");
  if (!edgeId) return;
  edges.value = edges.value.filter((e) => String(e.id) !== edgeId);
  if (String(edgeMenu.value.edgeId || "") === edgeId) closeEdgeMenu();
  selectedEdgeId.value = "";
}

function isTypingTarget(target) {
  const el = target instanceof Element ? target : null;
  if (!el) return false;
  if (el.closest("input, textarea, select")) return true;
  return !!el.closest("[contenteditable='true']");
}

function onGlobalKeydown(event) {
  if (event.defaultPrevented) return;
  if (event.key !== "Delete" && event.key !== "Backspace") return;
  if (isTypingTarget(event.target)) return;

  if (selectedEdgeId.value) {
    event.preventDefault();
    deleteSelectedEdge();
    return;
  }
  if (selectedNodeId.value) {
    event.preventDefault();
    deleteSelectedNode();
  }
}

function getCookie(name) {
  const pref = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const c = part.trim();
    if (c.startsWith(pref)) return decodeURIComponent(c.slice(pref.length));
  }
  return "";
}

function isTriggerNode(node) {
  if (!node) return false;
  return node.type === "input" || node?.data?.kind === "trigger";
}

function validateFlowData() {
  const nodeMap = new Map(nodes.value.map((n) => [String(n.id), n]));
  const incoming = new Map();
  const outgoing = new Map();
  const errors = [];

  for (const node of nodes.value) {
    const id = String(node.id || "");
    incoming.set(id, []);
    outgoing.set(id, []);
  }

  for (const edge of edges.value) {
    const source = String(edge?.source || "");
    const target = String(edge?.target || "");
    if (!nodeMap.has(source) || !nodeMap.has(target)) {
      errors.push("Есть связь с несуществующим узлом.");
      continue;
    }
    outgoing.get(source).push(target);
    incoming.get(target).push(source);
  }

  const triggerNodes = nodes.value.filter((node) => isTriggerNode(node));
  if (!triggerNodes.length) {
    errors.push("Добавьте хотя бы один Trigger.");
  }

  for (const trigger of triggerNodes) {
    const triggerId = String(trigger.id);
    if ((incoming.get(triggerId) || []).length > 0) {
      const label = trigger?.data?.label || triggerId;
      errors.push(`Trigger "${label}" должен быть в начале графа (без входящих связей).`);
    }
  }

  // Basic DAG check for predictable execution order.
  const indegree = new Map();
  for (const node of nodes.value) {
    const id = String(node.id || "");
    indegree.set(id, (incoming.get(id) || []).length);
  }
  const queue = [];
  for (const [nodeId, deg] of indegree.entries()) {
    if (deg === 0) queue.push(nodeId);
  }
  let visited = 0;
  while (queue.length) {
    const current = queue.shift();
    visited += 1;
    for (const next of outgoing.get(current) || []) {
      const deg = (indegree.get(next) || 0) - 1;
      indegree.set(next, deg);
      if (deg === 0) queue.push(next);
    }
  }
  if (visited !== nodes.value.length) {
    errors.push("Граф содержит цикл. Поддерживается только DAG.");
  }

  return errors;
}

async function save() {
  if (!props.saveUrl) return;
  saveMsg.value = "";
  const validationErrors = validateFlowData();
  if (validationErrors.length) {
    saveMsg.value = validationErrors[0];
    return;
  }
  saving.value = true;
  try {
    const body = {
      flow_data: {
        nodes: nodes.value,
        edges: edges.value,
      },
    };
    const r = await fetch(props.saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || r.statusText);
    saveMsg.value = "Сохранено";
    setTimeout(() => {
      saveMsg.value = "";
    }, 2500);
  } catch (err) {
    saveMsg.value = err.message || "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  try {
    const uiMode = String(localStorage.getItem(UI_MODE_LS_KEY) || "").trim().toLowerCase();
    if (uiMode === "advanced" || uiMode === "simple") {
      editorUiMode.value = uiMode;
    }
  } catch (_) {
    // ignore storage issues
  }

  const m = mergeInitial(props.initial || {});
  nodes.value = (m.nodes || []).map((n) => {
    if (!n) return n;
    const data = n.data || {};
    if (isTriggerNode(n)) {
      const triggerType = (data.triggerType || "webhook").trim?.() ? data.triggerType : "webhook";
      const normalized = {
        ...n,
        type: n.type || "input",
        data: {
          ...data,
          kind: "trigger",
          triggerType,
        },
      };
      if (triggerType === "email" && !normalized.data.emailConfig) {
        normalized.data.emailConfig = {
          imap_host: "",
          imap_port: 993,
          username: "",
          password: "",
          mailbox: "INBOX",
          max_messages: 5,
        };
      }
      return normalized;
    }
    return {
      ...n,
      data: {
        ...data,
        kind: data.kind || "action",
        config: data.config || { continue_on_error: false },
      },
    };
  });
  edges.value = m.edges;

  const editorWidth = getEditorWidth();
  let initialWorkArea = editorWidth;
  let initialSide = 320;
  try {
    const fromLsWorkArea = Number(localStorage.getItem(LS_WORK_AREA_WIDTH));
    const fromLsSide = Number(localStorage.getItem(LS_SIDE_WIDTH));
    if (Number.isFinite(fromLsWorkArea) && fromLsWorkArea > 0) {
      initialWorkArea = clamp(fromLsWorkArea, OUTER_MIN_WIDTH, editorWidth);
    }
    if (Number.isFinite(fromLsSide) && fromLsSide > 0) {
      initialSide = fromLsSide;
    }
  } catch (_) {
    // ignore storage errors
  }
  workAreaWidth.value = initialWorkArea;
  sideWidth.value = clamp(initialSide, SIDE_MIN_WIDTH, getMaxSideWidth(initialWorkArea));
  window.addEventListener("keydown", onGlobalKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("mousemove", onResizeMove);
  window.removeEventListener("mouseup", onResizeEnd);
  window.removeEventListener("keydown", onGlobalKeydown);
});
</script>

<style>
@import "@vue-flow/core/dist/style.css";
@import "@vue-flow/core/dist/theme-default.css";

.editor-wrap {
  display: flex;
  flex-direction: column;
  height: min(82vh, 820px);
  min-height: 520px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
}

.work-area-wrap {
  display: flex;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #fff;
  border-bottom: 1px solid #eee;
}

.toolbar .title {
  flex: 1;
  font-weight: 600;
}

.btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: #111;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
}

.btn--ghost {
  background: #fff;
  color: #111;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.msg {
  font-size: 14px;
  color: #0a0;
}

.flow-host {
  flex: 1;
  min-height: 0;
  position: relative;
}

.flow {
  width: 100%;
  height: 100%;
}

.work-area {
  display: flex;
  flex: 1;
  min-height: 0;
  margin: 0 auto;
  min-width: 0;
}

.side {
  border-left: 1px solid #eee;
  background: #fff;
  padding: 12px;
  overflow: auto;
  min-width: 0;
}

.resize-handle {
  border: 0;
  background: transparent;
  padding: 0;
  margin: 0;
  cursor: ew-resize;
}

.resize-handle--outer {
  width: 12px;
  position: relative;
}

.resize-handle--outer::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 5px;
  width: 2px;
  background: #e5e7eb;
}

.resize-handle--outer:hover::before,
.resize-handle--outer:focus-visible::before {
  background: #ff4a00;
}

.resize-handle--inner {
  width: 10px;
  border-left: 1px solid #eee;
  border-right: 1px solid #eee;
  background: #fafafa;
}

.resize-handle--inner:hover,
.resize-handle--inner:focus-visible {
  background: #fff2eb;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.field--inline {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.field input,
.field select,
.field textarea {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 7px 8px;
}

.field textarea {
  resize: vertical;
}

.segmented {
  display: inline-flex;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
}

.segmented__btn {
  border: 0;
  background: #fff;
  color: #111;
  cursor: pointer;
  padding: 6px 10px;
  font-size: 13px;
}

.segmented__btn--active {
  background: #ff4a00;
  color: #fff;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #fff;
  color: #111;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
}

.chip:hover {
  border-color: #ff4a00;
  color: #ff4a00;
}

.checks {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
}

.check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.kv-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 6px;
  margin-bottom: 6px;
}

.hint {
  color: #666;
  font-size: 13px;
}

.hint--error {
  color: #dc2626;
}

.card-lite {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fafafa;
  padding: 10px;
  margin-top: 12px;
}

.card-lite__title {
  font-weight: 600;
  margin-bottom: 8px;
}

.btn-row {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}

.create-menu {
  position: absolute;
  z-index: 15;
  display: flex;
  gap: 6px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}
</style>
