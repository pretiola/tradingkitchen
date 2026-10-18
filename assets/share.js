// Share the canonical recipe URL, without preview hosts or tracking parameters.
(() => {
  const canonical = document.querySelector('link[rel="canonical"]');
  const url = canonical ? canonical.href : window.location.href;
  const title = document.title;
  const button = document.getElementById('copy-link');
  const status = document.getElementById('share-status');

  document.getElementById('share-x').href =
    `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;
  document.getElementById('share-facebook').href =
    `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
  document.getElementById('share-email').href =
    `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(`Check out this recipe: ${url}`)}`;

  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = 'Recipe link copied.';
    } catch {
      status.replaceChildren();
      status.append('Copy this recipe link: ');
      const link = document.createElement('a');
      link.href = url;
      link.textContent = url;
      link.className = 'underline break-all';
      status.append(link);
    }
  });
})();
