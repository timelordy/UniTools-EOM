using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace EOMHub.DockablePane.Commands;

[Transaction(TransactionMode.Manual)]
public class ShowHubCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        try
        {
            var pane = commandData.Application.GetDockablePane(HubApp.PaneId);
            pane?.Show();
            return Result.Succeeded;
        }
        catch (Autodesk.Revit.Exceptions.InvalidOperationException ex)
        {
            message = $"Не удалось открыть панель EOM Hub: {ex.Message}";
            return Result.Failed;
        }
    }
}
