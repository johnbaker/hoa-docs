const pdfFile = "/assets/winston-hills-ccrs-and-amendments-complete-searchable-toc.pdf";

const snapshotConfigs = [
  {
    id: "ccr",
    instrumentId: "ccr-1999-05-27",
    file: "./data/snapshots/ccr@asof-2005-01-12.json",
  },
  {
    id: "exhibit-c",
    instrumentId: "exhibit-c-2005-01-04",
    file: "./data/snapshots/exhibit-c@asof-2005-01-12.json",
  },
  {
    id: "exhibit-d",
    instrumentId: "exhibit-d-1999-05-27",
    file: "./data/snapshots/exhibit-d@asof-2005-01-12.json",
  },
];

const docList = document.getElementById("docList");
const tocSelect = document.getElementById("tocSelect");
const docTitle = document.getElementById("docTitle");
const docSubtitle = document.getElementById("docSubtitle");
const docAsOf = document.getElementById("docAsOf");
const docBody = document.getElementById("docBody");
const metaPanel = document.getElementById("metaPanel");
const pdfLink = document.getElementById("pdfLink");
const pdfCanvas = document.getElementById("pdfCanvas");
const pdfFallback = document.getElementById("pdfFallback");
const pdfPageLabel = document.getElementById("pdfPageLabel");
const pdfJump = document.getElementById("pdfJump");
const pdfPopout = document.getElementById("pdfPopout");
const breadcrumbText = document.getElementById("breadcrumbText");
const debugPanel = document.getElementById("debugPanel");
const recordingBox = document.getElementById("recordingBox");
const landing = document.getElementById("landing");
const asOfList = document.getElementById("asOfList");
const instrumentIndexList = document.getElementById("instrumentIndexList");
const docHeader = document.querySelector(".doc-header");
const breadcrumbBar = document.querySelector(".breadcrumb-inline");
const findInput = document.getElementById("findInput");
const findPrev = document.getElementById("findPrev");
const findNext = document.getElementById("findNext");
const findCount = document.getElementById("findCount");
const topbar = document.getElementById("topbar");

const pdfModuleUrl = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.4.149/pdf.min.mjs";
const pdfWorkerUrl = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.4.149/pdf.worker.min.mjs";
const pdfDestMapFile = "./data/pdf-dest-map.json";
const instrumentIndexFile = "./data/instruments/index.json";

let documents = [];
let activeDoc = null;
let activeNodeId = null;
let matches = [];
let matchIndex = -1;
let pdfDoc = null;
let currentPdfPage = 1;
let pdfRendering = false;
let pdfPendingPage = null;
let pendingDest = null;
let pdfjsLib = null;
let pdfWorker = null;
let pdfDestinations = null;
let lastDest = null;
let debugLines = [];
let pdfDestMap = {};
let pendingScroll = null;
let lastViewport = null;
let breadcrumbObserver = null;
let instrumentIndex = {};
let instrumentsData = [];
const instrumentContentCache = {};
let pdfWindow = null;
let tocObserver = null;
let pendingPopoutJump = null;

function getInstrumentById(instrumentId) {
  if (!instrumentId) return null;
  return instrumentIndex[instrumentId] || null;
}

function formatCitation(instrument) {
  if (!instrument || !instrument.recording) return "";
  const recording = instrument.recording || {};
  const locationParts = [];
  if (recording.county) locationParts.push(`${recording.county} County`);
  if (recording.state) locationParts.push(recording.state);
  const bookPart = recording.book ? `Record Book ${recording.book}` : "";
  const pagePart = recording.page ? `Page ${recording.page}` : "";
  const bookPage = [bookPart, pagePart].filter(Boolean).join(", ");
  return [locationParts.join(", "), bookPage].filter(Boolean).join(" — ");
}

function extractCitationPart(text, pattern) {
  if (!text) return null;
  const match = text.match(pattern);
  return match ? match[1] : null;
}

function normalizeClauseLabel(label) {
  if (!label) return "";
  const trimmed = label.trim();
  if (!trimmed) return "";
  if (/^\(.+\)$/.test(trimmed)) return trimmed;
  const stripped = trimmed.replace(/[.)]$/, "");
  if (stripped && stripped.length <= 6) return `(${stripped})`;
  return trimmed;
}

