#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <objbase.h>

typedef struct Wv2WebView Wv2WebView;
typedef struct Wv2Controller Wv2Controller;
typedef struct Wv2Environment Wv2Environment;
typedef struct Wv2CtlHandler Wv2CtlHandler;

static const WCHAR APP_URL[] = L"https://amirwolf512-manga-autotranslate.hf.space/";
static const WCHAR APP_TITLE[] =
    L"\u0645\u0627\u0646\u06AF\u0627 \u06A9\u0644\u0648\u062F"
    L" \u2014 \u0645\u062A\u0631\u062C\u0645 \u0627\u0646\u06AF\u0627";

static const IID IID_WV2_ENV_DONE = {
    0x4e8a3389, 0xc9d8, 0x4bd2,
    {0xb6, 0xb5, 0x12, 0x4f, 0xee, 0x6c, 0xc1, 0x4d}};
static const IID IID_WV2_CTL_DONE = {
    0x6c4819f3, 0xc9b7, 0x4260,
    {0x81, 0x27, 0xc9, 0xf5, 0xbd, 0xe7, 0xf6, 0x8c}};

static HWND g_hwnd = NULL;
static Wv2Controller *g_controller = NULL;

struct Wv2Environment {
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) = 0;
    virtual ULONG STDMETHODCALLTYPE AddRef() = 0;
    virtual ULONG STDMETHODCALLTYPE Release() = 0;
    virtual HRESULT STDMETHODCALLTYPE CreateCoreWebView2Controller(
        HWND parentWindow, Wv2CtlHandler *handler) = 0;
};

struct Wv2WebView {
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) = 0;
    virtual ULONG STDMETHODCALLTYPE AddRef() = 0;
    virtual ULONG STDMETHODCALLTYPE Release() = 0;
    virtual HRESULT STDMETHODCALLTYPE get_Settings(void **settings) = 0;
    virtual HRESULT STDMETHODCALLTYPE get_Source(LPWSTR *uri) = 0;
    virtual HRESULT STDMETHODCALLTYPE Navigate(LPCWSTR uri) = 0;
    virtual HRESULT STDMETHODCALLTYPE NavigateToString(LPCWSTR html) = 0;
};

struct Wv2Controller {
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) = 0;
    virtual ULONG STDMETHODCALLTYPE AddRef() = 0;
    virtual ULONG STDMETHODCALLTYPE Release() = 0;
    virtual HRESULT STDMETHODCALLTYPE get_IsVisible(BOOL *visible) = 0;
    virtual HRESULT STDMETHODCALLTYPE put_IsVisible(BOOL visible) = 0;
    virtual HRESULT STDMETHODCALLTYPE get_Bounds(RECT *bounds) = 0;
    virtual HRESULT STDMETHODCALLTYPE put_Bounds(RECT bounds) = 0;
};

static void *vslot(void *obj, unsigned int idx) {
    void **vt = *(void ***)obj;
    return vt[idx];
}

static void OpenFallback(void) {
    ShellExecuteW(NULL, L"open", APP_URL, NULL, NULL, SW_SHOWNORMAL);
}

struct Wv2CtlHandler {
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) {
        if (ppv == NULL)
            return E_POINTER;
        if (IsEqualIID(riid, IID_IUnknown) || IsEqualIID(riid, IID_WV2_CTL_DONE)) {
            *ppv = this;
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }
    virtual ULONG STDMETHODCALLTYPE AddRef() { return 2; }
    virtual ULONG STDMETHODCALLTYPE Release() { return 1; }
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode, Wv2Controller *controller) {
        if (FAILED(errorCode) || controller == NULL) {
            OpenFallback();
            PostQuitMessage(0);
            return S_OK;
        }
        g_controller = controller;
        RECT rc;
        GetClientRect(g_hwnd, &rc);
        controller->put_Bounds(rc);
        Wv2WebView *wv = NULL;
        HRESULT hr = ((HRESULT(STDMETHODCALLTYPE *)(void *, Wv2WebView **))
                      vslot(controller, 25))(controller, &wv);
        if (SUCCEEDED(hr) && wv != NULL)
            wv->Navigate(APP_URL);
        return S_OK;
    }
};

static Wv2CtlHandler g_ctlHandler;

