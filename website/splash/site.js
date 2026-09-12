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
  const miniInstallCopy = document.querySelector('.mini-install-copy');
  const workflowStages = [...document.querySelectorAll('[data-workflow-stage]')];
  const workflowLogs = [...document.querySelectorAll('[data-workflow-log]')];
  const hero = document.querySelector('.hero');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');


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

  miniInstallCopy?.addEventListener('click', async () => {
    const value = miniInstallCopy.dataset.copyValue ?? '';
    const tooltip = miniInstallCopy.querySelector('.copy-tooltip');
    if (!value) return;
    try {
      await copyText(value);
      miniInstallCopy.classList.remove('is-copy-error');
      miniInstallCopy.classList.add('is-copied');
      miniInstallCopy.setAttribute('aria-label', 'Copied install command');
      const icon = miniInstallCopy.querySelector('i');
      icon?.classList.remove('ph-copy');
      icon?.classList.add('ph-check');
      if (tooltip) tooltip.textContent = 'Copied';
      window.setTimeout(() => {
        miniInstallCopy.classList.remove('is-copied');
        miniInstallCopy.setAttribute('aria-label', 'Copy install command');
        icon?.classList.remove('ph-check');
        icon?.classList.add('ph-copy');
      }, 1500);
    } catch {
      miniInstallCopy.classList.remove('is-copied');
      miniInstallCopy.classList.add('is-copy-error');
      miniInstallCopy.setAttribute('aria-label', 'Copy failed');
      if (tooltip) tooltip.textContent = 'Copy failed';
      window.setTimeout(() => {
        miniInstallCopy.classList.remove('is-copy-error');
        miniInstallCopy.setAttribute('aria-label', 'Copy install command');
        if (tooltip) tooltip.textContent = 'Copied';
      }, 1800);
    }
  });

  workflowStages.forEach(stage => {
    stage.addEventListener('click', () => {
      const selectedStage = stage.dataset.workflowStage;
      if (!selectedStage) return;
      workflowStages.forEach(item => {
        const isActive = item === stage;
        item.classList.toggle('is-active', isActive);
        item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      });
      workflowLogs.forEach(log => {
        log.classList.toggle('is-stage-highlighted', log.dataset.workflowLog === selectedStage);
      });
    });
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

  if (tagline && taglineAction && !reduceMotion.matches) {
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

  if (!reduceMotion.matches) {
    window.addEventListener('pointermove', event => {
      const normalizedX = (event.clientX / window.innerWidth) - 0.5;
      const normalizedY = (event.clientY / window.innerHeight) - 0.5;
      const meshX = normalizedX * 28;
      const meshY = normalizedY * 28;
      root.style.setProperty('--mesh-x', `${meshX}px`);
      root.style.setProperty('--mesh-y', `${meshY}px`);
      root.style.setProperty('--hero-grid-x', `${normalizedX * 14}px`);
      root.style.setProperty('--hero-grid-y', `${normalizedY * 10}px`);
      root.style.setProperty('--hero-parallax-x', `${normalizedX * 5}px`);
      root.style.setProperty('--hero-parallax-y', `${normalizedY * 4}px`);
    }, { passive: true });

    let heroScrollFrame = 0;
    const updateHeroScroll = () => {
      heroScrollFrame = 0;
      if (!hero) return;
      const scrollOffset = Math.min(window.scrollY * 0.055, 22);
      root.style.setProperty('--hero-scroll-y', `${scrollOffset}px`);
    };
    window.addEventListener('scroll', () => {
      if (heroScrollFrame) return;
      heroScrollFrame = window.requestAnimationFrame(updateHeroScroll);
    }, { passive: true });
    updateHeroScroll();
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