function parseExhibitLabel(label) {
  if (!label) return "";
  const match = label.match(/EXHIBIT\\s+\"?([A-Z0-9]+)\"?/i);
  if (match) return `Exhibit ${match[1]}`;
  return label.replace(/\s+/g, " ").trim();
}

function extractClauseLabelFromText(text) {
  if (!text) return "";
  const match = text.trim().match(/^\(([a-z0-9]+)\)/i);
  return match ? `(${match[1]})` : "";
}

function buildCitation(nodeId) {
  if (!activeDoc || !activeDoc.nodeMap) return "";
  const nodes = [];
  let current = nodeId;
  while (current) {
    const node = activeDoc.nodeMap.get(current);
    if (node) nodes.push(node);
    current = activeDoc.parentMap.get(current);
  }

  let articleNum = null;
  let chapterNum = null;
  let sectionNum = null;
  let exhibitLabel = null;
  const listLabels = getListIndexLabels(nodeId);
  const clauseLabels = [];

  nodes.forEach((node) => {
    const text = (node.title || node.label || "").toString();
    if (!articleNum) {
      articleNum = extractCitationPart(text, /ARTICLE\s+([IVXLCDM]+|\d+)/i);
    }
    if (!chapterNum) {
      chapterNum = extractCitationPart(text, /CHAPTER\s+([IVXLCDM]+|\d+)/i);
    }
    if (!sectionNum) {
      sectionNum = extractCitationPart(text, /SECTION\s+([0-9A-Z]+(?:\.[0-9A-Z]+)*)/i);
    }
    if (!sectionNum && node.label) {
      const numericLabel = node.label.trim();
      if (/^\d+(?:\.\d+)*$/.test(numericLabel)) {
        sectionNum = numericLabel;
      } else if (!chapterNum) {
        const chapterMatch = numericLabel.match(/chapter\s*(\d+|[ivxlcdm]+)/i);
        if (chapterMatch) chapterNum = chapterMatch[1];
      }
    }
    if (!exhibitLabel && node.type === "exhibit") {
      exhibitLabel = parseExhibitLabel(node.label || node.title || "");
    }
  });

  nodes
    .slice()
    .reverse()
    .forEach((node) => {
      if (node.type === "list_item") {
        const label = node.label || extractClauseLabelFromText(node.text);
        if (label) clauseLabels.push(normalizeClauseLabel(label));
      } else if (node.type === "paragraph") {
        const label = node.label || extractClauseLabelFromText(node.text);
        if (label) clauseLabels.push(normalizeClauseLabel(label));
      }
    });

  const parts = [];
  if (exhibitLabel) parts.push(exhibitLabel);
  if (articleNum) parts.push(`Article ${articleNum}`);
  if (!articleNum && chapterNum) parts.push(`Chapter ${chapterNum}`);
  if (sectionNum) parts.push(`Section ${sectionNum}`);
  listLabels.forEach((label) => parts.push(label));
  const clauses = clauseLabels.filter(Boolean);
  return [...parts, ...clauses].join(", ");
}

function getListIndexLabels(nodeId) {
  if (!activeDoc || !activeDoc.nodeMap) return [];
  const labels = [];
  let current = nodeId;
  while (current) {
    const parentId = activeDoc.parentMap.get(current);
    if (!parentId) break;
    const parent = activeDoc.nodeMap.get(parentId);
    if (parent && parent.type === "list") {
      const listParentId = activeDoc.parentMap.get(parentId);
      const listParent = listParentId ? activeDoc.nodeMap.get(listParentId) : null;
      if (listParent && Array.isArray(listParent.children)) {
        const listRefs = listParent.children
          .map((child) => (child && child.ref ? activeDoc.nodeMap.get(child.ref) : null))
          .filter((childNode) => childNode && childNode.type === "list");
        if (listRefs.length > 1) {
          const index = listRefs.findIndex((listNode) => listNode.id === parentId);
          if (index >= 0) labels.push(`List ${index + 1}`);
        }
      }
    }
    current = parentId;
  }
  return labels.reverse();
}

function renderMetaPanel(nodeId) {
  if (!activeDoc || !activeDoc.nodeMap) return;
  const node = activeDoc.nodeMap.get(nodeId);
  if (!node) return;
  const meta = node.meta || {};
  const provenance = meta.provenance || {};
  const createdInstrument =
    getInstrumentById(provenance.created_by_instrument_id) ||
    getInstrumentById(provenance.source_ref?.instrument_id);
  const modifiedInstrument = getInstrumentById(provenance.modified_by_instrument_id);
  const citationText = buildCitation(nodeId);
  const notes = collectNotes(nodeId);

  metaPanel.innerHTML = `
    <div><span class="meta-key">Created by:</span> ${createdInstrument?.title || "—"}</div>
    <div><span class="meta-key">Modified by:</span> ${modifiedInstrument?.title || "—"}</div>
    <div><span class="meta-key">Citation:</span> ${citationText || "—"}</div>
    ${notes ? `<div><span class="meta-key">Notes:</span> ${notes}</div>` : ""}
  `;
}

function collectNotes(nodeId) {
  if (!activeDoc || !activeDoc.nodeMap) return "";
  const notes = [];
  let current = nodeId;
  while (current) {
    const node = activeDoc.nodeMap.get(current);
    if (node && node.meta) {
      const note = node.meta.note || node.meta.notes;
      if (note && typeof note === "string") notes.push(note);
    }
    current = activeDoc.parentMap.get(current);
  }
  return notes.join(" ");
}

function hasAmendment(node) {
  if (!node || !node.meta || !node.meta.provenance) return false;
  const provenance = node.meta.provenance;
  return Boolean(provenance.created_by_instrument_id || provenance.modified_by_instrument_id);
}

function clearMetaPanel() {
  metaPanel.innerHTML =
    '<div class="meta-empty">Select a paragraph to view provenance, conflicts, and notes.</div>';
}

function restoreMetaPanel() {
  if (activeNodeId) {
    renderMetaPanel(activeNodeId);
  } else {
    clearMetaPanel();
  }
}

function restorePdfDest(nodeId) {
  if (!activeDoc || !activeNodeId || activeNodeId === nodeId) return;
  const dest = getPdfDest(activeDoc, activeNodeId);
  if (dest) updatePdfDest(dest);
}

function setLoading(isLoading) {
  document.body.classList.toggle("is-loading", isLoading);
}

function parseAsOf(file) {
  const match = file.match(/@asof-(\d{4}-\d{2}-\d{2})/);
  return match ? `As of ${match[1]}` : "";
}

function buildTreeData(snapshot, config) {
  const nodes = snapshot.content.nodes;
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  const parentMap = new Map();
  const instrument = instrumentIndex[config.instrumentId] || null;

  nodes.forEach((node) => {
    if (!node.children) return;
    node.children.forEach((child) => {
      if (child.ref) parentMap.set(child.ref, node.id);
    });
  });

  let headingText = null;
  const root = nodeMap.get(snapshot.content.root_ref);
  if (root && root.children) {
    const headingRef = root.children.find((child) => {
      const childNode = nodeMap.get(child.ref);
      return childNode && childNode.type === "heading";
    });
    if (headingRef) {
      headingText = nodeMap.get(headingRef.ref).text;
    }
  }

  return {
    id: config.id,
    instrumentId: config.instrumentId,
    instrument,
    title: (instrument && instrument.title) || headingText || config.id,
    snapshotTitle: headingText || config.id,
    subtitle: (instrument && instrument.doc_type) || "",
    asOf: parseAsOf(config.file),
    file: config.file,
    nodeMap,
    parentMap,
    rootId: snapshot.content.root_ref,
  };
}

function collectInstrumentIds(doc) {
  const ids = new Set();
  doc.nodeMap.forEach((node) => {
    const meta = node.meta || {};
    if (meta.provenance) {
      const prov = meta.provenance;
      if (prov.created_by_instrument_id) ids.add(prov.created_by_instrument_id);
      if (prov.modified_by_instrument_id) ids.add(prov.modified_by_instrument_id);
      if (prov.source_ref && prov.source_ref.instrument_id) {
        ids.add(prov.source_ref.instrument_id);
      }
    }
    if (meta.exhibit_ref && meta.exhibit_ref.instrument_id) {
      ids.add(meta.exhibit_ref.instrument_id);
    }
  });
  return Array.from(ids);
}

function getPdfDest(doc, nodeId) {
  let currentId = nodeId;
  while (currentId) {
    const node = doc.nodeMap.get(currentId);
    if (node && node.meta) {
      if (node.meta.pdf_dest && node.meta.pdf_dest.name) {
        return node.meta.pdf_dest.name;
      }
      if (
        currentId === nodeId &&
        node.meta.provenance &&
        node.meta.provenance.source_ref &&
        node.meta.provenance.source_ref.pdf_dest &&
        node.meta.provenance.source_ref.pdf_dest.name
      ) {
        return node.meta.provenance.source_ref.pdf_dest.name;
      }
    }
    currentId = doc.parentMap.get(currentId);
  }
  return null;
}

async function loadPdfJs() {
  const module = await import(pdfModuleUrl);
  if (!module) throw new Error("PDF.js module missing");
  pdfjsLib = module;
  try {
    pdfWorker = new Worker(pdfWorkerUrl, { type: "module" });
    pdfjsLib.GlobalWorkerOptions.workerPort = pdfWorker;
  } catch (error) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
  }
}

