from pathlib import Path


LANDING_HTML = Path(__file__).resolve().parents[1] / "web" / "wordcraft_landing.html"


def test_landing_contains_reviews_and_faq_sections():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert '<section id="reviews"' in html
    assert 'class="reviews-grid"' in html
    assert 'class="review-action"' in html
    assert "写下一句真实体验" in html
    assert 'onclick="openFeedbackModal()">我要评论</button>' in html
    assert "zha******@qq.com" in html
    assert '<section id="faq"' in html
    assert 'class="faq-list"' in html
    assert "免费版有什么限制？" in html


def test_landing_feedback_entrypoints_and_modal_exist():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert 'onclick="scrollToReviews()">我要反馈</button>' in html
    assert 'id="feedbackModal"' in html
    assert 'onsubmit="submitFeedback(event)"' in html
    assert 'id="feedbackContent"' in html
    assert 'id="feedbackRating" type="hidden"' in html
    assert 'class="feedback-star" data-rating="5"' in html
    assert "function prefillFeedbackUser()" in html
    assert "function maskFeedbackIdentity(value)" in html
    assert "function setFeedbackRating(rating)" in html
    assert "function bindFeedbackRating()" in html
    assert "function scrollToReviews()" in html
    assert "function openFeedbackModal()" in html
    assert "function submitFeedback(event)" in html
    assert "window.supabaseClient.auth.getSession()" in html
    assert "nameInput.value = maskFeedbackIdentity(email);" in html
    assert "local.slice(0,3) + '****@' + domain" in html
    assert "请先选择评分" in html


def test_landing_pro_cta_and_countdown_badge_are_conversion_ready():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert 'id="proCountdownBadge"' in html
    assert "const targetDate = new Date('2026-06-30T23:59:59+08:00');" in html
    assert '<div class="price-amount"><span class="num">¥6.9</span><span class="unit">/ 月</span></div>' in html
    assert "Pro 月付" in html
    assert "Pro 年付" in html
    assert '<span class="strike">¥9.9 / 月</span>' in html
    assert '<span class="deal">¥6.9 / 月</span>' in html
    assert '<span class="strike">¥79 / 年</span>' in html
    assert '<span class="deal">¥69 / 年</span>' in html
    assert 'button class="price-cta primary" onclick="openWechatModal(\'pro\')">微信咨询订阅</button>' in html
    assert 'button class="price-cta primary" onclick="openWechatModal(\'emergency\')">微信咨询下单</button>' in html
    assert "Math.max(0, Math.floor((targetDate - now) / 86400000));" in html


def test_landing_wechat_modal_has_distinct_emergency_and_pro_copy():
    html = LANDING_HTML.read_text(encoding="utf-8")

    assert "const modalConfigs = {" in html
    assert "emergency: {" in html
    assert "pro: {" in html
    assert "contact: {" in html
    assert "论文急诊包 · 微信咨询" in html
    assert "Pro 订阅 · 微信咨询" in html
    assert "微信联系" in html
    assert "扫码咨询 Pro 月付 / 年付方案，确认后发放激活码。" in html
    assert "扫码添加企业微信进行咨询" in html
    assert "24h 内交付检查报告" in html
    assert "Pro 月付：" in html
    assert "6.9 / 月" in html
    assert "69 / 年" in html
    assert "付款后发送激活码，登录后即可升级" in html
    assert "微信号：" not in html
    assert 'id="wechatModalQrImage"' in html
    assert 'src="assets/wechat-contact-qr.jpg"' in html
    assert "openWechatModal('contact')" in html
    assert "meta: ''" in html
    assert "meta.style.display = config.meta ? 'block' : 'none';" in html
    assert 'id="wechatModalMeta" style="font-size:13px;color:var(--text-muted);line-height:1.7;margin-bottom:20px;display:none"' in html
    assert 'width:520px;max-width:94vw;text-align:center' in html
