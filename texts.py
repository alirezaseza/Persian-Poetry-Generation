# -*- coding: utf-8 -*-
"""All the texts the user sees (Persian + English). Edit freely."""

# Optional stickers: paste a sticker file_id here (send any sticker to the bot as admin -> it replies with the id).
STICKERS = {"welcome": "", "working": "", "done": "", "fail": ""}

T = {
"fa": {
"choose_lang": "🌍 <b>زبان خودتو انتخاب کن</b>\nChoose your language 👇",
"menu": ("🌹 <b>به شعرساز خوش اومدی!</b> 🌹\n\n"
         "اینجا یه هوش مصنوعی داره شعر فارسی می‌سازه؛ از حافظ و فردوسی تا مولوی ✨\n"
         "💳 اعتبار باقی‌مونده‌ی تو: <b>{credits}</b>\n\n"
         "یکی از گزینه‌ها رو بزن 👇"),
"b_poem": "📜 ساخت شعر", "b_about": "🤖 درباره مدل", "b_credit": "💳 درخواست کردیت",
"b_contact": "📞 تماس با ما", "b_lang": "🌐 English", "b_back": "🔙 برگشت", "b_menu": "🏠 منوی اصلی",
"pick_poet": ("🎨 <b>کدوم سبک رو می‌خوای؟</b>\n\n"
              "🌹 حافظ — غزل‌های عاشقانه و عارفانه\n"
              "⚔️ فردوسی — حماسه و شاهنامه‌وار\n"
              "📜 مولوی — فقط مثنوی، به سبک مثنوی معنوی\n"
              "🎭 ترکیب همه — قاطی‌پاطیِ همه‌ی شاعرها"),
"b_hafez": "🌹 حافظ", "b_ferdowsi": "⚔️ فردوسی", "b_masnavi": "📖 مثنوی", "b_mix": "🎭 ترکیب همه شاعرها",
"ask_mixform": "🎭 <b>ترکیب همه شاعرها!</b>\nچه نوع شعری می‌خوای؟",
"b_mf_gh": "🌹 غزلیات", "b_mf_ms": "📖 مثنوی", "b_mf_all": "🎲 مخلوط (هر چی مدل دوست داره)",
"b_molavi": "📜 مولوی", "label_molavi": "مولوی",
"ask_story": "⚔️ <b>فردوسی انتخاب شد!</b>\nشعرش از کدوم بخش شاهنامه باشه؟",
"b_fs": ["🎲 هر بخشی (مدل انتخاب کنه)", "🛡 رستم و اسفندیار", "⚔️ جنگ بزرگ کیخسرو با افراسیاب", "👑 خسرو پرویز",
         "🐗 بهرام گور", "🏛 اسکندر", "🏇 دوازده رخ"],
"label_hafez": "حافظ", "label_ferdowsi": "فردوسی", "label_masnavi": "مثنوی", "label_mix": "ترکیب همه شاعرها",
"ask_ghazal": "🌹 <b>حافظ انتخاب شد!</b>\nشعر <b>غزلیات</b> باشه یا هر قالبی که مدل دوست داره؟",
"b_ghazal_yes": "✅ آره، غزلیات", "b_ghazal_no": "🔀 نه، هر قالبی",
"ask_pair": ("📖 <b>{label} انتخاب شد!</b>\nقافیه‌ها چطور باشن؟\n\n"
             "📏 <b>فقط آخر بیت</b> — مثل شعر معمولی\n"
             "🔗 <b>آخر هر مصرع</b> — هر دو مصرعِ بیت با هم هم‌قافیه می‌شن (جفت‌قافیه)"),
"b_pair_end": "📏 فقط آخر بیت", "b_pair_each": "🔗 آخر هر مصرع",
"ask_prompt": ("🎯 <b>می‌خوای شعر از کجا شروع بشه؟</b>\n\n"
               "✍️ <b>پرامپت خودم</b> — مصرع اولو خودت می‌دی\n"
               "🎲 <b>رندوم</b> — بذار مدل خودش شروع کنه\n\n"
               "⭐ <b>پیشنهاد ما: بذار خودِ مدل شروع کنه!</b> معمولاً شعرهای بهتری درمیاد 😉"),
"b_prompt_own": "✍️ پرامپت خودم", "b_prompt_rnd": "🎲 رندوم (پیشنهادی) ⭐",
"own_info": ("✍️ <b>مصرع اولِ شعرتو بنویس و بفرست</b>\n\n"
             "💡 سعی کن <b>کوتاه</b> باشه (۲ تا ۸ کلمه) و از <b>واژه‌های قدیمی و کلاسیک</b> استفاده کن، مثل «دلا»، «ساقی»، «یار»، «شبان» …\n\n"
             "⚠️ راستش <b>توصیه نمی‌کنیم</b> از این حالت استفاده کنی؛ حالت رندوم معمولاً شعر بهتری می‌سازه 😉\n"
             "فقط حروف فارسی (بدون عدد و حروف انگلیسی)."),
"prompt_bad": {
    "foreign_char": "🙈 فقط حروف فارسی! عدد و حروف انگلیسی نداشته باشه.",
    "too_short": "🐣 این یکی خیلی کوتاهه! یه کم بلندترش کن.",
    "one_word": "🐣 حداقل دو کلمه بنویس.",
    "too_long": "🐘 خیلی بلند شد! مصرع کوتاه‌تر بفرست.",
    "too_many_words": "🐘 کلمه‌هاش زیاده! حداکثر ۱۵ کلمه.",
    "char_run": "🤔 تکرار حرف‌ها زیاده، یه جور دیگه بنویس.",
    "not_text": "📝 فقط متن بفرست لطفاً."},
"prompt_ok": "👌 عالی! شروع شعر: «<i>{first}</i>»",
"ask_make": ("🏭 <b>چندتا شعر بسازم؟</b> (حداکثر ۱۰۰ تا)\n"
             "هرچی بیشتر بسازم، انتخاب بهتری داریم اما صبر بیشتری می‌خواد ⏳\n\n"
             "💳 هر شعر ساخته‌شده ۱ کردیت مصرف می‌کنه. کردیت تو: <b>{credits}</b>"),
"ask_top": ("🏆 <b>چندتا از بهترین‌ها رو نشونت بدم؟</b>\nمن {make} تا می‌سازم و بهترین‌ها رو برات جدا می‌کنم.\n"
            "💳 هزینه: <b>{make}</b> کردیت"),
"b_cancel": "❌ لغو ساخت",
"queued": "🚦 تو صف هستی… نفر {pos} ام. چند لحظه صبر کن 🙏",
"cancelling": "🛑 دارم لغو می‌کنم…",
"cancelled": "🛑 <b>ساخت شعر لغو شد.</b>\nکردیتت کامل برگشت 💳",
"working": ("{spin} <b>دارم شعر می‌سازم…</b>\n\n"
            "🎭 سبک: {label}\n⏱ زمان: {sec} ثانیه\n🧪 کاندیدا: {c}/{n}\n\n"
            "شاعرهای مجازی دارن قلم‌به‌دست می‌شن ✍️"),
"done": "🎉 <b>شعرها آماده شد!</b>  ({sec} ثانیه)",
"poem_n": "شعر", "qaf": "قافیه", "rad": "ردیف",
"after": "دوست داشتی؟ یه دور دیگه بسازیم؟ 👇",
"b_again": "🔁 دوباره با همین تنظیمات", "b_new": "🆕 شعر جدید",
"failed": "😵 ای وای! مدل این دفعه نتونست شعر بسازه. کردیتت برگشت، دوباره امتحان کن 🙏",
"timeout": "⏰ خیلی طول کشید و متوقفش کردم. کردیتت برگشت؛ تعداد کمتری بساز 🙏",
"busy": "⏳ هنوز شعر قبلیت در حال ساخته شدنه، یه کم صبر کن!",
"no_credit": ("😢 <b>اعتبارت تموم شده!</b>\n\nبرای شارژ دوباره، دکمه‌ی «💳 درخواست کردیت» رو بزن."),
"about": ("🤖 <b>درباره مدل</b>\n\n"
          "این بات به یک مدل زبانیِ <b>GPT مخصوص شعر فارسی</b> وصله که از پایه (from scratch) آموزش داده شده 🧠\n\n"
          "📚 مدل از هزاران شعر کلاسیک (حافظ، فردوسی، مثنوی و …) یاد گرفته چطور وزن، قافیه و ردیف‌ها کنار هم می‌شن.\n"
          "🔎 برای هر درخواست چند شعر می‌سازه، قافیه و تکرارها و کلمه‌های ساختگی رو چک می‌کنه و فقط <b>بهترین‌ها</b> رو نشونت می‌ده.\n\n"
          "⚠️ شعرها <b>ساخته‌ی هوش مصنوعی</b> هستن و از خودِ شاعرها نیستن؛ ممکنه گاهی اشتباه یا بی‌معنی باشن. این یه پروژه‌ی آزمایشیه 🧪\n\n"
          "🔬 برای جزئیات فنی، دکمه‌ی «بخش تخصصی» رو بزن 👇"),
"b_tech": "🔬 بخش تخصصی", "b_prev": "⬅️ قبلی", "b_next": "بعدی ➡️", "b_about_back": "🤖 درباره مدل",
"tech": [
("🔬 <b>بخش تخصصی ‹۱ از ۵›</b>\n<b>۱) داده و پیش‌پردازش</b>\n\n"
 "▪️ <b>منبع:</b> آرشیو شعرهای گنجور (فایل‌های JSON هر شعر). مسیر هر شعر، نام شاعر و قالب (غزل، مثنوی، قصیده…) از ساختار آرشیو استخراج می‌شه.\n"
 "▪️ <b>نرمال‌سازی متن:</b> یکسان‌سازی حروف عربی/فارسی (ك→ک، ي→ی و …)، حذف اعراب و کشیده و نویسه‌های نامرئی، فقط حروف فارسی و نیم‌فاصله (ZWNJ) مجازه. بیت‌های دارای عدد یا حروف لاتین کنار گذاشته می‌شن.\n"
 "▪️ <b>بیت‌ها:</b> هر شعر به جفت‌مصرع شکسته می‌شه. شعرهای بلند به تکه‌های حداکثر ۱۲ بیتی تقسیم می‌شن تا داخل پنجره‌ی ۵۱۲ توکنی جا بشن.\n"
 "▪️ <b>حذف تکراری‌ها:</b> هم تکرار دقیق و هم تکرار تقریبی؛ شعری که ۶۰٪ یا بیشتر بیت‌هاش قبلاً دیده شده حذف می‌شه.\n"
 "▪️ <b>تحلیل قافیه و ردیف:</b> برای هر شعر قافیه و ردیف تشخیص داده می‌شه. اگه ≥۷۵٪ بیت‌ها با قافیه جور باشن، بیت‌های بی‌قافیه دور ریخته می‌شن. غزل و قصیده‌ی بدون قافیه‌ی قابل‌تشخیص حذف می‌شه.\n"
 "▪️ <b>برچسب شاعر و قالب:</b> شاعر با کمتر از ۲۰ شعر به برچسب «ناشناس» و قالب با کمتر از ۳۰ شعر به «متفرقه» تبدیل می‌شه.\n"
 "▪️ <b>تقسیم آموزش/اعتبارسنجی:</b> بر اساس هشِ ثابتِ هر شعر (حدود ۱٪ برای اعتبارسنجی)؛ بنابراین هیچ شعری هم‌زمان در هر دو بخش نیست."),
("🔬 <b>بخش تخصصی ‹۲ از ۵›</b>\n<b>۲) توکنایزر و قالب دنباله</b>\n\n"
 "▪️ <b>توکنایزر:</b> BPE با اندازه‌ی واژگان ۱۶٬۰۰۰، آموزش‌دیده روی خودِ شعرها (فقط حروف فارسی + نیم‌فاصله). یک تست رفت‌وبرگشت (encode/decode) برای اطمینان از بدون‌اتلاف بودن اجرا می‌شه.\n\n"
 "▪️ <b>توکن‌های ویژه:</b> <code>&lt;|poem|&gt; &lt;|sep|&gt; &lt;|m|&gt; &lt;|n|&gt; &lt;|end|&gt; &lt;|rhy|&gt; &lt;|rad|&gt; &lt;|pad|&gt; &lt;|unk|&gt;</code>\n\n"
 "▪️ <b>قالب هر نمونه:</b>\n"
 "<code>&lt;|poem|&gt; شاعر &lt;|sep|&gt; قالب &lt;|rhy|&gt; قافیه &lt;|rad|&gt; ردیف &lt;|n|&gt; مصرع۱ &lt;|m|&gt; مصرع۲ &lt;|n|&gt; مصرع۱ &lt;|m|&gt; مصرع۲ &lt;|n|&gt; … &lt;|end|&gt;</code>\n\n"
 "▪️ <b>چرا این قالب؟</b> شاعر، قالب، قافیه و ردیف در ابتدای دنباله می‌آن؛ پس مدل از همون ابتدا «می‌دونه» چه شعری قراره بسازه، و ما هم موقع تولید می‌تونیم با گذاشتن این برچسب‌ها در پرامپت، سبک و قافیه رو کنترل کنیم (مثلاً <i>حافظ · غزلیات</i>).\n"
 "▪️ برچسب «ناشناس» یعنی «سبک نامشخص» و برای حالت ترکیب همه‌ی شاعرها استفاده می‌شه."),
("🔬 <b>بخش تخصصی ‹۳ از ۵›</b>\n<b>۳) معماری مدل</b>\n\n"
 "مدل <b>PoetGPT</b>؛ یک Transformer فقط‌دیکودر (decoder-only) به سبک LLaMA، با پیکربندی پیش‌فرض:\n\n"
 "▪️ بُعد پنهان: <b>۵۱۲</b> | لایه‌ها: <b>۱۲</b> | پنجره‌ی متن: <b>۵۱۲</b> توکن\n"
 "▪️ <b>توجه (Attention):</b> ۸ سر پرسش و ۴ سر کلید/مقدار → <b>GQA</b> (Grouped-Query Attention) با ابعاد هر سر ۶۴؛ یعنی حافظه‌ی KV نصفه می‌شه و تولید سریع‌تر.\n"
 "▪️ <b>RoPE:</b> کدگذاری موقعیتِ چرخشی (θ = ۱۰٬۰۰۰) به‌جای جدول موقعیت.\n"
 "▪️ <b>QK-Norm:</b> نرمال‌سازی RMS روی Q و K برای پایداری آموزش.\n"
 "▪️ <b>نرمال‌سازی:</b> RMSNorm به‌صورت Pre-Norm قبل از هر زیرلایه.\n"
 "▪️ <b>FFN:</b> SwiGLU با بُعد میانی ۱۴۰۸ (دروازه و بالا‌برنده در یک ماتریس ادغام شده‌اند).\n"
 "▪️ بدون بایاس در همه‌ی لایه‌های خطی؛ <b>وزن‌های امبدینگ و خروجی مشترک</b> (weight tying).\n"
 "▪️ مقداردهی اولیه N(0، 0.02) و ضرایب خروجیِ Attention/FFN با مقیاس ۰٫۰۲/√(۲L).\n"
 "▪️ Dropout بین ۰٫۰۵ تا ۰٫۱۵ (بسته به تعداد دوره‌های پیش‌بینی‌شده).\n"
 "▪️ <b>تعداد پارامترها:</b> حدود <b>۴۳٫۶ میلیون</b> (که ۸٫۲ میلیونش امبدینگ است).\n"
 "▪️ کرنل‌های سفارشیِ <b>Triton</b> برای RMSNorm، SwiGLU و Cross-Entropy ادغام‌شده (با بازگشت خودکار به PyTorch)."),
("🔬 <b>بخش تخصصی ‹۴ از ۵›</b>\n<b>۴) آموزش</b>\n\n"
 "▪️ <b>تابع هزینه:</b> Cross-Entropy برای پیش‌بینی توکن بعدی، با دو نکته:\n"
 "   • <b>وزن‌دهی قافیه:</b> سه توکنِ آخرِ هر بیت (درست قبل از &lt;|n|&gt;) و خودِ آن وزنِ دو برابر می‌گیرن؛ چون قافیه همون‌جا تعیین می‌شه.\n"
 "   • <b>z-loss</b> با ضریب ۱e-۴ برای جلوگیری از رشد بی‌رویه‌ی لوجیت‌ها.\n"
 "▪️ <b>بهینه‌ساز:</b> AdamW با β=(۰٫۹، ۰٫۹۵)، weight decay برابر ۰٫۱ (فقط روی ماتریس‌ها نه بایاس/نرم)، اجرای fused.\n"
 "▪️ <b>نرخ یادگیری:</b> اوج ۶e-۴، گرم‌کردن ۳۰۰ گام، سپس کاهش کسینوسی تا مقدار کم.\n"
 "▪️ <b>اندازه‌ی بچ:</b> حدود ۳۲٬۷۶۸ توکن در هر گام با تجمیع گرادیان (gradient accumulation)؛ اندازه‌ی میکروبچ خودکار با توجه به حافظه‌ی GPU کالیبره می‌شه.\n"
 "▪️ <b>دقت عددی:</b> bf16 (یا fp16 با GradScaler)، برش گرادیان روی ۱٫۰.\n"
 "▪️ <b>EMA:</b> میانگین متحرک نمایی وزن‌ها (ضریب ۰٫۹۹۹۵)؛ در هر ارزیابی، بهتر از دو حالت «وزن خام» و «EMA» ذخیره می‌شه.\n"
 "▪️ <b>زمان‌بندی:</b> برنامه‌ی نرخ یادگیری بر اساس ساعتِ تعیین‌شده برای آموزش پیش می‌ره، با توقف زودهنگام (early stopping) و ذخیره‌ی دوره‌ایِ چک‌پوینت.\n"
 "▪️ <b>ارزیابی:</b> loss اعتبارسنجی + <b>دقت قافیه</b> روی پرامپت‌های ثابت با seed ثابت (برای مقایسه‌ی عادلانه بین چک‌پوینت‌ها)."),
("🔬 <b>بخش تخصصی ‹۵ از ۵›</b>\n<b>۵) تولید شعر</b>\n\n"
 "▪️ <b>نمونه‌برداری:</b> temperature، top-k، top-p و جریمه‌ی تکرار (repetition penalty) روی ۹۶ توکن آخر. مقادیر هر سبک جداست (مثلاً حافظ: temp ۰٫۷، فردوسی/مثنوی: ۰٫۷۵).\n"
 "▪️ <b>قیدهای ساختاری:</b> توکن‌های ویژه فقط در جای درست مجازن؛ مصرع حداکثر ۴۰ توکن؛ شعر تا رسیدن به حداقل تعداد بیتِ سبک تموم نمی‌شه.\n"
 "▪️ <b>تأیید بیت‌به‌بیت + بازگشت (rollback):</b> بعد از هر بیت، قافیه/ردیف بررسی می‌شه؛ بیت خراب پاک و دوباره نمونه‌برداری می‌شه (تا ۸ بار). کلمه‌ی قافیه‌ی تکراری ممنوعه.\n"
 "▪️ <b>حالت Polish:</b> فقط واژه‌های واقعی (فرهنگ‌واژه‌ی ساخته‌شده از داده‌ی آموزش)، بیتِ اول (مطلع) در غزل/قصیده باید هم‌قافیه باشه، و تکرار کلمه‌ی محتوایی در یک مصرع ممنوعه.\n"
 "▪️ <b>حالت جفت‌قافیه (pair-rhyme):</b> برای مثنوی، فردوسی و ترکیبی (به انتخاب کاربر)؛ هر دو مصرعِ بیت باید با هم هم‌قافیه باشن.\n"
 "▪️ <b>انتخاب بهترین‌ها (Best-of-N):</b> چند کاندیدا ساخته می‌شه و با امتیاز <i>۲×دقت قافیه + تنوع واژگان − ۰٫۵×loss + اصلاح‌گر</i> رتبه‌بندی می‌شن (اصلاح‌گر: جریمه‌ی تکرار و کلمات ناشناخته، پاداش تخلص در بیت آخر غزل).\n"
 "▪️ <b>سرعت:</b> KV-cache + <b>CUDA Graph</b> برای رمزگشایی تک‌توکنی؛ خروجیِ مسیر سریع قبل از استفاده با مدل کامل مقایسه و تأیید می‌شه.\n\n"
 "💬 <b>هر سوالی داشتید به {contact} پیام بدید.</b> 🌷"),
],
"credit": ("💳 <b>درخواست کردیت</b>\n\n"
           "🪙 کردیت فعلی تو: <b>{credits}</b>  (هر شعر ساخته‌شده = ۱ کردیت)\n\n"
           "✅ <b>درخواستت ارسال شد!</b>\n"
           "بات به پی‌وی ادمین پیام داد و آیدی عددی تو رو بهش گفت:\n<code>{uid}</code>\n"
           "به‌محض بررسی، کردیت اضافه می‌شه و بات بهت خبر می‌ده 🎁\n\n"
           "اگه دیر شد، می‌تونی مستقیم به {contact} هم پیام بدی."),
"credit_wait": ("⏳ <b>درخواستت قبلاً ارسال شده.</b>\nچند دقیقه صبر کن تا ادمین بررسی کنه؛ بعد می‌تونی دوباره درخواست بدی.\n"
                "🪙 کردیت فعلی: <b>{credits}</b>\n\nمستقیم هم می‌تونی پیام بدی: {contact}"),
"credit_nofwd": ("💳 <b>درخواست کردیت</b>\n\n🪙 کردیت فعلی تو: <b>{credits}</b>\n\n"
                 "برای گرفتن کردیت به تلگرام من پیام بده 👉 {contact}\nو این آیدی رو بفرست:\n<code>{uid}</code>"),
"credit_denied": "🙏 درخواست کردیتت این بار تأیید نشد. اگه سوالی داری به {contact} پیام بده.",
"contact": ("📞 <b>تماس با ما</b>\n\n"
            "سوال، پیشنهاد، باگ یا کردیت؟ 💌\n"
            "آیدی تلگرام: {contact}\n\n"
            "خوشحال می‌شم نظرت رو بشنوم 🌷"),
"credit_added": "🎁 {n} کردیت بهت اضافه شد! موجودی جدید: <b>{total}</b> 🎉\nحالا می‌تونی شعر بسازی 📜",
},

"en": {
"choose_lang": "🌍 <b>زبان خودتو انتخاب کن</b>\nChoose your language 👇",
"menu": ("🌹 <b>Welcome to the Poem Maker!</b> 🌹\n\n"
         "An AI that writes Persian poetry — from Hafez and Ferdowsi to Molavi ✨\n"
         "💳 Your credits: <b>{credits}</b>\n\n"
         "Pick an option 👇"),
"b_poem": "📜 Make a poem", "b_about": "🤖 About the model", "b_credit": "💳 Request credit",
"b_contact": "📞 Contact us", "b_lang": "🌐 فارسی", "b_back": "🔙 Back", "b_menu": "🏠 Main menu",
"pick_poet": ("🎨 <b>Which style do you want?</b>\n\n"
              "🌹 Hafez — romantic & mystic ghazals\n"
              "⚔️ Ferdowsi — epic, Shahnameh-like\n"
              "📜 Molavi — masnavi only, Masnavi-e Ma'navi style\n"
              "🎭 Mix — all the poets, blended"),
"b_hafez": "🌹 Hafez", "b_ferdowsi": "⚔️ Ferdowsi", "b_masnavi": "📖 Masnavi", "b_mix": "🎭 Mix of all poets",
"ask_mixform": "🎭 <b>Mix of all poets!</b>\nWhat kind of poem do you want?",
"b_mf_gh": "🌹 Ghazals", "b_mf_ms": "📖 Masnavi", "b_mf_all": "🎲 Mixed (anything the model likes)",
"b_molavi": "📜 Molavi (Rumi)", "label_molavi": "Molavi",
"ask_story": "⚔️ <b>Ferdowsi it is!</b>\nWhich part of the Shahnameh?",
"b_fs": ["🎲 Any part (model picks)", "🛡 Rostam & Esfandiyar", "⚔️ Kay Khosrow's great war vs Afrasiyab", "👑 Khosrow Parviz",
         "🐗 Bahram Gur", "🏛 Alexander", "🏇 The Twelve Rukhs"],
"label_hafez": "Hafez", "label_ferdowsi": "Ferdowsi", "label_masnavi": "Masnavi", "label_mix": "Mix of all poets",
"ask_ghazal": "🌹 <b>Hafez it is!</b>\nShould the poem be a <b>ghazal</b>, or any form the model likes?",
"b_ghazal_yes": "✅ Yes, ghazal", "b_ghazal_no": "🔀 No, any form",
"ask_pair": ("📖 <b>{label} it is!</b>\nHow should the rhymes work?\n\n"
             "📏 <b>Only at the end of the couplet</b> — like a normal poem\n"
             "🔗 <b>At the end of every hemistich</b> — both halves of each couplet rhyme with each other"),
"b_pair_end": "📏 End of couplet only", "b_pair_each": "🔗 Every hemistich",
"ask_prompt": ("🎯 <b>How should the poem start?</b>\n\n"
               "✍️ <b>My own prompt</b> — you write the first hemistich\n"
               "🎲 <b>Random</b> — let the model start by itself\n\n"
               "⭐ <b>We recommend letting the model start by itself!</b> It usually gives better poems 😉"),
"b_prompt_own": "✍️ My own prompt", "b_prompt_rnd": "🎲 Random (recommended) ⭐",
"own_info": ("✍️ <b>Send me the first hemistich of your poem</b>\n\n"
             "💡 Keep it <b>short</b> (2–8 words) and use <b>old, classical words</b> like «dilā», «sāqi», «yār»… (in Persian script)\n\n"
             "⚠️ Honestly, we <b>don't recommend</b> this mode — random usually gives better poems 😉\n"
             "Persian letters only (no digits or Latin letters)."),
"prompt_bad": {
    "foreign_char": "🙈 Persian letters only! No digits or Latin letters.",
    "too_short": "🐣 That's too short! Make it a bit longer.",
    "one_word": "🐣 Write at least two words.",
    "too_long": "🐘 Too long! Send a shorter hemistich.",
    "too_many_words": "🐘 Too many words! 15 at most.",
    "char_run": "🤔 Too many repeated letters, try rephrasing.",
    "not_text": "📝 Please send text only."},
"prompt_ok": "👌 Great! The poem starts with: «<i>{first}</i>»",
"ask_make": ("🏭 <b>How many poems should I generate?</b> (up to 100)\n"
             "More poems = better picks, but longer waiting ⏳\n\n"
             "💳 Every generated poem costs 1 credit. Your credits: <b>{credits}</b>"),
"ask_top": ("🏆 <b>How many of the best should I show you?</b>\nI'll generate {make} and pick the best ones.\n"
            "💳 Cost: <b>{make}</b> credits"),
"b_cancel": "❌ Cancel",
"queued": "🚦 You're in the queue… position {pos}. Hang tight 🙏",
"cancelling": "🛑 Cancelling…",
"cancelled": "🛑 <b>Generation cancelled.</b>\nYour credits were fully refunded 💳",
"working": ("{spin} <b>Writing your poems…</b>\n\n"
            "🎭 Style: {label}\n⏱ Time: {sec}s\n🧪 Candidate: {c}/{n}\n\n"
            "Virtual poets are picking up their pens ✍️"),
"done": "🎉 <b>Your poems are ready!</b>  ({sec}s)",
"poem_n": "Poem", "qaf": "Qafiye", "rad": "Radif",
"after": "Liked it? Shall we do another round? 👇",
"b_again": "🔁 Again, same settings", "b_new": "🆕 New poem",
"failed": "😵 Oops! The model couldn't write a poem this time. Your credits are refunded, please try again 🙏",
"timeout": "⏰ It took too long so I stopped it. Credits refunded — try generating fewer poems 🙏",
"busy": "⏳ Your previous poem is still being written, hold on!",
"no_credit": "😢 <b>You're out of credits!</b>\n\nTap “💳 Request credit” to get more.",
"about": ("🤖 <b>About the model</b>\n\n"
          "This bot is connected to a <b>GPT built for Persian poetry</b>, trained from scratch 🧠\n\n"
          "📚 It learned from thousands of classical poems (Hafez, Ferdowsi, Masnavi and more) how meter, rhyme (qafiye) and radif fit together.\n"
          "🔎 For each request it writes several poems, checks rhymes, repetitions and made-up words, and shows you only the <b>best ones</b>.\n\n"
          "⚠️ The poems are <b>AI-generated</b>, not written by the real poets, and may sometimes be wrong or meaningless. This is an experimental project 🧪\n\n"
          "🔬 Tap “Technical section” for the full details 👇"),
"b_tech": "🔬 Technical section", "b_prev": "⬅️ Prev", "b_next": "Next ➡️", "b_about_back": "🤖 About the model",
"tech": [
("🔬 <b>Technical ‹1 of 5›</b>\n<b>1) Data & preprocessing</b>\n\n"
 "▪️ <b>Source:</b> the Ganjoor poetry archive (one JSON per poem). Poet, form (ghazal, masnavi, qasida…) and path come from the archive structure.\n"
 "▪️ <b>Text normalisation:</b> Arabic/Persian letter unification (ك→ک, ي→ی …), removal of diacritics, tatweel and invisible characters; only Persian letters and ZWNJ are allowed. Lines with digits or Latin letters are dropped.\n"
 "▪️ <b>Couplets:</b> each poem becomes (hemistich, hemistich) pairs; long poems are chunked into pieces of at most 12 couplets so they fit the 512-token window.\n"
 "▪️ <b>Deduplication:</b> exact and near-duplicates; a poem with ≥60% already-seen couplets is removed.\n"
 "▪️ <b>Rhyme analysis:</b> qafiye and radif are detected per poem. If ≥75% of couplets agree, the ones that break the rhyme are dropped. Ghazals/qasidas with no detectable rhyme are removed.\n"
 "▪️ <b>Tags:</b> poets with fewer than 20 poems become “unknown”, forms with fewer than 30 poems become “misc”.\n"
 "▪️ <b>Train/validation split:</b> by a fixed hash of each poem (~1% validation), so no poem is ever in both sets."),
("🔬 <b>Technical ‹2 of 5›</b>\n<b>2) Tokenizer & sequence format</b>\n\n"
 "▪️ <b>Tokenizer:</b> BPE, vocabulary 16,000, trained on the poems themselves (Persian letters + ZWNJ only). An encode/decode round-trip test checks it is lossless.\n\n"
 "▪️ <b>Special tokens:</b> <code>&lt;|poem|&gt; &lt;|sep|&gt; &lt;|m|&gt; &lt;|n|&gt; &lt;|end|&gt; &lt;|rhy|&gt; &lt;|rad|&gt; &lt;|pad|&gt; &lt;|unk|&gt;</code>\n\n"
 "▪️ <b>Sample layout:</b>\n"
 "<code>&lt;|poem|&gt; poet &lt;|sep|&gt; form &lt;|rhy|&gt; qafiye &lt;|rad|&gt; radif &lt;|n|&gt; hemistich1 &lt;|m|&gt; hemistich2 &lt;|n|&gt; hemistich1 &lt;|m|&gt; hemistich2 &lt;|n|&gt; … &lt;|end|&gt;</code>\n\n"
 "▪️ <b>Why this layout?</b> Poet, form, qafiye and radif come first, so the model knows from the start what it is writing — and at generation time we steer style and rhyme simply by writing these tags into the prompt (e.g. <i>Hafez · Ghazals</i>).\n"
 "▪️ The “unknown poet” tag means “unspecified style” and is what the mix-of-all-poets mode uses."),
("🔬 <b>Technical ‹3 of 5›</b>\n<b>3) Model architecture</b>\n\n"
 "<b>PoetGPT</b> — a LLaMA-style decoder-only Transformer, default configuration:\n\n"
 "▪️ Hidden size: <b>512</b> | layers: <b>12</b> | context: <b>512</b> tokens\n"
 "▪️ <b>Attention:</b> 8 query heads and 4 key/value heads → <b>GQA</b> (Grouped-Query Attention), head dim 64; the KV cache is halved and decoding is faster.\n"
 "▪️ <b>RoPE:</b> rotary position embeddings (θ = 10,000) instead of a learned position table.\n"
 "▪️ <b>QK-Norm:</b> RMS normalisation on Q and K for training stability.\n"
 "▪️ <b>Normalisation:</b> pre-norm RMSNorm before every sub-layer.\n"
 "▪️ <b>FFN:</b> SwiGLU with intermediate size 1408 (gate and up projections fused into one matrix).\n"
 "▪️ No biases in any linear layer; <b>input embedding and output head are tied</b> (weight tying).\n"
 "▪️ Init N(0, 0.02), with attention/FFN output projections scaled by 0.02/√(2L).\n"
 "▪️ Dropout 0.05–0.15 depending on the expected number of epochs.\n"
 "▪️ <b>Parameters:</b> about <b>43.6M</b> (8.2M of them embeddings).\n"
 "▪️ Custom <b>Triton</b> kernels for RMSNorm, SwiGLU and fused cross-entropy (with automatic PyTorch fallback)."),
("🔬 <b>Technical ‹4 of 5›</b>\n<b>4) Training</b>\n\n"
 "▪️ <b>Loss:</b> next-token cross-entropy with two extras:\n"
 "   • <b>Rhyme weighting:</b> the last three tokens of each couplet (right before &lt;|n|&gt;) and the &lt;|n|&gt; itself get 2× weight, since that is where the rhyme is decided.\n"
 "   • <b>z-loss</b> (1e-4) to keep logits from drifting.\n"
 "▪️ <b>Optimizer:</b> AdamW, β=(0.9, 0.95), weight decay 0.1 on matrices only (not on biases/norms), fused implementation.\n"
 "▪️ <b>Learning rate:</b> peak 6e-4, 300 warm-up steps, then cosine decay to a small floor.\n"
 "▪️ <b>Batch:</b> ~32,768 tokens per step via gradient accumulation; the micro-batch size is auto-calibrated to the GPU memory.\n"
 "▪️ <b>Precision:</b> bf16 (or fp16 with GradScaler), gradient clipping at 1.0.\n"
 "▪️ <b>EMA:</b> exponential moving average of weights (decay 0.9995); at each evaluation the better of “raw” and “EMA” is kept.\n"
 "▪️ <b>Schedule:</b> the LR schedule follows a time budget given in hours, with early stopping and periodic checkpoints.\n"
 "▪️ <b>Evaluation:</b> validation loss + <b>rhyme accuracy</b> on fixed prompts with fixed seeds, for fair checkpoint comparison."),
("🔬 <b>Technical ‹5 of 5›</b>\n<b>5) Poem generation</b>\n\n"
 "▪️ <b>Sampling:</b> temperature, top-k, top-p and a repetition penalty over the last 96 tokens. Each style has its own values (e.g. Hafez: temp 0.7, Ferdowsi/Masnavi: 0.75).\n"
 "▪️ <b>Structural constraints:</b> special tokens are only allowed where they make sense; a hemistich is at most 40 tokens; a poem cannot end before the style's minimum number of couplets.\n"
 "▪️ <b>Couplet-by-couplet verification + rollback:</b> after each couplet the rhyme/radif is checked; a bad couplet is deleted and re-sampled (up to 8 times). Reusing a rhyme word is forbidden.\n"
 "▪️ <b>Polish mode:</b> only real words (lexicon built from the training data), the opening couplet of a ghazal/qasida must rhyme, and repeating a content word inside one hemistich is forbidden.\n"
 "▪️ <b>Pair-rhyme mode:</b> for masnavi — both hemistichs of every couplet must rhyme with each other.\n"
 "▪️ <b>Best-of-N selection:</b> several candidates are generated and ranked by <i>2×rhyme accuracy + lexical diversity − 0.5×loss + adjustment</i> (adjustment: penalties for repeats and unknown words, bonus for a pen-name in the last couplet of a ghazal).\n"
 "▪️ <b>Speed:</b> KV-cache + <b>CUDA Graph</b> for single-token decoding; the fast path is verified against the full model before use.\n\n"
 "💬 <b>If you have any questions, message {contact}.</b> 🌷"),
],
"credit": ("💳 <b>Request credit</b>\n\n"
           "🪙 Your credits: <b>{credits}</b>  (each generated poem = 1 credit)\n\n"
           "✅ <b>Your request was sent!</b>\n"
           "The bot messaged the admin privately and told them your numeric ID:\n<code>{uid}</code>\n"
           "As soon as it is reviewed, credits are added and the bot will let you know 🎁\n\n"
           "If it takes long, you can also message {contact} directly."),
"credit_wait": ("⏳ <b>Your request was already sent.</b>\nPlease wait a few minutes for the admin to review it; then you can request again.\n"
                "🪙 Your credits: <b>{credits}</b>\n\nYou can also message directly: {contact}"),
"credit_nofwd": ("💳 <b>Request credit</b>\n\n🪙 Your credits: <b>{credits}</b>\n\n"
                 "To get credits, message me on Telegram 👉 {contact}\nand send this ID:\n<code>{uid}</code>"),
"credit_denied": "🙏 Your credit request wasn't approved this time. If you have questions, message {contact}.",
"contact": ("📞 <b>Contact us</b>\n\n"
            "Question, idea, bug or credit? 💌\n"
            "Telegram: {contact}\n\n"
            "I'd love to hear from you 🌷"),
"credit_added": "🎁 {n} credits were added! New balance: <b>{total}</b> 🎉\nYou can make poems now 📜",
},
}
