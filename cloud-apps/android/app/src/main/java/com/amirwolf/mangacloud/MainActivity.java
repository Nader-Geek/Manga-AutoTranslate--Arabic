package com.amirwolf.mangacloud;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

public class MainActivity extends Activity {

    private static final String HOME_URL =
            "https://amirwolf512-manga-autotranslate.hf.space/";

    private WebView web;
    private LinearLayout splash;
    private ValueCallback<Uri[]> filePathCallback;
    private static final int FILE_CHOOSER_CODE = 1001;
    private boolean pageStarted = false;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0b0e14"));

        web = new WebView(this);
        root.addView(web, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        splash = buildSplash();
        root.addView(splash, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));

        setContentView(root);
        setupWebView();

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl(HOME_URL);
        }
    }

    private LinearLayout buildSplash() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER);
        box.setBackgroundColor(Color.parseColor("#0b0e14"));

        ProgressBar bar = new ProgressBar(this);
        box.addView(bar);

        TextView txt = new TextView(this);
        txt.setText("در حال اتصال به سرور…");
        txt.setTextColor(Color.parseColor("#c8ceda"));
        txt.setTextSize(15);
        txt.setPadding(0, 24, 0, 0);
        box.addView(txt);
        return box;
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void setupWebView() {
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            try {
                s.setForceDark(WebSettings.FORCE_DARK_OFF);
            } catch (Exception ignored) {
            }
        }

        CookieManager cm = CookieManager.getInstance();
        cm.setAcceptCookie(true);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            cm.setAcceptThirdPartyCookies(web, true);
        }

        web.setBackgroundColor(Color.parseColor("#0b0e14"));
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri u = request.getUrl();
                String scheme = u.getScheme() == null ? "" : u.getScheme();
                if (scheme.equals("http") || scheme.equals("https")) {
                    String host = u.getHost() == null ? "" : u.getHost();
                    if (host.contains("hf.space") || host.contains("huggingface.co")
                            || host.contains("gradio.app")) {
                        return false;
                    }
                    openExternal(u);
                    return true;
                }
                if (scheme.equals("mailto") || scheme.equals("tel")
                        || scheme.equals("intent")) {
                    openExternal(u);
                    return true;
                }
                return false;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                pageStarted = true;
                splash.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                splash.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                if (request.isForMainFrame()) {
                    showOfflinePage();
                }
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view,
                                             ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = callback;
                try {
                    Intent intent = params.createIntent();
                    startActivityForResult(intent, FILE_CHOOSER_CODE);
                } catch (ActivityNotFoundException e) {
                    filePathCallback = null;
                    return false;
                }
                return true;
            }
        });

        web.setDownloadListener(new DownloadListener() {
            @Override
            public void onDownloadStart(String url, String userAgent,
                                        String contentDisposition,
                                        String mimetype, long contentLength) {
                if (url.startsWith("data:")) {
                    saveDataUrl(url);
                    return;
                }
                try {
                    DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                    req.setMimeType(mimetype);
                    String cookies = CookieManager.getInstance().getCookie(url);
                    if (cookies != null) {
                        req.addRequestHeader("cookie", cookies);
                    }
                    req.addRequestHeader("User-Agent", userAgent);
                    req.setNotificationVisibility(
                            DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    req.setDestinationInExternalPublicDir(
                            Environment.DIRECTORY_DOWNLOADS,
                            fileNameFrom(contentDisposition, url));
                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    dm.enqueue(req);
                } catch (Exception ignored) {
                    openExternal(Uri.parse(url));
                }
            }
        });
    }

    private String fileNameFrom(String contentDisposition, String url) {
        try {
            if (contentDisposition != null) {
                String mark = "filename=";
                int i = contentDisposition.indexOf(mark);
                if (i >= 0) {
                    String nm = contentDisposition.substring(i + mark.length())
                            .replace("\"", "").replace(";", "").trim();
                    if (nm.length() > 0) return nm;
                }
            }
            String path = Uri.parse(url).getLastPathSegment();
            if (path != null && path.contains(".")) return path;
        } catch (Exception ignored) {
        }
        return "manga_download";
    }

    private void saveDataUrl(String dataUrl) {
        try {
            String[] parts = dataUrl.split(",", 2);
            if (parts.length < 2) return;
            String meta = parts[0];
            String name = "manga_download";
            if (meta.contains("name=")) {
                name = meta.substring(meta.indexOf("name=") + 5);
            }
            java.io.File dir = Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS);
            if (!dir.exists()) dir.mkdirs();
            boolean b64 = meta.contains(";base64");
            java.io.File out = new java.io.File(dir, name);
            java.io.FileOutputStream fos = new java.io.FileOutputStream(out);
            if (b64) {
                fos.write(android.util.Base64.decode(parts[1],
                        android.util.Base64.DEFAULT));
            } else {
                fos.write(android.net.Uri.decode(parts[1]).getBytes("UTF-8"));
            }
            fos.close();
        } catch (Exception ignored) {
        }
    }

    private void openExternal(Uri u) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (Exception ignored) {
        }
    }

    private void showOfflinePage() {
        String html = "<html><head><meta name=\"viewport\" content=\"width=device-width,"
                + "initial-scale=1\"><style>body{background:#0b0e14;color:#c8ceda;"
                + "font-family:sans-serif;display:flex;flex-direction:column;"
                + "align-items:center;justify-content:center;height:100vh;"
                + "margin:0;text-align:center}button{margin-top:24px;"
                + "background:#2563eb;color:#fff;border:0;border-radius:12px;"
                + "padding:14px 44px;font-size:17px}</style></head><body>"
                + "<h2>اتصال برقرار نشد</h2>"
                + "<p>سرور در دسترس نیست یا اینترنت قطع است.</p>"
                + "<p>هر ۱۰ ثانیه خودکار دوباره تلاش می‌شود.</p>"
                + "<button onclick=\"location.href='"
                + HOME_URL + "'\">تلاش دوباره</button>"
                + "<script>setTimeout(function(){location.href='"
                + HOME_URL + "';},10000);</script>"
                + "</body></html>";
        web.loadDataWithBaseURL(HOME_URL, html, "text/html", "UTF-8", null);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_CODE && filePathCallback != null) {
            Uri[] results = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                results = new Uri[]{data.getData()};
            } else if (resultCode == RESULT_OK && data != null && data.getClipData() != null) {
                int n = data.getClipData().getItemCount();
                results = new Uri[n];
                for (int i = 0; i < n; i++) {
                    results[i] = data.getClipData().getItemAt(i).getUri();
                }
            }
            filePathCallback.onReceiveValue(results);
            filePathCallback = null;
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        try {
            web.onPause();
            CookieManager.getInstance().flush();
        } catch (Exception ignored) {
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        try {
            web.onResume();
        } catch (Exception ignored) {
        }
        if (!pageStarted) {
            web.loadUrl(HOME_URL);
        }
    }
}
