/* =========================
   DOM
========================= */
const fileMenuBtn = document.getElementById("fileMenuBtn");
const fileDropdown = document.getElementById("fileDropdown");
const importImagesBtn = document.getElementById("importImages");
const importIntrinsicsBtn = document.getElementById("importIntrinsics");
const importExtrinsicsBtn = document.getElementById("importExtrinsics");
const openCameraModalBtn = document.getElementById("openCameraModal");
const exportJsonBtn = document.getElementById("exportJson");
const exportCsvBtn = document.getElementById("exportCsv");

const imageInput = document.getElementById("imageInput");
const intrinsicsInput = document.getElementById("intrinsicsInput");
const extrinsicsInput = document.getElementById("extrinsicsInput");

const gridView = document.getElementById("gridView");
const singleView = document.getElementById("singleView");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

const toolPoint = document.getElementById("toolPoint");
const toolFit = document.getElementById("toolFit");
const toolCompute3D = document.getElementById("toolCompute3D");
const toolDistance = document.getElementById("toolDistance");

const pointList = document.getElementById("pointList");
const currentPoint = document.getElementById("currentPoint");
const statusText = document.getElementById("statusText");
const computePreview = document.getElementById("computePreview");

// 手动内外参 modal（数值输入）
const cameraModal = document.getElementById("cameraModal");
const cameraSaveBtn = document.getElementById("cameraSaveBtn");
const cameraResetBtn = document.getElementById("cameraResetBtn");
const cameraCancelBtn = document.getElementById("cameraCancelBtn");

// 内参输入
const fxInput = document.getElementById("fxInput");
const fyInput = document.getElementById("fyInput");
const cxInput = document.getElementById("cxInput");
const cyInput = document.getElementById("cyInput");
const k1Input = document.getElementById("k1Input");
const k2Input = document.getElementById("k2Input");
const p1Input = document.getElementById("p1Input");
const p2Input = document.getElementById("p2Input");
const k3Input = document.getElementById("k3Input");

// 外参输入
const yawOffInput = document.getElementById("yawOffInput");
const pitchOffInput = document.getElementById("pitchOffInput");
const rollOffInput = document.getElementById("rollOffInput");
const dXInput = document.getElementById("dXInput");
const dYInput = document.getElementById("dYInput");
const dZInput = document.getElementById("dZInput");

/* =========================
   导出连线图功能
========================= */
const exportLineImageBtn = document.getElementById("exportLineImage");
const exportLineModal = document.getElementById("exportLineModal");
const exportLineClose = document.getElementById("exportLineClose");
const exportLineCancel = document.getElementById("exportLineCancel");
const exportLineSave = document.getElementById("exportLineSave");
const exportLinePreview = document.getElementById("exportLinePreview");
const exportFormat = document.getElementById("exportFormat");
const exportQuality = document.getElementById("exportQuality");
const exportSize = document.getElementById("exportSize");
const customSizeContainer = document.getElementById("customSizeContainer");
const customWidth = document.getElementById("customWidth");

// 初始化导出连线图按钮
if (exportLineImageBtn) {
  exportLineImageBtn.addEventListener("click", () => {
    showMenu(false);
    exportLineImage();
  });
}

// 关闭模态框
if (exportLineClose) {
  exportLineClose.addEventListener("click", () => {
    exportLineModal.classList.add("hidden");
  });
}

if (exportLineCancel) {
  exportLineCancel.addEventListener("click", () => {
    exportLineModal.classList.add("hidden");
  });
}

// 图片尺寸选择变化
if (exportSize) {
  exportSize.addEventListener("change", () => {
    customSizeContainer.style.display = exportSize.value === "custom" ? "block" : "none";
    if (exportLineModal && !exportLineModal.classList.contains("hidden")) {
      updateExportPreview();
    }
  });
}

// 导出选项变化时更新预览
[exportFormat, exportQuality, exportSize, customWidth].forEach(element => {
  if (element) {
    element.addEventListener("change", () => {
      if (exportLineModal && !exportLineModal.classList.contains("hidden")) {
        updateExportPreview();
      }
    });
  }
});

// 导出连线图功能
function exportLineImage() {
  // 检查是否有当前图像
  if (!currentImage || !imgObj) {
    setStatus("请先加载图片");
    return;
  }
  
  // 检查是否在距离标识模式下且有连线
  if (!modeDistance || distanceLines.length === 0) {
    setStatus("请在距离标识模式下绘制连线后再导出");
    return;
  }
  
  // 显示模态框
  exportLineModal.classList.remove("hidden");
  
  // 创建预览
  updateExportPreview();
}

