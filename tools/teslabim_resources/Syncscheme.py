'''
Программа синхронизирует данные из электроцепей Revit (созданных на планах) с однолинейными схемами (конкретными автоматическими выключателями).
Также синхронизируются ящики управления. Логика такая: семейства типовых аннотаций "GA_SHM_Ящик управления" синхронизируются с семействами в модели с именем "EE_ШУВ".
Кроме того, при запуске программы, принудительно для всех цепей в проекте устанавливает режим траектории цепей. 
Режим траектории который будет установлен можно выбрать в окне настроек программы.
Запас кабеля по умолчанию можно настроить в окне настроек Программы. 
Данный запас будет добавлен к длинам цепей, которые посчитал Revit при синхронизации схем.

'''

# http://www.revitapidocs.com/ -  очень полезный сайт

'''
хороший сайт по Питону
https://pythonworld.ru/tipy-dannyx-v-python/chisla-int-float-complex.html
'''

#закрывает консоль которая иначе вылетает после работы программы
#__window__.Close()

#всё это хозяйство запускаем в Ревите с помощью приложения Python Shell
#сам код написан в программе Visual Studio Code (но таких приложений полно, можно любое программерское скачивать)

#подгружаем нужные библиотеки
import clr
import System
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')
#clr.AddReference('RevitServices')
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
#from RevitServices.Persistence import DocumentManager
#from RevitServices.Transactions import TransactionManager
from Autodesk.Revit.ApplicationServices import Application
from System.Windows.Forms import *
from System.Drawing import *
import sys
clr.AddReference('RevitAPIUI') # подгружаем библиотеку для набора Autodesk.Revit.UI.Selection. А также для того чтобы Ревитовские окошки показывались
from Autodesk.Revit.UI.Selection import ObjectType
# Библиотеки ExtensibleStorage
import System.Runtime.InteropServices
from Autodesk.Revit.DB.ExtensibleStorage import *
from Autodesk.Revit.DB.ExtensibleStorage import *
from System import Guid # you need to import this, when you work with Guids!
from System.Collections.Generic import *
# Библиотеки для того чтобы Ревитовские окошки показывались
from Autodesk.Revit.UI import *


#doc = __revit__.ActiveUIDocument.Document
#uidoc = __revit__.ActiveUIDocument






# Функция по проверке повторяющихся имён (групп, панелей)
# На входе список с именами для проверки в виде строк, например ['N1-1', 'N1-2', 'N1-3', 'N1-4'], и две строки для правильного вывода предупреждения, т.е. что выводим: группы, имена панелей, автоматы и ящики управления.
# например: what1 = 'группа', what2 = 'У выбранных автоматов есть повторяющиеся номера групп. Скорее всего - это ошибка, т.к. у каждого автомата должен быть уникальный номер группы.'
# На выходе окно предупреждения что и сколько раз повторяется
def Repeated_names (Names_list, what1, what2):
	# формируем список повторяющихся имён
	Names_of_Repeated_Groups = []
	# а это список с количеством повторений. Пример: [2, 3, 2, 4]. Например: группа N1-1 повторяется 2 раза, а группа N1-2 повторяется 4 раза.
	Counts_of_Repeated_Groups = []
	for i in Names_list:
		if Names_list.count(i) > 1: # если имя группы встечается в спике всех групп более одного раза
			Names_of_Repeated_Groups.append(i)
			Counts_of_Repeated_Groups.append(Names_list.count(i))
			a = 0
			while a < Names_list.count(i):
				map(Names_list.remove(i), Names_list)
				a = a+1

	# формируем список с повторяющимися именами групп и количеством повторений для вывода на экран
	Repeated_Groups_error_list = []
	a = 0
	while a < len(Names_of_Repeated_Groups):
		Repeated_Groups_error_list.append(' ' + what1 + ' ')
		if Names_of_Repeated_Groups[a] == '':
			Repeated_Groups_error_list.append(' "<имя группы не заполнено>" ')
		else:
			Repeated_Groups_error_list.append(' "' + Names_of_Repeated_Groups[a] + '" ')
		Repeated_Groups_error_list.append(' повторяется ')
		Repeated_Groups_error_list.append(str(Counts_of_Repeated_Groups[a]))
		Repeated_Groups_error_list.append('раза;')
		a = a+1

	# формируем сообщение об ошибке если есть повторяющиеся группы
	if Names_of_Repeated_Groups != [] and Counts_of_Repeated_Groups != []:
		error_text_in_window = (what2 + ' Список повторений:' + ' '.join(Repeated_Groups_error_list))
		MessageBox.Show(error_text_in_window, 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)



# Функция получает значение параметров 'Имя' и 'Номер' из пространства в котором располагается выбранное семейство
# На входе элемент в виде <Autodesk.Revit.DB.FamilyInstance object at 0x0000000000000487 [Autodesk.Revit.DB.FamilyInstance]>
# На выходе кортеж с именем и номером пространства в котором располагается семейство. Например: ('Большая комната', '2')
# Если исходный элемент не располагался ни в каком пространстве, то на выходе будет кортеж (None, None).
# пример обращения GetSpaceNameNumberFromElement(ara)
def GetSpaceNameNumberFromElement (element):
	phase_collector = FilteredElementCollector(doc).OfClass(Phase) # фильтр со всеми фазами проектирования (вспомогательно)

	# Достаём пространство в котором располагается элемент
	element_space = None # Пространство в котором располагается элемент. Останется None если элемент не расположен ни в каком пространстве
	for i in [i for i in phase_collector]:
		try: 
			element_space = element.get_Space(i) # выдаёт <Autodesk.Revit.DB.Mechanical.Space object at 0x00000000000002B4 [Autodesk.Revit.DB.Mechanical.Space]>
		except:
			if element_space == None:
				element_space = None

	if element_space != None:
		# Достаём значения интересующих нас параметров
		for i in element_space.Parameters:
			if i.Definition.BuiltInParameter == BuiltInParameter.ROOM_NAME:
				param_roomname = i
			if i.Definition.BuiltInParameter == BuiltInParameter.ROOM_NUMBER:
				param_roomnumber = i
		
		param_roomnameAsstring = param_roomname.AsString()
		param_roomnumberAsstring = param_roomnumber.AsString()
	else:
		param_roomnameAsstring = None
		param_roomnumberAsstring = None

	return param_roomnameAsstring, param_roomnumberAsstring



# Функция получает параметр по встроенному имени параметра
# На входе: element - элемент вида: <Autodesk.Revit.DB.Electrical.ElectricalSystem object at 0x000000000000006C [Autodesk.Revit.DB.Electrical.ElectricalSystem]>
#	BuiltInParameterWithName - встроенное имя параметра вида: Autodesk.Revit.DB.BuiltInParameter.RBS_ELEC_TRUE_LOAD
# На выходе сам параметр вида: <Autodesk.Revit.DB.Parameter object at 0x00000000000000AE [Autodesk.Revit.DB.Parameter]>
# Пример обращения: GetBuiltinParam(ara, BuiltInParameter.RBS_ELEC_TRUE_LOAD)
def GetBuiltinParam(element, BuiltInParameterWithName):
	Builtinparam = None
	for i in element.Parameters:
		if i.Definition.BuiltInParameter == BuiltInParameterWithName:
			Builtinparam = i
	if Builtinparam == None:
		raise Exception('Отсутствует параметр ' + str(BuiltInParameter.RBS_ELEC_TRUE_LOAD) + '. Возможно в электроцепи подключены семейства не относящиеся к электросетям. Если ошибка повторится - обратитесь к разработчику.')
	return Builtinparam




# Функция выдаёт усреднённое значение длины электрической цепи. А потом возвращает режим траектории цепи в изначальное положение.
# На входе электрическая цепь в виде <Autodesk.Revit.DB.Electrical.ElectricalSystem object at 0x0000000000000170 [Autodesk.Revit.DB.Electrical.ElectricalSystem]>
# На выходе усреднённая длина = (max длина - min длина) / 2 + min длина в формате float, например 12.55795084781505
# Пример обращения GetMinMaxCircuitPath(ara)
def GetMinMaxCircuitPath(ElectricalCircuit):
	if ElectricalCircuit.CircuitPathMode == Electrical.ElectricalCircuitPathMode.FarthestDevice: # если изначально у цепи было FarthestDevice
		try:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS) # получаем длину
		except:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.AllDevices # теперь меняем на AllDevices
		t.Commit()
		try:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS)
		except:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		# Возвращаем CircuitPathMode на место
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.FarthestDevice
		t.Commit()
	elif ElectricalCircuit.CircuitPathMode == Electrical.ElectricalCircuitPathMode.AllDevices:
		try:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS) # получаем длину
		except:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.FarthestDevice
		t.Commit()
		try:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS)
		except:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		# Возвращаем CircuitPathMode на место
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.AllDevices
		t.Commit()
	elif ElectricalCircuit.CircuitPathMode == Electrical.ElectricalCircuitPathMode.Custom: # если был выставлен пользовательский режим траектории, то всё равно возьмём усреднённое значение
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.AllDevices # теперь меняем на AllDevices
		t.Commit()
		try:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS)
		except:
			l1 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.FarthestDevice
		t.Commit()
		try:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS)
		except:
			l2 = UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(ElectricalCircuit, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters)
		t = Transaction(doc, 'Change CircuitPathMode')
		t.Start()
		ElectricalCircuit.CircuitPathMode = Electrical.ElectricalCircuitPathMode.Custom
		t.Commit()
	deltalpertwo = (max(l1, l2) - min(l1, l2)) / 2
	l_averaged = min(l1, l2) + deltalpertwo
	return l_averaged



















''' создаём выборку. Пользователь выбирает нужные элементы'''
ids = uidoc.Selection.GetElementIds()

idd = [str(i) for i in ids]

# Если пользователь до запуска программы ничего не выбрал, то предложим ему выбрать после запуска программы
if len(ids) == 0:
	pickedObjs = uidoc.Selection.PickObjects(ObjectType.Element, "Выберите автоматические выключатели")
	idd = [str(i.ElementId) for i in pickedObjs]

#сообщение об ошибке которое должно вывестись в следующем модуле
error_text_in_window = 'Ничего не выбрано. Пожалуйста выберите автоматы которые должны быть синхронизированы с планами'
#если ничего не выбрано, выйти из программы
if idd == []: 
	raise Exception(error_text_in_window)
	#TaskDialog.Show('Ошибка', error_text_in_window)
	#MessageBox.Show(error_text_in_window, 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	#sys.exit()



#если пользователь что-то выбрал, продолжаем
try: # для Ревитов до 2025
	if isinstance(idd, list) == True:
		elems = [doc.GetElement(ElementId(int(i))) for i in idd]
	else:
		elems = doc.GetElement(ElementId(int(idd)))
except: # для Ревита 2026 где integer 32-битный нужно задавать как long 64-битный
	if isinstance(idd, list) == True:
		elems = [doc.GetElement(ElementId(long(i))) for i in idd]
	else:
		elems = doc.GetElement(ElementId(long(idd)))

'''Фильтруем общую выборку'''	


elems_avtomats = [] # семейства автоматических выключателей
Boxes = [] # Список со всеми щитками ваще
elems_control_boards = [] # семейства ящиков управления (типовых аннотаций)
elems_control_boards_model = [] # семейства ящиков управления (семейств из модели)
elems_TSLCable = [] # Семейства TSL_Кабель

#_____________________________________________________________________________________________________________________________________________________
# Объявим семейства с которыми работает данная программа.
# Разлочить при тестировании в Python Shell. А так получаем на входе от C#
'''
avt_family_names = ['TSL_2D автоматический выключатель_ВРУ', 'TSL_2D автоматический выключатель_Щит']
Control_board_family_names = ['TSL_Ящик управления']
using_auxiliary_cables = ['TSL_Кабель', 'TSL_Кабель с текстом 1.8']
using_calculated_tables = ['TSL_Таблица_Расчетная для схемы', 'TSL_Таблица_Расчетная для щитов'] 
fam_param_names = ['ADSK_Единица измерения', 'ADSK_Завод-изготовитель', 'ADSK_Наименование', 'ADSK_Обозначение']
# для понимания соответствия: fam_param_names[0] fam_param_names[1] fam_param_names[2]  fam_param_names[3] 
# А также имена параметров с которыми работает программа:
Param_Py = 'Py'
Param_Kc = 'Kc' 
Param_Cable_length = 'Длина проводника' # длина кабеля 
Param_Circuit_number = 'Номер цепи'
Param_3phase_CB = '3-фазный аппарат'
Param_Accessory = 'Принадлежность щиту'
Param_PanelName = 'Имя панели'
Param_Circuit_breaker_nominal = 'Уставка аппарата'
Param_Cosf = 'Cosf'
Param_Electric_receiver_Name = 'Наименование электроприёмника'
Param_Room_Name = 'Наименование помещения'
Param_Consumers_count = 'Число электроприёмников'
Param_Laying_Method = 'Способ прокладки'
Param_TSL_WireLength = 'TSL_Длина проводника'
Param_TSL_Param_Laying_Method = 'TSL_Способ прокладки'
Param_FarestWireLength = "Длина проводника до дальнего устройства"
Param_ReducedWireLength = "Длина проводника приведённая"
Param_TSL_FarestWireLength = "TSL_Длина проводника до дальнего устройства"
Param_TSL_ReducedWireLength = "TSL_Длина проводника приведённая"
# Семейства из модели (не типовые аннотации с которыми работает программа)
Control_board_family_names_Model = ['EE_ШУВ']

# Переменные отвечающие за соединение с ExtensibleStorage
Guidstr = 'c94ca2e5-771e-407d-9c09-f62feb4448b6'
FieldName_for_Tesla_settings = 'Tesla_settings_list'
Cable_stock_for_Tesla_settings = 'Cable_stock_for_circuitry'
Electrical_Circuit_PathMode_method_for_Tesla_settings = 'Electrical_Circuit_PathMode_method'


# Переменные отвечающие за соединение с хранилищем имён параметров (4-е хранилище)
Guidstr_Param_Names_Storage = '44bf8d44-4a4a-4fde-ada8-cd7d802648c4'
SchemaName_for_Param_Names_Storage = 'Param_Names_Storage'
FieldName_for_Param_Names_Storage = 'Param_Names_Storage_list'
'''

