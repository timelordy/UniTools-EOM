'''
Программа расчёта токов КЗ
Базируемся на этих методичках:
http://rza001.ru/nebrat
https://raschet.info/primer-rascheta-toka-odnofaznogo-kz/
'''


#подгружаем нужные библиотеки
import clr
import System
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.ApplicationServices import Application
from System.Windows.Forms import *
from System.Drawing import *
import sys
# Библиотеки ExtensibleStorage
import System.Runtime.InteropServices
# import uuid
from Autodesk.Revit.DB.ExtensibleStorage import *
from Autodesk.Revit.DB.ExtensibleStorage import *
from System import Guid # you need to import this, when you work with Guids!
from System.Collections.Generic import *
# Библиотеки для того чтобы Ревитовские окошки показывались
clr.AddReference('RevitAPIUI') # подгружаем библиотеку для набора Autodesk.Revit.UI.Selection
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import ObjectType
# Библиотека чтобы сохранять и открывать файлы
import System.IO
import math # математические функции







#____________________Переменные с которыми работает программа__________________________________________________________________________________

'''
# Сделать окно RPS немодальным:
TaskDialog.Show('название окна', 'ara')

# ВАЖНО! Ревит помнит созданные schema даже при всех закрытых документах. Чтобы он их забыл, нужно перезапускать Ревит!

# Объявим переменные с которыми работает данная программа.
# Разлочить при тестировании в Python Shell. А так получаем на входе от C#

# Имена семейств и параметров с которыми работает программа
avt_family_names = ['TSL_2D автоматический выключатель_ВРУ', 'TSL_2D автоматический выключатель_Щит']
using_auxiliary_cables = ['TSL_Кабель', 'TSL_Кабель с текстом 1.8']
using_any_avtomats = ['TSL_Вводной автомат для щитов', 'TSL_Любой автомат для схем'] # все автоматы не относящиеся к семействам из списка using_avtomats
using_reserve_avtomats = ['TSL_Резервный автомат для ВРУ', 'TSL_Резервный автомат для щитов'] # резервные автоматы

Param_Upit = 'Напряжение'
Param_Cable_length = 'Длина проводника'
Param_Cable_section = 'Сечение проводника'
Param_Circuit_breaker_nominal = 'Уставка аппарата'
Param_Wire_brand = 'Марка проводника'
Param_Rays_quantity = 'Количество лучей'
Param_Breaking_capacity = 'Отключающая способность (кА)'
Param_Circuit_number = 'Номер цепи'
Param_Short_Circuit_3ph = 'Ток КЗ 3ф (кА)' 
Param_Short_Circuit_1ph = 'Ток КЗ 1ф (кА)' 



# Необходимые данные для соединения с хранилищем Calculation Resourses (CR) (из Настроек Теслы)
Guidstr_CR = 'c96a640d-7cf1-47dd-bd1d-1a938122227f' # был раньше такой: 'bc9861d7-64ce-4c01-9ab5-18c40c3a59d4', а ещё раньше такой: '9c2310f8-4930-49d6-837c-d8307a356bbc'
SchemaName_for_CR = 'Tesla_CR_Storage'
FieldName_for_CR_1 = 'Sections_of_cables_CR'
FieldName_for_CR_2 = 'Currents_for_multiwire_copper_cables_CR'
FieldName_for_CR_3 = 'Currents_for_multiwire_aluminium_cables_CR'
FieldName_for_CR_4 = 'Currents_for_singlewire_copper_cables_CR'
FieldName_for_CR_5 = 'Currents_for_singlewire_aluminium_cables_CR'
FieldName_for_CR_6 = 'Current_breaker_nominal_CR'
FieldName_for_CR_7 = 'Cables_trays_reduction_factor_CR'
FieldName_for_CR_8 = 'Circuit_breakers_reduction_factor_CR'
FieldName_for_CR_9 = 'Volt_dropage_coeffitients_CR'
FieldName_for_CR_10 = 'Currents_for_1phase_multiwire_copper_cables_DB'
FieldName_for_CR_11 = 'Currents_for_1phase_multiwire_aluminium_cables_DB'
FieldName_for_CR_12 = 'Voltage_CR'
FieldName_for_CR_13 = 'Resistance_Active_Specific_for_copper_cables_DB'
FieldName_for_CR_14 = 'Resistance_Active_Specific_for_aluminium_cables_DB'
FieldName_for_CR_15 = 'Resistance_Inductive_Specific_for_all_cables_DB'



# Необходимые данные для соединения с хранилищем настроек расчётов токов КЗ
Guidstr_ShortCircuit_Settings = 'feed43d6-2017-4488-a83f-8fde400df18e'
SchemaName_for_ShortCircuit_Settings = 'ShortCircuit_Settings_Storage'
FieldName_for_ShortCircuit_Settings_1 = 'Transformer_Power_DB'
FieldName_for_ShortCircuit_Settings_2 = 'Resistance_r1t_Transformer_forward_reverse_DB'
FieldName_for_ShortCircuit_Settings_3 = 'Resistance_x1t_Transformer_forward_reverse_DB'
FieldName_for_ShortCircuit_Settings_4 = 'Resistance_z1t_Transformer_forward_reverse_DB'
FieldName_for_ShortCircuit_Settings_5 = 'Resistance_r1_1t_Transformer_1phSC_DB'
FieldName_for_ShortCircuit_Settings_6 = 'Resistance_x1_1t_Transformer_1phSC_DB'
FieldName_for_ShortCircuit_Settings_7 = 'Resistance_z1_1t_Transformer_1phSC_DB'
FieldName_for_ShortCircuit_Settings_8 = 'QF_Rated_current'
FieldName_for_ShortCircuit_Settings_9 = 'QF_Resistance_rkv'
FieldName_for_ShortCircuit_Settings_10 = 'QF_Resistance_xkv'



# Необходимые данные для сохранения информации в основном окне расчётов Токов КЗ
Guidstr_ShortCircuit_Main = '413cb225-2262-46a9-a9b5-61a2579540eb'
SchemaName_for_ShortCircuit_Main = 'ShortCircuit_Main_Storage'
FieldName_for_ShortCircuit_Main_1 = 'ChainSectionsInfo_DB'
FieldName_for_ShortCircuit_Main_2 = 'DifSettings_Info_DB'
FieldName_for_ShortCircuit_Main_3 = 'QFsCount_Info_DB'



# Хранилища для производителей кабелей
# В этом списке пусть 0-й элемент - это тот производитель который сейчас выбран пользователем для проекта
# Необходимые данные для соединения с хранилищем Имён производителей Кабелей
Guidstr_ManufNames_ManufacturerSelectCable = 'fc725aed-20ed-4d44-984c-522c476e3abc'
SchemaName_for_ManufNames_ManufacturerSelectCable = 'ManufNames_ManufacturerSelect_StorageCable'
FieldName_for_ManufNames_ManufacturerSelectCable = 'ManufNames_ManufacturerSelect_listCable' # отдельное поле для хранения информации имён производителей

# Необходимые данные для соединения с Хранилищами данных по производителю кабелей
Guidstr_Cable_ListDB_ManufacturerSelect = '895e7aef-18fd-4e6c-b8f2-73af53f04aba'
SchemaName_for_Cable_ListDB_ManufacturerSelect = 'Cable_ListDB_ManufacturerSelect_Storage'
FieldName_for_Cable_ListDB_ManufacturerSelect = 'Cable_ListDB_ManufacturerSelect_list' # отдельное поле для хранения информации обо всех кабелях

'''

#_______________________________________________________________________________________________________________________________________________________________________________________












#_______________________________________________________________________________________________________________________________________________________________________________________

# Из C# мы получаем списки с конкретным типом данных string. И почему-то к таким спискам нельзя применять некоторые команды, например .count(i.Name)
# поэтому для корректной работы придётся пересобрать все входящие списки заново. Для этого нужен вспомогательный список CS_help = []

CS_help = []
[CS_help.append(i) for i in avt_family_names]
avt_family_names = []
[avt_family_names.append(i) for i in CS_help]

CS_help = []
[CS_help.append(i) for i in using_auxiliary_cables]
using_auxiliary_cables = []
[using_auxiliary_cables.append(i) for i in CS_help]

CS_help = []
[CS_help.append(i) for i in using_any_avtomats]
using_any_avtomats = []
[using_any_avtomats.append(i) for i in CS_help]

CS_help = []
[CS_help.append(i) for i in using_reserve_avtomats]
using_reserve_avtomats = []
[using_reserve_avtomats.append(i) for i in CS_help]



#____________________________________________________________________________________________________















#_________________________Функции необходимые для работы программы_________________________________________________________________________________________________

# Функция по определению материала проводника (специальная для этой проги токов КЗ).
# Определяемся какой проводник используется: медный или алюминиевый. Al примем если марка кабеля начинается с буквы "А". В остальных случая медный..
# Пример обращения: Is_Cu_or_Al_forSC('АПвБбШп')
# На выходе из функции True если медь, False если алюминий
def Is_Cu_or_Al_forSC (wirebrandstr):
	if wirebrandstr[0] == 'А' or wirebrandstr[0] == 'а' or wirebrandstr[0] == 'A' or wirebrandstr[0] == 'a':
		exitbool = False
	else:
		exitbool = True
	return exitbool	


# функция получения индексов одинаковых элементов в списке
# на входе: элемент который ищем, список в котором ищем. На выходе список с индексами найденных элементов. Например: [2, 4]. Если совпадений не найдено - на выходе пустой список: []
def Get_coincidence_in_list (search_element, search_list):
	index_list = []
	for n, i in enumerate(search_list):
		if i == search_element:
			index_list.append(n)
	return index_list


# функция удаляет элементы из списка по указанным индексам
# на входе: список нужных индексов (например: [2, 4],) и список из которого их будем удалять (например [1, 2, 3, 4, 5]). 
# На выходе: список без удалённых элементов (например [1, 2, 4]). 
# Внимание! Входящий список deleting_list переобъявляется!! 
# То есть то, что мы подали на вход, после работы этой функции уже не будет содержать удалённых элементов.
def Delete_indexed_elements_in_list (indexes_list, deleting_list):
	a = (len(deleting_list)-1)
	while a >= 0:
		for i in indexes_list:
			if a == i:
				deleting_list.pop(a)
		a = a - 1

	return deleting_list


# Функция интерполяции
def interpol (x1, x2, x3, y1, y3):
	y2 = ((x2 - x1)*(y3 - y1)) / (x3 - x1) + y1
	return y2

# Функция поиска удельного сопротивления кабеля по его сечению (по данным из Настроек Теслы)
# На входе: искомое сечение, список сечений, список удельных сопротивлений
# На выходе: значение удельного сопротивления float
# Пример обращения: Find_CableResistance(2.5, Sections_of_cables_DB, Resistance_Active_Specific_for_copper_cables_DB)
def Find_CableResistance (section_to_find, Sections_of_cables_DB, List_of_resistances):
	for n, i in enumerate(Sections_of_cables_DB):
		if i == section_to_find:
			sec_index = n # индекс найденного сечения
			break
	Exit_Resistance = float(List_of_resistances[sec_index])
	return Exit_Resistance


# Функция проверки правильности введённых данных. Что введены исключительно цифры где надо.
# На вводе List_for_Check - список со строковыми значениями которые будем проверять на возможность перевода в числовые
# На выходе True, либо строки с ошибками
def Is_Float_InWindows (List_for_Check):
	Exit_var = True
	notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в списке у нас не число, а что-то другое
	for i in List_for_Check:
		try:
			float(i)
		except SystemError:
			Exit_var = 'Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули'
			notfloat = notfloat + 1
		except ValueError:
			Exit_var = 'Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки'
			notfloat = notfloat + 1
	return Exit_var



# Функция создаёт текст в указанной пользователем точке текущего вида
# На входе textstring - что нужно написать. Пример CreateText('Это мощь\nмощнецкая')
# На выходе созданный объект текст
def CreateText (textstring):
	textLoc = uidoc.Selection.PickPoint('Укажите точку куда вставить текст.') # <Autodesk.Revit.DB.XYZ object at 0x000000000000002B [(0.793950324, -0.120651318, 0.000000000)]>
	defaultTextTypeId = doc.GetDefaultElementTypeId(ElementTypeGroup.TextNoteType) # <Autodesk.Revit.DB.ElementId object at 0x000000000000002C [48349]>
	noteWidth = .2 # 0.20000000000000001
	minWidth = TextNote.GetMinimumAllowedWidth(doc, defaultTextTypeId) # 0.001
	maxWidth = TextNote.GetMaximumAllowedWidth(doc, defaultTextTypeId) # 7.0
	if noteWidth < minWidth:
		noteWidth = minWidth
	elif noteWidth > maxWidth:
		noteWidth = maxWidth
	# 0.20000000000000001
	opts = TextNoteOptions(defaultTextTypeId) # <Autodesk.Revit.DB.TextNoteOptions object at 0x000000000000002D [Autodesk.Revit.DB.TextNoteOptions]>
	opts.HorizontalAlignment = HorizontalTextAlignment.Left # Autodesk.Revit.DB.HorizontalTextAlignment.Left
	opts.Rotation = 0
	t = Transaction(doc, 'Create text')
	t.Start()
	textNote = TextNote.Create(doc, doc.ActiveView.Id, textLoc, noteWidth, textstring, opts)
	t.Commit()	






# Функция чтения всех полей из ExtensibleStorage. Работает только со строковами списками.
# Пример обращения Read_all_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject)
# важен тип входных данных:_______________________________________as Guid________ as Object______
# На выходе список из нескольких подсписков вида: ['Cables_trays_reduction_factor_CR', ['1.0', '0.87', '0.8', '0.77', '0.75', '0.73', '0.71', '0.7', '0.68'], 'Circuit_breakers_reduction_factor_CR', ['1.0', '0.8', '0.8', '0.7', '0.7', '0.6', '0.6', '0.6', '0.6', '0.5'], 'Current_breaker_nominal_CR', ['10', '16', '20', '25', '32', '40', '50', '63', '80', '100', '125', '160', '200', '250', '315', '400', '500', '630', '700', '800', '900', '1000'], 'Currents_for_multiwire_aluminium_cables_CR', ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858', '972'], 'Currents_for_multiwire_copper_cables_CR', ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030', '1143'], 'Currents_for_singlewire_aluminium_cables_CR', ['0', '19.5', '26', '33', '46', '61', '84', '105', '128', '166', '203', '237', '274', '315', '375', '434', '526', '610', '711', '858', '972'], 'Currents_for_singlewire_copper_cables_CR', ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030', '1143'], 'Sections_of_cables_CR', ['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800', '1000'], 'Volt_dropage_coeffitients_CR', ['72', '12', '44', '7.4']]
# где имя поля предшествует спискам со значениями полей
def Read_all_fields_to_ExtensibleStorage (schemaGuid, Object_to_connect_ES):
	Exit_list = [] # выходной список подсписками которого являются все считанные поля Схемы.
	# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
	#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
	#Получаем Schema:
	sch = Schema.Lookup(schemaGuid)
	#Получаем Entity из элемента:
	ent = Object_to_connect_ES.GetEntity(sch)

	# получаем список со всеми полями Схемы. Внимание!! Он сразу сортируется по именам!
	all_fields = []
	for i in sch.ListFields():
		all_fields.append(i)

	# получаем список с именами всех полей Схемы. (тоже сразу сортированный)
	field_names = []
	for i in sch.ListFields():
		field_names.append(i.FieldName)

	# Считываем значения из всех полей
	for i in all_fields:
		Exit_list.append(ent.Get[IList[str]](i))

	# пересоберём подсписки чтобы привести их к нормальному вид
	Exit_list_copy = []
	for i in Exit_list:
		Exit_list_copy.append([j for j in i])

	# Добавим имена полей в качестве подсписок перед списками значений полей (потом так удобнее понимать где какой список)
	Exit_list = []
	for n, i in enumerate(Exit_list_copy):
		Exit_list.append(field_names[n])
		Exit_list.append(i)

	return Exit_list



# Функция записи 10 полей списков строк в ExtensibleStorage
# на входе: Write_10_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject, SchemaName_for_CR, FieldName_for_CR_1, CR_Sections_of_cables_Storagelist, FieldName_for_CR_2, CR_Currents_for_multiwire_copper_cables_Storagelist, .....) 
# важен тип входных данных:_________________________________as Guid__________as Object___________as string___________as string__________as List (элементы д.б. str)_____________
def Write_10_fields_to_ExtensibleStorage (schemaGuid, Object_to_connect_ES, SchSchemaName, SchFieldName1, DataList1, SchFieldName2, DataList2, SchFieldName3, DataList3, SchFieldName4, DataList4, SchFieldName5, DataList5, SchFieldName6, DataList6, SchFieldName7, DataList7, SchFieldName8, DataList8, SchFieldName9, DataList9, SchFieldName10, DataList10):
	sb = SchemaBuilder (schemaGuid) # Построение будет выполняться через «промежуточный» класс SchemaBuilder. Создаем его, используя GUID
	sb.SetReadAccessLevel(AccessLevel.Public) # задаем уровень доступа
	fb1 = sb.AddArrayField(SchFieldName1, str) # Далее создаем поля для хранилища, опять же через промежуточный класс FieldBuilder
	fb2 = sb.AddArrayField(SchFieldName2, str)
	fb3 = sb.AddArrayField(SchFieldName3, str)
	fb4 = sb.AddArrayField(SchFieldName4, str)
	fb5 = sb.AddArrayField(SchFieldName5, str)
	fb6 = sb.AddArrayField(SchFieldName6, str)
	fb7 = sb.AddArrayField(SchFieldName7, str)
	fb8 = sb.AddArrayField(SchFieldName8, str)
	fb9 = sb.AddArrayField(SchFieldName9, str)
	fb10 = sb.AddArrayField(SchFieldName10, str)
	sb.SetSchemaName(SchSchemaName) # Задаем имя для хранилища
	sch = sb.Finish() # И «запекаем» SchemaBuilder, получая Schema

	# Из ранее созданной «Schema» получаем «поля», которые чуть позже используем для считывания значений из элемента. Потребуются имена, под которым мы их создавали:
	field1 = sch.GetField(SchFieldName1)
	field2 = sch.GetField(SchFieldName2)
	field3 = sch.GetField(SchFieldName3)
	field4 = sch.GetField(SchFieldName4)
	field5 = sch.GetField(SchFieldName5)
	field6 = sch.GetField(SchFieldName6)
	field7 = sch.GetField(SchFieldName7)
	field8 = sch.GetField(SchFieldName8)
	field9 = sch.GetField(SchFieldName9)
	field10 = sch.GetField(SchFieldName10)
	#Также создаем объект Entity, в который будем записывать значения полей:
	ent = Entity(sch)

	ent.Set[IList[str]](field1, List[str](DataList1)) # Создаёт список
	ent.Set[IList[str]](field2, List[str](DataList2))
	ent.Set[IList[str]](field3, List[str](DataList3))
	ent.Set[IList[str]](field4, List[str](DataList4))
	ent.Set[IList[str]](field5, List[str](DataList5))
	ent.Set[IList[str]](field6, List[str](DataList6))
	ent.Set[IList[str]](field7, List[str](DataList7))
	ent.Set[IList[str]](field8, List[str](DataList8))
	ent.Set[IList[str]](field9, List[str](DataList9))
	ent.Set[IList[str]](field10, List[str](DataList10))
	#Записываем Entity в элемент:
	t = Transaction(doc, 'Create storage')
	t.Start()
	Object_to_connect_ES.SetEntity(ent)
	t.Commit()




