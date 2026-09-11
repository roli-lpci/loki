(() => {
  const root = document.documentElement;
  const mesh = document.querySelector('.mesh');
  const banner = document.getElementById('cookie-banner');
  const dismiss = document.getElementById('cookie-dismiss');
  const consentKey = 'loki-cookie-banner-v1';
  const installCommands = {
    curl: 'curl -fsSL https://loki.computer/install.sh | bash',
    npm: 'npm install -g @wundercorp/loki',
    github: 'https://github.com/wundercorp/loki',
  };
  const installTabs = [...document.querySelectorAll('.install-tab')];
  const installCode = document.querySelector('#install-command code');
  const copyCommand = document.querySelector('.copy-command');
  const copyStatus = document.querySelector('.copy-status');


  const copyText = async value => {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }

    const textarea = document.createElement('textarea');
    textarea.value = value;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand('copy');
    textarea.remove();
    if (!copied) throw new Error('Copy failed');
  };

  copyCommand?.addEventListener('click', async () => {
    if (!installCode) return;
    const value = installCode.textContent ?? '';
    try {
      await copyText(value);
      copyCommand.classList.add('is-copied');
      copyCommand.setAttribute('aria-label', 'Copied');
      copyCommand.setAttribute('title', 'Copied');
      if (copyStatus) copyStatus.textContent = 'Copied to clipboard';
      window.setTimeout(() => {
        copyCommand.classList.remove('is-copied');
        copyCommand.setAttribute('aria-label', 'Copy install command');
        copyCommand.setAttribute('title', 'Copy');
        if (copyStatus) copyStatus.textContent = '';
      }, 1400);
    } catch {
      copyCommand.setAttribute('aria-label', 'Copy failed');
      copyCommand.setAttribute('title', 'Copy failed');
      if (copyStatus) copyStatus.textContent = 'Could not copy to clipboard';
    }
  });

  installTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const key = tab.dataset.install;
      if (!key || !installCommands[key] || !installCode) return;
      installTabs.forEach(item => {
        const active = item === tab;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      installCode.textContent = installCommands[key];
    });
  });

  if (mesh && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.addEventListener('pointermove', event => {
      const x = ((event.clientX / window.innerWidth) - 0.5) * 28;
      const y = ((event.clientY / window.innerHeight) - 0.5) * 28;
      root.style.setProperty('--mesh-x', `${x}px`);
      root.style.setProperty('--mesh-y', `${y}px`);
    }, { passive: true });
  }

  try {
    if (banner && localStorage.getItem(consentKey) !== 'dismissed') {
      banner.hidden = false;
    }
    dismiss?.addEventListener('click', () => {
      localStorage.setItem(consentKey, 'dismissed');
      banner.hidden = true;
    });
  } catch {
    if (banner) {
      banner.hidden = false;
    }
    dismiss?.addEventListener('click', () => {
      banner.hidden = true;
    });
  }
})();
