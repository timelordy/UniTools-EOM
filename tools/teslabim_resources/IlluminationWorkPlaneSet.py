'''
Программа выставляет высоту рабочей плоскости всем пространствам в модели для которых были найдены данные в ES (Хранилище, Настройках).
'''

#подгружаем нужные библиотеки
import clr
import System
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI') # подгружаем библиотеку для набора Autodesk.Revit.UI.Selection
from Autodesk.Revit.DB import *
from Autodesk.Revit.ApplicationServices import Application
from System.Windows.Forms import *
from System.Drawing import *
from Autodesk.Revit.UI import *
import sys
from System.Collections.Generic import *
# Библиотеки ExtensibleStorage
import System.Runtime.InteropServices
# import uuid
from Autodesk.Revit.DB.ExtensibleStorage import *
from Autodesk.Revit.DB.ExtensibleStorage import *
from System import Guid # you need to import this, when you work with Guids!
from System.Collections.Generic import *



#____________________Переменные с которыми работает программа__________________________________________________________________________________
'''
# Переменные отвечающие за соединение с хранилищем значений освещённости (5-е хранилище)
Guidstr_Illumination_Values_Storage = '36f085d8-43ee-4230-acec-099431f45dad'
SchemaName_for_Illumination_Values_Storage = 'Illumination_Values_Storage'
FieldName_for_Illumination_Values_Storage = 'Illumination_Values_Storage_list'
'''
#_______________________________________________________________________________________________________________________________________________________________________________________



# Функция получает параметр по встроенному имени параметра
# На входе: element - элемент вида: <Autodesk.Revit.DB.Electrical.ElectricalSystem object at 0x000000000000006C [Autodesk.Revit.DB.Electrical.ElectricalSystem]>
#	BuiltInParameterWithName - встроенное имя параметра вида: Autodesk.Revit.DB.BuiltInParameter.RBS_ELEC_TRUE_LOAD
# На выходе сам параметр вида: <Autodesk.Revit.DB.Parameter object at 0x00000000000000AE [Autodesk.Revit.DB.Parameter]>
# Пример обращения: GetBuiltinParam(ara, BuiltInParameter.RBS_ELEC_TRUE_LOAD)
def GetBuiltinParam(element, BuiltInParameterWithName):
	for i in element.Parameters:
		if i.Definition.BuiltInParameter == BuiltInParameterWithName:
			Builtinparam = i
	return Builtinparam

# функция получения индексов одинаковых элементов в списке
# на входе: элемент который ищем, список в котором ищем. На выходе список с индексами найденных элементов. Например: [2, 4]. Если совпадений не найдено - на выходе пустой список: []
def Get_coincidence_in_list (search_element, search_list):
	index_list = []
	for n, i in enumerate(search_list):
		if i == search_element:
			index_list.append(n)
	return index_list




# Считываем данные из Хранилища
# получаем объект "информация о проекте"
ProjectInfoObject = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).WhereElementIsNotElementType().ToElements()[0] 
schemaGuid_for_Illumination_Values_Storage = System.Guid(Guidstr_Illumination_Values_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_Illumination_Values_Storage = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)
# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_Illumination_Values_Storage) будет <type 'NoneType'>
if sch_Illumination_Values_Storage is None or ProjectInfoObject.GetEntity(sch_Illumination_Values_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	raise Exception('Настройки рабочих плоскостей освещения не найдены или были повреждены.\n Откройте окно настроек Программы, чтобы задать нормы рабочих плоскостей.')

# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch3 = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)
#Получаем Entity из элемента:
ent3 = ProjectInfoObject.GetEntity(sch3)
#Уже знакомым способом получаем «поля»:
field_Illumination_Values_Storage = sch3.GetField(FieldName_for_Illumination_Values_Storage)
#Для считывания значений используем метод Entity.Get:
znach3 = ent3.Get[IList[str]](field_Illumination_Values_Storage) # выдаёт List[str](['a', 'list', 'of', 'strings'])
# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach3]
znach3 = []
[znach3.append(i) for i in CS_help] # [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '']



# Готовим списки для работы плагина
spaces_els = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_MEPSpaces).ToElements() # вытаскиваем все пространства из проекта
spaces_els_numbers = [] # номера пространств ['1', '2', '4', '5']
spaces_els_names = [] # имена пространств ['Sup Space 1', 'Sup space 2', ...]
rated_illumination_workplane = [] # нормируемая рабочая плоскость из Хранилища

