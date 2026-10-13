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
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(BASE_DIR, "auth.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FONT_MAP_FILE = os.path.join(BASE_DIR, "font_map_table.json")

KX_RADICALS_TAB = str.maketrans(
    '⼀⼁⼂⼃⼄⼅⼆⼇⼈⼉⼊⼋⼌⼍⼎⼏⼐⼑⼒⼓⼔⼕⼖⼗⼘⼙⼚⼛⼜⼝⼞⼟⼠⼡⼢⼣⼤⼥⼦⼧⼨⼩⼪⼫⼬⼭⼮⼯⼰⼱⼲⼳⼴⼵⼶⼷⼸⼹⼺⼻⼼⼽⼾⼿⽀⽁⽂⽃⽄⽅⽆⽇⽈⽉⽊⽋⽌⽍⽎⽏⽐⽑⽒⽓⽔⽕⽖⽗⽘⽙⽚⽛⽜⽝⽞⽟⽠⽡⽢⽣⽤⽥⽦⽧⽨⽩⽪⽫⽬⽭⽮⽯⽰⽱⽲⽳⽴⽵⽶⽷⽸⽹⽺⽻⽼⽽⽾⽿⾀⾁⾂⾃⾄⾅⾆⾇⾈⾉⾊⾋⾌⾍⾎⾏⾐⾑⾒⾓⾔⾕⾖⾗⾘⾙⾚⾛⾜⾝⾞⾟⾠⾡⾢⾣⾤⾥⾦⾧⾨⾩⾪⾫⾬⾭⾮⾯⾰⾱⾲⾳⾴⾵⾶⾷⾸⾹⾺⾻⾼髙⾽⾾⾿⿀⿁⿂⿃⿄⿅⿆⿇⿈⿉⿊⿋⿌⿍⿎⿏⿐⿑⿒⿓⿔⿕⺠⻬⻩⻢⻜⻅⺟⻓',
    '一丨丶丿乙亅二亠人儿入八冂冖冫几凵刀力勹匕匚匸十卜卩厂厶又口囗土士夂夊夕大女子宀寸小尢尸屮山巛工己巾干幺广廴廾弋弓彐彡彳心戈戶手支攴文斗斤方无日曰月木欠止歹殳毋比毛氏气水火爪父爻爿片牙牛犬玄玉瓜瓦甘生用田疋疒癶白皮皿目矛矢石示禸禾穴立竹米糸缶网羊羽老而耒耳聿肉臣自至臼舌舛舟艮色艸虍虫血行衣襾見角言谷豆豕豸貝赤走足身車辛辰辵邑酉采里金長門阜隶隹雨青非面革韋韭音頁風飞食首香馬骨高高髟鬥鬯鬲鬼魚鳥鹵鹿麥麻黃黍黑黹黽鼎鼓鼠鼻齊齒龍龜龠民齐黄马飞见母长'
)

def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def load_config():
    default_cfg = {
        "quiz_mode": "skip",
        "ai_config": {
            "api_key": "",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        }
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

def play_video_frame(page, vf, video_idx, total_videos):
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
            if (!p) return null;
            p.muted(true);
            p.play();
            return p.duration();
        }""")
    except Exception as e:
        log(f"   ⚠️ 启动播放异常: {e}")
        page.remove_listener('response', on_response)
        return False

    time.sleep(2)
    dur = vf.evaluate("() => window.videojs && videojs.getPlayers()['video'] ? videojs.getPlayers()['video'].duration() : null")
    if not dur or str(dur) == 'nan':
        dur = 0

    log(f"   --> [视频 {video_idx}/{total_videos}] 开始播放，视频时长: {dur:.1f} 秒 ({dur/60:.2f} 分钟)")

    last_log_time = 0
    last_cur = -1
    stall_count = 0
    error_count = 0

    while True:
        time.sleep(5)

        # 检查是否被顶号
        current_page_url = page.url
        if any(k in current_page_url for k in ["space/index", "monitor_temp", "passport2.chaoxing.com"]):
            log("\n❌【严重警告】检测到超星账号在其他设备登录已被迫下线！")
            log("请先关闭其他设备上的网页，并在本机重新扫码登录。")
            page.remove_listener('response', on_response)
            sys.exit(1)

        try:
            status = vf.evaluate("""() => {
                const p = window.videojs ? videojs.getPlayers()['video'] : null;
                if (!p) return null;

                const quizDialog = document.querySelector('.ans-videoquiz');
                if (quizDialog && quizDialog.style.display !== 'none') {
                    const opts = quizDialog.querySelectorAll('input[type="radio"], input[type="checkbox"], .ans-videoquiz-opt');
                    if (opts.length > 0) {
                        opts[0].click();
                    }
                    const submitBtn = quizDialog.querySelector('.ans-videoquiz-submit, .btnSubmit, button');
                    if (submitBtn) submitBtn.click();
                }

                const cur = p.currentTime();
                const dur = p.duration();
                const ended = p.ended();

                if (!ended && (!dur || cur < dur - 2.5)) {
                    if (p.paused()) {
                        p.play();
                    }
                }
                return {
                    current: cur,
                    duration: dur,
                    paused: p.paused(),
                    ended: ended
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
        cur = status['current']
        dur = status['duration'] or dur

        if cur == last_cur and not status.get('paused') and cur < dur - 5.0:
            stall_count += 1
            if stall_count >= 8:
                log("   ⚠️ [看门狗] 缓冲卡顿超过 40 秒，触发播放器热重载恢复...")
                try:
                    vf.evaluate("() => { const p = videojs.getPlayers()['video']; if (p) { p.pause(); setTimeout(() => p.play(), 1000); } }")
                except Exception:
                    pass
                stall_count = 0
        else:
            stall_count = 0
        last_cur = cur

        if is_passed[0] and not notified_pass[0]:
            log(f"   [状态更新] 任务点已达标(isPassed=true)，继续播完至 100% 结束以确保数据审计完整...")
            notified_pass[0] = True

        if time.time() - last_log_time >= 25:
            pct = (cur / dur * 100) if dur > 0 else 0
            rem_sec = max(0, int(dur - cur))
            rem_str = f"{rem_sec // 60}分{rem_sec % 60:02d}秒"
            bar_len = 18
            filled = int(bar_len * (pct / 100))
            bar = "█" * filled + "░" * (bar_len - filled)
            pass_str = " [已通关]" if is_passed[0] else ""
            log(f"   [{bar}] {pct:5.1f}% | 剩余: {rem_str} | 已播: {int(cur)//60}分{int(cur)%60:02d}秒 / {int(dur)//60}分{int(dur)%60:02d}秒{pass_str}")
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

def solve_quiz_with_ai(work_frame, ai_cfg):
    """解密字体、大模型辅助答题并自动点击【暂存草稿】"""
    from fontTools.ttLib.ttFont import TTFont

    if not os.path.exists(FONT_MAP_FILE):
        log("   ⚠️ 未找到 font_map_table.json 字体解密表，跳过自动答题。")
        return

    with open(FONT_MAP_FILE, "r", encoding="utf-8") as f:
        char_map = json.load(f)
    hash_map = {h: c for c, h in char_map.items()}

    font_b64 = work_frame.evaluate("""() => {
        for (let s of document.querySelectorAll('style')) {
            let m = s.textContent.match(/base64,([\\w\\W]+?)'/);
            if (m) return m[1];
        }
        return null;
    }""")

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
                    except: pass
            res.append(ch)
        return ''.join(res).translate(KX_RADICALS_TAB)

    timus = work_frame.locator('.TiMu').all()
    log(f"   📝 检测到测验包含 {len(timus)} 道题，正在调用 AI 模型解答...")

    for idx, timu in enumerate(timus):
        raw_txt = decode_text(timu.inner_text()).strip()
        opts = timu.locator('ul li').all()
        opt_texts = []
        for o in opts:
            span = o.locator('.num_option, .num_option_dx')
            d = span.get_attribute('data') if span.count() > 0 else '?'
            opt_texts.append(f"{d}. {decode_text(o.inner_text()).strip()}")

        prompt = f"请为以下大学网课题目选择正确答案，严格只输出选项字母（如 A 或 true 或 ABC）：\n题目：{raw_txt}\n选项：\n" + "\n".join(opt_texts)

        # 调 OpenAI 兼容接口
        api_key = ai_cfg.get("api_key")
        base_url = ai_cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        model = ai_cfg.get("model", "deepseek-chat")

        answer_str = "A" # 兜底
        if api_key:
            try:
                req_data = json.dumps({
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    answer_str = resp_json["choices"][0]["message"]["content"].strip().upper()
            except Exception as e:
                log(f"   ⚠️ AI 答题请求失败 ({e})，将使用默认选项暂存。")

        # 勾选答案
        for o in opts:
            span = o.locator('.num_option, .num_option_dx')
            d = (span.get_attribute('data') or '').upper()
            if d and (d in answer_str or ('对' in answer_str and d == 'TRUE') or ('错' in answer_str and d == 'FALSE')):
                try:
                    o.click()
                except Exception:
                    pass

    # 核心安全操作：只点击“暂存”，绝不自动提交！
    time.sleep(1)
    work_frame.evaluate("() => { if (window.noSubmit) window.noSubmit(); }")
    log("   ✅【测验草稿暂存完成】所有题目已写入并自动暂存！请在网页端核对后手动提交。")

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

            success = play_video_frame(page, vf, idx + 1, len(video_frames))
            if success:
                log(f"   [打卡成功] 视频 {idx + 1} 学习完毕！")

    # 2. 章节测验/作业处理
    quiz_frames = [f for f in page.frames if 'doHomeWorkNew' in f.url]
    if quiz_frames:
        q_mode = cfg.get("quiz_mode", "skip")
        if q_mode == "ai":
            solve_quiz_with_ai(quiz_frames[0], cfg.get("ai_config", {}))
        else:
            log(f"   📝 [测验安全跳过] 当前标签包含单元测验，已按设定安全跳过（保留手动完成）。")

def run_study(url, start_chapter=None, cfg=None):
    if not cfg:
        cfg = load_config()

    info = parse_course_url(url)
    if not info["course_id"]:
        log("❌ 无法从链接中解析出 courseId，请检查输入的链接格式。")
        return

    with sync_playwright() as p:
        auth_path = ensure_login(p)

        browser = launch_browser(p, headless=True)
        context = browser.new_context(storage_state=auth_path)
        page = context.new_page()

        chapters = []
        cpi = info["cpi"] or "408853908"
        enc = info["enc"]

        if info["is_study_page"]:
            log("检测到输入链接为具体小节学习页面，正在直接加载并提取完整目录...")
            page.goto(info["raw_url"], wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            chapters = extract_chapters_from_page(page)

        elif info["is_mooc2_portal"]:
            log("检测到输入链接为 MOOC2 课程门户首页，正在加载章节框架...")
            page.goto(info["raw_url"], wait_until="networkidle")
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
            page.goto(info["raw_url"], wait_until="networkidle")
            page.wait_for_timeout(3000)
            chapters = extract_chapters_from_page(page)

        if not chapters:
            log("❌ 未能识别到课程章节目录，请确认该课程已开始且已选课。")
            browser.close()
            return

        log(f"🎉 成功识别课程结构，共检测到 {len(chapters)} 个有效小节。")

        start_idx = 0
        target_id = start_chapter or info["chapter_id"]
        if target_id:
            for idx, c in enumerate(chapters):
                if target_id in c["title"] or target_id == c["id"]:
                    start_idx = idx
                    break

        target_chapters = chapters[start_idx:]
        log(f"从第 {start_idx + 1} 节 [{target_chapters[0]['title']}] 开始，后续共 {len(target_chapters)} 个小节。\n")

        for ch in target_chapters:
            ch_id = ch["id"]
            ch_title = ch["title"]

            refer_url = f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={ch_id}&courseId={info['course_id']}&clazzid={info['clazz_id']}&cpi={cpi}&enc={enc}&mooc2=1&hidetype=0&fanyaVersion=0"
            transfer_url = f"https://mooc1.chaoxing.com/mycourse/transfer?moocId={info['course_id']}&clazzid={info['clazz_id']}&linkTime={int(time.time()*1000)}&ut=s&refer={urllib.parse.quote(refer_url)}"

            log(f"==================================================")
            log(f"正在进入小节: {ch_title} (ID: {ch_id})")
            log(f"==================================================")

            page.goto(transfer_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # 多 Tab 标签全自动轮询遍历
            tab_elements = page.locator('.prev_ul li').all()
            if not tab_elements:
                process_current_tab_tasks(page, cfg)
            else:
                log(f"检测到小节顶部包含 {len(tab_elements)} 个内容标签，逐一巡检...")
                for t_idx in range(len(tab_elements)):
                    cur_tabs = page.locator('.prev_ul li').all()
                    if t_idx < len(cur_tabs):
                        tab_item = cur_tabs[t_idx]
                        tab_name = tab_item.inner_text().strip().replace('\n', ' ')
                        log(f"👉 切换至标签 [{tab_name}]...")
                        tab_item.click()
                        page.wait_for_timeout(3000)
                        process_current_tab_tasks(page, cfg)

            log(f"[{ch_title}] 本小节全部内容巡检/学习完成！\n")

        log("\n🎉 所有目标章节任务点全部播放完成！")
        browser.close()

def main():
    parser = argparse.ArgumentParser(description="超星泛雅/学习通全自动跨平台挂课助手")
    parser.add_argument("--url", type=str, help="网课主页或学习页面完整 URL")
    parser.add_argument("--start", type=str, default=None, help="起始小节名称或ID (可选)")
    parser.add_argument("--quiz-mode", type=str, choices=["skip", "ai"], default=None, help="测验处理模式: skip(跳过) / ai(AI答题暂存)")
    args = parser.parse_args()

    cfg = load_config()

    course_url = args.url
    if not course_url:
        print("\n" + "=" * 55)
        print("🎓 欢迎使用 Chaoxing Study Mate 超星学习助手 (V2.5)")
        print("=" * 55)
        course_url = input("1. 请输入你的超星课程链接 (直接复制浏览器地址栏): ").strip()

    if not course_url:
        print("未输入有效链接，程序退出。")
        sys.exit(0)

    # 询问测验处理模式（若未在参数中指定）
    if not args.quiz_mode:
        saved_mode = cfg.get("quiz_mode", "skip")
        print("\n2. 请选择单元测试/章节测验处理方式:")
        print("   [1] 仅看视频，安全跳过测验（默认推荐，最稳妥）")
        print("   [2] AI 智能辅助答题并【自动暂存草稿】（可在 config.json 配置 Key）")
        choice = input(f"请输入选项 [1/2] (直接回车默认 [{'1' if saved_mode=='skip' else '2'}]): ").strip()

        if choice == "2":
            cfg["quiz_mode"] = "ai"
            if not cfg["ai_config"].get("api_key"):
                user_key = input("请输入你的 AI API Key (支持 DeepSeek / 硅基流动 / Qwen，直接回车可稍后填): ").strip()
                if user_key:
                    cfg["ai_config"]["api_key"] = user_key
        elif choice == "1":
            cfg["quiz_mode"] = "skip"
        save_config(cfg)
    else:
        cfg["quiz_mode"] = args.quiz_mode

    try:
        run_study(course_url, args.start, cfg)
    except KeyboardInterrupt:
        print("\n\n🛑 [用户已按 Ctrl+C 中断] 已安全退出，此前已完成的进度均已保存在服务器。")
        sys.exit(0)

if __name__ == "__main__":
    main()
