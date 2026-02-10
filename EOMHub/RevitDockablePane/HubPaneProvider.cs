using System;
using System.Windows.Controls;
using Autodesk.Revit.UI;

namespace EOMHub.DockablePane;

internal class HubPaneProvider : IDockablePaneProvider
{
    public void SetupDockablePane(DockablePaneProviderData data)
    {
        UserControl control;
        try
        {
            control = new HubPaneControl();
        }
        catch (Exception ex)
        {
            // Never block dockable pane registration due to WebView2/runtime issues.
            control = new UserControl
            {
                Content = new TextBlock
                {
                    Text = "Не удалось инициализировать UniTools Hub (WebView2).\n\n" + ex.Message,
                    TextWrapping = System.Windows.TextWrapping.Wrap,
                    Margin = new System.Windows.Thickness(12)
                }
            };
        }

        data.FrameworkElement = control;
        data.InitialState = new DockablePaneState
        {
            DockPosition = DockPosition.Left
        };
    }
}
