/**
 * E7-S3：Issue 列表/看板 Display 契约（个人 prefs 与 Saved View display_json 共用键）。
 * E37：swimlane_by / group_by 支持 cf:<field_key>。
 */
import {
  type GroupByKey,
  isCfDim,
  isGroupByKey,
  isGroupingCfType,
  parseCfDim
} from './groupIssuesBy';

export type SystemSwimlaneBy = 'none' | 'assignee' | 'priority' | 'type' | 'label';
export type SwimlaneBy = SystemSwimlaneBy | `cf:${string}`;

export type DisplayFieldKey =
  'assignee' | 'priority' | 'labels' | 'estimate_points' | 'due_date' | 'project' | 'cycle' | 'issue_code' | 'type';

export type IssueDisplayFields = Record<DisplayFieldKey, boolean>;

export type ConditionalTint = 'danger' | 'warning' | 'success' | 'info' | 'neutral';
export type ConditionalOp = 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte';
export type ConditionalTarget = 'row' | 'cell';

export interface ConditionalFormatRule {
  id: string;
  when: { field: string; op: ConditionalOp; value: unknown };
  style: { rowTint: ConditionalTint };
  target: ConditionalTarget;
}

/** E49 */
export type ColorPalette =
  | 'blue_red'
  | 'green_red'
  | 'mono'
  | 'yellow_blue'
  | 'purple_green';

export type DisplayIcon =
  | 'arrow_up'
  | 'arrow_down'
  | 'arrow_flat'
  | 'flag'
  | 'dot_red'
  | 'dot_yellow'
  | 'dot_green'
  | 'check'
  | 'warn';

export interface ColorScaleRule {
  id: string;
  field: string;
  domain: { min: number; max: number };
  palette: ColorPalette;
  target: ConditionalTarget;
}

export interface IconSetRule {
  id: string;
  field: string;
  rules: Array<{ op: ConditionalOp; value: unknown; icon: DisplayIcon }>;
}

export interface IssueDisplayState {
  viewMode: 'list' | 'board';
  groupBy: GroupByKey;
  swimlaneBy: SwimlaneBy;
  hideEmptyLanes: boolean;
  fields: IssueDisplayFields;
  /** E32：要在列表显示的自定义字段 key（有序） */
  customFieldKeys: string[];
  /** E46：条件格式（≤10；客户端求值） */
  conditionalFormats: ConditionalFormatRule[];
  /** E49：连续色阶（≤5） */
  colorScales: ColorScaleRule[];
  /** E49：图标集（≤5） */
  iconSets: IconSetRule[];
}

export const DISPLAY_FIELD_KEYS: DisplayFieldKey[] = [
  'issue_code',
  'assignee',
  'priority',
  'labels',
  'type',
  'estimate_points',
  'due_date',
  'project',
  'cycle'
];

export const DISPLAY_FIELD_LABELS: Record<DisplayFieldKey, string> = {
  issue_code: '编号',
  assignee: '负责人',
  priority: '优先级',
  labels: '标签',
  type: '类型',
  estimate_points: '估点',
  due_date: '截止日期',
  project: '项目',
  cycle: 'Cycle'
};

export const SWIMLANE_OPTIONS: { label: string; value: SwimlaneBy }[] = [
  { label: '无泳道', value: 'none' },
  { label: '负责人', value: 'assignee' },
  { label: '优先级', value: 'priority' },
  { label: '类型', value: 'type' },
  { label: '标签', value: 'label' }
];

const DEFAULT_FIELDS: IssueDisplayFields = {
  assignee: true,
  priority: true,
  labels: true,
  estimate_points: true,
  due_date: false,
  project: false,
  cycle: false,
  issue_code: true,
  type: false
};

function isSystemSwimlaneBy(value: unknown): value is SystemSwimlaneBy {
  return value === 'none' || value === 'assignee' || value === 'priority' || value === 'type' || value === 'label';
}

function isSwimlaneBy(value: unknown): value is SwimlaneBy {
  return isSystemSwimlaneBy(value) || isCfDim(value);
}

const TINTS = new Set(['danger', 'warning', 'success', 'info', 'neutral']);
const CFMT_OPS = new Set(['eq', 'neq', 'gt', 'gte', 'lt', 'lte']);
const CFMT_TARGETS = new Set(['row', 'cell']);
const CFMT_FIELD_RE = /^(?:cf:[a-z][a-z0-9_-]{0,63}|priority|status|due_date|estimate_points)$/;
const CFMT_MAX = 10;