#_____________________________________________________________________________________________________________________________________________________

Smart_lines_names = ['TSL_GM_в_Участок трассы_Горизонтальный', 'TSL_GM_в_Участок трассы_Вертикальный']

# Из C# мы получаем списки с конкретным типом данных string. И почему-то к таким спискам нельзя применять некоторые команды, например .count(i.Name)
# поэтому для корректной работы придётся пересобрать все входящие списки заново. Для этого нужен вспомогательный список CS_help = []
CS_help = []
[CS_help.append(i) for i in avt_family_names]
avt_family_names = []
[avt_family_names.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in Control_board_family_names]
Control_board_family_names = []
[Control_board_family_names.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in Control_board_family_names_Model]
Control_board_family_names_Model = []
[Control_board_family_names_Model.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in using_calculated_tables]
using_calculated_tables = []
[using_calculated_tables.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in using_auxiliary_cables]
TSLCable_family_name = CS_help[0] # Забираем имя "TSL_Кабель"




# Проверяем связь с настройками Тэслы. Если ExtensibleStorage с гуидом Guidstr присутствет в проекте, берём значения переменных оттуда.
# Если такого хранилища нет, выдадим предупреждение и выставим значения переменных по умолчанию.
schemaGuid_for_Tesla_settings = System.Guid(Guidstr) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
# получаем объект "информация о проекте"
ProjectInfoObject = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).WhereElementIsNotElementType().ToElements()[0] 
# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch = Schema.Lookup(schemaGuid_for_Tesla_settings)
if sch is None or ProjectInfoObject.GetEntity(sch).IsValid() == False: # Проверяем есть ли ExtensibleStorage
	TaskDialog.Show('Синхронизация схем', 'Невозможно найти настройки программы.\n Значения настроек будут использованы по умолчанию.') # Показывает окошко в стиле Ревит
	# Предложим пользователю возможность выбора сечений кабелей (делается в проге "Настройки Тэслы"). Либо по току уставки автомата, либо по току срабатывания автоматов с учётом коэффициентов совместной установки.
	Cable_stock_for_circuitry = 10 # 10% запас кабеля по умолчанию.
	Electrical_Circuit_PathMode_method = 1 # ставить ли свойства цепей "все устройства" (значение 1) или "наиболее удалённое устройство" (значение 2) или "не управлять режимом траектории" (значение 0) или "усреднённое значение" (значение 3)
else: # Если с Хранилищем всё в порядке, считываем переменные оттуда
	# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
	#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
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
	if len(znach) < 10: # Вот эту цифру и будем менять здесь в коде при добавлении новых настроек Тэслы
		raise Exception('С выходом новой версии программы добавились новые настройки.\n Запустите сначала кнопку "Настройки" для корректной работы.')
		#TaskDialog.Show('Расчёт схем', 'С выходом новой версии программы добавились новые настройки.\n Запустите сначала кнопку "Настройки" для корректной работы.')
		#sys.exit()
	# Присваиваем значения переменным в соответствии с информацией полученной из хранилища
	Cable_stock_for_circuitry = znach[int(znach.index(Cable_stock_for_Tesla_settings) + 1)] # поясняю: находим значение самой переменной на следующей (+1) позиции за именем самой переменной в списке из хранилища
	Electrical_Circuit_PathMode_method = int(znach[int(znach.index(Electrical_Circuit_PathMode_method_for_Tesla_settings) + 1)])




#_________________________________ Работаем с 4-м хранилищем (имена параметров с которыми работает программа) ____________________________________________________________________________
schemaGuid_for_Param_Names_Storage = System.Guid(Guidstr_Param_Names_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_Param_Names_Storage = Schema.Lookup(schemaGuid_for_Param_Names_Storage)
# Внутренние (только для этой программы) названия параметров:
Param_name_20_for_Param_Names_Storage = 'Param_name_20_for_Param_Names_Storage'
Param_name_30_for_Param_Names_Storage = 'Param_name_30_for_Param_Names_Storage'
Param_name_41_for_Param_Names_Storage = 'Param_name_41_for_Param_Names_Storage'
Param_name_42_for_Param_Names_Storage = 'Param_name_42_for_Param_Names_Storage'

# Если ExtensibleStorage с указанным guid'ом отсутствует, то type(sch_Param_Names_Storage) будет <type 'NoneType'>
if sch_Param_Names_Storage is None or ProjectInfoObject.GetEntity(sch_Param_Names_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	Param_TSL_WireLength = 'TSL_Длина проводника'
	Param_TSL_Param_Laying_Method = 'TSL_Способ прокладки'
	Param_TSL_FarestWireLength = 'TSL_Длина проводника до дальнего устройства'
	Param_TSL_ReducedWireLength = 'TSL_Длина проводника приведённая'
	TaskDialog.Show('Синхронизация', 'Имена параметров с которыми работает синхронизация не были найдены в Настройках Программы.\n Будут использованы имена параметров по умолчанию.\nЧтобы избежать появления этого предупреждения - откройте Настройки Программы и нажмите "Сохранить и закрыть".')
else: # Если имена параметров есть в Хранилище, то считаем их оттуда
	# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
	#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
	#Получаем Schema:
	sch2 = Schema.Lookup(schemaGuid_for_Param_Names_Storage)
	#Получаем Entity из элемента:
	ent2 = ProjectInfoObject.GetEntity(sch2)
	#Уже знакомым способом получаем «поля»:
	field_Param_Names_Storage = sch2.GetField(FieldName_for_Param_Names_Storage)
	#Для считывания значений используем метод Entity.Get:
	znachParams = ent2.Get[IList[str]](field_Param_Names_Storage) # выдаёт List[str](['a', 'list', 'of', 'strings'])

	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znachParams]
	znachParams = []
	[znachParams.append(i) for i in CS_help] # ['Param_name_0_for_Param_Names_Storage', u'BS_Единицы измерения', 'Param_name_1_for_Param_Names_Storage', u'BS_Изготовитель', 'Param_name_2_for_Param_Names_Storage', u'PIC_Наименование_по_ГОСТ', 'Param_name_3_for_Param_Names_Storage', u'BS_Обозначение', 'Param_name_2_for_Param_Names_Storage', u'EL_Имя нагрузки']

	try:
		Param_TSL_WireLength = znachParams[int(znachParams.index(Param_name_20_for_Param_Names_Storage) + 1)]
		Param_TSL_Param_Laying_Method = znachParams[int(znachParams.index(Param_name_30_for_Param_Names_Storage) + 1)]
		Param_TSL_FarestWireLength = znachParams[int(znachParams.index(Param_name_41_for_Param_Names_Storage) + 1)]
		Param_TSL_ReducedWireLength = znachParams[int(znachParams.index(Param_name_42_for_Param_Names_Storage) + 1)]
	except ValueError:
		Param_TSL_WireLength = 'TSL_Длина проводника'
		Param_TSL_Param_Laying_Method = 'TSL_Способ прокладки'
		Param_TSL_FarestWireLength = 'TSL_Длина проводника до дальнего устройства'
		Param_TSL_ReducedWireLength = 'TSL_Длина проводника приведённая'
		TaskDialog.Show('Синхронизация', 'Имена параметров с которыми работает синхронизация не были найдены в Настройках Программы.\n Будут использованы имена параметров по умолчанию.\nЧтобы избежать появления этого предупреждения - откройте Настройки Программы и нажмите "Сохранить и закрыть".')














#_______________Хранилище выставленных флажков в Синхронизации________________________________________________________

# Переменные отвечающие за хранилище положения флажков в окне синхронизации. Не будем брать их из GLOBALS, т.к. работают они только тут в этой команде.
GuidstrSyncSchemeCheckBoxesPosition = 'df1adfd0-962f-4a87-972e-cb0133247b7c'
SchemaName_for_SyncSchemeCheckBoxesPosition = 'SyncSchemeCheckBoxesPosition_Storage'
FieldName_for_SyncSchemeCheckBoxesPosition = 'SyncSchemeCheckBoxesPositionList'


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

# Список выставленных флажков по умолчанию
# Вид (Ру, 1, Cosf, 1, ....). 1 - флажок выставлен, 0 - не выставлен.
SyncSchemeCheckBoxesPositionList_by_Default = List[str](['Py', '1', 'Cosf', '1', 'L', '1', 'U', '1', 'Имя щита', '1', 'Наименование нагрузки', '1', 'Наименование помещения', '1', 'Число электроприёмников', '1', 'Синхр.коэфф.спроса', '0', 'Синхр.ящики упр.', '1', 'Что записать номер или имя пространства', '1', 'Способ прокладки проводника', '1'])



# Проверяем связь с настройками Тэслы. Если ExtensibleStorage с гуидом Guidstr присутствет в проекте, берём значения переменных оттуда.
# Если такого хранилища нет, выдадим предупреждение и выставим значения переменных по умолчанию.
schemaGuid_for_SyncSchemeCheckBoxesPosition = System.Guid(GuidstrSyncSchemeCheckBoxesPosition) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_SyncSchemeCheckBoxesPosition = Schema.Lookup(schemaGuid_for_SyncSchemeCheckBoxesPosition)
if sch_SyncSchemeCheckBoxesPosition is None or ProjectInfoObject.GetEntity(sch_SyncSchemeCheckBoxesPosition).IsValid() == False: # Проверяем есть ли ExtensibleStorage
	# TaskDialog.Show('Синхронизация схем', 'Невозможно найти настройки программы.\n Значения настроек будут использованы по умолчанию.') # Показывает окошко в стиле Ревит
	Wrtite_to_ExtensibleStorage (schemaGuid_for_SyncSchemeCheckBoxesPosition, ProjectInfoObject, FieldName_for_SyncSchemeCheckBoxesPosition, SchemaName_for_SyncSchemeCheckBoxesPosition, SyncSchemeCheckBoxesPositionList_by_Default) # пишем данные в хранилище 

# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
sch_SyncSchemeCheckBoxesPosition = Schema.Lookup(schemaGuid_for_SyncSchemeCheckBoxesPosition)
#Получаем Entity из элемента:
ent_SyncSchemeCheckBoxesPosition = ProjectInfoObject.GetEntity(sch_SyncSchemeCheckBoxesPosition)
#Уже знакомым способом получаем «поля»:
field_SyncSchemeCheckBoxesPosition = sch_SyncSchemeCheckBoxesPosition.GetField(FieldName_for_SyncSchemeCheckBoxesPosition)
#Для считывания значений используем метод Entity.Get:
znach_SyncSchemeCheckBoxesPosition = ent_SyncSchemeCheckBoxesPosition.Get[IList[str]](field_SyncSchemeCheckBoxesPosition) # выдаёт List[str](['a', 'list', 'of', 'strings'])
# пересоберём список чтобы привести его к нормальному виду
CS_help = []
[CS_help.append(i) for i in znach_SyncSchemeCheckBoxesPosition]
znach_SyncSchemeCheckBoxesPosition = []
[znach_SyncSchemeCheckBoxesPosition.append(i) for i in CS_help]


# При появлении новых параметров для синхронизации перезаписываем список по умолчанию:
if len(znach_SyncSchemeCheckBoxesPosition) < 24:
	Wrtite_to_ExtensibleStorage (schemaGuid_for_SyncSchemeCheckBoxesPosition, ProjectInfoObject, FieldName_for_SyncSchemeCheckBoxesPosition, SchemaName_for_SyncSchemeCheckBoxesPosition, SyncSchemeCheckBoxesPositionList_by_Default) # пишем данные в хранилище 
	# Теперь ExtensibleStorage с указанным guid'ом присутствет. Считываем переменные из него
	#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
	sch_SyncSchemeCheckBoxesPosition = Schema.Lookup(schemaGuid_for_SyncSchemeCheckBoxesPosition)
	#Получаем Entity из элемента:
	ent_SyncSchemeCheckBoxesPosition = ProjectInfoObject.GetEntity(sch_SyncSchemeCheckBoxesPosition)
	#Уже знакомым способом получаем «поля»:
	field_SyncSchemeCheckBoxesPosition = sch_SyncSchemeCheckBoxesPosition.GetField(FieldName_for_SyncSchemeCheckBoxesPosition)
	#Для считывания значений используем метод Entity.Get:
	znach_SyncSchemeCheckBoxesPosition = ent_SyncSchemeCheckBoxesPosition.Get[IList[str]](field_SyncSchemeCheckBoxesPosition) # выдаёт List[str](['a', 'list', 'of', 'strings'])
	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znach_SyncSchemeCheckBoxesPosition]
	znach_SyncSchemeCheckBoxesPosition = []
	[znach_SyncSchemeCheckBoxesPosition.append(i) for i in CS_help]