for i in spaces_els:
	spaces_els_numbers.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NUMBER).AsString()) # Получаем номер пространства
	cur_space_name_hlp = GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString() # вспомогательная переменная. Имя текщего пространства
	spaces_els_names.append(cur_space_name_hlp) # Получаем имя пространства
	cur_cons_list = Get_coincidence_in_list(cur_space_name_hlp, znach3) # вспомогательная переменная. Индексы найдённых имён пространств или [] если пространства не найдены в ES.
	if cur_cons_list != []: # если текущее имя пространства есть в Хранилище:
		rated_illumination_workplane.append(float(znach3[cur_cons_list[0]+2])) # выписываем высоту рабочей плоскости для данного имени пространства
	else:
		rated_illumination_workplane.append('Нет данных')


#Записываем нужные нам параметры в каждое пространство
isok_worplanes = 0 # счётчик в сколько пространств записали рабочие плоскости
spaces_els_names_absent = [] # список имён пространств для которых нет данных о рабочей плоскости из Хранилища
t = Transaction(doc, 'Set illumination workplanes')
t.Start()
for n, i in enumerate(spaces_els):
	if rated_illumination_workplane[n] != 'Нет данных':
		GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_ROOM_LIGHTING_CALC_WORKPLANE).Set(UnitUtils.ConvertToInternalUnits(rated_illumination_workplane[n], DisplayUnitType.DUT_MILLIMETERS))
		isok_worplanes = isok_worplanes + 1
	else:
		spaces_els_names_absent.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString()) # пишем имя пространства для которого нет данных по рабочей плоскости
t.Commit()

# Формируем строку об отсутствующих рабочих плоскостях
if spaces_els_names_absent != []:
	spaces_els_names_absent_string = '\nДля следующих пространств нет данных о высоте их рабочей плоскости освещения:\n' + ', '.join(spaces_els_names_absent) + '.\nВы можете задать для них рабочие плоскости в Настройках Программы.'
else:
	spaces_els_names_absent_string = ''

TaskDialog.Show('Выставить рабочие плоскости освещения', 'Рабочие плоскости освещения выставлены в ' + str(isok_worplanes) + ' пространствах.' + spaces_els_names_absent_string)




'''
ara = spaces_els[0] # <Autodesk.Revit.DB.Mechanical.Space object at 0x000000000000006C [Autodesk.Revit.DB.Mechanical.Space]>

GetBuiltinParam(ara, BuiltInParameter.ROOM_NAME).AsString() # Получаем имя пространства

self._IllCheck_dataGridView1.Rows[1].Cells[2].Style.ForeColor = Color.Aqua # меняет цвет в ячейке


#Записываем нужные нам параметры в каждый автомат
t = Transaction(doc, 'Circuit breakers calculation')
t.Start()
for n, i in enumerate(elems_avtomats):
	i.LookupParameter(Param_Py).Set(Py[n])
	i.LookupParameter(Param_Pp).Set(Pp[n])
	i.LookupParameter(Param_Ip).Set(Ip[n])
	i.LookupParameter(Param_Moment).Set(Moment[n])
	i.LookupParameter(Param_Voltage_drop).Set(deltaU[n])
	i.LookupParameter(Param_Wires_quantity).Set(Cab_wires[n])
	i.LookupParameter(Param_Cable_section).Set(Cab_section_min[n])
	i.LookupParameter(Param_Circuit_breaker_nominal).Set(Current_breaker_nominal_min[n])
	i.LookupParameter(Param_Internal_pipe_diameter).Set(internal_pipe_diameter[n])
	i.LookupParameter(Param_Laying_Method).Set(method_of_laying[n])
	if i.LookupParameter(Param_PE_section).AsDouble() != 0: # если пользователь вводил сечение отдельного проводника PE, то запишем его расчётное значение
		i.LookupParameter(Param_PE_section).Set(Cab_section_for_separate_PE_calculated[n])
	i.LookupParameter(Param_Current_breaker_overestimated).Set(Current_breaker_overestimated[n])
	i.LookupParameter(Param_Cab_section_overestimated).Set(Cab_section_overestimated[n])
t.Commit()

'''