// 更新导出预览
// 修改 updateExportPreview 函数中的绘制部分
function updateExportPreview() {
  if (!exportLinePreview || !currentImage || !imgObj) return;
  
  // 清空预览区域
  exportLinePreview.innerHTML = "";
  
  // 计算导出尺寸
  const baseWidth = imgObj.width;
  const baseHeight = imgObj.height;
  let exportWidth, exportHeight;
  
  const sizeOption = exportSize ? exportSize.value : "3x";
  if (sizeOption === "original") {
    exportWidth = baseWidth;
    exportHeight = baseHeight;
  } else if (sizeOption === "2x") {
    exportWidth = baseWidth * 2;
    exportHeight = baseHeight * 2;
  } else if (sizeOption === "3x") {
    exportWidth = baseWidth * 3;
    exportHeight = baseHeight * 3;
  } else if (sizeOption === "custom") {
    const customW = customWidth ? parseInt(customWidth.value) : 1920;
    const scale = customW / baseWidth;
    exportWidth = customW;
    exportHeight = Math.round(baseHeight * scale);
  } else {
    exportWidth = baseWidth * 3;
    exportHeight = baseHeight * 3;
  }
  
  // 确保尺寸在合理范围内
  exportWidth = Math.min(Math.max(100, exportWidth), 10000);
  exportHeight = Math.min(Math.max(100, exportHeight), 10000);
  
  // 创建临时画布
  const previewCanvas = document.createElement("canvas");
  previewCanvas.width = exportWidth;
  previewCanvas.height = exportHeight;
  const previewCtx = previewCanvas.getContext("2d");
  
  // 计算缩放比例
  const scale = exportWidth / baseWidth;
  
  // 绘制原始图像
  previewCtx.drawImage(imgObj, 0, 0, exportWidth, exportHeight);
  
  // 获取当前图片的所有点
  const pts = getPoints(currentImage.id);
  
  // 绘制连线（在绘制点之前，这样连线在点的下面）
  if (modeDistance && distanceLines.length > 0) {
    // 设置连线样式 - 增加线宽
    previewCtx.lineWidth = Math.max(4, 6 * scale); // 增加线宽
    previewCtx.lineCap = "round";
    previewCtx.lineJoin = "round";
    
    distanceLines.forEach(line => {
      const pa = findPointById(currentImage.id, line.a);
      const pb = findPointById(currentImage.id, line.b);
      
      if (pa && pb) {
        const ax = pa.x * scale;
        const ay = pa.y * scale;
        const bx = pb.x * scale;
        const by = pb.y * scale;
        
        // 绘制连线
        previewCtx.beginPath();
        previewCtx.moveTo(ax, ay);
        previewCtx.lineTo(bx, by);
        previewCtx.strokeStyle = "rgba(0, 255, 255, 0.95)"; // 增加透明度
        previewCtx.stroke();
        
        // 绘制距离标签
        if (line.distance != null) {
          const mx = (ax + bx) / 2;
          const my = (ay + by) / 2;
          const text = `距离: ${line.distance.toFixed(6)}`; // 直接显示"距离: 数值"
          
          // 计算文本尺寸 - 增加字体大小
          const fontSize = Math.max(16, 20 * scale); // 增加字体大小
          previewCtx.font = `bold ${fontSize}px Arial, sans-serif`;
          const textWidth = previewCtx.measureText(text).width;
          const textHeight = fontSize;
          
          // 绘制标签背景
          previewCtx.fillStyle = "rgba(0, 0, 0, 0.85)"; // 增加背景透明度
          previewCtx.fillRect(
            mx - textWidth / 2 - 15 * scale, // 增加内边距
            my - textHeight / 2 - 8 * scale,
            textWidth + 30 * scale,
            textHeight + 16 * scale
          );
          
          // 绘制文本
          previewCtx.fillStyle = "#ffffff";
          previewCtx.fillText(text, mx - textWidth / 2, my + textHeight / 2 - 4 * scale);
          
          // 移除单位距离标签
        }
      }
    });
  }
  
  // 绘制标注点 - 增加点的大小
  previewCtx.font = `bold ${Math.max(18, 22 * scale)}px Arial, sans-serif`; // 增加标签字体大小
  previewCtx.textBaseline = "middle";
  previewCtx.textAlign = "left";
  
  pts.forEach(p => {
    const sx = p.x * scale;
    const sy = p.y * scale;
    
    // 判断点的状态
    const isInLineA = distanceLines.some(line => line.a === p.keypoint_id);
    const isInLineB = distanceLines.some(line => line.b === p.keypoint_id);
    const isInLine = isInLineA || isInLineB;
    
    // 点半径 - 增加半径
    const radius = isInLine ? Math.max(12, 15 * scale) : Math.max(10, 12 * scale);
    
    // 绘制点外圈 - 增加外圈大小
    previewCtx.beginPath();
    previewCtx.arc(sx, sy, radius + Math.max(2, 3 * scale), 0, Math.PI * 2);
    previewCtx.fillStyle = "rgba(255, 255, 255, 0.9)"; // 增加外圈可见度
    previewCtx.fill();
    
    // 绘制点
    previewCtx.beginPath();
    previewCtx.arc(sx, sy, radius, 0, Math.PI * 2);
    
    if (isInLineA) {
      previewCtx.fillStyle = "#FFD700"; // 更亮的黄色
    } else if (isInLineB) {
      previewCtx.fillStyle = "#00FFFF"; // 更亮的青色
    } else if (isInLine) {
      previewCtx.fillStyle = "#FF6600";
    } else {
      previewCtx.fillStyle = "#FF0000"; // 更亮的红色
    }
    
    previewCtx.fill();
    
    // 为点添加白色边框，增加可见度
    previewCtx.beginPath();
    previewCtx.arc(sx, sy, radius, 0, Math.PI * 2);
    previewCtx.lineWidth = Math.max(2, 3 * scale);
    previewCtx.strokeStyle = "#FFFFFF";
    previewCtx.stroke();
    
    // 绘制点ID标签
    const label = `点${p.keypoint_id}`; // 改为中文标签
    const tx = sx + radius + 8 * scale; // 增加标签偏移
    const ty = sy;
    
    const textWidth = previewCtx.measureText(label).width;
    const textHeight = Math.max(18, 22 * scale); // 增加标签高度
    const padX = 12 * scale; // 增加内边距
    const padY = 6 * scale;
    
    // 标签背景
    previewCtx.fillStyle = "rgba(0, 0, 0, 0.85)";
    previewCtx.fillRect(
      tx - padX,
      ty - textHeight / 2 - padY,
      textWidth + padX * 2,
      textHeight + padY * 2
    );
    
    // 标签文本
    previewCtx.fillStyle = "#ffffff";
    previewCtx.fillText(label, tx, ty);
  });
  
  // 添加图片标题和元信息
  const titleText = `${currentImage.name || currentImage.id} - 距离标识连线图`;
  previewCtx.font = `bold ${Math.max(24, 28 * scale)}px Arial, sans-serif`; // 增加标题字体大小
  previewCtx.textAlign = "left";
  previewCtx.textBaseline = "top";
  
  const titleWidth = previewCtx.measureText(titleText).width;
  const titleHeight = Math.max(24, 28 * scale);
  
  // 标题背景
  previewCtx.fillStyle = "rgba(0, 0, 0, 0.9)";
  previewCtx.fillRect(30 * scale, 30 * scale, titleWidth + 60 * scale, titleHeight + 30 * scale);
  
  // 标题文本
  previewCtx.fillStyle = "#ffffff";
  previewCtx.fillText(titleText, 50 * scale, 40 * scale);
  
  // 添加距离信息
  if (distanceResults.length > 0) {
    const infoText = `共 ${distanceLines.length} 组连线，${distanceResults.length} 个距离计算结果`;
    previewCtx.font = `${Math.max(16, 18 * scale)}px Arial, sans-serif`; // 增加信息字体大小
    previewCtx.fillStyle = "rgba(255, 255, 255, 0.95)";
    previewCtx.fillText(infoText, 50 * scale, 80 * scale);
  }
  
  // 添加时间戳
  const timestamp = new Date().toLocaleString('zh-CN');
  previewCtx.font = `${Math.max(12, 14 * scale)}px Arial, sans-serif`;
  previewCtx.fillStyle = "rgba(255, 255, 255, 0.8)";
  previewCtx.fillText(`导出时间: ${timestamp}`, 50 * scale, exportHeight - 40 * scale);
  
  // 将预览画布添加到预览区域
  previewCanvas.style.maxWidth = "100%";
  previewCanvas.style.maxHeight = "100%";
  exportLinePreview.appendChild(previewCanvas);
}
// 保存图片
if (exportLineSave) {
  exportLineSave.addEventListener("click", () => {
    if (!exportLinePreview.firstChild || !currentImage) return;
    
    const previewCanvas = exportLinePreview.querySelector("canvas");
    if (!previewCanvas) return;
    
    // 获取导出选项
    const format = exportFormat ? exportFormat.value : "png";
    const quality = exportQuality ? parseFloat(exportQuality.value) : 0.8;
    const fileName = `连线图_${currentImage.name || currentImage.id}_${new Date().toISOString().slice(0, 10)}`;
    
    // 创建下载链接
    const link = document.createElement("a");
    link.download = `${fileName}.${format}`;
    
    if (format === "jpeg") {
      link.href = previewCanvas.toDataURL("image/jpeg", quality);
    } else {
      link.href = previewCanvas.toDataURL("image/png");
    }
    
    link.click();
    
    // 关闭模态框
    exportLineModal.classList.add("hidden");
    setStatus(`连线图已保存: ${fileName}.${format}`);
  });
}

