import {
  $,
  $$,
  icon,
  hydrateIcons,
  escapeHtml,
  bindModalClose,
  closeModal,
  toggleTheme,
} from "../ui-core.js?v=20261106-29";
import { AnatomyAtlasViewer, SYSTEM_META } from "./anatomy-atlas.js?v=20261106-29";

const SIDE_LABEL = { left: "左", right: "右" };

const FIXED_REGIONS = {
  head: {
    label: "头部与面部",
    anatomy: "包含颅骨、脑、眼、耳、鼻窦、口腔和下颌等结构。",
    symptoms: ["头痛", "头晕", "视物异常", "面部疼痛", "发热"],
    questions: ["持续了多久，是突发还是逐渐出现？", "是否伴有恶心、发热、视物异常或肢体无力？", "近期是否有头部外伤、熬夜或血压异常？"],
    warning: "突发剧烈头痛、意识改变、口角歪斜、单侧肢体无力、言语不清，或头部外伤后反复呕吐、嗜睡，应立即就医或拨打 120。",
    prompt: "我主要在头部或面部不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  backHead: {
    label: "后枕部与颈后",
    anatomy: "包含枕部、颅颈交界、颈椎后侧和后颈肌群。",
    symptoms: ["后枕部头痛", "颈后僵硬", "活动受限", "眩晕"],
    questions: ["疼痛是否会随转头或低头加重？", "是否伴有发热、恶心、视物异常或肢体麻木？", "近期是否有外伤或长时间保持同一姿势？"],
    warning: "颈部外伤后疼痛、发热伴颈部僵硬、突发眩晕并行走不稳，或神经症状进行性加重，应及时就医。",
    prompt: "我主要在后枕部或颈后不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  neck: {
    label: "颈部与咽喉",
    anatomy: "包含颈椎、气管、食管、甲状腺、颈部血管和淋巴结。",
    symptoms: ["颈痛", "咽痛", "吞咽不适", "颈部肿块", "活动受限"],
    questions: ["是否有外伤，疼痛会向肩臂或头部放射吗？", "是否伴有吞咽困难、声音改变或呼吸不畅？", "有无发热、颈部肿块或淋巴结肿大？"],
    warning: "呼吸困难、吞咽困难、颈部快速肿胀、外伤后活动障碍，或声音突然改变并持续加重，应立即就医。",
    prompt: "我主要在颈部或咽喉不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  backNeck: {
    label: "颈后与上颈椎",
    anatomy: "包含颈椎、枕下肌群、后颈韧带与神经。",
    symptoms: ["颈后疼痛", "僵硬", "转头受限", "肩背牵拉感"],
    questions: ["疼痛是否向手臂放射或伴麻木？", "是否有外伤、发热、晨僵或近期剧烈运动？", "哪些动作会明显加重或缓解？"],
    warning: "外伤后颈痛、四肢麻木无力、行走不稳、大小便异常，或发热伴颈部僵硬，应及时就医。",
    prompt: "我主要在颈后或上颈椎不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  chest: {
    label: "胸部",
    anatomy: "包含心脏、肺、胸骨、肋骨、食管及胸壁肌肉。",
    symptoms: ["胸痛", "胸闷", "心悸", "咳嗽", "呼吸困难"],
    questions: ["疼痛是压迫感、刺痛还是烧灼感？", "是否向肩臂、下颌或背部放射？", "是否伴出汗、呼吸困难、心悸或活动后加重？"],
    warning: "持续超过 15 分钟的压榨性胸痛、胸痛伴大汗或呼吸困难、突然晕厥，应立即拨打 120。",
    prompt: "我主要在胸部不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  upperBack: {
    label: "上背部与肩胛区",
    anatomy: "包含胸椎、肩胛骨、肋骨后侧、背部肌群和神经。",
    symptoms: ["上背痛", "肩胛间疼痛", "僵硬", "活动受限"],
    questions: ["疼痛是否与呼吸、咳嗽或转身有关？", "是否向胸部、手臂放射或伴有麻木无力？", "近期是否有外伤、久坐或突然负重？"],
    warning: "突发撕裂样背痛、背痛伴呼吸困难或冷汗、发热伴局部压痛，或进行性肢体无力，应及时就医。",
    prompt: "我主要在上背部或肩胛区不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  abdomen: {
    label: "腹部",
    anatomy: "包含胃、肠道、肝脏、胆囊、胰腺及腹壁结构。",
    symptoms: ["腹痛", "腹胀", "恶心", "呕吐", "食欲下降"],
    questions: ["具体在腹部哪一象限，疼痛会转移吗？", "与进食、排便或体位是否有关？", "是否有发热、呕血、黑便、持续呕吐或腹部僵硬？"],
    warning: "剧烈持续腹痛、腹部坚硬拒按、呕血或黑便、持续呕吐，或腹痛伴高热和意识改变，应立即就医。",
    prompt: "我主要在腹部不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  lowerBack: {
    label: "下背部与腰骶区",
    anatomy: "包含腰椎、椎间盘、腰背肌群、骶髂关节及肾脏邻近区域。",
    symptoms: ["下背痛", "腰部僵硬", "放射痛", "活动受限"],
    questions: ["疼痛是否向臀部或腿部放射，伴麻木无力？", "是否有外伤、发热或夜间痛醒？", "是否有排尿异常、血尿或近期负重扭伤？"],
    warning: "出现会阴麻木、大小便失控、双腿进行性无力，或发热伴剧烈腰痛，应立即就医。",
    prompt: "我主要在下背部或腰骶区不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  pelvis: {
    label: "骨盆与下腹",
    anatomy: "包含膀胱、直肠、生殖器官、骨盆骨和髋关节邻近结构。",
    symptoms: ["下腹痛", "骨盆痛", "排尿不适", "排便不适", "髋部疼痛"],
    questions: ["是否伴尿频、尿痛、血尿或排便异常？", "女性是否存在妊娠可能、异常出血或月经变化？", "是否有外伤、发热或活动时髋部疼痛？"],
    warning: "妊娠期下腹痛或出血、突发单侧剧痛、无法排尿，或骨盆外伤后不能负重，应及时就医。",
    prompt: "我主要在骨盆或下腹不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
  sacrum: {
    label: "骶尾部与尾骨",
    anatomy: "包含骶骨、尾骨、骶髂关节、骨盆底和骶神经。",
    symptoms: ["尾骨痛", "久坐疼痛", "骶尾部压痛", "排便不适"],
    questions: ["是否有跌倒、撞击或长时间骑行？", "疼痛是否只在坐硬物时出现？", "是否伴下肢麻木、大小便异常或局部皮肤破损？"],
    warning: "外伤后剧痛、局部畸形、会阴麻木或大小便功能改变，应及时就医。",
    prompt: "我主要在骶尾部或尾骨不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。",
  },
};

const SIDE_REGIONS = {
  upperArm: {
    label: "上臂与肩部",
    anatomy: "包含肩关节、肱骨、上臂肌群及邻近神经。",
    symptoms: ["肩臂痛", "抬臂受限", "肌肉酸痛", "局部肿胀"],
    questions: ["是否有外伤、突然提重物或重复运动？", "能否抬臂，疼痛是否向肘部或手指放射？", "是否伴麻木、无力、明显肿胀或畸形？"],
    warning: "外伤后明显畸形、无法活动、手指发凉或麻木加重，应及时就医。",
  },
  forearm: {
    label: "前臂",
    anatomy: "包含尺骨、桡骨、前臂肌群、肌腱和神经。",
    symptoms: ["前臂疼痛", "手腕活动痛", "局部肿胀", "麻木"],
    questions: ["是否有碰撞、扭伤或重复用力？", "手指活动、握力和感觉是否正常？", "局部是否明显肿胀、变形或皮肤发凉？"],
    warning: "明显畸形、无法握拳、手指持续麻木或皮肤苍白发凉，应及时就医。",
  },
  hand: {
    label: "手部",
    anatomy: "包含腕骨、掌骨、指骨、关节、肌腱和神经。",
    symptoms: ["手痛", "腕痛", "手指麻木", "握力下降"],
    questions: ["哪几根手指受影响，麻木是否固定？", "是否有外伤、劳损或晨起僵硬？", "手部是否明显肿胀、变形或活动困难？"],
    warning: "手部外伤后畸形、无法活动、持续苍白发凉，或突发单侧无力与言语异常，应及时就医。",
  },
  thigh: {
    label: "大腿与髋部",
    anatomy: "包含股骨、髋关节、大腿肌群、血管和神经。",
    symptoms: ["大腿痛", "髋部痛", "走路受限", "放射痛"],
    questions: ["疼痛在腹股沟、大腿前侧还是外侧？", "是否与走路、蹲起或转髋有关？", "是否有外伤、发热、肿胀或无法负重？"],
    warning: "外伤后无法负重、腿部明显短缩或外旋、进行性肿胀，或发热伴髋部剧痛，应及时就医。",
  },
  knee: {
    label: "膝部",
    anatomy: "包含膝关节、髌骨、半月板、韧带和周围肌腱。",
    symptoms: ["膝痛", "肿胀", "卡顿", "上下楼疼痛"],
    questions: ["是否有扭伤、撞击或近期增加运动量？", "膝盖是否会卡住、打软腿或明显肿胀？", "能否弯曲和完全伸直？"],
    warning: "膝关节明显肿胀变形、无法负重、关节锁死，或外伤后迅速肿大，应及时就医。",
  },
  shin: {
    label: "小腿",
    anatomy: "包含胫骨、腓骨、小腿肌群、肌腱和血管神经。",
    symptoms: ["小腿痛", "抽筋", "肿胀", "行走疼痛"],
    questions: ["是单侧还是双侧，是否伴小腿肿胀发热？", "近期是否有久坐、长途旅行、运动或外伤？", "是否出现气短、胸痛或皮肤颜色改变？"],
    warning: "单侧小腿突然肿胀发热并伴气短或胸痛，需警惕血栓并立即就医；外伤后畸形或无法行走也应就医。",
  },
  foot: {
    label: "足部与踝关节",
    anatomy: "包含踝关节、足骨、足底筋膜、肌腱和神经。",
    symptoms: ["足痛", "踝痛", "扭伤", "行走困难", "肿胀"],
    questions: ["是否有扭伤、崴脚或长时间站立行走？", "能否负重，局部是否明显肿胀或瘀青？", "是否有糖尿病、感觉减退或伤口久不愈合？"],
    warning: "踝足外伤后畸形、无法负重、足趾发凉麻木，或糖尿病患者足部伤口感染，应及时就医。",
  },
};

function sideRegion(base, side) {
  const data = SIDE_REGIONS[base];
  const prefix = SIDE_LABEL[side];
  return {
    ...data,
    id: `${base}-${side}`,
    label: `${prefix}${data.label.replace(/与.*$/, "")}`,
    prompt: `我主要在${prefix}${data.label.replace(/与.*$/, "")}不适。请解释这个区域可能涉及哪些结构、常见相关症状，以及我需要补充哪些信息来判断风险。`,
  };
}

function resolveRegion(partId, yaw) {
  const back = Math.cos(yaw) < -0.15;
  const torsoMap = {
    head: back ? "backHead" : "head",
    neck: back ? "backNeck" : "neck",
    chest: back ? "upperBack" : "chest",
    abdomen: back ? "lowerBack" : "abdomen",
    pelvis: back ? "sacrum" : "pelvis",
  };
  if (torsoMap[partId]) {
    return { id: torsoMap[partId], ...FIXED_REGIONS[torsoMap[partId]] };
  }
  const match = partId.match(/^(upperArm|forearm|hand|thigh|knee|shin|foot)-(left|right)$/);
  return match ? sideRegion(match[1], match[2]) : null;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function readStoredGender() {
  try {
    return localStorage.getItem("zhiheng_body_gender") === "female" ? "female" : "male";
  } catch {
    return "male";
  }
}

function storeGender(gender) {
  try {
    localStorage.setItem("zhiheng_body_gender", gender);
  } catch {
    // The current model selection still applies when storage is unavailable.
  }
}

class BodyModel {
  constructor(canvas, onSelect) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSelect = onSelect;
    this.gender = readStoredGender();
    this.zoom = 1;
    this.yaw = 0;
    this.pitch = 0.04;
    this.selectedPart = null;
    this.dragging = false;
    this.pointer = { x: 0, y: 0, startX: 0, startY: 0, moved: 0 };
    this.width = 0;
    this.height = 0;
    this.frame = null;
    this.hitParts = [];
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    this.bindEvents();
    this.resize();
  }

  bindEvents() {
    this.canvas.addEventListener("pointerdown", (event) => {
      this.dragging = true;
      this.pointer = {
        x: event.clientX,
        y: event.clientY,
        startX: event.clientX,
        startY: event.clientY,
        moved: 0,
      };
      this.canvas.setPointerCapture(event.pointerId);
      this.canvas.classList.add("is-dragging");
    });
    this.canvas.addEventListener("pointermove", (event) => {
      if (!this.dragging) return;
      const dx = event.clientX - this.pointer.x;
      const dy = event.clientY - this.pointer.y;
      this.pointer.moved += Math.abs(dx) + Math.abs(dy);
      this.pointer.x = event.clientX;
      this.pointer.y = event.clientY;
      this.yaw += dx * 0.012;
      this.pitch = clamp(this.pitch + dy * 0.005, -0.42, 0.42);
      this.schedule();
    });
    const finishPointer = (event) => {
      if (!this.dragging) return;
      this.dragging = false;
      this.canvas.classList.remove("is-dragging");
      if (this.canvas.hasPointerCapture?.(event.pointerId)) {
        this.canvas.releasePointerCapture(event.pointerId);
      }
      if (this.pointer.moved < 7) this.pick(event);
    };
    this.canvas.addEventListener("pointerup", finishPointer);
    this.canvas.addEventListener("pointercancel", finishPointer);
    this.canvas.addEventListener("dblclick", () => this.resetView());
  }

  destroy() {
    if (this.frame) cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
  }

  refreshTheme() {
    this.schedule();
  }

  setGender(gender) {
    this.gender = gender === "female" ? "female" : "male";
    storeGender(this.gender);
    this.schedule();
  }

  setZoom(value) {
    this.zoom = clamp(Number(value) || 1, 0.72, 1.65);
    const slider = $("#body-map-zoom");
    if (slider) slider.value = String(Math.round(this.zoom * 100));
    const valueLabel = $("#body-map-zoom-value");
    if (valueLabel) valueLabel.textContent = `${Math.round(this.zoom * 100)}%`;
    this.schedule();
  }

  resetView() {
    this.yaw = 0;
    this.pitch = 0.04;
    this.setZoom(1);
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.width = rect.width;
    this.height = rect.height;
    this.canvas.width = Math.max(1, Math.round(rect.width * dpr));
    this.canvas.height = Math.max(1, Math.round(rect.height * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.schedule();
  }

  schedule() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = null;
      this.draw();
    });
  }

  project(point) {
    const [x, y, z] = point;
    const cosYaw = Math.cos(this.yaw);
    const sinYaw = Math.sin(this.yaw);
    const cosPitch = Math.cos(this.pitch);
    const sinPitch = Math.sin(this.pitch);
    const x1 = x * cosYaw + z * sinYaw;
    const z1 = -x * sinYaw + z * cosYaw;
    const y1 = y * cosPitch - z1 * sinPitch;
    const z2 = y * sinPitch + z1 * cosPitch;
    const perspective = 8.5 / (8.5 - z2);
    const unit = Math.min(this.width / 4.5, this.height / 8.7) * 0.96 * this.zoom;
    return {
      x: this.width / 2 + x1 * unit * perspective,
      y: this.height * 0.52 - y1 * unit * perspective,
      z: z2,
      unit: unit * perspective,
    };
  }

  buildParts() {
    const female = this.gender === "female";
    const shoulder = female ? 0.76 : 0.9;
    const chest = female ? 0.72 : 0.82;
    const waist = female ? 0.58 : 0.65;
    const hip = female ? 0.79 : 0.68;
    const armX = female ? 0.86 : 0.98;
    return [
      { id: "head", kind: "ellipsoid", center: [0, 3.32, 0], radii: [0.44, 0.54, 0.42] },
      { id: "neck", kind: "capsule", a: [0, 2.66, 0], b: [0, 2.85, 0], radius: 0.18, region: "neck" },
      { id: "chest", kind: "ellipsoid", center: [0, 2.02, 0], radii: [chest, 0.62, 0.46], region: "chest" },
      { id: "abdomen", kind: "ellipsoid", center: [0, 1.04, 0], radii: [waist, 0.6, 0.4], region: "abdomen" },
      { id: "pelvis", kind: "ellipsoid", center: [0, 0.28, 0], radii: [hip, 0.43, 0.4], region: "pelvis" },
      { id: "shoulder-left", kind: "ellipsoid", center: [shoulder, 2.27, 0], radii: [0.2, 0.21, 0.21], region: "upperArm-left", joint: true },
      { id: "shoulder-right", kind: "ellipsoid", center: [-shoulder, 2.27, 0], radii: [0.2, 0.21, 0.21], region: "upperArm-right", joint: true },
      { id: "upperArm-left", kind: "capsule", a: [shoulder, 2.2, 0], b: [armX, 1.26, 0], radius: female ? 0.13 : 0.15, region: "upperArm-left" },
      { id: "upperArm-right", kind: "capsule", a: [-shoulder, 2.2, 0], b: [-armX, 1.26, 0], radius: female ? 0.13 : 0.15, region: "upperArm-right" },
      { id: "forearm-left", kind: "capsule", a: [armX, 1.25, 0], b: [armX + 0.1, 0.28, 0], radius: 0.105, region: "forearm-left" },
      { id: "forearm-right", kind: "capsule", a: [-armX, 1.25, 0], b: [-armX - 0.1, 0.28, 0], radius: 0.105, region: "forearm-right" },
      { id: "hand-left", kind: "ellipsoid", center: [armX + 0.11, -0.01, 0], radii: [0.1, 0.23, 0.09], region: "hand-left" },
      { id: "hand-right", kind: "ellipsoid", center: [-armX - 0.11, -0.01, 0], radii: [0.1, 0.23, 0.09], region: "hand-right" },
      { id: "thigh-left", kind: "capsule", a: [hip * 0.43, 0.18, 0], b: [0.4, -1.22, 0], radius: female ? 0.24 : 0.25, region: "thigh-left" },
      { id: "thigh-right", kind: "capsule", a: [-hip * 0.43, 0.18, 0], b: [-0.4, -1.22, 0], radius: female ? 0.24 : 0.25, region: "thigh-right" },
      { id: "knee-left", kind: "ellipsoid", center: [0.4, -1.3, 0], radii: [0.19, 0.19, 0.17], region: "knee-left", joint: true },
      { id: "knee-right", kind: "ellipsoid", center: [-0.4, -1.3, 0], radii: [0.19, 0.19, 0.17], region: "knee-right", joint: true },
      { id: "shin-left", kind: "capsule", a: [0.4, -1.38, 0], b: [0.4, -2.72, 0], radius: 0.145, region: "shin-left" },
      { id: "shin-right", kind: "capsule", a: [-0.4, -1.38, 0], b: [-0.4, -2.72, 0], radius: 0.145, region: "shin-right" },
      { id: "foot-left", kind: "ellipsoid", center: [0.41, -2.96, 0.12], radii: [0.2, 0.18, 0.32], region: "foot-left" },
      { id: "foot-right", kind: "ellipsoid", center: [-0.41, -2.96, 0.12], radii: [0.2, 0.18, 0.32], region: "foot-right" },
    ];
  }

  draw() {
    if (!this.width || !this.height) return;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);
    const light = document.documentElement.dataset.theme === "light";
    const palette = light
      ? {
          edge: "rgba(35, 93, 75, 0.42)",
          shadow: "rgba(32, 79, 62, 0.16)",
          body0: "#7bb59f",
          body1: "#b9dfd0",
          body2: "#effaf5",
          line: "rgba(243, 255, 250, 0.72)",
          glow: "rgba(22, 134, 94, 0.24)",
        }
      : {
          edge: "rgba(127, 222, 186, 0.48)",
          shadow: "rgba(0, 0, 0, 0.32)",
          body0: "#0c4a3a",
          body1: "#227b62",
          body2: "#75e8bd",
          line: "rgba(177, 255, 224, 0.48)",
          glow: "rgba(54, 218, 159, 0.32)",
        };
    this.drawAura(ctx, palette, light);

    const parts = this.buildParts()
      .map((part) => {
        if (part.kind === "capsule") {
          const a = this.project(part.a);
          const b = this.project(part.b);
          return { ...part, a2: a, b2: b, depth: (a.z + b.z) / 2 };
        }
        const c = this.project(part.center);
        return { ...part, c2: c, depth: c.z };
      })
      .sort((a, b) => a.depth - b.depth);

    this.hitParts = [];
    for (const part of parts) {
      this.drawPart(ctx, part, palette, light);
      this.hitParts.push(part);
    }
    this.drawSelection(ctx, parts, palette);
  }

  drawAura(ctx, palette, light) {
    const floor = this.project([0, -3.13, 0]);
    const radius = Math.min(this.width, this.height) * 0.22 * this.zoom;
    const glow = ctx.createRadialGradient(floor.x, floor.y, 2, floor.x, floor.y, radius);
    glow.addColorStop(0, light ? "rgba(22,134,94,.16)" : "rgba(104,224,177,.18)");
    glow.addColorStop(0.52, light ? "rgba(22,134,94,.045)" : "rgba(104,224,177,.045)");
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.save();
    ctx.translate(floor.x, floor.y);
    ctx.scale(1, 0.24);
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();
    ctx.strokeStyle = light ? "rgba(22,134,94,.22)" : "rgba(104,224,177,.18)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();

    ctx.save();
    ctx.strokeStyle = light ? "rgba(22,134,94,.08)" : "rgba(104,224,177,.065)";
    ctx.setLineDash([3, 8]);
    ctx.beginPath();
    ctx.moveTo(this.width * 0.1, floor.y);
    ctx.lineTo(this.width * 0.9, floor.y);
    ctx.stroke();
    ctx.restore();
  }

  drawPart(ctx, part, palette, light) {
    const selected = this.selectedPart === part.id;
    if (part.kind === "capsule") {
      const { a2, b2 } = part;
      const width = Math.max(4, part.radius * 2 * ((a2.unit + b2.unit) / 2));
      ctx.save();
      ctx.lineCap = "round";
      ctx.shadowColor = selected ? palette.glow : palette.shadow;
      ctx.shadowBlur = selected ? 22 : 11;
      ctx.shadowOffsetY = selected ? 0 : 4;
      ctx.strokeStyle = palette.edge;
      ctx.lineWidth = width + 2.5;
      ctx.beginPath();
      ctx.moveTo(a2.x, a2.y);
      ctx.lineTo(b2.x, b2.y);
      ctx.stroke();
      const gradient = ctx.createLinearGradient(a2.x, a2.y, b2.x, b2.y);
      gradient.addColorStop(0, palette.body1);
      gradient.addColorStop(0.52, palette.body0);
      gradient.addColorStop(1, palette.body1);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = width;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.globalAlpha = light ? 0.68 : 0.48;
      ctx.strokeStyle = palette.line;
      ctx.lineWidth = Math.max(1.3, width * 0.18);
      ctx.beginPath();
      ctx.moveTo(a2.x - width * 0.13, a2.y - width * 0.08);
      ctx.lineTo(b2.x - width * 0.13, b2.y - width * 0.08);
      ctx.stroke();
      ctx.restore();
      return;
    }

    const { c2, radii } = part;
    const rx = Math.max(2, radii[0] * c2.unit);
    const ry = Math.max(2, radii[1] * c2.unit);
    ctx.save();
    ctx.shadowColor = selected ? palette.glow : palette.shadow;
    ctx.shadowBlur = selected ? 28 : 13;
    ctx.shadowOffsetY = selected ? 0 : 5;
    ctx.beginPath();
    ctx.ellipse(c2.x, c2.y, rx, ry, 0, 0, Math.PI * 2);
    const fill = ctx.createRadialGradient(
      c2.x - rx * 0.3,
      c2.y - ry * 0.34,
      Math.max(1, rx * 0.08),
      c2.x,
      c2.y,
      Math.max(rx, ry) * 1.16,
    );
    fill.addColorStop(0, palette.body2);
    fill.addColorStop(0.22, palette.body1);
    fill.addColorStop(0.72, palette.body0);
    fill.addColorStop(1, light ? "#57927d" : "#062f25");
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = selected ? (light ? "rgba(22,134,94,.92)" : "rgba(143,255,208,.82)") : palette.edge;
    ctx.lineWidth = selected ? 2.2 : 1.25;
    ctx.stroke();
    if (selected) {
      ctx.globalAlpha = 0.58;
      ctx.beginPath();
      ctx.ellipse(c2.x, c2.y, rx + 7, ry + 7, 0, 0, Math.PI * 2);
      ctx.strokeStyle = palette.glow;
      ctx.lineWidth = 5;
      ctx.stroke();
    }
    ctx.restore();
  }

  drawSelection(ctx, parts, palette) {
    if (!this.selectedPart) return;
    const selected = parts.find((part) => part.id === this.selectedPart);
    if (!selected) return;
    const point = selected.kind === "capsule"
      ? {
          x: (selected.a2.x + selected.b2.x) / 2,
          y: (selected.a2.y + selected.b2.y) / 2,
        }
      : selected.c2;
    ctx.save();
    ctx.beginPath();
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = document.documentElement.dataset.theme === "light" ? "#16865e" : "#8fffd0";
    ctx.fill();
    ctx.restore();
  }

  pick(event) {
    const rect = this.canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    for (let index = this.hitParts.length - 1; index >= 0; index -= 1) {
      const part = this.hitParts[index];
      if (part.kind === "capsule") {
        const radius = Math.max(6, part.radius * ((part.a2.unit + part.b2.unit) / 2) * 1.2);
        if (this.distanceToSegment(x, y, part.a2, part.b2) <= radius) {
          this.selectPart(part);
          return;
        }
      } else {
        const rx = Math.max(5, part.radii[0] * part.c2.unit * 1.16);
        const ry = Math.max(5, part.radii[1] * part.c2.unit * 1.16);
        const dx = (x - part.c2.x) / rx;
        const dy = (y - part.c2.y) / ry;
        if (dx * dx + dy * dy <= 1) {
          this.selectPart(part);
          return;
        }
      }
    }
  }

  distanceToSegment(x, y, a, b) {
    const vx = b.x - a.x;
    const vy = b.y - a.y;
    const lengthSquared = vx * vx + vy * vy;
    const t = lengthSquared
      ? clamp(((x - a.x) * vx + (y - a.y) * vy) / lengthSquared, 0, 1)
      : 0;
    return Math.hypot(x - (a.x + t * vx), y - (a.y + t * vy));
  }

  selectPart(part) {
    const region = resolveRegion(part.region || part.id, this.yaw);
    if (!region) return;
    this.selectedPart = part.id;
    this.schedule();
    this.onSelect?.(region, { gender: this.gender, selectedPart: part.id });
  }
}