# Функция проставления и снятия значений флажков в окне синхронизации
# На входе список со значениями флажков из Хранилища, "ручка" заполняем или забираем значения (может быть In или Out), а также все элементы управления окна)
# ('Py', '1', 'Cosf', '1', 'L', '1', 'U', '1', 'Имя щита', '1', 'Наименование нагрузки', '1', 'Наименование помещения', '1', 'Число электроприёмников', '1', 'Синхр.коэфф.спроса', '1', 'Синхр.ящики упр.', '1', 'Что записать номер или имя пространства', '0')
def SyncWinowFill (znach_SyncSchemeCheckBoxesPosition, InOut,
checkBox_Py, checkBox_cosf, checkBox_Length, checkBox_Upit, checkBox_Box_Name, checkBox_Load_Name, checkBox_RoomName, checkBox_ConsumersCount, 
checkBox_SyncKc, checkBox_TSLCable, comboBox_RoomNameorNumber,
RoomNameorNumber, checkBox_LayingMethod
):

	if InOut == 'In': # Если заполняем окно
		if znach_SyncSchemeCheckBoxesPosition[1] == '1':
			checkBox_Py.Checked = True
		else:
			checkBox_Py.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[3] == '1':
			checkBox_cosf.Checked = True
		else:
			checkBox_cosf.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[5] == '1':
			checkBox_Length.Checked = True
		else:
			checkBox_Length.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[7] == '1':
			checkBox_Upit.Checked = True
		else:
			checkBox_Upit.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[9] == '1':
			checkBox_Box_Name.Checked = True
		else:
			checkBox_Box_Name.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[11] == '1':
			checkBox_Load_Name.Checked = True
		else:
			checkBox_Load_Name.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[13] == '1':
			checkBox_RoomName.Checked = True
		else:
			checkBox_RoomName.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[15] == '1':
			checkBox_ConsumersCount.Checked = True
		else:
			checkBox_ConsumersCount.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[17] == '1':
			checkBox_SyncKc.Checked = True
		else:
			checkBox_SyncKc.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[19] == '1':
			checkBox_TSLCable.Checked = True
		else:
			checkBox_TSLCable.Checked = False
		if znach_SyncSchemeCheckBoxesPosition[21] == '0':
			comboBox_RoomNameorNumber.SelectedItem = RoomNameorNumber[0] # 'Номер пространства'
		else:
			comboBox_RoomNameorNumber.SelectedItem = RoomNameorNumber[1] # 'Имя пространства'
		if znach_SyncSchemeCheckBoxesPosition[23] == '1':
			checkBox_LayingMethod.Checked = True
		else:
			checkBox_LayingMethod.Checked = False

	if InOut == 'Out': # Если забираем данные из окна
		znach_SyncSchemeCheckBoxesPosition_Output = [] # Выходной список с данными для Хранилища
		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[0])
		if checkBox_Py.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[2])
		if checkBox_cosf.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[4])
		if checkBox_Length.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[6])
		if checkBox_Upit.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[8])
		if checkBox_Box_Name.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[10])
		if checkBox_Load_Name.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[12])
		if checkBox_RoomName.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[14])
		if checkBox_ConsumersCount.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[16])
		if checkBox_SyncKc.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[18])
		if checkBox_TSLCable.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[20])
		if comboBox_RoomNameorNumber_SelectedItem == RoomNameorNumber[0]: # 'Номер пространства'
			znach_SyncSchemeCheckBoxesPosition_Output.append('0') 
		elif comboBox_RoomNameorNumber_SelectedItem == RoomNameorNumber[1]: # 'Имя пространства'
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')

		znach_SyncSchemeCheckBoxesPosition_Output.append(znach_SyncSchemeCheckBoxesPosition[22])
		if checkBox_LayingMethod.Checked == True:
			znach_SyncSchemeCheckBoxesPosition_Output.append('1')
		else:
			znach_SyncSchemeCheckBoxesPosition_Output.append('0')

		Wrtite_to_ExtensibleStorage (schemaGuid_for_SyncSchemeCheckBoxesPosition, ProjectInfoObject, FieldName_for_SyncSchemeCheckBoxesPosition, SchemaName_for_SyncSchemeCheckBoxesPosition, znach_SyncSchemeCheckBoxesPosition_Output) # пишем данные в хранилище




#_____________________________________________________________________________________________________________________________________________



# Функция накидывания запаса на способы прокладки
# на входе строка вида: 'лоток-12; открыто-14; в трубе-20' и значение запаса в виде дроби: 1.2
# на выходе такая же строка как на входе, но уже с запасом (exit_Laying_Method_AsString) вида: 'лоток-14;  открыто-17;  в трубе-24
def AddZapas_for_Laying_Method (Param_TSL_Param_Laying_Method_AsString, Length_stock_inside):
	#Param_TSL_Param_Laying_Method_AsString = 'лоток-12; открыто-14; в трубе-20' # чтобы тетстить
	#Length_stock_inside = 1.2 # чтобы тетстить
	exit_Laying_Method_AsString = ''
	try:
		# строка разбитая по дефису и ставшая списком:
		splitedbyhyphenlst = Param_TSL_Param_Laying_Method_AsString.split('-') # делает: ['лоток', '12; открыто', '14; в трубе', '20']
		exit_Laying_Method_AsString = splitedbyhyphenlst[0] + '-' # вставляем первый способ прокладки
		for n, i in enumerate(splitedbyhyphenlst):
			if n != 0: # первый элемент выходной строки уже записали
				exit_Laying_Method_AsString = exit_Laying_Method_AsString + str(int(float(i.split(';')[0])*Length_stock_inside)) # i - это '12; открыто'
				if len(i.split(';')) > 1:
					exit_Laying_Method_AsString = exit_Laying_Method_AsString + '; ' + i.split(';')[1] + '-'
	except: # если что-то пойдёт не так, то просто перепишем строку как было
		exit_Laying_Method_AsString = Param_TSL_Param_Laying_Method_AsString
	if Param_TSL_Param_Laying_Method_AsString == '': # а если на входе была пустая строка, то её и оставим.
		exit_Laying_Method_AsString = ''
	return exit_Laying_Method_AsString




# Окошко для вывода предупреждений:
class SyncScheme_AlertForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._OK_button = System.Windows.Forms.Button()
		self._SyncScheme_AlertForm_label1 = System.Windows.Forms.Label()
		self._SyncScheme_AlertForm_textBox1 = System.Windows.Forms.TextBox()
		self.SuspendLayout()
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._OK_button.Location = System.Drawing.Point(161, 253)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(75, 23)
		self._OK_button.TabIndex = 0
		self._OK_button.Text = "OK"
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# SyncScheme_AlertForm_label1
		# 
		self._SyncScheme_AlertForm_label1.Location = System.Drawing.Point(12, 9)
		self._SyncScheme_AlertForm_label1.Name = "SyncScheme_AlertForm_label1"
		self._SyncScheme_AlertForm_label1.Size = System.Drawing.Size(378, 26)
		self._SyncScheme_AlertForm_label1.TabIndex = 1
		self._SyncScheme_AlertForm_label1.Text = "Текст по умолчанию"
		# 
		# SyncScheme_AlertForm_textBox1
		# 
		self._SyncScheme_AlertForm_textBox1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._SyncScheme_AlertForm_textBox1.Location = System.Drawing.Point(12, 38)
		self._SyncScheme_AlertForm_textBox1.Multiline = True
		self._SyncScheme_AlertForm_textBox1.Name = "SyncScheme_AlertForm_textBox1"
		self._SyncScheme_AlertForm_textBox1.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
		self._SyncScheme_AlertForm_textBox1.Size = System.Drawing.Size(378, 196)
		self._SyncScheme_AlertForm_textBox1.TabIndex = 2
		# 
		# SyncScheme_AlertForm
		# 
		self.ClientSize = System.Drawing.Size(402, 288)
		self.Controls.Add(self._SyncScheme_AlertForm_textBox1)
		self.Controls.Add(self._SyncScheme_AlertForm_label1)
		self.Controls.Add(self._OK_button)
		self.MinimumSize = System.Drawing.Size(418, 267)
		self.Name = "SyncScheme_AlertForm"
		self.Text = "Предупреждение"
		self.Load += self.SyncScheme_AlertFormLoad
		self.ResumeLayout(False)
		self.PerformLayout()


		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell



	def SyncScheme_AlertFormLoad(self, sender, e):
		self.ActiveControl = self._OK_button # ставим фокус на кнопку ОК чтобы по Enter её быстро нажимать
		self._SyncScheme_AlertForm_label1.Text = 'Предупреждение:'
		self._SyncScheme_AlertForm_textBox1.Text = AlertString

	def OK_buttonClick(self, sender, e):
		self.Close()
























# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html
transGroup = TransactionGroup(doc, "SyncScheme")
transGroup.Start()




# Фильтруем автоматические выключатели
for element in elems:
	if element.Name in avt_family_names: elems_avtomats.append(element)

# Фильтруем TSL_Кабели
for element in elems:
	if element.Name == TSLCable_family_name: elems_TSLCable.append(element)

# Фильтруем ящики управления (типовые аннотации)
#for element in elems:
#	if element.Name in Control_board_family_names: elems_control_boards.append(element)

# Фильтруем ящики управления (семейства из модели)
#for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalEquipment).WhereElementIsNotElementType().ToElements():
#	if Control_board_family_names_Model.count(i.Symbol.FamilyName) > 0: elems_control_boards_model.append(i) 

'''
# Бывает что в щитках Имя панели (и другие текстовые параметры) не просто не заполнено, а None. Это влечёт за собой кучу ошибок потом. 
# Поэтому всем ЯУ в модели принудительно перепишем значения None на пустую строку ''.
t = Transaction(doc, 'Change None values in params')
t.Start()
for i in elems_control_boards_model:
	if GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_PANEL_NAME).AsString() == None: # То же что и i.LookupParameter('Имя панели').AsString() == None
		GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_PANEL_NAME).Set('')
	if fam_param_names[0] in [p.Definition.Name for p in i.Parameters]: # если такой параметр вообще есть в семействе (и он по экземпляру)...
		if i.LookupParameter(fam_param_names[0]).AsString() == None:
			i.LookupParameter(fam_param_names[0]).Set('')
	elif fam_param_names[0] in [p.Definition.Name for p in i.Symbol.Parameters]: # или по типу
		if i.Symbol.LookupParameter(fam_param_names[0]).AsString() == None:
			i.Symbol.LookupParameter(fam_param_names[0]).Set('')
	if fam_param_names[1] in [p.Definition.Name for p in i.Parameters]: 
		if i.LookupParameter(fam_param_names[1]).AsString() == None:
			i.LookupParameter(fam_param_names[1]).Set('')
	elif fam_param_names[1] in [p.Definition.Name for p in i.Symbol.Parameters]: 
		if i.Symbol.LookupParameter(fam_param_names[1]).AsString() == None:
			i.Symbol.LookupParameter(fam_param_names[1]).Set('')
	if fam_param_names[2] in [p.Definition.Name for p in i.Parameters]: 
		if i.LookupParameter(fam_param_names[2]).AsString() == None:
			i.LookupParameter(fam_param_names[2]).Set('')
	elif fam_param_names[2] in [p.Definition.Name for p in i.Symbol.Parameters]:
		if i.Symbol.LookupParameter(fam_param_names[2]).AsString() == None:
			i.Symbol.LookupParameter(fam_param_names[2]).Set('')
	if fam_param_names[3] in [p.Definition.Name for p in i.Parameters]:
		if i.LookupParameter(fam_param_names[3]).AsString() == None:
			i.LookupParameter(fam_param_names[3]).Set('')
	elif fam_param_names[3] in [p.Definition.Name for p in i.Symbol.Parameters]: 
		if i.Symbol.LookupParameter(fam_param_names[3]).AsString() == None:
			i.Symbol.LookupParameter(fam_param_names[3]).Set('')
t.Commit()
'''







# вытаскиваем все электрические цепи из проекта
networks = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalCircuit).ToElements()

# В зависимости от настроек устанавливаем режим траектории цепей во всём проекте
if Electrical_Circuit_PathMode_method == 1:
	# Для всех цепей принудительно поставим ElectricalCircuitPathMode AllDevices
	t = Transaction(doc, 'Change CircuitPathMode for all Circuits')
	t.Start()
	for i in networks:
		i.CircuitPathMode = Electrical.ElectricalCircuitPathMode.AllDevices
	t.Commit()
elif Electrical_Circuit_PathMode_method == 2:
	# Для всех цепей принудительно поставим ElectricalCircuitPathMode FarthestDevice
	t = Transaction(doc, 'Change CircuitPathMode for all Circuits')
	t.Start()
	for i in networks:
		i.CircuitPathMode = Electrical.ElectricalCircuitPathMode.FarthestDevice
	t.Commit()

#сообщение об ошибке которое должно вывестись в следующем модуле
error_text_in_window = 'Вы не выбрали автоматические выключатели для синхронизации. Программа работает только с определёнными семействами автоматических выключателей и кабелей: ' + ', '.join(avt_family_names) + TSLCable_family_name + '. Пожалуйста, выберите их и запустите программу заново.'
#если выбрано не то что надо, выйти из программы
if elems_avtomats == [] and elems_TSLCable == []: 
	raise Exception(error_text_in_window)
	#MessageBox.Show(error_text_in_window, 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	#sys.exit()

