/* =========================
   状态
========================= */
let images = [];                // [{id,name,url}]
let currentImage = null;        // {id,name,url}
let imgObj = null;

let modePoint = false;          // 标注模式
let modeDistance = false;       // 距离标识模式
let zoom = 1;

let pointsMap = {};             // image_id -> [{keypoint_id:int, x:number, y:number}]
let selectedId = null;
let draggingId = null;
let dragOffset = { dx: 0, dy: 0 };
let hoverId = null;

let saveTimer = null;

// 3D结果缓存：keypoint_id -> [X,Y,Z]
let kp3dMap = new Map();
// 最近一次 compute 的 rows（用于挑图）
let lastComputeRows = [];
let distanceLines = [];  // 存储多组距离标识点对
let distanceResults = [];  // 用来保存所有计算的距离结果

function saveDistanceResult(pointA, pointB, distance) {
  distanceResults.push({
    pointA_keypoint_id: pointA.keypoint_id,
    pointA_x: pointA.x.toFixed(2),
    pointA_y: pointA.y.toFixed(2),
    pointB_keypoint_id: pointB.keypoint_id,
    pointB_x: pointB.x.toFixed(2),
    pointB_y: pointB.y.toFixed(2),
    distance: distance.toFixed(6)
  });
}


// 距离模式选择
let distAId = null;
let distBId = null;
let distValue = null;

/* =========================
   通用工具
========================= */
function setStatus(txt) {
  if (statusText) statusText.textContent = txt;
}

function showMenu(open) {
  if (!fileDropdown) return;
  fileDropdown.style.display = open ? "block" : "none";
}

function showCameraModal(open) {
  if (!cameraModal) return;
  cameraModal.classList.toggle("hidden", !open);
}

function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

function numOrZero(v) {
  const x = parseFloat(v);
  return Number.isFinite(x) ? x : 0;
}

function getPoints(imageId) {
  return pointsMap[imageId] || [];
}

function setPoints(imageId, pts) {
  pointsMap[imageId] = pts;
}

function scheduleSave() {
  if (!currentImage) return;
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    try { await saveAnnotations(); } catch (_) {}
  }, 250);
}

async function saveAnnotations() {
  if (!currentImage) return;
  const image_id = currentImage.id;
  const pts = getPoints(image_id);

  await fetch(`/api/annotations/${image_id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      points: pts,
      meta: { name: currentImage.name, url: currentImage.url }
    })
  });
}

/* =========================
   自动编号：补缺优先
========================= */
function nextAvailableId(imageId) {
  const pts = getPoints(imageId);
  const used = new Set(
    pts.map(p => Number(p.keypoint_id))
       .filter(n => Number.isFinite(n) && n > 0)
  );
  let i = 1;
  while (used.has(i)) i++;
  return i;
}

function hasId(imageId, id) {
  const pts = getPoints(imageId);
  return pts.some(p => Number(p.keypoint_id) === Number(id));
}

function findPointById(imageId, id) {
  return getPoints(imageId).find(p => Number(p.keypoint_id) === Number(id)) || null;
}

/* =========================
   光标控制
========================= */
function updateCursor() {
  if (!canvas) return;
  canvas.classList.remove("crosshair");
  canvas.classList.remove("can-move");

  if (modePoint) {
    if (draggingId != null || hoverId != null) canvas.classList.add("can-move");
    else canvas.classList.add("crosshair");
  } else if (modeDistance) {
    // 距离模式：只点选，不拖动
    canvas.classList.add("crosshair");
  }
}

/* =========================
   文件菜单
========================= */
if (fileMenuBtn) {
  fileMenuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    showMenu(fileDropdown?.style.display !== "block");
  });
}
document.addEventListener("click", () => showMenu(false));
if (fileDropdown) fileDropdown.addEventListener("click", (e) => e.stopPropagation());

if (importImagesBtn) {
  importImagesBtn.addEventListener("click", () => {
    showMenu(false);
    if (imageInput) {
      imageInput.value = "";
      imageInput.click();
    }
  });
}

if (exportCsvBtn) {
  exportCsvBtn.addEventListener("click", () => {
    showMenu(false);

    const triggerDownload = (href, downloadName = "") => {
      const link = document.createElement("a");
      link.href = href;
      if (downloadName) {
        link.download = downloadName;
      }
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    // 若当前没有距离结果，回退导出后端聚合的关键点 CSV
    if (distanceResults.length === 0) {
      triggerDownload("/api/export/csv");
      setStatus("未检测到距离结果，已导出关键点 CSV");
      return;
    }

    const toCsvCell = (value) => {
      const text = value == null ? "" : String(value);
      if (/[",\r\n]/.test(text)) {
        return `"${text.replace(/"/g, '""')}"`;
      }
      return text;
    };

    // 创建 CSV 文件
    const csvHeader = ["点 A keypoint_id", "点 A X", "点 A Y", "点 B keypoint_id", "点 B X", "点 B Y", "距离"];
    const csvRows = distanceResults.map(result => [
      result.pointA_keypoint_id,
      result.pointA_x,
      result.pointA_y,
      result.pointB_keypoint_id,
      result.pointB_x,
      result.pointB_y,
      result.distance
    ]);

    // 生成 CSV 字符串
    const csvContent = [csvHeader, ...csvRows]
      .map(row => row.map(toCsvCell).join(","))
      .join("\r\n");

    // 创建 Blob 并触发下载
    const fileName = `distance_results_${new Date().toISOString().slice(0, 10)}.csv`;
    const blob = new Blob(["\uFEFF", csvContent], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    triggerDownload(url, fileName);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus(`已导出距离结果 CSV: ${fileName}`);
  });
}

