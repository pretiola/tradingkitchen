/* Load visible recipe images and one next image, without prefetching the whole grid. */
(function () {
  'use strict';

  function init() {
    var images = Array.from(document.querySelectorAll('img[data-defer-image][data-src]'));
    var pending = new Set(images);
    if (!pending.size) return;
    var observer;
    var frame;

    function stopWatching() {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      if (observer) observer.disconnect();
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
      if (!pending.size) stopWatching();
    }

    function visibleAndNext() {
      frame = null;
      var next = 0;
      images.forEach(function (image, index) {
        var box = image.getBoundingClientRect();
        if (box.top < window.innerHeight) next = index + 1;
        if (box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth) load(image);
      });
      // Compute this from viewport position, never from which images have loaded.
      // Otherwise preloading one image could recursively fetch the rest of the grid.
      if (next < images.length) load(images[next]);
    }

    function schedule() {
      if (frame == null) frame = window.requestAnimationFrame(visibleAndNext);
    }

    if (typeof window.IntersectionObserver === 'function') {
      observer = new window.IntersectionObserver(schedule, { root: null, rootMargin: '0px', threshold: 0.01 });
      images.forEach(function (image) { observer.observe(image); });
      // Keep the speculative image observed so entering the viewport advances the lookahead.
      schedule();
    } else {
      // Older browsers use the same lookahead, with scroll work batched once per frame.
      window.addEventListener('scroll', schedule, { passive: true });
      window.addEventListener('resize', schedule);
      schedule();
    }

    window.addEventListener('beforeprint', function () {
      pending.forEach(load);
      stopWatching();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
}());