const SCALE_MAX = 5;
const SCALE_PALETTES = new Set([
  'blue_red',
  'green_red',
  'mono',
  'yellow_blue',
  'purple_green'
]);
const SCALE_FIELD_RE = /^(?:cf:[a-z][a-z0-9_-]{0,63}|due_date|estimate_points)$/;
const ICON_SET_MAX = 5;
const ICON_RULES_MAX = 8;
const ICON_VOCAB = new Set([
  'arrow_up',
  'arrow_down',
  'arrow_flat',
  'flag',
  'dot_red',
  'dot_yellow',
  'dot_green',
  'check',
  'warn'
]);

const PALETTE_ENDS: Record<ColorPalette, [string, string]> = {
  blue_red: ['#2080f0', '#d03050'],
  green_red: ['#18a058', '#d03050'],
  mono: ['#e8e8e8', '#4a4a4a'],
  yellow_blue: ['#f0a020', '#2080f0'],
  purple_green: ['#8a2be2', '#18a058']
};

function parseDomainBound(raw: unknown): number | null {
  if (raw === null || raw === undefined || typeof raw === 'boolean') return null;
  if (typeof raw === 'number') {
    if (!Number.isFinite(raw)) return null;
    return raw;
  }
  const s = String(raw).trim();
  if (!s) return null;
  const asNum = Number(s);
  if (!Number.isNaN(asNum) && Number.isFinite(asNum)) return asNum;
  if (s.length >= 10 && s[4] === '-' && s[7] === '-') {
    const digits = s.slice(0, 10).replace(/-/g, '');
    if (/^\d{8}$/.test(digits)) return Number(digits);
  }
  return null;
}

function normalizeColorScales(raw: unknown): ColorScaleRule[] {
  if (!Array.isArray(raw)) return [];
  const out: ColorScaleRule[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const obj = item as Record<string, unknown>;
    const field = String(obj.field || '').trim();
    if (!SCALE_FIELD_RE.test(field)) continue;
    const palette = String(obj.palette || '').trim().toLowerCase();
    if (!SCALE_PALETTES.has(palette)) continue;
    const target = String(obj.target || 'row').trim().toLowerCase();
    if (!CFMT_TARGETS.has(target)) continue;
    const domain = obj.domain;
    if (!domain || typeof domain !== 'object') continue;
    const d = domain as Record<string, unknown>;
    const dmin = parseDomainBound(d.min);
    const dmax = parseDomainBound(d.max);
    if (dmin === null || dmax === null) continue;
    const id = String(obj.id || '').trim() || `cscale_${out.length + 1}`;
    out.push({
      id,
      field,
      domain: { min: dmin, max: dmax },
      palette: palette as ColorPalette,
      target: target as ConditionalTarget
    });
    if (out.length >= SCALE_MAX) break;
  }
  return out;
}

function normalizeIconSets(raw: unknown): IconSetRule[] {
  if (!Array.isArray(raw)) return [];
  const out: IconSetRule[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const obj = item as Record<string, unknown>;
    const field = String(obj.field || '').trim();
    if (!CFMT_FIELD_RE.test(field)) continue;
    const rulesIn = obj.rules;
    if (!Array.isArray(rulesIn)) continue;
    const rules: IconSetRule['rules'] = [];
    for (const rule of rulesIn) {
      if (!rule || typeof rule !== 'object') continue;
      const r = rule as Record<string, unknown>;
      const op = String(r.op || '').trim().toLowerCase();
      if (!CFMT_OPS.has(op)) continue;
      const icon = String(r.icon || '').trim().toLowerCase();
      if (!ICON_VOCAB.has(icon)) continue;
      rules.push({ op: op as ConditionalOp, value: r.value, icon: icon as DisplayIcon });
      if (rules.length >= ICON_RULES_MAX) break;
    }
    if (!rules.length) continue;
    const id = String(obj.id || '').trim() || `iset_${out.length + 1}`;
    out.push({ id, field, rules });
    if (out.length >= ICON_SET_MAX) break;
  }
  return out;
}