if (exportJsonBtn) {
  exportJsonBtn.addEventListener("click", () => {
    showMenu(false);
    const link = document.createElement("a");
    link.href = "/api/export/json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setStatus("已导出标注点JSON(批量)（xanything label）");
  });
}


// 清空当前图片和相关计算结果
function clearCurrentImageData() {
  distanceResults = [];
  if (computePreview) {
    computePreview.textContent = "";  // 清空预览区域
  }

  // 清空标注点数据
  if (currentImage) {
    pointsMap[currentImage.id] = [];  // 清空标注点数据
  }

  // 重置当前图片状态
  currentImage = null;
  selectedId = null;
  draggingId = null;
  hoverId = null;

  // 清空画布上的所有点
  if (canvas) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // 如果当前处于距离模式下，退出该模式
  if (modeDistance) {
    modeDistance = false;
    toolDistance.classList.toggle("active", false);
    distAId = distBId = distValue = null;
    distanceLines = [];  // 清空所有连线
    updateCursor();
    redraw();
    setStatus("已退出距离标识模式");
  }
}

// 绑定刷新按钮事件
const refreshBtn = document.getElementById("refreshBtn");
if (refreshBtn) {
  refreshBtn.addEventListener("click", refreshImages);  // 点击刷新时清空图片区域
}


// 批量上传图片
if (imageInput) {
  imageInput.addEventListener("change", async () => {
    const files = Array.from(imageInput.files || []);
    if (!files.length) return;

    const total = files.reduce((s, f) => s + (f.size || 0), 0);
    const limitMB = 500;
    if (total > limitMB * 1024 * 1024) {
      setStatus(`选择的图片总大小超过 ${limitMB}MB，请分批导入`);
      return;
    }

    const fd = new FormData();
    files.forEach(f => fd.append("images", f)); // 后端字段名 images

    setStatus("上传图片中...");
    try {
      const res = await fetch("/api/images/upload", { method: "POST", body: fd });
      if (!res.ok) {
        const t = await res.text();
        setStatus(`上传失败：HTTP ${res.status}`);
        console.error(t);
        return;
      }
      const data = await res.json();
      const newOnes = data.images || [];

      // 清空原图的相关数据并加载新图
      clearCurrentImageData();
      
      // 清空缩略图区域
      const gridView = document.getElementById("gridView");
      gridView.innerHTML = "";  // 清空图片缩略图区域

      // 更新图片数组并渲染新图片
      images = newOnes;
      renderThumbnails();  // 重新渲染缩略图

      if (images.length) {
        await openImage(images[0].id);  // 打开新导入的图片
      } else {
        setStatus("未加载图片");
      }

    } catch (e) {
      setStatus("上传失败：网络异常");
      console.error(e);
    }
  });
}

async function refreshImages() {
  setStatus("清空中...");

  // 发送请求到后端清空数据
  const r = await fetch("/api/images/clear", { method: "POST" });
  if (!r.ok) {
    setStatus("清空失败：后端接口错误");
    return;
  }

  // 清空前端的所有图片数据
  images = [];
  currentImage = null;
  imgObj = null;
  pointsMap = {};
  kp3dMap.clear();
  lastComputeRows = [];
  distanceLines = [];
  distanceResults = [];
  distAId = distBId = distValue = null;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 重新加载缩略图
  renderThumbnails();
  renderPointPanel();
  if (computePreview) computePreview.textContent = "请先导入图片并标注点";
  setStatus("图片区域已清空，等待新图片导入");
  
  // 重新从后端获取图片数据
  const res = await fetch("/api/images/list");
  const data = await res.json();
  images = data.images || [];
  renderThumbnails();
}


function renderThumbnails() {
  const gridView = document.getElementById("gridView");
  gridView.innerHTML = "";  // 清空现有的缩略图

  if (images.length === 0) {
    // 如果没有图片，则显示一个提示
    gridView.innerHTML = "<p>暂无图片，点击上传新图片</p>";
    return;
  }

  images.forEach(img => {
    const d = document.createElement("div");
    d.className = "thumb" + (currentImage && currentImage.id === img.id ? " selected" : "");
    d.title = img.name || img.id;
    d.innerHTML = `<img src="${img.url}" alt="">`;
    d.onclick = async () => { await openImage(img.id); };
    gridView.appendChild(d);
  });
}


// 打开图片并清空原图数据
async function openImage(imageId) {
  const img = images.find(x => x.id === imageId);
  if (!img) return;

  currentImage = img;
  selectedId = null;
  draggingId = null;
  hoverId = null;

  renderThumbnails();
  setStatus(`当前：${img.name || img.id}`);

  // 清空原图片的计算结果
  distanceResults = [];  // 清空上次的计算结果
  if (computePreview) {
    computePreview.textContent = "";  // 清空预览区域
  }

  // 拉取标注
  try {
    const ann = await fetch(`/api/annotations/${imageId}`).then(r => r.json());
    const pts = (ann.points || []).map(p => ({
      keypoint_id: Number(p.keypoint_id),
      x: Number(p.x),
      y: Number(p.y),
    })).filter(p =>
      Number.isFinite(p.keypoint_id) && Number.isFinite(p.x) && Number.isFinite(p.y)
    );
    setPoints(imageId, pts);
  } catch (_) {
    setPoints(imageId, []);
  }

  // 加载新图像
  imgObj = new Image();
  imgObj.onload = () => {
    const vw = Math.max(1, singleView.clientWidth - 20);
    const vh = Math.max(1, singleView.clientHeight - 20);
    zoom = Math.min(vw / imgObj.width, vh / imgObj.height, 1);

    applyZoomAndRedraw(true);
    renderPointPanel();
    updateCursor();
  };
  imgObj.onerror = () => setStatus("图片加载失败");
  imgObj.src = img.url;
}