# Проводим проверки о повторениях в именах групп и ящиков управления на схемах и планах
# формируем сообщение об ошибке если есть повторяющиеся группы
Repeated_names([i.LookupParameter(Param_Circuit_number).AsString() for i in elems_avtomats] + [i.LookupParameter(Param_Circuit_number).AsString() for i in elems_TSLCable], 'группа', 'У выбранных автоматов (и/или кабелей) есть повторяющиеся номера групп. Скорее всего - это ошибка, т.к. у каждого автомата должен быть уникальный номер группы.')
# Проверим нет ли повторяющихся имён групп в самих цепях. Всё аналогично проверке повторения номеров групп. Ищем параметр 'Номер цепи'
Repeated_names([GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_CIRCUIT_NUMBER).AsString() for i in networks], 'группа', 'В модели есть повторяющиеся номера групп. Скорее всего - это ошибка, т.к. у каждого автомата должен быть уникальный номер группы.')
# Проверки ящиков управления (аналогичны проверкам цепей). Только связь идёт по параметру "Имя панели". Проверка повторяющихся имён панелей на схеме
#Repeated_names([k.LookupParameter(Param_PanelName).AsString() for k in elems_control_boards], 'имя панели', 'У выбранных ящиков управления на схеме есть повторяющиеся имена панелей. Скорее всего - это ошибка, т.к. у каждого ЯУ должно быть уникальное имя.')
# Проверка повторяющихся имён панелей на планах:	Ищем параметр 'Имя панели'
#Repeated_names([GetBuiltinParam(k, BuiltInParameter.RBS_ELEC_PANEL_NAME).AsString() for k in elems_control_boards_model], 'имя панели', 'У ящиков управления в модели есть повторяющиеся имена панелей. Скорее всего - это ошибка, т.к. у каждого ЯУ должно быть уникальное имя.')







# Проверим есть ли у выбранных автоматов номера групп, которых нет в электроцепях проекта
# формируем список в котором записаны все имена групп выбранных автоматов. Пример: Names_of_Groups   ['N1-1', 'N1-2', 'N1-3', 'N1-4']
Names_of_Groups_1 = []
AVsCbls_Ids = [] # список с id автоматов и кабелей попавших в выборку
for i in elems_avtomats:
	Names_of_Groups_1.append(i.LookupParameter(Param_Circuit_number).AsString())
	AVsCbls_Ids.append((str(i.Id)))
# добавляем в него имена цепей из TSL_Кабель
for i in elems_TSLCable:
	Names_of_Groups_1.append(i.LookupParameter(Param_Circuit_number).AsString())
	AVsCbls_Ids.append((str(i.Id)))
# то же, но имена групп с планов (цепей)
Names_of_Groups_in_Project_1 = []
for i in networks:
	Names_of_Groups_in_Project_1.append(GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_CIRCUIT_NUMBER).AsString()) # RBS_ELEC_CIRCUIT_NUMBER => Номер цепи. То же что и i.LookupParameter('Номер цепи')

Missing_Groups = [] # список с отсутствующими группами
Missing_Groups_AVsCbls_Ids = [] # список с id автоматов и кабелей для которых нет электроцепей в модели
for n, i in enumerate(Names_of_Groups_1):
	if Names_of_Groups_in_Project_1.count(i) == 0:
		if i == '':
			Missing_Groups.append('<имя группы не заполнено>')
		else:
			Missing_Groups.append(i)
		Missing_Groups_AVsCbls_Ids.append(AVsCbls_Ids[n])

if len(Missing_Groups) == len(Names_of_Groups_1):
	Missing_Groups_handle = 1 # Вспомогательная переменная. Если у всех выбранных автоматов номера групп, которых нет в электроцепях проекта, то "1". Иначе "0".
else:
	Missing_Groups_handle = 0

# если спсиок отсутствующих групп не пустой, то вывести окно с предупреждением
if Missing_Groups != []:
	error_text_in_window = ('У одного или нескольких выбранных автоматов (и/или кабелей) есть имя группы, которой нет среди электрических цепей на планах. Никакие данные не будут записаны в автоматы с такими именами групп. Остальные автоматы будут синхронизированны корректно. Отсутствующие имена групп: ' + '; '.join(Missing_Groups) + '. Id элементов: ' + '; '.join(Missing_Groups_AVsCbls_Ids))
	MessageBox.Show(error_text_in_window, 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
	

'''
# Аналогичная проверка для имён ящиков управления. Выдаём предупреждение если среди выбранных ящиков есть имя которого нет в модели.
# [k.LookupParameter(Param_PanelName).AsString() for k in elems_control_boards] # имена панели ЯУ из типовых аннотаций (выбранных пользователем)
# [k.LookupParameter('Имя панели').AsString() for k in elems_control_boards_model] # имена панели ЯУ из модели
Missing_Panel_Names = [] # список с отсутствующими именами
for i in [k.LookupParameter(Param_PanelName).AsString() for k in elems_control_boards]:
	if [GetBuiltinParam(k, BuiltInParameter.RBS_ELEC_PANEL_NAME).AsString() for k in elems_control_boards_model].count(i) == 0: # RBS_ELEC_PANEL_NAME => Имя панели. То же что и k.LookupParameter('Имя панели').AsString()
		Missing_Panel_Names.append(i)
# если спсиок отсутствующих имён панелей не пустой, то вывести окно с предупреждением
if Missing_Panel_Names != []:
	error_text_in_window = ('У одного или нескольких выбранных ящиков управления есть имя панели, которого нет среди имён панелей на планах. Никакие данные не будут записаны в ЯУ с такими именами панелей. Остальные ЯУ будут синхронизированны корректно. Отсутствующие имена панелей: ' + '; '.join(Missing_Panel_Names) + '.')
	MessageBox.Show(error_text_in_window, 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
if len(Missing_Panel_Names) == len([k.LookupParameter(Param_PanelName).AsString() for k in elems_control_boards]):
	Missing_Panels_handle = 1 # Вспомогательная переменная. Если у всех выбранных ЯУ имена панелей, которых нет в семействах в проекте, то "1". Иначе "0".
else:
	Missing_Panels_handle = 0
'''

# Если выбраны только автоматы для которых нет групп на плане - выдать ошибку, выкинуть из программы. (То же касается имён панелей для ЯУ)
if Missing_Groups_handle == 1:
	#MessageBox.Show('Ни одной из выбранных групп нет на планах. Синхронизация не будет выполнена.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	#sys.exit()
	# Предложим пользователю выбор
	td = TaskDialog('Синхронизация')
	td.MainContent = 'Ни одной из выбранных групп нет на планах. Синхронизация с планами не будет выполнена. Продолжить с синхронизацией коэффициентов спроса?'
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, 'Продолжить')
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, 'Отмена')
	GetUserResult = td.Show()
	if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
		pass
	elif GetUserResult == TaskDialogResult.CommandLink2:
		raise Exception('Ни одной из выбранных групп нет на планах. Синхронизация не будет выполнена.')
	


'''функция для записи нужных данных в чертёж
обращение:
Transaction_sukhov (doc, 'Py', 1.96, текущий элемент)
где:
doc - текущий документ (объявлен в начале программы)
changing_parametr - изменяемый параметр в формате String. То есть тот параметр который нужно искать в выбранном элементе
element_to_write_down - элемент для записи. То есть данные которые нужно записать. Например число 20.
current_element_in_list - текущий элемент в который мы производим запись. Не номер, а физический элемент! Например один автомат.
'''
def Transaction_sukhov_1 (doc, changing_parametr, element_to_write_down, current_element_in_list):
#	t = Transaction(doc, 'Change changing_parametr')
#	t.Start()
	current_element_in_list.LookupParameter(changing_parametr).Set(element_to_write_down)
	#TransactionManager.Instance.TransactionTaskDone()
#	t.Commit()


# Переменная для заполнения выпадающего списка: что берём для синхронизации: номер или имя пространства.
RoomNameorNumber = ['Номер пространства', 'Имя пространства']

global Button_Cancel_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_pushed = 1