function normalizeConditionalFormats(raw: unknown): ConditionalFormatRule[] {
  if (!Array.isArray(raw)) return [];
  const out: ConditionalFormatRule[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const obj = item as Record<string, unknown>;
    const when = obj.when;
    const style = obj.style;
    if (!when || typeof when !== 'object' || !style || typeof style !== 'object') continue;
    const w = when as Record<string, unknown>;
    const s = style as Record<string, unknown>;
    const field = String(w.field || '').trim();
    if (!CFMT_FIELD_RE.test(field)) continue;
    const op = String(w.op || '').trim().toLowerCase();
    if (!CFMT_OPS.has(op)) continue;
    const tint = String(s.rowTint || s.row_tint || '').trim().toLowerCase();
    if (!TINTS.has(tint)) continue;
    const target = String(obj.target || 'row').trim().toLowerCase();
    if (!CFMT_TARGETS.has(target)) continue;
    const id = String(obj.id || '').trim() || `cfmt_${out.length + 1}`;
    out.push({
      id,
      when: { field, op: op as ConditionalOp, value: w.value },
      style: { rowTint: tint as ConditionalTint },
      target: target as ConditionalTarget
    });
    if (out.length >= CFMT_MAX) break;
  }
  return out;
}

export function defaultIssueDisplay(): IssueDisplayState {
  return {
    viewMode: 'list',
    groupBy: 'none',
    swimlaneBy: 'none',
    hideEmptyLanes: false,
    fields: { ...DEFAULT_FIELDS },
    customFieldKeys: [],
    conditionalFormats: [],
    colorScales: [],
    iconSets: []
  };
}

export function normalizeIssueDisplay(raw: unknown): IssueDisplayState {
  const out = defaultIssueDisplay();
  if (!raw || typeof raw !== 'object') return out;
  const obj = raw as Record<string, unknown>;

  if (obj.view_mode === 'list' || obj.view_mode === 'board') {
    out.viewMode = obj.view_mode;
  }
  if (isGroupByKey(obj.group_by)) {
    out.groupBy = obj.group_by;
  }
  if (isSwimlaneBy(obj.swimlane_by)) {
    out.swimlaneBy = obj.swimlane_by;
  }
  if ('hide_empty_lanes' in obj) {
    out.hideEmptyLanes = Boolean(obj.hide_empty_lanes);
  }
  const fieldsIn = obj.fields;
  if (fieldsIn && typeof fieldsIn === 'object') {
    const f = fieldsIn as Record<string, unknown>;
    for (const key of DISPLAY_FIELD_KEYS) {
      if (key in f) {
        out.fields[key] = Boolean(f[key]);
      }
    }
  }
  const cfKeys = obj.custom_field_keys;
  if (Array.isArray(cfKeys)) {
    out.customFieldKeys = cfKeys
      .map(k => String(k || '').trim().toLowerCase())
      .filter(Boolean);
  }
  out.conditionalFormats = normalizeConditionalFormats(
    obj.conditional_formats ?? obj.conditionalFormats
  );
  out.colorScales = normalizeColorScales(obj.color_scales ?? obj.colorScales);
  out.iconSets = normalizeIconSets(obj.icon_sets ?? obj.iconSets);

  // 选中 cf:<key> 时并入 custom_field_keys（去重）
  for (const dim of [out.groupBy, out.swimlaneBy]) {
    const key = parseCfDim(dim);
    if (key && !out.customFieldKeys.includes(key)) {
      out.customFieldKeys = [...out.customFieldKeys, key];
    }
  }
  return out;
}

export function displayStateToJson(state: IssueDisplayState): Record<string, unknown> {
  return {
    view_mode: state.viewMode,
    group_by: state.groupBy,
    swimlane_by: state.swimlaneBy,
    hide_empty_lanes: state.hideEmptyLanes,
    fields: { ...state.fields },
    custom_field_keys: [...(state.customFieldKeys || [])],
    conditional_formats: [...(state.conditionalFormats || [])],
    color_scales: [...(state.colorScales || [])],
    icon_sets: [...(state.iconSets || [])]
  };
}

/** E46：按数组序先匹配先生效；返回 row tint 或 null */
export function resolveRowTint(
  issue: Record<string, unknown>,
  rules: ConditionalFormatRule[] | undefined | null
): ConditionalTint | null {
  if (!rules || !rules.length) return null;
  for (const rule of rules) {
    if (rule.target !== 'row') continue;
    if (matchConditionalWhen(issue, rule.when)) return rule.style.rowTint;
  }
  return null;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
  return (
    '#' +
    [clamp(r), clamp(g), clamp(b)]
      .map(x => x.toString(16).padStart(2, '0'))
      .join('')
  );
}

/** E49：线性插值 palette；t clamp 到 [0,1] */
export function interpolateScaleColor(palette: ColorPalette, t: number): string {
  const ends = PALETTE_ENDS[palette] || PALETTE_ENDS.mono;
  const tt = Number.isFinite(t) ? Math.max(0, Math.min(1, t)) : 0;
  const [a, b] = [hexToRgb(ends[0]), hexToRgb(ends[1])];
  return rgbToHex(
    a[0] + (b[0] - a[0]) * tt,
    a[1] + (b[1] - a[1]) * tt,
    a[2] + (b[2] - a[2]) * tt
  );
}

