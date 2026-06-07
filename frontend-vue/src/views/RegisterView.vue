<template>
  <div class="min-h-screen bg-[#f8f7f4] flex items-center justify-center p-6">
    <div class="w-full max-w-sm">
      <div class="text-center mb-10"><span class="text-6xl block mb-4">🎯</span><h1 class="text-3xl font-bold text-gray-900">OFFER<span class="text-[#d4a853]">CATCHER</span></h1></div>
      <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-8">
        <h2 class="text-lg font-bold text-gray-900 mb-6">注册</h2>
        <div v-if="err" class="mb-4 p-3 bg-red-50 border border-red-100 rounded-xl text-red-500 text-xs">{{ err }}</div>
        <div class="space-y-4">
          <input v-model="u" placeholder="用户名（至少2位）" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-[#d4a853]" @keyup.enter="go">
          <input v-model="p" type="password" placeholder="密码（至少3位）" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-[#d4a853]" @keyup.enter="go">
          <button @click="go" :disabled="l" class="w-full py-3 bg-gray-900 text-white rounded-xl font-bold text-sm hover:bg-gray-800 disabled:opacity-40">{{ l?'注册中...':'注册' }}</button>
        </div>
        <p class="text-center text-gray-400 text-xs mt-6">已有账号？<router-link to="/login" class="text-[#d4a853] hover:underline">登录</router-link></p>
      </div>
    </div>
  </div>
</template>
<script setup>import{ref}from'vue';import{useRouter}from'vue-router';import{useAuthStore}from'../stores/auth';const r=useRouter(),a=useAuthStore(),u=ref(''),p=ref(''),err=ref(''),l=ref(false);async function go(){l.value=true;try{await a.register(u.value,p.value);r.push('/')}catch(e){err.value=e.response?.data?.detail||'注册失败'};l.value=false}</script>