function initPdf() {
  if (!pdfjsLib) {
    pdfFallback.classList.add("active");
    return;
  }
  pdfjsLib
    .getDocument(pdfFile)
    .promise.then((doc) => {
      pdfDoc = doc;
      pdfFallback.classList.remove("active");
      pdfDoc.getDestinations().then((dests) => {
        pdfDestinations = dests || {};
        logDebug(`destinations loaded: ${Object.keys(pdfDestinations).length}`);
      });
      queueRenderPage(currentPdfPage);
      if (pendingDest) {
        const dest = pendingDest;
        pendingDest = null;
        goToDest(dest);
      }
    })
    .catch(() => {
      pdfFallback.classList.add("active");
    });
}

function getPdfScale(page) {
  const container = pdfCanvas.parentElement;
  const viewport = page.getViewport({ scale: 1 });
  const scale = container.clientWidth / viewport.width;
  return Math.max(scale, 0.5);
}

function renderPdfPage(num) {
  pdfRendering = true;
  pdfDoc.getPage(num).then((page) => {
    const scale = getPdfScale(page);
    const viewport = page.getViewport({ scale });
    lastViewport = viewport;
    const outputScale = window.devicePixelRatio || 1;
    pdfCanvas.width = Math.floor(viewport.width * outputScale);
    pdfCanvas.height = Math.floor(viewport.height * outputScale);
    pdfCanvas.style.width = `${Math.floor(viewport.width)}px`;
    pdfCanvas.style.height = `${Math.floor(viewport.height)}px`;
    const context = pdfCanvas.getContext("2d");
    context.setTransform(outputScale, 0, 0, outputScale, 0, 0);
    const renderContext = { canvasContext: context, viewport };
    return page.render(renderContext).promise.then(() => ({ viewport }));
  }).then(() => {
    if (pendingScroll && pendingScroll.page === num) {
      applyPendingScroll(pendingScroll, pdfCanvas.parentElement, lastViewport);
      pendingScroll = null;
    }
    pdfRendering = false;
    if (pdfPendingPage !== null) {
      const pending = pdfPendingPage;
      pdfPendingPage = null;
      renderPdfPage(pending);
    }
  });
}

function queueRenderPage(num) {
  if (!pdfDoc) return;
  currentPdfPage = num;
  if (pdfRendering) {
    pdfPendingPage = num;
  } else {
    renderPdfPage(num);
  }
}

function applyPendingScroll(target, container, viewport) {
  if (!container || !viewport) return;
  if (target.x === null || target.y === null) {
    container.scrollTop = 0;
    return;
  }
  const point = viewport.convertToViewportPoint(target.x, target.y);
  const targetY = Math.max(point[1] - container.clientHeight * 0.2, 0);
  container.scrollTop = targetY;
}

function sendPdfJump(payload) {
  if (!pdfWindow || pdfWindow.closed) return;
  pendingPopoutJump = payload;
  pdfWindow.postMessage({ type: "pdf-jump", payload }, "*");
}

function goToDest(destName) {
  if (!destName) return;
  if (!pdfDoc) {
    pendingDest = destName;
    return;
  }
  if (destName === lastDest) return;
  lastDest = destName;
  pdfJump.href = `${pdfFile}#nameddest=${destName}`;
  const knownDest = pdfDestinations && pdfDestinations[destName];
  logDebug(`dest lookup: ${destName} ${knownDest ? "cache-hit" : "cache-miss"}`);
  const destPromise = knownDest ? Promise.resolve(knownDest) : pdfDoc.getDestination(destName);
  destPromise.then((dest) => {
    if (!dest || dest.length === 0) {
      logDebug(`dest not found: ${destName}`);
      return;
    }
    const pageRef = dest[0];
    return pdfDoc.getPageIndex(pageRef).then((pageIndex) => {
      const pageNumber = pageIndex + 1;
      logDebug(`dest page: ${destName} -> ${pageNumber}`);
      pdfPageLabel.textContent = `Page ${pageNumber}`;
      sendPdfJump({ page: pageNumber, x: null, y: null });
      queueRenderPage(pageNumber);
    });
  }).catch((error) => {
    logDebug(`dest error: ${destName}`);
    console.error(error);
  });
}

