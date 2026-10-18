(() => {
  const form = document.getElementById('invite-form');
  const status = document.getElementById('form-status');
  if (!form || !status) return;
  const button = form.querySelector('button[type="submit"]');
  let submitting = false;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitting || !form.reportValidity()) return;
    submitting = true;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Sending…';
    form.setAttribute('aria-busy', 'true');
    status.textContent = '';
    status.classList.add('hidden');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        const errors = Array.isArray(result.errors)
          ? result.errors.map(error => error.message).filter(Boolean).join(' ')
          : '';
        throw new Error(errors || 'Your request could not be sent. Please try again later.');
      }
      // Only a confirmed successful response counts; never send the email to GA.
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'generate_lead', { form_name: 'trading_post_invite' });
      }
      window.location.assign('thanks.html');
    } catch (error) {
      status.textContent = error.name === 'AbortError'
        ? 'The request timed out. Please check your connection and try again.'
        : (error.message === 'Failed to fetch'
          ? 'We could not connect. Please check your connection and try again.'
          : error.message || 'Your request could not be sent. Please try again later.');
      status.classList.remove('hidden');
      status.classList.add('text-red-700');
    } finally {
      clearTimeout(timer);
      button.disabled = false;
      button.textContent = originalText;
      form.removeAttribute('aria-busy');
      submitting = false;
    }
  });
})();
