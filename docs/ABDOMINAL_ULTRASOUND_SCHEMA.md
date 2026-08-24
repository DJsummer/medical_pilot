# 腹部 B超 Schema 设计

> 检查类型：`abdominal_ultrasound`（腹部超声）
> 覆盖器官：肝脏、胆囊、胆管、胰腺、脾脏、双肾、膀胱

## 设计原则

1. **只描述所见，不做诊断** — `impression_hints` 仅为提示性短语，医生可改
2. **未提及 omit** — LLM 不填「正常」，由模板默认句式处理
3. **数值带单位** — `size_mm`、`thickness_mm` 等，校验层统一
4. **不确定标 uncertainty** — 字段级 `uncertainty: true`
5. **病灶用数组** — 同一器官可多个病灶

## 器官字段定义

### 肝脏 (liver)

| 字段 | 类型 | 说明 | 正常参考 |
|------|------|------|----------|
| `size` | object | 大小 | 肋下未探及 |
| `size.status` | enum | normal / enlarged / shrunk | |
| `size.description` | string | 如「右叶斜径约130mm」 | 斜径 ≤140mm |
| `morphology` | enum | normal / abnormal | |
| `morphology_description` | string | 形态异常描述 | |
| `capsule` | enum | smooth / rough / irregular | smooth |
| `parenchyma_echo` | enum | normal / increased / decreased / heterogeneous | normal |
| `parenchyma_description` | string | 实质回声补充 | |
| `vessels` | object | 血管 | |
| `vessels.portal_vein` | string | 门静脉 | 内径 ≤13mm |
| `vessels.hepatic_veins` | string | 肝静脉 | |
| `lesions` | array | 病灶列表 | |

**病灶 (liver.lesions[])**

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | enum | cyst / solid / calcification / hemangioma / other |
| `location` | string | 部位，如「右叶」 |
| `size_mm` | number | 大小 mm |
| `echo` | enum | anechoic / hypoechoic / hyperechoic / mixed / isoechoic |
| `boundary` | enum | clear / unclear |
| `shape` | enum | round / oval / irregular |
| `acoustic_shadow` | boolean | 后方声影 |
| `posterior_enhancement` | boolean | 后方增强 |
| `uncertainty` | boolean | 不确定 |

### 胆囊 (gallbladder)

| 字段 | 类型 | 说明 | 正常参考 |
|------|------|------|----------|
| `size` | object | | |
| `size.status` | enum | normal / enlarged / shrunk | |
| `size.length_mm` | number | 长径 | 长径 ≤80mm |
| `wall` | object | | |
| `wall.thickness_mm` | number | 壁厚 | ≤3mm |
| `wall.status` | enum | normal / thickened | |
| `wall.description` | string | | |
| `cavity` | object | 腔内 | |
| `cavity.description` | string | 腔内一般描述 | |
| `lesions` | array | 病灶（结石/息肉等） | |

**病灶 (gallbladder.lesions[])**

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | enum | stone / polyp / sludge / other |
| `size_mm` | number | |
| `echo` | enum | hyperechoic / hypoechoic / mixed |
| `mobility` | enum | mobile / immobile / not_tested |
| `acoustic_shadow` | boolean | |
| `attachment` | enum | intraluminal / wall_attached |
| `count` | enum | single / multiple |
| `uncertainty` | boolean | |

### 胆管 (bile_duct)

| 字段 | 类型 | 说明 | 正常参考 |
|------|------|------|----------|
| `common_bile_duct_mm` | number | 胆总管内径 | ≤6mm（术后可放宽） |
| `common_bile_duct_status` | enum | normal / dilated |
| `hepatic_duct` | string | 肝内胆管 | 未见扩张 |
| `description` | string | 补充 | |

### 胰腺 (pancreas)

| 字段 | 类型 | 说明 |
|------|------|------|
| `visibility` | enum | clear / partial / obscured |
| `size` | enum | normal / enlarged / atrophic |
| `echo` | enum | normal / increased / decreased / heterogeneous |
| `duct_mm` | number | 主胰管内径 | ≤2mm |
| `lesions` | array | 同肝脏病灶结构简化版 |

### 脾脏 (spleen)

| 字段 | 类型 | 说明 | 正常参考 |
|------|------|------|----------|
| `size` | object | | |
| `size.thickness_mm` | number | 厚径 | ≤40mm |
| `size.status` | enum | normal / enlarged |
| `echo` | enum | normal / increased / decreased / heterogeneous |
| `lesions` | array | |

### 肾脏 (kidneys)

左右各一：`kidneys.left` / `kidneys.right`

| 字段 | 类型 | 说明 | 正常参考 |
|------|------|------|----------|
| `size` | object | | |
| `size.length_mm` | number | 长径 | 90-120mm |
| `size.width_mm` | number | 宽径 | |
| `morphology` | enum | normal / abnormal |
| `cortex_echo` | enum | normal / increased / decreased |
| `cortex_thickness` | enum | normal / thinned |
| `collecting_system` | string | 集合系统 | 未见分离 |
| `lesions` | array | |

**病灶 (kidneys.*.lesions[])**

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | enum | cyst / stone / solid / calcification / other |
| `location` | string | 上极/中极/下极 |
| `size_mm` | number | |
| `echo` | enum | |
| `acoustic_shadow` | boolean | |
| `uncertainty` | boolean | |

### 膀胱 (bladder)

| 字段 | 类型 | 说明 |
|------|------|------|
| `filling` | enum | good / poor / empty |
| `wall` | enum | smooth / rough / thickened |
| `wall_thickness_mm` | number | |
| `cavity` | string | 腔内描述 |
| `lesions` | array | |

### 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `exam_type` | string | `abdominal_ultrasound` |
| `organs_examined` | array | 实际检查的器官列表 |
| `free_fluid` | object | 腹腔积液 |
| `free_fluid.present` | boolean | |
| `free_fluid.description` | string | |
| `other_findings` | string | 其他所见 |
| `impression_hints` | array | AI 提示性短语（非诊断） |
| `metadata` | object | |
| `metadata.asr_text` | string | 原始 ASR |
| `metadata.uncertain_fields` | array | 不确定字段路径 |

## 口语 → 标准表达映射（示例）

| 医生口语 | Schema 字段 | 标准报告表达 |
|----------|-------------|--------------|
| 肝实质回声稍增强 | liver.parenchyma_echo=increased | 肝实质回声稍增强 |
| 胆囊里有个六毫米强回声 | gallbladder.lesions[].type=polyp, size_mm=6 | 腔内可见约6mm强回声 |
| 不动 | mobility=immobile | 改变体位不移动 |
| 没有声影 | acoustic_shadow=false | 后方未见明显声影 |
| 壁不厚 | wall.status=normal | 壁不厚 |
| 胆总管八毫米 | common_bile_duct_mm=8 | 胆总管内径约8mm |

## JSON 完整示例

见 `data/gold_dataset/abdominal_20_samples.json` 第 1 条。
