<template>
  <div class="min-h-screen bg-[#f8f7f4] text-gray-900">
    <header class="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-100">
      <div class="max-w-7xl mx-auto px-8 py-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
          <span class="text-2xl">🎯</span>
          <span class="text-lg font-bold tracking-tight">
            <span class="text-gray-900">OFFER</span><span class="text-[#d4a853]">CATCHER</span>
          </span>
        </div>
        <div class="flex items-center gap-6 text-sm text-gray-400">
          <span>{{ auth?.username }}</span>
          <button @click="logout" class="hover:text-red-500">退出</button>
        </div>
      </div>
    </header>

    <div class="max-w-7xl mx-auto px-8 py-12 space-y-10">
      <div class="flex gap-1">
        <div v-for="(s,i) in ['简历','JD','分析']" :key="i"
          class="flex-1 h-1 rounded-full transition-all duration-700"
          :class="i < currentStep ? 'bg-[#d4a853]' : i === currentStep ? 'bg-[#d4a853]/40' : 'bg-gray-100'"></div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-widest">简历上传</h2>
          </div>
          <div class="flex flex-wrap gap-2 mb-4">
            <button v-for="(l,k) in industries" :key="k" @click="industry=k"
              class="text-xs px-2.5 py-1 rounded-full transition-all"
              :class="industry===k ? 'bg-[#d4a853]/10 text-[#d4a853] border border-[#d4a853]/30' : 'text-gray-400 border border-gray-200 hover:border-gray-300'">{{ l }}</button>
          </div>
          <div v-if="savedResumes.length" class="flex flex-wrap gap-1.5 mb-3">
            <button v-for="r in savedResumes" :key="r.resume_id" @click="loadSaved(r.resume_id)"
              class="text-xs px-2 py-1 rounded border border-gray-200 text-gray-500 hover:text-[#d4a853] hover:border-[#d4a853]/30 transition-colors">{{ r.filename }}</button>
          </div>
          <div class="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all"
            :class="file?'border-emerald-400/30 bg-emerald-50':'border-gray-200 hover:border-gray-400'"
            @click="$refs.fi.click()" @dragover.prevent @drop.prevent="file=$event.dataTransfer.files[0]">
            <span class="text-3xl block mb-2">{{ fileIcon }}</span>
            <span class="text-gray-500 text-sm">{{ file ? file.name : '拖拽或点击选择文件' }}</span>
          </div>
          <input ref="fi" type="file" accept=".pdf,.docx,.doc" class="hidden" @change="file=$event.target.files[0]">
          <button @click="doExtract" :disabled="!file||uploading"
            class="w-full mt-3 py-2.5 rounded-xl text-sm font-semibold transition-all"
            :class="file&&!uploading?'bg-gray-900 text-white hover:bg-gray-800':'bg-gray-100 text-gray-400'">{{ uploading?'提取中...':file?'提取文本':'选择文件后提取' }}</button>
          <div v-if="upStatus" class="text-xs text-center mt-2" v-html="upStatus"></div>
        </div>

        <div class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="w-2 h-2 rounded-full bg-blue-400"></span>
            <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-widest">岗位描述</h2>
          </div>
          <textarea v-model="jdText" rows="6" placeholder="粘贴岗位描述..."
            class="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-900 placeholder-gray-400 resize-y focus:outline-none focus:border-[#d4a853]/50 focus:ring-1 focus:ring-[#d4a853]/20 transition-all"></textarea>
          <div class="flex flex-wrap gap-1.5 mt-2">
            <button v-for="(job,i) in jds" :key="i" @click="jdText=job.jd"
              class="text-xs px-2.5 py-1 rounded-full border border-gray-200 text-gray-400 hover:text-[#d4a853] hover:border-[#d4a853]/30 transition-colors">{{ job.label }}</button>
          </div>
        </div>
      </div>

      <div v-if="resumeText" class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs text-gray-400 uppercase tracking-widest">简历文本 · {{ resumeText.length }} 字符 · 可编辑</span>
          <button @click="resumeText=''" class="text-xs text-gray-400 hover:text-red-500">清空</button>
        </div>
        <textarea v-model="resumeText" class="w-full min-h-[200px] bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-900 leading-relaxed resize-y focus:outline-none focus:border-[#d4a853]/50 font-mono"></textarea>
      </div>

      <div class="text-center">
        <button @click="doAnalyze" :disabled="!ready||analyzing"
          class="px-12 py-4 rounded-2xl text-lg font-bold transition-all duration-300 shadow-sm"
          :class="ready&&!analyzing?'bg-gray-900 text-white hover:bg-gray-800 hover:scale-[1.02]':'bg-gray-100 text-gray-400'">
          <span v-if="analyzing" class="flex items-center gap-3"><span class="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>引擎分析中...</span>
          <span v-else>🚀 开始匹配分析</span>
        </button>
        <div v-if="err" class="mt-4 p-4 bg-red-50 border border-red-100 rounded-xl text-red-500 text-sm">{{ err }}</div>
      </div>

      <div v-if="result" class="space-y-10">
        <div class="text-center py-12">
          <div class="inline-flex items-center justify-center w-44 h-44 rounded-full border-2 border-[#d4a853]/30 relative mb-6">
            <div class="absolute inset-2 rounded-full border border-[#d4a853]/10"></div>
            <span class="text-7xl font-bold tracking-tighter text-[#d4a853] font-mono">{{ result.overall_score }}</span>
          </div>
          <p class="text-gray-500 text-sm max-w-lg mx-auto leading-relaxed">{{ result.match_verdict }}</p>
          <p v-if="result.killer_sentence" class="text-[#d4a853] text-sm mt-3 font-medium">⚡ {{ result.killer_sentence }}</p>
        </div>
        <div class="flex justify-center"><div class="w-full max-w-sm"><canvas ref="rc"></canvas></div></div>
        <div v-if="result.strategy" class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
          <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
            <div>
              <h3 class="text-sm font-bold text-gray-900 mb-2">投递策略</h3>
              <p class="text-xs text-gray-500 leading-relaxed max-w-2xl">{{ result.strategy.insight || result.strategy.positioning }}</p>
            </div>
            <span class="px-4 py-2 rounded-xl text-sm font-bold whitespace-nowrap" :class="actionClass(result.strategy.recommended_action)">
              {{ result.strategy.recommended_action }}
            </span>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div>
              <div class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">风险雷达</div>
              <div class="space-y-2">
                <div v-for="(r,i) in result.strategy.risk_radar" :key="i" class="rounded-xl border p-3" :class="riskClass(r.level)">
                  <div class="flex items-center justify-between gap-2 mb-1">
                    <span class="text-sm font-semibold">{{ r.label }}</span>
                    <span class="text-xs uppercase">{{ r.level }}</span>
                  </div>
                  <p class="text-xs text-gray-500 leading-relaxed">{{ r.reason }}</p>
                </div>
                <p v-if="!result.strategy.risk_radar?.length" class="text-xs text-emerald-600 bg-emerald-50 rounded-xl p-3">暂无明显高风险项，重点打磨表达即可。</p>
              </div>
            </div>
            <div>
              <div class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">补短 Sprint</div>
              <div class="space-y-2">
                <div v-for="(s,i) in result.strategy.learning_sprints" :key="i" class="rounded-xl bg-gray-50 border border-gray-100 p-3">
                  <div class="text-sm font-semibold text-gray-900">{{ s.target }}</div>
                  <p class="text-xs text-gray-500 leading-relaxed mt-1">{{ s.plan }}</p>
                  <div class="text-xs text-[#d4a853] mt-2">{{ s.effort }}</div>
                </div>
                <p v-if="!result.strategy.learning_sprints?.length" class="text-xs text-gray-500 bg-gray-50 rounded-xl p-3">没有必须先补的核心技能，优先整理项目证据。</p>
              </div>
            </div>
            <div>
              <div class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">简历聚焦</div>
              <div class="space-y-2">
                <div v-for="(f,i) in result.strategy.resume_focus" :key="i" class="rounded-xl bg-blue-50 border border-blue-100 p-3 text-xs text-gray-600 leading-relaxed">{{ f }}</div>
                <p v-if="!result.strategy.resume_focus?.length" class="text-xs text-gray-500 bg-gray-50 rounded-xl p-3">当前简历方向比较清晰，保持真实证据和量化表达。</p>
              </div>
            </div>
          </div>
        </div>
        <div v-if="result.resume_version_preview" class="rounded-2xl border border-gray-200 bg-white shadow-sm p-6">
          <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
            <div>
              <h3 class="text-sm font-bold text-gray-900 mb-2">简历版本管理</h3>
              <p class="text-xs text-gray-500 leading-relaxed">{{ result.resume_version_preview.source_note }}</p>
            </div>
            <button @click="saveResumeVersion" class="text-xs px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800">{{ versionMsg || '保存当前版本' }}</button>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div class="space-y-2">
              <div v-for="(f,i) in result.resume_version_preview.target_focus" :key="i" class="rounded-xl bg-gray-50 border border-gray-100 p-3 text-xs text-gray-600 leading-relaxed">{{ f }}</div>
            </div>
            <div class="space-y-2">
              <div v-for="v in savedVersions.slice(0,3)" :key="v.version_id" class="rounded-xl bg-emerald-50 border border-emerald-100 p-3">
                <div class="text-sm font-semibold text-gray-900">{{ v.name }}</div>
                <div class="text-xs text-gray-500 mt-1">{{ v.target_role || '目标岗位' }} · {{ v.created_at?.slice(0,10) }}</div>
              </div>
              <p v-if="!savedVersions.length" class="text-xs text-gray-500 bg-gray-50 rounded-xl p-3">还没有保存过版本。</p>
            </div>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="(label,key) in dimLabels" :key="key" class="rounded-2xl border border-gray-100 bg-white shadow-sm p-5 hover:shadow-md transition-all">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs text-gray-400 uppercase tracking-widest">{{ label }}</span>
              <span class="text-2xl font-bold font-mono" :class="sc(dim(key))">{{ dim(key) }}</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-1.5 mb-3 overflow-hidden"><div class="h-1.5 rounded-full transition-all duration-1000" :class="dc(dim(key))" :style="{width:dim(key)+'%'}"></div></div>
            <p class="text-xs text-gray-500 leading-relaxed">{{ detail(key) }}</p>
          </div>
        </div>
        <div>
          <h3 class="text-sm font-bold text-gray-900 mb-4">差距分析</h3>
          <div class="space-y-3">
            <div v-for="(g,i) in result.gap_analysis" :key="i" class="rounded-2xl p-5 transition-all hover:shadow-sm" :class="gb(g.severity)">
              <div class="flex justify-between mb-2"><span class="font-semibold text-sm">{{ g.gap }}</span><span class="text-xs px-3 py-1 rounded-full font-medium whitespace-nowrap" :class="bb(g.severity)">{{ g.severity }} · {{ g.effort }}</span></div>
              <p class="text-xs text-gray-500">💡 {{ g.suggestion }}</p>
            </div>
          </div>
        </div>
        <div>
          <h3 class="text-sm font-bold text-gray-900 mb-4">优化建议</h3>
          <div class="space-y-3">
            <div v-for="(s,i) in result.suggestions" :key="i" class="rounded-2xl border border-gray-200 bg-white shadow-sm p-5 hover:shadow-md transition-all">
              <div class="flex items-center gap-2 mb-3">
                <span class="text-xs px-2 py-0.5 rounded-full font-medium" :class="tb(s.type)">{{ s.type }}</span>
                <span class="font-semibold text-sm">{{ s.section }} › {{ s.field }}</span>
              </div>
              <div v-if="s.original" class="text-xs text-red-500 bg-red-50 p-3 rounded-xl mb-2 font-mono leading-relaxed">— {{ s.original }}</div>
              <div class="text-sm text-emerald-600 bg-emerald-50 p-3 rounded-xl mb-2 leading-relaxed">+ {{ s.suggested }}</div>
              <p class="text-xs text-gray-400">理由：{{ s.reason }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="text-center text-xs text-gray-400 py-6 border-t border-gray-200">
        <button @click="doClear" class="hover:text-red-500">🗑 清空数据</button>
        <span v-if="cs" class="ml-4">{{ cs }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, shallowRef, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const router=useRouter(); const auth=useAuthStore()
const industry=ref('internet'),file=ref(null),uploading=ref(false),upStatus=ref(''),resumeText=ref(''),jdText=ref(''),analyzing=ref(false),err=ref(''),result=shallowRef(null),cs=ref(''),savedResumes=ref([]),savedVersions=ref([]),versionMsg=ref('')
let radarChart=null; const rc=ref(null)
function logout(){auth.logout();router.push('/login')}

const industries={internet:'💻技术/产品',finance:'💰金融财会',government:'🏛️公共事务',education:'📚教育培训',medical:'🏥医疗健康',manufacturing:'⚙️制造供应链',sales:'📈销售市场',design:'🎨设计传媒'}
const jds=computed(()=>({internet:[{label:'后端开发',jd:'【岗位】后端开发工程师\n【职责】1.负责业务系统开发维护 2.参与接口设计、性能优化和线上问题排查\n【要求】1.计算机相关本科及以上 2.Python/Go/Java至少一种 3.熟悉MySQL、Redis、Linux 4.了解Docker优先 5.具备协作沟通和问题定位能力'},{label:'产品运营',jd:'【岗位】产品运营专员\n【职责】1.跟进用户反馈和需求 2.策划运营活动 3.分析转化数据并推动优化\n【要求】1.本科及以上 2.熟悉Excel/数据分析 3.有活动策划或用户调研经历 4.沟通协调能力强'}],finance:[{label:'银行管培',jd:'【岗位】银行管理培训生\n【职责】1.轮岗学习柜面、客户经理、风险管理等业务 2.参与客户服务和产品营销\n【要求】1.本科及以上，金融/经济/会计/管理相关优先 2.具备数据分析、客户沟通和合规意识 3.通过英语四六级优先'},{label:'财务助理',jd:'【岗位】财务助理\n【职责】1.协助费用审核、凭证整理、报表编制 2.配合审计和税务资料准备\n【要求】1.财会相关专业 2.熟悉Excel 3.了解会计准则 4.细致严谨，有初级会计证优先'}],government:[{label:'综合管理',jd:'【岗位】综合管理岗\n【职责】1.负责公文材料、会议组织、档案管理和跨部门协调 2.协助政策研究和事项督办\n【要求】1.本科及以上 2.文字功底扎实 3.熟悉Office 4.责任心强，具备服务意识和流程意识'},{label:'选调生',jd:'【岗位】选调生\n【职责】基层治理、群众服务、材料写作、政策执行和组织协调\n【要求】1.本科及以上 2.党员或学生干部经历优先 3.文字表达、组织协调、抗压能力强'}],education:[{label:'中学教师',jd:'【岗位】中学教师\n【职责】1.承担课程教学、作业批改和班级管理 2.参与教研和家校沟通\n【要求】1.本科及以上 2.教师资格证 3.学科基础扎实 4.表达能力、耐心和责任心强'}],medical:[{label:'住院医师',jd:'【岗位】住院医师\n【职责】1.完成病史采集、病历书写和临床诊疗协助 2.参与值班和患者沟通\n【要求】1.临床医学相关专业 2.医师资格证优先 3.病历书写规范 4.严谨负责，具备患者沟通能力'}],manufacturing:[{label:'质量工程师',jd:'【岗位】质量工程师\n【职责】1.跟进生产过程质量问题 2.分析异常原因并推动整改 3.维护质量记录\n【要求】1.机械/材料/工业工程相关 2.熟悉质量管理、统计分析或CAD 3.沟通协调能力强，能适应现场工作'}],sales:[{label:'市场营销',jd:'【岗位】市场营销专员\n【职责】1.策划市场活动和内容传播 2.维护客户线索 3.跟踪活动转化数据\n【要求】1.本科及以上 2.具备文案、活动策划、客户沟通能力 3.熟悉Excel或新媒体工具 4.有销售/社团/活动案例优先'}],design:[{label:'视觉设计',jd:'【岗位】视觉设计师\n【职责】1.负责活动海报、品牌物料和新媒体视觉 2.与运营和产品协作完成设计交付\n【要求】1.设计相关专业优先 2.熟悉Figma/Photoshop/Illustrator 3.有作品集 4.具备审美、沟通和按时交付能力'}],}[industry.value]||[]))
const currentStep=computed(()=>result.value?3:jdText.value?2:resumeText.value?1:0)
const fileIcon=computed(()=>file.value?(file.value.name.match(/\.pdf$/i)?'📕':'📘'):'📁')
const ready=computed(()=>resumeText.value.length>=50&&jdText.value.length>=30)

const dimLabels={hard_skills:'关键能力',projects:'经历证据',education:'门槛资质',soft_skills:'通用素质',industry:'行业场景',growth:'成长潜力'}
function dim(k){return result.value?.dimensions?.[k]?.score||0}
function detail(k){return result.value?.dimensions?.[k]?.detail||result.value?.dimensions?.[k]?.reason||''}
function dc(s){return s>=80?'bg-emerald-400':s>=60?'bg-[#d4a853]':'bg-red-400'}
function sc(s){return s>=80?'text-emerald-500':s>=60?'text-[#d4a853]':'text-red-500'}
function gb(s){return s==='critical'?'bg-red-50 border border-red-100':s==='moderate'?'bg-amber-50 border border-amber-100':'bg-blue-50 border border-blue-100'}
function bb(s){return s==='critical'?'bg-red-100 text-red-600':s==='moderate'?'bg-amber-100 text-amber-600':'bg-blue-100 text-blue-600'}
function tb(t){return{rewrite:'bg-purple-100 text-purple-600',enhance:'bg-blue-100 text-blue-600',add:'bg-emerald-100 text-emerald-600'}[t]||'bg-gray-100 text-gray-600'}
function riskClass(l){return l==='high'?'bg-red-50 border-red-100 text-red-700':l==='medium'?'bg-amber-50 border-amber-100 text-amber-700':'bg-blue-50 border-blue-100 text-blue-700'}
function actionClass(a){return a==='优先投递'?'bg-emerald-100 text-emerald-700':a==='优化后投递'?'bg-[#d4a853]/10 text-[#b8862e]':a==='谨慎投递'?'bg-amber-100 text-amber-700':'bg-red-100 text-red-700'}

async function doExtract(){if(!file.value)return;uploading.value=true;upStatus.value='<span class="text-gray-400">⏳ 提取...</span>';try{const f=new FormData();f.append('file',file.value);const{data}=await axios.post('/api/extract-text',f);resumeText.value=data.text;upStatus.value='<span class="text-emerald-500">✓ 已提取</span>'}catch(e){upStatus.value='<span class="text-red-500">✗ '+(e.response?.data?.detail||e.message)+'</span>'};uploading.value=false}
async function doAnalyze(){if(!ready.value)return;analyzing.value=true;err.value='';try{const{data}=await axios.post('/api/analyze-v2',{resume_text:resumeText.value,jd_text:jdText.value,filename:file.value?.name||'简历'});sessionStorage.setItem(`match:${data.match_id}`,JSON.stringify(data));router.push(`/analysis/${data.match_id}`)}catch(e){err.value=e.response?.data?.detail||e.message};analyzing.value=false}
async function renderRadar(){const c=rc.value;if(!c)return;const{Chart}=await import('chart.js/auto');const s=Math.min(c.parentElement.clientWidth,380);c.width=s;c.height=s;const ctx=c.getContext('2d');if(!ctx)return;if(radarChart)radarChart.destroy();const keys=Object.keys(dimLabels);radarChart=new Chart(ctx,{type:'radar',data:{labels:Object.values(dimLabels),datasets:[{data:keys.map(k=>dim(k)),backgroundColor:'rgba(212,168,83,0.08)',borderColor:'#d4a853',borderWidth:2,pointBackgroundColor:'#fff',pointBorderColor:'#d4a853',pointBorderWidth:2,pointRadius:4}]},options:{responsive:false,scales:{r:{beginAtZero:true,max:100,ticks:{stepSize:20,font:{size:9},color:'#9ca3af',backdropColor:'transparent'},pointLabels:{font:{size:10,weight:'600'},color:'#374151'},grid:{color:'#e5e7eb'},angleLines:{color:'#e5e7eb'}}},plugins:{legend:{display:false}}}})}
async function loadSaved(id){try{const{data}=await axios.get(`/api/resume/${id}`);resumeText.value=data.resume_text||''}catch(e){}}
async function loadVersions(){try{const{data}=await axios.get('/api/resume-versions');savedVersions.value=data.versions||[]}catch(e){}}
async function saveResumeVersion(){if(!result.value?.resume_id||!result.value?.resume_version_preview)return;try{await axios.post('/api/resume-versions',{resume_id:result.value.resume_id,jd_id:result.value.jd_id,match_id:result.value.match_id,name:result.value.resume_version_preview.version_name,target_role:result.value.resume_version_preview.version_name,content_json:result.value.resume_version_preview,score_snapshot:result.value.resume_version_preview.score_snapshot});versionMsg.value='已保存';await loadVersions();setTimeout(()=>versionMsg.value='',1600)}catch(e){versionMsg.value='保存失败'}}
async function doClear(){if(!confirm('确认清空?'))return;try{await axios.delete('/api/all-data');cs.value='✓ 已清空';result.value=null;resumeText.value='';jdText.value=''}catch(e){cs.value='✗ '+e.message}}
onMounted(async()=>{try{const{data}=await axios.get('/api/resumes');savedResumes.value=data.resumes||[]}catch(e){};await loadVersions()})
</script>