# Функция записи 3 полей списков строк в ExtensibleStorage
# на входе: Write_3_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject, SchemaName_for_CR, FieldName_for_CR_1, CR_Sections_of_cables_Storagelist, FieldName_for_CR_2, CR_Currents_for_multiwire_copper_cables_Storagelist, .....) 
# важен тип входных данных:_________________________________as Guid__________as Object___________as string___________as string__________as List (элементы д.б. str)_____________
def Write_3_fields_to_ExtensibleStorage (schemaGuid, Object_to_connect_ES, SchSchemaName, SchFieldName1, DataList1, SchFieldName2, DataList2, SchFieldName3, DataList3):
	sb = SchemaBuilder (schemaGuid) # Построение будет выполняться через «промежуточный» класс SchemaBuilder. Создаем его, используя GUID
	sb.SetReadAccessLevel(AccessLevel.Public) # задаем уровень доступа
	fb1 = sb.AddArrayField(SchFieldName1, str) # Далее создаем поля для хранилища, опять же через промежуточный класс FieldBuilder
	fb2 = sb.AddArrayField(SchFieldName2, str)
	fb3 = sb.AddArrayField(SchFieldName3, str)
	sb.SetSchemaName(SchSchemaName) # Задаем имя для хранилища
	sch = sb.Finish() # И «запекаем» SchemaBuilder, получая Schema

	# Из ранее созданной «Schema» получаем «поля», которые чуть позже используем для считывания значений из элемента. Потребуются имена, под которым мы их создавали:
	field1 = sch.GetField(SchFieldName1)
	field2 = sch.GetField(SchFieldName2)
	field3 = sch.GetField(SchFieldName3)
	#Также создаем объект Entity, в который будем записывать значения полей:
	ent = Entity(sch)

	ent.Set[IList[str]](field1, List[str](DataList1)) # Создаёт список
	ent.Set[IList[str]](field2, List[str](DataList2))
	ent.Set[IList[str]](field3, List[str](DataList3))
	#Записываем Entity в элемент:
	t = Transaction(doc, 'Create storage')
	t.Start()
	Object_to_connect_ES.SetEntity(ent)
	t.Commit()




# Функция записи токов КЗ в автоматы
# На входе имена соответствующих параметров и значения результатов расчёта токов КЗ, а также имена нужных семейств
# На выходе ничего, просто записали в автомат.
def WriteSC_inAVs (Param_Short_Circuit_3ph, Param_Short_Circuit_1ph, IscRes3ph, IscRes1ph, avt_family_names, using_reserve_avtomats, using_any_avtomats):

	# Пользователь выбирает элементы на схеме
	try:
		pickedObjs = uidoc.Selection.PickObjects(ObjectType.Element, 'Выберите автоматические выключатели')
	except:
		return
	idd = [str(i.ElementId) for i in pickedObjs]
	#если ничего не выбрано, выйти
	if idd == []: 
		return

	#если пользователь что-то выбрал, продолжаем
	if isinstance(idd, list) == True:
		elems = [doc.GetElement(ElementId(int(i))) for i in idd]
	else:
		elems = doc.GetElement(ElementId(int(idd)))

	#Фильтруем общую выборку
	elems_avtomats = [] # все автоматы которые участвуют в электротехнических расчётах
	elems_reserve_avtomats = [] # резервные автоматы. 
	elems_any_avtomats = [] # любые автоматы для схем и вводные. 

	for element in elems:
		if element.Name in avt_family_names: elems_avtomats.append(element)
		elif element.Name in using_reserve_avtomats: elems_reserve_avtomats.append(element)
		elif element.Name in using_any_avtomats: elems_any_avtomats.append(element)


	#сообщение об ошибке которое должно вывестись в следующем модуле
	error_text_in_window = 'Вы не выбрали автоматические выключатели для записи результата. Программа работает только с определёнными семействами автоматических выключателей: ' + ', '.join(avt_family_names + using_reserve_avtomats + using_any_avtomats) + '. И семействами кабелей: ' + '. Пожалуйста, выберите их и запустите расчёт заново.'

	#если не выбраны автоматы, выйти из программы
	if elems_avtomats+elems_reserve_avtomats+elems_any_avtomats == []: 
		TaskDialog.Show('Расчёт токов КЗ', error_text_in_window)
		return

	# Дальше проверим есть ли у автоматов нужные параметры.
	All_selected_avs = elems_avtomats + elems_reserve_avtomats + elems_any_avtomats
	Missing_params_famNames = [] # Список с именами семейств у которых отсутствуют необходимые параметры
	for i in All_selected_avs:
		if Param_Short_Circuit_3ph not in [p.Definition.Name for p in i.Parameters] or Param_Short_Circuit_1ph not in [p.Definition.Name for p in i.Parameters]: 
			if i.Name not in Missing_params_famNames:
				Missing_params_famNames.append(i.Name)
		else:
			t = Transaction(doc, 'Write to QFs')
			t.Start()
			i.LookupParameter(Param_Short_Circuit_3ph).Set(float(IscRes3ph))
			i.LookupParameter(Param_Short_Circuit_1ph).Set(float(IscRes1ph))
			t.Commit()

	Exit_alert = ''
	if len(Missing_params_famNames) > 0:
		Exit_alert = 'У следующих семейств отсутствуют параметры необходимые для записи токов КЗ: ' + ', '.join(Missing_params_famNames) + '. Загрузите последнюю версию этих семейств и перезапустите расчёт.' 
		return TaskDialog.Show('Расчёт токов КЗ', Exit_alert)

	return

	


#______________Выбор элементов пользователем________________________________________________________________________________________
# Функция выбора автоматов и кабелей на схемах с участием пользователя
# На выходе кортеж из трёх списков с элементами: автоматами для схем, кабелями, любыми автоматами для схем
def Elements_Select (avt_family_names, using_auxiliary_cables, using_any_avtomats):

	elems_avtomats = [] # все автоматы которые участвуют в электротехнических расчётах
	elems_auxiliary_cables = [] # семейства кабелей (отдельные). 
	elems_any_avtomats = []  

	Continue = 0 # Вспомогательная переменная

	# Предложим пользователю выбор
	td = TaskDialog('Выбор элементов цепи')
	td.MainContent = 'Выбрать участки цепи для которых будет произведёт расчёт токов КЗ?'
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Выбрать', 'Выберите автоматические выключатели и/или семейства кабелей на схемах')
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Не выбирать', 'Вы сможете внести данные об участках цепи позднее')
	GetUserResult = td.Show()
	if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
		Continue = 1
	elif GetUserResult == TaskDialogResult.CommandLink2:
		return [], [], []


	if Continue == 1:
		# Пользователь выбирает элементы на схеме
		pickedObjs = uidoc.Selection.PickObjects(ObjectType.Element, "Выберите автоматические выключатели и/или семейства кабелей")
		idd = [str(i.ElementId) for i in pickedObjs]


		#сообщение об ошибке которое должно вывестись в следующем модуле
		error_text_in_window = 'Ничего не выбрано.'
		#если ничего не выбрано, выйти из выбора
		if idd == []: 
			TaskDialog.Show('Расчёт токов КЗ', error_text_in_window)
			return [], [], []

		#если пользователь что-то выбрал, продолжаем
		if isinstance(idd, list) == True:
			elems = [doc.GetElement(ElementId(int(i))) for i in idd]
		else:
			elems = doc.GetElement(ElementId(int(idd)))


		#Фильтруем общую выборку
		for element in elems:
			if element.Name in avt_family_names: elems_avtomats.append(element)
			elif element.Name in using_auxiliary_cables: elems_auxiliary_cables.append(element)
			elif element.Name in using_any_avtomats: elems_any_avtomats.append(element)


		#сообщение об ошибке которое должно вывестись в следующем модуле
		error_text_in_window = 'Вы не выбрали автоматические выключатели для расчёта и/или семейства отдельных кабелей. Программа работает только с определёнными семействами автоматических выключателей: ' + ', '.join(avt_family_names) + '. И семействами кабелей: ' + ', '.join(using_auxiliary_cables) + '.'

		#если не выбраны основные автоматы, выйти из программы
		if elems_avtomats == [] and elems_auxiliary_cables == [] and elems_any_avtomats == []: 
			TaskDialog.Show('Расчёт токов КЗ', error_text_in_window)
			return [], [], []


		# Сделаем также проверку на наличие "единичек" в именах автоматов
		wrong_avt_family_names = [] # список с неправильными именами автоматов
		for i in elems:
			for j in avt_family_names:
				if j in i.Name and len(i.Name) != len(j):
					if i.Name not in wrong_avt_family_names:
						wrong_avt_family_names.append(i.Name)

		# отдельная песня для проверки семейств кабелей
		for i in elems:
			for j in using_auxiliary_cables: # только имена семейств с кабелями
				if j in i.Name and len(i.Name) > len(j) and len(i.Name) <= (len(j) + 3):
					if i.Name not in wrong_avt_family_names:
						wrong_avt_family_names.append(i.Name)

		if wrong_avt_family_names != []:
			#TaskDialog.Show('Расчёт схем', 'Внимание! Среди выбранных автоматов есть автоматы с неправильными именами:\n' + '", "'.join(wrong_avt_family_names) + '.\nОни будут исключены из расчётов!') # Показывает окошко в стиле Ревит
			MessageBox.Show('Внимание! Среди выбранных семейств есть семейства с неправильными именами:\n' + '", "'.join(wrong_avt_family_names) + '.\nОни будут исключены из расчётов!', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)

	return elems_avtomats, elems_auxiliary_cables, elems_any_avtomats





# Функция кодирует список со списками в единый список с разделителями для хранения в ES
# На входе список списков вида: [['0', '0', '16', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ['0', '0', '25', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ...]
# На выходе единый список вида: ['0?!?0?!?16?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?0?!?25?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?1?!?16?!?C?!?30?!?2?!?3.5?!?Basic?!?EKF?!?1', '0?!?0?!?16?!?C?!?0?!?1?!?4?!?iC60N?!?Schneider?!?0']
def EncodingListofListsforES (ListofLists):
	hlplist = []
	for i in ListofLists:
		hlpelem = ''
		for j in range(len(i)):	
			hlpelem = hlpelem + i[j]+'?!?'
		hlpelem = hlpelem[0:-3] # удаляем последние '?!?'
		hlplist.append(hlpelem)
	return hlplist

# Функция декодирует список с разделителями из ES в список со списками
# На входе единый список вида: ['0?!?0?!?16?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?0?!?25?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?1?!?16?!?C?!?30?!?2?!?3.5?!?Basic?!?EKF?!?1', '0?!?0?!?16?!?C?!?0?!?1?!?4?!?iC60N?!?Schneider?!?0']
# На выходе список списков вида: [['0', '0', '16', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ['0', '0', '25', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ...]
def DecodingListofListsforES (ListwithSeparators):
	znach1hlp = []
	for i in ListwithSeparators:
		znach1hlp.append(i.split('?!?'))
	return znach1hlp






# Функция достаёт из выбранных пользователем автоматов и кабелей информацию для записи в таблицу участков цепи
# На входе: elems_avtomats, elems_auxiliary_cables в виде: [<Autodesk.Revit.DB.AnnotationSymbol object at 0x000000000000002D [Autodesk.Revit.DB.AnnotationSymbol]>]
# На выходе список списков вида: [['АПвБбШп', '1', '185', '100', 'Кабель от ТП до ВРУ', '0'], ['ВВГнг', '1', '35', '50', '', '0']]
def DecodingAVsandCables (elems_avtomats, elems_auxiliary_cables, Param_Wire_brand, Param_Rays_quantity, Param_Cable_section, Param_Cable_length):
	Exit_list = []
	# Создаём общий список со всеми выбранными автоматами и кабелями
	elems_to_decode = elems_avtomats + elems_auxiliary_cables

	for i in elems_to_decode:
		tmp_memb = [] # текущий член будущего выходного списка
		tmp_memb.append(i.LookupParameter(Param_Wire_brand).AsString())
		if i.LookupParameter(Param_Rays_quantity).AsInteger() == 0:
			tmp_memb.append('1')
		else:
			tmp_memb.append(str(i.LookupParameter(Param_Rays_quantity).AsInteger()))
		tmp_memb.append(str(i.LookupParameter(Param_Cable_section).AsDouble()))
		tmp_memb.append(str(i.LookupParameter(Param_Cable_length).AsDouble()))
		tmp_memb.append(i.LookupParameter(Param_Circuit_number).AsString())
		tmp_memb.append('0') # это будет галочка "Не сохранять"
		Exit_list.append(tmp_memb)

	return Exit_list



# Функция достаёт из выбранных пользователем автоматов информацию для записи в таблицу автоматов
# На входе: elems_avtomats, elems_any_avtomats в виде: [<Autodesk.Revit.DB.AnnotationSymbol object at 0x000000000000002D [Autodesk.Revit.DB.AnnotationSymbol]>]
# На выходе список списков вида: [['1', '630'], ['1', '125.0'], ['2', '16.0'], ['1', '50.0']]
def DecodingAvtomatsNominals (elems_avtomats, elems_any_avtomats, Param_Circuit_breaker_nominal):
	Exit_list = []
	# Создаём общий список со всеми выбранными автоматами и кабелями
	elems_to_decode = elems_avtomats + elems_any_avtomats

	hlp_lst = [] # вспомогательный список с уставками автоматов вида [16.0, 16.0, 50.0, ...], где элементы могут повторяться
	for i in elems_to_decode:
		hlp_lst.append(i.LookupParameter(Param_Circuit_breaker_nominal).AsDouble())


	# Теперь создадим список где элементами будут подсписки с уникальными уставками автоматов плюс количество таких уникальных элементов.
	# То есть второй элемент в каждом подсписке будет количеством.
	# то есть нужно отфильтровать hlp_lst выкинув повторяющиеся и дописав количество.
	hlp_lst_withcount = []
	unique_count = [] # вспомогательный список состоящий только из количеств одинаковых элементов

	Copy_hlp_lst = [] # вспомогательный список - точная копия исходного списка. Но просто так его объявить нельзя, иначе почему-то все действия с копией будут автоматически происходить с оригиналом. Поэтому пересобираем список командой append.
	for i in hlp_lst:
		Copy_hlp_lst.append(i)

	for i in hlp_lst:
		for j in Copy_hlp_lst:
			if i == j:
				hlp_lst_withcount.append(j) # добавляем совпавший элемент к итоговому списку
				cur_indx = Get_coincidence_in_list (j, Copy_hlp_lst) # получаем индексы совпавших элементов
				unique_count.append(len(cur_indx)) # формируем список с количеством одинаковых элементов
				Delete_indexed_elements_in_list (cur_indx, Copy_hlp_lst) # удаляем совпавшие элементы из списка Copy_hlp_lst

	for i in hlp_lst_withcount:
		Exit_list.append([])
	# добавляем количество одинаковых элементов в каждый подсписок итогового списка
	for n, i in enumerate(hlp_lst_withcount):
		Exit_list[n].append(str(unique_count[n]))
		Exit_list[n].append(str(i))
		Exit_list[n].append('0') # это будет галочка "Не сохранять"
	# Теперь у нас в списке Exit_list уникальные данные по автоматам и их количество. Пример: [['1', '630'], ['1', '125.0'], ['2', '16.0'], ['1', '50.0']]

	return Exit_list





# Функция считывает данные о траснформаторах и их сопротивлениях из БД и выдаёт на выходе
# актуальный список в виде: [('160', '16.6', '41.7', '45', '135', '135', '135'), ('250', '28.7', '28.7', '28.7', '86.3', '86.3', '86.3'), ('400', '18', '18', '18', '54', '54', '54'), ('630', '14', '14', '14', '42', '42', '42'), ('1000', '8.8', '8.8', '8.8', '26.4', '26.4', '26.4'), ('1600', '5.5', '5.5', '5.5', '16.5', '16.5', '16.5'), ('2500', '3.52', '3.52', '3.52', '10.56', '10.56', '10.56')]
def Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7): 
	# Считываем данные из Хранилища
	ShortCircuit_Settings_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject) # Вид: ['Resistance_Total_Transformer_1phSC_DB', ['135', '86.3', '54', '42', '26.4', '16.5', '10.56'], 'Resistance_Total_Transformer_forward_reverse_DB', ['45', '28.7', '18', '14', '8.8', '5.5', '3.52'], 'Transformer_Power_DB', ['160', '250', '400', '630', '1000', '1600', '2500']]

	# Формируем список для заполнения Формы
	Transformers_Resistance_from_ShortCircuit_Settings = list(zip(ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_1) + 1)], 
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_2) + 1)], # поясню: это обращение к содержимому списка по имени поля в хранилище
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_3) + 1)],
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_4) + 1)],
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_5) + 1)],
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_6) + 1)],
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_7) + 1)],
	))

	return Transformers_Resistance_from_ShortCircuit_Settings


# Функция считывает данные об автоматах и их сопротивлениях из БД и выдаёт на выходе
# актуальный список в виде: 
def Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10): 
	# Считываем данные из Хранилища
	ShortCircuit_Settings_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject) # Вид: 

	# Формируем список для заполнения Формы
	QFs_Resistance_from_ShortCircuit_Settings = list(zip(ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_8) + 1)], 
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_9) + 1)], # поясню: это обращение к содержимому списка по имени поля в хранилище
	ShortCircuit_Settings_Storage_DataList[int(ShortCircuit_Settings_Storage_DataList.index(FieldName_for_ShortCircuit_Settings_10) + 1)]
	))

	return QFs_Resistance_from_ShortCircuit_Settings



# Функция по сохранению данных из окна настроек КЗ
# Пример обращения:
#if Button_Cancel_ShortCircuit_Settings_Form_pushed != 1: # Если кнопка "Cancel" не была нажата
	#ShortCircuit_Settings_Form_Save (Transformers_Resistance_Output, QFs_Resistance_Output, schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)