function renderDocList() {
  if (docList) docList.innerHTML = "";
  documents.forEach((doc) => {
    if (docList) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.docId = doc.id;
      button.innerHTML = `<div class="doc-name">${doc.title}</div><div class="doc-note">${doc.asOf}</div>`;
      if (doc.id === activeDoc.id) button.classList.add("active");
      button.addEventListener("click", () => selectDoc(doc.id));
      docList.appendChild(button);
    }
  });
}


function renderNode(doc, nodeId, parentEl, depth, inListItem = false) {
  const node = doc.nodeMap.get(nodeId);
  if (!node) return;

  if (node.type === "heading") {
    return;
  }

  if (node.type === "document") {
    renderChildrenWithContinuation(doc, node.children || [], parentEl, depth);
    return;
  }

  if (node.type === "section") {
    const sectionEl = document.createElement("section");
    sectionEl.className = "section";
    sectionEl.dataset.nodeId = node.id;
    if (node.label) sectionEl.dataset.label = node.label;
    if (node.label || node.title) {
      const h2 = document.createElement("h2");
      const label = node.label ? `${node.label} ` : "";
      h2.textContent = `${label}${node.title || ""}`.trim();
      sectionEl.appendChild(h2);
    }
    parentEl.appendChild(sectionEl);
    renderChildrenWithContinuation(doc, node.children || [], sectionEl, depth + 1);
    return;
  }

  if (node.type === "subsection") {
    const subEl = document.createElement("div");
    subEl.className = "subsection";
    subEl.dataset.nodeId = node.id;
    if (node.label) subEl.dataset.label = node.label;
    if (node.label || node.title) {
      const h3 = document.createElement("h3");
      const label = node.label ? `${node.label} ` : "";
      h3.textContent = `${label}${node.title || ""}`.trim();
      subEl.appendChild(h3);
    }
    parentEl.appendChild(subEl);
    renderChildrenWithContinuation(doc, node.children || [], subEl, depth + 1);
    return;
  }

  if (node.type === "paragraph") {
    const p = document.createElement("p");
    p.className = `para node-block${inListItem ? " nested" : ""}`;
    p.dataset.nodeId = node.id;
    if (collectNotes(node.id)) p.classList.add("has-note");
    if (hasAmendment(node)) p.classList.add("has-amendment");
    const span = document.createElement("span");
    span.className = "text-node";
    span.dataset.nodeId = node.id;
    span.dataset.text = node.text || "";
    span.dataset.pdfDest = getPdfDest(doc, node.id) || "";
    span.textContent = node.text || "";
    span.addEventListener("mouseenter", () => {
      renderMetaPanel(span.dataset.nodeId);
      if (span.dataset.pdfDest) updatePdfDest(span.dataset.pdfDest);
    });
    span.addEventListener("click", (event) => {
      event.stopPropagation();
      selectNode(span.dataset.nodeId, p);
    });
    p.addEventListener("click", (event) => {
      event.stopPropagation();
      selectNode(span.dataset.nodeId, p);
    });
    p.appendChild(span);
    parentEl.appendChild(p);
    return;
  }

  if (node.type === "list") {
    const listEl = document.createElement("ul");
    listEl.className = "node-list";
    listEl.dataset.nodeId = node.id;
    parentEl.appendChild(listEl);
    (node.children || []).forEach((child) => {
      if (child.ref) renderNode(doc, child.ref, listEl, depth + 1, inListItem);
    });
    return;
  }

  if (node.type === "list_item") {
    const li = document.createElement("li");
    li.className = "node-block";
    li.dataset.nodeId = node.id;
    if (collectNotes(node.id)) li.classList.add("has-note");
    if (hasAmendment(node)) li.classList.add("has-amendment");
    const label = node.label || "";
    const title = node.title || "";
    const text = node.text || "";
    const span = document.createElement("span");
    span.className = "text-node";
    span.dataset.nodeId = node.id;
    span.dataset.label = label;
    span.dataset.title = title;
    span.dataset.rawText = text;
    span.dataset.text = `${label} ${title} ${text}`.trim();
    span.dataset.pdfDest = getPdfDest(doc, node.id) || "";
    span.innerHTML = buildListItemMarkup(label, title, text);
    span.addEventListener("mouseenter", () => {
      renderMetaPanel(span.dataset.nodeId);
      if (span.dataset.pdfDest) updatePdfDest(span.dataset.pdfDest);
    });
    span.addEventListener("click", (event) => {
      event.stopPropagation();
      selectNode(span.dataset.nodeId, li);
    });
    li.appendChild(span);
    if (node.label) li.classList.add("has-label");
    if (!node.label) li.classList.add("no-label");
    if (label) li.dataset.label = label;
    if (node.children && node.children.length) {
      node.children.forEach((child) => {
        if (child.ref) renderNode(doc, child.ref, li, depth + 1, true);
      });
    }
    parentEl.appendChild(li);
    return;
  }

  if (node.type === "table") {
    const tableWrap = document.createElement("div");
    tableWrap.className = "table-wrap";
    const table = document.createElement("table");
    table.className = "data-table";
    table.dataset.nodeId = node.id;

    const columns = node.columns || [];
    const rows = node.rows || [];
    const columnCount = columns.length || Math.max(0, ...rows.map((row) => row.length));
    if (columns.length) {
      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      columns.forEach((col) => {
        const th = document.createElement("th");
        th.textContent = col;
        headerRow.appendChild(th);
      });
      thead.appendChild(headerRow);
      table.appendChild(thead);
    }

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      const isTitleRow =
        row.length > 1 && row[0] && row.slice(1).every((cell) => !String(cell || "").trim());
      if (isTitleRow) {
        const th = document.createElement("th");
        th.className = "table-title";
        th.colSpan = Math.max(columnCount, 1);
        th.textContent = row[0];
        tr.appendChild(th);
      } else {
        const paddedRow = row.slice();
        while (paddedRow.length < columnCount) paddedRow.push("");
        paddedRow.forEach((cell) => {
          const td = document.createElement("td");
          td.className = "node-block";
          if (collectNotes(node.id)) td.classList.add("has-note");
          if (hasAmendment(node)) td.classList.add("has-amendment");
          const span = document.createElement("span");
          span.className = "text-node";
          span.dataset.nodeId = node.id;
          span.dataset.text = cell;
          span.dataset.pdfDest = getPdfDest(doc, node.id) || "";
          span.textContent = cell;
        span.addEventListener("mouseenter", () => {
          renderMetaPanel(span.dataset.nodeId);
          if (span.dataset.pdfDest) updatePdfDest(span.dataset.pdfDest);
        });
          span.addEventListener("click", (event) => {
            event.stopPropagation();
            selectNode(span.dataset.nodeId, td);
          });
          td.appendChild(span);
          tr.appendChild(td);
        });
      }
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    parentEl.appendChild(tableWrap);
    return;
  }

  if (node.type === "exhibit") {
    const exhibit = document.createElement("div");
    exhibit.className = "exhibit-block";
    const label = node.label || "Exhibit";
    const title = node.title ? ` — ${node.title}` : "";
    const exhibitRef = node.meta && node.meta.exhibit_ref;
    if (exhibitRef && exhibitRef.instrument_id) {
      const refDoc = documents.find((doc) => doc.instrumentId === exhibitRef.instrument_id);
      if (refDoc) {
        const link = document.createElement("button");
        link.type = "button";
        link.className = "exhibit-link";
        link.textContent = `${label}${title}`;
        link.addEventListener("click", () => selectDoc(refDoc.id));
        exhibit.appendChild(link);
      } else {
        exhibit.textContent = `${label}${title}`;
      }
    } else {
      exhibit.textContent = `${label}${title}`;
    }
    parentEl.appendChild(exhibit);
    if (node.children && node.children.length) {
      node.children.forEach((child) => {
        if (child.ref) renderNode(doc, child.ref, exhibit, depth + 1);
      });
    }
    return;
  }
}

