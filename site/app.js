(() => {
  const docs = (window.HOADocs || []).slice();

  const indexView = document.getElementById("index-view");
  const docView = document.getElementById("doc-view");
  const listEl = document.getElementById("doc-list");
  const featuredListEl = document.getElementById("featured-list");
  const featuredPanel = document.getElementById("featured-panel");
  const listSearchEl = document.getElementById("list-search");
  const backButton = document.getElementById("back-button");
  const docTitleEl = document.getElementById("doc-title");
  const docDateEl = document.getElementById("doc-date");
  const docDescEl = document.getElementById("doc-description");
  const docPdfEl = document.getElementById("doc-pdf");
  const docContentEl = document.getElementById("doc-content");
  const annotationsEl = document.getElementById("annotations");
  const docSearchEl = document.getElementById("doc-search");
  const docNextEl = document.getElementById("doc-next");
  const docPrevEl = document.getElementById("doc-prev");
  const docMatchCountEl = document.getElementById("doc-match-count");
  const docToolbar = document.getElementById("doc-toolbar");
  const scrollTopBtn = document.getElementById("scroll-top");

  let currentDoc = null;
  let renderedHtml = "";
  let baseContentHtml = "";
  let matchSpans = [];
  let currentMatchIndex = -1;

  const slugify = (text) =>
    text
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-");

  const formatDate = (dateStr) =>
    new Date(dateStr + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  const scrollToSlug = (slug) => {
    const el = document.getElementById(slug);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const highlight = (query) => {
    if (!baseContentHtml) return;
    docContentEl.innerHTML = baseContentHtml;
    matchSpans = [];
    currentMatchIndex = -1;
    if (!query) {
      docMatchCountEl.textContent = "0 / 0";
      return;
    }

    const regex = new RegExp(escapeRegExp(query), "gi");
    const walker = document.createTreeWalker(docContentEl, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    while (walker.nextNode()) {
      nodes.push(walker.currentNode);
    }
    nodes.forEach((node) => {
      const text = node.nodeValue;
      let match;
      let lastIndex = 0;
      const frag = document.createDocumentFragment();
      let found = false;
      while ((match = regex.exec(text)) !== null) {
        found = true;
        const before = text.slice(lastIndex, match.index);
        if (before) frag.appendChild(document.createTextNode(before));
        const mark = document.createElement("mark");
        mark.className = "match";
        mark.textContent = match[0];
        frag.appendChild(mark);
        lastIndex = regex.lastIndex;
      }
      if (found) {
        const after = text.slice(lastIndex);
        if (after) frag.appendChild(document.createTextNode(after));
        node.parentNode.replaceChild(frag, node);
      }
    });

    matchSpans = Array.from(docContentEl.querySelectorAll("mark.match"));
    if (matchSpans.length) {
      currentMatchIndex = 0;
      scrollToMatch(currentMatchIndex);
      docMatchCountEl.textContent = `${currentMatchIndex + 1} / ${matchSpans.length}`;
    } else {
      docMatchCountEl.textContent = "0 / 0";
    }
  };

  const scrollToMatch = (index) => {
    const target = matchSpans[index];
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    matchSpans.forEach((m) => m.classList.remove("active-match"));
    target.classList.add("active-match");
    docMatchCountEl.textContent = `${index + 1} / ${matchSpans.length}`;
  };

  const renderAnnotations = (doc, headingMap) => {
    annotationsEl.innerHTML = "";
    if (!doc.annotations || doc.annotations.length === 0) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "No annotations provided for this filing yet.";
      annotationsEl.appendChild(empty);
      return;
    }
    doc.annotations.forEach((item) => {
      const block = document.createElement("div");
      block.className = "annotation";
      const title = document.createElement("h4");
      title.textContent = item.label;
      const body = document.createElement("p");
      body.textContent = item.text;
      if (item.section) {
        const slug = slugify(item.section);
        if (headingMap[slug]) {
          const link = document.createElement("a");
          link.href = `#${slug}`;
          link.textContent = item.section;
          link.className = "pill ghost";
          link.dataset.target = slug;
          body.prepend(link);
          const spacer = document.createTextNode(" ");
          body.insertBefore(spacer, link.nextSibling);
        }
      }
      block.append(title, body);
      annotationsEl.appendChild(block);
    });
  };

  const addHeadingAnchors = () => {
    const headings = Array.from(docContentEl.querySelectorAll("h1,h2,h3,h4,h5,h6"));
    const map = {};
    headings.forEach((h) => {
      const slug = h.id || slugify(h.textContent);
      h.id = slug;
      map[slug] = h;
    });
    return map;
  };

  const injectInlineAnnotations = (doc, headingMap) => {
    if (!doc.annotations) return;
    doc.annotations.forEach((item) => {
      if (!item.section) return;
      const slug = slugify(item.section);
      const target = headingMap[slug];
      if (!target) return;
      const box = document.createElement("div");
      box.className = "inline-annotation";
      const title = document.createElement("div");
      title.className = "inline-annotation__title";
      title.textContent = item.label;
      const body = document.createElement("p");
      body.textContent = item.inlineDetail || item.text;
      box.append(title, body);
      target.insertAdjacentElement("afterend", box);
    });
  };

  const setView = (showDoc) => {
    if (showDoc) {
      indexView.classList.add("hidden");
      docView.classList.remove("hidden");
      backButton.classList.remove("hidden");
      docToolbar.classList.remove("hidden");
    } else {
      indexView.classList.remove("hidden");
      docView.classList.add("hidden");
      backButton.classList.add("hidden");
      docToolbar.classList.add("hidden");
      document.title = "Winston Hills HOA Documents";
    }
  };

  const openDoc = async (slug, skipPush = false) => {
    const doc = docs.find((d) => d.slug === slug);
    if (!doc) return;
    currentDoc = doc;
    docTitleEl.textContent = doc.title;
    docDateEl.textContent = formatDate(doc.date);
    docDescEl.textContent = doc.description;
    docPdfEl.href = doc.pdfPath;
    docPdfEl.textContent = "Open PDF";
    docSearchEl.value = "";
    docContentEl.innerHTML = "Loading…";
    setView(true);
    document.title = `${doc.title} | Winston Hills HOA`;

    try {
      const res = await fetch(doc.mdPath);
      const text = await res.text();
      const html = marked.parse(text);
      docContentEl.innerHTML = html;
      const headingMap = addHeadingAnchors();
      injectInlineAnnotations(doc, headingMap);
      renderAnnotations(doc, headingMap);
      annotationsEl.querySelectorAll("a[data-target]").forEach((anchor) => {
        anchor.addEventListener("click", (e) => {
          e.preventDefault();
          scrollToSlug(anchor.dataset.target);
        });
      });
      renderedHtml = docContentEl.innerHTML;
      baseContentHtml = docContentEl.innerHTML;
      highlight(docSearchEl.value.trim());
    } catch (err) {
      docContentEl.innerHTML = `<p class="hint">Unable to load document.</p>`;
      console.error(err);
    }

    if (!skipPush) {
      history.pushState({ doc: slug }, "", `?doc=${encodeURIComponent(slug)}`);
    }
  };

  const renderList = (query = "") => {
    listEl.innerHTML = "";
    featuredListEl.innerHTML = "";
    const normalized = query.trim().toLowerCase();
    const filtered = normalized
      ? docs.filter(
          (doc) =>
            doc.title.toLowerCase().includes(normalized) ||
            doc.description.toLowerCase().includes(normalized)
        )
      : docs;

    const featured = filtered.filter((d) => d.featured);
    const others = filtered.filter((d) => !d.featured).sort((a, b) => new Date(a.date) - new Date(b.date));

    if (featured.length) {
      featuredPanel.classList.remove("hidden");
    } else {
      featuredPanel.classList.add("hidden");
    }

    const renderCard = (doc, container) => {
      const card = document.createElement("article");
      card.className = "doc-card";
      if (doc.featured) {
        card.classList.add("featured");
      }
      card.addEventListener("click", () => openDoc(doc.slug));

      const eyebrow = document.createElement("p");
      eyebrow.className = "eyebrow";
      eyebrow.textContent = formatDate(doc.date);

      const title = document.createElement("h3");
      title.textContent = doc.title;

      const desc = document.createElement("p");
      desc.textContent = doc.description;

      const pills = document.createElement("div");
      pills.className = "doc-links";
      const pdf = document.createElement("span");
      pdf.className = "pill";
      pdf.textContent = "PDF";
      pills.append(pdf);

      card.append(eyebrow, title, desc, pills);
      container.appendChild(card);
    };

    featured.forEach((doc) => renderCard(doc, featuredListEl));
    others.forEach((doc) => renderCard(doc, listEl));
  };

  const resetToIndex = (skipPush = false) => {
    currentDoc = null;
    setView(false);
    if (!skipPush) {
      history.pushState({}, "", "?");
    }
  };

  listSearchEl.addEventListener("input", (e) => renderList(e.target.value));
  backButton.addEventListener("click", () => resetToIndex());
  docSearchEl.addEventListener("input", (e) => highlight(e.target.value.trim()));
  docNextEl.addEventListener("click", () => {
    if (!matchSpans.length) return;
    currentMatchIndex = (currentMatchIndex + 1) % matchSpans.length;
    scrollToMatch(currentMatchIndex);
  });
  docPrevEl.addEventListener("click", () => {
    if (!matchSpans.length) return;
    currentMatchIndex = (currentMatchIndex - 1 + matchSpans.length) % matchSpans.length;
    scrollToMatch(currentMatchIndex);
  });
  scrollTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("popstate", (event) => {
    const slug = event.state?.doc || new URLSearchParams(window.location.search).get("doc");
    if (slug) {
      openDoc(slug, true);
    } else {
      resetToIndex(true);
    }
  });

  // Show/hide Top button only when toolbar is at top
  const toggleToolbarStick = () => {
    if (!docToolbar || !scrollTopBtn) return;
    const toolbarRect = docToolbar.getBoundingClientRect();
    const isAtTop = toolbarRect.top <= 0;
    scrollTopBtn.classList.toggle("hidden", !isAtTop);
  };

  window.addEventListener("scroll", toggleToolbarStick, { passive: true });
  toggleToolbarStick();

  // Initial load
  renderList();
  const initialSlug = new URLSearchParams(window.location.search).get("doc");
  if (initialSlug) {
    openDoc(initialSlug, true);
  } else {
    setView(false);
  }
})();