struct Wv2EnvHandler {
    virtual HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, void **ppv) {
        if (ppv == NULL)
            return E_POINTER;
        if (IsEqualIID(riid, IID_IUnknown) || IsEqualIID(riid, IID_WV2_ENV_DONE)) {
            *ppv = this;
            AddRef();
            return S_OK;
        }
        *ppv = NULL;
        return E_NOINTERFACE;
    }
    virtual ULONG STDMETHODCALLTYPE AddRef() { return 2; }
    virtual ULONG STDMETHODCALLTYPE Release() { return 1; }
    virtual HRESULT STDMETHODCALLTYPE Invoke(HRESULT errorCode, Wv2Environment *environment) {
        if (FAILED(errorCode) || environment == NULL) {
            OpenFallback();
            PostQuitMessage(0);
            return S_OK;
        }
        HRESULT hr = environment->CreateCoreWebView2Controller(g_hwnd, &g_ctlHandler);
        if (FAILED(hr)) {
            OpenFallback();
            PostQuitMessage(0);
        }
        return S_OK;
    }
};

static Wv2EnvHandler g_envHandler;

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_SIZE:
        if (g_controller != NULL) {
            RECT rc;
            GetClientRect(hwnd, &rc);
            g_controller->put_Bounds(rc);
        }
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcW(hwnd, msg, wp, lp);
    }
}

int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int nCmdShow) {
    typedef HRESULT(STDMETHODCALLTYPE *CreateEnvFn)(
        PCWSTR browserFolder, PCWSTR userDataFolder, void *options, Wv2EnvHandler *handler);
    typedef BOOL(WINAPI *SetDpiCtxFn)(HANDLE value);

    HMODULE user32 = GetModuleHandleW(L"user32.dll");
    if (user32 != NULL) {
        SetDpiCtxFn setCtx =
            (SetDpiCtxFn)(void *)(uintptr_t)GetProcAddress(user32, "SetProcessDpiAwarenessContext");
        if (setCtx != NULL)
            setCtx((HANDLE)(INT_PTR)-4);
    }
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);

    WNDCLASSEXW wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInst;
    wc.hIcon = LoadIconW(hInst, MAKEINTRESOURCEW(1));
    wc.hIconSm = wc.hIcon;
    wc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.lpszClassName = L"MangaCloudWnd";
    RegisterClassExW(&wc);

    int sw = GetSystemMetrics(SM_CXSCREEN);
    int sh = GetSystemMetrics(SM_CYSCREEN);
    int ww = sw < 1320 ? (sw > 40 ? sw - 40 : sw) : 1280;
    int wh = sh < 900 ? (sh > 80 ? sh - 80 : sh) : 820;
    int x = sw > ww ? (sw - ww) / 2 : 0;
    int y = sh > wh ? (sh - wh) / 2 : 0;

    g_hwnd = CreateWindowExW(0, L"MangaCloudWnd", APP_TITLE,
                             WS_OVERLAPPEDWINDOW, x, y, ww, wh,
                             NULL, NULL, hInst, NULL);
    if (g_hwnd == NULL)
        return 1;
    ShowWindow(g_hwnd, nCmdShow);
    UpdateWindow(g_hwnd);

    HMODULE loader = LoadLibraryW(L"WebView2Loader.dll");
    if (loader == NULL) {
        OpenFallback();
        return 0;
    }
    CreateEnvFn createEnv = (CreateEnvFn)(void *)(uintptr_t)GetProcAddress(
        loader, "CreateCoreWebView2EnvironmentWithOptions");
    if (createEnv == NULL) {
        OpenFallback();
        return 0;
    }

    WCHAR base[MAX_PATH];
    WCHAR udf[MAX_PATH + 32];
    PCWSTR userDataFolder = NULL;
    if (GetEnvironmentVariableW(L"LOCALAPPDATA", base, MAX_PATH) > 0) {
        wsprintfW(udf, L"%s\\MangaCloud", base);
        userDataFolder = udf;
    }

    HRESULT hr = createEnv(NULL, userDataFolder, NULL, &g_envHandler);
    if (FAILED(hr)) {
        OpenFallback();
        return 0;
    }

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    return (int)msg.wParam;
}
