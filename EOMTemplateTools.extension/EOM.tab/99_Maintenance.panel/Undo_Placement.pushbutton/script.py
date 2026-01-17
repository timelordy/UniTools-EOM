 # -*- coding: utf-8 -*-
 """Undo AUTO_EOM placements.
 
 This script allows users to selectively delete elements
 that were automatically placed by EOM Template Tools.
 """
 from __future__ import print_function
 
 from pyrevit import DB, forms, revit, script
 
 import rollback_utils
 
 # Get current document
 doc = revit.doc
 output = script.get_output()
 
 
 def main():
     """Main entry point."""
     
     # Get all unique tags in the document
     tags = rollback_utils.get_unique_tags(doc)
     
     if not tags:
         forms.alert(
             "Не найдено элементов с тегом AUTO_EOM.\n\n"
             "Возможно, автоматическая расстановка ещё не выполнялась.",
             title="Нет элементов для удаления",
             warn_icon=False
         )
         return
     
     # Build options list
     total_count = sum(count for _, count in tags)
     
     options = []
     for tag, count in tags:
         # Extract tool name for display
         parts = tag.split(":")
         tool_name = parts[1] if len(parts) > 1 else "UNKNOWN"
         
         # Translate common tool names to Russian
         tool_display = {
             "SOCKET": "Розетки",
             "LIGHT": "Светильники", 
             "SWITCH": "Выключатели",
             "PANEL": "Щиты",
             "AC": "Кондиционеры",
             "WET": "Мокрые зоны",
             "KITCHEN": "Кухня",
             "LOW_VOLTAGE": "Слаботочка",
             "SHDUP": "ШДУП",
             "PK": "Указатели ПК",
             "LIFT": "Лифтовые шахты",
             "ENTRANCE": "Входные группы",
         }.get(tool_name, tool_name)
         
         options.append("{} ({} шт.)".format(tool_display, count))
     
     # Add "Delete All" option
     options.append("--- ВСЕ ЭЛЕМЕНТЫ ({} шт.) ---".format(total_count))
     
     # Show selection dialog
     selected = forms.SelectFromList.show(
         options,
         title="Выберите тип элементов для удаления",
         button_name="Удалить",
         multiselect=True
     )
     
     if not selected:
         return
     
     # Check if "Delete All" was selected
     delete_all = any("ВСЕ ЭЛЕМЕНТЫ" in s for s in selected)
     
     if delete_all:
         # Confirm deletion of all elements
         confirm = forms.alert(
             "Вы уверены, что хотите удалить ВСЕ {} элементов?\n\n"
             "Это действие можно отменить через Ctrl+Z до сохранения файла.".format(total_count),
             title="Подтверждение удаления",
             yes=True,
             no=True,
             warn_icon=True
         )
         
         if not confirm:
             return
         
         # Delete all
         deleted = rollback_utils.delete_all_auto_eom(doc)
         
         forms.alert(
             "Удалено {} элементов.".format(deleted),
             title="Готово",
             warn_icon=False
         )
         
     else:
         # Delete selected categories
         total_deleted = 0
         
         for selection in selected:
             # Find matching tag
             for tag, count in tags:
                 parts = tag.split(":")
                 tool_name = parts[1] if len(parts) > 1 else "UNKNOWN"
                 
                 # Check if this tag matches the selection
                 if tool_name in selection or any(
                     display in selection 
                     for display in [
                         "Розетки", "Светильники", "Выключатели", "Щиты",
                         "Кондиционеры", "Мокрые зоны", "Кухня", "Слаботочка",
                         "ШДУП", "Указатели ПК", "Лифтовые шахты", "Входные группы"
                     ]
                     if tool_name == {
                         "Розетки": "SOCKET",
                         "Светильники": "LIGHT",
                         "Выключатели": "SWITCH",
                         "Щиты": "PANEL",
                         "Кондиционеры": "AC",
                         "Мокрые зоны": "WET",
                         "Кухня": "KITCHEN",
                         "Слаботочка": "LOW_VOLTAGE",
                         "ШДУП": "SHDUP",
                         "Указатели ПК": "PK",
                         "Лифтовые шахты": "LIFT",
                         "Входные группы": "ENTRANCE",
                     }.get(display)
                 ):
                     deleted = rollback_utils.delete_by_tool(doc, tool_name)
                     total_deleted += deleted
                     output.print_md("**{}**: удалено {} элементов".format(tag, deleted))
                     break
         
         if total_deleted > 0:
             forms.alert(
                 "Удалено {} элементов.\n\n"
                 "Используйте Ctrl+Z для отмены (до сохранения файла).".format(total_deleted),
                 title="Готово",
                 warn_icon=False
             )
         else:
             forms.alert(
                 "Не удалось удалить элементы.",
                 title="Ошибка",
                 warn_icon=True
             )
 
 
 if __name__ == "__main__":
     main()
