using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Collections.Generic;
using System.Net.Sockets;

namespace EOMHub.DockablePane;

internal static class SessionPortLocator
{
    private static DateTime _lastReadMoment = DateTime.MinValue;
    private static HubSessionInfo? _cachedSession;
    private static readonly TimeSpan CacheTtl = TimeSpan.FromSeconds(3);

    internal sealed class HubSessionInfo
    {
        public HubSessionInfo(int port, string? sessionId, int? pid, double? startedAt)
        {
            Port = port;
            SessionId = sessionId;
            Pid = pid;
            StartedAt = startedAt;
        }

        public int Port { get; }
        public string? SessionId { get; }
        public int? Pid { get; }
        public double? StartedAt { get; }

        public string VersionToken
        {
            get
            {
                if (StartedAt.HasValue)
                {
                    return ((long)(StartedAt.Value * 1000)).ToString();
                }

                if (!string.IsNullOrWhiteSpace(SessionId))
                {
                    return SessionId!;
                }

                if (Pid.HasValue)
                {
                    return Pid.Value.ToString();
                }

                return Port.ToString();
            }
        }
    }

    public static int? TryReadHubPort()
    {
        return TryReadHubSessionInfo()?.Port;
    }

    public static HubSessionInfo? TryReadHubSessionInfo()
    {
        if ((DateTime.UtcNow - _lastReadMoment) < CacheTtl && _cachedSession != null)
        {
            return _cachedSession;
        }

        _cachedSession = ReadSessionInternal();
        _lastReadMoment = DateTime.UtcNow;
        return _cachedSession;
    }

    private static HubSessionInfo? ReadSessionInternal()
    {
        foreach (var sessionFile in ResolveSessionFiles())
        {
            if (string.IsNullOrWhiteSpace(sessionFile) || !File.Exists(sessionFile))
            {
                continue;
            }

            try
            {
                using var stream = File.OpenRead(sessionFile);
                using var doc = JsonDocument.Parse(stream);

                if (!doc.RootElement.TryGetProperty("hubPort", out var portProperty) ||
                    !portProperty.TryGetInt32(out var port) ||
                    port <= 0)
                {
                    continue;
                }

                if (!IsPortReachable(port))
                {
                    continue;
                }

                string? sessionId = null;
                if (doc.RootElement.TryGetProperty("sessionId", out var sessionProperty))
                {
                    sessionId = sessionProperty.GetString();
                }

                int? pid = null;
                if (doc.RootElement.TryGetProperty("pid", out var pidProperty) && pidProperty.TryGetInt32(out var parsedPid))
                {
                    pid = parsedPid;
                }

                double? startedAt = null;
                if (doc.RootElement.TryGetProperty("startedAt", out var startedProperty) && startedProperty.TryGetDouble(out var parsedStarted))
                {
                    startedAt = parsedStarted;
                }

                return new HubSessionInfo(port, sessionId, pid, startedAt);
            }
            catch
            {
                // Skip invalid candidate and continue.
            }
        }

        return null;
    }

    private static bool IsPortReachable(int port)
    {
        if (port <= 0) return false;

        try
        {
            using var tcp = new TcpClient();
            var task = tcp.ConnectAsync("127.0.0.1", port);
            var completed = task.Wait(TimeSpan.FromMilliseconds(300));
            return completed && tcp.Connected;
        }
        catch
        {
            return false;
        }
    }

    private static IEnumerable<string> ResolveSessionFiles()
    {
        var temp = Environment.GetEnvironmentVariable("TEMP") ??
                   Environment.GetEnvironmentVariable("TMP") ??
                   Path.GetTempPath();
        var candidates = new List<string>();

        var statusSessionId = TryReadSessionIdFromStatus(temp);
        if (!string.IsNullOrWhiteSpace(statusSessionId))
        {
            var statusSessionFile = TryResolveSessionFileById(temp, statusSessionId!);
            if (!string.IsNullOrWhiteSpace(statusSessionFile))
            {
                candidates.Add(statusSessionFile!);
            }
        }

        var envSessionId = Environment.GetEnvironmentVariable("EOM_SESSION_ID");
        if (!string.IsNullOrWhiteSpace(envSessionId))
        {
            var envSessionFile = TryResolveSessionFileById(temp, envSessionId!);
            if (!string.IsNullOrWhiteSpace(envSessionFile))
            {
                candidates.Add(envSessionFile!);
            }
        }

        foreach (var file in candidates.Where(File.Exists))
        {
            yield return file;
        }

        var fallback = TryResolveLatestSessionFile(temp);
        if (!string.IsNullOrWhiteSpace(fallback))
        {
            yield return fallback!;
        }
    }

    private static string? TryReadSessionIdFromStatus(string temp)
    {
        try
        {
            var statusPath = Path.Combine(temp, "eom_hub_status.json");
            if (!File.Exists(statusPath))
            {
                return null;
            }

            using var stream = File.OpenRead(statusPath);
            using var doc = JsonDocument.Parse(stream);
            if (doc.RootElement.TryGetProperty("sessionId", out var sessionProperty))
            {
                return sessionProperty.GetString();
            }
        }
        catch
        {
            return null;
        }

        return null;
    }

    private static string? TryResolveLatestSessionFile(string temp)
    {
        try
        {
            return Directory
                .GetFiles(temp, "eom_hub_session_*.json", SearchOption.AllDirectories)
                .OrderByDescending(File.GetLastWriteTimeUtc)
                .FirstOrDefault();
        }
        catch
        {
            return null;
        }
    }

    private static string? TryResolveSessionFileById(string temp, string sessionId)
    {
        if (string.IsNullOrWhiteSpace(sessionId))
        {
            return null;
        }

        var fileName = $"eom_hub_session_{sessionId}.json";

        try
        {
            var topLevel = Path.Combine(temp, fileName);
            if (File.Exists(topLevel))
            {
                return topLevel;
            }

            foreach (var dir in Directory.GetDirectories(temp))
            {
                var nested = Path.Combine(dir, fileName);
                if (File.Exists(nested))
                {
                    return nested;
                }
            }
        }
        catch
        {
            return null;
        }

        return null;
    }
}
