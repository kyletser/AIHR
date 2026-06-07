<template>
  <div class="min-h-screen bg-[#f8f7f4] text-gray-900">
    <header class="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
      <div class="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        <button @click="router.push('/')" class="text-sm text-gray-500 hover:text-gray-900">返回工作台</button>
        <div class="text-sm font-bold tracking-tight"><span>OFFER</span><span class="text-[#d4a853]">CATCHER</span></div>
        <span class="text-xs text-gray-400">{{ auth?.username }}</span>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-8 py-10">
      <div v-if="loading" class="rounded-2xl bg-white border border-gray-200 p-8 text-center text-gray-400">加载分析结果...</div>
      <div v-else-if="err" class="rounded-2xl bg-red-50 border border-red-100 p-8 text-red-500">{{ err }}</div>
      <div v-else-if="result" class="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-6 items-start">
        <section class="space-y-6">
          <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-8">
            <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
              <div>
                <div class="text-xs text-gray-400 uppercase tracking-widest mb-2">匹配分析</div>
                <p class="text-sm text-gray-500 leading-relaxed max-w-2xl">{{ result.match_verdict }}</p>
                <p v-if="result.killer_sentence" class="text-[#b8862e] text-sm mt-3 font-medium">{{ result.killer_sentence }}</p>
              </div>
              <div class="flex items-center gap-5">
                <div class="w-32 h-32 rounded-full border-2 border-[#d4a853]/30 flex items-center justify-center">
                  <span class="text-5xl font-bold font-mono text-[#d4a853]">{{ result.overall_score }}</span>
                </div>
                <canvas ref="rc" class="hidden md:block"></canvas>
              </div>
            </div>
          </div>

          <div v-if="result.strategy" class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
              <div>
                <h2 class="text-sm font-bold mb-2">投递策略</h2>
                <p class="text-xs text-gray-500 leading-relaxed">{{ result.strategy.insight || result.strategy.positioning }}</p>
              </div>
              <span class="px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap" :class="actionClass(result.strategy.recommended_action)">
                {{ result.strategy.recommended_action }}
              </span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <div class="text-xs text-gray-400 uppercase tracking-widest mb-2">风险雷达</div>
                <div class="space-y-2">
                  <div v-for="(r,i) in result.strategy.risk_radar" :key="i" class="rounded-xl border p-3" :class="riskClass(r.level)">
                    <div class="text-sm font-semibold">{{ r.label }}</div>
                    <p class="text-xs text-gray-500 mt-1">{{ r.reason }}</p>
                  </div>
                  <p v-if="!result.strategy.risk_radar?.length" class="text-xs bg-emerald-50 text-emerald-700 rounded-xl p-3">暂无明显高风险项。</p>
                </div>
              </div>
              <div>
                <div class="text-xs text-gray-400 uppercase tracking-widest mb-2">补短 Sprint</div>
                <div class="space-y-2">
                  <div v-for="(s,i) in result.strategy.learning_sprints" :key="i" class="rounded-xl bg-gray-50 border border-gray-100 p-3">
                    <div class="text-sm font-semibold">{{ s.target }}</div>
                    <p class="text-xs text-gray-500 mt-1">{{ s.plan }}</p>
                    <div class="text-xs text-[#b8862e] mt-2">{{ s.effort }}</div>
                  </div>
                  <p v-if="!result.strategy.learning_sprints?.length" class="text-xs bg-gray-50 rounded-xl p-3 text-gray-500">优先整理经历证据。</p>
                </div>
              </div>
              <div>
                <div class="text-xs text-gray-400 uppercase tracking-widest mb-2">简历聚焦</div>
                <div class="space-y-2">
                  <div v-for="(f,i) in result.strategy.resume_focus" :key="i" class="rounded-xl bg-blue-50 border border-blue-100 p-3 text-xs text-gray-600">{{ f }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="(label,key) in dimLabels" :key="key" class="rounded-2xl border border-gray-100 bg-white shadow-sm p-5">
              <div class="flex items-center justify-between mb-3">
                <span class="text-xs text-gray-400 uppercase tracking-widest">{{ label }}</span>
                <span class="text-2xl font-bold font-mono" :class="sc(dim(key))">{{ dim(key) }}</span>
              </div>
              <div class="w-full bg-gray-100 rounded-full h-1.5 mb-3 overflow-hidden">
                <div class="h-1.5 rounded-full" :class="dc(dim(key))" :style="{width:dim(key)+'%'}"></div>
              </div>
              <p class="text-xs text-gray-500 leading-relaxed">{{ detail(key) }}</p>
            </div>
          </div>

          <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
            <h2 class="text-sm font-bold mb-4">差距分析</h2>
            <div class="space-y-3">
              <div v-for="(g,i) in result.gap_analysis" :key="i" class="rounded-xl p-4" :class="gb(g.severity)">
                <div class="flex justify-between gap-3 mb-2">
                  <span class="font-semibold text-sm">{{ g.gap }}</span>
                  <span class="text-xs px-3 py-1 rounded-full whitespace-nowrap" :class="bb(g.severity)">{{ g.severity }} · {{ g.effort }}</span>
                </div>
                <p class="text-xs text-gray-500">{{ g.suggestion }}</p>
              </div>
            </div>
          </div>

          <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
              <div>
                <h2 class="text-sm font-bold mb-2">简历版本管理</h2>
                <p class="text-xs text-gray-500">{{ result.resume_version_preview?.source_note }}</p>
              </div>
              <button @click="saveResumeVersion" class="text-xs px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800">{{ versionMsg || '保存当前版本' }}</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div class="space-y-2">
                <div v-for="(f,i) in result.resume_version_preview?.target_focus || []" :key="i" class="rounded-xl bg-gray-50 border border-gray-100 p-3 text-xs text-gray-600">{{ f }}</div>
              </div>
              <div class="space-y-2">
                <div v-for="v in savedVersions.slice(0,4)" :key="v.version_id" class="rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                  <div class="text-sm font-semibold">{{ v.name }}</div>
                  <div class="text-xs text-gray-500 mt-1">{{ v.target_role || '目标岗位' }} · {{ v.created_at?.slice(0,10) }}</div>
                </div>
                <p v-if="!savedVersions.length" class="text-xs text-gray-500 bg-gray-50 rounded-xl p-3">还没有保存过版本。</p>
              </div>
            </div>
          </div>

        </section>

        <aside class="xl:sticky xl:top-24 rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div class="p-5 border-b border-gray-100">
            <h2 class="text-sm font-bold mb-1">与智能体对话</h2>
            <p class="text-xs text-gray-400">基于当前简历、JD和匹配结果继续追问。</p>
          </div>
          <div class="h-[520px] overflow-y-auto p-4 space-y-3 bg-gray-50">
            <div v-for="(m,i) in chatMessages" :key="i" class="flex" :class="m.role==='user'?'justify-end':'justify-start'">
              <div class="max-w-[86%] rounded-2xl px-4 py-3 text-sm leading-relaxed" :class="m.role==='user'?'bg-gray-900 text-white':'bg-white border border-gray-100 text-gray-700'">
                {{ m.content }}
                <div v-if="m.actions?.length" class="mt-3 space-y-1">
                  <div v-for="a in m.actions" :key="a" class="text-xs text-[#b8862e]">{{ a }}</div>
                </div>
              </div>
            </div>
            <div v-if="chatting" class="text-xs text-gray-400">智能体思考中...</div>
          </div>
          <div class="p-4 border-t border-gray-100">
            <textarea v-model="chatInput" rows="3" placeholder="问：我应该投这个岗位吗？简历先改哪里？还缺什么信息？"
              class="w-full resize-none rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm focus:outline-none focus:border-[#d4a853]/50"></textarea>
            <button @click="sendChat" :disabled="!chatInput.trim()||chatting" class="w-full mt-2 rounded-xl bg-gray-900 text-white py-2.5 text-sm font-semibold disabled:bg-gray-200 disabled:text-gray-400">发送</button>
          </div>
        </aside>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, shallowRef, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const route=useRoute(),router=useRouter(),auth=useAuthStore()
const result=shallowRef(null),loading=ref(true),err=ref(''),rc=ref(null),savedVersions=ref([]),versionMsg=ref('')
const chatInput=ref(''),chatting=ref(false)
const chatMessages=ref([{role:'assistant',content:'我已经读到这次匹配结果了。你可以问我：该不该投、先改哪段简历、目标岗位怎么选、缺的信息怎么补。'}])
let radarChart=null

const dimLabels={hard_skills:'关键能力',projects:'经历证据',education:'门槛资质',soft_skills:'通用素质',industry:'行业场景',growth:'成长潜力'}
function dim(k){return result.value?.dimensions?.[k]?.score||0}
function detail(k){return result.value?.dimensions?.[k]?.detail||result.value?.dimensions?.[k]?.reason||''}
function dc(s){return s>=80?'bg-emerald-400':s>=60?'bg-[#d4a853]':'bg-red-400'}
function sc(s){return s>=80?'text-emerald-500':s>=60?'text-[#d4a853]':'text-red-500'}
function gb(s){return s==='critical'?'bg-red-50 border border-red-100':s==='moderate'?'bg-amber-50 border border-amber-100':'bg-blue-50 border border-blue-100'}
function bb(s){return s==='critical'?'bg-red-100 text-red-600':s==='moderate'?'bg-amber-100 text-amber-600':'bg-blue-100 text-blue-600'}
function riskClass(l){return l==='high'?'bg-red-50 border-red-100 text-red-700':l==='medium'?'bg-amber-50 border-amber-100 text-amber-700':'bg-blue-50 border-blue-100 text-blue-700'}
function actionClass(a){return a==='优先投递'?'bg-emerald-100 text-emerald-700':a==='优化后投递'?'bg-[#d4a853]/10 text-[#b8862e]':a==='谨慎投递'?'bg-amber-100 text-amber-700':'bg-red-100 text-red-700'}

async function renderRadar(){const c=rc.value;if(!c||!result.value)return;const{Chart}=await import('chart.js/auto');c.width=160;c.height=160;const ctx=c.getContext('2d');if(!ctx)return;if(radarChart)radarChart.destroy();const keys=Object.keys(dimLabels);radarChart=new Chart(ctx,{type:'radar',data:{labels:Object.values(dimLabels),datasets:[{data:keys.map(k=>dim(k)),backgroundColor:'rgba(212,168,83,0.08)',borderColor:'#d4a853',borderWidth:2,pointRadius:2}]},options:{responsive:false,plugins:{legend:{display:false}},scales:{r:{beginAtZero:true,max:100,ticks:{display:false},pointLabels:{font:{size:8},color:'#6b7280'},grid:{color:'#e5e7eb'},angleLines:{color:'#e5e7eb'}}}}})}
async function loadVersions(){try{const{data}=await axios.get('/api/resume-versions');savedVersions.value=data.versions||[]}catch(e){}}
async function loadResult(){loading.value=true;const id=route.params.matchId;try{const cached=sessionStorage.getItem(`match:${id}`);if(cached){result.value=JSON.parse(cached)}else{const{data}=await axios.get(`/api/match-record/${id}`);result.value=data;sessionStorage.setItem(`match:${id}`,JSON.stringify(data))}await loadVersions();await nextTick();renderRadar()}catch(e){err.value=e.response?.data?.detail||e.message}loading.value=false}
async function saveResumeVersion(){if(!result.value?.resume_id||!result.value?.resume_version_preview)return;try{await axios.post('/api/resume-versions',{resume_id:result.value.resume_id,jd_id:result.value.jd_id,match_id:result.value.match_id,name:result.value.resume_version_preview.version_name,target_role:result.value.resume_version_preview.version_name,content_json:result.value.resume_version_preview,score_snapshot:result.value.resume_version_preview.score_snapshot});versionMsg.value='已保存';await loadVersions();setTimeout(()=>versionMsg.value='',1600)}catch(e){versionMsg.value='保存失败'}}
async function sendChat(){const text=chatInput.value.trim();if(!text)return;chatMessages.value.push({role:'user',content:text});chatInput.value='';chatting.value=true;try{const{data}=await axios.post('/api/agent/chat',{match_id:result.value.match_id,message:text,messages:chatMessages.value});chatMessages.value.push({role:'assistant',content:data.answer||'我暂时没有生成有效回复。',actions:data.suggested_actions||[]})}catch(e){chatMessages.value.push({role:'assistant',content:e.response?.data?.detail||e.message})};chatting.value=false}
onMounted(loadResult)
</script>