def ShortCircuit_Settings_Form_Save (Transformers_Resistance_Output, QFs_Resistance_Output, schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10):

	# Сортируем списки по возрастанию
	
	# Запутанная синхронная сортировка по индексам. Скачано отсюда https://ru.stackoverflow.com/questions/599129/%D0%A1%D0%B8%D0%BD%D1%85%D1%80%D0%BE%D0%BD%D0%BD%D0%B0%D1%8F-%D1%81%D0%BE%D1%80%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B0-%D1%81%D0%BF%D0%B8%D1%81%D0%BA%D0%BE%D0%B2-python
	Transformers_Resistance_Output_copy = []
	indexes = sorted(range(len([float(j) for j in Transformers_Resistance_Output[0]])), key=lambda i: [float(j) for j in Transformers_Resistance_Output[0]][i]) # Получаем сортированные индексы первого списка (сортируем по мощностям трансов)
	for i in Transformers_Resistance_Output:
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[0][i] for i in indexes]) # переписываем отсортированные по индексам списки
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[1][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[2][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[3][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[4][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[5][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[6][i] for i in indexes])

	QFs_Resistance_Output_copy = []
	indexes = sorted(range(len([float(j) for j in QFs_Resistance_Output[0]])), key=lambda i: [float(j) for j in QFs_Resistance_Output[0]][i]) # Получаем сортированные индексы первого списка (сортируем по номиналам автоматов)
	for i in QFs_Resistance_Output:
		QFs_Resistance_Output_copy.append([QFs_Resistance_Output[0][i] for i in indexes]) # переписываем отсортированные по индексам списки
		QFs_Resistance_Output_copy.append([QFs_Resistance_Output[1][i] for i in indexes])
		QFs_Resistance_Output_copy.append([QFs_Resistance_Output[2][i] for i in indexes])


	# Пишем данные из окна в Хранилище
	Write_10_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, 
	FieldName_for_ShortCircuit_Settings_1, Transformers_Resistance_Output_copy[0], 
	FieldName_for_ShortCircuit_Settings_2, Transformers_Resistance_Output_copy[1],
	FieldName_for_ShortCircuit_Settings_3, Transformers_Resistance_Output_copy[2], 
	FieldName_for_ShortCircuit_Settings_4, Transformers_Resistance_Output_copy[3],
	FieldName_for_ShortCircuit_Settings_5, Transformers_Resistance_Output_copy[4],
	FieldName_for_ShortCircuit_Settings_6, Transformers_Resistance_Output_copy[5],
	FieldName_for_ShortCircuit_Settings_7, Transformers_Resistance_Output_copy[6],
	FieldName_for_ShortCircuit_Settings_8, QFs_Resistance_Output_copy[0],
	FieldName_for_ShortCircuit_Settings_9, QFs_Resistance_Output_copy[1],
	FieldName_for_ShortCircuit_Settings_10, QFs_Resistance_Output_copy[2]
	)


#____________________________________________________________________________________________________















#_______________________________________________________________________________________________________
# Выборка элементов пользователем
try:
	exit_list = Elements_Select(avt_family_names, using_auxiliary_cables, using_any_avtomats)
	elems_avtomats = exit_list[0] # Список с выбранными автоматами
	elems_auxiliary_cables = exit_list[1] # Список с выбранными кабелями
	elems_any_avtomats = exit_list[2] # Список с выбранными любыми автоматами для схем
except: #Ловим ошибку если пользователь нажал Esc пока выбирал что-то. Autodesk.Revit.Exceptions.OperationCanceledException
	elems_avtomats = []
	elems_auxiliary_cables = []
	elems_any_avtomats = []













#_______________________________________________________________________________________________________


# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html
transGroup = TransactionGroup(doc, "TeslaShortCircuit")
transGroup.Start()






#____________________________________________________________________________________________________













#_______________Коннектимся к Хранилищам________________________________________________
# получаем объект "информация о проекте"
ProjectInfoObject = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).WhereElementIsNotElementType().ToElements()[0] 


#____Работаем с хранилищем Calculation Resourses (CR) из основных настроек Теслы_____________________________________

# При первом запуске этой команды в Настройках Теслы может не быть данных об удельных сопротивлениях кабелей.
# Поэтому пока Пользователь не зашёл в основные Настройки, тут мы будем пользоваться данными по умолчанию.

schemaGuid_for_CR = System.Guid(Guidstr_CR) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
schCR = Schema.Lookup(schemaGuid_for_CR)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if schCR is None or ProjectInfoObject.GetEntity(schCR).IsValid() == False: # Проверяем есть ли ExtensibleStorage. 
# Если ExtensibleStorage с указанным guid'ом отсутствет, то используем значения по умолчанию (ничего в это хранилище не пишем!)
	Sections_of_cables_DB = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630, 800, 1000]
	# Список удельных сопротивлений кабелей (данные по умолчанию)
	# https://rusenergetics.ru/polezno-znat/soprotivlenie-mednogo-provoda-tablitsa
	# https://raschet.info/spravochnye-tablicy-soprotivlenij-elementov-seti-0-4-kv/
	# Данные по умолчанию взяты из картинки в папке "О токах КЗ".
	# Активные удельные сопротивления медных кабелей (мОм/м)
	Resistance_Active_Specific_for_copper_cables_DB = [13.35, 8.0, 5.0, 3.33, 2.0, 1.25, 0.8, 0.57, 0.4, 0.29, 0.21, 0.17, 0.13, 0.11, 0.08, 0.07, 0, 0, 0, 0, 0]
	# Активные удельные сопротивления алюминиевых кабелей (мОм/м)
	Resistance_Active_Specific_for_aluminium_cables_DB = [22.2, 13.3, 8.35, 5.55, 3.33, 2.08, 1.33, 0.95, 0.67, 0.48, 0.35, 0.28, 0.22, 0.18, 0.15, 0.12, 0, 0, 0, 0, ]
	# Индуктивные удельные сопротивления медных и алюминиевых кабелей проложенных в трубах (мОм/м)
	Resistance_Inductive_Specific_for_all_cables_DB = [0.11, 0.09, 0.1, 0.09, 0.07, 0.07, 0.07, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0, 0, 0, 0, 0]
	# Напряжения с которыми работает программа (В):
	U3f = 380.0
	U1f = 220.0
else: # Если с Хранилищем всё в порядке, то считываем данные оттуда
	# Считываем данные из Хранилища
	CRF_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject)	
	# Вытаскиваем из этого списка нужные нам значения:
	Sections_of_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)] # выдаёт список с сечениями кабелей
	Resistance_Active_Specific_for_copper_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_13) + 1)]
	Resistance_Active_Specific_for_aluminium_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_14) + 1)]
	Resistance_Inductive_Specific_for_all_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_15) + 1)]
	# Переведём строковые значения в цифровые
	Sections_of_cables_DB = [float(i) for i in Sections_of_cables_DB]
	Resistance_Active_Specific_for_copper_cables_DB = [float(i) for i in Resistance_Active_Specific_for_copper_cables_DB]
	Resistance_Active_Specific_for_aluminium_cables_DB = [float(i) for i in Resistance_Active_Specific_for_aluminium_cables_DB]
	Resistance_Inductive_Specific_for_all_cables_DB = [float(i) for i in Resistance_Inductive_Specific_for_all_cables_DB]
	# Забираем напряжение
	U3f = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_12) + 1)]][0]
	U1f = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_12) + 1)]][1]






#____Работаем с хранилищем для расчётов токов КЗ_____________________________________

schemaGuid_for_ShortCircuit_Settings = System.Guid(Guidstr_ShortCircuit_Settings) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
sch_ShortCircuit_Settings = Schema.Lookup(schemaGuid_for_ShortCircuit_Settings)


# Данные по умолчанию
# Номинальные мощности трансформаторов (в строгом соответствии с их сопротивлениями) (кВА)
Transformer_Power_DB = [160, 250, 400, 630, 1000, 1600, 2500]
# Расчётные сопротивления трансформаторов (мОм) (по схеме тругольник-звезда). (По pdf'ке в папке о токах КЗ) Zт.
# Прямой и обратной последовательностей (взято отсюда https://www.proektant.org/index.php?topic=42604.0):
Resistance_r1t_Transformer_forward_reverse_DB = [16.6, 9.4, 5.9, 3.4, 1.9, 1.1, 0.64]
Resistance_x1t_Transformer_forward_reverse_DB = [41.7, 27.2, 17, 13.5, 8.6, 5.4, 3.46]
Resistance_z1t_Transformer_forward_reverse_DB = [45, 28.7, 18, 14, 8.8, 5.5, 3.52]
# Сопротивление току однофазного КЗ (мОм):
Resistance_r1_1t_Transformer_1phSC_DB = [49.8, 28.2, 17.7, 10.2, 5.7, 3.3, 1.92]
Resistance_x1_1t_Transformer_1phSC_DB = [125, 81.6, 51, 40.5, 25.8, 16.2, 10.38]
Resistance_z1_1t_Transformer_1phSC_DB = [135, 86.3, 54, 42, 26.4, 16.5, 10.56]

# Общий список
Transformers_Resistance_from_ShortCircuit_Settings_By_Default = list(zip([str(i) for i in Transformer_Power_DB], 
[str(i) for i in Resistance_r1t_Transformer_forward_reverse_DB],
[str(i) for i in Resistance_x1t_Transformer_forward_reverse_DB],
[str(i) for i in Resistance_z1t_Transformer_forward_reverse_DB],
[str(i) for i in Resistance_r1_1t_Transformer_1phSC_DB],
[str(i) for i in Resistance_x1_1t_Transformer_1phSC_DB],
[str(i) for i in Resistance_z1_1t_Transformer_1phSC_DB]
))


# Сопротивления катушек автоматов (по умолчанию по ГОСТ 50270-92 приложению 6)
QF_Rated_current = [50, 70, 100, 140, 200, 400, 600, 1000, 1600, 2500, 4000]
QF_Resistance_rkv = [7, 3.5, 2.15, 1.3, 1.1, 0.65, 0.41, 0.25, 0.14, 0.13, 0.1]
QF_Resistance_xkv = [4.5, 2, 1.2, 0.7, 0.5, 0.17, 0.13, 0.1, 0.08, 0.07, 0.05]

QFs_Resistance_from_ShortCircuit_Settings_By_Default = list(zip([str(i) for i in QF_Rated_current], 
[str(i) for i in QF_Resistance_rkv],
[str(i) for i in QF_Resistance_xkv]
))
'''
FieldName_for_ShortCircuit_Settings_8 = 'QF_Rated_current'
FieldName_for_ShortCircuit_Settings_9 = 'QF_Resistance_rkv'
FieldName_for_ShortCircuit_Settings_10 = 'QF_Resistance_xkv'

'''


# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if sch_ShortCircuit_Settings is None or ProjectInfoObject.GetEntity(sch_ShortCircuit_Settings).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки токов КЗ', 'Исходные данные для расчётов не найдены.\n Будут созданы данные по умолчанию.')
	# Пишем данные по умолчанию в Хранилище
	Write_10_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, 
	FieldName_for_ShortCircuit_Settings_1, [str(i) for i in Transformer_Power_DB], 
	FieldName_for_ShortCircuit_Settings_2, [str(i) for i in Resistance_r1t_Transformer_forward_reverse_DB],
	FieldName_for_ShortCircuit_Settings_3, [str(i) for i in Resistance_x1t_Transformer_forward_reverse_DB],
	FieldName_for_ShortCircuit_Settings_4, [str(i) for i in Resistance_z1t_Transformer_forward_reverse_DB],
	FieldName_for_ShortCircuit_Settings_5, [str(i) for i in Resistance_r1_1t_Transformer_1phSC_DB],
	FieldName_for_ShortCircuit_Settings_6, [str(i) for i in Resistance_x1_1t_Transformer_1phSC_DB],
	FieldName_for_ShortCircuit_Settings_7, [str(i) for i in Resistance_z1_1t_Transformer_1phSC_DB],
	FieldName_for_ShortCircuit_Settings_8, [str(i) for i in QF_Rated_current],
	FieldName_for_ShortCircuit_Settings_9, [str(i) for i in QF_Resistance_rkv],
	FieldName_for_ShortCircuit_Settings_10, [str(i) for i in QF_Resistance_xkv]
	)



# Считываем данные из Хранилища
# О трансформаторах
Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7)
# О сопротивлениях автоматов
QFs_Resistance_from_ShortCircuit_Settings = Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)












#____Работаем с хранилищем настроек в главном окне ShortCircuit_Main_Storage_____________________________________

schemaGuid_for_ShortCircuit_Main_Storage = System.Guid(Guidstr_ShortCircuit_Main) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
sch_ShortCircuit_Main_Storage = Schema.Lookup(schemaGuid_for_ShortCircuit_Main_Storage)

# Здесь у нас в БД будут храниться списки с данными об участках цепи в построчном виде: ?!? - разделитель элементов в подсписках
# ['Марка кабеля?!?Кол-во жил на фазу?!?Сечение?!?Примечание?!?Сохранить(да/нет - 1 или 0)', ....]
# Формируем список по умолчанию. В нём для примера будет одна строка с данными по кабелю от ВРУ до ТП.
ChainSectionsInfo_DB = EncodingListofListsforES ([['АПвБбШп', '1', '185', '100', 'Кабель от ТП до ВРУ', '1']]) # Вид по умолчанию [u'АПвБбШп?!?1?!?185?!?100?!?Кабель от ТП до ВРУ?!?1']

# А также делаем список со всякими другими сохранёнными настройками. Например выбранным номиналом трансформатора.
DifSettings_Info_DB = EncodingListofListsforES([['1000'], ['0.1'], ['1.0']])
DifSettings_Info_byDefault = [['1000'], ['0.1'], ['1.0']]
# 0-член - номинал трансформатора
# 1-член - Активное сопротивление контактных соединений (мОм). Кабелей. (по пособию по расчёту токов КЗ стр. 63)
# 2-член - Активное сопротивление контактных соединений (мОм). Коммутационных аппаратов.

# А это список с автоматами в расчётном участке цепи. FieldName_for_ShortCircuit_Main_3 = 'QFsCount_Info_DB'
QFsCount_Info_DB = EncodingListofListsforES ([['1', '630', '1']])

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if sch_ShortCircuit_Main_Storage is None or ProjectInfoObject.GetEntity(sch_ShortCircuit_Main_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	#TaskDialog.Show('Настройки', 'Настройки программы не найдены или были повреждены.\n Будут созданы настройки по умолчанию.')
	# Пишем в хранилище
	Write_3_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Main_Storage, ProjectInfoObject, SchemaName_for_ShortCircuit_Main, FieldName_for_ShortCircuit_Main_1, List[str](ChainSectionsInfo_DB), FieldName_for_ShortCircuit_Main_2, List[str](DifSettings_Info_DB), FieldName_for_ShortCircuit_Main_3, List[str](QFsCount_Info_DB))

# Если ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
tmp_lst = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Main_Storage, ProjectInfoObject) # выдаёт ['ChainSectionsInfo_DB', [u'АПвБбШп?!?1?!?185?!?100?!?Кабель от ТП до ВРУ?!?1'], 'DifSettings_Info_DB', ['1000']]
# Объявим нужные нам в дальнейшем переменные:
# Список для таблицы с участками цепи
ChainSectionsInfo_DB = DecodingListofListsforES(tmp_lst[int(tmp_lst.index(FieldName_for_ShortCircuit_Main_1) + 1)]) # поясню: это обращение к содержимому списка по имени поля в хранилище
# Получим список вида: [['АПвБбШп', '1', '185', '100', 'Кабель от ТП до ВРУ', '1']]

# Список с прочими настройками главного окна
DifSettings_Info_DB = DecodingListofListsforES(tmp_lst[int(tmp_lst.index(FieldName_for_ShortCircuit_Main_2) + 1)]) # Получим [['1000']]

# Список с количеством и номиналами автоматов в участке цепи
QFsCount_Info_DB = DecodingListofListsforES(tmp_lst[int(tmp_lst.index(FieldName_for_ShortCircuit_Main_3) + 1)]) 

#_______________________________________________________________________________________________________________________________________________________________________________________










#_____________________________________________________Работа с хранилищем имён производителей кабелей____________________________________________________________________


# Функции, необходимые для работы с производителями кабелей
# Функция по считыванию данных из хранилища по именам производителя кабелей. (такая же как в команде ManufacturerSelectCable.py)
# На выходе: Вид: [['EKF', 'AV_Averes', 'AV_Basic', 'AV_PROxima', 'EQ_Basic', 'EQ_Averes', 'EQ_PROxima'], [u'(нет производителя)']]
def ReadES_ManufacturerSelect (schemaGuid_for_ManufNames_ManufacturerSelect, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelect):
	# Считываем данные о последнем использованном элементе из Хранилища
	#Получаем Schema:
	sch1 = Schema.Lookup(schemaGuid_for_ManufNames_ManufacturerSelect)
	#Получаем Entity из элемента:
	ent1 = ProjectInfoObject.GetEntity(sch1)
	#Уже знакомым способом получаем «поля»:
	field2 = sch1.GetField(FieldName_for_ManufNames_ManufacturerSelect)
	#Для считывания значений используем метод Entity.Get:
	znach2 = ent1.Get[IList[str]](field2) 

	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znach2]
	znach2 = []
	[znach2.append(i) for i in CS_help] 
	# Перекодируем его в список со списками:
	CS_help = []
	CS_help = DecodingListofListsforES(znach2)
	znach2 = []
	[znach2.append(i) for i in CS_help] # вид: 

	return znach2


