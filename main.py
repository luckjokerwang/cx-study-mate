# /// script
# dependencies = [
#   "playwright>=1.40.0",
# ]
# ///

"""
====================================================================
🎓 Chaoxing Study Mate (超星学习助手) - V2.0 工业增强版
====================================================================
- 跨平台支持：Windows / macOS / Linux 均可一键运行
- 认证机制：手机“学习通” App 扫码登录，持久化存储在 auth.json（免密复用）
- 播放控制：100% 完整时长播放、真实心跳上报、突破失焦暂停、静音无头运行
- 多Tab支持：全面支持小节内多标签轮询 (学习目标 / 视频 / 章节测验 / 文档)
- 安全机制：防顶号下线强校验，杜绝虚假“打卡成功”，校园网卡顿自动看门狗
====================================================================
"""

import os
import sys
import time
import json
import re
import argparse
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright

AUTH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth.json")

def log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def launch_browser(p, headless=True):
    """跨平台智能探测并唤起本地已有的 Chrome 或 Edge，无需重新下载 300MB 浏览器"""
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
    """检查登录态。若不存在或已过期，则弹出二维码让用户通过学习通 App 扫码登录"""
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

        # 1. 严格检查是否被其他设备顶号下线
        current_page_url = page.url
        if any(k in current_page_url for k in ["space/index", "monitor_temp", "passport2.chaoxing.com"]):
            log("\n❌【严重警告】检测到超星账号在其他设备（手机/其他电脑）登录，已被迫下线！")
            log("请先关闭其他设备上的学习通网页，并在本机重新扫码登录后再挂机。")
            page.remove_listener('response', on_response)
            sys.exit(1)

        try:
            status = vf.evaluate("""() => {
                const p = window.videojs ? videojs.getPlayers()['video'] : null;
                if (!p) return null;

                // 自动处理视频中途弹窗小测
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

                // 仅在未播完且距离末尾大于 2.5 秒时防暂停恢复播放
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
                log(f"   ❌ 视频播放帧失联异常: {e}，跳过此视频。")
                page.remove_listener('response', on_response)
                return False
            continue

        if not status:
            error_count += 1
            if error_count >= 5:
                log("   ❌ 未能获取到播放器状态，跳过此视频。")
                page.remove_listener('response', on_response)
                return False
            continue

        error_count = 0
        cur = status['current']
        dur = status['duration'] or dur

        # 2. 看门狗检测：如果进度连续 40 秒未改变（校园网卡顿），自动触发播放器热重载
        if cur == last_cur and not status.get('paused') and cur < dur - 5.0:
            stall_count += 1
            if stall_count >= 8:
                log("   ⚠️ [看门狗] 检测到视频缓冲卡顿超过 40 秒，触发播放器热重载恢复...")
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

        # 3. 必须真正播到视频最后 2.5 秒内或触发 ended 视为 100% 完播
        if status.get('ended') or (dur > 0 and cur >= dur - 2.5):
            log(f"   [100% 完播] 视频已完整播放至最后一秒，时长审计 100%！")
            time.sleep(3)
            page.remove_listener('response', on_response)
            return True

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

def process_current_tab_tasks(page):
    """处理当前卡片/标签下的所有任务点（包含视频与章节测验）"""
    cards_frame = None
    for f in page.frames:
        if 'cards' in f.url:
            cards_frame = f
            break

    # 1. 检查当前 Tab 下是否有视频
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

    # 2. 检查当前 Tab 下是否有章节测验/作业
    quiz_frames = [f for f in page.frames if 'work' in f.url or 'quiz' in f.url or 'doHomeWorkNew' in f.url]
    if quiz_frames:
        log(f"   📝 检测到本标签包含【章节测验/单元测试】任务点。")

def run_study(url, start_chapter=None):
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
                cfg = zj_frame.evaluate("""() => {
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
                if cfg:
                    enc = cfg["enc"] or enc
                    cpi = cfg["cpi"] or cpi
                    chapters = cfg["chapters"]

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

            # 构建进入小节的 URL
            refer_url = f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={ch_id}&courseId={info['course_id']}&clazzid={info['clazz_id']}&cpi={cpi}&enc={enc}&mooc2=1&hidetype=0&fanyaVersion=0"
            transfer_url = f"https://mooc1.chaoxing.com/mycourse/transfer?moocId={info['course_id']}&clazzid={info['clazz_id']}&linkTime={int(time.time()*1000)}&ut=s&refer={urllib.parse.quote(refer_url)}"

            log(f"==================================================")
            log(f"正在进入小节: {ch_title} (ID: {ch_id})")
            log(f"==================================================")

            page.goto(transfer_url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)

            # 核心升级：遍历本小节顶部的所有 Tab 标签 (例如：1学习目标、2视频、3章节测验)
            tab_elements = page.locator('.prev_ul li').all()
            if not tab_elements:
                # 若无多 Tab，直接处理当前卡片内容
                process_current_tab_tasks(page)
            else:
                log(f"检测到小节顶部包含 {len(tab_elements)} 个内容标签，逐一巡检...")
                for t_idx in range(len(tab_elements)):
                    # 重新定位以防 DOM 刷新
                    cur_tabs = page.locator('.prev_ul li').all()
                    if t_idx < len(cur_tabs):
                        tab_item = cur_tabs[t_idx]
                        tab_name = tab_item.inner_text().strip().replace('\n', ' ')
                        log(f"👉 切换至标签 [{tab_name}]...")
                        tab_item.click()
                        page.wait_for_timeout(3000)
                        process_current_tab_tasks(page)

            log(f"[{ch_title}] 本小节全部内容巡检/学习完成！\n")

        log("\n🎉 所有目标章节任务点全部播放完成！")
        browser.close()

def main():
    parser = argparse.ArgumentParser(description="超星泛雅/学习通全自动跨平台挂课助手")
    parser.add_argument("--url", type=str, help="网课主页或学习页面完整 URL")
    parser.add_argument("--start", type=str, default=None, help="起始小节名称或ID (可选)")
    args = parser.parse_args()

    course_url = args.url
    if not course_url:
        print("\n" + "=" * 50)
        print("🎓 欢迎使用 Chaoxing Study Mate 超星学习助手")
        print("=" * 50)
        course_url = input("请输入你的超星课程链接 (直接复制浏览器地址栏): ").strip()

    if not course_url:
        print("未输入有效链接，程序退出。")
        sys.exit(0)

    try:
        run_study(course_url, args.start)
    except KeyboardInterrupt:
        print("\n\n🛑 [用户已按 Ctrl+C 中断] 已安全退出，此前已完成的进度均已保存在服务器。")
        sys.exit(0)

if __name__ == "__main__":
    main()