/* =========================
   缩放与绘制
========================= */
function applyZoomAndRedraw(centerToView) {
  if (!imgObj || !currentImage) return;

  const dpr = window.devicePixelRatio || 1;
  const cssW = Math.max(1, Math.round(imgObj.width * zoom));
  const cssH = Math.max(1, Math.round(imgObj.height * zoom));

  canvas.style.width = cssW + "px";
  canvas.style.height = cssH + "px";
  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  redraw();

  if (centerToView) {
    const viewW = singleView.clientWidth;
    const viewH = singleView.clientHeight;
    singleView.scrollLeft = Math.max(0, (cssW - viewW) / 2);
    singleView.scrollTop = Math.max(0, (cssH - viewH) / 2);
  }
}

function redraw() {
  if (!currentImage || !imgObj) return;

  const cssW = Math.round(imgObj.width * zoom);
  const cssH = Math.round(imgObj.height * zoom);

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.drawImage(imgObj, 0, 0, cssW, cssH);

  const pts = getPoints(currentImage.id);

  // 绘制多个距离连线
  if (modeDistance) {
    distanceLines.forEach(line => {
      const pa = findPointById(currentImage.id, line.a);
      const pb = findPointById(currentImage.id, line.b);
      if (pa && pb) {
        const ax = pa.x * zoom, ay = pa.y * zoom;
        const bx = pb.x * zoom, by = pb.y * zoom;

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "rgba(0,255,255,0.9)";
        ctx.stroke();

        if (line.distance != null) {
          const mx = (ax + bx) / 2;
          const my = (ay + by) / 2;
          const text = `${line.distance.toFixed(6)}`;
          ctx.font = "13px Arial";
          const w = ctx.measureText(text).width;
          ctx.fillStyle = "rgba(0,0,0,0.6)";
          ctx.fillRect(mx - w / 2 - 6, my - 12, w + 12, 22);
          ctx.fillStyle = "#fff";
          ctx.fillText(text, mx - w / 2, my + 4);
        }
      }
    });
  }

  // 再画点
  ctx.font = "12px Arial";
  ctx.textBaseline = "middle";

  for (const p of pts) {
    const sx = p.x * zoom;
    const sy = p.y * zoom;

    const isSel = (Number(p.keypoint_id) === Number(selectedId));
    const isA = (modeDistance && Number(p.keypoint_id) === Number(distAId));
    const isB = (modeDistance && Number(p.keypoint_id) === Number(distBId));

    const r = (isSel || isA || isB) ? 8 : 7;

    ctx.beginPath();
    ctx.arc(sx, sy, r, 0, Math.PI * 2);

    if (isA) ctx.fillStyle = "yellow";
    else if (isB) ctx.fillStyle = "cyan";
    else ctx.fillStyle = isSel ? "yellow" : "red";

    ctx.fill();

    const label = String(p.keypoint_id);
    const tx = sx + 10;
    const ty = sy;

    const padX = 4, padY = 2;
    const w = ctx.measureText(label).width;

    ctx.fillStyle = "rgba(0,0,0,0.55)";
    ctx.fillRect(tx - padX, ty - 10 - padY, w + padX * 2, 20 + padY * 2);

    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, tx, ty);
  }
}

function updateDistanceTable(imageName, pointA, pointB, distance) {
  const tableBody = document.getElementById("distanceTable").getElementsByTagName("tbody")[0];
  
  // 创建新的一行
  const newRow = tableBody.insertRow();
  
  // 创建表格单元格并填充内容
  const cellImageName = newRow.insertCell(0);
  cellImageName.textContent = imageName;

  const cellPointA = newRow.insertCell(1);
  cellPointA.textContent = `(${pointA.keypoint_id}, ${pointA.x}, ${pointA.y})`;

  const cellPointB = newRow.insertCell(2);
  cellPointB.textContent = `(${pointB.keypoint_id}, ${pointB.x}, ${pointB.y})`;

  const cellDistance = newRow.insertCell(3);
  cellDistance.textContent = distance.toFixed(6); // 格式化为小数点后6位
}


/* Ctrl+滚轮缩放；普通滚轮滚动 */
if (singleView) {
  singleView.addEventListener("wheel", (e) => {
    if (!imgObj) return;

    if (e.ctrlKey) {
      e.preventDefault();

      const rect = singleView.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      const sx = singleView.scrollLeft;
      const sy = singleView.scrollTop;

      const imgX = (sx + mx) / zoom;
      const imgY = (sy + my) / zoom;

      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      zoom = clamp(zoom * factor, 0.05, 8);

      applyZoomAndRedraw(false);

      singleView.scrollLeft = imgX * zoom - mx;
      singleView.scrollTop = imgY * zoom - my;
    }
  }, { passive: false });
}

/* =========================
   工具栏：标注模式 / 适配 / 计算3D / 距离标识
========================= */
if (toolPoint) {
  toolPoint.addEventListener("click", () => {
    modePoint = !modePoint;
    if (modePoint) {
      modeDistance = false;
      distAId = distBId = distValue = null;
    }
    toolPoint.classList.toggle("active", modePoint);
    if (toolDistance) toolDistance.classList.toggle("active", modeDistance);

    draggingId = null;
    hoverId = null;
    updateCursor();
    redraw();
  });
}

if (toolFit) {
  toolFit.addEventListener("click", () => {
    if (!imgObj) return;
    const vw = Math.max(1, singleView.clientWidth - 20);
    const vh = Math.max(1, singleView.clientHeight - 20);
    zoom = Math.min(vw / imgObj.width, vh / imgObj.height, 1);
    applyZoomAndRedraw(true);
  });
}

function isValidPos(pos) {
  return Array.isArray(pos) && pos.length === 3 && pos.every(v => Number.isFinite(Number(v)));
}

function updateComputePreview() {
  if (!computePreview) return;

  const ids = Array.from(kp3dMap.keys()).sort((a, b) => a - b);
  const lines = [];
  lines.push("keypoint_id,X,Y,Z");

  for (const id of ids) {
    const p = kp3dMap.get(id);
    lines.push(`${id},${p[0]},${p[1]},${p[2]}`);
  }

  if (ids.length === 0) lines.push("（暂无可用3D点：请先标注并计算3D）");
  computePreview.textContent = lines.join("\n");
}

