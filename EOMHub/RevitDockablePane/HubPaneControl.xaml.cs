using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Controls;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using System.Windows;

namespace EOMHub.DockablePane;

public partial class HubPaneControl : UserControl
{
    private const double DefaultZoomFactor = 1.0;
    private readonly DispatcherTimer _sessionTimer;
    private string? _lastNavigatedUrl;
    private static string WebViewLogPath => Path.Combine(Path.GetTempPath(), "eom_webview2.log");

    public HubPaneControl()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Unloaded += OnUnloaded;

        _sessionTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(5)
        };
        _sessionTimer.Tick += async (_, _) => await UpdateWebViewSourceAsync();
    }

    private async void OnLoaded(object sender, System.Windows.RoutedEventArgs e)
    {
        await EnsureWebViewAsync();
        await UpdateWebViewSourceAsync(force: true);
        _sessionTimer.Start();
    }

    private void OnUnloaded(object sender, System.Windows.RoutedEventArgs e)
    {
        _sessionTimer.Stop();
    }

    private async Task EnsureWebViewAsync()
    {
        if (HubWebView.CoreWebView2 != null)
        {
            ApplyZoomFactor();
            return;
        }

        try
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var userDataFolder = Path.Combine(localAppData, "EOMHub", "WebView2", "DockablePane");
            Directory.CreateDirectory(userDataFolder);

            var env = await CoreWebView2Environment.CreateAsync(
                browserExecutableFolder: null,
                userDataFolder: userDataFolder,
                options: null);

            await HubWebView.EnsureCoreWebView2Async(env);
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[EOMHub] WebView2 custom env failed, fallback to default: {ex.Message}");
            await HubWebView.EnsureCoreWebView2Async();
        }

        HubWebView.CoreWebView2!.NavigationStarting += (_, args) => LogWebView($"NavigationStarting: {args.Uri}");
        HubWebView.CoreWebView2!.NavigationCompleted += OnNavigationCompleted;

        try
        {
            var enableDevTools = (Environment.GetEnvironmentVariable("EOM_HUB_DEVTOOLS") ?? "")
                .Trim()
                .Equals("1", StringComparison.OrdinalIgnoreCase);
            if (enableDevTools)
            {
                HubWebView.CoreWebView2.OpenDevToolsWindow();
            }
        }
        catch (Exception ex)
        {
            LogWebView($"OpenDevToolsWindow failed: {ex.Message}");
        }

        ApplyZoomFactor();
    }

    private static string? ResolveHubUrl()
    {
        var session = SessionPortLocator.TryReadHubSessionInfo();
        if (session != null && session.Port > 0)
        {
            return $"http://127.0.0.1:{session.Port}/index.html?v={Uri.EscapeDataString(session.VersionToken)}";
        }

        return null;
    }

    private async Task UpdateWebViewSourceAsync(bool force = false)
    {
        var url = ResolveHubUrl();
        if (string.IsNullOrWhiteSpace(url))
        {
            ShowPlaceholder("Нажмите кнопку «Хаб» в pyRevit, чтобы запустить сервер.");
            return;
        }

        if (!force && string.Equals(url, _lastNavigatedUrl, StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        await EnsureWebViewAsync();
        _ = ShowWebViewAsync(url!);
    }

    private void OnNavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
    {
        if (!e.IsSuccess)
        {
            ShowPlaceholder("Не удалось загрузить UniTools Hub. Проверьте, запущен ли сервер.");
            _ = UpdateWebViewSourceAsync(force: true);
            return;
        }

        ApplyZoomFactor();
    }

    private async Task ShowWebViewAsync(string url)
    {
        if (HubWebView.CoreWebView2 == null)
        {
            await EnsureWebViewAsync();
        }

        HubWebView.Visibility = Visibility.Visible;
        PlaceholderPanel.Visibility = Visibility.Collapsed;
        HubWebView.CoreWebView2?.Navigate(url);
        _lastNavigatedUrl = url;
    }

    private void ShowPlaceholder(string message)
    {
        Debug.WriteLine($"[EOMHub] Dockable pane placeholder: {message}");
        LogWebView($"Placeholder: {message}");
        if (PlaceholderText != null)
        {
            PlaceholderText.Text = message;
        }

        PlaceholderPanel.Visibility = Visibility.Visible;
        HubWebView.Visibility = Visibility.Collapsed;
        _lastNavigatedUrl = null;
    }

    private async void OnPlaceholderRefreshClick(object sender, RoutedEventArgs e)
    {
        await UpdateWebViewSourceAsync(force: true);
    }

    private void ApplyZoomFactor()
    {
        try
        {
            HubWebView.ZoomFactor = DefaultZoomFactor;
        }
        catch
        {
            // Ignore zoom errors.
        }
    }

    private static void LogWebView(string message)
    {
        try
        {
            File.AppendAllText(
                WebViewLogPath,
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}] {message}{Environment.NewLine}");
        }
        catch
        {
        }
    }
}
