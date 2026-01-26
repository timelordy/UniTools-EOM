'''
Программа содержит настройки Tesla. С помощью данной команды вы можете настроить программу по своему усмотрению. Настройки привязываются к конкретному проекту.
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
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import *
# Библиотека чтобы сохранять и открывать файлы
import System.IO



#____________________Переменные с которыми работает программа__________________________________________________________________________________

# ВАЖНО! Ревит помнит созданные schema даже при всех закрытых документах. Чтобы он их забыл, нужно перезапускать Ревит!

# Объявим переменные с которыми работает данная программа.
# Разлочить при тестировании в Python Shell. А так получаем на входе от C#
'''
# Переменные отвечающие за соединение с ExtensibleStorage (1-е хранилище)
Guidstr = 'c94ca2e5-771e-407d-9c09-f62feb4448b6'
SchemaName_for_Tesla_settings = 'Tesla_settings_Storage'
FieldName_for_Tesla_settings = 'Tesla_settings_list'
Cable_section_calculation_method_for_Tesla_settings = 'Cable_section_calculation_method'
Volt_Dropage_key_for_Tesla_settings = 'Volt_Dropage_key'
Cable_stock_for_Tesla_settings = 'Cable_stock_for_circuitry'
Electrical_Circuit_PathMode_method_for_Tesla_settings = 'Electrical_Circuit_PathMode_method'
DeltaU_boundary_value_for_Tesla_settings = 'deltaU_boundary_value'
Round_value_for_Tesla_settings = 'Round_value_ts'
Require_tables_select_for_Tesla_settings = 'Require_tables_select_ts'
Require_PHtables_select_for_Tesla_settings = 'Require_PHtables_select_ts'
Select_Cable_by_DeltaU_for_Tesla_settings = 'Select_Cable_by_DeltaU_ts'
flat_calculation_way_for_Tesla_settings = 'flat_calculation_way_ts'
Distributed_Volt_Dropage_koefficient_for_Tesla_settings = 'Distributed_Volt_Dropage_koefficient' 
PhaseNaming_for_Tesla_settings = 'Phase_Naming' 

# Необходимые данные для соединения со вторым хранилищем (где храним инфу о распределённых потерях) (2-е хранилище)
Guidstr_Distributed_volt_dropage_Tesla_settings = '64261417-f3b0-4156-9db2-5c2fd1fd2059'
SchemaName_for_Distributed_volt_dropage_Tesla_settings = 'Distributed_volt_dropage_Tesla_settings_Storage'
FieldName_for_Distributed_volt_dropage_Tesla_settings = 'Distributed_volt_dropage_Tesla_settings_list' # отдельное поле для хранения информации о распределённых потерях

# Необходимые данные для соединения с хранилищем Calculation Resourses (CR) (3-е хранилище)
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


# Переменные отвечающие за соединение с хранилищем имён параметров (4-е хранилище)
Guidstr_Param_Names_Storage = '44bf8d44-4a4a-4fde-ada8-cd7d802648c4'
SchemaName_for_Param_Names_Storage = 'Param_Names_Storage'
FieldName_for_Param_Names_Storage = 'Param_Names_Storage_list'


# Переменные отвечающие за соединение с хранилищем значений освещённости (5-е хранилище)
Guidstr_Illumination_Values_Storage = '36f085d8-43ee-4230-acec-099431f45dad'
SchemaName_for_Illumination_Values_Storage = 'Illumination_Values_Storage'
FieldName_for_Illumination_Values_Storage = 'Illumination_Values_Storage_list'



# Переменные отвечающие за соединение с хранилищем коэффициентов спроса (6-е хранилище)
Guidstr_Kc_Storage = '3de55145-e17d-4f10-be27-daf375c317af'
SchemaName_for_Kc = 'Koefficients_Storage'
FieldName_for_Kc_1 = 'Kkr_flats_koefficient'
FieldName_for_Kc_2 = 'Flat_count_SP'
FieldName_for_Kc_3 = 'Flat_unit_wattage_SP'
FieldName_for_Kc_4 = 'Py_high_comfort'
FieldName_for_Kc_5 = 'Ks_high_comfort'
FieldName_for_Kc_6 = 'Flat_count_high_comfort'
FieldName_for_Kc_7 = 'Ko_high_comfort'
FieldName_for_Kc_8 = 'Kcpwrres'
FieldName_for_Kc_9 = 'Elevator_count_SP'
FieldName_for_Kc_10 = 'Ks_elevators_below12'
FieldName_for_Kc_11 = 'Ks_elevators_above12'
FieldName_for_Kc_12 = 'Load_Class_elevators'
FieldName_for_Kc_13 = 'Load_Class_falts'
FieldName_for_Kc_14 = 'Ks_Reserve_1'
FieldName_for_Kc_15 = 'Ks_Reserve_2'


# Данные для соединения с хранилищем пользовательских Кс (7-е хранилище)
Guidstr_UserKc = '3772f576-269f-4c05-8fa9-c5f9e5f65390'
SchemaName_for_UserKc = 'UserKc_SchemaName'
FieldName_for_UserKc = 'UserKc_FieldName'


# Данные для соединения с хранилищем пользовательских Р мощностей (7.2 хранилище)
Guidstr_UserP = 'c1a6b65b-822c-4091-8592-b8252b3bdbc4'
SchemaName_for_UserP = 'UserP_SchemaName'
FieldName_for_UserP = 'UserP_FieldName'


# Данные для соединения с хранилищем пользовательских формул (7.3 хранилище)
Guidstr_UserFormula = 'd87d5871-ed16-4003-9a23-6c9fc3860600'
SchemaName_for_UserFormula = 'UserFormula_SchemaName'
FieldName_for_UserFormula = 'UserFormula_FieldName'


# Данные для соединения с хранилищем запаса свободного места в НКУ (8 хранилище)
Guidstr_VolumeCapacityNKU = 'be501520-4a57-4ad3-a4df-6f11afe6e007'
SchemaName_for_VolumeCapacityNKU = 'VolumeCapacityNKU_SchemaName'
FieldName_for_VolumeCapacityNKU = 'VolumeCapacityNKU_FieldName'


# Данные для соединения с хранилищем настроек Выбора производителя (9 хранилище)
Guidstr_ManufacturerSettings = '8a3c4aad-74f6-46b2-b685-d17cd7c53a6b'
SchemaName_for_ManufacturerSettings = 'ManufacturerSettings_SchemaName'
FieldName_for_ManufacturerSettings = 'ManufacturerSettings_FieldName'


# Данные для соединения с хранилищем настроек Дополнительные настройки (10 хранилище) !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Guidstr_AdvancedSettings = 'ce52623d-2141-4760-b078-785406cb51ee'
SchemaName_for_AdvancedSettings = 'AdvancedSettings_SchemaName'
FieldName_for_AdvancedSettings = 'AdvancedSettings_FieldName'



# Семейства с котроыми работает программа
avt_family_names = ['GA_SHM_2D автоматический выключатель_ВРУ', 'GA_SHM_2D автоматический выключатель_Щит']

# Параметры семейств с которыми работает программа
Param_Circuit_number = 'Номер цепи'
Param_Electric_receiver_Name = 'Наименование электроприёмника'
fam_param_names = ['ADSK_Единица измерения', 'ADSK_Завод-изготовитель', 'ADSK_Наименование', 'ADSK_Обозначение']
# для понимания соответствия: fam_param_names[0] fam_param_names[1] fam_param_names[2]  fam_param_names[3] 
Param_Load_Name = 'TSL_Имя нагрузки'
Param_Rated_Illuminance = 'TSL_Нормируемая освещённость'
Param_Feeding_Chain = 'TSL_Номер питающей цепи'
Param_Outgoing_Chain = 'TSL_Номер отходящей цепи'

# Имена параметров для Витиной проги по получению заданий
Param_ES_Rated_Power = 'ADSK_Номинальная мощность'
Param_ES_Cosinus = 'ADSK_Коэффициент мощности'
Param_ES_Phase_Count = 'ADSK_Количество фаз'
Param_ES_Voltage = 'ADSK_Напряжение'
# И для других Витиных прог:
Param_TSL_Area = 'TSL_Площадь'
Param_TSL_MarkFromLevel = 'TSL_Отметка от уровня_СП'
Param_TSL_MarkFromZero = 'TSL_Отметка от нуля_СП'
Param_TSL_BatchGroupName = 'TSL_Имя сборки (группы)'
Param_TSL_SpaceName = 'TSL_Имя пространства'
Param_TSL_LevelName = 'TSL_Имя уровня'
# Ещё имена параметров
Param_ADSK_product_code = 'ADSK_Код изделия'
Param_TSL_LuminareInfo = 'TSL_Сведения о светильниках' # (в ПИКе MEP_Сведения о светильниках)
Param_TSL_WireMark = 'TSL_Марка проводника'
Param_TSL_WireLength = 'TSL_Длина проводника'
Param_TSL_WireCountAndSection = 'TSL_Количество жил и сечение проводника'
Param_TSL_Quantity = 'ADSK_Количество'
Param_TSL_MarkFromFloor = 'TSL_Отметка от чистого пола_СП'
Param_TSL_CableTrayGroupNumber = 'TSL_КНК_Номер цепи'
Param_TSL_CableTrayVolumeOfCombustibleMass = 'TSL_КНК_Объём горючей массы (л/м)'
Param_TSL_CableTrayTrayOccupancy = 'TSL_КНК_Заполняемость лотка (%)'
Param_TSL_SpaceNumber = 'TSL_Номер пространства'
Param_TSL_WeightTrackSection = 'TSL_КНК_Масса участка (кг/м)'
Param_ADSK_grouping = 'ADSK_Группирование'
Param_TSL_Param_Laying_Method = 'TSL_Способ прокладки'
Param_TSL_IdLinkedFile = 'TSL_Id связанного файла Revit'
Param_TSL_IdOriginalElement = 'TSL_Id исходного элемента'
Param_TSL_CopyReport = 'TSL_Отчёт о копировании'
Param_TSL_BroadcastTask = 'TSL_Транслировать в качестве задания'
Param_TSL_LinkedFileName = 'TSL_Имя связанного файла Revit'
Param_ADSK_Position = 'ADSK_Позиция'
Param_ADSK_MassText = 'ADSK_Масса_Текст'
Param_ADSK_Note = 'ADSK_Примечание'
Param_TSL_QuantityText = 'TSL_Количество_Текст'
Param_ADSK_Kit = 'ADSK_Комплект'
Param_TSL_FarestWireLength = "TSL_Длина проводника до дальнего устройства"
Param_TSL_ReducedWireLength = "TSL_Длина проводника приведённая"
Param_ADSK_dimension_length = "ADSK_Размер_Длина"
Param_ADSK_dimension_width = "ADSK_Размер_Ширина"
Param_ADSK_dimension_diameter = "ADSK_Размер_Диаметр"
Param_TSL_CableTrayGroupNumberEM = "TSL_КНК_Номер цепи ЭМ"
Param_TSL_CableTrayGroupNumberEO = "TSL_КНК_Номер цепи ЭО"
Param_TSL_CableTrayGroupNumberES = "TSL_КНК_Номер цепи ЭС"

# Имя самой программы
Program_name = 'Teslabim'
'''

#_______________________________________________________________________________________________________________________________________________________________________________________






# Из C# мы получаем списки с конкретным типом данных string. И почему-то к таким спискам нельзя применять некоторые команды, например .count(i.Name)
# поэтому для корректной работы придётся пересобрать все входящие списки заново. Для этого нужен вспомогательный список CS_help = []
CS_help = []
[CS_help.append(i) for i in avt_family_names]
avt_family_names = []
[avt_family_names.append(i) for i in CS_help]

#____________________________________________________________________________________________________









#_________________________Функции необходимые для работы программы_________________________________________________________________________________________________


# Функция записи диапазона табличных значений из буфера обмена в таблицу винформы datagridview
# На входе datagridview в виде self._CRF_Wires_dataGridView		
# На выходе - изменённые значения соответствующих ячеек в datagridview
# Пример обращения insert_from_clipboard_to_datagridview(self._CRF_Wires_dataGridView)
def insert_from_clipboard_to_datagridview (some_dataGridView):
	#_______принимаем данные из буфера обмена_________
	# работает после импорта from System.Windows.Forms import *
	ClipboardText = Clipboard.GetText() # получим '100\t200\t\t300\r\n101\t201\t\t301\r\n'
	# разобьём данные из буфера на список списков (т.к. мы подразумеваем что вставляется таблица из exel)	
	# ClipboardText.split('\r\n') # - ['100\t200\t\t300', '101\t201\t\t301']. Тут каждый элемент списка - это строка со значениями из exel
	global data_to_CtrlV
	data_to_CtrlV = [] # список с данными для вставки в выделенные ячейки
	for i in ClipboardText.split('\r\n'):
		data_to_CtrlV.append(i.split('\t')) # получаем [['100', '200', '', '300'], ['101', '201', '', '301']]. Кол-во элементов списка = кол-ву строк, кол-во элементов подсписков = кол-ву столбцов
	# Бывает что последний элемент это '', выкинем его.
	if data_to_CtrlV[-1] == ['']:
		data_to_CtrlV = data_to_CtrlV[:-1]
	# Теперь смотрим сколько ячеек выделено
	global Selected_cells
	Selected_cells = [i for i in some_dataGridView.SelectedCells] # список вида: [<System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000284 [DataGridViewTextBoxCell { ColumnIndex=3, RowIndex=1 }]>, <System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000285 [DataGridViewTextBoxCell { ColumnIndex=3, RowIndex=0 }]>, <System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000286 [DataGridViewTextBoxCell { ColumnIndex=2, RowIndex=1 }]>, <System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000287 [DataGridViewTextBoxCell { ColumnIndex=1, RowIndex=1 }]>, <System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000288 [DataGridViewTextBoxCell { ColumnIndex=2, RowIndex=0 }]>, <System.Windows.Forms.DataGridViewTextBoxCell object at 0x0000000000000289 [DataGridViewTextBoxCell { ColumnIndex=1, RowIndex=0 }]>]
	# Составим список списков аналогичный data_to_CtrlV чтобы сверить, что выбранные диапазоны одинаковые
	global Selected_cells_check
	Selected_cells_check = [] # вид списка: [[0, 1, 2, 3], [0, 1, 2, 3]] # по структуре аналогичный data_to_CtrlV
	rowdifference = max([i.RowIndex for i in Selected_cells]) - min([i.RowIndex for i in Selected_cells])
	columndifference = max([i.ColumnIndex for i in Selected_cells]) - min([i.ColumnIndex for i in Selected_cells])
	for i in range(rowdifference + 1): # заполняем список подсписками по количеству выбранных строк
		Selected_cells_check.append([j for j in range(columndifference + 1)]) # а подсписки заполняем условными значениями которые скажут нам о количестве выбранных столбцов
	# Теперь сравним списки и выдадим предупреждение если они не соответствуют друг другу
	if len(data_to_CtrlV) != len(Selected_cells_check) or len(data_to_CtrlV[0]) != len(Selected_cells_check[0]):
		TaskDialog.Show('Настройки', 'Выделенный диапазон не совпадает со вставляемым')
	else: # если диапазоны совпадают
		#pass
		# начнём писать из буфера. При этом порядковые номера строк и столбцов таблицы dataGridView нужно привести к 0.
		for n, i in enumerate(data_to_CtrlV): # n - строки, m - столбцы
			for m, j in enumerate(i):
				some_dataGridView[m + min([i.ColumnIndex for i in Selected_cells]), n + min([i.RowIndex for i in Selected_cells])].Value = j





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

# Функция проверяет можно ли преобразовать строку во float. Выдаёт True если можно, False если строка не является числом
# Обращение: is_Float('2.3') или is_Float('2,3')
def is_Float (inpstring):
	symbollist = ['0','1','2','3','4','5','6','7','8','9','.',',','']
	symbollistonlynumbers = ['0','1','2','3','4','5','6','7','8','9']
	exit_bool_list = []
	a = 0
	while a < len(inpstring):
		if inpstring[a] not in symbollist:
			exit_bool_list.append(False)
		else:
			exit_bool_list.append(True)
		a = a + 1
	if len(inpstring) > 0:
		if inpstring[0] not in symbollistonlynumbers: # проверяем что первый символ это цифра
			exit_bool_list.append(False)
#	if inpstring[len(inpstring)-1] not in symbollistonlynumbers:
#		exit_bool_list.append(False)
	if False in exit_bool_list:
		exit_bool = False
	else:
		exit_bool = True
	return exit_bool




# Функция записи 15 полей списков строк в ExtensibleStorage
# на входе: Write_several_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject, SchemaName_for_CR, FieldName_for_CR_1, CR_Sections_of_cables_Storagelist, FieldName_for_CR_2, CR_Currents_for_multiwire_copper_cables_Storagelist, .....) 
# важен тип входных данных:_________________________________as Guid__________as Object___________as string___________as string__________as List (элементы д.б. str)_____________
def Write_several_fields_to_ExtensibleStorage (schemaGuid, Object_to_connect_ES, SchSchemaName, SchFieldName1, DataList1, SchFieldName2, DataList2, SchFieldName3, DataList3, SchFieldName4, DataList4, SchFieldName5, DataList5, SchFieldName6, DataList6, SchFieldName7, DataList7, SchFieldName8, DataList8, SchFieldName9, DataList9, SchFieldName10, DataList10, SchFieldName11, DataList11, SchFieldName12, DataList12, SchFieldName13, DataList13, SchFieldName14, DataList14, SchFieldName15, DataList15):

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
	fb11 = sb.AddArrayField(SchFieldName11, str)
	fb12 = sb.AddArrayField(SchFieldName12, str)
	fb13 = sb.AddArrayField(SchFieldName13, str)
	fb14 = sb.AddArrayField(SchFieldName14, str)
	fb15 = sb.AddArrayField(SchFieldName15, str)
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
	field11 = sch.GetField(SchFieldName11)
	field12 = sch.GetField(SchFieldName12)
	field13 = sch.GetField(SchFieldName13)
	field14 = sch.GetField(SchFieldName14)
	field15 = sch.GetField(SchFieldName15)
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
	ent.Set[IList[str]](field11, List[str](DataList11))
	ent.Set[IList[str]](field12, List[str](DataList12))
	ent.Set[IList[str]](field13, List[str](DataList13))
	ent.Set[IList[str]](field14, List[str](DataList14))
	ent.Set[IList[str]](field15, List[str](DataList15))
	#Записываем Entity в элемент:
	t = Transaction(doc, 'Create storage')
	t.Start()
	Object_to_connect_ES.SetEntity(ent)
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








# Функция по добавлению нового параметра в определённую категорию семейств. По экземпляру. Как по типу - хз.
# Создаёт группу в ФОП и предлагает создать в ней параметр если таких там раньше не было. А уж потом предлагает добавить параметр к указанным категорям семейств.
# На входе: 
# GroupName_in_FOP - имя группы в ФОП в которой должен быть нужный параметр
# Param_Name - имя нового параметра
# Убрали из обращения из-за 2023 Ревита Param_Type - тип нового параметра. В формате ParameterType.ElectricalIlluminance. Т.е. Autodesk.Revit.DB.ParameterType.ElectricalIlluminance
# BuiltInCategory_Name - внутреннее имя категории семейств к которым мы хотим добавить новый параметр. В формате Autodesk.Revit.DB.BuiltInCategory.OST_MEPSpaces
# BuiltInParameter_Group- в какую группу добавлять новый параметр. Например BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING в виде: Autodesk.Revit.DB.BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING
# Guidstr - текстовая строка с уникальным гуидом который будет присвоен новому параметру. Например 'c8de45ca-92dd-4b87-a09f-c3c6dc77b914'
# На выходе числовые значения:
# 0 - команда была отменена пользователем
# 1 - Не был указан путь к ФОПу в модели
# 2 - В модели отсутствуют семейства нужной категории
# 3 - Нужный параметр уже был в нужных семействах
# 4 - Параметр был успешно добавлен к нужным семействам
# 5 - Параметр уже был в ФОПе, но с другим типом данных (т.е. не удалось добавить нужный параметр к семействам)
# Обращение: Add_a_new_Param_to_Category ('TESLA', 'TSL_Нормируемая освещённость', ParameterType.ElectricalIlluminance, BuiltInCategory.OST_MEPSpaces)
# ara = Add_a_new_Param_to_Category ('PETA', 'Vaska1', ParameterType.ElectricalIlluminance, BuiltInCategory.OST_MEPSpaces)
# ara = Add_a_new_Param_to_Category ('PETA', 'Vaska2', ParameterType.Text, BuiltInCategory.OST_ElectricalFixtures)
# ara = Add_a_new_Param_to_Category ('PETA', 'Vaska2', ParameterType.ElectricalIlluminance, BuiltInCategory.OST_ElectricalFixtures)
def Add_a_new_Param_to_Category (GroupName_in_FOP, Param_Name, BuiltInCategory_Name, BuiltInParameter_Group, Guidstr):
	# Чтоб тестить:
	'''
	GroupName_in_FOP = 'TESLA'
	Param_Name = 'TSL_Нормируемая освещённость'
	BuiltInCategory_Name = BuiltInCategory.OST_MEPSpaces
	BuiltInParameter_Group = BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING
	Guidstr = 'c8de45ca-92dd-4b87-a09f-c3c6dc77b914'
	'''
	exit_bool = 0 # выходная логическая переменная.

	try:
		Param_Type = ParameterType.ElectricalIlluminance
	except (NameError): # для Revit 2023 в котором поменяли обращение к типа параметра https://thebuildingcoder.typepad.com/blog/2021/04/whats-new-in-the-revit-2022-api.html#4.1.1
		Param_Type = ForgeTypeId('autodesk.spec.aec.electrical:illuminance-1.0.0') # Выдаёт <Autodesk.Revit.DB.ForgeTypeId object at 0x000000000000003F [Autodesk.Revit.DB.ForgeTypeId]>


	# Выясним есть ли указанный параметр у определённой категории семейств. А то может и продолжать не надо.
	# Выберем семейство указанной категории и выясним есть ли у него указанный параметр.
	# вытаскиваем все семейства указанной категории из проекта
	Elems_of_Categoty = FilteredElementCollector(doc).OfCategory(BuiltInCategory_Name).ToElements()
	# Если нет семейств этой категории в модели, выкинуть пользователя
	if len(Elems_of_Categoty) == 0:
		#raise Exception('В модели отсутствуют семейства категории "' + BuiltInCategory_Name.ToString() + '".')
		exit_bool = 2
		return(exit_bool) # прекратить выполнение функции
	# Возьмём один элемент и посмотрим есть ли у него нужный нам параметр.
	test_el = Elems_of_Categoty[0]
	Param_is_in_family = False # вспомогательная переменная: есть ли параметр в семействе?
	try:
		if Param_Name in [p.Definition.Name for p in test_el.Symbol.Parameters]: # проверяем есть ли вообще Тип у данной категории семейств. Потому что например у Пространств Типа нет в принципе.
			Param_is_in_family = True
	except:
		pass
	if Param_Name in [p.Definition.Name for p in test_el.Parameters]: # если такой параметр вообще есть в семействе (и он по экземпляру)...
		Param_is_in_family = True
	else: # нет такого параметра
		Param_is_in_family = False

	if Param_is_in_family == True: # если параметр уже есть в семействе - закончить функцию
		exit_bool = 3
		return(exit_bool) # прекратить выполнение функции


	

	GuidObjforParam = System.Guid(Guidstr)

	# Сначала выясняем указан ли ФОП вообще:
	definition_file = doc.Application.OpenSharedParameterFile() # <Autodesk.Revit.DB.DefinitionFile object at 0x000000000000002B [Autodesk.Revit.DB.DefinitionFile]>
	if definition_file == None:
		#raise Exception('Не указан путь к файлу общих параметров (ФОП). Пожалуйста, укажите путь к ФОП на вкладке Управление и перезапустите команду')
		exit_bool = 1
		return(exit_bool) # прекратить выполнение функции

	# Достаём из ФОПа группу с указанным именем
	definition_Group = definition_file.Groups.get_Item(GroupName_in_FOP) # <Autodesk.Revit.DB.DefinitionGroup object at 0x0000000000000031 [Autodesk.Revit.DB.DefinitionGroup]>
	if definition_Group == None: # если такой группы нет, создадим её
		definition_Group = definition_file.Groups.Create(GroupName_in_FOP) # создаёт новую группу в ФОПе

	# Ищем в этой группе нужный нам параметр:
	definition = definition_Group.Definitions.get_Item(Param_Name)

	if definition == None: # если такого параметра в группе нет, предложим его создать
		td = TaskDialog('Создание параметра')
		td.MainContent = 'Для работы программы необходим общий параметр "' + Param_Name + '". Создать его?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Будет создан параметр "' + Param_Name + '" в группе "' + GroupName_in_FOP + '"')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет', 'Вернуться в предыдущее окно')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			# Формируем описание нового параметра:
			# создаёт описание параметра по Имени и типу параметра
			defOptions = ExternalDefinitionCreationOptions(Param_Name, Param_Type) # <Autodesk.Revit.DB.ExternalDefinitionCreationOptions object at 0x0000000000000037 [Autodesk.Revit.DB.ExternalDefinitionCreationOptions]>
			defOptions.GUID = GuidObjforParam # задаём строго гуид для будущего параметра
			# создаём параметр в группе
			definition = definition_Group.Definitions.Create(defOptions) # <Autodesk.Revit.DB.ExternalDefinition object at 0x0000000000000039 [Autodesk.Revit.DB.ExternalDefinition]>
		else: # если пользователь закрыл окошко
			#raise Exception('Команда отменена')
			exit_bool = 0
			return(exit_bool) # прекратить выполнение функции

	# Если такой параметр уже был в ФОПе,
	# проверим совпадает ли тип параметра из ФОП и из того что подали на входе в функцию.
	# А то вдруг в ФОПе уже был такой параметр, но с другим типом данных.
	try:
		if definition.ParameterType != Param_Type:
			exit_bool = 5
			return(exit_bool) # прекратить выполнение функции
	except: # для Revit 2023 в котором поменяли обращение к типа параметра
		if definition.GetDataType() != Param_Type:
			exit_bool = 5
			return(exit_bool) # прекратить выполнение функции



	# Если нужного параметра в семействе нет, то предложим его добавить:
	if Param_is_in_family == False:
		try:
			td = TaskDialog('Добавление параметра в семейства')
			td.MainContent = 'Для работы программы необходимо добавить параметр "' + Param_Name + '". В семейства категории: "' + BuiltInCategory_Name.ToString() + '". Добавить параметр?'
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Параметр "' + Param_Name + '" будет добавлен ко всем семействам категории "' + BuiltInCategory_Name.ToString() + '"')
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет', 'Вернуться в предыдущее окно')
			GetUserResult = td.Show()
			if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
				# Добавляем новый параметр к указанным категориям семейств Ревита
				# получаем описание категории пространств OST_MEPSpaces
				category = doc.Settings.Categories.get_Item(BuiltInCategory_Name) # <Autodesk.Revit.DB.Category object at 0x000000000000003A [Autodesk.Revit.DB.Category]>
				# Новый пустой набор категорий
				categorySet = doc.Application.Create.NewCategorySet() # <Autodesk.Revit.DB.CategorySet object at 0x000000000000003B [Autodesk.Revit.DB.CategorySet]>
				categorySet.Insert(category) # вставляем в него нашу категорию "Пространства"
				instanceBinding = doc.Application.Create.NewInstanceBinding(categorySet) # <Autodesk.Revit.DB.InstanceBinding object at 0x000000000000003C [Autodesk.Revit.DB.InstanceBinding]>
				# Добавляем параметр в указанную категорию семейств (параметр получается по экземпляру)
				t=Transaction(doc, 'Add_Parameter')
				t.Start()
				doc.ParameterBindings.Insert(definition, instanceBinding, BuiltInParameter_Group)
				t.Commit()

				exit_bool = 4
		except: # В Ревите 2025 поменяли способ создания параметров, поэтому скажем юзеру чтобы сам добавлял.
			exit_bool = 6

		else: # если пользователь закрыл окошко
			#raise Exception('Команда отменена')
			exit_bool = 0
			return(exit_bool) # прекратить выполнение функции
	elif Param_is_in_family == True: # если параметр уже есть в семействе - закончить функцию
		exit_bool = 3

	return(exit_bool)

'''
ara = Add_a_new_Param_to_Category ('PETA', 'Vaska2', ParameterType.Text, BuiltInCategory.OST_ElectricalFixtures)
TaskDialog.Show('название окна', str(ara))
doc.ParameterBindings.Insert(def, typeBinding, BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING)
'''
# Ещё понять как добавлять по типу или по экземаляру!!!!




# Функция экспорта настроек из исходных данных для расчётов
# На входе списки со всех элементов окошка:
#Currents_and_SectionsOutput # [['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['22', '30', '40', '51', '70', '94', '119', '148', '180', '232', '282', '328', '379', '434', '514', '593', '0', '0', '0', '0'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030'], ['0', '23', '31', '39', '54', '73', '89', '111', '135', '173', '210', '244', '282', '322', '380', '439', '0', '0', '0', '0'], ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858'], ['0', '19.5', '26', '33', '46', '61', '84', '105', '128', '166', '203', '237', '274', '315', '375', '434', '526', '610', '711', '858'], ['13.35', '8.0', '5.0', '3.33', '2.0', '1.25', '0.8', '0.57', '0.4', '0.29', '0.21', '0.17', '0.13', '0.11', '0.08', '0.07', '0', '0', '0', '0'], ['22.2', '13.3', '8.35', '5.55', '3.33', '2.08', '1.33', '0.95', '0.67', '0.48', '0.35', '0.28', '0.22', '0.18', '0.15', '0.12', '0', '0', '0', '0'], ['0.11', '0.09', '0.1', '0.09', '0.07', '0.07', '0.07', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0', '0', '0', '0']]
#Current_breakersOutput # ['10', '16', '20', '25', '32', '40', '50', '63', '80', '100', '125', '160', '200', '250', '315', '400', '500', '630', '700', '800', '900', '1000']
#Cables_trays_reduction_factorOutput # ['1.0', '0.87', '0.8', '0.77', '0.75', '0.73', '0.71', '0.7', '0.68']
#CB_reduction_factorOutput # ['1.0', '0.8', '0.8', '0.7', '0.7', '0.6', '0.6', '0.6', '0.6', '0.5']
#VoltageDrop_Coefficiets_KnorrOutput # ['72', '12', '44', '7.4']
#VoltageOutput # ['380', '220']
# На выходе txt файл закодированный как надо.
# Обращение: CRF_settings_Export(Currents_and_SectionsOutput, Current_breakersOutput, Cables_trays_reduction_factorOutput, CB_reduction_factorOutput, VoltageDrop_Coefficiets_KnorrOutput, VoltageOutput)
def CRF_settings_Export (Currents_and_SectionsOutput, Current_breakersOutput, Cables_trays_reduction_factorOutput, CB_reduction_factorOutput, VoltageDrop_Coefficiets_KnorrOutput, VoltageOutput):
	
	# '$$@@$$' # разделитель следующей переменной. Например между Currents_and_SectionsOutput и Current_breakersOutput
	# '&&@@&&' # разделитель следующего списка, если кодируется список списков. Напрмер Currents_and_SectionsOutput
	# '<<@@>>' # разделитель элементов внутри списка.

	# Кодируем Currents_and_SectionsOutput.
	Export_text_string = '' # строка для экспорта
	Export_text_string = Export_text_string + '$$@@$$'
	for i in Currents_and_SectionsOutput:
		Export_text_string = Export_text_string + '&&@@&&' # разделитель нового списка
		for j in i:
			try:
				Export_text_string = Export_text_string + j + '<<@@>>' # разделитель значений в строке
			except:
				Export_text_string = Export_text_string + '' + '<<@@>>' # чтобы пустые значения в таблице воспринимались пустыми строками, а не NoneType
	# На выходе получаем: '$$@@$$&&@@&&1.5<<@@>>2.5<<@@>>4<<@@>>6<<@@>>10<<@@>>16<<@@>>25<<@@>>35<<@@>>50<<@@>>70<<@@>>95<<@@>>120<<@@>>150<<@@>>185<<@@>>240<<@@>>300<<@@>>400<<@@>>500<<@@>>630<<@@>>800<<@@>>&&@@&&22<<@@>>30<<@@>>40<<@@>>51<<@@>>70<<@@>>94<<@@>>119<<@@>>148<<@@>>180<<@@>>232<<@@>>282<<@@>>328<<@@>>379<<@@>>434<<@@>>514<<@@>>593<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>101<<@@>>126<<@@>>153<<@@>>196<<@@>>238<<@@>>276<<@@>>319<<@@>>364<<@@>>430<<@@>>497<<@@>>633<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>110<<@@>>137<<@@>>167<<@@>>216<<@@>>264<<@@>>308<<@@>>356<<@@>>409<<@@>>485<<@@>>561<<@@>>656<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&0<<@@>>23<<@@>>31<<@@>>39<<@@>>54<<@@>>73<<@@>>89<<@@>>111<<@@>>135<<@@>>173<<@@>>210<<@@>>244<<@@>>282<<@@>>322<<@@>>380<<@@>>439<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>78<<@@>>96<<@@>>117<<@@>>150<<@@>>183<<@@>>212<<@@>>245<<@@>>280<<@@>>330<<@@>>381<<@@>>501<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>84<<@@>>105<<@@>>128<<@@>>166<<@@>>203<<@@>>237<<@@>>274<<@@>>315<<@@>>375<<@@>>434<<@@>>526<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&13.35<<@@>>8.0<<@@>>5.0<<@@>>3.33<<@@>>2.0<<@@>>1.25<<@@>>0.8<<@@>>0.57<<@@>>0.4<<@@>>0.29<<@@>>0.21<<@@>>0.17<<@@>>0.13<<@@>>0.11<<@@>>0.08<<@@>>0.07<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&22.2<<@@>>13.3<<@@>>8.35<<@@>>5.55<<@@>>3.33<<@@>>2.08<<@@>>1.33<<@@>>0.95<<@@>>0.67<<@@>>0.48<<@@>>0.35<<@@>>0.28<<@@>>0.22<<@@>>0.18<<@@>>0.15<<@@>>0.12<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0.11<<@@>>0.09<<@@>>0.1<<@@>>0.09<<@@>>0.07<<@@>>0.07<<@@>>0.07<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>'

	# Кодируем Current_breakersOutput.
	Export_text_string = Export_text_string + '$$@@$$'
	for i in Current_breakersOutput:
		try:
			Export_text_string = Export_text_string + i + '<<@@>>' # разделитель значений в строке
		except:
			Export_text_string = Export_text_string + '' + '<<@@>>' # чтобы пустые значения в таблице воспринимались пустыми строками, а не NoneType
	# На выходе получаем: '$$@@$$&&@@&&1.5<<@@>>2.5<<@@>>4<<@@>>6<<@@>>10<<@@>>16<<@@>>25<<@@>>35<<@@>>50<<@@>>70<<@@>>95<<@@>>120<<@@>>150<<@@>>185<<@@>>240<<@@>>300<<@@>>400<<@@>>500<<@@>>630<<@@>>800<<@@>>&&@@&&22<<@@>>30<<@@>>40<<@@>>51<<@@>>70<<@@>>94<<@@>>119<<@@>>148<<@@>>180<<@@>>232<<@@>>282<<@@>>328<<@@>>379<<@@>>434<<@@>>514<<@@>>593<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>101<<@@>>126<<@@>>153<<@@>>196<<@@>>238<<@@>>276<<@@>>319<<@@>>364<<@@>>430<<@@>>497<<@@>>633<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>110<<@@>>137<<@@>>167<<@@>>216<<@@>>264<<@@>>308<<@@>>356<<@@>>409<<@@>>485<<@@>>561<<@@>>656<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&0<<@@>>23<<@@>>31<<@@>>39<<@@>>54<<@@>>73<<@@>>89<<@@>>111<<@@>>135<<@@>>173<<@@>>210<<@@>>244<<@@>>282<<@@>>322<<@@>>380<<@@>>439<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>78<<@@>>96<<@@>>117<<@@>>150<<@@>>183<<@@>>212<<@@>>245<<@@>>280<<@@>>330<<@@>>381<<@@>>501<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>84<<@@>>105<<@@>>128<<@@>>166<<@@>>203<<@@>>237<<@@>>274<<@@>>315<<@@>>375<<@@>>434<<@@>>526<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&13.35<<@@>>8.0<<@@>>5.0<<@@>>3.33<<@@>>2.0<<@@>>1.25<<@@>>0.8<<@@>>0.57<<@@>>0.4<<@@>>0.29<<@@>>0.21<<@@>>0.17<<@@>>0.13<<@@>>0.11<<@@>>0.08<<@@>>0.07<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&22.2<<@@>>13.3<<@@>>8.35<<@@>>5.55<<@@>>3.33<<@@>>2.08<<@@>>1.33<<@@>>0.95<<@@>>0.67<<@@>>0.48<<@@>>0.35<<@@>>0.28<<@@>>0.22<<@@>>0.18<<@@>>0.15<<@@>>0.12<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0.11<<@@>>0.09<<@@>>0.1<<@@>>0.09<<@@>>0.07<<@@>>0.07<<@@>>0.07<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>$$@@$$10<<@@>>16<<@@>>20<<@@>>25<<@@>>32<<@@>>40<<@@>>50<<@@>>63<<@@>>80<<@@>>100<<@@>>125<<@@>>160<<@@>>200<<@@>>250<<@@>>315<<@@>>400<<@@>>500<<@@>>630<<@@>>700<<@@>>800<<@@>>900<<@@>>1000<<@@>>'

	# Кодируем Cables_trays_reduction_factorOutput.
	Export_text_string = Export_text_string + '$$@@$$'
	for i in Cables_trays_reduction_factorOutput:
		try:
			Export_text_string = Export_text_string + i + '<<@@>>' # разделитель значений в строке
		except:
			Export_text_string = Export_text_string + '' + '<<@@>>' # чтобы пустые значения в таблице воспринимались пустыми строками, а не NoneType
	# На выходе получаем: '$$@@$$&&@@&&1.5<<@@>>2.5<<@@>>4<<@@>>6<<@@>>10<<@@>>16<<@@>>25<<@@>>35<<@@>>50<<@@>>70<<@@>>95<<@@>>120<<@@>>150<<@@>>185<<@@>>240<<@@>>300<<@@>>400<<@@>>500<<@@>>630<<@@>>800<<@@>>&&@@&&22<<@@>>30<<@@>>40<<@@>>51<<@@>>70<<@@>>94<<@@>>119<<@@>>148<<@@>>180<<@@>>232<<@@>>282<<@@>>328<<@@>>379<<@@>>434<<@@>>514<<@@>>593<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>101<<@@>>126<<@@>>153<<@@>>196<<@@>>238<<@@>>276<<@@>>319<<@@>>364<<@@>>430<<@@>>497<<@@>>633<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>110<<@@>>137<<@@>>167<<@@>>216<<@@>>264<<@@>>308<<@@>>356<<@@>>409<<@@>>485<<@@>>561<<@@>>656<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&0<<@@>>23<<@@>>31<<@@>>39<<@@>>54<<@@>>73<<@@>>89<<@@>>111<<@@>>135<<@@>>173<<@@>>210<<@@>>244<<@@>>282<<@@>>322<<@@>>380<<@@>>439<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>78<<@@>>96<<@@>>117<<@@>>150<<@@>>183<<@@>>212<<@@>>245<<@@>>280<<@@>>330<<@@>>381<<@@>>501<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>84<<@@>>105<<@@>>128<<@@>>166<<@@>>203<<@@>>237<<@@>>274<<@@>>315<<@@>>375<<@@>>434<<@@>>526<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&13.35<<@@>>8.0<<@@>>5.0<<@@>>3.33<<@@>>2.0<<@@>>1.25<<@@>>0.8<<@@>>0.57<<@@>>0.4<<@@>>0.29<<@@>>0.21<<@@>>0.17<<@@>>0.13<<@@>>0.11<<@@>>0.08<<@@>>0.07<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&22.2<<@@>>13.3<<@@>>8.35<<@@>>5.55<<@@>>3.33<<@@>>2.08<<@@>>1.33<<@@>>0.95<<@@>>0.67<<@@>>0.48<<@@>>0.35<<@@>>0.28<<@@>>0.22<<@@>>0.18<<@@>>0.15<<@@>>0.12<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0.11<<@@>>0.09<<@@>>0.1<<@@>>0.09<<@@>>0.07<<@@>>0.07<<@@>>0.07<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>$$@@$$10<<@@>>16<<@@>>20<<@@>>25<<@@>>32<<@@>>40<<@@>>50<<@@>>63<<@@>>80<<@@>>100<<@@>>125<<@@>>160<<@@>>200<<@@>>250<<@@>>315<<@@>>400<<@@>>500<<@@>>630<<@@>>700<<@@>>800<<@@>>900<<@@>>1000<<@@>>$$@@$$1.0<<@@>>0.87<<@@>>0.8<<@@>>0.77<<@@>>0.75<<@@>>0.73<<@@>>0.71<<@@>>0.7<<@@>>0.68<<@@>>'

	# Кодируем CB_reduction_factorOutput.
	Export_text_string = Export_text_string + '$$@@$$'
	for i in CB_reduction_factorOutput:
		try:
			Export_text_string = Export_text_string + i + '<<@@>>' 
		except:
			Export_text_string = Export_text_string + '' + '<<@@>>' 

	# Кодируем VoltageDrop_Coefficiets_KnorrOutput.
	Export_text_string = Export_text_string + '$$@@$$'
	for i in VoltageDrop_Coefficiets_KnorrOutput:
		try:
			Export_text_string = Export_text_string + i + '<<@@>>' 
		except:
			Export_text_string = Export_text_string + '' + '<<@@>>'

	# Кодируем VoltageOutput.
	Export_text_string = Export_text_string + '$$@@$$'
	for i in VoltageOutput:
		try:
			Export_text_string = Export_text_string + i + '<<@@>>' 
		except:
			Export_text_string = Export_text_string + '' + '<<@@>>'

	return Export_text_string






# Функция импорта исходных данных для расчёта
# На входе кодированная строка из внешнего файла
# На выходе кортеж списков по порядку: Currents_and_SectionsOutput, Current_breakersOutput, Cables_trays_reduction_factorOutput, CB_reduction_factorOutput, VoltageDrop_Coefficiets_KnorrOutput, VoltageOutput
def CRF_settings_Import (Import_text_string):
	# '$$@@$$' # разделитель следующей переменной. Например между Currents_and_SectionsOutput и Current_breakersOutput
	# '&&@@&&' # разделитель следующего списка, если кодируется список списков. Напрмер Currents_and_SectionsOutput
	# '<<@@>>' # разделитель элементов внутри списка.
	
	# Надо разбить входную строку на подсписки. Их разделение взять по маркеру '$$@@$$'
	Vars_splites_lst = Import_text_string.split('$$@@$$')[1:] # ['&&@@&&1.5<<@@>>2.5<<@@>>4<<@@>>6<<@@>>10<<@@>>16<<@@>>25<<@@>>35<<@@>>50<<@@>>70<<@@>>95<<@@>>120<<@@>>150<<@@>>185<<@@>>240<<@@>>300<<@@>>400<<@@>>500<<@@>>630<<@@>>800<<@@>>&&@@&&22<<@@>>30<<@@>>40<<@@>>51<<@@>>70<<@@>>94<<@@>>119<<@@>>148<<@@>>180<<@@>>232<<@@>>282<<@@>>328<<@@>>379<<@@>>434<<@@>>514<<@@>>593<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>101<<@@>>126<<@@>>153<<@@>>196<<@@>>238<<@@>>276<<@@>>319<<@@>>364<<@@>>430<<@@>>497<<@@>>633<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>110<<@@>>137<<@@>>167<<@@>>216<<@@>>264<<@@>>308<<@@>>356<<@@>>409<<@@>>485<<@@>>561<<@@>>656<<@@>>749<<@@>>855<<@@>>1030<<@@>>&&@@&&0<<@@>>23<<@@>>31<<@@>>39<<@@>>54<<@@>>73<<@@>>89<<@@>>111<<@@>>135<<@@>>173<<@@>>210<<@@>>244<<@@>>282<<@@>>322<<@@>>380<<@@>>439<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>78<<@@>>96<<@@>>117<<@@>>150<<@@>>183<<@@>>212<<@@>>245<<@@>>280<<@@>>330<<@@>>381<<@@>>501<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>84<<@@>>105<<@@>>128<<@@>>166<<@@>>203<<@@>>237<<@@>>274<<@@>>315<<@@>>375<<@@>>434<<@@>>526<<@@>>610<<@@>>711<<@@>>858<<@@>>&&@@&&13.35<<@@>>8.0<<@@>>5.0<<@@>>3.33<<@@>>2.0<<@@>>1.25<<@@>>0.8<<@@>>0.57<<@@>>0.4<<@@>>0.29<<@@>>0.21<<@@>>0.17<<@@>>0.13<<@@>>0.11<<@@>>0.08<<@@>>0.07<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&22.2<<@@>>13.3<<@@>>8.35<<@@>>5.55<<@@>>3.33<<@@>>2.08<<@@>>1.33<<@@>>0.95<<@@>>0.67<<@@>>0.48<<@@>>0.35<<@@>>0.28<<@@>>0.22<<@@>>0.18<<@@>>0.15<<@@>>0.12<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>&&@@&&0.11<<@@>>0.09<<@@>>0.1<<@@>>0.09<<@@>>0.07<<@@>>0.07<<@@>>0.07<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>', '10<<@@>>16<<@@>>20<<@@>>25<<@@>>32<<@@>>40<<@@>>50<<@@>>63<<@@>>80<<@@>>100<<@@>>125<<@@>>160<<@@>>200<<@@>>250<<@@>>315<<@@>>400<<@@>>500<<@@>>630<<@@>>700<<@@>>800<<@@>>900<<@@>>1000<<@@>>', '1.0<<@@>>0.87<<@@>>0.8<<@@>>0.77<<@@>>0.75<<@@>>0.73<<@@>>0.71<<@@>>0.7<<@@>>0.68<<@@>>']

	# Формируем Currents_and_SectionsOutput.
	Currents_and_SectionsOutput_Imported = [] 
	for i in Vars_splites_lst[0].split('&&@@&&')[1:]: # ['1.5<<@@>>2.5<<@@>>4<<@@>>6<<@@>>10<<@@>>16<<@@>>25<<@@>>35<<@@>>50<<@@>>70<<@@>>95<<@@>>120<<@@>>150<<@@>>185<<@@>>240<<@@>>300<<@@>>400<<@@>>500<<@@>>630<<@@>>800<<@@>>', '22<<@@>>30<<@@>>40<<@@>>51<<@@>>70<<@@>>94<<@@>>119<<@@>>148<<@@>>180<<@@>>232<<@@>>282<<@@>>328<<@@>>379<<@@>>434<<@@>>514<<@@>>593<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>', '19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>101<<@@>>126<<@@>>153<<@@>>196<<@@>>238<<@@>>276<<@@>>319<<@@>>364<<@@>>430<<@@>>497<<@@>>633<<@@>>749<<@@>>855<<@@>>1030<<@@>>', '19<<@@>>25<<@@>>34<<@@>>43<<@@>>60<<@@>>80<<@@>>110<<@@>>137<<@@>>167<<@@>>216<<@@>>264<<@@>>308<<@@>>356<<@@>>409<<@@>>485<<@@>>561<<@@>>656<<@@>>749<<@@>>855<<@@>>1030<<@@>>', '0<<@@>>23<<@@>>31<<@@>>39<<@@>>54<<@@>>73<<@@>>89<<@@>>111<<@@>>135<<@@>>173<<@@>>210<<@@>>244<<@@>>282<<@@>>322<<@@>>380<<@@>>439<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>', '0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>78<<@@>>96<<@@>>117<<@@>>150<<@@>>183<<@@>>212<<@@>>245<<@@>>280<<@@>>330<<@@>>381<<@@>>501<<@@>>610<<@@>>711<<@@>>858<<@@>>', '0<<@@>>19.5<<@@>>26<<@@>>33<<@@>>46<<@@>>61<<@@>>84<<@@>>105<<@@>>128<<@@>>166<<@@>>203<<@@>>237<<@@>>274<<@@>>315<<@@>>375<<@@>>434<<@@>>526<<@@>>610<<@@>>711<<@@>>858<<@@>>', '13.35<<@@>>8.0<<@@>>5.0<<@@>>3.33<<@@>>2.0<<@@>>1.25<<@@>>0.8<<@@>>0.57<<@@>>0.4<<@@>>0.29<<@@>>0.21<<@@>>0.17<<@@>>0.13<<@@>>0.11<<@@>>0.08<<@@>>0.07<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>', '22.2<<@@>>13.3<<@@>>8.35<<@@>>5.55<<@@>>3.33<<@@>>2.08<<@@>>1.33<<@@>>0.95<<@@>>0.67<<@@>>0.48<<@@>>0.35<<@@>>0.28<<@@>>0.22<<@@>>0.18<<@@>>0.15<<@@>>0.12<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>', '0.11<<@@>>0.09<<@@>>0.1<<@@>>0.09<<@@>>0.07<<@@>>0.07<<@@>>0.07<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0.06<<@@>>0<<@@>>0<<@@>>0<<@@>>0<<@@>>']
		cur_lst = [] # текущий подсписок
		cur_lst = i.split('<<@@>>')[:-1] # последний элемент всегда '', его выкидываем ['0.11', '0.09', '0.1', '0.09', '0.07', '0.07', '0.07', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0', '0', '0', '0']
		Currents_and_SectionsOutput_Imported.append(cur_lst) # Получаем точно как и было: [['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['22', '30', '40', '51', '70', '94', '119', '148', '180', '232', '282', '328', '379', '434', '514', '593', '0', '0', '0', '0'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030'], ['0', '23', '31', '39', '54', '73', '89', '111', '135', '173', '210', '244', '282', '322', '380', '439', '0', '0', '0', '0'], ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858'], ['0', '19.5', '26', '33', '46', '61', '84', '105', '128', '166', '203', '237', '274', '315', '375', '434', '526', '610', '711', '858'], ['13.35', '8.0', '5.0', '3.33', '2.0', '1.25', '0.8', '0.57', '0.4', '0.29', '0.21', '0.17', '0.13', '0.11', '0.08', '0.07', '0', '0', '0', '0'], ['22.2', '13.3', '8.35', '5.55', '3.33', '2.08', '1.33', '0.95', '0.67', '0.48', '0.35', '0.28', '0.22', '0.18', '0.15', '0.12', '0', '0', '0', '0'], ['0.11', '0.09', '0.1', '0.09', '0.07', '0.07', '0.07', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0', '0', '0', '0']]

	# Формируем Current_breakersOutput.
	Current_breakersOutput_Imported = [] 
	for i in Vars_splites_lst[1].split('<<@@>>')[:-1]: # последний элемент всегда '', его выкидываем. ['10', '16', '20', '25', '32', '40', '50', '63', '80', '100', '125', '160', '200', '250', '315', '400', '500', '630', '700', '800', '900', '1000']
		Current_breakersOutput_Imported.append(i) # Получаем точно как и было: ['10', '16', '20', '25', '32', '40', '50', '63', '80', '100', '125', '160', '200', '250', '315', '400', '500', '630', '700', '800', '900', '1000']

	# Формируем Cables_trays_reduction_factorOutput.
	Cables_trays_reduction_factorOutput_Imported = [] 
	for i in Vars_splites_lst[2].split('<<@@>>')[:-1]: 
		Cables_trays_reduction_factorOutput_Imported.append(i) 

	# Формируем CB_reduction_factorOutput.
	CB_reduction_factorOutput_Imported = [] 
	for i in Vars_splites_lst[3].split('<<@@>>')[:-1]: 
		CB_reduction_factorOutput_Imported.append(i) 

	# Формируем VoltageDrop_Coefficiets_KnorrOutput.
	VoltageDrop_Coefficiets_KnorrOutput_Imported = [] 
	for i in Vars_splites_lst[4].split('<<@@>>')[:-1]: 
		VoltageDrop_Coefficiets_KnorrOutput_Imported.append(i) 

	# Формируем VoltageOutput.
	VoltageOutput_Imported = [] 
	for i in Vars_splites_lst[5].split('<<@@>>')[:-1]: 
		VoltageOutput_Imported.append(i) 

	return Currents_and_SectionsOutput_Imported, Current_breakersOutput_Imported, Cables_trays_reduction_factorOutput_Imported, CB_reduction_factorOutput_Imported, VoltageDrop_Coefficiets_KnorrOutput_Imported, VoltageOutput_Imported





# Функция по экспорту настроек из основного окна Настроек Теслы
# На входе данные из окна формы.
'''
# Чтоб тестить
Cable_section_by_rated_current_radioButton = True
Volt_Dropage_key_textBox = 'ОСВЕЩ\r\nСВЕТ'
textBox_Length_stock = '10'
trackBar_Length_stock = 1
Electrical_Circuit_PathMode_radioButton4 = True
Electrical_Circuit_PathMode_radioButton1 = False
Electrical_Circuit_PathMode_radioButton2 = False
Electrical_Circuit_PathMode_radioButton3 = False
deltaU_boundary_value_textBox = '2'
Select_Cable_by_DeltaU_checkBox = True
Round_value_textBox = '1'
Require_tables_select_checkBox1 = True
Require_tables_select_checkBox2 = True
flat_calculation_way_radioButton1 = True
Distributed_Volt_Dropage_koefficient_textBox = '0.5'
'''
# Обращение: Main_settings_Export (self._Cable_section_by_rated_current_radioButton.Checked, self._Volt_Dropage_key_textBox.Text, self._textBox_Length_stock.Text, self._trackBar_Length_stock.Value, self._Electrical_Circuit_PathMode_radioButton4.Checked, self._Electrical_Circuit_PathMode_radioButton1.Checked, self._Electrical_Circuit_PathMode_radioButton2.Checked, self._Electrical_Circuit_PathMode_radioButton3.Checked, self._deltaU_boundary_value_textBox.Text, self._Select_Cable_by_DeltaU_checkBox.Checked, self._Round_value_textBox.Text, self._Require_tables_select_checkBox1.Checked, self._Require_tables_select_checkBox2.Checked, self._flat_calculation_way_radioButton1.Checked)
def Main_settings_Export (Cable_section_by_rated_current_radioButton, Volt_Dropage_key_textBox, textBox_Length_stock, trackBar_Length_stock, Electrical_Circuit_PathMode_radioButton4, Electrical_Circuit_PathMode_radioButton1, Electrical_Circuit_PathMode_radioButton2, Electrical_Circuit_PathMode_radioButton3, Electrical_Circuit_PathMode_radioButton5, deltaU_boundary_value_textBox, Select_Cable_by_DeltaU_checkBox, Round_value_textBox, Require_tables_select_checkBox1, Require_tables_select_checkBox2, flat_calculation_way_radioButton1, VolumeCapacityNKU_textBox, trackBar_VolumeCapacityNKU, Distributed_Volt_Dropage_koefficient_textBox, PhaseNaming_ABC_radioButton_Checked):
	# Кодировать будем тупо списком
	# '$$@@$$' # разделитель следующей переменной.
	# '<<@@>>' # разделитель элементов внутри списка.
	# '$$@@$$' Метод выбора сечения кабелей (две радиокнопки, будет список вида ['1', '0']) '$$@@$$' и т.д......
	Export_text_string = '' # строка для экспорта

	# Кодируем Метод выбора сечения кабелей.
	Export_text_string = Export_text_string + '$$@@$$'
	if Cable_section_by_rated_current_radioButton == True:
		Export_text_string = Export_text_string + 'True<<@@>>False'
	else:
		Export_text_string = Export_text_string + 'False<<@@>>True'

	# Кодируем что считать по распределённым потерям
	Export_text_string = Export_text_string + '$$@@$$' + Volt_Dropage_key_textBox

	# Кодируем запас кабеля по умолчанию
	Export_text_string = Export_text_string + '$$@@$$' + textBox_Length_stock + '<<@@>>' + str(trackBar_Length_stock) # '$$@@$$1<<@@>>0$$@@$$\u041e\u0421\u0412\u0415\u0429\r\n\u0421\u0412\u0415\u0422$$@@$$10<<@@>>1'

	# Кодируем режим траектории цепей
	Export_text_string = Export_text_string + '$$@@$$'
	hlp_lst = [Electrical_Circuit_PathMode_radioButton4, Electrical_Circuit_PathMode_radioButton1, Electrical_Circuit_PathMode_radioButton2, Electrical_Circuit_PathMode_radioButton3, Electrical_Circuit_PathMode_radioButton5]
	for i in hlp_lst: # [True, False, False, False, False]
		if i == True:
			Export_text_string = Export_text_string + 'True<<@@>>'
		else:
			Export_text_string = Export_text_string + 'False<<@@>>'
	Export_text_string = Export_text_string[:-6] # удалим последний разделитель элементов

	# Кодируем граничное значение потерь и выбор кабеля по потерям
	Export_text_string = Export_text_string + '$$@@$$'
	Export_text_string = Export_text_string + deltaU_boundary_value_textBox + '<<@@>>'
	if Select_Cable_by_DeltaU_checkBox == False:
		Export_text_string = Export_text_string + 'False'
	else:
		Export_text_string = Export_text_string + 'True'

	# Кодируем до какого знака окруление
	Export_text_string = Export_text_string + '$$@@$$'
	Export_text_string = Export_text_string + Round_value_textBox

	# Кодируем выбирать ли таблички результата и фазировки
	Export_text_string = Export_text_string + '$$@@$$'
	if Require_tables_select_checkBox1 == True:
		Export_text_string = Export_text_string + 'True<<@@>>'
	else: 
		Export_text_string = Export_text_string + 'False<<@@>>'
	if Require_tables_select_checkBox2 == True:
		Export_text_string = Export_text_string + 'True'
	else: 
		Export_text_string = Export_text_string + 'False'

	# Кодируем способ расчёта квартир
	Export_text_string = Export_text_string + '$$@@$$'
	if flat_calculation_way_radioButton1 == True:
		Export_text_string = Export_text_string + 'True<<@@>>False'
	else:
		Export_text_string = Export_text_string + 'False<<@@>>True'

	# Кодируем запас пространства внутри НКУ
	Export_text_string = Export_text_string + '$$@@$$' + VolumeCapacityNKU_textBox + '<<@@>>' + str(trackBar_VolumeCapacityNKU)

	# Кодируем понижающий коэффициент на распределённые потери:
	Export_text_string = Export_text_string + '$$@@$$' + Distributed_Volt_Dropage_koefficient_textBox

	# Кодируем именование фаз
	if PhaseNaming_ABC_radioButton_Checked == True:
		Export_text_string = Export_text_string + '$$@@$$' + 'True<<@@>>False'
	else:
		Export_text_string = Export_text_string + '$$@@$$' + 'False<<@@>>True'

	# '$$@@$$True<<@@>>False$$@@$$\u041e\u0421\u0412\u0415\u0429\r\n\u0421\u0412\u0415\u0422$$@@$$10<<@@>>1$$@@$$True<<@@>>False<<@@>>False<<@@>>False$$@@$$2<<@@>>True$$@@$$1$$@@$$True<<@@>>True$$@@$$True<<@@>>False'
	return Export_text_string







# Функция импорта основных настроек
# На входе кодированная строка из внешнего файла
# На выходе список списков с данными для заполнения в Основном окне настроек
def Main_settings_Import (Import_text_string):
	# Надо разбить входную строку на подсписки. Их разделение взять по маркеру '$$@@$$'
	Vars_splites_lst = Import_text_string.split('$$@@$$')[1:] # ['True<<@@>>False', u'\u041e\u0421\u0412\u0415\u0429\r\n\u0421\u0412\u0415\u0422', '10<<@@>>1', 'True<<@@>>False<<@@>>False<<@@>>False', '2<<@@>>True', '1', 'True<<@@>>True', 'True<<@@>>False']
	# Теперь сделаем список списков где и элементы будут разделены по маркеру <<@@>>
	hlp_lst = [] # [['True', 'False'], [u'\u041e\u0421\u0412\u0415\u0429\r\n\u0421\u0412\u0415\u0422'], ['10', '1'], ['True', 'False', 'False', 'False'], ['2', 'True'], ['1'], ['True', 'True'], ['True', 'False']]
	for i in Vars_splites_lst:
		hlp_lst.append(i.split('<<@@>>')) 
	# А теперь переведём строчные 'True', 'False' в настоящие логические
	Exit_list = [] # [[True, False], [u'\u041e\u0421\u0412\u0415\u0429\r\n\u0421\u0412\u0415\u0422'], ['10', '1'], [True, False, False, False], ['2', True], ['1'], [True, True], [True, False]]
	for i in hlp_lst:
		curel = [] # текущий элемент подсписок
		for j in i:
			if j == 'True':
				curel.append(True)
			elif j == 'False':
				curel.append(False)
			else:
				curel.append(j)
		Exit_list.append(curel)

	return Exit_list









# Функция сбора и проверки на правильность информации из окна исходных данных для расчёта.
# используется перед сохранением или экспортом.
# Объявляет глобальные списки Currents_and_SectionsOutput, Current_breakersOutput, Cables_trays_reduction_factorOutput, CB_reduction_factorOutput, VoltageDrop_Coefficiets_KnorrOutput, VoltageOutput
# На выходе выдаёт значение notfloat и errorprovider_textstring если есть предупреждения
# Обращение: 
# Collect_data_from_CRF(self._CRF_Wires_dataGridView, self._CRF_CBnominal_dataGridView, self._CRF_Cables_reduction_factor_dataGridView, self._CRF_Circuit_breakers_reduction_factor_dataGridView, self._Cu_Al_Udrop_coeff_dataGridView, self._CRF_Voltage_textBox)
def Collect_data_from_CRF (CRF_Wires_dataGridView, CRF_CBnominal_dataGridView, CRF_Cables_reduction_factor_dataGridView, CRF_Circuit_breakers_reduction_factor_dataGridView, Cu_Al_Udrop_coeff_dataGridView, CRF_Voltage_textBox):

	# Забираем значения сеченией и токов. Нам нужен список с подсписками [[сечения], [токи медных многожильных кабелей], ...]. То есть будет так: [['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800', '1000'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030', '1143'], ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858', '972'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030', '1143']]
	global Currents_and_SectionsOutput
	Currents_and_SectionsOutput = []
	for i in range(CRF_Wires_dataGridView.Columns.Count):
		Currents_and_SectionsOutput.append([])
	for n, i in enumerate(Currents_and_SectionsOutput):
		for j in range(CRF_Wires_dataGridView.Rows.Count-1):
			i.append(CRF_Wires_dataGridView[n, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
	# Забираем значения уставок автоматов
	global Current_breakersOutput
	Current_breakersOutput = []
	for i in range(CRF_CBnominal_dataGridView.Rows.Count-1):
		Current_breakersOutput.append(CRF_CBnominal_dataGridView[0, i].Value)
	# Забираем значения понижающих коэффициентов совместной прокладки кабелей
	global Cables_trays_reduction_factorOutput
	Cables_trays_reduction_factorOutput = []
	for i in range(CRF_Cables_reduction_factor_dataGridView.Rows.Count-1):
		Cables_trays_reduction_factorOutput.append(CRF_Cables_reduction_factor_dataGridView[1, i].Value)
	# Забираем значения понижающих коэффициентов совместной установки аппаратов
	global CB_reduction_factorOutput
	CB_reduction_factorOutput = []
	for i in range(CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Count-1):
		CB_reduction_factorOutput.append(CRF_Circuit_breakers_reduction_factor_dataGridView[1, i].Value)
	# Забираем значения коэффициентов потерь Кнорринга
	global VoltageDrop_Coefficiets_KnorrOutput
	VoltageDrop_Coefficiets_KnorrOutput = []
	for i in range(Cu_Al_Udrop_coeff_dataGridView.Columns.Count):
		VoltageDrop_Coefficiets_KnorrOutput.append(Cu_Al_Udrop_coeff_dataGridView[i, 0].Value)
	# Забираем значения рабочих напряжений
	global VoltageOutput
	VoltageOutput = CRF_Voltage_textBox.Text.split('/') # список вида ['400', '230']


	# ______________________________Проверяем корректность введённых данных__________________________________________
	notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь ввёл не число, а что-то другое
	errorprovider_textstring = '' # Строка для вывода предупреждения в еррорпровайдер
	for i in Currents_and_SectionsOutput:
		for j in i:
			try:
				float(j)
			except SystemError:
				errorprovider_textstring = 'Табл. 1. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули'
				notfloat = notfloat + 1
			except ValueError:
				errorprovider_textstring = 'Табл. 1. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки'
				notfloat = notfloat + 1
	for i in Current_breakersOutput:
		try:
			int(i)
		except TypeError:
			errorprovider_textstring = 'Табл. 2. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули или удалять ненужные строки'
			notfloat = notfloat + 1
		except ValueError:
			errorprovider_textstring = 'Табл. 2. Введённые Вами значения должны быть\nцелыми числами'
			notfloat = notfloat + 1
	for i in Cables_trays_reduction_factorOutput:
		try:
			float(i)
		except SystemError:
			errorprovider_textstring = 'Табл. 3. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули или удалять ненужные строки'
			notfloat = notfloat + 1
		except ValueError:
			errorprovider_textstring = 'Табл. 3. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки'
			notfloat = notfloat + 1
	for i in CB_reduction_factorOutput:
		try:
			float(i)
		except SystemError:
			errorprovider_textstring = 'Табл. 4. Пустые ячейки в таблицах не допускаются.\nВместо пустых значений допускается писать нули или удалять ненужные строки'
			notfloat = notfloat + 1
		except ValueError:
			errorprovider_textstring = 'Табл. 4. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки'
			notfloat = notfloat + 1
	for i in VoltageDrop_Coefficiets_KnorrOutput:
		isok = True # вспомогательная переменная
		try:
			float(i)
		except SystemError:
			errorprovider_textstring = 'Табл. 5. Пустые ячейки и нулевые \nзначения в таблице 5 не допускаются'
			notfloat = notfloat + 1
			isok = False # вспомогательная переменная
		except ValueError:
			errorprovider_textstring = 'Табл. 5. Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки, либо целыми числами'
			notfloat = notfloat + 1
			isok = False # вспомогательная переменная
		if isok != False and float(i) == 0: 
			errorprovider_textstring = 'Табл. 5. Нулевые значения в таблице 5 не допускаются.'
			notfloat = notfloat + 1
	# Проверим все таблицы на удаление всех строк
	if CRF_Wires_dataGridView.Rows.Count <= 1 or CRF_CBnominal_dataGridView.Rows.Count <= 1 or CRF_Cables_reduction_factor_dataGridView.Rows.Count <= 1 or CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Count <= 1:
		errorprovider_textstring = 'Удаление всех строк из таблиц не допускается'
		notfloat = notfloat + 1
	# Проверим првильность введённого напряжения
	for i in VoltageOutput:
		try:
			float(i)
		except ValueError:
			errorprovider_textstring = 'Рабочие напряжения должны быть введены в формате: 380/220'
			notfloat = notfloat + 1

	return notfloat, errorprovider_textstring


# Функция по заполнению таблицы с текущим коэффициентом спроса в окошке коэффициентов спроса
# На входе данные таблицы и список с коэф.спроса
# На выходе заполненная таблица
# Обращение: Fill_curKc_Table(All_koeffs, selected_code, self._CurKc_dataGridView, self._CurKc_label, Kc_descriptions)
def Fill_curKc_Table (All_koeffs, selected_code, CurKc_dataGridView, CurKc_label, Kc_descriptions):
	# Ищем нужные данные и заполняем текущую таблицу:
	for i in All_koeffs:
		if i[0] == selected_code:
			if selected_code == 1001:
				#self._CurKc_dataGridView.AllowUserToAddRows = False
				CurKc_dataGridView.Columns.Add('Column1', 'Значение')
				CurKc_dataGridView.Rows.Add(i[1])
				CurKc_label.Text = Kc_descriptions[0][1]
				break
			elif selected_code == 1002:
				a = 0
				while a <= len(i[1]):
					#CurKc_dataGridView.Columns.Add('Column'+str(a), '')
					cur_column = System.Windows.Forms.DataGridViewTextBoxColumn() # Кодируем текущий столбец
					cur_column.Name = 'Column'+str(a)
					cur_column.HeaderText = ''
					cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
					CurKc_dataGridView.Columns.Add(cur_column)
					a = a + 1
				CurKc_dataGridView.Rows.Add('Количество квартир')
				CurKc_dataGridView.Rows.Add('Удельная Рр (кВт) на квартиру')
				a = 1
				while a <= len(i[1]):
					CurKc_dataGridView[a, 0].Value = i[1][a-1] # обращение "столбец", "строка"
					CurKc_dataGridView[a, 1].Value = i[2][a-1]
					a = a + 1
				CurKc_label.Text = Kc_descriptions[1][1]
				break
			elif selected_code == 1003:
				a = 0
				while a <= len(i[1]):
					cur_column = System.Windows.Forms.DataGridViewTextBoxColumn()
					cur_column.Name = 'Column'+str(a)
					cur_column.HeaderText = ''
					cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
					CurKc_dataGridView.Columns.Add(cur_column)
					a = a + 1
				CurKc_dataGridView.Rows.Add('Заявленная мощность (кВт)')
				CurKc_dataGridView.Rows.Add('Коэффициент спроса')
				a = 1
				while a <= len(i[1]):
					CurKc_dataGridView[a, 0].Value = i[1][a-1]
					CurKc_dataGridView[a, 1].Value = i[2][a-1]
					a = a + 1
				CurKc_label.Text = Kc_descriptions[2][1]
				break
			elif selected_code == 1004:
				a = 0
				while a <= len(i[1]):
					cur_column = System.Windows.Forms.DataGridViewTextBoxColumn()
					cur_column.Name = 'Column'+str(a)
					cur_column.HeaderText = ''
					cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
					CurKc_dataGridView.Columns.Add(cur_column)
					a = a + 1
				CurKc_dataGridView.Rows.Add('Количество квартир')
				CurKc_dataGridView.Rows.Add('Коэффициент одновременности Ко')
				a = 1
				while a <= len(i[1]):
					CurKc_dataGridView[a, 0].Value = i[1][a-1]
					CurKc_dataGridView[a, 1].Value = i[2][a-1]
					a = a + 1
				CurKc_label.Text = Kc_descriptions[3][1]
				break
			elif selected_code == 1005:
				CurKc_dataGridView.Columns.Add('Column1', 'Значение')
				CurKc_dataGridView.Rows.Add(i[1])
				CurKc_label.Text = Kc_descriptions[4][1]
				break
			elif selected_code == 1006:
				cur_column = System.Windows.Forms.DataGridViewTextBoxColumn()
				cur_column.Name = 'Column 1'
				cur_column.HeaderText = 'Число лифтовых установок'
				cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
				CurKc_dataGridView.Columns.Add(cur_column)
				cur_column = System.Windows.Forms.DataGridViewTextBoxColumn()
				cur_column.Name = 'Column 2'
				cur_column.HeaderText = 'Кс.л. до 12 этажей'
				cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
				CurKc_dataGridView.Columns.Add(cur_column)
				cur_column = System.Windows.Forms.DataGridViewTextBoxColumn()
				cur_column.Name = 'Column 3'
				cur_column.HeaderText = 'Кс.л. 12 и выше этажей'
				cur_column.SortMode = DataGridViewColumnSortMode.NotSortable
				CurKc_dataGridView.Columns.Add(cur_column)
				for j in map(list, zip(*[i[1],i[2],i[3]])): # транспонируем список
					CurKc_dataGridView.Rows.Add(j[0], j[1], j[2]) # добавляем ряды
				CurKc_label.Text = Kc_descriptions[5][1]
				break



# Функция забирает данные из таблицы текущих Кс, проверяет их корректность и обновляет список All_koeffs_Output
# Обращение:  TakeDataFrom_curKc_Table (All_koeffs_Output, selected_code, self._CurKc_dataGridView)
# На выходе обновлённый список All_koeffs_Output
def TakeDataFrom_curKc_Table (All_koeffs_Output, selected_code, CurKc_dataGridView):
	exept_float_string = 'Введённые вами данные должны быть числами с разделителем целой и дробной частей в виде точки'
	Koeff_cur_index = 0 # индекс элемента в в исходном/выходном списке который будем заменять
	for n, i in enumerate(All_koeffs_Output):
		if i[0] == selected_code:
			Koeff_cur_index = n
			break
	# Выясняем текущий код списков Кс и по нему составляем список вида одного из подсписков All_koeffs_Output
	# [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
	Koeff_cur = [] # подсписок который будет заменён в исходном/выходном списке
	exception_marker = 0 # маркер ошибки. 0 если всё прошло успешно, больше 0 если была ошибка
	if selected_code == 1001 or selected_code == 1005: # для таблиц с едиственным значением
		Koeff_cur.append(selected_code)
		try:
			float(CurKc_dataGridView.CurrentCell.Value) # проверка правильности текущей ячейки
			Koeff_cur.append(CurKc_dataGridView.CurrentCell.Value)
		except:
			TaskDialog.Show('Коэффициенты спроса', exept_float_string)
			CurKc_dataGridView.CurrentCell.Value = All_koeffs_Output[Koeff_cur_index][1] # возвращаем данные по умолчанию в случае ошибки
			exception_marker = exception_marker + 1
	elif selected_code == 1002 or selected_code == 1003 or selected_code == 1004: # для горизонтальных таблиц
		Koeff_cur.append(selected_code)
		# Если текущая ячйка не из 0-го столбца (там пояснения). Ещё есть .RowIndex
		if CurKc_dataGridView.CurrentCell.ColumnIndex != 0:
			try:
				float(CurKc_dataGridView.CurrentCell.Value)
				for i in range(CurKc_dataGridView.Rows.Count):
					cur_sublist = []
					for j in range(CurKc_dataGridView.Columns.Count):
						cur_sublist.append(CurKc_dataGridView[j, i].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
					cur_sublist.pop(0) # 0-й элемент это пояснение, его удаляем
					Koeff_cur.append(cur_sublist)
			except:
				TaskDialog.Show('Коэффициенты спроса', exept_float_string)
				CurKc_dataGridView.CurrentCell.Value = All_koeffs_Output[Koeff_cur_index][CurKc_dataGridView.CurrentCell.RowIndex][CurKc_dataGridView.CurrentCell.ColumnIndex + 1] # возвращаем данные по умолчанию в случае ошибки
				exception_marker = exception_marker + 1
		else:
			exception_marker = exception_marker + 1 # это если пользователь вообще ничего не делал. Тогда оставим всё как было.
	elif selected_code == 1006: # для вертикальных таблиц
		Koeff_cur.append(selected_code)
		try:
			float(CurKc_dataGridView.CurrentCell.Value)
			for i in range(CurKc_dataGridView.Columns.Count):
				cur_sublist = []
				for j in range(CurKc_dataGridView.Rows.Count):
					cur_sublist.append(CurKc_dataGridView[i, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
				Koeff_cur.append(cur_sublist)
		except:
			TaskDialog.Show('Коэффициенты спроса', exept_float_string)
			CurKc_dataGridView.CurrentCell.Value = All_koeffs_Output[Koeff_cur_index][CurKc_dataGridView.CurrentCell.RowIndex][CurKc_dataGridView.CurrentCell.ColumnIndex + 1] # возвращаем данные по умолчанию в случае ошибки
			exception_marker = exception_marker + 1

	# Если всё прошло без ошибок меняем текущий подсписок в исходном списке
	if exception_marker == 0:
		# Заменяем нужный элемент в исходном/выходном списке
		All_koeffs_Output[Koeff_cur_index] = Koeff_cur

	return All_koeffs_Output


# Функция очищает любую dataGridView от ВСЕХ столбцов и строк
# Обращение: dataGridView_Clear(self._KcList_dataGridView)
def dataGridView_Clear (dataGridViewObject):
	# Удаляем все строки и столбцы из таблицы
	a = dataGridViewObject.Rows.Count
	while a > 0:
		dataGridViewObject.Rows.RemoveAt(0)
		a = a - 1
	a = dataGridViewObject.Columns.Count
	while a > 0:
		dataGridViewObject.Columns.RemoveAt(0)
		a = a - 1




# Функция считывания данных о пользовательских Кс, Р и формулах из Хранилища. Да и вообще считывания чего угодно.
# Пример обращения: znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
def Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc):
	# Считываем данные о Кс из хранилища
	#Получаем Schema:
	schKc = Schema.Lookup(schemaGuid_for_UserKc)
	#Получаем Entity из элемента:
	entKc = ProjectInfoObject.GetEntity(schKc)
	#Уже знакомым способом получаем «поля»:
	fieldKc = schKc.GetField(FieldName_for_UserKc)
	#Для считывания значений используем метод Entity.Get:
	znachKc = entKc.Get[IList[str]](fieldKc) 

	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znachKc]
	znachKc = []
	[znachKc.append(i) for i in CS_help]
	# znachKc - Получили список со всеми Кс из хранилища: 'Введите имя таблицы!!Прочее!!Кс.сантех!!!!Зависит от уд.веса в других нагрузках!!Ру (вся)&&??&&Рр (вся)!!Резерв 1!!Резерв 2!!Резерв 3!!1&&??&&2&&??&&3!!Столбец 1. Удельный вес установленной мощности в других нагрузках (%)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)!!Количество электропримников: (заполните далее эту строку)&&??&&1&&??&&2>>3&&??&&4&&??&&5>>0&&??&&0&&??&&0', 'Арина таблица!!Прочее!!Кс.сантех!!!!Зависит от уд.веса в других нагрузках!!Ру (вся)&&??&&Рр (вся)!!Резерв 1!!Резерв 2!!Резерв 3!!1&&??&&2&&??&&3!!Столбец 1. Удельный вес установленной мощности в других нагрузках (%)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)!!Количество электропримников: (заполните далее эту строку)&&??&&1&&??&&2>>3&&??&&4&&??&&5>>0&&??&&0&&??&&0'	return znachKc
	return znachKc


			

#Kc_Storage_Form().ShowDialog()

#____________________________________________________________________________________________________






# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html
transGroup = TransactionGroup(doc, "TeslaSettings")
transGroup.Start()









#_________________________________ Работаем с основным ExtensibleStorage ____________________________________________________________________________
schemaGuid_for_Tesla_settings = System.Guid(Guidstr) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# получаем объект "информация о проекте"
ProjectInfoObject = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).WhereElementIsNotElementType().ToElements()[0] 



# функция записи в ExtensibleStorage
# на входе: Wrtite_to_ExtensibleStorage (schemaGuid_for_Tesla_settings, ProjectInfoObject, 'Tesla_settings_list', 'Tesla_settings_Storage', Tesla_settings_Storagelist)
# важен тип входных данных:________________as Guid________________________as Object___________as string_______________as string_______________as List[str]_____________
def Wrtite_to_ExtensibleStorage (schemaGuid, Object_for_write_down, SchFieldName, SchSchemaName, DataList):

	sb = SchemaBuilder (schemaGuid) # Построение будет выполняться через «промежуточный» класс SchemaBuilder. Создаем его, используя GUID
	sb.SetReadAccessLevel(AccessLevel.Public) # задаем уровень доступа
	fb1 = sb.AddArrayField(SchFieldName, str) # Далее создаем поля для хранилища, опять же через промежуточный класс FieldBuilder
	sb.SetSchemaName(SchSchemaName) # Задаем имя для хранилища
	sch = sb.Finish() # И «запекаем» SchemaBuilder, получая Schema

	# Из ранее созданной «Schema» получаем «поля», которые чуть позже используем для считывания значений из элемента. Потребуются имена, под которым мы их создавали:
	field1 = sch.GetField(SchFieldName)
	#Также создаем объект Entity, в который будем записывать значения полей:
	ent = Entity(sch)

	ent.Set[IList[str]](field1, DataList) # Создаёт список
	#Записываем Entity в элемент:
	t = Transaction(doc, 'Create storage')
	t.Start()
	Object_for_write_down.SetEntity(ent)
	t.Commit()


# Вот это и есть наш список настроек Тэслы. В своём значении по умолчанию. Список может содержать только строки.
# Структура такая: [ 'Имя переменной 1', 'Значение переменной 1', 'Имя переменной 2', 'Значение переменной 2',.....         ]
# Тогда мы сможем всегда легко обращаться к нужному нам значению переменной
Tesla_settings_Storagelist_by_Default = List[str]([Cable_section_calculation_method_for_Tesla_settings, '0', Volt_Dropage_key_for_Tesla_settings, 'ОСВЕЩ\r\nСВЕТ', Cable_stock_for_Tesla_settings, '10', Electrical_Circuit_PathMode_method_for_Tesla_settings, '3', DeltaU_boundary_value_for_Tesla_settings, '2', Round_value_for_Tesla_settings, '1', Require_tables_select_for_Tesla_settings, '0', Require_PHtables_select_for_Tesla_settings, '0', Select_Cable_by_DeltaU_for_Tesla_settings, '1', flat_calculation_way_for_Tesla_settings, '0', Distributed_Volt_Dropage_koefficient_for_Tesla_settings, '0.5', PhaseNaming_for_Tesla_settings, '0'])


# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch = Schema.Lookup(schemaGuid_for_Tesla_settings)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if sch is None or ProjectInfoObject.GetEntity(sch).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки', 'Настройки программы не найдены или были повреждены.\n Будут созданы настройки по умолчанию.')
	# Пишем настройки Тэслы
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Tesla_settings, ProjectInfoObject, FieldName_for_Tesla_settings, SchemaName_for_Tesla_settings, Tesla_settings_Storagelist_by_Default) # пишем данные в хранилище 
	

# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch = Schema.Lookup(schemaGuid_for_Tesla_settings)
#Получаем Entity из элемента:
ent = ProjectInfoObject.GetEntity(sch)
#Уже знакомым способом получаем «поля»:
field1 = sch.GetField(FieldName_for_Tesla_settings)
#Для считывания значений используем метод Entity.Get:
znach = ent.Get[IList[str]](field1) # выдаёт List[str](['a', 'list', 'of', 'strings'])

# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach]
znach = []
[znach.append(i) for i in CS_help]


# Кроме того при добавлении новых настроек длина списка Tesla_settings_Storagelist увеличивается. Нужно принудительно записывать новые настройки в хранилище в этом случае.
if len(znach) < 24: # Вот эту цифру и будем менять здесь в коде при добавлении новых настроек Тэслы
	TaskDialog.Show('Настройки', 'С выходом новой версии программы добавились новые настройки.\nОбратите внимание на новые возможности!')
	try:
		Tesla_settings_Storagelist = List[str]([Cable_section_calculation_method_for_Tesla_settings, znach[1], Volt_Dropage_key_for_Tesla_settings, znach[3], Cable_stock_for_Tesla_settings, znach[5], Electrical_Circuit_PathMode_method_for_Tesla_settings, znach[7], DeltaU_boundary_value_for_Tesla_settings, '2', Round_value_for_Tesla_settings, '1', Require_tables_select_for_Tesla_settings, '0', Require_PHtables_select_for_Tesla_settings, '0', Select_Cable_by_DeltaU_for_Tesla_settings, '1', flat_calculation_way_for_Tesla_settings, '0', Distributed_Volt_Dropage_koefficient_for_Tesla_settings, '0.5', PhaseNaming_for_Tesla_settings, '0'])
	except IndexError:
		Tesla_settings_Storagelist = [i for i in Tesla_settings_Storagelist_by_Default]
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Tesla_settings, ProjectInfoObject, FieldName_for_Tesla_settings, SchemaName_for_Tesla_settings, Tesla_settings_Storagelist) # пишем данные в хранилище 
	# и ещё раз считываем значения настроек
	sch = Schema.Lookup(schemaGuid_for_Tesla_settings)
	ent = ProjectInfoObject.GetEntity(sch)
	field1 = sch.GetField(FieldName_for_Tesla_settings)
	znach = ent.Get[IList[str]](field1)
	CS_help = []
	[CS_help.append(i) for i in znach]
	znach = []
	[znach.append(i) for i in CS_help]



# Присваиваем значения переменным в соответствии с информацией полученной из хранилища
Cable_section_calculation_method = int(znach[int(znach.index(Cable_section_calculation_method_for_Tesla_settings) + 1)]) # поясняю: находим значение самой переменной на следующей (+1) позиции за именем самой переменной в списке из хранилища
Volt_Dropage_key = znach[int(znach.index(Volt_Dropage_key_for_Tesla_settings) + 1)]
Cable_stock_for_circuitry = znach[int(znach.index(Cable_stock_for_Tesla_settings) + 1)]
Electrical_Circuit_PathMode_method = int(znach[int(znach.index(Electrical_Circuit_PathMode_method_for_Tesla_settings) + 1)])
deltaU_boundary_value = znach[int(znach.index(DeltaU_boundary_value_for_Tesla_settings) + 1)]
Round_value_ts = znach[int(znach.index(Round_value_for_Tesla_settings) + 1)]
Require_tables_select_ts = znach[int(znach.index(Require_tables_select_for_Tesla_settings) + 1)]
Require_PHtables_select_ts = znach[int(znach.index(Require_PHtables_select_for_Tesla_settings) + 1)]
Select_Cable_by_DeltaU_ts = znach[int(znach.index(Select_Cable_by_DeltaU_for_Tesla_settings) + 1)]
flat_calculation_way_ts = znach[int(znach.index(flat_calculation_way_for_Tesla_settings) + 1)]
Distributed_Volt_Dropage_koefficient = znach[int(znach.index(Distributed_Volt_Dropage_koefficient_for_Tesla_settings) + 1)]
PhaseNaming = znach[int(znach.index(PhaseNaming_for_Tesla_settings) + 1)]

global Button_Cancel_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_pushed = 1






















# ________________Модуль диалогового окна распределённых потерь по группам_____________________________________________________________________________________
#_______________________________________________________________________________________________________________________________________________________________

elems_avtomats = [] # все автоматы (типовые аннотации) со всей модели

for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_GenericAnnotation).WhereElementIsNotElementType().ToElements():
	if avt_family_names.count(i.Name) > 0: elems_avtomats.append(i) 

Group_names = [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats] # имена всех групп автоматов (типовых аннотаций)
Electric_receiver_Names = [element.LookupParameter(Param_Electric_receiver_Name).AsString() for element in elems_avtomats] # все наименования электроприёмников

# Отсортируем списки по алфавиту и возрастанию
GroupsAndRecievers_names = list(zip(Group_names, Electric_receiver_Names))
GroupsAndRecievers_names.sort() # список вида: [(u'1РП.ППУ-1', u'ав. освещение эл.щитовой и СС'), (u'1РП.ППУ-10', u'ав. освещение площадки лестницы'), ... ]


# Guid для этого хранилища
schemaGuid_for_Distributed_volt_dropage_Tesla_settings = System.Guid(Guidstr_Distributed_volt_dropage_Tesla_settings)

#Получаем Schema:
schDeltaU = Schema.Lookup(schemaGuid_for_Distributed_volt_dropage_Tesla_settings)


# А это список с информацией по значениям распределённых потерь
# Его структура такая: 
# ['Номер цепи1?!?Наименование электроприёмника1?!?Заданные потери1', 'Номер цепи2?!?Наименование электроприёмника2?!?Заданные потери2', ...], например ['1РП1-1?!?освещение эл.щитовой и СС?!?0', ]
# где ?!? это разделитель элементов подсписков. Он нужен т.к. в ExtensibleStorage нельзя хранить списки с подсписками
# Причём "Заданные потери" храняться в виде 0 если мы не считаем распределённые потери, и в виде числа (например 1.53) если считаем.
hlplist = []
for i in GroupsAndRecievers_names:
	hlplist.append(i[0]+'?!?'+i[1]+'?!?'+'0')
Tesla_settings_Distributed_volt_dropage_list_by_Default = List[str](hlplist)

# Проверяем корректность хранилища
if schDeltaU is None or ProjectInfoObject.GetEntity(schDeltaU).IsValid() == False:
	TaskDialog.Show('Настройки', 'Данные о значениях распределённых потерь не были найдены.\n Будут созданы данные по умолчанию.')
	# Пишем инфу о распределённых потерях
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Distributed_volt_dropage_Tesla_settings, ProjectInfoObject, FieldName_for_Distributed_volt_dropage_Tesla_settings, SchemaName_for_Distributed_volt_dropage_Tesla_settings, Tesla_settings_Distributed_volt_dropage_list_by_Default) # пишем данные в хранилище 


# Считываем данные о значениях распределённых потерь из Хранилища
#Получаем Schema:
sch1 = Schema.Lookup(schemaGuid_for_Distributed_volt_dropage_Tesla_settings)
#Получаем Entity из элемента:
ent1 = ProjectInfoObject.GetEntity(sch1)
#Уже знакомым способом получаем «поля»:
field2 = sch1.GetField(FieldName_for_Distributed_volt_dropage_Tesla_settings)
#Для считывания значений используем метод Entity.Get:
znach1 = ent1.Get[IList[str]](field2) 

# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach1]
znach1 = []
[znach1.append(i) for i in CS_help]

# приведём этот список в приличный вид: список с подсписками без всяких разделителей. 
# В нём в каждом подсписке уже нормально присутствуют [['Номер цепи1', 'Наименование электроприёмника1', 'Заданные потери1'], , ...]
znach1hlp = []
for i in znach1:
	znach1hlp.append([i.partition('?!?')[0], i.partition('?!?')[2].partition('?!?')[0], i.partition('?!?')[2].partition('?!?')[2]])

# Теперь нужно сравнить список групп и наименований электроприёмников из модели со списком из Хранилища.
# Логика такая: если в модели больше групп чем в хранилище - добавть их для окна
# если в модели меньше групп чем в хранилище - убрать их для окна
# если в хранилище есть группы которых нет в модели - убрать их из окна
GroupsAndNamesForWindowInput = [] # список с группами для вывода в окно

GroupsAndRecievers_names_copy = [] # копия списка
for i in GroupsAndRecievers_names:
	GroupsAndRecievers_names_copy.append(i)

for i in GroupsAndRecievers_names:
	for j in znach1hlp:
		if [i[0], i[1]] == [j[0], j[1]]: # если группа есть и в хранилище и в модели...
			if j[2] == '0': # если не считаем распределённые потери
				GroupsAndNamesForWindowInput.append([j[0], j[1], '']) # добавляем группу в выходной список
			else: # если считаем распределённые потери
				GroupsAndNamesForWindowInput.append([j[0], j[1], j[2]])
			cur_indx = Get_coincidence_in_list (j, znach1hlp) # получаем индексы совпавших элементов
			Delete_indexed_elements_in_list (cur_indx, znach1hlp) # удаляем совпавшие элементы из списка
			cur_indx = Get_coincidence_in_list (i, GroupsAndRecievers_names_copy)
			Delete_indexed_elements_in_list (cur_indx, GroupsAndRecievers_names_copy)


#ara = 'пусто тут'

# Если в модели остались группы которых нет в Хранилище
if len(GroupsAndRecievers_names_copy) > 0:
	for i in GroupsAndRecievers_names_copy:
		GroupsAndNamesForWindowInput.append([i[0], i[1], ''])
		#ara = ara + i[0] + i[1] + ''

#MessageBox.Show(ara, "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Information)		

global Button_Cancel_DeltaUByGroups_Form_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_DeltaUByGroups_Form_pushed = 1


'''
ara = znach1[0]
ara.partition('?!?')
i.partition('?!?')[0]
i = GroupsAndRecievers_names[0]
j = znach1hlp[0]
[i[0], i[1]]
[j[0], j[1]]
Забирает значение из ячейки
		#global ara
		#ara = self._DeltaUByGroupsForm_dataGridView[1, 1].Value
'''




class DeltaUByGroups_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		#resources = System.Resources.ResourceManager("DeltaUByGroups_Form", System.Reflection.Assembly.GetEntryAssembly())
		self._OK_DeltaUByGroupsForm_button = System.Windows.Forms.Button()
		self._Cancel_DeltaUByGroupsForm_button = System.Windows.Forms.Button()
		self._DeltaUByGroupsForm_dataGridView = System.Windows.Forms.DataGridView()
		self._Du_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Du_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Du_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Clear_DeltaUByGroupsForm_button = System.Windows.Forms.Button()
		self._DeltaUByGroupsForm_label1 = System.Windows.Forms.Label()
		self._DeltaUByGroupsForm_dataGridView.BeginInit()
		self.SuspendLayout()
		# 
		# OK_DeltaUByGroupsForm_button
		# 
		self._OK_DeltaUByGroupsForm_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_DeltaUByGroupsForm_button.Location = System.Drawing.Point(12, 448)
		self._OK_DeltaUByGroupsForm_button.Name = "OK_DeltaUByGroupsForm_button"
		self._OK_DeltaUByGroupsForm_button.Size = System.Drawing.Size(128, 23)
		self._OK_DeltaUByGroupsForm_button.TabIndex = 0
		self._OK_DeltaUByGroupsForm_button.Text = "Сохранить и закрыть"
		self._OK_DeltaUByGroupsForm_button.UseVisualStyleBackColor = True
		self._OK_DeltaUByGroupsForm_button.Click += self.OK_DeltaUByGroupsForm_buttonClick
		# 
		# Cancel_DeltaUByGroupsForm_button
		# 
		self._Cancel_DeltaUByGroupsForm_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_DeltaUByGroupsForm_button.Location = System.Drawing.Point(585, 448)
		self._Cancel_DeltaUByGroupsForm_button.Name = "Cancel_DeltaUByGroupsForm_button"
		self._Cancel_DeltaUByGroupsForm_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_DeltaUByGroupsForm_button.TabIndex = 1
		self._Cancel_DeltaUByGroupsForm_button.Text = "Cancel"
		self._Cancel_DeltaUByGroupsForm_button.UseVisualStyleBackColor = True
		self._Cancel_DeltaUByGroupsForm_button.Click += self.Cancel_DeltaUByGroupsForm_buttonClick
		# 
		# DeltaUByGroupsForm_dataGridView
		# 
		self._DeltaUByGroupsForm_dataGridView.AllowUserToAddRows = False
		self._DeltaUByGroupsForm_dataGridView.AllowUserToDeleteRows = False
		self._DeltaUByGroupsForm_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._DeltaUByGroupsForm_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._DeltaUByGroupsForm_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._Du_Column1,
			self._Du_Column2,
			self._Du_Column3]))
		self._DeltaUByGroupsForm_dataGridView.Location = System.Drawing.Point(12, 63)
		self._DeltaUByGroupsForm_dataGridView.Name = "DeltaUByGroupsForm_dataGridView"
		self._DeltaUByGroupsForm_dataGridView.Size = System.Drawing.Size(648, 368)
		self._DeltaUByGroupsForm_dataGridView.TabIndex = 2
		self._DeltaUByGroupsForm_dataGridView.CellContentClick += self.DeltaUByGroupsForm_dataGridViewCellContentClick
		# 
		# Du_Column1
		# 
		self._Du_Column1.HeaderText = "Номер цепи"
		self._Du_Column1.Name = "Du_Column1"
		self._Du_Column1.ReadOnly = True
		# 
		# Du_Column2
		# 
		self._Du_Column2.HeaderText = "Наименование электроприёмника"
		self._Du_Column2.Name = "Du_Column2"
		self._Du_Column2.ReadOnly = True
		self._Du_Column2.Width = 390
		# 
		# Du_Column3
		# 
		self._Du_Column3.HeaderText = "Заданные потери"
		self._Du_Column3.Name = "Du_Column3"
		# 
		# Clear_DeltaUByGroupsForm_button
		# 
		self._Clear_DeltaUByGroupsForm_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Clear_DeltaUByGroupsForm_button.Location = System.Drawing.Point(269, 448)
		self._Clear_DeltaUByGroupsForm_button.Name = "Clear_DeltaUByGroupsForm_button"
		self._Clear_DeltaUByGroupsForm_button.Size = System.Drawing.Size(129, 23)
		self._Clear_DeltaUByGroupsForm_button.TabIndex = 3
		self._Clear_DeltaUByGroupsForm_button.Text = "Очистить все потери"
		self._Clear_DeltaUByGroupsForm_button.UseVisualStyleBackColor = True
		self._Clear_DeltaUByGroupsForm_button.Click += self.Clear_DeltaUByGroupsForm_buttonClick
		# 
		# DeltaUByGroupsForm_label1
		# 
		self._DeltaUByGroupsForm_label1.Location = System.Drawing.Point(12, 9)
		self._DeltaUByGroupsForm_label1.Name = "DeltaUByGroupsForm_label1"
		self._DeltaUByGroupsForm_label1.Size = System.Drawing.Size(648, 42)
		self._DeltaUByGroupsForm_label1.TabIndex = 4
		self._DeltaUByGroupsForm_label1.Text = 'В данной таблице содержатся все группы присутствующие на схемах в модели. Введите значения конкретных потерь в столбец "Заданные потери". Эти значения сохранятся для групп с указанным номером цепи и наименованием электроприёмника. Они не будут пересчитаны при расчётах схем.'
		# 
		# DeltaUByGroups_Form
		# 
		self.ClientSize = System.Drawing.Size(678, 483)
		self.Controls.Add(self._DeltaUByGroupsForm_label1)
		self.Controls.Add(self._Clear_DeltaUByGroupsForm_button)
		self.Controls.Add(self._DeltaUByGroupsForm_dataGridView)
		self.Controls.Add(self._Cancel_DeltaUByGroupsForm_button)
		self.Controls.Add(self._OK_DeltaUByGroupsForm_button)
		self.Name = "DeltaUByGroups_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Потери по группам"
		self.Load += self.DeltaUByGroups_FormLoad
		self._DeltaUByGroupsForm_dataGridView.EndInit()
		self.ResumeLayout(False)


		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def OK_DeltaUByGroupsForm_buttonClick(self, sender, e):
		# Забираем значения
		global GroupsAndNamesForWindowOutput
		GroupsAndNamesForWindowOutput = []
		notfloat = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь ввёл не число, а что-то другое
		a = 0
		while a < self._DeltaUByGroupsForm_dataGridView.Rows.Count:
			Duhlp = self._DeltaUByGroupsForm_dataGridView[2, a].Value # вспомогательная переменная. Значение распределённых потерь
			if Duhlp == None:
				Duhlp = ''
			try:
				if Duhlp != '':
					float(Duhlp) # если введённое значение распределённых потерь не может быть преобразовано в число
			except ValueError:
				#self._errorProvider1.SetError(self._OK_DeltaUByGroupsForm_button, 'Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки')
				MessageBox.Show('Введённые Вами значения должны быть\nчислами с разделителем целой и дробной\nчастей в виде точки', "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Information)
				notfloat = notfloat + 1
			if notfloat == 0 and Duhlp != '':
				if float(Duhlp) < 0 or float(Duhlp) > 5: # проверяем что значение от 0 до 5 включительно
					#self._errorProvider1.SetError(self._OK_DeltaUByGroupsForm_button, 'Значения потерь должны быть от 0 до 5 %')
					MessageBox.Show('Значения потерь должны быть от 0 до 5 %', "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Information)
					notfloat = notfloat + 1
			GroupsAndNamesForWindowOutput.append([self._DeltaUByGroupsForm_dataGridView[0, a].Value, self._DeltaUByGroupsForm_dataGridView[1, a].Value, Duhlp]) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
			a = a + 1

		if notfloat == 0:
			# Выставляем "кнопка отмена не нажата"
			global Button_Cancel_DeltaUByGroups_Form_pushed
			Button_Cancel_DeltaUByGroups_Form_pushed = 0
			self.Close()

	def Cancel_DeltaUByGroupsForm_buttonClick(self, sender, e):
		self.Close()

	def DeltaUByGroupsForm_dataGridViewCellContentClick(self, sender, e):
		pass

	def DeltaUByGroups_FormLoad(self, sender, e):
		for i in GroupsAndNamesForWindowInput:
			self._DeltaUByGroupsForm_dataGridView.Rows.Add(i[0], i[1], i[2]) # Заполняем таблицу исходными данными

	def Clear_DeltaUByGroupsForm_buttonClick(self, sender, e): # Стираем все конкретные значения потерь
		a = 0
		while a < self._DeltaUByGroupsForm_dataGridView.Rows.Count:
			self._DeltaUByGroupsForm_dataGridView[2, a].Value = None
			a = a + 1


#DeltaUByGroups_Form().ShowDialog()




















#_____________________МОДУЛЬ ПО РАБОТЕ С ОКОШКОМ Calculation Resourses (CR)_____________________________________________________________________________________
#_______________________________________________________________________________________________________________________________________________________________


#_____________________ Значения списков исходных данных по умолчанию_______________________________________________________________________________________
# Список токов для сечений медных и алюминиевых многожильных кабелей по ГОСТ Р 50571.5.52-2011 табл. В52.10 столбец 3 и ГОСТ Р 53769-2010 табл. 19, 21 (для больших сечений):    (если нужно, сюда можно добавлять вручную ещё токи для следующих сечений)
Currents_for_multiwire_copper_cables_DB = [19, 25, 34, 43, 60, 80, 101, 126, 153, 196, 238, 276, 319, 364, 430, 497, 633, 749, 855, 1030, 1143]
Currents_for_multiwire_aluminium_cables_DB = [0, 19.5, 26, 33, 46, 61, 78, 96, 117, 150, 183, 212, 245, 280, 330, 381, 501, 610, 711, 858, 972] # Для сечения 1,5 кв.мм у Al кабелей стоит допустимый ток 0 потому что не бывает Al кабелей с сечением 1,5 кв.мм. Но чтобы списки были одинаковой длины, пришлось написать 0. Программа всегда будет подбирать Al сечения начиная с 2,5 кв.мм, считая, что 1,5 кв.мм никогда не проходит по току. 
Currents_for_1phase_multiwire_copper_cables_DB = [22, 30, 40, 51, 70, 94, 119, 148, 180, 232, 282, 328, 379, 434, 514, 593, 0, 0, 0, 0, 0]
Currents_for_1phase_multiwire_aluminium_cables_DB = [0, 23, 31, 39, 54, 73, 89, 111, 135, 173, 210, 244, 282, 322, 380, 439, 0, 0, 0, 0, 0]
# Список токов для сечений медных и алюминиевых одножильных кабелей по ГОСТ Р 50571.5.52-2011 табл. В52.10 столбец 5 и ГОСТ Р 53769-2010 табл. 19, 21 (для больших сечений):    (если нужно, сюда можно добавлять вручную ещё токи для следующих сечений)
Currents_for_singlewire_copper_cables_DB = [19, 25, 34, 43, 60, 80, 110, 137, 167, 216, 264, 308, 356, 409, 485, 561, 656, 749, 855, 1030, 1143]
Currents_for_singlewire_aluminium_cables_DB = [0, 19.5, 26, 33, 46, 61, 84, 105, 128, 166, 203, 237, 274, 315, 375, 434, 526, 610, 711, 858, 972] 
# Список самих сечений в полном соответствии со списком токов для этих сечений:		(если нужно, сюда можно добавлять вручную ещё сечения)
Sections_of_cables_DB = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630, 800, 1000]
# Список уставок автоматических выключателей:		(если нужно, сюда можно добавлять вручную ещё номиналы)
Current_breaker_nominal_DB = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 700, 800, 900, 1000]
# Список понижающих коэффициентов для кабелей по ГОСТ 50571.5.52-2011 табл. В.52.20
# понижающие коэффициенты приведены от 1 до 9 кабелей проложенных совместно на лотках (два перфорированных лотка друг под другом). Поэтому в списке 9 членов.
Cables_trays_reduction_factor_DB = [1.0, 0.87, 0.8, 0.77, 0.75, 0.73, 0.71, 0.7, 0.68]
# Список понижающих коэффициентов для автоматов по ГОСТ 32397-2013 табл. В.1 (коэффициенты одновременности)
# 0-й элемент: 1 автомат; 1-й: 2авт; 2-й: 3 авт. и т.д. до 10 автоматов
Circuit_breakers_reduction_factor_DB = [1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5]
# Коэффициенты для расчёта потерь в медных и алюминиевых проводниках (из Кнорринга, табл. 12-9 стр. 348 и стр. 356)
Cmed3f = 72
Cmed1f = 12
Cal3f = 44
Cal1f = 7.4
# Напряжения с которыми работает программа (В):
U3f = 380
U1f = 220

# Список удельных сопротивлений кабелей 
# https://rusenergetics.ru/polezno-znat/soprotivlenie-mednogo-provoda-tablitsa
# https://raschet.info/spravochnye-tablicy-soprotivlenij-elementov-seti-0-4-kv/
# Данные по умолчанию взяты из картинки в папке "О токах КЗ".
# Активные удельные сопротивления медных кабелей (мОм/м)
Resistance_Active_Specific_for_copper_cables_DB = [13.35, 8.0, 5.0, 3.33, 2.0, 1.25, 0.8, 0.57, 0.4, 0.29, 0.21, 0.17, 0.13, 0.11, 0.08, 0.07, 0, 0, 0, 0, 0]
# Активные удельные сопротивления алюминиевых кабелей (мОм/м)
Resistance_Active_Specific_for_aluminium_cables_DB = [22.2, 13.3, 8.35, 5.55, 3.33, 2.08, 1.33, 0.95, 0.67, 0.48, 0.35, 0.28, 0.22, 0.18, 0.15, 0.12, 0, 0, 0, 0, ]
# Индуктивные удельные сопротивления медных и алюминиевых кабелей проложенных в трубах (мОм/м)
Resistance_Inductive_Specific_for_all_cables_DB = [0.11, 0.09, 0.1, 0.09, 0.07, 0.07, 0.07, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0, 0, 0, 0, 0]




# Формируем списки значений по умолчанию
Currents_and_Sections_Default = list(zip([str(i) for i in Sections_of_cables_DB],
[str(i) for i in Currents_for_1phase_multiwire_copper_cables_DB], 
[str(i) for i in Currents_for_multiwire_copper_cables_DB],
[str(i) for i in Currents_for_singlewire_copper_cables_DB],
[str(i) for i in Currents_for_1phase_multiwire_aluminium_cables_DB],
[str(i) for i in Currents_for_multiwire_aluminium_cables_DB],
[str(i) for i in Currents_for_singlewire_aluminium_cables_DB],
[str(i) for i in Resistance_Active_Specific_for_copper_cables_DB],
[str(i) for i in Resistance_Active_Specific_for_aluminium_cables_DB],
[str(i) for i in Resistance_Inductive_Specific_for_all_cables_DB]
))

Current_breakers_Default = [str(i) for i in Current_breaker_nominal_DB]

Cables_trays_reduction_factor_Default = [str(i) for i in Cables_trays_reduction_factor_DB]

CB_reduction_factor_Default = [str(i) for i in Circuit_breakers_reduction_factor_DB]

VoltageDrop_Coefficiets_Knorr_Default = [Cmed3f, Cmed1f, Cal3f, Cal1f]

Voltage_Default = [U3f, U1f]

#_______________________________________________________________________________________________________________________________________________






schemaGuid_for_CR = System.Guid(Guidstr_CR) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
schCR = Schema.Lookup(schemaGuid_for_CR)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if schCR is None or ProjectInfoObject.GetEntity(schCR).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки', 'Исходные данные для расчётов не найдены или были повреждены.\n Будут созданы данные по умолчанию.')
	# Пишем данные по умолчанию в Хранилище
	Write_several_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject, SchemaName_for_CR, 
	FieldName_for_CR_1, [str(i) for i in Sections_of_cables_DB], 
	FieldName_for_CR_2, [str(i) for i in Currents_for_multiwire_copper_cables_DB],
	FieldName_for_CR_3, [str(i) for i in Currents_for_multiwire_aluminium_cables_DB], 
	FieldName_for_CR_4, [str(i) for i in Currents_for_singlewire_copper_cables_DB],
	FieldName_for_CR_5, [str(i) for i in Currents_for_singlewire_aluminium_cables_DB],
	FieldName_for_CR_6, [str(i) for i in Current_breaker_nominal_DB],
	FieldName_for_CR_7, [str(i) for i in Cables_trays_reduction_factor_DB],
	FieldName_for_CR_8, [str(i) for i in Circuit_breakers_reduction_factor_DB],
	FieldName_for_CR_9, [str(i) for i in VoltageDrop_Coefficiets_Knorr_Default],
	FieldName_for_CR_10, [str(i) for i in Currents_for_1phase_multiwire_copper_cables_DB],
	FieldName_for_CR_11, [str(i) for i in Currents_for_1phase_multiwire_aluminium_cables_DB],
	FieldName_for_CR_12, [str(i) for i in Voltage_Default],
	FieldName_for_CR_13, [str(i) for i in Resistance_Active_Specific_for_copper_cables_DB],
	FieldName_for_CR_14, [str(i) for i in Resistance_Active_Specific_for_aluminium_cables_DB],
	FieldName_for_CR_15, [str(i) for i in Resistance_Inductive_Specific_for_all_cables_DB]
	)

# Считываем данные из Хранилища
CRF_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject)





# CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)] # выдаёт список с сечениями кабелей

# Формируем списки для заполнения Формы
Currents_and_Sections_from_ES = list(zip(CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)], 
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_10) + 1)], # поясню: это обращение к содержимому списка по имени поля в хранилище
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_2) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_4) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_11) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_3) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_5) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_13) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_14) + 1)],
CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_15) + 1)]
))

Current_breakers_from_ES = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_6) + 1)]

Cables_trays_reduction_factor_from_ES = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_7) + 1)]

CB_reduction_factor_from_ES = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_8) + 1)]

VoltageDrop_Coefficiets_Knorr_ES = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_9) + 1)]

Voltage_ES = CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_12) + 1)]



global Button_Cancel_CRF_Form_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_CRF_Form_pushed = 1



# Стирает ExtensibleStorage ЦЕЛИКОМ и полностью! Но только если открыт один единственный документ и в нём выгружены все внешние ссылки.
'''
sch = Schema.Lookup(schemaGuid_for_CR)
t = Transaction(doc, 'Erase storage')
t.Start()
sch.EraseSchemaAndAllEntities(sch, False)
t.Commit()
'''



# _______________Окошко исходных данных для расчётов_______________________________________________________


class CalculationResoursesForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._CRF_OK_button = System.Windows.Forms.Button()
		self._CRF_Cancel_button = System.Windows.Forms.Button()
		self._CRF_Wires_dataGridView = System.Windows.Forms.DataGridView()
		self._CRF_label1 = System.Windows.Forms.Label()
		self._CRF_return_default_table1_button = System.Windows.Forms.Button()
		self._CRF_CBnominal_dataGridView = System.Windows.Forms.DataGridView()
		self._CRF_label2 = System.Windows.Forms.Label()
		self._CRF_return_default_table2_button = System.Windows.Forms.Button()
		self._CRF_CBnominal_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Cables_reduction_factor_dataGridView = System.Windows.Forms.DataGridView()
		self._CRF_label3 = System.Windows.Forms.Label()
		self._CRF_Cables_reduction_factor_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Cables_reduction_factor_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_return_default_table3_button = System.Windows.Forms.Button()
		self._CRF_Circuit_breakers_reduction_factor_dataGridView = System.Windows.Forms.DataGridView()
		self._CRF_Circuit_breakers_reduction_factor_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Circuit_breakers_reduction_factor_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_return_default_table4_button = System.Windows.Forms.Button()
		self._CRF_label4 = System.Windows.Forms.Label()
		self._Cu_Al_Udrop_coeff_dataGridView = System.Windows.Forms.DataGridView()
		self._Cu_Al_Udrop_coeff_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Cu_Al_Udrop_coeff_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Cu_Al_Udrop_coeff_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Cu_Al_Udrop_coeff_Column4 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_label5 = System.Windows.Forms.Label()
		self._CRF_return_default_table5_button = System.Windows.Forms.Button()
		self._CRF_label6 = System.Windows.Forms.Label()
		self._CRF_Voltage_textBox = System.Windows.Forms.TextBox()
		self._CRF_CtrlV_table1_button = System.Windows.Forms.Button()
		self._CRF_Wires_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column6 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column7 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column4 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column5 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column8 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column9 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Wires_Column10 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._CRF_Import_button = System.Windows.Forms.Button()
		self._CRF_Export_button = System.Windows.Forms.Button()
		self._CRF_Wires_dataGridView.BeginInit()
		self._CRF_CBnominal_dataGridView.BeginInit()
		self._CRF_Cables_reduction_factor_dataGridView.BeginInit()
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.BeginInit()
		self._Cu_Al_Udrop_coeff_dataGridView.BeginInit()
		self.SuspendLayout()
		# 
		# CRF_OK_button
		# 
		self._CRF_OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._CRF_OK_button.Location = System.Drawing.Point(22, 627)
		self._CRF_OK_button.Name = "CRF_OK_button"
		self._CRF_OK_button.Size = System.Drawing.Size(128, 23)
		self._CRF_OK_button.TabIndex = 0
		self._CRF_OK_button.Text = "Сохранить и закрыть"
		self._CRF_OK_button.UseVisualStyleBackColor = True
		self._CRF_OK_button.Click += self.CRF_OK_buttonClick
		# 
		# CRF_Cancel_button
		# 
		self._CRF_Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_Cancel_button.Location = System.Drawing.Point(1366, 627)
		self._CRF_Cancel_button.Name = "CRF_Cancel_button"
		self._CRF_Cancel_button.Size = System.Drawing.Size(75, 23)
		self._CRF_Cancel_button.TabIndex = 1
		self._CRF_Cancel_button.Text = "Cancel"
		self._CRF_Cancel_button.UseVisualStyleBackColor = True
		self._CRF_Cancel_button.Click += self.CRF_Cancel_buttonClick
		# 
		# CRF_Wires_dataGridView
		# 
		self._CRF_Wires_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._CRF_Wires_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._CRF_Wires_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._CRF_Wires_Column1,
			self._CRF_Wires_Column6,
			self._CRF_Wires_Column2,
			self._CRF_Wires_Column3,
			self._CRF_Wires_Column7,
			self._CRF_Wires_Column4,
			self._CRF_Wires_Column5,
			self._CRF_Wires_Column8,
			self._CRF_Wires_Column9,
			self._CRF_Wires_Column10]))
		self._CRF_Wires_dataGridView.Location = System.Drawing.Point(22, 72)
		self._CRF_Wires_dataGridView.Name = "CRF_Wires_dataGridView"
		self._CRF_Wires_dataGridView.RowTemplate.Height = 24
		self._CRF_Wires_dataGridView.Size = System.Drawing.Size(755, 393)
		self._CRF_Wires_dataGridView.TabIndex = 2
		# 
		# CRF_label1
		# 
		self._CRF_label1.Location = System.Drawing.Point(22, 21)
		self._CRF_label1.Name = "CRF_label1"
		self._CRF_label1.Size = System.Drawing.Size(512, 42)
		self._CRF_label1.TabIndex = 3
		self._CRF_label1.Text = "Таблица 1. Сечения кабелей и допустимые токовые нагрузки. По умолчанию заполнена данными из ГОСТ Р 50571.5.52: способ монтажа E, PVC изоляция. И ГОСТ 31996 табл. 19, 21.	"
		# 
		# CRF_return_default_table1_button
		# 
		self._CRF_return_default_table1_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._CRF_return_default_table1_button.Location = System.Drawing.Point(22, 471)
		self._CRF_return_default_table1_button.Name = "CRF_return_default_table1_button"
		self._CRF_return_default_table1_button.Size = System.Drawing.Size(156, 41)
		self._CRF_return_default_table1_button.TabIndex = 4
		self._CRF_return_default_table1_button.Text = "Установить данные по умолчанию (для табл.1)"
		self._CRF_return_default_table1_button.UseVisualStyleBackColor = True
		self._CRF_return_default_table1_button.Click += self.CRF_return_default_table1_buttonClick
		# 
		# CRF_CBnominal_dataGridView
		# 
		self._CRF_CBnominal_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_CBnominal_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._CRF_CBnominal_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._CRF_CBnominal_Column1]))
		self._CRF_CBnominal_dataGridView.Location = System.Drawing.Point(809, 72)
		self._CRF_CBnominal_dataGridView.Name = "CRF_CBnominal_dataGridView"
		self._CRF_CBnominal_dataGridView.RowTemplate.Height = 24
		self._CRF_CBnominal_dataGridView.Size = System.Drawing.Size(156, 393)
		self._CRF_CBnominal_dataGridView.TabIndex = 5
		# 
		# CRF_label2
		# 
		self._CRF_label2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._CRF_label2.Location = System.Drawing.Point(809, 21)
		self._CRF_label2.Name = "CRF_label2"
		self._CRF_label2.Size = System.Drawing.Size(156, 42)
		self._CRF_label2.TabIndex = 6
		self._CRF_label2.Text = "Таблица 2. Номинальные токи аппаратов защиты."
		# 
		# CRF_return_default_table2_button
		# 
		self._CRF_return_default_table2_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_return_default_table2_button.Location = System.Drawing.Point(809, 471)
		self._CRF_return_default_table2_button.Name = "CRF_return_default_table2_button"
		self._CRF_return_default_table2_button.Size = System.Drawing.Size(156, 41)
		self._CRF_return_default_table2_button.TabIndex = 7
		self._CRF_return_default_table2_button.Text = "Установить данные по умолчанию (для табл.2)"
		self._CRF_return_default_table2_button.UseVisualStyleBackColor = True
		self._CRF_return_default_table2_button.Click += self.CRF_return_default_table2_buttonClick
		# 
		# CRF_CBnominal_Column1
		# 
		self._CRF_CBnominal_Column1.HeaderText = "Номинальные токи аппаратов защиты (А)."
		self._CRF_CBnominal_Column1.Name = "CRF_CBnominal_Column1"
		self._CRF_CBnominal_Column1.Width = 95
		# 
		# CRF_Cables_reduction_factor_dataGridView
		# 
		self._CRF_Cables_reduction_factor_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_Cables_reduction_factor_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._CRF_Cables_reduction_factor_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._CRF_Cables_reduction_factor_Column1,
			self._CRF_Cables_reduction_factor_Column2]))
		self._CRF_Cables_reduction_factor_dataGridView.Location = System.Drawing.Point(989, 72)
		self._CRF_Cables_reduction_factor_dataGridView.Name = "CRF_Cables_reduction_factor_dataGridView"
		self._CRF_Cables_reduction_factor_dataGridView.RowTemplate.Height = 24
		self._CRF_Cables_reduction_factor_dataGridView.Size = System.Drawing.Size(213, 312)
		self._CRF_Cables_reduction_factor_dataGridView.TabIndex = 8
		# 
		# CRF_label3
		# 
		self._CRF_label3.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._CRF_label3.Location = System.Drawing.Point(989, 21)
		self._CRF_label3.Name = "CRF_label3"
		self._CRF_label3.Size = System.Drawing.Size(223, 42)
		self._CRF_label3.TabIndex = 9
		self._CRF_label3.Text = "Таблица 3. Понижающие коэффициенты для кабелей (по умолчанию по ГОСТ 50571.5.52 табл. В.52.20)"
		# 
		# CRF_Cables_reduction_factor_Column1
		# 
		self._CRF_Cables_reduction_factor_Column1.HeaderText = "Кол-во кабелей"
		self._CRF_Cables_reduction_factor_Column1.Name = "CRF_Cables_reduction_factor_Column1"
		self._CRF_Cables_reduction_factor_Column1.Width = 70
		# 
		# CRF_Cables_reduction_factor_Column2
		# 
		self._CRF_Cables_reduction_factor_Column2.HeaderText = "Коэффициенты совместной прокладки кабелей"
		self._CRF_Cables_reduction_factor_Column2.Name = "CRF_Cables_reduction_factor_Column2"
		self._CRF_Cables_reduction_factor_Column2.Width = 90
		# 
		# CRF_return_default_table3_button
		# 
		self._CRF_return_default_table3_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_return_default_table3_button.Location = System.Drawing.Point(989, 390)
		self._CRF_return_default_table3_button.Name = "CRF_return_default_table3_button"
		self._CRF_return_default_table3_button.Size = System.Drawing.Size(156, 41)
		self._CRF_return_default_table3_button.TabIndex = 10
		self._CRF_return_default_table3_button.Text = "Установить данные по умолчанию (для табл.3)"
		self._CRF_return_default_table3_button.UseVisualStyleBackColor = True
		self._CRF_return_default_table3_button.Click += self.CRF_return_default_table3_buttonClick
		# 
		# CRF_Circuit_breakers_reduction_factor_dataGridView
		# 
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._CRF_Circuit_breakers_reduction_factor_Column1,
			self._CRF_Circuit_breakers_reduction_factor_Column2]))
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.Location = System.Drawing.Point(1228, 72)
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.Name = "CRF_Circuit_breakers_reduction_factor_dataGridView"
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.RowTemplate.Height = 24
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.Size = System.Drawing.Size(213, 312)
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.TabIndex = 11
		# 
		# CRF_Circuit_breakers_reduction_factor_Column1
		# 
		self._CRF_Circuit_breakers_reduction_factor_Column1.HeaderText = "Число защитных аппаратов"
		self._CRF_Circuit_breakers_reduction_factor_Column1.Name = "CRF_Circuit_breakers_reduction_factor_Column1"
		self._CRF_Circuit_breakers_reduction_factor_Column1.Width = 70
		# 
		# CRF_Circuit_breakers_reduction_factor_Column2
		# 
		self._CRF_Circuit_breakers_reduction_factor_Column2.HeaderText = "Коэффициенты одновремен- ности"
		self._CRF_Circuit_breakers_reduction_factor_Column2.Name = "CRF_Circuit_breakers_reduction_factor_Column2"
		self._CRF_Circuit_breakers_reduction_factor_Column2.Width = 90
		# 
		# CRF_return_default_table4_button
		# 
		self._CRF_return_default_table4_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_return_default_table4_button.Location = System.Drawing.Point(1228, 390)
		self._CRF_return_default_table4_button.Name = "CRF_return_default_table4_button"
		self._CRF_return_default_table4_button.Size = System.Drawing.Size(156, 41)
		self._CRF_return_default_table4_button.TabIndex = 12
		self._CRF_return_default_table4_button.Text = "Установить данные по умолчанию (для табл.4)"
		self._CRF_return_default_table4_button.UseVisualStyleBackColor = True
		self._CRF_return_default_table4_button.Click += self.CRF_return_default_table4_buttonClick
		# 
		# CRF_label4
		# 
		self._CRF_label4.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._CRF_label4.Location = System.Drawing.Point(1228, 9)
		self._CRF_label4.Name = "CRF_label4"
		self._CRF_label4.Size = System.Drawing.Size(223, 58)
		self._CRF_label4.TabIndex = 13
		self._CRF_label4.Text = "Таблица 4. Коэффициенты одновременности совместно установленных аппаратов защиты (по умолчанию по ГОСТ 32397 табл.В.1)."
		# 
		# Cu_Al_Udrop_coeff_dataGridView
		# 
		self._Cu_Al_Udrop_coeff_dataGridView.AllowUserToAddRows = False
		self._Cu_Al_Udrop_coeff_dataGridView.AllowUserToDeleteRows = False
		self._Cu_Al_Udrop_coeff_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cu_Al_Udrop_coeff_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._Cu_Al_Udrop_coeff_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._Cu_Al_Udrop_coeff_Column,
			self._Cu_Al_Udrop_coeff_Column2,
			self._Cu_Al_Udrop_coeff_Column3,
			self._Cu_Al_Udrop_coeff_Column4]))
		self._Cu_Al_Udrop_coeff_dataGridView.Location = System.Drawing.Point(989, 510)
		self._Cu_Al_Udrop_coeff_dataGridView.Name = "Cu_Al_Udrop_coeff_dataGridView"
		self._Cu_Al_Udrop_coeff_dataGridView.Size = System.Drawing.Size(415, 60)
		self._Cu_Al_Udrop_coeff_dataGridView.TabIndex = 14
		# 
		# Cu_Al_Udrop_coeff_Column
		# 
		self._Cu_Al_Udrop_coeff_Column.HeaderText = "Медных 400/230 В"
		self._Cu_Al_Udrop_coeff_Column.Name = "Cu_Al_Udrop_coeff_Column"
		self._Cu_Al_Udrop_coeff_Column.Width = 90
		# 
		# Cu_Al_Udrop_coeff_Column2
		# 
		self._Cu_Al_Udrop_coeff_Column2.HeaderText = "Медных    230 В"
		self._Cu_Al_Udrop_coeff_Column2.Name = "Cu_Al_Udrop_coeff_Column2"
		self._Cu_Al_Udrop_coeff_Column2.Width = 90
		# 
		# Cu_Al_Udrop_coeff_Column3
		# 
		self._Cu_Al_Udrop_coeff_Column3.HeaderText = "Алюминиевых 400/230 В"
		self._Cu_Al_Udrop_coeff_Column3.Name = "Cu_Al_Udrop_coeff_Column3"
		self._Cu_Al_Udrop_coeff_Column3.Width = 90
		# 
		# Cu_Al_Udrop_coeff_Column4
		# 
		self._Cu_Al_Udrop_coeff_Column4.HeaderText = "Алюминиевых 230 В"
		self._Cu_Al_Udrop_coeff_Column4.Name = "Cu_Al_Udrop_coeff_Column4"
		self._Cu_Al_Udrop_coeff_Column4.Width = 90
		# 
		# CRF_label5
		# 
		self._CRF_label5.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_label5.Location = System.Drawing.Point(989, 455)
		self._CRF_label5.Name = "CRF_label5"
		self._CRF_label5.Size = System.Drawing.Size(290, 52)
		self._CRF_label5.TabIndex = 15
		self._CRF_label5.Text = "Таблица 5. Значения коэффициентов, входящих в формулы для расчёта сетей по потере напряжения (по умолчанию Кнорринг табл.12-9). Для проводников:"
		# 
		# CRF_return_default_table5_button
		# 
		self._CRF_return_default_table5_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._CRF_return_default_table5_button.Location = System.Drawing.Point(1285, 455)
		self._CRF_return_default_table5_button.Name = "CRF_return_default_table5_button"
		self._CRF_return_default_table5_button.Size = System.Drawing.Size(156, 41)
		self._CRF_return_default_table5_button.TabIndex = 16
		self._CRF_return_default_table5_button.Text = "Установить данные по умолчанию (для табл.5)"
		self._CRF_return_default_table5_button.UseVisualStyleBackColor = True
		self._CRF_return_default_table5_button.Click += self.CRF_return_default_table5_buttonClick
		# 
		# CRF_label6
		# 
		self._CRF_label6.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._CRF_label6.Location = System.Drawing.Point(22, 544)
		self._CRF_label6.Name = "CRF_label6"
		self._CRF_label6.Size = System.Drawing.Size(147, 26)
		self._CRF_label6.TabIndex = 17
		self._CRF_label6.Text = "Рабочее напряжение (В):"
		# 
		# CRF_Voltage_textBox
		# 
		self._CRF_Voltage_textBox.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._CRF_Voltage_textBox.Location = System.Drawing.Point(160, 541)
		self._CRF_Voltage_textBox.Name = "CRF_Voltage_textBox"
		self._CRF_Voltage_textBox.Size = System.Drawing.Size(100, 22)
		self._CRF_Voltage_textBox.TabIndex = 18
		# 
		# CRF_CtrlV_table1_button
		# 
		self._CRF_CtrlV_table1_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._CRF_CtrlV_table1_button.Location = System.Drawing.Point(194, 471)
		self._CRF_CtrlV_table1_button.Name = "CRF_CtrlV_table1_button"
		self._CRF_CtrlV_table1_button.Size = System.Drawing.Size(78, 41)
		self._CRF_CtrlV_table1_button.TabIndex = 19
		self._CRF_CtrlV_table1_button.Text = "Вставить из буфера"
		self._CRF_CtrlV_table1_button.UseVisualStyleBackColor = True
		self._CRF_CtrlV_table1_button.Click += self.CRF_CtrlV_table1_buttonClick
		# 
		# CRF_Wires_Column1
		# 
		self._CRF_Wires_Column1.HeaderText = "Сечение (кв.мм)"
		self._CRF_Wires_Column1.Name = "CRF_Wires_Column1"
		# 
		# CRF_Wires_Column6
		# 
		self._CRF_Wires_Column6.HeaderText = "Медный многожильный 1-фазный кабель. Ток (А)"
		self._CRF_Wires_Column6.Name = "CRF_Wires_Column6"
		# 
		# CRF_Wires_Column2
		# 
		self._CRF_Wires_Column2.HeaderText = "Медный многожильный 3-фазный кабель. Ток (А)."
		self._CRF_Wires_Column2.Name = "CRF_Wires_Column2"
		# 
		# CRF_Wires_Column3
		# 
		self._CRF_Wires_Column3.HeaderText = "Медный одножильный кабель. Ток (А)."
		self._CRF_Wires_Column3.Name = "CRF_Wires_Column3"
		# 
		# CRF_Wires_Column7
		# 
		self._CRF_Wires_Column7.HeaderText = "Алюминиевый многожильный 1-фазный кабель. Ток (А)."
		self._CRF_Wires_Column7.Name = "CRF_Wires_Column7"
		# 
		# CRF_Wires_Column4
		# 
		self._CRF_Wires_Column4.HeaderText = "Алюминиевый многожильный 3-фазный кабель. Ток (А)."
		self._CRF_Wires_Column4.Name = "CRF_Wires_Column4"
		# 
		# CRF_Wires_Column5
		# 
		self._CRF_Wires_Column5.HeaderText = "Алюминиевый одножильный кабель. Ток (А)."
		self._CRF_Wires_Column5.Name = "CRF_Wires_Column5"
		# 
		# CRF_Wires_Column8
		# 
		self._CRF_Wires_Column8.HeaderText = "Активные удельные сопротивления медных кабелей (мОм/м)"
		self._CRF_Wires_Column8.Name = "CRF_Wires_Column8"
		# 
		# CRF_Wires_Column9
		# 
		self._CRF_Wires_Column9.HeaderText = "Активные удельные сопротивления алюминиевых кабелей (мОм/м)"
		self._CRF_Wires_Column9.Name = "CRF_Wires_Column9"
		# 
		# CRF_Wires_Column10
		# 
		self._CRF_Wires_Column10.HeaderText = "Индуктивные удельные сопротивления кабелей (мОм/м)"
		self._CRF_Wires_Column10.Name = "CRF_Wires_Column10"
		# 
		# CRF_Import_button
		# 
		self._CRF_Import_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._CRF_Import_button.Location = System.Drawing.Point(640, 627)
		self._CRF_Import_button.Name = "CRF_Import_button"
		self._CRF_Import_button.Size = System.Drawing.Size(75, 23)
		self._CRF_Import_button.TabIndex = 20
		self._CRF_Import_button.Text = "Импорт"
		self._CRF_Import_button.UseVisualStyleBackColor = True
		self._CRF_Import_button.Click += self.CRF_Import_buttonClick
		# 
		# CRF_Export_button
		# 
		self._CRF_Export_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._CRF_Export_button.Location = System.Drawing.Point(765, 627)
		self._CRF_Export_button.Name = "CRF_Export_button"
		self._CRF_Export_button.Size = System.Drawing.Size(75, 23)
		self._CRF_Export_button.TabIndex = 21
		self._CRF_Export_button.Text = "Экспорт"
		self._CRF_Export_button.UseVisualStyleBackColor = True
		self._CRF_Export_button.Click += self.CRF_Export_buttonClick
		# 
		# CalculationResoursesForm
		# 
		self.ClientSize = System.Drawing.Size(1462, 668)
		self.Controls.Add(self._CRF_Export_button)
		self.Controls.Add(self._CRF_Import_button)
		self.Controls.Add(self._CRF_CtrlV_table1_button)
		self.Controls.Add(self._CRF_Voltage_textBox)
		self.Controls.Add(self._CRF_label6)
		self.Controls.Add(self._CRF_return_default_table5_button)
		self.Controls.Add(self._CRF_label5)
		self.Controls.Add(self._Cu_Al_Udrop_coeff_dataGridView)
		self.Controls.Add(self._CRF_label4)
		self.Controls.Add(self._CRF_return_default_table4_button)
		self.Controls.Add(self._CRF_Circuit_breakers_reduction_factor_dataGridView)
		self.Controls.Add(self._CRF_return_default_table3_button)
		self.Controls.Add(self._CRF_label3)
		self.Controls.Add(self._CRF_Cables_reduction_factor_dataGridView)
		self.Controls.Add(self._CRF_return_default_table2_button)
		self.Controls.Add(self._CRF_label2)
		self.Controls.Add(self._CRF_CBnominal_dataGridView)
		self.Controls.Add(self._CRF_return_default_table1_button)
		self.Controls.Add(self._CRF_label1)
		self.Controls.Add(self._CRF_Wires_dataGridView)
		self.Controls.Add(self._CRF_Cancel_button)
		self.Controls.Add(self._CRF_OK_button)
		self.Name = "CalculationResoursesForm"
		self.Text = "Исходные данные для расчётов"
		self.Load += self.CalculationResoursesFormLoad
		self._CRF_Wires_dataGridView.EndInit()
		self._CRF_CBnominal_dataGridView.EndInit()
		self._CRF_Cables_reduction_factor_dataGridView.EndInit()
		self._CRF_Circuit_breakers_reduction_factor_dataGridView.EndInit()
		self._Cu_Al_Udrop_coeff_dataGridView.EndInit()
		self.ResumeLayout(False)
		self.PerformLayout()


		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell





	def CRF_OK_buttonClick(self, sender, e):
		# Забираем значения сеченией и токов. Нам нужен список с подсписками [[сечения], [токи медных многожильных кабелей], ...]. То есть будет так: [['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800', '1000'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030', '1143'], ['0', '19.5', '26', '33', '46', '61', '78', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858', '972'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030', '1143']]
		# заодно проверяем правильность введённых данных
		Exit_cortege = Collect_data_from_CRF(self._CRF_Wires_dataGridView, self._CRF_CBnominal_dataGridView, self._CRF_Cables_reduction_factor_dataGridView, self._CRF_Circuit_breakers_reduction_factor_dataGridView, self._Cu_Al_Udrop_coeff_dataGridView, self._CRF_Voltage_textBox)
		notfloat = Exit_cortege[0]
		if notfloat != 0:
			#self._CRF_errorProvider1.SetError(self._CRF_OK_button, Exit_cortege[1])
			MessageBox.Show(Exit_cortege[1], "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Information)
		elif notfloat == 0:
			# Выставляем "кнопка отмена не нажата"
			global Button_Cancel_CRF_Form_pushed
			Button_Cancel_CRF_Form_pushed = 0
			self.Close()

	def CRF_Cancel_buttonClick(self, sender, e):
		self.Close()

	def CalculationResoursesFormLoad(self, sender, e):
		# Заполняем форму исходными данными
		for i in Currents_and_Sections_from_ES:
			self._CRF_Wires_dataGridView.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9]) # Токи и сечения
		for i in Current_breakers_from_ES:
			self._CRF_CBnominal_dataGridView.Rows.Add(i) # Номиналы автоматов
		for n, i in enumerate(Cables_trays_reduction_factor_from_ES):
			self._CRF_Cables_reduction_factor_dataGridView.Rows.Add(str(n+1), i) # Понижающие коэффициенты совместной прокладки кабелей
		for n, i in enumerate(CB_reduction_factor_from_ES):
			self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Add(str(n+1), i) # Понижающие коэффициенты совместной установки автоматов
		self._Cu_Al_Udrop_coeff_dataGridView.Rows.Add(VoltageDrop_Coefficiets_Knorr_ES[0], VoltageDrop_Coefficiets_Knorr_ES[1], VoltageDrop_Coefficiets_Knorr_ES[2], VoltageDrop_Coefficiets_Knorr_ES[3]) # Коэфф. потерь Кнорринга
		self._CRF_Voltage_textBox.Text = '/'.join(Voltage_ES)

	#________________________Переписываем таблицы данными по умолчанию________________________________________________________________
	def CRF_return_default_table1_buttonClick(self, sender, e):
		a = self._CRF_Wires_dataGridView.Rows.Count-1
		while a > 0:
			self._CRF_Wires_dataGridView.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		for i in Currents_and_Sections_Default:
			self._CRF_Wires_dataGridView.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9]) # Потом записываем заново все Токи и сечения по умолчанию
		
	def CRF_return_default_table2_buttonClick(self, sender, e):
		a = self._CRF_CBnominal_dataGridView.Rows.Count-1
		while a > 0:
			self._CRF_CBnominal_dataGridView.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		for i in Current_breakers_Default:
			self._CRF_CBnominal_dataGridView.Rows.Add(i) # Номиналы автоматов

	def CRF_return_default_table3_buttonClick(self, sender, e):
		a = self._CRF_Cables_reduction_factor_dataGridView.Rows.Count-1
		while a > 0:
			self._CRF_Cables_reduction_factor_dataGridView.Rows.RemoveAt(0) 
			a = a - 1
		for n, i in enumerate(Cables_trays_reduction_factor_Default):
			self._CRF_Cables_reduction_factor_dataGridView.Rows.Add(str(n+1), i) 

	def CRF_return_default_table4_buttonClick(self, sender, e):
		a = self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Count-1
		while a > 0:
			self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.RemoveAt(0) 
			a = a - 1
		for n, i in enumerate(CB_reduction_factor_Default):
			self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Add(str(n+1), i) 

	def CRF_return_default_table5_buttonClick(self, sender, e):
		for i in range(self._Cu_Al_Udrop_coeff_dataGridView.Columns.Count):
			self._Cu_Al_Udrop_coeff_dataGridView[i, 0].Value = str(VoltageDrop_Coefficiets_Knorr_Default[i]) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.

	def CRF_CtrlV_table1_buttonClick(self, sender, e):
		insert_from_clipboard_to_datagridview(self._CRF_Wires_dataGridView) # принимаем данные из буфера обмена и пишем их в ячейки таблицы

	def CRF_Import_buttonClick(self, sender, e):
		# Открываем файл для считывания данных
		ofd = OpenFileDialog() # <System.Windows.Forms.OpenFileDialog object at 0x000000000000002B [System.Windows.Forms.OpenFileDialog: Title: , FileName: ]>
		if (ofd.ShowDialog() == DialogResult.OK):
			filename = ofd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			fileText = System.IO.File.ReadAllText(filename)
			# Считываем данные из файла
			global Imported_list
			Imported_list = CRF_settings_Import(fileText) # ([['1.5', '2.5', '4', '6', '10', '16', '25', '35', '50', '70', '95', '120', '150', '185', '240', '300', '400', '500', '630', '800'], ['22', '30', '40', '51', '70', '94', '119', '148', '180', '232', '282', '328', '379', '434', '514', '593', '0', '0', '0', '0'], ['19', '25', '34', '43', '60', '80', '101', '126', '153', '196', '238', '276', '319', '364', '430', '497', '633', '749', '855', '1030'], ['19', '25', '34', '43', '60', '80', '110', '137', '167', '216', '264', '308', '356', '409', '485', '561', '656', '749', '855', '1030'], ['0', '23', '31', '39', '54', '777777777', '89', '111', '135', '173', '210', '244', '282', '322', '380', '439', '0', '0', '0', '0'], ['0', '19.5', '26', '33', '46', '61', '77', '96', '117', '150', '183', '212', '245', '280', '330', '381', '501', '610', '711', '858'], ['0', '19.5', '26', '33', '46', '61', '84', '105', '128', '166', '203', '237', '274', '315', '375', '434', '526', '610', '711', '858'], ['13.35', '8.0', '5.0', '3.33', '2.0', '1.25', '0.8', '0.57', '0.4', '0.29', '0.21', '0.17', '0.13', '0.11', '0.08', '0.07', '0', '0', '0', '0'], ['22.2', '13.3', '8.35', '5.55', '3.33', '2.08', '1.33', '0.95', '0.67', '0.48', '0.35', '0.28', '0.22', '0.18', '0.15', '0.12', '0', '0', '0', '0'], ['0.11', '0.09', '0.1', '0.09', '0.07', '0.07', '0.07', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0.06', '0', '0', '0', '0']], ['10', '16', '20', '25', '32', '40', '50', '63', '80', '100', '125', '160', '200', '250', '315', '400', '500', '630', '700', '800', '900', '1000'], ['1.0', '0.87', '0.8', '0.77', '0.75', '0.73', '0.71', '0.7', '0.68'], ['1.0', '0.8', '0.8', '0.7', '0.7', '0.6', '0.6', '0.6', '0.6', '0.5'], ['72', '12', '44', '7.4'], ['380', '220'])
			# Пробуем заполнить таблицы:
			try:
				# Токи, сечения, удельные сопротивления
				a = self._CRF_Wires_dataGridView.Rows.Count-1
				while a > 0:
					self._CRF_Wires_dataGridView.Rows.RemoveAt(0) # сначала удаляем все строки
					a = a - 1
				# for j in map(list, zip(*[i[1],i[2],i[3]])): # транспонируем список
				# for i in Imported_list[0]:
				for i in map(list, zip(*[Imported_list[0][0],Imported_list[0][1],Imported_list[0][2],Imported_list[0][3],Imported_list[0][4],Imported_list[0][5],Imported_list[0][6],Imported_list[0][7],Imported_list[0][8],Imported_list[0][9]])): # транспонируем список
					self._CRF_Wires_dataGridView.Rows.Add(i[0], i[1], i[2], i[3], i[4], i[5], i[6], i[7], i[8], i[9]) # Потом записываем заново все Токи и сечения
				# Номиналы автоматов (уставки)
				a = self._CRF_CBnominal_dataGridView.Rows.Count-1
				while a > 0:
					self._CRF_CBnominal_dataGridView.Rows.RemoveAt(0) # сначала удаляем все строки
					a = a - 1
				for i in Imported_list[1]:
					self._CRF_CBnominal_dataGridView.Rows.Add(i) # Номиналы автоматов
				# Понижающие коэффициенты кабелей
				a = self._CRF_Cables_reduction_factor_dataGridView.Rows.Count-1
				while a > 0:
					self._CRF_Cables_reduction_factor_dataGridView.Rows.RemoveAt(0) 
					a = a - 1
				for n, i in enumerate(Imported_list[2]):
					self._CRF_Cables_reduction_factor_dataGridView.Rows.Add(str(n+1), i) 
				# Понижающие коэффициенты автоматов
				a = self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Count-1
				while a > 0:
					self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.RemoveAt(0) 
					a = a - 1
				for n, i in enumerate(Imported_list[3]):
					self._CRF_Circuit_breakers_reduction_factor_dataGridView.Rows.Add(str(n+1), i) 
				# Коэффициенты Кнорринга
				for i in range(self._Cu_Al_Udrop_coeff_dataGridView.Columns.Count):
					self._Cu_Al_Udrop_coeff_dataGridView[i, 0].Value = str(Imported_list[4][i]) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
				# Напряжения
				self._CRF_Voltage_textBox.Text = '/'.join(Imported_list[5])
				TaskDialog.Show('Исходные данные для расчётов', 'Данные успешно импортированы')
			except:
				TaskDialog.Show('Исходные данные для расчётов', 'Не удалось импортировать данные. Файл импорта некорректен.')

	def CRF_Export_buttonClick(self, sender, e):
		# Собираем данные с формы (и там же их и проверяем на правильность)
		Exit_cortege = Collect_data_from_CRF(self._CRF_Wires_dataGridView, self._CRF_CBnominal_dataGridView, self._CRF_Cables_reduction_factor_dataGridView, self._CRF_Circuit_breakers_reduction_factor_dataGridView, self._Cu_Al_Udrop_coeff_dataGridView, self._CRF_Voltage_textBox)
		notfloat = Exit_cortege[0]
		if notfloat != 0:
			#self._CRF_errorProvider1.SetError(self._CRF_OK_button, Exit_cortege[1])
			MessageBox.Show(Exit_cortege[1], "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Information)
		elif notfloat == 0:
			# Сохраняем настройки во внешний txt файл
			sfd = SaveFileDialog()
			sfd.Filter = "Text files(*.txt)|*.txt" #sfd.Filter = "Text files(*.txt)|*.txt|All files(*.*)|*.*"
			sfd.FileName = doc.Title + '_исходные данные для расчётов' # имя файла по умолчанию
			if (sfd.ShowDialog() == DialogResult.OK): # sfd.ShowDialog() # файл на сохранение
				filename = sfd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
				System.IO.File.WriteAllText(filename, CRF_settings_Export(Currents_and_SectionsOutput, Current_breakersOutput, Cables_trays_reduction_factorOutput, CB_reduction_factorOutput, VoltageDrop_Coefficiets_KnorrOutput, VoltageOutput))



#_________________________________________________________________________________________________________________________________________________



















#_________________________________ Работаем с 4-м хранилищем (имена параметров с которыми работает программа) ____________________________________________________________________________
schemaGuid_for_Param_Names_Storage = System.Guid(Guidstr_Param_Names_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Вот это и есть наш список имён параметров с которыми работате программа. В своём значении по умолчанию. Список может содержать только строки.
# Структура такая: [ 'Внутреннее имя параметра 1', 'Видимое пользователю имя параметра 1', 'Описание параметра 1', 'Внутреннее имя параметра 2', 'Видимое пользователю имя параметра 2', 'Описание параметра 2',.....         ]
# Тогда мы сможем всегда легко обращаться к нужному нам значению переменной
# Внутренние (только для этой программы) названия параметров:
Param_name_0_for_Param_Names_Storage = 'Param_name_0_for_Param_Names_Storage'
Param_name_1_for_Param_Names_Storage = 'Param_name_1_for_Param_Names_Storage'
Param_name_2_for_Param_Names_Storage = 'Param_name_2_for_Param_Names_Storage'
Param_name_3_for_Param_Names_Storage = 'Param_name_3_for_Param_Names_Storage'
Param_name_4_for_Param_Names_Storage = 'Param_name_4_for_Param_Names_Storage'
Param_name_5_for_Param_Names_Storage = 'Param_name_5_for_Param_Names_Storage'
Param_name_6_for_Param_Names_Storage = 'Param_name_6_for_Param_Names_Storage'
Param_name_7_for_Param_Names_Storage = 'Param_name_7_for_Param_Names_Storage'
Param_name_8_for_Param_Names_Storage = 'Param_name_8_for_Param_Names_Storage'
Param_name_9_for_Param_Names_Storage = 'Param_name_9_for_Param_Names_Storage'
Param_name_10_for_Param_Names_Storage = 'Param_name_10_for_Param_Names_Storage'
Param_name_11_for_Param_Names_Storage = 'Param_name_11_for_Param_Names_Storage'
Param_name_12_for_Param_Names_Storage = 'Param_name_12_for_Param_Names_Storage'
Param_name_13_for_Param_Names_Storage = 'Param_name_13_for_Param_Names_Storage'
Param_name_14_for_Param_Names_Storage = 'Param_name_14_for_Param_Names_Storage'
Param_name_15_for_Param_Names_Storage = 'Param_name_15_for_Param_Names_Storage'
Param_name_16_for_Param_Names_Storage = 'Param_name_16_for_Param_Names_Storage'
Param_name_17_for_Param_Names_Storage = 'Param_name_17_for_Param_Names_Storage'
Param_name_18_for_Param_Names_Storage = 'Param_name_18_for_Param_Names_Storage'
Param_name_19_for_Param_Names_Storage = 'Param_name_19_for_Param_Names_Storage'
Param_name_20_for_Param_Names_Storage = 'Param_name_20_for_Param_Names_Storage'
Param_name_21_for_Param_Names_Storage = 'Param_name_21_for_Param_Names_Storage'
Param_name_22_for_Param_Names_Storage = 'Param_name_22_for_Param_Names_Storage'
Param_name_23_for_Param_Names_Storage = 'Param_name_23_for_Param_Names_Storage'
Param_name_24_for_Param_Names_Storage = 'Param_name_24_for_Param_Names_Storage'
Param_name_25_for_Param_Names_Storage = 'Param_name_25_for_Param_Names_Storage'
Param_name_26_for_Param_Names_Storage = 'Param_name_26_for_Param_Names_Storage'
Param_name_27_for_Param_Names_Storage = 'Param_name_27_for_Param_Names_Storage'
Param_name_28_for_Param_Names_Storage = 'Param_name_28_for_Param_Names_Storage'
Param_name_29_for_Param_Names_Storage = 'Param_name_29_for_Param_Names_Storage'
Param_name_30_for_Param_Names_Storage = 'Param_name_30_for_Param_Names_Storage'
Param_name_31_for_Param_Names_Storage = 'Param_name_31_for_Param_Names_Storage'
Param_name_32_for_Param_Names_Storage = 'Param_name_32_for_Param_Names_Storage'
Param_name_33_for_Param_Names_Storage = 'Param_name_33_for_Param_Names_Storage'
Param_name_34_for_Param_Names_Storage = 'Param_name_34_for_Param_Names_Storage'
Param_name_35_for_Param_Names_Storage = 'Param_name_35_for_Param_Names_Storage'
Param_name_36_for_Param_Names_Storage = 'Param_name_36_for_Param_Names_Storage'
Param_name_37_for_Param_Names_Storage = 'Param_name_37_for_Param_Names_Storage'
Param_name_38_for_Param_Names_Storage = 'Param_name_38_for_Param_Names_Storage'
Param_name_39_for_Param_Names_Storage = 'Param_name_39_for_Param_Names_Storage'
Param_name_40_for_Param_Names_Storage = 'Param_name_40_for_Param_Names_Storage'
Param_name_41_for_Param_Names_Storage = 'Param_name_41_for_Param_Names_Storage'
Param_name_42_for_Param_Names_Storage = 'Param_name_42_for_Param_Names_Storage'
Param_name_43_for_Param_Names_Storage = 'Param_name_43_for_Param_Names_Storage'
Param_name_44_for_Param_Names_Storage = 'Param_name_44_for_Param_Names_Storage'
Param_name_45_for_Param_Names_Storage = 'Param_name_45_for_Param_Names_Storage'
Param_name_46_for_Param_Names_Storage = 'Param_name_46_for_Param_Names_Storage'
Param_name_47_for_Param_Names_Storage = 'Param_name_47_for_Param_Names_Storage'
Param_name_48_for_Param_Names_Storage = 'Param_name_48_for_Param_Names_Storage'
Param_name_49_for_Param_Names_Storage = 'Param_name_49_for_Param_Names_Storage'



#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ДОБАВИТЬ ЕЩЁ 2 ПАРАМЕТРА ДЛЯ СПЕЦИФИКАЦИИ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#Param_name_11_for_Param_Names_Storage = 'Param_name_11_for_Param_Names_Storage'
#Param_name_12_for_Param_Names_Storage = 'Param_name_12_for_Param_Names_Storage'


# Описания параметров
Param_description_0_for_Param_Names_Storage = 'Параметр отвечающий за столбец "Единица измерения" в спецификации'
Param_description_1_for_Param_Names_Storage = 'Параметр отвечающий за столбец "Поставщик" в спецификации'
Param_description_2_for_Param_Names_Storage = 'Параметр отвечающий за столбец "Наименование и техническая характеристика" в спецификации'
Param_description_3_for_Param_Names_Storage = 'Параметр отвечающий за столбец "Тип, марка, обозначение документа, опросного листа" в спецификации'
Param_description_4_for_Param_Names_Storage = 'Участвует в команде "Имя нагрузки в эл.цепи". Параметр можно добавить ко всем семействам категории "Электрические приборы"'
Param_description_5_for_Param_Names_Storage = 'Участвует в команде "Номер цепи в щиты". Параметр можно добавить ко всем семействам категории "Электрооборудование"'
Param_description_6_for_Param_Names_Storage = 'Участвует в команде "Номер цепи в щиты". Параметр можно добавить ко всем семействам категории "Электрооборудование"'
Param_description_7_for_Param_Names_Storage = 'Номинальная мощность'
Param_description_8_for_Param_Names_Storage = 'Коэффициент мощности'
Param_description_9_for_Param_Names_Storage = 'Количество фаз'
Param_description_10_for_Param_Names_Storage = 'Напряжение'
Param_description_11_for_Param_Names_Storage = 'Значение площади выбранного элемента'
Param_description_12_for_Param_Names_Storage = 'Значение высотной отметки от уровня к которому привязан элемент'
Param_description_13_for_Param_Names_Storage = 'Значение высотной отметки от нуля проекта'
Param_description_14_for_Param_Names_Storage = 'Наименование группы или сборки для элементов входящие в её состав'
Param_description_15_for_Param_Names_Storage = 'Имя пространства'
Param_description_16_for_Param_Names_Storage = 'Имя уровня'
Param_description_17_for_Param_Names_Storage = 'Параметр отвечающий за столбец "Код продукции" в спецификации'
Param_description_18_for_Param_Names_Storage = 'Значение количества, типа и мощности осветительного прибора'
Param_description_19_for_Param_Names_Storage = 'Марка проводника'
Param_description_20_for_Param_Names_Storage = 'Длина проводника'
Param_description_21_for_Param_Names_Storage = 'Количество жил и сечение проводника'
Param_description_22_for_Param_Names_Storage = 'Количество (для спецификации)'
Param_description_23_for_Param_Names_Storage = 'Отметка от чистого пола'
Param_description_24_for_Param_Names_Storage = 'Номер группы (для трасс лотков)'
Param_description_25_for_Param_Names_Storage = 'Объём горючей массы кабеля (л/м)'
Param_description_26_for_Param_Names_Storage = 'Заполняемость лотка (%)'
Param_description_27_for_Param_Names_Storage = 'Номер пространства'
Param_description_28_for_Param_Names_Storage = 'Масса участка трассы кабелей (кг/м)'
Param_description_29_for_Param_Names_Storage = 'Группировка позиций в спецификации'
Param_description_30_for_Param_Names_Storage = 'Способ прокладки проводника (в электроцепях)'
Param_description_31_for_Param_Names_Storage = 'Id связанного файла Revit'
Param_description_32_for_Param_Names_Storage = 'Id исходного элемента'
Param_description_33_for_Param_Names_Storage = 'Отчёт о копировании'
Param_description_34_for_Param_Names_Storage = 'Транслировать в качестве задания'
Param_description_35_for_Param_Names_Storage = 'Имя связанного файла Revit'
Param_description_36_for_Param_Names_Storage = 'Позиция'
Param_description_37_for_Param_Names_Storage = 'Масса (текст)'
Param_description_38_for_Param_Names_Storage = 'Параметр примечания'
Param_description_39_for_Param_Names_Storage = 'Количество (текст)'
Param_description_40_for_Param_Names_Storage = 'Комплект чертежей'
Param_description_41_for_Param_Names_Storage = 'Длина проводника для расчёта КЗ'
Param_description_42_for_Param_Names_Storage = 'Длина проводника для расчёта распределённых потерь'
Param_description_43_for_Param_Names_Storage = 'Нормируемая освещённость'
Param_description_44_for_Param_Names_Storage = 'Габаритный размер - длина'
Param_description_45_for_Param_Names_Storage = 'Габаритный размер - ширина'
Param_description_46_for_Param_Names_Storage = 'Габаритный размер - диаметр'
Param_description_47_for_Param_Names_Storage = 'Номера цепей электрооборудования в кабеленесущих конструкциях'
Param_description_48_for_Param_Names_Storage = 'Номера цепей электроосвещения в кабеленесущих конструкциях'
Param_description_49_for_Param_Names_Storage = 'Прочие номера цепей в кабеленесущих конструкциях'


# Param_description_5_for_Param_Names_Storage = 'Участвует в команде "Записать нормы освещённости в пространства". Параметр можно добавить ко всем семействам категории "Пространства"'

# Текст для лейбла с описанием чо делает это окошко
Label_description_Param_name = 'Ниже представлена таблица с именами параметров с которыми работает программа ' + Program_name + '. Если в Вашей модели у семейств уже есть аналогичные параметры отвечающие за то же самое, Вы можете изменить имена в этой таблице. Тогда Программа будет работать с ними. Удобно также изменить стандартные имена в этой таблице если Вы работаете на шаблоне ADSK.'

# Формируем список с именами параметров по умолчанию.
Storagelist_by_Default_for_Param_Names_Storage = List[str]([Param_name_0_for_Param_Names_Storage, fam_param_names[0], Param_description_0_for_Param_Names_Storage,
Param_name_1_for_Param_Names_Storage, fam_param_names[1], Param_description_1_for_Param_Names_Storage,
Param_name_2_for_Param_Names_Storage, fam_param_names[2], Param_description_2_for_Param_Names_Storage, 
Param_name_3_for_Param_Names_Storage, fam_param_names[3], Param_description_3_for_Param_Names_Storage, 
Param_name_4_for_Param_Names_Storage, Param_Load_Name, Param_description_4_for_Param_Names_Storage,
Param_name_5_for_Param_Names_Storage, Param_Feeding_Chain, Param_description_5_for_Param_Names_Storage,
Param_name_6_for_Param_Names_Storage, Param_Outgoing_Chain, Param_description_6_for_Param_Names_Storage,
Param_name_7_for_Param_Names_Storage, Param_ES_Rated_Power, Param_description_7_for_Param_Names_Storage,
Param_name_8_for_Param_Names_Storage, Param_ES_Cosinus, Param_description_8_for_Param_Names_Storage,
Param_name_9_for_Param_Names_Storage, Param_ES_Phase_Count, Param_description_9_for_Param_Names_Storage,
Param_name_10_for_Param_Names_Storage, Param_ES_Voltage, Param_description_10_for_Param_Names_Storage,
Param_name_11_for_Param_Names_Storage, Param_TSL_Area, Param_description_11_for_Param_Names_Storage,
Param_name_12_for_Param_Names_Storage, Param_TSL_MarkFromLevel, Param_description_12_for_Param_Names_Storage,
Param_name_13_for_Param_Names_Storage, Param_TSL_MarkFromZero, Param_description_13_for_Param_Names_Storage,
Param_name_14_for_Param_Names_Storage, Param_TSL_BatchGroupName, Param_description_14_for_Param_Names_Storage,
Param_name_15_for_Param_Names_Storage, Param_TSL_SpaceName, Param_description_15_for_Param_Names_Storage,
Param_name_16_for_Param_Names_Storage, Param_TSL_LevelName, Param_description_16_for_Param_Names_Storage,
Param_name_17_for_Param_Names_Storage, Param_ADSK_product_code, Param_description_17_for_Param_Names_Storage,
Param_name_18_for_Param_Names_Storage, Param_TSL_LuminareInfo, Param_description_18_for_Param_Names_Storage,
Param_name_19_for_Param_Names_Storage, Param_TSL_WireMark, Param_description_19_for_Param_Names_Storage,
Param_name_20_for_Param_Names_Storage, Param_TSL_WireLength, Param_description_20_for_Param_Names_Storage,
Param_name_21_for_Param_Names_Storage, Param_TSL_WireCountAndSection, Param_description_21_for_Param_Names_Storage,
Param_name_22_for_Param_Names_Storage, Param_TSL_Quantity, Param_description_22_for_Param_Names_Storage,
Param_name_23_for_Param_Names_Storage, Param_TSL_MarkFromFloor, Param_description_23_for_Param_Names_Storage,
Param_name_24_for_Param_Names_Storage, Param_TSL_CableTrayGroupNumber, Param_description_24_for_Param_Names_Storage,
Param_name_25_for_Param_Names_Storage, Param_TSL_CableTrayVolumeOfCombustibleMass, Param_description_25_for_Param_Names_Storage,
Param_name_26_for_Param_Names_Storage, Param_TSL_CableTrayTrayOccupancy, Param_description_26_for_Param_Names_Storage,
Param_name_27_for_Param_Names_Storage, Param_TSL_SpaceNumber, Param_description_27_for_Param_Names_Storage,
Param_name_28_for_Param_Names_Storage, Param_TSL_WeightTrackSection, Param_description_28_for_Param_Names_Storage,
Param_name_29_for_Param_Names_Storage, Param_ADSK_grouping, Param_description_29_for_Param_Names_Storage,
Param_name_30_for_Param_Names_Storage, Param_TSL_Param_Laying_Method, Param_description_30_for_Param_Names_Storage,
Param_name_31_for_Param_Names_Storage, Param_TSL_IdLinkedFile, Param_description_31_for_Param_Names_Storage,
Param_name_32_for_Param_Names_Storage, Param_TSL_IdOriginalElement, Param_description_32_for_Param_Names_Storage,
Param_name_33_for_Param_Names_Storage, Param_TSL_CopyReport, Param_description_33_for_Param_Names_Storage,
Param_name_34_for_Param_Names_Storage, Param_TSL_BroadcastTask, Param_description_34_for_Param_Names_Storage,
Param_name_35_for_Param_Names_Storage, Param_TSL_LinkedFileName, Param_description_35_for_Param_Names_Storage,
Param_name_36_for_Param_Names_Storage, Param_ADSK_Position, Param_description_36_for_Param_Names_Storage,
Param_name_37_for_Param_Names_Storage, Param_ADSK_MassText, Param_description_37_for_Param_Names_Storage,
Param_name_38_for_Param_Names_Storage, Param_ADSK_Note, Param_description_38_for_Param_Names_Storage,
Param_name_39_for_Param_Names_Storage, Param_TSL_QuantityText, Param_description_39_for_Param_Names_Storage,
Param_name_40_for_Param_Names_Storage, Param_ADSK_Kit, Param_description_40_for_Param_Names_Storage,
Param_name_41_for_Param_Names_Storage, Param_TSL_FarestWireLength, Param_description_41_for_Param_Names_Storage,
Param_name_42_for_Param_Names_Storage, Param_TSL_ReducedWireLength, Param_description_42_for_Param_Names_Storage,
Param_name_43_for_Param_Names_Storage, Param_Rated_Illuminance, Param_description_43_for_Param_Names_Storage,
Param_name_44_for_Param_Names_Storage, Param_ADSK_dimension_length, Param_description_44_for_Param_Names_Storage,
Param_name_45_for_Param_Names_Storage, Param_ADSK_dimension_width, Param_description_45_for_Param_Names_Storage,
Param_name_46_for_Param_Names_Storage, Param_ADSK_dimension_diameter, Param_description_46_for_Param_Names_Storage,
Param_name_47_for_Param_Names_Storage, Param_TSL_CableTrayGroupNumberEM, Param_description_47_for_Param_Names_Storage,
Param_name_48_for_Param_Names_Storage, Param_TSL_CableTrayGroupNumberEO, Param_description_48_for_Param_Names_Storage,
Param_name_49_for_Param_Names_Storage, Param_TSL_CableTrayGroupNumberES, Param_description_49_for_Param_Names_Storage])




# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_Param_Names_Storage = Schema.Lookup(schemaGuid_for_Param_Names_Storage)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_Param_Names_Storage) будет <type 'NoneType'>
if sch_Param_Names_Storage is None or ProjectInfoObject.GetEntity(sch_Param_Names_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки', 'Настройки имён параметров не найдены или были повреждены.\n Будут созданы настройки имён параметров по умолчанию.')
	# Пишем настройки Тэслы
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage, SchemaName_for_Param_Names_Storage, Storagelist_by_Default_for_Param_Names_Storage) # пишем данные в хранилище 

znach2 = Read_UserKc_fromES(schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage) # Считываем данные из хранилища

# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach2]
znach2 = []
[znach2.append(i) for i in CS_help] # Вид: ['param_name_0_for_param_names_storage', u'adsk_Единица измерения', u'Параметр отвечающий за столбец "Единица измерения" в спецификации', 'param_name_1_for_param_names_storage', u'adsk_Завод-изготовитель', u'Параметр отвечающий за столбец "Поставщик" в спецификации', 'param_name_2_for_param_names_storage', u'adsk_Наименование', u'Параметр отвечающий за столбец "Наименование и техническая характеристика" в спецификации', 'param_name_3_for_param_names_storage', u'adsk_Обозначение', u'Параметр отвечающий за столбец "Тип, марка, обозначение документа, опросного листа" в спецификации', 'param_name_4_for_param_names_storage', u'tsl_Имя нагрузки', u'Параметр можно добавить ко всем семействам категории "Электрические приборы"']

# Далее накатываем обновление: новые имена параметров.
if len(znach2) < 150: # Это проверяем если в модели ещё только было 5 старых параметров. А надо же записать ещё несколько новых.
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage, SchemaName_for_Param_Names_Storage, Storagelist_by_Default_for_Param_Names_Storage) # пишем данные в хранилище 
	# И считываем их заново
	znach2 = Read_UserKc_fromES(schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage) # Считываем данные из хранилища
	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znach2]
	znach2 = []
	[znach2.append(i) for i in CS_help] # Вид: ['param_name_0_for_param_names_storage', u'adsk_Единица измерения', u'Параметр отвечающий за столбец "Единица измерения" в спецификации', 'param_name_1_for_param_names_storage', u'adsk_Завод-изготовитель', u'Параметр отвечающий за столбец "Поставщик" в спецификации', 'param_name_2_for_param_names_storage', u'adsk_Наименование', u'Параметр отвечающий за столбец "Наименование и техническая характеристика" в спецификации', 'param_name_3_for_param_names_storage', u'adsk_Обозначение', u'Параметр отвечающий за столбец "Тип, марка, обозначение документа, опросного листа" в спецификации', 'param_name_4_for_param_names_storage', u'tsl_Имя нагрузки', u'Параметр можно добавить ко всем семействам категории "Электрические приборы"']



# Присваиваем значения переменным в соответствии с информацией полученной из хранилища
Visible_Param_Name_0_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_0_for_Param_Names_Storage) + 1)] # поясняю: находим значение самой переменной на следующей (+1) позиции за именем самой переменной в списке из хранилища
Visible_Param_Name_1_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_1_for_Param_Names_Storage) + 1)]
Visible_Param_Name_2_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_2_for_Param_Names_Storage) + 1)]
Visible_Param_Name_3_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_3_for_Param_Names_Storage) + 1)]
Visible_Param_Name_4_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_4_for_Param_Names_Storage) + 1)]
Visible_Param_Name_5_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_5_for_Param_Names_Storage) + 1)] 
Visible_Param_Name_6_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_6_for_Param_Names_Storage) + 1)]
Visible_Param_Name_7_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_7_for_Param_Names_Storage) + 1)]
Visible_Param_Name_8_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_8_for_Param_Names_Storage) + 1)]
Visible_Param_Name_9_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_9_for_Param_Names_Storage) + 1)]
Visible_Param_Name_10_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_10_for_Param_Names_Storage) + 1)]
Visible_Param_Name_11_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_11_for_Param_Names_Storage) + 1)]
Visible_Param_Name_12_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_12_for_Param_Names_Storage) + 1)]
Visible_Param_Name_13_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_13_for_Param_Names_Storage) + 1)]
Visible_Param_Name_14_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_14_for_Param_Names_Storage) + 1)]
Visible_Param_Name_15_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_15_for_Param_Names_Storage) + 1)]
Visible_Param_Name_16_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_16_for_Param_Names_Storage) + 1)]
Visible_Param_Name_17_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_17_for_Param_Names_Storage) + 1)]
Visible_Param_Name_18_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_18_for_Param_Names_Storage) + 1)]
Visible_Param_Name_19_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_19_for_Param_Names_Storage) + 1)]
Visible_Param_Name_20_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_20_for_Param_Names_Storage) + 1)]
Visible_Param_Name_21_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_21_for_Param_Names_Storage) + 1)]
Visible_Param_Name_22_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_22_for_Param_Names_Storage) + 1)]
Visible_Param_Name_23_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_23_for_Param_Names_Storage) + 1)]
Visible_Param_Name_24_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_24_for_Param_Names_Storage) + 1)]
Visible_Param_Name_25_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_25_for_Param_Names_Storage) + 1)]
Visible_Param_Name_26_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_26_for_Param_Names_Storage) + 1)]
Visible_Param_Name_27_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_27_for_Param_Names_Storage) + 1)]
Visible_Param_Name_28_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_28_for_Param_Names_Storage) + 1)]
Visible_Param_Name_29_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_29_for_Param_Names_Storage) + 1)]
Visible_Param_Name_30_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_30_for_Param_Names_Storage) + 1)]
Visible_Param_Name_31_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_31_for_Param_Names_Storage) + 1)]
Visible_Param_Name_32_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_32_for_Param_Names_Storage) + 1)]
Visible_Param_Name_33_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_33_for_Param_Names_Storage) + 1)]
Visible_Param_Name_34_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_34_for_Param_Names_Storage) + 1)]
Visible_Param_Name_35_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_35_for_Param_Names_Storage) + 1)]
Visible_Param_Name_36_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_36_for_Param_Names_Storage) + 1)]
Visible_Param_Name_37_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_37_for_Param_Names_Storage) + 1)]
Visible_Param_Name_38_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_38_for_Param_Names_Storage) + 1)]
Visible_Param_Name_39_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_39_for_Param_Names_Storage) + 1)]
Visible_Param_Name_40_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_40_for_Param_Names_Storage) + 1)]
Visible_Param_Name_41_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_41_for_Param_Names_Storage) + 1)]
Visible_Param_Name_42_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_42_for_Param_Names_Storage) + 1)]
Visible_Param_Name_43_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_43_for_Param_Names_Storage) + 1)]
Visible_Param_Name_44_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_44_for_Param_Names_Storage) + 1)]
Visible_Param_Name_45_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_45_for_Param_Names_Storage) + 1)]
Visible_Param_Name_46_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_46_for_Param_Names_Storage) + 1)]
Visible_Param_Name_47_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_47_for_Param_Names_Storage) + 1)]
Visible_Param_Name_48_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_48_for_Param_Names_Storage) + 1)]
Visible_Param_Name_49_for_Param_Names_Storage = znach2[int(znach2.index(Param_name_49_for_Param_Names_Storage) + 1)]

#global Button_Cancel_for_Param_Names_Storage_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
#Button_Cancel_for_Param_Names_Storage_pushed = 1


# Диалоговое окно с именами парамтеров

class Param_Names_Storage_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Param_Names_Storage_Form_ОКbutton = System.Windows.Forms.Button()
		self._Param_Names_Storage_Form_Cancelbutton = System.Windows.Forms.Button()
		self._Param_Names_Storage_Form_label1 = System.Windows.Forms.Label()
		self._Param_Names_Storage_dataGridView1 = System.Windows.Forms.DataGridView()
		self._Param_Names_Storage_Form_Default_button = System.Windows.Forms.Button()
		self._Param_Names_Storage_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Param_Names_Storage_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Param_Names_Storage_Form_Importbutton = System.Windows.Forms.Button()
		self._Param_Names_Storage_Form_Exportbutton = System.Windows.Forms.Button()
		self._Param_Names_Storage_dataGridView1.BeginInit()
		self.SuspendLayout()
		# 
		# Param_Names_Storage_Form_ОКbutton
		# 
		self._Param_Names_Storage_Form_ОКbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Param_Names_Storage_Form_ОКbutton.Location = System.Drawing.Point(33, 511)
		self._Param_Names_Storage_Form_ОКbutton.Name = "Param_Names_Storage_Form_ОКbutton"
		self._Param_Names_Storage_Form_ОКbutton.Size = System.Drawing.Size(75, 23)
		self._Param_Names_Storage_Form_ОКbutton.TabIndex = 0
		self._Param_Names_Storage_Form_ОКbutton.Text = "OK"
		self._Param_Names_Storage_Form_ОКbutton.UseVisualStyleBackColor = True
		self._Param_Names_Storage_Form_ОКbutton.Click += self.Param_Names_Storage_Form_ОКbuttonClick
		# 
		# Param_Names_Storage_Form_Cancelbutton
		# 
		self._Param_Names_Storage_Form_Cancelbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Param_Names_Storage_Form_Cancelbutton.Location = System.Drawing.Point(520, 511)
		self._Param_Names_Storage_Form_Cancelbutton.Name = "Param_Names_Storage_Form_Cancelbutton"
		self._Param_Names_Storage_Form_Cancelbutton.Size = System.Drawing.Size(75, 23)
		self._Param_Names_Storage_Form_Cancelbutton.TabIndex = 1
		self._Param_Names_Storage_Form_Cancelbutton.Text = "Cancel"
		self._Param_Names_Storage_Form_Cancelbutton.UseVisualStyleBackColor = True
		self._Param_Names_Storage_Form_Cancelbutton.Click += self.Param_Names_Storage_Form_CancelbuttonClick
		# 
		# Param_Names_Storage_Form_label1
		# 
		self._Param_Names_Storage_Form_label1.Location = System.Drawing.Point(33, 9)
		self._Param_Names_Storage_Form_label1.Name = "Param_Names_Storage_Form_label1"
		self._Param_Names_Storage_Form_label1.Size = System.Drawing.Size(577, 71)
		self._Param_Names_Storage_Form_label1.TabIndex = 2
		self._Param_Names_Storage_Form_label1.Text = "Инфа сюда попадает из кода"
		# 
		# Param_Names_Storage_dataGridView1
		# 
		self._Param_Names_Storage_dataGridView1.AllowUserToAddRows = False
		self._Param_Names_Storage_dataGridView1.AllowUserToDeleteRows = False
		self._Param_Names_Storage_dataGridView1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Param_Names_Storage_dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._Param_Names_Storage_dataGridView1.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._Param_Names_Storage_Column1,
			self._Param_Names_Storage_Column2]))
		self._Param_Names_Storage_dataGridView1.Location = System.Drawing.Point(33, 83)
		self._Param_Names_Storage_dataGridView1.Name = "Param_Names_Storage_dataGridView1"
		self._Param_Names_Storage_dataGridView1.RowTemplate.Height = 24
		self._Param_Names_Storage_dataGridView1.Size = System.Drawing.Size(562, 361)
		self._Param_Names_Storage_dataGridView1.TabIndex = 3
		# 
		# Param_Names_Storage_Form_Default_button
		# 
		self._Param_Names_Storage_Form_Default_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Param_Names_Storage_Form_Default_button.Location = System.Drawing.Point(33, 455)
		self._Param_Names_Storage_Form_Default_button.Name = "Param_Names_Storage_Form_Default_button"
		self._Param_Names_Storage_Form_Default_button.Size = System.Drawing.Size(243, 38)
		self._Param_Names_Storage_Form_Default_button.TabIndex = 4
		self._Param_Names_Storage_Form_Default_button.Text = "По умолчанию"
		self._Param_Names_Storage_Form_Default_button.UseVisualStyleBackColor = True
		self._Param_Names_Storage_Form_Default_button.Click += self.Param_Names_Storage_Form_Default_buttonClick
		# 
		# Param_Names_Storage_Column1
		# 
		self._Param_Names_Storage_Column1.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.AllCells
		self._Param_Names_Storage_Column1.HeaderText = "Имя параметра"
		self._Param_Names_Storage_Column1.Name = "Param_Names_Storage_Column1"
		self._Param_Names_Storage_Column1.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.NotSortable
		self._Param_Names_Storage_Column1.Width = 105
		# 
		# Param_Names_Storage_Column2
		# 
		self._Param_Names_Storage_Column2.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.Fill
		self._Param_Names_Storage_Column2.HeaderText = "Описание параметра"
		self._Param_Names_Storage_Column2.Name = "Param_Names_Storage_Column2"
		self._Param_Names_Storage_Column2.ReadOnly = True
		self._Param_Names_Storage_Column2.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.NotSortable
		# 
		# Param_Names_Storage_Form_Importbutton
		# 
		self._Param_Names_Storage_Form_Importbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Param_Names_Storage_Form_Importbutton.Location = System.Drawing.Point(201, 511)
		self._Param_Names_Storage_Form_Importbutton.Name = "Param_Names_Storage_Form_Importbutton"
		self._Param_Names_Storage_Form_Importbutton.Size = System.Drawing.Size(75, 23)
		self._Param_Names_Storage_Form_Importbutton.TabIndex = 5
		self._Param_Names_Storage_Form_Importbutton.Text = "Импорт"
		self._Param_Names_Storage_Form_Importbutton.UseVisualStyleBackColor = True
		self._Param_Names_Storage_Form_Importbutton.Click += self.Param_Names_Storage_Form_ImportbuttonClick
		# 
		# Param_Names_Storage_Form_Exportbutton
		# 
		self._Param_Names_Storage_Form_Exportbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Param_Names_Storage_Form_Exportbutton.Location = System.Drawing.Point(347, 511)
		self._Param_Names_Storage_Form_Exportbutton.Name = "Param_Names_Storage_Form_Exportbutton"
		self._Param_Names_Storage_Form_Exportbutton.Size = System.Drawing.Size(75, 23)
		self._Param_Names_Storage_Form_Exportbutton.TabIndex = 6
		self._Param_Names_Storage_Form_Exportbutton.Text = "Экспорт"
		self._Param_Names_Storage_Form_Exportbutton.UseVisualStyleBackColor = True
		self._Param_Names_Storage_Form_Exportbutton.Click += self.Param_Names_Storage_Form_ExportbuttonClick
		# 
		# Param_Names_Storage_Form
		# 
		self.ClientSize = System.Drawing.Size(627, 546)
		self.Controls.Add(self._Param_Names_Storage_Form_Exportbutton)
		self.Controls.Add(self._Param_Names_Storage_Form_Importbutton)
		self.Controls.Add(self._Param_Names_Storage_Form_Default_button)
		self.Controls.Add(self._Param_Names_Storage_dataGridView1)
		self.Controls.Add(self._Param_Names_Storage_Form_label1)
		self.Controls.Add(self._Param_Names_Storage_Form_Cancelbutton)
		self.Controls.Add(self._Param_Names_Storage_Form_ОКbutton)
		self.Name = "Param_Names_Storage_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Имена параметров"
		self.Load += self.Param_Names_Storage_FormLoad
		self._Param_Names_Storage_dataGridView1.EndInit()
		self.ResumeLayout(False)

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def Param_Names_Storage_FormLoad(self, sender, e):
		a = 1 # счётчик
		while a < len(znach2):
			self._Param_Names_Storage_dataGridView1.Rows.Add(znach2[a], znach2[a+1]) # Заполняем таблицу исходными данными
			a = a + 3
		self._Param_Names_Storage_Form_label1.Text = Label_description_Param_name
		self._Param_Names_Storage_Form_Default_button.Text = 'Выставить имена парамтеров по умолчанию из шаблона ' + Program_name

	def Param_Names_Storage_Form_ОКbuttonClick(self, sender, e):
		# Забираем значения
		#global ParamNamesForWindowOutput # Список вида ['Единицы измерения', 'Изготовитель', 'НаименованиепоГОСТ', 'Обозначение', 'Имя нагрузки']
		ParamNamesForWindowOutput = []
		a = 0 # счётчик
		while a < self._Param_Names_Storage_dataGridView1.Rows.Count:
			ParamNamesForWindowOutput.append(self._Param_Names_Storage_dataGridView1[0, a].Value)
			a = a + 1

		# формируем список для записи
		Storagelist_for_Param_Names_Storage = List[str]([Param_name_0_for_Param_Names_Storage, ParamNamesForWindowOutput[0], Param_description_0_for_Param_Names_Storage,
		Param_name_1_for_Param_Names_Storage, ParamNamesForWindowOutput[1], Param_description_1_for_Param_Names_Storage,
		Param_name_2_for_Param_Names_Storage, ParamNamesForWindowOutput[2], Param_description_2_for_Param_Names_Storage, 
		Param_name_3_for_Param_Names_Storage, ParamNamesForWindowOutput[3], Param_description_3_for_Param_Names_Storage, 
		Param_name_4_for_Param_Names_Storage, ParamNamesForWindowOutput[4], Param_description_4_for_Param_Names_Storage,
		Param_name_5_for_Param_Names_Storage, ParamNamesForWindowOutput[5], Param_description_5_for_Param_Names_Storage,
		Param_name_6_for_Param_Names_Storage, ParamNamesForWindowOutput[6], Param_description_6_for_Param_Names_Storage,
		Param_name_7_for_Param_Names_Storage, ParamNamesForWindowOutput[7], Param_description_7_for_Param_Names_Storage,
		Param_name_8_for_Param_Names_Storage, ParamNamesForWindowOutput[8], Param_description_8_for_Param_Names_Storage,
		Param_name_9_for_Param_Names_Storage, ParamNamesForWindowOutput[9], Param_description_9_for_Param_Names_Storage,
		Param_name_10_for_Param_Names_Storage, ParamNamesForWindowOutput[10], Param_description_10_for_Param_Names_Storage,
		Param_name_11_for_Param_Names_Storage, ParamNamesForWindowOutput[11], Param_description_11_for_Param_Names_Storage,
		Param_name_12_for_Param_Names_Storage, ParamNamesForWindowOutput[12], Param_description_12_for_Param_Names_Storage,
		Param_name_13_for_Param_Names_Storage, ParamNamesForWindowOutput[13], Param_description_13_for_Param_Names_Storage,
		Param_name_14_for_Param_Names_Storage, ParamNamesForWindowOutput[14], Param_description_14_for_Param_Names_Storage,
		Param_name_15_for_Param_Names_Storage, ParamNamesForWindowOutput[15], Param_description_15_for_Param_Names_Storage,
		Param_name_16_for_Param_Names_Storage, ParamNamesForWindowOutput[16], Param_description_16_for_Param_Names_Storage,
		Param_name_17_for_Param_Names_Storage, ParamNamesForWindowOutput[17], Param_description_17_for_Param_Names_Storage,
		Param_name_18_for_Param_Names_Storage, ParamNamesForWindowOutput[18], Param_description_18_for_Param_Names_Storage,
		Param_name_19_for_Param_Names_Storage, ParamNamesForWindowOutput[19], Param_description_19_for_Param_Names_Storage,
		Param_name_20_for_Param_Names_Storage, ParamNamesForWindowOutput[20], Param_description_20_for_Param_Names_Storage,
		Param_name_21_for_Param_Names_Storage, ParamNamesForWindowOutput[21], Param_description_21_for_Param_Names_Storage,
		Param_name_22_for_Param_Names_Storage, ParamNamesForWindowOutput[22], Param_description_22_for_Param_Names_Storage,
		Param_name_23_for_Param_Names_Storage, ParamNamesForWindowOutput[23], Param_description_23_for_Param_Names_Storage,
		Param_name_24_for_Param_Names_Storage, ParamNamesForWindowOutput[24], Param_description_24_for_Param_Names_Storage,
		Param_name_25_for_Param_Names_Storage, ParamNamesForWindowOutput[25], Param_description_25_for_Param_Names_Storage,
		Param_name_26_for_Param_Names_Storage, ParamNamesForWindowOutput[26], Param_description_26_for_Param_Names_Storage,
		Param_name_27_for_Param_Names_Storage, ParamNamesForWindowOutput[27], Param_description_27_for_Param_Names_Storage,
		Param_name_28_for_Param_Names_Storage, ParamNamesForWindowOutput[28], Param_description_28_for_Param_Names_Storage,
		Param_name_29_for_Param_Names_Storage, ParamNamesForWindowOutput[29], Param_description_29_for_Param_Names_Storage,
		Param_name_30_for_Param_Names_Storage, ParamNamesForWindowOutput[30], Param_description_30_for_Param_Names_Storage,
		Param_name_31_for_Param_Names_Storage, ParamNamesForWindowOutput[31], Param_description_31_for_Param_Names_Storage,
		Param_name_32_for_Param_Names_Storage, ParamNamesForWindowOutput[32], Param_description_32_for_Param_Names_Storage,
		Param_name_33_for_Param_Names_Storage, ParamNamesForWindowOutput[33], Param_description_33_for_Param_Names_Storage,
		Param_name_34_for_Param_Names_Storage, ParamNamesForWindowOutput[34], Param_description_34_for_Param_Names_Storage,
		Param_name_35_for_Param_Names_Storage, ParamNamesForWindowOutput[35], Param_description_35_for_Param_Names_Storage,
		Param_name_36_for_Param_Names_Storage, ParamNamesForWindowOutput[36], Param_description_36_for_Param_Names_Storage,
		Param_name_37_for_Param_Names_Storage, ParamNamesForWindowOutput[37], Param_description_37_for_Param_Names_Storage,
		Param_name_38_for_Param_Names_Storage, ParamNamesForWindowOutput[38], Param_description_38_for_Param_Names_Storage,
		Param_name_39_for_Param_Names_Storage, ParamNamesForWindowOutput[39], Param_description_39_for_Param_Names_Storage,
		Param_name_40_for_Param_Names_Storage, ParamNamesForWindowOutput[40], Param_description_40_for_Param_Names_Storage,
		Param_name_41_for_Param_Names_Storage, ParamNamesForWindowOutput[41], Param_description_41_for_Param_Names_Storage,
		Param_name_42_for_Param_Names_Storage, ParamNamesForWindowOutput[42], Param_description_42_for_Param_Names_Storage,
		Param_name_43_for_Param_Names_Storage, ParamNamesForWindowOutput[43], Param_description_43_for_Param_Names_Storage,
		Param_name_44_for_Param_Names_Storage, ParamNamesForWindowOutput[44], Param_description_44_for_Param_Names_Storage,
		Param_name_45_for_Param_Names_Storage, ParamNamesForWindowOutput[45], Param_description_45_for_Param_Names_Storage,
		Param_name_46_for_Param_Names_Storage, ParamNamesForWindowOutput[46], Param_description_46_for_Param_Names_Storage,
		Param_name_47_for_Param_Names_Storage, ParamNamesForWindowOutput[47], Param_description_47_for_Param_Names_Storage,
		Param_name_48_for_Param_Names_Storage, ParamNamesForWindowOutput[48], Param_description_48_for_Param_Names_Storage,
		Param_name_49_for_Param_Names_Storage, ParamNamesForWindowOutput[49], Param_description_49_for_Param_Names_Storage
		])
		# пишем данные в хранилище
		Wrtite_to_ExtensibleStorage (schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage, SchemaName_for_Param_Names_Storage, Storagelist_for_Param_Names_Storage) # пишем данные в хранилище 
		global znach2
		znach2 = Read_UserKc_fromES(schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage) # Считываем данные из хранилища
		#global Button_Cancel_for_Param_Names_Storage_pushed
		#Button_Cancel_for_Param_Names_Storage_pushed = 0
		self.Close()

	def Param_Names_Storage_Form_Default_buttonClick(self, sender, e):
		# Заполняем таблицу именами параметров по умолчанию
		a = 1
		for i in range(self._Param_Names_Storage_dataGridView1.Rows.Count):
			self._Param_Names_Storage_dataGridView1[0, i].Value = Storagelist_by_Default_for_Param_Names_Storage[a]
			a = a + 3


	def Param_Names_Storage_Form_ImportbuttonClick(self, sender, e):
		# Открываем файл для считывания данных
		ofd = OpenFileDialog() # <System.Windows.Forms.OpenFileDialog object at 0x000000000000002B [System.Windows.Forms.OpenFileDialog: Title: , FileName: ]>
		if (ofd.ShowDialog() == DialogResult.OK):
			filename = ofd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			fileText = System.IO.File.ReadAllText(filename)
			Imported_list = fileText.split('<<@@>>')
		# Заполняем таблицу имён параметров
		try:
			a = 0 # счётчик
			while a < len(Imported_list):
				self._Param_Names_Storage_dataGridView1[0, a].Value = Imported_list[a] # Заполняем таблицу импортированными данными. первая цифра - номер столбца, вторая - номер строки (нумерация идёт с нуля)
				a = a + 1
			TaskDialog.Show('Имена параметров', 'Данные успешно импортированы')
		except:
			TaskDialog.Show('Имена параметров', 'Не удалось импортировать данные. Файл импорта некорректен.')

			
	def Param_Names_Storage_Form_ExportbuttonClick(self, sender, e):
		# Забираем значения
		ParamNamesForExport = [] # список вида: [u'ADSK_Единица измерения', u'ADSK_Завод-изготовитель', u'ADSK_Наименование', ... ]
		a = 0 # счётчик
		while a < self._Param_Names_Storage_dataGridView1.Rows.Count:
			ParamNamesForExport.append(self._Param_Names_Storage_dataGridView1[0, a].Value)
			a = a + 1
		# Экспортируем
		Export_text_string = '' # строка для экспорта вида: 'ADSK_Единица измерения<<@@>>ADSK_Завод-изготовитель<<@@>>ADSK_Наименование<<@@>>...
		Export_text_string = '<<@@>>'.join(ParamNamesForExport)
		# Сохраняем настройки во внешний txt файл
		sfd = SaveFileDialog()
		sfd.Filter = "Text files(*.txt)|*.txt" #sfd.Filter = "Text files(*.txt)|*.txt|All files(*.*)|*.*"
		sfd.FileName = doc.Title + '_имена_параметров' # имя файла по умолчанию
		if (sfd.ShowDialog() == DialogResult.OK): # sfd.ShowDialog() # файл на сохранение
			filename = sfd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			System.IO.File.WriteAllText(filename, Export_text_string)


	def Param_Names_Storage_Form_CancelbuttonClick(self, sender, e):
		self.Close()




#Param_Names_Storage_Form().ShowDialog()





































#_________________________________ Работаем с 5-м хранилищем (нормы освещённости с которыми работает программа) ____________________________________________________________________________
schemaGuid_for_Illumination_Values_Storage = System.Guid(Guidstr_Illumination_Values_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Вот это и есть наш список норм освещённости с которыми работате программа. В своём значении по умолчанию. Список может содержать только строки.
# В нём зарезервировано по пять дополнительных значений на каждое помещение - это на всякий случай на будущее
# Структура такая: [ 'Имя помещения 1', 'Норма освещённости (Лк) 1', 'Высота рабочей плоскости 1', 'Ссылка на нормы или пояснение 1', 'Резерв ячейки 1.1', 'Резерв ячейки 1.2', 'Резерв ячейки 1.3', 'Резерв ячейки 1.4', 'Резерв ячейки 1.5', 'Имя помещения 2', 'Норма освещённости (Лк) 2', 'Высота рабочей плоскости 2', 'Ссылка на нормы или пояснение 2',  'Резерв ячейки 2.1', 'Резерв ячейки 2.2', 'Резерв ячейки 2.3', 'Резерв ячейки 2.4', 'Резерв ячейки 2.5', .....         ]

# Формируем список с именами параметров по умолчанию.
Storagelist_by_Default_for_Illumination_Values_Storage = List[str](['Раздевальная', '300', '0', 'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '',
'Групповая', '400', '0', 'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '',
'Игральная', '400', '0', 'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '',
'Столовая', '400', '0', 'СП 52.13330.2016, табл. Л.1, п.55',  '', '', '', '', '',
'Спальная', '150', '0', 'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', ''])


# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_Illumination_Values_Storage = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_Illumination_Values_Storage) будет <type 'NoneType'>
if sch_Illumination_Values_Storage is None or ProjectInfoObject.GetEntity(sch_Illumination_Values_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки', 'Настройки норм освещённости не найдены или были повреждены.\n Будут созданы настройки норм освещённости по умолчанию.')
	# Пишем настройки Тэслы
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Illumination_Values_Storage, ProjectInfoObject, FieldName_for_Illumination_Values_Storage, SchemaName_for_Illumination_Values_Storage, Storagelist_by_Default_for_Illumination_Values_Storage) # пишем данные в хранилище 


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


# Заполняем лэйблы
IlVal_label2_text = 'Таблица пространств найденных в модели для которых не указаны нормы освещённости в таблице выше'

# Функция забирает значения из таблицы норм освещённости и формирует список готовый для записи в Хранилище
# На входе сама таблица DataGridView в виде: self._IlVal_dataGridView1
# На выходе список вида: [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '', u'вася', '233', '22', u'ййййй', '', '', '', '', '']
def Take_IlluminationNormsDataFromWindow (DataGridView_totakefrom):
	OutputListforES = []
	a = 0 # счётчик
	while a < DataGridView_totakefrom.Rows.Count - 1:
		OutputListforES.append(DataGridView_totakefrom[0, a].Value)
		OutputListforES.append(DataGridView_totakefrom[1, a].Value)
		OutputListforES.append(DataGridView_totakefrom[2, a].Value)
		OutputListforES.append(DataGridView_totakefrom[3, a].Value)
		OutputListforES.append('') # зарезервировано на всякий случай
		OutputListforES.append('')
		OutputListforES.append('')
		OutputListforES.append('')
		OutputListforES.append('')
		a = a + 1
	return OutputListforES



# Функция проверки правильности введённых данных
# На входе <System.Windows.Forms.DataGridView object at 0x000000000000002C [System.Windows.Forms.DataGridView]>
# На выходе строка с сформированным предупреждением о неправильности ввода
def IlVal_InputChecks (DataGridView_totakefrom):
	hlp_empty = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь оставил пустое значение
	hlp_onlypoint = 0 # вспомогательная переменная. Если она будет больше нуля, то где-то в таблицах Пользователь разделил целую и дробную части запятой, а не точкой
	for i in range(DataGridView_totakefrom.Rows.Count - 1):
		if DataGridView_totakefrom[0, i].Value == None or DataGridView_totakefrom[0, i].Value == '':
			hlp_empty = hlp_empty + 1
		try:
			float(DataGridView_totakefrom[1, i].Value)
		except SystemError:
			hlp_empty = hlp_empty + 1 # проверка что поле не пустое
		except ValueError:
			hlp_onlypoint = hlp_onlypoint + 1 # проверка что число введено с точкой
		try:
			float(DataGridView_totakefrom[2, i].Value)
		except SystemError:
			hlp_empty = hlp_empty + 1 # проверка что поле не пустое
		except ValueError:
			hlp_onlypoint = hlp_onlypoint + 1 # проверка что число введено с точкой

	Exit_alert_text = ''
	if hlp_empty > 0:
		Exit_alert_text = Exit_alert_text + 'Пустые ячейки в столбцах имени помещения, освещённости и рабочей плоскости не допускаются. Вместо пустых значений допускается писать нули.\n'
	if hlp_onlypoint > 0:
		Exit_alert_text = Exit_alert_text + 'Введённые Вами цифры должны быть числами с разделителем целой и дробной частей в виде точки.'

	return Exit_alert_text


# Функция эскпорта данных осввещённости
# На входе <System.Windows.Forms.DataGridView object at 0x000000000000002C [System.Windows.Forms.DataGridView]>
# На выходе строка готовая для записи во внешний файл
def IlVal_Export (DataGridView_totakefrom):
	Export_text_string = '' # строка для экспорта
	for i in range(DataGridView_totakefrom.Rows.Count - 1):
		Export_text_string = Export_text_string + '&&@@&&' # разделитель новой строки
		for j in range(DataGridView_totakefrom.Columns.Count):
			try:
				Export_text_string = Export_text_string + DataGridView_totakefrom[j, i].Value + '<<@@>>' # разделитель значений в строке
			except:
				Export_text_string = Export_text_string + '' + '<<@@>>' # чтобы пустые значения в таблице воспринимались пустыми строками, а не NoneType
	return Export_text_string



# Функция импорта данных осввещённости
# На входе кодированная строка из внешнего файла
# На выходе список готовый для заполнения таблицы вида [[u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52'], [u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55'], [u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56'], [u'вася', '123', '450', u'ппп'], [u'вапвыпа', '1', '44', ''], ['Sup Space 1', '12', '15', '']]def IlVal_Import (Import_text_string):
def IlVal_Import(Import_text_string):
	Imported_list = [] # [[u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52'], [u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55'], [u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56'], [u'вася', '123', '450', u'ппп'], [u'вапвыпа', '1', '44', ''], ['Sup Space 1', '12', '15', '']]
	# Разобьём строку на список со строками
	Rows_list_tmp = Import_text_string.partition('&&@@&&')
	Rows_list = [] # Список с элементами - строками в будущей таблице. Например станет равным ['11', '22', '33', '44']. То есть: [u'Раздевальная<<@@>>300<<@@>>0<<@@>>СП 52.13330.2016, табл. Л.1, п.52<<@@>>', u'Групповая<<@@>>400<<@@>>0<<@@>>СП 52.13330.2016, табл. Л.1, п.53<<@@>>', u'Игральная<<@@>>400<<@@>>0<<@@>>СП 52.13330.2016, табл. Л.1, п.53<<@@>>', u'Столовая<<@@>>400<<@@>>0<<@@>>СП 52.13330.2016, табл. Л.1, п.55<<@@>>', u'Спальная<<@@>>150<<@@>>0<<@@>>СП 52.13330.2016, табл. Л.1, п.56<<@@>>', u'вася<<@@>>123<<@@>>450<<@@>>ппп<<@@>>', u'вапвыпа<<@@>>1<<@@>>44<<@@>><<@@>>', 'Sup Space 1<<@@>>12<<@@>>15<<@@>><<@@>>']
	while Rows_list_tmp != ('', '', ''):
		Rows_list.append(Rows_list_tmp[0])
		Rows_list_tmphlp = Rows_list_tmp[-1].partition('&&@@&&')
		Rows_list_tmp = Rows_list_tmphlp
	Rows_list = Rows_list[1:] # выкинем первый элемент - он всегда будет ''

	# Теперь сделаем из Rows_list итоговый список с подсписками
	for i in Rows_list:
		Cur_Rows_list_tmp = i.partition('<<@@>>')
		cur_list_hlp = [] # список - текущая строка будущей таблицы в виде списка
		while Cur_Rows_list_tmp != ('', '', ''):
			cur_list_hlp.append(Cur_Rows_list_tmp[0])
			Cur_Rows_list_tmphlp = Cur_Rows_list_tmp[-1].partition('<<@@>>')
			Cur_Rows_list_tmp = Cur_Rows_list_tmphlp
		# cur_list_hlp = cur_list_hlp[1:] # выкинем первый элемент - он всегда будет ''
		Imported_list.append(cur_list_hlp)

	return Imported_list


# Окошко с выводом результатов по нормам освещённости и рабочим плоскостям записанным в пространства моделей
# Illumination_WPandRA_AlertForm().ShowDialog()
class Illumination_WPandRA_AlertForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Illumination_WPandRA_AlertForm_textBox1 = System.Windows.Forms.TextBox()
		self._Illumination_WPandRA_AlertForm_OKbutton = System.Windows.Forms.Button()
		self.SuspendLayout()
		# 
		# Illumination_WPandRA_AlertForm_textBox1
		# 
		self._Illumination_WPandRA_AlertForm_textBox1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Illumination_WPandRA_AlertForm_textBox1.Location = System.Drawing.Point(24, 12)
		self._Illumination_WPandRA_AlertForm_textBox1.Multiline = True
		self._Illumination_WPandRA_AlertForm_textBox1.Name = "Illumination_WPandRA_AlertForm_textBox1"
		self._Illumination_WPandRA_AlertForm_textBox1.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
		self._Illumination_WPandRA_AlertForm_textBox1.Size = System.Drawing.Size(323, 139)
		self._Illumination_WPandRA_AlertForm_textBox1.TabIndex = 0
		# 
		# Illumination_WPandRA_AlertForm_OKbutton
		# 
		self._Illumination_WPandRA_AlertForm_OKbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Illumination_WPandRA_AlertForm_OKbutton.Location = System.Drawing.Point(145, 178)
		self._Illumination_WPandRA_AlertForm_OKbutton.Name = "Illumination_WPandRA_AlertForm_OKbutton"
		self._Illumination_WPandRA_AlertForm_OKbutton.Size = System.Drawing.Size(75, 23)
		self._Illumination_WPandRA_AlertForm_OKbutton.TabIndex = 1
		self._Illumination_WPandRA_AlertForm_OKbutton.Text = "OK"
		self._Illumination_WPandRA_AlertForm_OKbutton.UseVisualStyleBackColor = True
		self._Illumination_WPandRA_AlertForm_OKbutton.Click += self.Illumination_WPandRA_AlertForm_OKbuttonClick
		# 
		# Illumination_WPandRA_AlertForm
		# 
		self.ClientSize = System.Drawing.Size(370, 213)
		self.Controls.Add(self._Illumination_WPandRA_AlertForm_OKbutton)
		self.Controls.Add(self._Illumination_WPandRA_AlertForm_textBox1)
		self.Name = "Illumination_WPandRA_AlertForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Нормы и рабочие плоскости освещённости"
		self.Load += self.Illumination_WPandRA_AlertFormLoad
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def Illumination_WPandRA_AlertFormLoad(self, sender, e):
		self.ActiveControl = self._Illumination_WPandRA_AlertForm_OKbutton # ставим фокус на кнопку ОК чтобы по Enter её быстро нажимать
		self._Illumination_WPandRA_AlertForm_textBox1.Text = exit_str_WPandRI

	def Illumination_WPandRA_AlertForm_OKbuttonClick(self, sender, e):
		self.Close()











'''
Программа выставляет высоту рабочей плоскости и нормы освещённости
всем пространствам в модели для которых были найдены данные в Табличке из Настроек программы.
И выдаёт результат чего и где вытсавлено в виде строки.
Обращение: IlluminationWorkPlaneSet(self._IlVal_dataGridView1, 'TSL_Нормируемая освещённость')
'''
def IlluminationWorkPlaneSet (DataGridView_totakefrom, Param_Name):

	# Забираем данные по рабочим плоскостям из таблицы
	znach3 = Take_IlluminationNormsDataFromWindow(DataGridView_totakefrom) # На выходе список вида: [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '', u'вася', '233', '22', u'ййййй', '', '', '', '', '']

	# Готовим списки для работы плагина
	spaces_els = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_MEPSpaces).ToElements() # вытаскиваем все пространства из проекта
	spaces_els_numbers = [] # номера пространств ['1', '2', '4', '5']
	spaces_els_names = [] # имена пространств ['Sup Space 1', 'Sup space 2', ...]
	rated_illumination_workplane = [] # нормируемая рабочая плоскость из таблицы в окне настроек
	rated_illumination_value = [] # нормируемая освещённость из таблицы в окне настроек

	for i in spaces_els:
		spaces_els_numbers.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NUMBER).AsString()) # Получаем номер пространства
		cur_space_name_hlp = GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString() # вспомогательная переменная. Имя текущего пространства
		spaces_els_names.append(cur_space_name_hlp) # Получаем имя пространства
		cur_cons_list = Get_coincidence_in_list(cur_space_name_hlp, znach3) # вспомогательная переменная. Индексы найдённых имён пространств или [] если пространства не найдены в ES.
		if cur_cons_list != []: # если текущее имя пространства есть в Хранилище:
			rated_illumination_workplane.append(float(znach3[cur_cons_list[0]+2])) # выписываем высоту рабочей плоскости для данного имени пространства
			rated_illumination_value.append(float(znach3[cur_cons_list[0]+1])) # выписываем норму освещённости для данного имени пространства
		else:
			rated_illumination_workplane.append('Нет данных')
			rated_illumination_value.append('Нет данных')

	# Param_Name = 'TSL_Нормируемая освещённость'
	#Записываем рабочие плоскости и нормы освещённости в каждое пространство
	isok_worplanes = 0 # счётчик в сколько пространств записали рабочие плоскости
	spaces_els_names_absent_WP = [] # список имён пространств для которых нет данных о рабочей плоскости из Таблички в окне
	isok_ratedilluminance = 0 # счётчик в сколько пространств записали нормы освещённости
	spaces_els_names_absent_RI = [] # список имён пространств для которых нет данных о нормах освещённости из Таблички в окне
	t = Transaction(doc, 'Set illumination values and workplanes')
	t.Start()
	for n, i in enumerate(spaces_els):
		# рабочие плоскости
		if rated_illumination_workplane[n] != 'Нет данных':
			try: # для ревита 2019
				GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_ROOM_LIGHTING_CALC_WORKPLANE).Set(UnitUtils.ConvertToInternalUnits(rated_illumination_workplane[n], DisplayUnitType.DUT_MILLIMETERS))
			except: # для Ревита 2022
				GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_ROOM_LIGHTING_CALC_WORKPLANE).Set(UnitUtils.ConvertToInternalUnits(rated_illumination_workplane[n], UnitTypeId.Millimeters))
			isok_worplanes = isok_worplanes + 1
		else:
			spaces_els_names_absent_WP.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString()) # пишем имя пространства для которого нет данных по рабочей плоскости
		# нормы освещённости
		if rated_illumination_value[n] != 'Нет данных':
			try: # для ревита 2019
				i.LookupParameter(Param_Name).Set(UnitUtils.ConvertToInternalUnits(rated_illumination_value[n], DisplayUnitType.DUT_LUX))
			except: # для Ревита 2022
				i.LookupParameter(Param_Name).Set(UnitUtils.ConvertToInternalUnits(rated_illumination_value[n], UnitTypeId.Lux))
			#i.LookupParameter(Param_Name).Set(rated_illumination_value[n])
			isok_ratedilluminance = isok_ratedilluminance + 1
		else:
			spaces_els_names_absent_RI.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString()) # пишем имя пространства для которого нет данных по нормам освещённости

	t.Commit()

	# Формируем строку об отсутствующих рабочих плоскостях
	if spaces_els_names_absent_WP != []:
		spaces_els_names_absent_WP_string = 'Для следующих пространств нет данных о высоте их рабочей плоскости освещения:\r\n' + ', '.join(spaces_els_names_absent_WP) + '.\r\nВы можете задать для них рабочие плоскости в Настройках Программы.'
	else:
		spaces_els_names_absent_WP_string = ''

	# Формируем строку об отсутствующих нормах освещённости
	if spaces_els_names_absent_RI != []:
		spaces_els_names_absent_RI_string = 'Для следующих пространств нет данных о нормируемой освещённости:\r\n' + ', '.join(spaces_els_names_absent_RI) + '.\r\nВы можете задать для них нормы освещённости в Настройках Программы.'
	else:
		spaces_els_names_absent_RI_string = ''

	# Формируем строку для оповещения пользователя.
	exitstr = 'Нормы освещённости выставлены в ' + str(isok_ratedilluminance) + ' пространствах.\r\n' + spaces_els_names_absent_RI_string + '.\r\n\r\nРабочие плоскости освещения выставлены в ' + str(isok_worplanes) + ' пространствах.\r\n' + spaces_els_names_absent_WP_string
	#TaskDialog.Show('Выставить рабочие плоскости освещения', 'Рабочие плоскости освещения выставлены в ' + str(isok_worplanes) + ' пространствах.' + spaces_els_names_absent_WP_string)

	return exitstr

















# Данные для заполнения второй таблицы (с отсутствующими именами пространств)
# вытаскиваем все пространства из проекта
spaces_els = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_MEPSpaces).ToElements()


global Button_Cancel_for_Illumination_Values_Storage_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_for_Illumination_Values_Storage_pushed = 1


# Прогрессбар норм освещённости
# Заполняем лейбл
IlVal_label3Text = 'В модели найдено пространств: ' + str(len(spaces_els)) + '.'
if len(spaces_els) > 100: # если пространств больше 100 - вывести предупреждение, что их обработка может занять длительное время.
	IlVal_label3Text = IlVal_label3Text + '\nПостроение списка пространств для которых не найдены нормы освещённости\nможет занять много времени.'


# Основное окошко норм освещённости

class Illumination_Values_Storage_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._IlVal_dataGridView1 = System.Windows.Forms.DataGridView()
		self._IlVal_OK_button = System.Windows.Forms.Button()
		self._IlVal_Cancel_button = System.Windows.Forms.Button()
		self._IlVal_RefreshRooms_button = System.Windows.Forms.Button()
		self._IlVal_Export_button = System.Windows.Forms.Button()
		self._IlVal_RoomName_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_IlluminationNorm_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_WorkPlane_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_Explanation_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_label1 = System.Windows.Forms.Label()
		self._IlVal_dataGridView2 = System.Windows.Forms.DataGridView()
		self._IlVal_label2 = System.Windows.Forms.Label()
		self._IlVal_MissingRoomsNumbers_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_MissingRoomsNames_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IlVal_Save_button = System.Windows.Forms.Button()
		self._IlVal_Import_button = System.Windows.Forms.Button()
		self._IlVal_label3 = System.Windows.Forms.Label()
		self._IlVal_progressBar1 = System.Windows.Forms.ProgressBar()
		self._IlVal_WriteToSpaces_button = System.Windows.Forms.Button()
		self._IlVal_RewriteMissingSpaces_button = System.Windows.Forms.Button()
		self._IlVal_dataGridView1.BeginInit()
		self._IlVal_dataGridView2.BeginInit()
		self.SuspendLayout()
		# 
		# IlVal_dataGridView1
		# 
		self._IlVal_dataGridView1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._IlVal_dataGridView1.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._IlVal_RoomName_Column,
			self._IlVal_IlluminationNorm_Column,
			self._IlVal_WorkPlane_Column,
			self._IlVal_Explanation_Column]))
		self._IlVal_dataGridView1.Location = System.Drawing.Point(25, 142)
		self._IlVal_dataGridView1.Name = "IlVal_dataGridView1"
		self._IlVal_dataGridView1.RowTemplate.Height = 24
		self._IlVal_dataGridView1.Size = System.Drawing.Size(600, 386)
		self._IlVal_dataGridView1.TabIndex = 0
		# 
		# IlVal_OK_button
		# 
		self._IlVal_OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._IlVal_OK_button.Location = System.Drawing.Point(25, 619)
		self._IlVal_OK_button.Name = "IlVal_OK_button"
		self._IlVal_OK_button.Size = System.Drawing.Size(130, 23)
		self._IlVal_OK_button.TabIndex = 1
		self._IlVal_OK_button.Text = "Сохранить и закрыть"
		self._IlVal_OK_button.UseVisualStyleBackColor = True
		self._IlVal_OK_button.Click += self.IlVal_OK_buttonClick
		# 
		# IlVal_Cancel_button
		# 
		self._IlVal_Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_Cancel_button.Location = System.Drawing.Point(1158, 619)
		self._IlVal_Cancel_button.Name = "IlVal_Cancel_button"
		self._IlVal_Cancel_button.Size = System.Drawing.Size(75, 23)
		self._IlVal_Cancel_button.TabIndex = 2
		self._IlVal_Cancel_button.Text = "Cancel"
		self._IlVal_Cancel_button.UseVisualStyleBackColor = True
		self._IlVal_Cancel_button.Click += self.IlVal_Cancel_buttonClick
		# 
		# IlVal_RefreshRooms_button
		# 
		self._IlVal_RefreshRooms_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_RefreshRooms_button.Location = System.Drawing.Point(704, 14)
		self._IlVal_RefreshRooms_button.Name = "IlVal_RefreshRooms_button"
		self._IlVal_RefreshRooms_button.Size = System.Drawing.Size(130, 23)
		self._IlVal_RefreshRooms_button.TabIndex = 3
		self._IlVal_RefreshRooms_button.Text = "Обновить список"
		self._IlVal_RefreshRooms_button.UseVisualStyleBackColor = True
		self._IlVal_RefreshRooms_button.Click += self.IlVal_RefreshRooms_buttonClick
		# 
		# IlVal_Export_button
		# 
		self._IlVal_Export_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._IlVal_Export_button.Location = System.Drawing.Point(652, 619)
		self._IlVal_Export_button.Name = "IlVal_Export_button"
		self._IlVal_Export_button.Size = System.Drawing.Size(75, 23)
		self._IlVal_Export_button.TabIndex = 4
		self._IlVal_Export_button.Text = "Экспорт"
		self._IlVal_Export_button.UseVisualStyleBackColor = True
		self._IlVal_Export_button.Click += self.IlVal_Export_buttonClick
		# 
		# IlVal_RoomName_Column
		# 
		self._IlVal_RoomName_Column.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
		self._IlVal_RoomName_Column.HeaderText = "Помещения"
		self._IlVal_RoomName_Column.Name = "IlVal_RoomName_Column"
		self._IlVal_RoomName_Column.Width = 111
		# 
		# IlVal_IlluminationNorm_Column
		# 
		self._IlVal_IlluminationNorm_Column.HeaderText = "Нормируемая освещённость (Лк)"
		self._IlVal_IlluminationNorm_Column.Name = "IlVal_IlluminationNorm_Column"
		self._IlVal_IlluminationNorm_Column.Width = 90
		# 
		# IlVal_WorkPlane_Column
		# 
		self._IlVal_WorkPlane_Column.HeaderText = "Рабочая плоскость мм от у.ч.п."
		self._IlVal_WorkPlane_Column.Name = "IlVal_WorkPlane_Column"
		self._IlVal_WorkPlane_Column.Width = 80
		# 
		# IlVal_Explanation_Column
		# 
		self._IlVal_Explanation_Column.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.DisplayedCells
		self._IlVal_Explanation_Column.HeaderText = "Пояснение"
		self._IlVal_Explanation_Column.Name = "IlVal_Explanation_Column"
		self._IlVal_Explanation_Column.Width = 106
		# 
		# IlVal_label1
		# 
		self._IlVal_label1.Location = System.Drawing.Point(25, 14)
		self._IlVal_label1.Name = "IlVal_label1"
		self._IlVal_label1.Size = System.Drawing.Size(266, 34)
		self._IlVal_label1.TabIndex = 5
		self._IlVal_label1.Text = "Ниже представлены нормы освещённости для конкретных помещений"
		# 
		# IlVal_dataGridView2
		# 
		self._IlVal_dataGridView2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_dataGridView2.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._IlVal_dataGridView2.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._IlVal_MissingRoomsNumbers_Column,
			self._IlVal_MissingRoomsNames_Column]))
		self._IlVal_dataGridView2.Location = System.Drawing.Point(704, 142)
		self._IlVal_dataGridView2.Name = "IlVal_dataGridView2"
		self._IlVal_dataGridView2.RowTemplate.Height = 24
		self._IlVal_dataGridView2.Size = System.Drawing.Size(529, 385)
		self._IlVal_dataGridView2.TabIndex = 6
		# 
		# IlVal_label2
		# 
		self._IlVal_label2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_label2.Location = System.Drawing.Point(704, 49)
		self._IlVal_label2.Name = "IlVal_label2"
		self._IlVal_label2.Size = System.Drawing.Size(277, 90)
		self._IlVal_label2.TabIndex = 7
		self._IlVal_label2.Text = "Заполняется программно"
		# 
		# IlVal_MissingRoomsNumbers_Column
		# 
		self._IlVal_MissingRoomsNumbers_Column.HeaderText = "Номер отсутствующего помещения"
		self._IlVal_MissingRoomsNumbers_Column.Name = "IlVal_MissingRoomsNumbers_Column"
		# 
		# IlVal_MissingRoomsNames_Column
		# 
		self._IlVal_MissingRoomsNames_Column.HeaderText = "Имя отсутствующего помещения"
		self._IlVal_MissingRoomsNames_Column.Name = "IlVal_MissingRoomsNames_Column"
		self._IlVal_MissingRoomsNames_Column.Width = 300
		# 
		# IlVal_Save_button
		# 
		self._IlVal_Save_button.Location = System.Drawing.Point(495, 14)
		self._IlVal_Save_button.Name = "IlVal_Save_button"
		self._IlVal_Save_button.Size = System.Drawing.Size(130, 23)
		self._IlVal_Save_button.TabIndex = 8
		self._IlVal_Save_button.Text = "Сохранить таблицу"
		self._IlVal_Save_button.UseVisualStyleBackColor = True
		self._IlVal_Save_button.Click += self.IlVal_Save_buttonClick
		# 
		# IlVal_Import_button
		# 
		self._IlVal_Import_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._IlVal_Import_button.Location = System.Drawing.Point(550, 619)
		self._IlVal_Import_button.Name = "IlVal_Import_button"
		self._IlVal_Import_button.Size = System.Drawing.Size(75, 23)
		self._IlVal_Import_button.TabIndex = 9
		self._IlVal_Import_button.Text = "Импорт"
		self._IlVal_Import_button.UseVisualStyleBackColor = True
		self._IlVal_Import_button.Click += self.IlVal_Import_buttonClick
		# 
		# IlVal_label3
		# 
		self._IlVal_label3.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_label3.Location = System.Drawing.Point(991, 14)
		self._IlVal_label3.Name = "IlVal_label3"
		self._IlVal_label3.Size = System.Drawing.Size(253, 65)
		self._IlVal_label3.TabIndex = 10
		self._IlVal_label3.Text = "Заполняется программно"
		# 
		# IlVal_progressBar1
		# 
		self._IlVal_progressBar1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_progressBar1.Location = System.Drawing.Point(851, 14)
		self._IlVal_progressBar1.Name = "IlVal_progressBar1"
		self._IlVal_progressBar1.Size = System.Drawing.Size(130, 23)
		self._IlVal_progressBar1.TabIndex = 11
		# 
		# IlVal_WriteToSpaces_button
		# 
		self._IlVal_WriteToSpaces_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._IlVal_WriteToSpaces_button.Location = System.Drawing.Point(25, 543)
		self._IlVal_WriteToSpaces_button.Name = "IlVal_WriteToSpaces_button"
		self._IlVal_WriteToSpaces_button.Size = System.Drawing.Size(253, 51)
		self._IlVal_WriteToSpaces_button.TabIndex = 12
		self._IlVal_WriteToSpaces_button.Text = "Записать освещённости и рабочие плоскости в пространства"
		self._IlVal_WriteToSpaces_button.UseVisualStyleBackColor = True
		self._IlVal_WriteToSpaces_button.Click += self.IlVal_WriteToSpaces_buttonClick
		# 
		# IlVal_RewriteMissingSpaces_button
		# 
		self._IlVal_RewriteMissingSpaces_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._IlVal_RewriteMissingSpaces_button.Location = System.Drawing.Point(638, 257)
		self._IlVal_RewriteMissingSpaces_button.Name = "IlVal_RewriteMissingSpaces_button"
		self._IlVal_RewriteMissingSpaces_button.Size = System.Drawing.Size(55, 36)
		self._IlVal_RewriteMissingSpaces_button.TabIndex = 13
		self._IlVal_RewriteMissingSpaces_button.Text = "<<"
		self._IlVal_RewriteMissingSpaces_button.UseVisualStyleBackColor = True
		self._IlVal_RewriteMissingSpaces_button.Click += self.IlVal_RewriteMissingSpaces_buttonClick
		# 
		# Illumination_Values_Storage_Form
		# 
		self.ClientSize = System.Drawing.Size(1256, 659)
		self.Controls.Add(self._IlVal_RewriteMissingSpaces_button)
		self.Controls.Add(self._IlVal_WriteToSpaces_button)
		self.Controls.Add(self._IlVal_progressBar1)
		self.Controls.Add(self._IlVal_label3)
		self.Controls.Add(self._IlVal_Import_button)
		self.Controls.Add(self._IlVal_Save_button)
		self.Controls.Add(self._IlVal_label2)
		self.Controls.Add(self._IlVal_dataGridView2)
		self.Controls.Add(self._IlVal_label1)
		self.Controls.Add(self._IlVal_Export_button)
		self.Controls.Add(self._IlVal_RefreshRooms_button)
		self.Controls.Add(self._IlVal_Cancel_button)
		self.Controls.Add(self._IlVal_OK_button)
		self.Controls.Add(self._IlVal_dataGridView1)
		self.MinimumSize = System.Drawing.Size(1274, 706)
		self.Name = "Illumination_Values_Storage_Form"
		self.Text = "Нормы освещённости"
		self.Load += self.Illumination_Values_Storage_FormLoad
		self._IlVal_dataGridView1.EndInit()
		self._IlVal_dataGridView2.EndInit()
		self.ResumeLayout(False)

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def Illumination_Values_Storage_FormLoad(self, sender, e):
		# Когда в модели много пространств прога долго их обрабатывает. Нужно выводить для этого прогрессбар.
		self._IlVal_label3.Text = IlVal_label3Text
		self._IlVal_progressBar1.Maximum = len(spaces_els)
		self._IlVal_progressBar1.Step = 1

		# Заполняем таблицу норм освещённости данными
		a = 0 # счётчик
		while a < len(znach3):
			self._IlVal_dataGridView1.Rows.Add(znach3[a], znach3[a+1], znach3[a+2], znach3[a+3]) # Заполняем таблицу исходными данными
			a = a + 9
		self._IlVal_label2.Text = IlVal_label2_text # заполняем лэйбл


	def IlVal_RefreshRooms_buttonClick(self, sender, e):
		self._IlVal_progressBar1.Value = 0 # Обнуляем прогрессбар
		# сначала удаляем все строки
		a = self._IlVal_dataGridView2.Rows.Count-1
		while a > 0:
			self._IlVal_dataGridView2.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		# Переформировываем список отсутствующих пространств
		missing_spaces_numbers_and_names = [] # список отсутствующих в Хранилище пространств вида [номер пр-ва1, имя пр-ва1, номер пр-ва2, имя пр-ва2, ...] или ['1', 'Sup Space 1', '2', 'Sup space 2']
		for i in spaces_els:
			self._IlVal_progressBar1.PerformStep()
			for j in znach3:
				if GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString() not in znach3 and GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString() not in missing_spaces_numbers_and_names: # если имени помещения нет в Хранилище И такого имени ещё нет в missing_spaces_numbers_and_names
					missing_spaces_numbers_and_names.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NUMBER).AsString()) # Получаем номер пространства
					missing_spaces_numbers_and_names.append(GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString()) # Получаем имя пространства
		# Заполняем заново таблицу отсутствующих помещений
		a = 0 # счётчик
		while a < len(missing_spaces_numbers_and_names):
			self._IlVal_dataGridView2.Rows.Add(missing_spaces_numbers_and_names[a], missing_spaces_numbers_and_names[a+1]) # Заполняем таблицу исходными данными
			a = a + 2


	def IlVal_Export_buttonClick(self, sender, e):
		# Сохраняем настройки во внешний txt файл
		sfd = SaveFileDialog()
		sfd.Filter = "Text files(*.txt)|*.txt" #sfd.Filter = "Text files(*.txt)|*.txt|All files(*.*)|*.*"
		sfd.FileName = doc.Title + '_нормы_освещённости' # имя файла по умолчанию
		if (sfd.ShowDialog() == DialogResult.OK): # sfd.ShowDialog() # файл на сохранение
			filename = sfd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			System.IO.File.WriteAllText(filename, IlVal_Export(self._IlVal_dataGridView1))


	def IlVal_Import_buttonClick(self, sender, e):
		# Открываем файл для считывания данных
		ofd = OpenFileDialog() # <System.Windows.Forms.OpenFileDialog object at 0x000000000000002B [System.Windows.Forms.OpenFileDialog: Title: , FileName: ]>
		if (ofd.ShowDialog() == DialogResult.OK):
			filename = ofd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			fileText = System.IO.File.ReadAllText(filename)
			Imported_list = IlVal_Import(fileText) # [[u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52'], [u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53'], [u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55'], [u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56'], [u'вася', '123', '450', u'ппп'], [u'вапвыпа', '1', '44', ''], ['Sup Space 1', '12', '15', '']]			# сначала удаляем все строки
			# Проверим правильность данных в импортируемом списке:
			if len(Imported_list) > 0 and len(Imported_list[0]) == 4:
				a = self._IlVal_dataGridView1.Rows.Count-1
				while a > 0:
					self._IlVal_dataGridView1.Rows.RemoveAt(0) # сначала удаляем все строки
					a = a - 1
				# Заполняем таблицу норм освещённости данными
				for i in Imported_list:
					self._IlVal_dataGridView1.Rows.Add(i[0], i[1], i[2], i[3]) # Заполняем таблицу исходными данными
				TaskDialog.Show('Нормы освещённости', 'Данные успешно импортированы')
			else:
				TaskDialog.Show('Нормы освещённости', 'Не удалось импортировать данные. Файл импорта некорректен.')



	def IlVal_Save_buttonClick(self, sender, e):
		# Проверяем правильность введённых данных
		if IlVal_InputChecks (self._IlVal_dataGridView1) != '':
			TaskDialog.Show('Нормы освещённости', 'Данные НЕ сохранены! Проверьте правильность введённых данных.\n' + IlVal_InputChecks (self._IlVal_dataGridView1))
		else:
			try:
				# Забираем значения
				global IlVal_forsaveinwindow
				IlVal_forsaveinwindow = [] # Список вида [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '', u'вася', '233', '22', u'ййййй', '', '', '', '', '']
				for i in Take_IlluminationNormsDataFromWindow(self._IlVal_dataGridView1):
					if i == None: # None не должен попасть в список для записи в Хранилище
						IlVal_forsaveinwindow.append('') 
					else:
						IlVal_forsaveinwindow.append(i) 
				# Сохраняем значения в ES
				Wrtite_to_ExtensibleStorage (schemaGuid_for_Illumination_Values_Storage, ProjectInfoObject, FieldName_for_Illumination_Values_Storage, SchemaName_for_Illumination_Values_Storage, List[str](IlVal_forsaveinwindow)) # пишем данные в хранилище 
				# Сразу считываем их оттуда чтобы обновить список znach3
				sch3 = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)
				ent3 = ProjectInfoObject.GetEntity(sch3)
				field_Illumination_Values_Storage = sch3.GetField(FieldName_for_Illumination_Values_Storage)
				global znach3
				znach3 = ent3.Get[IList[str]](field_Illumination_Values_Storage)
				# пересоберём список чтобы привести его к нормальному виду
				CS_help = []
				[CS_help.append(i) for i in znach3]
				znach3 = []
				[znach3.append(i) for i in CS_help] # [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '']
				TaskDialog.Show('Нормы освещённости', 'Данные сохранены')
			except:
				TaskDialog.Show('Нормы освещённости', 'Данные НЕ сохранены! Что-то пошло не так. Попробуйте перезапустить Программу.')


	def IlVal_OK_buttonClick(self, sender, e):
		# Проверяем правильность введённых данных
		if IlVal_InputChecks (self._IlVal_dataGridView1) != '':
			TaskDialog.Show('Нормы освещённости', 'Данные НЕ сохранены! Проверьте правильность введённых данных.\n' + IlVal_InputChecks (self._IlVal_dataGridView1))
		else:
			try:
				# Забираем значения
				global IlVal_forsaveinwindow
				IlVal_forsaveinwindow = [] # Список вида [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '', u'вася', '233', '22', u'ййййй', '', '', '', '', '']
				for i in Take_IlluminationNormsDataFromWindow(self._IlVal_dataGridView1):
					if i == None: # None не должен попасть в список для записи в Хранилище
						IlVal_forsaveinwindow.append('') 
					else:
						IlVal_forsaveinwindow.append(i) 
				# Сохраняем значения в ES
				Wrtite_to_ExtensibleStorage (schemaGuid_for_Illumination_Values_Storage, ProjectInfoObject, FieldName_for_Illumination_Values_Storage, SchemaName_for_Illumination_Values_Storage, List[str](IlVal_forsaveinwindow)) # пишем данные в хранилище 
				# Сразу считываем их оттуда чтобы обновить список znach3
				sch3 = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)
				ent3 = ProjectInfoObject.GetEntity(sch3)
				field_Illumination_Values_Storage = sch3.GetField(FieldName_for_Illumination_Values_Storage)
				global znach3
				znach3 = ent3.Get[IList[str]](field_Illumination_Values_Storage) # выдаёт List[str](['a', 'list', 'of', 'strings'])
				# пересоберём список чтобы привести его к нормальному виду
				CS_help = []
				[CS_help.append(i) for i in znach3]
				znach3 = []
				[znach3.append(i) for i in CS_help] # [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '']
				self.Close()
			except:
				TaskDialog.Show('Нормы освещённости', 'Данные НЕ сохранены! Что-то пошло не так. Попробуйте перезапустить Программу.')		

	def IlVal_Cancel_buttonClick(self, sender, e):
		# Считываем список znach3 и переобъявляем его
		sch3 = Schema.Lookup(schemaGuid_for_Illumination_Values_Storage)
		ent3 = ProjectInfoObject.GetEntity(sch3)
		field_Illumination_Values_Storage = sch3.GetField(FieldName_for_Illumination_Values_Storage)
		global znach3
		znach3 = ent3.Get[IList[str]](field_Illumination_Values_Storage)
		# пересоберём список чтобы привести его к нормальному виду
		CS_help = []
		[CS_help.append(i) for i in znach3]
		znach3 = []
		[znach3.append(i) for i in CS_help] # [u'Раздевальная', '300', '0', u'СП 52.13330.2016, табл. Л.1, п.52', '', '', '', '', '', u'Групповая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Игральная', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.53', '', '', '', '', '', u'Столовая', '400', '0', u'СП 52.13330.2016, табл. Л.1, п.55', '', '', '', '', '', u'Спальная', '150', '0', u'СП 52.13330.2016, табл. Л.1, п.56', '', '', '', '', '']

		self.Close()


	def IlVal_WriteToSpaces_buttonClick(self, sender, e):
		# Проверяем правильность введённых данных
		global ara
		ara = IlVal_InputChecks (self._IlVal_dataGridView1)
		if IlVal_InputChecks (self._IlVal_dataGridView1) != '':
			TaskDialog.Show('Нормы освещённости', 'Данные НЕ сохранены! Проверьте правильность введённых данных.\n' + IlVal_InputChecks (self._IlVal_dataGridView1))
		else:
			# Прописывается без сохранения! Напрямую из таблицы!
			# Санчала предложим пользователю добавить необходимый параметр освещённости в пространства
			# Выходные оповещения пользователя (после запуска этой функции)
			#!!!!!!!!!!!!ТУТ С ГУИДОМ НАДО РАЗОБРАТЬСЯ. ЕСЛИ ПОЛЬЗОВАТЕЛЬ ХОЧЕТ ДОБАВИТЬ ПАРАМЕТР С ДРУГИМ ИМЕНЕМ НО ТЕМ ЖЕ ГУИДОМ, ТО КАКОЙ-ТО КОСЯК ВЫХОДИТ!!!!!!!!!!!!!!!!!!!!!!
			global addparam_result
			try: # для 2019 - 2024 Ревитов
				BuiltInParameter_Group = BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING
			except: # для 2025 ревита
				BuiltInParameter_Group = 'Нет такого метода в 2025 Ревите'
			addparam_result = Add_a_new_Param_to_Category ('TESLA', Param_Rated_Illuminance, BuiltInCategory.OST_MEPSpaces, BuiltInParameter_Group, 'c8de45ca-92dd-4b87-a09f-c3c6dc77b914')		
			if addparam_result == 0:
				TaskDialog.Show('Нормы освещённости', 'Без добавления параметра "' + Param_Rated_Illuminance + '" работа команды невозможна.')
			elif addparam_result == 1:
				TaskDialog.Show('Нормы освещённости', 'Не указан путь к файлу общих параметров (ФОП). Пожалуйста, укажите путь к ФОП на вкладке Управление и перезапустите команду.')
			elif addparam_result == 2:
				TaskDialog.Show('Нормы освещённости', 'В модели отсутствуют семейства пространств.\nРабота команды невозможна.')
			elif addparam_result == 3:
				global exit_str_WPandRI
				exit_str_WPandRI = IlluminationWorkPlaneSet(self._IlVal_dataGridView1, Param_Rated_Illuminance) # прописываем нормы освещённости и рабочие плоскости в пространства
				Illumination_WPandRA_AlertForm().ShowDialog()
			elif addparam_result == 4: # для 2019-2024 Ревитов можем добавить параметр нормируемой освещённости
				TaskDialog.Show('Нормы освещённости', 'Параметр "' + Param_Rated_Illuminance + '" был добавлен ко всем пространствам модели.')
				global exit_str_WPandRI
				exit_str_WPandRI = IlluminationWorkPlaneSet(self._IlVal_dataGridView1, Param_Rated_Illuminance) # прописываем нормы освещённости и рабочие плоскости в пространства
				Illumination_WPandRA_AlertForm().ShowDialog()
			elif addparam_result == 5:
				TaskDialog.Show('Нормы освещённости', 'Параметр "' + Param_Rated_Illuminance + '" уже пристутсвет в ФОП, но с другим типом данных.\nРабота команды невозможна.')
			elif addparam_result == 6: # для 2025 Ревита скажем чтобы пользователь сам добавил нужный параметр нормируемой освещённости
				TaskDialog.Show('Нормы освещённости', 'Параметр "' + Param_Rated_Illuminance + '" отсутствует у семейств пространств. Пожалуйста добавьте его самостоятельно, а затем перезапустите данное окно.')


	def IlVal_RewriteMissingSpaces_buttonClick(self, sender, e):
		Selected_cells = [i for i in self._IlVal_dataGridView2.SelectedCells] # список выбранных ячеек
		Selected_Rows_indexes = [i.RowIndex for i in Selected_cells] # список с номерами выбранных рядов
		for i in Selected_Rows_indexes:
			try:
				self._IlVal_dataGridView1.Rows.Add(self._IlVal_dataGridView2[1, i].Value) # Добавляем значения в таблицу
				self._IlVal_dataGridView2.Rows.RemoveAt(i) # Удаляем значения из таблицы
			except:
				pass



#i.append(self._CRF_Wires_dataGridView[n, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
#Illumination_Values_Storage_Form().ShowDialog()







































#_________________________________ Работаем с 7-м хранилищем (Пользовательские коэффициенты спроса) ____________________________________________________________________________




# Функция отрисовывает новую таблицу коэффициентов спроса
# На входе данные с формы: (зависит от количества электроприёмников? Удельный вес мощности в других нагрузках (%)?)
# На выходе кортеж: список со столбцами, количество строк, имя первой строки
# Пример обращения CreateTableKc(True, True)	
def CreateTableKc (EPcount, UnitDependentPwr):
	# Если у нас сложная таблица с удельным весом, то в ней изначально должно быть не менее 3 столбцов и 2 строк
	FirstColumsHeaderText = ''
	if UnitDependentPwr == True:
		columnscount = 3
		rowscount = 3
		# А название первого столбца должно содержать инфу об удельном весе в %
		FirstColumsHeaderText = 'Столбец 1. Удельный вес установленной мощности в других нагрузках (%)'
	else:
		columnscount = 2
		rowscount = 2

	# Название первой строки
	if EPcount == True: # если от количества электроприёмников
		if UnitDependentPwr == True:
			FirstRowCellText = 'Количество электроприёмников: (заполните далее эту строку)'
		else:
			FirstRowCellText = ''
		OtherColumnsHeaderTextSuffix = 'Число ЭП (в 1-й строке), значения Кс (в остальных строках)'
	else: # если от мощности электроприёмников
		if UnitDependentPwr == True:
			FirstRowCellText = 'Мощность электроприёмников (кВт): (заполните далее эту строку)'
		else:
			FirstRowCellText = ''
		OtherColumnsHeaderTextSuffix = 'Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)'

	ColumnsList = [] # выходной список столбцов
	for i in range(columnscount):
		New_Column = DataGridViewTextBoxColumn() # Создаём класс нового столбца (текстовый)
		# Задаём ему свойства:
		New_Column.Name = 'Column' + str(i + 1) # Имя нового столбца. 
		if i == 0 and FirstColumsHeaderText != '': # особое имя для 1-го столбца (если имеется)
			New_Column.HeaderText = FirstColumsHeaderText # Название нового столбца
		else:
			New_Column.HeaderText = 'Столбец ' + str(i + 1) + '. ' + OtherColumnsHeaderTextSuffix
		New_Column.SortMode = DataGridViewColumnSortMode.NotSortable
		ColumnsList.append(New_Column)

	return ColumnsList, rowscount, FirstRowCellText



# Функция по декодированию таблиц Кс пользовательских из Хранилища.
# На входе закодированная строка с таблицами Кс из Хранилища
# На выходе список списков с нормальными данными.
# Пример обращения UserKcTablesDecoding (znachKc)
def UserKcTablesDecoding (UserKcdatafromES):
	Exit_listoflists = [] # Выходной список
	for i in UserKcdatafromES:
		curtable = [] # текущая таблица Кс.
		Firstlevelsplit = i.split('@@!!@@') 
		for n, j in enumerate(Firstlevelsplit):
			if n <= 4:
				curtable.append(j)
			elif n == 11:
				Secondlevelsplit = j.split('$$>>$$') # разбиваем на строки 
				curcurelem = []
				for k in Secondlevelsplit:
					curcurelem.append(k.split('&&??&&'))
				curtable.append(curcurelem)
			else:
				curtable.append(j.split('&&??&&'))
		Exit_listoflists.append(curtable)
	return Exit_listoflists






# Функция проверки правильности введённых данных в окне пользовательских коэффициентов спроса.
# На входе проверяемые перменные, на выходе сообщение об ошибке если есть
# Пример обращения: UserKcFormCorreectCheck(DataFromUserKcForm[1], DataFromUserKcForm[2], DataFromUserKcForm[3], DataFromUserKcForm[4], znachKc, UserKcDataFromFormBeginEdit, DataFromUserKcForm[5], DataFromUserKcForm[0])
'''
Чтоб тестить: 
UserKcName = DataFromUserKcForm[1] # 'Кс.сан.тех.'
UnitDependentPwr = DataFromUserKcForm[2]
OtherPUnitDependent = DataFromUserKcForm[3]
AllCellsValues = DataFromUserKcForm[4]
KcDependsOnP = DataFromUserKcForm[5]
UserKcDataFromForm - это 'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Ру.сантех.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4'
DataFromUserKcForm - это (u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Ру.сантех.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4', u'Кс.сан.тех.', u'Зависит от уд.веса в других нагрузках', u'Ру (вся)', u'Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4', u'Ру.сантех.')
'''
def UserKcFormCorreectCheck (UserKcName, UnitDependentPwr, OtherPUnitDependent, AllCellsValues, znachKc, UserKcDataFromFormBeginEdit, KcDependsOnP, KcTableName):
	exit_string = ''
	if UserKcName == '':
		exit_string = exit_string + 'Не заполнено имя Кс'
	elif UnitDependentPwr == 'Зависит от уд.веса в других нагрузках' and OtherPUnitDependent == '':
		exit_string = exit_string + 'Не указаны другие нагрузки для расчёта удельной мощности'
	elif 'ПУСТАЯ_ЯЧЕЙКА' in AllCellsValues:
		exit_string = exit_string + 'Необходимо заполнить все ячейки в таблице значений Кс'
	elif AllCellsValues == '':
		exit_string = exit_string + 'Нужно сформировать и заполнить таблицу значений Кс'

	# Также проверим нет ли в хранилище уже Кс с таким именем
	if UserKcDataFromFormBeginEdit == '': # если форма открывалась на редактирование
		for i in znachKc:
			if i.split('@@!!@@')[2] == UserKcName:
				exit_string = exit_string + 'В Настройках уже есть коэффициент спроса с таким именем. Необходимо использовать коэффициенты с уникальными именами.'

	# И нет ли такого же описания Кс. 
	if UserKcDataFromFormBeginEdit == '': # если форма открывалась на редактирование
		for i in znachKc:
			if i.split('@@!!@@')[0] == KcTableName:
				exit_string = exit_string + 'В Настройках уже есть таблица с таким именем. Необходимо использовать уникальные имена (краткие описания) таблиц Кс.'
				break

	# Проверка на то что указано на какие мощности данный Кс влияет
	if KcDependsOnP == '': 
		exit_string = exit_string + 'Не указано на какие мощности влияет данный Кс.'

	# Проверка на то что в ячейках таблицы числа. Но кроме 0-го столбца, 0 ячейки если есть удельная зависимость.
	# AllCellsValues - '0,9&&??&&0.5$$>>$$qqq&&??&&33'
	readableAllCellsValues = [] # Вид: [[u'Количество электроприёмников:', '100', '84', '74', '49', '24'], ['2', '1', '1', '1', '1', '1'], ['3', '0.9', '1', '1', '1', '1'], ['5', '0.8', '0.75', '0.7', '0.65', '0.6'], ['8', '0.75', '0.7', '0.65', '0.6', '0.6'], ['10', '0.7', '0.65', '0.65', '0.6', '0.55'], ['15', '0.65', '0.6', '0.6', '0.55', '0.5'], ['20', '0.65', '0.6', '0.6', '0.5', '0.5'], ['30', '0.6', '0.6', '0.55', '0.5', '0.5'], ['50', '0.55', '0.55', '0.5', '0.5', '0.45'], ['100', '0.55', '0.55', '0.5', '0.45', '0.45'], ['200', '0.5', '0.5', '0.45', '0.45', '0.4']]
	NotFloat = 0
	for i in AllCellsValues.split('$$>>$$'): # ['0,9&&??&&0.5', 'qqq&&??&&33'] разбивка по строкам
		readableAllCellsValues.append(i.split('&&??&&'))
	readableAllCellsValues = map(list, zip(*readableAllCellsValues)) # транспонируем список (чтоб по столбцам были члены) [['0,9', 'qqq'], ['0.5', '33']]
	if UnitDependentPwr == 'Зависит от уд.веса в других нагрузках': # если так, то проверяем исключая самую первую ячейку
		for n, i in enumerate(readableAllCellsValues):
			for m, j in enumerate(i):
				if m > 0: # Самую первую ячейку не проверяем, т.к. в ней напдпись, а не цифра. Что-то вроде 'Количество электроприёмников:'.
					try:
						float(j)
					except:
						NotFloat = NotFloat + 1
	else:
		for n, i in enumerate(readableAllCellsValues):
			for j in i:
				try:
					float(j)
				except:
					NotFloat = NotFloat + 1
	if NotFloat > 0:
		exit_string = exit_string + 'Пустые ячейки в таблицах не допускаются. Вместо пустых значений допускается писать нули.\nВведённые Вами значения должны быть числами с разделителем целой и дробной частей в виде точки.\n(Кроме самой первой ячейки в случае если есть удельная зависимость Кс).'

	return exit_string




# Функция отрисовывает таблицу пользовательских Кс по входному списку с инфой
# На входе Selected_tableName - имя таблицы которую захотел показать пользователь; Readable_znachKc - список с инфой по всем пользовательским Кс
# Пример обращения: Fill_UserKc_Form('Введите имя таблицы', Readable_znachKc, self._KcName_textBox, self._EPcount_radioButton, self._EPpower_radioButton, self._UnitDependentPwr_checkBox, self._UnitDependentPwr_checkedListBox, UnitDependentPwrList, self._TableName_textBox, self._dataGridView1, self._LoadClassList_comboBox, self._KcDependsOnP_checkedListBox)
def Fill_UserKc_Form (Selected_tableName, Readable_znachKc, KcName_textBox, EPcount_radioButton, EPpower_radioButton, UnitDependentPwr_checkBox, UnitDependentPwr_checkedListBox, UnitDependentPwrList, TableName_textBox, dataGridView1, LoadClassList_comboBox, KcDependsOnP_checkedListBox):
	for i in Readable_znachKc:
		if Selected_tableName == i[0]:
			table_to_show = i # конкретная таблица которую будем показывать в форме пользовательских Кс. Вид: [u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин', u'Системы ОВ', u'Кс.сан.тех.', 'epcount', u'Зависит от уд.веса в других нагрузках', [u'Ру (вся)'], [u'Ру.мех.об.', u'Ру.ов', u'Ру.вк', u'Ру.холод.'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11', 'column12'], [u'Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84', '1', '1', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74', '1', '1', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49', '1', '1', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '1', '1', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]]
	# Начинаем заполнять
	KcName_textBox.Text = table_to_show[2]
	if table_to_show[3].upper() == 'EPcount'.upper():
		EPcount_radioButton.Checked = True
		EPpower_radioButton.Checked = False
	elif table_to_show[3].upper() == 'EPpower'.upper():
		EPcount_radioButton.Checked = False
		EPpower_radioButton.Checked = True
	if table_to_show[4] == 'Зависит от уд.веса в других нагрузках':
		UnitDependentPwr_checkBox.Checked = True
		curhlp = []
		for i in UnitDependentPwr_checkedListBox.Items:
			curhlp.append(i)
		for n, i in enumerate(curhlp):
			if i in table_to_show[5]: # [u'Ру (вся)', u'Рр (вся)']
				UnitDependentPwr_checkedListBox.SetItemChecked(n, True)
	TableName_textBox.Text = table_to_show[0]
	# Добавляем столбцы
	for n, i in enumerate(table_to_show[9]):
		New_Column = DataGridViewTextBoxColumn() # Создаём класс нового столбца (текстовый)
		# Задаём ему свойства:
		New_Column.Name = i # Имя нового столбца. 
		New_Column.HeaderText = table_to_show[10][n] # Название нового столбца
		New_Column.SortMode = DataGridViewColumnSortMode.NotSortable # Запрещаем сортировку
		dataGridView1.Columns.Add(New_Column)
	# Добавляем и заполняем строки
	dataGridView1.Rows.Add(len(table_to_show[11])) # Добавляем нужное количество строк в таблицу
	for n, i in enumerate(table_to_show[11]): # [[u'Количество электроприёмников: (заполните далее эту строку)', '1', '2'], ['3', '4', '5'], ['0', '0', '0']]
		a = 0
		while a < len(i): # число столбцов
			dataGridView1[a, n].Value = i[a] # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
			a = a + 1
	# Указываем класс нагрузок для данного Кс
	LoadClassList_comboBox.Text = table_to_show[1]
	# Заполняем на какие мощности влияет данный Кс
	curhlp = []
	for i in KcDependsOnP_checkedListBox.Items:
		curhlp.append(i)
	for n, i in enumerate(curhlp):
		if i in table_to_show[6]: # [u'Ру (вся)', u'Рр (вся)']
			KcDependsOnP_checkedListBox.SetItemChecked(n, True)
		


# Функция сбора данных с формы пользовательских Кс и кодирования их для записи в хранилище
# На входе состояние разных элементов формы
# На выходе кортеж необходимых переменных
# Обращение: EncodingData_form_UserKcForm(self._TableName_textBox.Text, self._LoadClassList_comboBox.SelectedItem, self._KcName_textBox.Text, self._EPcount_radioButton.Checked, self._UnitDependentPwr_checkBox.Checked, self._UnitDependentPwr_checkedListBox.CheckedItems, self._dataGridView1, self._KcDependsOnP_checkedListBox.CheckedItems)
def EncodingData_form_UserKcForm (TableName_Selected, LoadClassNameSelected, UserKcName, EPcount_radioButton_Checked, UnitDependentPwr_checkBox_Checked, UnitDependentPwr_checkedListBox_CheckedItems, dataGridView1, KcDependsOnP_checkedListBox_CheckedItems):
	# Собираем данные с формы и формируем их для подачи на команду сохранения
	#global TableName_Selected
	#TableName_Selected = self._TableName_textBox.Text
	#global LoadClassNameSelected
	#LoadClassNameSelected = self._LoadClassList_comboBox.SelectedItem # 'Аварийное освещение'
	#global UserKcName
	#UserKcName = self._KcName_textBox.Text # 'Кс.сантех'
	#global EPcountOrPower 
	EPcountOrPower = ''
	if EPcount_radioButton_Checked == True:
		EPcountOrPower = 'EPcount'
	else:
		EPcountOrPower = 'EPpower'
	# Себе проверка!
	if EPcountOrPower == '':
		TaskDialog.Show('Пользовательские Кс', 'Что-то не так с зависимостью от количества или мощности электроприёмников! Напишите разработчику!')
	#global UnitDependentPwr
	if UnitDependentPwr_checkBox_Checked == True:
		UnitDependentPwr = 'Зависит от уд.веса в других нагрузках'
	else:
		UnitDependentPwr = 'Не зависит от уд.веса в других нагрузках'
	#global OtherPUnitDependent
	OtherPUnitDependent = ''
	for i in UnitDependentPwr_checkedListBox_CheckedItems:
		OtherPUnitDependent = OtherPUnitDependent + i.ToString() + '&&??&&'
	OtherPUnitDependent = OtherPUnitDependent[0:-6] # 'Ру (вся)&&??&&Рр (вся)'
	#global InnerColumnsNames
	InnerColumnsNames = []
	#global VisibleColumnsNames
	VisibleColumnsNames = []
	for i in range(dataGridView1.Columns.Count):
		InnerColumnsNames.append(dataGridView1.Columns[i].Name) # ['Column1', 'Column2', 'Column3']
		VisibleColumnsNames.append(dataGridView1.Columns[i].HeaderText) # [u'Столбец 1. Удельный вес установленной мощности в других нагрузках (%)', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)']
	InnerColumnsNames = '&&??&&'.join(InnerColumnsNames) # 'Column1&&??&&Column2&&??&&Column3'
	VisibleColumnsNames = '&&??&&'.join(VisibleColumnsNames) # 'Столбец 1. Удельный вес установленной мощности в других нагрузках (%)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'
	#global AllCellsValues
	AllCellsValues = ''
	for i in range(dataGridView1.Rows.Count-1): # для каждой строки... 
		if i != 0:
			AllCellsValues = AllCellsValues[0:-6] # Выкидываем последний разделитель значений
			AllCellsValues = AllCellsValues + '$$>>$$' # вставляем разделитель строк
		for j in range(dataGridView1.ColumnCount): # для каждого столбца...
			if dataGridView1[j, i].Value != None:
				AllCellsValues = AllCellsValues + dataGridView1[j, i].Value + '&&??&&' # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
			else:
				AllCellsValues = AllCellsValues + 'ПУСТАЯ_ЯЧЕЙКА' + '&&??&&' # Такого варианта не будет, потом проверку на это накатил
	AllCellsValues = AllCellsValues[0:-6] # 'Количество электроприёмников: (заполните далее эту строку)&&??&&1&&??&&2$$>>$$3&&??&&4&&??&&5$$>>$$6&&??&&7&&??&&0'

	KcDependsOnP = '' # На какие мощности влияет данный Кс?
	for i in KcDependsOnP_checkedListBox_CheckedItems:
		KcDependsOnP = KcDependsOnP + i.ToString() + '&&??&&'
	KcDependsOnP = KcDependsOnP[0:-6] # 'Ру (вся)&&??&&Рр (вся)'

	# Итоговая строка со всей необходимой инфой по Кс для записи в хранилище
	#global UserKcDataFromForm
	UserKcDataFromForm = TableName_Selected + '@@!!@@' + LoadClassNameSelected + '@@!!@@' + UserKcName + '@@!!@@' + EPcountOrPower + '@@!!@@' + UnitDependentPwr + '@@!!@@' + OtherPUnitDependent + '@@!!@@' + KcDependsOnP + '@@!!@@' + 'Резерв 2' + '@@!!@@' + 'Резерв 3' + '@@!!@@' + InnerColumnsNames + '@@!!@@' + VisibleColumnsNames + '@@!!@@' + AllCellsValues
	return UserKcDataFromForm, UserKcName, UnitDependentPwr, OtherPUnitDependent, AllCellsValues, KcDependsOnP, TableName_Selected
'''
Вид и порядковые номера
0	['Имя таблицы', 											TableName_Selected
1	'Классификация нагрузок данного Кс', 						LoadClassNameSelected
2	'Имя нового Кс'												UserKcName
3	'От кол-ва или мощности ЭП зависит', 						EPcountOrPower
4	'Зависит ли от удельного веса в других нагрузках',			UnitDependentPwr
5	'От каких других мощностей зависит (при удельном весе)'		OtherPUnitDependent
6	'На какие мощности влияет данный Кс?'						KcDependsOnP
7	'Резервное поле 2'
8	'Резервное поле 3'
9	'Внутренние имена столбцов с разделителем '&&??&&'  '
10	'Видимые имена столбцов с разделителем '&&??&&'  '
11	'Содержание ячеек: 1 строка, в ней по порядку значения с разделителем '&&??&&'  , потом разделитель 2 строки $$>>$$ и далее её значения и т.д.']

@@!!@@ - Разделитель между членами этого списка 

Вид выходной строки UserKcDataFromForm:
'Введите имя таблицы@@!!@@Прочее@@!!@@Кс.сантех@@!!@@EPcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)&&??&&Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@Column1&&??&&Column2&&??&&Column3@@!!@@Столбец 1. Удельный вес установленной мощности в других нагрузках (%)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников: (заполните далее эту строку)&&??&&1&&??&&2$$>>$$3&&??&&4&&??&&5$$>>$$0&&??&&0&&??&&0'
'''













#_________Хранилище таблиц пользовательских коэффициентов спроса__________________

schemaGuid_for_UserKc = System.Guid(Guidstr_UserKc) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
schUserKc = Schema.Lookup(schemaGuid_for_UserKc)

# Данные по умолчанию
defaultKcdata = ['Таблица 7.6 - Коэффициенты спроса для рабочего освещения@@!!@@Рабочее освещение@@!!@@Кс.раб.осв.@@!!@@eppower@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.раб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@5&&??&&10&&??&&15&&??&&25&&??&&50&&??&&100&&??&&200&&??&&400&&??&&500$$>>$$1&&??&&0.95&&??&&0.9&&??&&0.85&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6', 
'Костыль для лифтов@@!!@@Лифты@@!!@@Кс.л.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.л@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&1$$>>$$1&&??&&1', 
'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков@@!!@@Термическая нагрузка@@!!@@Кс.терм.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.терм.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&60&&??&&100&&??&&120$$>>$$0.9&&??&&0.85&&??&&0.75&&??&&0.65&&??&&0.6&&??&&0.5&&??&&0.45&&??&&0.4&&??&&0.3&&??&&0.3&&??&&0.25', 
'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Ру.мех.об.&&??&&Ру.ов&&??&&Ру.вк&&??&&Ру.холод.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4', 
'Таблица 7.10 - Коэффициенты спроса для посудомоечных машин (от сети ХВС)@@!!@@Посудомоечные машины@@!!@@Кс.посудом.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.посудом.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&2&&??&&3$$>>$$1&&??&&0.9&&??&&0.85', 
'Таблица 7.8 - Коэффициенты спроса для силовых электрических сетей общественных зданий. (Для Руко- и полотенцесушителей)@@!!@@Полотенцесушители@@!!@@Кс.полот.суш.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.полот.суш.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@3&&??&&5$$>>$$0.4&&??&&0.15', 
'Таблица 7.7 - Расчетные коэффициенты спроса для розеток. (Групповые сети)@@!!@@Розетки бытовые@@!!@@Кс.роз.быт.техн.групп.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.роз.быт.&&??&&Ру.роз.техн.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&100$$>>$$1&&??&&1', 
'Таблица 7.7 - Расчетные коэффициенты спроса для розеток. (Питающие сети).@@!!@@Розетки бытовые@@!!@@Кс.роз.быт.техн.питающ.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.роз.быт.&&??&&Ру.роз.техн.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&100$$>>$$0.2&&??&&0.2', 
'Таблица 7.8 - Коэффициенты спроса для силовых электрических сетей общественных зданий. (Для компьютерных розеток как для Вычислительных машин (без технологического кондиционирования)).@@!!@@Розетки компьютерные@@!!@@Кс.роз.комп.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.роз.комп.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@3&&??&&5$$>>$$0.5&&??&&0.4']


UserKc_list_by_Default = List[str](defaultKcdata) 

# Проверяем корректность хранилища
if schUserKc is None or ProjectInfoObject.GetEntity(schUserKc).IsValid() == False:
	# Пишем инфу 
	Wrtite_to_ExtensibleStorage (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, UserKc_list_by_Default) # пишем данные в хранилище 

znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс 
# Вид: [[u'Таблица 7.6 - Коэффициенты спроса для рабочего освещения', u'Рабочее освещение', u'Кс.о.', 'epcount', u'Не зависит от уд.веса в других нагрузках', [''], [u'Рраб.осв.'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9'], [u'Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)'], [['5', '10', '15', '25', '50', '100', '200', '400', '500'], ['1', '0.8', '0.7', '0.6', '0.5', '0.4', '0.35', '0.3', '0.3']]], [u'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков', u'Тепловое оборудование пищеблоков', u'Кс.гор.пищ.', 'epcount', u'Не зависит от уд.веса в других нагрузках', [''], [u'Ргор.пищ.'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11'], [u'Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [['2', '3', '5', '8', '10', '15', '20', '30', '60', '100', '120'], ['0.9', '0.85', '0.75', '0.65', '0.6', '0.5', '0.45', '0.4', '0.3', '0.3', '0.25']]], [u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин', u'Системы ОВ', u'Кс.сан.тех.', 'epcount', u'Зависит от уд.веса в других нагрузках', [u'Ру (вся)'], [u'Рр.сантех.', u'Рр.ов'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11', 'column12'], [u'Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84', '0', '0', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74', '0', '0', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49', '0', '0', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '0', '0', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]]]



# классификации нагрузок
LoadClasses = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalLoadClassifications).ToElements()
LoadClassesNames = []
for i in LoadClasses:
	LoadClassesNames.append(i.Name)






#_________Пользовательские мощности______________________________________________________

# Функция декодирования значений мощностей Р в чиитаемый вид
# Обращение: UserPDecoding(znachP)
# На выходе: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
def UserPDecoding (znachP):
	Exit_listoflists = [] # Выходной список
	Firstlevelsplit = [j.split('@@!!@@') for j in znachP] # [[u'Ру (вся)', 'all', 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', 'all', 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', u'hvac&&??&&ОВК&&??&&Системы ВК&&??&&Системы ОВ', 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
	for i in Firstlevelsplit: # i это [u'Ру (вся)', 'all', 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3']
		curP = [] # Текущая мощность Р
		for n, j in enumerate(i):
			if n != 1:
				curP.append(j)
			else:
				curP.append(j.split('&&??&&'))
		Exit_listoflists.append(curP)
	return Exit_listoflists



schemaGuid_for_UserP = System.Guid(Guidstr_UserP) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
schUserP = Schema.Lookup(schemaGuid_for_UserP)

# Вот эти 'Ру (вся)', 'Рр (вся)' сделаем переменными, чтобы потом в коде на них ссылаться и переименовывать легко если надо
PyAll = 'Ру (вся)' # соответствующая ей особая классификация нагрузок: 'ALL'
PpAll = 'Рр (вся)' # 'ALL'
'''
'Ру (без классиф.)' # 'Нет классификации' или ''
'Рр (без классиф.)' # 'Нет классификации' или ''
'Ру (др. классиф.)' # 'OTHER'
'Рр (др. классиф.)' # 'OTHER'
'''




# Данные по умолчанию
'''
Мощности в хранилище будут кодироваться так:
0 - Имя мощности - 'Ру (вся)'
1 - Классификация нагрузок данной мощности - Для Ру и Рр особая моя классификация, вшитая и недоступная для редактирования. Называется 'ALL'
2 - Установленная или расчётная - 'Py' или 'Pp' ЛАТИНИЦЕЙ
3 - Резерв 1
4 - Резерв 2
5 - Резерв 3

@@!!@@ - Разделитель между членами этого списка 
Например: 'Ру (вся)@@!!@@ALL@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3'
'''

defaultPdata = ['Ру (вся)@@!!@@ALL@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (вся)@@!!@@ALL@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (др. классиф.)@@!!@@OTHER@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рр (др. классиф.)@@!!@@OTHER@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Ру.л@@!!@@Лифты@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Ру.раб.осв.@@!!@@Рабочее освещение@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.ав.осв.@@!!@@Аварийное освещение@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.мех.об.@@!!@@Механическое оборудование@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.посудом.@@!!@@Посудомоечные машины@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.полот.суш.@@!!@@Полотенцесушители@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.роз.быт.@@!!@@Розетки бытовые@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.роз.комп.@@!!@@Розетки компьютерные@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.роз.техн.@@!!@@Розетки технологические@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.ов@@!!@@Системы ОВ@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.вк@@!!@@Системы ВК@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.терм.@@!!@@Термическая нагрузка@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.холод.@@!!@@Холодильные установки@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.ппу@@!!@@Противопожарные системы@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру.щгп@@!!@@1 категория (не ППУ)@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']



UserP_list_by_Default = List[str](defaultPdata) 

# Проверяем корректность хранилища
if schUserP is None or ProjectInfoObject.GetEntity(schUserP).IsValid() == False:
	# Пишем инфу 
	Wrtite_to_ExtensibleStorage (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP, SchemaName_for_UserP, UserP_list_by_Default) # пишем данные в хранилище 

znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
# Вид: [u'Ру (вся)@@!!@@all@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр (вся)@@!!@@all@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
Readable_znachP = UserPDecoding(znachP) # Вид: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]


# Список с мощностями для комбобокса "В каких нагрузках"
# По умолчанию там будет только вся Ру и вся Рр.
UnitDependentPwrList = [] # Вид: ['Ру (вся)', 'Рр (вся)']
for i in Readable_znachP:
	UnitDependentPwrList.append(i[0]) 


# Функия по проверке и подготовке данных по мощности для записи в хранилище
# Пример обращения: UserPFormCorreectCheck(self._PName_textBox, self._Py_radioButton.Checked, self._Pp_radioButton.Checked, self._LoadClass_checkedListBox.CheckedItems, znachP, True)
def UserPFormCorreectCheck (PName_textBox, Py_radioButton_Checked, Pp_radioButton_Checked, LoadClass_checkedListBox_CheckedItems, znachP, checknameornot):
	ExitStr = '' # Вид: 'ppсантех@@!!@@hvac&&??&&ОВК@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3'
	ExitAlert = ''
	if PName_textBox.Text == '':
		ExitAlert = ExitAlert + 'Необходимо заполнить название мощности. '
	else:
		ExitStr = ExitStr + PName_textBox.Text + '@@!!@@'

	curel_hlp = ''
	for i in LoadClass_checkedListBox_CheckedItems:
		curel_hlp = curel_hlp + i.ToString() + '&&??&&' # разделитель элементов в списке
	if curel_hlp == '':
		ExitAlert = ExitAlert + 'Необходимо выбрать классификацию нагрузок. '
	else:
		ExitStr = ExitStr + curel_hlp[0:-6] + '@@!!@@'

	if Py_radioButton_Checked == False and Pp_radioButton_Checked == False:
		ExitAlert = ExitAlert + 'Необходимо выбрать Ру или Рр. '
	elif Py_radioButton_Checked == True:
		ExitStr = ExitStr + 'Py' + '@@!!@@'
	else:
		ExitStr = ExitStr + 'Pp' + '@@!!@@'

	ExitStr = ExitStr + 'Резерв 1' + '@@!!@@' + 'Резерв 2' + '@@!!@@' + 'Резерв 3'

	if checknameornot == True: # Даётся на входе: проверять совпадение имён мощностей в хранидище или нет?
		# Проверим что в хранилище ещё нет такой мощности
		for i in znachP:
			if i.split('@@!!@@')[0] == PName_textBox.Text: # 'Ру (вся)'
				ExitAlert = ExitAlert + 'В Настройках уже есть мощность с таким именем. Необходимо использовать мощности с уникальными именами.'

	if ExitAlert == '':
		return ExitStr
	else:
		TaskDialog.Show('Пользовательские Р', ExitAlert)
		ExitStr = ''
		return ExitStr




#_________Пользовательские формулы___________________________________

# Функция декодирования значений формул в чиитаемый вид
# Обращение: UserFormulaDecoding(znachUserFormula)
# На выходе: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]
def UserFormulaDecoding (znachUserFormula):
	Exit_listoflists = [] # Выходной список
	Firstlevelsplit = [j.split('@@!!@@') for j in znachUserFormula] # [[u'Расчёт Рр', u'Рр (вся)', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
	for i in Firstlevelsplit: 
		curP = [] # Текущая формула
		for n, j in enumerate(i):
			if n != 1:
				curP.append(j)
			else:
				curP.append(j.split('&&??&&'))
		Exit_listoflists.append(curP)
	return Exit_listoflists

# Тестим: znachUserFormula = ['Расчёт Рр@@!!@@Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 'Супер расчёт@@!!@@P1&&??&&+&&??&&Pss&&??&&*&&??&&Kcss&&??&&+&&??&&(&&??&&P2&&??&&+&&??&&Pqq&&??&&)&&??&&*&&??&&0.5@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']



schemaGuid_for_UserFormula = System.Guid(Guidstr_UserFormula) # Этот guid не менять! Он отвечает за ExtensibleStorage!

#Получаем Schema:
schUserFormula = Schema.Lookup(schemaGuid_for_UserFormula)

# Данные по умолчанию
'''
Формулы в хранилище будут кодироваться так:
0 - Имя формулы - 'Дет.садик'
1 - Сама формула в виде списка с отдельными членами. Типа такого: ['P1', '+', 'Pss', '*', 'Kcss', '+', '(', 'P2', '+', 'Pqq', ')', '*', '0.5']
2 - Резерв 1
3 - Резерв 2
4 - Резерв 3

@@!!@@ - Разделитель между членами этого списка 
Например: 'Дет.садик@@!!@@....
'''
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ДОБАВИТЬ КНОПКУ ПО УМОЛЧАНИЮ ДЛЯ КС Р И ФОРМУЛ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

defaultUserFormuladata = ['Рабочий (или аварийный) режим с Кс@@!!@@Ру.раб.осв.&&??&&*&&??&&Кс.раб.осв.&&??&&+&&??&&Ру.ав.осв.&&??&&+&&??&&Ру.л&&??&&*&&??&&Кс.л.&&??&&+&&??&&(&&??&&Ру.мех.об.&&??&&+&&??&&Ру.ов&&??&&+&&??&&Ру.вк&&??&&+&&??&&Ру.холод.&&??&&)&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру.посудом.&&??&&*&&??&&Кс.посудом.&&??&&+&&??&&Ру.полот.суш.&&??&&*&&??&&Кс.полот.суш.&&??&&+&&??&&(&&??&&Ру.роз.быт.&&??&&+&&??&&Ру.роз.техн.&&??&&)&&??&&*&&??&&Кс.роз.быт.техн.питающ.&&??&&+&&??&&Ру.роз.комп.&&??&&*&&??&&Кс.роз.комп.&&??&&+&&??&&Ру.терм.&&??&&*&&??&&Кс.терм.&&??&&+&&??&&Ру.щгп&&??&&+&&??&&Рр (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Режим "При пожаре" с Кс@@!!@@Ру.раб.осв.&&??&&*&&??&&Кс.раб.осв.&&??&&+&&??&&Ру.ав.осв.&&??&&+&&??&&Ру.л&&??&&*&&??&&Кс.л.&&??&&+&&??&&(&&??&&Ру.мех.об.&&??&&+&&??&&Ру.ов&&??&&+&&??&&Ру.вк&&??&&+&&??&&Ру.холод.&&??&&)&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру.посудом.&&??&&*&&??&&Кс.посудом.&&??&&+&&??&&Ру.полот.суш.&&??&&*&&??&&Кс.полот.суш.&&??&&+&&??&&(&&??&&Ру.роз.быт.&&??&&+&&??&&Ру.роз.техн.&&??&&)&&??&&*&&??&&Кс.роз.быт.техн.питающ.&&??&&+&&??&&Ру.роз.комп.&&??&&*&&??&&Кс.роз.комп.&&??&&+&&??&&Ру.терм.&&??&&*&&??&&Кс.терм.&&??&&+&&??&&Ру.щгп&&??&&+&&??&&Рр (без классиф.)&&??&&+&&??&&Ру.ппу@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']

UserFormula_list_by_Default = List[str](defaultUserFormuladata) 

# Проверяем корректность хранилища
if schUserFormula is None or ProjectInfoObject.GetEntity(schUserFormula).IsValid() == False:
	# Пишем инфу 
	Wrtite_to_ExtensibleStorage (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula, SchemaName_for_UserFormula, UserFormula_list_by_Default) # пишем данные в хранилище 

znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
# Вид: [u'Расчёт Рр@@!!@@Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Супер расчёт@@!!@@p1&&??&&+&&??&&pss&&??&&*&&??&&kcss&&??&&+&&??&&(&&??&&p2&&??&&+&&??&&pqq&&??&&)&&??&&*&&??&&0.5@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # Вид: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]

UserFormulaNamesList = [i[0] for i in Readable_znachUserFormula] # [u'Расчёт Рр']

# Функция по проверке формул на правильность синтаксиса
# На входе список с формулой, где каждый член - это переменная или матесатический знак. И список мат.символов.
# На выходе пустая строка если всё ок, сообщение об ошибке если не ок.
# Пример обращения: FormulaCheck ([u'Ру.раб.осв.', '*', u'Кс.о.', '+', u'Ру.гор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Ру.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру.л', '*', u'Кс.л.', '+', u'Рр (без классиф.)'], MathSymbolsList) 
def FormulaCheck (FormulaList, MathSymbolsList, Readable_znachP, Readable_znachKc):
	ExitAlertText = ''

	# 1) Проверка на возможность выполнения формулы.
	# Сначала надо всем буквам присвоить любые цифры какие-нибудь. Но только если это не мат. символы.
	# Чтоб тестить FormulaList = ['P1', '+', 'Pss', '*', 'Kcss', '+', '(', 'P2', '+', 'Pqq', ')', '*', '0.5']
	TestFormulaString = '' # формула в виде строки для проверки правильности. Например '2+3*4+(5+6)*7'. Результат 91
	a = 2 # случайная цифра для переменных
	for i in FormulaList:
		if i not in MathSymbolsList:
			TestFormulaString = TestFormulaString + str(a)
			a = a + 1
		else:
			TestFormulaString = TestFormulaString + i
	try:
		eval(TestFormulaString)
	except:
		ExitAlertText = ExitAlertText + 'Ошибка при составлении формулы. Проверьте пожалуйста формулу ещё раз.'

	# 2) Проверка чтобы в формуле не было двух и более мощностей, обслуживающих одну и ту же классификацию нагрузок
	# Составим список со всеми классификациями, которые обслуживаются формулой.
	FormulaLoadClasses = [] # [u'Рабочее освещение', u'Термическая нагрузка', u'ОВК', u'Системы ВК', u'Системы ОВ', u'Лифты', u'Нет классификации', '', 'all', 'hvac', u'ОВК', u'Системы ВК', u'Системы ОВ']
	for i in FormulaList:
		for j in Readable_znachP:
			if i == j[0]: # Если совпало имя мощности
				for k in j[1]:
					FormulaLoadClasses.append(k)
	# И теперь будем искать совпадения.
	FormulaLoadClasses_Copy = [i for i in FormulaLoadClasses]
	for i in FormulaLoadClasses_Copy:
		if FormulaLoadClasses.count(i) > 1: 
			ExitAlertText = ExitAlertText + 'В формуле присутствуют мощности которые обслуживают одинаковую классификацию нагрузок: "' + i + '". Каждая мощность в формуле должна обслуживать свой уникальный список классификаций, иначе расчёт будет некорректным. Необходимо убрать из формулы мощность, дублирующую указанную классификацию нагрузок.' 
			break
	for i in FormulaLoadClasses:
		if i == 'ALL' and len(FormulaLoadClasses) > 1: # также проверяем особый случай чтобы вся мощность была в формуле только если одна одинёшенька.
			ExitAlertText = ExitAlertText + 'Мощности "Ру (вся)" или "Рр (вся)" не могут находиться в одной формуле с другими мощностями. Это приведёт к дублированию уже учтённых формулой мощностей и расчёт будет некорректным.'

	# 3 ) Проверяем чтобы между Кс и Р всегда был бы какой-нибудь математический символ. Да и вообще чтобы Р или Кс не стояли подряд без мат.символов.
	KcAvailableNames = [] # список с доступными именами Кс. Вид: [u'Кс.л.', u'Кс.гор.пищ.', u'Кс.о.', u'Кс.сан.тех.']
	PAvailableNames = [] # список с доступными именами P. Вид: [u'Ру (вся)', u'Рр (вся)', u'Ру (без классиф.)', u'Рр (без классиф.)', u'Ру (др. классиф.)', u'Рр (др. классиф.)', u'Ру.л', u'Рр.сантех.', u'Рраб.осв.', u'Ргор.пищ.', u'Рр.ов', u'Ру.сантех.', u'Ру.раб.осв.', u'Ру.гор.пищ.', u'Руpeta']
	for i in Readable_znachKc:
		KcAvailableNames.append(i[2])
	for i in Readable_znachP:
		PAvailableNames.append(i[0])
	#if len(FormulaList) > 1: # Если в формуле всего одна мощность, то ничего проверять не надо
	for n, i in enumerate(FormulaList):
		if i in PAvailableNames or i in KcAvailableNames: # нашли какую-то мощность или Кс
			if n != 0 and n != len(FormulaList)-1: # Первый и последний не предлагать
				try: # Проверяем чего слева
					if FormulaList[n-1] in KcAvailableNames or FormulaList[n-1] in PAvailableNames:
						ExitAlertText = ExitAlertText + 'Перед мощностью "' + i + '" должен стоять математический символ.' 
						break
				except IndexError:
					pass
				try: # Проверяем чего справа
					if FormulaList[n+1] in KcAvailableNames or FormulaList[n+1] in PAvailableNames:
						ExitAlertText = ExitAlertText + 'После мощности "' + i + '" должен стоять математический символ.' 
						break
				except IndexError:
					pass

	# 4 ) Проверим чтобы в формуле не повторялись одни и те же Кс (да и названия мощностей тут же будут проверяться чтобы не повторялись)
	# FormulaList вид: [u'Pу.сан.тех', '*', u'Кс.сан.тех.', '+', u'Ру.роз.быт.', '*', u'Кс.роз.быт.техн.питающ.', '+', u'Ру.слаб.точ.сист.', '*', u'Кс.слаб.точ.сист.', '+', u'Pу.убор.тех.', '*', u'Kс.убор.тех.', '+', u'Ру.полот.суш.', '*', u'Кс.полот.суш.', '+', u'Pу.технол.оборуд.кроме пищебл.', '*', u'Кс.сан.тех.']
	FormulaList_Copy = [i for i in FormulaList]
	for i in FormulaList_Copy:
		if i not in MathSymbolsList:
			if FormulaList.count(i) > 1: 
				ExitAlertText = ExitAlertText + 'В формуле дублируются одни и те же коэффициенты спроса или мощности: "' + i + '". Все коэффициенты спроса и мощности, входящие в формулу должны быть уникальными и не повторяться.' 
				break

	return ExitAlertText


'''
FormulaList = ['Ру.раб.осв.', '*', 'Кс.о.', '+', 'Ру.гор.пищ.', '*', 'Кс.гор.пищ.', '+', 'Ру.сантех.', '*', 'Кс.сан.тех.', '+', 'Ру.л', '*', 'Кс.л.', '+', 'Рр (без классиф.)']
FormulaList = ['Ру.раб.осв.', '*', 'Кс.о.', '+', 'Ру.гор.пищ.', '*', 'Кс.гор.пищ.', '+', 'Ру.сантех.', '*', 'Кс.сан.тех.', '+', 'Ру.л', '*', 'Кс.л.', '+', 'Рр (без классиф.)', '+', 'Ру (вся)', '+', 'Рр.сантех.']
FormulaList = ['Ру.раб.осв.', '*', 'Кс.о.', '+', 'Ру.гор.пищ.', '*', 'Кс.гор.пищ.', '+', 'Ру.сантех.', 'Кс.сан.тех.', '+', 'Ру.л', '*', 'Кс.л.', '+', 'Рр (без классиф.)']

['+', '-', '*', '/', '(', ')']

[[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рр (вся)', ['all'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру (без классиф.)', [u'Нет классификации', ''], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рр (без классиф.)', [u'Нет классификации', ''], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру (др. классиф.)', ['other'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рр (др. классиф.)', ['other'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру.л', [u'Лифты'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рраб.осв.', [u'Рабочее освещение'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ргор.пищ.', [u'Тепловое оборудование пищеблоков'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Рр.ов', [u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру.сантех.', [u'ОВК', u'Системы ВК', u'Системы ОВ'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру.раб.осв.', [u'Рабочее освещение'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], 
[u'Ру.гор.пищ.', [u'Термическая нагрузка'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
'''



# Кодирует формулу для её записи в хранилище. Или удаления оттуда.
# На выходе срока в виде: 'Супер расчёт@@!!@@p1&&??&&+&&??&&pss&&??&&*&&??&&kcss&&??&&+&&??&&(&&??&&p2&&??&&+&&??&&pqq&&??&&)&&??&&*&&??&&0.5@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3'
# Пример обращения: EncodingFormula(FormulaName, FormulaList, 'Резерв 1', 'Резерв 2', 'Резерв 3')
def EncodingFormula (FormulaName, FormulaList, Reserve1, Reserve2, Reserve3):
	CodedFormulaDescriptionString = ''
	CodedFormulaDescriptionString = CodedFormulaDescriptionString + FormulaName + '@@!!@@'
	for i in FormulaList:
		CodedFormulaDescriptionString = CodedFormulaDescriptionString + i + '&&??&&'
	CodedFormulaDescriptionString = CodedFormulaDescriptionString[0:-6]
	CodedFormulaDescriptionString = CodedFormulaDescriptionString + '@@!!@@' + Reserve1 + '@@!!@@' + Reserve2 + '@@!!@@' + Reserve3
	return CodedFormulaDescriptionString





# Маркеры
IsOkPushed_UserKc = False # Ставим что Сохранить и закрыть не нажато
EnterUserKcShow = '' # Ставим что вход в окно пользовательских Кс изначально по кнопке "Создать". Если знаечение не пустая строка, то это значит, что вход был по кнопке "Показать"
UserKcDataFromFormBeginEdit = '' # Закодированный данные Кс открытого для редактирования. Вид: u'Васька сам@@!!@@Резервные@@!!@@Ксваська@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&2$$>>$$3&&??&&4'
PSelecet_SelectedItem = '' # Выбранная пользователем мощность
NewFormulaWasCreated = False # Создавалась новая формула? Или была отредактирована старая?


# Вшитые возможные математические символы
MathSymbolsList = ['+', '-', '*', '/', '(', ')']

# Для того чтоы всё было чики-пики, мы создадим виртуальный список, членами которого будут элементы формулы
# В него будем добавлять/удалять элементы и из него же заполнять строку предпросмотра. И его же потом проерять на правильность.
FormulaList = []




# Окошко новых мощностей (для Кс и расчётов)
class UserP(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Cancel_button = System.Windows.Forms.Button()
		self._SaveAndClose_button = System.Windows.Forms.Button()
		self._PName_textBox = System.Windows.Forms.TextBox()
		self._label1 = System.Windows.Forms.Label()
		self._LoadClass_checkedListBox = System.Windows.Forms.CheckedListBox()
		self._label2 = System.Windows.Forms.Label()
		self._Py_radioButton = System.Windows.Forms.RadioButton()
		self._Pp_radioButton = System.Windows.Forms.RadioButton()
		self._label3 = System.Windows.Forms.Label()
		self._Delete_button = System.Windows.Forms.Button()
		self.SuspendLayout()
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(313, 267)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 0
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# SaveAndClose_button
		# 
		self._SaveAndClose_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SaveAndClose_button.Location = System.Drawing.Point(12, 267)
		self._SaveAndClose_button.Name = "SaveAndClose_button"
		self._SaveAndClose_button.Size = System.Drawing.Size(158, 23)
		self._SaveAndClose_button.TabIndex = 1
		self._SaveAndClose_button.Text = "Сохранить и закрыть"
		self._SaveAndClose_button.UseVisualStyleBackColor = True
		self._SaveAndClose_button.Click += self.SaveAndClose_buttonClick
		# 
		# PName_textBox
		# 
		self._PName_textBox.Location = System.Drawing.Point(12, 59)
		self._PName_textBox.Name = "PName_textBox"
		self._PName_textBox.Size = System.Drawing.Size(100, 22)
		self._PName_textBox.TabIndex = 2
		# 
		# label1
		# 
		self._label1.Location = System.Drawing.Point(13, 13)
		self._label1.Name = "label1"
		self._label1.Size = System.Drawing.Size(157, 41)
		self._label1.TabIndex = 3
		self._label1.Text = "Введите название новой мощности"
		# 
		# LoadClass_checkedListBox
		# 
		self._LoadClass_checkedListBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._LoadClass_checkedListBox.FormattingEnabled = True
		self._LoadClass_checkedListBox.Location = System.Drawing.Point(171, 74)
		self._LoadClass_checkedListBox.Name = "LoadClass_checkedListBox"
		self._LoadClass_checkedListBox.Size = System.Drawing.Size(217, 174)
		self._LoadClass_checkedListBox.TabIndex = 4
		# 
		# label2
		# 
		self._label2.Location = System.Drawing.Point(171, 13)
		self._label2.Name = "label2"
		self._label2.Size = System.Drawing.Size(229, 58)
		self._label2.TabIndex = 5
		self._label2.Text = "К каким классификациям нагрузок относится данная мощность?"
		# 
		# Py_radioButton
		# 
		self._Py_radioButton.Location = System.Drawing.Point(13, 181)
		self._Py_radioButton.Name = "Py_radioButton"
		self._Py_radioButton.Size = System.Drawing.Size(104, 24)
		self._Py_radioButton.TabIndex = 6
		self._Py_radioButton.TabStop = True
		self._Py_radioButton.Text = "Ру"
		self._Py_radioButton.UseVisualStyleBackColor = True
		# 
		# Pp_radioButton
		# 
		self._Pp_radioButton.Location = System.Drawing.Point(13, 211)
		self._Pp_radioButton.Name = "Pp_radioButton"
		self._Pp_radioButton.Size = System.Drawing.Size(104, 24)
		self._Pp_radioButton.TabIndex = 7
		self._Pp_radioButton.TabStop = True
		self._Pp_radioButton.Text = "Рр"
		self._Pp_radioButton.UseVisualStyleBackColor = True
		# 
		# label3
		# 
		self._label3.Location = System.Drawing.Point(13, 105)
		self._label3.Name = "label3"
		self._label3.Size = System.Drawing.Size(152, 73)
		self._label3.TabIndex = 8
		self._label3.Text = "Собирать со схем установленную или расчётную мощность?"
		# 
		# Delete_button
		# 
		self._Delete_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Delete_button.Location = System.Drawing.Point(207, 267)
		self._Delete_button.Name = "Delete_button"
		self._Delete_button.Size = System.Drawing.Size(75, 23)
		self._Delete_button.TabIndex = 9
		self._Delete_button.Text = "Удалить"
		self._Delete_button.UseVisualStyleBackColor = True
		self._Delete_button.Click += self.Delete_buttonClick
		# 
		# UserP
		# 
		self.ClientSize = System.Drawing.Size(412, 302)
		self.Controls.Add(self._Delete_button)
		self.Controls.Add(self._label3)
		self.Controls.Add(self._Pp_radioButton)
		self.Controls.Add(self._Py_radioButton)
		self.Controls.Add(self._label2)
		self.Controls.Add(self._LoadClass_checkedListBox)
		self.Controls.Add(self._label1)
		self.Controls.Add(self._PName_textBox)
		self.Controls.Add(self._SaveAndClose_button)
		self.Controls.Add(self._Cancel_button)
		self.MinimumSize = System.Drawing.Size(430, 349)
		self.Name = "UserP"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Мощность"
		self.Load += self.UserPLoad
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy


	def UserPLoad(self, sender, e):
		self._LoadClass_checkedListBox.DataSource = LoadClassesNames 
		self._Delete_button.Enabled = False
		# Если мощность открывалась на редактирование, то заполним и другие поля.
		if PSelecet_SelectedItem != '':
			znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
			Readable_znachP = UserPDecoding(znachP) # Вид: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
			self._PName_textBox.Text = PSelecet_SelectedItem
			self._PName_textBox.Enabled = False
			self._Delete_button.Enabled = True
			global PSelecet_SelectedItem
			PSelecet_SelectedItem = '' # Обнуляем маркер
			# Заполняем окошко
			# Readable_znachP # [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
			# Если пользователь хочет посмотрть вшитые Ру и Рр (вся), то засерим вообще всё.
			if self._PName_textBox.Text.upper() == PyAll.upper() or self._PName_textBox.Text.upper() == PpAll.upper():
				if self._PName_textBox.Text.upper() == PpAll.upper():
					self._Pp_radioButton.Checked = True
				else:
					self._Py_radioButton.Checked = True
				self._Py_radioButton.Enabled = False
				self._Pp_radioButton.Enabled = False
				for n, i in enumerate(LoadClassesNames):
					self._LoadClass_checkedListBox.SetItemChecked(n, True) # Проставляем вообще все флажки
				self._LoadClass_checkedListBox.Enabled = False
				self._SaveAndClose_button.Enabled = False
				self._Delete_button.Enabled = False
			elif self._PName_textBox.Text == 'Ру (без классиф.)' or self._PName_textBox.Text == 'Рр (без классиф.)' or self._PName_textBox.Text == 'Ру (др. классиф.)' or self._PName_textBox.Text == 'Рр (др. классиф.)':
				if self._PName_textBox.Text == 'Ру (без классиф.)' or self._PName_textBox.Text == 'Ру (др. классиф.)':
					self._Py_radioButton.Checked = True
				else:
					self._Pp_radioButton.Checked = True
				self._Py_radioButton.Enabled = False
				self._Pp_radioButton.Enabled = False
				self._LoadClass_checkedListBox.Enabled = False
				self._SaveAndClose_button.Enabled = False
				self._Delete_button.Enabled = False
				curhlp = []
				for i in self._LoadClass_checkedListBox.Items:
					curhlp.append(i) # [u'Прочее', u'Мощность', u'Освещение', 'hvac', u'Двигатель', u'Резервная', u'Квартиры', u'Лифты', u'Силовые цепи', u'ОВК', u'Резервные', u'Аварийное освещение', u'НКУ', u'Подъёмные механизмы', u'Полотенцесушители', u'Посудомоечные машины', u'Розетки', u'Системы ВК', u'Системы ОВ', u'Термическая нагрузка', u'Холодильные установки', u'ЭВМ', u'Нет классификации', u'Рабочее освещение', u'Розетки бытовые', u'Розетки компьютерные', u'Розетки технологические', u'Механическое оборудование', u'Апартаменты', u'Офисы']
				for n, i in enumerate(curhlp):
					if i == 'Нет классификации':
						self._LoadClass_checkedListBox.SetItemChecked(n, True) 
			elif self._PName_textBox.Text == 'Ру.л':
				self._Py_radioButton.Checked = True
				self._Py_radioButton.Enabled = False
				self._Pp_radioButton.Enabled = False
				self._LoadClass_checkedListBox.Enabled = False
				self._SaveAndClose_button.Enabled = False
				self._Delete_button.Enabled = False
				curhlp = []
				for i in self._LoadClass_checkedListBox.Items:
					curhlp.append(i) # [u'Прочее', u'Мощность', u'Освещение', 'hvac', u'Двигатель', u'Резервная', u'Квартиры', u'Лифты', u'Силовые цепи', u'ОВК', u'Резервные', u'Аварийное освещение', u'НКУ', u'Подъёмные механизмы', u'Полотенцесушители', u'Посудомоечные машины', u'Розетки', u'Системы ВК', u'Системы ОВ', u'Термическая нагрузка', u'Холодильные установки', u'ЭВМ', u'Нет классификации', u'Рабочее освещение', u'Розетки бытовые', u'Розетки компьютерные', u'Розетки технологические', u'Механическое оборудование', u'Апартаменты', u'Офисы']
				for n, i in enumerate(curhlp):
					if i == 'Лифты':
						self._LoadClass_checkedListBox.SetItemChecked(n, True) 
			else:
				# Заполняем форму
				curhlp = []
				for i in self._LoadClass_checkedListBox.Items:
					curhlp.append(i) # [u'Прочее', u'Мощность', u'Освещение', 'hvac', u'Двигатель', u'Резервная', u'Квартиры', u'Лифты', u'Силовые цепи', u'ОВК', u'Резервные', u'Аварийное освещение', u'НКУ', u'Подъёмные механизмы', u'Полотенцесушители', u'Посудомоечные машины', u'Розетки', u'Системы ВК', u'Системы ОВ', u'Термическая нагрузка', u'Холодильные установки', u'ЭВМ', u'Нет классификации', u'Рабочее освещение', u'Розетки бытовые', u'Розетки компьютерные', u'Розетки технологические', u'Механическое оборудование', u'Апартаменты', u'Офисы']
				for i in Readable_znachP:
					if i[0] == self._PName_textBox.Text:
						for n, j in enumerate(curhlp):
							if j in i[1]: # [u'Ру (вся)', u'Рр (вся)']
								self._LoadClass_checkedListBox.SetItemChecked(n, True)
						if i[2].upper() == 'Pp'.upper():
							self._Pp_radioButton.Checked = True
						else:
							self._Py_radioButton.Checked = True
						break
			global Exit_P_BeginEdit # текущее состояние Р чтобы потом её удалить и перезаписать новую, т.к. открыто на редактирование
			Exit_P_BeginEdit = UserPFormCorreectCheck(self._PName_textBox, self._Py_radioButton.Checked, self._Pp_radioButton.Checked, self._LoadClass_checkedListBox.CheckedItems, znachP, False)


	def SaveAndClose_buttonClick(self, sender, e):
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища # Вид: [u'Ру (вся)@@!!@@all@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр (вся)@@!!@@all@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
		if self._PName_textBox.Enabled == True: # если делали новую мощность
			# Проверяем и формируем данные для записи новой мощности в Хранилище
			# global Exit_P # Вид: 'ppсантех@@!!@@hvac&&??&&ОВК@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3'
			Exit_P = UserPFormCorreectCheck(self._PName_textBox, self._Py_radioButton.Checked, self._Pp_radioButton.Checked, self._LoadClass_checkedListBox.CheckedItems, znachP, True)
			if Exit_P != '':
				znachP.append(Exit_P)
				Wrtite_to_ExtensibleStorage (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP, SchemaName_for_UserP, znachP) # пишем данные в хранилище 
				self.Close()
		else: # если открывали на редактирование существующую мощность Exit_P_BeginEdit
			# Удаляем эту строку (инфу об этом Кс) из списка данных
			znach_hlp = [] # Вспомогательный список для перезаписи в хранилище. Будет без удалённого элемента.
			for i in znachP:
				if i.split('@@!!@@')[0] != self._PName_textBox.Text: # Сравниваем по именам Р
					znach_hlp.append(i)
			Exit_P = UserPFormCorreectCheck(self._PName_textBox, self._Py_radioButton.Checked, self._Pp_radioButton.Checked, self._LoadClass_checkedListBox.CheckedItems, znach_hlp, False)
			if Exit_P != '':
				znach_hlp.append(Exit_P)
				Wrtite_to_ExtensibleStorage (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP, SchemaName_for_UserP, znach_hlp) # пишем данные в хранилище 
				self.Close()

	def Delete_buttonClick(self, sender, e):
		# Сначала убедимся что данная мощность не входит ни в одну формулу
		# Считываем актуальные данные по Кс и формулам.
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP)
		znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula)
		Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], ['test count', [u'Ру.раб.осв.', '*', u'Кс.о.', '+', u'Ру.гор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Ру.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру.л', '*', u'Кс.л.', '+', u'Рр (без классиф.)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Расчёт Ру', [u'Р
		hlp_lst = [] # Вспомогательный список. Останется пустым если данная мощность не входит ни в одну формулу. Или же в него попадут имена формул в которые входит данная мощность.
		for n, i in enumerate(Readable_znachUserFormula):
			if self._PName_textBox.Text not in i[1]:
				pass
			else:
				hlp_lst.append(i[0]) # Добавляем имя формулы в которую входит данная мощность
		if hlp_lst != []:
			TaskDialog.Show('Пользовательские мощности', 'Данную мощность невозможно удалить, т.к. она участвует в следующих формулах: ' + ', '.join(hlp_lst))
		else:
			deletequestionstring = 'Удалить мощность?'
			# Проверим не входит ли данная мощность в какой-нибудь Кс
			znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
			Readable_znachKc = UserKcTablesDecoding(znachKc) 
			hlp_lst = [] # Вспомогательный список. Останется пустым если данная мощность не входит ни в один Кс.
			for n, i in enumerate(Readable_znachKc):
				if self._PName_textBox.Text not in i[6]:
					pass
				else:
					hlp_lst.append(i[2]) # Добавляем имя Кс в который входит данная мощность
			if hlp_lst != []:
				deletequestionstring = 'Данная мощность входит в следующие коэффициенты спроса: ' + ', '.join(hlp_lst) + '. Вы уверены что хотите её удалить?'
			# Спросим уверен ли пользователь
			td = TaskDialog('Удаление мощности')
			td.MainContent = deletequestionstring
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Данная мощность будет полностью удалена.')
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
			GetUserResult = td.Show()
			if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
				znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
				znach_hlp = [] # Вспомогательный список для перезаписи в хранилище. Будет без удалённого элемента.
				for i in znachP:
					if i.split('@@!!@@')[0] != self._PName_textBox.Text: # Сравниваем по именам Р
						znach_hlp.append(i)
				Wrtite_to_ExtensibleStorage (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP, SchemaName_for_UserP, znach_hlp) # пишем данные в хранилище 
				self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()















# Окошко создания и переименования столбцов

class DB_Rename_Add_Column_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Enter_Column_Name_textBox = System.Windows.Forms.TextBox()
		self._Enter_Column_Name_label = System.Windows.Forms.Label()
		self._OK_button_DB_Rename_Add_Column = System.Windows.Forms.Button()
		self._Cancel_button_DB_Rename_Add_Column = System.Windows.Forms.Button()
		self.SuspendLayout()
		# 
		# Enter_Column_Name_textBox
		# 
		self._Enter_Column_Name_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Enter_Column_Name_textBox.Location = System.Drawing.Point(13, 36)
		self._Enter_Column_Name_textBox.Multiline = True
		self._Enter_Column_Name_textBox.Name = "Enter_Column_Name_textBox"
		self._Enter_Column_Name_textBox.Size = System.Drawing.Size(216, 72)
		self._Enter_Column_Name_textBox.TabIndex = 0
		# 
		# Enter_Column_Name_label
		# 
		self._Enter_Column_Name_label.Location = System.Drawing.Point(13, 10)
		self._Enter_Column_Name_label.Name = "Enter_Column_Name_label"
		self._Enter_Column_Name_label.Size = System.Drawing.Size(155, 23)
		self._Enter_Column_Name_label.TabIndex = 1
		self._Enter_Column_Name_label.Text = "Введите имя столбца:"
		# 
		# OK_button_DB_Rename_Add_Column
		# 
		self._OK_button_DB_Rename_Add_Column.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_button_DB_Rename_Add_Column.Location = System.Drawing.Point(12, 161)
		self._OK_button_DB_Rename_Add_Column.MinimumSize = System.Drawing.Size(75, 23)
		self._OK_button_DB_Rename_Add_Column.Name = "OK_button_DB_Rename_Add_Column"
		self._OK_button_DB_Rename_Add_Column.Size = System.Drawing.Size(75, 23)
		self._OK_button_DB_Rename_Add_Column.TabIndex = 2
		self._OK_button_DB_Rename_Add_Column.Text = "OK"
		self._OK_button_DB_Rename_Add_Column.UseVisualStyleBackColor = True
		self._OK_button_DB_Rename_Add_Column.Click += self.OK_button_DB_Rename_Add_ColumnClick
		# 
		# Cancel_button_DB_Rename_Add_Column
		# 
		self._Cancel_button_DB_Rename_Add_Column.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button_DB_Rename_Add_Column.Location = System.Drawing.Point(154, 161)
		self._Cancel_button_DB_Rename_Add_Column.Name = "Cancel_button_DB_Rename_Add_Column"
		self._Cancel_button_DB_Rename_Add_Column.Size = System.Drawing.Size(75, 23)
		self._Cancel_button_DB_Rename_Add_Column.TabIndex = 3
		self._Cancel_button_DB_Rename_Add_Column.Text = "Cancel"
		self._Cancel_button_DB_Rename_Add_Column.UseVisualStyleBackColor = True
		self._Cancel_button_DB_Rename_Add_Column.Click += self.Cancel_button_DB_Rename_Add_ColumnClick
		# 
		# DB_Rename_Add_Column_Form
		# 
		self.ClientSize = System.Drawing.Size(247, 196)
		self.Controls.Add(self._Cancel_button_DB_Rename_Add_Column)
		self.Controls.Add(self._OK_button_DB_Rename_Add_Column)
		self.Controls.Add(self._Enter_Column_Name_label)
		self.Controls.Add(self._Enter_Column_Name_textBox)
		self.MinimumSize = System.Drawing.Size(265, 243)
		self.Name = "DB_Rename_Add_Column_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Введите имя столбца"
		self.Load += self.DB_Rename_Add_Column_FormLoad
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy

	def DB_Rename_Add_Column_FormLoad(self, sender, e):
		self._Enter_Column_Name_textBox.Text = Old_Column_Name

	def OK_button_DB_Rename_Add_ColumnClick(self, sender, e):
		global DB_Rename_Add_Column_Form_Answer # Ответ Да или Нет в формате True или False
		DB_Rename_Add_Column_Form_Answer = True
		global New_Column_Name
		New_Column_Name = self._Enter_Column_Name_textBox.Text # новое имя столбца (или имя нового столбца)
		self.Close()

	def Cancel_button_DB_Rename_Add_ColumnClick(self, sender, e):
		global DB_Rename_Add_Column_Form_Answer # Ответ Да или Нет в формате True или False
		DB_Rename_Add_Column_Form_Answer = False
		self.Close()




















# Форма для создания новых мощностей и пользовательских Кс 

class UserKcForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Cancel_button = System.Windows.Forms.Button()
		self._OKsave_button = System.Windows.Forms.Button()
		self._Kc_groupBox = System.Windows.Forms.GroupBox()
		self._label5 = System.Windows.Forms.Label()
		self._EPpower_radioButton = System.Windows.Forms.RadioButton()
		self._EPcount_radioButton = System.Windows.Forms.RadioButton()
		self._label6 = System.Windows.Forms.Label()
		self._KcName_textBox = System.Windows.Forms.TextBox()
		self._UnitDependentPwr_checkBox = System.Windows.Forms.CheckBox()
		self._label4 = System.Windows.Forms.Label()
		self._UnitDependentPwr_checkedListBox = System.Windows.Forms.CheckedListBox()
		self._CreateTable_groupBox = System.Windows.Forms.GroupBox()
		self._CreateTable_button = System.Windows.Forms.Button()
		self._dataGridView1 = System.Windows.Forms.DataGridView()
		self._RenameColumn_button = System.Windows.Forms.Button()
		self._AddColumn_button = System.Windows.Forms.Button()
		self._DeleteColumn_button = System.Windows.Forms.Button()
		self._ClearTable_button = System.Windows.Forms.Button()
		self._TableName_textBox = System.Windows.Forms.TextBox()
		self._LoadClassList_comboBox = System.Windows.Forms.ComboBox()
		self._label3 = System.Windows.Forms.Label()
		self._DeleteKc_button = System.Windows.Forms.Button()
		self._label1 = System.Windows.Forms.Label()
		self._KcDependsOnP_checkedListBox = System.Windows.Forms.CheckedListBox()
		self._label2 = System.Windows.Forms.Label()
		self._Kc_groupBox.SuspendLayout()
		self._CreateTable_groupBox.SuspendLayout()
		self._dataGridView1.BeginInit()
		self.SuspendLayout()
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(838, 756)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 0
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# OKsave_button
		# 
		self._OKsave_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OKsave_button.Location = System.Drawing.Point(27, 756)
		self._OKsave_button.Name = "OKsave_button"
		self._OKsave_button.Size = System.Drawing.Size(157, 23)
		self._OKsave_button.TabIndex = 1
		self._OKsave_button.Text = "Сохранить и закрыть"
		self._OKsave_button.UseVisualStyleBackColor = True
		self._OKsave_button.Click += self.OKsave_buttonClick
		# 
		# Kc_groupBox
		# 
		self._Kc_groupBox.Controls.Add(self._KcDependsOnP_checkedListBox)
		self._Kc_groupBox.Controls.Add(self._label1)
		self._Kc_groupBox.Controls.Add(self._LoadClassList_comboBox)
		self._Kc_groupBox.Controls.Add(self._label3)
		self._Kc_groupBox.Controls.Add(self._UnitDependentPwr_checkedListBox)
		self._Kc_groupBox.Controls.Add(self._label4)
		self._Kc_groupBox.Controls.Add(self._UnitDependentPwr_checkBox)
		self._Kc_groupBox.Controls.Add(self._label5)
		self._Kc_groupBox.Controls.Add(self._EPpower_radioButton)
		self._Kc_groupBox.Controls.Add(self._EPcount_radioButton)
		self._Kc_groupBox.Controls.Add(self._label6)
		self._Kc_groupBox.Controls.Add(self._KcName_textBox)
		self._Kc_groupBox.Location = System.Drawing.Point(27, 12)
		self._Kc_groupBox.Name = "Kc_groupBox"
		self._Kc_groupBox.Size = System.Drawing.Size(886, 251)
		self._Kc_groupBox.TabIndex = 7
		self._Kc_groupBox.TabStop = False
		self._Kc_groupBox.Text = "Коэффициент спроса"
		# 
		# label5
		# 
		self._label5.Location = System.Drawing.Point(253, 18)
		self._label5.Name = "label5"
		self._label5.Size = System.Drawing.Size(120, 22)
		self._label5.TabIndex = 4
		self._label5.Text = "Зависит от:"
		# 
		# EPpower_radioButton
		# 
		self._EPpower_radioButton.Location = System.Drawing.Point(253, 81)
		self._EPpower_radioButton.Name = "EPpower_radioButton"
		self._EPpower_radioButton.Size = System.Drawing.Size(168, 39)
		self._EPpower_radioButton.TabIndex = 3
		self._EPpower_radioButton.TabStop = True
		self._EPpower_radioButton.Text = "Мощности электроприёмников"
		self._EPpower_radioButton.UseVisualStyleBackColor = True
		# 
		# EPcount_radioButton
		# 
		self._EPcount_radioButton.Location = System.Drawing.Point(253, 43)
		self._EPcount_radioButton.Name = "EPcount_radioButton"
		self._EPcount_radioButton.Size = System.Drawing.Size(161, 41)
		self._EPcount_radioButton.TabIndex = 2
		self._EPcount_radioButton.TabStop = True
		self._EPcount_radioButton.Text = "Количества электроприёмников"
		self._EPcount_radioButton.UseVisualStyleBackColor = True
		# 
		# label6
		# 
		self._label6.Location = System.Drawing.Point(6, 23)
		self._label6.Name = "label6"
		self._label6.Size = System.Drawing.Size(156, 34)
		self._label6.TabIndex = 1
		self._label6.Text = "Введите название нового Кс"
		# 
		# KcName_textBox
		# 
		self._KcName_textBox.Location = System.Drawing.Point(6, 63)
		self._KcName_textBox.Name = "KcName_textBox"
		self._KcName_textBox.Size = System.Drawing.Size(100, 22)
		self._KcName_textBox.TabIndex = 0
		# 
		# UnitDependentPwr_checkBox
		# 
		self._UnitDependentPwr_checkBox.Location = System.Drawing.Point(253, 129)
		self._UnitDependentPwr_checkBox.Name = "UnitDependentPwr_checkBox"
		self._UnitDependentPwr_checkBox.Size = System.Drawing.Size(164, 63)
		self._UnitDependentPwr_checkBox.TabIndex = 5
		self._UnitDependentPwr_checkBox.Text = "Удельный вес мощности в других нагрузках (%)"
		self._UnitDependentPwr_checkBox.UseVisualStyleBackColor = True
		self._UnitDependentPwr_checkBox.CheckedChanged += self.UnitDependentPwr_checkBoxCheckedChanged
		# 
		# label4
		# 
		self._label4.Location = System.Drawing.Point(420, 129)
		self._label4.Name = "label4"
		self._label4.Size = System.Drawing.Size(172, 24)
		self._label4.TabIndex = 8
		self._label4.Text = "В каких нагрузках?"
		# 
		# UnitDependentPwr_checkedListBox
		# 
		self._UnitDependentPwr_checkedListBox.FormattingEnabled = True
		self._UnitDependentPwr_checkedListBox.Location = System.Drawing.Point(420, 156)
		self._UnitDependentPwr_checkedListBox.Name = "UnitDependentPwr_checkedListBox"
		self._UnitDependentPwr_checkedListBox.Size = System.Drawing.Size(254, 89)
		self._UnitDependentPwr_checkedListBox.TabIndex = 9
		# 
		# CreateTable_groupBox
		# 
		self._CreateTable_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._CreateTable_groupBox.Controls.Add(self._label2)
		self._CreateTable_groupBox.Controls.Add(self._DeleteKc_button)
		self._CreateTable_groupBox.Controls.Add(self._TableName_textBox)
		self._CreateTable_groupBox.Controls.Add(self._ClearTable_button)
		self._CreateTable_groupBox.Controls.Add(self._DeleteColumn_button)
		self._CreateTable_groupBox.Controls.Add(self._AddColumn_button)
		self._CreateTable_groupBox.Controls.Add(self._RenameColumn_button)
		self._CreateTable_groupBox.Controls.Add(self._dataGridView1)
		self._CreateTable_groupBox.Controls.Add(self._CreateTable_button)
		self._CreateTable_groupBox.Location = System.Drawing.Point(27, 278)
		self._CreateTable_groupBox.Name = "CreateTable_groupBox"
		self._CreateTable_groupBox.Size = System.Drawing.Size(883, 472)
		self._CreateTable_groupBox.TabIndex = 8
		self._CreateTable_groupBox.TabStop = False
		self._CreateTable_groupBox.Text = "Сформировать таблицу коэффициентов спроса"
		# 
		# CreateTable_button
		# 
		self._CreateTable_button.Location = System.Drawing.Point(7, 97)
		self._CreateTable_button.Name = "CreateTable_button"
		self._CreateTable_button.Size = System.Drawing.Size(124, 43)
		self._CreateTable_button.TabIndex = 0
		self._CreateTable_button.Text = "Сформировать таблицу Кс"
		self._CreateTable_button.UseVisualStyleBackColor = True
		self._CreateTable_button.Click += self.CreateTable_buttonClick
		# 
		# dataGridView1
		# 
		self._dataGridView1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._dataGridView1.Location = System.Drawing.Point(7, 149)
		self._dataGridView1.Name = "dataGridView1"
		self._dataGridView1.RowTemplate.Height = 24
		self._dataGridView1.Size = System.Drawing.Size(857, 317)
		self._dataGridView1.TabIndex = 1
		# 
		# RenameColumn_button
		# 
		self._RenameColumn_button.Location = System.Drawing.Point(148, 97)
		self._RenameColumn_button.Name = "RenameColumn_button"
		self._RenameColumn_button.Size = System.Drawing.Size(124, 43)
		self._RenameColumn_button.TabIndex = 2
		self._RenameColumn_button.Text = "Переименовать столбец"
		self._RenameColumn_button.UseVisualStyleBackColor = True
		self._RenameColumn_button.Click += self.RenameColumn_buttonClick
		# 
		# AddColumn_button
		# 
		self._AddColumn_button.Location = System.Drawing.Point(287, 97)
		self._AddColumn_button.Name = "AddColumn_button"
		self._AddColumn_button.Size = System.Drawing.Size(124, 43)
		self._AddColumn_button.TabIndex = 3
		self._AddColumn_button.Text = "Добавить столбец"
		self._AddColumn_button.UseVisualStyleBackColor = True
		self._AddColumn_button.Click += self.AddColumn_buttonClick
		# 
		# DeleteColumn_button
		# 
		self._DeleteColumn_button.Location = System.Drawing.Point(427, 97)
		self._DeleteColumn_button.Name = "DeleteColumn_button"
		self._DeleteColumn_button.Size = System.Drawing.Size(124, 43)
		self._DeleteColumn_button.TabIndex = 4
		self._DeleteColumn_button.Text = "Удалить столбец"
		self._DeleteColumn_button.UseVisualStyleBackColor = True
		self._DeleteColumn_button.Click += self.DeleteColumn_buttonClick
		# 
		# ClearTable_button
		# 
		self._ClearTable_button.Location = System.Drawing.Point(567, 97)
		self._ClearTable_button.Name = "ClearTable_button"
		self._ClearTable_button.Size = System.Drawing.Size(124, 43)
		self._ClearTable_button.TabIndex = 5
		self._ClearTable_button.Text = "Очистить таблицу"
		self._ClearTable_button.UseVisualStyleBackColor = True
		self._ClearTable_button.Click += self.ClearTable_buttonClick
		# 
		# TableName_textBox
		# 
		self._TableName_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._TableName_textBox.Location = System.Drawing.Point(10, 21)
		self._TableName_textBox.Multiline = True
		self._TableName_textBox.Name = "TableName_textBox"
		self._TableName_textBox.Size = System.Drawing.Size(541, 70)
		self._TableName_textBox.TabIndex = 6
		self._TableName_textBox.Text = "Введите имя таблицы"
		# 
		# LoadClassList_comboBox
		# 
		self._LoadClassList_comboBox.FormattingEnabled = True
		self._LoadClassList_comboBox.Location = System.Drawing.Point(692, 96)
		self._LoadClassList_comboBox.Name = "LoadClassList_comboBox"
		self._LoadClassList_comboBox.Size = System.Drawing.Size(172, 24)
		self._LoadClassList_comboBox.TabIndex = 5
		# 
		# label3
		# 
		self._label3.Location = System.Drawing.Point(692, 23)
		self._label3.Name = "label3"
		self._label3.Size = System.Drawing.Size(172, 70)
		self._label3.TabIndex = 6
		self._label3.Text = "К какой классификации нагрузок относится Кс? (Справочно. Не влияет на расчёты)"
		# 
		# DeleteKc_button
		# 
		self._DeleteKc_button.Location = System.Drawing.Point(706, 97)
		self._DeleteKc_button.Name = "DeleteKc_button"
		self._DeleteKc_button.Size = System.Drawing.Size(124, 43)
		self._DeleteKc_button.TabIndex = 7
		self._DeleteKc_button.Text = "Удалить данный Кс"
		self._DeleteKc_button.UseVisualStyleBackColor = True
		self._DeleteKc_button.Click += self.DeleteKc_buttonClick
		# 
		# label1
		# 
		self._label1.Location = System.Drawing.Point(6, 92)
		self._label1.Name = "label1"
		self._label1.Size = System.Drawing.Size(172, 45)
		self._label1.TabIndex = 10
		self._label1.Text = "На какие мощности влияет данный Кс?"
		# 
		# KcDependsOnP_checkedListBox
		# 
		self._KcDependsOnP_checkedListBox.FormattingEnabled = True
		self._KcDependsOnP_checkedListBox.Location = System.Drawing.Point(10, 140)
		self._KcDependsOnP_checkedListBox.Name = "KcDependsOnP_checkedListBox"
		self._KcDependsOnP_checkedListBox.Size = System.Drawing.Size(225, 106)
		self._KcDependsOnP_checkedListBox.TabIndex = 11
		# 
		# label2
		# 
		self._label2.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._label2.Location = System.Drawing.Point(567, 46)
		self._label2.Name = "label2"
		self._label2.Size = System.Drawing.Size(246, 20)
		self._label2.TabIndex = 12
		self._label2.Text = "Имя таблицы (краткое описание)."
		# 
		# UserKcForm
		# 
		self.ClientSize = System.Drawing.Size(946, 791)
		self.Controls.Add(self._CreateTable_groupBox)
		self.Controls.Add(self._Kc_groupBox)
		self.Controls.Add(self._OKsave_button)
		self.Controls.Add(self._Cancel_button)
		self.MinimumSize = System.Drawing.Size(964, 814)
		self.Name = "UserKcForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Рр и Кс"
		self.Load += self.UserKcFormLoad
		self._Kc_groupBox.ResumeLayout(False)
		self._Kc_groupBox.PerformLayout()
		self._CreateTable_groupBox.ResumeLayout(False)
		self._CreateTable_groupBox.PerformLayout()
		self._dataGridView1.EndInit()
		self.ResumeLayout(False)

		self.Icon = iconmy


	def UserKcFormLoad(self, sender, e):
		self._LoadClassList_comboBox.DataSource = LoadClassesNames # Заполняем имена классификации нагрузок
		#self._EPcount_radioButton.Checked = True
		self._DeleteKc_button.Enabled = False
		# Обновим списки с мощностями
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
		Readable_znachP = UserPDecoding(znachP) # Вид: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		UnitDependentPwrList = [] # Вид: ['Ру (вся)', 'Рр (вся)']
		for i in Readable_znachP:
			UnitDependentPwrList.append(i[0]) 
		self._UnitDependentPwr_checkedListBox.DataSource = UnitDependentPwrList # Заполняем Рр для удельного веса мощностей
		self._UnitDependentPwr_checkedListBox.Enabled = False # засереваем его по умолчанию
		self._KcDependsOnP_checkedListBox.DataSource = UnitDependentPwrList # Заполняем от каких мощностей зависит данный Кс
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс
		# Далее нужно понять как пользователь попал в это окно. Если он открыл Кс на редактирование, то заполнять будем форму данными из хранилища.
		# А также нужно запомнить какой он собственно Кс открыл на редактирование. Т.к. он может всё в нём поменять, а его потом нужно пересохранить.
		if EnterUserKcShow != '':
			self._UnitDependentPwr_checkedListBox.DataSource = UnitDependentPwrList # Заполняем Рр для удельного веса мощностей
			self._KcDependsOnP_checkedListBox.DataSource = UnitDependentPwrList # Заполняем от каких мощностей зависит данный Кс
			Fill_UserKc_Form(EnterUserKcShow, Readable_znachKc, self._KcName_textBox, self._EPcount_radioButton, self._EPpower_radioButton, self._UnitDependentPwr_checkBox, self._UnitDependentPwr_checkedListBox, UnitDependentPwrList, self._TableName_textBox, self._dataGridView1, self._LoadClassList_comboBox, self._KcDependsOnP_checkedListBox)
			DataFromUserKcFormBeginEdit = EncodingData_form_UserKcForm(self._TableName_textBox.Text, self._LoadClassList_comboBox.SelectedItem, self._KcName_textBox.Text, self._EPcount_radioButton.Checked, self._UnitDependentPwr_checkBox.Checked, self._UnitDependentPwr_checkedListBox.CheckedItems, self._dataGridView1, self._KcDependsOnP_checkedListBox.CheckedItems)
			global UserKcDataFromFormBeginEdit # Закодированный данные Кс открытого для редактирования. Чтоб потом его перезаписать можно было.
			UserKcDataFromFormBeginEdit = DataFromUserKcFormBeginEdit[0]
			# И потом от греха засереваем настройки. Чтобы не было ошибок при сохранении.
			self._KcName_textBox.Enabled = False
			#self._EPcount_radioButton.Enabled = False
			#self._EPpower_radioButton.Enabled = False
			self._UnitDependentPwr_checkBox.Enabled = False
			self._CreateTable_button.Enabled = False
			if self._UnitDependentPwr_checkBox.Checked == True:
				self._UnitDependentPwr_checkedListBox.Enabled = True
			self._DeleteKc_button.Enabled = True
			# И сразу обнуляем метку перехода между окнами
			global EnterUserKcShow
			EnterUserKcShow = ''

	def UnitDependentPwr_checkBoxCheckedChanged(self, sender, e):
		if self._UnitDependentPwr_checkBox.Checked == True:
			self._UnitDependentPwr_checkedListBox.Enabled = True
		else:
			self._UnitDependentPwr_checkedListBox.Enabled = False

	def CreateTable_buttonClick(self, sender, e):
		# Формируем заготовок таблицы
		InitResult = CreateTableKc(self._EPcount_radioButton.Checked, self._UnitDependentPwr_checkBox.Checked)	
		for i in range(len(InitResult[0])):
			self._dataGridView1.Columns.Add(InitResult[0][i]) # добавляем столбцы
		self._dataGridView1.Rows.Add(InitResult[1])
		self._dataGridView1[0, 0].Value = InitResult[2] # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		# И потом от греха засереваем настройки. Чтобы не было ошибок при сохранении.
		#self._KcName_textBox.Enabled = False
		self._EPcount_radioButton.Enabled = False
		self._EPpower_radioButton.Enabled = False
		self._UnitDependentPwr_checkBox.Enabled = False
		self._CreateTable_button.Enabled = False
		self._UnitDependentPwr_checkedListBox.Enabled = False

	def RenameColumn_buttonClick(self, sender, e):
		Current_Column_index = self._dataGridView1.CurrentCellAddress.X # Индекс текущего столбца. Получается из Адреса текущей ячейки в виде <System.Drawing.Point object at 0x0000000000000233 [{X=1,Y=0}]> Где X - номер столбца, Y - номер строки
		global Old_Column_Name 
		Old_Column_Name = ''
		Old_Column_Name = self._dataGridView1.Columns[Current_Column_index].HeaderText # Старое имя столбца
		global DB_Rename_Add_Column_Form_Answer
		DB_Rename_Add_Column_Form_Answer = False # Обнуляем ответ. Потому что иначе может остаться неправильное значение ответа если пользователь закроет окно по крестику.
		DB_Rename_Add_Column_Form().ShowDialog()
		if DB_Rename_Add_Column_Form_Answer == True:
			self._dataGridView1.Columns[Current_Column_index].HeaderText = New_Column_Name # Переименование текущего столбца. 

	def AddColumn_buttonClick(self, sender, e):
		global Old_Column_Name 
		Old_Column_Name = ''
		global DB_Rename_Add_Column_Form_Answer
		DB_Rename_Add_Column_Form_Answer = False # Обнуляем ответ. Потому что иначе может остаться неправильное значение ответа если пользователь закроет окно по крестику.
		DB_Rename_Add_Column_Form().ShowDialog()
		if DB_Rename_Add_Column_Form_Answer == True:
			New_Column = DataGridViewTextBoxColumn() # Создаём класс нового столбца (текстовый)
			# Задаём ему свойства:
			New_Column.Name = 'Column' + str(self._dataGridView1.ColumnCount + 1) # Имя нового столбца. )
			New_Column.HeaderText = New_Column_Name # Название нового столбца
			self._dataGridView1.Columns.Add(New_Column)


	def DeleteColumn_buttonClick(self, sender, e):
		Current_Column_index = self._dataGridView1.CurrentCellAddress.X # Индекс текущего столбца.
		Current_Column_Name = self._dataGridView1.Columns[Current_Column_index].HeaderText # Имя текущего столбца
		# Спросим уверен ли пользователь
		td = TaskDialog('Удаление столбца')
		td.MainContent = 'Удалить столбец?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Столбец: "'+Current_Column_Name+'" будет удалён.')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			self._dataGridView1.Columns.RemoveAt(Current_Column_index)

	def ClearTable_buttonClick(self, sender, e):
		# Потом очищаем dataGridView
		for i in list(reversed(range(self._dataGridView1.Rows.Count-1))):
			self._dataGridView1.Rows.RemoveAt(i) # сначала удаляем все строки
		for i in list(reversed(range(self._dataGridView1.Columns.Count))):
			self._dataGridView1.Columns.RemoveAt(i) # потом удаляем все столбцы
		# Включаем элементы управления
		#self._KcName_textBox.Enabled = True
		self._EPcount_radioButton.Enabled = True
		self._EPpower_radioButton.Enabled = True
		self._UnitDependentPwr_checkBox.Enabled = True
		self._CreateTable_button.Enabled = True
		self._UnitDependentPwr_checkedListBox.Enabled = True

	def DeleteKc_buttonClick(self, sender, e):
		# Сначала убедимся что данный Кс не входит ни в одну формулу
		# Считываем актуальные данные по Кс и формулам.
		znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc)
		#Readable_znachKc = UserKcTablesDecoding(znachKc) # Вид: [[u'Костыль для лифтов', u'Лифты', u'Кс.л.', 'epcount', u'Не за
		znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula)
		Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], ['test count', [u'Ру.раб.осв.', '*', u'Кс.о.', '+', u'Ру.гор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Ру.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру.л', '*', u'Кс.л.', '+', u'Рр (без классиф.)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Расчёт Ру', [u'Р
		hlp_lst = [] # Вспомогательный список. Останется пустым если данный Кс не входит ни в одну формулу. Или же в него попадут имена формул в которые входит данный Кс.
		for n, i in enumerate(Readable_znachUserFormula):
			if self._KcName_textBox.Text not in i[1]:
				pass
			else:
				hlp_lst.append(i[0]) # Добавляем имя формулы в которую входит данный Кс
		if hlp_lst != []:
			TaskDialog.Show('Пользовательские Кс', 'Данный Кс невозможно удлить, т.к. он участвует в следующих формулах: ' + ', '.join(hlp_lst))
		else:
			# Спросим уверен ли пользователь
			td = TaskDialog('Удаление Кс')
			td.MainContent = 'Удалить все данные по текущему Кс?'
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Текущий Кс будет полностью удалён.')
			td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
			GetUserResult = td.Show()
			if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
				# Собираем данные с формы
				DataFromUserKcForm = EncodingData_form_UserKcForm(self._TableName_textBox.Text, self._LoadClassList_comboBox.SelectedItem, self._KcName_textBox.Text, self._EPcount_radioButton.Checked, self._UnitDependentPwr_checkBox.Checked, self._UnitDependentPwr_checkedListBox.CheckedItems, self._dataGridView1, self._KcDependsOnP_checkedListBox.CheckedItems)
				UserKcDataFromForm = DataFromUserKcForm[0]
				# Удаляем эту строку (инфу об этом Кс) из списка данных
				znach_hlp = [] # Вспомогательный список для перезаписи в хранилище. Будет без удалённого элемента.
				for i in znachKc:
					#if UserKcDataFromForm != i: было так раньше
					if UserKcDataFromForm.split('@@!!@@')[2] != i.split('@@!!@@')[2]: # Сравниваем по именам Кс:
						znach_hlp.append(i)
				Wrtite_to_ExtensibleStorage(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, List[str](znach_hlp) )
				global IsOkPushed_UserKc
				IsOkPushed_UserKc = True
				self.Close()


	def OKsave_buttonClick(self, sender, e):
		znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		#global DataFromUserKcForm
		DataFromUserKcForm = EncodingData_form_UserKcForm(self._TableName_textBox.Text, self._LoadClassList_comboBox.SelectedItem, self._KcName_textBox.Text, self._EPcount_radioButton.Checked, self._UnitDependentPwr_checkBox.Checked, self._UnitDependentPwr_checkedListBox.CheckedItems, self._dataGridView1, self._KcDependsOnP_checkedListBox.CheckedItems)
		#global UserKcDataFromForm
		UserKcDataFromForm = DataFromUserKcForm[0]
		# Проверяем правильность заполнения формы. Должно быть заполнено имя Кс, зависимость от др.мощностей если выставлена эта галочка. И все поля в таблице.
		if UserKcFormCorreectCheck(DataFromUserKcForm[1], DataFromUserKcForm[2], DataFromUserKcForm[3], DataFromUserKcForm[4], znachKc, UserKcDataFromFormBeginEdit, DataFromUserKcForm[5], DataFromUserKcForm[6]) == '': 
			try:
				if UserKcDataFromFormBeginEdit != '': # Если был открыт на редактирование существующий Кс и его необходимо перезаписать
					# Удаляем эту строку (инфу об этом Кс) из списка данных
					znach_hlp = [] # Вспомогательный список для перезаписи в хранилище. Будет без удалённого элемента.
					for i in znachKc:
						if UserKcDataFromFormBeginEdit.split('@@!!@@')[2] != i.split('@@!!@@')[2]: # Сравниваем по именам Кс
							znach_hlp.append(i)
					znach_hlp.append(UserKcDataFromForm) # Добавляем новый Кс к списку для записи в Хранилище
					Wrtite_to_ExtensibleStorage(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, List[str](znach_hlp) )
				else: # Если мы создавали новый Кс и не нужно перезаписывать старый
					znachKc.append(UserKcDataFromForm) # Добавляем новый Кс к списку для записи в Хранилище
					Wrtite_to_ExtensibleStorage (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, List[str](znachKc) )
				global IsOkPushed_UserKc
				IsOkPushed_UserKc = True
				global UserKcDataFromFormBeginEdit # Обнуляем маркер
				UserKcDataFromFormBeginEdit = ''
				self.Close()
			except:
				raise Exception('Данные по Кс не сохранены. Что-то пошло не так, обратитесь к разработчику')
		else:
			TaskDialog.Show('Пользовательские Кс', UserKcFormCorreectCheck(DataFromUserKcForm[1], DataFromUserKcForm[2], DataFromUserKcForm[3], DataFromUserKcForm[4], znachKc, UserKcDataFromFormBeginEdit, DataFromUserKcForm[5], DataFromUserKcForm[6]))
		

	def Cancel_buttonClick(self, sender, e):
		global IsOkPushed_UserKc
		IsOkPushed_UserKc = False
		global UserKcDataFromFormBeginEdit # Обнуляем маркер
		UserKcDataFromFormBeginEdit = ''
		self.Close()
		

#UserKcForm().ShowDialog()


		

#__________Редактор формул______________________

class EquationForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._P_groupBox = System.Windows.Forms.GroupBox()
		self._Cancel_button = System.Windows.Forms.Button()
		self._SaveandClose_button = System.Windows.Forms.Button()
		self._PSelecet_comboBox = System.Windows.Forms.ComboBox()
		self._label1 = System.Windows.Forms.Label()
		self._P_Edit_button = System.Windows.Forms.Button()
		self._P_New_button = System.Windows.Forms.Button()
		self._P_InsertFormula_button = System.Windows.Forms.Button()
		self._Kc_groupBox = System.Windows.Forms.GroupBox()
		self._Kc_InsertFormula_button = System.Windows.Forms.Button()
		self._Kc_New_button = System.Windows.Forms.Button()
		self._Kc_Edit_button = System.Windows.Forms.Button()
		self._label2 = System.Windows.Forms.Label()
		self._KcSelecet_comboBox = System.Windows.Forms.ComboBox()
		self._Math_groupBox = System.Windows.Forms.GroupBox()
		self._Math_InsertFormula_button = System.Windows.Forms.Button()
		self._label3 = System.Windows.Forms.Label()
		self._MathSelecet_comboBox = System.Windows.Forms.ComboBox()
		self._Formula_groupBox = System.Windows.Forms.GroupBox()
		self._FormulaCheck_button = System.Windows.Forms.Button()
		self._Formula_Delete_button = System.Windows.Forms.Button()
		self._Formula_New_button = System.Windows.Forms.Button()
		self._label4 = System.Windows.Forms.Label()
		self._FormulaSelecet_comboBox = System.Windows.Forms.ComboBox()
		self._FormulaPreview_textBox = System.Windows.Forms.TextBox()
		self._label5 = System.Windows.Forms.Label()
		self._label6 = System.Windows.Forms.Label()
		self._NewFormula_textBox = System.Windows.Forms.TextBox()
		self._DeleteLastElement_button = System.Windows.Forms.Button()
		self._P_groupBox.SuspendLayout()
		self._Kc_groupBox.SuspendLayout()
		self._Math_groupBox.SuspendLayout()
		self._Formula_groupBox.SuspendLayout()
		self.SuspendLayout()
		# 
		# P_groupBox
		# 
		self._P_groupBox.Controls.Add(self._P_InsertFormula_button)
		self._P_groupBox.Controls.Add(self._P_New_button)
		self._P_groupBox.Controls.Add(self._P_Edit_button)
		self._P_groupBox.Controls.Add(self._label1)
		self._P_groupBox.Controls.Add(self._PSelecet_comboBox)
		self._P_groupBox.Location = System.Drawing.Point(12, 12)
		self._P_groupBox.Name = "P_groupBox"
		self._P_groupBox.Size = System.Drawing.Size(338, 195)
		self._P_groupBox.TabIndex = 0
		self._P_groupBox.TabStop = False
		self._P_groupBox.Text = "Мощность"
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(883, 473)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# SaveandClose_button
		# 
		self._SaveandClose_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SaveandClose_button.Location = System.Drawing.Point(12, 473)
		self._SaveandClose_button.Name = "SaveandClose_button"
		self._SaveandClose_button.Size = System.Drawing.Size(161, 23)
		self._SaveandClose_button.TabIndex = 2
		self._SaveandClose_button.Text = "Сохранить и закрыть"
		self._SaveandClose_button.UseVisualStyleBackColor = True
		self._SaveandClose_button.Click += self.SaveandClose_buttonClick
		# 
		# PSelecet_comboBox
		# 
		self._PSelecet_comboBox.FormattingEnabled = True
		self._PSelecet_comboBox.Location = System.Drawing.Point(9, 65)
		self._PSelecet_comboBox.Name = "PSelecet_comboBox"
		self._PSelecet_comboBox.Size = System.Drawing.Size(140, 24)
		self._PSelecet_comboBox.TabIndex = 0
		# 
		# label1
		# 
		self._label1.Location = System.Drawing.Point(9, 22)
		self._label1.Name = "label1"
		self._label1.Size = System.Drawing.Size(140, 40)
		self._label1.TabIndex = 1
		self._label1.Text = "Выберите мощность"
		# 
		# P_Edit_button
		# 
		self._P_Edit_button.Location = System.Drawing.Point(175, 36)
		self._P_Edit_button.Name = "P_Edit_button"
		self._P_Edit_button.Size = System.Drawing.Size(145, 23)
		self._P_Edit_button.TabIndex = 2
		self._P_Edit_button.Text = "Редактировать"
		self._P_Edit_button.UseVisualStyleBackColor = True
		self._P_Edit_button.Click += self.P_Edit_buttonClick
		# 
		# P_New_button
		# 
		self._P_New_button.Location = System.Drawing.Point(175, 65)
		self._P_New_button.Name = "P_New_button"
		self._P_New_button.Size = System.Drawing.Size(145, 23)
		self._P_New_button.TabIndex = 3
		self._P_New_button.Text = "Создать"
		self._P_New_button.UseVisualStyleBackColor = True
		self._P_New_button.Click += self.P_New_buttonClick
		# 
		# P_InsertFormula_button
		# 
		self._P_InsertFormula_button.Location = System.Drawing.Point(175, 147)
		self._P_InsertFormula_button.Name = "P_InsertFormula_button"
		self._P_InsertFormula_button.Size = System.Drawing.Size(145, 42)
		self._P_InsertFormula_button.TabIndex = 5
		self._P_InsertFormula_button.Text = "Вставить в формулу"
		self._P_InsertFormula_button.UseVisualStyleBackColor = True
		self._P_InsertFormula_button.Click += self.P_InsertFormula_buttonClick
		# 
		# Kc_groupBox
		# 
		self._Kc_groupBox.Controls.Add(self._Kc_InsertFormula_button)
		self._Kc_groupBox.Controls.Add(self._Kc_New_button)
		self._Kc_groupBox.Controls.Add(self._Kc_Edit_button)
		self._Kc_groupBox.Controls.Add(self._label2)
		self._Kc_groupBox.Controls.Add(self._KcSelecet_comboBox)
		self._Kc_groupBox.Location = System.Drawing.Point(371, 12)
		self._Kc_groupBox.Name = "Kc_groupBox"
		self._Kc_groupBox.Size = System.Drawing.Size(338, 195)
		self._Kc_groupBox.TabIndex = 6
		self._Kc_groupBox.TabStop = False
		self._Kc_groupBox.Text = "Коэффициент спроса"
		# 
		# Kc_InsertFormula_button
		# 
		self._Kc_InsertFormula_button.Location = System.Drawing.Point(175, 147)
		self._Kc_InsertFormula_button.Name = "Kc_InsertFormula_button"
		self._Kc_InsertFormula_button.Size = System.Drawing.Size(145, 42)
		self._Kc_InsertFormula_button.TabIndex = 5
		self._Kc_InsertFormula_button.Text = "Вставить в формулу"
		self._Kc_InsertFormula_button.UseVisualStyleBackColor = True
		self._Kc_InsertFormula_button.Click += self.Kc_InsertFormula_buttonClick
		# 
		# Kc_New_button
		# 
		self._Kc_New_button.Location = System.Drawing.Point(175, 65)
		self._Kc_New_button.Name = "Kc_New_button"
		self._Kc_New_button.Size = System.Drawing.Size(145, 23)
		self._Kc_New_button.TabIndex = 3
		self._Kc_New_button.Text = "Создать"
		self._Kc_New_button.UseVisualStyleBackColor = True
		self._Kc_New_button.Click += self.Kc_New_buttonClick
		# 
		# Kc_Edit_button
		# 
		self._Kc_Edit_button.Location = System.Drawing.Point(175, 36)
		self._Kc_Edit_button.Name = "Kc_Edit_button"
		self._Kc_Edit_button.Size = System.Drawing.Size(145, 23)
		self._Kc_Edit_button.TabIndex = 2
		self._Kc_Edit_button.Text = "Редактировать"
		self._Kc_Edit_button.UseVisualStyleBackColor = True
		self._Kc_Edit_button.Click += self.Kc_Edit_buttonClick
		# 
		# label2
		# 
		self._label2.Location = System.Drawing.Point(9, 22)
		self._label2.Name = "label2"
		self._label2.Size = System.Drawing.Size(160, 40)
		self._label2.TabIndex = 1
		self._label2.Text = "Выберите коэффициент спроса"
		# 
		# KcSelecet_comboBox
		# 
		self._KcSelecet_comboBox.FormattingEnabled = True
		self._KcSelecet_comboBox.Location = System.Drawing.Point(9, 65)
		self._KcSelecet_comboBox.Name = "KcSelecet_comboBox"
		self._KcSelecet_comboBox.Size = System.Drawing.Size(140, 24)
		self._KcSelecet_comboBox.TabIndex = 0
		# 
		# Math_groupBox
		# 
		self._Math_groupBox.Controls.Add(self._Math_InsertFormula_button)
		self._Math_groupBox.Controls.Add(self._label3)
		self._Math_groupBox.Controls.Add(self._MathSelecet_comboBox)
		self._Math_groupBox.Location = System.Drawing.Point(736, 12)
		self._Math_groupBox.Name = "Math_groupBox"
		self._Math_groupBox.Size = System.Drawing.Size(222, 195)
		self._Math_groupBox.TabIndex = 7
		self._Math_groupBox.TabStop = False
		self._Math_groupBox.Text = "Математические символы"
		# 
		# Math_InsertFormula_button
		# 
		self._Math_InsertFormula_button.Location = System.Drawing.Point(9, 147)
		self._Math_InsertFormula_button.Name = "Math_InsertFormula_button"
		self._Math_InsertFormula_button.Size = System.Drawing.Size(145, 42)
		self._Math_InsertFormula_button.TabIndex = 5
		self._Math_InsertFormula_button.Text = "Вставить в формулу"
		self._Math_InsertFormula_button.UseVisualStyleBackColor = True
		self._Math_InsertFormula_button.Click += self.Math_InsertFormula_buttonClick
		# 
		# label3
		# 
		self._label3.Location = System.Drawing.Point(9, 22)
		self._label3.Name = "label3"
		self._label3.Size = System.Drawing.Size(160, 40)
		self._label3.TabIndex = 1
		self._label3.Text = "Выберите коэффициент спроса"
		# 
		# MathSelecet_comboBox
		# 
		self._MathSelecet_comboBox.FormattingEnabled = True
		self._MathSelecet_comboBox.Location = System.Drawing.Point(9, 65)
		self._MathSelecet_comboBox.Name = "MathSelecet_comboBox"
		self._MathSelecet_comboBox.Size = System.Drawing.Size(140, 24)
		self._MathSelecet_comboBox.TabIndex = 0
		# 
		# Formula_groupBox
		# 
		self._Formula_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Formula_groupBox.Controls.Add(self._DeleteLastElement_button)
		self._Formula_groupBox.Controls.Add(self._NewFormula_textBox)
		self._Formula_groupBox.Controls.Add(self._label6)
		self._Formula_groupBox.Controls.Add(self._label5)
		self._Formula_groupBox.Controls.Add(self._FormulaPreview_textBox)
		self._Formula_groupBox.Controls.Add(self._FormulaCheck_button)
		self._Formula_groupBox.Controls.Add(self._Formula_Delete_button)
		self._Formula_groupBox.Controls.Add(self._Formula_New_button)
		self._Formula_groupBox.Controls.Add(self._label4)
		self._Formula_groupBox.Controls.Add(self._FormulaSelecet_comboBox)
		self._Formula_groupBox.Location = System.Drawing.Point(12, 227)
		self._Formula_groupBox.Name = "Formula_groupBox"
		self._Formula_groupBox.Size = System.Drawing.Size(946, 240)
		self._Formula_groupBox.TabIndex = 6
		self._Formula_groupBox.TabStop = False
		self._Formula_groupBox.Text = "Расчётная формула"
		# 
		# FormulaCheck_button
		# 
		self._FormulaCheck_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._FormulaCheck_button.Location = System.Drawing.Point(229, 122)
		self._FormulaCheck_button.Name = "FormulaCheck_button"
		self._FormulaCheck_button.Size = System.Drawing.Size(145, 42)
		self._FormulaCheck_button.TabIndex = 5
		self._FormulaCheck_button.Text = "Проверить формулу"
		self._FormulaCheck_button.UseVisualStyleBackColor = True
		self._FormulaCheck_button.Click += self.FormulaCheck_buttonClick
		# 
		# Formula_Delete_button
		# 
		self._Formula_Delete_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Formula_Delete_button.Location = System.Drawing.Point(175, 202)
		self._Formula_Delete_button.Name = "Formula_Delete_button"
		self._Formula_Delete_button.Size = System.Drawing.Size(145, 23)
		self._Formula_Delete_button.TabIndex = 4
		self._Formula_Delete_button.Text = "Удалить формулу"
		self._Formula_Delete_button.UseVisualStyleBackColor = True
		self._Formula_Delete_button.Click += self.Formula_Delete_buttonClick
		# 
		# Formula_New_button
		# 
		self._Formula_New_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._Formula_New_button.Location = System.Drawing.Point(9, 202)
		self._Formula_New_button.Name = "Formula_New_button"
		self._Formula_New_button.Size = System.Drawing.Size(145, 23)
		self._Formula_New_button.TabIndex = 3
		self._Formula_New_button.Text = "Создать"
		self._Formula_New_button.UseVisualStyleBackColor = True
		self._Formula_New_button.Click += self.Formula_New_buttonClick
		# 
		# label4
		# 
		self._label4.Location = System.Drawing.Point(9, 28)
		self._label4.Name = "label4"
		self._label4.Size = System.Drawing.Size(140, 29)
		self._label4.TabIndex = 1
		self._label4.Text = "Выберите формулу"
		# 
		# FormulaSelecet_comboBox
		# 
		self._FormulaSelecet_comboBox.FormattingEnabled = True
		self._FormulaSelecet_comboBox.Location = System.Drawing.Point(9, 65)
		self._FormulaSelecet_comboBox.Name = "FormulaSelecet_comboBox"
		self._FormulaSelecet_comboBox.Size = System.Drawing.Size(140, 24)
		self._FormulaSelecet_comboBox.TabIndex = 0
		self._FormulaSelecet_comboBox.SelectedIndexChanged += self.FormulaSelecet_comboBoxSelectedIndexChanged
		# 
		# FormulaPreview_textBox
		# 
		self._FormulaPreview_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._FormulaPreview_textBox.BackColor = System.Drawing.SystemColors.Window
		self._FormulaPreview_textBox.Location = System.Drawing.Point(229, 45)
		self._FormulaPreview_textBox.Multiline = True
		self._FormulaPreview_textBox.Name = "FormulaPreview_textBox"
		self._FormulaPreview_textBox.ReadOnly = True
		self._FormulaPreview_textBox.Size = System.Drawing.Size(555, 71)
		self._FormulaPreview_textBox.TabIndex = 6
		# 
		# label5
		# 
		self._label5.Location = System.Drawing.Point(228, 18)
		self._label5.Name = "label5"
		self._label5.Size = System.Drawing.Size(280, 19)
		self._label5.TabIndex = 7
		self._label5.Text = "Предпросмотр"
		# 
		# label6
		# 
		self._label6.Location = System.Drawing.Point(9, 100)
		self._label6.Name = "label6"
		self._label6.Size = System.Drawing.Size(140, 51)
		self._label6.TabIndex = 8
		self._label6.Text = "Или введите имя новой формулы и нажмите \"Создать\""
		# 
		# NewFormula_textBox
		# 
		self._NewFormula_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._NewFormula_textBox.Location = System.Drawing.Point(9, 164)
		self._NewFormula_textBox.Multiline = True
		self._NewFormula_textBox.Name = "NewFormula_textBox"
		self._NewFormula_textBox.Size = System.Drawing.Size(187, 22)
		self._NewFormula_textBox.TabIndex = 9
		# 
		# DeleteLastElement_button
		# 
		self._DeleteLastElement_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._DeleteLastElement_button.Location = System.Drawing.Point(795, 45)
		self._DeleteLastElement_button.Name = "DeleteLastElement_button"
		self._DeleteLastElement_button.Size = System.Drawing.Size(145, 60)
		self._DeleteLastElement_button.TabIndex = 10
		self._DeleteLastElement_button.Text = "Удалить последний элемент"
		self._DeleteLastElement_button.UseVisualStyleBackColor = True
		self._DeleteLastElement_button.Click += self.DeleteLastElement_buttonClick
		# 
		# EquationForm
		# 
		self.ClientSize = System.Drawing.Size(977, 508)
		self.Controls.Add(self._Formula_groupBox)
		self.Controls.Add(self._Math_groupBox)
		self.Controls.Add(self._Kc_groupBox)
		self.Controls.Add(self._SaveandClose_button)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._P_groupBox)
		self.MinimumSize = System.Drawing.Size(995, 522)
		self.Name = "EquationForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Редактор формул"
		self.Load += self.EquationFormLoad
		self._P_groupBox.ResumeLayout(False)
		self._Kc_groupBox.ResumeLayout(False)
		self._Math_groupBox.ResumeLayout(False)
		self._Formula_groupBox.ResumeLayout(False)
		self._Formula_groupBox.PerformLayout()
		self.ResumeLayout(False)

		self.Icon = iconmy


	def EquationFormLoad(self, sender, e):
		self._PSelecet_comboBox.DataSource = UnitDependentPwrList 
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс 
		KcList = []
		for i in Readable_znachKc:
			KcList.append(i[2])
		self._KcSelecet_comboBox.DataSource = KcList 
		self._MathSelecet_comboBox.DataSource = MathSymbolsList
		znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
		Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # Вид: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		self._FormulaPreview_textBox.Text = ' '.join(Readable_znachUserFormula[0][1]) 
		# Забираем значения в FormulaList
		global FormulaList
		FormulaList = Readable_znachUserFormula[0][1]
		UserFormulaNamesList = [i[0] for i in Readable_znachUserFormula] # обновляем список имён формул
		self._FormulaSelecet_comboBox.DataSource = UserFormulaNamesList # пишем список имён формул

	def P_Edit_buttonClick(self, sender, e):
		global PSelecet_SelectedItem
		PSelecet_SelectedItem = self._PSelecet_comboBox.SelectedItem # Берём имя выбранной мощности 'Рр.сантех.'
		UserP().ShowDialog()
		# Переисываем список мощностей.
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
		Readable_znachP = UserPDecoding(znachP) # Вид: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		UnitDependentPwrList = [] # Вид: ['Ру (вся)', 'Рр (вся)']
		for i in Readable_znachP:
			UnitDependentPwrList.append(i[0]) 
		self._PSelecet_comboBox.DataSource = UnitDependentPwrList 

	def P_New_buttonClick(self, sender, e):
		UserP().ShowDialog()
		# Переписываем список мощностей.
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
		Readable_znachP = UserPDecoding(znachP) # Вид: [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		UnitDependentPwrList = [] # Вид: ['Ру (вся)', 'Рр (вся)']
		for i in Readable_znachP:
			UnitDependentPwrList.append(i[0]) 
		self._PSelecet_comboBox.DataSource = UnitDependentPwrList 

	def P_InsertFormula_buttonClick(self, sender, e):
		global FormulaList
		FormulaList.append(self._PSelecet_comboBox.SelectedItem)
		self._FormulaPreview_textBox.Text = ' '.join(FormulaList) # Показываем выбранную формулу
		# От греха засереваем опасные кнопки элементы управления.
		self._FormulaSelecet_comboBox.Enabled = False
		self._Formula_New_button.Enabled = False
		self._NewFormula_textBox.Enabled = False

	def Kc_Edit_buttonClick(self, sender, e):
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс 
		# Вид: [[u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин', u'Системы ОВ', u'Кс.сан.тех.', 'epcount', u'Зависит от уд.веса в других нагрузках', [u'Ру (вся)'], [u'Резерв 1'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11', 'column12'], [u'Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100-85', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84-75', '0', '0', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74-50', '0', '0', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49-25', '0', '0', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '0', '0', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]]]
		KcSelecet_SelectedItem = self._KcSelecet_comboBox.SelectedItem # Берём имя выбранного Кс
		if KcSelecet_SelectedItem != 'Кс.л.':
			# Чтобы понять по какой кнопке пользователь попал в окно пользовательских Кс выставим соответствующую вспомогательную метку
			# Она же заодно и имя выбранной пользователем таблицы
			global EnterUserKcShow # 'Арина таблица'
			for i in Readable_znachKc:
				if i[2] == KcSelecet_SelectedItem:
					EnterUserKcShow = i[0]
					break
			UserKcForm().ShowDialog()
			znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
			Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс 
			KcList = []
			for i in Readable_znachKc:
				KcList.append(i[2])
			self._KcSelecet_comboBox.DataSource = KcList
		else: # Если пользователь хотел отредактировать Кс лифтов
			TaskDialog.Show('Редактор формул', 'Кс.л. - коэффициент спроса лифтов вшит в Программу. Чтобы посмотреть значения Кс.л. перейтите из Редактора формул в окно "Коэффициенты спроса".')
			#pass

	def Kc_New_buttonClick(self, sender, e):
		UserKcForm().ShowDialog()
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		Readable_znachKc = UserKcTablesDecoding(znachKc) # Для первоначального заполнения формы всех Кс 
		KcList = []
		for i in Readable_znachKc:
			KcList.append(i[2])
		self._KcSelecet_comboBox.DataSource = KcList

	def Kc_InsertFormula_buttonClick(self, sender, e):
		global FormulaList
		FormulaList.append(self._KcSelecet_comboBox.SelectedItem)
		self._FormulaPreview_textBox.Text = ' '.join(FormulaList) # Показываем выбранную формулу
		# От греха засереваем опасные кнопки элементы управления.
		self._FormulaSelecet_comboBox.Enabled = False
		self._Formula_New_button.Enabled = False
		self._NewFormula_textBox.Enabled = False

	def Math_InsertFormula_buttonClick(self, sender, e):
		global FormulaList
		FormulaList.append(self._MathSelecet_comboBox.SelectedItem)
		self._FormulaPreview_textBox.Text = ' '.join(FormulaList) # Показываем выбранную формулу
		# От греха засереваем опасные кнопки элементы управления.
		self._FormulaSelecet_comboBox.Enabled = False
		self._Formula_New_button.Enabled = False
		self._NewFormula_textBox.Enabled = False

	def Formula_New_buttonClick(self, sender, e):
		# Создаём новую формулу
		NewFormulaName = self._NewFormula_textBox.Text
		self._FormulaSelecet_comboBox.DataSource = [NewFormulaName]
		# Засереваем нафиг все опасные кнопки и элементы управления
		self._FormulaSelecet_comboBox.Enabled = False
		self._Formula_New_button.Enabled = False
		self._Formula_Delete_button.Enabled = False
		self._NewFormula_textBox.Enabled = False
		self._FormulaPreview_textBox.Text = '' # очищаем строку предпросмотра
		global FormulaList
		FormulaList = [] # очищаем контрольный список
		global NewFormulaWasCreated
		NewFormulaWasCreated = True # Выставляем маркер что создавалась новая формула

	def FormulaSelecet_comboBoxSelectedIndexChanged(self, sender, e):
		SelectedFormulaName = self._FormulaSelecet_comboBox.SelectedItem # Берём имя выбранной формулы
		znachUserFormula = Read_UserKc_fromES(schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
		Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # Вид: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		for i in Readable_znachUserFormula:
			if i[0] == SelectedFormulaName:
				self._FormulaPreview_textBox.Text = ' '.join(i[1]) # Показываем выбранную формулу
				# Забираем значения в FormulaList
				global FormulaList
				FormulaList = i[1]
				break
		
	def DeleteLastElement_buttonClick(self, sender, e):
		# Убираем последний элемент из контрольного списка
		if len(FormulaList) > 0:
			global FormulaList
			FormulaList.pop(-1)
			self._FormulaPreview_textBox.Text = ' '.join(FormulaList) # Показываем выбранную формулу		
		# От греха засереваем опасные кнопки элементы управления.
		self._FormulaSelecet_comboBox.Enabled = False
		self._Formula_New_button.Enabled = False
		self._NewFormula_textBox.Enabled = False

	def Formula_Delete_buttonClick(self, sender, e):
		# Спросим уверен ли пользователь
		td = TaskDialog('Удаление формулы')
		td.MainContent = 'Удалить все данные по текущей формуле?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да', 'Текущая формула будет полностью удалёна.')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			SelectedFormulaName = self._FormulaSelecet_comboBox.SelectedItem # Берём имя выбранной формулы
			znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
			Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # Вид: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]
			znachUserFormula_hlp = [] # без удалённого элемента
			for n, i in enumerate(Readable_znachUserFormula):
				if i[0] != SelectedFormulaName: 
					znachUserFormula_hlp.append(znachUserFormula[n])
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula, SchemaName_for_UserFormula, znachUserFormula_hlp) # пишем данные в хранилище 
			global FormulaList
			FormulaList = [] # очищаем список
			global NewFormulaWasCreated
			NewFormulaWasCreated = False # Выставляем маркер в исходное состояние
			self.Close()

	def FormulaCheck_buttonClick(self, sender, e):
		global Readable_znachKc
		global FormulaList
		# Считываем актуальные данные по Р и Кс
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc)
		Readable_znachKc = UserKcTablesDecoding(znachKc)
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP)
		Readable_znachP = UserPDecoding(znachP)
		Alertstr = FormulaCheck(FormulaList, MathSymbolsList, Readable_znachP, Readable_znachKc)
		if Alertstr != '':
			TaskDialog.Show('Редактор формул', Alertstr)
		else:
			TaskDialog.Show('Редактор формул', 'Всё ОК. Вы отлично справились с составлением формулы.')


	def SaveandClose_buttonClick(self, sender, e):
		SelectedFormulaName = self._FormulaSelecet_comboBox.SelectedItem # Берём имя выбранной формулы
		# Проверяем правильность формулы
		# Считываем актуальные данные по Р и Кс
		znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc)
		Readable_znachKc = UserKcTablesDecoding(znachKc)
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP)
		Readable_znachP = UserPDecoding(znachP)
		Alertstr = FormulaCheck(FormulaList, MathSymbolsList, Readable_znachP, Readable_znachKc)
		# Проверяем нет ли такой формулы в хранилище
		znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
		Readable_znachUserFormula = UserFormulaDecoding(znachUserFormula) # Вид: [[u'Расчёт Рр', [u'Рр (вся)'], u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Супер расчёт', ['p1', '+', 'pss', '*', 'kcss', '+', '(', 'p2', '+', 'pqq', ')', '*', '0.5'], u'Резерв 1', u'Резерв 2', u'Резерв 3']]
		hlpel = 0 # есть ли в хранилище формула с таким же именем. если больше 0, то есть
		for i in Readable_znachUserFormula:
			if i[0] == SelectedFormulaName:
				hlpel = hlpel + 1
				break
		if NewFormulaWasCreated == False and Alertstr == '': # Если редактировалась существующая формула, и формула составлена правильно.
			# Сначала удаляем формулу с тем же названием
			znachUserFormula_hlp = [] # без удалённого элемента
			for n, i in enumerate(Readable_znachUserFormula):
				if i[0] != SelectedFormulaName: 
					znachUserFormula_hlp.append(znachUserFormula[n])
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula, SchemaName_for_UserFormula, znachUserFormula_hlp) # пишем данные в хранилище 
			znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula) # считываем данные о формулах из Хранилища
		# Далее и для новой и для редактируемой формул одно и то же
		if Alertstr != '':
			TaskDialog.Show('Редактор формул', Alertstr)
		elif hlpel > 0 and NewFormulaWasCreated == True:
			TaskDialog.Show('Редактор формул', 'Формула с таким именем уже есть в Настройках')
		else: # если всё ок, продолжаем
			NewFormulaString = EncodingFormula(SelectedFormulaName, FormulaList, 'Резерв 1', 'Резерв 2', 'Резерв 3') # Вид: 'vasa@@!!@@Рр (вся)&&??&&+&&??&&(@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3'
			znachUserFormula.append(NewFormulaString)
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula, SchemaName_for_UserFormula, znachUserFormula) # пишем данные в хранилище 
			global FormulaList
			FormulaList = [] # очищаем список 
			global NewFormulaWasCreated
			NewFormulaWasCreated = False # Выставляем маркер в исходное состояние
			self.Close()
			



	def Cancel_buttonClick(self, sender, e):
		global FormulaList
		FormulaList = [] # очищаем список
		global NewFormulaWasCreated
		NewFormulaWasCreated = False # Выставляем маркер в исходное состояние
		self.Close()







































#_________________________________ Работаем с 6-м хранилищем (Коэффициенты спроса) ____________________________________________________________________________
schemaGuid_for_Kc_Storage = System.Guid(Guidstr_Kc_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

#_____________________ Значения списков исходных данных по умолчанию_______________________________________________________________________________________

# Табличные данные по умолчанию:
# Поправочный коэффициент для расчёта нагрузки жилого дома в зависимости от региона (п.7.1.10 поправок к СП256)
Kkr_flats_koefficient = [1]
# Удельная расчётная электрическая нагрузка (кВт) для квартир мощностью Рр=10 кВт (по табл.7.1 СП 256.1325800.2016), или коэффициент одновременности для квартир повышенной комфортности (по табл.7.3 того же СП)
# Для этого перепишем сюда табл. 7.1 СП 256.1325800.2016
Flat_count_SP = [5, 6, 9, 12, 15, 18, 24, 40, 60, 100, 200, 400, 600, 1000] # количество квартир
Flat_unit_wattage_SP = [10.0, 5.1, 3.8, 3.2, 2.8, 2.6, 2.2, 1.95, 1.7, 1.5, 1.36, 1.27, 1.23, 1.19] # удельная расчётная электрическая нагрузка при количестве квартир
# А также таблицы 7.2 и 7.3
Py_high_comfort = [14, 20, 30, 40, 50, 60, 70]
Ks_high_comfort = [0.8, 0.65, 0.6, 0.55, 0.5, 0.48, 0.45] # коэффициенты спроса для квартир повышенной комфортности
Flat_count_high_comfort = [5, 6, 9, 12, 15, 18, 24, 40, 60, 100, 200, 400, 600] # количество квартир
Ko_high_comfort = [1, 0.51, 0.38, 0.32, 0.29, 0.26, 0.24, 0.2, 0.18, 0.16, 0.14, 0.13, 0.11] # Коэффициенты одновременности для квартир повышенной комфортности
Kcpwrres = [0.9] # коэффициент на силовую нагрузку жилого дома по СП 256.1325800.2016 п. 7.1.10 - Рр.ж.д = Ркв + 0,9 * Рс
Elevator_count_SP = [1, 2, 3, 4, 5, 6, 10, 20, 25]
Ks_elevators_below12 = [1, 0.8, 0.8, 0.7, 0.7, 0.65, 0.5, 0.4, 0.35]
Ks_elevators_above12 = [1, 0.9, 0.9, 0.8, 0.8, 0.75, 0.6, 0.5, 0.4]
# Вспомогательный костыль: поиск частей слов нагрузок
Load_Class_elevators = ['ЛИФТ'] # поиск части слова Лифты в Классификации нагрузок
Load_Class_falts = ['КВАРТИР', 'АПАРТАМЕНТ'] # и квартир
Ks_Reserve_1 = [] # резервное поле
Ks_Reserve_2 = [] # резервное поле

# Список с скоэффициентами по умолчанию:
All_koeffs_byDefault = [[1001, [str(i) for i in Kkr_flats_koefficient][0]],
[1002, [str(i) for i in Flat_count_SP], [str(i) for i in Flat_unit_wattage_SP]],
[1003, [str(i) for i in Py_high_comfort], [str(i) for i in Ks_high_comfort]],
[1004, [str(i) for i in Flat_count_high_comfort], [str(i) for i in Ko_high_comfort]],
[1005, [str(i) for i in Kcpwrres][0]],
[1006, [str(i) for i in Elevator_count_SP], [str(i) for i in Ks_elevators_below12], [str(i) for i in Ks_elevators_above12]]]


#Получаем Schema:
sch_Kc_Storage = Schema.Lookup(schemaGuid_for_Kc_Storage)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_Kc_Storage) будет <type 'NoneType'>
if sch_Kc_Storage is None or ProjectInfoObject.GetEntity(sch_Kc_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show('Настройки', 'Настройки коэффициентов спроса не найдены или были повреждены.\n Будут созданы настройки по умолчанию.')
	# Пишем данные по умолчанию в Хранилище
	Write_several_fields_to_ExtensibleStorage (schemaGuid_for_Kc_Storage, ProjectInfoObject, SchemaName_for_Kc, 
	FieldName_for_Kc_1, [str(i) for i in Kkr_flats_koefficient], 
	FieldName_for_Kc_2, [str(i) for i in Flat_count_SP],
	FieldName_for_Kc_3, [str(i) for i in Flat_unit_wattage_SP], 
	FieldName_for_Kc_4, [str(i) for i in Py_high_comfort],
	FieldName_for_Kc_5, [str(i) for i in Ks_high_comfort],
	FieldName_for_Kc_6, [str(i) for i in Flat_count_high_comfort],
	FieldName_for_Kc_7, [str(i) for i in Ko_high_comfort],
	FieldName_for_Kc_8, [str(i) for i in Kcpwrres],
	FieldName_for_Kc_9, [str(i) for i in Elevator_count_SP],
	FieldName_for_Kc_10, [str(i) for i in Ks_elevators_below12],
	FieldName_for_Kc_11, [str(i) for i in Ks_elevators_above12],
	FieldName_for_Kc_12, Load_Class_elevators,
	FieldName_for_Kc_13, Load_Class_falts,
	FieldName_for_Kc_14, [str(i) for i in Ks_Reserve_1],
	FieldName_for_Kc_15, [str(i) for i in Ks_Reserve_2]
	)



# Считываем данные из Хранилища
Kc_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_Kc_Storage, ProjectInfoObject)

# Переобъявляем считанные данные
Kkr_flats_koefficient = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_1) + 1)] # ['1']. Обращение к содержимому по имени поля.
Flat_count_SP = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_2) + 1)] # ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000']
Flat_unit_wattage_SP = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_3) + 1)]
Py_high_comfort = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_4) + 1)]
Ks_high_comfort = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_5) + 1)]
Flat_count_high_comfort = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_6) + 1)]
Ko_high_comfort = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_7) + 1)]
Kcpwrres = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_8) + 1)]
Elevator_count_SP = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_9) + 1)]
Ks_elevators_below12 = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_10) + 1)]
Ks_elevators_above12 = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_11) + 1)]
Load_Class_elevators = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_12) + 1)]
Load_Class_falts = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_13) + 1)] # [u'КВАРТИР', u'АПАРТАМЕНТ']

# Формируем списки для заполнения таблицы с текущими коэффициентами спроса (0-м элементом идёт внутренний уникальный код)
Koeff_1001 = [1001, Kkr_flats_koefficient[0]] # вид [1001, '1']
Koeff_1002 = [1002, Flat_count_SP, Flat_unit_wattage_SP] # вид [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']]
Koeff_1003 = [1003, Py_high_comfort, Ks_high_comfort]
Koeff_1004 = [1004, Flat_count_high_comfort, Ko_high_comfort]
Koeff_1005 = [1005, Kcpwrres[0]] # Вид [1005, '0.9']
Koeff_1006 = [1006, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12]

All_koeffs = [Koeff_1001, Koeff_1002, Koeff_1003, Koeff_1004, Koeff_1005, Koeff_1006] # [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]

# Характерные названия и описания коэффициентов спроса (для группировки в таблице). 
# Плюс 0-м элементом подсписка пойдёт уникальный мой внутренний код коэффициента. Чтобы его было удобно искать.
Kc_descriptions = [
	[1001, 'Поправочный коэффициент для расчёта нагрузки жилого дома в зависимости от региона (п.7.1.10 поправок к СП256.1325800)', 'Жилой дом'],
	[1002, 'Удельная расчётная электрическая нагрузка (кВт) для квартир мощностью Рр=10 кВт (по табл.7.1 СП 256.1325800)', 'Квартиры'],
	[1003, 'Коэффициенты спроса для квартир повышенной комфортности (таблица 7.2 СП 256.1325800)', 'Квартиры'],
	[1004, 'Коэффициенты одновременности для квартир повышенной комфортности (таблица 7.3 СП 256.1325800)', 'Квартиры'],
	[1005, 'Понижающий коэффициент на силовую нагрузку жилого дома п.7.1.10 СП 256.1325800', 'Жилой дом'],
	[1006, 'Коэффициенты спроса для лифтовых установок таблица 7.4 СП 256.1325800', 'Лифты']
]



# Функция заполнения таблицы списком Кс (вызывается при загрузке формы Кс и при работе с пользовательскими Кс)
# Пример обращения: Kc_Storage_FormLoad_Func(self._KcList_dataGridView, Kc_descriptions, Readable_znachKc, 'Показать')
def Kc_Storage_FormLoad_Func (dataGridViewObj, Kc_descriptions, Readable_znachKc, ShowbuttonName):
	a = 0 # счётчик
	while a < len(Kc_descriptions):
		dataGridViewObj.Rows.Add(Kc_descriptions[a][2], Kc_descriptions[a][1], ShowbuttonName) # Заполняем таблицу исходными данными
		a = a + 1
	# После этого дописываем пользовательские таблицы Кс
	a = 0 # счётчик
	while a < len(Readable_znachKc):
		if Readable_znachKc[a][0] != 'Костыль для лифтов': # эту фигню не показываем. Костыль же.
			dataGridViewObj.Rows.Add(Readable_znachKc[a][1], Readable_znachKc[a][0], ShowbuttonName) # Заполняем таблицу исходными данными
			a = a + 1
		else:
			a = a + 1



# Функция по экспорту всех Кс, мощностей и формул.
# На входе списки Кс, Р, формул и базовых Кс
# На выходе ничего
def Export_All_Kc_P_Formula (znachKc, znachP, znachUserFormula, All_koeffs_Output):
	# Сначала закодируем All_koeffs_Output аналогично остальным спискам.
	All_koeffs_Output_Coded = [] # Вид: ['1001@@!!@@1', '1002@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600$$>>$$1000@@!!@@10.0$$>>$$5.1$$>>$$3.8$$>>$$3.2$$>>$$2.8$$>>$$2.6$$>>$$2.2$$>>$$1.95$$>>$$1.7$$>>$$1.5$$>>$$1.36$$>>$$1.27$$>>$$1.23$$>>$$1.19', '1003@@!!@@14$$>>$$20$$>>$$30$$>>$$40$$>>$$50$$>>$$60$$>>$$70@@!!@@0.8$$>>$$0.65$$>>$$0.6$$>>$$0.55$$>>$$0.5$$>>$$0.48$$>>$$0.45', '1004@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600@@!!@@1$$>>$$0.51$$>>$$0.38$$>>$$0.32$$>>$$0.29$$>>$$0.26$$>>$$0.24$$>>$$0.2$$>>$$0.18$$>>$$0.16$$>>$$0.14$$>>$$0.13$$>>$$0.11', '1005@@!!@@0.9', '1006@@!!@@1$$>>$$2$$>>$$3$$>>$$4$$>>$$5$$>>$$6$$>>$$10$$>>$$20$$>>$$25@@!!@@1$$>>$$0.8$$>>$$0.8$$>>$$0.7$$>>$$0.7$$>>$$0.65$$>>$$0.5$$>>$$0.4$$>>$$0.35@@!!@@1$$>>$$0.9$$>>$$0.9$$>>$$0.8$$>>$$0.8$$>>$$0.75$$>>$$0.6$$>>$$0.5$$>>$$0.4']
	for i in All_koeffs_Output:
		cur_str = ''
		for n, j in enumerate(i):
			if n == 0:
				cur_str = cur_str + str(j)
			elif type(j) != list:
				cur_str = cur_str + '@@!!@@' + j
			else:
				curcurstr = ''
				for k in j:
					curcurstr = curcurstr + k + '$$>>$$'
				curcurstr = curcurstr[:-6]
				cur_str = cur_str + '@@!!@@' + curcurstr
		All_koeffs_Output_Coded.append(cur_str)

	# Закодируем входящие списки.
	znachKc_1 = '@&<>&@'.join(znachKc)
	znachP_1 = '@&<>&@'.join(znachP)
	znachUserFormula_1 = '@&<>&@'.join(znachUserFormula)
	All_koeffs_Output_Coded_1 = '@&<>&@'.join(All_koeffs_Output_Coded) # Вид: '1001@@!!@@1@&<>&@1002@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600$$>>$$1000@@!!@@10.0$$>>$$5.1$$>>$$3.8$$>>$$3.2$$>>$$2.8$$>>$$2.6$$>>$$2.2$$>>$$1.95$$>>$$1.7$$>>$$1.5$$>>$$1.36$$>>$$1.27$$>>$$1.23$$>>$$1.19@&<>&@1003@@!!@@14$$>>$$20$$>>$$30$$>>$$40$$>>$$50$$>>$$60$$>>$$70@@!!@@0.8$$>>$$0.65$$>>$$0.6$$>>$$0.55$$>>$$0.5$$>>$$0.48$$>>$$0.45@&<>&@1004@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600@@!!@@1$$>>$$0.51$$>>$$0.38$$>>$$0.32$$>>$$0.29$$>>$$0.26$$>>$$0.24$$>>$$0.2$$>>$$0.18$$>>$$0.16$$>>$$0.14$$>>$$0.13$$>>$$0.11@&<>&@1005@@!!@@0.9@&<>&@1006@@!!@@1$$>>$$2$$>>$$3$$>>$$4$$>>$$5$$>>$$6$$>>$$10$$>>$$20$$>>$$25@@!!@@1$$>>$$0.8$$>>$$0.8$$>>$$0.7$$>>$$0.7$$>>$$0.65$$>>$$0.5$$>>$$0.4$$>>$$0.35@@!!@@1$$>>$$0.9$$>>$$0.9$$>>$$0.8$$>>$$0.8$$>>$$0.75$$>>$$0.6$$>>$$0.5$$>>$$0.4'
	# Итоговая выходная строка.
	Exit_Big_String = znachKc_1 + '$@&><&@$' + znachP_1 + '$@&><&@$' + znachUserFormula_1 + '$@&><&@$' + All_koeffs_Output_Coded_1

	# Сохраняем настройки во внешний txt файл
	sfd = SaveFileDialog()
	sfd.Filter = "Text files(*.txt)|*.txt" #sfd.Filter = "Text files(*.txt)|*.txt|All files(*.*)|*.*"
	sfd.FileName = doc.Title + '_Кс_Р_Расчетные_формулы' # имя файла по умолчанию
	if (sfd.ShowDialog() == DialogResult.OK): # sfd.ShowDialog() # файл на сохранение
		filename = sfd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
		System.IO.File.WriteAllText(filename, Exit_Big_String)

'''
znachKc = Read_UserKc_fromES (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
# [u'Костыль для лифтов@@!!@@Лифты@@!!@@Кс.л.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.л@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&1$$>>$$1&&??&&1', u'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков@@!!@@Прочее@@!!@@Кс.гор.пищ.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.гор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&60&&??&&100&&??&&120$$>>$$0.9&&??&&0.85&&??&&0.75&&??&&0.65&&??&&0.6&&??&&0.5&&??&&0.45&&??&&0.4&&??&&0.3&&??&&0.3&&??&&0.25', u'Таблица 7.6 - Коэффициенты спроса для рабочего освещения@@!!@@Рабочее освещение@@!!@@Кс.о.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.раб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@5&&??&&10&&??&&15&&??&&25&&??&&50&&??&&100&&??&&200&&??&&400&&??&&500$$>>$$1&&??&&0.8&&??&&0.7&&??&&0.6&&??&&0.5&&??&&0.4&&??&&0.35&&??&&0.3&&??&&0.3', u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Ру.сантех.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4', u'ВАСЯ@@!!@@Прочее@@!!@@КСАРА@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Рр.сантех.@@!!@@Ру.раб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3@@!!@@Столбец 1. Удельный вес установленной мощности в других нагрузках (\)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников: (заполните далее эту строку)&&??&&1&&??&&2$$>>$$2&&??&&3&&??&&4$$>>$$99.4&&??&&77&&??&&88', u'qwerty@@!!@@Прочее@@!!@@kctestov@@!!@@eppower@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Рр (вся)@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&2$$>>$$3&&??&&4', u'ЦифирЬ@@!!@@Прочее@@!!@@Кс ЦИФРА@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру (вся)&&??&&Рр (вся)&&??&&Ру (без классиф.)&&??&&Рр (без классиф.)&&??&&Ру (др. классиф.)&&??&&Рр (др. классиф.)&&??&&Ру.л&&??&&Рр.сантех.&&??&&Рраб.осв.&&??&&Ргор.пищ.&&??&&Рр.ов&&??&&Ру.сантех.&&??&&Ру.раб.осв.&&??&&Ру.гор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&100$$>>$$0.7&&??&&0.7']
znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
# [u'Ру (вся)@@!!@@all@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр (вся)@@!!@@all@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру (др. классиф.)@@!!@@other@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр (др. классиф.)@@!!@@other@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру.л@@!!@@Лифты@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр.сантех.@@!!@@hvac&&??&&ОВК&&??&&Системы ВК&&??&&Системы ОВ@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рраб.осв.@@!!@@Рабочее освещение@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ргор.пищ.@@!!@@Тепловое оборудование пищеблоков@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр.ов@@!!@@Системы ОВ@@!!@@pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру.сантех.@@!!@@ОВК&&??&&Системы ВК&&??&&Системы ОВ@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру.раб.осв.@@!!@@Рабочее освещение@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру.гор.пищ.@@!!@@Термическая нагрузка@@!!@@py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula)
# [u'Расчёт Рр@@!!@@Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'test count@@!!@@Ру.раб.осв.&&??&&*&&??&&Кс.о.&&??&&+&&??&&Ру.гор.пищ.&&??&&*&&??&&Кс.гор.пищ.&&??&&+&&??&&Ру.сантех.&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру.л&&??&&*&&??&&Кс.л.&&??&&+&&??&&Рр (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Расчёт Ру@@!!@@Ру (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Рр без класс@@!!@@Рр (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Ру без класс@@!!@@Ру (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Др класс и сантех@@!!@@Рр.сантех.&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Рр (др. классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Др класс Ру и сантех@@!!@@Ру.сантех.&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру (др. классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'formula peta@@!!@@Ру.сантех.&&??&&*&&??&&kctestov@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', u'Тестов Цифирь@@!!@@(&&??&&Рраб.осв.&&??&&+&&??&&Ру.сантех.&&??&&)&&??&&*&&??&&Кс ЦИФРА@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
All_koeffs_Output это [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]

@@!!@@ - разделитель между членами каждого списка. 1 уровень.
&&??&& - разделитель внутри членов подсписков. 2 уровень.
$$>>$$ - разделитель подсписков внутри подсписков. 3 уровень.
нам понадобится:
@&<>&@ - разделитель -1 уровня. (чтобы сделать линейными списки выше)
$@&><&@$ - разделитель -2 уровня. (чтобы разделить списки Кс, Р, формул)

'''

# Функция импорта Кс, Р, формул и базовых Кс из внешнего файла. И их декодирования для записи в хранилище.
# На выходе кортеж из 4-х списков: Кс, Р, формулы, вшитые Кс - в виде готовом для записи в Хранилище.
def Import_All_Kc_P_Formula ():
	# Открываем файл для считывания данных
	ofd = OpenFileDialog() # <System.Windows.Forms.OpenFileDialog object at 0x000000000000002B [System.Windows.Forms.OpenFileDialog: Title: , FileName: ]>
	if (ofd.ShowDialog() == DialogResult.OK):
		filename = ofd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
		fileText = System.IO.File.ReadAllText(filename)

	# Погнали раздербанивать списки
	Explode_1 = fileText.split('$@&><&@$') # Получили 4 наших строки: Кс, Р, формулы, вшитые Кс

	znachKc_1 = Explode_1[0].split('@&<>&@') # [u'Костыль для лифтов@@!!@@Лифты@@!!@@Кс.л.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.л@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&1$$>>$$1&&??&&1', u'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков@@!!@@Прочее@@!!@@Кс.гор.пищ.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.гор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&60&&??&&100&&??&&120$$>>$$0.9&&??&&0.85&&??&&0.75&&??&&0.65&&??&&0.6&&??&&0.5&&??&&0.45&&??&&0.4&&??&&0.3&&??&&0.3&&??&&0.25', u'Таблица 7.6 - Коэффициенты спроса для рабочего освещения@@!!@@Рабочее освещение@@!!@@Кс.о.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.раб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@5&&??&&10&&??&&15&&??&&25&&??&&50&&??&&100&&??&&200&&??&&400&&??&&500$$>>$$1&&??&&0.8&&??&&0.7&&??&&0.6&&??&&0.5&&??&&0.4&&??&&0.35&&??&&0.3&&??&&0.3', u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Ру.сантех.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4', u'ВАСЯ@@!!@@Прочее@@!!@@КСАРА@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Рр.сантех.@@!!@@Ру.раб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3@@!!@@Столбец 1. Удельный вес установленной мощности в других нагрузках (\)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников: (заполните далее эту строку)&&??&&1&&??&&2$$>>$$2&&??&&3&&??&&4$$>>$$99.4&&??&&77&&??&&88', u'qwerty@@!!@@Прочее@@!!@@kctestov@@!!@@eppower@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Рр (вся)@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&2$$>>$$3&&??&&4', u'ЦифирЬ@@!!@@Прочее@@!!@@Кс ЦИФРА@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру (вся)&&??&&Рр (вся)&&??&&Ру (без классиф.)&&??&&Рр (без классиф.)&&??&&Ру (др. классиф.)&&??&&Рр (др. классиф.)&&??&&Ру.л&&??&&Рр.сантех.&&??&&Рраб.осв.&&??&&Ргор.пищ.&&??&&Рр.ов&&??&&Ру.сантех.&&??&&Ру.раб.осв.&&??&&Ру.гор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&100$$>>$$0.7&&??&&0.7']
	znachP_1 = Explode_1[1].split('@&<>&@')
	znachUserFormula_1 = Explode_1[2].split('@&<>&@')
	All_koeffs_Output_Coded_1 = Explode_1[3].split('@&<>&@') # ['1001@@!!@@1', '1002@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600$$>>$$1000@@!!@@10.0$$>>$$5.1$$>>$$3.8$$>>$$3.2$$>>$$2.8$$>>$$2.6$$>>$$2.2$$>>$$1.95$$>>$$1.7$$>>$$1.5$$>>$$1.36$$>>$$1.27$$>>$$1.23$$>>$$1.19', '1003@@!!@@14$$>>$$20$$>>$$30$$>>$$40$$>>$$50$$>>$$60$$>>$$70@@!!@@0.8$$>>$$0.65$$>>$$0.6$$>>$$0.55$$>>$$0.5$$>>$$0.48$$>>$$0.45', '1004@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600@@!!@@1$$>>$$0.51$$>>$$0.38$$>>$$0.32$$>>$$0.29$$>>$$0.26$$>>$$0.24$$>>$$0.2$$>>$$0.18$$>>$$0.16$$>>$$0.14$$>>$$0.13$$>>$$0.11', '1005@@!!@@0.9', '1006@@!!@@1$$>>$$2$$>>$$3$$>>$$4$$>>$$5$$>>$$6$$>>$$10$$>>$$20$$>>$$25@@!!@@1$$>>$$0.8$$>>$$0.8$$>>$$0.7$$>>$$0.7$$>>$$0.65$$>>$$0.5$$>>$$0.4$$>>$$0.35@@!!@@1$$>>$$0.9$$>>$$0.9$$>>$$0.8$$>>$$0.8$$>>$$0.75$$>>$$0.6$$>>$$0.5$$>>$$0.4']

	# Первые трое готовы для записи в Хранилище. Осталось только их туда сохоанить:
	# Wrtite_to_ExtensibleStorage (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, List[str](znachKc_1))

	# А последний
	# ['1001@@!!@@1', '1002@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600$$>>$$1000@@!!@@10.0$$>>$$5.1$$>>$$3.8$$>>$$3.2$$>>$$2.8$$>>$$2.6$$>>$$2.2$$>>$$1.95$$>>$$1.7$$>>$$1.5$$>>$$1.36$$>>$$1.27$$>>$$1.23$$>>$$1.19', '1003@@!!@@14$$>>$$20$$>>$$30$$>>$$40$$>>$$50$$>>$$60$$>>$$70@@!!@@0.8$$>>$$0.65$$>>$$0.6$$>>$$0.55$$>>$$0.5$$>>$$0.48$$>>$$0.45', '1004@@!!@@5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600@@!!@@1$$>>$$0.51$$>>$$0.38$$>>$$0.32$$>>$$0.29$$>>$$0.26$$>>$$0.24$$>>$$0.2$$>>$$0.18$$>>$$0.16$$>>$$0.14$$>>$$0.13$$>>$$0.11', '1005@@!!@@0.9', '1006@@!!@@1$$>>$$2$$>>$$3$$>>$$4$$>>$$5$$>>$$6$$>>$$10$$>>$$20$$>>$$25@@!!@@1$$>>$$0.8$$>>$$0.8$$>>$$0.7$$>>$$0.7$$>>$$0.65$$>>$$0.5$$>>$$0.4$$>>$$0.35@@!!@@1$$>>$$0.9$$>>$$0.9$$>>$$0.8$$>>$$0.8$$>>$$0.75$$>>$$0.6$$>>$$0.5$$>>$$0.4']
	# Надо привести к виду
	# [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
	All_koeffs_Output_Coded_2 = [] # [['1001', '1'], ['1002', '5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600$$>>$$1000', '10.0$$>>$$5.1$$>>$$3.8$$>>$$3.2$$>>$$2.8$$>>$$2.6$$>>$$2.2$$>>$$1.95$$>>$$1.7$$>>$$1.5$$>>$$1.36$$>>$$1.27$$>>$$1.23$$>>$$1.19'], ['1003', '14$$>>$$20$$>>$$30$$>>$$40$$>>$$50$$>>$$60$$>>$$70', '0.8$$>>$$0.65$$>>$$0.6$$>>$$0.55$$>>$$0.5$$>>$$0.48$$>>$$0.45'], ['1004', '5$$>>$$6$$>>$$9$$>>$$12$$>>$$15$$>>$$18$$>>$$24$$>>$$40$$>>$$60$$>>$$100$$>>$$200$$>>$$400$$>>$$600', '1$$>>$$0.51$$>>$$0.38$$>>$$0.32$$>>$$0.29$$>>$$0.26$$>>$$0.24$$>>$$0.2$$>>$$0.18$$>>$$0.16$$>>$$0.14$$>>$$0.13$$>>$$0.11'], ['1005', '0.9'], ['1006', '1$$>>$$2$$>>$$3$$>>$$4$$>>$$5$$>>$$6$$>>$$10$$>>$$20$$>>$$25', '1$$>>$$0.8$$>>$$0.8$$>>$$0.7$$>>$$0.7$$>>$$0.65$$>>$$0.5$$>>$$0.4$$>>$$0.35', '1$$>>$$0.9$$>>$$0.9$$>>$$0.8$$>>$$0.8$$>>$$0.75$$>>$$0.6$$>>$$0.5$$>>$$0.4']]
	for i in All_koeffs_Output_Coded_1:
		All_koeffs_Output_Coded_2.append(i.split('@@!!@@'))
	All_koeffs_Output_Coded_3 = [] # Вид: [['1001', '1'], ['1002', ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], ['1003', ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], ['1004', ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], ['1005', '0.9'], ['1006', ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
	for i in All_koeffs_Output_Coded_2:
		cur_lst = []
		for j in i:
			if len(j.split('$$>>$$')) > 1:
				cur_lst.append(j.split('$$>>$$'))
			else:
				cur_lst.append(j)
		All_koeffs_Output_Coded_3.append(cur_lst)
	# И осталось везде нулевые элементы перевести в integer
	All_koeffs_Output_Coded_4 = [] # Вид: [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
	for i in All_koeffs_Output_Coded_3:
		cur_lst = []
		for n, j in enumerate(i):
			if n == 0:
				cur_lst.append(int(j))
			else:
				cur_lst.append(j)
		All_koeffs_Output_Coded_4.append(cur_lst)

	return znachKc_1, znachP_1, znachUserFormula_1, All_koeffs_Output_Coded_4

# [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
# [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '0.32', '0.29', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.9', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]









All_koeffs_Output = [i for i in All_koeffs] # Выходной список с данными из формы Кс. Сначала приравняем исходному, потом будем в нём заменять элементы.

global Kc_Storage_Form_Button_Cancel_pushed # Переменная чтобы понять нажал ли Пользователь "Сохранить"
Kc_Storage_Form_Button_Cancel_pushed = 1
ImportKcButtonPushed = False # Нажата ли кнопка Импорта Кс, Р, формул


# _______________Окошко коэффициентов спроса_______________________________________________________

class Kc_Storage_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Cancel_button = System.Windows.Forms.Button()
		self._SaveandClose_button = System.Windows.Forms.Button()
		self._KcList_dataGridView = System.Windows.Forms.DataGridView()
		self._KcList_label = System.Windows.Forms.Label()
		self._CurKc_dataGridView = System.Windows.Forms.DataGridView()
		self._CurKc_label = System.Windows.Forms.Label()
		self._ByDefault_button = System.Windows.Forms.Button()
		self._CreateUserKc_button = System.Windows.Forms.Button()
		self._KcList_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._KcList_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._KcList_Column3 = System.Windows.Forms.DataGridViewButtonColumn()
		self._EquationEditor_button = System.Windows.Forms.Button()
		self._Export_button = System.Windows.Forms.Button()
		self._Import_button = System.Windows.Forms.Button()
		self._KcList_dataGridView.BeginInit()
		self._CurKc_dataGridView.BeginInit()
		self.SuspendLayout()
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(826, 608)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 0
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# SaveandClose_button
		# 
		self._SaveandClose_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SaveandClose_button.Location = System.Drawing.Point(26, 608)
		self._SaveandClose_button.Name = "SaveandClose_button"
		self._SaveandClose_button.Size = System.Drawing.Size(156, 23)
		self._SaveandClose_button.TabIndex = 1
		self._SaveandClose_button.Text = "Сохранить и закрыть"
		self._SaveandClose_button.UseVisualStyleBackColor = True
		self._SaveandClose_button.Click += self.SaveandClose_buttonClick
		# 
		# KcList_dataGridView
		# 
		self._KcList_dataGridView.AllowUserToAddRows = False
		self._KcList_dataGridView.AllowUserToDeleteRows = False
		self._KcList_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._KcList_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._KcList_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._KcList_Column1,
			self._KcList_Column2,
			self._KcList_Column3]))
		self._KcList_dataGridView.Location = System.Drawing.Point(26, 39)
		self._KcList_dataGridView.Name = "KcList_dataGridView"
		self._KcList_dataGridView.ReadOnly = True
		self._KcList_dataGridView.RowTemplate.Height = 24
		self._KcList_dataGridView.Size = System.Drawing.Size(875, 202)
		self._KcList_dataGridView.TabIndex = 2
		self._KcList_dataGridView.CellContentClick += self.KcList_dataGridViewCellContentClick
		# 
		# KcList_label
		# 
		self._KcList_label.Location = System.Drawing.Point(26, 13)
		self._KcList_label.Name = "KcList_label"
		self._KcList_label.Size = System.Drawing.Size(777, 23)
		self._KcList_label.TabIndex = 3
		self._KcList_label.Text = "Список поддерживаемых коэффициентов спроса для различных нагрузок:"
		# 
		# CurKc_dataGridView
		# 
		self._CurKc_dataGridView.AllowUserToAddRows = False
		self._CurKc_dataGridView.AllowUserToDeleteRows = False
		self._CurKc_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._CurKc_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._CurKc_dataGridView.Location = System.Drawing.Point(26, 346)
		self._CurKc_dataGridView.Name = "CurKc_dataGridView"
		self._CurKc_dataGridView.RowTemplate.Height = 24
		self._CurKc_dataGridView.Size = System.Drawing.Size(875, 235)
		self._CurKc_dataGridView.TabIndex = 4
		self._CurKc_dataGridView.CellContentClick += self.CurKc_dataGridViewCellContentClick
		self._CurKc_dataGridView.CellLeave += self.CurKc_dataGridViewCellLeave
		self._CurKc_dataGridView.CellValueChanged += self.CurKc_dataGridViewCellValueChanged
		# 
		# CurKc_label
		# 
		self._CurKc_label.Location = System.Drawing.Point(26, 302)
		self._CurKc_label.Name = "CurKc_label"
		self._CurKc_label.Size = System.Drawing.Size(777, 41)
		self._CurKc_label.TabIndex = 5
		self._CurKc_label.Text = "Текущая таблица:"
		# 
		# ByDefault_button
		# 
		self._ByDefault_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._ByDefault_button.Location = System.Drawing.Point(603, 608)
		self._ByDefault_button.Name = "ByDefault_button"
		self._ByDefault_button.Size = System.Drawing.Size(116, 23)
		self._ByDefault_button.TabIndex = 6
		self._ByDefault_button.Text = "По умолчанию"
		self._ByDefault_button.UseVisualStyleBackColor = True
		self._ByDefault_button.Click += self.ByDefault_buttonClick
		# 
		# CreateUserKc_button
		# 
		self._CreateUserKc_button.Location = System.Drawing.Point(26, 262)
		self._CreateUserKc_button.Name = "CreateUserKc_button"
		self._CreateUserKc_button.Size = System.Drawing.Size(137, 23)
		self._CreateUserKc_button.TabIndex = 7
		self._CreateUserKc_button.Text = "Создать новый Кс"
		self._CreateUserKc_button.UseVisualStyleBackColor = True
		self._CreateUserKc_button.Visible = False
		self._CreateUserKc_button.Click += self.CreateUserKc_buttonClick
		# 
		# KcList_Column1
		# 
		self._KcList_Column1.HeaderText = "Тип нагрузки"
		self._KcList_Column1.Name = "KcList_Column1"
		self._KcList_Column1.ReadOnly = True
		self._KcList_Column1.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.NotSortable
		# 
		# KcList_Column2
		# 
		self._KcList_Column2.HeaderText = "Описание"
		self._KcList_Column2.Name = "KcList_Column2"
		self._KcList_Column2.ReadOnly = True
		self._KcList_Column2.SortMode = System.Windows.Forms.DataGridViewColumnSortMode.NotSortable
		self._KcList_Column2.Width = 500
		# 
		# KcList_Column3
		# 
		self._KcList_Column3.HeaderText = "Сформировать таблицу"
		self._KcList_Column3.Name = "KcList_Column3"
		self._KcList_Column3.ReadOnly = True
		self._KcList_Column3.Resizable = System.Windows.Forms.DataGridViewTriState.True
		self._KcList_Column3.Text = "Показать"
		# 
		# EquationEditor_button
		# 
		self._EquationEditor_button.Location = System.Drawing.Point(390, 262)
		self._EquationEditor_button.Name = "EquationEditor_button"
		self._EquationEditor_button.Size = System.Drawing.Size(153, 23)
		self._EquationEditor_button.TabIndex = 9
		self._EquationEditor_button.Text = "Редактор формул"
		self._EquationEditor_button.UseVisualStyleBackColor = True
		self._EquationEditor_button.Click += self.EquationEditor_buttonClick
		# 
		# Export_button
		# 
		self._Export_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Export_button.Location = System.Drawing.Point(427, 608)
		self._Export_button.Name = "Export_button"
		self._Export_button.Size = System.Drawing.Size(116, 23)
		self._Export_button.TabIndex = 10
		self._Export_button.Text = "Экспорт"
		self._Export_button.UseVisualStyleBackColor = True
		self._Export_button.Click += self.Export_buttonClick
		# 
		# Import_button
		# 
		self._Import_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Import_button.Location = System.Drawing.Point(245, 608)
		self._Import_button.Name = "Import_button"
		self._Import_button.Size = System.Drawing.Size(116, 23)
		self._Import_button.TabIndex = 11
		self._Import_button.Text = "Импорт"
		self._Import_button.UseVisualStyleBackColor = True
		self._Import_button.Click += self.Import_buttonClick
		# 
		# Kc_Storage_Form
		# 
		self.ClientSize = System.Drawing.Size(934, 643)
		self.Controls.Add(self._Import_button)
		self.Controls.Add(self._Export_button)
		self.Controls.Add(self._EquationEditor_button)
		self.Controls.Add(self._CreateUserKc_button)
		self.Controls.Add(self._ByDefault_button)
		self.Controls.Add(self._CurKc_label)
		self.Controls.Add(self._CurKc_dataGridView)
		self.Controls.Add(self._KcList_label)
		self.Controls.Add(self._KcList_dataGridView)
		self.Controls.Add(self._SaveandClose_button)
		self.Controls.Add(self._Cancel_button)
		self.MinimumSize = System.Drawing.Size(719, 500)
		self.Name = "Kc_Storage_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Коэффициенты спроса"
		self.Load += self.Kc_Storage_FormLoad
		self._KcList_dataGridView.EndInit()
		self._CurKc_dataGridView.EndInit()
		self.ResumeLayout(False)

		self.Icon = iconmy


	def Kc_Storage_FormLoad(self, sender, e):
		# Заполняем таблицу списком Кс
		Kc_Storage_FormLoad_Func(self._KcList_dataGridView, Kc_descriptions, Readable_znachKc, 'Показать')
		
	def Cancel_buttonClick(self, sender, e):
		self.Close()

	def CurKc_dataGridViewCellLeave(self, sender, e): # событие ухода фокуса из ячейки
		pass

	def CurKc_dataGridViewCellContentClick(self, sender, e): # событие клика в ячейке
		pass

	def ByDefault_buttonClick(self, sender, e):
		td = TaskDialog('По умолчанию')
		td.MainContent = 'Выставить данные во всех таблицах по умлочанию?'
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Да')
		td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Нет')
		GetUserResult = td.Show()
		if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
			global All_koeffs_Output
			All_koeffs_Output = [i for i in All_koeffs_byDefault]
			# Узнаём какой же коэффициент пользователь захотел показать
			selected_code = Kc_descriptions[self._KcList_dataGridView.CurrentCell.RowIndex][0] # вид 1001
			# Удаляем все строки и столбцы из таблицы текущих Кс
			a = self._CurKc_dataGridView.Rows.Count
			while a > 0:
				self._CurKc_dataGridView.Rows.RemoveAt(0)
				a = a - 1
			a = self._CurKc_dataGridView.Columns.Count
			while a > 0:
				self._CurKc_dataGridView.Columns.RemoveAt(0)
				a = a - 1
			self._CurKc_label.Text = 'Текущая таблица:'
			# Ищем нужные данные и заполняем текущую таблицу:
			Fill_curKc_Table(All_koeffs_Output, selected_code, self._CurKc_dataGridView, self._CurKc_label, Kc_descriptions)
		elif GetUserResult == TaskDialogResult.CommandLink2:
			pass


	def CurKc_dataGridViewCellValueChanged(self, sender, e): # событие изменения содержимого ячейки
		# При изменении данных в ячейках таблиц с Кс мы будем обновлять список All_koeffs_Output,
		# а сохранять будем только по кнопке Сохранить
		# Узнаём какой же коэффициент пользователь захотел показать
		selected_code = Kc_descriptions[self._KcList_dataGridView.CurrentCell.RowIndex][0] # вид 1001
		# Забираем данные с текущей таблицы Кс:
		All_koeffs_Output_hlp = [i for i in TakeDataFrom_curKc_Table(All_koeffs_Output, selected_code, self._CurKc_dataGridView)]
		global All_koeffs_Output
		All_koeffs_Output = [i for i in All_koeffs_Output_hlp]


	def KcList_dataGridViewCellContentClick(self, sender, e):
		# Обрабатываем нажатие кнопок "Показать"
		if self._KcList_dataGridView.CurrentCell.ColumnIndex == 2 and self._KcList_dataGridView.CurrentCell.RowIndex != -1:
			# сначала удаляем все строки и столбцы из таблицы текущих Кс
			dataGridView_Clear(self._CurKc_dataGridView) # Очищаем таблицу
			self._CurKc_label.Text = 'Текущая таблица:'
			# Узнаём какой же коэффициент пользователь захотел показать
			try: # если пользователь захотел посмотреть Кс которые были вшиты
				selected_code = Kc_descriptions[self._KcList_dataGridView.CurrentCell.RowIndex][0] # вид 1001
				# Ищем нужные данные и заполняем текущую таблицу:
				Fill_curKc_Table(All_koeffs_Output, selected_code, self._CurKc_dataGridView, self._CurKc_label, Kc_descriptions)
			except IndexError: # если он хочет посмотреть собственные Кс 
				# Чтобы понять по какой кнопке пользователь попал в окно пользовательских Кс выставим соответствующую вспомогательную метку
				# Она же заодно и имя выбранной пользователем таблицы
				global EnterUserKcShow # 'Арина таблица'
				EnterUserKcShow = self._KcList_dataGridView[1, self._KcList_dataGridView.CurrentCell.RowIndex].Value # Вход в окно пользовательских Кс был по кнопке "Показать"
				UserKcForm().ShowDialog()
				znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
				Readable_znachKc = UserKcTablesDecoding(znachKc) # Декодируем список с данными в приличный вид
				# Удаляем все строки из списка Кс
				a = self._KcList_dataGridView.Rows.Count
				while a > 0:
					self._KcList_dataGridView.Rows.RemoveAt(0)
					a = a - 1
				# Заполняем таблицу списком Кс (как при загрузке формы)
				Kc_Storage_FormLoad_Func(self._KcList_dataGridView, Kc_descriptions, Readable_znachKc, 'Показать')
				# Обнуляем маркер нажатия ОК
				global IsOkPushed_UserKc
				IsOkPushed_UserKc = False


	def CreateUserKc_buttonClick(self, sender, e): # Кнопка сейчас скрыта
		pass
		'''
		UserKcForm().ShowDialog()
		#__Если нажали ОК в окне пользовательских Кс____________
		if IsOkPushed_UserKc == True:
			# Удаляем все строки и столбцы из таблицы текущих Кс
			dataGridView_Clear(self._CurKc_dataGridView) # Очищаем таблицу
			self._CurKc_label.Text = 'Текущая таблица:'
			znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
			Readable_znachKc = UserKcTablesDecoding(znachKc) # Декодируем список с данными в приличный вид
			# Удаляем все строки из списка Кс
			a = self._KcList_dataGridView.Rows.Count
			while a > 0:
				self._KcList_dataGridView.Rows.RemoveAt(0)
				a = a - 1
			# Заполняем таблицу списком Кс (как при загрузке формы)
			Kc_Storage_FormLoad_Func(self._KcList_dataGridView, Kc_descriptions, Readable_znachKc, 'Показать')
			# Обнуляем маркер нажатия ОК
			global IsOkPushed_UserKc
			IsOkPushed_UserKc = False
			'''

	def Import_buttonClick(self, sender, e):
		try:
			Exit_Cortage = Import_All_Kc_P_Formula()
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc, SchemaName_for_UserKc, List[str](Exit_Cortage[0]))
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP, SchemaName_for_UserP, List[str](Exit_Cortage[1]))
			Wrtite_to_ExtensibleStorage (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula, SchemaName_for_UserFormula, List[str](Exit_Cortage[2])) 
			# Ну и наши многострадальные вшитые Кс:
			# Надо раздербанить Exit_Cortage[3] (аналог All_koeffs_Output) на отдельные списки готовые для записи в Хранилище
			global All_koeffs_Output
			All_koeffs_Output = Exit_Cortage[3]
			Kkr_flats_koefficient = All_koeffs_Output[0][1]
			Flat_count_SP = [i for i in All_koeffs_Output[1][1]]
			Flat_unit_wattage_SP = [i for i in All_koeffs_Output[1][2]]
			Py_high_comfort = [i for i in All_koeffs_Output[2][1]]
			Ks_high_comfort = [i for i in All_koeffs_Output[2][2]]
			Flat_count_high_comfort = [i for i in All_koeffs_Output[3][1]]
			Ko_high_comfort = [i for i in All_koeffs_Output[3][2]]
			Kcpwrres = All_koeffs_Output[4][1]
			Elevator_count_SP = [i for i in All_koeffs_Output[5][1]]
			Ks_elevators_below12 = [i for i in All_koeffs_Output[5][2]]
			Ks_elevators_above12 = [i for i in All_koeffs_Output[5][3]]
			# Пишем данные в Хранилище
			Write_several_fields_to_ExtensibleStorage (schemaGuid_for_Kc_Storage, ProjectInfoObject, SchemaName_for_Kc, 
			FieldName_for_Kc_1, [Kkr_flats_koefficient], 
			FieldName_for_Kc_2, [str(i) for i in Flat_count_SP],
			FieldName_for_Kc_3, [str(i) for i in Flat_unit_wattage_SP], 
			FieldName_for_Kc_4, [str(i) for i in Py_high_comfort],
			FieldName_for_Kc_5, [str(i) for i in Ks_high_comfort],
			FieldName_for_Kc_6, [str(i) for i in Flat_count_high_comfort],
			FieldName_for_Kc_7, [str(i) for i in Ko_high_comfort],
			FieldName_for_Kc_8, [Kcpwrres],
			FieldName_for_Kc_9, [str(i) for i in Elevator_count_SP],
			FieldName_for_Kc_10, [str(i) for i in Ks_elevators_below12],
			FieldName_for_Kc_11, [str(i) for i in Ks_elevators_above12],
			FieldName_for_Kc_12, Load_Class_elevators,
			FieldName_for_Kc_13, Load_Class_falts,
			FieldName_for_Kc_14, [str(i) for i in Ks_Reserve_1],
			FieldName_for_Kc_15, [str(i) for i in Ks_Reserve_2]
			)
			TaskDialog.Show('Настройки', 'Данные успешно импортированы. Перезапустите пожалуйста данное окно.')
			global ImportKcButtonPushed
			ImportKcButtonPushed = True # Чтоб все окна настроек закрыть.
			self.Close()
		except:
			TaskDialog.Show('Настройки', 'Не удалось импортировать данные.')

	def Export_buttonClick(self, sender, e):
		# Обновим списки перед экспортом.
		znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
		znachP = Read_UserKc_fromES (schemaGuid_for_UserP, ProjectInfoObject, FieldName_for_UserP) # считываем данные о пользовательских мощностях из Хранилища
		znachUserFormula = Read_UserKc_fromES (schemaGuid_for_UserFormula, ProjectInfoObject, FieldName_for_UserFormula)
		Export_All_Kc_P_Formula(znachKc, znachP, znachUserFormula, All_koeffs_Output)

	def EquationEditor_buttonClick(self, sender, e):
		EquationForm().ShowDialog()
		#__Если нажали ОК в окне пользовательских Кс____________
		if IsOkPushed_UserKc == True:
			# Удаляем все строки и столбцы из таблицы текущих Кс
			dataGridView_Clear(self._CurKc_dataGridView) # Очищаем таблицу
			self._CurKc_label.Text = 'Текущая таблица:'
			znachKc = Read_UserKc_fromES(schemaGuid_for_UserKc, ProjectInfoObject, FieldName_for_UserKc) # считываем данные о пользовательских Кс из Хранилища
			Readable_znachKc = UserKcTablesDecoding(znachKc) # Декодируем список с данными в приличный вид
			# Удаляем все строки из списка Кс
			a = self._KcList_dataGridView.Rows.Count
			while a > 0:
				self._KcList_dataGridView.Rows.RemoveAt(0)
				a = a - 1
			# Заполняем таблицу списком Кс (как при загрузке формы)
			Kc_Storage_FormLoad_Func(self._KcList_dataGridView, Kc_descriptions, Readable_znachKc, 'Показать')
			# Обнуляем маркер нажатия ОК
			global IsOkPushed_UserKc
			IsOkPushed_UserKc = False


	def SaveandClose_buttonClick(self, sender, e):
		global Kc_Storage_Form_Button_Cancel_pushed
		Kc_Storage_Form_Button_Cancel_pushed = 0
		self.Close()



#Kc_Storage_Form().ShowDialog()













#_________________________________ Работаем с 8-м хранилищем (Запас свободного пространства в НКУ) ____________________________________________________________________________
schemaGuid_for_VolumeCapacityNKU = System.Guid(Guidstr_VolumeCapacityNKU) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Формируем список по умолчанию.
Storagelist_by_Default_for_VolumeCapacityNKU = List[str](['20'])


# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_VolumeCapacityNKU_Storage = Schema.Lookup(schemaGuid_for_VolumeCapacityNKU)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_VolumeCapacityNKU_Storage) будет <type 'NoneType'>
if sch_VolumeCapacityNKU_Storage is None or ProjectInfoObject.GetEntity(sch_VolumeCapacityNKU_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	# TaskDialog.Show('Настройки', 'Настройки норм освещённости не найдены или были повреждены.\n Будут созданы настройки норм освещённости по умолчанию.')
	# Пишем данные
	Wrtite_to_ExtensibleStorage (schemaGuid_for_VolumeCapacityNKU, ProjectInfoObject, FieldName_for_VolumeCapacityNKU, SchemaName_for_VolumeCapacityNKU, Storagelist_by_Default_for_VolumeCapacityNKU) # пишем данные в хранилище 


# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_VolumeCapacityNKU = Schema.Lookup(schemaGuid_for_VolumeCapacityNKU)
#Получаем Entity из элемента:
ent_VolumeCapacityNKU = ProjectInfoObject.GetEntity(sch_VolumeCapacityNKU)
#Уже знакомым способом получаем «поля»:
field_VolumeCapacityNKU_Storage = sch_VolumeCapacityNKU.GetField(FieldName_for_VolumeCapacityNKU)
#Для считывания значений используем метод Entity.Get:
znach_VolumeCapacityNKU = ent_VolumeCapacityNKU.Get[IList[str]](field_VolumeCapacityNKU_Storage) # выдаёт List[str](['a', 'list', 'of', 'strings'])

# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach_VolumeCapacityNKU]
znach_VolumeCapacityNKU = []
[znach_VolumeCapacityNKU.append(i) for i in CS_help] # ['20']


#_________________________________________________________________________________________________________________________________________________________





















#_________________________________ Работаем с 9-м хранилищем (Настройки выбора производителя) ____________________________________________________________________________
schemaGuid_for_ManufacturerSettings = System.Guid(Guidstr_ManufacturerSettings) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Формируем список по умолчанию.
Storagelist_by_Default_for_ManufacturerSettings = List[str](['Icn']) # Первый член списка одно из значений макс.отклюспособности: Icn, Icu, Ics


# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_ManufacturerSettings = Schema.Lookup(schemaGuid_for_ManufacturerSettings)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_ManufacturerSettings) будет <type 'NoneType'>
if sch_ManufacturerSettings is None or ProjectInfoObject.GetEntity(sch_ManufacturerSettings).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	# Пишем данные
	Wrtite_to_ExtensibleStorage (schemaGuid_for_ManufacturerSettings, ProjectInfoObject, FieldName_for_ManufacturerSettings, SchemaName_for_ManufacturerSettings, Storagelist_by_Default_for_ManufacturerSettings) # пишем данные в хранилище 




# Окно настроек выбора производителя

class ManufacturerSettings_Storage_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Cancel_button = System.Windows.Forms.Button()
		self._SaveAndClose_button = System.Windows.Forms.Button()
		self._Icn_radioButton = System.Windows.Forms.RadioButton()
		self._Icu_radioButton = System.Windows.Forms.RadioButton()
		self._Ics_radioButton = System.Windows.Forms.RadioButton()
		self._Breaking_capacity_label = System.Windows.Forms.Label()
		self.SuspendLayout()
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(297, 212)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 0
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# SaveAndClose_button
		# 
		self._SaveAndClose_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._SaveAndClose_button.Location = System.Drawing.Point(12, 212)
		self._SaveAndClose_button.Name = "SaveAndClose_button"
		self._SaveAndClose_button.Size = System.Drawing.Size(168, 23)
		self._SaveAndClose_button.TabIndex = 1
		self._SaveAndClose_button.Text = "Сохранить и закрыть"
		self._SaveAndClose_button.UseVisualStyleBackColor = True
		self._SaveAndClose_button.Click += self.SaveAndClose_buttonClick
		# 
		# Icn_radioButton
		# 
		self._Icn_radioButton.Location = System.Drawing.Point(11, 66)
		self._Icn_radioButton.Name = "Icn_radioButton"
		self._Icn_radioButton.Size = System.Drawing.Size(104, 24)
		self._Icn_radioButton.TabIndex = 2
		self._Icn_radioButton.TabStop = True
		self._Icn_radioButton.Text = "Icn"
		self._Icn_radioButton.UseVisualStyleBackColor = True
		# 
		# Icu_radioButton
		# 
		self._Icu_radioButton.Location = System.Drawing.Point(11, 96)
		self._Icu_radioButton.Name = "Icu_radioButton"
		self._Icu_radioButton.Size = System.Drawing.Size(104, 24)
		self._Icu_radioButton.TabIndex = 3
		self._Icu_radioButton.TabStop = True
		self._Icu_radioButton.Text = "Icu"
		self._Icu_radioButton.UseVisualStyleBackColor = True
		# 
		# Ics_radioButton
		# 
		self._Ics_radioButton.Location = System.Drawing.Point(11, 126)
		self._Ics_radioButton.Name = "Ics_radioButton"
		self._Ics_radioButton.Size = System.Drawing.Size(104, 24)
		self._Ics_radioButton.TabIndex = 4
		self._Ics_radioButton.TabStop = True
		self._Ics_radioButton.Text = "Ics"
		self._Ics_radioButton.UseVisualStyleBackColor = True
		# 
		# Breaking_capacity_label
		# 
		self._Breaking_capacity_label.Location = System.Drawing.Point(12, 9)
		self._Breaking_capacity_label.Name = "Breaking_capacity_label"
		self._Breaking_capacity_label.Size = System.Drawing.Size(203, 54)
		self._Breaking_capacity_label.TabIndex = 5
		self._Breaking_capacity_label.Text = "По какой максимальной отключающей способности выбирать аппараты?"
		# 
		# ManufacturerSettings_Storage_Form
		# 
		self.ClientSize = System.Drawing.Size(393, 247)
		self.Controls.Add(self._Breaking_capacity_label)
		self.Controls.Add(self._Ics_radioButton)
		self.Controls.Add(self._Icu_radioButton)
		self.Controls.Add(self._Icn_radioButton)
		self.Controls.Add(self._SaveAndClose_button)
		self.Controls.Add(self._Cancel_button)
		self.MinimumSize = System.Drawing.Size(411, 294)
		self.Name = "ManufacturerSettings_Storage_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Настройки выбора производителя"
		self.Load += self.ManufacturerSettings_Storage_FormLoad
		self.ResumeLayout(False)

		self.Icon = iconmy


	def ManufacturerSettings_Storage_FormLoad(self, sender, e):
		# Считываем данные из хранилища
		znach_ManufacturerSettings = Read_UserKc_fromES(schemaGuid_for_ManufacturerSettings, ProjectInfoObject, FieldName_for_ManufacturerSettings)
		Way_ofselecting_Breaking_capacity = znach_ManufacturerSettings[0]
		if Way_ofselecting_Breaking_capacity == 'Icu':
			self._Icu_radioButton.Checked = True
		elif Way_ofselecting_Breaking_capacity == 'Ics':
			self._Ics_radioButton.Checked = True
		else:
			self._Icn_radioButton.Checked = True # Это если Icn

		# Ставим всплывающие подсказки
		ToolTip().SetToolTip(self._Icn_radioButton, 'Номинальный выдерживаемый ток короткого замыкания') 
		ToolTip().SetToolTip(self._Icu_radioButton, 'Номинальная предельная отключающая способность при коротком замыкании') 
		ToolTip().SetToolTip(self._Ics_radioButton, 'Номинальная рабочая отключающая способность при коротком замыкании') 

	def SaveAndClose_buttonClick(self, sender, e):
		# Забираем по какому значению выбирать макс. откл. способность
		if self._Icn_radioButton.Checked == True:
			Way_ofselecting_Breaking_capacity = 'Icn'
		elif self._Icu_radioButton.Checked == True:
			Way_ofselecting_Breaking_capacity = 'Icu'
		elif self._Ics_radioButton.Checked == True:
			Way_ofselecting_Breaking_capacity = 'Ics'

		Storagelist_for_ManufacturerSettings = List[str]([Way_ofselecting_Breaking_capacity])
		Wrtite_to_ExtensibleStorage (schemaGuid_for_ManufacturerSettings, ProjectInfoObject, FieldName_for_ManufacturerSettings, SchemaName_for_ManufacturerSettings, Storagelist_for_ManufacturerSettings) # пишем данные в хранилище
		self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()





#_________________________________________________________________________________________________________________________________________________________




















#____________Работа с дополнительными настройками Теслы__________________________________________________________________________________________

#________10-е хранилище. Дополнительные настройки Теслы________________________
schemaGuid_for_AdvancedSettings = System.Guid(Guidstr_AdvancedSettings) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Формируем список по умолчанию.
Storagelist_by_Default_for_AdvancedSettings = List[str](['0', 'Зайдите в Настройки@@!!@@И сформируйте список группировки@@!!@@', '1']) 
# 1 член: ConsidergroupingES на выходе должен быть True/False. Соответственно в хранилище будет '1'/'0'
# 2 член: groupingorderlist список с группировкой. По умолчанию: ['Неспецифицируемые элементы', 'Осветительное оборудование', '']
# разделение членов этого списка: @@!!@@ - Разделитель между членами этого списка
# ara.split('@@!!@@') превращает строку в список
# '@@!!@@'.join(ara1) превращает список в строку
# 3 член: With_empty_strings значение True # по умолчанию не убирать пустые строки. В списке '1'/'0'

# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_AdvancedSettings = Schema.Lookup(schemaGuid_for_AdvancedSettings)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_AdvancedSettings) будет <type 'NoneType'>
if sch_AdvancedSettings is None or ProjectInfoObject.GetEntity(sch_AdvancedSettings).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	# Пишем данные
	Wrtite_to_ExtensibleStorage (schemaGuid_for_AdvancedSettings, ProjectInfoObject, FieldName_for_AdvancedSettings, SchemaName_for_AdvancedSettings, Storagelist_by_Default_for_AdvancedSettings) # пишем данные в хранилище 



# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_AdvancedSettings = Schema.Lookup(schemaGuid_for_AdvancedSettings)
#Получаем Entity из элемента:
ent_AdvancedSettings = ProjectInfoObject.GetEntity(sch_AdvancedSettings)
#Уже знакомым способом получаем «поля»:
field_AdvancedSettings = sch_AdvancedSettings.GetField(FieldName_for_AdvancedSettings)
#Для считывания значений используем метод Entity.Get:
znach_AdvancedSettings = ent_AdvancedSettings.Get[IList[str]](field_AdvancedSettings) # выдаёт List[str](['a', 'list', 'of', 'strings'])

# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach_AdvancedSettings]
znach_AdvancedSettings = []
[znach_AdvancedSettings.append(i) for i in CS_help] 


# Сформируем список со всеми значениями параметра Param_ADSK_grouping в модели
# Для этого соберём все семейства категорий, входящих в спецификацию. Кроме типовых аннотаций, их не надо.
AllspecifiedFamilies = []
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i)
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_LightingFixtures).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_LightingDevices).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_DataDevices).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalFixtures).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_CableTray).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_CableTrayFitting).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_GenericModel).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 
for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Conduit).WhereElementIsNotElementType().ToElements():
	AllspecifiedFamilies.append(i) 

# Функция получения типа кабельного лотка по элементу кабельный лоток. Такие же точно как в проге Спецификация.
# На входе элемент кабельный лоток <Autodesk.Revit.DB.Electrical.CableTray object at 0x0000000000000048 [Autodesk.Revit.DB.Electrical.CableTray]>
# На выходе его тип.
# Обращение: GetCableTrayTypeFromElementId(elems_of_specified_category[0])
def GetCableTrayTypeFromElementId (elem_CableTray):
	for i in FilteredElementCollector(doc).OfClass(Electrical.CableTrayType).ToElements(): # все типы кабельных лотков в модели
		if i.Id == elem_CableTray.GetTypeId(): # Вид: <Autodesk.Revit.DB.ElementId object at 0x0000000000000091 [1733140]>
			return i
# Такая же функция для коробов
def GetConduitTypeFromElementId (elem_Conduit):
	for i in FilteredElementCollector(doc).OfClass(Electrical.ConduitType).ToElements(): # все типы кабельных лотков в модели
		if i.Id == elem_Conduit.GetTypeId(): # Вид: <Autodesk.Revit.DB.ElementId object at 0x0000000000000091 [1733140]>
			return i

# Вытащим значения параметра Param_ADSK_grouping в отдельный список. Причём 'Электрооборудование' всегда первое.
Allgroupinginmodel = ['Электрооборудование'] # Вид: ['Электрооборудование', u'Неспецифицируемые элементы', '', u'Розеточки', u'Кабеленесущие конструкции']
groupinginmodelAlert = [] # Предупреждение об ошибке если нет параметра
for i in AllspecifiedFamilies:
	if Param_ADSK_grouping in [p.Definition.Name for p in i.Parameters]:
		curparamvalue = i.LookupParameter(Param_ADSK_grouping).AsString() # текущее значение параметра
		if curparamvalue not in Allgroupinginmodel:
			Allgroupinginmodel.append(curparamvalue)
	else:
		try:
			if Param_ADSK_grouping in [p.Definition.Name for p in i.Symbol.Parameters]:
				curparamvalue = i.Symbol.LookupParameter(Param_ADSK_grouping).AsString()
				if curparamvalue not in Allgroupinginmodel:
					Allgroupinginmodel.append(curparamvalue)
		except System.MissingMemberException: # ловим: Exception : System.MissingMemberException: 'NoneType' object has no attribute 'Parameters'
			try:
				if Param_ADSK_grouping in [p.Definition.Name for p in GetCableTrayTypeFromElementId(i).Parameters]:
					curparamvalue = GetCableTrayTypeFromElementId(i).LookupParameter(Param_ADSK_grouping).AsString()
					if curparamvalue not in Allgroupinginmodel:
						Allgroupinginmodel.append(curparamvalue)
			except AttributeError: # ловим: AttributeError: 'NoneType' object has no attribute 'Parameters'. 
				try:
					if Param_ADSK_grouping in [p.Definition.Name for p in GetConduitTypeFromElementId(i).Parameters]:
						curparamvalue = GetConduitTypeFromElementId(i).LookupParameter(Param_ADSK_grouping).AsString()
						if curparamvalue not in Allgroupinginmodel:
							Allgroupinginmodel.append(curparamvalue)
				except: # если нет параметра Param_ADSK_grouping нигде
					if i.Name not in groupinginmodelAlert:
						groupinginmodelAlert.append(i.Name)
						groupinginmodelAlert.append(i.Category.Name)

# Выводим предупреждение:
if groupinginmodelAlert != []:
	TaskDialog.Show('Настройки', 'Параметр "' + Param_ADSK_grouping + '" не найден у следующих семейств следующих категорий: ' + ', '.join(groupinginmodelAlert) + '. Эти семейства могут некорректно специфицироваться. Рекомендуем добавить параметр "' + Param_ADSK_grouping + '" ко всем семействам в модели.')

Allgroupinginmodel = list(map(lambda x: x if x != None else '', Allgroupinginmodel)) # заменяем None на ''
# Выкидываем дублирующиеся ''
while Allgroupinginmodel.count('') > 1:
	Allgroupinginmodel.remove('')
# Последняя строка всегда будет 'Кабельные изделия'
Allgroupinginmodel.append('Кабельные изделия')

# теперь сделаем проверку. Вдруг в Allgroupinginmodel не то же самое что в Хранилище. Тогда предупредим пользователя.
Alerttext = 'Списки группировок в Настройках и в модели не соответствуют друг другу.'
groupingorderlist = znach_AdvancedSettings[1].split('@@!!@@')
hlpstr = ''
for i in Allgroupinginmodel:
	if i not in groupingorderlist:
		hlpstr = hlpstr + i + ', '
hlpstr[:-2] # убираем последние ', '
if hlpstr != '':
	Alerttext = Alerttext + ' В модели есть группировки которых нет в Настройках: ' + hlpstr + '.'
hlpstr = ''
for i in groupingorderlist:
	if i not in Allgroupinginmodel:
		hlpstr = hlpstr + i + ', '
hlpstr[:-2] # убираем последние ', '
if hlpstr != '':
	Alerttext = Alerttext + ' В Настройках есть группировки которых нет в модели: ' + hlpstr + '.'
if len(Alerttext) > 71: # если есть несоответствие списков
	Alerttext = Alerttext + ' Список группировок в данном окне был обновлён данными из модели.'



# Функция перемещаения ряда в таблице вверх или вниз
# на входе сама таблица и смещение. (-1 при движении вверх), (+1 при движении вниз). upborder, downborder границы до которых разрешается перемещение, направление движения строки
def DataGridViewMoveRow (dgv, offset, upborder, downborder, direction):
	currowindex = dgv.CurrentCell.RowIndex # индекс текущей строки
	currow = dgv.CurrentRow # текущая строка
	if direction == 'up':
		if currowindex >= upborder: # двигать выше 2-й строки нельзя, т.к. там всегда должно быть Электрооборудование
			dgv.Rows.Remove(currow) # удаляем текущую строку
			dgv.Rows.Insert(currowindex + offset, currow) # добавляем эту строку в нужное место
			dgv.CurrentCell = dgv.Rows[currowindex + offset].Cells[0] # оставляем выбранной ту же самую строку
	if direction == 'down':
		if currowindex < downborder: # двигать ниже последней строки нельзя, т.к. там всегда должно быть Кабельные изделия
			dgv.Rows.Remove(currow) # удаляем текущую строку
			dgv.Rows.Insert(currowindex + offset, currow) # добавляем эту строку в нужное место
			dgv.CurrentCell = dgv.Rows[currowindex + offset].Cells[0] # оставляем выбранной ту же самую строку




#________________Диалоговое окно дополнительных настроек_____________________________________________________________________________________________

class AdvancedSettings_Form(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._SpecSettings_groupBox = System.Windows.Forms.GroupBox()
		self._Cancel_button = System.Windows.Forms.Button()
		self._OKsave_button = System.Windows.Forms.Button()
		self._AllowGrouping_checkBox = System.Windows.Forms.CheckBox()
		self._GrouppingList_dataGridView = System.Windows.Forms.DataGridView()
		self._GroupingValues_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._MoveUp_button = System.Windows.Forms.Button()
		self._MoveDown_button = System.Windows.Forms.Button()
		self._checkBox_EmptyStr = System.Windows.Forms.CheckBox()
		self._GrouppingList_label = System.Windows.Forms.Label()
		self._SpecSettings_groupBox.SuspendLayout()
		self._GrouppingList_dataGridView.BeginInit()
		self.SuspendLayout()
		# 
		# SpecSettings_groupBox
		# 
		self._SpecSettings_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._SpecSettings_groupBox.Controls.Add(self._GrouppingList_label)
		self._SpecSettings_groupBox.Controls.Add(self._checkBox_EmptyStr)
		self._SpecSettings_groupBox.Controls.Add(self._MoveDown_button)
		self._SpecSettings_groupBox.Controls.Add(self._MoveUp_button)
		self._SpecSettings_groupBox.Controls.Add(self._GrouppingList_dataGridView)
		self._SpecSettings_groupBox.Controls.Add(self._AllowGrouping_checkBox)
		self._SpecSettings_groupBox.Location = System.Drawing.Point(12, 12)
		self._SpecSettings_groupBox.Name = "SpecSettings_groupBox"
		self._SpecSettings_groupBox.Size = System.Drawing.Size(561, 338)
		self._SpecSettings_groupBox.TabIndex = 0
		self._SpecSettings_groupBox.TabStop = False
		self._SpecSettings_groupBox.Text = "Спецификация"
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(492, 416)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# OKsave_button
		# 
		self._OKsave_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OKsave_button.Location = System.Drawing.Point(12, 416)
		self._OKsave_button.Name = "OKsave_button"
		self._OKsave_button.Size = System.Drawing.Size(169, 23)
		self._OKsave_button.TabIndex = 2
		self._OKsave_button.Text = "Сохранить и закрыть"
		self._OKsave_button.UseVisualStyleBackColor = True
		self._OKsave_button.Click += self.OKsave_buttonClick
		# 
		# AllowGrouping_checkBox
		# 
		self._AllowGrouping_checkBox.Location = System.Drawing.Point(7, 31)
		self._AllowGrouping_checkBox.Name = "AllowGrouping_checkBox"
		self._AllowGrouping_checkBox.Size = System.Drawing.Size(472, 24)
		self._AllowGrouping_checkBox.TabIndex = 0
		self._AllowGrouping_checkBox.Text = "Группировать позиции по параметру"
		self._AllowGrouping_checkBox.UseVisualStyleBackColor = True
		# 
		# GrouppingList_dataGridView
		# 
		self._GrouppingList_dataGridView.AllowUserToAddRows = False
		self._GrouppingList_dataGridView.AllowUserToDeleteRows = False
		self._GrouppingList_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._GrouppingList_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._GrouppingList_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._GroupingValues_Column]))
		self._GrouppingList_dataGridView.Location = System.Drawing.Point(7, 129)
		self._GrouppingList_dataGridView.Name = "GrouppingList_dataGridView"
		self._GrouppingList_dataGridView.ReadOnly = True
		self._GrouppingList_dataGridView.RowTemplate.Height = 24
		self._GrouppingList_dataGridView.Size = System.Drawing.Size(404, 203)
		self._GrouppingList_dataGridView.TabIndex = 1
		# 
		# GroupingValues_Column
		# 
		self._GroupingValues_Column.HeaderText = "Значения параметра"
		self._GroupingValues_Column.Name = "GroupingValues_Column"
		self._GroupingValues_Column.ReadOnly = True
		self._GroupingValues_Column.Width = 350
		# 
		# MoveUp_button
		# 
		self._MoveUp_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._MoveUp_button.Location = System.Drawing.Point(434, 157)
		self._MoveUp_button.Name = "MoveUp_button"
		self._MoveUp_button.Size = System.Drawing.Size(121, 47)
		self._MoveUp_button.TabIndex = 2
		self._MoveUp_button.Text = "Переместить вверх"
		self._MoveUp_button.UseVisualStyleBackColor = True
		self._MoveUp_button.Click += self.MoveUp_buttonClick
		# 
		# MoveDown_button
		# 
		self._MoveDown_button.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right
		self._MoveDown_button.Location = System.Drawing.Point(434, 210)
		self._MoveDown_button.Name = "MoveDown_button"
		self._MoveDown_button.Size = System.Drawing.Size(121, 47)
		self._MoveDown_button.TabIndex = 3
		self._MoveDown_button.Text = "Переместить вниз"
		self._MoveDown_button.UseVisualStyleBackColor = True
		self._MoveDown_button.Click += self.MoveDown_buttonClick
		# 
		# checkBox_EmptyStr
		# 
		self._checkBox_EmptyStr.Location = System.Drawing.Point(7, 61)
		self._checkBox_EmptyStr.Name = "checkBox_EmptyStr"
		self._checkBox_EmptyStr.Size = System.Drawing.Size(472, 24)
		self._checkBox_EmptyStr.TabIndex = 4
		self._checkBox_EmptyStr.Text = "Разделять данные пустыми строками"
		self._checkBox_EmptyStr.UseVisualStyleBackColor = True
		# 
		# GrouppingList_label
		# 
		self._GrouppingList_label.Location = System.Drawing.Point(7, 101)
		self._GrouppingList_label.Name = "GrouppingList_label"
		self._GrouppingList_label.Size = System.Drawing.Size(404, 23)
		self._GrouppingList_label.TabIndex = 5
		self._GrouppingList_label.Text = "Таблица группировки позиций в спецификации:"
		# 
		# AdvancedSettings_Form
		# 
		self.ClientSize = System.Drawing.Size(585, 451)
		self.Controls.Add(self._OKsave_button)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._SpecSettings_groupBox)
		self.MinimumSize = System.Drawing.Size(603, 498)
		self.Name = "AdvancedSettings_Form"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Дополнительные настройки"
		self.Load += self.AdvancedSettings_FormLoad
		self._SpecSettings_groupBox.ResumeLayout(False)
		self._GrouppingList_dataGridView.EndInit()
		self.ResumeLayout(False)

		self.Icon = iconmy

	def AdvancedSettings_FormLoad(self, sender, e):
		self._AllowGrouping_checkBox.Text = 'Группировать позиции по параметру "' + Param_ADSK_grouping + '"'
		# Выставляем флажок группирования
		if znach_AdvancedSettings[0] == '1':
			self._AllowGrouping_checkBox.Checked = True
		else:
			self._AllowGrouping_checkBox.Checked = False
		# Выставляем флажок разделять пустыми строками
		if znach_AdvancedSettings[2] == '0':
			self._checkBox_EmptyStr.Checked = False
		else:
			self._checkBox_EmptyStr.Checked = True
		self._GroupingValues_Column.HeaderText = 'Значения параметра "' + Param_ADSK_grouping + '" в модели'
		if len(Alerttext) > 71: # если есть несоответствие списков
			for i in Allgroupinginmodel:
				self._GrouppingList_dataGridView.Rows.Add(i) # Заполняем таблицу исходными данными из модели
			TaskDialog.Show('Предупреждение', Alerttext)
		else:
			for i in groupingorderlist:
				self._GrouppingList_dataGridView.Rows.Add(i) # Заполняем таблицу исходными данными из хранилища

	def MoveUp_buttonClick(self, sender, e):
		offset = -1 # смещение (-1 при движении вверх)
		dgv = self._GrouppingList_dataGridView
		if dgv.CurrentCell.RowIndex != dgv.RowCount-1: # чтобы 'Электрооборудование' всегда осталось первым
			DataGridViewMoveRow(dgv, offset, 2, dgv.RowCount-2, 'up')

	def MoveDown_buttonClick(self, sender, e):
		offset = 1 # смещение (1 при движении вниз)
		dgv = self._GrouppingList_dataGridView
		if dgv.CurrentCell.RowIndex != 0: # чтобы 'Кабельные изделия' всегда остались последними
			DataGridViewMoveRow(dgv, offset, 2, dgv.RowCount-2, 'down')		

	def OKsave_buttonClick(self, sender, e):
		global Storagelist_for_AdvancedSettings
		Storagelist_for_AdvancedSettings = []
		# забираем значения флажка группировки
		if self._AllowGrouping_checkBox.Checked == True: 
			Storagelist_for_AdvancedSettings.append('1')
		else:
			Storagelist_for_AdvancedSettings.append('0')
		# забираем значения списка группировки
		dgv = self._GrouppingList_dataGridView
		hlp_lst = []
		for j in range(dgv.RowCount):
			hlp_lst.append(dgv[0, j].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		Storagelist_for_AdvancedSettings.append('@@!!@@'.join(hlp_lst))
		# забираем значения флажка разделять пустыми строками
		if self._checkBox_EmptyStr.Checked == False: 
			Storagelist_for_AdvancedSettings.append('0')
		else:
			Storagelist_for_AdvancedSettings.append('1')
		Wrtite_to_ExtensibleStorage (schemaGuid_for_AdvancedSettings, ProjectInfoObject, FieldName_for_AdvancedSettings, SchemaName_for_AdvancedSettings, Storagelist_for_AdvancedSettings)
		self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()


























#__________________________________________________________________________________________________________________________________________
#_______________________________ Основное диалоговое окно настроек Тэслы___________________________________________________________________



class TeslaSettings(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._OK_button = System.Windows.Forms.Button()
		self._Cancel_button = System.Windows.Forms.Button()
		self._Cable_section_calculation_method_groupBox = System.Windows.Forms.GroupBox()
		self._Cable_section_by_CBnominal_radioButton = System.Windows.Forms.RadioButton()
		self._Cable_section_by_rated_current_radioButton = System.Windows.Forms.RadioButton()
		self._Volt_Dropage_key_groupBox = System.Windows.Forms.GroupBox()
		self._Volt_Dropage_key_textBox = System.Windows.Forms.TextBox()
		self._Cable_stock_for_circuitry_groupBox = System.Windows.Forms.GroupBox()
		self._trackBar_Length_stock = System.Windows.Forms.TrackBar()
		self._textBox_Length_stock = System.Windows.Forms.TextBox()
		self._Electrical_Circuit_PathMode_groupBox = System.Windows.Forms.GroupBox()
		self._Electrical_Circuit_PathMode_radioButton3 = System.Windows.Forms.RadioButton()
		self._Electrical_Circuit_PathMode_radioButton2 = System.Windows.Forms.RadioButton()
		self._Electrical_Circuit_PathMode_radioButton1 = System.Windows.Forms.RadioButton()
		self._deltaU_boundary_value_groupBox = System.Windows.Forms.GroupBox()
		self._deltaU_boundary_value_textBox = System.Windows.Forms.TextBox()
		self._deltaU_boundary_value_label1 = System.Windows.Forms.Label()
		self._deltaU_boundary_value_label2 = System.Windows.Forms.Label()
		self._Settings_by_default_button = System.Windows.Forms.Button()
		self._Round_value_groupBox = System.Windows.Forms.GroupBox()
		self._Round_value_label2 = System.Windows.Forms.Label()
		self._Round_value_label1 = System.Windows.Forms.Label()
		self._Round_value_textBox = System.Windows.Forms.TextBox()
		self._DeltaUByGroupsShowForm_button = System.Windows.Forms.Button()
		self._Require_tables_select_groupBox = System.Windows.Forms.GroupBox()
		self._Require_tables_select_checkBox1 = System.Windows.Forms.CheckBox()
		self._Require_tables_select_checkBox2 = System.Windows.Forms.CheckBox()
		self._CalculationResoursesFormShow_button = System.Windows.Forms.Button()
		self._Electrical_Circuit_PathMode_radioButton4 = System.Windows.Forms.RadioButton()
		self._Select_Cable_by_DeltaU_checkBox = System.Windows.Forms.CheckBox()
		self._flat_calculation_way_groupBox = System.Windows.Forms.GroupBox()
		self._flat_calculation_way_radioButton1 = System.Windows.Forms.RadioButton()
		self._flat_calculation_way_radioButton2 = System.Windows.Forms.RadioButton()
		self._Param_Names_Storage_FormShow_button = System.Windows.Forms.Button()
		self._Illumination_Values_Storage_FormShow_button = System.Windows.Forms.Button()
		self._Import_button = System.Windows.Forms.Button()
		self._Export_button = System.Windows.Forms.Button()
		self._Kc_Storage_FormShow_button = System.Windows.Forms.Button()
		self._VolumeCapacityNKU_groupBox = System.Windows.Forms.GroupBox()
		self._textBox_VolumeCapacityNKU = System.Windows.Forms.TextBox()
		self._trackBar_VolumeCapacityNKU = System.Windows.Forms.TrackBar()
		self._ManufacturerSettings_Storage_FormShow_button = System.Windows.Forms.Button()
		self._Distributed_Volt_Dropage_koefficient_textBox = System.Windows.Forms.TextBox()
		self._Distributed_Volt_Dropage_koefficient_label = System.Windows.Forms.Label()
		self._PhaseNaming_groupBox = System.Windows.Forms.GroupBox()
		self._PhaseNaming_ABC_radioButton = System.Windows.Forms.RadioButton()
		self._PhaseNaming_L123_radioButton = System.Windows.Forms.RadioButton()
		self._AdvancedSettings_button = System.Windows.Forms.Button()
		self._Electrical_Circuit_PathMode_radioButton5 = System.Windows.Forms.RadioButton()
		self._Cable_section_calculation_method_groupBox.SuspendLayout()
		self._Volt_Dropage_key_groupBox.SuspendLayout()
		self._Cable_stock_for_circuitry_groupBox.SuspendLayout()
		self._trackBar_Length_stock.BeginInit()
		self._Electrical_Circuit_PathMode_groupBox.SuspendLayout()
		self._deltaU_boundary_value_groupBox.SuspendLayout()
		self._Round_value_groupBox.SuspendLayout()
		self._Require_tables_select_groupBox.SuspendLayout()
		self._flat_calculation_way_groupBox.SuspendLayout()
		self._VolumeCapacityNKU_groupBox.SuspendLayout()
		self._trackBar_VolumeCapacityNKU.BeginInit()
		self._PhaseNaming_groupBox.SuspendLayout()
		self.SuspendLayout()
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_button.Location = System.Drawing.Point(21, 788)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(255, 23)
		self._OK_button.TabIndex = 0
		self._OK_button.Text = "Сохранить и закрыть"
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(776, 788)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(112, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# Cable_section_calculation_method_groupBox
		# 
		self._Cable_section_calculation_method_groupBox.Controls.Add(self._Cable_section_by_rated_current_radioButton)
		self._Cable_section_calculation_method_groupBox.Controls.Add(self._Cable_section_by_CBnominal_radioButton)
		self._Cable_section_calculation_method_groupBox.Location = System.Drawing.Point(21, 12)
		self._Cable_section_calculation_method_groupBox.Name = "Cable_section_calculation_method_groupBox"
		self._Cable_section_calculation_method_groupBox.Size = System.Drawing.Size(434, 102)
		self._Cable_section_calculation_method_groupBox.TabIndex = 2
		self._Cable_section_calculation_method_groupBox.TabStop = False
		self._Cable_section_calculation_method_groupBox.Text = "Метод выбора сечений кабелей"
		# 
		# Cable_section_by_CBnominal_radioButton
		# 
		self._Cable_section_by_CBnominal_radioButton.Location = System.Drawing.Point(18, 65)
		self._Cable_section_by_CBnominal_radioButton.Name = "Cable_section_by_CBnominal_radioButton"
		self._Cable_section_by_CBnominal_radioButton.Size = System.Drawing.Size(410, 24)
		self._Cable_section_by_CBnominal_radioButton.TabIndex = 0
		self._Cable_section_by_CBnominal_radioButton.TabStop = True
		self._Cable_section_by_CBnominal_radioButton.Text = "По уставке аппарата защиты"
		self._Cable_section_by_CBnominal_radioButton.UseVisualStyleBackColor = True
		# 
		# Cable_section_by_rated_current_radioButton
		# 
		self._Cable_section_by_rated_current_radioButton.Location = System.Drawing.Point(18, 24)
		self._Cable_section_by_rated_current_radioButton.Name = "Cable_section_by_rated_current_radioButton"
		self._Cable_section_by_rated_current_radioButton.Size = System.Drawing.Size(410, 24)
		self._Cable_section_by_rated_current_radioButton.TabIndex = 1
		self._Cable_section_by_rated_current_radioButton.TabStop = True
		self._Cable_section_by_rated_current_radioButton.Text = "По току срабатывания аппарата защиты"
		self._Cable_section_by_rated_current_radioButton.UseVisualStyleBackColor = True
		# 
		# Volt_Dropage_key_groupBox
		# 
		self._Volt_Dropage_key_groupBox.Controls.Add(self._Distributed_Volt_Dropage_koefficient_label)
		self._Volt_Dropage_key_groupBox.Controls.Add(self._Distributed_Volt_Dropage_koefficient_textBox)
		self._Volt_Dropage_key_groupBox.Controls.Add(self._DeltaUByGroupsShowForm_button)
		self._Volt_Dropage_key_groupBox.Controls.Add(self._Volt_Dropage_key_textBox)
		self._Volt_Dropage_key_groupBox.Location = System.Drawing.Point(21, 120)
		self._Volt_Dropage_key_groupBox.Name = "Volt_Dropage_key_groupBox"
		self._Volt_Dropage_key_groupBox.Size = System.Drawing.Size(434, 222)
		self._Volt_Dropage_key_groupBox.TabIndex = 3
		self._Volt_Dropage_key_groupBox.TabStop = False
		self._Volt_Dropage_key_groupBox.Text = "Для каких нагрузок считать распределённые потери"
		# 
		# Volt_Dropage_key_textBox
		# 
		self._Volt_Dropage_key_textBox.Location = System.Drawing.Point(18, 32)
		self._Volt_Dropage_key_textBox.Multiline = True
		self._Volt_Dropage_key_textBox.Name = "Volt_Dropage_key_textBox"
		self._Volt_Dropage_key_textBox.Size = System.Drawing.Size(163, 148)
		self._Volt_Dropage_key_textBox.TabIndex = 0
		# 
		# Cable_stock_for_circuitry_groupBox
		# 
		self._Cable_stock_for_circuitry_groupBox.Controls.Add(self._textBox_Length_stock)
		self._Cable_stock_for_circuitry_groupBox.Controls.Add(self._trackBar_Length_stock)
		self._Cable_stock_for_circuitry_groupBox.Location = System.Drawing.Point(21, 348)
		self._Cable_stock_for_circuitry_groupBox.Name = "Cable_stock_for_circuitry_groupBox"
		self._Cable_stock_for_circuitry_groupBox.Size = System.Drawing.Size(434, 72)
		self._Cable_stock_for_circuitry_groupBox.TabIndex = 4
		self._Cable_stock_for_circuitry_groupBox.TabStop = False
		self._Cable_stock_for_circuitry_groupBox.Text = "Запас кабеля по умолчанию (в %)"
		# 
		# trackBar_Length_stock
		# 
		self._trackBar_Length_stock.Location = System.Drawing.Point(6, 23)
		self._trackBar_Length_stock.Name = "trackBar_Length_stock"
		self._trackBar_Length_stock.Size = System.Drawing.Size(146, 56)
		self._trackBar_Length_stock.TabIndex = 11
		self._trackBar_Length_stock.Value = 1
		self._trackBar_Length_stock.Scroll += self.TrackBar_Length_stockScroll
		# 
		# textBox_Length_stock
		# 
		self._textBox_Length_stock.Location = System.Drawing.Point(172, 23)
		self._textBox_Length_stock.Name = "textBox_Length_stock"
		self._textBox_Length_stock.Size = System.Drawing.Size(50, 22)
		self._textBox_Length_stock.TabIndex = 13
		self._textBox_Length_stock.Text = "10"
		self._textBox_Length_stock.TextChanged += self.TextBox_Length_stockTextChanged
		# 
		# Electrical_Circuit_PathMode_groupBox
		# 
		self._Electrical_Circuit_PathMode_groupBox.Controls.Add(self._Electrical_Circuit_PathMode_radioButton5)
		self._Electrical_Circuit_PathMode_groupBox.Controls.Add(self._Electrical_Circuit_PathMode_radioButton4)
		self._Electrical_Circuit_PathMode_groupBox.Controls.Add(self._Electrical_Circuit_PathMode_radioButton3)
		self._Electrical_Circuit_PathMode_groupBox.Controls.Add(self._Electrical_Circuit_PathMode_radioButton1)
		self._Electrical_Circuit_PathMode_groupBox.Controls.Add(self._Electrical_Circuit_PathMode_radioButton2)
		self._Electrical_Circuit_PathMode_groupBox.Location = System.Drawing.Point(477, 12)
		self._Electrical_Circuit_PathMode_groupBox.Name = "Electrical_Circuit_PathMode_groupBox"
		self._Electrical_Circuit_PathMode_groupBox.Size = System.Drawing.Size(416, 193)
		self._Electrical_Circuit_PathMode_groupBox.TabIndex = 3
		self._Electrical_Circuit_PathMode_groupBox.TabStop = False
		self._Electrical_Circuit_PathMode_groupBox.Text = "Режим траектории цепей"
		# 
		# Electrical_Circuit_PathMode_radioButton3
		# 
		self._Electrical_Circuit_PathMode_radioButton3.Location = System.Drawing.Point(18, 159)
		self._Electrical_Circuit_PathMode_radioButton3.Name = "Electrical_Circuit_PathMode_radioButton3"
		self._Electrical_Circuit_PathMode_radioButton3.Size = System.Drawing.Size(392, 24)
		self._Electrical_Circuit_PathMode_radioButton3.TabIndex = 2
		self._Electrical_Circuit_PathMode_radioButton3.TabStop = True
		self._Electrical_Circuit_PathMode_radioButton3.Text = "Не управлять режимом траектории"
		self._Electrical_Circuit_PathMode_radioButton3.UseVisualStyleBackColor = True
		# 
		# Electrical_Circuit_PathMode_radioButton2
		# 
		self._Electrical_Circuit_PathMode_radioButton2.Location = System.Drawing.Point(18, 90)
		self._Electrical_Circuit_PathMode_radioButton2.Name = "Electrical_Circuit_PathMode_radioButton2"
		self._Electrical_Circuit_PathMode_radioButton2.Size = System.Drawing.Size(392, 24)
		self._Electrical_Circuit_PathMode_radioButton2.TabIndex = 0
		self._Electrical_Circuit_PathMode_radioButton2.TabStop = True
		self._Electrical_Circuit_PathMode_radioButton2.Text = "Наиболее удалённое устройство"
		self._Electrical_Circuit_PathMode_radioButton2.UseVisualStyleBackColor = True
		# 
		# Electrical_Circuit_PathMode_radioButton1
		# 
		self._Electrical_Circuit_PathMode_radioButton1.Location = System.Drawing.Point(18, 55)
		self._Electrical_Circuit_PathMode_radioButton1.Name = "Electrical_Circuit_PathMode_radioButton1"
		self._Electrical_Circuit_PathMode_radioButton1.Size = System.Drawing.Size(392, 24)
		self._Electrical_Circuit_PathMode_radioButton1.TabIndex = 1
		self._Electrical_Circuit_PathMode_radioButton1.TabStop = True
		self._Electrical_Circuit_PathMode_radioButton1.Text = "Все устройства"
		self._Electrical_Circuit_PathMode_radioButton1.UseVisualStyleBackColor = True
		# 
		# deltaU_boundary_value_groupBox
		# 
		self._deltaU_boundary_value_groupBox.Controls.Add(self._Select_Cable_by_DeltaU_checkBox)
		self._deltaU_boundary_value_groupBox.Controls.Add(self._deltaU_boundary_value_label2)
		self._deltaU_boundary_value_groupBox.Controls.Add(self._deltaU_boundary_value_label1)
		self._deltaU_boundary_value_groupBox.Controls.Add(self._deltaU_boundary_value_textBox)
		self._deltaU_boundary_value_groupBox.Location = System.Drawing.Point(477, 211)
		self._deltaU_boundary_value_groupBox.Name = "deltaU_boundary_value_groupBox"
		self._deltaU_boundary_value_groupBox.Size = System.Drawing.Size(416, 95)
		self._deltaU_boundary_value_groupBox.TabIndex = 4
		self._deltaU_boundary_value_groupBox.TabStop = False
		self._deltaU_boundary_value_groupBox.Text = "Граничное значение потерь"
		# 
		# deltaU_boundary_value_textBox
		# 
		self._deltaU_boundary_value_textBox.Location = System.Drawing.Point(254, 23)
		self._deltaU_boundary_value_textBox.Name = "deltaU_boundary_value_textBox"
		self._deltaU_boundary_value_textBox.Size = System.Drawing.Size(53, 22)
		self._deltaU_boundary_value_textBox.TabIndex = 0
		self._deltaU_boundary_value_textBox.TextChanged += self.DeltaU_boundary_value_textBoxTextChanged
		# 
		# deltaU_boundary_value_label1
		# 
		self._deltaU_boundary_value_label1.Location = System.Drawing.Point(7, 21)
		self._deltaU_boundary_value_label1.Name = "deltaU_boundary_value_label1"
		self._deltaU_boundary_value_label1.Size = System.Drawing.Size(226, 24)
		self._deltaU_boundary_value_label1.TabIndex = 1
		self._deltaU_boundary_value_label1.Text = "Введите значение:"
		# 
		# deltaU_boundary_value_label2
		# 
		self._deltaU_boundary_value_label2.Location = System.Drawing.Point(310, 26)
		self._deltaU_boundary_value_label2.Name = "deltaU_boundary_value_label2"
		self._deltaU_boundary_value_label2.Size = System.Drawing.Size(44, 24)
		self._deltaU_boundary_value_label2.TabIndex = 2
		self._deltaU_boundary_value_label2.Text = "%"
		# 
		# Settings_by_default_button
		# 
		self._Settings_by_default_button.Location = System.Drawing.Point(21, 728)
		self._Settings_by_default_button.Name = "Settings_by_default_button"
		self._Settings_by_default_button.Size = System.Drawing.Size(329, 27)
		self._Settings_by_default_button.TabIndex = 5
		self._Settings_by_default_button.Text = "Установить настройки по умолчанию"
		self._Settings_by_default_button.UseVisualStyleBackColor = True
		self._Settings_by_default_button.Click += self.Settings_by_default_buttonClick
		# 
		# Round_value_groupBox
		# 
		self._Round_value_groupBox.Controls.Add(self._Round_value_label2)
		self._Round_value_groupBox.Controls.Add(self._Round_value_label1)
		self._Round_value_groupBox.Controls.Add(self._Round_value_textBox)
		self._Round_value_groupBox.Location = System.Drawing.Point(477, 312)
		self._Round_value_groupBox.Name = "Round_value_groupBox"
		self._Round_value_groupBox.Size = System.Drawing.Size(416, 70)
		self._Round_value_groupBox.TabIndex = 5
		self._Round_value_groupBox.TabStop = False
		self._Round_value_groupBox.Text = "Округление значений"
		# 
		# Round_value_label2
		# 
		self._Round_value_label2.Location = System.Drawing.Point(254, 15)
		self._Round_value_label2.Name = "Round_value_label2"
		self._Round_value_label2.Size = System.Drawing.Size(157, 52)
		self._Round_value_label2.TabIndex = 2
		self._Round_value_label2.Text = "знаков после запятой"
		# 
		# Round_value_label1
		# 
		self._Round_value_label1.Location = System.Drawing.Point(7, 21)
		self._Round_value_label1.Name = "Round_value_label1"
		self._Round_value_label1.Size = System.Drawing.Size(159, 46)
		self._Round_value_label1.TabIndex = 1
		self._Round_value_label1.Text = "Округлять значения до:"
		# 
		# Round_value_textBox
		# 
		self._Round_value_textBox.Location = System.Drawing.Point(172, 18)
		self._Round_value_textBox.Name = "Round_value_textBox"
		self._Round_value_textBox.Size = System.Drawing.Size(61, 22)
		self._Round_value_textBox.TabIndex = 0
		self._Round_value_textBox.TextChanged += self.Round_value_textBoxTextChanged
		# 
		# DeltaUByGroupsShowForm_button
		# 
		self._DeltaUByGroupsShowForm_button.Location = System.Drawing.Point(199, 30)
		self._DeltaUByGroupsShowForm_button.Name = "DeltaUByGroupsShowForm_button"
		self._DeltaUByGroupsShowForm_button.Size = System.Drawing.Size(217, 27)
		self._DeltaUByGroupsShowForm_button.TabIndex = 1
		self._DeltaUByGroupsShowForm_button.Text = "Потери по группам"
		self._DeltaUByGroupsShowForm_button.UseVisualStyleBackColor = True
		self._DeltaUByGroupsShowForm_button.Click += self.DeltaUByGroupsShowForm_buttonClick
		# 
		# Require_tables_select_groupBox
		# 
		self._Require_tables_select_groupBox.Controls.Add(self._Require_tables_select_checkBox2)
		self._Require_tables_select_groupBox.Controls.Add(self._Require_tables_select_checkBox1)
		self._Require_tables_select_groupBox.Location = System.Drawing.Point(475, 388)
		self._Require_tables_select_groupBox.Name = "Require_tables_select_groupBox"
		self._Require_tables_select_groupBox.Size = System.Drawing.Size(418, 116)
		self._Require_tables_select_groupBox.TabIndex = 6
		self._Require_tables_select_groupBox.TabStop = False
		self._Require_tables_select_groupBox.Text = "Выбор элементов"
		# 
		# Require_tables_select_checkBox1
		# 
		self._Require_tables_select_checkBox1.Location = System.Drawing.Point(18, 20)
		self._Require_tables_select_checkBox1.Name = "Require_tables_select_checkBox1"
		self._Require_tables_select_checkBox1.Size = System.Drawing.Size(394, 42)
		self._Require_tables_select_checkBox1.TabIndex = 0
		self._Require_tables_select_checkBox1.Text = "Требовать выбора результата расчёта и примечаний при расчёте схем"
		self._Require_tables_select_checkBox1.UseVisualStyleBackColor = True
		# 
		# Require_tables_select_checkBox2
		# 
		self._Require_tables_select_checkBox2.Location = System.Drawing.Point(18, 68)
		self._Require_tables_select_checkBox2.Name = "Require_tables_select_checkBox2"
		self._Require_tables_select_checkBox2.Size = System.Drawing.Size(394, 42)
		self._Require_tables_select_checkBox2.TabIndex = 1
		self._Require_tables_select_checkBox2.Text = "Требовать выбора таблички фазировки при фазировке щитов"
		self._Require_tables_select_checkBox2.UseVisualStyleBackColor = True
		# 
		# CalculationResoursesFormShow_button
		# 
		self._CalculationResoursesFormShow_button.Location = System.Drawing.Point(21, 517)
		self._CalculationResoursesFormShow_button.Name = "CalculationResoursesFormShow_button"
		self._CalculationResoursesFormShow_button.Size = System.Drawing.Size(329, 27)
		self._CalculationResoursesFormShow_button.TabIndex = 2
		self._CalculationResoursesFormShow_button.Text = "Исходные данные для расчётов"
		self._CalculationResoursesFormShow_button.UseVisualStyleBackColor = True
		self._CalculationResoursesFormShow_button.Click += self.CalculationResoursesFormShow_buttonClick
		# 
		# Electrical_Circuit_PathMode_radioButton4
		# 
		self._Electrical_Circuit_PathMode_radioButton4.Location = System.Drawing.Point(18, 21)
		self._Electrical_Circuit_PathMode_radioButton4.Name = "Electrical_Circuit_PathMode_radioButton4"
		self._Electrical_Circuit_PathMode_radioButton4.Size = System.Drawing.Size(392, 24)
		self._Electrical_Circuit_PathMode_radioButton4.TabIndex = 3
		self._Electrical_Circuit_PathMode_radioButton4.TabStop = True
		self._Electrical_Circuit_PathMode_radioButton4.Text = "Усреднённое значение длины цепи"
		self._Electrical_Circuit_PathMode_radioButton4.UseVisualStyleBackColor = True
		# 
		# Select_Cable_by_DeltaU_checkBox
		# 
		self._Select_Cable_by_DeltaU_checkBox.Location = System.Drawing.Point(18, 44)
		self._Select_Cable_by_DeltaU_checkBox.Name = "Select_Cable_by_DeltaU_checkBox"
		self._Select_Cable_by_DeltaU_checkBox.Size = System.Drawing.Size(392, 45)
		self._Select_Cable_by_DeltaU_checkBox.TabIndex = 2
		self._Select_Cable_by_DeltaU_checkBox.Text = "Выбирать сечение кабеля по потерям"
		self._Select_Cable_by_DeltaU_checkBox.UseVisualStyleBackColor = True
		# 
		# flat_calculation_way_groupBox
		# 
		self._flat_calculation_way_groupBox.Controls.Add(self._flat_calculation_way_radioButton1)
		self._flat_calculation_way_groupBox.Controls.Add(self._flat_calculation_way_radioButton2)
		self._flat_calculation_way_groupBox.Location = System.Drawing.Point(475, 510)
		self._flat_calculation_way_groupBox.Name = "flat_calculation_way_groupBox"
		self._flat_calculation_way_groupBox.Size = System.Drawing.Size(418, 91)
		self._flat_calculation_way_groupBox.TabIndex = 7
		self._flat_calculation_way_groupBox.TabStop = False
		self._flat_calculation_way_groupBox.Text = "Способ расчёта разных типов квартир"
		# 
		# flat_calculation_way_radioButton1
		# 
		self._flat_calculation_way_radioButton1.Location = System.Drawing.Point(10, 22)
		self._flat_calculation_way_radioButton1.Name = "flat_calculation_way_radioButton1"
		self._flat_calculation_way_radioButton1.Size = System.Drawing.Size(402, 24)
		self._flat_calculation_way_radioButton1.TabIndex = 5
		self._flat_calculation_way_radioButton1.TabStop = True
		self._flat_calculation_way_radioButton1.Text = "Общий Ко на все квартиры"
		self._flat_calculation_way_radioButton1.UseVisualStyleBackColor = True
		self._flat_calculation_way_radioButton1.CheckedChanged += self.Flat_calculation_way_radioButton1CheckedChanged
		# 
		# flat_calculation_way_radioButton2
		# 
		self._flat_calculation_way_radioButton2.Location = System.Drawing.Point(10, 53)
		self._flat_calculation_way_radioButton2.Name = "flat_calculation_way_radioButton2"
		self._flat_calculation_way_radioButton2.Size = System.Drawing.Size(402, 24)
		self._flat_calculation_way_radioButton2.TabIndex = 4
		self._flat_calculation_way_radioButton2.TabStop = True
		self._flat_calculation_way_radioButton2.Text = "Отдельный Ко для каждого типа квартир"
		self._flat_calculation_way_radioButton2.UseVisualStyleBackColor = True
		self._flat_calculation_way_radioButton2.CheckedChanged += self.Flat_calculation_way_radioButton2CheckedChanged
		# 
		# Param_Names_Storage_FormShow_button
		# 
		self._Param_Names_Storage_FormShow_button.Location = System.Drawing.Point(21, 552)
		self._Param_Names_Storage_FormShow_button.Name = "Param_Names_Storage_FormShow_button"
		self._Param_Names_Storage_FormShow_button.Size = System.Drawing.Size(329, 27)
		self._Param_Names_Storage_FormShow_button.TabIndex = 8
		self._Param_Names_Storage_FormShow_button.Text = "Имена параметров"
		self._Param_Names_Storage_FormShow_button.UseVisualStyleBackColor = True
		self._Param_Names_Storage_FormShow_button.Click += self.Param_Names_Storage_FormShow_buttonClick
		# 
		# Illumination_Values_Storage_FormShow_button
		# 
		self._Illumination_Values_Storage_FormShow_button.Location = System.Drawing.Point(21, 587)
		self._Illumination_Values_Storage_FormShow_button.Name = "Illumination_Values_Storage_FormShow_button"
		self._Illumination_Values_Storage_FormShow_button.Size = System.Drawing.Size(329, 27)
		self._Illumination_Values_Storage_FormShow_button.TabIndex = 9
		self._Illumination_Values_Storage_FormShow_button.Text = "Нормы освещённости"
		self._Illumination_Values_Storage_FormShow_button.UseVisualStyleBackColor = True
		self._Illumination_Values_Storage_FormShow_button.Click += self.Illumination_Values_Storage_FormShow_buttonClick
		# 
		# Import_button
		# 
		self._Import_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Import_button.Location = System.Drawing.Point(370, 788)
		self._Import_button.Name = "Import_button"
		self._Import_button.Size = System.Drawing.Size(107, 23)
		self._Import_button.TabIndex = 10
		self._Import_button.Text = "Импорт"
		self._Import_button.UseVisualStyleBackColor = True
		self._Import_button.Click += self.Import_buttonClick
		# 
		# Export_button
		# 
		self._Export_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._Export_button.Location = System.Drawing.Point(483, 788)
		self._Export_button.Name = "Export_button"
		self._Export_button.Size = System.Drawing.Size(101, 23)
		self._Export_button.TabIndex = 11
		self._Export_button.Text = "Экспорт"
		self._Export_button.UseVisualStyleBackColor = True
		self._Export_button.Click += self.Export_buttonClick
		# 
		# Kc_Storage_FormShow_button
		# 
		self._Kc_Storage_FormShow_button.Location = System.Drawing.Point(21, 622)
		self._Kc_Storage_FormShow_button.Name = "Kc_Storage_FormShow_button"
		self._Kc_Storage_FormShow_button.Size = System.Drawing.Size(329, 27)
		self._Kc_Storage_FormShow_button.TabIndex = 12
		self._Kc_Storage_FormShow_button.Text = "Коэффициенты спроса"
		self._Kc_Storage_FormShow_button.UseVisualStyleBackColor = True
		self._Kc_Storage_FormShow_button.Click += self.Kc_Storage_FormShow_buttonClick
		# 
		# VolumeCapacityNKU_groupBox
		# 
		self._VolumeCapacityNKU_groupBox.Controls.Add(self._textBox_VolumeCapacityNKU)
		self._VolumeCapacityNKU_groupBox.Controls.Add(self._trackBar_VolumeCapacityNKU)
		self._VolumeCapacityNKU_groupBox.Location = System.Drawing.Point(21, 426)
		self._VolumeCapacityNKU_groupBox.Name = "VolumeCapacityNKU_groupBox"
		self._VolumeCapacityNKU_groupBox.Size = System.Drawing.Size(434, 72)
		self._VolumeCapacityNKU_groupBox.TabIndex = 14
		self._VolumeCapacityNKU_groupBox.TabStop = False
		self._VolumeCapacityNKU_groupBox.Text = "Запас пространства внутри НКУ (в %)"
		# 
		# textBox_VolumeCapacityNKU
		# 
		self._textBox_VolumeCapacityNKU.Location = System.Drawing.Point(172, 23)
		self._textBox_VolumeCapacityNKU.Name = "textBox_VolumeCapacityNKU"
		self._textBox_VolumeCapacityNKU.Size = System.Drawing.Size(50, 22)
		self._textBox_VolumeCapacityNKU.TabIndex = 13
		self._textBox_VolumeCapacityNKU.Text = "10"
		self._textBox_VolumeCapacityNKU.TextChanged += self.TextBox_VolumeCapacityNKUTextChanged
		# 
		# trackBar_VolumeCapacityNKU
		# 
		self._trackBar_VolumeCapacityNKU.Location = System.Drawing.Point(6, 23)
		self._trackBar_VolumeCapacityNKU.Name = "trackBar_VolumeCapacityNKU"
		self._trackBar_VolumeCapacityNKU.Size = System.Drawing.Size(146, 56)
		self._trackBar_VolumeCapacityNKU.TabIndex = 11
		self._trackBar_VolumeCapacityNKU.Value = 1
		self._trackBar_VolumeCapacityNKU.Scroll += self.TrackBar_VolumeCapacityNKUScroll
		# 
		# ManufacturerSettings_Storage_FormShow_button
		# 
		self._ManufacturerSettings_Storage_FormShow_button.Location = System.Drawing.Point(21, 657)
		self._ManufacturerSettings_Storage_FormShow_button.Name = "ManufacturerSettings_Storage_FormShow_button"
		self._ManufacturerSettings_Storage_FormShow_button.Size = System.Drawing.Size(329, 27)
		self._ManufacturerSettings_Storage_FormShow_button.TabIndex = 15
		self._ManufacturerSettings_Storage_FormShow_button.Text = "Выбор производителя"
		self._ManufacturerSettings_Storage_FormShow_button.UseVisualStyleBackColor = True
		self._ManufacturerSettings_Storage_FormShow_button.Click += self.ManufacturerSettings_Storage_FormShow_buttonClick
		# 
		# Distributed_Volt_Dropage_koefficient_textBox
		# 
		self._Distributed_Volt_Dropage_koefficient_textBox.Location = System.Drawing.Point(197, 158)
		self._Distributed_Volt_Dropage_koefficient_textBox.Name = "Distributed_Volt_Dropage_koefficient_textBox"
		self._Distributed_Volt_Dropage_koefficient_textBox.Size = System.Drawing.Size(58, 22)
		self._Distributed_Volt_Dropage_koefficient_textBox.TabIndex = 3
		self._Distributed_Volt_Dropage_koefficient_textBox.TextChanged += self.Distributed_Volt_Dropage_koefficient_textBoxTextChanged
		# 
		# Distributed_Volt_Dropage_koefficient_label
		# 
		self._Distributed_Volt_Dropage_koefficient_label.Location = System.Drawing.Point(199, 64)
		self._Distributed_Volt_Dropage_koefficient_label.Name = "Distributed_Volt_Dropage_koefficient_label"
		self._Distributed_Volt_Dropage_koefficient_label.Size = System.Drawing.Size(229, 91)
		self._Distributed_Volt_Dropage_koefficient_label.TabIndex = 3
		self._Distributed_Volt_Dropage_koefficient_label.Text = "Понижающий коэффициент на распределённые потери:"
		# 
		# PhaseNaming_groupBox
		# 
		self._PhaseNaming_groupBox.Controls.Add(self._PhaseNaming_ABC_radioButton)
		self._PhaseNaming_groupBox.Controls.Add(self._PhaseNaming_L123_radioButton)
		self._PhaseNaming_groupBox.Location = System.Drawing.Point(477, 607)
		self._PhaseNaming_groupBox.Name = "PhaseNaming_groupBox"
		self._PhaseNaming_groupBox.Size = System.Drawing.Size(416, 100)
		self._PhaseNaming_groupBox.TabIndex = 8
		self._PhaseNaming_groupBox.TabStop = False
		self._PhaseNaming_groupBox.Text = "Наименование фаз"
		# 
		# PhaseNaming_ABC_radioButton
		# 
		self._PhaseNaming_ABC_radioButton.Location = System.Drawing.Point(10, 22)
		self._PhaseNaming_ABC_radioButton.Name = "PhaseNaming_ABC_radioButton"
		self._PhaseNaming_ABC_radioButton.Size = System.Drawing.Size(313, 24)
		self._PhaseNaming_ABC_radioButton.TabIndex = 5
		self._PhaseNaming_ABC_radioButton.TabStop = True
		self._PhaseNaming_ABC_radioButton.Text = "A, B, C"
		self._PhaseNaming_ABC_radioButton.UseVisualStyleBackColor = True
		# 
		# PhaseNaming_L123_radioButton
		# 
		self._PhaseNaming_L123_radioButton.Location = System.Drawing.Point(10, 53)
		self._PhaseNaming_L123_radioButton.Name = "PhaseNaming_L123_radioButton"
		self._PhaseNaming_L123_radioButton.Size = System.Drawing.Size(313, 24)
		self._PhaseNaming_L123_radioButton.TabIndex = 4
		self._PhaseNaming_L123_radioButton.TabStop = True
		self._PhaseNaming_L123_radioButton.Text = "L1, L2, L3"
		self._PhaseNaming_L123_radioButton.UseVisualStyleBackColor = True
		# 
		# AdvancedSettings_button
		# 
		self._AdvancedSettings_button.Location = System.Drawing.Point(21, 692)
		self._AdvancedSettings_button.Name = "AdvancedSettings_button"
		self._AdvancedSettings_button.Size = System.Drawing.Size(329, 27)
		self._AdvancedSettings_button.TabIndex = 16
		self._AdvancedSettings_button.Text = "Дополнительные настройки"
		self._AdvancedSettings_button.UseVisualStyleBackColor = True
		self._AdvancedSettings_button.Click += self.AdvancedSettings_buttonClick
		# 
		# Electrical_Circuit_PathMode_radioButton5
		# 
		self._Electrical_Circuit_PathMode_radioButton5.Location = System.Drawing.Point(18, 124)
		self._Electrical_Circuit_PathMode_radioButton5.Name = "Electrical_Circuit_PathMode_radioButton5"
		self._Electrical_Circuit_PathMode_radioButton5.Size = System.Drawing.Size(392, 24)
		self._Electrical_Circuit_PathMode_radioButton5.TabIndex = 4
		self._Electrical_Circuit_PathMode_radioButton5.TabStop = True
		self._Electrical_Circuit_PathMode_radioButton5.Text = "Расчётное значение длины цепи"
		self._Electrical_Circuit_PathMode_radioButton5.UseVisualStyleBackColor = True
		self._Electrical_Circuit_PathMode_radioButton5.CheckedChanged += self.Electrical_Circuit_PathMode_radioButton5CheckedChanged
		# 
		# TeslaSettings
		# 
		self.ClientSize = System.Drawing.Size(905, 823)
		self.Controls.Add(self._AdvancedSettings_button)
		self.Controls.Add(self._PhaseNaming_groupBox)
		self.Controls.Add(self._ManufacturerSettings_Storage_FormShow_button)
		self.Controls.Add(self._VolumeCapacityNKU_groupBox)
		self.Controls.Add(self._Kc_Storage_FormShow_button)
		self.Controls.Add(self._Export_button)
		self.Controls.Add(self._Import_button)
		self.Controls.Add(self._Illumination_Values_Storage_FormShow_button)
		self.Controls.Add(self._Param_Names_Storage_FormShow_button)
		self.Controls.Add(self._flat_calculation_way_groupBox)
		self.Controls.Add(self._CalculationResoursesFormShow_button)
		self.Controls.Add(self._Require_tables_select_groupBox)
		self.Controls.Add(self._Round_value_groupBox)
		self.Controls.Add(self._Settings_by_default_button)
		self.Controls.Add(self._deltaU_boundary_value_groupBox)
		self.Controls.Add(self._Electrical_Circuit_PathMode_groupBox)
		self.Controls.Add(self._Cable_stock_for_circuitry_groupBox)
		self.Controls.Add(self._Volt_Dropage_key_groupBox)
		self.Controls.Add(self._Cable_section_calculation_method_groupBox)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._OK_button)
		self.MaximumSize = System.Drawing.Size(923, 870)
		self.MinimumSize = System.Drawing.Size(736, 771)
		self.Name = "TeslaSettings"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
		self.Text = "Настройки"
		self.Load += self.TeslaSettingsLoad
		self._Cable_section_calculation_method_groupBox.ResumeLayout(False)
		self._Volt_Dropage_key_groupBox.ResumeLayout(False)
		self._Volt_Dropage_key_groupBox.PerformLayout()
		self._Cable_stock_for_circuitry_groupBox.ResumeLayout(False)
		self._Cable_stock_for_circuitry_groupBox.PerformLayout()
		self._trackBar_Length_stock.EndInit()
		self._Electrical_Circuit_PathMode_groupBox.ResumeLayout(False)
		self._deltaU_boundary_value_groupBox.ResumeLayout(False)
		self._deltaU_boundary_value_groupBox.PerformLayout()
		self._Round_value_groupBox.ResumeLayout(False)
		self._Round_value_groupBox.PerformLayout()
		self._Require_tables_select_groupBox.ResumeLayout(False)
		self._flat_calculation_way_groupBox.ResumeLayout(False)
		self._VolumeCapacityNKU_groupBox.ResumeLayout(False)
		self._VolumeCapacityNKU_groupBox.PerformLayout()
		self._trackBar_VolumeCapacityNKU.EndInit()
		self._PhaseNaming_groupBox.ResumeLayout(False)
		self.ResumeLayout(False)


		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell

	def Electrical_Circuit_PathMode_radioButton5CheckedChanged(self, sender, e):
		pass

	def Flat_calculation_way_radioButton1CheckedChanged(self, sender, e):
		pass

	def Flat_calculation_way_radioButton2CheckedChanged(self, sender, e):
		pass


	def OK_buttonClick(self, sender, e):
		# Выставляем "кнопка отмена не нажата"
		global Button_Cancel_pushed
		Button_Cancel_pushed = 0
		# Снимаем значение метода выбора сечения кабелей
		if self._Cable_section_by_CBnominal_radioButton.Checked == True:
			global Cable_section_calculatingMethod_radioButton
			Cable_section_calculatingMethod_radioButton = 1
		elif self._Cable_section_by_rated_current_radioButton.Checked == True:
			global Cable_section_calculatingMethod_radioButton
			Cable_section_calculatingMethod_radioButton = 0
		# Снимаем значение ключа для расчёта распределённых потерь
		global Volt_Dropage_key_textBox
		Volt_Dropage_key_textBox = self._Volt_Dropage_key_textBox.Text
		# Снимаем значение запаса кабеля по умолчанию
		global Length_stock_textBox
		Length_stock_textBox = self._textBox_Length_stock.Text
		# Снимаем значение режима траектории цепей
		if self._Electrical_Circuit_PathMode_radioButton1.Checked == True:
			global Electrical_Circuit_PathMode_radioButton
			Electrical_Circuit_PathMode_radioButton = 1
		elif self._Electrical_Circuit_PathMode_radioButton2.Checked == True:
			global Electrical_Circuit_PathMode_radioButton
			Electrical_Circuit_PathMode_radioButton = 2
		elif self._Electrical_Circuit_PathMode_radioButton3.Checked == True:
			global Electrical_Circuit_PathMode_radioButton
			Electrical_Circuit_PathMode_radioButton = 0
		elif self._Electrical_Circuit_PathMode_radioButton4.Checked == True:
			global Electrical_Circuit_PathMode_radioButton
			Electrical_Circuit_PathMode_radioButton = 3
		elif self._Electrical_Circuit_PathMode_radioButton5.Checked == True:
			global Electrical_Circuit_PathMode_radioButton
			Electrical_Circuit_PathMode_radioButton = 4
		# Снимаем граничное значение потерь
		global deltaU_boundary_value_textBox
		deltaU_boundary_value_textBox = self._deltaU_boundary_value_textBox.Text
		# Снимаем округление до такой-то цифры после запятой
		global Round_value_textBox
		Round_value_textBox = self._Round_value_textBox.Text
		# Снимаем значение флажка обязательного выбора расчётной таблички и примечаний
		global Require_tables_select_checkBox1
		Require_tables_select_checkBox1 = self._Require_tables_select_checkBox1.Checked
		# Снимаем значение флажка обязательного выбора таблички фазировки
		global Require_tables_select_checkBox2
		Require_tables_select_checkBox2 = self._Require_tables_select_checkBox2.Checked
		# Снимаем значение флажка выбора кабеля по потерям
		global Select_Cable_by_DeltaU_checkBox
		Select_Cable_by_DeltaU_checkBox = self._Select_Cable_by_DeltaU_checkBox.Checked
		# Снимаем значение радиокнопки выбора способа расчёта квартир повышенной комфортности
		if self._flat_calculation_way_radioButton2.Checked == True:
			global flat_calculation_way_ts_radioButton
			flat_calculation_way_ts_radioButton = 1
		elif self._flat_calculation_way_radioButton1.Checked == True:
			global flat_calculation_way_ts_radioButton
			flat_calculation_way_ts_radioButton = 0
		# Снимаем данные по запасу свободного пространства в НКУ
		global VolumeCapacityNKU_textBox
		VolumeCapacityNKU_textBox = self._textBox_VolumeCapacityNKU.Text
		# Снимаем значение понижающего коэффициента на распределённые потери
		global Distributed_Volt_Dropage_koefficient_textBox
		Distributed_Volt_Dropage_koefficient_textBox = self._Distributed_Volt_Dropage_koefficient_textBox.Text
		# Снимаем данные по именованию фаз
		global PhaseNaming_radiobuttonposition
		if self._PhaseNaming_ABC_radioButton.Checked == True:
			PhaseNaming_radiobuttonposition = '0'
		else:
			PhaseNaming_radiobuttonposition = '1'

		self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()

	def TrackBar_Length_stockScroll(self, sender, e):
		self._textBox_Length_stock.Text = str(self._trackBar_Length_stock.Value * 10) # пишем текст запаса кабеля при перемещении скрол-бара

	def TextBox_Length_stockTextChanged(self, sender, e):
		if self._textBox_Length_stock.Text != '':
			self._trackBar_Length_stock.Value = int(int(self._textBox_Length_stock.Text) / 10) # перемещаем скролл-бар при изменении текста запаса кабеля	

	def TrackBar_VolumeCapacityNKUScroll(self, sender, e):
		self._textBox_VolumeCapacityNKU.Text = str(self._trackBar_VolumeCapacityNKU.Value * 10) # пишем текст запаса свободного пространства в щитах при перемещении скрол-бара

	def TextBox_VolumeCapacityNKUTextChanged(self, sender, e):
		if self._textBox_VolumeCapacityNKU.Text != '':
			self._trackBar_VolumeCapacityNKU.Value = int(int(self._textBox_VolumeCapacityNKU.Text) / 10) # перемещаем скролл-бар при изменении текста запаса свободного пространства в щитах

	def DeltaU_boundary_value_textBoxTextChanged(self, sender, e):
		if is_Float(self._deltaU_boundary_value_textBox.Text) == False: # если введённое значение не может быть преобразовано в число
			self._deltaU_boundary_value_textBox.Text = deltaU_boundary_value # то оставить значение как было

	def Distributed_Volt_Dropage_koefficient_textBoxTextChanged(self, sender, e):
		if is_Float(self._Distributed_Volt_Dropage_koefficient_textBox.Text) == False: # если введённое значение не может быть преобразовано в число
			self._Distributed_Volt_Dropage_koefficient_textBox.Text = Distributed_Volt_Dropage_koefficient # то оставить значение как было

	def DeltaUByGroupsShowForm_buttonClick(self, sender, e):
		DeltaUByGroups_Form().ShowDialog()

	def CalculationResoursesFormShow_buttonClick(self, sender, e):
		CalculationResoursesForm().ShowDialog()

	def Param_Names_Storage_FormShow_buttonClick(self, sender, e):
		Param_Names_Storage_Form().ShowDialog()

	def Illumination_Values_Storage_FormShow_buttonClick(self, sender, e):
		Illumination_Values_Storage_Form().ShowDialog()		

	def Kc_Storage_FormShow_buttonClick(self, sender, e):
		Kc_Storage_Form().ShowDialog()
		if ImportKcButtonPushed == True:
			self.Close()

	def Round_value_textBoxTextChanged(self, sender, e):
		try:
			int(self._Round_value_textBox.Text) # если введённое значение не может быть преобразовано в число
		except ValueError:
			self._Round_value_textBox.Text = Round_value_ts # то оставить значение как было
		if int(self._Round_value_textBox.Text) < 0 or int(self._Round_value_textBox.Text) > 4: # проверяем что значение от 0 до 4 включительно
			self._Round_value_textBox.Text = Round_value_ts # оставить значение как было


	def AdvancedSettings_buttonClick(self, sender, e):
		AdvancedSettings_Form().ShowDialog()

	def ManufacturerSettings_Storage_FormShow_buttonClick(self, sender, e):
		ManufacturerSettings_Storage_Form().ShowDialog()


	def Settings_by_default_buttonClick(self, sender, e):
		self._Cable_section_by_rated_current_radioButton.Checked = True
		self._Volt_Dropage_key_textBox.Text = 'ОСВЕЩ\r\nСВЕТ'
		self._textBox_Length_stock.Text = '10'
		self._trackBar_Length_stock.Value = 1
		self._textBox_VolumeCapacityNKU.Text = '20'
		self._trackBar_VolumeCapacityNKU.Value = 2
		self._Electrical_Circuit_PathMode_radioButton4.Checked = True
		self._deltaU_boundary_value_textBox.Text = '2'
		self._Round_value_textBox.Text = '1'
		self._Require_tables_select_checkBox1.Checked = True
		self._Require_tables_select_checkBox2.Checked = True
		self._Select_Cable_by_DeltaU_checkBox.Checked = True
		self._flat_calculation_way_radioButton1.Checked = True
		self._Distributed_Volt_Dropage_koefficient_textBox.Text = '0.5'
		self._PhaseNaming_ABC_radioButton.Checked = True

	def TeslaSettingsLoad(self, sender, e):
		# Выставляем отображение настроек по данным полученным из хранилища
		# Выставляем метод выбора сечения кабелей
		if Cable_section_calculation_method == 0:
			self._Cable_section_by_CBnominal_radioButton.Checked = False
			self._Cable_section_by_rated_current_radioButton.Checked = True
		else:
			self._Cable_section_by_CBnominal_radioButton.Checked = True
			self._Cable_section_by_rated_current_radioButton.Checked = False
		# Пишем однокоренные слова для распределённых потерь
		self._Volt_Dropage_key_textBox.Text = Volt_Dropage_key
		# Устанавливаем запас кабеля
		self._trackBar_Length_stock.Value = int(int(Cable_stock_for_circuitry)/10)
		self._textBox_Length_stock.Text = Cable_stock_for_circuitry
		# Устанавливаем запас свободного пространства в НКУ
		self._trackBar_VolumeCapacityNKU.Value = int(int(znach_VolumeCapacityNKU[0])/10)
		self._textBox_VolumeCapacityNKU.Text = znach_VolumeCapacityNKU[0]
		# Выставляем режим траектории цепей
		if Electrical_Circuit_PathMode_method == 0:
			self._Electrical_Circuit_PathMode_radioButton1.Checked = False
			self._Electrical_Circuit_PathMode_radioButton2.Checked = False
			self._Electrical_Circuit_PathMode_radioButton3.Checked = True
			self._Electrical_Circuit_PathMode_radioButton4.Checked = False
			self._Electrical_Circuit_PathMode_radioButton5.Checked = False
		elif Electrical_Circuit_PathMode_method == 1:
			self._Electrical_Circuit_PathMode_radioButton1.Checked = True
			self._Electrical_Circuit_PathMode_radioButton2.Checked = False
			self._Electrical_Circuit_PathMode_radioButton3.Checked = False
			self._Electrical_Circuit_PathMode_radioButton4.Checked = False
			self._Electrical_Circuit_PathMode_radioButton5.Checked = False
		elif Electrical_Circuit_PathMode_method == 2:
			self._Electrical_Circuit_PathMode_radioButton1.Checked = False
			self._Electrical_Circuit_PathMode_radioButton2.Checked = True
			self._Electrical_Circuit_PathMode_radioButton3.Checked = False
			self._Electrical_Circuit_PathMode_radioButton4.Checked = False
			self._Electrical_Circuit_PathMode_radioButton5.Checked = False
		elif Electrical_Circuit_PathMode_method == 3:
			self._Electrical_Circuit_PathMode_radioButton1.Checked = False
			self._Electrical_Circuit_PathMode_radioButton2.Checked = False
			self._Electrical_Circuit_PathMode_radioButton3.Checked = False
			self._Electrical_Circuit_PathMode_radioButton4.Checked = True
			self._Electrical_Circuit_PathMode_radioButton5.Checked = False
		elif Electrical_Circuit_PathMode_method == 4:
			self._Electrical_Circuit_PathMode_radioButton1.Checked = False
			self._Electrical_Circuit_PathMode_radioButton2.Checked = False
			self._Electrical_Circuit_PathMode_radioButton3.Checked = False
			self._Electrical_Circuit_PathMode_radioButton4.Checked = False
			self._Electrical_Circuit_PathMode_radioButton5.Checked = True
		# Пишем граничное значение потерь
		self._deltaU_boundary_value_textBox.Text = deltaU_boundary_value
		# Пишем до скольки знаков после запятой округляем
		self._Round_value_textBox.Text = Round_value_ts
		# Выставляем флажок "Требовать выбора расчётной таблички и примечаний"
		if Require_tables_select_ts == '0':
			self._Require_tables_select_checkBox1.Checked = False
		else:
			self._Require_tables_select_checkBox1.Checked = True
		# Выставляем флажок "Требовать выбора таблички фазировки"
		if Require_PHtables_select_ts == '0':
			self._Require_tables_select_checkBox2.Checked = False
		else:
			self._Require_tables_select_checkBox2.Checked = True
		# Выставляем флажок "Выбирать кабель по потерям"
		if Select_Cable_by_DeltaU_ts == '0':
			self._Select_Cable_by_DeltaU_checkBox.Checked = False
		else:
			self._Select_Cable_by_DeltaU_checkBox.Checked = True
		# Выставляем способ расчёта квартир повышенной комфортности
		if flat_calculation_way_ts == '0':
			self._flat_calculation_way_radioButton1.Checked = True
		else:
			self._flat_calculation_way_radioButton2.Checked = True
		# Выставляем понижающий коэффициент на распределённые потери:
		self._Distributed_Volt_Dropage_koefficient_textBox.Text = Distributed_Volt_Dropage_koefficient
		# Выставляем обозначение фаз
		if PhaseNaming == '0':
			self._PhaseNaming_ABC_radioButton.Checked = True
		else:
			self._PhaseNaming_L123_radioButton.Checked = True
		# Пишем имя формы
		self.Text = 'Настройки ' + Program_name
		
		# делаем всплывающие подсказки
		ToolTip().SetToolTip(self._Cable_section_by_CBnominal_radioButton, 'Программа будет выбирать сечения кабелей, пропускающих ток не меньший чем номинальный ток аппарата защиты.') 
		ToolTip().SetToolTip(self._Cable_section_by_rated_current_radioButton, 'Программа будет выбирать сечения кабелей, исходя из реального тока срабатывания аппарата защиты\r\n(Iном. * Ко, где Ко - коэффициент одновременности для аппаратов защиты установленных рядом друг с другом.') 
		ToolTip().SetToolTip(self._Volt_Dropage_key_textBox, 'Введите части строк которые программа будет искать в наименовании электроприёмника.\r\nНапример:\r\nОСВЕЩ\r\nСВЕТ\r\nЧасти строк вводятся в это поле с новой строки.\r\nПри совпадении введённых в настройках частей строк с какой-то частью наименования электроприёмника,\r\nпрограмма посчитает данные потери как распределённые.') 
		ToolTip().SetToolTip(self._trackBar_Length_stock, 'Запас кабеля используемый при синхронизации схем с планами.\r\nПроцент запаса будет добавлен к длинам цепей, рассчитанных Revit.')
		ToolTip().SetToolTip(self._trackBar_VolumeCapacityNKU, 'Запас свободного места в НКУ.\r\nИспользуется при подборе корпусов щитов и ВРУ')
		ToolTip().SetToolTip(self._Electrical_Circuit_PathMode_radioButton1, 'В этом случае Revit считает длины кабелей, как правило, больше реальных') 
		ToolTip().SetToolTip(self._Electrical_Circuit_PathMode_radioButton2, 'В этом случае Revit считает длины кабелей, как правило, меньше реальных') 
		ToolTip().SetToolTip(self._Electrical_Circuit_PathMode_radioButton3, 'В этом случае можно будет выбирать режим траектории для конкретной цепи вручную') 
		ToolTip().SetToolTip(self._Electrical_Circuit_PathMode_radioButton4, 'В этом случае для расчёта длины цепи будет браться среднее значение траектории цепи\n(между наиболее удалённым и всеми устройствами).\nТакое значение ближе всего к реальной длине цепи')
		ToolTip().SetToolTip(self._Electrical_Circuit_PathMode_radioButton5, 'В этом случае длина проводника для расчётов будет браться из параметра "' + Param_TSL_WireLength + '" в электроцепи.')  
		ToolTip().SetToolTip(self._deltaU_boundary_value_textBox, 'При расчёте схем будет выдаваться предупреждение о превышении потерь выше указанного в этом поле значения') 
		ToolTip().SetToolTip(self._Round_value_textBox, 'При расчёте схем округляться будут значения Ру, Рр, Iр, потери') 
		ToolTip().SetToolTip(self._Require_tables_select_checkBox1, 'При расчёте схем требовать включать в выборку не только сами автоматы, но и табличку для записи результата, а также примечания к расчёту') 
		ToolTip().SetToolTip(self._Require_tables_select_checkBox2, 'При выполнении фазировки требовать обязательного выбора семейства результатов фазировки') 
		ToolTip().SetToolTip(self._Settings_by_default_button, 'Вернуться к заводским настройкам') 
		ToolTip().SetToolTip(self._Select_Cable_by_DeltaU_checkBox, 'Выбирать сечения кабелей также исходя из граничного значения потерь') 
		ToolTip().SetToolTip(self._flat_calculation_way_radioButton1, 'Pр.кв. = Ркв.*n*Ко, где Ркв. - общая суммарная мощность всех квартир,\r\nn - общее количество квартир, Ко - коэффициент одновременности для общего количества квартир.') 
		ToolTip().SetToolTip(self._flat_calculation_way_radioButton2, 'Pр.кв. = Ркв.1*n1*Ко1 + ... + Ркв.i*ni*Коi  , где Ркв.i - мощность квартир i-го типа,\r\nni - количество квартир i-го типа, Коi - коэффициент одновременности для квартир i-го типа.') 
		ToolTip().SetToolTip(self._Distributed_Volt_Dropage_koefficient_textBox, 'На этот коэффициент будет умножено расчётное значение потерь\r\nесли потери у данной линии распределённые')
		ToolTip().SetToolTip(self._PhaseNaming_ABC_radioButton, 'Обозначение фаз в автоматах и при фазировке') 
		ToolTip().SetToolTip(self._PhaseNaming_L123_radioButton, 'Обозначение фаз в автоматах и при фазировке') 


	def Import_buttonClick(self, sender, e):
		# Открываем файл для считывания данных
		ofd = OpenFileDialog() # <System.Windows.Forms.OpenFileDialog object at 0x000000000000002B [System.Windows.Forms.OpenFileDialog: Title: , FileName: ]>
		if (ofd.ShowDialog() == DialogResult.OK):
			filename = ofd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt' или 'D:\\Сухов ПА\\Revit Горпроект\\Разное\\тестим настройки распр потерь_основные настройки.txt'
			fileText = System.IO.File.ReadAllText(filename)
			# Считываем данные из файла
			global Imported_list
			Imported_list = Main_settings_Import(fileText) # [[True, False], [u'ОСВЕЩ\r\nСВЕТ'], ['10', '1'], [True, False, False, False], ['2', True], ['1'], [True, True], [True, False], ['20', '2'], ['0.7']]
			# Пробуем заполнить форму:
			try:
				# Выставляем метод выбора сечения кабелей
				if Imported_list[0][0] == True:
					self._Cable_section_by_CBnominal_radioButton.Checked = False
					self._Cable_section_by_rated_current_radioButton.Checked = True
				else:
					self._Cable_section_by_CBnominal_radioButton.Checked = True
					self._Cable_section_by_rated_current_radioButton.Checked = False
				# Пишем однокоренные слова для распределённых потерь
				self._Volt_Dropage_key_textBox.Text = Imported_list[1][0]
				# Устанавливаем запас кабеля
				self._trackBar_Length_stock.Value = int(Imported_list[2][1])
				self._textBox_Length_stock.Text = Imported_list[2][0]
				# Устанавливаем запас пространства в НКУ
				self._trackBar_VolumeCapacityNKU.Value = int(Imported_list[8][1])
				self._textBox_VolumeCapacityNKU.Text = Imported_list[8][0]
				# Выставляем режим траектории цепей
				self._Electrical_Circuit_PathMode_radioButton1.Checked = Imported_list[3][1]
				self._Electrical_Circuit_PathMode_radioButton2.Checked = Imported_list[3][2]
				self._Electrical_Circuit_PathMode_radioButton3.Checked = Imported_list[3][3]
				self._Electrical_Circuit_PathMode_radioButton4.Checked = Imported_list[3][0]
				self._Electrical_Circuit_PathMode_radioButton5.Checked = Imported_list[3][4]
				# Пишем граничное значение потерь
				self._deltaU_boundary_value_textBox.Text = Imported_list[4][0]
				# Выставляем флажок "Выбирать кабель по потерям"
				if Imported_list[4][1] == False:
					self._Select_Cable_by_DeltaU_checkBox.Checked = False
				else:
					self._Select_Cable_by_DeltaU_checkBox.Checked = True
				# Пишем до скольки знаков после запятой округляем
				self._Round_value_textBox.Text = Imported_list[5][0]
				# Выставляем флажок "Требовать выбора расчётной таблички и примечаний"
				if Imported_list[6][0] == False:
					self._Require_tables_select_checkBox1.Checked = False
				else:
					self._Require_tables_select_checkBox1.Checked = True
				# Выставляем флажок "Требовать выбора таблички фазировки"
				if Imported_list[6][1] == False:
					self._Require_tables_select_checkBox2.Checked = False
				else:
					self._Require_tables_select_checkBox2.Checked = True
				# Выставляем способ расчёта квартир повышенной комфортности
				if Imported_list[7][0] == True:
					self._flat_calculation_way_radioButton1.Checked = True
				else:
					self._flat_calculation_way_radioButton2.Checked = True
				# Пишем понижающий коэффициент на распределённые потери
				self._Distributed_Volt_Dropage_koefficient_textBox.Text = Imported_list[9][0]
				# Проставляем именование фаз:
				if Imported_list[10][0] == True:
					self._PhaseNaming_ABC_radioButton.Checked = True
					self._PhaseNaming_L123_radioButton.Checked = False
				else:
					self._PhaseNaming_ABC_radioButton.Checked = False
					self._PhaseNaming_L123_radioButton.Checked = True
				TaskDialog.Show('Настройки', 'Данные успешно импортированы')
			except:
				TaskDialog.Show('Настройки', 'Не удалось импортировать данные. Файл импорта некорректен.')

	def Export_buttonClick(self, sender, e):
		# Сохраняем настройки во внешний txt файл
		sfd = SaveFileDialog()
		sfd.Filter = "Text files(*.txt)|*.txt" #sfd.Filter = "Text files(*.txt)|*.txt|All files(*.*)|*.*"
		sfd.FileName = doc.Title + '_основные настройки' # имя файла по умолчанию
		if (sfd.ShowDialog() == DialogResult.OK): # sfd.ShowDialog() # файл на сохранение
			filename = sfd.FileName # u'C:\\Users\\sukhovpa\ownloads\\авва\\вася.txt'
			System.IO.File.WriteAllText(filename, Main_settings_Export(self._Cable_section_by_rated_current_radioButton.Checked, self._Volt_Dropage_key_textBox.Text, self._textBox_Length_stock.Text, self._trackBar_Length_stock.Value, self._Electrical_Circuit_PathMode_radioButton4.Checked, self._Electrical_Circuit_PathMode_radioButton1.Checked, self._Electrical_Circuit_PathMode_radioButton2.Checked, self._Electrical_Circuit_PathMode_radioButton3.Checked, self._Electrical_Circuit_PathMode_radioButton5.Checked, self._deltaU_boundary_value_textBox.Text, self._Select_Cable_by_DeltaU_checkBox.Checked, self._Round_value_textBox.Text, self._Require_tables_select_checkBox1.Checked, self._Require_tables_select_checkBox2.Checked, self._flat_calculation_way_radioButton1.Checked, self._textBox_VolumeCapacityNKU.Text, self._trackBar_VolumeCapacityNKU.Value, self._Distributed_Volt_Dropage_koefficient_textBox.Text, self._PhaseNaming_ABC_radioButton.Checked))







TeslaSettings().ShowDialog()

if Button_Cancel_pushed != 1: # Если кнопка "Cancel" не была нажата

	# Теперь переобъявим внутренние переменные по глобальным полученным из окошка

	# Метод выбора сечения кабелей
	if Cable_section_calculatingMethod_radioButton == 1:
		Cable_section_calculation_method = 1
	elif Cable_section_calculatingMethod_radioButton == 0:
		Cable_section_calculation_method = 0

	# распределённые потери
	# Может быть такая ситуация, что пользователь вводил корни слов для распределённых потерь с лишним пробелом. Тогда Volt_Dropage_key
	# будет выглядеть так: 'QQQ\r\n\r\nWWW'. А команда Volt_Dropage_key_textBox.split('\r\n') выдаст вот что: ['QQQ', '', 'WWW']
	# Поэтому нам нужно убрать пустые строки из этого списка, чтобы не накосячить с расчётом распределённых потерь.
	helplist = []
	for i in Volt_Dropage_key_textBox.split('\r\n'):
		if i != '':
			helplist.append(i.upper()) # заодно переведём в верхний регистр
	Volt_Dropage_key = '\r\n'.join(helplist) 
	if Volt_Dropage_key == '': # если пользователь вообще убрал все однокоренные слова, то придётся записать предупреждение. Иначе останется пустая строка и все линии будут считаться как распределённые.
		Volt_Dropage_key = '!Введите однокоренные слова для расчёта распределённых потерь!'

	# Запас кабеля по умолчанию
	Cable_stock_for_circuitry = Length_stock_textBox 

	# Режим траектории цепей
	Electrical_Circuit_PathMode_method = Electrical_Circuit_PathMode_radioButton

	# Граничное значение потерь
	# Ещё одна проверка на то что пользователь должен был ввести число в TextBox
	try:
		float(deltaU_boundary_value_textBox.replace(',', '.'))
	except ValueError:
		deltaU_boundary_value = '1.5' # если пользователь накосячил со вводом данных, вернём значение по умолчанию
	else:
		deltaU_boundary_value = deltaU_boundary_value_textBox.replace(',', '.') # заодно меняем запятую на точку

	# Округление значений до такой-то цифры после запятой
	Round_value_ts = Round_value_textBox 

	# Требовать выбора расчётной таблички и примечаний при расчёте схем
	if Require_tables_select_checkBox1 == False:
		Require_tables_select_ts = '0'
	else:
		Require_tables_select_ts = '1'

	# Требовать выбора таблички фазировки при выполнении фазировки
	if Require_tables_select_checkBox2 == False:
		Require_PHtables_select_ts = '0'
	else:
		Require_PHtables_select_ts = '1'

	# Выбирать сечение кабеля по потерям
	if Select_Cable_by_DeltaU_checkBox == False:
		Select_Cable_by_DeltaU_ts = '0'
	else:
		Select_Cable_by_DeltaU_ts = '1'

	# Способ расчёта квартир повышенной комфортности
	if flat_calculation_way_ts_radioButton == 0:
		flat_calculation_way_ts = '0'
	else:
		flat_calculation_way_ts = '1'

	# Понижающий коэффициент на распределённые потери
	#Distributed_Volt_Dropage_koefficient_textBox
	# Ещё одна проверка на то что пользователь должен был ввести число в TextBox
	try:
		float(Distributed_Volt_Dropage_koefficient_textBox.replace(',', '.'))
	except ValueError:
		Distributed_Volt_Dropage_koefficient = '0.5' # если пользователь накосячил со вводом данных, вернём значение по умолчанию
	else:
		Distributed_Volt_Dropage_koefficient = Distributed_Volt_Dropage_koefficient_textBox.replace(',', '.') # заодно меняем запятую на точку


	# Теперь запишем настройки в хранилище
	Tesla_settings_Storagelist = List[str]([Cable_section_calculation_method_for_Tesla_settings, str(Cable_section_calculation_method), Volt_Dropage_key_for_Tesla_settings, Volt_Dropage_key, Cable_stock_for_Tesla_settings, Cable_stock_for_circuitry, Electrical_Circuit_PathMode_method_for_Tesla_settings, str(Electrical_Circuit_PathMode_method), DeltaU_boundary_value_for_Tesla_settings, deltaU_boundary_value, Round_value_for_Tesla_settings, Round_value_ts, Require_tables_select_for_Tesla_settings, Require_tables_select_ts, Require_PHtables_select_for_Tesla_settings, Require_PHtables_select_ts, Select_Cable_by_DeltaU_for_Tesla_settings, Select_Cable_by_DeltaU_ts, flat_calculation_way_for_Tesla_settings, flat_calculation_way_ts, Distributed_Volt_Dropage_koefficient_for_Tesla_settings, Distributed_Volt_Dropage_koefficient, PhaseNaming_for_Tesla_settings, PhaseNaming_radiobuttonposition])
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Tesla_settings, ProjectInfoObject, FieldName_for_Tesla_settings, SchemaName_for_Tesla_settings, Tesla_settings_Storagelist) # пишем данные в хранилище 
	# Пишем запас свободного пространства в НКУ
	Wrtite_to_ExtensibleStorage (schemaGuid_for_VolumeCapacityNKU, ProjectInfoObject, FieldName_for_VolumeCapacityNKU, SchemaName_for_VolumeCapacityNKU, List[str]([VolumeCapacityNKU_textBox])) # пишем данные в хранилище 




#_____________________Принимаем и записываем данные из вложенного окошка распределённых потерь__________________________________________________
if Button_Cancel_DeltaUByGroups_Form_pushed != 1: # Если кнопка "Cancel" не была нажата в окошке распределённых потерь
	# Переведём список GroupsAndNamesForWindowOutput в форму для хранения в Хранилище: ['Номер цепи1?!?Наименование электроприёмника1?!?Заданные потери1', 'Номер цепи2?!?Наименование электроприёмника2?!?Заданные потери2', ...]
	hlplist = []
	for i in GroupsAndNamesForWindowOutput:
		if i[2] == '':
			hlp = '0'
		else:
			hlp = i[2]
		hlplist.append(i[0] + '?!?' + i[1] + '?!?' + hlp)

	# пишем данные в хранилище
	Tesla_settings_Distributed_volt_dropage_list = List[str](hlplist)
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Distributed_volt_dropage_Tesla_settings, ProjectInfoObject, FieldName_for_Distributed_volt_dropage_Tesla_settings, SchemaName_for_Distributed_volt_dropage_Tesla_settings, Tesla_settings_Distributed_volt_dropage_list)  




#___________________Принимаем и записываем данные из окошка Calculation Resourses (CR)_________________________________________________________

if Button_Cancel_CRF_Form_pushed != 1: # Если кнопка "Cancel" не была нажата
	# Сортируем списки по возрастанию
	
	# Запутанная синхронная сортировка по индексам. Скачано отсюда https://ru.stackoverflow.com/questions/599129/%D0%A1%D0%B8%D0%BD%D1%85%D1%80%D0%BE%D0%BD%D0%BD%D0%B0%D1%8F-%D1%81%D0%BE%D1%80%D1%82%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B0-%D1%81%D0%BF%D0%B8%D1%81%D0%BA%D0%BE%D0%B2-python
	Currents_and_SectionsOutput_copy = []
	indexes = sorted(range(len([float(j) for j in Currents_and_SectionsOutput[0]])), key=lambda i: [float(j) for j in Currents_and_SectionsOutput[0]][i]) # Получаем сортированные индексы первого списка (сортируем по сечениям)
	for i in Currents_and_SectionsOutput:
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[0][i] for i in indexes]) # переписываем отсортированные по индексам списки
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[1][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[2][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[3][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[4][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[5][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[6][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[7][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[8][i] for i in indexes])
		Currents_and_SectionsOutput_copy.append([Currents_and_SectionsOutput[9][i] for i in indexes])

	# Сортируем уставки автоматов
	Current_breakersOutput = [str(j) for j in sorted([int(i) for i in Current_breakersOutput])] 

	# Сортируем (по убыванию) понижающие коэффициенты совместной прокладки кабелей
	Cables_trays_reduction_factorOutput = [str(j) for j in sorted([float(i) for i in Cables_trays_reduction_factorOutput], reverse=True)] 

	# Сортируем (по убыванию) понижающие коэффициенты совместной установки автоматов
	CB_reduction_factorOutput = [str(j) for j in sorted([float(i) for i in CB_reduction_factorOutput], reverse=True)] 

	# Пишем данные из окна в Хранилище
	Write_several_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject, SchemaName_for_CR, 
	FieldName_for_CR_1, Currents_and_SectionsOutput_copy[0], 
	FieldName_for_CR_2, Currents_and_SectionsOutput_copy[2],
	FieldName_for_CR_3, Currents_and_SectionsOutput_copy[5], 
	FieldName_for_CR_4, Currents_and_SectionsOutput_copy[3],
	FieldName_for_CR_5, Currents_and_SectionsOutput_copy[6],
	FieldName_for_CR_6, Current_breakersOutput,
	FieldName_for_CR_7, Cables_trays_reduction_factorOutput,
	FieldName_for_CR_8, CB_reduction_factorOutput,
	FieldName_for_CR_9, VoltageDrop_Coefficiets_KnorrOutput, # коэфф. потерь Кнорринга пишем как есть, т.к. их порядок в хранилище всегдя одинаковый
	FieldName_for_CR_10, Currents_and_SectionsOutput_copy[1],
	FieldName_for_CR_11, Currents_and_SectionsOutput_copy[4],
	FieldName_for_CR_12, VoltageOutput,
	FieldName_for_CR_13, Currents_and_SectionsOutput_copy[7],
	FieldName_for_CR_14, Currents_and_SectionsOutput_copy[8],
	FieldName_for_CR_15, Currents_and_SectionsOutput_copy[9]
	)




#_____________________Принимаем и записываем данные из вложенного окошка Коэффициентов спроса (6-е хранилище)__________________________________________________
if Kc_Storage_Form_Button_Cancel_pushed != 1:
	# Надо раздербанить All_koeffs_Output на отдельные списки готовые для записи в Хранилище
	# [[1001, '1'], [1002, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600', '1000'], ['10.0', '5.1', '3.8', '3.2', '2.8', '2.6', '2.2', '1.95', '1.7', '1.5', '1.36', '1.27', '1.23', '1.19']], [1003, ['14', '20', '30', '40', '50', '60', '70'], ['0.8', '0.65', '0.6', '0.55', '0.5', '0.48', '0.45']], [1004, ['5', '6', '9', '12', '15', '18', '24', '40', '60', '100', '200', '400', '600'], ['1', '0.51', '0.38', '18', '24', '0.26', '0.24', '0.2', '0.18', '0.16', '0.14', '0.13', '0.11']], [1005, '0.9'], [1006, ['1', '2', '3', '4', '5', '6', '10', '20', '25'], ['1', '0.8', '0.8', '0.7', '0.7', '0.65', '0.5', '0.4', '0.35'], ['1', '0.9', '0.7', '0.8', '0.8', '0.75', '0.6', '0.5', '0.4']]]
	Kkr_flats_koefficient = All_koeffs_Output[0][1]
	Flat_count_SP = [i for i in All_koeffs_Output[1][1]]
	Flat_unit_wattage_SP = [i for i in All_koeffs_Output[1][2]]
	Py_high_comfort = [i for i in All_koeffs_Output[2][1]]
	Ks_high_comfort = [i for i in All_koeffs_Output[2][2]]
	Flat_count_high_comfort = [i for i in All_koeffs_Output[3][1]]
	Ko_high_comfort = [i for i in All_koeffs_Output[3][2]]
	Kcpwrres = All_koeffs_Output[4][1]
	Elevator_count_SP = [i for i in All_koeffs_Output[5][1]]
	Ks_elevators_below12 = [i for i in All_koeffs_Output[5][2]]
	Ks_elevators_above12 = [i for i in All_koeffs_Output[5][3]]

	# Пишем данные в Хранилище
	Write_several_fields_to_ExtensibleStorage (schemaGuid_for_Kc_Storage, ProjectInfoObject, SchemaName_for_Kc, 
	FieldName_for_Kc_1, [Kkr_flats_koefficient], 
	FieldName_for_Kc_2, [str(i) for i in Flat_count_SP],
	FieldName_for_Kc_3, [str(i) for i in Flat_unit_wattage_SP], 
	FieldName_for_Kc_4, [str(i) for i in Py_high_comfort],
	FieldName_for_Kc_5, [str(i) for i in Ks_high_comfort],
	FieldName_for_Kc_6, [str(i) for i in Flat_count_high_comfort],
	FieldName_for_Kc_7, [str(i) for i in Ko_high_comfort],
	FieldName_for_Kc_8, [Kcpwrres],
	FieldName_for_Kc_9, [str(i) for i in Elevator_count_SP],
	FieldName_for_Kc_10, [str(i) for i in Ks_elevators_below12],
	FieldName_for_Kc_11, [str(i) for i in Ks_elevators_above12],
	FieldName_for_Kc_12, Load_Class_elevators,
	FieldName_for_Kc_13, Load_Class_falts,
	FieldName_for_Kc_14, [str(i) for i in Ks_Reserve_1],
	FieldName_for_Kc_15, [str(i) for i in Ks_Reserve_2]
	)
	#Kc_Storage_Form().ShowDialog()




transGroup.Assimilate() # принимаем группу транзакций





'''
#_____________________Принимаем и записываем данные из вложенного окошка имён параметров (4-е хранилище)__________________________________________________
if Button_Cancel_for_Param_Names_Storage_pushed == 0: # Если в окошке нажали ОК

	# формируем список для записи
	Storagelist_for_Param_Names_Storage = List[str]([Param_name_0_for_Param_Names_Storage, ParamNamesForWindowOutput[0], Param_description_0_for_Param_Names_Storage,
	Param_name_1_for_Param_Names_Storage, ParamNamesForWindowOutput[1], Param_description_1_for_Param_Names_Storage,
	Param_name_2_for_Param_Names_Storage, ParamNamesForWindowOutput[2], Param_description_2_for_Param_Names_Storage, 
	Param_name_3_for_Param_Names_Storage, ParamNamesForWindowOutput[3], Param_description_3_for_Param_Names_Storage, 
	Param_name_4_for_Param_Names_Storage, ParamNamesForWindowOutput[4], Param_description_4_for_Param_Names_Storage,
	Param_name_5_for_Param_Names_Storage, ParamNamesForWindowOutput[5], Param_description_5_for_Param_Names_Storage,
	Param_name_6_for_Param_Names_Storage, ParamNamesForWindowOutput[6], Param_description_6_for_Param_Names_Storage,
	Param_name_7_for_Param_Names_Storage, ParamNamesForWindowOutput[7], Param_description_7_for_Param_Names_Storage])

	# пишем данные в хранилище
	Wrtite_to_ExtensibleStorage (schemaGuid_for_Param_Names_Storage, ProjectInfoObject, FieldName_for_Param_Names_Storage, SchemaName_for_Param_Names_Storage, Storagelist_for_Param_Names_Storage) # пишем данные в хранилище 
'''




'''
Старые данные по умолчанию

defaultPdata = ['Ру (вся)@@!!@@ALL@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (вся)@@!!@@ALL@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (др. классиф.)@@!!@@OTHER@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рр (др. классиф.)@@!!@@OTHER@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Ру.л@@!!@@Лифты@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рр.сантех.@@!!@@hvac&&??&&ОВК&&??&&Системы ВК&&??&&Системы ОВ@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рраб.осв.@@!!@@Рабочее освещение@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ргор.пищ.@@!!@@Тепловое оборудование пищеблоков@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр.ов@@!!@@Системы ОВ@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']


defaultKcdata = ['Костыль для лифтов@@!!@@Лифты@@!!@@Кс.л.@@!!@@EPcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.л@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&1$$>>$$1&&??&&1',
'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Рр.сантех.&&??&&Рр.ов@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4',
'Таблица 7.6 - Коэффициенты спроса для рабочего освещения@@!!@@Рабочее освещение@@!!@@Кс.раб.осв.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Рраб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@5&&??&&10&&??&&15&&??&&25&&??&&50&&??&&100&&??&&200&&??&&400&&??&&500$$>>$$1&&??&&0.8&&??&&0.7&&??&&0.6&&??&&0.5&&??&&0.4&&??&&0.35&&??&&0.3&&??&&0.3',
'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков@@!!@@Тепловое оборудование пищеблоков@@!!@@Кс.терм.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ргор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&60&&??&&100&&??&&120$$>>$$0.9&&??&&0.85&&??&&0.75&&??&&0.65&&??&&0.6&&??&&0.5&&??&&0.45&&??&&0.4&&??&&0.3&&??&&0.3&&??&&0.25']


defaultUserFormuladata = ['Расчёт Рр@@!!@@Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'test count@@!!@@Рраб.осв.&&??&&*&&??&&Кс.о.&&??&&+&&??&&Ргор.пищ.&&??&&*&&??&&Кс.гор.пищ.&&??&&+&&??&&Рр.сантех.&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру.л&&??&&*&&??&&Кс.л.&&??&&+&&??&&Рр (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']
















defaultKcdata = ['Костыль для лифтов@@!!@@Лифты@@!!@@Кс.л.@@!!@@EPcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ру.л@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@1&&??&&1$$>>$$1&&??&&1',
'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин@@!!@@Системы ОВ@@!!@@Кс.сан.тех.@@!!@@epcount@@!!@@Зависит от уд.веса в других нагрузках@@!!@@Ру (вся)@@!!@@Рр.сантех.&&??&&Рр.ов@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11&&??&&column12@@!!@@Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@Количество электроприёмников:&&??&&2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&50&&??&&100&&??&&200$$>>$$100&&??&&1&&??&&0.9&&??&&0.8&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$84&&??&&1&&??&&1&&??&&0.75&&??&&0.7&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.55&&??&&0.5$$>>$$74&&??&&1&&??&&1&&??&&0.7&&??&&0.65&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.45$$>>$$49&&??&&1&&??&&1&&??&&0.65&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45$$>>$$24&&??&&1&&??&&1&&??&&0.6&&??&&0.6&&??&&0.55&&??&&0.5&&??&&0.5&&??&&0.5&&??&&0.45&&??&&0.45&&??&&0.4',
'Таблица 7.6 - Коэффициенты спроса для рабочего освещения@@!!@@Рабочее освещение@@!!@@Кс.о.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Рраб.осв.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9@@!!@@Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@5&&??&&10&&??&&15&&??&&25&&??&&50&&??&&100&&??&&200&&??&&400&&??&&500$$>>$$1&&??&&0.8&&??&&0.7&&??&&0.6&&??&&0.5&&??&&0.4&&??&&0.35&&??&&0.3&&??&&0.3',
'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков@@!!@@Тепловое оборудование пищеблоков@@!!@@Кс.гор.пищ.@@!!@@epcount@@!!@@Не зависит от уд.веса в других нагрузках@@!!@@@@!!@@Ргор.пищ.@@!!@@Резерв 2@@!!@@Резерв 3@@!!@@column1&&??&&column2&&??&&column3&&??&&column4&&??&&column5&&??&&column6&&??&&column7&&??&&column8&&??&&column9&&??&&column10&&??&&column11@@!!@@Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)&&??&&Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)@@!!@@2&&??&&3&&??&&5&&??&&8&&??&&10&&??&&15&&??&&20&&??&&30&&??&&60&&??&&100&&??&&120$$>>$$0.9&&??&&0.85&&??&&0.75&&??&&0.65&&??&&0.6&&??&&0.5&&??&&0.45&&??&&0.4&&??&&0.3&&??&&0.3&&??&&0.25']


defaultPdata = ['Ру (вся)@@!!@@ALL@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (вся)@@!!@@ALL@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр (без классиф.)@@!!@@Нет классификации&&??&&@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ру (др. классиф.)@@!!@@OTHER@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рр (др. классиф.)@@!!@@OTHER@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Ру.л@@!!@@Лифты@@!!@@Py@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рр.сантех.@@!!@@hvac&&??&&ОВК&&??&&Системы ВК&&??&&Системы ОВ@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3',
'Рраб.осв.@@!!@@Рабочее освещение@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Ргор.пищ.@@!!@@Тепловое оборудование пищеблоков@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'Рр.ов@@!!@@Системы ОВ@@!!@@Pp@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']


defaultUserFormuladata = ['Расчёт Рр@@!!@@Рр (вся)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3', 
'test count@@!!@@Рраб.осв.&&??&&*&&??&&Кс.о.&&??&&+&&??&&Ргор.пищ.&&??&&*&&??&&Кс.гор.пищ.&&??&&+&&??&&Рр.сантех.&&??&&*&&??&&Кс.сан.тех.&&??&&+&&??&&Ру.л&&??&&*&&??&&Кс.л.&&??&&+&&??&&Рр (без классиф.)@@!!@@Резерв 1@@!!@@Резерв 2@@!!@@Резерв 3']




# Табличные данные по умолчанию:
# Поправочный коэффициент для расчёта нагрузки жилого дома в зависимости от региона (п.7.1.10 поправок к СП256)
Kkr_flats_koefficient = [1]
# Удельная расчётная электрическая нагрузка (кВт) для квартир мощностью Рр=10 кВт (по табл.7.1 СП 256.1325800.2016), или коэффициент одновременности для квартир повышенной комфортности (по табл.7.3 того же СП)
# Для этого перепишем сюда табл. 7.1 СП 256.1325800.2016
Flat_count_SP = [5, 6, 9, 12, 15, 18, 24, 40, 60, 100, 200, 400, 600, 1000] # количество квартир
Flat_unit_wattage_SP = [10.0, 5.1, 3.8, 3.2, 2.8, 2.6, 2.2, 1.95, 1.7, 1.5, 1.36, 1.27, 1.23, 1.19] # удельная расчётная электрическая нагрузка при количестве квартир
# А также таблицы 7.2 и 7.3
Py_high_comfort = [14, 20, 30, 40, 50, 60, 70]
Ks_high_comfort = [0.8, 0.65, 0.6, 0.55, 0.5, 0.48, 0.45] # коэффициенты спроса для квартир повышенной комфортности
Flat_count_high_comfort = [5, 6, 9, 12, 15, 18, 24, 40, 60, 100, 200, 400, 600] # количество квартир
Ko_high_comfort = [1, 0.51, 0.38, 0.32, 0.29, 0.26, 0.24, 0.2, 0.18, 0.16, 0.14, 0.13, 0.11] # Коэффициенты одновременности для квартир повышенной комфортности
Kcpwrres = [0.9] # коэффициент на силовую нагрузку жилого дома по СП 256.1325800.2016 п. 7.1.10 - Рр.ж.д = Ркв + 0,9 * Рс
Elevator_count_SP = [1, 2, 3, 4, 5, 6, 10, 20, 25]
Ks_elevators_below12 = [1, 0.8, 0.8, 0.7, 0.7, 0.65, 0.5, 0.4, 0.35]
Ks_elevators_above12 = [1, 0.9, 0.9, 0.8, 0.8, 0.75, 0.6, 0.5, 0.4]
# Вспомогательный костыль: поиск частей слов нагрузок
Load_Class_elevators = ['ЛИФТ'] # поиск части слова Лифты в Классификации нагрузок
Load_Class_falts = ['КВАРТИР', 'АПАРТАМЕНТ'] # и квартир
Ks_Reserve_1 = [] # резервное поле
Ks_Reserve_2 = [] # резервное поле












		# Удаляем вся ряды
		a = self._Param_Names_Storage_dataGridView1.Rows.Count
		while a > 0:
			self._Param_Names_Storage_dataGridView1.Rows.RemoveAt(0) 
			a = a - 1	



if Button_Cancel_pushed == 1:
	#quit()
	sys.exit()


Volt_Dropage_key.split('\r\n')

Многострочный текст в текст боксе разделяется так:
'qqq\r\nwww\r\neee\r\nrrr'

ara.partition('\r\n')
('qqq', '\r\n', 'www\r\neee\r\nrrr')

ara.split('\r\n')
['qqq', 'www', 'eee', 'rrr'] - то что надо

'\r\n'.join(['qqq', 'www', 'eee', 'rrr']) - обратная операция

ara1 = []
for i in ara.partition('\r\n'):


MessageBox.Show(Volt_Dropage_key_textBox.upper(), 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)

'''