<template>
  <header v-if="currentUser" class="app-toolbar">
    <div class="account-bar">
      <router-link class="app-brand" to="/" aria-label="记账首页"><span class="app-mark"><BookOpen :size="20" :stroke-width="1.7" /></span><span>记账</span></router-link>
      <nav class="app-tabs" aria-label="账本导航"><router-link to="/" :class="{ selected: $route.path === '/' }">总览</router-link><router-link to="/ledger" :class="{ selected: ['/ledger', '/expense', '/income'].includes($route.path) }">账单</router-link><router-link to="/people" :class="{ selected: $route.path === '/people' }">人情</router-link><router-link to="/balance" :class="{ selected: $route.path === '/balance' }">统计</router-link></nav>
      <div class="toolbar-actions"><DraftsMenu /><router-link class="toolbar-key" to="/keys" aria-label="API Key 设置"><KeyRound :size="17" /><span>AI 设置</span></router-link><router-link class="toolbar-account" to="/account" :aria-label="`${currentUser.username} · 账号`"><span class="account-avatar"><UserRound :size="17" /></span><span class="account-name">{{ currentUser.username }}</span></router-link></div>
    </div>
  </header>
  <div v-if="globalError" class="connection-error" role="alert">{{ globalError }} <button @click="retry">重试</button></div>
  <router-view :key="`${currentUser?.id || 'guest'}:${$route.path}`" />
  <EntryEditor v-if="currentUser && editorRequest" :key="`${currentUser.id}:${editorRequest.key}`" :request="editorRequest" />
</template>
<script setup>
import { currentUser, globalError } from "./services/api";
import { BookOpen, KeyRound, UserRound } from "@lucide/vue";
import DraftsMenu from "./components/DraftsMenu.vue";
import EntryEditor from "./components/EntryEditor.vue";
import { editorRequest } from "./services/editor";
function retry() { location.reload(); }
</script>
