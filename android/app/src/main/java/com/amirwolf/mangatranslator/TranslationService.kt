package com.amirwolf.mangatranslator

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

// v1.14.150/151 — سرویسِ پیشزمینهٔ ترجمه: تا وقتی کاری در جریان است، اپ را
// از فریزِ «پردازهٔ انبارشده» (cached-app freezer، اندروید ۱۱+) در امان
// نگه میدارد و اعلانِ «در حال ترجمه» با پیشرفت (صفحهٔ N از M + فاز) نشان
// میدهد. کنترل از MainActivity: شروع با acquireKeepAwake (شروعِ کار)،
// توقف با releaseKeepAwake (پایانِ کار).
// v1.14.151 — رفتارِ بستن: کاربر اپ را از recentها ببندد → onTaskRemoved
// اعلان را کامل برمیدارد و سرویس میایستد (START_NOT_STICKY → هیچوقت
// خودش بالا نمیآید و اعلانِ زامبی نمیگذارد).
class TranslationService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        current = this
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        try {
            goForeground()
        } catch (_: Exception) {
            try {
                stopSelf()
            } catch (_: Exception) {
            }
        }
        return START_NOT_STICKY
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // v1.14.160 — «اپ میبندم پسزمینه داره کار میکنه با این که بستم»:
        // قبلاً فقط سرویس میایستاد ولی موتورِ پایتون (همان پروسه) با
        // wakeLock تا تمامشدنِ کار در پسزمینه ادامه میداد. حالا بستنِ اپ
        // از recentها = لغوِ فوریِ کارِ پایتون + خروجِ کاملِ پروسه.
        TranslationService.hardStopAndExit()
        try {
            stopForeground(true)
        } catch (_: Exception) {
        }
        try {
            stopSelf()
        } catch (_: Exception) {
        }
        if (current === this) current = null
        super.onTaskRemoved(rootIntent)
    }

    override fun onDestroy() {
        if (current === this) current = null
        super.onDestroy()
    }

    private fun goForeground() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CH_ID, "ترجمه در جریان",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
        startFg(buildNotif(0, 0, ""))
    }

    private fun startFg(n: Notification) {
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(
                NOTIF_ID, n,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            @Suppress("DEPRECATION")
            startForeground(NOTIF_ID, n)
        }
    }

    private fun buildNotif(done: Int, total: Int, phase: String): Notification {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(
                NotificationChannel(
                    CH_ID, "ترجمه در جریان",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }
        val ph = phase.ifBlank { "در حال ترجمه…" }
        // v1.14.154 — «کدوم قسمته کدوم عکسه چند درصده»:
        // «استخراج متن — صفحهٔ ۳ از ۵ (٪۶۰)»
        val pct = if (total > 0 && done > 0) done * 100 / total else 0
        val txt = if (total > 0 && done > 0)
            "$ph — صفحهٔ $done از $total (٪$pct)" else ph
        val b = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, CH_ID)
        } else {
            @Suppress("DEPRECATION") Notification.Builder(this)
        }
        // v1.14.153 — «مربعِ سیاه» نشون میداد: smallIcon فقط کانالِ آلفا را
        // میخواند و ic_launcher مربعِ قرمزِ توپر بود → silhouetteِ مربع.
        // درمان: ic_notif = نویسهٔ «漫» سفیدِ خودِ لوگو (زمینهٔ شفاف) +
        // largeIcon = لوگویِ رنگیِ واقعیِ اپ (مربعِ قرمز) در بدنهٔ اعلان.
        b.setContentTitle("مانگا مترجم")
            .setContentText(txt)
            .setSmallIcon(R.drawable.ic_notif)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
        try {
            val lp = android.graphics.BitmapFactory.decodeResource(
                resources, R.mipmap.ic_launcher)
            if (lp != null) b.setLargeIcon(lp)
        } catch (_: Exception) {
        }
        if (total > 0) {
            b.setProgress(total, done.coerceIn(0, total), false)
        } else {
            b.setProgress(0, 0, true)
        }
        return b.build()
    }

    private fun notifyProgress(done: Int, total: Int, phase: String) {
        try {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            nm.notify(NOTIF_ID, buildNotif(done, total, phase))
        } catch (_: Exception) {
        }
    }

    companion object {
        private const val CH_ID = "translation"
        private const val NOTIF_ID = 4150

        @Volatile
        var current: TranslationService? = null
            private set

        @JvmStatic
        fun updateProgress(done: Int, total: Int, phase: String) {
            try {
                current?.notifyProgress(done, total, phase)
            } catch (_: Exception) {
            }
        }

        // v1.14.160 — توقفِ سختِ همه‌چیز: لغوِ کارِ پایتون (stop_requested →
        // قطعِ بینِ صفحه‌ها) + یک فرصتِ کوتاه برای تمامشدنِ نوشتنِ فایلِ
        // جاری + کشتنِ کاملِ پروسه. هم از onTaskRemoved (سوایپ از recentها)
        // هم از onDestroyِ اکتیویتی وقتی isFinishing (خروجِ واقعی) صدا
        // زده میشود — ولی هرگز در home/تعویضِ اپ (آن مسیرِ ادامهٔ کار است).
        @Volatile
        private var hardStopDone = false

        @JvmStatic
        fun hardStopAndExit() {
            if (hardStopDone) return
            hardStopDone = true
            Thread {
                try {
                    if (com.chaquo.python.Python.isStarted()) {
                        com.chaquo.python.Python.getInstance()
                            .getModule("native_bridge").callAttr("cancel")
                    }
                } catch (_: Exception) {
                }
                try {
                    Thread.sleep(1200)
                } catch (_: Exception) {
                }
                try {
                    android.os.Process.killProcess(android.os.Process.myPid())
                } catch (_: Exception) {
                }
                try {
                    java.lang.System.exit(0)
                } catch (_: Exception) {
                }
            }.start()
        }
    }
}
