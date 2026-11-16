package com.amirwolf.mangacloud;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.JsResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;

/**
 * v1.14.322 — مرورگرِ داخلیِ اپِ کلود برای سایت‌هایی که کپچا دارند.
 * کاربر خودش وارد سایتِ مانهوا میشود، کپچا را رد میکند و با
 * «🖼 استخراج عکس» لینکِ عکس‌ها را به صفحهٔ اصلی (فیلدِ ورودیِ
 * وب‌اپ) برمی‌گرداند.
 */
public class BrowserActivity extends Activity {

    public static final String EXTRA_URL = "url";
    public static final String EXTRA_LINKS = "links";

    /** همان فیلترهای نشانکِ وب — img/source + لودِ تنبل + حذفِ آیکون‌ها */
    private static final String EXTRACT_JS =
        "(function(){" +
        "var seen={},out=[];" +
        "function abs(u){try{var a=document.createElement('a');a.href=u;return a.href}catch(e){return null}}" +
        "function junk(u){" +
        "if(!u)return 1;" +
        "if(u.indexOf('data:')===0)return 1;" +
        "if(!/^https?:/i.test(u))return 1;" +
        "if(/\\.(svg|ico)([?#]|$)/i.test(u))return 1;" +
        "if(/(logo|icon|avatar|banner|sprite|favicon|badge|flag|ads?[._-]|button|emoji|thumb(nail)?s?[._-])/i.test(u))return 1;" +
        "return 0}" +
        "var els=document.querySelectorAll('img,source');" +
        "for(var i=0;i<els.length;i++){" +
        "var el=els[i],cs=null;" +
        "try{cs=el.currentSrc||el.src||null}catch(e){}" +
        "var c=[cs,el.getAttribute('data-src'),el.getAttribute('data-lazy-src')," +
        "el.getAttribute('data-original'),el.getAttribute('data-echo')];" +
        "var ss=el.getAttribute('srcset')||el.getAttribute('data-srcset');" +
        "if(ss){var p=ss.split(',');" +
        "if(p.length)c.push(p[p.length-1].trim().split(/\\s+/)[0])}" +
        "if(el.tagName==='SOURCE'&&el.parentNode){" +
        "var pp=el.parentNode.querySelector('img');" +
        "if(pp&&pp.src)c.push(pp.src)}" +
        "for(var j=0;j<c.length;j++){" +
        "var u=c[j];if(!u)continue;" +
        "u=abs(String(u).trim());" +
        "if(!u||junk(u)||seen[u])continue;" +
        "var w=el.naturalWidth||el.width||0,h=el.naturalHeight||el.height||0;" +
        "if(w&&h&&(w<120||h<120))continue;" +
        "seen[u]=1;out.push(u);break}}" +
        "function nk(s){var t=String(s).split(/[^0-9]+/).filter(Boolean),r=[];" +
        "for(var i=0;i<t.length;i++)r.push(parseInt(t[i],10));return r}" +
        "out.sort(function(a,b){var x=nk(a),y=nk(b);" +
        "for(var i=0;i<Math.min(x.length,y.length);i++){" +
        "if(x[i]!==y[i])return x[i]-y[i]}return a<b?-1:1});" +
        "return JSON.stringify(out);" +
        "})()";

    private WebView web;
    private EditText urlBox;
    private TextView extractBtn;
    private TextView countLbl;
    private ProgressBar progress;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#0b0e14"));

        // ——— نوارِ بالا: آدرس + بستن ———
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setBackgroundColor(Color.parseColor("#10131b"));
        top.setPadding(dp(10), dp(8), dp(10), dp(8));