function renderDoc() {
  document.body.classList.remove("landing-page");
  if (landing) landing.classList.add("is-hidden");
  if (docHeader) docHeader.classList.remove("is-hidden");
  if (recordingBox) recordingBox.classList.remove("is-hidden");
  if (docBody) docBody.classList.remove("is-hidden");
  docTitle.textContent = activeDoc.instrument?.title || activeDoc.title;
  docSubtitle.textContent = activeDoc.instrument?.doc_type || activeDoc.subtitle || "";
  docAsOf.textContent = activeDoc.asOf || "";
  pdfLink.href = `${pdfFile}#page=1`;
  pdfPageLabel.textContent = "Page 1";
  pdfJump.href = `${pdfFile}#page=1`;
  docBody.innerHTML = "";

  if (activeDoc.nodeMap && activeDoc.rootId) {
    renderNode(activeDoc, activeDoc.rootId, docBody, 0);
  } else {
    const placeholder = document.createElement("section");
    placeholder.className = "section";
    placeholder.textContent = "Text not available in corpus for this instrument.";
    docBody.appendChild(placeholder);
  }

  renderRecordingBox();
  updateStickyOffsets();
  setupBreadcrumbs();
  setupTocSelectSync();
  resetFind();
  renderTocSelect(buildTocTree(activeDoc));
}

function renderLanding() {
  if (!landing || !asOfList || !instrumentIndexList) return;
  document.body.classList.add("landing-page");
  landing.classList.remove("is-hidden");
  if (docHeader) docHeader.classList.add("is-hidden");
  if (recordingBox) recordingBox.classList.add("is-hidden");
  if (docBody) docBody.classList.add("is-hidden");
  asOfList.innerHTML = "";
  documents.forEach((doc) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "landing-link";
    const title = doc.instrument?.title || "Untitled instrument";
    button.innerHTML = `
      ${title}
      <span>${doc.asOf}</span>
    `;
    button.addEventListener("click", () => selectDoc(doc.id));
    asOfList.appendChild(button);
  });
  const primaryButton = document.getElementById("landingPrimary");
  if (primaryButton) {
    const firstDoc = documents[0];
    primaryButton.onclick = () => selectDoc(firstDoc.id);
  }

  instrumentIndexList.innerHTML = "";
  if (!instrumentsData.length) {
    instrumentIndexList.textContent = "Instrument list unavailable in this view.";
    return;
  }
  instrumentsData.forEach((inst) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "landing-link";
    button.innerHTML = `
      ${inst.title}
      <span>${inst.recorded_at || "Unknown"}</span>
    `;
    button.addEventListener("click", () => selectInstrument(inst.id));
    instrumentIndexList.appendChild(button);
  });
}

function selectDoc(docId, options = {}) {
  const { push = true } = options;
  const next = documents.find((doc) => doc.id === docId);
  if (!next) return;
  activeDoc = next;
  activeNodeId = null;
  renderDocList();
  if (landing) landing.classList.add("is-hidden");
  renderDoc();
  clearMetaPanel();
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (push) {
    const url = new URL(window.location.href);
    url.hash = `#/doc?id=${encodeURIComponent(docId)}`;
    history.pushState({ docId }, "", url.toString());
  }
}

function selectInstrument(instrumentId, options = {}) {
  const { push = true } = options;
  if (!instrumentId) return;
  return loadInstrumentDoc(instrumentId).then((doc) => {
    if (!doc) return;
    activeDoc = doc;
    activeNodeId = null;
    renderDocList();
    if (landing) landing.classList.add("is-hidden");
    renderDoc();
    clearMetaPanel();
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (push) {
      const url = new URL(window.location.href);
      url.hash = `#/instrument?id=${encodeURIComponent(instrumentId)}`;
      history.pushState({ instrumentId }, "", url.toString());
    }
  });
}

