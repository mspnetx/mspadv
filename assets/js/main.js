/* MSPADV — interações do site */
(function () {
  "use strict";
  var doc = document, root = doc.documentElement;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function $$(s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // Cabeçalho + barra de progresso
  var header = doc.querySelector(".site-header"), bar = doc.querySelector(".progress span"), ticking = false;
  function onScroll() {
    if (header) header.classList.toggle("scrolled", window.scrollY > 40);
    if (bar) {
      var max = root.scrollHeight - window.innerHeight;
      bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, window.scrollY / max) : 0) + ")";
    }
    ticking = false;
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  // Menu mobile
  var burger = doc.querySelector(".burger"), panel = doc.querySelector(".mobile-panel"), overlay = doc.querySelector(".overlay");
  function setMenu(open) {
    if (!panel) return;
    panel.classList.toggle("open", open); burger.classList.toggle("open", open); overlay.classList.toggle("open", open);
    burger.setAttribute("aria-expanded", open ? "true" : "false");
    doc.body.style.overflow = open ? "hidden" : "";
  }
  if (burger) burger.addEventListener("click", function () { setMenu(!panel.classList.contains("open")); });
  if (overlay) overlay.addEventListener("click", function () { setMenu(false); });
  doc.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });
  if (panel) $$("a", panel).forEach(function (a) { a.addEventListener("click", function () { setMenu(false); }); });

  // Perguntas frequentes
  $$(".faq-q").forEach(function (q) {
    q.addEventListener("click", function () {
      var item = q.closest(".faq-item"), ans = item.querySelector(".faq-a");
      var open = item.classList.toggle("open");
      q.setAttribute("aria-expanded", open ? "true" : "false");
      ans.style.maxHeight = open ? ans.scrollHeight + "px" : null;
    });
  });

  // Revelação ao rolar, com escalonamento entre irmãos
  var reveals = $$("[data-reveal]");
  reveals.forEach(function (el) {
    var sibs = $$(":scope > [data-reveal]", el.parentNode);
    if (sibs.length > 1) el.style.setProperty("--i", Math.min(sibs.indexOf(el), 7));
  });
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // Contadores
  function count(el) {
    var end = parseInt(el.getAttribute("data-count"), 10), pre = el.getAttribute("data-prefix") || "", suf = el.getAttribute("data-suffix") || "";
    if (reduce || isNaN(end)) return;
    var t0 = null, dur = 1200;
    function step(t) {
      if (!t0) t0 = t;
      var p = Math.min(1, (t - t0) / dur), v = Math.round(end * (1 - Math.pow(1 - p, 3)));
      el.textContent = pre + v + suf;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  if ("IntersectionObserver" in window) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { count(e.target); co.unobserve(e.target); } });
    }, { threshold: 0.6 });
    $$("[data-count]").forEach(function (el) { co.observe(el); });
  }

  // Idioma: lembra a escolha e sugere a outra versão (sem redirecionar)
  var pageLang = (root.lang || "pt").slice(0, 2).toLowerCase();
  $$("[data-setlang]").forEach(function (a) { a.addEventListener("click", function () { store("mspadv-lang", a.getAttribute("data-setlang")); }); });
  var hint = doc.querySelector(".lang-hint");
  if (hint) {
    var pref = store("mspadv-lang"), nav = (navigator.language || "pt").slice(0, 2).toLowerCase();
    var wants = pref || (nav === "pt" ? "pt" : "en");
    if (wants !== pageLang && !store("mspadv-hint-off")) hint.hidden = false;
    var x = hint.querySelector("[data-dismiss]");
    if (x) x.addEventListener("click", function () { hint.hidden = true; store("mspadv-hint-off", "1"); store("mspadv-lang", pageLang); });
  }

  // Formulário de contato -> WhatsApp ou e-mail
  $$("form[data-contact]").forEach(function (form) {
    var L = (form.getAttribute("data-labels") || "").split("|");
    var err = form.querySelector(".form-err"), ok = form.querySelector(".form-ok");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var via = (e.submitter && e.submitter.value) || "wa";
      var d = new FormData(form), v = function (k) { return (d.get(k) || "").toString().trim(); };
      var nome = v("nome"), tel = v("telefone");
      $$("input", form).forEach(function (i) { i.classList.remove("bad"); });
      if (!nome || !tel) {
        if (!nome) form.querySelector("[name=nome]").classList.add("bad");
        if (!tel) form.querySelector("[name=telefone]").classList.add("bad");
        err.style.display = "block"; ok.style.display = "none";
        return;
      }
      err.style.display = "none";
      var lines = [L[0] + ": " + nome, L[1] + ": " + tel];
      if (v("email")) lines.push(L[2] + ": " + v("email"));
      lines.push(L[3] + ": " + v("area"));
      if (v("mensagem")) lines.push(L[4] + ": " + v("mensagem"));
      var endpoint = form.getAttribute("data-endpoint");
      if (via === "wa") {
        window.open("https://wa.me/" + form.getAttribute("data-wa") + "?text=" + encodeURIComponent(form.getAttribute("data-intro") + "\n\n" + lines.join("\n")), "_blank", "noopener");
        ok.style.display = "block";
      } else if (endpoint) {
        fetch(endpoint, { method: "POST", headers: { Accept: "application/json" }, body: d })
          .then(function (r) { if (!r.ok) throw 0; ok.style.display = "block"; form.reset(); })
          .catch(function () { err.style.display = "block"; });
      } else {
        location.href = "mailto:" + form.getAttribute("data-email") + "?subject=" + encodeURIComponent(L[5] + " — " + v("area")) + "&body=" + encodeURIComponent(lines.join("\n"));
        ok.style.display = "block";
      }
    });
  });

  var y = doc.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();
})();
