# Page Reporter v2.6.1
#
# v2.6.1 fix:
#  - Only announce page load if the treeInterceptor is the active/foreground one
#    (fixes repeated announcements when tabs load in background or focus is outside browser)
#
# v3.4 changes:
#  - REMOVED from NVDA config system entirely (no more config.conf.spec injection)
#  - Settings now stored in %APPDATA%\nvda\pageReporter.json
#  - toggle (NVDA+Shift+W) and onSave() no longer call config.conf.save()
#    so NVDA's own "save configuration on exit" behavior is never affected
#
# v3.1 fixes carried over:
#  - Robust URL reading (Facebook accValue fallback)
#  - busy:true retry with exponential back-off
#  - Non-blocking chunked COM tree walk
#  - virtualBuffer fields fast path
#  - SPA URL watcher (YouTube, etc.)
#  - GetWindowText for thread-safe title detection

import globalPluginHandler
import ui
import speech
import queueHandler
import controlTypes
import wx
import addonHandler
import weakref
import threading
import os
import json
from collections import deque

addonHandler.initTranslation()

try:
    from gui.settingsDialogs import SettingsPanel
except ImportError:
    from gui import SettingsPanel
import gui
from gui import guiHelper

# ---------------------------------------------------------------------------
# Standalone JSON config — completely isolated from NVDA's nvda.ini
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "nvda", "pageReporter.json"
)

_DEFAULTS = {
    "enabled":          True,
    "reportHeadings":   True,
    "reportLinks":      True,
    "reportButtons":    True,
    "reportFormFields": True,
    "reportLandmarks":  True,
    "blockedSites":     "",
}

_config = {}

