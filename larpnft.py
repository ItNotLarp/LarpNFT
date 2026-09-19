__id__ = "larpnft"
__name__ = "larpnft"
__description__ = "я - бог ксививайда,ратка - сидит на твоем телефоне"
__version__ = "1.0.0"
__author__ = "@larpplugins и дипсик"
__icon__ = "SvoZov77/15"
__app_version__ = ">=11.12.0"
__sdk_version__ = ">=1.4.0"

import time
import json
import base64
import threading
from java import dynamic_proxy, jclass
from java.util import ArrayList
from org.telegram.tgnet import TLRPC
from org.telegram.messenger import (
    UserConfig, MessagesController, MessagesStorage,
    MessageObject, ApplicationLoader, AndroidUtilities,
    NotificationCenter,
)
from base_plugin import BasePlugin, MethodHook
from android_utils import run_on_ui_thread
from ui.bulletin import BulletinHelper
from client_utils import get_last_fragment
from hook_utils import find_class

VISUAL_TAB_ID = 1700949999
FLAG_OUT = 2
FLAG_FROM_ID = 256
GIFT_SHEET = "org.telegram.ui.Gifts.GiftSheet"
TABS_FACTORY = "org.telegram.ui.Gifts.GiftSheet$Tabs$Factory"
GIFT_CELL_FACTORY = "org.telegram.ui.Gifts.GiftSheet$GiftCell$Factory"
SEND_GIFT_SHEET = "org.telegram.ui.Gifts.SendGiftSheet"
STAR_GIFT_SHEET = "org.telegram.ui.Stars.StarGiftSheet"
STARS_CTRL = "org.telegram.ui.Stars.StarsController"
LAUNCH_ACTIVITY = "org.telegram.ui.LaunchActivity"
CONNECTIONS = "org.telegram.tgnet.ConnectionsManager"
NOTIF_CTRL = "org.telegram.messenger.NotificationsController"

HOLD_ICON = 6291816386410847066
MAJOR_ICON = 6016937066422604737
HOLD_DESC = "Аккаунт верифицирован организацией «Hold»."
MAJOR_DESC = "Аккаунт верифицирован организацией «Major»."
TL_BOT_VERIF = "org.telegram.tgnet.tl.TL_bots$botVerification"
RATING_CLASSES = (
    "org.telegram.tgnet.tl.TL_stars$Tl_starsRating",
    "org.telegram.tgnet.tl.TL_stars$TL_starsRating",
    "org.telegram.tgnet.TLRPC$TL_starsRating",
)
FLAGS2_RATING = 131072

_BAD_MSG = (
    "осталось", "remaining", "именем отправителя", "with sender",
    "аноним", "anonymous", "скрыть", "hide sender", "send anonymously",
    "от кого", "from whom", "продано", "sold", "преимуществ",
    "уникальных", "для получения", "visual", "оригинал",
)

_pending_dialog = 0
_pending_dialog_ts = 0.0
SERVER_URL = "https://visual.hiniw44549.workers.dev"
PLUGIN_KEY = "vg_secret_7f9a2kLmX9pQ2026"
POLL_MIN = 4
POLL_MAX = 22
POLL_AFTER_RECEIVE = 10


def _cls(name):
    try:
        c = find_class(name)
        if c is not None:
            return c
    except Exception:
        pass
    try:
        return jclass(name)
    except Exception:
        return None


def _run_ui(fn, delay=0):
    try:
        r = dynamic_proxy(jclass("java.lang.Runnable"))(type("R", (), {"run": lambda s: fn()})())
        if delay > 0:
            AndroidUtilities.runOnUIThread(r, delay)
        else:
            AndroidUtilities.runOnUIThread(r)
    except Exception:
        try:
            run_on_ui_thread(fn)
        except Exception:
            pass


def _find_method(cls, name, param_count=None):
    if cls is None:
        return None
    try:
        for m in cls.getDeclaredMethods():
            if m.getName() == name:
                if param_count is None or len(m.getParameterTypes()) == param_count:
                    m.setAccessible(True)
                    return m
        for m in cls.getMethods():
            if m.getName() == name:
                if param_count is None or len(m.getParameterTypes()) == param_count:
                    return m
    except Exception:
        pass
    return None


def _find_field(obj_or_cls, name):
    try:
        cls = obj_or_cls if hasattr(obj_or_cls, "getDeclaredFields") else obj_or_cls.getClass()
    except Exception:
        cls = None
    if cls is None:
        return None
    try:
        for c in (cls,):
            try:
                f = c.getDeclaredField(name)
                f.setAccessible(True)
                return f
            except Exception:
                pass
            try:
                f = c.getField(name)
                f.setAccessible(True)
                return f
            except Exception:
                pass
    except Exception:
        pass
    return None


def _new_instance(cls):
    
    if cls is None:
        return None
    try:
        return cls()
    except Exception:
        pass
    try:
        ctor = cls.getDeclaredConstructor()
        ctor.setAccessible(True)
        return ctor.newInstance()
    except Exception:
        pass
    try:
        return cls.newInstance()
    except Exception:
        pass
    return None


def _is_gift(obj):
    if obj is None:
        return False
    try:
        n = str(obj.getClass().getName())
    except Exception:
        return False
    for b in ("Action", "Sheet", "Controller", "Fragment", "Message", "GiftSheet", "Saved"):
        if b in n and "TL_starGift" not in n and "StarGift" not in n:
            return False
    for g in ("TL_starGift", "TL_stars$TL_starGift", "tl.TL_stars$StarGift",
              "tl.TL_stars$TL_starGift", "$StarGift", "StarGiftUnique"):
        if g in n:
            return True
    try:
        sn = obj.getClass().getSimpleName()
        if sn in ("TL_starGift", "TL_starGiftUnique", "StarGift", "StarGiftUnique"):
            return True
        if sn.startswith("TL_starGift"):
            return True
    except Exception:
        pass
    return False


def _is_unique(gift):
    if gift is None:
        return False
    try:
        if "unique" in gift.getClass().getSimpleName().lower():
            return True
    except Exception:
        pass
    try:
        if "unique" in str(gift.getClass().getName()).lower():
            return True
    except Exception:
        pass
    for attr in ("slug", "num", "attributes"):
        try:
            v = getattr(gift, attr, None)
            if attr == "slug" and v and str(v).strip():
                return True
            if attr == "num" and v is not None and int(v) > 0:
                return True
            if attr == "attributes" and v is not None and hasattr(v, "size") and int(v.size()) > 0:
                return True
        except Exception:
            pass
    return False


def _extract_gift(obj):
    if obj is None:
        return None
    if _is_gift(obj):
        return obj
    for fname in ("starGift", "gift", "selectedGift", "currentGift", "mGift",
                  "uniqueGift", "giftUnique", "toGift", "resaleGift", "savedGift"):
        try:
            g = getattr(obj, fname, None)
            if g is None:
                continue
            if _is_gift(g):
                return g
            try:
                inner = getattr(g, "gift", None)
                if _is_gift(inner):
                    return inner
            except Exception:
                pass
        except Exception:
            pass
    try:
        cls = obj.getClass()
        for _ in range(6):
            if cls is None or str(cls.getName()) == "java.lang.Object":
                break
            try:
                for f in cls.getDeclaredFields():
                    try:
                        f.setAccessible(True)
                        val = f.get(obj)
                        if _is_gift(val):
                            return val
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception:
        pass
    return None


def _bad_text(s):
    if not s:
        return True
    low = s.lower().strip()
    if len(low) < 1 or (low.isdigit() and len(low) <= 4):
        return True
    for b in _BAD_MSG:
        if b in low:
            return True
    return False


def _extract_message(sheet):
    if sheet is None:
        return " "
    obj = None
    try:
        cls = sheet.getClass()
        for _ in range(8):
            if cls is None or str(cls.getName()) == "java.lang.Object":
                break
            for getter in ("getDeclaredMethod", "getMethod"):
                try:
                    m = getattr(cls, getter)("getMessage")
                    m.setAccessible(True)
                    obj = m.invoke(sheet)
                    if obj is not None:
                        break
                except Exception:
                    pass
            if obj is not None:
                break
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception:
        pass
    if obj is None:
        try:
            action = getattr(sheet, "action", None)
            if action is not None:
                obj = getattr(action, "message", None)
        except Exception:
            pass
    if obj is None:
        try:
            obj = getattr(sheet, "message", None)
        except Exception:
            pass
    if obj is None:
        return " "
    try:
        t = getattr(obj, "text", None)
        if t is not None:
            s = str(t).strip()
            if s and not _bad_text(s):
                return s
    except Exception:
        pass
    try:
        s = str(obj).strip()
        if s and not s.startswith("org.telegram") and "Object@" not in s and not _bad_text(s) and len(s) < 500:
            return s
    except Exception:
        pass
    return " "


def _extract_anonymous(obj):
    if obj is None:
        return False
    for fname in ("anonymous", "isAnonymous", "anon", "hideSender", "senderHidden", "nameHidden"):
        try:
            v = getattr(obj, fname, None)
            if v is not None:
                return bool(v)
        except Exception:
            pass
    for mname in ("isAnonymous", "getAnonymous", "isHideSender", "isNameHidden"):
        try:
            m = obj.getClass().getDeclaredMethod(mname)
            m.setAccessible(True)
            return bool(m.invoke(obj))
        except Exception:
            pass
    return False


def _extract_dialog_id(obj):
    if obj is None:
        return 0
    for fname in (
        "dialogId", "dialog_id", "currentDialogId", "selectedDialogId",
        "userId", "user_id", "chatId", "chat_id", "to_id", "toId",
        "mDialogId",
    ):
        try:
            v = getattr(obj, fname, None)
            if v is None:
                continue
            try:
                uid = getattr(v, "user_id", None)
                if uid is not None and abs(int(uid)) > 1000:
                    return int(uid)
            except Exception:
                pass
            try:
                cid = getattr(v, "chat_id", None)
                if cid is not None and abs(int(cid)) > 1000:
                    return -abs(int(cid))
            except Exception:
                pass
            try:
                iv = int(v)
                if abs(iv) > 1000:
                    return iv
            except Exception:
                pass
        except Exception:
            pass
    for mname in ("getDialogId", "getPeerId", "getUserId", "getChatId", "getId"):
        try:
            m = obj.getClass().getMethod(mname)
            m.setAccessible(True)
            res = m.invoke(obj)
            if res is None:
                continue
            try:
                uid = getattr(res, "user_id", None)
                if uid is not None and abs(int(uid)) > 1000:
                    return int(uid)
            except Exception:
                pass
            try:
                iv = int(res)
                if abs(iv) > 1000:
                    return iv
            except Exception:
                pass
        except Exception:
            pass
    try:
        cls = obj.getClass()
        for _ in range(5):
            if cls is None or str(cls.getName()) == "java.lang.Object":
                break
            for f in cls.getDeclaredFields():
                try:
                    t = str(f.getType().getName())
                    if t not in ("long", "java.lang.Long", "int", "java.lang.Integer"):
                        continue
                    name = f.getName().lower()
                    if not any(k in name for k in ("dialog", "user", "chat", "peer", "to_id", "toid")):
                        continue
                    f.setAccessible(True)
                    v = f.get(obj)
                    if v is None:
                        continue
                    iv = int(v)
                    if abs(iv) > 1000:
                        return iv
                except Exception:
                    continue
            try:
                cls = cls.getSuperclass()
            except Exception:
                break
    except Exception:
        pass
    return 0


def _remember_dialog(did):
    global _pending_dialog, _pending_dialog_ts
    try:
        did = int(did or 0)
        if abs(did) > 1000:
            _pending_dialog = did
            _pending_dialog_ts = time.time()
    except Exception:
        pass


def _get_pending():
    try:
        if abs(_pending_dialog) > 1000 and (time.time() - _pending_dialog_ts) < 180:
            return _pending_dialog
    except Exception:
        pass
    return 0


def _dismiss_sheet(sheet):
    def _do():
        try:
            if sheet is not None:
                for m in ("dismiss", "lambdaDismiss", "finish", "closeParentSheet",
                          "onDismiss", "dismissInternal", "cancel"):
                    try:
                        fn = getattr(sheet, m, None)
                        if callable(fn):
                            fn()
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            la = _cls(LAUNCH_ACTIVITY)
            inst = getattr(la, "instance", None) if la else None
            if inst is not None:
                for _ in range(6):
                    try:
                        d = getattr(inst, "visibleDialog", None)
                        if d is not None and callable(getattr(d, "dismiss", None)):
                            d.dismiss()
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            frag = get_last_fragment()
            if frag is not None:
                for _ in range(6):
                    try:
                        d = getattr(frag, "visibleDialog", None)
                        if d is not None and callable(getattr(d, "dismiss", None)):
                            d.dismiss()
                    except Exception:
                        pass
        except Exception:
            pass
    _run_ui(_do, 0)
    _run_ui(_do, 40)
    _run_ui(_do, 100)


def _return_to_chat(dialog_id):
    try:
        dialog_id = int(dialog_id or 0)
    except Exception:
        return
    if abs(dialog_id) <= 1000:
        return
    def _do_return():
        try:
            la = _cls(LAUNCH_ACTIVITY)
            inst = getattr(la, "instance", None) if la else None
            if inst is None:
                return
            for _ in range(8):
                try:
                    d = getattr(inst, "visibleDialog", None)
                    if d is not None and callable(getattr(d, "dismiss", None)):
                        d.dismiss()
                except Exception:
                    pass
            try:
                frag = get_last_fragment()
                for _ in range(10):
                    if frag is None:
                        break
                    name = ""
                    try:
                        name = str(frag.getClass().getName())
                    except Exception:
                        break
                    if any(x in name for x in (
                        "Gift", "Stars", "Sheet", "Profile", "Market",
                        "StarGift", "SendGift", "BottomSheet"
                    )):
                        try:
                            if callable(getattr(frag, "finishFragment", None)):
                                frag.finishFragment()
                        except Exception:
                            pass
                        try:
                            if callable(getattr(frag, "finish", None)):
                                frag.finish()
                        except Exception:
                            pass
                        try:
                            frag = get_last_fragment()
                        except Exception:
                            break
                    else:
                        break
            except Exception:
                pass
            for _ in range(4):
                try:
                    d = getattr(inst, "visibleDialog", None)
                    if d is not None and callable(getattr(d, "dismiss", None)):
                        d.dismiss()
                except Exception:
                    pass
            try:
                ChatAct = _cls("org.telegram.ui.ChatActivity")
                if ChatAct is None:
                    return
                bundle_cls = _cls("android.os.Bundle")
                if bundle_cls is None:
                    return
                bundle = bundle_cls()
                if dialog_id > 0:
                    bundle.putLong("user_id", int(dialog_id))
                else:
                    bundle.putLong("chat_id", abs(int(dialog_id)))
                chat_frag = ChatAct(bundle)
                if callable(getattr(inst, "presentFragment", None)):
                    try:
                        inst.presentFragment(chat_frag, True, True)
                    except Exception:
                        try:
                            inst.presentFragment(chat_frag, True)
                        except Exception:
                            try:
                                inst.presentFragment(chat_frag)
                            except Exception:
                                pass
            except Exception:
                pass
        except Exception:
            pass
    _run_ui(_do_return, 60)
    _run_ui(_do_return, 180)
    _run_ui(_do_return, 320)


def _http(method, url, body=None, headers=None, timeout=10):
    try:
        URL = jclass("java.net.URL")
        conn = URL(url).openConnection()
        conn.setConnectTimeout(timeout * 1000)
        conn.setReadTimeout(timeout * 1000)
        conn.setRequestMethod(method)
        conn.setDoInput(True)
        if headers:
            for k, v in headers.items():
                conn.setRequestProperty(str(k), str(v))
        if body is not None:
            conn.setDoOutput(True)
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            out = conn.getOutputStream()
            data = body.encode("utf-8") if isinstance(body, str) else body
            out.write(data)
            out.flush()
            out.close()
        code = int(conn.getResponseCode())
        stream = None
        try:
            stream = conn.getInputStream() if code < 400 else conn.getErrorStream()
        except Exception:
            pass
        text = " "
        if stream is not None:
            baos = jclass("java.io.ByteArrayOutputStream")()
            buf = jclass("[B")(4096)
            while True:
                n = stream.read(buf)
                if n < 0:
                    break
                baos.write(buf, 0, n)
            stream.close()
            text = bytes(baos.toByteArray()).decode("utf-8", errors="ignore")
        return code, text
    except Exception as e:
        return -1, str(e)


def _serialize_gift(gift):
    if gift is None:
        return None
    try:
        SerData = _cls("org.telegram.tgnet.SerializedData")
        if SerData is None:
            return None
        Saved = _cls("org.telegram.tgnet.tl.TL_stars$TL_savedStarGift")
        if Saved is None:
            Saved = _cls("org.telegram.tgnet.TLRPC$TL_savedStarGift")
        if Saved is not None:
            try:
                saved = _new_instance(Saved)
                if saved is None:
                    saved = Saved()
                ok = False
                try:
                    saved.gift = gift
                    ok = True
                except Exception:
                    try:
                        f = saved.getClass().getDeclaredField("gift")
                        f.setAccessible(True)
                        f.set(saved, gift)
                        ok = True
                    except Exception:
                        pass
                if ok:
                    m = _find_method(saved.getClass(), "serializeToStream", 1)
                    if m is not None:
                        size = 8192
                        try:
                            sm = _find_method(saved.getClass(), "getObjectSize", 0)
                            if sm:
                                s = sm.invoke(saved)
                                if s is not None:
                                    size = max(256, int(s))
                        except Exception:
                            pass
                        sd = SerData(int(size))
                        m.invoke(saved, sd)
                        arr = sd.toByteArray()
                        if arr is not None and len(arr) > 0:
                            return base64.b64encode(bytes(arr)).decode("ascii")
            except Exception:
                pass
            try:
                m = _find_method(gift.getClass(), "serializeToStream", 1)
                if m is not None:
                    size = 4096
                    try:
                        sm = _find_method(gift.getClass(), "getObjectSize", 0)
                        if sm:
                            s = sm.invoke(gift)
                            if s is not None:
                                size = max(256, int(s))
                    except Exception:
                        pass
                    sd = SerData(int(size))
                    m.invoke(gift, sd)
                    arr = sd.toByteArray()
                    if arr is not None and len(arr) > 0:
                        return base64.b64encode(bytes(arr)).decode("ascii")
            except Exception:
                pass
        return None
    except Exception:
        return None


