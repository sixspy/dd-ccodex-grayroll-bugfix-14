import { api } from "../api.js";
const { ref, onMounted } = Vue;
export const EvaluateView = {
  setup() {
    const form = ref({ flag_key: "checkout.new_pay", env_code: "prod", subject_key: "u-1001" });
    const result = ref(null); const board = ref(null); const roster = ref(null);
    const err = ref(""); const msg = ref("");
    async function reloadBoard() { board.value = await api("/api/evaluate/board"); }
    async function reloadRoster() { roster.value = await api("/api/roster"); }
    async function reloadAll() {
      err.value = "";
      try { await Promise.all([reloadBoard(), reloadRoster()]); }
      catch (e) { err.value = e.message || String(e); }
    }
    async function run() {
      err.value = "";
      try { result.value = await api("/api/evaluate", { method: "POST", body: JSON.stringify(form.value) }); }
      catch (e) { err.value = e.message || String(e); }
    }
    async function refreshRoster() {
      err.value = ""; msg.value = "";
      try {
        const r = await api("/api/roster/refresh", { method: "POST", body: JSON.stringify({}) });
        msg.value = `名册已刷新，可放量计数=${r.releasable_count}（同事务剔除灰态归档）`;
        await reloadRoster();
      } catch (e) { err.value = e.message || String(e); }
    }
    onMounted(reloadAll);
    return { form, result, board, roster, err, msg, run, reloadAll, refreshRoster };
  },
  template: `
  <div class="grid">
    <div class="panel span-5">
      <h2>在线求值</h2>
      <div class="field"><label>开关键</label><input v-model="form.flag_key" /></div>
      <div class="field"><label>环境</label>
        <select v-model="form.env_code"><option>dev</option><option>staging</option><option>prod</option></select>
      </div>
      <div class="field"><label>主体键</label><input v-model="form.subject_key" /></div>
      <button class="btn" @click="run">求值</button>
      <div class="err" v-if="err">{{ err }}</div>
      <pre v-if="result" style="margin-top:0.8rem">{{ result }}</pre>
    </div>
    <div class="panel span-7">
      <h2>可放量名册 <span class="pill">计数 {{ roster && roster.releasable_count }}</span></h2>
      <p class="hint">同事务联查 flags 灰态归档标记，archived 开关一律剔除，计数与名册同源。</p>
      <table v-if="roster">
        <thead><tr><th>开关</th><th>环境</th><th>状态</th><th>类型</th><th>%</th><th>版本</th></tr></thead>
        <tbody>
          <tr v-for="(r,i) in roster.items" :key="i">
            <td><code>{{ r.flag_key }}</code></td><td>{{ r.env_code }}</td>
            <td><span class="pill" :class="{warn: r.status==='draft', danger: r.status==='killed'}">{{ r.status }}</span></td>
            <td>{{ r.kind }}</td><td>{{ r.percent }}</td><td>v{{ r.version }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted" v-if="roster && !roster.items.length">名册为空</p>
      <div style="margin-top:0.7rem;display:flex;gap:0.6rem;align-items:center;flex-wrap:wrap">
        <button class="btn" @click="refreshRoster">刷新名册（互斥）</button>
        <button class="btn secondary" @click="reloadAll">重载</button>
        <span class="muted" v-if="msg">{{ msg }}</span>
      </div>
    </div>
    <div class="panel span-12">
      <h2>正式规则板（已剔除灰态归档）</h2>
      <table v-if="board">
        <thead><tr><th>开关</th><th>环境</th><th>状态</th><th>类型</th><th>%</th><th>版本</th><th>可命中</th></tr></thead>
        <tbody>
          <tr v-for="(r,i) in board.rules" :key="'b'+i">
            <td>{{ r.flag_key }}</td><td>{{ r.env_code }}</td><td>{{ r.status }}</td>
            <td>{{ r.kind }}</td><td>{{ r.percent }}</td><td>v{{ r.version }}</td>
            <td>{{ r.hit_eligible ? '是' : '否' }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted">规则板可放量计数：{{ board && board.releasable_count }}（与名册同源）</p>
    </div>
  </div>`
};
