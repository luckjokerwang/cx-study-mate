# /// script
# dependencies = [
#   "playwright>=1.40.0",
#   "fonttools>=4.40.0",
# ]
# ///

"""
====================================================================
🎓 Chaoxing Study Mate (超星学习助手) - V2.5 终极生产版
====================================================================
- 跨平台支持：Windows / macOS / Linux 均可一键运行
- 极速镜像加速：自动检测国内外网络环境，启用清华/阿里镜像极速拉取
- 认证机制：手机“学习通” App 扫码登录，持久化存储在 auth.json（免密复用）
- 播放控制：100% 完整时长播放、真实心跳上报、突破失焦暂停、静音无头运行
- 多Tab支持：全面支持小节内多标签轮询 (学习目标 / 视频 / 章节测验 / 文档)
- 作业测验自选：自由选择【跳过测验】或【AI智能辅助解题并自动暂存草稿】
- 安全机制：防顶号下线强校验，杜绝虚假“打卡成功”，校园网卡顿自动看门狗
====================================================================
"""

import os
import sys
import time
import json
import re
import io
import base64
import hashlib
import argparse
import urllib.request
import urllib.parse
import math
import shutil
import subprocess
import platform
import threading
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_VERSION = "2.9.0"
AUTH_FILE = os.path.join(BASE_DIR, "auth.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
COURSE_CACHE_FILE = os.path.join(BASE_DIR, "course_cache.json")
FONT_MAP_FILE = os.path.join(BASE_DIR, "font_map_table.json")
VERSION_FILE = os.path.join(BASE_DIR, "version.json")
UPDATE_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/luckjokerwang/cx-study-mate@main/",
    "https://ghproxy.net/https://raw.githubusercontent.com/luckjokerwang/cx-study-mate/main/",
    "https://raw.githubusercontent.com/luckjokerwang/cx-study-mate/main/"
]
KX_RADICALS_TAB = str.maketrans(
    '⼀⼁⼂⼃⼄⼅⼆⼇⼈⼉⼊⼋⼌⼍⼎⼏⼐⼑⼒⼓⼔⼕⼖⼗⼘⼙⼚⼛⼜⼝⼞⼟⼠⼡⼢⼣⼤⼥⼦⼧⼨⼩⼪⼫⼬⼭⼮⼯⼰⼱⼲⼳⼴⼵⼶⼷⼸⼹⼺⼻⼼⼽⼾⼿⽀⽁⽂⽃⽄⽅⽆⽇⽈⽉⽊⽋⽌⽍⽎⽏⽐⽑⽒⽓⽔⽕⽖⽗⽘⽙⽚⽛⽜⽝⽞⽟⽠⽡⽢⽣⽤⽥⽦⽧⽨⽩⽪⽫⽬⽭⽮⽯⽰⽱⽲⽳⽴⽵⽶⽷⽸⽹⽺⽻⽼⽽⽾⽿⾀⾁⾂⾃⾄⾅⾆⾇⾈⾉⾊⾋⾌⾍⾎⾏⾐⾑⾒⾓⾔⾕⾖⾗⾘⾙⾚⾛⾜⾝⾞⾟⾠⾡⾢⾣⾤⾥⾦⾧⾨⾩⾪⾫⾬⾭⾮⾯⾰⾱⾲⾳⾴⾵⾶⾷⾸⾹⾺⾻⾼髙⾽⾾⾿⿀⿁⿂⿃⿄⿅⿆⿇⿈⿉⿊⿋⿌⿍⿎⿏⿐⿑⿒⿓⿔⿕⺠⻬⻩⻢⻜⻅⺟⻓',
    '一丨丶丿乙亅二亠人儿入八冂冖冫几凵刀力勹匕匚匸十卜卩厂厶又口囗土士夂夊夕大女子宀寸小尢尸屮山巛工己巾干幺广廴廾弋弓彐彡彳心戈戶手支攴文斗斤方无日曰月木欠止歹殳毋比毛氏气水火爪父爻爿片牙牛犬玄玉瓜瓦甘生用田疋疒癶白皮皿目矛矢石示禸禾穴立竹米糸缶网羊羽老而耒耳聿肉臣自至臼舌舛舟艮色艸虍虫血行衣襾見角言谷豆豕豸貝赤走足身車辛辰辵邑酉采里金長門阜隶隹雨青非面革韋韭音頁風飞食首香馬骨高高髟鬥鬯鬲鬼魚鳥鹵鹿麥麻黃黍黑黹黽鼎鼓鼠鼻齊齒龍龜龠民齐黄马飞见母长'
)