def _deserialize_gift(b64):
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64.strip())
        SerData = _cls("org.telegram.tgnet.SerializedData")
        if SerData is None:
            return None
        for sname in (
            "org.telegram.tgnet.tl.TL_stars$TL_savedStarGift",
            "org.telegram.tgnet.TLRPC$TL_savedStarGift",
        ):
            Saved = _cls(sname)
            if Saved is None:
                continue
            try:
                sd = SerData(raw)
                ctor = int(sd.readInt32(False))
                m = _find_method(Saved, "TLdeserialize", 3)
                if m is not None:
                    obj = m.invoke(None, sd, ctor, False)
                    if obj is not None:
                        g = getattr(obj, "gift", None)
                        if g is not None and _is_gift(g):
                            return g
                    if _is_gift(obj):
                        return obj
            except Exception:
                pass
            try:
                sd2 = SerData(raw)
                sd2.readInt32(False)
                obj = _new_instance(Saved)
                if obj is None:
                    obj = Saved()
                m = _find_method(obj.getClass(), "readParams", 2)
                if m is not None:
                    m.invoke(obj, sd2, False)
                    g = getattr(obj, "gift", None)
                    if g is not None and _is_gift(g):
                        return g
            except Exception:
                pass
        for gname in (
            "org.telegram.tgnet.tl.TL_stars$TL_starGift",
            "org.telegram.tgnet.TLRPC$TL_starGift",
            "org.telegram.tgnet.tl.TL_stars$TL_starGiftUnique",
            "org.telegram.tgnet.TLRPC$TL_starGiftUnique",
        ):
            Cls = _cls(gname)
            if Cls is None:
                continue
            try:
                sd = SerData(raw)
                ctor = int(sd.readInt32(False))
                m = _find_method(Cls, "TLdeserialize", 3)
                if m is not None:
                    obj = m.invoke(None, sd, ctor, False)
                    if obj is not None and _is_gift(obj):
                        return obj
            except Exception:
                pass
        return None
    except Exception:
        return None


class FillHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def after_hooked_method(self, param):
        try:
            this = param.thisObject
            d = _extract_dialog_id(this)
            if abs(d) > 1000:
                _remember_dialog(d)
            else:
                try:
                    frag = get_last_fragment()
                    d2 = _extract_dialog_id(frag)
                    if abs(d2) > 1000:
                        _remember_dialog(d2)
                except Exception:
                    pass
            self.plugin.on_fill_items(param)
        except Exception:
            pass


class BuyHook(MethodHook):
    def __init__(self, plugin, tag=""):
        self.plugin = plugin
        self.tag = tag

    def before_hooked_method(self, param):
        if not getattr(self.plugin, "visual_mode", False):
            return
        try:
            this = param.thisObject
            args = list(param.args) if param.args else []
            gift = None
            dialog_id = 0
            anonymous = False
            if this is not None:
                gift = _extract_gift(this)
                dialog_id = _extract_dialog_id(this)
                anonymous = _extract_anonymous(this)
            for a in args:
                if a is None:
                    continue
                g = _extract_gift(a)
                if g is not None:
                    gift = g
                try:
                    v = int(a)
                    if abs(v) > 10000:
                        dialog_id = v
                except Exception:
                    pass
                d2 = _extract_dialog_id(a)
                if abs(d2) > 1000:
                    dialog_id = d2
            my = 0
            try:
                my = int(UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId())
            except Exception:
                my = 0

            def _valid_peer(d, allow_self=True):
                try:
                    d = int(d or 0)
                except Exception:
                    return 0
                if abs(d) <= 1000:
                    return 0
                return d

            def _chat_dialog():
                try:
                    frag = get_last_fragment()
                    if frag is None:
                        return 0
                    try:
                        name = str(frag.getClass().getName())
                    except Exception:
                        return 0
                    if "ChatActivity" not in name:
                        return 0
                    try:
                        m = frag.getClass().getMethod("getDialogId")
                        return _valid_peer(m.invoke(frag))
                    except Exception:
                        return _valid_peer(_extract_dialog_id(frag))
                except Exception:
                    return 0

            dialog_id = _valid_peer(dialog_id)
            if not dialog_id:
                dialog_id = _chat_dialog()
            if not dialog_id:
                dialog_id = _valid_peer(_get_pending())
            if not dialog_id:
                dialog_id = _valid_peer(self.plugin.resolve_dialog())
            message = _extract_message(this)
            if gift is None:
                return
            if not dialog_id:
                return
            unique = _is_unique(gift)
            try:
                param.setResult(None)
            except Exception:
                pass
            self.plugin._log("BuyHook: intercepting send for dialog=%s, unique=%s" % (dialog_id, unique))
            _dismiss_sheet(this)
            self.plugin.send_visual(gift, dialog_id, unique, anonymous, message)
            _return_to_chat(dialog_id)
        except Exception:
            pass


class LarpnftPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self._hooks = []
        self.visual_mode = True
        self._cb = None
        self.inject_count = 0
        self._last_dialog = 0
        self._busy = False
        self._poll_thread = None
        self._poll_stop = False
        self._seen_events = set()
        self._fail_count = {}
        self._poll_interval = POLL_MIN
        self._empty_streak = 0
        self._local_profile_gifts = {}
        self._profile_hook_done = False
        self._req_hook_done = False
        self._fw_last = 0.0
        self._pending_confetti = set()
        self._remote_ratings = {}
        self._pending_rating_requests = set()
        self._gift_cell_factory = None
        self._tabs_factory = None
        self._tabs_factory_instance = None

    def create_settings(self):
        items = []
        try:
            from ui.settings import Header, Switch, Selector, Input, Text
        except Exception as e:
            self._log("settings import fail: %s" % e)
            return []

        def add(*rows):
            for r in rows:
                if r is not None:
                    items.append(r)

        try:
            add(
                Header(text="larpnft"),
                Switch(key="confetti", text="Конфетти", subtext="При отправке и получении", default=True),
                Switch(key="sync_enabled", text="Синхронизация",
                       subtext="Отправка и получение через сервер", default=True),
            )
        except Exception as e:
            self._log("settings base fail: %s" % e)
        try:
            add(Header(text="Баланс звёзд"))
            add(Switch(key="custom_balance", text="Подмена баланса звезд",
                       subtext="Только звёзды", default=False))
            add(Input(key="balance_value", text="Звёзды",
                      default="67", subtext="Целое число (например 67)"))
            add(Switch(key="custom_gram", text="Подмена баланса грам",
                       subtext="Отдельно от звезд", default=False))
            add(Input(key="gram_value", text="Gram",
                      default="0", subtext="Число (77 → 77.0)"))
        except Exception as e:
            self._log("settings balance fail: %s" % e)
        try:
            add(Header(text="Рейтинг"))
            add(Switch(key="custom_rating", text="Подмена рейтинга",
                       subtext="Показывать свой рейтинг", default=False))
            add(Input(key="rating_stars", text="звезды", default="150000",
                      subtext="Текущее количество звезд"))
            add(Input(key="rating_level", text="Уровень", default="10",
                      subtext="Уровень рейтинга"))
            add(Input(key="rating_next", text="До след уровня", default="200000",
                      subtext="Порог следующего уровня"))
        except Exception as e:
            self._log("settings rating fail: %s" % e)
        try:
            add(Header(text="Бейдж"))
            try:
                add(Selector(key="badge_mode", text="Бейдж верификации",
                             default=0, items=["Нет", "Hold", "Major"]))
            except Exception:
                add(Input(key="badge_mode", text="Бейдж (0=нет,1=Hold,2=Major)", default="0"))
        except Exception as e:
            self._log("settings badge fail: %s" % e)
        try:
            add(Header(text="Номер телефона"))
            add(Switch(key="custom_number", text="Подмена номера",
                       subtext="Визуальный номер", default=False))
            add(Input(key="phone_number", text="Номер", default="88812345678",
                      subtext="Только цифры рекомендуется 888..."))
        except Exception as e:
            self._log("settings phone fail: %s" % e)
        try:
            add(Header(text="нфт юзернеймы"))
            names = self._visual_usernames()
            add(
                Switch(
                    key="custom_visual_username",
                    text="Подмена нфт юзернейма",
                    subtext=self._visual_username_status(),
                    default=self._bool("custom_visual_username", False),
                    on_change=self._visual_username_switch,
                ),
                Text(
                    text="Добавить нфт юзернеймы",
                    subtext="Можно указать несколько через запятую",
                    on_click=lambda _: self._input(
                        "юзернеймы (через запятую)", "", self._add_visual_usernames
                    ),
                ),
                Text(
                    text="Выданные юзернеймы",
                    subtext="%d сохранено" % len(names),
                    on_click=lambda _: self._show_visual_username_list(names),
                ),
            )
            if names:
                add(Header(text="Сохранённые нфт юзернеймы"))
                for name in names:
                    add(Text(
                        text="@" + name,
                        subtext="Визуальный нфт юзернейм",
                    ))
                add(Text(
                    text="Очистить всё",
                    subtext="Удалить все юзернеймы",
                    red=True,
                    on_click=lambda _: self._clear_visual_usernames(),
                ))
            else:
                add(Text(
                    text="Нет выданных юзернеймов",
                    subtext="Нажми «Добавить», чтобы создать первый",
                ))
        except Exception as e:
            self._log("settings username fail: %s" % e)

        try:
            add(Header(text="Синхронизация профиля"))
            add(Text(text="Синхронизировать профиль",
                     subtext="Отправить настройки на сервер и применить чужие",
                     on_click=self._sync_profile_click))
        except Exception as e:
            self._log("settings sync btn fail: %s" % e)
        try:
            add(Header(text="Логи"))
            add(Switch(key="debug_log", text="Подробные логи",
                       subtext="Писать отладочные сообщения в буфер", default=False))
            try:
                add(Text(text="Отправить логи",
                         subtext="Нажми, чтобы поделиться логами",
                         on_click=self._share_logs_click))
            except Exception:
                try:
                    add(Text(text="Отправить логи (см. буфер)",
                             subtext=self._log_path() or "лог-буфер"))
                except Exception:
                    pass
            try:
                add(Text(text="Очистить логи",
                         subtext="Удалить сохранённый лог-файл",
                         on_click=self._clear_logs_click))
            except Exception:
                pass
        except Exception as e:
            try:
                self._log("settings logs fail: %s" % e)
            except Exception:
                pass
        return items

    def _bool(self, key, default=False):
        try:
            v = self.get_setting(key, default)
            if v is None:
                return bool(default)
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return int(v) != 0
            s = str(v).strip().lower()
            if s in ("1", "true", "yes", "on", "y"):
                return True
            if s in ("0", "false", "no", "off", "n", ""):
                return False
            return bool(v)
        except Exception:
            return bool(default)

    def _save_dialog(self, did):
        try:
            did = int(did or 0)
            if abs(did) < 1000:
                return
            self._last_dialog = did
            try:
                self.set_setting("last_dialog_id", did)
            except Exception:
                pass
        except Exception:
            pass

    def on_plugin_load(self):
        try:
            saved = int(self.get_setting("last_dialog_id", 0) or 0)
            if abs(saved) > 1000:
                self._last_dialog = saved
        except Exception:
            pass
        try:
            self._gift_cell_factory = _cls(GIFT_CELL_FACTORY)
            self._tabs_factory = _cls(TABS_FACTORY)
            if self._tabs_factory is not None:
                self._tabs_factory_instance = _new_instance(self._tabs_factory)
            self._log("Factories: GiftCell=%s, Tabs=%s, TabsInst=%s" % (
                self._gift_cell_factory is not None,
                self._tabs_factory is not None,
                self._tabs_factory_instance is not None))
        except Exception as e:
            self._log("Factories init error: %s" % e)
        self._hook_fill()
        self._hook_buy()
        if self._bool("sync_enabled", True):
            try:
                self._start_poll()
            except Exception:
                pass
        self._hook_send_request()
        self._hook_gifts_list_notify()
        self._hook_user_full_apply()
        self._hook_profile_rows()
        self._hook_chat_visible()
        self._hook_balance_bypass()
        self._hook_identity()
        self._hook_profile_rating_ui()
        try:
            self._paint_self_cache()
        except Exception:
            pass
        try:
            _run_ui(lambda: self._paint_self_cache(), 400)
            _run_ui(lambda: self._post_user_info_did_load("load"), 600)
        except Exception:
            pass
        if self._bool("sync_enabled", True):
            _run_ui(lambda: self._push_identity_to_server(), 800)
        try:
            self._log(
                "plugin loaded v%s bal=%s(%s) gram=%s(%s) rating=%s badge=%s number=%s"
                % (
                    __version__,
                    self._bool("custom_balance", False),
                    self.get_setting("balance_value", ""),
                    self._bool("custom_gram", False),
                    self.get_setting("gram_value", ""),
                    self._bool("custom_rating", False),
                    self._badge_mode(),
                    self._bool("custom_number", False),
                ),
                force=True,
            )
        except Exception:
            try:
                self._log("plugin loaded v%s" % __version__, force=True)
            except Exception:
                pass

    def on_plugin_unload(self):
        self._poll_stop = True
        self._level_poll_stop = True
        for h in self._hooks:
            try:
                self.unhook_method(h)
            except Exception:
                pass
        self._hooks.clear()

    def _hook_fill(self):
        gs = _cls(GIFT_SHEET)
        if gs is None:
            return
        try:
            refs = self.hook_all_methods(gs, "fillItems", FillHook(self))
            if refs:
                self._hooks.extend(refs if isinstance(refs, list) else [refs])
        except Exception:
            pass

    def _hook_buy(self):
        for m in ("buyStarGift", "buyGift", "sendStarGift", "buyResaleGift"):
            self._try_hook(STARS_CTRL, m, BuyHook(self, "SC.%s" % m))
        for m in ("buyStarGift", "send", "sendGift", "onSendPressed"):
            self._try_hook(SEND_GIFT_SHEET, m, BuyHook(self, "SGS.%s" % m))
        for m in ("onBuyPressed", "buy", "buyPressed", "send"):
            self._try_hook(STAR_GIFT_SHEET, m, BuyHook(self, "SG.%s" % m))

    def _try_hook(self, cls_name, method, hook):
        c = _cls(cls_name)
        if c is None:
            return
        try:
            refs = self.hook_all_methods(c, method, hook)
            if refs:
                self._hooks.extend(refs if isinstance(refs, list) else [refs])
        except Exception:
            pass

    def on_fill_items(self, param):
        try:
            args = param.args
            if not args:
                return
            items = args[0]
            if items is None:
                return
            try:
                size = int(items.size())
            except Exception:
                return
            for i in range(size):
                try:
                    it = items.get(i)
                    if it is not None and int(getattr(it, "id", 0) or 0) == VISUAL_TAB_ID:
                        return
                except Exception:
                    pass
            insert_at = -1
            for i in range(size):
                try:
                    it = items.get(i)
                    obj = getattr(it, "object", None) if it else None
                    if obj is not None and hasattr(obj, "size") and int(obj.size()) > 0:
                        first = obj.get(0)
                        if isinstance(first, str):
                            insert_at = i
                            break
                except Exception:
                    pass
            tab = self._make_tabs()
            if tab is None:
                return
            try:
                items.add(insert_at if insert_at >= 0 else min(1, size), tab)
                self.inject_count += 1
            except Exception:
                pass
        except Exception:
            pass

    def _make_tabs(self):
        try:
            labels = ArrayList()
            labels.add("@larpplugins")
            labels.add("Оригинал")
            factory = self._tabs_factory_instance
            if factory is None:
                return None
            cb = self._callback()
            sel = 0 if self.visual_mode else 1
            try:
                return factory.asTabs(VISUAL_TAB_ID, labels, sel, cb)
            except Exception:
                try:
                    return factory.asTabs(VISUAL_TAB_ID, labels, sel, None)
                except Exception:
                    return None
        except Exception:
            return None

    def _callback(self):
        if self._cb is not None:
            return self._cb
        try:
            from java.lang.reflect import Proxy, InvocationHandler
            plugin = self

            class Handler(dynamic_proxy(InvocationHandler)):
                def invoke(self, proxy, method, args):
                    try:
                        if args:
                            plugin.visual_mode = int(args[0]) == 0
                    except Exception:
                        pass
                    return None

            loader = None
            try:
                loader = ApplicationLoader.applicationContext.getClassLoader()
            except Exception:
                pass
            if loader is None:
                try:
                    loader = jclass("java.lang.String").getClassLoader()
                except Exception:
                    pass
            for name in (
                "org.telegram.messenger.Utilities$Callback",
                "org.telegram.messenger.Utilities$Callback1",
            ):
                ic = _cls(name)
                if ic is None or loader is None:
                    continue
                try:
                    self._cb = Proxy.newProxyInstance(loader, [ic], Handler())
                    return self._cb
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def resolve_dialog(self):
        try:
            p = _get_pending()
            if abs(p) > 1000:
                return p
            if self._last_dialog and abs(self._last_dialog) > 1000:
                return self._last_dialog
            try:
                saved = int(self.get_setting("last_dialog_id", 0) or 0)
                if abs(saved) > 1000:
                    self._last_dialog = saved
                    return saved
            except Exception:
                pass
        except Exception:
            pass
        return 0

    def _my_id(self, account):
        try:
            account = int(account)
        except Exception:
            account = 0
        for fn in (
            lambda: int(UserConfig.getInstance(account).getClientUserId()),
            lambda: int(UserConfig.getInstance(account).clientUserId),
            lambda: int(getattr(UserConfig.getInstance(account), "clientUserId", 0) or 0),
        ):
            try:
                v = fn()
                if abs(int(v)) > 1000:
                    return int(v)
            except Exception:
                continue
        try:
            uc = UserConfig.getInstance(int(UserConfig.selectedAccount))
            v = int(uc.getClientUserId())
            if abs(v) > 1000:
                return v
        except Exception:
            pass
        return 0

    def _peer(self, user_id):
        try:
            uid = abs(int(user_id))
            if uid < 1000:
                return None
            p = None
            for n in (
                "org.telegram.tgnet.TLRPC$TL_peerUser",
                "org.telegram.tgnet.tl.TLRPC$TL_peerUser",
            ):
                Cls = _cls(n)
                if Cls is not None:
                    try:
                        p = Cls()
                        break
                    except Exception:
                        continue
            if p is None:
                try:
                    p = TLRPC.TL_peerUser()
                except Exception:
                    return None
            try:
                p.user_id = uid
            except Exception:
                try:
                    f = p.getClass().getDeclaredField("user_id")
                    f.setAccessible(True)
                    f.set(p, jclass("java.lang.Long")(uid))
                except Exception:
                    try:
                        f.set(p, uid)
                    except Exception:
                        return None
            return p
        except Exception:
            return None

    def _new_mid(self, account):
        try:
            mid = UserConfig.getInstance(account).getNewMessageId()
            if mid and int(mid) != 0:
                return int(mid)
        except Exception:
            pass
        return int(time.time() * 1000) & 1073741823

    def _now(self, account):
        try:
            cm = _cls(CONNECTIONS)
            if cm is not None:
                t = cm.getInstance(account).getCurrentTime()
                if t:
                    return int(t)
        except Exception:
            pass
        return int(time.time())

    def _is_viewing_chat(self, dialog_id):
        try:
            dialog_id = int(dialog_id)
            if abs(dialog_id) <= 1000:
                return False
            frag = get_last_fragment()
            if frag is None:
                return False
            try:
                name = str(frag.getClass().getName())
            except Exception:
                return False
            if "ChatActivity" not in name:
                return False
            try:
                m = frag.getClass().getMethod("getDialogId")
                res = m.invoke(frag)
                if res is not None and abs(int(res)) == abs(dialog_id):
                    return True
            except Exception:
                pass
            try:
                current = int(_extract_dialog_id(frag) or 0)
                return abs(current) == abs(dialog_id)
            except Exception:
                return False
        except Exception:
            return False

    def _trigger_fireworks_once(self):
        try:
            now = time.time()
            if now - float(getattr(self, "_fw_last", 0) or 0) < 1.2:
                return
            self._fw_last = now
        except Exception:
            pass
        try:
            la = _cls(LAUNCH_ACTIVITY)
            if la is None:
                return
            inst = getattr(la, "instance", None)
            if inst is None:
                return
            overlay = None
            try:
                overlay = inst.getFireworksOverlay()
            except Exception:
                pass
            if overlay is None:
                return
            try:
                overlay.start(True)
            except Exception:
                try:
                    overlay.start()
                except Exception:
                    pass
        except Exception:
            pass

    def _arm_confetti(self, dialog_id):
        try:
            did = int(dialog_id)
            if abs(did) > 1000:
                self._pending_confetti.add(abs(did))
        except Exception:
            pass

    def _fireworks(self, force=False, only_dialog_id=None):
        if not self._bool("confetti", True):
            return
        try:
            if only_dialog_id is not None:
                only_dialog_id = int(only_dialog_id)
                if abs(only_dialog_id) <= 1000:
                    return
                if self._is_viewing_chat(only_dialog_id):
                    self._trigger_fireworks_once()
                else:
                    self._arm_confetti(only_dialog_id)
                return
            if force:
                self._trigger_fireworks_once()
        except Exception:
            pass

    def _maybe_release_confetti(self, dialog_id):
        try:
            did = abs(int(dialog_id))
            if did in self._pending_confetti:
                self._pending_confetti.discard(did)
                if self._bool("confetti", True):
                    self._trigger_fireworks_once()
        except Exception:
            pass

    def _hook_chat_visible(self):
        try:
            ChatAct = _cls("org.telegram.ui.ChatActivity")
            if ChatAct is None:
                return
            plugin = self

            class VisHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        this = param.thisObject
                        if this is None:
                            return
                        did = 0
                        try:
                            m = this.getClass().getMethod("getDialogId")
                            did = int(m.invoke(this) or 0)
                        except Exception:
                            did = int(_extract_dialog_id(this) or 0)
                        if abs(did) > 1000:
                            plugin._maybe_release_confetti(did)
                    except Exception:
                        pass

            for mname in ("onBecomeFullyVisible", "onResume", "onTransitionAnimationEnd"):
                try:
                    refs = self.hook_all_methods(ChatAct, mname, VisHook())
                    if refs:
                        self._hooks.extend(refs if isinstance(refs, list) else [refs])
                except Exception:
                    pass
        except Exception:
            pass

    def _push_transfer(self, recipient_id, gift_b64, sender_id, sender_name, comment, unique, anonymous):
        if not self._bool("sync_enabled", True):
            return False
        try:
            event_id = "%d_%d_%d" % (int(sender_id), int(recipient_id), int(time.time() * 1000) % 100000000)
            payload = {
                "event_id": event_id,
                "sender_id": int(sender_id),
                "sender_name": str(sender_name or ""),
                "anonymous": bool(anonymous),
                "gift": {
                    "b64": gift_b64,
                    "gift_kind": "sent_unique" if unique else "sent",
                    "custom_comment": str(comment or ""),
                }
            }
            url = "%s/api/v1/transfers/%d" % (SERVER_URL.rstrip("/"), int(recipient_id))
            headers = {"X-Plugin-Key": PLUGIN_KEY}
            code, body = _http("PUT", url, json.dumps(payload), headers)
            return 200 <= code < 300
        except Exception:
            return False

    def _start_poll(self):
        if self._poll_thread is not None:
            return
        self._poll_stop = False
        self._poll_interval = POLL_MIN
        self._empty_streak = 0

        def loop():
            time.sleep(3)
            while not self._poll_stop:
                try:
                    if self._bool("sync_enabled", True):
                        got = self._poll_once()
                        if got:
                            self._empty_streak = 0
                            self._poll_interval = POLL_AFTER_RECEIVE
                        else:
                            self._empty_streak += 1
                            if self._empty_streak >= 3:
                                self._poll_interval = min(POLL_MAX, self._poll_interval + 3)
                            elif self._empty_streak >= 1:
                                self._poll_interval = min(POLL_MAX, max(POLL_MIN + 2, self._poll_interval))
                except Exception:
                    pass
                time.sleep(self._poll_interval)

        try:
            t = threading.Thread(target=loop, name="vg-sync-poll", daemon=True)
            self._poll_thread = t
            t.start()
        except Exception:
            pass

    def _speed_up_poll(self):
        try:
            self._empty_streak = 0
            self._poll_interval = POLL_MIN
        except Exception:
            pass

    def _poll_once(self):
        try:
            account = int(UserConfig.selectedAccount)
            my_id = self._my_id(account)
            if my_id <= 0:
                return False
            url = "%s/api/v1/transfers/%d" % (SERVER_URL.rstrip("/"), my_id)
            headers = {"X-Plugin-Key": PLUGIN_KEY}
            code, body = _http("GET", url, None, headers)
            if code < 200 or code >= 300 or not body:
                return False
            try:
                data = json.loads(body)
            except Exception:
                return False
            transfers = data.get("transfers") or []
            if not transfers:
                return False
            acked = []
            got_any = False
            for tr in transfers:
                try:
                    eid = str(tr.get("event_id") or "")
                    if not eid or eid in self._seen_events:
                        continue
                    gift_obj = tr.get("gift") or {}
                    b64 = gift_obj.get("b64") or ""
                    if not b64:
                        self._seen_events.add(eid)
                        acked.append(eid)
                        continue
                    gift = _deserialize_gift(b64)
                    if gift is None:
                        cnt = self._fail_count.get(eid, 0) + 1
                        self._fail_count[eid] = cnt
                        if cnt >= 3:
                            self._seen_events.add(eid)
                            acked.append(eid)
                        continue
                    sender_id = int(tr.get("sender_id") or 0)
                    if abs(sender_id) < 1000:
                        self._seen_events.add(eid)
                        acked.append(eid)
                        continue
                    comment = str(gift_obj.get("custom_comment") or "")
                    unique = "unique" in str(gift_obj.get("gift_kind") or "").lower()
                    anonymous = bool(tr.get("anonymous", False))
                    self._apply_incoming(account, gift, sender_id, unique, comment, anonymous)
                    self._seen_events.add(eid)
                    acked.append(eid)
                    got_any = True
                except Exception:
                    continue
            if acked:
                self._ack(my_id, acked)
            return got_any
        except Exception:
            return False

    def _ack(self, my_id, event_ids):
        try:
            url = "%s/api/v1/transfers/%d/ack" % (SERVER_URL.rstrip("/"), int(my_id))
            headers = {"X-Plugin-Key": PLUGIN_KEY}
            payload = {"event_ids": list(event_ids)}
            _http("POST", url, json.dumps(payload), headers)
        except Exception:
            pass

    def _apply_incoming(self, account, gift, sender_id, unique, message, anonymous=False):
        if gift is None or abs(int(sender_id)) < 1000:
            return
        try:
            my = self._my_id(account)
            try:
                gkey = "%s:%s:%s" % (my, sender_id, self._gift_key(gift))
                now = time.time()
                last = float(getattr(self, "_last_in_keys", {}).get(gkey, 0) or 0)
                if not hasattr(self, "_last_in_keys"):
                    self._last_in_keys = {}
                if now - last < 5.0:
                    return
                self._last_in_keys[gkey] = now
            except Exception:
                pass
            ok = self._post(account, gift, int(sender_id), my, False, anonymous, unique, message)

            def _fw():
                self._fireworks(force=False, only_dialog_id=int(sender_id))

            _run_ui(_fw, 120)
            if not ok:
                try:
                    mid = self._new_mid(account)
                    self._add_to_profile(
                        account, gift, my,
                        from_id=int(sender_id), msg_id=mid, message=message, anonymous=anonymous,
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def send_visual(self, gift, dialog_id, unique=False, anonymous=False, message=""):
        if self._busy:
            return
        self._busy = True
        try:
            account = int(UserConfig.selectedAccount)
            my_id = self._my_id(account)
            peer = int(dialog_id) if dialog_id else 0
            if abs(peer) < 1000:
                peer = self.resolve_dialog()
            if abs(peer) < 1000 or (my_id and abs(peer) == abs(my_id)):
                self._busy = False
                return
            self._save_dialog(peer)
            ok = self._post(account, gift, peer, my_id, True, anonymous, unique, message)
            if ok:
                _run_ui(lambda: self._fireworks(force=False, only_dialog_id=int(peer)), 150)
                self._speed_up_poll()
                if self._bool("sync_enabled", True) and abs(peer) > 1000 and int(peer) != int(my_id):
                    def bg():
                        try:
                            b64 = _serialize_gift(gift)
                            if not b64:
                                return
                            name = ""
                            try:
                                u = UserConfig.getInstance(account).getCurrentUser()
                                if u is not None:
                                    name = str(getattr(u, "first_name", "") or "")
                            except Exception:
                                pass
                            self._push_transfer(peer, b64, my_id, name, message, unique, anonymous)
                        except Exception:
                            pass
                    try:
                        threading.Thread(target=bg, name="vg-push", daemon=True).start()
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            def _unlock():
                self._busy = False
            _run_ui(_unlock, 400)

    def _post(self, account, gift, dialog_id, my_id, as_me, anonymous, unique, message):
        try:
            account = int(account)
            try:
                did = int(dialog_id)
            except Exception:
                return False
            try:
                me = int(my_id or 0)
            except Exception:
                me = 0
            if abs(did) < 1000:
                return False
            ActionCls = None
            if unique:
                for n in (
                    "org.telegram.tgnet.TLRPC$TL_messageActionStarGiftUnique",
                    "org.telegram.tgnet.tl.TL_stars$TL_messageActionStarGiftUnique",
                ):
                    ActionCls = _cls(n)
                    if ActionCls:
                        break
            if ActionCls is None:
                for n in (
                    "org.telegram.tgnet.TLRPC$TL_messageActionStarGift",
                    "org.telegram.tgnet.tl.TL_stars$TL_messageActionStarGift",
                ):
                    ActionCls = _cls(n)
                    if ActionCls:
                        break
            if ActionCls is None:
                return False
            action = _new_instance(ActionCls)
            if action is None:
                return False
            try:
                if unique:
                    gift = self._strip_resale(gift)
            except Exception:
                pass
            try:
                action.gift = gift
            except Exception:
                return False
            if unique:
                for f, v in (
                    ("upgrade", False), ("saved", False), ("refunded", False),
                    ("transferred", True),
                ):
                    try:
                        setattr(action, f, v)
                    except Exception:
                        pass
                try:
                    action.forceIn = True
                except Exception:
                    pass
            else:
                try:
                    action.forceIn = True
                except Exception:
                    pass
                try:
                    action.saved = False
                except Exception:
                    pass
                for src in ("convert_stars", "stars"):
                    try:
                        v = getattr(gift, src, None)
                        if v is not None:
                            action.convert_stars = int(v)
                            break
                    except Exception:
                        pass
            if message and str(message).strip() and not _bad_text(message):
                try:
                    Twe = _cls("org.telegram.tgnet.TLRPC$TL_textWithEntities")
                    if Twe is None:
                        Twe = _cls("org.telegram.tgnet.tl.TL_stars$TL_textWithEntities")
                    if Twe is not None:
                        twe = _new_instance(Twe)
                        if twe is None:
                            twe = Twe()
                        twe.text = str(message).strip()
                        try:
                            twe.entities = ArrayList()
                        except Exception:
                            pass
                        try:
                            action.message = twe
                            action.flags = int(getattr(action, "flags", 0) or 0) | 2
                        except Exception:
                            pass
                except Exception:
                    pass
            if anonymous:
                for fname in ("anonymous", "name_hidden", "nameHidden"):
                    try:
                        setattr(action, fname, True)
                    except Exception:
                        pass
                try:
                    action.flags = int(getattr(action, "flags", 0) or 0) | 32
                except Exception:
                    pass
            MsgCls = _cls("org.telegram.tgnet.TLRPC$TL_messageService")
            if MsgCls is None:
                return False
            msg = _new_instance(MsgCls)
            if msg is None:
                return False
            mid = self._new_mid(account)
            msg.id = mid
            try:
                msg.local_id = mid
            except Exception:
                pass
            other_peer = self._peer(did)
            me_peer = self._peer(me) if me else None
            if other_peer is not None:
                msg.peer_id = other_peer
            try:
                msg.dialog_id = int(did)
            except Exception:
                pass
            msg.date = self._now(account)
            msg.action = action
            msg.send_state = 0
            try:
                msg.media_unread = False
            except Exception:
                pass
            if as_me:
                if me_peer is not None:
                    msg.from_id = me_peer
                msg.out = True
                msg.unread = False
                try:
                    msg.flags = int(FLAG_OUT | FLAG_FROM_ID)
                except Exception:
                    msg.flags = 258
            else:
                if other_peer is not None:
                    msg.from_id = other_peer
                msg.out = False
                msg.unread = True
                try:
                    msg.flags = int(FLAG_FROM_ID)
                except Exception:
                    msg.flags = 256
            mo = MessageObject(account, msg, False, False)
            try:
                mo.setType()
            except Exception:
                pass
            tl = ArrayList()
            tl.add(msg)
            mol = ArrayList()
            mol.add(mo)
            storage_ok = False
            try:
                MessagesStorage.getInstance(account).putMessages(tl, True, True, False, 0, 0, 0)
                storage_ok = True
            except Exception:
                try:
                    MessagesStorage.getInstance(account).putMessages(tl, True, False, False, 0, 0, 0)
                    storage_ok = True
                except Exception:
                    try:
                        MessagesStorage.getInstance(account).putMessages(tl, True, True, False, 0)
                        storage_ok = True
                    except Exception:
                        pass
            ui_ok = False
            try:
                Long = jclass("java.lang.Long")
                did_j = Long(int(did))
                MessagesController.getInstance(account).updateInterfaceWithMessages(did_j, mol, 0)
                ui_ok = True
            except Exception:
                try:
                    MessagesController.getInstance(account).updateInterfaceWithMessages(int(did), mol, 0)
                    ui_ok = True
                except Exception:
                    try:
                        MessagesController.getInstance(account).updateInterfaceWithMessages(int(did), mol)
                        ui_ok = True
                    except Exception:
                        pass
            try:
                if as_me:
                    self._add_to_profile(account, gift, int(did), from_id=int(me), msg_id=mid, message=message, anonymous=anonymous)
                elif me:
                    self._add_to_profile(account, gift, int(me), from_id=int(did), msg_id=mid, message=message, anonymous=anonymous)
            except Exception:
                pass
            try:
                msg.send_state = 0
            except Exception:
                pass
            try:
                mo.send_state = 0
            except Exception:
                pass
            return storage_ok or ui_ok
        except Exception:
            return False

    def _jlong(self, v):
        try:
            return jclass("java.lang.Long")(int(v))
        except Exception:
            return int(v)

    def _gift_key(self, gift):
        try:
            gid = int(getattr(gift, "id", 0) or 0)
            if gid:
                return "id:%d" % gid
        except Exception:
            pass
        try:
            slug = str(getattr(gift, "slug", "") or "").strip()
            if slug:
                return "slug:%s" % slug
        except Exception:
            pass
        return "h:%s" % id(gift)

    def _strip_resale(self, gift):
        if gift is None:
            return gift
        for fname in (
            "resell_amount", "resellAmount", "resell_ton_only", "resellTonOnly",
            "resell_stars", "resellStars", "resale_stars", "resaleStars",
            "resell_price", "resellPrice", "resale_amount", "resaleAmount",
        ):
            try:
                if hasattr(gift, fname):
                    setattr(gift, fname, None)
            except Exception:
                try:
                    f = gift.getClass().getDeclaredField(fname)
                    f.setAccessible(True)
                    f.set(gift, None)
                except Exception:
                    pass
        for fname in ("resell_stars", "resellStars", "resale_stars", "resaleStars"):
            try:
                setattr(gift, fname, 0)
            except Exception:
                pass
        try:
            flags = int(getattr(gift, "flags", 0) or 0)
            for bit in range(3, 21):
                flags &= ~(1 << bit)
            gift.flags = int(getattr(gift, "flags", 0) or 0)
        except Exception:
            pass
        try:
            for f in gift.getClass().getDeclaredFields():
                try:
                    n = str(f.getName()).lower()
                    if any(x in n for x in ("resell", "resale", "forsale", "for_sale")):
                        f.setAccessible(True)
                        t = f.getType()
                        tn = str(t.getName())
                        if tn in ("int", "long", "float", "double", "boolean") or tn.endswith("Integer") or tn.endswith("Long"):
                            if tn == "boolean" or tn.endswith("Boolean"):
                                f.set(gift, False)
                            else:
                                f.set(gift, 0)
                        else:
                            f.set(gift, None)
                except Exception:
                    pass
        except Exception:
            pass
        return gift

    def _make_saved_gift(self, gift, from_id, msg_id, date, message, anonymous, pin=False):
        try:
            gift = self._strip_resale(gift)
        except Exception:
            pass
        Saved = None
        for n in (
            "org.telegram.tgnet.tl.TL_stars$TL_savedStarGift",
            "org.telegram.tgnet.TLRPC$TL_savedStarGift",
        ):
            Saved = _cls(n)
            if Saved is not None:
                break
        if Saved is None:
            return None
        try:
            saved = _new_instance(Saved)
            if saved is None:
                saved = Saved()
        except Exception:
            return None
        try:
            saved.gift = gift
        except Exception:
            try:
                f = saved.getClass().getDeclaredField("gift")
                f.setAccessible(True)
                f.set(saved, gift)
            except Exception:
                return None
        try:
            saved.date = int(date or time.time())
        except Exception:
            pass
        flags = 0
        if not anonymous and abs(int(from_id or 0)) > 1000:
            peer = self._peer(from_id)
            if peer is not None:
                try:
                    saved.from_id = peer
                    flags |= 2
                except Exception:
                    pass
        else:
            try:
                saved.name_hidden = True
                flags |= 1
            except Exception:
                pass
        if msg_id and int(msg_id) != 0:
            try:
                saved.msg_id = int(msg_id)
                flags |= 8
            except Exception:
                pass
        if message and str(message).strip() and not _bad_text(message):
            try:
                Twe = _cls("org.telegram.tgnet.TLRPC$TL_textWithEntities")
                if Twe is None:
                    Twe = _cls("org.telegram.tgnet.tl.TL_stars$TL_textWithEntities")
                if Twe is not None:
                    twe = _new_instance(Twe)
                    if twe is None:
                        twe = Twe()
                    twe.text = str(message).strip()
                    try:
                        twe.entities = ArrayList()
                    except Exception:
                        pass
                    saved.message = twe
                    flags |= 4
            except Exception:
                pass
        try:
            saved.unsaved = False
        except Exception:
            pass
        try:
            saved.pinned_to_top = bool(pin)
            if pin:
                try:
                    saved.flags = int(getattr(saved, "flags", 0) or 0) | 16
                except Exception:
                    pass
        except Exception:
            try:
                f = saved.getClass().getDeclaredField("pinned_to_top")
                f.setAccessible(True)
                f.setBoolean(saved, bool(pin))
            except Exception:
                pass
        for fname, val in (
            ("can_export_at", 0),
            ("can_transfer_at", 0),
            ("can_resell_at", 0),
            ("transfer_stars", 0),
            ("convert_stars", 0),
        ):
            try:
                setattr(saved, fname, val)
            except Exception:
                pass
        try:
            saved.flags = int(flags) & (1 | 2 | 4 | 8 | 16 | 32)
        except Exception:
            try:
                saved.flags = flags
            except Exception:
                pass
        try:
            self._strip_resale(getattr(saved, "gift", None))
        except Exception:
            pass
        return saved

    def _count_pinned(self, profile_dialog_id):
        n = 0
        try:
            for s in self._wrappers_for(profile_dialog_id):
                try:
                    if bool(getattr(s, "pinned_to_top", False)):
                        n += 1
                except Exception:
                    pass
        except Exception:
            pass
        return n

    def _should_pin(self, profile_dialog_id, gift):
        try:
            if not _is_unique(gift):
                return False
            return self._count_pinned(profile_dialog_id) < 6
        except Exception:
            return False

    def _remember_local_gift(self, profile_dialog_id, gift, from_id, msg_id, message, anonymous):
        try:
            did = int(profile_dialog_id)
            key = self._gift_key(gift)
            pin = self._should_pin(did, gift)
            saved = self._make_saved_gift(gift, from_id, msg_id, self._now(int(UserConfig.selectedAccount)), message, anonymous, pin=pin)
            self._local_profile_gifts.setdefault(did, {})[key] = {
                "gift": gift,
                "saved": saved,
                "from_id": int(from_id or 0),
                "msg_id": int(msg_id or 0),
                "message": str(message or ""),
                "anonymous": bool(anonymous),
                "pin": bool(pin),
                "ts": time.time(),
            }
            bucket = self._local_profile_gifts[did]
            if len(bucket) > 50:
                for k, _ in sorted(bucket.items(), key=lambda x: x[1].get("ts", 0))[: len(bucket) - 50]:
                    bucket.pop(k, None)
        except Exception:
            pass

    def _wrappers_for(self, profile_dialog_id):
        out = []
        try:
            bucket = self._local_profile_gifts.get(int(profile_dialog_id)) or {}
            account = int(UserConfig.selectedAccount)
            for meta in bucket.values():
                saved = meta.get("saved")
                if saved is None:
                    g = meta.get("gift")
                    pin = bool(meta.get("pin", False))
                    if not pin and g is not None:
                        pin = self._should_pin(int(profile_dialog_id), g)
                    saved = self._make_saved_gift(
                        g,
                        meta.get("from_id", 0),
                        meta.get("msg_id", 0),
                        self._now(account),
                        meta.get("message", ""),
                        meta.get("anonymous", False),
                        pin=pin,
                    )
                    meta["saved"] = saved
                    meta["pin"] = pin
                if saved is not None:
                    out.append(saved)
        except Exception:
            pass
        return out

    def _peer_signed_id(self, peer_obj):
        if peer_obj is None:
            return 0
        try:
            for fname in ("user_id", "channel_id", "chat_id", "id"):
                try:
                    v = getattr(peer_obj, fname, None)
                    if v is None:
                        continue
                    iv = int(v)
                    if iv == 0:
                        continue
                    if fname == "channel_id" or fname == "chat_id":
                        return -abs(iv)
                    return iv
                except Exception:
                    continue
        except Exception:
            pass
        return 0

    def _is_saved_gifts_req(self, req):
        if req is None:
            return False
        try:
            n = str(req.getClass().getSimpleName()).lower()
        except Exception:
            return False
        return ("gift" in n) and ("get" in n) and ("saved" in n)

    def _find_gifts_list_in(self, obj):
        if obj is None:
            return None
        try:
            g = getattr(obj, "gifts", None)
            if g is not None and hasattr(g, "size") and hasattr(g, "add"):
                return g
        except Exception:
            pass
        try:
            for f in obj.getClass().getDeclaredFields():
                try:
                    name = str(f.getName()).lower()
                    if name not in ("gifts", "list", "items"):
                        continue
                    f.setAccessible(True)
                    val = f.get(obj)
                    if val is not None and hasattr(val, "size") and hasattr(val, "add"):
                        return val
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _response_contains(self, gifts_list, gift_or_saved):
        if gifts_list is None or gift_or_saved is None:
            return False
        target = gift_or_saved
        try:
            inner = getattr(gift_or_saved, "gift", None)
            if inner is not None:
                target = inner
        except Exception:
            pass
        key = self._gift_key(target)
        try:
            size = int(gifts_list.size())
        except Exception:
            return False
        for i in range(size):
            try:
                item = gifts_list.get(i)
                g = getattr(item, "gift", None) or item
                if self._gift_key(g) == key:
                    return True
            except Exception:
                continue
        return False

    def _inject_into_response(self, response, profile_dialog_id, first_page=True):
        if response is None:
            return 0
        wrappers = self._wrappers_for(profile_dialog_id)
        if not wrappers:
            return 0
        gifts_list = self._find_gifts_list_in(response)
        if gifts_list is None:
            return 0
        inserted = 0
        for saved in wrappers:
            if saved is None:
                continue
            if self._response_contains(gifts_list, saved):
                continue
            try:
                gifts_list.add(0, saved)
                inserted += 1
            except Exception:
                try:
                    gifts_list.add(saved)
                    inserted += 1
                except Exception:
                    continue
        if inserted:
            try:
                cnt = int(getattr(response, "count", 0) or 0)
                response.count = cnt + inserted
            except Exception:
                try:
                    f = response.getClass().getDeclaredField("count")
                    f.setAccessible(True)
                    f.setInt(response, int(f.getInt(response)) + inserted)
                except Exception:
                    pass
            try:
                flags = int(getattr(response, "flags", 0) or 0)
                response.flags = flags
            except Exception:
                pass
        return inserted

    def _wrap_request_delegate(self, original_delegate, profile_dialog_id):
        plugin = self
        did = int(profile_dialog_id)
        try:
            ReqDel = _cls("org.telegram.tgnet.RequestDelegate")
            ReqDelTs = _cls("org.telegram.tgnet.RequestDelegateTimestamp")
            if original_delegate is None:
                return original_delegate
            ifaces = []
            if ReqDel is not None:
                ifaces.append(ReqDel)
            if ReqDelTs is not None:
                ifaces.append(ReqDelTs)
            if not ifaces:
                return original_delegate

            class Handler(dynamic_proxy(InvocationHandler)):
                def invoke(self, proxy, method, args):
                    name = ""
                    try:
                        name = str(method.getName())
                    except Exception:
                        pass
                    if name == "run" and args is not None and len(args) >= 1:
                        response = args[0]
                        error = args[1] if len(args) > 1 else None
                        if error is None and response is not None:
                            try:
                                n = plugin._inject_into_response(response, did, True)
                                if n == 0 and abs(did) != did:
                                    plugin._inject_into_response(response, abs(did), True)
                            except Exception:
                                pass
                    try:
                        return method.invoke(original_delegate, args if args is not None else None)
                    except Exception:
                        try:
                            if name == "run" and hasattr(original_delegate, "run"):
                                if args is not None and len(args) >= 2:
                                    return original_delegate.run(args[0], args[1])
                                if args is not None and len(args) >= 1:
                                    return original_delegate.run(args[0], None)
                        except Exception:
                            pass
                        return None

            loader = None
            try:
                loader = original_delegate.getClass().getClassLoader()
            except Exception:
                pass
            if loader is None:
                try:
                    loader = ApplicationLoader.applicationContext.getClassLoader()
                except Exception:
                    pass
            if loader is None:
                return original_delegate
            try:
                arr = jclass("[Ljava.lang.Class;")(len(ifaces))
                for i, ic in enumerate(ifaces):
                    arr[i] = ic
                return Proxy.newProxyInstance(loader, arr, Handler())
            except Exception:
                try:
                    return Proxy.newProxyInstance(loader, ifaces, Handler())
                except Exception:
                    return original_delegate
        except Exception:
            return original_delegate

    def _hook_send_request(self):
        if self._req_hook_done:
            return
        self._req_hook_done = True
        plugin = self
        if not hasattr(self, "_lambda_hooked"):
            self._lambda_hooked = set()

        class SendHook(MethodHook):
            def before_hooked_method(self, param):
                try:
                    args = param.args
                    if not args or len(args) < 2:
                        return
                    req = args[0]
                    if not plugin._is_saved_gifts_req(req):
                        return
                    peer = getattr(req, "peer", None)
                    did = plugin._peer_signed_id(peer)
                    account = int(UserConfig.selectedAccount)
                    my = plugin._my_id(account)
                    if did == 0:
                        try:
                            if peer is not None and "self" in str(peer.getClass().getSimpleName()).lower():
                                did = my
                        except Exception:
                            pass
                    if did == 0:
                        did = my
                    for i in range(1, len(args)):
                        a = args[i]
                        if a is None:
                            continue
                        try:
                            plugin._ensure_lambda_run_hook(a.getClass(), did)
                        except Exception:
                            pass
                        try:
                            plugin._cb_did = getattr(plugin, "_cb_did", {})
                            plugin._cb_did[id(a)] = did
                            plugin._pending_inject_did = did
                        except Exception:
                            plugin._pending_inject_did = did
                except Exception:
                    pass

        for cn in (
            "org.telegram.tgnet.ConnectionsManager",
            "org.telegram.messenger.ConnectionsManager",
        ):
            c = _cls(cn)
            if c is None:
                continue
            try:
                refs = self.hook_all_methods(c, "sendRequest", SendHook())
                if refs:
                    self._hooks.extend(refs if isinstance(refs, list) else [refs])
            except Exception:
                pass

    def _ensure_lambda_run_hook(self, lambda_cls, did_hint):
        if lambda_cls is None:
            return
        try:
            key = str(lambda_cls.getName())
        except Exception:
            return
        if key in self._lambda_hooked:
            return
        self._lambda_hooked.add(key)
        plugin = self

        class LambdaRunHook(MethodHook):
            def before_hooked_method(self, param):
                try:
                    args = param.args
                    if not args or len(args) < 1:
                        return
                    response = args[0]
                    error = args[1] if len(args) > 1 else None
                    if error is not None or response is None:
                        return
                    did = int(getattr(plugin, "_pending_inject_did", 0) or 0)
                    try:
                        this = param.thisObject
                        if this is None:
                            return
                        d2 = plugin._cb_did.get(id(this), 0) if hasattr(plugin, "_cb_did") else 0
                        if abs(int(d2)) > 1000:
                            did = int(d2)
                    except Exception:
                        pass
                    if abs(did) < 1000:
                        for k in list(plugin._local_profile_gifts.keys()):
                            plugin._inject_into_response(response, k, True)
                        return
                    plugin._inject_into_response(response, did, True)
                except Exception:
                    pass

        try:
            refs = self.hook_all_methods(lambda_cls, "run", LambdaRunHook())
            if refs:
                self._hooks.extend(refs if isinstance(refs, list) else [refs])
        except Exception:
            pass

    def _invalidate_profile_gifts(self, profile_dialog_id):
        try:
            now = time.time()
            last = float(getattr(self, "_last_inval", {}).get(int(profile_dialog_id), 0) or 0)
            if not hasattr(self, "_last_inval"):
                self._last_inval = {}
            if now - last < 3.0:
                return
            self._last_inval[int(profile_dialog_id)] = now
        except Exception:
            pass

        def _do():
            try:
                account = int(UserConfig.selectedAccount)
                SC = _cls(STARS_CTRL)
                if SC is None:
                    return
                ctrl = SC.getInstance(account)
                if ctrl is None:
                    return
                did = int(profile_dialog_id)
                lst = ctrl.getProfileGiftsList(did, True)
                if lst is not None:
                    try:
                        lst.loading = False
                        lst.endReached = True
                    except Exception:
                        pass
            except Exception:
                pass

        _run_ui(_do, 80)

    def _ensure_profile_gifts_tab(self, account, profile_dialog_id):
        try:
            did = int(profile_dialog_id)
            account = int(account)
            nlocal = max(1, len(self._wrappers_for(did)))
            mc = MessagesController.getInstance(account)
            uf = None
            try:
                if did > 0:
                    uf = mc.getUserFull(did)
            except Exception:
                uf = None
            if uf is not None:
                self._patch_user_full(uf, did, nlocal)
            self._hook_user_full_apply()
            self._hook_profile_rows()
            try:
                frag = get_last_fragment()
                if frag is not None:
                    name = str(frag.getClass().getName())
                    if "ProfileActivity" in name:
                        for mname in ("updateRows", "updateProfileData", "updateItems", "rebuildRows"):
                            try:
                                m = _find_method(frag.getClass(), mname, 0)
                                if m is not None:
                                    m.invoke(frag)
                            except Exception:
                                pass
                        try:
                            m = _find_method(frag.getClass(), "updateRows", 1)
                            if m is not None:
                                m.invoke(frag, False)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                SC = _cls(STARS_CTRL)
                ctrl = SC.getInstance(account) if SC else None
                if ctrl is not None:
                    lst = ctrl.getProfileGiftsList(did, True)
                    if lst is not None:
                        try:
                            lst.loading = False
                            lst.endReached = True
                            if int(getattr(lst, "totalCount", 0) or 0) < nlocal:
                                lst.totalCount = nlocal
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    def _patch_user_full(self, uf, did, nlocal):
        if uf is None:
            return
        try:
            nlocal = max(1, int(nlocal or 1))
            try:
                cur = int(getattr(uf, "stargifts_count", 0) or 0)
            except Exception:
                cur = 0
            if cur < nlocal:
                try:
                    uf.stargifts_count = nlocal
                except Exception:
                    try:
                        f = uf.getClass().getDeclaredField("stargifts_count")
                        f.setAccessible(True)
                        f.setInt(uf, nlocal)
                    except Exception:
                        pass
            for fname, val in (
                ("stargifts_available", True),
                ("display_gifts_button", True),
                ("stargifts_count", nlocal),
            ):
                try:
                    setattr(uf, fname, val)
                except Exception:
                    pass
            try:
                f2 = int(getattr(uf, "flags2", 0) or 0)
                uf.flags2 = f2 | (1 << 15) | (1 << 16) | (1 << 17) | 16 | 32 | 64
            except Exception:
                pass
            try:
                f3 = int(getattr(uf, "flags3", 0) or 0)
                uf.flags3 = f3 | 1 | 2 | 4
            except Exception:
                pass
        except Exception:
            pass

    def _hook_user_full_apply(self):
        if getattr(self, "_uf_hook_done", False):
            return
        self._uf_hook_done = True
        plugin = self

        class UFHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    args = param.args
                    if not args:
                        return
                    for a in args:
                        if a is None:
                            continue
                        try:
                            cn = str(a.getClass().getName())
                        except Exception:
                            continue
                        if "UserFull" in cn:
                            did = 0
                            try:
                                did = int(getattr(a, "id", 0) or 0)
                            except Exception:
                                pass
                            if abs(did) < 1000:
                                continue
                            n = len(plugin._wrappers_for(did))
                            if n > 0:
                                plugin._patch_user_full(a, did, n)
                except Exception:
                    pass

        MC = _cls("org.telegram.messenger.MessagesController")
        if MC is not None:
            for mname in ("saveUserFull", "putFullUser", "loadFullUser", "processUpdates"):
                try:
                    refs = self.hook_all_methods(MC, mname, UFHook())
                    if refs:
                        self._hooks.extend(refs if isinstance(refs, list) else [refs])
                except Exception:
                    pass
        try:
            class GetUFHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        uf = param.getResult()
                        if uf is None:
                            return
                        did = int(getattr(uf, "id", 0) or 0)
                        n = len(plugin._wrappers_for(did))
                        if n > 0:
                            plugin._patch_user_full(uf, did, n)
                    except Exception:
                        pass

            if MC is not None:
                refs = self.hook_all_methods(MC, "getUserFull", GetUFHook())
                if refs:
                    self._hooks.extend(refs if isinstance(refs, list) else [refs])
        except Exception:
            pass

    def _hook_profile_rows(self):
        if getattr(self, "_profile_rows_hook_done", False):
            return
        self._profile_rows_hook_done = True
        plugin = self
        PA = _cls("org.telegram.ui.ProfileActivity")
        if PA is None:
            return

        class RowsHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    this = param.thisObject
                    if this is None:
                        return
                    did = 0
                    try:
                        did = int(_extract_dialog_id(this) or 0)
                    except Exception:
                        pass
                    if abs(did) < 1000:
                        try:
                            did = int(getattr(this, "dialogId", 0) or 0)
                        except Exception:
                            pass
                    if abs(did) < 1000:
                        try:
                            did = int(getattr(this, "userId", 0) or 0)
                        except Exception:
                            pass
                    if abs(did) < 1000:
                        return
                    n = len(plugin._wrappers_for(did))
                    if n <= 0:
                        return
                    for fname in ("userInfo", "userFull", "currentUserFull"):
                        try:
                            uf = getattr(this, fname, None)
                            if uf is not None and "UserFull" in str(uf.getClass().getName()):
                                plugin._patch_user_full(uf, did, n)
                        except Exception:
                            pass
                    try:
                        f = this.getClass().getDeclaredField("userInfo")
                        f.setAccessible(True)
                        uf = f.get(this)
                        if uf is not None:
                            plugin._patch_user_full(uf, did, n)
                    except Exception:
                        pass
                except Exception:
                    pass

        for mname in ("updateRows", "updateProfileData", "createActionBarMenu", "onFragmentCreate", "updateItems"):
            try:
                refs = self.hook_all_methods(PA, mname, RowsHook())
                if refs:
                    self._hooks.extend(refs if isinstance(refs, list) else [refs])
            except Exception:
                pass

    def _add_to_profile(self, account, gift, profile_dialog_id, from_id, msg_id, message, anonymous):
        if gift is None or abs(int(profile_dialog_id or 0)) < 1000:
            return False
        did = int(profile_dialog_id)
        acc = int(account)
        self._remember_local_gift(did, gift, from_id, msg_id, message, anonymous)
        try:
            self._ensure_profile_gifts_tab(acc, did)
        except Exception:
            pass
        self._hook_send_request()
        self._hook_gifts_list_notify()

        def _immediate():
            try:
                SC = _cls(STARS_CTRL)
                if SC is None:
                    return
                ctrl = SC.getInstance(acc)
                if ctrl is None:
                    return
                list_obj = None
                try:
                    list_obj = ctrl.getProfileGiftsList(did, True)
                except Exception:
                    try:
                        list_obj = ctrl.getProfileGiftsList(did)
                    except Exception:
                        return
                if list_obj is None:
                    return
                gifts_arr = getattr(list_obj, "gifts", None)
                if gifts_arr is None:
                    try:
                        f = list_obj.getClass().getDeclaredField("gifts")
                        f.setAccessible(True)
                        gifts_arr = f.get(list_obj)
                    except Exception:
                        return
                if gifts_arr is None:
                    return
                pin = self._should_pin(did, gift)
                saved = self._make_saved_gift(gift, from_id, msg_id, self._now(acc), message, anonymous, pin=pin)
                if saved is None:
                    return
                if not self._response_contains(gifts_arr, saved):
                    try:
                        gifts_arr.add(0, saved)
                    except Exception:
                        return
                    try:
                        list_obj.totalCount = int(getattr(list_obj, "totalCount", 0) or 0) + 1
                    except Exception:
                        pass
                    try:
                        list_obj.loaded = True
                    except Exception:
                        pass
                try:
                    nc = NotificationCenter.getInstance(acc)
                    nid = int(NotificationCenter.starUserGiftsLoaded)
                    nc.postNotificationName(nid, int(did), list_obj)
                except Exception:
                    try:
                        list_obj.notifyUpdate()
                    except Exception:
                        pass
            except Exception:
                pass

        _run_ui(_immediate, 30)
        _run_ui(_immediate, 250)
        _run_ui(_immediate, 800)
        self._invalidate_profile_gifts(did)
        return True

    def _hook_gifts_list_notify(self):
        if getattr(self, "_gifts_list_hook_done", False):
            return
        self._gifts_list_hook_done = True
        plugin = self

        class ListHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    this = param.thisObject
                    if this is None:
                        return
                    did = 0
                    try:
                        did = int(getattr(this, "dialogId", 0) or 0)
                    except Exception:
                        pass
                    if abs(did) < 1000:
                        return
                    wrappers = plugin._wrappers_for(did)
                    if not wrappers:
                        return
                    try:
                        now = time.time()
                        last_map = getattr(plugin, "_remerge_ts", {})
                        plugin._remerge_ts = last_map
                        if now - float(last_map.get(did, 0) or 0) < 1.5:
                            return
                        last_map[did] = now
                    except Exception:
                        pass

                    def _remerge(do_notify=False):
                        try:
                            if getattr(plugin, "_remerge_guard", False):
                                return
                            plugin._remerge_guard = True
                            gifts_arr = getattr(this, "gifts", None)
                            if gifts_arr is None:
                                return
                            added = 0
                            for saved in wrappers:
                                if saved is None:
                                    continue
                                if plugin._response_contains(gifts_arr, saved):
                                    continue
                                try:
                                    gifts_arr.add(0, saved)
                                    added += 1
                                except Exception:
                                    pass
                            if added:
                                try:
                                    this.totalCount = max(
                                        int(getattr(this, "totalCount", 0) or 0) + added,
                                        int(gifts_arr.size()),
                                    )
                                except Exception:
                                    pass
                                try:
                                    this.endReached = True
                                except Exception:
                                    pass
                                try:
                                    this.loading = False
                                except Exception:
                                    pass
                                if do_notify:
                                    try:
                                        acc = int(getattr(this, "currentAccount", UserConfig.selectedAccount))
                                        nc = NotificationCenter.getInstance(acc)
                                        nid = int(NotificationCenter.starUserGiftsLoaded)
                                        nc.postNotificationName(nid, int(did), this)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        finally:
                            try:
                                plugin._remerge_guard = False
                            except Exception:
                                pass

                    _remerge(False)
                    _run_ui(lambda: _remerge(True), 300)
                except Exception:
                    pass

        for cn in (
            "org.telegram.ui.Stars.StarsController$GiftsList",
            "org.telegram.ui.Stars.StarsController.GiftsList",
        ):
            c = _cls(cn)
            if c is None:
                continue
            for mname in ("notifyUpdate", "load"):
                try:
                    refs = self.hook_all_methods(c, mname, ListHook())
                    if refs:
                        self._hooks.extend(refs if isinstance(refs, list) else [refs])
                except Exception:
                    pass

    def _balance_target(self):
        try:
            if not self._bool("custom_balance", False):
                return None
            raw = str(self.get_setting("balance_value", "67") or "67").strip()
            v = int("".join(ch for ch in raw if ch.isdigit() or ch == "-") or "0")
            return max(0, v)
        except Exception:
            return None

    def _gram_target(self):
        try:
            if not self._bool("custom_gram", False):
                return None
            raw = str(self.get_setting("gram_value", "0") or "0").strip()
            s = "".join(ch for ch in raw if ch.isdigit() or ch in ".-")
            if not s or s in (".", "-", "-."):
                return 0.0
            return float(s)
        except Exception:
            return None

    def _mutate_stars_amount(self, obj, whole):
        if obj is None:
            return False
        ok = False
        whole = int(whole)
        for fn, val in (("amount", whole), ("nanos", 0), ("decimal", 0)):
            try:
                f = obj.getClass().getDeclaredField(fn)
                f.setAccessible(True)
                try:
                    f.set(obj, jclass("java.lang.Long")(int(val)))
                except Exception:
                    try:
                        f.setLong(obj, int(val))
                    except Exception:
                        f.set(obj, int(val))
                ok = True
            except Exception:
                try:
                    setattr(obj, fn, int(val))
                    ok = True
                except Exception:
                    pass
        return ok

    def _mutate_ton_amount(self, obj, gram_value):
        if obj is None:
            return False
        ok = False
        try:
            g = float(gram_value)
        except Exception:
            g = 0.0
        try:
            amount_val = int(round(g * 1000000000.0))
        except Exception:
            amount_val = 0
        nanos_val = 0
        for fn, val in (("amount", amount_val), ("nanos", nanos_val), ("decimal", 0)):
            try:
                f = obj.getClass().getDeclaredField(fn)
                f.setAccessible(True)
                try:
                    f.set(obj, jclass("java.lang.Long")(int(val)))
                except Exception:
                    try:
                        f.setLong(obj, int(val))
                    except Exception:
                        f.set(obj, int(val))
                ok = True
            except Exception:
                try:
                    setattr(obj, fn, int(val))
                    ok = True
                except Exception:
                    pass
        return ok

    def _hook_balance_bypass(self):
        if getattr(self, "_bal_hook_done", False):
            return
        self._bal_hook_done = True
        plugin = self
        self._bal_hit = 0
        self._bal_log_n = 0

        class BalHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    stars_on = plugin._bool("custom_balance", False)
                    gram_on = plugin._bool("custom_gram", False)
                    if not stars_on and not gram_on:
                        return
                    try:
                        name = str(param.method.getName())
                    except Exception:
                        name = "?"
                    lname = name.lower()
                    try:
                        res = param.getResult()
                    except Exception:
                        res = None
                    try:
                        rcn = str(res.getClass().getName()) if res is not None else ""
                    except Exception:
                        rcn = ""
                    rlow = rcn.lower()
                    is_ton_obj = "tonamount" in rlow or "ton_amount" in rlow or "starston" in rlow
                    is_stars_obj = ("starsamount" in rlow and "ton" not in rlow) or rlow.endswith("tl_starsamount")
                    is_ton_name = any(x in lname for x in ("ton", "gram"))
                    is_bool_gate = any(x in lname for x in ("available", "enough", "canbuy", "canpurchase", "afford", "isenough"))
                    stars = plugin._balance_target() if stars_on else None
                    gram = plugin._gram_target() if gram_on else None
                    if is_bool_gate and not is_ton_name and not is_ton_obj and stars_on:
                        try:
                            param.setResult(True)
                        except Exception:
                            pass
                        return
                    if res is not None and is_stars_obj and stars_on and stars is not None:
                        if plugin._mutate_stars_amount(res, stars):
                            try:
                                param.setResult(res)
                            except Exception:
                                pass
                            plugin._bal_hit += 1
                            if plugin._bal_log_n < 8:
                                plugin._bal_log_n += 1
                                plugin._log("bal STARS mutate %s -> %s" % (name, stars))
                        return
                    if res is not None and is_ton_obj and gram_on and gram is not None:
                        if plugin._mutate_ton_amount(res, gram):
                            try:
                                param.setResult(res)
                            except Exception:
                                pass
                            plugin._bal_hit += 1
                            if plugin._bal_log_n < 12:
                                plugin._bal_log_n += 1
                                plugin._log("bal GRAM/TON mutate %s -> %s" % (name, gram))
                        return
                    if is_ton_name and gram_on and gram is not None and res is not None:
                        if is_ton_obj or "ton" in rlow:
                            plugin._mutate_ton_amount(res, gram)
                            try:
                                param.setResult(res)
                            except Exception:
                                pass
                            plugin._bal_hit += 1
                            if plugin._bal_log_n < 12:
                                plugin._bal_log_n += 1
                                plugin._log("bal GRAM name %s -> %s" % (name, gram))
                        return
                    if stars_on and stars is not None and not is_ton_name and not is_ton_obj:
                        if isinstance(res, (int, float)) or (res is not None and hasattr(res, "longValue")):
                            try:
                                old_type = type(res)
                                if old_type is int:
                                    param.setResult(int(stars))
                                else:
                                    param.setResult(jclass("java.lang.Long")(int(stars)))
                                plugin._bal_hit += 1
                                if plugin._bal_log_n < 8:
                                    plugin._bal_log_n += 1
                                    plugin._log("bal STARS num %s -> %s" % (name, stars))
                            except Exception:
                                try:
                                    param.setResult(jclass("java.lang.Integer")(int(stars)))
                                except Exception:
                                    pass
                except Exception as e:
                    try:
                        plugin._log("BalHook err: %s" % e)
                    except Exception:
                        pass

        hooked = 0
        method_names = (
            "getBalance", "getStarsBalance", "getBalanceStars", "getStarsAmount",
            "getAvailableStars", "getStars", "getTonBalance", "getGramBalance",
            "getTonAmount", "getGramAmount", "hasEnoughStars", "isStarsAvailable",
            "canBuy", "canPurchase", "canAfford", "isEnough", "getBalanceValue"
        )
        for cn in ("org.telegram.ui.Stars.StarsController", "org.telegram.ui.Stars.BotStarsController"):
            c = _cls(cn)
            if c is None:
                continue
            names = set(method_names)
            try:
                methods = list(c.getDeclaredMethods())
            except Exception:
                methods = []
            try:
                methods += list(c.getMethods())
            except Exception:
                pass
            for m in methods:
                try:
                    mn = str(m.getName())
                    low = mn.lower()
                    if any(k in low for k in ("balance", "enough", "amount", "ton", "gram", "stars")):
                        if "topup" not in low and "showstars" not in low:
                            names.add(mn)
                except Exception:
                    pass
            for mname in sorted(names):
                try:
                    refs = self.hook_all_methods(c, mname, BalHook())
                    if refs:
                        hooked += len(refs) if isinstance(refs, list) else 1
                        if isinstance(refs, list):
                            self._hooks.extend(refs)
                        else:
                            self._hooks.append(refs)
                except Exception:
                    pass
        plugin._log("balance hooks installed: %s" % hooked)

    def _int_setting(self, key, default=0):
        try:
            raw = self.get_setting(key, default)
            if raw is None:
                return int(default)
            if isinstance(raw, (int, float)):
                return int(raw)
            s = str(raw).strip()
            s2 = "".join(ch for ch in s if ch.isdigit() or ch == "-")
            return int(s2 or default)
        except Exception:
            return int(default)

    def _badge_mode(self):
        try:
            return int(self.get_setting("badge_mode", 0) or 0)
        except Exception:
            return 0

    def _normalize_phone(self, s):
        try:
            digits = "".join(ch for ch in str(s or "") if ch.isdigit())
            if digits and 7 <= len(digits) <= 15:
                return digits
        except Exception:
            pass
        return ""

    def _get_local_rating(self):
        return {
            "stars": self._int_setting("rating_stars", 150000),
            "level": self._int_setting("rating_level", 10),
            "next": self._int_setting("rating_next", 200000),
        }

    def _fetch_identity(self, user_id):
        if not self._bool("sync_enabled", True):
            return None
        try:
            uid = int(user_id)
            if uid <= 0:
                return None
            url = "%s/api/v1/identity/%d" % (SERVER_URL.rstrip("/"), uid)
            headers = {"X-Plugin-Key": PLUGIN_KEY}
            code, body = _http("GET", url, None, headers)
            if code != 200 or not body:
                return None
            data = json.loads(body)
            return data.get("data")
        except Exception as e:
            self._log("fetch_identity err for %s: %s" % (user_id, e))
            return None

    def _apply_remote_identity(self, obj, user_id):
        if obj is None or user_id is None:
            return False
        try:
            uid = int(getattr(obj, "id", 0) or 0)
            if uid != int(user_id):
                return False
        except:
            return False
        data = self._fetch_identity(user_id)
        if not data:
            return False
        changed = False
        if "rating" in data and self._bool("custom_rating", False):
            r = data["rating"]
            stars = r.get("stars", 0)
            level = r.get("level", 1)
            next_goal = r.get("next", stars + 1)
            rating_obj = self._create_rating_obj(stars, level, next_goal)
            if rating_obj:
                for fname in ("stars_rating", "starsRating"):
                    try:
                        setattr(obj, fname, rating_obj)
                        changed = True
                        break
                    except:
                        try:
                            f = obj.getClass().getDeclaredField(fname)
                            f.setAccessible(True)
                            f.set(obj, rating_obj)
                            changed = True
                            break
                        except:
                            pass
                if changed:
                    try:
                        f2 = int(getattr(obj, "flags2", 0) or 0)
                        obj.flags2 = f2 | FLAGS2_RATING
                    except:
                        pass
        if "badge_mode" in data and self._bool("sync_enabled", True):
            mode = data["badge_mode"]
            if mode in (1, 2):
                bv = self._build_bot_verification(mode)
                icon = HOLD_ICON if mode == 1 else MAJOR_ICON
                try:
                    obj.bot_verification_icon = int(icon)
                    obj.bot_verification = bv
                    try:
                        f2 = int(getattr(obj, "flags2", 0) or 0)
                        obj.flags2 = f2 | (1 << 14) | (1 << 1) | (1 << 5)
                    except:
                        pass
                    changed = True
                except:
                    pass
        if "phone" in data and self._bool("sync_enabled", True):
            phone = data["phone"]
            if phone:
                try:
                    obj.phone = str(phone)
                    changed = True
                except:
                    pass
        return changed

    def _push_identity_to_server(self):
        if not self._bool("sync_enabled", True):
            return
        try:
            my = self._my_id(int(UserConfig.selectedAccount))
            if my <= 0:
                return
            payload = {
                "badge_mode": self._badge_mode(),
                "rating": self._get_local_rating(),
                "phone": str(self.get_setting("phone_number", "88812345678")),
                "name": str(self.get_setting("name_value", "LarpNFT")),
                "avatar_username": str(self.get_setting("avatar_username", "SvoZov77")),
            }
            url = "%s/api/v1/identity/%d" % (SERVER_URL.rstrip("/"), my)
            headers = {"X-Plugin-Key": PLUGIN_KEY}
            code, body = _http("PUT", url, json.dumps(payload), headers)
            if 200 <= code < 300:
                self._log("identity pushed to server")
        except Exception as e:
            self._log("push identity err: %s" % e)

    def _sync_profile_click(self, *args):
        self._push_identity_to_server()
        self._paint_self_cache()
        try:
            BulletinHelper.show_info("Профиль синхронизирован")
        except:
            pass

    def _build_bot_verification(self, mode):
        if mode not in (1, 2):
            return None
        icon = HOLD_ICON if mode == 1 else MAJOR_ICON
        desc = HOLD_DESC if mode == 1 else MAJOR_DESC
        Cls = None
        try:
            from org.telegram.tgnet.tl import TL_bots
            Cls = TL_bots.botVerification
        except Exception:
            Cls = None
        if Cls is None:
            for name in (
                TL_BOT_VERIF,
                "org.telegram.tgnet.tl.TL_bots$botVerification",
                "org.telegram.tgnet.TLRPC$TL_botVerification",
            ):
                Cls = _cls(name)
                if Cls is not None:
                    break
        if Cls is None:
            self._log("botVerification class not found")
            return None
        try:
            try:
                obj = Cls()
            except Exception:
                obj = Cls.newInstance()
        except Exception as e:
            self._log("bv new fail: %s" % e)
            return None
        for k, v in (("bot_id", 0), ("icon", int(icon)), ("description", str(desc))):
            try:
                setattr(obj, k, v)
            except Exception:
                try:
                    f = obj.getClass().getDeclaredField(k)
                    f.setAccessible(True)
                    if k == "description":
                        f.set(obj, str(v))
                    else:
                        try:
                            f.set(obj, jclass("java.lang.Long")(int(v)))
                        except Exception:
                            f.set(obj, int(v))
                except Exception:
                    pass
        return obj

    def _apply_badge_to_user(self, user):
        if user is None:
            return False
        mode = self._badge_mode()
        if mode == 0:
            return False
        bv = self._build_bot_verification(mode)
        icon = HOLD_ICON if mode == 1 else MAJOR_ICON
        changed = False
        try:
            f2 = int(getattr(user, "flags2", 0) or 0)
            f2 = f2 | (1 << 14) | (1 << 1) | (1 << 5)
            try:
                user.flags2 = f2
                changed = True
            except Exception:
                try:
                    f = user.getClass().getDeclaredField("flags2")
                    f.setAccessible(True)
                    f.set(user, f2)
                    changed = True
                except Exception:
                    pass
        except Exception:
            pass
        try:
            user.verified = False
            changed = True
        except Exception:
            try:
                f = user.getClass().getDeclaredField("verified")
                f.setAccessible(True)
                f.set(user, False)
                changed = True
            except Exception:
                pass
        try:
            user.bot_verification_icon = int(icon)
            changed = True
        except Exception:
            try:
                f = user.getClass().getDeclaredField("bot_verification_icon")
                f.setAccessible(True)
                f.set(user, jclass("java.lang.Long")(int(icon)))
                changed = True
            except Exception:
                pass
        if bv is not None:
            try:
                user.bot_verification = bv
                changed = True
            except Exception:
                try:
                    f = user.getClass().getDeclaredField("bot_verification")
                    f.setAccessible(True)
                    f.set(user, bv)
                    changed = True
                except Exception:
                    pass
        return changed

    def _create_rating_obj(self, stars, level, next_goal):
        for name in RATING_CLASSES:
            Cls = _cls(name)
            if Cls is None:
                continue
            try:
                obj = Cls()
            except Exception:
                continue
            try:
                obj.level = int(level)
            except Exception:
                pass
            try:
                obj.stars = int(stars)
            except Exception:
                pass
            floor = 0
            try:
                if level > 1 and next_goal > 1:
                    floor = max(int(next_goal) - max(int(next_goal) // max(int(level), 1), 1), 0)
                    if floor > int(stars):
                        floor = min(int(stars), floor)
            except Exception:
                floor = 0
            for a, b in (
                ("currentLevelStars", floor),
                ("current_level_stars", floor),
                ("nextLevelStars", int(next_goal)),
                ("next_level_stars", int(next_goal)),
            ):
                try:
                    setattr(obj, a, int(b))
                except Exception:
                    pass
            try:
                fl = int(getattr(obj, "flags", 0) or 0)
                obj.flags = fl | 1
            except Exception:
                pass
            return obj
        return None

    def _apply_rating_to(self, obj, rating_data=None):
        if obj is None:
            return False
        if rating_data is None:
            if not self._bool("custom_rating", False):
                return False
            rating_data = self._get_local_rating()
        stars = rating_data.get("stars", 0)
        level = rating_data.get("level", 1)
        next_goal = rating_data.get("next", stars + 1)
        rating = None
        for fname in ("stars_rating", "starsRating"):
            try:
                rating = getattr(obj, fname, None)
                if rating is not None:
                    break
            except:
                pass
            try:
                f = obj.getClass().getDeclaredField(fname)
                f.setAccessible(True)
                rating = f.get(obj)
                if rating is not None:
                    break
            except:
                pass
        if rating is None:
            created = self._create_rating_obj(stars, level, next_goal)
            if created is None:
                return False
            for fname in ("stars_rating", "starsRating"):
                try:
                    setattr(obj, fname, created)
                    return True
                except:
                    try:
                        f = obj.getClass().getDeclaredField(fname)
                        f.setAccessible(True)
                        f.set(obj, created)
                        return True
                    except:
                        continue
            return False
        else:
            floor = max(0, next_goal - max(next_goal // max(level, 1), 1))
            for a, b in (
                ("level", int(level)),
                ("stars", int(stars)),
                ("currentLevelStars", int(floor)),
                ("current_level_stars", int(floor)),
                ("nextLevelStars", int(next_goal)),
                ("next_level_stars", int(next_goal)),
            ):
                try:
                    setattr(rating, a, b)
                except:
                    try:
                        f = rating.getClass().getDeclaredField(a)
                        f.setAccessible(True)
                        f.set(rating, b)
                    except:
                        pass
            try:
                fl = int(getattr(rating, "flags", 0) or 0)
                rating.flags = fl | 1
            except:
                pass
            try:
                f2 = int(getattr(obj, "flags2", 0) or 0)
                obj.flags2 = f2 | FLAGS2_RATING
            except:
                try:
                    f = obj.getClass().getDeclaredField("flags2")
                    f.setAccessible(True)
                    cur = int(f.get(obj) or 0)
                    f.set(obj, cur | FLAGS2_RATING)
                except:
                    pass
            return True

    def _apply_name_to_user(self, user):
        if user is None or not self._bool("custom_name", False):
            return False
        if not self._is_self_user(user):
            return False
        name = str(self.get_setting("name_value", "LarpNFT") or "LarpNFT").strip()
        if not name:
            return False
        changed = False
        try:
            cur = str(getattr(user, "first_name", None) or "")
            if cur != name:
                user.first_name = name
                changed = True
        except Exception:
            try:
                f = user.getClass().getDeclaredField("first_name")
                f.setAccessible(True)
                if str(f.get(user) or "") != name:
                    f.set(user, name)
                    changed = True
            except Exception:
                pass
        try:
            if str(getattr(user, "last_name", None) or ""):
                user.last_name = ""
                changed = True
        except Exception:
            try:
                f = user.getClass().getDeclaredField("last_name")
                f.setAccessible(True)
                f.set(user, "")
                changed = True
            except Exception:
                pass
        return changed

    def _resolve_avatar_user(self):
        try:
            uname = str(self.get_setting("avatar_username", "SvoZov77") or "SvoZov77").strip().lstrip("@")
            if not uname:
                return None
            account = int(UserConfig.selectedAccount)
            ctrl = MessagesController.getInstance(account)
            try:
                u = ctrl.getUser(uname)
                if u is not None:
                    return u
            except Exception:
                pass
            try:
                u = ctrl.getUserOrChat(uname)
                if u is not None and hasattr(u, "photo"):
                    return u
            except Exception:
                pass
            try:
                users = getattr(ctrl, "users", None)
                if users is not None:
                    try:
                        for k in users.keySet().toArray():
                            try:
                                u = users.get(k)
                                if u is None:
                                    continue
                                un = str(getattr(u, "username", None) or "")
                                if un.lower() == uname.lower():
                                    return u
                            except Exception:
                                continue
                    except Exception:
                        pass
            except Exception:
                pass
            return None
        except Exception:
            return None

    def _apply_avatar_to_user(self, user):
        if user is None or not self._bool("custom_avatar", False):
            return False
        if not self._is_self_user(user):
            return False
        src = self._resolve_avatar_user()
        if src is None:
            return False
        try:
            photo = getattr(src, "photo", None)
            if photo is None:
                try:
                    f = src.getClass().getDeclaredField("photo")
                    f.setAccessible(True)
                    photo = f.get(src)
                except Exception:
                    photo = None
            if photo is None:
                return False
            try:
                user.photo = photo
                return True
            except Exception:
                try:
                    f = user.getClass().getDeclaredField("photo")
                    f.setAccessible(True)
                    f.set(user, photo)
                    return True
                except Exception:
                    return False
        except Exception:
            return False

    def _apply_number_to_user(self, user):
        if user is None or not self._bool("custom_number", False):
            return False
        if not self._is_self_user(user):
            return False
        raw = str(self.get_setting("phone_number", "") or "").strip()
        digits = self._normalize_phone(raw)
        if not digits:
            return False
        changed = False
        try:
            cur = str(getattr(user, "phone", None) or "")
            if cur != digits:
                user.phone = digits
                changed = True
        except Exception:
            try:
                f = user.getClass().getDeclaredField("phone")
                f.setAccessible(True)
                cur = str(f.get(user) or "")
                if cur != digits:
                    f.set(user, digits)
                    changed = True
            except Exception:
                pass
        try:
            cls = user.getClass()
            for f in cls.getFields():
                try:
                    if str(f.getType().getName()) != "java.lang.String":
                        continue
                    low = str(f.getName()).lower()
                    if "phone" not in low and low not in ("number", "phone_number", "phonenumber"):
                        continue
                    f.setAccessible(True)
                    cur = str(f.get(user) or "")
                    if cur != digits:
                        f.set(user, digits)
                        changed = True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            nested = getattr(user, "user", None)
            if nested is not None and nested is not user:
                try:
                    if str(getattr(nested, "phone", "") or "") != digits:
                        nested.phone = digits
                        changed = True
                except Exception:
                    pass
        except Exception:
            pass
        return changed

    def _is_self_user(self, obj):
        if obj is None:
            return False
        try:
            if bool(getattr(obj, "bot", False)):
                return False
        except Exception:
            pass
        uid = int(getattr(obj, "id", 0) or 0)
        if abs(uid) < 1000:
            return False
        my = self._my_id(int(UserConfig.selectedAccount))
        return abs(my) > 1000 and abs(uid) == abs(my)

    def _apply_identity_to(self, obj):
        if obj is None:
            return False
        user_id = 0
        if hasattr(obj, "id"):
            try:
                user_id = int(obj.id)
            except:
                pass
        if user_id == 0:
            try:
                user_id = int(getattr(obj, "user_id", 0) or 0)
            except:
                pass
        if user_id == 0:
            try:
                for fname in ("id", "user_id"):
                    try:
                        f = obj.getClass().getDeclaredField(fname)
                        f.setAccessible(True)
                        val = f.get(obj)
                        if val is not None:
                            user_id = int(val)
                            break
                    except:
                        pass
            except:
                pass
        if user_id == 0:
            return False
        my = self._my_id(int(UserConfig.selectedAccount))
        if user_id == my:
            changed = False
            if self._bool("custom_rating", False):
                if self._apply_rating_to(obj, self._get_local_rating()):
                    changed = True
            if self._apply_name_to_user(obj):
                changed = True
            if self._apply_avatar_to_user(obj):
                changed = True
            if self._apply_number_to_user(obj):
                changed = True
            names = self._visual_usernames()
            if self._bool("custom_visual_username", False) and names:
                if self._set_visual_username_on_user(obj, names[0]):
                    changed = True
                if self._ensure_visual_usernames(obj, names):
                    changed = True
            if self._apply_badge_to_user(obj):
                changed = True
            return changed
        else:
            if self._bool("sync_enabled", True):
                return self._apply_remote_identity(obj, user_id)
            return False

    def _paint_self_cache(self):
        try:
            if not self._identity_needed():
                return
            now = time.time()
            if now - float(getattr(self, "_paint_ts", 0) or 0) < 2.0:
                return
            self._paint_ts = now
            account = int(UserConfig.selectedAccount)
            my = self._my_id(account)
            if my <= 0:
                self._log("paint_cache: no my id")
                return
            changed = 0
            ctrl = MessagesController.getInstance(account)
            try:
                u = ctrl.getUser(int(my))
                if self._apply_identity_to(u):
                    changed += 1
            except Exception as e:
                self._log("paint user: %s" % e)
            full = None
            try:
                full = ctrl.getUserFull(int(my))
            except Exception:
                full = None
            if full is not None:
                if self._apply_identity_to(full):
                    changed += 1
                try:
                    if self._apply_identity_to(getattr(full, "user", None)):
                        changed += 1
                except Exception:
                    pass
            try:
                if self._apply_identity_to(UserConfig.getInstance(account).getCurrentUser()):
                    changed += 1
            except Exception:
                pass
            try:
                now = time.time()
                if changed or now - float(getattr(self, "_paint_log_ts", 0) or 0) > 5.0:
                    self._paint_log_ts = now
                    self._log("paint_cache my=%s changed=%s badge=%s rating=%s" % (
                        my, changed, self._badge_mode(), self._bool("custom_rating", False)
                    ))
            except Exception:
                pass
            if changed:
                try:
                    self._post_user_info_did_load("paint_cache")
                except Exception:
                    pass
        except Exception as e:
            self._log("paint_cache: %s" % e)

    def _verification_desc(self):
        mode = self._badge_mode()
        if mode == 1:
            return HOLD_DESC
        if mode == 2:
            return MAJOR_DESC
        return ""

    def _apply_profile_ui_badge(self):
        try:
            if self._badge_mode() == 0:
                return
            frag = get_last_fragment()
            if frag is None:
                return
            try:
                cname = str(frag.getClass().getName())
            except Exception:
                return
            if "ProfileActivity" not in cname:
                return
            did = 0
            try:
                did = int(_extract_dialog_id(frag) or 0)
            except Exception:
                did = 0
            if abs(did) < 1000:
                try:
                    did = int(getattr(frag, "userId", 0) or 0)
                except Exception:
                    pass
            my = self._my_id(int(UserConfig.selectedAccount))
            if abs(my) < 1000:
                return
            if abs(did) > 1000 and abs(did) != abs(my):
                return
            desc = self._verification_desc()
            if not desc:
                return
            roots = []
            for g in ("getFragmentView", "getView"):
                try:
                    v = getattr(frag, g)()
                    if v is not None:
                        roots.append(v)
                except Exception:
                    pass
            hits = 0
            for root in roots:
                stack = [root]
                steps = 0
                while stack and steps < 700:
                    steps += 1
                    v = stack.pop()
                    try:
                        for i in range(int(v.getChildCount())):
                            stack.append(v.getChildAt(i))
                    except Exception:
                        pass
                    try:
                        cn = str(v.getClass().getName())
                    except Exception:
                        continue
                    if "SimpleTextView" not in cn and not cn.endswith(".TextView"):
                        continue
                    try:
                        t = str(v.getText() or "")
                    except Exception:
                        t = ""
                    if not t:
                        continue
                    low = t.lower()
                    if any(x in low for x in (
                        "верифицирован", "организац", "hold", "major",
                        "verified by", "organization"
                    )):
                        try:
                            v.setText(desc)
                            hits += 1
                        except Exception:
                            pass
            if hits:
                self._log("profile ui badge text hits=%d" % hits)
        except Exception as e:
            self._log("profile ui badge: %s" % e)

    def _rating_level_value(self):
        try:
            return max(1, self._int_setting("rating_level", 10))
        except Exception:
            return 10

    def _find_profile_fragment(self):
        candidates = []
        seen = set()

        def _add(fr):
            if fr is None:
                return
            try:
                i = id(fr)
                if i in seen:
                    return
                seen.add(i)
                candidates.append(fr)
            except Exception:
                candidates.append(fr)

        try:
            _add(get_last_fragment())
        except Exception:
            pass
        try:
            la = _cls(LAUNCH_ACTIVITY)
            inst = getattr(la, "instance", None) if la else None
            if inst is not None:
                for attr in ("actionBarLayout", "mainFragmentsStack", "fragmentsStack", "rightActionBarLayout", "layersActionBarLayout"):
                    try:
                        layout = getattr(inst, attr, None)
                        if layout is None:
                            continue
                        try:
                            for i in range(int(layout.size())):
                                _add(layout.get(i))
                        except Exception:
                            pass
                        try:
                            stack = getattr(layout, "fragmentsStack", None)
                            if stack is not None:
                                for i in range(int(stack.size())):
                                    _add(stack.get(i))
                        except Exception:
                            pass
                    except Exception:
                        pass
        except Exception:
            pass
        profile = None
        for fr in candidates:
            try:
                cn = str(fr.getClass().getName())
            except Exception:
                continue
            if "ProfileActivity" in cn:
                profile = fr
                break
        if profile is None:
            for fr in candidates:
                try:
                    cn = str(fr.getClass().getName())
                except Exception:
                    continue
                if "Profile" in cn:
                    profile = fr
                    break
        return profile, candidates

    def _dig_profile_from_tabs(self):
        try:
            frag = get_last_fragment()
        except Exception:
            frag = None
        tabs = frag
        try:
            if frag is not None and "MainTabs" not in str(frag.getClass().getName()):
                tabs = None
        except Exception:
            tabs = frag
        found = []
        roots = []
        if frag is not None:
            roots.append(frag)
        try:
            la = _cls(LAUNCH_ACTIVITY)
            inst = getattr(la, "instance", None) if la else None
            if inst is not None:
                for attr in ("actionBarLayout", "mainFragmentsStack", "fragmentsStack"):
                    try:
                        layout = getattr(inst, attr, None)
                        stack = getattr(layout, "fragmentsStack", None) if layout is not None else None
                        if stack is not None:
                            for i in range(int(stack.size())):
                                roots.append(stack.get(i))
                        elif layout is not None and hasattr(layout, "size"):
                            for i in range(int(layout.size())):
                                roots.append(layout.get(i))
                    except Exception:
                        pass
        except Exception:
            pass
        for root in roots:
            if root is None:
                continue
            try:
                if "ProfileActivity" in str(root.getClass().getName()):
                    return root
            except Exception:
                pass
            try:
                cls = root.getClass()
                depth = 0
                while cls is not None and depth < 5:
                    depth += 1
                    for f in cls.getDeclaredFields():
                        try:
                            f.setAccessible(True)
                            val = f.get(root)
                            if val is None:
                                continue
                            try:
                                vcn = str(val.getClass().getName())
                            except Exception:
                                vcn = ""
                            if "ProfileActivity" in vcn:
                                return val
                            if "TabState" in vcn or "Fragment" in vcn:
                                for attr in ("fragment", "fragmentClass", "baseFragment", "obj", "object"):
                                    try:
                                        inner = getattr(val, attr, None)
                                        if inner is None:
                                            try:
                                                ff = val.getClass().getDeclaredField(attr)
                                                ff.setAccessible(True)
                                                inner = ff.get(val)
                                            except Exception:
                                                inner = None
                                        if inner is not None and "ProfileActivity" in str(inner.getClass().getName()):
                                            return inner
                                    except Exception:
                                        pass
                            try:
                                n = int(val.size()) if hasattr(val, "size") else int(val.length)
                                for i in range(n):
                                    item = val.get(i) if hasattr(val, "get") else val[i]
                                    if item is None:
                                        continue
                                    if "ProfileActivity" in str(item.getClass().getName()):
                                        return item
                                    for attr in ("fragment", "baseFragment", "obj"):
                                        try:
                                            inner = getattr(item, attr, None)
                                            if inner is not None and "ProfileActivity" in str(inner.getClass().getName()):
                                                return inner
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                        except Exception:
                            continue
                    try:
                        cls = cls.getSuperclass()
                    except Exception:
                        break
            except Exception:
                pass
        return None

    def _force_profile_level_badge(self):
        if not self._bool("custom_rating", False):
            return
        try:
            account = int(UserConfig.selectedAccount)
            my = self._my_id(account)
            if my <= 0:
                return
            try:
                full = MessagesController.getInstance(account).getUserFull(int(my))
                if full is not None:
                    self._apply_rating_to(full)
            except Exception:
                pass
            now = time.time()
            if now - float(getattr(self, "_lvl_dig_ts", 0) or 0) < 3.0:
                return
            self._lvl_dig_ts = now
            prof = self._dig_profile_from_tabs()
            if prof is not None:
                for fname in ("userInfo", "userFull", "currentUserFull"):
                    try:
                        u = getattr(prof, fname, None)
                        if u is not None:
                            self._apply_rating_to(u)
                    except Exception:
                        pass
                for mname in ("updateProfileData", "updateAvatarLayout"):
                    try:
                        m = prof.getClass().getDeclaredMethod(mname)
                        m.setAccessible(True)
                        m.invoke(prof)
                    except Exception:
                        try:
                            m = prof.getClass().getDeclaredMethod(mname, jclass("boolean"))
                            m.setAccessible(True)
                            m.invoke(prof, False)
                        except Exception:
                            pass
            else:
                pass
        except Exception as e:
            self._log("force level: %s" % e)

    def _visual_usernames(self):
        try:
            raw = self.get_setting('visual_usernames', '[]')
            values = json.loads(str(raw)) if raw else []
        except Exception:
            values = []
        if not isinstance(values, (list, tuple)):
            return []
        result = []
        seen = set()
        for value in values:
            name = self._normalize_visual_username(value)
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(name)
            if len(result) >= 30:
                break
        return result

    def _normalize_visual_username(self, value):
        try:
            name = str(value or '').strip()
            if name.startswith('@'):
                name = name[1:]
            name = ''.join((
                char for char in name
                if ('a' <= char <= 'z') or ('A' <= char <= 'Z')
                or ('0' <= char <= '9') or char == '_'
            ))
            return name[:32]
        except Exception:
            return ''

    def _visual_username_status(self):
        if not self._bool('custom_visual_username', False):
            return 'Выключено'
        names = self._visual_usernames()
        if not names:
            return 'Выключено'
        if len(names) == 1:
            return '@' + names[0]
        return '@%s (+%d)' % (names[0], len(names) - 1)

    def _visual_username_switch(self, value):
        try:
            enabled = self._as_bool(value)
            self.set_setting('custom_visual_username', enabled)
            self._apply_visual_usernames()
        except Exception as e:
            self._log('username switch: %s' % e)

    def _show_visual_username_list(self, names):
        try:
            text = ', '.join(('@' + name for name in (names or self._visual_usernames())))
            BulletinHelper.show_info(text or 'Список пуст')
        except Exception:
            pass

    def _clear_visual_usernames(self):
        try:
            self.set_setting('visual_usernames', '[]')
            self.set_setting('custom_visual_username', False)
            self._apply_visual_usernames()
        except Exception as e:
            self._log('clear visual usernames: %s' % e)

    def _input(self, title, prefill, on_submit, numeric=False):
        try:
            from android.widget import EditText, FrameLayout
            from ui.alert import AlertDialogBuilder
            fragment = get_last_fragment()
            ctx = fragment.getParentActivity() if fragment else None
            if ctx is None:
                return
            container = FrameLayout(ctx)
            et = EditText(ctx)
            et.setText(str(prefill or ''))
            try:
                from org.telegram.ui.ActionBar import Theme
                et.setTextColor(Theme.getColor(Theme.key_dialogTextBlack))
                et.setHintTextColor(Theme.getColor(Theme.key_dialogTextHint))
            except Exception:
                pass
            if numeric:
                et.setInputType(2)
            lp = FrameLayout.LayoutParams(-1, -2)
            try:
                lp.leftMargin = AndroidUtilities.dp(20)
                lp.rightMargin = AndroidUtilities.dp(20)
            except Exception:
                pass
            et.setLayoutParams(lp)
            container.addView(et)
            builder = AlertDialogBuilder(ctx)
            builder.set_title(title)
            builder.set_view(container)
            def _ok(dialog, which):
                try:
                    on_submit(str(et.getText()))
                except Exception as e:
                    self._log('username input: %s' % e)
            builder.set_positive_button('Сохранить', _ok)
            builder.set_negative_button('Отмена', None)
            run_on_ui_thread(builder.show)
        except Exception as e:
            self._log('username input dialog: %s' % e)

    def _add_visual_username(self, username):
        return self._add_visual_usernames(username)

    def _split_visual_usernames(self, value):
        
        try:
            text = str(value or '').strip()
            for separator in (',', ';', '\n', '\r', '\t', ' '):
                text = text.replace(separator, ' ')
            result = []
            seen = set()
            for part in text.split():
                name = self._normalize_visual_username(part)
                if name and name.casefold() not in seen:
                    seen.add(name.casefold())
                    result.append(name)
            return result[:30]
        except Exception:
            return []

    def _add_visual_usernames(self, value):
        try:
            incoming = self._split_visual_usernames(value)
            if not incoming:
                BulletinHelper.show_error('Введите один или несколько username через запятую')
                return
            names = self._visual_usernames()
            incoming_keys = {name.casefold() for name in incoming}
            names = incoming + [
                name for name in names if name.casefold() not in incoming_keys
            ]
            self.set_setting('visual_usernames', json.dumps(names[:30], ensure_ascii=False))
            self.set_setting('custom_visual_username', True)
            self._apply_visual_usernames()
            BulletinHelper.show_info(
                'Сохранено username: ' + ', '.join('@' + name for name in incoming)
            )
        except Exception as e:
            self._log('add visual usernames: %s' % e)

    def _apply_visual_usernames(self):
        
        try:
            account = int(UserConfig.selectedAccount)
            my = self._my_id(account)
            if my <= 0:
                return False
            ctrl = MessagesController.getInstance(account)
            user = ctrl.getUser(my)
            if user is None:
                return False
            enabled = self._bool('custom_visual_username', False)
            names = self._visual_usernames()
            target = names[0] if enabled and names else ''
            if self.get_setting('visual_username_original', None) is None:
                try:
                    self.set_setting('visual_username_original', str(getattr(user, 'username', '') or ''))
                except Exception:
                    pass
            original = str(self.get_setting('visual_username_original', '') or '')
            changed = False
            
            if user is not None:
                if self._set_visual_username_on_user(user, target if enabled else original):
                    changed = True
                if enabled and names:
                    if self._ensure_visual_usernames(user, names):
                        changed = True
            
            try:
                current = UserConfig.getInstance(account).getCurrentUser()
                if current is not None:
                    if self._set_visual_username_on_user(current, target if enabled else original):
                        changed = True
                    if enabled and names:
                        if self._ensure_visual_usernames(current, names):
                            changed = True
            except Exception:
                pass
            
            try:
                full = ctrl.getUserFull(my)
                if full is not None:
                    nested = getattr(full, 'user', None)
                    if nested is not None:
                        if self._set_visual_username_on_user(nested, target if enabled else original):
                            changed = True
                        if enabled and names:
                            if self._ensure_visual_usernames(nested, names):
                                changed = True
            except Exception:
                pass
            
            
            return changed
        except Exception as e:
            self._log('apply visual username: %s' % e)
            return False

    def _ensure_visual_usernames(self, user, names):
        
        if user is None:
            return False
        normalized = []
        seen = set()
        for value in names or []:
            name = self._normalize_visual_username(value)
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            normalized.append(name)
        if not normalized:
            return False
        changed = False
        
        usernames = self._get_user_field(user, 'usernames')
        if usernames is None:
            try:
                usernames = ArrayList()
                changed = self._set_user_field(user, 'usernames', usernames) or changed
            except Exception:
                usernames = None
        
        if usernames is not None:
            existing = {}
            for entry in self._list_items(usernames):
                entry_name = self._normalize_visual_username(
                    self._get_user_field(entry, 'username', entry)
                )
                if entry_name:
                    existing[entry_name.casefold()] = entry
            
            for index, name in enumerate(normalized):
                entry = existing.get(name.casefold())
                if entry is None:
                    try:
                        username_cls = _cls('org.telegram.tgnet.TLRPC$TL_username')
                        if username_cls is None:
                            username_cls = _cls('org.telegram.tgnet.tl.TLRPC$TL_username')
                        entry = _new_instance(username_cls) if username_cls is not None else None
                    except Exception:
                        entry = None
                    if entry is None:
                        continue
                    self._set_user_field(entry, 'username', name)
                    self._set_user_field(entry, 'active', True)
                    self._set_user_field(entry, 'editable', False)
                    self._set_user_field(entry, 'flags', 2)
                    changed = self._list_add(usernames, entry, index) or changed
                else:
                    if self._set_user_field(entry, 'active', True):
                        changed = True
                    if self._set_user_field(entry, 'editable', False):
                        changed = True
                    if self._set_user_field(entry, 'flags', 2):
                        changed = True

        try:
            flags2 = int(self._get_user_field(user, 'flags2', 0) or 0)
            if self._set_user_field(user, 'flags2', flags2 | 1):
                changed = True
        except Exception:
            pass
        
        active_usernames = self._get_user_field(user, 'active_usernames')
        if active_usernames is not None:
            existing_active = {
                str(item).strip().lstrip('@').casefold()
                for item in self._list_items(active_usernames)
                if str(item).strip()
            }
            for name in normalized:
                if name.casefold() not in existing_active:
                    if self._list_add(active_usernames, name):
                        changed = True
        
        editable_usernames = self._get_user_field(user, 'editable_usernames')
        if editable_usernames is not None:
            try:
                if hasattr(editable_usernames, 'clear'):
                    editable_usernames.clear()
                    changed = True
            except Exception:
                pass
        
        return changed

    def _set_visual_username_on_user(self, user, value):
        if user is None:
            return False
        value = self._normalize_visual_username(value)
        changed = False
        try:
            current = str(self._get_user_field(user, 'username') or '')
            if current != value:
                changed = self._set_user_field(user, 'username', value)
        except Exception:
            pass
        if value:
            changed = self._ensure_visual_username_lists(user, value) or changed
        return changed

    def _get_user_field(self, obj, name, default=None):
        if obj is None:
            return default
        try:
            value = getattr(obj, name, None)
            if value is not None:
                return value
        except Exception:
            pass
        try:
            field = _find_field(obj, name)
            if field is None:
                return default
            value = field.get(obj)
            return default if value is None else value
        except Exception:
            return default

    def _set_user_field(self, obj, name, value):
        if obj is None:
            return False
        try:
            if getattr(obj, name, None) == value:
                return False
        except Exception:
            pass
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            pass
        try:
            field = _find_field(obj, name)
            if field is None:
                return False
            current = field.get(obj)
            if current == value or (value is not None and str(current) == str(value)):
                return False
            field.set(obj, value)
            return True
        except Exception:
            return False

    def _list_items(self, values):
        if values is None:
            return []
        try:
            return [values.get(i) for i in range(int(values.size()))]
        except Exception:
            try:
                return list(values)
            except Exception:
                return []

    def _list_add(self, values, item, index=None):
        try:
            if index is None:
                values.add(item)
            else:
                values.add(index, item)
            return True
        except Exception:
            try:
                if index is None:
                    values.append(item)
                else:
                    values.insert(index, item)
                return True
            except Exception:
                return False

    def _ensure_visual_username_lists(self, user, username):
        changed = False
        usernames = self._get_user_field(user, 'usernames')
        if usernames is None:
            try:
                usernames = ArrayList()
                changed = self._set_user_field(user, 'usernames', usernames)
            except Exception:
                usernames = None
        if usernames is not None:
            found = False
            for entry in self._list_items(usernames):
                entry_name = self._normalize_visual_username(
                    self._get_user_field(entry, 'username', entry)
                )
                if entry_name.casefold() != username.casefold():
                    continue
                found = True
                changed = self._set_user_field(entry, 'active', True) or changed
                changed = self._set_user_field(entry, 'editable', False) or changed
                changed = self._set_user_field(entry, 'flags', 2) or changed
                break
            if not found:
                entry = None
                try:
                    username_cls = _cls('org.telegram.tgnet.TLRPC$TL_username')
                    if username_cls is None:
                        username_cls = _cls('org.telegram.tgnet.tl.TLRPC$TL_username')
                    if username_cls is not None:
                        entry = _new_instance(username_cls)
                        if entry is not None:
                            self._set_user_field(entry, 'username', username)
                            self._set_user_field(entry, 'active', True)
                            self._set_user_field(entry, 'editable', False)
                            self._set_user_field(entry, 'flags', 2)
                except Exception:
                    entry = None
                if entry is None:
                    entry = username
                changed = self._list_add(usernames, entry, 0) or changed
        for field_name in ('active_usernames', 'editable_usernames'):
            values = self._get_user_field(user, field_name)
            if values is None:
                continue
            existing = {
                str(item).strip().lstrip('@').casefold()
                for item in self._list_items(values)
                if str(item).strip()
            }
            if username.casefold() not in existing:
                changed = self._list_add(values, username) or changed
        return changed

    def _identity_needed(self):
        try:
            if self._bool("custom_rating", False):
                return True
            if self._bool("custom_number", False):
                return True
            if self._bool("custom_name", False):
                return True
            if self._bool("custom_avatar", False):
                return True
            if self._badge_mode() != 0:
                return True
            if self._bool("custom_visual_username", False) and self._visual_usernames():
                return True
        except Exception:
            pass
        return False

    def _force_profile_phone_ui(self, pa=None):
        if not self._bool("custom_number", False):
            return
        raw = str(self.get_setting("phone_number", "") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return
        display = "+" + digits
        try:
            account = int(UserConfig.selectedAccount)
            my = self._my_id(account)
            ctrl = MessagesController.getInstance(account)
            try:
                u = ctrl.getUser(int(my))
                self._apply_number_to_user(u)
            except Exception:
                pass
            try:
                full = ctrl.getUserFull(int(my))
                if full is not None:
                    self._apply_number_to_user(full)
                    self._apply_number_to_user(getattr(full, "user", None))
            except Exception:
                pass
            try:
                self._apply_number_to_user(UserConfig.getInstance(account).getCurrentUser())
            except Exception:
                pass
        except Exception:
            pass
        try:
            if pa is None:
                try:
                    pa = get_last_fragment()
                except Exception:
                    pa = None
            roots = []
            if pa is not None:
                for g in ("getFragmentView", "getView"):
                    try:
                        v = getattr(pa, g)()
                        if v is not None:
                            roots.append(v)
                    except Exception:
                        pass
            try:
                la = _cls(LAUNCH_ACTIVITY)
                inst = getattr(la, "instance", None) if la else None
                if inst is not None:
                    roots.append(inst.getWindow().getDecorView())
            except Exception:
                pass
            hits = 0
            for root in roots:
                if root is None:
                    continue
                stack = [root]
                steps = 0
                while stack and steps < 1200:
                    steps += 1
                    v = stack.pop()
                    try:
                        for i in range(int(v.getChildCount())):
                            stack.append(v.getChildAt(i))
                    except Exception:
                        pass
                    try:
                        cn = str(v.getClass().getName()).lower()
                    except Exception:
                        continue
                    if "textview" not in cn and "simpletext" not in cn:
                        continue
                    try:
                        t = str(v.getText() or "").strip()
                    except Exception:
                        t = ""
                    if not t:
                        continue
                    td = "".join(ch for ch in t if ch.isdigit())
                    if t.startswith("+") and len(td) >= 7:
                        if td != digits:
                            try:
                                v.setText(display)
                                hits += 1
                            except Exception:
                                pass
                        continue
                    if 10 <= len(td) <= 15 and len(t) <= 20:
                        if td != digits:
                            try:
                                v.setText(display)
                                hits += 1
                            except Exception:
                                pass
                        continue
                    low = t.lower()
                    if any(x in low for x in ("телефон", "phone", "мобильный", "mobile")):
                        pass
            if hits:
                if time.time() - float(getattr(self, "_phone_ui_log", 0) or 0) > 2.0:
                    self._phone_ui_log = time.time()
                    self._log("phone UI hits=%s -> %s" % (hits, display))
        except Exception as e:
            self._log("phone UI: %s" % e)

    def _post_user_info_did_load(self, reason="rating"):
        try:
            if getattr(self, "_patching_nc", False):
                return
            if not self._bool("custom_rating", False) and not self._bool("custom_number", False) and self._badge_mode() == 0:
                return
            now = time.time()
            last = float(getattr(self, "_uidl_ts", 0) or 0)
            if now - last < 2.5:
                return
            self._uidl_ts = now
            account = int(UserConfig.selectedAccount)
            my = self._my_id(account)
            if my <= 0:
                return

            def _emit():
                try:
                    self._patching_nc = True
                except Exception:
                    pass
                try:
                    NC = jclass("org.telegram.messenger.NotificationCenter")
                    nc = NC.getInstance(int(account))
                    if nc is None:
                        return
                    eid = 0
                    try:
                        eid = int(NotificationCenter.userInfoDidLoad)
                    except Exception:
                        try:
                            eid = int(getattr(NC, "userInfoDidLoad"))
                        except Exception:
                            eid = 0
                    if eid <= 0:
                        self._log("userInfoDidLoad id missing")
                        return
                    ctrl = MessagesController.getInstance(account)
                    full = None
                    try:
                        full = ctrl.getUserFull(int(my))
                    except Exception:
                        full = None
                    if full is not None:
                        try:
                            self._apply_rating_to(full)
                        except Exception:
                            pass
                    try:
                        nc.postNotificationName(int(eid), int(my), full)
                        if time.time() - float(getattr(self, "_uidl_log_ts", 0) or 0) > 2.0:
                            self._uidl_log_ts = time.time()
                            self._log("posted userInfoDidLoad my=%s reason=%s" % (my, reason))
                    except Exception as e:
                        try:
                            nc.postNotificationName(int(eid), jclass("java.lang.Long")(int(my)), full)
                        except Exception as e2:
                            self._log("userInfoDidLoad post fail: %s / %s" % (e, e2))
                except Exception as e:
                    self._log("post uidl: %s" % e)
                finally:
                    try:
                        self._patching_nc = False
                    except Exception:
                        pass

            _run_ui(_emit, 0)
        except Exception as e:
            self._log("post_user_info: %s" % e)

    def _patch_rating_view_on_profile(self, pa):
        if pa is None or not self._bool("custom_rating", False):
            return False
        changed = False
        try:
            for fname in ("userInfo", "userFull", "currentUserInfo", "currentUserFull"):
                try:
                    f = pa.getClass().getDeclaredField(fname)
                    f.setAccessible(True)
                    obj = f.get(pa)
                except Exception:
                    try:
                        obj = getattr(pa, fname, None)
                    except Exception:
                        obj = None
                if obj is None:
                    continue
                if not self._is_self_user(obj):
                    continue
                try:
                    if self._apply_rating_to(obj):
                        changed = True
                except Exception:
                    pass
            rating_view = None
            try:
                f = pa.getClass().getDeclaredField("ratingView")
                f.setAccessible(True)
                rating_view = f.get(pa)
            except Exception:
                try:
                    rating_view = getattr(pa, "ratingView", None)
                except Exception:
                    rating_view = None
            if rating_view is not None:
                for fname in ("userInfo", "userFull", "currentUserInfo", "currentUserFull"):
                    try:
                        obj = None
                        try:
                            f = pa.getClass().getDeclaredField(fname)
                            f.setAccessible(True)
                            obj = f.get(pa)
                        except Exception:
                            obj = getattr(pa, fname, None)
                        if obj is None or not self._is_self_user(obj):
                            continue
                        try:
                            setattr(rating_view, fname, obj)
                            changed = True
                        except Exception:
                            try:
                                f = rating_view.getClass().getDeclaredField(fname)
                                f.setAccessible(True)
                                f.set(rating_view, obj)
                                changed = True
                            except Exception:
                                pass
                    except Exception:
                        pass
                try:
                    rating_view.invalidate()
                except Exception:
                    pass
                try:
                    if hasattr(rating_view, "getChildCount"):
                        n = min(int(rating_view.getChildCount() or 0), 12)
                        for i in range(n):
                            try:
                                rating_view.getChildAt(i).invalidate()
                            except Exception:
                                pass
                except Exception:
                    pass
                if time.time() - float(getattr(self, "_rv_log_ts", 0) or 0) > 2.0:
                    self._rv_log_ts = time.time()
                    self._log("ratingView patched/invalidated")
            return changed
        except Exception as e:
            self._log("patch ratingView: %s" % e)
            return False

    def _hook_profile_rating_ui(self):
        if getattr(self, "_profile_rating_ui_done", False):
            return
        self._profile_rating_ui_done = True
        plugin = self
        PA = _cls("org.telegram.ui.ProfileActivity")
        if PA is None:
            self._log("ProfileActivity class not found")
            return

        class PAHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    if getattr(plugin, "_patching_nc", False):
                        return
                    if not (plugin._bool("custom_rating", False) or plugin._bool("custom_number", False) or plugin._bool("custom_name", False) or plugin._bool("custom_avatar", False) or plugin._badge_mode() != 0):
                        return
                    now = time.time()
                    if now - float(getattr(plugin, "_pa_hook_ts", 0) or 0) < 2.0:
                        return
                    plugin._pa_hook_ts = now
                    this = param.thisObject
                    if this is None:
                        return
                    my = plugin._my_id(int(UserConfig.selectedAccount))
                    did = 0
                    for attr in ("userId", "dialogId", "peerId"):
                        try:
                            v = getattr(this, attr, None)
                            if v is not None and abs(int(v)) > 1000:
                                did = int(v)
                                break
                        except Exception:
                            pass
                    if abs(did) < 1000:
                        try:
                            did = int(_extract_dialog_id(this) or 0)
                        except Exception:
                            pass
                    if abs(my) > 1000 and abs(did) > 1000 and abs(did) != abs(my):
                        if plugin._bool("sync_enabled", True):
                            for fname in ("userInfo", "userFull", "currentUserInfo", "currentUserFull"):
                                try:
                                    u = getattr(this, fname, None)
                                    if u is not None and plugin._apply_identity_to(u):
                                        pass
                                except Exception:
                                    pass
                    else:
                        try:
                            full = MessagesController.getInstance(int(UserConfig.selectedAccount)).getUserFull(int(my))
                            if full is not None:
                                plugin._apply_identity_to(full)
                                try:
                                    plugin._apply_identity_to(getattr(full, "user", None))
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        for fname in ("user", "currentUser", "userInfo", "userFull"):
                            try:
                                f = this.getClass().getDeclaredField(fname)
                                f.setAccessible(True)
                                obj = f.get(this)
                                if obj is not None:
                                    plugin._apply_identity_to(obj)
                            except Exception:
                                try:
                                    obj = getattr(this, fname, None)
                                    if obj is not None:
                                        plugin._apply_identity_to(obj)
                                except Exception:
                                    pass
                    try:
                        plugin._patch_rating_view_on_profile(this)
                    except Exception:
                        pass
                    mname = ""
                    try:
                        mname = str(param.method.getName())
                    except Exception:
                        mname = ""
                    if mname in ("onFragmentCreate", "onResume", "onBecomeFullyVisible"):
                        try:
                            plugin._post_user_info_did_load("PA." + mname)
                        except Exception:
                            pass
                        try:
                            plugin._force_profile_phone_ui(this)
                        except Exception:
                            pass
                except Exception as e:
                    try:
                        plugin._log("PAHook: %s" % e)
                    except Exception:
                        pass

        hooked = 0
        for mname in (
            "onFragmentCreate", "onResume", "onBecomeFullyVisible",
            "updateProfileData", "updateAvatarLayout", "updateRows",
        ):
            try:
                refs = self.hook_all_methods(PA, mname, PAHook())
                if refs:
                    n = 1 if not isinstance(refs, list) else len(refs)
                    hooked += n
                    self._hooks.extend(refs if isinstance(refs, list) else [refs])
            except Exception:
                pass
        self._log("ProfileActivity rating hooks: %s" % hooked)
        try:
            SRV = _cls("org.telegram.ui.Components.StarRatingView")
            if SRV is not None:
                class SRVHook(MethodHook):
                    def after_hooked_method(self, param):
                        try:
                            if not plugin._bool("custom_rating", False):
                                return
                            v = param.thisObject
                            if v is not None:
                                try:
                                    v.invalidate()
                                except Exception:
                                    pass
                        except Exception:
                            pass

                n2 = 0
                for mname in ("setVisibility", "onMeasure", "setLayoutParams", "requestLayout"):
                    try:
                        refs = self.hook_all_methods(SRV, mname, SRVHook())
                        if refs:
                            n2 += 1 if not isinstance(refs, list) else len(refs)
                            self._hooks.extend(refs if isinstance(refs, list) else [refs])
                    except Exception:
                        pass
                self._log("StarRatingView hooks: %s" % n2)
        except Exception as e:
            self._log("StarRatingView skip: %s" % e)

    def _hook_identity(self):
        if getattr(self, "_identity_hook_done", False):
            return
        self._identity_hook_done = True
        plugin = self
        self._id_last_apply = 0.0

        class IdentityHook(MethodHook):
            def after_hooked_method(self, param):
                try:
                    if not plugin._identity_needed():
                        return
                    name = ""
                    try:
                        name = str(param.method.getName())
                    except Exception:
                        pass
                    now = time.time()
                    if name != "getUserFull":
                        if now - float(getattr(plugin, "_id_last_apply", 0) or 0) < 1.5:
                            return
                    res = None
                    try:
                        res = param.getResult()
                    except Exception:
                        res = None
                    if res is not None:
                        if plugin._apply_identity_to(res):
                            plugin._id_last_apply = now
                    if name in ("saveUserFull", "putUser", "putUsers", "putFullUser", "loadFullUser"):
                        args = param.args
                        if args:
                            for a in args:
                                if a is None:
                                    continue
                                try:
                                    if plugin._apply_identity_to(a):
                                        plugin._id_last_apply = now
                                except Exception:
                                    pass
                except Exception:
                    pass

        MC = _cls("org.telegram.messenger.MessagesController")
        if MC is not None:
            for mname in (
                "getUserFull", "saveUserFull", "putFullUser", "loadFullUser",
                "getUser",
            ):
                try:
                    refs = self.hook_all_methods(MC, mname, IdentityHook())
                    if refs:
                        self._hooks.extend(refs if isinstance(refs, list) else [refs])
                except Exception:
                    pass
        PA = _cls("org.telegram.ui.ProfileActivity")
        if PA is not None:
            class ProfileIdHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        if not plugin._identity_needed():
                            return
                        now = time.time()
                        if now - float(getattr(plugin, "_id_last_apply", 0) or 0) < 0.15:
                            return
                        this = param.thisObject
                        if this is None:
                            return
                        for fname in ("userInfo", "userFull", "currentUserFull", "user"):
                            try:
                                u = getattr(this, fname, None)
                                if u is not None and plugin._apply_identity_to(u):
                                    plugin._id_last_apply = now
                            except Exception:
                                pass
                        try:
                            plugin._paint_self_cache()
                        except Exception:
                            pass
                        try:
                            plugin._apply_profile_ui_badge()
                        except Exception:
                            pass
                        try:
                            plugin._force_profile_level_badge()
                        except Exception:
                            pass
                    except Exception:
                        pass

            for mname in ("updateProfileData", "onFragmentCreate", "onResume", "updateRows", "updateItems"):
                try:
                    refs = self.hook_all_methods(PA, mname, ProfileIdHook())
                    if refs:
                        self._hooks.extend(refs if isinstance(refs, list) else [refs])
                except Exception:
                    pass

            class ProfileResumeHook(MethodHook):
                def after_hooked_method(self, param):
                    try:
                        if not plugin._bool("custom_rating", False):
                            return

                        def _again():
                            try:
                                plugin._paint_self_cache()
                            except Exception:
                                pass
                            try:
                                plugin._force_profile_level_badge()
                            except Exception:
                                pass

                        for d in (80, 250, 600, 1200, 2500):
                            _run_ui(_again, d)
                    except Exception:
                        pass

            try:
                refs = self.hook_all_methods(PA, "onBecomeFullyVisible", ProfileResumeHook())
                if refs:
                    self._hooks.extend(refs if isinstance(refs, list) else [refs])
            except Exception:
                pass

    def _log(self, msg, force=False):
        try:
            line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), str(msg))
            if not hasattr(self, "_log_buf"):
                self._log_buf = []
            self._log_buf.append(line)
            if len(self._log_buf) > 400:
                self._log_buf = self._log_buf[-250:]
            try:
                self.log(str(msg))
            except Exception:
                pass
        except Exception:
            pass

    def _log_filename(self):
        try:
            ver = str(__version__).replace(" ", "_")
        except Exception:
            ver = "unknown"
        return "larpnft_v%s_debug.log" % ver

    def _log_path(self):
        name = self._log_filename()
        try:
            env = jclass("android.os.Environment")
            dl = env.getExternalStoragePublicDirectory(env.DIRECTORY_DOWNLOADS)
            if dl is not None:
                f = jclass("java.io.File")(dl, name)
                return str(f.getAbsolutePath())
        except Exception:
            pass
        for base in (
            "/storage/emulated/0/Download",
            "/sdcard/Download",
            "/storage/emulated/0/Downloads",
        ):
            return "%s/%s" % (base, name)
        try:
            ctx = ApplicationLoader.applicationContext
            d = ctx.getFilesDir()
            f = jclass("java.io.File")(d, name)
            return str(f.getAbsolutePath())
        except Exception:
            return "/storage/emulated/0/Download/%s" % name

    def _read_logs(self, max_lines=200):
        out = []
        try:
            if hasattr(self, "_log_buf") and self._log_buf:
                out.extend(self._log_buf[-max_lines:])
        except Exception:
            pass
        return out

    def _share_logs_click(self, *args, **kwargs):
        try:
            lines = self._read_logs(250)
            text = "\n".join(lines) if lines else "(пусто — включи «Подробные логи» и воспроизведи баг)"
            text = "LarpNFT v%s logs\n%s\n%s" % (
                str(__version__),
                self._log_path() or "буфер",
                text,
            )
            try:
                ctx = ApplicationLoader.applicationContext
                intent = jclass("android.content.Intent")(jclass("android.content.Intent").ACTION_SEND)
                intent.setType("text/plain")
                intent.putExtra(jclass("android.content.Intent").EXTRA_TEXT, text)
                chooser = jclass("android.content.Intent").createChooser(intent, "Отправить логи")
                chooser.addFlags(jclass("android.content.Intent").FLAG_ACTIVITY_NEW_TASK)
                ctx.startActivity(chooser)
                BulletinHelper.show_info("Логи отправлены")
            except Exception as e:
                try:
                    from android_utils import copy_to_clipboard
                    copy_to_clipboard(text)
                    BulletinHelper.show_info("Логи скопированы в буфер")
                except Exception:
                    cm = ctx.getSystemService(ctx.CLIPBOARD_SERVICE)
                    clip = jclass("android.content.ClipData").newPlainText("larpnft_logs", text)
                    cm.setPrimaryClip(clip)
                    BulletinHelper.show_info("Логи скопированы в буфер")
            self._log("logs shared, lines=%d" % len(lines), force=True)
        except Exception as e:
            self._log("share logs err: %s" % e, force=True)
            try:
                BulletinHelper.show_info("Ошибка отправки логов")
            except:
                pass

    def _clear_logs_click(self, *args, **kwargs):
        try:
            self._log_buf = []
            path = self._log_path()
            if path:
                try:
                    f = jclass("java.io.File")(path)
                    if f.exists():
                        f.delete()
                except:
                    pass
            try:
                BulletinHelper.show_info("Логи очищены")
            except Exception:
                pass
        except Exception as e:
            self._log("clear logs err: %s" % e, force=True)


def create_plugin():
    return LarpnftPlugin()


def get_plugin():
    return LarpnftPlugin()