#основное рабочее окно программы: Кстаи оно создано в программе SharpDevelop
class Form2(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._OK_button = System.Windows.Forms.Button()
		self._Cancel_button = System.Windows.Forms.Button()
		self._checkBox_Py = System.Windows.Forms.CheckBox()
		self._checkBox_cosf = System.Windows.Forms.CheckBox()
		self._groupBox1 = System.Windows.Forms.GroupBox()
		self._checkBox_Length = System.Windows.Forms.CheckBox()
		self._checkBox_Upit = System.Windows.Forms.CheckBox()
		self._trackBar_Length_stock = System.Windows.Forms.TrackBar()
		self._label_Length_stock = System.Windows.Forms.Label()
		self._textBox_Length_stock = System.Windows.Forms.TextBox()
		self._checkBox_Selectall = System.Windows.Forms.CheckBox()
		self._checkBox_Box_Name = System.Windows.Forms.CheckBox()
		self._checkBox_Load_Name = System.Windows.Forms.CheckBox()
		self._checkBox_TSLCable = System.Windows.Forms.CheckBox()
		self._groupBox2 = System.Windows.Forms.GroupBox()
		self._checkBox_RoomName = System.Windows.Forms.CheckBox()
		self._comboBox_RoomNameorNumber = System.Windows.Forms.ComboBox()
		self._label_RoomNameorNumber = System.Windows.Forms.Label()
		self._checkBox_ConsumersCount = System.Windows.Forms.CheckBox()
		self._checkBox_SyncKc = System.Windows.Forms.CheckBox()
		self._checkBox_LayingMethod = System.Windows.Forms.CheckBox()
		self._groupBox1.SuspendLayout()
		self._trackBar_Length_stock.BeginInit()
		self._groupBox2.SuspendLayout()
		self.SuspendLayout()
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_button.Location = System.Drawing.Point(25, 523)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(75, 23)
		self._OK_button.TabIndex = 0
		self._OK_button.Text = "OK"
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(438, 523)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(75, 23)
		self._Cancel_button.TabIndex = 1
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# checkBox_Py
		# 
		self._checkBox_Py.Checked = True
		self._checkBox_Py.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Py.Location = System.Drawing.Point(31, 42)
		self._checkBox_Py.Name = "checkBox_Py"
		self._checkBox_Py.Size = System.Drawing.Size(270, 25)
		self._checkBox_Py.TabIndex = 3
		self._checkBox_Py.Text = "Ру (установленная мощность)"
		self._checkBox_Py.UseVisualStyleBackColor = True
		self._checkBox_Py.CheckedChanged += self.CheckBox_PyCheckedChanged
		# 
		# checkBox_cosf
		# 
		self._checkBox_cosf.Checked = True
		self._checkBox_cosf.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_cosf.Location = System.Drawing.Point(31, 73)
		self._checkBox_cosf.Name = "checkBox_cosf"
		self._checkBox_cosf.Size = System.Drawing.Size(270, 24)
		self._checkBox_cosf.TabIndex = 4
		self._checkBox_cosf.Text = "Cosf (коэффициент мощности)"
		self._checkBox_cosf.UseVisualStyleBackColor = True
		self._checkBox_cosf.CheckedChanged += self.CheckBox_cosfCheckedChanged
		# 
		# groupBox1
		# 
		self._groupBox1.Controls.Add(self._checkBox_LayingMethod)
		self._groupBox1.Controls.Add(self._checkBox_ConsumersCount)
		self._groupBox1.Controls.Add(self._label_RoomNameorNumber)
		self._groupBox1.Controls.Add(self._comboBox_RoomNameorNumber)
		self._groupBox1.Controls.Add(self._checkBox_RoomName)
		self._groupBox1.Controls.Add(self._checkBox_Load_Name)
		self._groupBox1.Controls.Add(self._checkBox_Box_Name)
		self._groupBox1.Controls.Add(self._checkBox_Py)
		self._groupBox1.Controls.Add(self._checkBox_cosf)
		self._groupBox1.Controls.Add(self._textBox_Length_stock)
		self._groupBox1.Controls.Add(self._label_Length_stock)
		self._groupBox1.Controls.Add(self._trackBar_Length_stock)
		self._groupBox1.Controls.Add(self._checkBox_Upit)
		self._groupBox1.Controls.Add(self._checkBox_Length)
		self._groupBox1.Location = System.Drawing.Point(25, 42)
		self._groupBox1.Name = "groupBox1"
		self._groupBox1.Size = System.Drawing.Size(488, 320)
		self._groupBox1.TabIndex = 5
		self._groupBox1.TabStop = False
		self._groupBox1.Text = "Укажите какие данные необходимо взять с планов и записать в автоматы"
		# 
		# checkBox_Length
		# 
		self._checkBox_Length.Checked = True
		self._checkBox_Length.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Length.Location = System.Drawing.Point(31, 102)
		self._checkBox_Length.Name = "checkBox_Length"
		self._checkBox_Length.Size = System.Drawing.Size(245, 24)
		self._checkBox_Length.TabIndex = 6
		self._checkBox_Length.Text = "L (длина кабеля в группе)"
		self._checkBox_Length.UseVisualStyleBackColor = True
		self._checkBox_Length.CheckedChanged += self.CheckBox_LengthCheckedChanged
		# 
		# checkBox_Upit
		# 
		self._checkBox_Upit.Checked = True
		self._checkBox_Upit.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Upit.Location = System.Drawing.Point(31, 132)
		self._checkBox_Upit.Name = "checkBox_Upit"
		self._checkBox_Upit.Size = System.Drawing.Size(245, 24)
		self._checkBox_Upit.TabIndex = 7
		self._checkBox_Upit.Text = "U (напряжение)"
		self._checkBox_Upit.UseVisualStyleBackColor = True
		self._checkBox_Upit.CheckedChanged += self.CheckBox_UpitCheckedChanged
		# 
		# trackBar_Length_stock
		# 
		self._trackBar_Length_stock.Location = System.Drawing.Point(282, 103)
		self._trackBar_Length_stock.Name = "trackBar_Length_stock"
		self._trackBar_Length_stock.Size = System.Drawing.Size(146, 56)
		self._trackBar_Length_stock.TabIndex = 8
		self._trackBar_Length_stock.Value = 1
		self._trackBar_Length_stock.Scroll += self.TrackBar_Length_stockScroll
		# 
		# label_Length_stock
		# 
		self._label_Length_stock.Location = System.Drawing.Point(310, 90)
		self._label_Length_stock.Name = "label_Length_stock"
		self._label_Length_stock.Size = System.Drawing.Size(100, 16)
		self._label_Length_stock.TabIndex = 9
		self._label_Length_stock.Text = "Запас кабеля в %"
		# 
		# textBox_Length_stock
		# 
		self._textBox_Length_stock.Location = System.Drawing.Point(432, 106)
		self._textBox_Length_stock.Name = "textBox_Length_stock"
		self._textBox_Length_stock.Size = System.Drawing.Size(27, 22)
		self._textBox_Length_stock.TabIndex = 10
		self._textBox_Length_stock.Text = "10"
		self._textBox_Length_stock.TextChanged += self.TextBox_Length_stockTextChanged
		# 
		# checkBox_Selectall
		# 
		self._checkBox_Selectall.Checked = True
		self._checkBox_Selectall.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Selectall.Location = System.Drawing.Point(36, 11)
		self._checkBox_Selectall.Name = "checkBox_Selectall"
		self._checkBox_Selectall.Size = System.Drawing.Size(134, 24)
		self._checkBox_Selectall.TabIndex = 11
		self._checkBox_Selectall.Text = "Выбрать всё"
		self._checkBox_Selectall.UseVisualStyleBackColor = True
		self._checkBox_Selectall.CheckedChanged += self.CheckBox_SelectallCheckedChanged
		# 
		# checkBox_Box_Name
		# 
		self._checkBox_Box_Name.Checked = True
		self._checkBox_Box_Name.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Box_Name.Location = System.Drawing.Point(31, 162)
		self._checkBox_Box_Name.Name = "checkBox_Box_Name"
		self._checkBox_Box_Name.Size = System.Drawing.Size(245, 24)
		self._checkBox_Box_Name.TabIndex = 12
		self._checkBox_Box_Name.Text = "Имя щита"
		self._checkBox_Box_Name.UseVisualStyleBackColor = True
		self._checkBox_Box_Name.CheckedChanged += self.CheckBox_Box_NameCheckedChanged
		# 
		# checkBox_Load_Name
		# 
		self._checkBox_Load_Name.Checked = True
		self._checkBox_Load_Name.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_Load_Name.Location = System.Drawing.Point(31, 192)
		self._checkBox_Load_Name.Name = "checkBox_Load_Name"
		self._checkBox_Load_Name.Size = System.Drawing.Size(245, 24)
		self._checkBox_Load_Name.TabIndex = 13
		self._checkBox_Load_Name.Text = "Наименование нагрузки"
		self._checkBox_Load_Name.UseVisualStyleBackColor = True
		self._checkBox_Load_Name.CheckedChanged += self.CheckBox_Load_NameCheckedChanged
		# 
		# checkBox_TSLCable
		# 
		self._checkBox_TSLCable.Checked = True
		self._checkBox_TSLCable.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_TSLCable.Location = System.Drawing.Point(42, 49)
		self._checkBox_TSLCable.Name = "checkBox_TSLCable"
		self._checkBox_TSLCable.Size = System.Drawing.Size(386, 24)
		self._checkBox_TSLCable.TabIndex = 14
		self._checkBox_TSLCable.Text = "Синхронизировать TSL_Кабель"
		self._checkBox_TSLCable.UseVisualStyleBackColor = True
		# 
		# groupBox2
		# 
		self._groupBox2.Controls.Add(self._checkBox_SyncKc)
		self._groupBox2.Controls.Add(self._checkBox_TSLCable)
		self._groupBox2.Location = System.Drawing.Point(14, 403)
		self._groupBox2.Name = "groupBox2"
		self._groupBox2.Size = System.Drawing.Size(499, 92)
		self._groupBox2.TabIndex = 15
		self._groupBox2.TabStop = False
		self._groupBox2.Text = "Дополнительные параметры"
		# 
		# checkBox_RoomName
		# 
		self._checkBox_RoomName.Checked = True
		self._checkBox_RoomName.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_RoomName.Location = System.Drawing.Point(31, 222)
		self._checkBox_RoomName.Name = "checkBox_RoomName"
		self._checkBox_RoomName.Size = System.Drawing.Size(245, 24)
		self._checkBox_RoomName.TabIndex = 14
		self._checkBox_RoomName.Text = "Наименование помещения"
		self._checkBox_RoomName.UseVisualStyleBackColor = True
		# 
		# comboBox_RoomNameorNumber
		# 
		self._comboBox_RoomNameorNumber.FormattingEnabled = True
		self._comboBox_RoomNameorNumber.Location = System.Drawing.Point(282, 228)
		self._comboBox_RoomNameorNumber.Name = "comboBox_RoomNameorNumber"
		self._comboBox_RoomNameorNumber.Size = System.Drawing.Size(180, 24)
		self._comboBox_RoomNameorNumber.TabIndex = 15
		# 
		# label_RoomNameorNumber
		# 
		self._label_RoomNameorNumber.Location = System.Drawing.Point(282, 209)
		self._label_RoomNameorNumber.Name = "label_RoomNameorNumber"
		self._label_RoomNameorNumber.Size = System.Drawing.Size(180, 16)
		self._label_RoomNameorNumber.TabIndex = 16
		self._label_RoomNameorNumber.Text = "Что записать в щиток?"
		# 
		# checkBox_ConsumersCount
		# 
		self._checkBox_ConsumersCount.Checked = True
		self._checkBox_ConsumersCount.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_ConsumersCount.Location = System.Drawing.Point(31, 252)
		self._checkBox_ConsumersCount.Name = "checkBox_ConsumersCount"
		self._checkBox_ConsumersCount.Size = System.Drawing.Size(245, 24)
		self._checkBox_ConsumersCount.TabIndex = 17
		self._checkBox_ConsumersCount.Text = "Число электроприёмников"
		self._checkBox_ConsumersCount.UseVisualStyleBackColor = True
		# 
		# checkBox_SyncKc
		# 
		self._checkBox_SyncKc.Checked = True
		self._checkBox_SyncKc.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_SyncKc.Location = System.Drawing.Point(42, 21)
		self._checkBox_SyncKc.Name = "checkBox_SyncKc"
		self._checkBox_SyncKc.Size = System.Drawing.Size(386, 24)
		self._checkBox_SyncKc.TabIndex = 15
		self._checkBox_SyncKc.Text = "Синхронизировать коэффициенты спроса автоматов"
		self._checkBox_SyncKc.UseVisualStyleBackColor = True
		# 
		# checkBox_LayingMethod
		# 
		self._checkBox_LayingMethod.Checked = True
		self._checkBox_LayingMethod.CheckState = System.Windows.Forms.CheckState.Checked
		self._checkBox_LayingMethod.Location = System.Drawing.Point(31, 282)
		self._checkBox_LayingMethod.Name = "checkBox_LayingMethod"
		self._checkBox_LayingMethod.Size = System.Drawing.Size(245, 24)
		self._checkBox_LayingMethod.TabIndex = 18
		self._checkBox_LayingMethod.Text = "Способ прокладки проводника"
		self._checkBox_LayingMethod.UseVisualStyleBackColor = True
		# 
		# Form2
		# 
		self.ClientSize = System.Drawing.Size(538, 574)
		self.Controls.Add(self._groupBox2)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._checkBox_Selectall)
		self.Controls.Add(self._OK_button)
		self.Controls.Add(self._groupBox1)
		self.MinimumSize = System.Drawing.Size(554, 612)
		self.Name = "Form2"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
		self.Text = "Синхронизация схем с планами"
		self.Load += self.Form2Load
		self._groupBox1.ResumeLayout(False)
		self._groupBox1.PerformLayout()
		self._trackBar_Length_stock.EndInit()
		self._groupBox2.ResumeLayout(False)
		self.ResumeLayout(False)

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell



	def Form2Load(self, sender, e):
		if Missing_Groups_handle != 1:
			# Заполняем окно
			self._comboBox_RoomNameorNumber.DataSource = RoomNameorNumber # заполняем комбо-бокс
			SyncWinowFill(znach_SyncSchemeCheckBoxesPosition, 'In', self._checkBox_Py, self._checkBox_cosf, self._checkBox_Length, self._checkBox_Upit, self._checkBox_Box_Name, self._checkBox_Load_Name, self._checkBox_RoomName, self._checkBox_ConsumersCount, self._checkBox_SyncKc, self._checkBox_TSLCable, self._comboBox_RoomNameorNumber, RoomNameorNumber, self._checkBox_LayingMethod)
		else:
			self._checkBox_Py.Checked = False
			self._checkBox_Py.Enabled = False
			self._checkBox_cosf.Checked = False
			self._checkBox_cosf.Enabled = False
			self._checkBox_Length.Checked = False
			self._checkBox_Length.Enabled = False
			self._checkBox_Upit.Checked = False
			self._checkBox_Upit.Enabled = False
			self._checkBox_Box_Name.Checked = False
			self._checkBox_Box_Name.Enabled = False
			self._checkBox_Load_Name.Checked = False
			self._checkBox_Load_Name.Enabled = False
			self._checkBox_Selectall.Checked = False
			self._checkBox_Selectall.Enabled = False
			self._checkBox_RoomName.Checked = False
			self._checkBox_RoomName.Enabled = False
			self._comboBox_RoomNameorNumber.Enabled = False
			self._checkBox_ConsumersCount.Enabled = False
			self._checkBox_SyncKc.Checked = True
			self._checkBox_LayingMethod.Checked = False
			self._checkBox_LayingMethod.Enabled = False
			self._checkBox_TSLCable.Checked = False
			self._checkBox_TSLCable.Enabled = False

			

		# Было для ящиков управления	
		#if Missing_Panels_handle != 1:
			#self._checkBox_Control_board.Checked = True
			#self._checkBox_Control_board.Enabled = True
		#else:
			#self._checkBox_Control_board.Checked = False
			#self._checkBox_Control_board.Enabled = False
		self._trackBar_Length_stock.Value = int(int(Cable_stock_for_circuitry)/10) # устанавливаем запас кабеля по умолчанию
		self._textBox_Length_stock.Text = Cable_stock_for_circuitry # устанавливаем запас кабеля по умолчанию
		# Делаем всплывающие подсказки
		ToolTip().SetToolTip(self._checkBox_SyncKc, 'Если у конкретного аппарата на схеме значение в параметре "' + Param_Electric_receiver_Name + '"\nсовпадёт со значением параметра "' + Param_Accessory + '" какой-либо\nтаблички результатов расчётов (' + ', '.join(using_calculated_tables) +'),\nто из семейства этой таблички значение коэффициента спроса попадёт в соответствующий параметр автомата.')
		try:	
			ToolTip().SetToolTip(self._checkBox_Py, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_TRUE_LOAD).Definition.Name + '" из электроцепей будет записано в параметр "' + Param_Py + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_cosf, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_POWER_FACTOR).Definition.Name + '" из электроцепей будет записано в параметр "' + Param_Cosf + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_Length, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).Definition.Name + '" или "' + Param_TSL_WireLength + '" из электроцепей\nбудет обработано алгоритмом Программы и записано в параметр "' + Param_Cable_length + '" автоматов.\nЗначения параметров: "' + Param_TSL_FarestWireLength + '", "' + Param_TSL_ReducedWireLength + '" из электроцепей\nбудут записаны в параметры: "' + Param_FarestWireLength + '", "' + Param_ReducedWireLength + '" автоматов.')
			ToolTip().SetToolTip(self._checkBox_Upit, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_VOLTAGE).Definition.Name + '" из электроцепей будет записано в параметр "' + Param_3phase_CB + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_Box_Name, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_CIRCUIT_PANEL_PARAM).Definition.Name + '" из электроцепей будет записано в параметр "' + Param_Accessory + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_Load_Name, 'Значение параметра "' + GetBuiltinParam(networks[0], BuiltInParameter.RBS_ELEC_CIRCUIT_NAME).Definition.Name + '" из электроцепей будет записано в параметр "' + Param_Electric_receiver_Name + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_RoomName, 'Имена или номера Пространств в которых располагаются электроприёмники в модели\nбудут записаны в параметр "' + Param_Room_Name + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_ConsumersCount, 'Число электроприёмников, подключённых к данной цепи будет записано\nв параметр "' + Param_Consumers_count + '" каждого выбранного автомата')
			ToolTip().SetToolTip(self._checkBox_LayingMethod, 'Значение параметра "' + Param_TSL_Param_Laying_Method + '" из электроцепей' + '\nбудет записано в параметр "' + Param_Laying_Method + '" автоматов')
			ToolTip().SetToolTip(self._checkBox_TSLCable, 'Синхронизирует параметры семейства "' + TSLCable_family_name + '"')
		except:
			pass

		

	def CheckBox_PyCheckedChanged(self, sender, e):
		pass

	def CheckBox_cosfCheckedChanged(self, sender, e):
		pass

	def CheckBox_LengthCheckedChanged(self, sender, e):
		pass

	def CheckBox_UpitCheckedChanged(self, sender, e):
		pass

	def CheckBox_Box_NameCheckedChanged(self, sender, e):
		pass

	def CheckBox_Load_NameCheckedChanged(self, sender, e):
		pass

	def TrackBar_Length_stockScroll(self, sender, e):
		self._textBox_Length_stock.Text = str(self._trackBar_Length_stock.Value * 10) # пишем текст запаса кабеля при перемещении скрол-бара
		'''Length_stock = ((float(self._textBox_Length_stock.Text) / 100) + 1)  - вывод в тестовое поле
		self._textBox_ARA.Text = str(Length_stock)'''
		#self._checkBox_cosf.Checked = self._checkBox_Py.Checked

	def TextBox_Length_stockTextChanged(self, sender, e):
		self._trackBar_Length_stock.Value = int(int(self._textBox_Length_stock.Text) / 10) # перемещаем скролл-бар при изменении текста запаса кабеля

	# проставляем или убираем все флажки по флажку 'Выбрать всё'
	def CheckBox_SelectallCheckedChanged(self, sender, e):
		if self._checkBox_Selectall.Checked == True:
			self._checkBox_Py.Checked  = True
			self._checkBox_cosf.Checked = True
			self._checkBox_Length.Checked = True
			self._checkBox_Upit.Checked = True
			self._checkBox_Box_Name.Checked = True
			self._checkBox_Load_Name.Checked = True
			#if Missing_Panels_handle != 1: # Если выбраны типовые аннотации "ящик управления"
				#self._checkBox_Control_board.Checked = True
			self._checkBox_RoomName.Checked = True
			self._checkBox_ConsumersCount.Checked = True
			self._checkBox_SyncKc.Checked = True
			self._checkBox_LayingMethod.Checked = True
			self._checkBox_TSLCable.Checked = True
		else:
			self._checkBox_Py.Checked  = False
			self._checkBox_cosf.Checked = False
			self._checkBox_Length.Checked = False
			self._checkBox_Upit.Checked = False
			self._checkBox_Box_Name.Checked = False
			self._checkBox_Load_Name.Checked = False
			#self._checkBox_Control_board.Checked = False
			self._checkBox_RoomName.Checked = False
			self._checkBox_ConsumersCount.Checked = False
			self._checkBox_SyncKc.Checked = False
			self._checkBox_LayingMethod.Checked = False
			self._checkBox_TSLCable.Checked = False


	def OK_buttonClick(self, sender, e):
		# Выставляем "кнопка отмена не нажата"
		global Button_Cancel_pushed
		Button_Cancel_pushed = 0

		# Забираем значения по синхронизации наименования помещения для обработки в коде после закрытия окна
		global checkBox_RoomName_Checked # Выставлен ли флажок? True если выставлен, False если нет
		checkBox_RoomName_Checked = self._checkBox_RoomName.Checked 
		global comboBox_RoomNameorNumber_SelectedItem
		comboBox_RoomNameorNumber_SelectedItem = self._comboBox_RoomNameorNumber.SelectedItem # Значение либо: 'Номер пространства', либо 'Имя пространства'
		global checkBox_ConsumersCount_Checked
		checkBox_ConsumersCount_Checked = self._checkBox_ConsumersCount.Checked
		global checkBox_SyncKc_Checked
		checkBox_SyncKc_Checked = self._checkBox_SyncKc.Checked
		global checkBox_LayingMethod
		checkBox_LayingMethod = self._checkBox_LayingMethod.Checked
		global checkBox_TSLCable
		checkBox_TSLCable = self._checkBox_TSLCable.Checked

		t = Transaction(doc, 'Change changing_parametr')
		t.Start()
		# С остальными флажками пока работаем прямо в теле кода окна
		#   self._checkBox_cosf.Checked = self._checkBox_Py.Checked
		# если выставлен флажок Ру, то переписать Ру с планов в автоматы:
		Py_sync = self._checkBox_Py.Checked
		if Py_sync == True:
			for i in elems_avtomats:
				a = 0
				while a < len(networks):
					if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name:
						# networks[a].LookupParameter('Активная нагрузка').AsDouble() это то же самое что и GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_TRUE_LOAD).AsDouble()  
						try:
							Transaction_sukhov_1 (doc, Param_Py, round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_TRUE_LOAD).AsDouble(), DisplayUnitType.DUT_KILOWATTS), 2), i) # Пеперисываем установленную мощность. выдаст результат в киловаттах (например 1.5) в любом случае, какие бы единицы проекта не были выставлены пользователем
						except:
							Transaction_sukhov_1 (doc, Param_Py, round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_TRUE_LOAD).AsDouble(), UnitTypeId.Kilowatts), 2), i)
					a = a+1
		# если выставлен флажок cosf, то переписать cosf с планов в автоматы: 
		cosf_sync = self._checkBox_cosf.Checked
		if cosf_sync == True:
			for i in elems_avtomats:
				a = 0
				while a < len(networks):
					if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name:
						Transaction_sukhov_1 (doc, Param_Cosf, round(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_POWER_FACTOR).AsDouble(), 2), i) # Переписываем коэффициент мощности
					a = a+1
		# если выставлен флажок L, то переписать Длину с планов в автоматы:
		# Забираем значения по синхронизации длины для обработки в коде после закрытия окна
		global Length_sync
		Length_sync = self._checkBox_Length.Checked
		#снимаем значение запаса кабеля, которое выбрал пользователь, переврдим его из процентов в дробь вида: 1,1 (10%), или 1,3 (30%)  
		global Length_stock
		Length_stock = ((float(self._textBox_Length_stock.Text) / 100) + 1)


		# если выставлен флажок Upit, то переписать Upit с планов в автоматы:  RBS_ELEC_VOLTAGE => Напряжение
		Upit_sync = self._checkBox_Upit.Checked
		if Upit_sync == True:
			for i in elems_avtomats:
				a = 0
				while a < len(networks):
					# Если совпадает имя цепи и напряжение 230 Вольт - чтобы не делать строгой привязки к цифре поставим диапазон от 200 до 260 В.
					try: # для Ревита 2019-2021
						if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name and 200 < UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_VOLTAGE).AsDouble(), DisplayUnitType.DUT_VOLTS) < 260:
							Transaction_sukhov_1 (doc, Param_3phase_CB, 0, i)
						# чтобы не делать строгой привязки к цифре поставим диапазон от 350 до 420 В для трёхфазного напряжения
						elif i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name and 350 < UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_VOLTAGE).AsDouble(), DisplayUnitType.DUT_VOLTS) < 420:
							Transaction_sukhov_1 (doc, Param_3phase_CB, 1, i)
						a = a + 1
					except: # Для Ревита 2022
						if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name and 200 < UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_VOLTAGE).AsDouble(), UnitTypeId.Volts) < 260:
							Transaction_sukhov_1 (doc, Param_3phase_CB, 0, i)
						# чтобы не делать строгой привязки к цифре поставим диапазон от 350 до 420 В для трёхфазного напряжения
						elif i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name and 350 < UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_VOLTAGE).AsDouble(), UnitTypeId.Volts) < 420:
							Transaction_sukhov_1 (doc, Param_3phase_CB, 1, i)
						a = a + 1
		# если выставлен флажок checkBox_Box_Name, то переписать Param_Accessory с планов в автоматы:
		if self._checkBox_Box_Name.Checked == True:
			for i in elems_avtomats:
				a = 0
				while a < len(networks):
					if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name:
						Transaction_sukhov_1 (doc, Param_Accessory, GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_CIRCUIT_PANEL_PARAM).AsString(), i) # RBS_ELEC_CIRCUIT_PANEL_PARAM => Панель
					a = a+1
		# если выставлен флажок _checkBox_Load_Name, то переписать 'Имя нагрузки' с планов в автоматы:
		if self._checkBox_Load_Name.Checked == True:
			for i in elems_avtomats:
				a = 0
				while a < len(networks):
					if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name:
						Transaction_sukhov_1 (doc, Param_Electric_receiver_Name, GetBuiltinParam(networks[a], BuiltInParameter.RBS_ELEC_CIRCUIT_NAME).AsString(), i) # RBS_ELEC_CIRCUIT_NAME => Имя нагрузки
					a = a+1
		t.Commit()
		# если выставлен флажок _checkBox_Control_board, то переписать нужные нам параметры с планов в типовые аннотации ЯУ:
		'''
		if self._checkBox_Control_board.Checked == True:
			t = Transaction(doc, 'control_boards sync')
			t.Start()
			for i in elems_control_boards:
				a = 0
				while a < len(elems_control_boards_model):
					if i.LookupParameter(Param_PanelName).AsString() == elems_control_boards_model[a].Name:
						if fam_param_names[0] in [p.Definition.Name for p in elems_control_boards_model[a].Parameters]: # если такой параметр вообще есть в семействе (и он по экземпляру)...
							i.LookupParameter(fam_param_names[0]).Set(elems_control_boards_model[a].LookupParameter(fam_param_names[0]).AsString())
						elif fam_param_names[0] in [p.Definition.Name for p in elems_control_boards_model[a].Symbol.Parameters]: # или по типу
							i.LookupParameter(fam_param_names[0]).Set(elems_control_boards_model[a].Symbol.LookupParameter(fam_param_names[0]).AsString())	
						if fam_param_names[1] in [p.Definition.Name for p in elems_control_boards_model[a].Parameters]:
							i.LookupParameter(fam_param_names[1]).Set(elems_control_boards_model[a].LookupParameter(fam_param_names[1]).AsString())
						elif fam_param_names[1] in [p.Definition.Name for p in elems_control_boards_model[a].Symbol.Parameters]: 
							i.LookupParameter(fam_param_names[1]).Set(elems_control_boards_model[a].Symbol.LookupParameter(fam_param_names[1]).AsString())
						if fam_param_names[2] in [p.Definition.Name for p in elems_control_boards_model[a].Parameters]: 
							i.LookupParameter(fam_param_names[2]).Set(elems_control_boards_model[a].LookupParameter(fam_param_names[2]).AsString())
						elif fam_param_names[2] in [p.Definition.Name for p in elems_control_boards_model[a].Symbol.Parameters]: 
							i.LookupParameter(fam_param_names[2]).Set(elems_control_boards_model[a].Symbol.LookupParameter(fam_param_names[2]).AsString())
						if fam_param_names[3] in [p.Definition.Name for p in elems_control_boards_model[a].Parameters]: 
							i.LookupParameter(fam_param_names[3]).Set(elems_control_boards_model[a].LookupParameter(fam_param_names[3]).AsString())
						elif fam_param_names[3] in [p.Definition.Name for p in elems_control_boards_model[a].Symbol.Parameters]: 
							i.LookupParameter(fam_param_names[3]).Set(elems_control_boards_model[a].Symbol.LookupParameter(fam_param_names[3]).AsString())
						if Param_Circuit_breaker_nominal in [p.Definition.Name for p in elems_control_boards_model[a].Parameters]:
							try:
								i.LookupParameter(Param_Circuit_breaker_nominal).Set(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(elems_control_boards_model[a], BuiltInParameter.RBS_ELEC_PANEL_MCB_RATING_PARAM).AsDouble(), DisplayUnitType.DUT_AMPERES)) # RBS_ELEC_PANEL_MCB_RATING_PARAM => Номинал MCB. Это переписываем параметр 'Номинал MCB'. То же самое что elems_control_boards_model[a].Symbol.LookupParameter('Номинал MCB').AsDouble()
							except:
								i.LookupParameter(Param_Circuit_breaker_nominal).Set(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(elems_control_boards_model[a], BuiltInParameter.RBS_ELEC_PANEL_MCB_RATING_PARAM).AsDouble(), UnitTypeId.Amperes))
						elif Param_Circuit_breaker_nominal in [p.Definition.Name for p in elems_control_boards_model[a].Symbol.Parameters]:
							try:
								i.LookupParameter(Param_Circuit_breaker_nominal).Set(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(elems_control_boards_model[a].Symbol, BuiltInParameter.RBS_ELEC_PANEL_MCB_RATING_PARAM).AsDouble(), DisplayUnitType.DUT_AMPERES))
							except:
								i.LookupParameter(Param_Circuit_breaker_nominal).Set(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(elems_control_boards_model[a].Symbol, BuiltInParameter.RBS_ELEC_PANEL_MCB_RATING_PARAM).AsDouble(), UnitTypeId.Amperes))
					a = a + 1
			t.Commit()
		'''

		if Missing_Groups_handle != 1: # Чтобы не записать в Хранилище невыставленные флажки если не было групп в проекте
			SyncWinowFill(znach_SyncSchemeCheckBoxesPosition, 'Out', self._checkBox_Py, self._checkBox_cosf, self._checkBox_Length, self._checkBox_Upit, self._checkBox_Box_Name, self._checkBox_Load_Name, self._checkBox_RoomName, self._checkBox_ConsumersCount, self._checkBox_SyncKc, self._checkBox_TSLCable, self._comboBox_RoomNameorNumber, RoomNameorNumber, self._checkBox_LayingMethod)

		self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()



