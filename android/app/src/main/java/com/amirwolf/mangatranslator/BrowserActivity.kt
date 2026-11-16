package com.amirwolf.mangatranslator

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.webkit.CookieManager
import android.webkit.JsResult
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray

/**
 * v1.14.322 — مرورگرِ داخلی برای سایت‌هایی که کپچا دارند.
 * کاربر خودش وارد سایتِ مانهوا میشود (کپچا را رد میکند)، فصل را باز
 * میکند و با دکمهٔ «🖼 استخراج عکس» لینکِ همهٔ عکس‌های صفحه را
 * میگیرد و به فرمِ ورودیِ برنامه برمی‌گرداند.
 */
class BrowserActivity : Activity() {

    companion object {
        const val EXTRA_URL = "url"
        const val EXTRA_LINKS = "links"

        /** همان فیلترهای نشانکِ وب — img/source + لودِ تنبل + حذفِ آیکون‌ها */
        private const val EXTRACT_JS = """
(function(){
  var seen={},out=[];
  function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}}
  function junk(u){
    if(!u)return 1;
    if(u.indexOf('data:')===0)return 1;
    if(!/^https?:/i.test(u))return 1;
    if(/\.(svg|ico)([?#]|$)/i.test(u))return 1;
    if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|ads?[._-]|button|emoji|thumb(nail)?s?[._-])/i.test(u))return 1;
    return 0}
  var els=document.querySelectorAll('img,source');
  for(var i=0;i<els.length;i++){
    var el=els[i],cs=null;
    try{cs=el.currentSrc||el.src||null}catch(e){}
    var c=[cs,el.getAttribute('data-src'),el.getAttribute('data-lazy-src'),
           el.getAttribute('data-original'),el.getAttribute('data-echo')];
    var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');
    if(ss){var p=ss.split(',');
      if(p.length)c.push(p[p.length-1].trim().split(/\s+/)[0])}
    if(el.tagName==='SOURCE'&&el.parentNode){
      var pp=el.parentNode.querySelector('img');
      if(pp&&pp.src)c.push(pp.src)}
    for(var j=0;j<c.length;j++){
      var u=c[j];if(!u)continue;
      u=abs(String(u).trim());
      if(!u||junk(u)||seen[u])continue;
      var w=el.naturalWidth||el.width||0,h=el.naturalHeight||el.height||0;
      if(w&&h&&(w<120||h<120))continue;
      seen[u]=1;out.push(u);break}}
  function nk(s){var t=String(s).split(/[^0-9]+/).filter(Boolean),r=[];
    for(var i=0;i<t.length;i++)r.push(parseInt(t[i],10));return r}
  out.sort(function(a,b){var x=nk(a),y=nk(b);
    for(var i=0;i<Math.min(x.length,y.length);i++){
      if(x[i]!==y[i])return x[i]-y[i]}return a<b?-1:1});
  return JSON.stringify(out);
})()
"""
    }

    private val BG = Color.parseColor("#060607")
    private val CARD = Color.parseColor("#0d0d10")
    private val LINE = Color.parseColor("#1f1f24")
    private val TXT = Color.parseColor("#e8e6e1")
    private val MUT = Color.parseColor("#97948c")
    private val ACC = Color.parseColor("#ff4a3d")

    private lateinit var web: WebView
    private lateinit var urlBox: EditText
    private lateinit var extractBtn: TextView
    private lateinit var countLbl: TextView
    private lateinit var progress: ProgressBar

