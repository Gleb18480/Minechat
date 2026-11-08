package com.gleb.minechat;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.Intent;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.PowerManager;
import android.provider.Settings;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends Activity {
    private WebView webView;
    private static final int PERMISSION_REQUEST_CODE = 100;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) -> {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setMimeType(mimetype);
            String cookies = CookieManager.getInstance().getCookie(url);
            if (cookies != null) request.addRequestHeader("cookie", cookies);
            request.addRequestHeader("User-Agent", userAgent);
            request.setTitle(URLUtil.guessFileName(url, contentDisposition, mimetype));
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, URLUtil.guessFileName(url, contentDisposition, mimetype));
            DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
            if (dm != null) dm.enqueue(request);
            Toast.makeText(getApplicationContext(), "Скачивание начато", Toast.LENGTH_SHORT).show();
        });

        webView.setWebViewClient(new WebViewClient());
        String url = "https://minechat.de2.netrun.io/";
        Intent intent = getIntent();
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            String shared = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (shared != null) url += "?shared_text=" + Uri.encode(shared);
        }
        webView.loadUrl(url);

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                    runOnUiThread(() -> request.grant(request.getResources()));
                }
            }
        });

        checkPermissions();
        requestBatteryOptimization();
        startBackgroundService();
        createShortcut();
    }

    private void checkPermissions() {
        java.util.List<String> perms = new java.util.ArrayList<>();
        perms.add(android.Manifest.permission.CAMERA);
        perms.add(android.Manifest.permission.RECORD_AUDIO);
        perms.add(android.Manifest.permission.MODIFY_AUDIO_SETTINGS);
        perms.add(android.Manifest.permission.VIBRATE);
        perms.add(android.Manifest.permission.ACCESS_FINE_LOCATION);
        perms.add(android.Manifest.permission.WAKE_LOCK);
        perms.add(android.Manifest.permission.FOREGROUND_SERVICE);
        if (Build.VERSION.SDK_INT >= 33) {
            perms.add(android.Manifest.permission.POST_NOTIFICATIONS);
            perms.add(android.Manifest.permission.READ_MEDIA_IMAGES);
            perms.add(android.Manifest.permission.READ_MEDIA_VIDEO);
            perms.add(android.Manifest.permission.READ_MEDIA_AUDIO);
        } else {
            perms.add(android.Manifest.permission.READ_EXTERNAL_STORAGE);
            perms.add(android.Manifest.permission.WRITE_EXTERNAL_STORAGE);
        }
        boolean needed = false;
        for (String p : perms) {
            if (ContextCompat.checkSelfPermission(this, p) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                needed = true; break;
            }
        }
        if (needed) ActivityCompat.requestPermissions(this, perms.toArray(new String[0]), PERMISSION_REQUEST_CODE);
    }

    private void requestBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                i.setData(Uri.parse("package:" + getPackageName()));
                try { startActivity(i); } catch (Exception e) {}
            }
        }
    }

    private void startBackgroundService() {
        Intent serviceIntent = new Intent(this, BackgroundService.class);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(serviceIntent);
            else startService(serviceIntent);
        } catch (Exception e) {}
    }

    private void createShortcut() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ShortcutManager sm = getSystemService(ShortcutManager.class);
            if (sm != null && sm.isRequestPinShortcutSupported()) {
                Intent shortcutIntent = new Intent(this, MainActivity.class);
                shortcutIntent.setAction(Intent.ACTION_VIEW);
                ShortcutInfo shortcut = new ShortcutInfo.Builder(this, "minechat_shortcut")
                    .setShortLabel("Minechat").setLongLabel("Minechat (Russia)")
                    .setIcon(Icon.createWithResource(this, getApplicationInfo().icon))
                    .setIntent(shortcutIntent).build();
                try { sm.requestPinShortcut(shortcut, null); } catch (Exception e) {}
            }
        }
    }

    @Override
    public void onBackPressed() { if (webView.canGoBack()) webView.goBack(); else super.onBackPressed(); }
}