Form2().ShowDialog()




# Вспомогательная функция. По электроцепи выдаёт два списка: в первом элементы НЕ Электрооборудование, во втором ТОЛЬКО Электрооборудование
# Пример обращения ElEquipFind(cur_network)
# На выходе, например ([], [<Autodesk.Revit.DB.FamilyInstance object at 0x0000000000000044 [Autodesk.Revit.DB.FamilyInstance]>])
def ElEquipFind (networkToFindIn):
	Circuit_connected_elements = networkToFindIn.Elements
	ListOfConnectedElements = [] # Список с подключёнными семействами вида: [<Autodesk.Revit.DB.FamilyInstance object at 0x0000000000000034 [Autodesk.Revit.DB.FamilyInstance]>, <Autodesk.Revit.DB.FamilyInstance object at 0x0000000000000035 [Autodesk.Revit.DB.FamilyInstance]>]
	for i in Circuit_connected_elements:
		ListOfConnectedElements.append(i)
	# При этом сначала обработаем все категории кроме Электрооборудования. С ним отдельная песня.
	ListOfConnectedElementsNotElEquip = [] # Подключённые элементы не Электрооборудование.
	ListOfConnectedElementsOnlyElEquip = [] # Подключённые элементы ТОЛЬКО Электрооборудование. Вид: [<Autodesk.Revit.DB.FamilyInstance object at 0x000000000000003F [Autodesk.Revit.DB.FamilyInstance]>]
	for i in ListOfConnectedElements:
		try: # для Ревитов до 2025 включительно
			if i.Category.Id.IntegerValue != int(BuiltInCategory.OST_ElectricalEquipment):
				ListOfConnectedElementsNotElEquip.append(i)
			else:
				ListOfConnectedElementsOnlyElEquip.append(i)
		except: # для 2026 Ревита
			if i.Category.Id.Value != int(BuiltInCategory.OST_ElectricalEquipment):
				ListOfConnectedElementsNotElEquip.append(i)
			else:
				ListOfConnectedElementsOnlyElEquip.append(i)
	return ListOfConnectedElementsNotElEquip, ListOfConnectedElementsOnlyElEquip

