import { createApp } from "vue";
import App from "./App.vue";

function readPayload() {
  const el = document.getElementById("workflow-editor-data");
  if (!el?.textContent) {
    return {
      workflowId: 0,
      workflowName: "Dev",
      flow_data: {},
      saveUrl: "",
    };
  }
  try {
    return JSON.parse(el.textContent);
  } catch {
    return {};
  }
}

const root = document.getElementById("workflow-editor-root");
if (root) {
  const p = readPayload();
  createApp(App, {
    workflowId: p.workflowId,
    workflowName: p.workflowName || "",
    initial: p.flow_data || {},
    saveUrl: p.saveUrl || "",
  }).mount("#workflow-editor-root");
}
