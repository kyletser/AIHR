<template>
  <div class="min-h-screen bg-[#f8f7f4]">
    <router-view />
  </div>
</template>
<script setup>import { useAuthStore } from './stores/auth'; const a=useAuthStore(); a.initAuth()</script>
