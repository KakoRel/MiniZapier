<template>
  <div class="editor-wrap">
    <div class="toolbar">
      <span class="title">{{ workflowName }}</span>
      <button type="button" class="btn btn--ghost" @click="addTriggerNode">+ Trigger</button>
      <button type="button" class="btn btn--ghost" @click="addActionNode">+ Action</button>
      <button type="button" class="btn btn--ghost" :disabled="!selectedNodeId" @click="deleteSelectedNode">Delete selected</button>
      <button type="button" class="btn" :disabled="saving || !saveUrl" @click="save">
        {{ saving ? "Сохранение…" : "Сохранить" }}
      </button>
      <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
    </div>
    <div class="work-area">
      <div class="flow-host">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          fit-view-on-init
          class="flow"
          :min-zoom="0.2"
          :max-zoom="2"
          @node-click="onNodeClick"
        >
          <Background pattern-color="#aaa" :gap="16" />
          <Controls />
        </VueFlow>
      </div>
      <aside class="side">
        <h3>Настройка узла</h3>
        <p v-if="!selectedNodeId" class="hint">Выберите узел на схеме</p>
        <template v-else>
          <label class="field">
            <span>Название</span>
            <input v-model.trim="selectedLabel" type="text" />
          </label>
          <template v-if="selectedNode?.data?.kind === 'trigger'">
            <label class="field">
              <span>Тип триггера</span>
              <select v-model="selectedTriggerType">
                <option value="webhook">webhook</option>
                <option value="cron">cron</option>
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

            <p v-if="selectedTriggerType === 'webhook'" class="hint">Webhook URL показывается на странице редактора.</p>
          </template>

          <template v-else>
            <label class="field">
              <span>Тип действия</span>
              <select v-model="selectedActionType">
                <option value="">passthrough</option>
                <option value="http">http</option>
                <option value="telegram">telegram</option>
                <option value="email">email</option>
                <option value="sql">sql</option>
              </select>
            </label>
            <label v-if="selectedActionType === 'http'" class="field">
              <span>HTTP URL</span>
              <input v-model.trim="selectedHttpUrl" type="url" placeholder="https://api.example.com/hook" />
            </label>
            <template v-if="selectedActionType === 'telegram'">
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
            <template v-if="selectedActionType === 'email'">
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
            <template v-if="selectedActionType === 'sql'">
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
          </template>
        </template>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { VueFlow } from "@vue-flow/core";
import { ref, onMounted, computed } from "vue";

const props = defineProps({
  workflowId: { type: Number, required: true },
  workflowName: { type: String, default: "" },
  initial: { type: Object, default: () => ({}) },
  saveUrl: { type: String, default: "" },
});

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
      config: { url: "" },
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
        config: {},
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
}

function onNodeClick(evt) {
  selectedNodeId.value = evt?.node?.id || "";
}

function getCookie(name) {
  const pref = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const c = part.trim();
    if (c.startsWith(pref)) return decodeURIComponent(c.slice(pref.length));
  }
  return "";
}

async function save() {
  if (!props.saveUrl) return;
  saveMsg.value = "";
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
  const m = mergeInitial(props.initial || {});
  nodes.value = m.nodes;
  edges.value = m.edges;
});
</script>

<style>
@import "@vue-flow/core/dist/style.css";
@import "@vue-flow/core/dist/theme-default.css";

.editor-wrap {
  display: flex;
  flex-direction: column;
  height: min(70vh, 640px);
  min-height: 420px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: #fafafa;
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
}

.flow {
  width: 100%;
  height: 100%;
}

.work-area {
  display: flex;
  flex: 1;
  min-height: 0;
}

.side {
  width: 260px;
  border-left: 1px solid #eee;
  background: #fff;
  padding: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.field input,
.field select {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 7px 8px;
}

.hint {
  color: #666;
  font-size: 13px;
}
</style>
