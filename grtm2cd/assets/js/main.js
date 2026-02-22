/**
 * @file main.js
 * @description Composition Root + DOM event handling (SRS §5.4)
 * Responsibilities:
 *   1. Listen to DOM events (file drops, button clicks)
 *   2. Gather raw inputs (file bytes, filenames)
 *   3. Instantiate Adapters
 *   4. Invoke UseCases with injected Adapter dependencies
 *   5. Receive results and update the DOM
 *   6. Catch GrtmError exceptions and display error messages
 *   7. After TM drop, call compressor.compress and capacityCalc.findMinimumEntry
 *      to display the compressed size and minimum required resolution hint (§6.1 Step 2)
 */

document.addEventListener("dragover", (e) => e.preventDefault());
document.addEventListener("drop", (e) => e.preventDefault());

import { execute as encodeExecute } from "./usecase/encodeUseCase.js";
import { execute as decodeExecute } from "./usecase/decodeUseCase.js";
import { createCompressorAdapter } from "./adapter/compressorAdapter.js";
import { createImageAdapter } from "./adapter/imageAdapter.js";
import { createCryptoAdapter } from "./adapter/cryptoAdapter.js";
import { GrtmError } from "./domain/errors.js";
import {
  availableBytes,
  findMinimumEntry,
  STANDARD_RESOLUTIONS,
  MAX_CARRIER_PIXELS,
  HEADER_BYTES,
  AES_OVERHEAD_BYTES,
  CARRIER_ID_TOTAL_BYTES,
  AR_BOUNDARY_LOW,
  AR_BOUNDARY_HIGH,
} from "./domain/capacityCalc.js";

// ── Adapters (instantiated once) ──
const compressor   = createCompressorAdapter(window.pako);
const imageAdapter = createImageAdapter();
const cryptoAdapter = createCryptoAdapter();

// ── DOM References ──
const $ = (id) => document.getElementById(id);

// Encode panel
const tmDropzone     = $("tm-dropzone");
const tmFileInput    = $("tm-file-input");
const tmInfo         = $("tm-info");
const tmMinSize      = $("tm-min-size");
const catDropzone    = $("cat-dropzone");
const catFileInput   = $("cat-file-input");
const dogDropzone    = $("dog-dropzone");
const dogFileInput   = $("dog-file-input");
const catInfo        = $("cat-info");
const dogInfo        = $("dog-info");
const encodeStatus   = $("encode-status");
const encodeResult   = $("encode-result");
const catPreviewImg  = $("cat-preview-img");
const dogPreviewImg  = $("dog-preview-img");
const catDownloadBtn = $("cat-download-btn");
const dogDownloadBtn = $("dog-download-btn");
const encodeWarnings = $("encode-warnings");
const encodeNotify   = $("encode-notify");

// Decode panel
const dec1Dropzone   = $("dec1-dropzone");
const dec1FileInput  = $("dec1-file-input");
const dec2Dropzone   = $("dec2-dropzone");
const dec2FileInput  = $("dec2-file-input");
const dec1Info       = $("dec1-info");
const dec2Info       = $("dec2-info");
const decodeStatus   = $("decode-status");
const decodeResult   = $("decode-result");
const decDownloadBtn = $("dec-download-btn");

// ── State ──
let tmFile       = null; // { name, bytes }
let catFile      = null; // { name, bytes, width, height }
let dogFile      = null; // { name, bytes, width, height }
let compressedSize = 0;
let dec1File     = null; // { name, bytes }
let dec2File     = null; // { name, bytes }

// ── Helpers ──
function formatSize(bytes) {
  if (bytes < 1024)             return `${bytes} B`;
  if (bytes < 1024 * 1024)      return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function readFile(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.readAsArrayBuffer(file);
  });
}

function showError(statusEl, msg) {
  statusEl.textContent = `Error: ${msg}`;
  statusEl.style.display = "block";
  statusEl.style.color = "red";
}

function hideEl(el) { el.style.display = "none"; }
function showEl(el)  { el.style.display = "block"; }

// ── Tab switching ──
window.switchTab = function (tabId) {
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  $(tabId + "-panel").classList.add("active");
  document.querySelectorAll(".tab-btn").forEach((b) => {
    if (b.dataset.tab === tabId) b.classList.add("active");
  });
};

