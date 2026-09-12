(() => {
  const root = document.documentElement;
  const mesh = document.querySelector('.mesh');
  const banner = document.getElementById('cookie-banner');
  const dismiss = document.getElementById('cookie-dismiss');
  const consentKey = 'loki-cookie-banner-v1';
  const installCommands = {
    curl: { value: 'curl -fsSL https://loki.computer/install.sh | bash', link: false },
    npm: { value: 'npm install -g @wundercorp/loki', link: false },
    github: { value: 'https://github.com/wundercorp/loki', link: true },
  };
  const taglineActions = [
    'evolves with you',
    'works across your tools',
    'automates recurring work',
    'persists session memory',
    'turns intent into action',
  ];
  const installTabs = [...document.querySelectorAll('.install-tab')];
  const installCode = document.querySelector('.install-command-code');
  const installLink = document.querySelector('.install-command-link');
  const tagline = document.querySelector('.tagline');
  const taglineAction = document.getElementById('tagline-action');
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
    const activeTab = installTabs.find(tab => tab.classList.contains('is-active'));
    const activeKey = activeTab?.dataset.install ?? 'curl';
    const value = installCommands[activeKey]?.value ?? '';
    if (!value) return;
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
      const config = key ? installCommands[key] : null;
      if (!config || !installCode || !installLink) return;
      installTabs.forEach(item => {
        const active = item === tab;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      installCode.textContent = config.value;
      installCode.hidden = config.link;
      installLink.hidden = !config.link;
      if (config.link) {
        installLink.href = config.value;
        installLink.textContent = config.value;
      }
    });
  });

  if (tagline && taglineAction && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const typeDelay = 58;
    const eraseDelay = 30;
    const holdDelay = 1800;
    const restartDelay = 260;
    let taglineIndex = 0;

    const sleep = delay => new Promise(resolve => window.setTimeout(resolve, delay));

    const typeAction = async action => {
      taglineAction.textContent = '';
      for (const character of action) {
        taglineAction.textContent += character;
        await sleep(typeDelay);
      }
      tagline.setAttribute('aria-label', `The agent that ${action}`);
    };

    const eraseAction = async () => {
      while (taglineAction.textContent) {
        taglineAction.textContent = taglineAction.textContent.slice(0, -1);
        await sleep(eraseDelay);
      }
    };

    const runTypewriter = async () => {
      while (true) {
        const action = taglineActions[taglineIndex];
        await typeAction(action);
        await sleep(holdDelay);
        await eraseAction();
        await sleep(restartDelay);
        taglineIndex = (taglineIndex + 1) % taglineActions.length;
      }
    };

    runTypewriter();
  }

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