# Функция по декодированию данных из XML и хранилища если там хранится строка. (такая же как в команде ManufacturerSelectCable.py)
# На входе закодированная строка
# На выходе нормальный список списков: [[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]
def Data_DecodingXML (inputstring):
	Exit_listoflists = [] # Выходной список

	ZeroLevel_splites_lst = inputstring.split('@@??@@') # Разбивка 0-го уровня

	for i in ZeroLevel_splites_lst:
		hlp_lstzero = []
		FirstLevel_splites_lst = i.split('@@!!@@') # Разбивка 1-го уровня. Вид: [u'2.5<<&&>>4<<&&>>6<<@@>>30<<&&>>40<<&&>>51<<@@>>25<<&&>>34<<&&>>43<<@@>>25<<&&>>34<<&&>>43<<@@>>8<<&&>>5<<&&>>3.33<<@@>>0.09<<&&>>0.1<<&&>>0.09<<@@>>Cu<<&&>>Cu<<&&>>Cu&&??&&ВВГнг<<&&>>ВВГнг<<@@>>3<<&&>>1<<@@>>1.5<<&&>>70<<@@>>123.499<<&&>>4885.613<<@@>>8.82<<&&>>40.15<<@@>>0.2<<&&>>0.9&&??&&ВВГнг&&??&&тут и так всё ясно&&??&&777&&??&&True&&??&&Строительство&&??&&Кольчугино', u'2.5<<&&>>4<<&&>>6<<@@>>29<<&&>>39<<&&>>50<<@@>>24<<&&>>33<<&&>>42<<@@>>24<<&&>>33<<&&>>42<<@@>>10<<&&>>7<<&&>>4<<@@>>0.1<<&&>>0.12<<&&>>0.1<<@@>>Al<<&&>>Al<<&&>>Al&&??&&АВВГнг<<&&>>АВВГнг<<@@>>3<<&&>>1<<@@>>1.5<<&&>>70<<@@>>126<<&&>>4900<<@@>>9.5<<&&>>43<<@@>>0.3<<&&>>1.1&&??&&АВВГнг&&??&&тут и так всё ясно но алюминий&&??&&555&&??&&False&&??&&Строительство&&??&&Кольчугино', u'2.5<<&&>>4<<&&>>6<<@@>>28<<&&>>38<<&&>>49<<@@>>23<<&&>>32<<&&>>41<<@@>>23<<&&>>32<<&&>>41<<@@>>9<<&&>>6<<&&>>3<<@@>>0.08<<&&>>0.11<<&&>>0.08<<@@>>Cu<<&&>>Cu<<&&>>Cu&&??&&КПвПпБП<<&&>>КПвПпБП<<@@>>3<<&&>>1<<@@>>1.5<<&&>>70<<@@>>110<<&&>>4700<<@@>>7.5<<&&>>40<<@@>>0.2<<&&>>0.75&&??&&КПвПпБП&&??&&вот так-то&&??&&888&&??&&True&&??&&Нефтегазовая&&??&&Кольчугино']
		for j in FirstLevel_splites_lst:
			hlp_lst = []
			# Надо разбить входную строку на подсписки. Их разделение взять по маркеру '$$@@$$'
			SecondLevel_splites_lst = j.split('&&??&&') # ['2.5<<&&>>4<<&&>>6<<@@>>1<<&&>>1<<&&>>1<<@@>>2<<&&>>2<<&&>>2<<@@>>3<<&&>>3<<&&>>3<<@@>>4<<&&>>4<<&&>>4<<@@>>5<<&&>>5<<&&>>5<<@@>>6<<&&>>6<<&&>>6', u'ВВГнг<<&&>>ВВГнг<<@@>>3<<&&>>1<<@@>>2.5<<&&>>4<<@@>>100<<&&>>400<<@@>>200<<&&>>500<<@@>>300<<&&>>600', u'ВВГнг', u'ясен пень', '777', 'True', u'линейка 1', u'Кольчуга']
			# Теперь 0-й элемент списка нужно тоже превратить в список с подсписками. Это всегда данные по сечениям кабелей.
			ThirdLevel_splites_lst1 = SecondLevel_splites_lst[0].split('<<@@>>') # ['2.5<<&&>>4<<&&>>6', '1<<&&>>1<<&&>>1', '2<<&&>>2<<&&>>2', '3<<&&>>3<<&&>>3', '4<<&&>>4<<&&>>4', '5<<&&>>5<<&&>>5', '6<<&&>>6<<&&>>6', '7<<&&>>7<<&&>>7', '8<<&&>>8<<&&>>8', '9<<&&>>9<<&&>>9']
			# И теперь каждый его элемент тоже превратить в подсписок
			FourthLevel_splites_lst1 = []
			for i in ThirdLevel_splites_lst1:
				FourthLevel_splites_lst1.append(i.split('<<&&>>')) # [['2.5', '4', '6'], ['1', '1', '1'], ['2', '2', '2'], ['3', '3', '3'], ['4', '4', '4'], ['5', '5', '5'], ['6', '6', '6']]
			# И 1-й элемент это тоже всегда список с подписками (конкретные сечения, диаметры, массы)
			ThirdLevel_splites_lst2 = SecondLevel_splites_lst[1].split('<<@@>>') # ['2.5<<&&>>4<<&&>>6', '1<<&&>>1<<&&>>1', '2<<&&>>2<<&&>>2', '3<<&&>>3<<&&>>3', '4<<&&>>4<<&&>>4', '5<<&&>>5<<&&>>5', '6<<&&>>6<<&&>>6', '7<<&&>>7<<&&>>7', '8<<&&>>8<<&&>>8', '9<<&&>>9<<&&>>9']
			# И теперь каждый его элемент тоже превратить в подсписок
			FourthLevel_splites_lst2 = []
			for i in ThirdLevel_splites_lst2:
				FourthLevel_splites_lst2.append(i.split('<<&&>>')) # [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['2.5', '4'], ['100', '400'], ['200', '500'], ['300', '600']]
			# А теперь собираем нормальный список из разбитых:
			hlp_lst = [FourthLevel_splites_lst1] + [FourthLevel_splites_lst2] + SecondLevel_splites_lst[2:]  # Вид: [[['2.5', '4', '6'], ['1', '1', '1'], ['2', '2', '2'], ['3', '3', '3'], ['4', '4', '4'], ['5', '5', '5'], ['6', '6', '6']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['2.5', '4'], ['100', '400'], ['200', '500'], ['300', '600']], u'ВВГнг', u'ясен пень', '777', 'True', u'линейка 1', u'Кольчуга']
			hlp_lstzero.append(hlp_lst) # Вид: [[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]
		Exit_listoflists.append(hlp_lstzero)

	return Exit_listoflists



# Функция считывания их хранилища Строки String (такая же как в команде ManufacturerSelectCable.py)
def ReadString_from_ExtensibleStorage (schemaGuid, ProjectInfoObject, SchFieldName):
	# Считываем данные о последнем использованном элементе из Хранилища
	#Получаем Schema:
	sch1 = Schema.Lookup(schemaGuid)
	#Получаем Entity из элемента:
	ent1 = ProjectInfoObject.GetEntity(sch1)
	#Уже знакомым способом получаем «поля»:
	field2 = sch1.GetField(SchFieldName)
	#Для считывания значений используем метод Entity.Get:
	znach2 = ent1.Get[str](field2) 
	return znach2



# Функция определения материала проводника у конкретного кабеля производителя
# Чтоб тестить curr_cable_to_find = [u'ВВГнг(А)-LSLTx', '1', '4.0', '11.0', u'ЩР-1.2-2', '1']
# На выходе из функции True если медь, False если алюминий. Или строка '(нет производителя)' если производитель не выбран, или "не найдена марка кабеля", если нет такой марки у производителя
def Is_Cu_or_Al_withCabManufSC (curr_cable_to_find, Wires_List_UsedinModel):
	wirebrandstr = curr_cable_to_find[0] # Марка проводника в виде строки. Вид: u'ППГнг(А)-HF'
	if Wires_List_UsedinModel == []: # Если нет производителя
		exitbool = '(нет производителя)'
	for i in Wires_List_UsedinModel: 
		# i вида: [[['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'], ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22'], ['4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'], ['5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']], [[u'ВВГнг(А) (N, PE)', u'ВВГнг(А) ок PE', u'ВВГнг(А)', u'ВВГнг(А)', u'ВВГнг(А)'], ['1', '1', '1', '1', '1'], ['1.5', '2.5', '4', '6', '10'], ['1', '2', '3', '4', '5'], ['2', '3', '4', '5', '6'], ['3', '4', '5', '6', '7']], u'ВВГнг(А)', u'Кабели силовые с пластмассовой изоляцией, в том числе экранированные, в оболочке из поливинилхлоридного пластиката пониженной горючести. ', '-', 'True', u'Строительство', u'Холдинг Кабельный Альянс', 'Cu']
		if i[2] == wirebrandstr:
			if i[8] == 'Al':
				exitbool = False
			else:
				exitbool = True
			break
		else:
			exitbool = 'Не найдена марка кабеля'
	return exitbool	



# Теперь нам нужна функция которая будет переобъявлять списки с токами и сечениями которые у нас были по умолчанию из Настроек.
# На входе текущий кабель для расчёта вида: [u'ВВГнг(А)-LSLTx', '1', '4.0', '11.0', u'ЩР-1.2-2', '1']
#, список используемых сечений производителя, список используемых марок кабелей производителя, логическая переменная "вернуть как было в настройках Теслы"
# На выходе марка кабеля которую не нашли, во всех остальных случаях пустая строка
# Или марка не найденного кабеля в виде строки или пустая строка если не был выбран производитель.
# RedeclareToSettings - маркер чтобы переобъявить переменные обратно из Хранилища. Возможные значения True - вернуть к данным из Хранилища. False - не возвращать к данным их Хранилища.
# Если марка кабеля не найдена, то переобъявляем токи обратно из Хранилища.
# Чтоб тестить curr_cable_to_find = [u'ВВГнг(А)-LSLTx', '1', '4.0', '11.0', u'ЩР-1.2-2', '1']
# Чтоб тестить wirebrandstr = 'ВВГнг(А)'  RedeclareToSettings = False
def ReDeclareCableCharsResistance (curr_cable_to_find, Wires_List_UsedinModel, UsedWireMarks, RedeclareToSettings):
	global Sections_of_cables_DB # сечения   i[0][0]
	global Resistance_Active_Specific_for_aluminium_cables_DB # активные сопротивления Al кабеля
	global Resistance_Active_Specific_for_copper_cables_DB # активные сопротивления Cu кабеля
	global Resistance_Inductive_Specific_for_all_cables_DB # индуктивные сопротивления всех кабелей

	WireMarkNotFound = '' # Если не нашли нужную марку кабеля, то предупредим об этом пользователя

	# Переобъявление переменных
	if Wires_List_UsedinModel != []: # если вообще производитель выбран
		# Получаем текущую марку проводника
		wirebrandstr = curr_cable_to_find[0] # Марка проводника в виде строки. Вид: u'ППГнг(А)-HF'
		if wirebrandstr not in UsedWireMarks or RedeclareToSettings == True: # Если не нашли такую марку, ИЛИ было сказано вернуться к настройкам, то выведем её (марку) и завершим функцию (вернув значения переменных к данным из Хранилища)
			WireMarkNotFound = wirebrandstr
			Sections_of_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)] # выдаёт список с сечениями кабелей
			Resistance_Active_Specific_for_copper_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_13) + 1)]
			Resistance_Active_Specific_for_aluminium_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_14) + 1)]
			Resistance_Inductive_Specific_for_all_cables_DB = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_15) + 1)]
			# Переведём строковые значения в цифровые
			Sections_of_cables_DB = [float(i) for i in Sections_of_cables_DB]
			Resistance_Active_Specific_for_copper_cables_DB = [float(i) for i in Resistance_Active_Specific_for_copper_cables_DB]
			Resistance_Active_Specific_for_aluminium_cables_DB = [float(i) for i in Resistance_Active_Specific_for_aluminium_cables_DB]
			Resistance_Inductive_Specific_for_all_cables_DB = [float(i) for i in Resistance_Inductive_Specific_for_all_cables_DB]
			return WireMarkNotFound
		# Ищем эту марку в списке используемых кабелей
		for i in Wires_List_UsedinModel:
			if i[2] == wirebrandstr: # Если нашли нужную марку кабеля
				# Переобъявляем переменные.
				Sections_of_cables_DB = [float(j) for j in i[0][0]]
				if i[8] == 'Al': # Если проводник алюминиевый
					Resistance_Active_Specific_for_aluminium_cables_DB = [float(j) for j in i[0][4]]
					Resistance_Inductive_Specific_for_all_cables_DB = [float(j) for j in i[0][5]]
				else: # Если проводник медный
					Resistance_Active_Specific_for_copper_cables_DB = [float(j) for j in i[0][4]]
					Resistance_Inductive_Specific_for_all_cables_DB = [float(j) for j in i[0][5]]
				#break
				return WireMarkNotFound # Выводим пустую строку. А переменные уже переобъявлены.

	else: # Если производитель не выбран, то ничего переобъявлять не будем
		return WireMarkNotFound

'''
Wires_List_UsedinModel # Вид: [[[['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'], ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22'], ['4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'], ['5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']], [[u'ВВГнг(А) (N, PE)', u'ВВГнг(А) ок PE', u'ВВГнг(А)', u'ВВГнг(А)', u'ВВГнг(А)'], ['1', '1', '1', '1', '1'], ['1.5', '2.5', '4', '6', '10'], ['1', '2', '3', '4', '5'], ['2', '3', '4', '5', '6'], ['3', '4', '5', '6', '7']], u'ВВГнг(А)', u'Кабели силовые с пластмассовой изоляцией, в том числе экранированные, в оболочке из поливинилхлоридного пластиката пониженной горючести. ', '-', 'True', u'Строительство', u'Холдинг Кабельный Альянс', 'Cu'], [[['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'], ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22'], ['4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'], ['5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']], [[u'ВВГнг(А) (N, PE)', u'ВВГнг(А) ок PE', u'ВВГнг(А)', u'ВВГнг(А)', u'ВВГнг(А)'], ['1', '1', '1', '1', '1'], ['1.5', '2.5', '4', '6', '10'], ['1', '2', '3', '4', '5'], ['2', '3', '4', '5', '6'], ['3', '4', '5', '6', '7']], u'АВВГнг(А)', u'Кабели силовые с пластмассовой изоляцией, в том числе экранированные, в оболочке из поливинилхлоридного пластиката пониженной горючести. ', '-', 'True', u'Строительство', u'Холдинг Кабельный Альянс', 'Al'], [[['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'], ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22'], ['4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23'], ['5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24']], [[u'ВВГнг(А) (N, PE)', u'ВВГнг(А) ок PE', u'ВВГнг(А)', u'ВВГнг(А)', u'ВВГнг(А)'], ['1', '1', '1', '1', '1'], ['1.5', '2.5', '4', '6', '10'], ['1', '2', '3', '4', '5'], ['2', '3', '4', '5', '6'], ['3', '4', '5', '6', '7']], u'АВВГЭнг(А)', u'Кабели силовые с пластмассовой изоляцией, в том числе экранированные, в оболочке из поливинилхлоридного пластиката пониженной горючести. ', '-', 'True', u'Строительство', u'Холдинг Кабельный Альянс', 'Al']]
UsedWireMarks # Вид: [u'ВВГнг(А)', u'АВВГнг(А)', u'АВВГЭнг(А)']
'''




# Guid для этого хранилища
schemaGuid_for_ManufNames_ManufacturerSelectCable = System.Guid(Guidstr_ManufNames_ManufacturerSelectCable)

#Получаем Schema:
schCable_ManufNames = Schema.Lookup(schemaGuid_for_ManufNames_ManufacturerSelectCable)

# Проверяем корректность хранилища
if schCable_ManufNames is None or ProjectInfoObject.GetEntity(schCable_ManufNames).IsValid() == False:
	# Будем считать что выбрано '(нет производителя)'
	Cable_ManufSelected = '(нет производителя)'
else:
	# объявляем . Вид: [[u'(нет производителя)'], [u'Кольчугинский кабельный завод', 'https://elcable.ru/'], ['VASA', 'https://SAIT.RU']]
	# В этом списке на первой позиции должен стоять выбранный производитель.
	ManufNamesCable_Selected = ReadES_ManufacturerSelect(schemaGuid_for_ManufNames_ManufacturerSelectCable, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelectCable)
	Cable_ManufSelected = ManufNamesCable_Selected[0][0] # Объявляем имя выбранного производителя кабелей. Вид: 'Холдинг Кабельный Альянс'

#___________Достанем списки производителей кабелей из Хранилища_____________
# Guid для этого хранилища
schemaGuid_for_Cable_ListDB_ManufacturerSelectCable = System.Guid(Guidstr_Cable_ListDB_ManufacturerSelect)
#Получаем Schema:
schCable_ListDB = Schema.Lookup(schemaGuid_for_Cable_ListDB_ManufacturerSelectCable)
# Проверяем корректность хранилища
if schCable_ListDB is None or ProjectInfoObject.GetEntity(schCable_ListDB).IsValid() == False:
	# Будем считать что выбрано '(нет производителя)'
	Cable_ManufSelected = '(нет производителя)'
	#TaskDialog.Show('Предупреждение', 'Не найдены характеристики кабелей: "' + Cable_ManufSelected + '". Запустите команду выбора производителя кабельной продукции. Если ошибка повторится, обратитесь к разработчику. Далее при расчётах будут использованы данные по кабелям из основных настроек программы.')
else:
	# объявляем список с кабелями уже из Хранилища данной модели. Вид: [[[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']], [[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', 'QUQUSHKA'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', 'QUQUSHKA'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', 'QUQUSHKA']]]
	Wires_ListDB_from_ExtStorage = Data_DecodingXML(ReadString_from_ExtensibleStorage(schemaGuid_for_Cable_ListDB_ManufacturerSelectCable, ProjectInfoObject, FieldName_for_Cable_ListDB_ManufacturerSelect))



#_______Так же как это сделано в Avcounts.py__________________
Wires_List_UsedinModel = [] # Вид: [[[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]]
UsedWireMarks = [] # список используемых марок кабелей. Вид: [u'ВВГнг', u'КПвПпБП']
if Cable_ManufSelected != '(нет производителя)':
	# Сократим список, оставив в нём только одного выбранного производителя. 
	for i in Wires_ListDB_from_ExtStorage: # i Вид: [[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]
		if i[0][7] == Cable_ManufSelected: # имя производителя
			Wires_List_UsedinModel.append(i)
			break
	# А теперь выкинем кабели неиспользуемые в модели.
	hlp_lstCab = []
	for i in Wires_List_UsedinModel:
		for j in i:
			if j[5] == 'False': # Используется или нет в модели
				pass
			else:
				hlp_lstCab.append(j)
	Wires_List_UsedinModel = []
	Wires_List_UsedinModel = [i for i in hlp_lstCab] # Пересобираем список
	# Объявим список используемых марок кабелей. Вид: [u'ВВГнг', u'КПвПпБП']
	for i in Wires_List_UsedinModel:
		UsedWireMarks.append(i[2])
#_______________________________________________________________
































#______________________________Расчётный модуль__________________________________________

