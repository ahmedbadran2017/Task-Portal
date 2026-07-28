# Embedding the Task Hub reporter in a portal

`TaskHubWidget.vue` is a self-contained drop-in: floating "⚑ Report" button +
modal that posts to `task_hub.api.tickets.create_ticket`. No imports from the
host portal, own CSRF handling, scoped styles — copying the file is the whole
integration.

## Install (per portal)

1. Copy `TaskHubWidget.vue` into the portal's `frontend/src/components/`.
2. Mount it once in `App.vue` with the portal's name:

```vue
<template>
  <div>                                   <!-- keep the portal's existing root -->
    <router-view />
    <TaskHubWidget portal="Logistics" />  <!-- Supplier | Accounting | Logistics | Purchasing -->
  </div>
</template>

<script setup>
import TaskHubWidget from "@/components/TaskHubWidget.vue";
</script>
```

3. Rebuild the bundle (`cd frontend && npm run build`) and commit.

⚠️ Accounting and Supplier keep a **single root element** in `App.vue` on
purpose (fragment roots crash their production builds — see the comments in
those files). Mount the widget *inside* the existing root.

## Optional: richer record context

By default the ticket links to the current URL + document title. A page that
knows the record in view can pass it explicitly:

```vue
<TaskHubWidget
  portal="Purchasing"
  :linked="{
    doctype: 'Selection',
    name: selection.name,
    label: selection.title,
    url: `/purchasing/selections/${selection.name}`,
  }"
/>
```

## Updating

The canonical copy lives here (`task_hub/integration/`). If it changes, re-copy
the file into each portal — it is intentionally dependency-free so the copy
never drifts behind a shared package.
