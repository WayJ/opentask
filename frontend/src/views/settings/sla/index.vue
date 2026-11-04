<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue';
import {
  type DataTableColumns,
  NButton,
  NCard,
  NDataTable,
  NInput,
  NInputNumber,
  NSelect,
  NSpace,
  NSwitch,
  NText
} from 'naive-ui';
import {
  ISSUE_STATUSES,
  type SlaPolicyRow,
  fetchCreateSlaPolicy,
  fetchDeleteSlaPolicy,
  fetchSlaPolicies,
  fetchSlaRunDue,
  fetchUpdateSlaPolicy,
  fetchHolidayPacks,
  fetchHolidayPackPreview,
  fetchHolidayPackApply,
  type HolidayPackSummary,
  type HolidayPackMergeResult,
  slaMetricLabel
} from '@/service/api/sla';
import {
  type WorkspaceItem,
  fetchUpdateWorkspace,
  fetchWorkspace,
  fetchWorkspaceList
} from '@/service/api/workspace';
import { localStg } from '@/utils/storage';
import {
  WEEKDAY_KEYS,
  WEEKDAY_LABELS,
  type BusinessException,
  type ExceptionKind,
  type WeekdayKey,
  emptyWindows,
  normalizeBusinessHours,
  normalizeExceptions,
  normalizeWindows,
  validateTimezoneClient,
  weekdayPreset0918,
  normalizePolicyCalendar,
  type PolicyCalendar
} from '@/utils/businessHours';

defineOptions({ name: 'SettingsSlaPage' });

const loading = ref(false);
const rows = ref<SlaPolicyRow[]>([]);
const creating = ref(false);
const running = ref(false);
const form = reactive({
  name: 'Time in progress',
  startStatuses: ['in_progress'] as string[],
  stopStatuses: ['resolved', 'closed'] as string[],
  pauseStatuses: [] as string[],
  targetMinutes: 1440,
  metric: 'time_in_status',
  notifyAssignee: true,
  notifyWatchers: false,
  calendarEnabled: false,
  calendarTimezone: '' as string,
  calendarExceptions: [] as { date: string; kind: string; windows?: { start: string; end: string }[] }[]
});
const calExDraft = reactive({ date: '', kind: 'closed' as ExceptionKind, windowsText: '' });

const statusOptions = ISSUE_STATUSES.map(v => ({ label: v, value: v }));

const workspace = ref<WorkspaceItem | null>(null);
const bhSaving = ref(false);
const bhForm = reactive({
  timezone: 'Asia/Shanghai',
  enabled: false,
  windows: emptyWindows() as Record<WeekdayKey, { start: string; end: string }[]>,
  exceptions: [] as BusinessException[]
});
const exDraft = reactive({
  date: '',
  kind: 'closed' as ExceptionKind,
  windowsText: ''
});
const kindOptions = [
  { label: '关闭日 (closed)', value: 'closed' },
  { label: '强制营业 (forced_open)', value: 'forced_open' }
];
const timezoneOptions = [
  { label: 'Asia/Shanghai', value: 'Asia/Shanghai' },
  { label: 'UTC', value: 'UTC' },
  { label: 'America/Los_Angeles', value: 'America/Los_Angeles' },
  { label: 'America/New_York', value: 'America/New_York' },
  { label: 'Europe/London', value: 'Europe/London' }
];
const isOwner = computed(() => workspace.value?.role === 'owner');

const packOpen = ref(false);
const packLoading = ref(false);
const packApplying = ref(false);
const packRows = ref<HolidayPackSummary[]>([]);
const packRegion = ref('CN');
const packYear = ref(2026);
const packTarget = ref<'workspace' | 'policy'>('workspace');
const packPolicyId = ref<string | null>(null);
const packPreview = ref<HolidayPackMergeResult | null>(null);
const packSourceNote = ref('');
const packOptions = computed(() =>
  packRows.value.map(r => ({
    label: `${r.region} ${r.year} · ${r.name} (${r.count})`,
    value: `${r.region}:${r.year}`
  }))
);
const packKey = ref('CN:2026');
function onPackKeyUpdate(v: string) {
  packKey.value = v;
  const [r, y] = String(v).split(':');
  packRegion.value = r || 'CN';
  packYear.value = Number(y) || 2026;
  const meta = packRows.value.find(x => x.region === packRegion.value && x.year === packYear.value);
  packSourceNote.value = meta?.sourceNote || '';
  packPreview.value = null;
}
const policyOptions = computed(() =>
  rows.value.map(r => ({ label: r.name, value: r.id }))
);