def _loadConfig():
    global _config
    _config = dict(_DEFAULTS)
    try:
        if os.path.isfile(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only accept keys we know; silently drop unknown ones
            for k in _DEFAULTS:
                if k in data:
                    _config[k] = data[k]
    except Exception:
        pass  # If anything goes wrong, just use defaults

def _saveConfig():
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(_config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _cfg():
    return _config

def _isBlocked(domain):
    if not domain: return False
    raw = _config.get("blockedSites", "")
    if not raw: return False
    domain = domain.lower()
    for e in [s.strip().lower() for s in raw.split(",") if s.strip()]:
        if domain == e or domain.endswith("." + e): return True
    return False

# Load config at module import time
_loadConfig()

# ---------------------------------------------------------------------------
# Role sets
# ---------------------------------------------------------------------------
_H  = frozenset({controlTypes.Role.HEADING})
_LK = frozenset({controlTypes.Role.LINK})
_BT = frozenset({controlTypes.Role.BUTTON, controlTypes.Role.MENUBUTTON})
_FM = frozenset({controlTypes.Role.EDITABLETEXT, controlTypes.Role.COMBOBOX,
                 controlTypes.Role.CHECKBOX, controlTypes.Role.RADIOBUTTON})
_LM = frozenset({controlTypes.Role.LANDMARK, controlTypes.Role.REGION})

# ---------------------------------------------------------------------------
# URL / title helpers
# ---------------------------------------------------------------------------
def _getURL(ti):
    try:
        root = ti.rootNVDAObject
        v = root.value
        if v and "://" in v:
            return v.split("?")[0]
        try:
            v = root.IAccessibleObject.accValue(0)
            if v and "://" in v:
                return v.split("?")[0]
        except Exception:
            pass
        try:
            v = root.name or ""
            if "://" in v:
                return v.split("?")[0]
        except Exception:
            pass
    except Exception:
        pass
    return None

def _getTitle(ti):
    try:
        name = ti.rootNVDAObject.name
        return name.strip() if name else None
    except Exception:
        return None

def _getPageIdentity(ti):
    url = _getURL(ti)
    if url:
        return url
    return _getTitle(ti)

def _getDomain(ti):
    url = _getURL(ti)
    if not url: return ""
    try:
        host = url.split("://", 1)[1].split("/")[0]
        return host.lower()
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# busy:true retry
# ---------------------------------------------------------------------------
_BUSY_POLL_MS  = 300
_BUSY_MAX_S    = 8.0

def _isBusy(ti):
    try:
        attrs = ti.rootNVDAObject.IAccessibleObject.attributes
        if attrs and "busy:true" in attrs:
            return True
    except Exception:
        pass
    return False

def _waitThenAnnounce(tiRef, cancel_event):
    import time
    deadline = time.monotonic() + _BUSY_MAX_S
    while not cancel_event.is_set():
        ti = tiRef() if isinstance(tiRef, weakref.ref) else tiRef
        if ti is None:
            return

        result = [None]
        done   = threading.Event()
        def _check():
            try:
                result[0] = (ti.isReady, _isBusy(ti))
            except Exception:
                result[0] = (False, True)
            done.set()
        queueHandler.queueFunction(queueHandler.eventQueue, _check)
        done.wait(timeout=1.0)
        is_ready, is_busy = result[0] or (False, True)
        timed_out = time.monotonic() >= deadline

        if (is_ready and not is_busy) or timed_out:
            roles_result = [None]
            roles_done   = threading.Event()
            def _getRoles():
                try:
                    roles_result[0] = _rolesFromFields(ti)
                except Exception:
                    roles_result[0] = None
                roles_done.set()
            queueHandler.queueFunction(queueHandler.eventQueue, _getRoles)
            roles_done.wait(timeout=1.0)
            roles = roles_result[0]

            has_content = roles is not None and len(roles) > 0
            if has_content or timed_out:
                wx.CallAfter(_announce, tiRef, cancel_event)
                return
        time.sleep(_BUSY_POLL_MS / 1000.0)

# ---------------------------------------------------------------------------
# Debounce / cancellation
# ---------------------------------------------------------------------------
import time as _time

_pending      = {}
_pending_lock = threading.Lock()
_pending_timer = None

_DEBOUNCE_S = 2.5

def _registerPending(ti, url=None):
    global _pending_timer
    import time as _time_local
    now = _time_local.monotonic()
    with _pending_lock:
        key      = id(ti)
        existing = _pending.get(key)
        if existing:
            old_ev, old_url, old_ts = existing
            same         = (url is not None and old_url is not None and url == old_url)
            recent_noise = (url is None and now - old_ts < _DEBOUNCE_S)
            if same or recent_noise:
                return old_ev, False
            if _pending_timer is not None:
                try: _pending_timer.Stop()
                except Exception: pass
            _pending_timer = None
            old_ev.set()
        ev = threading.Event()
        _pending[key] = (ev, url, now)
    return ev, True

# ---------------------------------------------------------------------------
# Fast role extraction
# ---------------------------------------------------------------------------
def _rolesFromFields(ti):
    try:
        import textInfos
        info   = ti.makeTextInfo(textInfos.POSITION_ALL)
        fields = info.getTextWithFields()
        roles  = []
        for item in fields:
            if hasattr(item, 'field') and item.field:
                role = item.field.get('role')
                if role is not None:
                    roles.append(role)
        return roles
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Chunked COM tree walk fallback
# ---------------------------------------------------------------------------
_CHUNK    = 50
_CHUNK_MS = 5

class _ChunkedWalker:
    def __init__(self, root, cancel_event, on_done, maxNodes=3000):
        self._q        = deque([root])
        self._seen     = set()
        self._roles    = []
        self._n        = 0
        self._maxNodes = maxNodes
        self._cancel   = cancel_event
        self._on_done  = on_done

    def start(self):
        self._step()

    def _step(self):
        if self._cancel.is_set():
            return
        processed = 0
        q, seen, roles = self._q, self._seen, self._roles
        while q and self._n < self._maxNodes and processed < _CHUNK:
            o = q.popleft()
            if o is None or id(o) in seen:
                continue
            seen.add(id(o))
            self._n += 1
            processed += 1
            try:
                roles.append(o.role)
            except Exception:
                pass
            try:
                ch = o.firstChild
                while ch:
                    q.append(ch)
                    try: ch = ch.next
                    except Exception: break
            except Exception:
                pass

        if q and self._n < self._maxNodes and not self._cancel.is_set():
            wx.CallLater(_CHUNK_MS, self._step)
        else:
            self._on_done(self._roles)

# ---------------------------------------------------------------------------
# Count + summarise
# ---------------------------------------------------------------------------
def _countRoles(roles):
    c = {"h": 0, "lk": 0, "bt": 0, "fm": 0, "lm": 0}
    for r in roles:
        if   r in _H:  c["h"]  += 1
        elif r in _LK: c["lk"] += 1
        elif r in _BT: c["bt"] += 1
        elif r in _FM: c["fm"] += 1
        elif r in _LM: c["lm"] += 1
    return c

def _summary(c):
    cfg = _cfg(); p = []
    if cfg["reportHeadings"]   and c["h"]  > 0: p.append(f"{c['h']} heading{'s' if c['h']!=1 else ''}")
    if cfg["reportLinks"]      and c["lk"] > 0: p.append(f"{c['lk']} link{'s' if c['lk']!=1 else ''}")
    if cfg["reportButtons"]    and c["bt"] > 0: p.append(f"{c['bt']} button{'s' if c['bt']!=1 else ''}")
    if cfg["reportFormFields"] and c["fm"] > 0: p.append(f"{c['fm']} form field{'s' if c['fm']!=1 else ''}")
    if cfg["reportLandmarks"]  and c["lm"] > 0: p.append(f"{c['lm']} landmark{'s' if c['lm']!=1 else ''}")
    if not p: return "Page loaded."
    if len(p) == 1:
        return f"Page loaded. Page has {p[0]}."
    return "Page loaded. Page has " + ", ".join(p[:-1]) + f", and {p[-1]}."

def _speakResult(roles, cancel_event):
    def _worker():
        if cancel_event.is_set(): return
        c = _countRoles(roles)
        def _speak():
            if cancel_event.is_set(): return
            msg = _summary(c)
            speech.cancelSpeech()
            ui.message(msg)
            if _globalPlugin and _globalPlugin._spaWatcher:
                title = _getBrowserTitle()
                if title:
                    _globalPlugin._spaWatcher.confirmTitle(title)
        queueHandler.queueFunction(queueHandler.eventQueue, _speak)
    threading.Thread(target=_worker, daemon=True, name="PageReporter-count").start()

# ---------------------------------------------------------------------------
# Main announce
# ---------------------------------------------------------------------------
def _announce(tiRef, cancel_event):
    if cancel_event.is_set(): return
    ti = tiRef() if isinstance(tiRef, weakref.ref) else tiRef
    if not ti or not _cfg()["enabled"]: return
    try:
        domain = _getDomain(ti)
        if _isBlocked(domain): return

        roles = _rolesFromFields(ti)
        if roles is not None:
            _speakResult(roles, cancel_event)
            return

        root = ti.rootNVDAObject
        if root is None: return
        def _onWalkDone(roles):
            if not cancel_event.is_set():
                _speakResult(roles, cancel_event)
        _ChunkedWalker(root, cancel_event, _onWalkDone).start()

    except Exception:
        pass

# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
def _scheduleAnnounce(ti, delay_ms=1500):
    current_url  = _getPageIdentity(ti)
    cancel_event, should_schedule = _registerPending(ti, url=current_url)
    if not should_schedule:
        return
    tiRef = weakref.ref(ti)

    def _afterDelay():
        if cancel_event.is_set(): return
        threading.Thread(
            target=_waitThenAnnounce,
            args=(tiRef, cancel_event),
            daemon=True,
            name="PageReporter-busy-wait"
        ).start()

    with _pending_lock:
        global _pending_timer
        _pending_timer = wx.CallLater(delay_ms, _afterDelay)

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------
_orig_loadBufferDone  = None
_orig_docLoadComplete = None

def _isActiveTI(ti):
    """Return True only if ti is the currently focused treeInterceptor."""
    try:
        import api
        focusObj = api.getFocusObject()
        if focusObj is None:
            return False
        # The focused object's treeInterceptor should match
        activeTI = getattr(focusObj, 'treeInterceptor', None)
        if activeTI is ti:
            return True
        # Also accept if the rootNVDAObject of ti contains the focus
        root = getattr(ti, 'rootNVDAObject', None)
        if root is not None:
            obj = focusObj
            while obj is not None:
                if obj == root:
                    return True
                obj = getattr(obj, 'parent', None)
    except Exception:
        pass
    return False

def _installPatch():
    global _orig_loadBufferDone
    try:
        import virtualBuffers
        _orig_loadBufferDone = virtualBuffers.VirtualBuffer._loadBufferDone
        def _patched(self, *args, **kwargs):
            _orig_loadBufferDone(self, *args, **kwargs)
            if _cfg()["enabled"] and _isActiveTI(self):
                if _globalPlugin and _globalPlugin._spaWatcher:
                    _globalPlugin._spaWatcher.updateTI(self)
                _scheduleAnnounce(self)
        virtualBuffers.VirtualBuffer._loadBufferDone = _patched
    except Exception:
        _installFallbackPatch()

def _installFallbackPatch():
    global _orig_docLoadComplete
    try:
        import browseMode
        _orig_docLoadComplete = browseMode.BrowseModeDocumentTreeInterceptor.event_documentLoadComplete
        def _patched(self, obj, nextHandler):
            _orig_docLoadComplete(self, obj, nextHandler)
            if _cfg()["enabled"] and _isActiveTI(self):
                _scheduleAnnounce(self)
        browseMode.BrowseModeDocumentTreeInterceptor.event_documentLoadComplete = _patched
    except Exception:
        pass

def _removePatch():
    global _orig_loadBufferDone, _orig_docLoadComplete
    try:
        if _orig_loadBufferDone is not None:
            import virtualBuffers
            virtualBuffers.VirtualBuffer._loadBufferDone = _orig_loadBufferDone
            _orig_loadBufferDone = None
    except Exception: pass
    try:
        if _orig_docLoadComplete is not None:
            import browseMode
            browseMode.BrowseModeDocumentTreeInterceptor.event_documentLoadComplete = _orig_docLoadComplete
            _orig_docLoadComplete = None
    except Exception: pass

_installPatch()

_globalPlugin = None

# ---------------------------------------------------------------------------
# SPA watcher
# ---------------------------------------------------------------------------
_SPA_POLL_MS  = 400
_SPA_DEBOUNCE = 1.0

def _getBrowserTitle():
    try:
        import winUser
        hwnd = winUser.getForegroundWindow()
        if hwnd:
            return winUser.getWindowText(hwnd) or None
    except Exception:
        pass
    return None

def _normalizeTitle(title):
    if not title:
        return title
    import re
    return re.sub(r'^\(\d+\)\s*', '', title).strip()

class SPAWatcher:
    def __init__(self):
        self._stop           = threading.Event()
        self._ti_ref         = None
        self._last_title     = None
        self._pending_title  = None
        self._pending_since  = 0.0
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PageReporter-SPA")
        self._thread.start()

    def setActiveTI(self, ti):
        self._ti_ref = weakref.ref(ti) if ti is not None else None

    def updateTI(self, ti):
        self._ti_ref = weakref.ref(ti) if ti is not None else None

    def confirmTitle(self, title):
        title = _normalizeTitle(title)
        self._last_title    = title
        self._pending_title = None

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(_SPA_POLL_MS / 1000.0):
            try:
                self._tick()
            except Exception:
                pass

    def _tick(self):
        import time
        if not _cfg().get("enabled", True): return
        if self._ti_ref is None:
            return
        ti = self._ti_ref()
        if ti is None: return

        raw_title = _getBrowserTitle()
        title = _normalizeTitle(raw_title)

        if not title: return
        if title == self._last_title:
            self._pending_title = None
            return

        now = time.monotonic()
        if title != self._pending_title:
            self._pending_title  = title
            self._pending_since  = now
            return

        if now - self._pending_since >= _SPA_DEBOUNCE:
            self._last_title    = title
            self._pending_title = None
            ti2 = self._ti_ref() if self._ti_ref else None
            if ti2:
                wx.CallAfter(_scheduleAnnounce, ti2, 500)

# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------
class PageReporterSettingsPanel(SettingsPanel):
    title = "Page Reporter"

    def makeSettings(self, settingsSizer):
        helper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
        self.enabledCb = helper.addItem(wx.CheckBox(self, label="&Enable Page Reporter (NVDA+Shift+W)"))
        self.enabledCb.SetValue(_cfg()["enabled"])
        eb = guiHelper.BoxSizerHelper(self, sizer=wx.StaticBoxSizer(wx.StaticBox(self, label="Report these elements:"), wx.VERTICAL))
        helper.addItem(eb.sizer)
        self.hCb  = eb.addItem(wx.CheckBox(self, label="&Headings"));    self.hCb.SetValue(_cfg()["reportHeadings"])
        self.lkCb = eb.addItem(wx.CheckBox(self, label="&Links"));       self.lkCb.SetValue(_cfg()["reportLinks"])
        self.btCb = eb.addItem(wx.CheckBox(self, label="&Buttons"));     self.btCb.SetValue(_cfg()["reportButtons"])
        self.fmCb = eb.addItem(wx.CheckBox(self, label="&Form fields")); self.fmCb.SetValue(_cfg()["reportFormFields"])
        self.lmCb = eb.addItem(wx.CheckBox(self, label="L&andmarks"));   self.lmCb.SetValue(_cfg()["reportLandmarks"])
        sb = guiHelper.BoxSizerHelper(self, sizer=wx.StaticBoxSizer(wx.StaticBox(self, label="Disabled sites (one per line e.g. youtube.com):"), wx.VERTICAL))
        helper.addItem(sb.sizer)
        raw = _cfg().get("blockedSites", "")
        self.siteCtrl = sb.addItem(wx.TextCtrl(self, value="\n".join(s.strip() for s in raw.split(",") if s.strip()), style=wx.TE_MULTILINE, size=(-1, 80)))

    def onSave(self):
        # Write only to our own JSON — never touches NVDA's config
        _config["enabled"]          = self.enabledCb.GetValue()
        _config["reportHeadings"]   = self.hCb.GetValue()
        _config["reportLinks"]      = self.lkCb.GetValue()
        _config["reportButtons"]    = self.btCb.GetValue()
        _config["reportFormFields"] = self.fmCb.GetValue()
        _config["reportLandmarks"]  = self.lmCb.GetValue()
        _config["blockedSites"]     = ",".join(s.strip().lower() for s in self.siteCtrl.GetValue().splitlines() if s.strip())
        _saveConfig()

# ---------------------------------------------------------------------------
# GlobalPlugin
# ---------------------------------------------------------------------------
class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    __gestures = {"kb:NVDA+shift+w": "togglePageReporter"}

    def __init__(self, *args, **kwargs):
        global _globalPlugin
        super().__init__(*args, **kwargs)
        gui.NVDASettingsDialog.categoryClasses.append(PageReporterSettingsPanel)
        self._spaWatcher = SPAWatcher()
        _globalPlugin = self

    def terminate(self):
        self._spaWatcher.stop()
        with _pending_lock:
            for ev, _, _ts in _pending.values():
                ev.set()
            _pending.clear()
        _removePatch()
        try:
            gui.NVDASettingsDialog.categoryClasses.remove(PageReporterSettingsPanel)
        except ValueError: pass
        super().terminate()

    def script_togglePageReporter(self, gesture):
        s = not _cfg()["enabled"]
        _config["enabled"] = s
        _saveConfig()  # saves to JSON only — does NOT touch nvda.ini
        ui.message(f"Page Reporter {'on' if s else 'off'}.")
    script_togglePageReporter.__doc__ = "Toggle Page Reporter on or off."

    def event_treeInterceptor_gainFocus(self, treeInterceptor, nextHandler):
        nextHandler()
        self._spaWatcher.setActiveTI(treeInterceptor)
