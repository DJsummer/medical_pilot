const { createApp, ref, reactive, onMounted, onBeforeUnmount, nextTick } = Vue;

const TreeNode = {
  name: 'TreeNode',
  props: {
    data: { required: true },
    path: { type: String, default: '' },
    highlightPath: { type: String, default: '' },
    label: { type: String, default: '' },
  },
  emits: ['select'],
  template: `
    <div class="tree-node">
      <template v-if="isPrimitive">
        <div
          class="tree-row clickable"
          :class="{ highlight: path === highlightPath }"
          @click="$emit('select', path)"
        >
          <span class="tree-key">{{ displayLabel }}：</span>
          <span class="tree-value">{{ displayValue }}</span>
        </div>
      </template>
      <template v-else-if="isArray">
        <div v-if="label" class="tree-key" style="padding:2px 4px">{{ label }}</div>
        <div v-for="(item, i) in data" :key="i" class="tree-children">
          <tree-node
            :data="item"
            :path="childPath(i)"
            :highlight-path="highlightPath"
            :label="'[' + i + ']'"
            @select="$emit('select', $event)"
          />
        </div>
      </template>
      <template v-else>
        <div v-if="label" class="tree-key" style="padding:2px 4px;font-weight:600">{{ label }}</div>
        <div v-for="(val, key) in data" :key="key" class="tree-children">
          <tree-node
            :data="val"
            :path="childPath(key)"
            :highlight-path="highlightPath"
            :label="organLabel(key)"
            @select="$emit('select', $event)"
          />
        </div>
      </template>
    </div>
  `,
  computed: {
    isPrimitive() {
      const t = typeof this.data;
      return t === 'string' || t === 'number' || t === 'boolean' || this.data === null;
    },
    isArray() {
      return Array.isArray(this.data);
    },
    displayLabel() {
      if (this.label) return this.label;
      const parts = this.path.split('.');
      return fieldLabel(parts[parts.length - 1] || 'root');
    },
    displayValue() {
      if (this.data === null) return '—';
      if (typeof this.data === 'boolean') return this.data ? '是' : '否';
      return String(this.data);
    },
  },
  methods: {
    childPath(key) {
      if (!this.path) return String(key);
      return `${this.path}.${key}`;
    },
    organLabel(key) {
      return ORGAN_LABELS[key] || key;
    },
  },
};

const ORGAN_LABELS = {
  liver: '肝脏',
  gallbladder: '胆囊',
  bile_duct: '胆管',
  pancreas: '胰腺',
  spleen: '脾脏',
  kidneys: '双肾',
  left: '左肾',
  right: '右肾',
  bladder: '膀胱',
  free_fluid: '腹腔积液',
  thyroid_right: '甲状腺右叶',
  thyroid_left: '甲状腺左叶',
  isthmus: '峡部',
  breast_right: '右侧乳腺',
  breast_left: '左侧乳腺',
  uterus: '子宫',
  ovary_left: '左侧卵巢',
  ovary_right: '右侧卵巢',
  adnexa: '附件',
  lv: '左室',
  rv: '右室',
  atria: '心房',
  valves: '瓣膜',
  pericardium: '心包',
  carotid_right: '右侧颈动脉',
  carotid_left: '左侧颈动脉',
  vertebral: '椎动脉',
  lower_limb: '下肢血管',
  cervical: '颈部淋巴结',
  axillary: '腋窝淋巴结',
  other: '其他淋巴结',
  nodules: '结节',
  plaques: '斑块',
  cysts: '囊性包块',
  fibroids: '肌瘤',
  impression_hints: '提示',
  metadata: '元数据',
  lesions: '病灶',
  size: '大小',
  wall: '壁',
  vessels: '血管',
  cavity: '腔内',
  organs_examined: '检查器官',
  exam_type: '检查类型',
};

function fieldLabel(key) {
  const map = {
    status: '状态',
    type: '类型',
    size_mm: '大小(mm)',
    echo: '回声',
    mobility: '移动性',
    acoustic_shadow: '声影',
    thickness_mm: '厚度(mm)',
    length_mm: '长径(mm)',
    common_bile_duct_mm: '胆总管(mm)',
    asr_text: '原话',
    uncertain_fields: '不确定项',
    right_lobe: '右叶',
    left_lobe: '左叶',
    upper_pole: '上极',
    lower_pole: '下极',
    hypoechoic: '低回声',
    hyperechoic: '强回声',
    anechoic: '无回声',
    clear: '边界清',
    unclear: '边界欠清',
  };
  return map[key] || ORGAN_LABELS[key] || key;
}