function explanationMarkup(region) {
  return `
    <div class="body-map-result-head">
      <span><i></i> 已识别部位</span>
      <strong>${escapeHtml(region.label)}</strong>
      <p>${escapeHtml(region.anatomy)}</p>
    </div>
    <div class="body-map-result-group">
      <span class="body-map-kicker">常见相关感受</span>
      <div class="body-map-symptom-list">
        ${region.symptoms.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
    </div>
    <div class="body-map-result-group">
      <span class="body-map-kicker">补充这些信息有助于判断</span>
      <ol class="body-map-question-list">
        ${region.questions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ol>
    </div>
    <div class="body-map-warning">
      <span>${icon("alert")} 需要警惕</span>
      <p>${escapeHtml(region.warning)}</p>
    </div>
    <button class="primary-button body-map-use" id="body-map-use" type="button">
      ${icon("message")} 带入健康咨询
    </button>
  `;
}

const ANATOMY_GUIDES = {
  trachea: "气管是连接喉部与左右主支气管的主要气道，由软骨环支撑，负责将空气送入肺部。",
  气管: "气管是连接喉部与左右主支气管的主要气道，由软骨环支撑，负责将空气送入肺部。",
  bronchus: "支气管是气管分支后的气道，逐级通向肺叶和肺段，承担空气传导与分泌物清除。",
  bronchi: "支气管是气管分支后的气道，逐级通向肺叶和肺段，承担空气传导与分泌物清除。",
  支气管: "支气管是气管分支后的气道，逐级通向肺叶和肺段，承担空气传导与分泌物清除。",
  lung: "肺是气体交换器官，空气沿支气管到达肺泡，在那里完成氧气和二氧化碳交换。",
  肺: "肺是气体交换器官，空气沿支气管到达肺泡，在那里完成氧气和二氧化碳交换。",
  heart: "心脏是位于胸腔中央偏左的肌性泵，通过四个心腔和瓣膜维持肺循环与体循环。",
  心脏: "心脏是位于胸腔中央偏左的肌性泵，通过四个心腔和瓣膜维持肺循环与体循环。",
  liver: "肝脏位于右上腹，负责营养代谢、胆汁生成、蛋白合成和多种物质解毒，并可进一步划分为多个肝段。",
  肝: "肝脏位于右上腹，负责营养代谢、胆汁生成、蛋白合成和多种物质解毒，并可进一步划分为多个肝段。",
  stomach: "胃位于左上腹，连接食管和十二指肠，负责储存、搅拌食物并初步消化。",
  胃: "胃位于左上腹，连接食管和十二指肠，负责储存、搅拌食物并初步消化。",
  gallbladder: "胆囊位于肝脏下方，储存并浓缩胆汁，进食后通过胆道将胆汁送入十二指肠。",
  胆囊: "胆囊位于肝脏下方，储存并浓缩胆汁，进食后通过胆道将胆汁送入十二指肠。",
  pancreas: "胰腺横卧于上腹部，兼具消化酶分泌和胰岛素、胰高血糖素等激素分泌功能。",
  胰腺: "胰腺横卧于上腹部，兼具消化酶分泌和胰岛素、胰高血糖素等激素分泌功能。",
  spleen: "脾位于左上腹，参与血液过滤、衰老血细胞清除和免疫反应。",
  脾: "脾位于左上腹，参与血液过滤、衰老血细胞清除和免疫反应。",
  kidney: "肾脏位于腹膜后、脊柱两侧，负责过滤血液并调节水、电解质和酸碱平衡。",
  肾: "肾脏位于腹膜后、脊柱两侧，负责过滤血液并调节水、电解质和酸碱平衡。",
  bladder: "膀胱位于骨盆内，是储存尿液并通过尿道排出体外的肌性器官。",
  膀胱: "膀胱位于骨盆内，是储存尿液并通过尿道排出体外的肌性器官。",
  intestine: "肠道分为小肠和大肠，负责营养吸收、水分回收和粪便形成。",
  肠: "肠道分为小肠和大肠，负责营养吸收、水分回收和粪便形成。",
  colon: "结肠是大肠的主要部分，吸收水分和电解质并推动粪便向直肠移动。",
  结肠: "结肠是大肠的主要部分，吸收水分和电解质并推动粪便向直肠移动。",
  uterus: "子宫位于女性骨盆中央，是孕育胎儿的肌性器官。",
  子宫: "子宫位于女性骨盆中央，是孕育胎儿的肌性器官。",
  ovary: "卵巢是女性成对性腺，承担卵细胞产生及雌激素、孕激素分泌。",
  卵巢: "卵巢是女性成对性腺，承担卵细胞产生及雌激素、孕激素分泌。",
  prostate: "前列腺位于男性膀胱下方，环绕尿道起始部，分泌前列腺液。",
  前列腺: "前列腺位于男性膀胱下方，环绕尿道起始部，分泌前列腺液。",
};