# Функция по расчёту токов КЗ
# На входе:
# Данные из главного окна расчёта токов КЗ
# ChainSectionsInfo_Output в виде [[u'АПвБбШп', '1', '185', '100', u'Кабель от ТП до ВРУ'], [u'ВВГнг(А)-LS', '1', '50.0', '75.0', u'Р .1-2'], [u'ВВГнг(А)-LS', '1', '2.5', '6.0', u'Р .1-22'], [u'ВВГнг(А)-LS', '1', '2.5', '7.0', u'Р .1-24'], [u'ВВГнг(А)-FRLS', '2', '16.0', '5.0', u' -1-6']]
# QFsInfo_Output в виде [['1', '630'], ['1', '125.0'], ['2', '16.0'], ['1', '50.0']]
# DifSettings_Info_Output в виде [['1000'], ['0.1'], ['1.0']]
# Данные из окна настроек токов КЗ
# Данные для соединения с хранилищем этих настроек.
# schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10
# данные по сопротивлениям кабелей
# Resistance_Active_Specific_for_copper_cables_DB 
# Resistance_Active_Specific_for_aluminium_cables_DB 
# Resistance_Inductive_Specific_for_all_cables_DB 
# Sections_of_cables_DB - сечения кабелей
# U3f = 380.0
# U1f = 220.0
# Вид: [('160', '16.6', '41.7', '45', '49.8', '125', '135'), ('250', '9.4', '27.2', '28.7', '28.2', '81.6', '86.3'), ('400', '5.9', '17', '18', '17.7', '51', '54'), ('630', '3.4', '13.5', '14', '10.2', '40.5', '42'), ('1000', '1.9', '8.6', '8.8', '5.7', '25.8', '26.4'), ('1600', '1.1', '5.4', '5.5', '3.3', '16.2', '16.5'), ('2500', '0.64', '3.46', '3.52', '1.92', '10.38', '10.56')]
# Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7) 
# QFs_Resistance_from_ShortCircuit_Settings = Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)

# Формулы расчёта 1ф и 3ф токов КЗ взяты из пособия по расчёту токов КЗ стр. 62,63,64.
# Ссылки так, для справки
# http://rza001.ru/nebrat/52-9-raschety-tokov-kz-po-uproshchennym-formulam-i-raschetnym-krivym
# http://rza001.ru/nebrat/53-10-primer-rascheta-tokov-kz-v-seti-napryazheniem-04-kv
# Онлайн расчёт с формированием отчёта в ворде https://oncad.ru/kz

# На выходе кортеж (3фазный ток КЗ, 1фазный ток КЗ, список марок кабелей, не найденных у производителя): (1.1035357154995893, 0.63888909844713071, [u'АПвБбШп', u'ВВГнг(А)-LSLTx', ''])
# Обращение: ara = Count_SC (U3f, U1f, ChainSectionsInfo_Output, DifSettings_Info_Output, QFsInfo_Output, Sections_of_cables_DB, Resistance_Active_Specific_for_copper_cables_DB, Resistance_Active_Specific_for_aluminium_cables_DB, Resistance_Inductive_Specific_for_all_cables_DB, Transformers_Resistance_from_ShortCircuit_Settings, QFs_Resistance_from_ShortCircuit_Settings)

def Count_SC (U3f, U1f, ChainSectionsInfo_Output, DifSettings_Info_Output, QFsInfo_Output, Transformers_Resistance_from_ShortCircuit_Settings, QFs_Resistance_from_ShortCircuit_Settings):

	'''
	# Поставим проверочку что среди участов цепи нет сечений которых нет в настройках Теслы.
	for i in ChainSectionsInfo_Output:
		if float(i[2]) not in Sections_of_cables_DB:
			TaskDialog.Show('Расчёт КЗ', 'Расчёт невозможен. Среди участков цепи есть сечение ' + i[2] + ' кв.мм, которого нет в Настройках программы. Зайдите в Настройки и добавьте необходимое сечение и сопротивления для него.')
			return 'STOP' # выкинем из программы
	#Перенёс проверку ниже
	'''

	# Будем собирать активные и индуктивные сопротивления всех участков цепи.

	# 1. Сопротивления трансформатора (мОм).
	Rt = 0 # Активное сопротивление прямой и нулевой последновательности тр-ра
	Xt = 0 # Индуктивное сопротивление прямой и нулевой последновательности тр-ра
	Zt = 0 # Полное сопротивление тр-ра при однофазном КЗ
	# Считываем данные из хранилища: Вид: [('160', '16.6', '41.7', '45', '49.8', '125', '135'), ('250', '9.4', '27.2', '28.7', '28.2', '81.6', '86.3'), ('400', '5.9', '17', '18', '17.7', '51', '54'), ('630', '3.4', '13.5', '14', '10.2', '40.5', '42'), ('1000', '1.9', '8.6', '8.8', '5.7', '25.8', '26.4'), ('1600', '1.1', '5.4', '5.5', '3.3', '16.2', '16.5'), ('2500', '0.64', '3.46', '3.52', '1.92', '10.38', '10.56')]
	#Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7)
	# Получаем номинал трансформатора
	Transformer_Nominal = float(DifSettings_Info_Output[0][0]) # (кВА), вид: 1000.0
	# Находим нужные нам сопротивления:
	for i in Transformers_Resistance_from_ShortCircuit_Settings:
		if float(i[0]) == Transformer_Nominal:
			Rt = float(i[1])
			Xt = float(i[2])
			Zt = float(i[6])
			break

	# 2. Сопротивления токовых катушек и переходных сопротивлений подвижных контактов автоматических выключателей (мОм).
	Rkv = 0 # Активное 
	Xkv = 0 # Индуктивное 
	# Считываем данные из хранилища. Вид: [('50', '7', '4.5'), ('70', '3.5', '2'), ('100', '2.15', '1.2'), ('140', '1.3', '0.7'), ('200', '1.1', '0.5'), ('400', '0.65', '0.17'), ('600', '0.41', '0.13'), ('1000', '0.25', '0.1'), ('1600', '0.14', '0.08'), ('2500', '0.13', '0.07'), ('4000', '0.1', '0.05')]
	#QFs_Resistance_from_ShortCircuit_Settings = Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)

	# interpol (x1, x2, x3, y1, y3)
	# Начинаем суммировать сопротивления:
	for i in QFsInfo_Output: # Вид: QFsInfo_Output = [['1', '630'], ['1', '125.0'], ['2', '16.0'], ['1', '50.0']]
		for n, j in enumerate(QFs_Resistance_from_ShortCircuit_Settings):
			if float(i[1]) <= float(QFs_Resistance_from_ShortCircuit_Settings[0][0]): # Если уставка аппарата меньше первого тока из БД
				Rkv = Rkv + float(QFs_Resistance_from_ShortCircuit_Settings[0][1])*float(i[0]) # добавляем текущее активное сопротивление
				Xkv = Xkv + float(QFs_Resistance_from_ShortCircuit_Settings[0][2])*float(i[0]) # добавляем текущее индуктивное сопротивление
				break
			elif float(i[1]) > float(QFs_Resistance_from_ShortCircuit_Settings[-1][0]): # Если уставка аппарата больше последнего тока из БД
				Rkv = Rkv + float(QFs_Resistance_from_ShortCircuit_Settings[-1][1])*float(i[0]) 
				Xkv = Xkv + float(QFs_Resistance_from_ShortCircuit_Settings[-1][2])*float(i[0]) 
				break
			elif float(i[1]) > float(j[0]) and float(i[1]) <= float(QFs_Resistance_from_ShortCircuit_Settings[n+1][0]): # Если уставка аппарата где-то между членами списка из БД
				Rkv = Rkv + interpol(float(j[0]), float(i[1]), float(QFs_Resistance_from_ShortCircuit_Settings[n+1][0]), float(j[1]), float(QFs_Resistance_from_ShortCircuit_Settings[n+1][1]))*float(i[0])
				Xkv = Xkv + interpol(float(j[0]), float(i[1]), float(QFs_Resistance_from_ShortCircuit_Settings[n+1][0]), float(j[2]), float(QFs_Resistance_from_ShortCircuit_Settings[n+1][2]))*float(i[0]) 
				break

	# 3. Суммарное активное сопротивление различных контактов и контактных соединений (мОм).
	Rk = 0 # Активное 
	# будем считать его как по два контакта на каждый кабель и по одному контакту на каждый автомат
	for i in ChainSectionsInfo_Output:
		Rk = Rk + 2*float(DifSettings_Info_Output[1][0])*float(i[1]) # ещё умножаем на количество жил на фазу
	for i in QFsInfo_Output:
		Rk = Rk + float(DifSettings_Info_Output[2][0])*float(i[0]) # ещё умножаем на количество одинаковых автоматов

	# 4. Активное и индуктивное сопротивления кабелей (мОм/м).
	R1kb = 0 # Активное сопротивление прямой последовательности кабелей
	X1kb = 0 # Индуктивное сопротивление прямой последовательности кабелей
	R0kb = 0 # Активное сопротивление нулевой последовательности кабелей (у нас равна прямой)
	X0kb = 0 # Индуктивное сопротивление нулевой последовательности кабелей (у нас равна прямой)

	#!!!!!!!!!!СДЕЛАТЬ ПРОВЕРКУ ЕСЛИ МАРКА КАБЕЛЯ НАЙДЕНА У ПРОИЗВОДИТЕЛЯ, А СЕЧЕНИЕ НЕ НАЙДЕНО!!!!!!!!!!!!!!!
	Wire_marks_not_found_Manuf = [] # Список с марками кабелей не найденных у производителя. Для вывода предупреждения.
	# [[u'АПвБбШп', '1', '185', '100', u'Кабель от ТП до ВРУ'], [u'ВВГнг(А)-LS', '1', '50.0', '75.0', u'Р .1-2'], [u'ВВГнг(А)-LS', '1', '2.5', '6.0', u'Р .1-22'], [u'ВВГнг(А)-LS', '1', '2.5', '7.0', u'Р .1-24'], [u'ВВГнг(А)-FRLS', '2', '16.0', '5.0', u' -1-6']]
	for i in ChainSectionsInfo_Output:
		# Переопределение переменных (сопротивлений и сечений) из-за производителя кабелей
		#!!!!не переобъявляет с первого раза!!!
		Wire_marks_not_found_Manuf.append(ReDeclareCableCharsResistance(i, Wires_List_UsedinModel, UsedWireMarks, False)) # Вид '' если нашли марку или 'ВВГнг(А)' если не нашли
		if float(i[2]) not in Sections_of_cables_DB and Wire_marks_not_found_Manuf[-1] == '': # Если марка кабеля найдена у производителя, но сечение не найдено
			TaskDialog.Show('Расчёт КЗ', 'Расчёт невозможен. Среди участков цепи есть сечение ' + i[2] + ' кв.мм, которого нет у выбранного Производителя. Выберите другую марку кабеля или отключите подбор Производителя кабелей и задайте нужное сечение в Настройках Программы.')
			return 'STOP' # выкинем из программы
		elif float(i[2]) not in Sections_of_cables_DB and Wire_marks_not_found_Manuf[-1] != '': # Если марка не кабеля найдена у производителя, и сечение не найдено в настройках
			TaskDialog.Show('Расчёт КЗ', 'Расчёт невозможен. Среди участков цепи есть сечение ' + i[2] + ' кв.мм, которого нет в Настройках программы. Зайдите в Настройки и добавьте необходимое сечение и сопротивления для него.')
			return 'STOP' # выкинем из программы
		if Is_Cu_or_Al_forSC(i[0]) == False or Is_Cu_or_Al_withCabManufSC(i, Wires_List_UsedinModel) == False: # значит алюминиевый
			# (Удельное сопротивление / кол-во жил на фазу) * длину кабеля
			R1kb = R1kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Active_Specific_for_aluminium_cables_DB)/float(i[1])*float(i[3])
			R0kb = R0kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Active_Specific_for_aluminium_cables_DB)/float(i[1])*float(i[3])
		else: # значит медный
			R1kb = R1kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Active_Specific_for_copper_cables_DB)/float(i[1])*float(i[3])
			R0kb = R0kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Active_Specific_for_copper_cables_DB)/float(i[1])*float(i[3])
		# Индуктивные одинаковые для медных и алюминиевых кабелей
		X1kb = X1kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Inductive_Specific_for_all_cables_DB)/float(i[1])*float(i[3])
		X0kb = X0kb + Find_CableResistance(float(i[2]), Sections_of_cables_DB, Resistance_Inductive_Specific_for_all_cables_DB)/float(i[1])*float(i[3])
		# Для проверки что правильно берутся сопротивления (чтоб тестить)
		#TaskDialog.Show('ARA', 'Участок цепи: ' + ', '.join(i) + ' Не найденные марки кабелей: ' + ', '.join(Wire_marks_not_found_Manuf) + ' Сечения: ' + ', '.join(str(i) for i in Sections_of_cables_DB) + ' Алюм.актив.сопр.: ' + ', '.join(str(i) for i in Resistance_Active_Specific_for_aluminium_cables_DB) + ' Медь.актив.сопр.: ' + ', '.join(str(i) for i in Resistance_Active_Specific_for_copper_cables_DB) + ' Индуктив.сопр.: ' + ', '.join(str(i) for i in Resistance_Inductive_Specific_for_all_cables_DB))


	# считаем токи КЗ (кА)
	# 3-фазный КЗ (начальное действующее значение периодической составляющей тока трехфазного КЗ)
	I3ph = U3f / (math.sqrt(3) * math.sqrt( (Rt+Rkv+Rk+R1kb)**2 + (Xt+Xkv+X1kb)**2 ))
	# 1-фазный КЗ (начальное значение периодической составляющей тока однофазного КЗ)
	I1ph = (math.sqrt(3) * U1f) / ( math.sqrt( (2*(Rt+Rkv+Rk+R1kb) + (Rt+Rkv+Rk+R1kb))**2 + (2*(Xt+Xkv+X1kb) + (Xt+Xkv+X1kb))**2 ) )


	return round(I3ph, 2), round(I1ph, 2), Wire_marks_not_found_Manuf





# Махинации с немодальным окном и возможностью сохранения. Так просто оно не сохраняется из C#. Короче сделал модальным обычным.
# Объявим пустыми списками две главные переменные из окна настроек токов КЗ
# Если они пустые, значит окно настроек КЗ ещё не открывалось, и надо их читать из БД.
# А если не пустые, значит окно настроек КЗ открывалось, и читать надо из него.
global Transformers_Resistance_Output
global QFs_Resistance_Output
Transformers_Resistance_Output = []
QFs_Resistance_Output = []

# Кнопка окна настроек КЗ
global Button_Cancel_ShortCircuit_Settings_Form_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_ShortCircuit_Settings_Form_pushed = 1 # Кнопка Отмена нажата

# Кнопка основного окна 
global Button_Cancel_ShortCircuit_MainForm_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_ShortCircuit_MainForm_pushed = 1 # Кнопка Отмена нажата





#______Основное окно токов КЗ_______________