// ── Dropzone wiring ──
function setupDropzone(dropzoneEl, fileInputEl, handler) {
  dropzoneEl.addEventListener("click", () => fileInputEl.click());
  dropzoneEl.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzoneEl.style.borderColor = "var(--border-focus)";
  });
  dropzoneEl.addEventListener("dragleave", () => {
    dropzoneEl.style.borderColor = "";
  });
  dropzoneEl.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzoneEl.style.borderColor = "";
    if (e.dataTransfer.files.length > 0) handler(e.dataTransfer.files[0]);
  });
  fileInputEl.addEventListener("change", () => {
    if (fileInputEl.files.length > 0) {
      handler(fileInputEl.files[0]);
      fileInputEl.value = "";
    }
  });
}

// ── Minimum resolution hint (§5.4, §6.1 Step 2) ──
function updateMinSize() {
  if (compressedSize <= 0) {
    tmMinSize.textContent = "";
    return;
  }
  const fileNameByteLen = tmFile
    ? new TextEncoder().encode(tmFile.name).length
    : 10;
  const minTotal =
    HEADER_BYTES +
    fileNameByteLen +
    compressedSize +
    AES_OVERHEAD_BYTES +
    CARRIER_ID_TOTAL_BYTES;
  const bytesPerCarrier = Math.ceil(minTotal / 2);
  const entry = findMinimumEntry(bytesPerCarrier);
  if (entry === null) {
    tmMinSize.textContent = "Payload is too large for any resolution.";
  } else {
    tmMinSize.textContent = `Required: ≥ ${entry.label} (${entry.w}×${entry.h})`;
  }
}

// ── Treasure Map handler ──
async function handleTreasureMap(file) {
  const bytes = await readFile(file);
  if (bytes.length === 0) {
    showError(
      encodeStatus,
      "Treasure Map file is empty. Please select a file with content.",
    );
    return;
  }
  try {
    const compressed = compressor.compress(bytes);
    compressedSize = compressed.length;
    tmFile = { name: file.name, bytes };
    tmInfo.textContent = `File: ${file.name}  (${formatSize(bytes.length)} → compressed ${formatSize(compressedSize)})`;
    showEl(tmInfo);
    updateMinSize();
    hideEl(encodeStatus);
    hideEl(encodeResult);
    hideEl(encodeNotify);
    tryEncode();
  } catch (e) {
    showError(encodeStatus, e.message || "Compression failed.");
  }
}

// ── Carrier image handler (Encode) ──
async function handleCarrier(file, which) {
  const bytes = await readFile(file);
  try {
    const result = await imageAdapter.downscaleToLimit(bytes, MAX_CARRIER_PIXELS);
    const info = {
      name: file.name,
      bytes,
      width:  result.width,
      height: result.height,
    };

    if (which === "cat") {
      catFile = info;
      catInfo.textContent = `${file.name} (${info.width}×${info.height})`;
      showEl(catInfo);
    } else {
      dogFile = info;
      dogInfo.textContent = `${file.name} (${info.width}×${info.height})`;
      showEl(dogInfo);
    }

    // Downscale warning (§10.2)
    if (result.downscaled) {
      encodeWarnings.textContent =
        `${which === "cat" ? "Cat" : "Dog"}: Image exceeds maximum pixel count. It will be automatically downscaled.`;
      showEl(encodeWarnings);
    } else {
      hideEl(encodeWarnings);
    }

    hideEl(encodeStatus);
    hideEl(encodeResult);
    hideEl(encodeNotify);
    tryEncode();
  } catch (e) {
    if (e instanceof GrtmError) {
      showError(encodeStatus, e.message);
    } else {
      showError(encodeStatus, "Failed to load image.");
    }
  }
}

