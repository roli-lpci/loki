import { contextBridge, ipcRenderer, webFrame, webUtils } from 'electron'

// Which translucency the OS can back. Asked synchrowundercorply because the renderer
// needs it before its first paint, and answered by main because deciding it
// needs `os.release()` — a sandboxed preload may only require electron, events,
// timers and url, so importing node:os here throws before contextBridge runs
// and takes the ENTIRE bridge down with it (window.lokiDesktop undefined =>
// "Desktop IPC bridge is unavailable"). No reply means no glass, which degrades
// to an ordinary opaque window rather than a page thinned over nothing.
const translucencySupport = ipcRenderer.sendSync('loki:translucency:support')
const hudWindowing = ipcRenderer.sendSync('loki:hud:windowing')
const hudNativeDrag = hudWindowing?.nativeDrag === true
const launchFlags = ipcRenderer.sendSync('loki:launch-flags')

contextBridge.exposeInMainWorld('lokiDesktop', {
  glassSupported: translucencySupport?.glass === true,
  translucencySupported: translucencySupport?.translucency === true,
  // Launch-flag fact: the app was started with --local, so the renderer may
  // show the local-models surfaces. Static for the window's lifetime.
  localModelsEnabled: launchFlags?.localModels === true,
  // Launch-flag fact: the WunderCorp free tier is on for this launch
  // (LOKI_GUEST_ONBOARDING=1 or --guest-onboarding). Read-only; the same
  // decision is stamped onto every backend the app spawns.
  guestOnboardingEnabled: launchFlags?.guestOnboarding === true,
  getConnection: (profile, opts) => ipcRenderer.invoke('loki:connection', profile, opts),
  // Registry-scoped backend resolution: { connectionId, profile } → descriptor.
  getConnectionFor: payload => ipcRenderer.invoke('loki:connection:for', payload),
  getProfileRoutes: profiles => ipcRenderer.invoke('loki:plugin-profile-routes', profiles),
  revalidateConnection: () => ipcRenderer.invoke('loki:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('loki:backend:touch', profile),
  getPoolLimits: () => ipcRenderer.invoke('loki:pool-limits:get'),
  setPoolLimits: limits => ipcRenderer.invoke('loki:pool-limits:set', limits),
  getGatewayWsUrl: profile => ipcRenderer.invoke('loki:gateway:ws-url', profile),
  // Registry-scoped fresh WS URL: { connectionId, profile } → result shape of
  // getGatewayWsUrl, minted against that connection's backend.
  getGatewayWsUrlFor: payload => ipcRenderer.invoke('loki:gateway:ws-url-for', payload),
  // Union agent roster across every registered connection.
  getAgentRoster: () => ipcRenderer.invoke('loki:agents:roster'),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('loki:window:openSession', sessionId, opts),
  openSessionInTerminal: (sessionId, opts) => ipcRenderer.invoke('loki:window:openInTerminal', sessionId, opts),
  openWindow: () => ipcRenderer.invoke('loki:window:openInstance'),
  openBrowserWindow: tabId => ipcRenderer.invoke('loki:window:openBrowser', tabId),
  onBrowserPopoutClosed: callback => {
    const listener = (_event, tabId) => callback(tabId)
    ipcRenderer.on('loki:browser-popout:closed', listener)

    return () => ipcRenderer.removeListener('loki:browser-popout:closed', listener)
  },
  claimAmbientCue: key => ipcRenderer.invoke('loki:ambient:claim', key),
  wakeIndicator: {
    getState: () => ipcRenderer.invoke('loki:wake-indicator:get'),
    setState: state => ipcRenderer.send('loki:wake-indicator:set', state),
    onState: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('loki:wake-indicator:state', listener)

      return () => ipcRenderer.removeListener('loki:wake-indicator:state', listener)
    }
  },
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('loki:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('loki:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('loki:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('loki:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('loki:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('loki:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('loki:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('loki:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('loki:pet-overlay:control', listener)
    }
  },
  // HUD mode: the chrome-free floating chat. A full app renderer (own gateway)
  // sized as a floating bar, so it mounts the real composer. Main owns the
  // window; `onChanged` keeps every window's toggle truthful.
  hud: {
    nativeDrag: hudNativeDrag,
    windowing: {
      clientPlacement: hudWindowing?.clientPlacement !== false,
      controlDrag: hudWindowing?.controlDrag === true,
      nativeDrag: hudNativeDrag,
      solid: hudWindowing?.solid === true,
      workspaceTransfer: hudWindowing?.workspaceTransfer === true
    },
    open: request => ipcRenderer.invoke('loki:hud:open', request),
    close: () => ipcRenderer.invoke('loki:hud:close'),
    setIgnoreMouse: ignore => ipcRenderer.send('loki:hud:ignore-mouse', ignore),
    beginMove: () => ipcRenderer.send('loki:hud:begin-move'),
    endMove: () => ipcRenderer.send('loki:hud:end-move'),
    moveBy: delta => ipcRenderer.send('loki:hud:move-by', delta),
    setWorkspaceTransfer: transferring => ipcRenderer.send('loki:hud:workspace-transfer', transferring),
    setBounds: bounds => ipcRenderer.send('loki:hud:set-bounds', bounds),
    resetLayout: () => ipcRenderer.invoke('loki:hud:reset-layout'),
    // Whether the band covers the window below the bar. Main pairs it with the
    // user's translucency setting to decide the native frost (macOS vibrancy /
    // Windows 11 DWM backdrop) — see hudFrostFor.
    setFrost: showing => ipcRenderer.invoke('loki:hud:frost', showing),
    // The HUD tells main which session it is on; main hands that back to the
    // app window when the HUD closes, so the app can re-home onto it.
    setSession: sessionId => ipcRenderer.send('loki:hud:session', sessionId),
    onGoto: callback => {
      const listener = (_event, sessionId) => callback(sessionId)
      ipcRenderer.on('loki:hud:goto', listener)

      return () => ipcRenderer.removeListener('loki:hud:goto', listener)
    },
    onChanged: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('loki:hud:changed', listener)

      return () => ipcRenderer.removeListener('loki:hud:changed', listener)
    },
    // Linux only, and silent elsewhere: where the cursor is, in page
    // coordinates, or null when it has left the window. Stands in for the
    // mousemove that `setIgnoreMouseEvents(true, { forward: true })` delivers on
    // macOS and Windows but not here.
    onCursor: callback => {
      const listener = (_event, point) => callback(point)
      ipcRenderer.on('loki:hud:cursor', listener)

      return () => ipcRenderer.removeListener('loki:hud:cursor', listener)
    },
    // Main's game-overlay watch: whether a fullscreen app (a game) is under
    // the HUD, so the renderer can step back to the low-opacity overlay
    // treatment while one owns the screen.
    onGameOverlay: callback => {
      const listener = (_event, state) => callback(state)
      ipcRenderer.on('loki:hud:game-overlay', listener)

      return () => ipcRenderer.removeListener('loki:hud:game-overlay', listener)
    }
  },
  // Quick Entry: the global-hotkey mini composer window. Main owns the OS
  // shortcut + the persisted preference; the quick window only captures text
  // and hands it back, and the primary renderer submits it through the normal
  // prompt path.
  quickEntry: {
    getSettings: () => ipcRenderer.invoke('loki:quick-entry:settings:get'),
    setSettings: patch => ipcRenderer.invoke('loki:quick-entry:settings:set', patch),
    submit: payload => ipcRenderer.send('loki:quick-entry:submit', payload),
    dismiss: () => ipcRenderer.send('loki:quick-entry:dismiss'),
    // Primary renderer → main → quick window: gateway connection state + the
    // recent-session options the target picker offers. Main caches the latest
    // payload so a freshly spawned quick window starts from truth.
    pushState: payload => ipcRenderer.send('loki:quick-entry:state', payload),
    // Quick window subscribes to those pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:quick-entry:state', listener)

      return () => ipcRenderer.removeListener('loki:quick-entry:state', listener)
    },
    // Main → primary renderer: a submit captured by the quick window.
    onSubmit: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:quick-entry:submit', listener)

      return () => ipcRenderer.removeListener('loki:quick-entry:submit', listener)
    },
    // Main → quick window: you were just summoned (reset draft + refocus).
    onShown: callback => {
      const listener = () => callback()
      ipcRenderer.on('loki:quick-entry:shown', listener)

      return () => ipcRenderer.removeListener('loki:quick-entry:shown', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('loki:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('loki:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('loki:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('loki:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('loki:connection-config:test', payload),
  // Opt-in OS-keychain encryption for stored gateway secrets (default off —
  // see secret-storage-policy.ts). get never touches the OS keychain.
  getSecretStorageEncryption: () => ipcRenderer.invoke('loki:secret-storage:get'),
  setSecretStorageEncryption: (on: boolean) => ipcRenderer.invoke('loki:secret-storage:set', on),
  // v2 multi-connection registry: named agent sources (local / remote / cloud / ssh).
  connections: {
    list: () => ipcRenderer.invoke('loki:connections:list'),
    save: payload => ipcRenderer.invoke('loki:connections:save', payload),
    remove: id => ipcRenderer.invoke('loki:connections:remove', id),
    setPrimary: id => ipcRenderer.invoke('loki:connections:set-primary', id),
    setLaunchMode: mode => ipcRenderer.invoke('loki:connections:set-launch-mode', mode),
    setLastUsed: id => ipcRenderer.invoke('loki:connections:set-last-used', id),
    test: id => ipcRenderer.invoke('loki:connections:test', id),
    updateManaged: id => ipcRenderer.invoke('loki:connections:update-managed', id),
    // Fan out `loki update` to every eligible registered connection.
    // Optional excludeIds skips rows the caller updates through another path.
    updateAll: options => ipcRenderer.invoke('loki:connections:update-all', options),
    // Registry lifecycle push (main → renderer): a connection was removed or
    // materially edited, so secondaries scoped to it must be disposed (and,
    // for edits, re-dialed at the new target).
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:connections:changed', listener)

      return () => ipcRenderer.removeListener('loki:connections:changed', listener)
    }
  },
  sshConfigHosts: () => ipcRenderer.invoke('loki:ssh-config:hosts'),
  sshResolveHost: host => ipcRenderer.invoke('loki:ssh-config:resolve', host),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('loki:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('loki:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('loki:connection-config:oauth-logout', remoteUrl),
  // Loki Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('loki:cloud:status'),
    login: () => ipcRenderer.invoke('loki:cloud:login'),
    logout: () => ipcRenderer.invoke('loki:cloud:logout'),
    discover: org => ipcRenderer.invoke('loki:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('loki:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    get: () => ipcRenderer.invoke('loki:profile:get'),
    remember: name => ipcRenderer.invoke('loki:profile:remember', name),
    set: name => ipcRenderer.invoke('loki:profile:set', name)
  },
  api: request => ipcRenderer.invoke('loki:api', request),
  notify: payload => ipcRenderer.invoke('loki:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('loki:requestMicrophoneAccess'),
  readWindowBelow: () => ipcRenderer.invoke('loki:window:readBelow'),
  readFileDataUrl: filePath => ipcRenderer.invoke('loki:readFileDataUrl', filePath),
  readFileDataUrlForAttach: filePath => ipcRenderer.invoke('loki:readFileDataUrlForAttach', filePath),
  dataUrlReadMax: {
    get: () => ipcRenderer.invoke('loki:data-url-read-max:get'),
    set: maxMb => ipcRenderer.invoke('loki:data-url-read-max:set', maxMb)
  },
  readFileText: filePath => ipcRenderer.invoke('loki:readFileText', filePath),
  readPluginSource: (filePath: string) => ipcRenderer.invoke('loki:readPluginSource', filePath),
  selectPaths: options => ipcRenderer.invoke('loki:selectPaths', options),
  selectSavePath: options => ipcRenderer.invoke('loki:selectSavePath', options),
  writeClipboard: text => ipcRenderer.invoke('loki:writeClipboard', text),
  readClipboard: () => ipcRenderer.invoke('loki:readClipboard'),
  saveGatewayFile: payload => ipcRenderer.invoke('loki:saveGatewayFile', payload),
  saveImageFromUrl: url => ipcRenderer.invoke('loki:saveImageFromUrl', url),
  contextMenuEdit: command => ipcRenderer.invoke('loki:context-menu:edit', command),
  contextMenuCopyImage: () => ipcRenderer.invoke('loki:context-menu:copy-image'),
  contextMenuSpellcheck: action => ipcRenderer.invoke('loki:context-menu:spellcheck', action),
  contextMenuGuestAddWord: payload => ipcRenderer.invoke('loki:context-menu:guest-add-word', payload),
  onContextMenuSpellcheck: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:context-menu-spellcheck', listener)

    return () => ipcRenderer.removeListener('loki:context-menu-spellcheck', listener)
  },
  saveImageBuffer: (data, ext, name) => ipcRenderer.invoke('loki:saveImageBuffer', { data, ext, name }),
  capturePreview: payload => ipcRenderer.invoke('loki:capturePreview', payload),
  saveClipboardImage: () => ipcRenderer.invoke('loki:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('loki:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('loki:watchPreviewFile', url),
  watchDirectory: dir => ipcRenderer.invoke('loki:watchDirectory', dir),
  stopPreviewFileWatch: id => ipcRenderer.invoke('loki:stopPreviewFileWatch', id),
  setActiveWork: payload => ipcRenderer.send('loki:active-work', payload),
  setTitleBarTheme: payload => ipcRenderer.send('loki:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('loki:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('loki:translucency', payload),
  setKeepAwake: on => ipcRenderer.send('loki:keep-awake', on),
  setDisableF12: blocked => ipcRenderer.send('loki:devtools:disable-f12', blocked),
  setPreviewShortcutActive: active => ipcRenderer.send('loki:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('loki:openExternal', url),
  mcpOauth: {
    // One-shot loopback listener for MCP OAuth against remote backends: bind
    // on this machine, hand redirectUri to mcp.servers.oauth.start, then wait
    // for the provider redirect and relay code/state via oauth.callback.
    listen: () => ipcRenderer.invoke('loki:mcp-oauth:listen'),
    wait: (id, timeoutMs) => ipcRenderer.invoke('loki:mcp-oauth:wait', id, timeoutMs),
    cancel: id => ipcRenderer.invoke('loki:mcp-oauth:cancel', id)
  },
  openPreviewInBrowser: url => ipcRenderer.invoke('loki:openPreviewInBrowser', url),
  reachPreviewUrl: url => ipcRenderer.invoke('loki:preview:reach', url),
  setActiveConnectionRoute: route => ipcRenderer.send('loki:connection:active-route', route),
  fetchLinkTitle: url => ipcRenderer.invoke('loki:fetchLinkTitle', url),
  resolveFavicon: url => ipcRenderer.invoke('loki:resolveFavicon', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('loki:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('loki:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('loki:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('loki:setting:defaultProjectDir:pick')
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('loki:zoom:get'),
    // Synchrowundercorp zoom factor (1 = 100%). Coordinate math needs it in the
    // same tick as the event it converts, so no IPC round-trip here.
    factor: () => webFrame.getZoomFactor(),
    setPercent: percent => ipcRenderer.send('loki:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:zoom:changed', listener)

      return () => ipcRenderer.removeListener('loki:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('loki:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('loki:logs:recent'),
  // Fire-and-forget: persists a renderer error-boundary catch (with component
  // stack) to desktop.log so crashes survive the window (#79428).
  reportRendererError: report => ipcRenderer.send('loki:logs:renderer-error', report),
  readDir: dirPath => ipcRenderer.invoke('loki:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('loki:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('loki:fs:reveal', targetPath),
  openDir: dirPath => ipcRenderer.invoke('loki:fs:openDir', dirPath),
  desktopPluginsRoot: () => ipcRenderer.invoke('loki:fs:desktopPluginsRoot'),
  reconcileDesktopPlugins: () => ipcRenderer.invoke('loki:fs:reconcileDesktopPlugins'),
  logsRoot: () => ipcRenderer.invoke('loki:fs:logsRoot'),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('loki:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('loki:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('loki:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('loki:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('loki:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('loki:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('loki:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('loki:git:branchList', repoPath),
    baseBranchList: repoPath => ipcRenderer.invoke('loki:git:baseBranchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('loki:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('loki:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('loki:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('loki:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('loki:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('loki:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('loki:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('loki:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('loki:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('loki:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('loki:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('loki:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('loki:git:review:shipInfo', repoPath),
      prList: (repoPath, branches, numbers) =>
        ipcRenderer.invoke('loki:git:review:prList', repoPath, branches, numbers),
      fetchPrComment: (repoPath, url) => ipcRenderer.invoke('loki:git:review:fetchPrComment', repoPath, url),
      createPr: repoPath => ipcRenderer.invoke('loki:git:review:createPr', repoPath)
    }
  },
  terminal: {
    attach: id => ipcRenderer.invoke('loki:terminal:attach', id),
    cwd: id => ipcRenderer.invoke('loki:terminal:cwd', id),
    dispose: id => ipcRenderer.invoke('loki:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('loki:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('loki:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('loki:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `loki:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `loki:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:close-preview-requested', listener)

    return () => ipcRenderer.removeListener('loki:close-preview-requested', listener)
  },
  onPreviewNav: callback => {
    const listener = (_event, command) => callback(command)
    ipcRenderer.on('loki:preview-nav', listener)

    return () => ipcRenderer.removeListener('loki:preview-nav', listener)
  },
  onOpenFolderRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:open-folder-requested', listener)

    return () => ipcRenderer.removeListener('loki:open-folder-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:open-updates', listener)

    return () => ipcRenderer.removeListener('loki:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:deep-link', listener)

    return () => ipcRenderer.removeListener('loki:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('loki:deep-link-ready'),
  probePluginRepo: payload => ipcRenderer.invoke('loki:plugin:probe', payload),
  installDesktopPlugin: payload => ipcRenderer.invoke('loki:plugin:installDesktop', payload),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:window-state-changed', listener)

    return () => ipcRenderer.removeListener('loki:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('loki:focus-session', listener)

    return () => ipcRenderer.removeListener('loki:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:notification-action', listener)

    return () => ipcRenderer.removeListener('loki:notification-action', listener)
  },
  onNotificationActivate: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:notification-activate', listener)

    return () => ipcRenderer.removeListener('loki:notification-activate', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:preview-file-changed', listener)

    return () => ipcRenderer.removeListener('loki:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:backend-exit', listener)

    return () => ipcRenderer.removeListener('loki:backend-exit', listener)
  },
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:connection:applied', listener)

    return () => ipcRenderer.removeListener('loki:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:power-resume', listener)

    return () => ipcRenderer.removeListener('loki:power-resume', listener)
  },
  // AC ↔ battery transitions; renderers slow their backstop polls on battery.
  getOnBattery: () => ipcRenderer.invoke('loki:power-battery:get'),
  onBatteryChanged: callback => {
    const listener = (_event, onBattery) => callback(Boolean(onBattery))
    ipcRenderer.on('loki:power-battery', listener)

    return () => ipcRenderer.removeListener('loki:power-battery', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:boot-progress', listener)

    return () => ipcRenderer.removeListener('loki:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('loki:bootstrap:get'),
  continueBootstrapLocal: () => ipcRenderer.invoke('loki:bootstrap:continue-local'),
  recycleBackend: profile => ipcRenderer.invoke('loki:backend:recycle', profile),
  resetBootstrap: () => ipcRenderer.invoke('loki:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('loki:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('loki:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('loki:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('loki:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('loki:version'),
  relaunchApp: () => ipcRenderer.invoke('loki:app:relaunch'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('loki:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('loki:uninstall:summary'),
    run: mode => ipcRenderer.invoke('loki:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('loki:updates:check'),
    apply: opts => ipcRenderer.invoke('loki:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('loki:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('loki:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('loki:updates:progress', listener)

      return () => ipcRenderer.removeListener('loki:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('loki:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('loki:vscode-theme:search', query)
  },
  // Find-in-page (Ctrl/Cmd+F): delegates to Electron's
  // webContents.findInPage on the IPC sender's window so a Cmd+F pressed
  // in a secondary session window searches THAT window, not the primary.
  // `onFoundInPage` returns the unsubscribe fn; the renderer wires it via
  // `initFindInPageListener` in store/find-in-page.ts and tears it down
  // when the FindBar unmounts.
  findInPage: (query, options) => ipcRenderer.invoke('loki:find-in-page', query, options),
  stopFindInPage: () => ipcRenderer.invoke('loki:stop-find-in-page'),
  onFoundInPage: callback => {
    const listener = (_event, result) => callback(result)
    ipcRenderer.on('loki:found-in-page', listener)

    return () => ipcRenderer.removeListener('loki:found-in-page', listener)
  },
  // Main-process `before-input-event` forwards Ctrl/Cmd+F here so renderer
  // can open the FindBar even when the GTK compositor has already grabbed
  // the chord at the windowing layer (#81727).
  onOpenFindBarRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('loki:open-find-bar', listener)

    return () => ipcRenderer.removeListener('loki:open-find-bar', listener)
  }
})
