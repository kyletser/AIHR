<template>
  <div class="min-h-screen bg-[#f8f7f4] flex items-center justify-center p-6">
    <div class="w-full max-w-sm">
      <div class="text-center mb-10">
        <span class="text-6xl block mb-4">🎯</span>
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">OFFER<span class="text-[#d4a853]">CATCHER</span></h1>
        <p class="text-gray-400 text-xs">AI 求职匹配引擎</p>
      </div>
      <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-8">
        <h2 class="text-lg font-bold text-gray-900 mb-6">登录</h2>
        <div v-if="error" class="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-red-500 text-xs">{{ error }}</div>
        <div class="space-y-4">
          <input v-model="username" placeholder="用户名" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-[#d4a853]" @keyup.enter="handleLogin">
          <input v-model="password" type="password" placeholder="密码" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-[#d4a853]" @keyup.enter="handleLogin">
          <button @click="handleLogin" :disabled="loading" class="w-full py-3 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 transition-colors disabled:opacity-40">{{ loading?'登录中...':'登录' }}</button>
        </div>
        <p class="text-center text-gray-400 text-xs mt-6">没有账号？<router-link to="/register" class="text-[#d4a853] hover:underline">注册</router-link></p>
      </div>
      <p class="text-center text-gray-400 text-xs mt-6">管理员: admin / admin</p>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'; import { useRouter } from 'vue-router'; import { useAuthStore } from '../stores/auth'
const r=useRouter(); const a=useAuthStore(); const u=ref(''),p=ref(''),err=ref(''),l=ref(false)
async function handleLogin(){l.value=true;try{await a.login(u.value,p.value);r.push('/')}catch(e){err.value=e.response?.data?.detail||'登录失败'};l.value=false}
</script>
