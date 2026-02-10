using System;
using System.IO;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace EOMHub.DockablePane;

public class HubApp : IExternalApplication
{
    public static readonly DockablePaneId PaneId = new DockablePaneId(new Guid("59f3cd26-2ca0-4d4b-91f3-71b3fbda2e57"));
    internal static string AssemblyLocation => typeof(HubApp).Assembly.Location;
    private static string StartupLogPath => Path.Combine(Path.GetTempPath(), "eom_dockable_startup.log");

    public Result OnStartup(UIControlledApplication application)
    {
        Log($"OnStartup begin. Assembly={AssemblyLocation}");
        try
        {
            RegisterPane(application);
            Log("RegisterPane succeeded");
        }
        catch (Exception ex)
        {
            Log($"RegisterPane failed: {ex}");
        }

        try
        {
            CreateRibbonPanel(application);
            Log("CreateRibbonPanel succeeded");
        }
        catch (Exception ex)
        {
            Log($"CreateRibbonPanel failed: {ex}");
        }

        return Result.Succeeded;
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        return Result.Succeeded;
    }

    private static void RegisterPane(UIControlledApplication application)
    {
        var provider = new HubPaneProvider();
        application.RegisterDockablePane(PaneId, "UniTools Hub", provider);
    }

    private static void CreateRibbonPanel(UIControlledApplication application)
    {
        RibbonPanel? panel = null;
        try
        {
            panel = application.CreateRibbonPanel("UniTools Hub");
        }
        catch
        {
            // Panel already exists, try to reuse it.
            foreach (var existing in application.GetRibbonPanels())
            {
                if (existing.Name.Equals("UniTools Hub", StringComparison.OrdinalIgnoreCase))
                {
                    panel = existing;
                    break;
                }
            }
        }

        panel ??= application.CreateRibbonPanel("UniTools Hub");

        var buttonData = new PushButtonData(
            "EOMHubDock",
            "UniTools Hub",
            AssemblyLocation,
            typeof(Commands.ShowHubCommand).FullName
        )
        {
            ToolTip = "Open the UniTools Hub dockable pane",
            LongDescription = "Shows the UniTools Hub panel as a dockable window inside Revit."
        };

        panel.AddItem(buttonData);
    }

    private static void Log(string message)
    {
        try
        {
            File.AppendAllText(
                StartupLogPath,
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}] {message}{Environment.NewLine}");
        }
        catch
        {
        }
    }
}
