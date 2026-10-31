package com.tanvir.khoroch;

import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private boolean wasPaused = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WebView.setWebContentsDebuggingEnabled(false);
        if (this.bridge != null && this.bridge.getWebView() != null) {
            WebView webView = this.bridge.getWebView();
            WebSettings settings = webView.getSettings();
            settings.setDomStorageEnabled(true);
            settings.setDatabaseEnabled(true);
            settings.setJavaScriptEnabled(true);
            settings.setAllowFileAccess(false);
            settings.setAllowContentAccess(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (bridge != null && bridge.getWebView() != null) {
                    WebView wv = bridge.getWebView();
                    wv.evaluateJavascript("(function(){return (typeof window.handleHardwareBack==='function')?!!window.handleHardwareBack():false;})()", value -> {
                        if (!"true".equals(value)) {
                            wasPaused = true;
                            wv.evaluateJavascript("if(typeof window.onAppBackground==='function')window.onAppBackground();", null);
                            moveTaskToBack(true);
                        }
                    });
                } else {
                    moveTaskToBack(true);
                }
            }
        });
    }

    @Override
    public void onPause() {
        wasPaused = true;
        if (this.bridge != null && this.bridge.getWebView() != null) {
            this.bridge.getWebView().evaluateJavascript("if(typeof window.onAppBackground==='function')window.onAppBackground();", null);
        }
        super.onPause();
    }

    @Override
    public void onResume() {
        super.onResume();
        if (wasPaused && this.bridge != null && this.bridge.getWebView() != null) {
            wasPaused = false;
            this.bridge.getWebView().evaluateJavascript("if(typeof window.onAppReEnter==='function')window.onAppReEnter(true);", null);
        }
    }
}