async function loadHolidayPacks() {
  packLoading.value = true;
  try {
    const { data, error } = await fetchHolidayPacks();
    if (error || !data) return;
    packRows.value = data.rows || [];
    const meta = packRows.value.find(x => x.region === packRegion.value && x.year === packYear.value);
    packSourceNote.value = meta?.sourceNote || packRows.value[0]?.sourceNote || '';
    if (!meta && packRows.value[0]) {
      packRegion.value = packRows.value[0].region;
      packYear.value = packRows.value[0].year;
      packSourceNote.value = packRows.value[0].sourceNote;
    }
    packKey.value = `${packRegion.value}:${packYear.value}`;
  } finally {
    packLoading.value = false;
  }
}

async function previewHolidayPack() {
  packLoading.value = true;
  packPreview.value = null;
  try {
    const body: { target: string; policyId?: string } = { target: packTarget.value };
    if (packTarget.value === 'policy') {
      if (!packPolicyId.value) {
        window.$message?.error?.('请选择 policy');
        return;
      }
      body.policyId = packPolicyId.value;
    }
    const { data, error } = await fetchHolidayPackPreview(packRegion.value, packYear.value, body);
    if (error || !data) {
      window.$message?.error?.(error?.message || '预览失败');
      return;
    }
    packPreview.value = data;
    packSourceNote.value = data.sourceNote || packSourceNote.value;
  } finally {
    packLoading.value = false;
  }
}

async function applyHolidayPack() {
  if (!isOwner.value) return;
  packApplying.value = true;
  try {
    const body: { target: string; policyId?: string } = { target: packTarget.value };
    if (packTarget.value === 'policy') {
      if (!packPolicyId.value) {
        window.$message?.error?.('请选择 policy');
        return;
      }
      body.policyId = packPolicyId.value;
    }
    const { data, error } = await fetchHolidayPackApply(packRegion.value, packYear.value, body);
    if (error || !data) {
      window.$message?.error?.(error?.message || '应用失败');
      return;
    }
    packPreview.value = data;
    window.$message?.success?.(
      `已应用：+${(data.added || []).length} 覆盖${(data.replaced || []).length}`
    );
    await loadBusinessHours();
    await load();
  } finally {
    packApplying.value = false;
  }
}

function fillPolicyFromHolidayPack(policyId: string) {
  packTarget.value = 'policy';
  packPolicyId.value = policyId;
  packOpen.value = true;
}

async function resolveWorkspaceId(): Promise<string | null> {
  const cached = localStg.get('workspaceId');
  if (cached) return String(cached);
  const { data, error } = await fetchWorkspaceList();
  if (error || !data?.length) return null;
  localStg.set('workspaceId', data[0].id);
  return data[0].id;
}

async function loadBusinessHours() {
  const wsId = await resolveWorkspaceId();
  if (!wsId) return;
  const { data, error } = await fetchWorkspace(wsId);
  if (error || !data) return;
  workspace.value = data;
  const bh = normalizeBusinessHours(data.businessHours || null);
  bhForm.timezone = data.timezone || 'Asia/Shanghai';
  bhForm.enabled = bh.enabled;
  bhForm.windows = bh.windows;
  bhForm.exceptions = bh.exceptions;
}

function applyWeekdayPreset() {
  bhForm.windows = weekdayPreset0918();
}