function scaleTForValue(value: unknown, domain: { min: number; max: number }): number | null {
  const n = parseDomainBound(value);
  if (n === null) return null;
  const { min, max } = domain;
  if (min === max) return 0.5;
  return (n - min) / (max - min);
}

/** E49：第一条 target=row 且可插值的 scale → hex；否则 null */
export function resolveRowScale(
  issue: Record<string, unknown>,
  scales: ColorScaleRule[] | undefined | null
): string | null {
  if (!scales || !scales.length) return null;
  for (const scale of scales) {
    if (scale.target !== 'row') continue;
    const actual = readIssueField(issue, scale.field);
    const t = scaleTForValue(actual, scale.domain);
    if (t === null) continue;
    return interpolateScaleColor(scale.palette, t);
  }
  return null;
}

/** E49：tint > scale */
export function resolveRowBackground(
  issue: Record<string, unknown>,
  opts: {
    conditionalFormats?: ConditionalFormatRule[] | null;
    colorScales?: ColorScaleRule[] | null;
  }
): { kind: 'tint' | 'scale'; value: string } | null {
  const tint = resolveRowTint(issue, opts.conditionalFormats);
  if (tint) return { kind: 'tint', value: tint };
  const hex = resolveRowScale(issue, opts.colorScales);
  if (hex) return { kind: 'scale', value: hex };
  return null;
}

/** E49：按 sets 序、rules 序先匹配；可选 field 过滤到该列 */
export function resolveCellIcon(
  issue: Record<string, unknown>,
  sets: IconSetRule[] | undefined | null,
  field?: string
): DisplayIcon | null {
  if (!sets || !sets.length) return null;
  for (const set of sets) {
    if (field && set.field !== field) continue;
    for (const rule of set.rules) {
      if (matchConditionalWhen(issue, { field: set.field, op: rule.op, value: rule.value })) {
        return rule.icon;
      }
    }
  }
  return null;
}

export function matchConditionalWhen(
  issue: Record<string, unknown>,
  when: { field: string; op: ConditionalOp; value: unknown }
): boolean {
  const actual = readIssueField(issue, when.field);
  if (actual === null || actual === undefined) return false;
  const op = when.op;
  const expected = when.value;
  if (op === 'eq') return actual == expected || String(actual) === String(expected);
  if (op === 'neq') return actual != expected && String(actual) !== String(expected);
  const aNum = Number(actual);
  const bNum = Number(expected);
  const numeric = !Number.isNaN(aNum) && !Number.isNaN(bNum);
  const aCmp: string | number = numeric ? aNum : String(actual);
  const bCmp: string | number = numeric ? bNum : String(expected);
  if (op === 'gt') return aCmp > bCmp;
  if (op === 'gte') return aCmp >= bCmp;
  if (op === 'lt') return aCmp < bCmp;
  if (op === 'lte') return aCmp <= bCmp;
  return false;
}

function readIssueField(issue: Record<string, unknown>, field: string): unknown {
  if (field.startsWith('cf:')) {
    const key = field.slice(3);
    const list = (issue.customFields || issue.custom_fields || []) as Array<Record<string, unknown>>;
    if (Array.isArray(list)) {
      const hit = list.find(x => String(x.key || '') === key);
      if (hit && !hit.error) return hit.value;
    }
    return null;
  }
  if (field === 'estimate_points') return issue.estimatePoints ?? issue.estimate_points;
  if (field === 'due_date') return issue.dueDate ?? issue.due_date;
  return issue[field];
}

export function formatCustomFieldCellValue(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (Array.isArray(value)) return value.map(String).join(', ') || '—';
  return String(value);
}

export function isSwimlaneByKey(value: unknown): value is SwimlaneBy {
  return isSwimlaneBy(value);
}

export function buildSwimlaneOptions(
  customFields?: Array<{
    key: string;
    name: string;
    type: string;
    formulaResultType?: string | null;
  }>
): { label: string; value: SwimlaneBy }[] {
  const extras = (customFields || [])
    .filter(f => f && f.key && isGroupingCfType(f.type, f.formulaResultType))
    .map(f => ({
      label: f.type === 'formula' ? `${f.name || f.key}（计算值·只读）` : f.name || f.key,
      value: `cf:${f.key}` as SwimlaneBy
    }));
  return [...SWIMLANE_OPTIONS, ...extras];
}

export { isGroupingCfType, parseCfDim, isCfDim };