async function handleRoute() {
  const url = new URL(window.location.href);
  if (url.hash.startsWith("#/instrument")) {
    const hashParams = new URLSearchParams(url.hash.replace(/^#\/instrument\??/, ""));
    const instrumentId = hashParams.get("id");
    if (instrumentId) {
      await selectInstrument(instrumentId, { push: false });
      return;
    }
  }
  if (url.hash.startsWith("#/doc")) {
    const hashParams = new URLSearchParams(url.hash.replace(/^#\/doc\??/, ""));
    const docId = hashParams.get("id");
    if (docId) {
      selectDoc(docId, { push: false });
      return;
    }
    activeDoc = documents[0] || null;
    if (activeDoc) renderDoc();
    return;
  }
  activeDoc = null;
  renderLanding();
}

function selectNode(nodeId, element) {
  if (activeNodeId) {
    const prev = document.querySelector(`.node-block.active`);
    if (prev) prev.classList.remove("active");
  }
  activeNodeId = nodeId;
  element.classList.add("active");

  const pdfDest = getPdfDest(activeDoc, nodeId);
  updatePdfDest(pdfDest);
  renderMetaPanel(nodeId);
}

function updatePdfDest(dest) {
  if (!dest) return;
  const normalized = dest.startsWith("/") ? dest : `/${dest}`;
  logDebug(`scroll dest: ${normalized}`);
  const mapped = pdfDestMap[normalized] || pdfDestMap[normalized.replace(/^\//, "")];
  if (mapped && mapped.page) {
    logDebug(`map hit: ${normalized} -> ${mapped.page}`);
    pdfPageLabel.textContent = `Page ${mapped.page}`;
    pdfJump.href = `${pdfFile}#page=${mapped.page}`;
    pendingScroll = {
      page: mapped.page,
      x: mapped.x ?? null,
      y: mapped.y ?? null,
    };
    queueRenderPage(mapped.page);
    sendPdfJump({
      page: mapped.page,
      x: mapped.x ?? null,
      y: mapped.y ?? null,
    });
    return;
  }
  goToDest(normalized);
}

function setupBreadcrumbs() {
  if (!breadcrumbText) return;
  if (breadcrumbObserver) breadcrumbObserver.disconnect();
  const blocks = Array.from(document.querySelectorAll(".text-node"));
  const updateForNode = (node) => {
    const section = node.closest(".section");
    const subsection = node.closest(".subsection");
    const parts = [];
    if (section) {
      const sectionLabel =
        section.dataset.label ||
        extractHeadingLabel(section.querySelector("h2")?.textContent || "");
      const sectionTitle = section.querySelector("h2")?.textContent || "";
      const sectionText = sectionLabel
        ? `${sectionLabel} ${sectionTitle.replace(sectionLabel, "").trim()}`.trim()
        : sectionTitle.trim();
      if (sectionText) parts.push(sectionText);
    }
    if (subsection) {
      const subsectionLabel =
        subsection.dataset.label ||
        extractHeadingLabel(subsection.querySelector("h3")?.textContent || "");
      const subsectionTitle = subsection.querySelector("h3")?.textContent || "";
      const subsectionText = subsectionLabel
        ? `${subsectionLabel} ${subsectionTitle.replace(subsectionLabel, "").trim()}`.trim()
        : subsectionTitle.trim();
      if (subsectionText) parts.push(subsectionText);
    }
    const value = parts.length ? parts.join(" / ") : activeDoc.title;
    breadcrumbText.textContent = value;
  };

  breadcrumbObserver = new IntersectionObserver(
    (entries) => {
      let topEntry = null;
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          if (!topEntry || entry.boundingClientRect.top < topEntry.boundingClientRect.top) {
            topEntry = entry;
          }
        }
      });
      if (topEntry) updateForNode(topEntry.target);
    },
    { rootMargin: "-30% 0px -60% 0px", threshold: 0.1 }
  );

  blocks.forEach((block) => breadcrumbObserver.observe(block));
  if (blocks[0]) updateForNode(blocks[0]);
}

function extractHeadingLabel(text) {
  if (!text) return "";
  const match = text.match(/^(ARTICLE|SECTION)\\s+([IVXLCDM]+|\\d+)\\b/i);
  if (match) return `${match[1].toUpperCase()} ${match[2].toUpperCase()}`;
  return text.split(".")[0].trim();
}

function setupTocSelectSync() {
  if (!tocSelect) return;
  if (tocObserver) tocObserver.disconnect();
  const blocks = Array.from(document.querySelectorAll(".text-node"));
  const updateSelectForNode = (node) => {
    const section = node.closest(".section");
    const subsection = node.closest(".subsection");
    const targetId = subsection ? subsection.dataset.nodeId : section?.dataset.nodeId;
    if (targetId) tocSelect.value = targetId;
  };
  tocObserver = new IntersectionObserver(
    (entries) => {
      let topEntry = null;
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          if (!topEntry || entry.boundingClientRect.top < topEntry.boundingClientRect.top) {
            topEntry = entry;
          }
        }
      });
      if (topEntry) updateSelectForNode(topEntry.target);
    },
    { rootMargin: "-30% 0px -60% 0px", threshold: 0.1 }
  );
  blocks.forEach((block) => tocObserver.observe(block));
  if (blocks[0]) updateSelectForNode(blocks[0]);
}

function logDebug(line) {
  if (!debugPanel) return;
  debugLines.push(line);
  if (debugLines.length > 6) debugLines.shift();
  debugPanel.textContent = debugLines.join("\n");
}