function formatReportNo() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `US${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}${p(d.getHours())}${p(d.getMinutes())}`;
}

function formatChatTime() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}`;
}

function splitToUtterances(text) {
  if (!text || !text.trim()) return [];
  const parts = text
    .replace(/\n/g, '。')
    .split(/[。；]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  const t = formatChatTime();
  return parts.map((s, i) => ({
    id: `u-${Date.now()}-${i}`,
    text: s,
    time: t,
    source: 'loaded',
  }));
}

function formatExamDate() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

createApp({
  components: { TreeNode },
  setup() {
    const asrText = ref('');
    const structured = ref(null);
    const findingsText = ref('');
    const impressionText = ref('');
    const warnings = ref([]);
    const loading = ref(false);
    const error = ref('');
    const llmEnabled = ref(false);
    const llmUsed = ref(false);
    const useLlm = ref(true);
    const goldSamples = ref([]);
    const selectedSampleId = ref('');
    const examTypes = ref([]);
    const selectedExamType = ref('abdominal_ultrasound');
    const highlightPath = ref('');
    const editLog = ref([]);
    const reportId = ref('');
    const reportStatus = ref('draft');
    const saving = ref(false);
    const signing = ref(false);
    const savedReports = ref([]);
    const selectedReportId = ref('');

    const asrSupportsServer = ref(false);
    const asrSupportsBrowser = ref(false);
    const asrMode = ref('server');
    const asrStatus = ref('idle');
    const asrActive = ref(false);
    const asrButtonLabel = ref('点击录音');
    const asrStatusText = ref('');
    const asrInterim = ref('');
    const utterances = ref([]);
    const chatScrollRef = ref(null);
    let asrController = null;

    const reportNo = ref(formatReportNo());
    const examDate = ref(formatExamDate());
    const examPart = ref('腹部超声');
    const deviceModel = ref('');

    const patient = reactive({
      name: '',
      sex: '',
      age: '',
      outpatient_no: '',
      inpatient_no: '',
      bed_no: '',
      dept: '',
    });

    const signatures = reactive({
      examiner: '',
      recorder: '',
      reviewer: '',
    });

    let editDebounce = null;
    let lastFindings = '';
    let lastImpression = '';

    async function api(path, options = {}) {
      const res = await fetch(`/api${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
      });
      const text = await res.text();
      try {
        return JSON.parse(text);
      } catch {
        const snippet = text.slice(0, 120).replace(/\s+/g, ' ');
        throw new Error(
          res.ok
            ? `响应不是 JSON: ${snippet}`
            : `HTTP ${res.status}: ${snippet || res.statusText}`,
        );
      }
    }

    async function loadSavedReports() {
      const data = await api('/reports');
      savedReports.value = data.reports || [];
    }

    function buildSavePayload() {
      const et = structured.value?.exam_type || selectedExamType.value;
      return {
        id: reportId.value || undefined,
        exam_type: et,
        exam_part: examPart.value,
        report_no: reportNo.value,
        exam_date: examDate.value,
        device_model: deviceModel.value,
        patient: { ...patient },
        signatures: { ...signatures },
        asr_text: asrText.value,
        structured: structured.value || {},
        findings_text: findingsText.value,
        impression_text: impressionText.value,
        warnings: warnings.value,
        edit_log: editLog.value,
        status: reportStatus.value,
      };
    }

    async function saveDraft() {
      saving.value = true;
      error.value = '';
      try {
        const data = await api('/reports', {
          method: 'POST',
          body: JSON.stringify(buildSavePayload()),
        });
        if (!data.ok) {
          error.value = data.error || '保存失败';
          return;
        }
        reportId.value = data.report.id;
        reportStatus.value = data.report.status || 'draft';
        await loadSavedReports();
      } catch (e) {
        error.value = String(e);
      } finally {
        saving.value = false;
      }
    }

    async function signReport() {
      if (!reportId.value) await saveDraft();
      if (!reportId.value) return;
      signing.value = true;
      error.value = '';
      try {
        const hasError = warnings.value.some((w) => w.severity === 'error');
        const data = await api(`/reports/${reportId.value}/sign`, {
          method: 'POST',
          body: JSON.stringify({ force: !hasError }),
        });
        if (!data.ok) {
          error.value = data.error || '签发失败';
          return;
        }
        reportStatus.value = 'signed';
        await loadSavedReports();
      } catch (e) {
        error.value = String(e);
      } finally {
        signing.value = false;
      }
    }

    async function loadReport() {
      if (!selectedReportId.value) return;
      const data = await api(`/reports/${selectedReportId.value}`);
      if (!data.ok || !data.report) {
        error.value = data.error || '加载失败';
        return;
      }
      const r = data.report;
      reportId.value = r.id;
      reportStatus.value = r.status || 'draft';
      reportNo.value = r.report_no || formatReportNo();
      examDate.value = r.exam_date || formatExamDate();
      examPart.value = r.exam_part || '腹部超声';
      if (r.exam_type) selectedExamType.value = r.exam_type;
      if (r.structured?.exam_type) selectedExamType.value = r.structured.exam_type;
      deviceModel.value = r.device_model || '';
      Object.assign(patient, r.patient || {});
      Object.assign(signatures, r.signatures || {});
      asrText.value = r.asr_text || '';
      setUtterancesFromText(r.asr_text || '');
      structured.value = r.structured || null;
      findingsText.value = r.findings_text || '';
      impressionText.value = r.impression_text || '';
      warnings.value = r.warnings || [];
      editLog.value = r.edit_log || [];
      lastFindings = findingsText.value;
      lastImpression = impressionText.value;
    }

    async function regenerateReport() {
      if (!structured.value) return;
      loading.value = true;
      error.value = '';
      try {
        const data = await api('/report/generate', {
          method: 'POST',
          body: JSON.stringify({ structured: structured.value }),
        });
        findingsText.value = data.findings_text || '';
        impressionText.value = data.impression_text || '';
        warnings.value = data.warnings || [];
        lastFindings = findingsText.value;
        lastImpression = impressionText.value;
        reportStatus.value = 'draft';
      } catch (e) {
        error.value = String(e);
      } finally {
        loading.value = false;
      }
    }

    function syncAsrText() {
      asrText.value = utterances.value.map((u) => u.text).join('，');
    }

    function scrollChatToBottom() {
      nextTick(() => {
        const el = chatScrollRef.value;
        if (el) el.scrollTop = el.scrollHeight;
      });
    }

    function addUtterance(text, source = 'asr') {
      const t = (text || '').trim();
      if (!t) return;
      utterances.value.push({
        id: `u-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        text: t,
        time: formatChatTime(),
        source,
      });
      syncAsrText();
      scrollChatToBottom();
    }

    function setUtterancesFromText(text) {
      utterances.value = splitToUtterances(text);
      syncAsrText();
      scrollChatToBottom();
    }

    function updateAsrLabel() {
      const s = asrStatus.value;
      const m = asrMode.value;
      if (s === 'transcribing') asrButtonLabel.value = '转写中…';
      else if (s === 'recording') asrButtonLabel.value = '结束并转写';
      else if (s === 'listening') asrButtonLabel.value = '停止听写';
      else if (m === 'server') asrButtonLabel.value = '点击录音';
      else asrButtonLabel.value = '开始听写';
      if (s === 'recording') asrStatusText.value = '正在聆听…';
      else if (s === 'listening') asrStatusText.value = '正在听写…';
      else if (s === 'transcribing') asrStatusText.value = '正在转写…';
      else asrStatusText.value = '';
    }

    function initAsrController() {
      if (!window.MedicalASR) return;
      asrController = window.MedicalASR.createAsrController({
        serverAsrEnabled: asrSupportsServer.value,
        onUtterance: (text) => addUtterance(text, 'asr'),
        onInterim: (text) => {
          asrInterim.value = text;
          scrollChatToBottom();
        },
        onStatus: (status) => {
          asrStatus.value = status;
          asrActive.value = status === 'recording' || status === 'listening' || status === 'transcribing';
          if (status === 'idle') asrInterim.value = '';
          updateAsrLabel();
          scrollChatToBottom();
        },
        onError: (msg) => {
          error.value = msg;
        },
      });
      asrSupportsBrowser.value = asrController.supportsBrowser();
      asrMode.value = asrController.getMode();
      updateAsrLabel();
    }

    function toggleAsr() {
      if (asrController) asrController.toggle();
    }

    function onAsrModeChange() {
      if (!asrController) return;
      asrController.stop();
      asrController.setMode(asrMode.value);
      updateAsrLabel();
    }

    async function loadHealth() {
      const h = await api('/health');
      llmEnabled.value = h.llm_enabled;
      if (!h.llm_enabled) useLlm.value = false;
      asrSupportsServer.value = h.asr_enabled;
      initAsrController();
    }

    async function loadExamTypes() {
      const data = await api('/exam-types');
      examTypes.value = data.exam_types || [];
      if (!examTypes.value.find((t) => t.id === selectedExamType.value)) {
        selectedExamType.value = examTypes.value[0]?.id || 'abdominal_ultrasound';
      }
      const current = examTypes.value.find((t) => t.id === selectedExamType.value);
      if (current) examPart.value = current.label;
    }

    async function loadGoldList() {
      const data = await api(`/gold-dataset?exam_type=${encodeURIComponent(selectedExamType.value)}`);
      goldSamples.value = data.samples || [];
      if (goldSamples.value.length && !goldSamples.value.find((s) => s.id === selectedSampleId.value)) {
        selectedSampleId.value = goldSamples.value[0].id;
      }
    }

    async function onExamTypeChange() {
      const current = examTypes.value.find((t) => t.id === selectedExamType.value);
      if (current) examPart.value = current.label;
      structured.value = null;
      findingsText.value = '';
      impressionText.value = '';
      warnings.value = [];
      reportStatus.value = 'draft';
      reportId.value = '';
      await loadGoldList();
      if (goldSamples.value.length) {
        selectedSampleId.value = goldSamples.value[0].id;
        await loadSample();
      } else {
        selectedSampleId.value = '';
        utterances.value = [];
        syncAsrText();
      }
    }

    async function loadSample() {
      if (!selectedSampleId.value) return;
      const data = await api(`/gold-dataset/${selectedSampleId.value}`);
      if (data.ok && data.sample) {
        setUtterancesFromText(data.sample.asr_text);
      }
    }

    function recordEdit(field, value) {
      clearTimeout(editDebounce);
      editDebounce = setTimeout(() => {
        const prev = field === 'findings_text' ? lastFindings : lastImpression;
        if (value !== prev) {
          const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
          editLog.value.unshift({ field, time });
          if (field === 'findings_text') lastFindings = value;
          else lastImpression = value;
        }
      }, 600);
    }

    function onTreeSelect(path) {
      highlightPath.value = path;
    }

    async function runPipeline() {
      loading.value = true;
      error.value = '';
      reportNo.value = formatReportNo();
      try {
        const body = {
          asr_text: asrText.value,
          use_llm: useLlm.value && llmEnabled.value,
          sample_id: selectedSampleId.value || undefined,
          exam_type: selectedExamType.value,
        };
        const data = await api('/pipeline', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        if (!data.structured || Object.keys(data.structured).length === 0) {
          error.value = data.error || '生成失败';
          return;
        }
        structured.value = data.structured;
        findingsText.value = data.findings_text || '';
        impressionText.value = data.impression_text || '';
        warnings.value = data.warnings || [];
        llmUsed.value = data.llm_used;
        lastFindings = findingsText.value;
        lastImpression = impressionText.value;
        if (data.error) error.value = data.error;
        reportStatus.value = 'draft';
      } catch (e) {
        error.value = String(e);
      } finally {
        loading.value = false;
      }
    }

    onMounted(async () => {
      await loadHealth();
      await loadExamTypes();
      await loadGoldList();
      await loadSavedReports();
      if (goldSamples.value.length) {
        selectedSampleId.value = goldSamples.value[0].id;
        await loadSample();
      }
    });

    onBeforeUnmount(() => {
      if (asrController) asrController.destroy();
    });

    return {
      asrText,
      structured,
      findingsText,
      impressionText,
      warnings,
      loading,
      error,
      llmEnabled,
      llmUsed,
      useLlm,
      goldSamples,
      selectedSampleId,
      examTypes,
      selectedExamType,
      onExamTypeChange,
      highlightPath,
      editLog,
      reportNo,
      examDate,
      examPart,
      deviceModel,
      patient,
      signatures,
      reportId,
      reportStatus,
      saving,
      signing,
      savedReports,
      selectedReportId,
      asrSupportsServer,
      asrSupportsBrowser,
      asrMode,
      asrStatus,
      asrActive,
      asrButtonLabel,
      asrStatusText,
      asrInterim,
      utterances,
      chatScrollRef,
      toggleAsr,
      onAsrModeChange,
      loadSample,
      loadReport,
      runPipeline,
      regenerateReport,
      saveDraft,
      signReport,
      onTreeSelect,
      recordEdit,
    };
  },
}).mount('#app');
