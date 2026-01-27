 # -*- coding: utf-8 -*-
 """Delete ALL AUTO_EOM elements with strong confirmation.
 
 This is a destructive operation that removes all automatically
 placed elements. Requires explicit confirmation.
 """
 from __future__ import print_function
 
 from pyrevit import DB, forms, revit, script
 
 import rollback_utils
 
 # Get current document
 doc = revit.doc
 output = script.get_output()
 
 
 def main():
     """Main entry point."""
     
     # Get all tagged elements
     tags = rollback_utils.get_unique_tags(doc)
     
     if not tags:
         forms.alert(
             "Не найдено элементов с тегом AUTO_EOM.",
             title="Нет элементов для удаления",
             warn_icon=False
         )
         return
     
     # Calculate total
     total_count = sum(count for _, count in tags)
     
     # Build summary
     summary_lines = ["Будут удалены следующие элементы:\n"]
     for tag, count in tags:
         parts = tag.split(":")
         tool_name = parts[1] if len(parts) > 1 else "UNKNOWN"
         summary_lines.append("  - {}: {} шт.".format(tool_name, count))
     summary_lines.append("\nВСЕГО: {} элементов".format(total_count))
     summary_lines.append("\n" + "=" * 40)
     summary_lines.append("Для подтверждения введите: УДАЛИТЬ")
     
     summary = "\n".join(summary_lines)
     
     # Show confirmation dialog with text input
     confirm_text = forms.ask_for_string(
         prompt=summary,
         title="Подтверждение удаления ВСЕХ элементов",
         default=""
     )
     
     if not confirm_text:
         forms.alert(
             "Операция отменена.",
             title="Отмена",
             warn_icon=False
         )
         return
     
     # Check confirmation text
     if confirm_text.strip().upper() != "УДАЛИТЬ":
         forms.alert(
             "Неверное подтверждение.\n\n"
             "Для удаления необходимо ввести слово 'УДАЛИТЬ'.",
             title="Ошибка подтверждения",
             warn_icon=True
         )
         return
     
     # Perform deletion
     output.print_md("# Удаление всех AUTO_EOM элементов")
     output.print_md("---")
     
     deleted = rollback_utils.delete_all_auto_eom(doc)
     
     output.print_md("## Результат")
     output.print_md("**Удалено элементов:** {}".format(deleted))
     output.print_md("")
     output.print_md("*Используйте Ctrl+Z для отмены (до сохранения файла).*")
     
     forms.alert(
         "Удалено {} элементов.\n\n"
         "Ctrl+Z для отмены (до сохранения).".format(deleted),
         title="Удаление завершено",
         warn_icon=False
     )
 
 
 if __name__ == "__main__":
     main()
