// Scroll-driven photo story: the step nearest the reading line becomes active,
// and its photo or video fades in on the pinned frame.
(function () {
  var steps = Array.prototype.slice.call(document.querySelectorAll(".step"));
  var layers = Array.prototype.slice.call(document.querySelectorAll(".layer"));
  if (!steps.length) return;
  var count = document.querySelector(".meter .count");
  var bar = document.querySelector(".meter .bar i");
  var total = steps.length;
  var active = -1;
  var phone = window.matchMedia("(max-width: 800px)");

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  // Load photos just before they're needed.
  function warm(i) {
    for (var j = i; j <= i + 2 && j < layers.length; j++) {
      var img = layers[j].querySelector("img[data-src]");
      if (img) {
        img.srcset = img.getAttribute("data-srcset");
        img.src = img.getAttribute("data-src");
        img.removeAttribute("data-src");
        img.removeAttribute("data-srcset");
      }
    }
  }

  function setActive(i) {
    if (i === active) return;
    active = i;
    warm(i);
    steps.forEach(function (s, k) { s.classList.toggle("is-active", k === i); });
    layers.forEach(function (l, k) {
      var on = k === i;
      l.classList.toggle("is-active", on);
      var v = l.querySelector("video");
      if (v) {
        if (on) {
          if (v.preload === "none") v.preload = "auto";
          var p = v.play();
          if (p && p.catch) p.catch(function () {});
        } else {
          v.pause();
        }
      }
    });
    if (count) count.textContent = pad(i + 1) + " / " + pad(total);
    if (bar) bar.style.width = ((i + 1) / total * 100).toFixed(1) + "%";
  }

  // On a phone the photo covers the top half, so read from lower down.
  function readingLine() {
    return window.innerHeight * (phone.matches ? 0.76 : 0.5);
  }

  var ticking = false;
  function update() {
    ticking = false;
    var line = readingLine();
    var best = 0, bestDist = Infinity;
    for (var k = 0; k < steps.length; k++) {
      var r = steps[k].getBoundingClientRect();
      var d = Math.abs((r.top + r.bottom) / 2 - line);
      if (d < bestDist) { bestDist = d; best = k; }
    }
    setActive(best);
  }
  function onScroll() {
    if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);

  // Tap for sound
  document.querySelectorAll(".sound").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var v = btn.parentNode.querySelector("video");
      v.muted = !v.muted;
      btn.textContent = v.muted ? "Sound on" : "Sound off";
      btn.setAttribute("aria-pressed", v.muted ? "false" : "true");
      if (!v.muted) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    });
  });

  update();
})();