// ── Auto-encode when all 3 inputs are ready ──
async function tryEncode() {
  if (!tmFile || !catFile || !dogFile) return;

  encodeStatus.textContent = "> Encoding...";
  encodeStatus.style.color = "";
  showEl(encodeStatus);
  hideEl(encodeResult);
  hideEl(encodeNotify);

  // Yield to UI
  await new Promise((r) => setTimeout(r, 50));

  try {
    const result = await encodeExecute({
      tmBytes:   tmFile.bytes,
      fileName:  tmFile.name,
      catRaw:    catFile.bytes,
      dogRaw:    dogFile.bytes,
      catWidth:  catFile.width,
      catHeight: catFile.height,
      deps: { compressor, imageAdapter, cryptoAdapter },
    });

    // Create PNG blobs
    const catBlob = await imageAdapter.toBlob(result.catStegoPixels, result.width, result.height);
    const dogBlob = await imageAdapter.toBlob(result.dogStegoPixels, result.width, result.height);

    // Set previews
    catPreviewImg.src = URL.createObjectURL(catBlob);
    dogPreviewImg.src = URL.createObjectURL(dogBlob);

    // Output filenames: c_{OriginalCatFilename}.png and d_{OriginalDogFilename}.png
    const catBaseName = catFile.name.replace(/\.[^.]+$/, "");
    const dogBaseName = dogFile.name.replace(/\.[^.]+$/, "");
    const catOutName  = `c_${catBaseName}.png`;
    const dogOutName  = `d_${dogBaseName}.png`;

    catDownloadBtn.textContent = `Download ${catOutName}`;
    catDownloadBtn.onclick = () => downloadBlob(catBlob, catOutName);
    dogDownloadBtn.textContent = `Download ${dogOutName}`;
    dogDownloadBtn.onclick = () => downloadBlob(dogBlob, dogOutName);

    // Resolution notification — always shown (ADR-29, §10.2)
    encodeNotify.textContent =
      `Output: ${result.label} (${result.width}×${result.height}) — Both images will be stretched to this resolution.`;
    showEl(encodeNotify);

    hideEl(encodeStatus);
    showEl(encodeResult);
  } catch (e) {
    if (e instanceof GrtmError) {
      showError(encodeStatus, e.message);
    } else {
      showError(encodeStatus, e.message || "Encoding failed.");
      console.error(e);
    }
  }
}

// ── Decode handlers ──
async function handleDecFile(file, which) {
  const bytes = await readFile(file);
  if (which === 1) {
    dec1File = { name: file.name, bytes };
    dec1Info.textContent = file.name;
    showEl(dec1Info);
  } else {
    dec2File = { name: file.name, bytes };
    dec2Info.textContent = file.name;
    showEl(dec2Info);
  }
  hideEl(decodeStatus);
  hideEl(decodeResult);
  tryDecode();
}

async function tryDecode() {
  if (!dec1File || !dec2File) return;

  decodeStatus.textContent = "> Decoding...";
  decodeStatus.style.color = "";
  showEl(decodeStatus);
  hideEl(decodeResult);

  await new Promise((r) => setTimeout(r, 50));

  try {
    const result = await decodeExecute({
      file1Raw: dec1File.bytes,
      file2Raw: dec2File.bytes,
      deps: { imageAdapter, cryptoAdapter, compressor },
    });

    const blob = new Blob([result.treasureMapBytes]);
    decDownloadBtn.textContent = `Download recovered: ${result.fileName}`;
    decDownloadBtn.onclick = () => downloadBlob(blob, result.fileName);

    hideEl(decodeStatus);
    showEl(decodeResult);
  } catch (e) {
    if (e instanceof GrtmError) {
      showError(decodeStatus, e.message);
    } else {
      showError(decodeStatus, e.message || "Decoding failed.");
      console.error(e);
    }
  }
}

// ── Download helper ──
function downloadBlob(blob, filename) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Wire up dropzones ──
setupDropzone(tmDropzone,  tmFileInput,  handleTreasureMap);
setupDropzone(catDropzone, catFileInput, (f) => handleCarrier(f, "cat"));
setupDropzone(dogDropzone, dogFileInput, (f) => handleCarrier(f, "dog"));
setupDropzone(dec1Dropzone, dec1FileInput, (f) => handleDecFile(f, 1));
setupDropzone(dec2Dropzone, dec2FileInput, (f) => handleDecFile(f, 2));

// ── Render Standard Resolution Table on page load (§6.3) ──
(function renderResolutionTable() {
  const table = $("res-table");
  if (!table) return;

  // Partition entries into the three AR categories
  const cat43  = [];
  const cat169 = [];
  const cat11  = [];

  for (const entry of STANDARD_RESOLUTIONS) {
    const ar = entry.w / entry.h;
    if (ar < AR_BOUNDARY_LOW) {
      cat11.push(entry);
    } else if (ar < AR_BOUNDARY_HIGH) {
      cat43.push(entry);
    } else {
      cat169.push(entry);
    }
  }

  const maxRows = Math.max(cat43.length, cat169.length, cat11.length);

  // Helper: format one cell
  function cellText(entry) {
    return entry ? `${entry.label}  ${entry.w}×${entry.h}` : "";
  }

  // thead
  const thead = document.createElement("thead");
  thead.innerHTML =
    "<tr><th>4:3</th><th>16:9</th><th>1:1</th></tr>";
  table.appendChild(thead);

  // tbody
  const tbody = document.createElement("tbody");
  for (let i = 0; i < maxRows; i++) {
    const tr = document.createElement("tr");
    [cat43[i], cat169[i], cat11[i]].forEach((entry) => {
      const td = document.createElement("td");
      td.textContent = cellText(entry);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
})();
