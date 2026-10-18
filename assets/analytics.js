// Keep local previews and GitHub preview URLs out of production reports.
(() => {
  if (!['tradingkitchen.org', 'www.tradingkitchen.org'].includes(window.location.hostname)) return;
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', 'G-NMY1V4BQVB');
  const tag = document.createElement('script');
  tag.async = true;
  tag.src = 'https://www.googletagmanager.com/gtag/js?id=G-NMY1V4BQVB';
  document.head.appendChild(tag);
})();