class ShortCircuit_MainForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._components = System.ComponentModel.Container()
		self._OK_button = System.Windows.Forms.Button()
		self._Cancel_button = System.Windows.Forms.Button()
		self._Calculate_button = System.Windows.Forms.Button()
		self._SC_Settings_button = System.Windows.Forms.Button()
		self._SC_MainForm_ChainSection_dataGridView = System.Windows.Forms.DataGridView()
		self._SC_MainForm_ChainSection_label1 = System.Windows.Forms.Label()
		self._SC_MainForm_ChainSection_dataGridView_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_ChainSection_dataGridView_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_ChainSection_dataGridView_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_ChainSection_dataGridView_Column6 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_ChainSection_dataGridView_Column4 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_ChainSection_dataGridView_Column5 = System.Windows.Forms.DataGridViewCheckBoxColumn()
		self._SC_MainForm_1phSCres_label = System.Windows.Forms.Label()
		self._SC_MainForm_1phSCres_textBox = System.Windows.Forms.TextBox()
		self._SC_MainForm_3phSCres_label = System.Windows.Forms.Label()
		self._SC_MainForm_3phSCres_textBox = System.Windows.Forms.TextBox()
		self._SC_MainForm_Transes_comboBox = System.Windows.Forms.ComboBox()
		self._SC_MainForm_ChainSection_label3 = System.Windows.Forms.Label()
		self._SC_MainForm_ChainSection_label4 = System.Windows.Forms.Label()
		self._SC_MainForm_QFsCount_dataGridView = System.Windows.Forms.DataGridView()
		self._SC_MainForm_QFsCount_dataGridView_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_QFsCount_dataGridView_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_MainForm_QFsCount_dataGridView_Column3 = System.Windows.Forms.DataGridViewCheckBoxColumn()
		self._SC_MainForm_ChainSection_label5 = System.Windows.Forms.Label()
		self._SC_MainForm_Cablecontact_textBox = System.Windows.Forms.TextBox()
		self._SC_MainForm_QFscontact_textBox = System.Windows.Forms.TextBox()
		self._SC_MainForm_ChainSection_label6 = System.Windows.Forms.Label()
		self._SC_MainForm_ChainSection_label7 = System.Windows.Forms.Label()
		self._CableQFscontactByDefault_button = System.Windows.Forms.Button()
		self._groupBox1 = System.Windows.Forms.GroupBox()
		self._errorProvider1 = System.Windows.Forms.ErrorProvider(self._components)
		self._SC_MainForm_ChainSection_dataGridView.BeginInit()
		self._SC_MainForm_QFsCount_dataGridView.BeginInit()
		self._errorProvider1.BeginInit()
		self.SuspendLayout()
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_button.Location = System.Drawing.Point(27, 534)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(143, 43)
		self._OK_button.TabIndex = 0
		self._OK_button.Text = "Сохранить и записать в чертёж"
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(1026, 554)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# Calculate_button
		# 
		self._Calculate_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Calculate_button.Location = System.Drawing.Point(432, 555)
		self._Calculate_button.Name = "Calculate_button"
		self._Calculate_button.Size = System.Drawing.Size(114, 23)
		self._Calculate_button.TabIndex = 2
		self._Calculate_button.Text = "Рассчитать"
		self._Calculate_button.UseVisualStyleBackColor = True
		self._Calculate_button.Click += self.Calculate_buttonClick
		# 
		# SC_Settings_button
		# 
		self._SC_Settings_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._SC_Settings_button.Location = System.Drawing.Point(581, 554)
		self._SC_Settings_button.Name = "SC_Settings_button"
		self._SC_Settings_button.Size = System.Drawing.Size(114, 23)
		self._SC_Settings_button.TabIndex = 3
		self._SC_Settings_button.Text = "Настройки КЗ"
		self._SC_Settings_button.UseVisualStyleBackColor = True
		self._SC_Settings_button.Click += self.SC_Settings_buttonClick
		# 
		# SC_MainForm_ChainSection_dataGridView
		# 
		self._SC_MainForm_ChainSection_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._SC_MainForm_ChainSection_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._SC_MainForm_ChainSection_dataGridView_Column1,
			self._SC_MainForm_ChainSection_dataGridView_Column2,
			self._SC_MainForm_ChainSection_dataGridView_Column3,
			self._SC_MainForm_ChainSection_dataGridView_Column6,
			self._SC_MainForm_ChainSection_dataGridView_Column4,
			self._SC_MainForm_ChainSection_dataGridView_Column5]))
		self._SC_MainForm_ChainSection_dataGridView.Location = System.Drawing.Point(27, 54)
		self._SC_MainForm_ChainSection_dataGridView.Name = "SC_MainForm_ChainSection_dataGridView"
		self._SC_MainForm_ChainSection_dataGridView.RowTemplate.Height = 24
		self._SC_MainForm_ChainSection_dataGridView.Size = System.Drawing.Size(668, 227)
		self._SC_MainForm_ChainSection_dataGridView.TabIndex = 4
		# 
		# SC_MainForm_ChainSection_label1
		# 
		self._SC_MainForm_ChainSection_label1.Location = System.Drawing.Point(27, 13)
		self._SC_MainForm_ChainSection_label1.Name = "SC_MainForm_ChainSection_label1"
		self._SC_MainForm_ChainSection_label1.Size = System.Drawing.Size(371, 38)
		self._SC_MainForm_ChainSection_label1.TabIndex = 5
		self._SC_MainForm_ChainSection_label1.Text = "1 - Сопротивление проводников (зап. программно)"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column1
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column1.HeaderText = "Марка кабеля"
		self._SC_MainForm_ChainSection_dataGridView_Column1.Name = "SC_MainForm_ChainSection_dataGridView_Column1"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column2
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column2.HeaderText = "Кол-во жил на фазу"
		self._SC_MainForm_ChainSection_dataGridView_Column2.Name = "SC_MainForm_ChainSection_dataGridView_Column2"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column3
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column3.HeaderText = "Сечение (кв.мм)"
		self._SC_MainForm_ChainSection_dataGridView_Column3.Name = "SC_MainForm_ChainSection_dataGridView_Column3"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column6
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column6.HeaderText = "Длина (м)"
		self._SC_MainForm_ChainSection_dataGridView_Column6.Name = "SC_MainForm_ChainSection_dataGridView_Column6"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column4
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column4.HeaderText = "Примечание"
		self._SC_MainForm_ChainSection_dataGridView_Column4.Name = "SC_MainForm_ChainSection_dataGridView_Column4"
		# 
		# SC_MainForm_ChainSection_dataGridView_Column5
		# 
		self._SC_MainForm_ChainSection_dataGridView_Column5.HeaderText = "Сохранить"
		self._SC_MainForm_ChainSection_dataGridView_Column5.Name = "SC_MainForm_ChainSection_dataGridView_Column5"
		# 
		# SC_MainForm_1phSCres_label
		# 
		self._SC_MainForm_1phSCres_label.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SC_MainForm_1phSCres_label.Location = System.Drawing.Point(356, 490)
		self._SC_MainForm_1phSCres_label.Name = "SC_MainForm_1phSCres_label"
		self._SC_MainForm_1phSCres_label.Size = System.Drawing.Size(162, 22)
		self._SC_MainForm_1phSCres_label.TabIndex = 11
		self._SC_MainForm_1phSCres_label.Text = "1-фазный ток КЗ (кА)"
		# 
		# SC_MainForm_1phSCres_textBox
		# 
		self._SC_MainForm_1phSCres_textBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SC_MainForm_1phSCres_textBox.Location = System.Drawing.Point(275, 490)
		self._SC_MainForm_1phSCres_textBox.Name = "SC_MainForm_1phSCres_textBox"
		self._SC_MainForm_1phSCres_textBox.Size = System.Drawing.Size(75, 22)
		self._SC_MainForm_1phSCres_textBox.TabIndex = 10
		# 
		# SC_MainForm_3phSCres_label
		# 
		self._SC_MainForm_3phSCres_label.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SC_MainForm_3phSCres_label.Location = System.Drawing.Point(108, 490)
		self._SC_MainForm_3phSCres_label.Name = "SC_MainForm_3phSCres_label"
		self._SC_MainForm_3phSCres_label.Size = System.Drawing.Size(161, 22)
		self._SC_MainForm_3phSCres_label.TabIndex = 13
		self._SC_MainForm_3phSCres_label.Text = "3-фазный ток КЗ (кА)"
		# 
		# SC_MainForm_3phSCres_textBox
		# 
		self._SC_MainForm_3phSCres_textBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SC_MainForm_3phSCres_textBox.Location = System.Drawing.Point(27, 490)
		self._SC_MainForm_3phSCres_textBox.Name = "SC_MainForm_3phSCres_textBox"
		self._SC_MainForm_3phSCres_textBox.Size = System.Drawing.Size(75, 22)
		self._SC_MainForm_3phSCres_textBox.TabIndex = 12
		# 
		# SC_MainForm_Transes_comboBox
		# 
		self._SC_MainForm_Transes_comboBox.FormattingEnabled = True
		self._SC_MainForm_Transes_comboBox.Location = System.Drawing.Point(27, 342)
		self._SC_MainForm_Transes_comboBox.Name = "SC_MainForm_Transes_comboBox"
		self._SC_MainForm_Transes_comboBox.Size = System.Drawing.Size(121, 24)
		self._SC_MainForm_Transes_comboBox.TabIndex = 14
		self._SC_MainForm_Transes_comboBox.SelectedIndexChanged += self.SC_MainForm_Transes_comboBoxSelectedIndexChanged
		self._SC_MainForm_Transes_comboBox.Enter += self.SC_MainForm_Transes_comboBoxSelectedFocusEnter
		# 
		# SC_MainForm_ChainSection_label3
		# 
		self._SC_MainForm_ChainSection_label3.Location = System.Drawing.Point(27, 301)
		self._SC_MainForm_ChainSection_label3.Name = "SC_MainForm_ChainSection_label3"
		self._SC_MainForm_ChainSection_label3.Size = System.Drawing.Size(180, 38)
		self._SC_MainForm_ChainSection_label3.TabIndex = 15
		self._SC_MainForm_ChainSection_label3.Text = "3 - Номинал трансформатора (кВА)"
		# 
		# SC_MainForm_ChainSection_label4
		# 
		self._SC_MainForm_ChainSection_label4.Location = System.Drawing.Point(731, 13)
		self._SC_MainForm_ChainSection_label4.Name = "SC_MainForm_ChainSection_label4"
		self._SC_MainForm_ChainSection_label4.Size = System.Drawing.Size(240, 38)
		self._SC_MainForm_ChainSection_label4.TabIndex = 17
		self._SC_MainForm_ChainSection_label4.Text = "2 - Кол-во аппаратов защиты и управления в цепи"
		# 
		# SC_MainForm_QFsCount_dataGridView
		# 
		self._SC_MainForm_QFsCount_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._SC_MainForm_QFsCount_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._SC_MainForm_QFsCount_dataGridView_Column1,
			self._SC_MainForm_QFsCount_dataGridView_Column2,
			self._SC_MainForm_QFsCount_dataGridView_Column3]))
		self._SC_MainForm_QFsCount_dataGridView.Location = System.Drawing.Point(731, 54)
		self._SC_MainForm_QFsCount_dataGridView.Name = "SC_MainForm_QFsCount_dataGridView"
		self._SC_MainForm_QFsCount_dataGridView.RowTemplate.Height = 24
		self._SC_MainForm_QFsCount_dataGridView.Size = System.Drawing.Size(367, 227)
		self._SC_MainForm_QFsCount_dataGridView.TabIndex = 18
		# 
		# SC_MainForm_QFsCount_dataGridView_Column1
		# 
		self._SC_MainForm_QFsCount_dataGridView_Column1.HeaderText = "Кол-во"
		self._SC_MainForm_QFsCount_dataGridView_Column1.Name = "SC_MainForm_QFsCount_dataGridView_Column1"
		# 
		# SC_MainForm_QFsCount_dataGridView_Column2
		# 
		self._SC_MainForm_QFsCount_dataGridView_Column2.HeaderText = "Номинал (А)"
		self._SC_MainForm_QFsCount_dataGridView_Column2.Name = "SC_MainForm_QFsCount_dataGridView_Column2"
		# 
		# SC_MainForm_QFsCount_dataGridView_Column3
		# 
		self._SC_MainForm_QFsCount_dataGridView_Column3.HeaderText = "Сохранить"
		self._SC_MainForm_QFsCount_dataGridView_Column3.Name = "SC_MainForm_QFsCount_dataGridView_Column3"
		# 
		# SC_MainForm_ChainSection_label5
		# 
		self._SC_MainForm_ChainSection_label5.Location = System.Drawing.Point(248, 301)
		self._SC_MainForm_ChainSection_label5.Name = "SC_MainForm_ChainSection_label5"
		self._SC_MainForm_ChainSection_label5.Size = System.Drawing.Size(264, 43)
		self._SC_MainForm_ChainSection_label5.TabIndex = 20
		self._SC_MainForm_ChainSection_label5.Text = "4 - Активное сопротивление контактных соединений (мОм)."
		# 
		# SC_MainForm_Cablecontact_textBox
		# 
		self._SC_MainForm_Cablecontact_textBox.Location = System.Drawing.Point(248, 344)
		self._SC_MainForm_Cablecontact_textBox.Name = "SC_MainForm_Cablecontact_textBox"
		self._SC_MainForm_Cablecontact_textBox.Size = System.Drawing.Size(75, 22)
		self._SC_MainForm_Cablecontact_textBox.TabIndex = 21
		# 
		# SC_MainForm_QFscontact_textBox
		# 
		self._SC_MainForm_QFscontact_textBox.Location = System.Drawing.Point(248, 372)
		self._SC_MainForm_QFscontact_textBox.Name = "SC_MainForm_QFscontact_textBox"
		self._SC_MainForm_QFscontact_textBox.Size = System.Drawing.Size(75, 22)
		self._SC_MainForm_QFscontact_textBox.TabIndex = 22
		# 
		# SC_MainForm_ChainSection_label6
		# 
		self._SC_MainForm_ChainSection_label6.Location = System.Drawing.Point(329, 345)
		self._SC_MainForm_ChainSection_label6.Name = "SC_MainForm_ChainSection_label6"
		self._SC_MainForm_ChainSection_label6.Size = System.Drawing.Size(83, 24)
		self._SC_MainForm_ChainSection_label6.TabIndex = 23
		self._SC_MainForm_ChainSection_label6.Text = "- Кабелей"
		# 
		# SC_MainForm_ChainSection_label7
		# 
		self._SC_MainForm_ChainSection_label7.Location = System.Drawing.Point(329, 372)
		self._SC_MainForm_ChainSection_label7.Name = "SC_MainForm_ChainSection_label7"
		self._SC_MainForm_ChainSection_label7.Size = System.Drawing.Size(135, 40)
		self._SC_MainForm_ChainSection_label7.TabIndex = 24
		self._SC_MainForm_ChainSection_label7.Text = "- Коммутационных аппаратов"
		# 
		# CableQFscontactByDefault_button
		# 
		self._CableQFscontactByDefault_button.Location = System.Drawing.Point(248, 415)
		self._CableQFscontactByDefault_button.Name = "CableQFscontactByDefault_button"
		self._CableQFscontactByDefault_button.Size = System.Drawing.Size(120, 23)
		self._CableQFscontactByDefault_button.TabIndex = 25
		self._CableQFscontactByDefault_button.Text = "По умолчанию"
		self._CableQFscontactByDefault_button.UseVisualStyleBackColor = True
		self._CableQFscontactByDefault_button.Click += self.CableQFscontactByDefault_buttonClick
		# 
		# groupBox1
		# 
		self._groupBox1.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._groupBox1.Location = System.Drawing.Point(12, 457)
		self._groupBox1.Name = "groupBox1"
		self._groupBox1.Size = System.Drawing.Size(506, 70)
		self._groupBox1.TabIndex = 26
		self._groupBox1.TabStop = False
		self._groupBox1.Text = "Токи короткого замыкания на конечном участке цепи"
		# 
		# errorProvider1
		# 
		self._errorProvider1.ContainerControl = self
		# 
		# ShortCircuit_MainForm
		# 
		self.ClientSize = System.Drawing.Size(1139, 590)
		self.Controls.Add(self._CableQFscontactByDefault_button)
		self.Controls.Add(self._SC_MainForm_ChainSection_label7)
		self.Controls.Add(self._SC_MainForm_ChainSection_label6)
		self.Controls.Add(self._SC_MainForm_QFscontact_textBox)
		self.Controls.Add(self._SC_MainForm_Cablecontact_textBox)
		self.Controls.Add(self._SC_MainForm_ChainSection_label5)
		self.Controls.Add(self._SC_MainForm_QFsCount_dataGridView)
		self.Controls.Add(self._SC_MainForm_ChainSection_label4)
		self.Controls.Add(self._SC_MainForm_ChainSection_label3)
		self.Controls.Add(self._SC_MainForm_Transes_comboBox)
		self.Controls.Add(self._SC_MainForm_3phSCres_label)
		self.Controls.Add(self._SC_MainForm_3phSCres_textBox)
		self.Controls.Add(self._SC_MainForm_1phSCres_label)
		self.Controls.Add(self._SC_MainForm_1phSCres_textBox)
		self.Controls.Add(self._SC_MainForm_ChainSection_label1)
		self.Controls.Add(self._SC_MainForm_ChainSection_dataGridView)
		self.Controls.Add(self._SC_Settings_button)
		self.Controls.Add(self._Calculate_button)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._OK_button)
		self.Controls.Add(self._groupBox1)
		self.MinimumSize = System.Drawing.Size(1051, 571)
		self.Name = "ShortCircuit_MainForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
		self.Text = "Токи КЗ"
		self.Load += self.ShortCircuit_MainFormLoad
		self._SC_MainForm_ChainSection_dataGridView.EndInit()
		self._SC_MainForm_QFsCount_dataGridView.EndInit()
		self._errorProvider1.EndInit()
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def ShortCircuit_MainFormLoad(self, sender, e):
		self._SC_MainForm_ChainSection_label1.Text = 'Расчётные участки цепи'
		# Заполняем таблицу участков цепи
		for i in ChainSectionsInfo_DB:
			self._SC_MainForm_ChainSection_dataGridView.Rows.Add(i[0], i[1], i[2], i[3], i[4], int(i[5])) # Участки цепи
		# заполняем номиналы трансформаторов
		self._SC_MainForm_Transes_comboBox.DataSource = [i[0] for i in Transformers_Resistance_from_ShortCircuit_Settings]
		# выставляем ранее выбранный номинал трансформатора
		self._SC_MainForm_Transes_comboBox.SelectedItem = DifSettings_Info_DB[0][0]
		# Заполняем таблицу автоматов и их номиналов
		for i in QFsCount_Info_DB:
			self._SC_MainForm_QFsCount_dataGridView.Rows.Add(i[0], i[1], int(i[2])) # Автоматы и их номиналы
		# Заполняем сопротивления контактов кабелей и автоматов:
		self._SC_MainForm_Cablecontact_textBox.Text = DifSettings_Info_DB[1][0] # кабелей
		self._SC_MainForm_QFscontact_textBox.Text = DifSettings_Info_DB[2][0] # автоматов

		# Дозаполняем таблицу участков цепи выбранными участками цепи (если пользователь их выбрал)
		for i in DecodingAVsandCables(elems_avtomats, elems_auxiliary_cables, Param_Wire_brand, Param_Rays_quantity, Param_Cable_section, Param_Cable_length):
			self._SC_MainForm_ChainSection_dataGridView.Rows.Add(i[0], i[1], i[2], i[3], i[4], int(i[5])) # Участки цепи
		# Дозаполняем таблицу автоматов попавшими в выборку
		for i in DecodingAvtomatsNominals (elems_avtomats, elems_any_avtomats, Param_Circuit_breaker_nominal):
			self._SC_MainForm_QFsCount_dataGridView.Rows.Add(i[0], i[1], int(i[2])) # Автоматы и их количество


	def CableQFscontactByDefault_buttonClick(self, sender, e):
		# Заполняем сопротивления контактов кабелей и автоматов по умолчанию:
		self._SC_MainForm_Cablecontact_textBox.Text = DifSettings_Info_byDefault[1][0] # кабелей
		self._SC_MainForm_QFscontact_textBox.Text = DifSettings_Info_byDefault[2][0] # автоматов


	def SC_MainForm_Transes_comboBoxSelectedIndexChanged(self, sender, e):
		pass

	def SC_MainForm_Transes_comboBoxSelectedFocusEnter(self, sender, e):
		# По входе фокуса в список номиналов трансов, перепишем спиок (вдруг пользователь добавлял или удалял номиналы в окне настроек)
		# Если окно Настроек уже открывалось, то заполнять его нужно из прошлых сохранённых списов. 
		# А если не открывалось, то из БД:
		if Transformers_Resistance_Output + QFs_Resistance_Output != []: # это значит что форма Настроек уже открывалась и сохранялась
			self._SC_MainForm_Transes_comboBox.DataSource = [i[0] for i in list(map(list, zip(*Transformers_Resistance_Output)))]
		else: # это значит что окно настроек не открывалось или не сохранялось
			# заполняем номиналы трансформаторов
			Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7)
			self._SC_MainForm_Transes_comboBox.DataSource = [i[0] for i in Transformers_Resistance_from_ShortCircuit_Settings]



	def Calculate_buttonClick(self, sender, e):
		# Собираем данные из таблицы участков цепи
		global ChainSectionsInfo_Output
		ChainSectionsInfo_Output = [] # Вид: [[u'АПвБбШп', '1', '185', '100', u'Кабель от ТП до ВРУ', '1'], [u'ВВГнг(А)-LSLTx', '1', '4.0', '11.0', u'ЩР-1.2-2', '1'], [u'ВВГнг(А)-LSLTx', '1', '2.5', '8.0', u'ЩР-1.2-3', '1']]
		for i in range(self._SC_MainForm_ChainSection_dataGridView.Rows.Count-1):
			ChainSectionsInfo_Output.append([])
		for n, i in enumerate(ChainSectionsInfo_Output):
			for j in range(self._SC_MainForm_ChainSection_dataGridView.Columns.Count-1): # кроме последнего столбца "Сохранить". Он нам не нужен
				i.append(self._SC_MainForm_ChainSection_dataGridView[j, n].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		# Проверяем правильность списка
		notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь ввёл не число, а что-то другое
		for i in ChainSectionsInfo_Output:
			if Is_Float_InWindows ([i[1], i[2], i[3]]) != True: # Проверяем только эти элементы что они числа
				notfloat = notfloat + 1
				break

		# Соберём данные об автоматах в выбранном участке цепи
		#global QFsInfo_Output
		QFsInfo_Output = []
		for i in range(self._SC_MainForm_QFsCount_dataGridView.Rows.Count-1):
			QFsInfo_Output.append([])
		for n, i in enumerate(QFsInfo_Output):
			for j in range(self._SC_MainForm_QFsCount_dataGridView.Columns.Count-1): # кроме последнего столбца "Сохранить". Он нам не нужен
				i.append(self._SC_MainForm_QFsCount_dataGridView[j, n].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		# Проверяем правильность списка
		for i in QFsInfo_Output:
			if Is_Float_InWindows (i) != True: 
				notfloat = notfloat + 1
				break

		# Возьмём данные выбранного номинала траснформатора
		Tranformer_Selected_Output = self._SC_MainForm_Transes_comboBox.SelectedItem # В виде '1000'
		# Сформируем список с остальными настройками главного окна
		#global DifSettings_Info_Output
		DifSettings_Info_Output = []
		DifSettings_Info_Output.append([Tranformer_Selected_Output]) # Добавляем номинал выбранного трансформатора
		DifSettings_Info_Output.append([self._SC_MainForm_Cablecontact_textBox.Text]) # Сопротивление контактов кабелей
		DifSettings_Info_Output.append([self._SC_MainForm_QFscontact_textBox.Text]) # Сопротивление контактов автоматов
		# Проверяем правильность списка
		for i in DifSettings_Info_Output:
			if Is_Float_InWindows (i) != True: 
				notfloat = notfloat + 1
				break

		if notfloat == 0:
			# Если окно Настроек уже открывалось, то заполнять трансы и токи автоматов нужно из прошлых сохранённых списов. 
			# А если не открывалось, то из БД:
			if Transformers_Resistance_Output + QFs_Resistance_Output != []: # это значит что форма Настроек уже открывалась и сохранялась
				Transformers_Resistance_from_ShortCircuit_Settings = list(map(list, zip(*Transformers_Resistance_Output)))
				QFs_Resistance_from_ShortCircuit_Settings = list(map(list, zip(*QFs_Resistance_Output)))
			else: # это значит что окно настроек не открывалось или не сохранялось
				Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7) 
				QFs_Resistance_from_ShortCircuit_Settings = Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)

			# Рассчитываем токи КЗ
			global Isc_list # Вид : (1.4299999999999999, 0.81999999999999995, [u'АПвБбШп', u'ВВГнг(А)-LS', '', ''])
			Isc_list = Count_SC (U3f, U1f, ChainSectionsInfo_Output, DifSettings_Info_Output, QFsInfo_Output, Transformers_Resistance_from_ShortCircuit_Settings, QFs_Resistance_from_ShortCircuit_Settings)
			if Isc_list == 'STOP':
				self.Close()
			else:
				# Записываем их в тектовые поля:
				self._SC_MainForm_3phSCres_textBox.Text = str(Isc_list[0])
				self._SC_MainForm_1phSCres_textBox.Text = str(Isc_list[1])
				# Выводим предупреждение если какие-то марки кабелей не были найдены у производителя.
				WireMarksNotFoundAlert = []
				for i in Isc_list[2]:
					if i != '':
						WireMarksNotFoundAlert.append(i)
				if WireMarksNotFoundAlert != []:
					TaskDialog.Show('Расчёт токов КЗ', 'Марки кабелей: ' + ', '.join(WireMarksNotFoundAlert) + '\nНе найдены у выбранного производителя или не используются в модели.\nДанные по этим кабелям взяты из Настроек Программы.')
		else:
			TaskDialog.Show('Расчёт токов КЗ', 'Расчёт не получился!\nПустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули.\nВведённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки.')


	def SC_Settings_buttonClick(self, sender, e):
		ShortCircuit_Settings_Form().ShowDialog()

	def OK_buttonClick(self, sender, e):
		# Собираем данные из таблицы участков цепи
		global ChainSectionsInfo_Output
		ChainSectionsInfo_Output = []
		for i in range(self._SC_MainForm_ChainSection_dataGridView.Rows.Count-1):
			ChainSectionsInfo_Output.append([])
		for n, i in enumerate(ChainSectionsInfo_Output):
			for j in range(self._SC_MainForm_ChainSection_dataGridView.Columns.Count):
				if self._SC_MainForm_ChainSection_dataGridView[j, n].Value == True: # перводим True/False в единички и нули для хранения в Хранилище
					i.append('1')
				elif self._SC_MainForm_ChainSection_dataGridView[j, n].Value == False or self._SC_MainForm_ChainSection_dataGridView[j, n].Value == None:
					i.append('0')
				else:
					i.append(self._SC_MainForm_ChainSection_dataGridView[j, n].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		# Пересоберём список, выкинем из него все элементы у которых не стояла галочка "Сохранить"
		hlp_lst = [i for i in ChainSectionsInfo_Output]
		ChainSectionsInfo_Output = []
		for i in hlp_lst:
			if i[5] == '1': # тут выкидываем те участки которые пользователь сказал не сохранять
				ChainSectionsInfo_Output.append(i)
		# Проверяем правильность списка
		notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь ввёл не число, а что-то другое
		for i in ChainSectionsInfo_Output:
			if Is_Float_InWindows ([i[1], i[2], i[3]]) != True: # Проверяем только эти элементы что они числа
				notfloat = notfloat + 1
				break

		# Возьмём данные выбранного номинала траснформатора
		Tranformer_Selected_Output = self._SC_MainForm_Transes_comboBox.SelectedItem # В виде '1000'
		# Сформируем список с остальными настройками главного окна
		global DifSettings_Info_Output
		DifSettings_Info_Output = []
		DifSettings_Info_Output.append([Tranformer_Selected_Output]) # Добавляем номинал выбранного трансформатора
		DifSettings_Info_Output.append([self._SC_MainForm_Cablecontact_textBox.Text]) # Сопротивление контактов кабелей
		DifSettings_Info_Output.append([self._SC_MainForm_QFscontact_textBox.Text]) # Сопротивление контактов автоматов
		# Проверяем правильность списка
		for i in DifSettings_Info_Output:
			if Is_Float_InWindows (i) != True: 
				notfloat = notfloat + 1
				break

		# Соберём данные об автоматах в выбранном участке цепи
		global QFsInfo_Output
		QFsInfo_Output = []
		for i in range(self._SC_MainForm_QFsCount_dataGridView.Rows.Count-1):
			QFsInfo_Output.append([])
		for n, i in enumerate(QFsInfo_Output):
			for j in range(self._SC_MainForm_QFsCount_dataGridView.Columns.Count):
				if self._SC_MainForm_QFsCount_dataGridView[j, n].Value == True: # перводим True/False в единички и нули для хранения в Хранилище
					i.append('1')
				elif self._SC_MainForm_QFsCount_dataGridView[j, n].Value == False or self._SC_MainForm_QFsCount_dataGridView[j, n].Value == None:
					i.append('0')
				else:
					i.append(self._SC_MainForm_QFsCount_dataGridView[j, n].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		# Пересоберём список, выкинем из него все элементы у которых не стояла галочка "Сохранить"
		hlp_lst = [i for i in QFsInfo_Output]
		QFsInfo_Output = []
		for i in hlp_lst:
			if i[2] == '1': # тут выкидываем те автоматы которые пользователь сказал не сохранять
				QFsInfo_Output.append(i)
		# Проверяем правильность списка
		for i in QFsInfo_Output:
			if Is_Float_InWindows (i) != True: 
				notfloat = notfloat + 1
				break

		# Забираем нуные переменные для сохранения и записи после закрытия Главного окна
		global IscRes3ph
		global IscRes1ph
		IscRes3ph = self._SC_MainForm_3phSCres_textBox.Text
		IscRes1ph = self._SC_MainForm_1phSCres_textBox.Text
		

		if notfloat == 0: # Если ошибок в введённых данных нет
			global Button_Cancel_ShortCircuit_MainForm_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
			Button_Cancel_ShortCircuit_MainForm_pushed = 0 # Кнопка Отмена не нажата
			#Application.Exit()
			#self.Dispose()
			self.Close()
		else:
			#TaskDialog.Show('Расчёт токов КЗ', 'Данные не сохранены! Пустые ячейки в таблицах не допускаются. Вместо пустых значений допускается писать нули. Введённые Вами значения должны быть числами с разделителем целой и дробной частей в виде точки.')
			self._errorProvider1.SetError(self._OK_button, 'Данные не сохранены! Пустые ячейки в таблицах не допускаются. Вместо пустых значений допускается писать нули.\nВведённые Вами значения должны быть числами с разделителем целой и дробной частей в виде точки.')


	def Cancel_buttonClick(self, sender, e):
		self.Close()










#___Окно настроек расчётов токов КЗ______________

class ShortCircuit_Settings_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._components = System.ComponentModel.Container()
		self._SaveandClose_button = System.Windows.Forms.Button()
		self._Cancel_button = System.Windows.Forms.Button()
		self._SC_settings_label1 = System.Windows.Forms.Label()
		self._dataGridView1 = System.Windows.Forms.DataGridView()
		self._SC_Settings_Form_table1_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column4 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column5 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column6 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._SC_Settings_Form_table1_Column7 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._ShortCircuit_Settings_Form_errorProvider1 = System.Windows.Forms.ErrorProvider(self._components)
		self._ByDefault_table1_button = System.Windows.Forms.Button()
		self._dataGridView2 = System.Windows.Forms.DataGridView()
		self._SC_settings_label2 = System.Windows.Forms.Label()
		self._ByDefault_table2_button = System.Windows.Forms.Button()
		self._Table2_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Table2_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Table2_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._ShortCircuit_Settings_Form_errorProvider2 = System.Windows.Forms.ErrorProvider(self._components)
		self._dataGridView1.BeginInit()
		self._ShortCircuit_Settings_Form_errorProvider1.BeginInit()
		self._dataGridView2.BeginInit()
		self._ShortCircuit_Settings_Form_errorProvider2.BeginInit()
		self.SuspendLayout()
		# 
		# SaveandClose_button
		# 
		self._SaveandClose_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SaveandClose_button.Location = System.Drawing.Point(22, 597)
		self._SaveandClose_button.Name = "SaveandClose_button"
		self._SaveandClose_button.Size = System.Drawing.Size(75, 23)
		self._SaveandClose_button.TabIndex = 0
		self._SaveandClose_button.Text = "OK"
		self._SaveandClose_button.UseVisualStyleBackColor = True
		self._SaveandClose_button.Click += self.SaveandClose_buttonClick
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(893, 597)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# SC_settings_label1
		# 
		self._SC_settings_label1.Location = System.Drawing.Point(22, 13)
		self._SC_settings_label1.Name = "SC_settings_label1"
		self._SC_settings_label1.Size = System.Drawing.Size(698, 41)
		self._SC_settings_label1.TabIndex = 3
		self._SC_settings_label1.Text = "Заполняется программно"
		# 
		# dataGridView1
		# 
		self._dataGridView1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._dataGridView1.ColumnHeadersHeight = 85
		self._dataGridView1.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._SC_Settings_Form_table1_Column1,
			self._SC_Settings_Form_table1_Column2,
			self._SC_Settings_Form_table1_Column3,
			self._SC_Settings_Form_table1_Column4,
			self._SC_Settings_Form_table1_Column5,
			self._SC_Settings_Form_table1_Column6,
			self._SC_Settings_Form_table1_Column7]))
		self._dataGridView1.Location = System.Drawing.Point(22, 57)
		self._dataGridView1.Name = "dataGridView1"
		self._dataGridView1.RowTemplate.Height = 24
		self._dataGridView1.Size = System.Drawing.Size(756, 286)
		self._dataGridView1.TabIndex = 4
		# 
		# SC_Settings_Form_table1_Column1
		# 
		self._SC_Settings_Form_table1_Column1.HeaderText = "Номинальная мощность тр-ра (кВА)"
		self._SC_Settings_Form_table1_Column1.Name = "SC_Settings_Form_table1_Column1"
		# 
		# SC_Settings_Form_table1_Column2
		# 
		self._SC_Settings_Form_table1_Column2.HeaderText = "Сопротивление прямой и нулевой последовательности r1т (мОм)"
		self._SC_Settings_Form_table1_Column2.Name = "SC_Settings_Form_table1_Column2"
		# 
		# SC_Settings_Form_table1_Column3
		# 
		self._SC_Settings_Form_table1_Column3.HeaderText = "Сопротивление прямой и нулевой последовательности x1т (мОм)"
		self._SC_Settings_Form_table1_Column3.Name = "SC_Settings_Form_table1_Column3"
		# 
		# SC_Settings_Form_table1_Column4
		# 
		self._SC_Settings_Form_table1_Column4.HeaderText = "Сопротивление прямой и нулевой последовательности z1т (мОм)"
		self._SC_Settings_Form_table1_Column4.Name = "SC_Settings_Form_table1_Column4"
		# 
		# SC_Settings_Form_table1_Column5
		# 
		self._SC_Settings_Form_table1_Column5.HeaderText = "Сопротивление току 1-фазного КЗ r(1)1т (мОм)"
		self._SC_Settings_Form_table1_Column5.Name = "SC_Settings_Form_table1_Column5"
		# 
		# SC_Settings_Form_table1_Column6
		# 
		self._SC_Settings_Form_table1_Column6.HeaderText = "Сопротивление току 1-фазного КЗ x(1)1т (мОм)"
		self._SC_Settings_Form_table1_Column6.Name = "SC_Settings_Form_table1_Column6"
		# 
		# SC_Settings_Form_table1_Column7
		# 
		self._SC_Settings_Form_table1_Column7.HeaderText = "Сопротивление току 1-фазного КЗ z(1)1т (мОм)"
		self._SC_Settings_Form_table1_Column7.Name = "SC_Settings_Form_table1_Column7"
		# 
		# ShortCircuit_Settings_Form_errorProvider1
		# 
		self._ShortCircuit_Settings_Form_errorProvider1.ContainerControl = self
		# 
		# ByDefault_table1_button
		# 
		self._ByDefault_table1_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._ByDefault_table1_button.Location = System.Drawing.Point(795, 57)
		self._ByDefault_table1_button.Name = "ByDefault_table1_button"
		self._ByDefault_table1_button.Size = System.Drawing.Size(161, 46)
		self._ByDefault_table1_button.TabIndex = 5
		self._ByDefault_table1_button.Text = "Установить данные по умолчанию (табл.1)"
		self._ByDefault_table1_button.UseVisualStyleBackColor = True
		self._ByDefault_table1_button.Click += self.ByDefault_table1_buttonClick
		# 
		# dataGridView2
		# 
		self._dataGridView2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._dataGridView2.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._dataGridView2.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._Table2_Column1,
			self._Table2_Column2,
			self._Table2_Column3]))
		self._dataGridView2.Location = System.Drawing.Point(22, 399)
		self._dataGridView2.Name = "dataGridView2"
		self._dataGridView2.RowTemplate.Height = 24
		self._dataGridView2.Size = System.Drawing.Size(427, 182)
		self._dataGridView2.TabIndex = 6
		# 
		# SC_settings_label2
		# 
		self._SC_settings_label2.Location = System.Drawing.Point(22, 355)
		self._SC_settings_label2.Name = "SC_settings_label2"
		self._SC_settings_label2.Size = System.Drawing.Size(512, 41)
		self._SC_settings_label2.TabIndex = 7
		self._SC_settings_label2.Text = "Заполняется программно"
		# 
		# ByDefault_table2_button
		# 
		self._ByDefault_table2_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._ByDefault_table2_button.Location = System.Drawing.Point(467, 399)
		self._ByDefault_table2_button.Name = "ByDefault_table2_button"
		self._ByDefault_table2_button.Size = System.Drawing.Size(161, 46)
		self._ByDefault_table2_button.TabIndex = 8
		self._ByDefault_table2_button.Text = "Установить данные по умолчанию (табл.2)"
		self._ByDefault_table2_button.UseVisualStyleBackColor = True
		self._ByDefault_table2_button.Click += self.ByDefault_table2_buttonClick
		# 
		# Table2_Column1
		# 
		self._Table2_Column1.HeaderText = "Номинальный ток выключателя (А)"
		self._Table2_Column1.Name = "Table2_Column1"
		# 
		# Table2_Column2
		# 
		self._Table2_Column2.HeaderText = "Сопротивление катушки и контакта rкв (мОм)"
		self._Table2_Column2.Name = "Table2_Column2"
		# 
		# Table2_Column3
		# 
		self._Table2_Column3.HeaderText = "Сопротивление катушки и контакта xкв (мОм)"
		self._Table2_Column3.Name = "Table2_Column3"
		# 
		# ShortCircuit_Settings_Form_errorProvider2
		# 
		self._ShortCircuit_Settings_Form_errorProvider2.ContainerControl = self
		# 
		# ShortCircuit_Settings_Form
		# 
		self.ClientSize = System.Drawing.Size(990, 632)
		self.Controls.Add(self._ByDefault_table2_button)
		self.Controls.Add(self._SC_settings_label2)
		self.Controls.Add(self._dataGridView2)
		self.Controls.Add(self._ByDefault_table1_button)
		self.Controls.Add(self._dataGridView1)
		self.Controls.Add(self._SC_settings_label1)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._SaveandClose_button)
		self.MinimumSize = System.Drawing.Size(900, 635)
		self.Name = "ShortCircuit_Settings_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
		self.Text = "Настройки расчётов токов КЗ"
		self.Load += self.ShortCircuit_Settings_FormLoad
		self._dataGridView1.EndInit()
		self._ShortCircuit_Settings_Form_errorProvider1.EndInit()
		self._dataGridView2.EndInit()
		self._ShortCircuit_Settings_Form_errorProvider2.EndInit()
		self.ResumeLayout(False)


		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def ByDefault_table1_buttonClick(self, sender, e):
		a = self._dataGridView1.Rows.Count-1
		while a > 0:
			self._dataGridView1.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		for i in Transformers_Resistance_from_ShortCircuit_Settings_By_Default:
			self._dataGridView1.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) # Потом записываем заново всё

	def ByDefault_table2_buttonClick(self, sender, e):
		a = self._dataGridView2.Rows.Count-1
		while a > 0:
			self._dataGridView2.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		for i in QFs_Resistance_from_ShortCircuit_Settings_By_Default:
			self._dataGridView2.Rows.Add(i[0], i[1], i[2]) # Потом записываем заново всё
		

	def ShortCircuit_Settings_FormLoad(self, sender, e):
		# Заполняем форму исходными данными
		self._SC_settings_label1.Text = 'Табл.1. Сопротивления понижающих трансформаторов с вторичным напряжением 0,4 кВ, Д/Ун.'
		self._SC_settings_label2.Text = 'Табл.2. Сопротивления катушек и контактов автоматических выключателей.'

		# Если окно уже открывалось, то заполнять его нужно из прошлых сохранённых списов. 
		# А если не открывалось, то из БД:
		if Transformers_Resistance_Output + QFs_Resistance_Output != []: # это значит что форма уже открывалась и сохранялась
			for i in list(map(list, zip(*Transformers_Resistance_Output))): # транспонируем список для заполненеия построчно
				self._dataGridView1.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) # Трансы и их сопротивления
			for i in list(map(list, zip(*QFs_Resistance_Output))):
				self._dataGridView2.Rows.Add(i[0], i[1], i[2]) # Автоматы и их сопротивления
		else: # это значит что форма запускается впервые
			# Считываем данные из Хранилища о трансформаторах
			Transformers_Resistance_from_ShortCircuit_Settings = Read_info_about_Transformres (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7) 
			for i in Transformers_Resistance_from_ShortCircuit_Settings:
				self._dataGridView1.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6]) # Трансы и их сопротивления
			QFs_Resistance_from_ShortCircuit_Settings = Read_info_about_QFsResistance (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)
			for i in QFs_Resistance_from_ShortCircuit_Settings:
				self._dataGridView2.Rows.Add(i[0], i[1], i[2]) # Автоматы и их сопротивления

	def SaveandClose_buttonClick(self, sender, e):
		global Transformers_Resistance_Output
		global QFs_Resistance_Output
		# Забираем значения трансов и их сопротивлений. Нам нужен список с подсписками [[мощности трансов], [их сопротивления], ...]. То есть будет так: [['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800', '1000'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030', '1143'], ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858', '972'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030', '1143']]
		Transformers_Resistance_Output = []
		for i in range(self._dataGridView1.Columns.Count):
			Transformers_Resistance_Output.append([])
		for n, i in enumerate(Transformers_Resistance_Output):
			for j in range(self._dataGridView1.Rows.Count-1):
				i.append(self._dataGridView1[n, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.

		# Забираем значения автоматов и их сопротивлений.
		QFs_Resistance_Output = []
		for i in range(self._dataGridView2.Columns.Count):
			QFs_Resistance_Output.append([])
		for n, i in enumerate(QFs_Resistance_Output):
			for j in range(self._dataGridView2.Rows.Count-1):
				i.append(self._dataGridView2[n, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.

		# ______________________________Проверяем корректность введённых данных__________________________________________
		notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь ввёл не число, а что-то другое
		for i in Transformers_Resistance_Output:
			for j in i:
				try:
					float(j)
				except SystemError:
					self._ShortCircuit_Settings_Form_errorProvider1.SetError(self._SaveandClose_button, 'Табл. 1. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули')
					notfloat = notfloat + 1
				except ValueError:
					self._ShortCircuit_Settings_Form_errorProvider1.SetError(self._SaveandClose_button, 'Табл. 1. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки')
					notfloat = notfloat + 1
		for i in QFs_Resistance_Output:
			for j in i:
				try:
					float(j)
				except SystemError:
					self._ShortCircuit_Settings_Form_errorProvider2.SetError(self._SaveandClose_button, 'Табл. 2. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули')
					notfloat = notfloat + 1
				except ValueError:
					self._ShortCircuit_Settings_Form_errorProvider2.SetError(self._SaveandClose_button, 'Табл. 2. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки')
					notfloat = notfloat + 1

		if notfloat == 0:
			# Выставляем "кнопка отмена не нажата"
			global Button_Cancel_ShortCircuit_Settings_Form_pushed
			Button_Cancel_ShortCircuit_Settings_Form_pushed = 0
			self.Close()

		

	def Cancel_buttonClick(self, sender, e):
		# А в конце выставим обратно в исходное состояние кнопку Button_Cancel_ShortCircuit_Settings_Form_pushed "Кнопка отмена нажата"
		global Button_Cancel_ShortCircuit_Settings_Form_pushed
		Button_Cancel_ShortCircuit_Settings_Form_pushed = 1
		self.Close()






ShortCircuit_MainForm().ShowDialog()
#ShortCircuit_MainForm().Show()





# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html


# Сохраняем данные
if Button_Cancel_ShortCircuit_MainForm_pushed == 0: # Если в Главном окне пользователь не нажал Отмена
	
	# Предложим сохранить данные
	td = TaskDialog('Сохранение')
	td.MainContent = 'Сохранить данные?'
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да')
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
	GetUserResult = td.Show()
	if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
		# Сохраняем в Хранилище данные из Главного окна
		Write_3_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Main_Storage, ProjectInfoObject, SchemaName_for_ShortCircuit_Main, FieldName_for_ShortCircuit_Main_1, List[str](EncodingListofListsforES(ChainSectionsInfo_Output)), FieldName_for_ShortCircuit_Main_2, List[str](EncodingListofListsforES(DifSettings_Info_Output)), FieldName_for_ShortCircuit_Main_3, List[str](EncodingListofListsforES(QFsInfo_Output)))

		# Сохраняем данные в Хранилище из окна настроек токов КЗ
		if Button_Cancel_ShortCircuit_Settings_Form_pushed != 1: # Если кнопка "Cancel" не была нажата
			ShortCircuit_Settings_Form_Save (Transformers_Resistance_Output, QFs_Resistance_Output, schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)

	# Дальше спросим куда записать результаты расчёта, если расчёт был выполнен.
	if IscRes3ph != '' and IscRes1ph != '':
		td = TaskDialog('Запись в чертёж')
		td.MainContent = 'Записать токи КЗ в чертёж?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Записать текстом', 'Результат появится в виде текста в указанной Вами точке чертежа')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Записать в автомат', 'Результат будет записан в соответствующие параметры автомата')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, 'Записать и текстом, и в автомат', 'Результат будет записан и текстом, и в соответствующие параметры автомата')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink4, 'Нет', 'Не записывать результат никуда')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			textstring = 'Iкз3ф=' + IscRes3ph + 'кА\nIкз1ф=' + IscRes1ph + 'кА'
			CreateText (textstring)
		elif GetUserResult == TaskDialogResult.CommandLink2:
			WriteSC_inAVs(Param_Short_Circuit_3ph, Param_Short_Circuit_1ph, IscRes3ph, IscRes1ph, avt_family_names, using_reserve_avtomats, using_any_avtomats)
		elif GetUserResult == TaskDialogResult.CommandLink3:
			WriteSC_inAVs(Param_Short_Circuit_3ph, Param_Short_Circuit_1ph, IscRes3ph, IscRes1ph, avt_family_names, using_reserve_avtomats, using_any_avtomats)
			textstring = 'Iкз3ф=' + IscRes3ph + 'кА\nIкз1ф=' + IscRes1ph + 'кА'
			CreateText (textstring)
		else: 
			pass




transGroup.Assimilate() # принимаем группу транзакций










'''

Примечание   Если форма отображена как модальная, код, следующий за методом Show, не выполняется, пока окно диалога не закрыто. 
Но когда форма показывается как немодальная, код, следующий за методом Show, выполняется сразу после того, как отображается форма.

Метод Show имеет другой необязательный аргумент, "владельца", который может использоваться, чтобы определить 
родительско-дочерние отношения для формы. Вы можете передавать этому аргументу имя формы, чтобы делать эту форму "владельцем" из новой формы.

Чтобы отобразить форму как дочернюю другой формы

Используйте метод Show с аргументами "владельца" и стиля.
Например:

' Отображает frmAbout как немодальную дочернюю frmMain.
frmAbout.Show vbModeless, frmMain

Использование аргумента "владельца" с методом Show гарантирует, что когда родительское окно свернуто, 
окно диалога также будет свернуто, а когда родительская форма закрыта, оно будет выгружено.


if Button_Cancel_ShortCircuit_MainForm_pushed == 0:
	ShortCircuit_MainForm().Dispose()

if ara == 1:
	TaskDialog.Show('название окна', 'urraaa')
	global ara
	ara = 2
	ShortCircuit_MainForm().ShowDialog()

if ara == 2:
	TaskDialog.Show('название окна', 'urraaa 2')
	global ara
	ara = 3
	ShortCircuit_MainForm().ShowDialog()

# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html
transGroup = TransactionGroup(doc, "TeslaShortCircuit")
transGroup.Start()


if Button_Cancel_ShortCircuit_MainForm_pushed == 0: # Если в Главном окне пользователь не нажал Отмена
	
	# Предложим сохранить данные
	td = TaskDialog('Сохранение')
	td.MainContent = 'Сохранить данные?'
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да')
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
	GetUserResult = td.Show()
	if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
		# Сохраняем в Хранилище данные из Главного окна
		Write_3_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Main_Storage, ProjectInfoObject, SchemaName_for_ShortCircuit_Main, FieldName_for_ShortCircuit_Main_1, List[str](EncodingListofListsforES(ChainSectionsInfo_Output)), FieldName_for_ShortCircuit_Main_2, List[str](EncodingListofListsforES(DifSettings_Info_Output)), FieldName_for_ShortCircuit_Main_3, List[str](EncodingListofListsforES(QFsInfo_Output)))

		# Сохраняем данные в Хранилище из окна настроек токов КЗ
		if Button_Cancel_ShortCircuit_Settings_Form_pushed != 1: # Если кнопка "Cancel" не была нажата
			ShortCircuit_Settings_Form_Save (Transformers_Resistance_Output, QFs_Resistance_Output, schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, FieldName_for_ShortCircuit_Settings_1, FieldName_for_ShortCircuit_Settings_2, FieldName_for_ShortCircuit_Settings_3, FieldName_for_ShortCircuit_Settings_4, FieldName_for_ShortCircuit_Settings_5, FieldName_for_ShortCircuit_Settings_6, FieldName_for_ShortCircuit_Settings_7, FieldName_for_ShortCircuit_Settings_8, FieldName_for_ShortCircuit_Settings_9, FieldName_for_ShortCircuit_Settings_10)

	# Дальше спросим куда записать результаты расчёта, если расчёт был выполнен.
	if IscRes3ph != '' and IscRes1ph != '':
		td = TaskDialog('Запись в чертёж')
		td.MainContent = 'Записать токи КЗ в чертёж?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Записать текстом', 'Результат появится в виде текста в указанной Вами точке чертежа')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Записать в автомат', 'Результат будет записан в соответствующие параметры автомата')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink3, 'Нет', 'Не записывать результат никуда')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			textstring = 'Iкз3ф=' + IscRes3ph + 'кА\nIкз1ф=' + IscRes1ph + 'кА'
			CreateText (textstring)
		elif GetUserResult == TaskDialogResult.CommandLink2:
			WriteSC_inAVs(Param_Short_Circuit_3ph, Param_Short_Circuit_1ph, IscRes3ph, IscRes1ph, avt_family_names, using_reserve_avtomats, using_any_avtomats)
		else: 
			pass




transGroup.Assimilate() # принимаем группу транзакций
'''















'''
	self.FormClosing += System.Windows.Forms.FormClosingEventHandler(Form_Closing) # закрытие формы
	def Form_Closing(self, sender, e):
		TaskDialog.Show('название окна', 'aццццra')


# Расчётные сопротивления трансформаторов (мОм) (при первичном напряжении 6-10 кВ и схеме тругольник-звезда).
# По ГОСТ 11920-73 и ГОСТ 12022-76
# По умлочанию масляных https://raschet.info/primer-rascheta-toka-odnofaznogo-kz/
Resistance_Total_Transformer_DB = ['0.302', '0.187', '0.0754', '0.047', '0.03', '0.019', '0.014', '0.009', '0.0056', '0.0036']


# 2**3 - два в третьей степени
# 4**0.5 - корень из 4


#Составим список полных сопротивлений кабелей (мОм/м)
# Медных:
Resistance_Total_Specific_for_copper_cables_DB = []
# Алюминиевых:
Resistance_Total_Specific_for_aluminium_cables_DB = []

for n, i in enumerate(Resistance_Active_Specific_for_copper_cables_DB):
	Resistance_Total_Specific_for_copper_cables_DB.append(math.sqrt(i**2 + Resistance_Inductive_Specific_for_all_cables_DB[n]**2))
for n, i in enumerate(Resistance_Active_Specific_for_aluminium_cables_DB):
	Resistance_Total_Specific_for_aluminium_cables_DB.append(math.sqrt(i**2 + Resistance_Inductive_Specific_for_all_cables_DB[n]**2))



#___________________Принимаем и записываем данные из окошка SC_Settings_Form_________________________________________________________

if Button_Cancel_ShortCircuit_Settings_Form_pushed != 1: # Если кнопка "Cancel" не была нажата
	# Сортируем списки по возрастанию
	
	# Запутанная синхронная сортировка по индексам. Скачано отсюда https://ru.stackoverflow.com/questions/599129/%D0%A1%D0%B8%D0%BD%D1%85%D1%80%D0%BE%D0%BD%D0%BD%D0%B0%D1%8F-%D1%81%D0%BE%D1%80%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B0-%D1%81%D0%BF%D0%B8%D1%81%D0%BA%D0%BE%D0%B2-python
	Transformers_Resistance_Output_copy = []
	indexes = sorted(range(len([float(j) for j in Transformers_Resistance_Output[0]])), key=lambda i: [float(j) for j in Transformers_Resistance_Output[0]][i]) # Получаем сортированные индексы первого списка (сортируем по мощностям трансов)
	for i in Transformers_Resistance_Output:
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[0][i] for i in indexes]) # переписываем отсортированные по индексам списки
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[1][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[2][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[3][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[4][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[5][i] for i in indexes])
		Transformers_Resistance_Output_copy.append([Transformers_Resistance_Output[6][i] for i in indexes])


	# Пишем данные из окна в Хранилище
	Write_7_fields_to_ExtensibleStorage (schemaGuid_for_ShortCircuit_Settings, ProjectInfoObject, SchemaName_for_ShortCircuit_Settings, 
	FieldName_for_ShortCircuit_Settings_1, Transformers_Resistance_Output_copy[0], 
	FieldName_for_ShortCircuit_Settings_2, Transformers_Resistance_Output_copy[1],
	FieldName_for_ShortCircuit_Settings_3, Transformers_Resistance_Output_copy[2], 
	FieldName_for_ShortCircuit_Settings_4, Transformers_Resistance_Output_copy[3],
	FieldName_for_ShortCircuit_Settings_5, Transformers_Resistance_Output_copy[4],
	FieldName_for_ShortCircuit_Settings_6, Transformers_Resistance_Output_copy[5],
	FieldName_for_ShortCircuit_Settings_7, Transformers_Resistance_Output_copy[6]
	)




                if (Button_Cancel_ShortCircuit_MainForm_pushed == 0)
                {
                    // Запускаем скрипт во второй раз. 
                    ScriptEngine engine1 = Python.CreateEngine();
                    ScriptScope scope1 = engine1.CreateScope();

                    scope1.SetVariable("doc", doc);
                    scope1.SetVariable("uidoc", ui_doc);

                    // Переменные отвечающие за соединение с хранилищем настроек расчётов токов КЗ
                    scope1.SetVariable("Guidstr_ShortCircuit_Settings", GlobalsClass.Guidstr_ShortCircuit_Settings);
                    scope1.SetVariable("SchemaName_for_ShortCircuit_Settings", GlobalsClass.SchemaName_for_ShortCircuit_Settings);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_1", GlobalsClass.FieldName_for_ShortCircuit_Settings_1);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_2", GlobalsClass.FieldName_for_ShortCircuit_Settings_2);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_3", GlobalsClass.FieldName_for_ShortCircuit_Settings_3);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_4", GlobalsClass.FieldName_for_ShortCircuit_Settings_4);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_5", GlobalsClass.FieldName_for_ShortCircuit_Settings_5);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_6", GlobalsClass.FieldName_for_ShortCircuit_Settings_6);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_7", GlobalsClass.FieldName_for_ShortCircuit_Settings_7);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_8", GlobalsClass.FieldName_for_ShortCircuit_Settings_8);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_9", GlobalsClass.FieldName_for_ShortCircuit_Settings_9);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Settings_10", GlobalsClass.FieldName_for_ShortCircuit_Settings_10);


                    // Переменные отвечающие за Необходимые данные для сохранения информации в основном окне расчётов Токов КЗ
                    scope1.SetVariable("Guidstr_ShortCircuit_Main", GlobalsClass.Guidstr_ShortCircuit_Main);
                    scope1.SetVariable("SchemaName_for_ShortCircuit_Main", GlobalsClass.SchemaName_for_ShortCircuit_Main);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Main_1", GlobalsClass.FieldName_for_ShortCircuit_Main_1);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Main_2", GlobalsClass.FieldName_for_ShortCircuit_Main_2);
                    scope1.SetVariable("FieldName_for_ShortCircuit_Main_3", GlobalsClass.FieldName_for_ShortCircuit_Main_3);

                    // Имена семейств и параметров с которыми работает программа
                    scope1.SetVariable("avt_family_names", GlobalsClass.Family_names_avt);
                    scope1.SetVariable("using_auxiliary_cables", GlobalsClass.Family_names_auxiliary_cable);
                    scope1.SetVariable("using_any_avtomats", GlobalsClass.Family_names_using_any_avtomats);
                    scope1.SetVariable("using_reserve_avtomats", GlobalsClass.Family_names_reserve_avt);

                    scope1.SetVariable("Param_Upit", GlobalsClass.Param_Upit);
                    scope1.SetVariable("Param_Cable_length", GlobalsClass.Param_Cable_length);
                    scope1.SetVariable("Param_Cable_section", GlobalsClass.Param_Cable_section);
                    scope1.SetVariable("Param_Circuit_breaker_nominal", GlobalsClass.Param_Circuit_breaker_nominal);
                    scope1.SetVariable("Param_Wire_brand", GlobalsClass.Param_Wire_brand);
                    scope1.SetVariable("Param_Rays_quantity", GlobalsClass.Param_Rays_quantity);
                    scope1.SetVariable("Param_Breaking_capacity", GlobalsClass.Param_Breaking_capacity);
                    scope1.SetVariable("Param_Circuit_number", GlobalsClass.Param_Circuit_number);
                    scope1.SetVariable("Param_Short_Circuit_3ph", GlobalsClass.Param_Short_Circuit_3ph);
                    scope1.SetVariable("Param_Short_Circuit_1ph", GlobalsClass.Param_Short_Circuit_1ph);

                    // Переменные передаваемые из предыдущего скрипта

                    scope1.SetVariable("Button_Cancel_ShortCircuit_MainForm_pushed", Button_Cancel_ShortCircuit_MainForm_pushed);
                    scope1.SetVariable("ChainSectionsInfo_Output", ChainSectionsInfo_Output);
                    scope1.SetVariable("DifSettings_Info_Output", DifSettings_Info_Output);
                    scope1.SetVariable("QFsInfo_Output", QFsInfo_Output);
                    scope1.SetVariable("Button_Cancel_ShortCircuit_Settings_Form_pushed", Button_Cancel_ShortCircuit_Settings_Form_pushed);
                    scope1.SetVariable("Transformers_Resistance_Output", Transformers_Resistance_Output);
                    scope1.SetVariable("QFs_Resistance_Output", QFs_Resistance_Output);


                    string SimilarParams1 = Assembly.GetExecutingAssembly().GetName().Name + ".Resources." + "ShortCircuitSave.py";
                    Stream stream2 = Assembly.GetExecutingAssembly().GetManifestResourceStream(SimilarParams1);
                    if (stream2 != null)
                    {
                        string script1 = new StreamReader(stream2).ReadToEnd();
                        engine1.Execute(script1, scope1);
                    }

                }

'''