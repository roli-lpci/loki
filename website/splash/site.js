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
  const desktopMock = document.querySelector('.desktop-mock');
  const terminalDemo = document.querySelector('[data-terminal-demo]');
  const scheduleCard = document.querySelector('.schedule-card');
  const workflowConsole = document.querySelector('.workflow-console');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const wait = delay => new Promise(resolve => window.setTimeout(resolve, delay));


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

  let workflowManualSelection = false;
  let workflowVisible = false;
  let desktopDemoVisible = false;
  let terminalDemoVisible = false;

  const selectWorkflowStage = (selectedStage, executing = false) => {
    if (!selectedStage) return;
    workflowStages.forEach(item => {
      const isActive = item.dataset.workflowStage === selectedStage;
      item.classList.toggle('is-active', isActive);
      item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
    workflowLogs.forEach(log => {
      const matches = log.dataset.workflowLog === selectedStage;
      log.classList.toggle('is-stage-highlighted', matches);
      log.classList.toggle('is-executing', matches && executing);
    });
  };

  workflowStages.forEach(stage => {
    stage.addEventListener('click', () => {
      workflowManualSelection = true;
      workflowConsole?.classList.remove('is-running');
      workflowConsole?.classList.add('is-complete');
      selectWorkflowStage(stage.dataset.workflowStage, false);
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

  const typeWidgetText = async (element, speed = 24) => {
    if (!element) return;
    const finalText = element.dataset.typeText ?? element.textContent ?? '';
    const caret = element.parentElement?.querySelector('.widget-caret');
    element.textContent = '';
    caret?.classList.add('is-active');
    for (const character of finalText) {
      element.textContent += character;
      await wait(speed);
    }
    caret?.classList.remove('is-active');
  };

  const revealElement = element => {
    element?.classList.add('is-visible');
  };

  const runDesktopDemo = async () => {
    if (!desktopMock || reduceMotion.matches) return;
    const userStep = desktopMock.querySelector('[data-desktop-step="user"]');
    const agentStep = desktopMock.querySelector('[data-desktop-step="agent"]');
    const terminalStep = desktopMock.querySelector('[data-desktop-step="terminal"]');
    const userText = userStep?.querySelector('[data-type-text]');
    const agentText = agentStep?.querySelector('[data-type-text]');
    const commandText = terminalStep?.querySelector('[data-type-text]');
    const process = desktopMock.querySelector('[data-desktop-process]');
    const output = desktopMock.querySelector('[data-desktop-output]');
    const review = desktopMock.querySelector('[data-desktop-review]');

    while (desktopMock.isConnected) {
      if (!desktopDemoVisible) {
        await wait(500);
        continue;
      }
      [agentStep, terminalStep, process, output, review].forEach(element => element?.classList.remove('is-visible', 'is-running'));
      if (userText) userText.textContent = '';
      if (agentText) agentText.textContent = agentText.dataset.typeText ?? '';
      if (commandText) commandText.textContent = commandText.dataset.typeText ?? '';
      await wait(420);
      await typeWidgetText(userText, 24);
      await wait(420);
      revealElement(agentStep);
      await typeWidgetText(agentText, 18);
      await wait(480);
      revealElement(terminalStep);
      await typeWidgetText(commandText, 34);
      await wait(220);
      revealElement(process);
      process?.classList.add('is-running');
      await wait(1250);
      process?.classList.remove('is-running');
      revealElement(output);
      await wait(500);
      revealElement(review);
      review?.classList.add('is-running');
      await wait(1450);
      review?.classList.remove('is-running');
      if (review) review.textContent = '✓ diff reviewed · release notes next';
      await wait(3600);
      if (review) review.textContent = 'reviewing diff for risky changes...';
    }
  };

  const runTerminalDemo = async () => {
    if (!terminalDemo || reduceMotion.matches) return;
    const commands = [...terminalDemo.querySelectorAll('[data-type-text]')];
    const ready = terminalDemo.querySelector('[data-terminal-step="ready"]');
    const context = terminalDemo.querySelector('[data-terminal-step="context"]');
    const tests = terminalDemo.querySelector('[data-terminal-step="tests"]');
    const result = terminalDemo.querySelector('[data-terminal-step="result"]');

    while (terminalDemo.isConnected) {
      if (!terminalDemoVisible) {
        await wait(500);
        continue;
      }
      [ready, context, tests, result].forEach(element => element?.classList.remove('is-visible', 'is-running'));
      commands.forEach(element => { element.textContent = element.dataset.typeText ?? ''; });
      await wait(620);
      await typeWidgetText(commands[0], 65);
      await wait(260);
      revealElement(ready);
      await wait(720);
      await typeWidgetText(commands[1], 29);
      await wait(360);
      revealElement(context);
      context?.classList.add('is-running');
      await wait(1350);
      context?.classList.remove('is-running');
      revealElement(tests);
      tests?.classList.add('is-running');
      await wait(1500);
      tests?.classList.remove('is-running');
      revealElement(result);
      await wait(3700);
    }
  };

  const scrambleCharacters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789░▒▓<>/\\';

  const scrambleElement = async (element, duration = 620) => {
    const finalText = element.dataset.scrambleText ?? element.textContent ?? '';
    element.dataset.scrambleText = finalText;
    const startedAt = performance.now();

    while (true) {
      const elapsed = performance.now() - startedAt;
      const progress = Math.min(elapsed / duration, 1);
      const revealedCharacters = Math.floor(finalText.length * progress);
      element.textContent = [...finalText].map((character, index) => {
        if (/\s/.test(character) || index < revealedCharacters) return character;
        return scrambleCharacters[Math.floor(Math.random() * scrambleCharacters.length)];
      }).join('');
      if (progress >= 1) break;
      await wait(32);
    }
    element.textContent = finalText;
  };

  const decodeSchedule = async () => {
    if (!scheduleCard || scheduleCard.classList.contains('is-decoded')) return;
    const rows = [...scheduleCard.querySelectorAll('.schedule-row')];
    for (const row of rows) {
      row.classList.add('is-decoding');
      await Promise.all([...row.querySelectorAll('[data-scramble]')].map(element => scrambleElement(element)));
      row.classList.remove('is-decoding');
      await wait(110);
    }
    scheduleCard.classList.add('is-decoded');
  };

  const runWorkflowDemo = async () => {
    if (!workflowConsole || reduceMotion.matches) return;
    const stages = ['understand', 'operate', 'delegate', 'deliver'];
    while (!workflowManualSelection && workflowConsole.isConnected) {
      if (!workflowVisible) {
        await wait(500);
        continue;
      }
      workflowConsole.classList.remove('is-complete');
      workflowConsole.classList.add('is-running');
      for (const stage of stages) {
        if (workflowManualSelection || !workflowVisible) break;
        selectWorkflowStage(stage, true);
        await wait(stage === 'delegate' ? 1750 : 1450);
      }
      if (workflowManualSelection) break;
      workflowLogs.forEach(log => log.classList.remove('is-executing'));
      workflowConsole.classList.remove('is-running');
      workflowConsole.classList.add('is-complete');
      await wait(3300);
    }
  };

  if (!reduceMotion.matches) {
    root.classList.add('motion-ready');
    desktopMock?.querySelectorAll('[data-type-text]').forEach(element => { element.textContent = ''; });
    terminalDemo?.querySelectorAll('[data-type-text]').forEach(element => { element.textContent = ''; });
    scheduleCard?.querySelectorAll('[data-scramble]').forEach(element => {
      const finalText = element.textContent ?? '';
      element.dataset.scrambleText = finalText;
      element.textContent = [...finalText].map(character => {
        if (/\s/.test(character)) return character;
        return scrambleCharacters[Math.floor(Math.random() * scrambleCharacters.length)];
      }).join('');
    });

    if (scheduleCard || workflowConsole || desktopMock || terminalDemo) {
      const contentObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.target === scheduleCard && entry.isIntersecting) {
            decodeSchedule();
            contentObserver.unobserve(scheduleCard);
          }
          if (entry.target === workflowConsole) {
            workflowVisible = entry.isIntersecting;
          }
          if (entry.target === desktopMock) {
            desktopDemoVisible = entry.isIntersecting;
          }
          if (entry.target === terminalDemo) {
            terminalDemoVisible = entry.isIntersecting;
          }
        });
      }, { threshold: 0.28 });
      if (scheduleCard) contentObserver.observe(scheduleCard);
      if (workflowConsole) contentObserver.observe(workflowConsole);
      if (desktopMock) contentObserver.observe(desktopMock);
      if (terminalDemo) contentObserver.observe(terminalDemo);
    }

    runDesktopDemo();
    runTerminalDemo();
    runWorkflowDemo();
  } else {
    scheduleCard?.classList.add('is-decoded');
    workflowConsole?.classList.add('is-complete');
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