function anatomyGuide(names) {
  const normalized = names.map((name) => String(name).toLowerCase());
  if (names.length <= 3) {
    for (const [key, description] of Object.entries(ANATOMY_GUIDES)) {
      const needle = key.toLowerCase();
      if (normalized.some((name) => name === needle || name.includes(needle))) {
        return description;
      }
    }
  }
  if (names.some((name) => /[咽喉会厌声带气管舌腭扁桃]/u.test(name))) {
    return "这里展开的是口腔、咽部和喉部的细分结构，包括舌、软腭、扁桃体、咽肌、喉软骨、会厌、声带和相关气道。继续点击具体结构可以进一步缩小位置。";
  }
  if (names.length > 5) {
    return "该区域包含多个解剖结构，系统已保留细分名称。请补充疼痛性质、持续时间和伴随症状，以便进一步判断风险。";
  }
  for (const [key, description] of Object.entries(ANATOMY_GUIDES)) {
    const needle = key.toLowerCase();
    if (normalized.some((name) => name.includes(needle))) return description;
  }
  return "该区域由多个三维解剖结构组成。可以继续点击或缩小框选范围，以获得更精确的位置描述。";
}

function anatomySelectionMarkup(result) {
  const parts = result.parts.slice(0, 80);
  const extra = Math.max(0, result.parts.length - parts.length);
  const systems = result.systems.filter(Boolean);
  return `
    <div class="anatomy-result-head">
      <span>${icon("scan")} 已识别 ${result.parts.length} 个结构</span>
      <strong>${escapeHtml(result.label)}</strong>
      <p>${escapeHtml(systems.join(" · "))}</p>
    </div>
    <div class="anatomy-result-guide">
      <span>结构说明</span>
      <p>${escapeHtml(anatomyGuide(result.names))}</p>
    </div>
    <div class="anatomy-result-list">
      <span>框选范围中的细分结构</span>
      <div>
        ${parts.map((part) => `
          <button type="button" data-anatomy-part-id="${escapeHtml(part.id)}">
            ${escapeHtml(part.displayName || part.name)}
          </button>`).join("")}
        ${extra ? `<span>另有 ${extra} 个结构，可继续框选缩小范围</span>` : ""}
      </div>
    </div>
    ${result.isolated ? `<button class="ghost-button anatomy-context-button" id="body-map-context" type="button">显示周边结构</button>` : ""}
    <button class="primary-button body-map-use" id="body-map-use" type="button">
      ${icon("message")} 带入健康咨询
    </button>
  `;
}