function setDaySegments(day: WeekdayKey, raw: string) {
  // raw: "09:00-12:00,13:00-18:00" or empty
  const parts = String(raw || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const segs = parts.map(p => {
    const [start, end] = p.split('-').map(x => x.trim());
    return { start: start || '', end: end || '' };
  });
  bhForm.windows[day] = segs;
}

function daySegmentsText(day: WeekdayKey): string {
  return (bhForm.windows[day] || []).map(s => `${s.start}-${s.end}`).join(',');
}

async function saveBusinessHours() {
  if (!workspace.value || !isOwner.value) return;
  bhSaving.value = true;
  try {
    let tz: string | null;
    let windows;
    let exceptions: BusinessException[];
    try {
      tz = validateTimezoneClient(bhForm.timezone);
      windows = normalizeWindows(bhForm.windows);
      exceptions = normalizeExceptions(bhForm.exceptions);
    } catch (e: any) {
      window.$message?.error?.(e?.message || '时段非法');
      return;
    }
    const { data, error } = await fetchUpdateWorkspace(workspace.value.id, {
      timezone: tz,
      businessHours: { enabled: bhForm.enabled, windows, exceptions }
    });
    if (error || !data) {
      window.$message?.error?.(error?.message || '保存失败');
      return;
    }
    workspace.value = data;
    window.$message?.success?.('营业时段已保存（running/paused deadline 已重算）');
    await loadBusinessHours();
  } finally {
    bhSaving.value = false;
  }
}

function parseWindowsText(raw: string): { start: string; end: string }[] {
  const parts = String(raw || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  return parts.map(p => {
    const [start, end] = p.split('-').map(x => x.trim());
    return { start: start || '', end: end || '' };
  });
}

function addExceptionDraft() {
  if (!isOwner.value) return;
  try {
    const entry: BusinessException = {
      date: String(exDraft.date || '').trim(),
      kind: exDraft.kind
    };
    if (exDraft.kind === 'forced_open' && exDraft.windowsText.trim()) {
      entry.windows = parseWindowsText(exDraft.windowsText);
    }
    bhForm.exceptions = normalizeExceptions([...bhForm.exceptions, entry]);
    exDraft.date = '';
    exDraft.windowsText = '';
    exDraft.kind = 'closed';
  } catch (e: any) {
    window.$message?.error?.(e?.message || '例外日非法');
  }
}

function removeException(date: string) {
  bhForm.exceptions = bhForm.exceptions.filter(e => e.date !== date);
}

const metricOptions = [
  { label: '状态停留 (time_in_status)', value: 'time_in_status' },
  { label: '首次响应 (first_response)', value: 'first_response' }
];

const columns: DataTableColumns<SlaPolicyRow> = [
  {
    title: '名称',
    key: 'name',
    render: row =>
      h('div', [
        h('div', { style: 'font-weight:500' }, row.name),
        h(NText, { depth: 3, style: 'font-size:12px' }, { default: () => `${row.targetMinutes} 分钟 · ${slaMetricLabel(row.metric)}` })
      ])
  },
  {
    title: '启停状态',
    key: 'statuses',
    render: row =>
      h(
        NText,
        { depth: 3, style: 'font-size:12px' },
        {
          default: () =>
            `start: ${(row.startStatuses || []).join(', ') || '—'} → stop: ${(row.stopStatuses || []).join(', ') || '关闭类'} · pause: ${(row.pauseStatuses || []).join(', ') || '—'}`
        }
      )
  },
  {
    title: '启用',
    key: 'enabled',
    width: 90,
    render: row =>
      h(NSwitch, {
        value: row.enabled,
        size: 'small',
        onUpdateValue: (v: boolean) => toggle(row, v)
      })
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    render: row =>
      h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          { size: 'tiny', tertiary: true, onClick: () => fillPolicyFromHolidayPack(row.id) },
          { default: () => '假日包' }
        ),
        row.calendar
          ? h(
              NButton,
              { size: 'tiny', tertiary: true, onClick: () => clearCalendar(row) },
              { default: () => '清除覆盖' }
            )
          : null,
        h(
          NButton,
          { size: 'tiny', tertiary: true, type: 'error', onClick: () => removeRow(row.id) },
          { default: () => '删除' }
        )
      ])
  }
];

async function load() {
  loading.value = true;
  try {
    const { data, error } = await fetchSlaPolicies();
    if (error) {
      window.$message?.error?.(error.message || '加载失败');
      return;
    }
    rows.value = data?.rows || [];
  } finally {
    loading.value = false;
  }
}