function renderRecordingBox() {
  if (!recordingBox) return;
  const inst = activeDoc.instrument;
  if (!inst) {
    recordingBox.innerHTML = "";
    return;
  }
  const recording = inst.recording || {};
  recordingBox.innerHTML = `
    <div class="recording-row">
      <span class="recording-label">Instrument</span>
      <span class="recording-value">${inst.doc_type || inst.instrument_kind || ""}</span>
    </div>
    <div class="recording-row">
      <span class="recording-label">Effective</span>
      <span class="recording-value">${inst.effective_at || "Unknown"}</span>
    </div>
    <div class="recording-row">
      <span class="recording-label">Recorded</span>
      <span class="recording-value">${inst.recorded_at || "Unknown"}</span>
    </div>
    <div class="recording-row">
      <span class="recording-label">Book / Page</span>
      <span class="recording-value">${recording.book || "?"} / ${recording.page || "?"}</span>
    </div>
  `;
}

function updateStickyOffsets() {
  if (!topbar) return;
  const offset = topbar.offsetHeight + 24;
  document.documentElement.style.setProperty("--topbar-offset", `${offset}px`);
}


function resetFind() {
  matches = [];
  matchIndex = -1;
  findCount.textContent = "0";
  findInput.value = "";
  document.querySelectorAll(".text-node").forEach((node) => {
    if (node.dataset.label) {
      node.innerHTML = buildListItemMarkup(
        node.dataset.label,
        node.dataset.title || "",
        node.dataset.rawText || ""
      );
    } else {
      node.innerHTML = node.dataset.text || "";
    }
  });
}

function runFind() {
  const query = findInput.value.trim();
  matches = [];
  matchIndex = -1;

  document.querySelectorAll(".text-node").forEach((node) => {
    const text = node.dataset.text || "";
    if (!query) {
      if (node.dataset.label) {
        node.innerHTML = buildListItemMarkup(
          node.dataset.label,
          node.dataset.title || "",
          node.dataset.rawText || ""
        );
      } else {
        node.innerHTML = text;
      }
      return;
    }
    const regex = new RegExp(`(${escapeRegex(query)})`, "ig");
    if (regex.test(text)) {
      node.innerHTML = text.replace(regex, "<mark>$1</mark>");
      matches.push(node);
    } else {
      node.innerHTML = text;
    }
  });

  findCount.textContent = matches.length.toString();
  if (matches.length > 0) {
    matchIndex = 0;
    focusMatch();
  }
}

function focusMatch() {
  const active = document.querySelector(".node-block.active");
  if (active) active.classList.remove("active");
  const target = matches[matchIndex];
  if (!target) return;
  const wrapper = target.closest(".node-block") || target;
  wrapper.classList.add("active");
  wrapper.scrollIntoView({ behavior: "smooth", block: "center" });
  updatePdfDest(target.dataset.pdfDest || "");
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildListItemMarkup(label, title, text) {
  const safeLabel = label ? `<strong class="list-label">${escapeHtml(label)}</strong>` : "";
  const safeTitle = title ? `<strong class="list-title">${escapeHtml(title)}</strong>` : "";
  const safeText = escapeHtml(text);
  let bodyMarkup = safeText;
  if (!safeTitle && safeText) {
    const colonIndex = safeText.indexOf(":");
    if (colonIndex > 0 && colonIndex < 60) {
      bodyMarkup = `<strong class="list-title">${safeText.slice(0, colonIndex + 1)}</strong>${safeText.slice(colonIndex + 1)}`;
    }
  }
  return [safeLabel, safeTitle, bodyMarkup].filter(Boolean).join(" ").trim();
}

function buildTocTree(doc) {
  const items = [];
  const walk = (nodeId) => {
    const node = doc.nodeMap.get(nodeId);
    if (!node) return;
    if (node.type === "section") {
      const sectionTitle = [node.label, node.title].filter(Boolean).join(" ").trim();
      const section = { id: node.id, title: sectionTitle || node.id, children: [] };
      (node.children || []).forEach((child) => {
        if (!child.ref) return;
        const childNode = doc.nodeMap.get(child.ref);
        if (childNode && childNode.type === "subsection") {
          const childTitle = [childNode.label, childNode.title].filter(Boolean).join(" ").trim();
          if (childTitle) {
            section.children.push({ id: childNode.id, title: childTitle });
          }
        }
      });
      items.push(section);
    }
    (node.children || []).forEach((child) => {
      if (child.ref) walk(child.ref);
    });
  };
  walk(doc.rootId);
  return items;
}

function isLetteredParagraph(text) {
  if (!text) return false;
  return /^\([a-z]\)/i.test(text.trim());
}

function buildDocFromContent(content, instrument, options = {}) {
  if (!content || !content.nodes) return null;
  const nodeMap = new Map(content.nodes.map((node) => [node.id, node]));
  const parentMap = new Map();
  content.nodes.forEach((node) => {
    if (!node.children) return;
    node.children.forEach((child) => {
      if (child.ref) parentMap.set(child.ref, node.id);
    });
  });
  return {
    id: options.id || instrument?.id || "instrument",
    instrument,
    title: instrument?.title || options.title || "Instrument",
    subtitle: instrument?.doc_type || options.subtitle || "",
    asOf: instrument?.recorded_at ? `Recorded ${instrument.recorded_at}` : "",
    nodeMap,
    parentMap,
    rootId: content.root_ref,
  };
}

function loadInstrumentDoc(instrumentId) {
  if (instrumentContentCache[instrumentId]) {
    return Promise.resolve(instrumentContentCache[instrumentId]);
  }
  return fetch(`./data/instruments/${instrumentId}.json`)
    .then((response) => response.json())
    .then((data) => {
      const instrument = data.instrument || instrumentIndex[instrumentId];
      const doc = buildDocFromContent(data.content, instrument, { id: instrumentId });
      if (!doc) {
        return { id: instrumentId, instrument, title: instrument?.title || instrumentId };
      }
      instrumentContentCache[instrumentId] = doc;
      return doc;
    })
    .catch(() => null);
}

function scrollToNode(nodeId) {
  const target = document.querySelector(`[data-node-id="${nodeId}"]`);
  if (!target) return;
  const rootStyles = getComputedStyle(document.documentElement);
  const offset = parseFloat(rootStyles.getPropertyValue("--topbar-offset")) || 0;
  const top = target.getBoundingClientRect().top + window.scrollY - offset - 56;
  window.scrollTo({ top, behavior: "smooth" });
}

function renderTocSelect(items) {
  if (!tocSelect) return;
  tocSelect.innerHTML = "";
  const flat = [];
  items.forEach((section) => {
    flat.push({ id: section.id, title: abbreviateTocTitle(section.title) });
    section.children.forEach((child) => {
      flat.push({ id: child.id, title: `\u2014 ${abbreviateTocTitle(child.title)}` });
    });
  });
  flat.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.title;
    tocSelect.appendChild(option);
  });
}

