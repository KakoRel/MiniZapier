<template>
  <div class="editor-wrap">
    <div class="toolbar">
      <span class="title">{{ workflowName }}</span>
      <button type="button" class="btn" :disabled="saving || !saveUrl" @click="save">
        {{ saving ? "Сохранение…" : "Сохранить" }}
      </button>
      <span v-if="saveMsg" class="msg">{{ saveMsg }}</span>
    </div>
    <div class="flow-host">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        fit-view-on-init
        class="flow"
        :min-zoom="0.2"
        :max-zoom="2"
      >
        <Background pattern-color="#aaa" :gap="16" />
        <Controls />
      </VueFlow>
    </div>
  </div>
</template>

<script setup>
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { VueFlow } from "@vue-flow/core";
import { ref, onMounted } from "vue";

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
    data: { label: "Триггер (Webhook)" },
  },
  {
    id: "action-1",
    position: { x: 80, y: 160 },
    data: { label: "Действие (HTTP)" },
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
</style>