async function create() {
  if (!form.name.trim() || !form.startStatuses.length) {
    window.$message?.warning?.('名称与 startStatuses 必填');
    return;
  }
  creating.value = true;
  try {
    let calendar: PolicyCalendar | null = null;
    if (form.calendarEnabled) {
      try {
        const raw: Record<string, unknown> = {};
        if (form.calendarTimezone.trim()) raw.timezone = form.calendarTimezone.trim();
        if (form.calendarExceptions.length) raw.exceptions = form.calendarExceptions;
        calendar = normalizePolicyCalendar(raw);
      } catch (e: any) {
        window.$message?.error?.(e?.message || '日历覆盖无效');
        creating.value = false;
        return;
      }
    }
    const { error } = await fetchCreateSlaPolicy({
      name: form.name.trim(),
      startStatuses: form.startStatuses,
      stopStatuses: form.stopStatuses,
      pauseStatuses: form.pauseStatuses,
      targetMinutes: form.targetMinutes,
      metric: form.metric,
      notifyAssignee: form.notifyAssignee,
      notifyWatchers: form.notifyWatchers,
      ...(calendar ? { calendar } : {})
    });
    if (error) {
      window.$message?.error?.(error.message || '创建失败');
      return;
    }
    window.$message?.success?.('已创建');
    await load();
  } finally {
    creating.value = false;
  }
}

async function toggle(row: SlaPolicyRow, enabled: boolean) {
  const { error } = await fetchUpdateSlaPolicy(row.id, { enabled });
  if (error) {
    window.$message?.error?.(error.message || '更新失败');
    return;
  }
  row.enabled = enabled;
}

async function removeRow(id: string) {
  const { error } = await fetchDeleteSlaPolicy(id);
  if (error) {
    window.$message?.error?.(error.message || '删除失败');
    return;
  }
  window.$message?.success?.('已删除');
  await load();
}


async function clearCalendar(row: SlaPolicyRow) {
  const { error } = await fetchUpdateSlaPolicy(row.id, { calendar: null });
  if (error) {
    window.$message?.error?.(error.message || '清除失败');
    return;
  }
  window.$message?.success?.('已清除日历覆盖');
  await load();
}

function addCalExceptionDraft() {
  try {
    const entry: Record<string, unknown> = { date: calExDraft.date, kind: calExDraft.kind };
    if (calExDraft.kind === 'forced_open' && calExDraft.windowsText.trim()) {
      entry.windows = calExDraft.windowsText.split(',').map(s => {
        const [start, end] = s.trim().split('-');
        return { start: start.trim(), end: end.trim() };
      });
    }
    const normalized = normalizePolicyCalendar({
      exceptions: [...form.calendarExceptions, entry]
    });
    form.calendarExceptions = (normalized?.exceptions as any[]) || [];
    calExDraft.date = '';
    calExDraft.windowsText = '';
  } catch (e: any) {
    window.$message?.error?.(e?.message || '例外无效');
  }
}

async function runDue() {
  running.value = true;
  try {
    const { data, error } = await fetchSlaRunDue();
    if (error) {
      window.$message?.error?.(error.message || '执行失败');
      return;
    }
    window.$message?.success?.(
      `扫描 ${data?.scanned ?? 0} · 违约 ${data?.breached ?? 0} · 通知 ${data?.notificationsCreated ?? 0}`
    );
  } finally {
    running.value = false;
  }
}

onMounted(async () => {
  await load();
  await loadBusinessHours();
  await loadHolidayPacks();
});
</script>