async function compute3D() {
  setStatus("计算中：提取点位与XMP元信息 + 三角化...");
  if (computePreview) computePreview.textContent = "计算中...";

  const res = await fetch("/api/compute/3d", { method: "POST" });
  if (!res.ok) throw new Error(await res.text());

  const data = await res.json();
  const rows = data.rows || [];
  lastComputeRows = rows;

  // 构建 keypoint_id -> 3D
  kp3dMap.clear();
  for (const r of rows) {
    const id = Number(r.keypoint_id);
    const pos = r._3d_position;
    if (!Number.isFinite(id)) continue;
    if (!isValidPos(pos)) continue;
    if (!kp3dMap.has(id)) kp3dMap.set(id, [Number(pos[0]), Number(pos[1]), Number(pos[2])]);
  }

  setStatus(`计算完成：3D点数量=${kp3dMap.size}`);
  updateComputePreview();
  return rows;
}

if (toolCompute3D) {
  toolCompute3D.addEventListener("click", async () => {
    try {
      await compute3D();
    } catch (e) {
      setStatus("计算失败");
      if (computePreview) computePreview.textContent = String(e);
      console.error(e);
    }
  });
}

// 挑选“包含全部关键点”的图片（基于计算结果 rows）
function chooseBestImageNameFromRows(rows) {
  const allIds = new Set(Array.from(kp3dMap.keys())); // 只考虑已算出3D的点
  if (allIds.size === 0) return null;

  const imgMap = new Map(); // imageName -> Set(ids)
  for (const r of rows) {
    const name = r.image;
    const id = Number(r.keypoint_id);
    if (!name || !Number.isFinite(id)) continue;
    if (!allIds.has(id)) continue;

    if (!imgMap.has(name)) imgMap.set(name, new Set());
    imgMap.get(name).add(id);
  }

  // 1) 先找包含全部的
  for (const [name, setIds] of imgMap.entries()) {
    let ok = true;
    for (const id of allIds) {
      if (!setIds.has(id)) { ok = false; break; }
    }
    if (ok) return name;
  }

  // 2) 否则选覆盖最多的
  let bestName = null;
  let bestCount = -1;
  for (const [name, setIds] of imgMap.entries()) {
    if (setIds.size > bestCount) {
      bestCount = setIds.size;
      bestName = name;
    }
  }
  return bestName;
}

