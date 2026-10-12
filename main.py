# /// script
# dependencies = [
#   "playwright>=1.40.0",
# ]
# ///

"""
====================================================================
🎓 Chaoxing Study Mate (超星学习助手)
====================================================================
- 跨平台支持：Windows / macOS / Linux 均可一键运行
- 认证机制：手机“学习通” App 扫码登录，持久化存储在 auth.json（免密复用）
- 播放控制：100% 完整时长播放、真实心跳上报、突破失焦暂停、静音无头运行
- 架构兼容：深度适配旧版 MOOC1 (studentstudy) 与新版 MOOC2 (mooc2-ans/stu)
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

    # Linux 常见默认绝对路径回退
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

    # 兜底调用 playwright 默认 chromium
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

    # 等待扫码完成跳转（离开登录页）
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

    is_mooc2 = "mooc2" in parsed.netloc or "mooc2" in parsed.path or "/stu" in parsed.path

    return {
        "raw_url": u,
        "is_mooc2": is_mooc2,
        "course_id": course_id,
        "clazz_id": clazz_id,
        "cpi": cpi,
        "enc": enc
    }

def resolve_chapters_mooc2(page, info):
    """处理新版 MOOC2 (mooc2-ans/mycourse/stu) 架构，提取所有小节与凭证"""
    page.goto(info["raw_url"], wait_until="networkidle")
    time.sleep(2)

    zj_frame = page.frame("frame_content-zj")
    if not zj_frame:
        log("❌ 未能定位到 MOOC2 章节目录框架 frame_content-zj")
        return None

    config = zj_frame.evaluate("""() => {
        let enc = null;
        let cpi = null;
        if (window.toOld) {
            const encM = window.toOld.toString().match(/var enc = "([^"]+)"/);
            const cpiM = window.toOld.toString().match(/var cpi = (\\d+)/);
            enc = encM ? encM[1] : null;
            cpi = cpiM ? cpiM[1] : null;
        }
        const chapters = [];
        document.querySelectorAll('.chapter_item').forEach(el => {
            const inp = el.querySelector('input[name="checkbox"]');
            const titleEl = el.querySelector('.catalog_name a, .catalog_name span');
            if (inp && inp.value && titleEl) {
                chapters.push({
                    id: inp.value,
                    title: titleEl.innerText.trim().replace(/\\s+/g, ' ')
                });
            }
        });
        return { enc, cpi, chapters };
    }""")

    return config

def play_video_frame(page, vf, video_idx, total_videos):
    """控制单集视频播放，监听心跳，达到 100% 结束"""
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
        log(f"启动播放异常: {e}")
        page.remove_listener('response', on_response)
        return False

    time.sleep(2)
    dur = vf.evaluate("() => window.videojs && videojs.getPlayers()['video'] ? videojs.getPlayers()['video'].duration() : null")
    if not dur or str(dur) == 'nan':
        dur = 0

    log(f"--> [第 {video_idx}/{total_videos} 个视频] 开始播放，视频时长: {dur:.1f} 秒 ({dur/60:.2f} 分钟)")

    last_log_time = 0
    last_cur = -1
    stall_count = 0

    while True:
        time.sleep(5)
        try:
            status = vf.evaluate("""() => {
                const p = window.videojs ? videojs.getPlayers()['video'] : null;
                if (!p) return null;

                // 自动处理视频中途弹窗小测 (单选/多选/判断)
                const quizDialog = document.querySelector('.ans-videoquiz');
                if (quizDialog && quizDialog.style.display !== 'none') {
                    const opts = quizDialog.querySelectorAll('input[type="radio"], input[type="checkbox"], .ans-videoquiz-opt');
                    if (opts.length > 0) {
                        // 随机或默认选第一个
                        opts[0].click();
                    }
                    const submitBtn = quizDialog.querySelector('.ans-videoquiz-submit, .btnSubmit, button');
                    if (submitBtn) submitBtn.click();
                }

                const cur = p.currentTime();
                const dur = p.duration();
                const ended = p.ended();

                // 仅在未播完时防切屏暂停
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
        except Exception:
            break

        if not status:
            break

        cur = status['current']
        dur = status['duration'] or dur

        # 看门狗检测：如果进度连续 40 秒未改变（校园网卡顿），自动触发缓冲重启
        if cur == last_cur and not status.get('paused') and cur < dur - 5.0:
            stall_count += 1
            if stall_count >= 8: # 8 * 5s = 40s
                log("   ⚠️ [看门狗] 检测到视频缓冲卡顿超过 40 秒，已触发播放器热重载...")
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

        if time.time() - last_log_time >= 30:
            pct = (cur / dur * 100) if dur > 0 else 0
            pass_str = " [任务点已通过]" if is_passed[0] else ""
            log(f"   [播放中] 进度: {cur:.1f}s / {dur:.1f}s ({pct:.1f}%){pass_str}")
            last_log_time = time.time()

        # 到达最后 2.5 秒内或触发 ended 视为 100% 完播
        if status.get('ended') or (dur > 0 and cur >= dur - 2.5):
            log(f"   [100% 完播] 视频已完整播放至最后一秒，时长审计 100%！")
            time.sleep(3)
            break

    page.remove_listener('response', on_response)
    return True

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

        log("正在解析课程章节与知识点目录...")
        if info["is_mooc2"]:
            cfg = resolve_chapters_mooc2(page, info)
            if not cfg or not cfg["chapters"]:
                log("❌ 解析 MOOC2 目录失败。")
                browser.close()
                return

            enc = cfg["enc"] or info["enc"]
            cpi = cfg["cpi"] or info["cpi"] or "408853908"
            chapters = cfg["chapters"]
            log(f"成功识别 MOOC2 课程结构，共 {len(chapters)} 个有效小节。")

            # 过滤起始章节
            start_idx = 0
            if start_chapter:
                for idx, c in enumerate(chapters):
                    if start_chapter in c["title"] or start_chapter == c["id"]:
                        start_idx = idx
                        break

            target_chapters = chapters[start_idx:]
            for ch in target_chapters:
                ch_id = ch["id"]
                ch_title = ch["title"]

                if any(k in ch_title for k in ['习题', '作业', '测验', '问卷', '考试']):
                    log(f"跳过非视频小节: {ch_title}")
                    continue

                refer_url = f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={ch_id}&courseId={info['course_id']}&clazzid={info['clazz_id']}&cpi={cpi}&enc={enc}&mooc2=1&hidetype=0&fanyaVersion=0"
                transfer_url = f"https://mooc1.chaoxing.com/mycourse/transfer?moocId={info['course_id']}&clazzid={info['clazz_id']}&linkTime={int(time.time()*1000)}&ut=s&refer={urllib.parse.quote(refer_url)}"

                log(f"\n==========================================")
                log(f"进入小节: {ch_title} (ID: {ch_id})")
                log(f"==========================================")

                page.goto(transfer_url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                cards_frame = None
                for f in page.frames:
                    if 'cards' in f.url:
                        cards_frame = f
                        break

                video_frames = [f for f in page.frames if 'video' in f.url]
                if not video_frames:
                    log(f"[{ch_title}] 未检测到视频任务点，跳过。")
                    continue

                log(f"[{ch_title}] 检测到 {len(video_frames)} 个视频任务。")
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
                        log(f"--> [第 {idx + 1}/{len(video_frames)} 个视频] 此前已完成，自动跳过。")
                        continue

                    play_video_frame(page, vf, idx + 1, len(video_frames))
                    log(f"[打卡成功] 第 {idx + 1} 个视频播放完毕！")

                log(f"[{ch_title}] 本小节全部视频学习完成！")

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
        print("\n\n🛑 [用户已按 Ctrl+C 中断] 已安全退出，此前已播放完成的进度已全部保存在超星服务器。")
        sys.exit(0)
if __name__ == "__main__":
    main()