<template>
  <div class="p-4">
    <NCard title="SLA 策略" :bordered="false">
      <template #header-extra>
        <NSpace>
          <NButton size="small" :loading="running" @click="runDue">立即 run-due</NButton>
          <NButton size="small" @click="load">刷新</NButton>
        </NSpace>
      </template>
      <NText depth="3" style="display:block;margin-bottom:12px;font-size:12px">
        支持「状态停留」与「首次响应」两种 metric。默认墙钟分钟；下方启用营业时后按营业分钟。首次响应：非创建者首条评论即满足；指派不算。stop 为空时进入 resolved/closed/rejected 即满足。进入暂停状态时不计时，离开后按剩余时间续跑。无内置 cron，请外部调度 POST /api/sla/run-due。
      </NText>
      <NDataTable :columns="columns" :data="rows" :loading="loading" size="small" />
    </NCard>

    <NCard title="新建策略" :bordered="false" style="margin-top:16px">
      <NSpace vertical>
        <NInput v-model:value="form.name" placeholder="名称" maxlength="80" />
        <NSelect v-model:value="form.metric" :options="metricOptions" placeholder="metric" />
        <NText depth="3" style="font-size:12px">首次响应：非创建者首条评论算首响；指派负责人不算。</NText>
        <NSelect v-model:value="form.startStatuses" multiple :options="statusOptions" placeholder="startStatuses" />
        <NSelect v-model:value="form.stopStatuses" multiple :options="statusOptions" placeholder="stopStatuses（可空=关闭类）" />
        <NSelect
          v-model:value="form.pauseStatuses"
          multiple
          :options="statusOptions"
          placeholder="暂停计时的状态（可空=不启用暂停；示例 feedback）"
        />
        <NText depth="3" style="font-size:12px">进入这些状态时 SLA 暂停；离开后按剩余时间续跑。优先级：stop &gt; pause &gt; start。</NText>
        <NInputNumber v-model:value="form.targetMinutes" :min="1" :max="10080" placeholder="targetMinutes" />
        <NSpace>
          <span>通知负责人</span>
          <NSwitch v-model:value="form.notifyAssignee" />
          <span>通知关注者</span>
          <NSwitch v-model:value="form.notifyWatchers" />
        </NSpace>
        <div style="border:1px solid #eee;border-radius:6px;padding:12px">
          <NSpace align="center" style="margin-bottom:8px">
            <span style="font-weight:500">日历覆盖</span>
            <NSwitch v-model:value="form.calendarEnabled" />
            <NText depth="3" style="font-size:12px">关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承</NText>
          </NSpace>
          <template v-if="form.calendarEnabled">
            <NSpace align="center" style="margin-bottom:8px">
              <span>时区覆盖</span>
              <NSelect
                v-model:value="form.calendarTimezone"
                :options="[{ label: '（继承工作区）', value: '' }, ...timezoneOptions]"
                style="width:220px"
                filterable
                tag
                clearable
              />
            </NSpace>
            <NText depth="3" style="display:block;margin-bottom:6px;font-size:12px">例外覆盖（填写则整表替换 WS 例外；留空=继承）</NText>
            <div v-for="ex in form.calendarExceptions" :key="ex.date" style="display:flex;gap:8px;margin-bottom:4px">
              <span style="width:110px">{{ ex.date }}</span>
              <span style="width:120px">{{ ex.kind }}</span>
              <NButton size="tiny" @click="form.calendarExceptions = form.calendarExceptions.filter(e => e.date !== ex.date)">删</NButton>
            </div>
            <NSpace align="center">
              <NInput v-model:value="calExDraft.date" placeholder="YYYY-MM-DD" style="width:140px" />
              <NSelect v-model:value="calExDraft.kind" :options="kindOptions" style="width:180px" />
              <NButton size="small" @click="addCalExceptionDraft">添加例外</NButton>
            </NSpace>
          </template>
        </div>
        <NButton type="primary" :loading="creating" @click="create">创建</NButton>
      </NSpace>
    </NCard>

    <NCard title="营业时段（SLA business hours）" :bordered="false" style="margin-top:16px">
      <NText depth="3" style="display:block;margin-bottom:12px;font-size:12px">
        工作区级 IANA 时区 + 周内营业窗口。启用后 SLA deadline / pause 剩余按营业分钟计算；关闭则回退墙钟。配置保存后批量重算 running/paused。每日最多 2 段，格式 09:00-12:00,13:00-18:00。
      </NText>
      <NSpace vertical>
        <NSpace align="center">
          <span>启用营业时</span>
          <NSwitch v-model:value="bhForm.enabled" :disabled="!isOwner" />
          <NSelect
            v-model:value="bhForm.timezone"
            :options="timezoneOptions"
            style="width:220px"
            :disabled="!isOwner"
            filterable
            tag
          />
          <NButton size="small" :disabled="!isOwner" @click="applyWeekdayPreset">工作日 09–18</NButton>
        </NSpace>
        <div v-for="day in WEEKDAY_KEYS" :key="day" style="display:flex;gap:8px;align-items:center">
          <span style="width:48px">{{ WEEKDAY_LABELS[day] }}</span>
          <NInput
            :value="daySegmentsText(day)"
            :disabled="!isOwner"
            placeholder="空=非营业；例 09:00-12:00,13:00-18:00"
            @update:value="(v: string) => setDaySegments(day, v)"
          />
        </div>
        <div style="margin-top:8px">
          <NText depth="3" style="display:block;margin-bottom:8px;font-size:12px">
            例外日（本地日历日）：closed 全日不计营业分钟；forced_open 覆盖周窗（未填窗口则用周一窗或 09:00–18:00）。上限 366。
          </NText>
          <div v-if="!bhForm.exceptions.length" style="font-size:12px;color:#888;margin-bottom:8px">暂无例外日</div>
          <div
            v-for="ex in bhForm.exceptions"
            :key="ex.date"
            style="display:flex;gap:8px;align-items:center;margin-bottom:4px"
          >
            <span style="width:110px">{{ ex.date }}</span>
            <span style="width:120px">{{ ex.kind }}</span>
            <span style="flex:1;font-size:12px;color:#666">
              {{
                ex.kind === 'forced_open'
                  ? (ex.windows || []).map(s => `${s.start}-${s.end}`).join(',') || '默认窗'
                  : '—'
              }}
            </span>
            <NButton size="tiny" :disabled="!isOwner" @click="removeException(ex.date)">删除</NButton>
          </div>
          <NSpace align="center" style="margin-top:8px">
            <NInput v-model:value="exDraft.date" :disabled="!isOwner" placeholder="YYYY-MM-DD" style="width:140px" />
            <NSelect v-model:value="exDraft.kind" :options="kindOptions" :disabled="!isOwner" style="width:180px" />
            <NInput
              v-model:value="exDraft.windowsText"
              :disabled="!isOwner || exDraft.kind !== 'forced_open'"
              placeholder="forced_open 可选窗口"
              style="width:220px"
            />
            <NButton size="small" :disabled="!isOwner" @click="addExceptionDraft">添加例外</NButton>
          </NSpace>
        </div>
        <NButton type="primary" :loading="bhSaving" :disabled="!isOwner" @click="saveBusinessHours">保存营业时段</NButton>
      </NSpace>
    </NCard>

    <NCard title="假日包" :bordered="false" style="margin-top:16px">
      <div style="margin-bottom:8px">
        <span style="font-weight:500;cursor:pointer" @click="packOpen = !packOpen">
          {{ packOpen ? '▼' : '▶' }} 国家/地区假日包（一键合并例外日）
        </span>
      </div>
      <template v-if="packOpen">
        <NText depth="3" style="display:block;margin-bottom:12px;font-size:12px">
          精选静态包（CN/US）；预览后应用到本工作区营业例外或某 policy 日历覆盖。同日以包为准覆盖；包外例外保留。无外网同步。
        </NText>
        <NSpace vertical>
          <NSpace align="center">
            <NSelect :value="packKey" @update:value="onPackKeyUpdate" :options="packOptions" style="width:360px" :loading="packLoading" />
            <NSelect
              v-model:value="packTarget"
              :options="[
                { label: '本工作区 business_hours', value: 'workspace' },
                { label: '指定 policy 日历', value: 'policy' }
              ]"
              style="width:220px"
            />
            <NSelect
              v-if="packTarget === 'policy'"
              v-model:value="packPolicyId"
              :options="policyOptions"
              placeholder="选择 policy"
              style="width:200px"
              clearable
            />
          </NSpace>
          <NText depth="3" style="font-size:12px">{{ packSourceNote || '—' }}</NText>
          <NSpace>
            <NButton size="small" :loading="packLoading" @click="previewHolidayPack">预览</NButton>
            <NButton
              type="primary"
              size="small"
              :loading="packApplying"
              :disabled="!isOwner"
              @click="applyHolidayPack"
            >
              确认应用
            </NButton>
          </NSpace>
          <div v-if="packPreview" style="font-size:12px">
            <div style="margin-bottom:6px">
              变更：+{{ (packPreview.added || []).length }} /
              覆盖 {{ (packPreview.replaced || []).length }} /
              保留 {{ (packPreview.unchanged || []).length }}
              （{{ packPreview.countBefore }} → {{ packPreview.countAfter }}）
            </div>
            <div
              v-for="row in [...(packPreview.added || []).map((x: any) => ({ ...x, _tag: 'added' })), ...(packPreview.replaced || []).map((x: any) => ({ date: x.date, kind: x.after?.kind || x.kind, _tag: 'replaced' }))]"
              :key="row._tag + row.date"
              style="display:flex;gap:8px;margin-bottom:2px"
            >
              <span style="width:70px;color:#888">{{ row._tag }}</span>
              <span style="width:110px">{{ row.date }}</span>
              <span>{{ row.kind }}</span>
            </div>
          </div>
        </NSpace>
      </template>
    </NCard>
  </div>
</template>