export function openBodyMap(onChoose) {
  const root = $("#modal-root");
  if (!root) return;
  root.innerHTML = `
    <button class="modal-backdrop" data-close-modal aria-label="关闭解剖定位"></button>
    <section class="body-map-modal anatomy-atlas-modal" role="dialog" aria-modal="true" aria-labelledby="body-map-title">
      <header class="body-map-head">
        <div>
          <span class="eyebrow"><span></span> 三维解剖定位</span>
          <h2 class="modal-title" id="body-map-title">三维解剖定位</h2>
          <p class="modal-subtitle">点击表面、深入透视或框选任意区域，系统会识别内部结构并带入健康咨询。</p>
        </div>
        <button class="icon-button" data-close-modal type="button" aria-label="关闭">${icon("close")}</button>
      </header>
      <div class="body-map-layout">
        <div class="body-map-stage">
          <div class="body-map-toolbar">
            <div class="body-map-segment" role="group" aria-label="选择人体参考模型">
              <button type="button" data-body-gender="male">男性</button>
              <button type="button" data-body-gender="female">女性</button>
            </div>
            <div class="body-map-segment body-map-mode" role="group" aria-label="选择交互模式">
              <button type="button" data-body-mode="orbit">旋转</button>
              <button type="button" data-body-mode="box">框选</button>
            </div>
            <button class="body-map-theme" id="body-map-theme" type="button">
              ${icon(document.documentElement.dataset.theme === "dark" ? "sun" : "moon")} 明暗
            </button>
          </div>
          <div class="body-map-canvas-wrap">
            <canvas id="body-map-canvas" aria-label="真实男女分层三维解剖模型。从人体部位开始拖动可自由移动模型，从空白处开始拖动可旋转模型，滚轮或下方拉杆缩放。"></canvas>
            <div class="body-map-selection-box" id="body-map-selection-box" hidden></div>
            <div class="body-map-hover-tip" id="body-map-hover-tip" hidden></div>
            <span class="body-map-orientation">按住人体部位拖动可移动模型 · 按住空白处拖动可 360° 旋转 · 滚轮缩放</span>
            <div class="body-map-loading" id="body-map-loading">
              <div class="body-map-loading-orbit"><i></i><i></i><span></span></div>
              <strong id="body-map-loading-title">正在构建解剖场</strong>
              <p id="body-map-loading-copy">载入男女人体分层数据</p>
              <div class="body-map-progress"><i id="body-map-progress-bar"></i></div>
              <span id="body-map-progress-value">0%</span>
              <button class="body-map-retry" id="body-map-retry" type="button" hidden>
                ${icon("refresh")} 重新载入
              </button>
            </div>
            <div class="body-map-zoom-control">
              <input id="body-map-zoom" type="range" min="35" max="500" value="100" aria-label="模型放大比例" />
              <span id="body-map-zoom-value">100%</span>
            </div>
          </div>
          <div class="body-map-stage-foot">
            <div class="body-map-view-switch" role="group" aria-label="视角">
              <button type="button" data-body-view="front">正面</button>
              <button type="button" data-body-view="side">侧面</button>
              <button type="button" data-body-view="back">背面</button>
            </div>
            <button type="button" id="body-map-reset">${icon("refresh")} 重置</button>
          </div>
        </div>
        <aside class="body-map-explainer anatomy-explainer" aria-live="polite">
          <div class="anatomy-search-box">
            <span>${icon("search")}</span>
            <input id="body-map-search" type="search" autocomplete="off" placeholder="搜索气管、肝段、子宫、胃…" />
            <div class="anatomy-search-results" id="body-map-search-results" hidden></div>
          </div>
          <button class="anatomy-throat-button" id="body-map-throat" type="button">
            <span>${icon("scan")}</span>
            <span><strong>展开口腔与咽喉深部</strong><small>逐层查看舌、腭、扁桃体、咽、喉、会厌、声带和气管</small></span>
            ${icon("arrowRight")}
          </button>
          <div class="anatomy-depth-control">
            <div><span>体表粒子</span><output id="body-map-depth-value">100%</output></div>
            <input id="body-map-depth" type="range" min="0" max="100" value="0" aria-label="体表粒子强度" />
            <p>最左侧为柔和初始效果，向右减弱到无粒子；内部器官仍可点击。</p>
          </div>
          <details class="anatomy-layer-panel" open>
            <summary><span>解剖系统</span><small id="body-map-layer-summary">载入中</small></summary>
            <div class="anatomy-layer-list" id="body-map-layers"></div>
          </details>
          <div class="anatomy-pregnancy-note" id="body-map-pregnancy-note" hidden>
            孕期结构参考展示的是胎盘、羊膜、脐带和脐血管等通用三维结构，仅用于解剖定位，不代表真实孕周、胎儿大小或妊娠状态。开启时会同时显示子宫和卵巢作为位置参照。
          </div>
          <div class="body-map-empty anatomy-empty" id="body-map-empty">
            <div class="body-map-empty-figure">${icon("scan")}</div>
            <strong>用户可以自由框选</strong>
            <p>切换“框选”，在人体的任意位置拖出矩形。透视图层可深入气管、胃肠、肝肾等内部结构。</p>
            <small>左右以使用者身体方向为准。模型为解剖学习与定位参考，不提供确定诊断。</small>
          </div>
          <div id="body-map-result" hidden></div>
        </aside>
      </div>
      <footer class="body-map-disclaimer">
        <span>${icon("shield")}</span>
        <p>男女参考模型分库载入，生殖结构按所选性别显示。出现胸痛、呼吸困难、意识改变或严重外伤时，请立即拨打 120。</p>
        <a href="https://humanatlas.io/3d-reference-library" target="_blank" rel="noopener noreferrer">解剖数据来源 · 知识共享署名 4.0 许可</a>
      </footer>
    </section>`;

  hydrateIcons(root);
  let selectedResult = null;
  let model = null;
  const cleanup = () => model?.destroy();
  $$("[data-close-modal]", root).forEach((button) => button.addEventListener("click", cleanup));
  bindModalClose();

  const canvas = $("#body-map-canvas");
  const result = $("#body-map-result");
  const empty = $("#body-map-empty");
  const layers = $("#body-map-layers");
  const search = $("#body-map-search");
  const searchResults = $("#body-map-search-results");
  const loading = $("#body-map-loading");
  let currentSystems = [];
  let searchTimer = null;

  const renderLayers = (systems, visibleSystems) => {
    currentSystems = systems;
    layers.innerHTML = systems.map((system) => `
      <button type="button" data-atlas-system="${escapeHtml(system.id)}" class="${visibleSystems.includes(system.id) ? "active" : ""}">
        <i style="--system-color:${escapeHtml(system.color)}"></i>
        <span>${escapeHtml(system.label)}</span>
        <small>${system.count}</small>
      </button>
    `).join("");
    $("#body-map-layer-summary").textContent = `${visibleSystems.length} / ${systems.length}`;
    $$("[data-atlas-system]", layers).forEach((button) => {
      button.addEventListener("click", () => {
        const active = !button.classList.contains("active");
        button.classList.toggle("active", active);
        model.setSystemVisible(button.dataset.atlasSystem, active);
        if (button.dataset.atlasSystem === "pregnancy" && active) {
          const reproductiveButton = $(
            '[data-atlas-system="reproductive"]',
            layers,
          );
          if (reproductiveButton && !reproductiveButton.classList.contains("active")) {
            reproductiveButton.classList.add("active");
            model.setSystemVisible("reproductive", true);
          }
        }
        $("#body-map-pregnancy-note").hidden = !$$(
          '[data-atlas-system="pregnancy"].active',
          layers,
        ).length;
        $("#body-map-layer-summary").textContent =
          `${$$("[data-atlas-system].active", layers).length} / ${currentSystems.length}`;
      });
    });
  };

  model = new AnatomyAtlasViewer(canvas, {
    onLoading: (value, label) => {
      loading.hidden = value >= 100;
      $("#body-map-retry").hidden = true;
      $("#body-map-progress-bar").style.width = `${Math.min(100, value)}%`;
      $("#body-map-progress-value").textContent = `${Math.min(100, value)}%`;
      if (label) $("#body-map-loading-copy").textContent = label;
    },
    onReady: ({ systems, visibleSystems, partCount }) => {
      renderLayers(systems, visibleSystems);
      $("#body-map-loading-title").textContent = `${partCount.toLocaleString("zh-CN")} 个三维结构`;
      empty.hidden = false;
      result.hidden = true;
    },
    onZoom: (value) => {
      const zoom = $("#body-map-zoom");
      const label = $("#body-map-zoom-value");
      if (zoom) zoom.value = String(Math.round(value * 100));
      if (label) label.textContent = `${Math.round(value * 100)}%`;
    },
    onSelect: (selection) => {
      selectedResult = selection;
      empty.hidden = true;
      result.hidden = false;
      result.innerHTML = anatomySelectionMarkup(selection);
      hydrateIcons(result);
      $("#body-map-use").addEventListener("click", () => {
        const names = selection.names.slice(0, 16).join("、");
        const prompt = `我通过人体三维定位选择了：${names}。请解释这些结构可能涉及哪些器官或组织、常见相关症状，以及我还需要补充哪些信息来判断风险。`;
        onChoose?.({
          label: selection.label,
          prompt,
          modelGender: selection.sex,
          names: selection.names,
        });
        cleanup();
        closeModal();
      });
      $("#body-map-context")?.addEventListener("click", (event) => {
        model.showContext();
        event.currentTarget.hidden = true;
      });
      $$("[data-anatomy-part-id]", result).forEach((button) => {
        button.addEventListener("click", () => {
          const part = model.parts.find((item) => item.id === button.dataset.anatomyPartId);
          if (part) {
            model.selectParts(
              [part.id],
              model.displayName(part.name),
              { isolate: true },
            );
          }
        });
      });
      if (window.innerWidth < 820) {
        result.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    },
    onHover: (part) => {
      const tip = $("#body-map-hover-tip");
      if (!tip) return;
      if (!part) {
        tip.hidden = true;
        return;
      }
      tip.textContent = `${part.displayName} · ${part.systemLabel}`;
      tip.hidden = false;
    },
    onSelectionEmpty: () => {
      empty.hidden = false;
      result.hidden = true;
    },
    onError: (message) => {
      loading.hidden = false;
      $("#body-map-loading-title").textContent = "解剖数据载入失败";
      $("#body-map-loading-copy").textContent = message;
      $("#body-map-progress-value").textContent = "错误";
      $("#body-map-retry").hidden = false;
    },
  });

  const setGender = (gender) => {
    model.setSex(gender);
    selectedResult = null;
    empty.hidden = false;
    result.hidden = true;
    $$("[data-body-gender]", root).forEach((button) => {
      const active = button.dataset.bodyGender === gender;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  };
  setGender("male");
  $$("[data-body-gender]", root).forEach((button) => {
    button.addEventListener("click", () => setGender(button.dataset.bodyGender));
  });

  $$("[data-body-mode]", root).forEach((button) => {
    button.classList.toggle("active", button.dataset.bodyMode === "orbit");
    button.addEventListener("click", () => {
      $$("[data-body-mode]", root).forEach((item) => item.classList.toggle("active", item === button));
      model.setSelectionMode(button.dataset.bodyMode);
    });
  });
  $$("[data-body-view]", root).forEach((button) => {
    button.classList.toggle("active", button.dataset.bodyView === "front");
    button.addEventListener("click", () => {
      $$("[data-body-view]", root).forEach((item) => item.classList.toggle("active", item === button));
      model.setView(button.dataset.bodyView);
    });
  });

  search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      const query = search.value.trim();
      if (!query) {
        searchResults.hidden = true;
        searchResults.innerHTML = "";
        return;
      }
      const matches = model.search(query).slice(0, 12);
      searchResults.innerHTML = matches.length
        ? matches.map((concept, index) => `
            <button type="button" data-anatomy-result-index="${index}">
              <span>${escapeHtml(concept.displayName)}</span>
              <small>${escapeHtml(SYSTEM_META[model.parts.find((part) => part.id === concept.elements[0])?.system]?.label || "")}</small>
            </button>`).join("")
        : `<p>没有匹配的结构，请尝试更具体的名称。</p>`;
      searchResults.hidden = false;
      $$("[data-anatomy-result-index]", searchResults).forEach((button) => {
        button.addEventListener("click", () => {
          const concept = matches[Number(button.dataset.anatomyResultIndex)];
          searchResults.hidden = true;
          search.value = concept.displayName;
          model.selectConcept(concept, { isolate: true });
        });
      });
    }, 130);
  });

  $("#body-map-depth").addEventListener("input", (event) => {
    const value = Number(event.target.value);
    $("#body-map-depth-value").textContent =
      value >= 100 ? "无粒子" : `${100 - value}%`;
    model.setDepth(value / 100);
  });
  $("#body-map-throat").addEventListener("click", () => {
    $("#body-map-depth").value = "72";
    $("#body-map-depth-value").textContent = "28%";
    $$("[data-body-view]", root).forEach((item) =>
      item.classList.toggle("active", item.dataset.bodyView === "front"),
    );
    model.expandThroat();
  });
  $("#body-map-theme").addEventListener("click", () => {
    toggleTheme();
    const light = document.documentElement.dataset.theme === "light";
    $("#body-map-theme").innerHTML = `${icon(light ? "moon" : "sun")} 明暗`;
    model.refreshTheme();
  });
  $("#body-map-retry").addEventListener("click", () => {
    $("#body-map-progress-bar").style.width = "0%";
    $("#body-map-progress-value").textContent = "0%";
    $("#body-map-loading-title").textContent = "正在重新载入解剖数据";
    model.setSex(model.sex);
  });
  $("#body-map-zoom").addEventListener("input", (event) => {
    const value = model.setZoom(Number(event.target.value) / 100);
    $("#body-map-zoom-value").textContent = `${Math.round(value * 100)}%`;
  });
  $("#body-map-reset").addEventListener("click", () => {
    model.resetView();
    $("#body-map-zoom").value = "100";
    $("#body-map-zoom-value").textContent = "100%";
    $("#body-map-depth").value = "0";
    $("#body-map-depth-value").textContent = "100%";
    model.setDepth(0);
  });
}
