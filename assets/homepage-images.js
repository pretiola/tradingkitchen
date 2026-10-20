/* Keep image URLs away from the preload scanner until their cards enter the viewport. */
(function () {
  'use strict';

  function init() {
    var pending = new Set(document.querySelectorAll('img[data-defer-image][data-src]'));
    if (!pending.size) return;
    var observer;
    var frame;

    function stopFallback() {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    }

    function load(image) {
      if (!pending.has(image)) return;
      // Set responsive candidates first so the browser does not also request the fallback.
      var srcset = image.getAttribute('data-srcset');
      if (srcset) image.setAttribute('srcset', srcset);
      image.setAttribute('src', image.getAttribute('data-src'));
      image.removeAttribute('data-src');
      image.removeAttribute('data-srcset');
      image.removeAttribute('data-defer-image');
      pending.delete(image);
      if (observer) observer.unobserve(image);
      if (!pending.size) stopFallback();
    }

    function visible() {
      frame = null;
      pending.forEach(function (image) {
        var box = image.getBoundingClientRect();
        if (box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth) load(image);
      });
    }

    function schedule() {
      if (frame == null) frame = window.requestAnimationFrame(visible);
    }

    if (typeof window.IntersectionObserver === 'function') {
      observer = new window.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && entry.intersectionRatio > 0) load(entry.target);
        });
      }, { root: null, rootMargin: '0px', threshold: 0.01 });
      pending.forEach(function (image) { observer.observe(image); });
    } else {
      // Older browsers still defer offscreen cards; scroll work is batched once per frame.
      window.addEventListener('scroll', schedule, { passive: true });
      window.addEventListener('resize', schedule);
      schedule();
    }

    window.addEventListener('beforeprint', function () {
      pending.forEach(load);
      if (observer) observer.disconnect();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
}());