function calc3dDistance(aId, bId) {
  const a = kp3dMap.get(Number(aId));
  const b = kp3dMap.get(Number(bId));
  if (!isValidPos(a) || !isValidPos(b)) return null;
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

if (toolDistance) {
  toolDistance.addEventListener("click", async () => {
    if (modeDistance) {
      // 退出距离模式时
      modeDistance = false;
      toolDistance.classList.toggle("active", false);
      distAId = distBId = distValue = null;
      distanceLines = [];  // 清空所有连线
      updateCursor();
      redraw();
      setStatus("已退出距离标识模式");

      // 保持已计算的 CSV 结果
    } else {
      // 进入距离模式时，清空上一次的计算结果
      modeDistance = true;
      modePoint = false;
      toolDistance.classList.toggle("active", true);
      if (toolPoint) toolPoint.classList.toggle("active", false);

      distAId = distBId = distValue = null;
      selectedId = null;
      draggingId = null;
      hoverId = null;
      updateCursor();
      redraw();
      setStatus("距离标识模式：依次点击两个关键点，自动计算3D距离并画线（A黄/B青）");

      // 进入距离模式时，清空历史计算结果
      distanceResults = [];  // 清空上一次的计算结果
      if (computePreview) {
        computePreview.textContent = "";  // 清空预览区域
      }
    }
  });
}

/* =========================
   画布坐标 & 命中检测
========================= */
function toImageXY(ev) {
  const rect = canvas.getBoundingClientRect();
  const cx = ev.clientX - rect.left;
  const cy = ev.clientY - rect.top;
  return { x: Math.round(cx / zoom), y: Math.round(cy / zoom) };
}

function hitTest(x, y) {
  if (!currentImage) return null;
  const pts = getPoints(currentImage.id);

  const rScreen = 12;
  const th = rScreen / zoom;

  let bestId = null;
  let bestD = Infinity;
  for (const p of pts) {
    const d = Math.hypot(p.x - x, p.y - y);
    if (d < th && d < bestD) {
      bestD = d;
      bestId = p.keypoint_id;
    }
  }
  return bestId;
}

/* =========================
   画布交互：标注模式（新增/拖动/删除）
   距离模式（仅点选两点）
========================= */
if (canvas) {
  canvas.addEventListener("mousemove", (e) => {
    if (!currentImage) return;

    const { x, y } = toImageXY(e);
    hoverId = hitTest(x, y);
    updateCursor();

    // 距离模式下不做别的
    if (modeDistance) return;

    // 标注模式：拖动由 window mousemove 处理
  });

  canvas.addEventListener("mouseleave", () => {
    hoverId = null;
    updateCursor();
  });

  canvas.addEventListener("mousedown", (e) => {
    if (!currentImage || !imgObj) return;

    const { x, y } = toImageXY(e);
    const hitId = hitTest(x, y);

    // ---------- 距离模式：添加多组距离标识点 ----------
    if (modeDistance) {
      if (hitId == null) return;

      // 点必须有3D坐标才能参与计算
      if (!kp3dMap.has(Number(hitId))) {
        setStatus(`点 ${hitId} 没有3D坐标（可能观测不足两张或未计算3D）`);
        return;
      }

      // 如果没有选择A点，则选择A点
      if (distAId == null || (distAId != null && distBId != null)) {
        distAId = hitId;
        distBId = null;
        distanceLines.push({ a: distAId, b: distBId, distance: null });  // 新建一组距离对，初始距离为null
        distValue = null;  // 清空上次的计算值
        setStatus(`已选择 A=${distAId}，请再选择 B`);
      } else {
        distBId = hitId;
        distanceLines[distanceLines.length - 1].b = distBId;  // 更新最近的一组点对
        if (Number(distBId) === Number(distAId)) {
          setStatus("A 与 B 不能相同，请重新选择 B");
          distBId = null;
          distValue = null;  // 清空之前的距离值
          redraw();
          return;
        }

        // 计算新的距离
        const distance = calc3dDistance(distAId, distBId);
        distanceLines[distanceLines.length - 1].distance = distance; // 更新新的距离值

        if (distance == null) {
          setStatus("A或B没有可用3D坐标，无法计算");
        } else {
          setStatus(`A=${distAId}, B=${distBId} 距离=${distance.toFixed(6)}（ECEF单位一致）`);

          // 获取点A和点B的坐标
          const pointA = findPointById(currentImage.id, distAId);
          const pointB = findPointById(currentImage.id, distBId);

          if (pointA && pointB && computePreview) {
            // 保存距离计算结果
            saveDistanceResult(pointA, pointB, distance);
            
            // 更新预览区显示
            computePreview.textContent += `A(${pointA.keypoint_id}): (${pointA.x.toFixed(2)}, ${pointA.y.toFixed(2)}) ` +
                                          `B(${pointB.keypoint_id}): (${pointB.x.toFixed(2)}, ${pointB.y.toFixed(2)}) ` +
                                          `Distance: ${distance.toFixed(6)}\n`;
          }
        }
      }

      redraw();
      return;
    }

    // ---------- 标注模式 ----------
    if (!modePoint) return;

    // 点击已有点：进入拖动
    if (hitId != null) {
      selectedId = hitId;
      const p = findPointById(currentImage.id, hitId);
      draggingId = hitId;
      dragOffset.dx = p ? (p.x - x) : 0;
      dragOffset.dy = p ? (p.y - y) : 0;
      renderPointPanel();
      redraw();
      updateCursor();
      return;
    }

    // 点击空白：新增点（自动编号补缺）
    const imageId = currentImage.id;
    const kid = nextAvailableId(imageId);

    const pts = getPoints(imageId);
    pts.push({ keypoint_id: kid, x, y });
    setPoints(imageId, pts);

    selectedId = kid;
    renderPointPanel();
    redraw();
    scheduleSave();
    updateCursor();
  });
}

// 拖动：仅标注模式允许
window.addEventListener("mousemove", (e) => {
  if (!modePoint || modeDistance) return;
  if (!currentImage || draggingId == null) return;

  const { x, y } = toImageXY(e);
  const p = findPointById(currentImage.id, draggingId);
  if (!p) return;

  p.x = x + dragOffset.dx;
  p.y = y + dragOffset.dy;

  redraw();
  renderPointPanel(false);
  scheduleSave();
});

window.addEventListener("mouseup", () => {
  if (draggingId != null) {
    draggingId = null;
    updateCursor();
  }
});

// Delete 删除：仅标注模式允许
window.addEventListener("keydown", (e) => {
  if (e.key !== "Delete") return;
  if (!modePoint || modeDistance) return;
  if (!currentImage || selectedId == null) return;

  const imageId = currentImage.id;
  const pts = getPoints(imageId).filter(p => Number(p.keypoint_id) !== Number(selectedId));
  setPoints(imageId, pts);

  selectedId = null;
  draggingId = null;
  hoverId = null;
  updateCursor();

  renderPointPanel();
  redraw();
  scheduleSave();
});

/* =========================
   右侧列表：双击改 ID（仅标注模式允许）
========================= */
function renderPointPanel(scrollToSelected = true) {
  if (!currentImage) {
    if (pointList) pointList.innerHTML = "";
    if (currentPoint) currentPoint.textContent = "未选中";
    return;
  }

  const imageId = currentImage.id;
  const pts = getPoints(imageId).slice().sort((a, b) => a.keypoint_id - b.keypoint_id);

  if (pointList) pointList.innerHTML = "";

  pts.forEach(p => {
    const row = document.createElement("div");
    row.className = "point-row" + (Number(p.keypoint_id) === Number(selectedId) ? " selected" : "");

    const idSpan = document.createElement("span");
    idSpan.className = "point-label";
    idSpan.textContent = `#${p.keypoint_id}`;

    const coordSpan = document.createElement("span");
    coordSpan.className = "point-coord";
    coordSpan.textContent = `(${p.x}, ${p.y})`;

    row.addEventListener("click", () => {
      selectedId = p.keypoint_id;
      renderPointPanel();
      redraw();
    });

    idSpan.addEventListener("dblclick", (ev) => {
      ev.stopPropagation();
      if (!modePoint || modeDistance) {
        setStatus("距离标识模式下不允许修改ID");
        return;
      }

      const v = prompt("输入新的点ID（仅数字且不重复）：", String(p.keypoint_id));
      if (v == null) return;

      const s = String(v).trim();
      if (!/^\d+$/.test(s)) return;

      const newId = parseInt(s, 10);
      if (!Number.isFinite(newId) || newId <= 0) return;

      if (newId !== p.keypoint_id && hasId(imageId, newId)) return;

      const real = findPointById(imageId, p.keypoint_id);
      if (!real) return;

      real.keypoint_id = newId;
      selectedId = newId;

      setStatus("点ID已修改：如需3D/测距请重新计算3D");

      renderPointPanel(false);
      redraw();
      scheduleSave();
    });

    row.appendChild(idSpan);
    row.appendChild(coordSpan);
    pointList.appendChild(row);
  });

  const sel = selectedId != null ? findPointById(imageId, selectedId) : null;
  if (!currentPoint) return;

  if (!sel) {
    currentPoint.textContent = "未选中";
  } else {
    currentPoint.innerHTML = `
      <div><b>ID：</b>${sel.keypoint_id}</div>
      <div><b>X：</b>${sel.x}</div>
      <div><b>Y：</b>${sel.y}</div>
    `;
  }

  if (scrollToSelected && selectedId != null && pointList) {
    const el = pointList.querySelector(".point-row.selected");
    if (el) el.scrollIntoView({ block: "nearest" });
  }
}

/* =========================
   相机参数：导入 JSON + 手动数值设置
========================= */
async function fetchCameraParams() {
  const r = await fetch("/api/camera/params");
  return await r.json();
}

async function fillCameraFormFromServer() {
  const params = await fetchCameraParams();
  const intr = params.intrinsics || {};
  const extr = params.extrinsics || {};

  const K = intr.camera_matrix || [[0, 0, 0], [0, 0, 0], [0, 0, 1]];
  if (fxInput) fxInput.value = K?.[0]?.[0] ?? 0;
  if (fyInput) fyInput.value = K?.[1]?.[1] ?? 0;
  if (cxInput) cxInput.value = K?.[0]?.[2] ?? 0;
  if (cyInput) cyInput.value = K?.[1]?.[2] ?? 0;

  let dc = intr.distortion_coefficients ?? [[0, 0, 0, 0, 0]];
  if (Array.isArray(dc) && dc.length === 5) dc = [dc];
  const d0 = (dc && dc[0]) ? dc[0] : [0, 0, 0, 0, 0];

  if (k1Input) k1Input.value = d0[0] ?? 0;
  if (k2Input) k2Input.value = d0[1] ?? 0;
  if (p1Input) p1Input.value = d0[2] ?? 0;
  if (p2Input) p2Input.value = d0[3] ?? 0;
  if (k3Input) k3Input.value = d0[4] ?? 0;

  if (yawOffInput) yawOffInput.value = extr.yaw_offset ?? 0;
  if (pitchOffInput) pitchOffInput.value = extr.pitch_offset ?? 0;
  if (rollOffInput) rollOffInput.value = extr.roll_offset ?? 0;
  if (dXInput) dXInput.value = extr.dX ?? 0;
  if (dYInput) dYInput.value = extr.dY ?? 0;
  if (dZInput) dZInput.value = extr.dZ ?? 0;
}

function buildIntrinsicsPayload() {
  const fx = numOrZero(fxInput?.value);
  const fy = numOrZero(fyInput?.value);
  const cx = numOrZero(cxInput?.value);
  const cy = numOrZero(cyInput?.value);

  const k1 = numOrZero(k1Input?.value);
  const k2 = numOrZero(k2Input?.value);
  const p1 = numOrZero(p1Input?.value);
  const p2 = numOrZero(p2Input?.value);
  const k3 = numOrZero(k3Input?.value);

  return {
    camera_matrix: [
      [fx, 0.0, cx],
      [0.0, fy, cy],
      [0.0, 0.0, 1.0]
    ],
    distortion_coefficients: [[k1, k2, p1, p2, k3]]
  };
}

function buildExtrinsicsPayload() {
  return {
    yaw_offset: numOrZero(yawOffInput?.value),
    pitch_offset: numOrZero(pitchOffInput?.value),
    roll_offset: numOrZero(rollOffInput?.value),
    dX: numOrZero(dXInput?.value),
    dY: numOrZero(dYInput?.value),
    dZ: numOrZero(dZInput?.value)
  };
}

if (importIntrinsicsBtn) {
  importIntrinsicsBtn.addEventListener("click", () => {
    showMenu(false);
    if (intrinsicsInput) {
      intrinsicsInput.value = "";
      intrinsicsInput.click();
    }
  });
}
if (importExtrinsicsBtn) {
  importExtrinsicsBtn.addEventListener("click", () => {
    showMenu(false);
    if (extrinsicsInput) {
      extrinsicsInput.value = "";
      extrinsicsInput.click();
    }
  });
}

if (intrinsicsInput) {
  intrinsicsInput.addEventListener("change", async () => {
    const f = intrinsicsInput.files?.[0];
    if (!f) return;
    try {
      const json = JSON.parse(await f.text());
      const r = await fetch("/api/camera/intrinsics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json)
      });
      if (!r.ok) throw new Error(await r.text());
      setStatus("内参已加载（如需测距请重新计算3D）");
    } catch (e) {
      setStatus("内参加载失败");
      alert(String(e));
    }
  });
}