function abbreviateTocTitle(title) {
  if (!title) return "";
  const match = title.match(/^(ARTICLE|SECTION)\\s+([IVXLCDM]+|\\d+\\.?)/i);
  if (match) {
    const label = match[1].toUpperCase() === "ARTICLE" ? "ART." : "SEC.";
    return `${label} ${match[2]}`;
  }
  const fallback = title.split(" ").slice(0, 2).join(" ");
  return fallback || title;
}

function getLastListItemElement(element) {
  if (!element || !element.classList) return null;
  if (!element.classList.contains("node-list")) return null;
  return element.lastElementChild || null;
}

function renderChildrenWithContinuation(doc, children, parentEl, depth) {
  let continuationListItemEl = null;
  let lastListItemEl = null;
  for (let i = 0; i < children.length; i += 1) {
    const child = children[i];
    if (!child.ref) continue;
    const childNode = doc.nodeMap.get(child.ref);
    const nextChild = children[i + 1];
    const nextNode = nextChild && nextChild.ref ? doc.nodeMap.get(nextChild.ref) : null;
    if (childNode && childNode.type === "paragraph" && isLetteredParagraph(childNode.text)) {
      const lastListItemEl =
        continuationListItemEl || getLastListItemElement(parentEl.lastElementChild);
      if (lastListItemEl) {
        renderNode(doc, child.ref, lastListItemEl, depth + 1, true);
        continuationListItemEl = lastListItemEl;
        continue;
      }
    }
    if (
      childNode &&
      childNode.type === "paragraph" &&
      !isLetteredParagraph(childNode.text) &&
      nextNode &&
      nextNode.type === "paragraph" &&
      isLetteredParagraph(nextNode.text) &&
      lastListItemEl
    ) {
      renderNode(doc, child.ref, lastListItemEl, depth + 1, true);
      continuationListItemEl = lastListItemEl;
      continue;
    }
    continuationListItemEl = null;
    renderNode(doc, child.ref, parentEl, depth + 1);
    const lastListItem = getLastListItemElement(parentEl.lastElementChild);
    if (lastListItem) {
      lastListItemEl = lastListItem;
    } else {
      lastListItemEl = null;
    }
  }
}

findInput.addEventListener("input", () => runFind());
findPrev.addEventListener("click", () => {
  if (matches.length === 0) return;
  matchIndex = (matchIndex - 1 + matches.length) % matches.length;
  focusMatch();
});
findNext.addEventListener("click", () => {
  if (matches.length === 0) return;
  matchIndex = (matchIndex + 1) % matches.length;
  focusMatch();
});

function loadSnapshots() {
  return Promise.all(
    snapshotConfigs.map((config) =>
      fetch(config.file)
        .then((response) => response.json())
        .then((snapshot) => buildTreeData(snapshot, config))
    )
  );
}

function loadInstrumentList() {
  return fetch(instrumentIndexFile)
    .then((response) => (response.ok ? response.json() : {}))
    .then((index) => Object.values(index))
    .catch(() => []);
}

async function initApp() {
  setLoading(true);
  try {
    instrumentIndex = await fetch(instrumentIndexFile)
      .then((response) => (response.ok ? response.json() : {}))
      .catch(() => ({}));
    instrumentsData = Object.values(instrumentIndex);
    documents = await loadSnapshots();
    renderDocList();
    await handleRoute();
    setLoading(false);
  } catch (error) {
    docBody.innerHTML = `<div class="section">Failed to load snapshots. ${error}</div>`;
    pdfFallback.classList.add("active");
    setLoading(false);
    return;
  }

  try {
    fetch(pdfDestMapFile)
      .then((response) => (response.ok ? response.json() : {}))
      .then((map) => {
        pdfDestMap = map || {};
        logDebug(`map loaded: ${Object.keys(pdfDestMap).length}`);
      })
      .catch(() => {});
    await loadPdfJs();
    initPdf();
  } catch (error) {
    pdfFallback.classList.add("active");
  }
}

initApp();

// Sync TOC dropdown on mobile.
if (tocSelect) {
  tocSelect.addEventListener("change", (event) => scrollToNode(event.target.value));
}
if (pdfPopout) {
  pdfPopout.addEventListener("click", () => {
    const width = Math.min(window.screen.width * 0.7, 1100);
    const height = Math.min(window.screen.height * 0.8, 900);
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    const url = `./pdf-popout.html?file=${encodeURIComponent(pdfFile)}`;
    pdfWindow = window.open(
      url,
      "hoaPdf",
      `width=${Math.floor(width)},height=${Math.floor(height)},left=${Math.floor(left)},top=${Math.floor(top)}`
    );
    if (pdfWindow) {
      pdfWindow.focus();
      sendPdfJump({ page: currentPdfPage, x: null, y: null });
    }
  });
}
window.addEventListener("message", (event) => {
  if (!pdfWindow || pdfWindow.closed) return;
  if (event.source !== pdfWindow) return;
  if (event.data && event.data.type === "pdf-popout-ready") {
    if (pendingPopoutJump) {
      sendPdfJump(pendingPopoutJump);
    }
  }
});
window.addEventListener("hashchange", () => {
  handleRoute();
});
window.addEventListener("resize", () => {
  if (pdfDoc) queueRenderPage(currentPdfPage);
  updateStickyOffsets();
});
