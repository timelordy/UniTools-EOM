# EOM Hub Dockable Pane (Revit Add-in)

Докуемая панель Revit, которая встраивает текущий интерфейс UniTools (React + eel) через WebView2.

## Структура

- `EOMHub.DockablePane.csproj` — WPF Class Library (.NET Framework 4.8). Подтягивает RevitAPI/ RevitAPIUI через `REVIT_API_PATH`.
- `HubApp.cs` — реализация `IExternalApplication`, регистрирует панель и кнопку на вкладке EOM Hub.
- `HubPaneControl` — WPF `UserControl` c WebView2 (подгружает UI с `http://localhost:<порт>/index.html`).
- `SessionPortLocator` — ищет JSON-файл `eom_hub_session_<session>.json`, чтобы получить порт running EOM Hub.
- `Commands/ShowHubCommand.cs` — внешняя команда для быстрого показа панели.
- `EOMHub.DockablePane.addin` — пример `.addin` манифеста (обновите путь под свою сборку).

## Сборка

```powershell
cd EOMHub/RevitDockablePane
dotnet build -c Release
```

Параметр `REVIT_API_PATH` можно переопределить: `dotnet build -p:REVIT_API_PATH="C:\Program Files\Autodesk\Revit 2025"`.

## Установка

1. Скопируйте `bin\Release\EOMHub.DockablePane.dll` в папку `%AppData%\Autodesk\Revit\Addins\<версия>\EOMHubDockablePane\`.
2. Скопируйте `EOMHub.DockablePane.addin` в ту же папку и поправьте путь в `<Assembly>` (например, `C:\Users\<you>\AppData\Roaming\Autodesk\Revit\Addins\2024\EOMHubDockablePane\EOMHub.DockablePane.dll`).
3. Убедитесь, что на рабочем месте установлен Microsoft Edge WebView2 Runtime.

После запуска Revit появится вкладка **EOM Hub** → кнопка **EOM Hub**, открывающая закрепляемую панель. Панель автоматически ищет активный EOM Hub (по сессии `EOM_SESSION_ID`). Если фронт ещё не поднят, WebView2 может показать пустую страницу — запустите `EOMHub.exe`, и панель обновится сразу, как только появится JSON с портом.