        TextView closeBtn = new TextView(this);
        closeBtn.setText("✕");
        closeBtn.setTextColor(Color.parseColor("#c8ceda"));
        closeBtn.setTextSize(16);
        closeBtn.setPadding(dp(12), dp(6), dp(12), dp(6));
        closeBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { finish(); }
        });

        urlBox = new EditText(this);
        urlBox.setTextColor(Color.parseColor("#e7ebf3"));
        urlBox.setHintTextColor(Color.parseColor("#67718a"));
        urlBox.setHint("آدرس سایت مانهوا…");
        urlBox.setTextSize(13);
        urlBox.setSingleLine(true);
        urlBox.setImeOptions(EditorInfo.IME_ACTION_GO);
        GradientDrawable urlBg = new GradientDrawable();
        urlBg.setColor(Color.parseColor("#1a1f2b"));
        urlBg.setCornerRadius(dp(20));
        urlBg.setStroke(1, Color.parseColor("#273043"));
        urlBox.setBackground(urlBg);
        urlBox.setPadding(dp(16), dp(12), dp(16), dp(12));
        urlBox.setOnEditorActionListener((v, action, ev) -> {
            if (action == EditorInfo.IME_ACTION_GO) { goUrl(); return true; }
            return false;
        });

        TextView goBtn = new TextView(this);
        goBtn.setText("برو");
        goBtn.setTextColor(Color.WHITE);
        goBtn.setTextSize(13);
        goBtn.setTypeface(Typeface.DEFAULT_BOLD);
        goBtn.setPadding(dp(16), dp(8), dp(16), dp(8));
        GradientDrawable goBg = new GradientDrawable();
        goBg.setColor(Color.parseColor("#e8590c"));
        goBg.setCornerRadius(dp(16));
        goBtn.setBackground(goBg);
        goBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { goUrl(); }
        });

        top.addView(closeBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        LinearLayout.LayoutParams urlLp = new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        urlLp.setMargins(dp(6), 0, dp(6), 0);
        top.addView(urlBox, urlLp);
        top.addView(goBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(top, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        progress = new ProgressBar(this, null,
                android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setProgress(0);
        try { progress.setProgressTint(Color.parseColor("#e8590c")); } catch (Exception ignored) {}
        root.addView(progress, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(3)));

        // ——— وب‌ویو ———
        web = new WebView(this);
        setupWebView();
        root.addView(web, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        // ——— نوارِ پایین: استخراج ———
        LinearLayout bottom = new LinearLayout(this);
        bottom.setOrientation(LinearLayout.HORIZONTAL);
        bottom.setGravity(Gravity.CENTER_VERTICAL);
        bottom.setBackgroundColor(Color.parseColor("#10131b"));
        bottom.setPadding(dp(10), dp(8), dp(10), dp(8));

        countLbl = new TextView(this);
        countLbl.setText("عکسی پیدا نشده — اول فصل را باز کن");
        countLbl.setTextColor(Color.parseColor("#8a93a8"));
        countLbl.setTextSize(12);
        countLbl.setPadding(dp(4), 0, dp(4), 0);

        extractBtn = new TextView(this);
        extractBtn.setText("🖼 استخراج عکس");
        extractBtn.setTextColor(Color.WHITE);
        extractBtn.setTextSize(14);
        extractBtn.setTypeface(Typeface.DEFAULT_BOLD);
        extractBtn.setPadding(dp(20), dp(12), dp(20), dp(12));
        GradientDrawable exBg = new GradientDrawable();
        exBg.setColor(Color.parseColor("#e8590c"));
        exBg.setCornerRadius(dp(22));
        extractBtn.setBackground(exBg);
        extractBtn.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { extractImages(); }
        });

        bottom.addView(countLbl, new LinearLayout.LayoutParams(
                0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        bottom.addView(extractBtn, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(bottom, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));

        setContentView(root);

        String startUrl = getIntent() != null && getIntent().getStringExtra(EXTRA_URL) != null
                ? getIntent().getStringExtra(EXTRA_URL).trim() : "";
        if (startUrl.startsWith("http")) {
            urlBox.setText(startUrl);
            web.loadUrl(startUrl);
            recountAsync();
        } else {
            web.loadUrl("about:blank");
            urlBox.requestFocus();
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(true);
        s.setDisplayZoomControls(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        }
        s.setUserAgentString(
                "Mozilla/5.0 (Linux; Android 10; Pixel 7) " +
                "AppleWebKit/537.36 (KHTML, like Gecko) " +
                "Chrome/120.0.0.0 Mobile Safari/537.36");
        try {
            CookieManager cm = CookieManager.getInstance();
            cm.setAcceptCookie(true);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                cm.setAcceptThirdPartyCookies(web, true);
            }
        } catch (Exception ignored) {}

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                try { urlBox.setText(url != null ? url : ""); } catch (Exception ignored) {}
                recountAsync();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progress.setProgress(newProgress);
                progress.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public boolean onJsAlert(WebView view, String url, String message,
                                     JsResult result) {
                try {
                    Toast.makeText(BrowserActivity.this,
                            message != null ? message : "", Toast.LENGTH_SHORT).show();
                } catch (Exception ignored) {}
                result.confirm();
                return true;
            }
        });
    }

    private void goUrl() {
        String u = urlBox.getText().toString().trim();
        if (u.isEmpty()) return;
        if (!u.startsWith("http://") && !u.startsWith("https://")) u = "https://" + u;
        urlBox.setText(u);
        web.loadUrl(u);
    }

    /** شمارشِ زندهٔ عکسهای صفحه */
    private void recountAsync() {
        try {
            web.evaluateJavascript(EXTRACT_JS, value -> {
                try {
                    final int n = new JSONArray(value != null ? value : "[]").length();
                    runOnUiThread(() -> countLbl.setText(n > 0
                            ? n + " عکس آماده استخراج"
                            : "عکسی پیدا نشده — اول فصل را باز کن"));
                } catch (Exception ignored) {}
            });
        } catch (Exception ignored) {}
    }

    private void extractImages() {
        String cur;
        try { cur = web.getUrl() != null ? web.getUrl() : ""; }
        catch (Exception e) { cur = ""; }
        if (cur.isEmpty() || cur.equals("about:blank")) {
            Toast.makeText(this, "اول یک سایت را باز کن",
                    Toast.LENGTH_SHORT).show();
            return;
        }
        extractBtn.setText("… در حال استخراج");
        try {
            web.evaluateJavascript(EXTRACT_JS, value -> runOnUiThread(() -> {
                extractBtn.setText("🖼 استخراج عکس");
                try {
                    JSONArray arr = new JSONArray(value != null ? value : "[]");
                    if (arr.length() == 0) {
                        countLbl.setText("عکسی پیدا نشد — تا آخرِ صفحه اسکرول کن");
                        Toast.makeText(BrowserActivity.this,
                                "هیچ عکسی پیدا نشد — تا آخرِ صفحه اسکرول کن " +
                                "تا عکس‌های تنبل لود بشن",
                                Toast.LENGTH_LONG).show();
                        return;
                    }
                    StringBuilder links = new StringBuilder();
                    for (int i = 0; i < arr.length(); i++) {
                        if (i > 0) links.append('\n');
                        links.append(arr.getString(i));
                    }
                    Intent out = new Intent();
                    out.putExtra(EXTRA_LINKS, links.toString());
                    setResult(RESULT_OK, out);
                    Toast.makeText(BrowserActivity.this,
                            "✅ " + arr.length() + " لینک عکس گرفته شد",
                            Toast.LENGTH_SHORT).show();
                    finish();
                } catch (final Exception e) {
                    Toast.makeText(BrowserActivity.this,
                            "خطا در استخراج: " + e.getMessage(),
                            Toast.LENGTH_LONG).show();
                }
            }));
        } catch (Exception e) {
            extractBtn.setText("🖼 استخراج عکس");
            Toast.makeText(this, "خطا: " + e.getMessage(),
                    Toast.LENGTH_LONG).show();
        }
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        try {
            if (web.canGoBack()) web.goBack(); else finish();
        } catch (Exception e) {
            finish();
        }
    }

    @Override
    protected void onDestroy() {
        try { web.destroy(); } catch (Exception ignored) {}
        super.onDestroy();
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }
}
