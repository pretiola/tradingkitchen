(function () {
  'use strict';

  const initialized = new WeakSet();

  function initNutrition(root) {
    const sections = root.querySelectorAll('.nutrition-section');
    sections.forEach(function (section) {
      if (initialized.has(section)) return;
      const select = section.querySelector('[data-nutrition-select]');
      const panels = Array.from(section.querySelectorAll('.nutrition-panel[data-portion]'));
      if (!select || panels.length === 0) return;

      const controls = section.querySelector('.nutrition-controls');
      const status = section.querySelector('[data-nutrition-status]');
      const options = Array.from(select.options).filter(function (option) {
        return panels.some(function (panel) { return panel.dataset.portion === option.value; });
      });
      if (options.length === 0) return;

      function showSelected(announce) {
        let selected = panels.find(function (panel) {
          return panel.dataset.portion === select.value;
        });
        if (!selected) {
          selected = panels.find(function (panel) { return !panel.hidden; }) || panels[0];
          select.value = selected.dataset.portion;
        }
        panels.forEach(function (panel) { panel.hidden = panel !== selected; });
        if (announce && status) {
          const option = options.find(function (item) { return item.value === selected.dataset.portion; });
          const label = option ? option.textContent.trim() : 'Selected serving';
          status.textContent = label + ': estimated nutrition shown.';
        }
      }

      showSelected(false);
      const canChoose = options.length > 1;
      select.hidden = !canChoose;
      select.disabled = !canChoose;
      if (controls) controls.hidden = !canChoose;
      select.addEventListener('change', function () { showSelected(true); });
      if (typeof window !== 'undefined') {
        window.addEventListener('pageshow', function () { showSelected(false); });
      }
      initialized.add(section);
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initNutrition: initNutrition };
  }
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { initNutrition(document); }, { once: true });
    } else {
      initNutrition(document);
    }
  }
}());
