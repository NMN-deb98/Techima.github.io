# راه‌اندازی امن دیدگاه‌های تکیما

## معماری و حریم خصوصی
- فرم سایت از Cloudflare Worker درخواست می‌فرستد.
- Worker ایمیل و اطلاعات کامل را فقط در مخزن **خصوصی** `NMN-deb98/techima-private-feedback` ذخیره می‌کند.
- فایل `comments.json` در مخزن عمومی سایت فقط شامل `id`، `name`، `message` و `createdAt` است.
- توکن GitHub هرگز در HTML یا JavaScript سایت قرار نمی‌گیرد.

## پیش‌نیازهایی که باید یک بار انجام بدهی

### 1. ساخت مخزن خصوصی
در GitHub وارد حساب خودت شو و مخزنی با نام دقیق `techima-private-feedback` بساز. حتماً **Private** را انتخاب کن. GitHub Pages برای آن لازم نیست.

### 2. ساخت توکن محدود GitHub
یک Fine-grained personal access token بساز که فقط به این دو مخزن دسترسی داشته باشد:
- `NMN-deb98/Techima.github.io`
- `NMN-deb98/techima-private-feedback`

مجوز **Contents: Read and write** را بده. مجوزهای دیگر یا دسترسی به مخزن‌های دیگر لازم نیست. توکن را در سایت یا فایل‌های مخزن قرار نده.

### 3. انتشار Worker در Cloudflare
در داشبورد Cloudflare، بخش **Workers & Pages** یک Worker جدید بساز. محتوای فایل `backend/worker.js` را در ویرایشگر Worker قرار بده و Deploy کن. سپس در Settings → Variables and Secrets این مقادیر را ثبت کن:
- **Secret** `GITHUB_TOKEN`: توکن مرحلهٔ قبل
- **Variable** `PUBLIC_REPO`: `NMN-deb98/Techima.github.io`
- **Variable** `PRIVATE_REPO`: `NMN-deb98/techima-private-feedback`
- **Variable** `ALLOWED_ORIGIN`: `https://nmn-deb98.github.io`

پس از ذخیرهٔ مقادیر، Worker را دوباره Deploy کن. آدرس آن معمولاً شبیه `https://نام-انتخابی.حساب.workers.dev` است.

### 4. وصل کردن سایت به Worker
در فایل `assets/js/comments.js` مقدار `API_BASE` را به آدرس واقعی Worker تغییر بده؛ فقط دامنه را وارد کن، بدون `/comments`. مثال:
```js
var API_BASE = "https://نام-انتخابی.حساب.workers.dev";
```
این فایل را Commit کن تا سایت به‌روز شود.

## آزمایش
1. آدرس Worker را در مرورگر باز کن و انتهایش `/comments` بگذار. باید JSON با فهرست پیام‌ها برگردد.
2. از سایت یک پیام آزمایشی با ایمیل خودت بفرست.
3. بررسی کن که نام و متن در سایت و فایل عمومی `comments.json` دیده شوند.
4. در مخزن **خصوصی** `techima-private-feedback` مسیر `submissions/YYYY-MM/` را باز کن و مطمئن شو ایمیل فقط همان‌جا ثبت شده است.

## نکات امنیتی
- دیدگاه‌های ثبت‌شده در سایت عمومی هستند؛ فقط ایمیل خصوصی است.
- متن دیدگاه با `textContent` نمایش داده می‌شود تا HTML یا اسکریپت ارسالی اجرا نشود.
- فرم محدودیت طول، اعتبارسنجی سمت سرور، بررسی Origin و فیلد ضدربات دارد.
- برای مقابله قوی‌تر با هرزنامه و محدودکردن نرخ ارسال، Cloudflare Turnstile و rate limiting را نیز فعال کن.
- ایمیل‌ها در مخزن خصوصی در تاریخچه Git باقی می‌مانند؛ حذف فایل لزوماً تاریخچه را پاک نمی‌کند.
- تا وقتی Worker منتشر و `API_BASE` تنظیم نشده باشد، فرم عمداً ارسال را غیرفعال نشان می‌دهد.