    private var lastCount = 0

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(BG)
        }

        // ——— نوارِ بالا: آدرس + بستن ———
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(CARD)
            setPadding(12, 10, 12, 10)
        }
        val closeBtn = TextView(this).apply {
            text = "✕"
            setTextColor(TXT)
            textSize = 16f
            setPadding(14, 8, 14, 8)
            setOnClickListener { finish() }
        }
        urlBox = EditText(this).apply {
            setTextColor(TXT)
            setHintTextColor(MUT)
            hint = "آدرس سایت مانهوا…"
            textSize = 13f
            setSingleLine(true)
            imeOptions = EditorInfo.IME_ACTION_GO
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#15151a"))
                cornerRadius = 22f
                setStroke(1, LINE)
            }
            setPadding(20, 16, 20, 16)
            setOnEditorActionListener { _, action, _ ->
                if (action == EditorInfo.IME_ACTION_GO) {
                    goUrl(); true
                } else false
            }
        }
        val goBtn = TextView(this).apply {
            text = "برو"
            setTextColor(Color.WHITE)
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(18, 10, 18, 10)
            background = GradientDrawable().apply {
                setColor(ACC)
                cornerRadius = 18f
            }
            setOnClickListener { goUrl() }
        }
        top.addView(closeBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        top.addView(urlBox, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
            marginStart = 6; marginEnd = 6
        })
        top.addView(goBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(top, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))

        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 0
            progressTint = ACC
        }
        root.addView(progress, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, dp(3)))

        // ——— وب‌ویو ———
        web = WebView(this)
        setupWebView()
        root.addView(web, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))

        // ——— نوارِ پایین: استخراج ———
        val bottom = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(CARD)
            setPadding(12, 10, 12, 10)
        }
        countLbl = TextView(this).apply {
            text = "عکسی پیدا نشده — اول فصل را باز کن"
            setTextColor(MUT)
            textSize = 12f
            setPadding(4, 0, 4, 0)
        }
        extractBtn = TextView(this).apply {
            text = "🖼 استخراج عکس"
            setTextColor(Color.WHITE)
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setPadding(22, 14, 22, 14)
            background = GradientDrawable().apply {
                setColor(ACC)
                cornerRadius = 24f
            }
            setOnClickListener { extractImages() }
        }
        bottom.addView(countLbl, LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        bottom.addView(extractBtn, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(bottom, LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT))

        setContentView(root)

        val startUrl = (intent?.getStringExtra(EXTRA_URL) ?: "").trim()
        if (startUrl.startsWith("http")) {
            urlBox.setText(startUrl)
            web.loadUrl(startUrl)
            recountAsync()
        } else {
            web.loadUrl("about:blank")
            urlBox.requestFocus()
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = true
            displayZoomControls = false
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            userAgentString =
                "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/120.0.0.0 Mobile Safari/537.36"
        }
        try {
            CookieManager.getInstance().apply {
                setAcceptCookie(true)
                if (Build.VERSION.SDK_INT >= 21) setAcceptThirdPartyCookies(web, true)
            }
        } catch (_: Exception) {}
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?, request: WebResourceRequest?): Boolean {
                return false
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                try { urlBox.setText(url ?: "") } catch (_: Exception) {}
                recountAsync()
            }
        }
        web.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility =
                    if (newProgress >= 100) View.GONE else View.VISIBLE
            }

            override fun onJsAlert(
                view: WebView?, url: String?, message: String?,
                result: JsResult): Boolean {
                try {
                    Toast.makeText(this@BrowserActivity,
                        message ?: "", Toast.LENGTH_SHORT).show()
                } catch (_: Exception) {}
                result.confirm()
                return true
            }
        }
    }

    private fun goUrl() {
        var u = urlBox.text.toString().trim()
        if (u.isEmpty()) return
        if (!u.startsWith("http://") && !u.startsWith("https://")) u = "https://$u"
        urlBox.setText(u)
        web.loadUrl(u)
    }

    /** شمارشِ زندهٔ عکسهای صفحه (بدون برگرداندنِ نتیجه) */
    private fun recountAsync() {
        try {
            web.evaluateJavascript(EXTRACT_JS) { raw ->
                try {
                    val n = JSONArray(raw ?: "[]").length()
                    runOnUiThread {
                        lastCount = n
                        countLbl.text = if (n > 0) {
                            "$n عکس آماده استخراج"
                        } else {
                            "عکسی پیدا نشده — اول فصل را باز کن"
                        }
                    }
                } catch (_: Exception) {}
            }
        } catch (_: Exception) {}
    }

    private fun extractImages() {
        val cur = try { web.url ?: "" } catch (_: Exception) { "" }
        if (cur.isEmpty() || cur == "about:blank") {
            Toast.makeText(this, "اول یک سایت را باز کن",
                Toast.LENGTH_SHORT).show()
            return
        }
        extractBtn.text = "… در حال استخراج"
        try {
            web.evaluateJavascript(EXTRACT_JS) { raw ->
                runOnUiThread {
                    extractBtn.text = "🖼 استخراج عکس"
                    try {
                        val arr = JSONArray(raw ?: "[]")
                        if (arr.length() == 0) {
                            countLbl.text = "عکسی پیدا نشد — تا آخرِ صفحه اسکرول کن"
                            Toast.makeText(this,
                                "هیچ عکسی پیدا نشد — تا آخرِ صفحه اسکرول کن " +
                                "تا عکس‌های تنبل لود بشن",
                                Toast.LENGTH_LONG).show()
                            return@runOnUiThread
                        }
                        val links = StringBuilder()
                        for (i in 0 until arr.length()) {
                            if (i > 0) links.append('\n')
                            links.append(arr.getString(i))
                        }
                        val out = Intent()
                        out.putExtra(EXTRA_LINKS, links.toString())
                        setResult(RESULT_OK, out)
                        Toast.makeText(this,
                            "✅ ${arr.length()} لینک عکس گرفته شد",
                            Toast.LENGTH_SHORT).show()
                        finish()
                    } catch (e: Exception) {
                        Toast.makeText(this,
                            "خطا در استخراج: ${e.message}",
                            Toast.LENGTH_LONG).show()
                    }
                }
            }
        } catch (e: Exception) {
            extractBtn.text = "🖼 استخراج عکس"
            Toast.makeText(this, "خطا: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        try {
            if (web.canGoBack()) web.goBack() else finish()
        } catch (_: Exception) {
            finish()
        }
    }

    override fun onDestroy() {
        try { web.destroy() } catch (_: Exception) {}
        super.onDestroy()
    }

    private fun dp(v: Int): Int =
        (v * resources.displayMetrics.density + 0.5f).toInt()
}