if (extrinsicsInput) {
  extrinsicsInput.addEventListener("change", async () => {
    const f = extrinsicsInput.files?.[0];
    if (!f) return;
    try {
      const json = JSON.parse(await f.text());
      const r = await fetch("/api/camera/extrinsics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(json)
      });
      if (!r.ok) throw new Error(await r.text());
      setStatus("外参已加载（如需测距请重新计算3D）");
    } catch (e) {
      setStatus("外参加载失败");
      alert(String(e));
    }
  });
}

if (openCameraModalBtn) {
  openCameraModalBtn.addEventListener("click", async () => {
    showMenu(false);
    try { await fillCameraFormFromServer(); } catch (e) { console.error(e); }
    showCameraModal(true);
  });
}
if (cameraCancelBtn) cameraCancelBtn.addEventListener("click", () => showCameraModal(false));

if (cameraResetBtn) {
  cameraResetBtn.addEventListener("click", async () => {
    try {
      const r = await fetch("/api/camera/reset", { method: "POST" });
      if (!r.ok) { alert(await r.text()); return; }
      await fillCameraFormFromServer();
      setStatus("已恢复默认内外参（如需测距请重新计算3D）");
    } catch (e) {
      alert(String(e));
    }
  });
}

if (cameraSaveBtn) {
  cameraSaveBtn.addEventListener("click", async () => {
    try {
      const intr = buildIntrinsicsPayload();
      const extr = buildExtrinsicsPayload();

      const r1 = await fetch("/api/camera/intrinsics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(intr)
      });
      if (!r1.ok) throw new Error(await r1.text());

      const r2 = await fetch("/api/camera/extrinsics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(extr)
      });
      if (!r2.ok) throw new Error(await r2.text());

      setStatus("内外参已保存（如需测距请重新计算3D）");
      showCameraModal(false);
    } catch (e) {
      alert("保存失败：" + String(e));
    }
  });
}

/* =========================
   启动：拉取图片列表
========================= */
(async function boot() {
  try {
    updateCursor();
    setStatus("加载中...");

    // ✅ 判断是否是浏览器刷新（F5/刷新按钮）
    const navEntry = performance.getEntriesByType?.("navigation")?.[0];
    const isReload =
      (navEntry && navEntry.type === "reload") ||
      (performance.navigation && performance.navigation.type === 1); // 兼容老浏览器

    // ✅ 如果是刷新，则先清后端内存
    if (isReload) {
      const r = await fetch("/api/images/clear", { method: "POST" });
      if (!r.ok) {
        console.warn("clear failed:", await r.text());
      }
    }

    // 再拉取列表
    const res = await fetch("/api/images/list");
    const data = await res.json();
    images = data.images || [];
    renderThumbnails();

    if (images.length) {
      await openImage(images[0].id);
      if (computePreview) computePreview.textContent = "请先标注并计算3D";
    } else {
      setStatus("未加载图片");
      if (computePreview) computePreview.textContent = "请先导入图片并标注点";
    }
  } catch (e) {
    setStatus("启动失败：请检查后端服务是否运行");
    console.error(e);
  }
})();