def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)
def notify_user(title, message, is_popup=False, block=False):
    """
    全平台原生桌面弹窗与通知系统（Windows / macOS / Linux 通用）
    支持：
    1. 视频卡顿预警与深度卡顿告警
    2. 账号顶号下线与运行异常中断弹窗
    3. 课程全集播放完毕大功告成弹窗
    """
    sys.stdout.write('\a')
    sys.stdout.flush()
    log(f"🔔【系统提醒】{title}: {message}")

    try:
        cfg = load_config()
        notif_cfg = cfg.get("notification", {})
        if not notif_cfg.get("enabled", True):
            return
        if not notif_cfg.get("popup", True):
            is_popup = False
        is_persistent = notif_cfg.get("persistent", True)
    except Exception:
        is_persistent = True
    def _dispatch():
        plat = platform.system().lower()
        if 'windows' in plat:
            if is_popup:
                try:
                    import ctypes
                    # MB_ICONINFORMATION (0x40) | MB_SETFOREGROUND (0x10000) | MB_TOPMOST (0x40000)
                    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x10000 | 0x40000)
                    return
                except Exception:
                    pass
            try:
                show_timeout = 0 if is_persistent else 10000
                ps_script = (
                    f'[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
                    f'$obj = New-Object System.Windows.Forms.NotifyIcon; '
                    f'$obj.Icon = [System.Drawing.SystemIcons]::Information; '
                    f'$obj.BalloonTipTitle = "{title}"; '
                    f'$obj.BalloonTipText = "{message}"; '
                    f'$obj.Visible = $True; '
                    f'$obj.ShowBalloonTip({show_timeout});'
                )
                subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        elif 'darwin' in plat:
            try:
                safe_msg = message.replace('"', '\\"')
                safe_title = title.replace('"', '\\"')
                if is_popup:
                    cmd = ["osascript", "-e", f'display alert "{safe_title}" message "{safe_msg}" as informational']
                else:
                    cmd = ["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"']
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:  # Linux (GNOME, KDE, Arch, etc.)
            if is_popup:
                if shutil.which("zenity"):
                    try:
                        if block:
                            subprocess.run(
                                ["zenity", "--info", f"--title={title}", f"--text={message}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                            )
                        else:
                            subprocess.Popen(
                                ["zenity", "--info", f"--title={title}", f"--text={message}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                    except Exception:
                        pass
                elif shutil.which("kdialog"):
                    try:
                        if block:
                            subprocess.run(
                                ["kdialog", f"--title={title}", "--msgbox", message],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                            )
                        else:
                            subprocess.Popen(
                                ["kdialog", f"--title={title}", "--msgbox", message],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                    except Exception:
                        pass
            if shutil.which("notify-send"):
                try:
                    urgency = "critical" if is_popup else "normal"
                    # -t 0 告知通知中心永不超时自动消失，用户不主动点击或清理则一直常驻
                    expire_args = ["-t", "0"] if is_persistent else []
                    subprocess.run(
                        ["notify-send", "-u", urgency, *expire_args, title, message],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

    if block:
        _dispatch()
    else:
        threading.Thread(target=_dispatch, daemon=False).start()


def load_config():
    default_cfg = {
        "auto_update": True,
        "quiz_mode": "skip",
        "ai_config": {
            "api_key": "",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        },
        "tiku_config": {
            "api_url": "",
            "token": ""
        },
        "notification": {
            "enabled": True,
            "popup": True,
            "persistent": True
        },
        "headless": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return {**default_cfg, **json.load(f)}
        except Exception:
            pass
    return default_cfg

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def check_and_auto_update(cfg):
    """
    无 Git 依赖的国内自适应热更新引擎
    - 支持 ZIP 下载用户无感知开箱即用自动同步 Bug 修复
    - 基于 jsDelivr / GHProxy 国内高速镜像容灾竞速
    - 严格执行 Python 语法自检与原子替换，防半截文件损坏
    - 更新完成后原地 execv 进程热重载，开箱即用永不掉队
    """
    if not cfg.get("auto_update", True):
        return
    if "--no-update" in sys.argv:
        return

    for base_url in UPDATE_MIRRORS:
        ver_url = f"{base_url}version.json"
        try:
            req = urllib.request.Request(ver_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                remote_info = json.loads(resp.read().decode("utf-8"))
                remote_ver = str(remote_info.get("version", "")).strip()
                changelog = remote_info.get("changelog", "常规稳定性与功能修复")
                def _vtuple(v):
                    return tuple(int(x) for x in re.findall(r'\d+', str(v)))

                if not remote_ver or _vtuple(remote_ver) <= _vtuple(APP_VERSION):
                    return

                log(f"🔄 检测到新版本 v{remote_ver} (当前 v{APP_VERSION}): {changelog}")
                log("🚀 正在通过高速镜像节点自动同步最新修复代码...")

                main_url = f"{base_url}main.py"
                main_req = urllib.request.Request(main_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(main_req, timeout=6) as main_resp:
                    new_code = main_resp.read().decode("utf-8")

                # 关键安全防线：语法自检，防止网络中断下载到 404 或残缺文件破坏主程序
                compile(new_code, "main_update.py", "exec")

                main_path = os.path.join(BASE_DIR, "main.py")
                bak_path = os.path.join(BASE_DIR, "main.py.bak")
                tmp_path = os.path.join(BASE_DIR, "main.py.tmp")

                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(new_code)

                try:
                    shutil.copy2(main_path, bak_path)
                except Exception:
                    pass
                os.replace(tmp_path, main_path)

                try:
                    with open(VERSION_FILE, "w", encoding="utf-8") as f:
                        json.dump(remote_info, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

                log(f"🎉 成功同步更新至 v{remote_ver}！正在原地热重载启动新版...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
                return
        except Exception:
            continue

def load_course_cache():
    """加载上次未完成的课程状态与断点"""
    if os.path.exists(COURSE_CACHE_FILE):
        try:
            with open(COURSE_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_course_cache(cache_data):
    """持久化保存当前课程进度"""
    try:
        with open(COURSE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def launch_browser(p, headless=True):
    """跨平台智能探测并唤起本地已有的 Chrome 或 Edge"""
    for ch in ["chrome", "msedge"]:
        try:
            return p.chromium.launch(
                channel=ch,
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--mute-audio',
                    '--no-sandbox',
                    '--disable-gpu',
                ]
            )
        except Exception:
            continue

    for exec_path in ["/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/usr/bin/chromium"]:
        if os.path.exists(exec_path):
            try:
                return p.chromium.launch(
                    executable_path=exec_path,
                    headless=headless,
                    args=['--disable-blink-features=AutomationControlled', '--mute-audio', '--no-sandbox']
                )
            except Exception:
                pass

    return p.chromium.launch(headless=headless, args=['--disable-blink-features=AutomationControlled', '--mute-audio'])

def ensure_login(p):
    """检查登录态，无登录态则弹出二维码扫码"""
    if os.path.exists(AUTH_FILE):
        try:
            with open(AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and data.get("cookies"):
                return AUTH_FILE
        except Exception:
            pass

    log("\n" + "=" * 50)
    log("【首次登录指引】检测到尚未登录，正在启动扫码登录窗口...")
    log("请打开手机【学习通】App -> 右上角扫一扫，扫描弹出的二维码登录。")
    log("=" * 50 + "\n")

    browser = launch_browser(p, headless=False)
    context = browser.new_context()
    page = context.new_page()

    login_url = "https://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.mooc.chaoxing.com"
    page.goto(login_url)

    try:
        page.wait_for_url(lambda u: "passport2.chaoxing.com/login" not in u and "chaoxing.com" in u, timeout=180000)
    except Exception:
        log("❌ 登录等待超时（超过 3 分钟），请重新运行并及时扫码。")
        browser.close()
        sys.exit(1)

    log("🎉 登录成功！正在保存登录凭证至 auth.json...")
    context.storage_state(path=AUTH_FILE)
    browser.close()
    log("凭证已持久化，后续运行将自动免密并在后台静默挂机。\n")
    return AUTH_FILE

def parse_course_url(input_url):
    """解析输入的各种超星课程链接"""
    u = input_url.strip()
    parsed = urllib.parse.urlparse(u)
    qs = urllib.parse.parse_qs(parsed.query)

    course_id = qs.get("courseid", qs.get("courseId", [None]))[0]
    clazz_id = qs.get("clazzid", qs.get("classId", [None]))[0]
    cpi = qs.get("cpi", [None])[0]
    enc = qs.get("enc", qs.get("stuenc", [None]))[0]
    chapter_id = qs.get("chapterId", qs.get("chapterid", [None]))[0]

    is_study_page = "/studentstudy" in parsed.path
    is_mooc2_portal = "/mycourse/stu" in parsed.path or "mooc2-ans" in parsed.netloc

    return {
        "raw_url": u,
        "is_study_page": is_study_page,
        "is_mooc2_portal": is_mooc2_portal,
        "course_id": course_id,
        "clazz_id": clazz_id,
        "cpi": cpi,
        "enc": enc,
        "chapter_id": chapter_id
    }

def to_safe_float(val, default=0.0):
    """安全转换浮点数，过滤 None、NaN 以及 Inf"""
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default

def play_video_frame(page, vf, video_idx, total_videos, cfg=None):
    """控制单集视频播放，监听心跳，达到 100% 结束，具备掉线强校验与看门狗"""
    is_passed = [False]
    notified_pass = [False]

    def on_response(response):
        if 'multimedia/log' in response.url:
            try:
                res = response.json()
                if res.get('isPassed') is True:
                    is_passed[0] = True
            except Exception:
                pass

    page.on('response', on_response)

    try:
        dur = vf.evaluate("""() => {
            const p = window.videojs ? videojs.getPlayers()['video'] : null;
            if (!p) return 0;
            p.muted(true);
            try { p.play(); } catch(e){}
            const playBtn = document.querySelector('.vjs-big-play-button');
            if (playBtn && p.paused()) { try { playBtn.click(); } catch(e){} }
            // 注入反暂停自动唤醒 Hook
            if (!p.__hooked_auto_play) {
                p.__hooked_auto_play = true;
                const origPause = p.pause ? p.pause.bind(p) : null;
                p.pause = function() {
                    // 当页面存在可见的随堂测验时，允许正常暂停答题，严禁高频抢锁造成死锁震荡
                    const quiz = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                    if (quiz && quiz.style.display !== 'none') {
                        return origPause ? origPause() : undefined;
                    }
                    if (p.currentTime() >= p.duration() - 2.5 || p.ended()) {
                        return origPause ? origPause() : undefined;
                    }
                    setTimeout(() => {
                        const q = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                        if (!q || q.style.display === 'none') {
                            try { p.play(); } catch(e){}
                        }
                    }, 300);
                };
                p.on('pause', function() {
                    const quiz = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                    if (quiz && quiz.style.display !== 'none') {
                        return; // 有测验弹窗时允许正常暂停
                    }
                    if (!p.ended()) {
                        setTimeout(() => {
                            const q = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                            if (!q || q.style.display === 'none') {
                                try { p.play(); } catch(e){}
                            }
                        }, 300);
                    }
                });
            }
            const d = p.duration();
            return (typeof d === 'number' && !isNaN(d) && isFinite(d)) ? d : 0;
        }""")
    except Exception as e:
        log(f"   ⚠️ 启动播放异常: {e}")
        page.remove_listener('response', on_response)
        return False

    time.sleep(2)
    new_dur = vf.evaluate("""() => {
        const p = window.videojs ? videojs.getPlayers()['video'] : null;
        if (!p) return 0;
        const d = p.duration();
        return (typeof d === 'number' && !isNaN(d) && isFinite(d)) ? d : 0;
    }""")
    dur = to_safe_float(new_dur if (new_dur and new_dur > 0) else dur, 0.0)

    if dur > 0:
        log(f"   --> [视频 {video_idx}/{total_videos}] 开始播放，视频时长: {dur:.1f} 秒 ({dur/60:.2f} 分钟)")
    else:
        log(f"   --> [视频 {video_idx}/{total_videos}] 开始播放，正在缓冲加载视频...")

    last_log_time = time.time()
    max_cur = 0.0
    stall_count = 0
    error_count = 0
    current_quiz_key = None
    quiz_attempt = 0

    while True:
        time.sleep(5)

        # 检查是否被顶号
        current_page_url = page.url
        if any(k in current_page_url for k in ["space/index", "monitor_temp", "passport2.chaoxing.com"]):
            log("\n❌【严重警告】检测到超星账号在其他设备登录已被迫下线！")
            log("请先关闭其他设备上的网页，并在本机重新扫码登录。")
            notify_user("超星学习助手 - 账号被顶号下线", "检测到超星账号在其他设备登录已被迫下线！请先关闭其他设备并在本机重新扫码登录。", is_popup=True)
            page.remove_listener('response', on_response)
            sys.exit(1)

        try:
            status = vf.evaluate("""() => {
                const p = window.videojs ? videojs.getPlayers()['video'] : null;
                if (!p) return null;

                // 1. 全面扫描并处理随堂测验与任何阻断弹窗
                const quiz = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                let quizInfo = null;
                if (quiz && quiz.style.display !== 'none') {
                    // 若有“继续观看”已激活直接点击
                    const contBtn = quiz.querySelector('.ans-videoquiz-continue, [class*="continue"]');
                    if (contBtn && contBtn.offsetParent !== null) {
                        try { contBtn.click(); } catch(e){}
                    }

                    const titleEl = quiz.querySelector('.ans-videoquiz-title');
                    const rawTitle = titleEl ? titleEl.innerText.trim() : '';

                    const radios = Array.from(quiz.querySelectorAll('input[type="radio"]'));
                    const checkboxes = Array.from(quiz.querySelectorAll('input[type="checkbox"]'));

                    let opts = [];
                    const lis = Array.from(quiz.querySelectorAll('.ans-videoquiz-opt li, ul li'));
                    if (lis.length > 0) {
                        opts = lis.map((el, i) => ({ index: i, text: el.innerText.trim() }));
                    } else {
                        const labels = Array.from(quiz.querySelectorAll('.ans-videoquiz-opt label, label'));
                        if (labels.length > 0) {
                            opts = labels.map((el, i) => ({ index: i, text: el.innerText.trim() }));
                        }
                    }

                    quizInfo = {
                        title: rawTitle,
                        options: opts,
                        radios_count: radios.length,
                        checkboxes_count: checkboxes.length
                    };
                }

                // 2. 扫描关闭“继续观看”、“确定”、“我知道了”等课中暂停阻断按钮
                document.querySelectorAll('button, a, span, .ans-videoquiz-continue').forEach(el => {
                    const txt = (el.innerText || '').trim();
                    if (['继续观看', '继续播放', '提交', '确定', '我知道了'].includes(txt) || el.classList.contains('ans-videoquiz-continue')) {
                        try { el.click(); } catch(e){}
                    }
                });

                let cur = p.currentTime();
                let dur = p.duration();
                if (typeof cur !== 'number' || isNaN(cur) || !isFinite(cur)) cur = 0;
                if (typeof dur !== 'number' || isNaN(dur) || !isFinite(dur)) dur = 0;
                const ended = Boolean(p.ended());

                if (!ended && !quizInfo && (dur <= 0 || cur < dur - 2.5)) {
                    if (p.paused()) {
                        try { p.play(); } catch(e){}
                        const playBtn = document.querySelector('.vjs-big-play-button');
                        if (playBtn) { try { playBtn.click(); } catch(e){} }
                    }
                }
                const isFinished = typeof window.isUnFinishJob === 'function' ? !window.isUnFinishJob() : false;
                return {
                    current: cur,
                    duration: dur,
                    paused: p.paused(),
                    ended: ended,
                    is_finished: isFinished,
                    quiz_info: quizInfo
                };
            }""")
        except Exception as e:
            error_count += 1
            if error_count >= 5:
                log(f"   ❌ 视频播放帧失联: {e}，跳过此视频。")
                page.remove_listener('response', on_response)
                return False
            continue

        if not status:
            error_count += 1
            if error_count >= 5:
                log("   ❌ 未能获取播放状态，跳过此视频。")
                page.remove_listener('response', on_response)
                return False
            continue

        error_count = 0
        cur = to_safe_float(status.get('current'), 0.0)
        report_dur = to_safe_float(status.get('duration'), 0.0)
        if report_dur > 0:
            dur = report_dur
        if status.get('is_finished'):
            is_passed[0] = True

        # 穿透处理顶级页面可能的阻断弹窗
        try:
            page.evaluate("""() => {
                document.querySelectorAll('button, a, span, .ans-videoquiz-continue').forEach(el => {
                    const txt = (el.innerText || '').trim();
                    if (['继续观看', '继续播放', '确定', '我知道了'].includes(txt)) {
                        try { el.click(); } catch(e){}
                    }
                });
            }""")
        except Exception:
            pass

        quiz_info = status.get('quiz_info')
        if quiz_info:
            stall_count = 0  # 随堂测验不计入视频卡顿
            raw_title = quiz_info.get('title', '').strip()
            options = quiz_info.get('options', [])

            quiz_key = f"{int(cur)}_{raw_title[:20]}"
            if current_quiz_key != quiz_key:
                current_quiz_key = quiz_key
                quiz_attempt = 0
            quiz_attempt += 1

            matched_idx = -1
            clean_t = clean_question_text(raw_title)

            # 首轮尝试题库与 AI 精准匹配
            if quiz_attempt == 1 and clean_t and options:
                disp_title = clean_t if len(clean_t) <= 32 else clean_t[:32] + "..."
                log(f"   📝 [随堂测验] 视频在 {int(cur)//60}分{int(cur)%60:02d}秒 触发测验: 《{disp_title}》")
                log(f"      🔍 正在调用题库/AI 检索标准答案...")

                tiku_cfg = (cfg or {}).get("tiku_config", {})
                ai_cfg = (cfg or {}).get("ai_config", {})

                # 1. 优先题库查询
                try:
                    ans = query_tiku_api(clean_t, tiku_cfg=tiku_cfg)
                except Exception:
                    ans = None

                if ans:
                    log(f"      🎯 题库命中标准答案: {ans}")
                    matched_idx = match_option_index(ans, options)

                # 2. 题库未命中且配置了 AI，请求 AI 辅助
                if matched_idx < 0 and ai_cfg.get("api_key"):
                    opt_strings = [o.get("text", "") for o in options]
                    ai_ans = query_ai_for_question(clean_t, opt_strings, ai_cfg)
                    if ai_ans:
                        log(f"      🤖 AI 辅助解答给出: {ai_ans}")
                        matched_idx = match_option_index(ai_ans, options)

            # 确定作答动作（精准匹配 vs 轮换兜底）
            action_desc = ""
            if matched_idx >= 0:
                action_desc = f"题库/AI 精准选中选项 [{matched_idx + 1}/{len(options)}]"
            else:
                if quiz_attempt == 1:
                    log("      ⚠️ 题库/AI 未收录此题，自动无缝启动选项轮换兜底...")
                action_desc = f"轮换兜底尝试 #{quiz_attempt}"

            log(f"      👉 正在提交作答 ({action_desc})...")

            try:
                vf.evaluate("""({ targetIdx, attempt }) => {
                    const quiz = document.querySelector('.ans-videoquiz, .ans-cc, .x-window');
                    if (!quiz) return;

                    const radios = Array.from(quiz.querySelectorAll('input[type="radio"]'));
                    const checkboxes = Array.from(quiz.querySelectorAll('input[type="checkbox"]'));
                    const opts = Array.from(quiz.querySelectorAll('.ans-videoquiz-opt li, .ans-videoquiz-opt label, .ans-videoquiz-opt, li'));

                    let selectIdx = targetIdx;
                    if (selectIdx < 0) {
                        const count = radios.length || opts.length || 1;
                        selectIdx = (attempt - 1) % count;
                    }

                    if (radios.length > 0) {
                        radios.forEach((r, idx) => {
                            if (idx === selectIdx) {
                                r.checked = true;
                                 try { r.click(); } catch(e){}
                            } else {
                                r.checked = false;
                            }
                        });
                    } else if (checkboxes.length > 0) {
                        checkboxes.forEach((c, idx) => {
                            if (targetIdx >= 0) {
                                if (idx === targetIdx && !c.checked) { try { c.click(); } catch(e){} }
                            } else {
                                if (!c.checked) { try { c.click(); } catch(e){} }
                            }
                        });
                    } else if (opts.length > 0 && selectIdx < opts.length) {
                        try { opts[selectIdx].click(); } catch(e){}
                    }

                    // 提交
                    setTimeout(() => {
                        const submitBtns = quiz.querySelectorAll('.ans-videoquiz-submit, #videoquiz-submit, .btnSubmit, button, .ans-videoquiz-btn, [class*="submit"]');
                        submitBtns.forEach(b => { try { b.click(); } catch(e){} });
                    }, 250);

                    // 延迟尝试穿透继续观看
                    setTimeout(() => {
                        const cb = quiz.querySelector('.ans-videoquiz-continue, [class*="continue"]');
                        if (cb) { try { cb.click(); } catch(e){} }
                        document.querySelectorAll('button, a, span, .ans-videoquiz-continue').forEach(el => {
                            const txt = (el.innerText || '').trim();
                            if (['继续观看', '继续播放', '提交', '确定', '我知道了'].includes(txt)) {
                                try { el.click(); } catch(e){}
                            }
                        });
                    }, 650);

                    // 极端兜底：连续超 8 次尝试（40秒）尝试清除遮罩
                    if (attempt >= 8) {
                        setTimeout(() => {
                            try {
                                document.querySelectorAll('.x-component-default, .x-mask, .ext-el-mask').forEach(el => el.remove());
                            } catch(e){}
                        }, 800);
                    }
                }""", {"targetIdx": matched_idx, "attempt": quiz_attempt})
            except Exception as e:
                log(f"      ⚠️ 作答提交异常: {e}")

            time.sleep(2)
            continue
        else:
            current_quiz_key = None
            quiz_attempt = 0

        # 核心修复：基于真实前进进度统计卡顿，彻底杜绝回退导致清零卡顿计数器的死循环
        if cur > max_cur + 0.4:
            max_cur = cur
            stall_count = 0
        elif not status.get('paused') and (dur <= 0 or cur < dur - 5.0):
            # 若服务器已记录该任务点达标，无需漫长等待看门狗，立即安全结课
            if is_passed[0]:
                log("   🎉 [任务点已达标] 检测到服务器已记录该任务点达标 (isPassed=true)，遇缓冲阻滞安全放行！")
                time.sleep(2)
                page.remove_listener('response', on_response)
                return True

            stall_count += 1
            if stall_count % 8 == 0:
                watchdog_round = stall_count // 8
                # Level 1: 40s - 唤醒播放器、清理弹窗、重触发播放
                if watchdog_round == 1:
                    log("   ⚠️ [看门狗 L1] 缓冲卡顿超 40 秒，重新激活播放器并穿透阻断...")
                    try:
                        vf.evaluate("""() => {
                            const p = window.videojs ? videojs.getPlayers()['video'] : null;
                            if (p) {
                                p.muted(true);
                                p.play().catch(() => {});
                            }
                            const v = document.querySelector('video');
                            if (v && v.paused) { try { v.play(); } catch(e){} }
                            document.querySelectorAll('button, a, span, .ans-videoquiz-continue').forEach(el => {
                                const txt = (el.innerText || '').trim();
                                if (['继续观看', '继续播放', '确定', '我知道了'].includes(txt) || el.classList.contains('ans-videoquiz-continue')) {
                                    try { el.click(); } catch(e){}
                                }
                            });
                        }""")
                    except Exception:
                        pass

                # Level 2: 80s - 智能跃过死锁帧 (+1.5s) 与可靠的媒体流恢复
                elif watchdog_round == 2:
                    log("   ⚠️ [看门狗 L2] 缓冲卡顿超 80 秒，触发媒体流热恢复与死锁点跨越...")
                    notify_user("超星学习助手 - 播放卡顿预警", f"视频 [视频 {video_idx}/{total_videos}] 在 {int(cur)//60}分{int(cur)%60:02d}秒 卡顿超 80 秒，正在自动热恢复...", is_popup=False)
                    try:
                        vf.evaluate(f"""() => {{
                            const p = window.videojs ? videojs.getPlayers()['video'] : null;
                            if (p) {{
                                const dur = p.duration() || 0;
                                const target = (dur > 0 && {max_cur} + 1.5 < dur) ? {max_cur} + 1.5 : {max_cur};
                                // 1. 先尝试直接跨越死锁点并播放
                                try {{
                                    p.currentTime(target);
                                    p.muted(true);
                                    p.play().catch(() => {{}});
                                }} catch(e){{}}

                                // 2. 注册 loadedmetadata 确保即使 reload 也能精准定位
                                p.one('loadedmetadata', () => {{
                                    try {{ p.currentTime(target); }} catch(e){{}}
                                    p.muted(true);
                                    setTimeout(() => {{ try {{ p.play(); }} catch(e){{}} }}, 600);
                                }});

                                // 3. 若依然暂停或卡死，执行 load() 重建媒体管道
                                setTimeout(() => {{
                                    if (p.paused() || p.currentTime() <= {max_cur}) {{
                                        try {{ p.load(); }} catch(e){{}}
                                    }}
                                }}, 1200);
                            }}
                        }}""")
                    except Exception:
                        pass

                # Level 3: 120s+ (2~3 分钟) - 达标安全放行或超时跳过
                elif watchdog_round >= 3:
                    if is_passed[0]:
                        log("   🎉 [任务点已就绪] 虽遇网络卡顿，但服务器已记录该任务点达标(isPassed=true)，安全打卡结课！")
                        time.sleep(2)
                        page.remove_listener('response', on_response)
                        return True
                    else:
                        if watchdog_round == 3:
                            log(f"   ⚠️ [看门狗 L3] 缓冲卡顿持续超 2 分钟，弹出系统级预警并尝试强制唤醒...")
                            notify_user("超星学习助手 - 视频持续卡顿", f"视频 [视频 {video_idx}/{total_videos}] 持续卡顿超 2 分钟，请检查网络或代理！", is_popup=True)
                            try:
                                vf.evaluate("""() => {
                                    const v = document.querySelector('video');
                                    if (v) {
                                        v.muted = true;
                                        v.play().catch(() => {});
                                    }
                                }""")
                            except Exception:
                                pass
                        if watchdog_round >= 5:
                            log("   ⚠️ [看门狗超时] 视频断流超 3 分钟，安全放行此视频进入后续流程，避免无限卡死！")
                            page.remove_listener('response', on_response)
                            return False
        if is_passed[0] and not notified_pass[0]:
            log(f"   [状态更新] 任务点已达标(isPassed=true)，继续播完至 100% 结束以确保数据审计完整...")
            notified_pass[0] = True

        if time.time() - last_log_time >= 25:
            cur_sec = int(cur)
            if dur > 0:
                pct = min(100.0, max(0.0, (cur / dur * 100)))
                rem_sec = max(0, int(dur - cur))
                rem_str = f"{rem_sec // 60}分{rem_sec % 60:02d}秒"
                bar_len = 18
                filled = int(bar_len * (pct / 100))
                bar = "█" * filled + "░" * (bar_len - filled)
                pass_str = " [已通关]" if is_passed[0] else ""
                dur_sec = int(dur)
                log(f"   [{bar}] {pct:5.1f}% | 剩余: {rem_str} | 已播: {cur_sec//60}分{cur_sec%60:02d}秒 / {dur_sec//60}分{dur_sec%60:02d}秒{pass_str}")
            else:
                log(f"   [缓冲中] 视频正在加载缓冲 (已播: {cur_sec//60}分{cur_sec%60:02d}秒)...")
            last_log_time = time.time()

        if status.get('ended') or (dur > 0 and cur >= dur - 2.5):
            log(f"   [100% 完播] 视频已完整播放至最后一秒，时长审计 100%！")
            time.sleep(3)
            page.remove_listener('response', on_response)
            return True

def hash_glyph(glyph):
    if glyph.numberOfContours <= 0: return ''
    pos_data = []
    last_index = 0
    for i in range(glyph.numberOfContours):
        end_point = glyph.endPtsOfContours[i]
        for j in range(last_index, end_point + 1):
            x, y = glyph.coordinates[j]
            flag = glyph.flags[j] & 0x01
            pos_data.append(f'{x}{y}{flag}')
        last_index = end_point + 1
    return hashlib.md5(''.join(pos_data).encode()).hexdigest()

def clean_question_text(q):
    if not q:
        return ""
    # 移除前导题号，如 "1." 或 "12、"
    q = re.sub(r'^[0-9]+[、. ]*', '', q)
    # 移除常见题型标签前缀，如 【单选题】、[多选题]、(判断题)
    q = re.sub(r'^[【\[(（]?(?:单选题|多选题|判断题|填空题|简答题|名词解释|论述题|计算题|问答题)[】\])）]?', '', q)
    # 移除分值后缀，如 "（5.0分）" 或 "(5分)"
    q = re.sub(r'[\(（]\s*\d+(?:\.\d+)?\s*分\s*[\)）]', '', q)
    # 规范化空填空括号，保留带有实体区分内容的括号
    q = re.sub(r'[（\(]\s*[）\)]', '（ ）', q)
    # 移除末尾标点和空白
    q = re.sub(r'[。？！\s]+$', '', q)
    return q.strip()

TYPE_SINGLE = "0"
TYPE_MULTI = "1"
TYPE_FILL = "2"
TYPE_JUDGE = "3"
TYPE_ESSAY = "4"

TYPE_NAMES = {
    TYPE_SINGLE: "单选题",
    TYPE_MULTI: "多选题",
    TYPE_FILL: "填空题",
    TYPE_JUDGE: "判断题",
    TYPE_ESSAY: "主观题"
}

def identify_question_type(timu_loc, raw_text=""):
    """多维度自适应识别超星各类题型 (单选/多选/判断/填空/简答)"""
    t = raw_text or ""
    # 1. 显式标签识别
    if re.search(r'[【\[(（]?(?:多选题|多选)[】\])）]?', t):
        return TYPE_MULTI
    if re.search(r'[【\[(（]?(?:判断题|判断)[】\])）]?', t):
        return TYPE_JUDGE
    if re.search(r'[【\[(（]?(?:填空题|填空)[】\])）]?', t):
        return TYPE_FILL
    if re.search(r'[【\[(（]?(?:简答题|名词解释|论述题|计算题|问答题)[】\])）]?', t):
        return TYPE_ESSAY
    if re.search(r'[【\[(（]?(?:单选题|单选)[】\])）]?', t):
        return TYPE_SINGLE

    # 2. 检查 DOM 隐藏 input[name*="type"] / [answertype]
    try:
        type_input = timu_loc.locator('input[name*="type"], input[name*="answertype"]').first
        if type_input.count() > 0:
            val = str(type_input.get_attribute("value") or "").strip()
            if val == "0": return TYPE_SINGLE
            if val == "1": return TYPE_MULTI
            if val == "3": return TYPE_JUDGE
            if val == "2": return TYPE_FILL
            if val in ["4", "5", "6", "7", "9"]: return TYPE_ESSAY
    except Exception:
        pass

    # 3. 检查 DOM 控件特征
    try:
        if timu_loc.locator('input[type="checkbox"], .check_answer_dx, .num_option_dx').count() > 0:
            return TYPE_MULTI

        if timu_loc.locator('.num_option[data="true"], .num_option[data="false"], input[value="true"], input[value="false"]').count() > 0:
            return TYPE_JUDGE

        opts = timu_loc.locator('ul li, .answerBg, .answer_p').all()
        if len(opts) == 2:
            all_opt_text = " ".join([o.inner_text() for o in opts])
            if any(k in all_opt_text for k in ["对", "错", "正确", "错误", "√", "×", "True", "False"]):
                return TYPE_JUDGE

        if timu_loc.locator('input[type="radio"], .check_answer, .num_option').count() > 0:
            return TYPE_SINGLE

        textareas = timu_loc.locator('textarea, input[type="text"]').all()
        if textareas:
            if len(textareas) > 1 or '（ ）' in t or '空' in t:
                return TYPE_FILL
            return TYPE_ESSAY
    except Exception:
        pass

    return TYPE_SINGLE

def extract_timu_data(timu_loc, decode_fn):
    """从单个题目 DOM 容器中提取标准题干、选项及控件信息"""
    title_selectors = [
        '.Zy_TItle .clearfix',
        '.clearfix .fontLabel',
        '.mark_name',
        '.TiMu_title',
        '.colorDeep',
        '.Zy_TItle',
        '[class*="TItle"]'
    ]
    raw_title = ""
    for sel in title_selectors:
        loc = timu_loc.locator(sel).first
        if loc.count() > 0:
            raw_title = loc.inner_text().strip()
            if raw_title:
                break
    if not raw_title:
        raw_title = timu_loc.inner_text().split('\n')[0].strip()

    decoded_title = decode_fn(raw_title)
    cleaned_title = clean_question_text(decoded_title)
    q_type = identify_question_type(timu_loc, raw_title)

    opt_selectors = [
        'ul li',
        '.textDIV',
        '.answer_p',
        '.ans-videoquiz-opt li',
        '.answerBg .textDIV',
        '.answerBg'
    ]
    opt_elements = []
    for o_sel in opt_selectors:
        found = timu_loc.locator(o_sel).all()
        if found:
            opt_elements = found
            break

    options = []
    for idx, opt_el in enumerate(opt_elements):
        raw_opt = opt_el.inner_text().strip()
        decoded_opt = decode_fn(raw_opt)

        num_span = opt_el.locator('.num_option, .num_option_dx, .num_option_pd').first
        if num_span.count() > 0:
            opt_key = num_span.inner_text().strip().rstrip('、. ')
        else:
            m = re.match(r'^([A-Za-z0-9√×对错]+)[、. ]*', decoded_opt)
            opt_key = m.group(1) if m else chr(ord('A') + idx)

        opt_text = re.sub(r'^[A-Za-z0-9√×对错]+[、. ]*', '', decoded_opt).strip()
        options.append({
            "index": idx,
            "key": opt_key.upper(),
            "text": opt_text or decoded_opt,
            "raw": decoded_opt,
            "locator": opt_el
        })

    return {
        "raw_title": raw_title,
        "title": cleaned_title or decoded_title,
        "type": q_type,
        "type_name": TYPE_NAMES.get(q_type, "单选题"),
        "options": options
    }

def query_tiku_api(question, tiku_cfg=None):
    """优先请求用户配置的私有/自定义题库，若未配置或未命中则回退至公开免费接口"""
    cq = clean_question_text(question)
    if not cq:
        return None

    # 1. 优先尝试用户自定义题库 (config.json 中的 tiku_config)
    if tiku_cfg and tiku_cfg.get("api_url"):
        api_url = tiku_cfg["api_url"].strip()
        token = tiku_cfg.get("token", "").strip()
        try:
            req_data = json.dumps({"question": cq, "token": token}).encode("utf-8")
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            req = urllib.request.Request(api_url, data=req_data, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                ans = res.get("data") if res.get("data") is not None else (res.get("answer") or res.get("result"))
                if ans:
                    ans_str = str(ans).strip()
                    if ans_str and not any(k in ans_str for k in ["未搜索到", "未收录", "李恒雅正在睡觉", "查无此题"]):
                        return ans_str
        except Exception:
            pass

    # 2. 回退到公开免费题库
    return query_public_tiku(cq)

def query_public_tiku(question):
    """请求去商业化的公开免费题库接口"""
    cq = clean_question_text(question)
    if not cq:
        return None
    url = "http://cx.icodef.com/wyn-nb?v=4"
    data = json.dumps({"question": cq}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "X-Forwarded-For": "114.114.114.114"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("code") == 1:
                ans = str(res.get("data", "")).strip()
                # 过滤第三方广告与无答案提示
                if not any(k in ans for k in ["叛逆", "公众号", "李恒雅", "一之", "付费", "扫码", "未搜索到", "睡觉觉"]):
                    return ans
    except Exception:
        pass
    return None

def query_ai_for_question(title, opt_texts, ai_cfg=None, q_type=TYPE_SINGLE):
    """按题型定制针对性 Prompt 的通用 AI 答题请求封装"""
    if not ai_cfg or not ai_cfg.get("api_key"):
        return None
    api_key = str(ai_cfg["api_key"]).strip()
    if not api_key:
        return None
    base_url = ai_cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
    model = ai_cfg.get("model", "deepseek-chat")

    formatted_opts = "\n".join(opt_texts) if isinstance(opt_texts, list) else str(opt_texts)
    if q_type == TYPE_SINGLE:
        prompt = f"请为以下大学网课单选题选择唯一正确答案，严格只输出选项字母或对应内容（例如 A）：\n题目：{title}\n选项：\n{formatted_opts}"
    elif q_type == TYPE_MULTI:
        prompt = f"请为以下大学网课多选题选择所有正确答案，严格只输出选项字母组合或内容（例如 A,B,C）：\n题目：{title}\n选项：\n{formatted_opts}"
    elif q_type == TYPE_JUDGE:
        prompt = f"请为以下大学网课判断题判断对错，严格只输出“正确”或“错误”：\n题目：{title}"
    elif q_type == TYPE_FILL:
        prompt = f"请为以下大学网课填空题作答，若有多个空请用 # 分隔，严格只输出答案内容：\n题目：{title}"
    else:
        prompt = f"请为以下大学网课题目提供精炼准确的解答草稿：\n题目：{title}"

    try:
        req_data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/chat/completions", data=req_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"      ⚠️ AI 请求失败: {e}")
        return None

def fill_answer_to_dom(work_frame, timu_loc, q_type, answer_str, options):
    """根据题型和题库/AI 答案，智能填涂超星 DOM 控件"""
    if not answer_str:
        return False
    ans_str = str(answer_str).strip()

    # 1. 单选题填涂
    if q_type == TYPE_SINGLE:
        target_idx = match_option_index(ans_str, options)
        if target_idx >= 0 and target_idx < len(options):
            target = options[target_idx]
            try:
                # 优先操作原生单选框控件
                radio = target["locator"].locator('input[type="radio"]').first
                if radio.count() > 0:
                    try: radio.check(); return True
                    except Exception: radio.click(); return True

                clickable = target["locator"].locator('.answerBg, .num_option, a, label').first
                if clickable.count() > 0:
                    clickable.click()
                else:
                    target["locator"].click()
                return True
            except Exception:
                try: target["locator"].click(); return True
                except Exception: pass
        return False

    # 2. 判断题填涂
    elif q_type == TYPE_JUDGE:
        is_true = bool(re.search(r'(正确|对|true|是|√|T|ri)', ans_str, re.I))
        is_false = bool(re.search(r'(错误|错|false|否|×|F|wr)', ans_str, re.I))
        if is_true:
            try:
                btn = timu_loc.locator('.num_option[data="true"], input[value="true"]').first
                if btn.count() > 0: btn.click(); return True
            except Exception: pass
            for o in options:
                if any(k in o["raw"] for k in ["正确", "对", "√", "True", "true"]):
                    try: o["locator"].click(); return True
                    except Exception: pass
            if options:
                try: options[0]["locator"].click(); return True
                except Exception: pass
        elif is_false:
            try:
                btn = timu_loc.locator('.num_option[data="false"], input[value="false"]').first
                if btn.count() > 0: btn.click(); return True
            except Exception: pass
            for o in options:
                if any(k in o["raw"] for k in ["错误", "错", "×", "False", "false"]):
                    try: o["locator"].click(); return True
                    except Exception: pass
            if len(options) > 1:
                try: options[1]["locator"].click(); return True
                except Exception: pass
        return False

    # 3. 多选题填涂
    elif q_type == TYPE_MULTI:
        matched_indices = set()
        letters = re.findall(r'[A-Za-z]', ans_str.upper())
        if letters and all(ord(l) - ord('A') < len(options) for l in letters):
            for l in letters:
                matched_indices.add(ord(l) - ord('A'))
        else:
            ans_items = [a.strip() for a in re.split(r'[#;,/\n]', ans_str) if a.strip()]
            for item in ans_items:
                idx = match_option_index(item, options)
                if idx >= 0:
                    matched_indices.add(idx)

        if not matched_indices and options:
            return False

        filled_any = False
        for idx in matched_indices:
            if idx < len(options):
                opt = options[idx]
                try:
                    cb = opt["locator"].locator('input[type="checkbox"]').first
                    if cb.count() > 0:
                        try:
                            if not cb.is_checked(): cb.check()
                            filled_any = True
                        except Exception:
                            cb.click()
                            filled_any = True
                    else:
                        opt["locator"].click()
                        filled_any = True
                except Exception:
                    try: opt["locator"].click(); filled_any = True
                    except Exception: pass
        return filled_any

    # 4. 填空题填涂
    elif q_type == TYPE_FILL:
        parts = [p.strip() for p in re.split(r'[#\n|]|第\d+空[:：]', ans_str) if p.strip()]
        if not parts:
            parts = [ans_str]

        inputs = timu_loc.locator('textarea, input[type="text"]').all()
        if not inputs:
            return False

        for i, val in enumerate(parts):
            if i < len(inputs):
                inp = inputs[i]
                try:
                    inp.fill(val)
                    name = inp.get_attribute("name")
                    if name:
                        work_frame.evaluate("""({name, content}) => {
                            if (window.UE && window.UE.getEditor) {
                                try { window.UE.getEditor(name).setContent(content); } catch(e){}
                            }
                        }""", {"name": name, "content": val})
                except Exception:
                    pass
        return True

    # 5. 简答题/主观题填涂
    elif q_type == TYPE_ESSAY:
        textarea = timu_loc.locator('textarea').first
        if textarea.count() > 0:
            try:
                textarea.fill(ans_str)
                name = textarea.get_attribute("name")
                if name:
                    work_frame.evaluate("""({name, content}) => {
                        if (window.UE && window.UE.getEditor) {
                            try { window.UE.getEditor(name).setContent(content); } catch(e){}
                        }
                    }""", {"name": name, "content": ans_str})
                return True
            except Exception:
                pass
        return False

    return False
def match_option_index(answer_str, options):
    """根据题库/AI 答案字符串，在选项列表中匹配最佳选项索引 (0-based)"""
    if not answer_str or not options:
        return -1
    ans_clean = clean_question_text(answer_str).strip()

    # 1. 单字母前缀匹配 (例如答案为 "A" 或 "B.")
    m = re.match(r'^([A-Za-z])(?:[、. ]|$)', ans_clean)
    if m:
        letter = m.group(1).upper()
        target_idx = ord(letter) - ord('A')
        if 0 <= target_idx < len(options):
            return target_idx

    # 2. 判断题关键字匹配
    if re.search(r'(正确|对|true|是|√)', ans_clean, re.I):
        for idx, o in enumerate(options):
            txt = o.get('text', '') if isinstance(o, dict) else str(o)
            if any(k in txt for k in ["正确", "对", "√"]):
                return idx
        return 0
    elif re.search(r'(错误|错|false|否|×)', ans_clean, re.I):
        for idx, o in enumerate(options):
            txt = o.get('text', '') if isinstance(o, dict) else str(o)
            if any(k in txt for k in ["错误", "错", "×"]):
                return idx
        if len(options) > 1:
            return 1

    # 3. 文本最佳匹配 (全词 / 子串 / 字符重合度)
    best_idx = -1
    best_score = 0.0
    ans_parts = [a.strip() for a in re.split(r'[#;,/ ]', ans_clean) if a.strip()]
    for ans_item in ans_parts:
        for idx, o in enumerate(options):
            opt_text = (o.get('text', '') if isinstance(o, dict) else str(o)).strip()
            opt_body = re.sub(r'^[A-Za-z][、. ]*', '', opt_text).strip()
            if not opt_body:
                continue
            if ans_item == opt_text or ans_item == opt_body:
                return idx
            if len(ans_item) > 1 and (ans_item in opt_body or opt_body in ans_item):
                return idx
            s1, s2 = set(ans_item), set(opt_body)
            overlap = len(s1 & s2) / max(len(s1), 1)
            if overlap > best_score:
                best_score = overlap
                best_idx = idx

    if best_score >= 0.6:
        return best_idx

    return -1
def solve_quiz(work_frame, mode="tiku", ai_cfg=None, tiku_cfg=None):
    """解密字体、全题型智能识别与作答，并自动安全【暂存草稿】"""
    from fontTools.ttLib.ttFont import TTFont

    # 1. 递归检查嵌套 iframe (兼容 /ananas/modules/work/index.html -> /work/doHomeWorkNew)
    timus = work_frame.locator('.TiMu, .questionLi, .mark_table').all()
    if len(timus) == 0 and hasattr(work_frame, 'child_frames') and work_frame.child_frames:
        for cf in work_frame.child_frames:
            solve_quiz(cf, mode=mode, ai_cfg=ai_cfg, tiku_cfg=tiku_cfg)
        return

    if not timus:
        return

    # 2. 字体解密准备 (离线字模表 + TTFont 动态解析)
    char_map = {}
    if os.path.exists(FONT_MAP_FILE):
        try:
            with open(FONT_MAP_FILE, "r", encoding="utf-8") as f:
                char_map = json.load(f)
        except Exception:
            pass
    hash_map = {h: c for c, h in char_map.items()}

    font_b64 = None
    try:
        font_b64 = work_frame.evaluate("""() => {
            for (let s of document.querySelectorAll('style')) {
                let m = s.textContent.match(/base64,([A-Za-z0-9+/=]+)/);
                if (m) return m[1];
            }
            return null;
        }""")
    except Exception:
        pass

    font_hashmap = {}
    if font_b64:
        try:
            font_file = TTFont(io.BytesIO(base64.b64decode(font_b64)), lazy=False)
            glyf_table = font_file['glyf']
            for name in glyf_table.glyphOrder:
                if name.startswith('uni'):
                    ghash = hash_glyph(glyf_table.glyphs[name])
                    if ghash: font_hashmap[name] = ghash
        except Exception:
            pass

    def decode_text(enc_text):
        if not enc_text:
            return ""
        res = []
        for ch in enc_text:
            cname = f'uni{ord(ch):X}'
            if cname in font_hashmap:
                ghash = font_hashmap[cname]
                orig_code = hash_map.get(ghash)
                if orig_code:
                    try:
                        res.append(chr(int(orig_code[3:], 16)))
                        continue
                    except Exception: pass
            res.append(ch)
        return ''.join(res).translate(KX_RADICALS_TAB)

    log(f"   📝 检测到测验包含 {len(timus)} 道题，正在进行全题型智能识别与解答 (模式: {mode})...")

    matched_count = 0
    for idx, timu in enumerate(timus):
        try:
            data = extract_timu_data(timu, decode_text)
            q_title = data["title"]
            q_type = data["type"]
            q_name = data["type_name"]
            options = data["options"]

            disp_title = q_title if len(q_title) <= 28 else q_title[:28] + "..."
            log(f"      [题 {idx+1}/{len(timus)}] [{q_name}] 题干: 《{disp_title}》")

            answer_str = None
            # 1. 优先公共题库
            if mode == "tiku":
                answer_str = query_tiku_api(q_title, tiku_cfg=tiku_cfg)
                if answer_str:
                    log(f"         🎯 题库命中: {answer_str}")
                else:
                    log(f"         ⚠️ 题库未收录，尝试 AI 辅助或保留空白。")

            # 2. 题库未命中且启用 AI
            if not answer_str and (mode == "ai" or (ai_cfg and ai_cfg.get("api_key"))):
                opt_strings = [f"{o['key']}. {o['text']}" for o in options]
                answer_str = query_ai_for_question(q_title, opt_strings, ai_cfg=ai_cfg, q_type=q_type)
                if answer_str:
                    log(f"         🤖 AI 辅助解答: {answer_str}")

            if not answer_str:
                continue

            filled = fill_answer_to_dom(work_frame, timu, q_type, answer_str, options)
            if filled:
                matched_count += 1
                log(f"         ✍️ 已成功填涂选项/草稿")
        except Exception as e:
            log(f"      ⚠️ [题 {idx+1}] 解析作答异常: {e}")

    # 核心安全操作：只点击“暂存草稿”，绝不自动提交！
    time.sleep(1)
    try:
        work_frame.evaluate("""() => {
            if (typeof window.noSubmit === 'function') {
                try { window.noSubmit(); return; } catch(e){}
            }
            const btns = Array.from(document.querySelectorAll('a, button, span, input[type="button"]'));
            for (const b of btns) {
                const txt = (b.innerText || b.value || '').trim();
                if (['暂存', '保存草稿', '保存'].includes(txt)) {
                    try { b.click(); return; } catch(e){}
                }
            }
        }""")
    except Exception:
        pass
    log(f"   ✅【测验草稿暂存完成】已成功识别并填涂 {matched_count}/{len(timus)} 题并暂存草稿！请在网页端核对后手动提交。")
def extract_chapters_from_page(page):
    """自适应提取页面中所有的章节信息"""
    return page.evaluate("""() => {
        const list = [];
        document.querySelectorAll('[onclick*="getTeacherAjax"]').forEach(el => {
            const m = el.getAttribute('onclick').match(/getTeacherAjax\\('[^']*','[^']*','(\\d+)'/);
            if (m) {
                list.push({
                    id: m[1],
                    title: el.innerText.trim().replace(/\\s+/g, ' ')
                });
            }
        });
        if (list.length === 0) {
            document.querySelectorAll('a[href*="studentstudy"]').forEach(a => {
                const m = a.href.match(/chapterId=(\\d+)/);
                if (m) {
                    list.push({
                        id: m[1],
                        title: a.innerText.trim().replace(/\\s+/g, ' ')
                    });
                }
            });
        }
        return list;
    }""")

def process_current_tab_tasks(page, cfg):
    """处理当前卡片/标签下的所有任务点（包含视频与章节测验）"""
    if page.is_closed():
        return
    cards_frame = None
    for f in page.frames:
        if 'cards' in f.url:
            cards_frame = f
            break

    # 1. 视频处理
    video_frames = [f for f in page.frames if 'video' in f.url]
    if video_frames:
        log(f"   发现 {len(video_frames)} 个视频任务，准备播放...")
        for idx, vf in enumerate(video_frames):
            is_done = False
            if cards_frame:
                try:
                    is_done = cards_frame.evaluate(f"""() => {{
                        const cts = document.querySelectorAll('.ans-attach-ct');
                        if (cts[{idx}]) {{
                            const icon = cts[{idx}].querySelector('.ans-job-icon');
                            return icon && (icon.getAttribute('aria-label') || '').includes('已完成');
                        }}
                        return false;
                    }}""")
                except Exception:
                    pass

            if is_done:
                log(f"   --> [视频 {idx + 1}/{len(video_frames)}] 此前已打卡完成，跳过。")
                continue

            success = play_video_frame(page, vf, idx + 1, len(video_frames), cfg=cfg)
            if success:
                log(f"   [打卡成功] 视频 {idx + 1} 学习完毕！")

    if page.is_closed():
        return
    # 2. 章节测验/作业处理
    quiz_frames = [
        f for f in page.frames
        if any(k in f.url for k in ['doHomeWorkNew', 'dowork', 'selectWorkQuestion', 'work/index.html', 'work/question'])
    ]
    if quiz_frames:
        q_mode = cfg.get("quiz_mode", "skip")
        if q_mode in ["tiku", "ai"]:
            for qf in quiz_frames:
                solve_quiz(qf, mode=q_mode, ai_cfg=cfg.get("ai_config", {}), tiku_cfg=cfg.get("tiku_config", {}))
        else:
            log(f"   📝 [测验安全跳过] 当前标签包含单元测验，已按设定安全跳过（保留手动完成）。")

def safe_goto(page, url, wait_until="domcontentloaded", timeout=45000, max_retries=5):
    """具备抗网络丢包、DNS 瞬时抖动与自动容灾重试的安全页面导航"""
    for try_idx in range(1, max_retries + 1):
        try:
            page.goto(url, wait_until=wait_until, timeout=timeout)
            return True
        except Exception as e:
            err_line = str(e).split('\n')[0]
            if try_idx < max_retries:
                log(f"   ⚠️ 页面导航/域名解析瞬时波动 ({err_line})，3 秒后自动重试 [{try_idx}/{max_retries}]...")
                time.sleep(3)
            else:
                log(f"   ❌ 页面访问连续 {max_retries} 次失败: {err_line}")
                raise

def run_study(url, start_chapter=None, cfg=None):
    if not cfg:
        cfg = load_config()

    info = parse_course_url(url)
    if not info["course_id"]:
        log("❌ 无法从链接中解析出 courseId，请检查输入的链接格式。")
        return

    is_headless = cfg.get("headless", True)
    with sync_playwright() as p:
        auth_path = ensure_login(p)

        browser = launch_browser(p, headless=is_headless)
        context = browser.new_context(storage_state=auth_path)
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        chapters = []
        cpi = info["cpi"] or "408853908"
        enc = info["enc"]

        if info["is_study_page"]:
            log("检测到输入链接为具体小节学习页面，正在直接加载并提取完整目录...")
            safe_goto(page, info["raw_url"], wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            chapters = extract_chapters_from_page(page)

        elif info["is_mooc2_portal"]:
            log("检测到输入链接为 MOOC2 课程门户首页，正在加载章节框架...")
            safe_goto(page, info["raw_url"], wait_until="networkidle")
            page.wait_for_timeout(3000)
            zj_frame = page.frame("frame_content-zj")
            if zj_frame:
                parsed_cfg = zj_frame.evaluate("""() => {
                    let enc = null;
                    let cpi = null;
                    if (window.toOld) {
                        const encM = window.toOld.toString().match(/var enc = "([^"]+)"/);
                        const cpiM = window.toOld.toString().match(/var cpi = (\\d+)/);
                        enc = encM ? encM[1] : null;
                        cpi = cpiM ? cpiM[1] : null;
                    }
                    const chs = [];
                    document.querySelectorAll('.chapter_item').forEach(el => {
                        const inp = el.querySelector('input[name="checkbox"]');
                        const titleEl = el.querySelector('.catalog_name a, .catalog_name span');
                        if (inp && inp.value && titleEl) {
                            chs.push({
                                id: inp.value,
                                title: titleEl.innerText.trim().replace(/\\s+/g, ' ')
                            });
                        }
                    });
                    return { enc, cpi, chapters: chs };
                }""")
                if parsed_cfg:
                    enc = parsed_cfg["enc"] or enc
                    cpi = parsed_cfg["cpi"] or cpi
                    chapters = parsed_cfg["chapters"]

        else:
            log("正在加载课程主页目录...")
            safe_goto(page, info["raw_url"], wait_until="networkidle")
            page.wait_for_timeout(3000)
            chapters = extract_chapters_from_page(page)

        if not chapters:
            if "passport2.chaoxing.com/login" in page.url:
                log("⚠️ 检测到当前账号未登录或在其他设备被迫下线，正在重新唤起扫码登录...")
                browser.close()
                if os.path.exists(AUTH_FILE):
                    os.remove(AUTH_FILE)
                auth_path = ensure_login(p)
                browser = launch_browser(p, headless=is_headless)
                context = browser.new_context(storage_state=auth_path)
                page = context.new_page()
                safe_goto(page, info["raw_url"], wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                chapters = extract_chapters_from_page(page)
            if not chapters:
                log("❌ 未能识别到课程章节目录，请确认该课程已开始且已选课。")
                browser.close()
                return

        raw_title = page.title()
        course_name = raw_title.replace("学生学习页面", "").replace("课程门户", "").replace("首页", "").strip() or f"课程_{info['course_id']}"
        log(f"🎉 成功识别课程《{course_name}》，共检测到 {len(chapters)} 个有效小节。")

        start_idx = 0
        target_id = start_chapter or info["chapter_id"]
        if target_id:
            try:
                num_idx = int(target_id)
                if 0 <= num_idx < len(chapters):
                    start_idx = num_idx
                elif 1 <= num_idx <= len(chapters):
                    start_idx = num_idx - 1
            except ValueError:
                for idx, c in enumerate(chapters):
                    if target_id in c["title"] or target_id == c["id"]:
                        start_idx = idx
                        break
        else:
            # 自动查询本地断点进度
            c_cache = load_course_cache()
            if c_cache and c_cache.get("course_id") == info["course_id"] and not c_cache.get("is_finished"):
                cached_idx = c_cache.get("last_chapter_index", 0)
                if 0 <= cached_idx < len(chapters):
                    start_idx = cached_idx
                    log(f"📌 自动恢复本地断点进度: 跳过前 {start_idx} 节，直达第 {start_idx + 1} 节继续！")

        target_chapters = chapters[start_idx:]
        log(f"从第 {start_idx + 1} 节 [{target_chapters[0]['title']}] 开始，后续共 {len(target_chapters)} 个小节。\n")

        for offset, ch in enumerate(target_chapters):
            current_abs_idx = start_idx + offset
            ch_id = ch["id"]
            ch_title = ch["title"]

            refer_url = f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={ch_id}&courseId={info['course_id']}&clazzid={info['clazz_id']}&cpi={cpi}&enc={enc}&mooc2=1&hidetype=0&fanyaVersion=0"
            transfer_url = f"https://mooc1.chaoxing.com/mycourse/transfer?moocId={info['course_id']}&clazzid={info['clazz_id']}&linkTime={int(time.time()*1000)}&ut=s&refer={urllib.parse.quote(refer_url)}"

            log(f"==================================================")
            log(f"正在进入小节 [{current_abs_idx + 1}/{len(chapters)}]: {ch_title} (ID: {ch_id})")
            log(f"==================================================")

            safe_goto(page, transfer_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # 多 Tab 标签全自动轮询遍历
            tab_elements = page.locator('.prev_ul li').all()
            if len(tab_elements) <= 1:
                # 只有 1 个标签或没有标签时，该标签默认已激活且在超星中被隐藏，无需点击切换，直接处理卡片！
                process_current_tab_tasks(page, cfg)
            else:
                log(f"检测到小节顶部包含 {len(tab_elements)} 个内容标签，逐一巡检...")
                for t_idx in range(len(tab_elements)):
                    cur_tabs = page.locator('.prev_ul li').all()
                    if t_idx < len(cur_tabs):
                        tab_item = cur_tabs[t_idx]
                        tab_name = tab_item.inner_text().strip().replace('\n', ' ')
                        is_active = "active" in (tab_item.get_attribute("class") or "")
                        if not is_active:
                            log(f"👉 切换至标签 [{tab_name}]...")
                            try:
                                # 使用原生 JS 点击，规避因 CSS 隐藏/不可见导致的 Playwright click() 30秒超时
                                tab_item.evaluate("el => el.click()")
                                page.wait_for_timeout(3000)
                            except Exception as e:
                                log(f"   ⚠️ 标签切换异常: {e}")
                        else:
                            log(f"👉 当前标签已就绪: [{tab_name}]")
                        process_current_tab_tasks(page, cfg)
            log(f"[{ch_title}] 本小节全部内容巡检/学习完成！\n")

            # 实时更新保存本地断点缓存
            save_course_cache({
                "url": url,
                "course_id": info["course_id"],
                "course_name": course_name,
                "total_chapters": len(chapters),
                "last_chapter_id": ch_id,
                "last_chapter_title": ch_title,
                "last_chapter_index": current_abs_idx + 1,
                "is_finished": False,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        log("\n🎉 所有目标章节任务点全部播放完成！")
        # 完结标记
        save_course_cache({
            "url": url,
            "course_id": info["course_id"],
            "course_name": course_name,
            "total_chapters": len(chapters),
            "last_chapter_id": target_chapters[-1]["id"] if target_chapters else "",
            "last_chapter_title": target_chapters[-1]["title"] if target_chapters else "",
            "last_chapter_index": len(chapters),
            "is_finished": True,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        notify_user("超星学习助手 - 学习任务圆满完成", f"恭喜！课程《{course_name}》共 {len(chapters)} 个小节已全部学习完成！", is_popup=True, block=True)
        browser.close()
        print("\n" + "=" * 55)
        print(f"🎉 恭喜！课程《{course_name}》共 {len(chapters)} 个小节已全部学完打卡！")
        print("=" * 55)
        try:
            input("\n请按 [回车] 键安全退出程序...")
        except (EOFError, KeyboardInterrupt):
            pass

def main():
    parser = argparse.ArgumentParser(description="超星泛雅/学习通全自动跨平台挂课助手")
    parser.add_argument("--url", type=str, help="网课主页或学习页面完整 URL")
    parser.add_argument("--start", type=str, default=None, help="起始小节名称或ID (可选)")
    parser.add_argument("--quiz-mode", type=str, choices=["skip", "ai"], default=None, help="测验处理模式: skip(跳过) / ai(AI答题暂存)")
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口（用于直观排查卡顿或界面验证）")
    parser.add_argument("--no-update", action="store_true", help="跳过自动检测更新")
    args = parser.parse_args()

    cfg = load_config()
    check_and_auto_update(cfg)
    cached = load_course_cache()
    has_unfinished = cached and not cached.get("is_finished") and cached.get("url")

    course_url = args.url
    if not course_url:
        print("\n" + "=" * 55)
        print(f"🎓 欢迎使用 Chaoxing Study Mate 超星学习助手 (V{APP_VERSION})")
        print("=" * 55)

        if has_unfinished:
            c_name = cached.get('course_name') or '未命名课程'
            c_idx = cached.get('last_chapter_index', 1)
            c_tot = cached.get('total_chapters', '?')
            c_title = cached.get('last_chapter_title', '')
            c_time = cached.get('updated_at', '')
            print("📌 检测到上次未完成的课程记录:")
            print(f"   - 课程名称: 《{c_name}》 (ID: {cached.get('course_id')})")
            print(f"   - 上次进度: 第 {c_idx}/{c_tot} 节 [{c_title}]")
            print(f"   - 记录时间: {c_time}")
            prompt_str = "\n1. 直接按 [回车] 继续上次进度，或输入新的课程链接: "
        else:
            prompt_str = "1. 请输入你的超星课程链接 (直接复制浏览器地址栏): "

        try:
            user_input = input(prompt_str).strip()
        except (EOFError, KeyboardInterrupt):
            user_input = ""

        if not user_input and has_unfinished:
            course_url = cached["url"]
            print(f"⚡ 已自动选择继续上次进度，直达第 {cached.get('last_chapter_index', 1)} 节！")
        else:
            course_url = user_input

    if not course_url:
        print("未输入有效链接，程序退出。")
        sys.exit(0)

    # 询问测验处理模式（若未在参数中指定）
    if not args.quiz_mode:
        saved_mode = cfg.get("quiz_mode", "skip")
        print("\n2. 请选择单元测试/章节测验处理方式:")
        print("   [1] 仅看视频，安全跳过测验（默认最稳妥）")
        print("   [2] 公共题库自动答题并【自动暂存草稿】（推荐，零门槛免配置开箱即用）")
        print("   [3] AI 智能辅助答题并【自动暂存草稿】（可在 config.json 配置 Key）")
        default_disp = '1' if saved_mode == 'skip' else ('2' if saved_mode == 'tiku' else '3')
        try:
            choice = input(f"请输入选项 [1/2/3] (直接回车默认 [{default_disp}]): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        if choice == "2":
            cfg["quiz_mode"] = "tiku"
        elif choice == "3":
            cfg["quiz_mode"] = "ai"
            if not cfg["ai_config"].get("api_key"):
                user_key = input("请输入你的 AI API Key (直接回车可稍后填): ").strip()
                if user_key:
                    cfg["ai_config"]["api_key"] = user_key
        elif choice == "1":
            cfg["quiz_mode"] = "skip"
        save_config(cfg)
    else:
        cfg["quiz_mode"] = args.quiz_mode

    # 询问浏览器显示模式（若命令行未强制指定 --headful）
    if not args.headful:
        saved_headless = cfg.get("headless", True)
        default_hl = "1" if saved_headless else "2"
        print("\n3. 请选择浏览器运行显示方式:")
        print("   [1] 后台静默运行（无头模式，省 CPU/内存，挂机推荐）")
        print("   [2] 弹出浏览器窗口（图形界面，便于实时观察画面）")
        try:
            choice_hl = input(f"请输入选项 [1/2] (直接回车默认 [{default_hl}]): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice_hl = ""
        if choice_hl == "2":
            cfg["headless"] = False
        elif choice_hl == "1":
            cfg["headless"] = True
        else:
            cfg["headless"] = saved_headless
        save_config(cfg)
    else:
        cfg["headless"] = False

    try:
        run_study(course_url, args.start, cfg)
    except KeyboardInterrupt:
        print("\n\n🛑 [用户已按 Ctrl+C 中断] 已安全退出，此前已完成的进度均已保存在服务器。")
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ [程序发生异常退出]: {e}")
        notify_user("超星学习助手 - 运行异常中断", f"程序异常退出: {e}，请检查后重新启动。", is_popup=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