# Вспомогательная функция. Выдаёт число электроприёмников ненулевой мощности для списка элементов НЕ Электрооборудования.
# Пример обращения: ConsCoutForNotElEquipList(ListOfConnectedElementsNotElEquip)
def ConsCoutForNotElEquipList (ListOfConnectedElementsNotElEquip):
	ConsCountinList = 0 # выходное число эл.приём.
	# Теперь соберём все приёмники с ненулевой мощностью.
	# придётся понимать по строке во встроенном параметре RBS_ELECTRICAL_DATA. Потому что сама мощность может содержаться в любом параметре с любым именем.
	for i in ListOfConnectedElementsNotElEquip:
		try:
			# Достаём сам коннектор, т.к. только из его параметров можно узнать полную мощность нормальным образом.
			# https://forums.autodesk.com/t5/revit-api-forum/getting-electrical-load-information-from-in-place-families/m-p/7392932#M25316
			it = i.MEPModel.ConnectorManager.Connectors.GetEnumerator() # <Autodesk.Revit.DB.ConnectorSetIteratorForward object at 0x000000000000027D [Autodesk.Revit.DB.ConnectorSetIteratorForward]>
			it.MoveNext()
			conn = it.Current # <Autodesk.Revit.DB.Connector object at 0x000000000000027E [Autodesk.Revit.DB.Connector]>
			famConnInfo = conn.GetMEPConnectorInfo() # <Autodesk.Revit.DB.MEPFamilyConnectorInfo object at 0x000000000000027F [Autodesk.Revit.DB.MEPFamilyConnectorInfo]>
			param = famConnInfo.GetConnectorParameterValue(ElementId(BuiltInParameter.RBS_ELEC_APPARENT_LOAD)) # <Autodesk.Revit.DB.IntegerParameterValue object at 0x0000000000000281 [Autodesk.Revit.DB.IntegerParameterValue]>
			if param.Value > 0:
				ConsCountinList = ConsCountinList + 1
		except: # !!!!!!!!!ТУТ РАЗОБРАТЬСЯ, ИНОГДА ВЫДАЁТ ЧТО ПАПАРМЕТР НИЧТО! НЕ ПОНЯТНО ПОЧЕМУ. ПОКА ЧТО ПРОСТО БУДЕМ СЧИТАТЬ ЧТО ЕСТЬ ЭЛЕКТРОПРИЁМНИК НЕНУЛЕВОЙ МОЩНОСТИ!!!!!!!!!!!!!!!
			ConsCountinList = ConsCountinList + 1
		'''
		было так
		rvtPowerString = GetBuiltinParam(i, BuiltInParameter.RBS_ELECTRICAL_DATA).AsString() # строка "Данные об электрооборудовании" вида:'230 В/1-108 В*А'
		if '-0 ' not in rvtPowerString and '-0,0 ' not in rvtPowerString and '-0,00 ' not in rvtPowerString and '-0,000 ' not in rvtPowerString and '-0.0 ' not in rvtPowerString and '-0.00 ' not in rvtPowerString and '-0.000 ' not in rvtPowerString: # Вид: '230 В/1-108 В*А'
			ConsCountinList = ConsCountinList + 1
		'''
	return ConsCountinList


# Функция выдаёт число электроприёмников для списка семейств Электрооборудования.
# А также 2-м элементом кортежа список следующего по уровню Электрооборудования для следующего анализа.
# Пример обращения ElEquipAnalisys(ListOfConnectedElementsOnlyElEquip)
def ElEquipAnalisys (ListOfConnectedElementsOnlyElEquip):
	ConsCount = 0 # Текущее количество эл.приём во всём входном списке.
	ListOfConnectedElementsOnlyElEquip_1 = [] # список с электроприёмниками (семействами) следующего уровня.
	curNetworksList_1 = None # Список с текущими электроцепями данного Электрооборудования.
	# Разбираемся с Электрооборудованием. Если оно было в цепи, то нужно влезть в его эл.цепи и провернуть функцию ещё раз.
	for i in ListOfConnectedElementsOnlyElEquip: # i - Это <Autodesk.Revit.DB.FamilyInstance object at 0x0000000000000040 [Autodesk.Revit.DB.FamilyInstance]>
		try:
			curNetworksList_1 = i.MEPModel.AssignedElectricalSystems # Список с текущими электроцепями данного Электрооборудования. <Autodesk.Revit.DB.Electrical.ElectricalSystemSet object at 0x0000000000000043 [Autodesk.Revit.DB.Electrical.ElectricalSystemSet]>
		except: # Для 2022 Ревита
			if len([j for j in i.MEPModel.GetAssignedElectricalSystems()]) > 0: # Убеждаемся что количество цепей больше 0, т.е. они вообще есть.
				curNetworksList_1 = i.MEPModel.GetAssignedElectricalSystems() # Метод для 2022 Ревита
		if curNetworksList_1 is not None: # Если у щита вообще есть электроцепи
			for j in curNetworksList_1: # Вид <Autodesk.Revit.DB.Electrical.ElectricalSystemSet object at 0x0000000000000045 [Autodesk.Revit.DB.Electrical.ElectricalSystemSet]>
				# Вытаскиваем для каждой цепи число подключённых эл.приём НЕ Электрооборудование
				exitCortage_1 = ElEquipFind(j) # j - это электроцепь
				ListOfConnectedElementsNotElEquip_1 = exitCortage_1[0] # Подключённые элементы не Электрооборудование.
				ListOfConnectedElementsOnlyElEquip_1 = exitCortage_1[1] # Подключённые элементы ТОЛЬКО Электрооборудование.
				# Теперь соберём все приёмники с ненулевой мощностью.
				ConsCount = ConsCount + ConsCoutForNotElEquipList(ListOfConnectedElementsNotElEquip_1)
		else:
			pass
	return ConsCount, ListOfConnectedElementsOnlyElEquip_1



# Функция выдаёт количество электроприёмников в цепи с ненулевой мощностью
# На входе конкретная эл. цепь.
# На выходе число электроприёмников в ней.
# Пример обращения: ConsumersCountinNetwork(networks[0]) # текущая цепь cur_network = networks[7]
def ConsumersCountinNetwork (cur_network):
	ConsCountinNetwork = 0 # Выходное количество электроприёмников в данной цепи

	ListOfConnectedElementsNotElEquip = [] # Подключённые элементы не Электрооборудование.
	ListOfConnectedElementsOnlyElEquip = [] # Подключённые элементы ТОЛЬКО Электрооборудование. Вид: [<Autodesk.Revit.DB.FamilyInstance object at 0x000000000000003F [Autodesk.Revit.DB.FamilyInstance]>]
	exitCortage = ElEquipFind(cur_network)
	ListOfConnectedElementsNotElEquip = exitCortage[0]
	ListOfConnectedElementsOnlyElEquip = exitCortage[1]

	# Теперь соберём все приёмники с ненулевой мощностью.
	ConsCountinNetwork = ConsCountinNetwork + ConsCoutForNotElEquipList(ListOfConnectedElementsNotElEquip)

	while ListOfConnectedElementsOnlyElEquip != []:
		exitCortage_1 = ElEquipAnalisys(ListOfConnectedElementsOnlyElEquip)
		ConsCountinNetwork = ConsCountinNetwork + exitCortage_1[0]
		ListOfConnectedElementsOnlyElEquip = exitCortage_1[1]
			
	
	return ConsCountinNetwork



# функция синхронизации длины для автоматов и кабелей
# На входе:
# elems_avtomats_or_cables - семейства автоматов или кабелей
# networks - электроцепи
# Param_Circuit_number - имя параметра "Имя цепи"
# Electrical_Circuit_PathMode_method - настройка метода подсчёта длин кабелей из Настроек Теслы
# Length_stock - запас кабеля
# Param_Cable_length, Param_FarestWireLength, Param_ReducedWireLength - имена параметров длины кабеля
def Length_Sync_Function (elems_avtomats_or_cables, networks, Param_Circuit_number, Electrical_Circuit_PathMode_method, Length_stock, Param_Cable_length, Param_FarestWireLength, Param_ReducedWireLength):

	for i in elems_avtomats_or_cables:
		for j in networks:
			if i.LookupParameter(Param_Circuit_number).AsString() == j.Name: # Если совпадает имя цепи
				if Electrical_Circuit_PathMode_method == 3: # если длину берём как "усреднённое значение"
					cur_middle_length = round(GetMinMaxCircuitPath(j) * Length_stock) # Текущая усреднённая длина
					t = Transaction(doc, 'ElectricalCircuitLengthSync')
					t.Start()
					i.LookupParameter(Param_Cable_length).Set(cur_middle_length)
					try: # при этом режиме расчёта длины нужно обнулить параметры дальней и приведённой длин чтобы не мешались потом в расчётах схем
						i.LookupParameter(Param_FarestWireLength).Set(0)
						i.LookupParameter(Param_ReducedWireLength).Set(0)
					except:
						pass
					t.Commit()
				elif Electrical_Circuit_PathMode_method == 4: # если длину берём из параметра Param_TSL_WireLength TSL_Длина проводника
					t = Transaction(doc, 'ElectricalCircuitLengthSync')
					t.Start()
					try:	
						i.LookupParameter(Param_Cable_length).Set(round(j.LookupParameter(Param_TSL_WireLength).AsDouble() * Length_stock)) # Переписываем длину из TSL_Длина проводника					
					except:
						TaskDialog.Show('Синхронизация', 'Не удалось синхронизировать длину кабеля по параметру ' + Param_TSL_WireLength + '. Проверьте Настройки программы.')
						#raise Exception('Не удалось синхронизировать длину кабеля по параметру ' + Param_TSL_WireLength + '. Проверьте Настройки программы.')	
					try:
						i.LookupParameter(Param_FarestWireLength).Set(round(j.LookupParameter(Param_TSL_FarestWireLength).AsDouble() * Length_stock)) # Переписываем длину из TSL_Длина проводника до дальнего устройства
						i.LookupParameter(Param_ReducedWireLength).Set(round(j.LookupParameter(Param_TSL_ReducedWireLength).AsDouble() * Length_stock)) # Переписываем длину из TSL_Длина проводника приведённая
					except:
						# если нет какого-то из четырёх параметров длины
						# if Param_FarestWireLength not in [p.Definition.Name for p in i.Parameters] or Param_TSL_FarestWireLength not in [p.Definition.Name for p in j.Parameters] or Param_ReducedWireLength not in [p.Definition.Name for p in i.Parameters] or Param_TSL_ReducedWireLength not in [p.Definition.Name for p in j.Parameters]:
						pass # ничего не делать если что-то не так с четырмя параметрами особенных длин
					t.Commit()
				else: # если длину берём как "все устройства", "наиболее удалённое устройство" или "не управлять режимом траектории"
					t = Transaction(doc, 'ElectricalCircuitLengthSync')
					t.Start()
					try:	
						i.LookupParameter(Param_Cable_length).Set(round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(j, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS) * Length_stock)) # Переписываем длину					
						#Transaction_sukhov_1 (doc, Param_Cable_length, round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(j, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), DisplayUnitType.DUT_METERS) * Length_stock), i) # Переписываем длину
					except:
						i.LookupParameter(Param_Cable_length).Set(round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(j, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters) * Length_stock)) # Переписываем длину	
						#Transaction_sukhov_1 (doc, Param_Cable_length, round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(j, BuiltInParameter.RBS_ELEC_CIRCUIT_LENGTH_PARAM).AsDouble(), UnitTypeId.Meters) * Length_stock), i) # Переписываем длину
					try: # при этом режиме расчёта длины нужно обнулить параметры дальней и приведённой длин чтобы не мешались потом в расчётах схем
						i.LookupParameter(Param_FarestWireLength).Set(0)
						i.LookupParameter(Param_ReducedWireLength).Set(0)
					except:
						pass
					t.Commit()








'''
i j 
k x 
y z

Чтоб тестить 
ara = []
for i in networks:
	ara.append(ConsumersCountinNetwork(i))
# [2, 1, 2, 4, 1, 1, 2, 15, 0, 1, 2, 4, 1, 0, 0, 1]
ara1 = []
for i in networks:
	ara1.append(i.Name)
# [u'ЩР-2-1', u'ЩР-2-2', u'ЩР-2-3', u'ЩР-2-4', u'ЩР-2-5', u'ЩР-2-6', u'ЩР-1-1', u'ЩР-1-2', u'ЩР-1-3', u'ЩР-3-1', u'ЩР-3-2', u'ЩР-2-7', u'ЩР-4-1', u'ЩР-4-2', u'ЩР-4-3', u'ЩР-3-3']
'''



if Button_Cancel_pushed != 1: # Если кнопка "Cancel" не была нажата



	# Если был выставлен флажок синхронизации длины				
	if Length_sync == True and elems_avtomats != []:
		Length_Sync_Function(elems_avtomats, networks, Param_Circuit_number, Electrical_Circuit_PathMode_method, Length_stock, Param_Cable_length, Param_FarestWireLength, Param_ReducedWireLength)

	# Если был выставлен флажок "Синхронизировать TSL_Кабель"
	if checkBox_TSLCable == True and elems_TSLCable != []:
		Length_Sync_Function(elems_TSLCable, networks, Param_Circuit_number, Electrical_Circuit_PathMode_method, Length_stock, Param_Cable_length, Param_FarestWireLength, Param_ReducedWireLength)

	t = Transaction(doc, 'OK_sync')
	t.Start()

	if checkBox_RoomName_Checked == True: # если был выставлен флажок "синхронизировать наименование помещения"
		for i in elems_avtomats:
			for j in networks:
				if i.LookupParameter(Param_Circuit_number).AsString() == j.Name: # если совпадает имя цепи
					Circuit_connected_elements = j.Elements # Получаем список всех элементов подключённых к данной цепи
					# Если выставлен флажок "Не брать имена пространств для умных линий", то выкидываем умные линии, чтобы не записались пространства в которых они проходят
					SmartLines_donttake = 1 # пока что всегда будем выкидывать умные линии. А там видно будет.
					if SmartLines_donttake == 1:
						hlplst = []
						for b in Circuit_connected_elements:
							if b.Symbol.FamilyName not in Smart_lines_names:
								hlplst.append(b)
						Circuit_connected_elements = [d for d in hlplst]
					Circuit_spaces = [] # Создаём список с номерами или именами пространств
					for k in Circuit_connected_elements:
						if comboBox_RoomNameorNumber_SelectedItem == RoomNameorNumber[0]: # если пользователь синхронизирует 'Номер пространства'
							if GetSpaceNameNumberFromElement(k)[1] not in Circuit_spaces and GetSpaceNameNumberFromElement(k)[1] != None: # если такого номера ещё нет в списке номеров пространств AND номер не None
								Circuit_spaces.append(GetSpaceNameNumberFromElement(k)[1])
						else: # если пользователь синхронизирует 'Имя пространства'
							if GetSpaceNameNumberFromElement(k)[0] not in Circuit_spaces and GetSpaceNameNumberFromElement(k)[0] != None: # если такого имени ещё нет в списке номеров пространств AND имя не None
								Circuit_spaces.append(GetSpaceNameNumberFromElement(k)[0])
					#t = Transaction(doc, 'room_name sync')
					#t.Start()
					if i.LookupParameter(Param_Room_Name) != None: # если такой параметр есть у автомата
						i.LookupParameter(Param_Room_Name).Set( ', '.join(Circuit_spaces)  )
					#t.Commit()



	# Если был выставлен флажок "Число электроприёмников"
	if checkBox_ConsumersCount_Checked == True:
		for i in elems_avtomats:
			for j in networks:
				if i.LookupParameter(Param_Circuit_number).AsString() == j.Name: # Если совпадает имя цепи
					Current_ConsumersCountinNetwork = ConsumersCountinNetwork(j)
					if i.LookupParameter(Param_Consumers_count) != None: # если такой параметр есть у автомата
						i.LookupParameter(Param_Consumers_count).Set(Current_ConsumersCountinNetwork)

	# Если был выставлен флажок "Способ прокладки"
	if checkBox_LayingMethod == True:
		for i in elems_avtomats:
			for j in networks:
				if i.LookupParameter(Param_Circuit_number).AsString() == j.Name: # Если совпадает имя цепи
					if j.LookupParameter(Param_TSL_Param_Laying_Method) != None and j.LookupParameter(Param_TSL_Param_Laying_Method).AsString() != None: # если такой параметр есть в элеткроцепи и он прописан вообще
						i.LookupParameter(Param_Laying_Method).Set(AddZapas_for_Laying_Method(j.LookupParameter(Param_TSL_Param_Laying_Method).AsString(), Length_stock))
		for i in elems_TSLCable:
			for j in networks:
				if i.LookupParameter(Param_Circuit_number).AsString() == j.Name: # Если совпадает имя цепи
					if j.LookupParameter(Param_TSL_Param_Laying_Method) != None and j.LookupParameter(Param_TSL_Param_Laying_Method).AsString() != None: # если такой параметр есть в элеткроцепи и он прописан вообще
						i.LookupParameter(Param_Laying_Method).Set(AddZapas_for_Laying_Method(j.LookupParameter(Param_TSL_Param_Laying_Method).AsString(), Length_stock))


	elems_avtomats_idsFoundKc = [] # Айдишники автоматов в которые удалось переписать Кс
	# Если был выставлен флажок "Синхронизировать коэффициенты спроса"
	if checkBox_SyncKc_Checked == True:
		# Собираем все семейства расчётных табличек у которых в параметре Принадлежность есть данные как в наименовании электроприёмников у выбранных автоматов.
		Electric_receiver_Names_InAVsSelected = [] # Наименования электроприёмников у выбранных автоматов. Вид: [u'ЩО-1', u'ЩР-1.2']
		for i in elems_avtomats:
			if i.LookupParameter(Param_Electric_receiver_Name).AsString() != '': # Если у кого не заполнено наименование электроприёмника, то не берём такие в выборку
				Electric_receiver_Names_InAVsSelected.append(i.LookupParameter(Param_Electric_receiver_Name).AsString())
		
		Electric_receiver_Names_InAVsSelected_NotFoundInCalcTables = [] # Наименования электроприёмников не найденные в принадлежностях табличек результата (для предупреждения пользователю)
		#CalcTables_RepeatedAccessory_Ids = [] # Id шники табличек с одинаковыми принадлежностями, которые найдены в списке наименований электроприёмников (для предупреждения пользователю). Вид: ['1517673']
		CalcTables_AccessoriesList = [] # Принадлежности найденных нужных нам табличек (вспомогательный список). Вид: [u'ЩР-1.2']
		# Electric_receiver_NamesFoundinCalcTables = [] # Имена электроприёмников найденные в табличках результата (вспомогательный список).
		#Electric_receiver_NamesNotFoundinCalcTables = [] # Имена электроприёмников НЕ найденные в табличках результата (для предупреждения пользователю)

		# Собираем таблички результатов (только нужные нам)
		elems_calculated_tables = [] # Вид: [<Autodesk.Revit.DB.AnnotationSymbol object at 0x000000000000002E [Autodesk.Revit.DB.AnnotationSymbol]>]
		elems_calculated_tables_RepeatedAccessory = [] # таблички с дублирующимися принадлежностями
		for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_GenericAnnotation).WhereElementIsNotElementType().ToElements():
			if using_calculated_tables.count(i.Name) > 0: # Если это семейство таблички результатов
				if i.LookupParameter(Param_Accessory).AsString() in Electric_receiver_Names_InAVsSelected: # Если её принадлежность есть в списке наименований электроприёмников
					if i.LookupParameter(Param_Accessory).AsString() not in CalcTables_AccessoriesList: # Если это не табличка с дублирующейся принадлежностью
						elems_calculated_tables.append(i) 
						CalcTables_AccessoriesList.append(i.LookupParameter(Param_Accessory).AsString())
					else:
						elems_calculated_tables_RepeatedAccessory.append(i)
						#CalcTables_RepeatedAccessory_Ids.append(str(i.Id)) # Вид: ['1517673']

		# Вытащим айдишники табличек с дублирующимися принадлежностями
		Double_AlertStringKc = '' # Строка для предупреждения о дублировании принадлежностей в расчётных 
		for i in CalcTables_AccessoriesList:
			curAccessory = i
			curIds = []
			for j in elems_calculated_tables + elems_calculated_tables_RepeatedAccessory:
				if i == j.LookupParameter(Param_Accessory).AsString():
					curIds.append(str(j.Id))
			if len(curIds) > 1: # Если есть повторения принадлежности
				Double_AlertStringKc = Double_AlertStringKc + '\r\n' + i + ': ' + ';'.join(curIds)


		# Переписываем коэффициенты спроса из найденных табличек в автоматы
		elems_avtomats_idsNotFoundKc = [] # Айдишники автоматов в которые НЕ удалось переписать Кс
		if elems_calculated_tables != []: # если вообще хоть одна табличка попалась
			for i in elems_avtomats:
				for j in elems_calculated_tables:
					if i.LookupParameter(Param_Electric_receiver_Name).AsString() == j.LookupParameter(Param_Accessory).AsString(): # Если наименование электроприёмника совпало с принадлежностью таблички
						i.LookupParameter(Param_Kc).Set(j.LookupParameter(Param_Kc).AsDouble())
						elems_avtomats_idsFoundKc.append(str(i.Id))
		for i in elems_avtomats:
			if str(i.Id) not in elems_avtomats_idsFoundKc:
				elems_avtomats_idsNotFoundKc.append(str(i.Id))

		# Формируем предупреждения о том какие Кс не записались
		AlertString = ''
		if elems_avtomats_idsFoundKc == []:
			AlertString = 'Не удалось синхронизировать ни один коэффициент спроса!\r\n\r\n'

		if Double_AlertStringKc != '':
			AlertString = AlertString + 'Некоторые таблички результатов (' + ', '.join(using_calculated_tables) + ') имеют дублирующиеся значения в параметре "' + Param_Accessory + '".\r\nКоэффициент спроса был синхронизирован только из одной из них. Id остальных табличек с дублирующимися принадлежностями: \r\n' + Double_AlertStringKc + '\r\n\r\n'

		if elems_avtomats_idsNotFoundKc != []:
			AlertString = AlertString + 'Для некоторых автоматических выключателей Кс не был синхронизирован, т.к. в модели нет табличек результата (' + ', '.join(using_calculated_tables) + ') в которых значение параметра "' + Param_Accessory + '" совпадало бы со значением параметра "' + Param_Electric_receiver_Name + '" автоматов. Id автоматов для которых не удалось синхронизировать коэффициенты спроса: \r\n' + ';'.join(elems_avtomats_idsNotFoundKc)

		if AlertString != '':
			SyncScheme_AlertForm().ShowDialog()


	t.Commit()

	if Missing_Groups_handle != 1 or elems_avtomats_idsFoundKc != []:
		TaskDialog.Show('Синхронизация', 'Синхронизация выполнена. Данные записаны в аппараты.') # Показывает окошко в стиле Ревит 

transGroup.Assimilate() # принимаем группу транзакций





'''
for i in elems_avtomats:
	a = 0
	while a < len(networks):
		if i.LookupParameter(Param_Circuit_number).AsString() == networks[a].Name:
			Transaction_sukhov_1 (doc, Param_Cosf, round(networks[a].LookupParameter('Коэффициент мощности').AsDouble(), 2), i)
		a = a+1


Param_Accessory = 'Принадлежность щиту'
Param_Electric_receiver_Name = 'Наименование электроприёмника'


		self._SyncScheme_AlertForm_textBox1.Text = Ids_notwritten_Textstring


		hlp_lst = [] # вспомогательный список
		for i in elems_calculated_tables_RepeatedAccessory:
			for j in elems_calculated_tables:
				if str(i.Id) not in CalcTables_RepeatedAccessory_Ids and str(j.Id) not in CalcTables_RepeatedAccessory_Ids:
					if i.LookupParameter(Param_Accessory).AsString() == j.LookupParameter(Param_Accessory).AsString():
						CalcTables_RepeatedAccessory_Ids.append(str(i.Id))
						CalcTables_RepeatedAccessory_Ids.append(str(j.Id))




if fam_param_name2 in [p.Definition.Name for p in i.Parameters]: # если такой параметр вообще есть в семействе (и он по экземпляру)...
			elems_params_value[n].append(i.LookupParameter(fam_param_name2).AsString())
		elif fam_param_name2 in [p.Definition.Name for p in i.Symbol.Parameters]: # или по типу
			elems_params_value[n].append(i.Symbol.LookupParameter(fam_param_name2).AsString())

fam_param_names[0] fam_param_names[1] fam_param_names[2]  fam_param_names[3] 





'''