'''
Программа проверяет соответствует ли освещённость пространств заданным в Настройках значениям освещённости.
'''

import os
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
# pyRevit context
from pyrevit import revit, forms
try:
	import link_reader
except Exception:
	_lib_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
	_lib_path = os.path.join(_lib_root, 'lib')
	if _lib_path not in sys.path:
		sys.path.insert(0, _lib_path)
	import link_reader
# Библиотеки ExtensibleStorage
import System.Runtime.InteropServices
# import uuid
from Autodesk.Revit.DB.ExtensibleStorage import *
from Autodesk.Revit.DB.ExtensibleStorage import *
from System import Guid # you need to import this, when you work with Guids!
from System.Collections.Generic import *



#____________________Переменные с которыми работает программа__________________________________________________________________________________
doc = revit.doc
uidoc = revit.uidoc

# Переменные отвечающие за соединение с хранилищем значений освещённости (5-е хранилище)
Guidstr_Illumination_Values_Storage = '36f085d8-43ee-4230-acec-099431f45dad'
SchemaName_for_Illumination_Values_Storage = 'Illumination_Values_Storage'
FieldName_for_Illumination_Values_Storage = 'Illumination_Values_Storage_list'

# Имя самой программы
Program_name = 'UniBIM'

# Иконка окна (если есть)
iconmy = None
try:
	icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
	if os.path.exists(icon_path):
		iconmy = Icon(icon_path)
except Exception:
	iconmy = None

'''
# Переменные отвечающие за соединение с хранилищем значений освещённости (5-е хранилище)
Guidstr_Illumination_Values_Storage = '36f085d8-43ee-4230-acec-099431f45dad'
SchemaName_for_Illumination_Values_Storage = 'Illumination_Values_Storage'
FieldName_for_Illumination_Values_Storage = 'Illumination_Values_Storage_list'

# Имя самой программы
Program_name = 'TESLABIM'
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
	TaskDialog.Show('Проверка освещённости', 'Настройки норм освещённости не найдены или были повреждены.\n Откройте окно настроек Программы, чтобы задать нормы освещённости.')
	znach3 = [] # тогда делаем этот список пустым
else:
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



# Готовим списки для заполнения таблицы в окне

# Функция подготовки данных для заполнения таблицы в окне.
# На входе список znach3 из Хранилища
# На выходе ничего, но объявлены нужные нам списки
def _select_space_sources(host_doc):
    # Auto-select: prefer first loaded link, otherwise current model
    out = []
    
    # 1. Try link
    link_inst = link_reader.select_link_instance_auto(host_doc)
    if link_inst:
        try:
            name = getattr(link_inst, 'Name', u'Связь')
            label = u"Связь: {0}".format(name)
            out.append((label, link_inst))
        except Exception:
            pass
            
    # 2. If no link (or just always?), add current model? 
    # User said "find the one that exists". If link exists, use it.
    # If no link, use current?
    if not out:
        out.append((u"Текущая модель", None))
        
    return out


def _iter_spaces_for_source(host_doc, source_tuple):
	label, link_inst = source_tuple
	if link_inst is None:
		return host_doc, label, FilteredElementCollector(host_doc).OfCategory(BuiltInCategory.OST_MEPSpaces).ToElements()
	if not link_reader.is_link_loaded(link_inst):
		return None, label, []
	link_doc = link_reader.get_link_doc(link_inst)
	if link_doc is None:
		return None, label, []
	return link_doc, label, FilteredElementCollector(link_doc).OfCategory(BuiltInCategory.OST_MEPSpaces).ToElements()


def IllCheck_dataGridView_Fill (znach3):
	global spaces_meta
	global spaces_els_numbers
	global spaces_els_names
	global spaces_els_names_display
	global spaces_els_illumination_calculated
	global rated_illumination
	# вытаскиваем все пространства из проекта
	spaces_meta = []
	spaces_els_numbers = [] # номера пространств ['1', '2', '4', '5']
	spaces_els_names = [] # имена пространств ['Sup Space 1', 'Sup space 2', ...]
	spaces_els_names_display = [] # имена пространств с пометкой источника
	spaces_els_illumination_calculated = [] # расчётная (получившаяся) освещённость
	rated_illumination = [] # нормируемая освещённость из Хранилища

	for source in selected_sources:
		source_doc, source_label, spaces_els = _iter_spaces_for_source(doc, source)
		if not spaces_els:
			continue
		for i in spaces_els:
			try:
				number_val = GetBuiltinParam(i, BuiltInParameter.ROOM_NUMBER).AsString()
			except Exception:
				number_val = ''
			spaces_els_numbers.append(number_val) # Получаем номер пространства
			cur_space_name_hlp = GetBuiltinParam(i, BuiltInParameter.ROOM_NAME).AsString() # вспомогательная переменная. Имя текщего пространства
			spaces_els_names.append(cur_space_name_hlp) # Получаем имя пространства
			if source_label != u"Текущая модель":
				display_name = u"{0} ({1})".format(cur_space_name_hlp, source_label)
			else:
				display_name = cur_space_name_hlp
			spaces_els_names_display.append(display_name)
			spaces_meta.append({
				"doc": source_doc,
				"link_instance": source[1],
				"name": cur_space_name_hlp,
				"number": number_val,
				"display": display_name,
				"element": i
			})
			try:
				spaces_els_illumination_calculated.append(round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_ROOM_AVERAGE_ILLUMINATION).AsDouble(), DisplayUnitType.DUT_LUX), 0)) # Получаем освещённость пространства
			except:
				spaces_els_illumination_calculated.append(round(UnitUtils.ConvertFromInternalUnits(GetBuiltinParam(i, BuiltInParameter.RBS_ELEC_ROOM_AVERAGE_ILLUMINATION).AsDouble(), UnitTypeId.Lux), 0))
			cur_cons_list = Get_coincidence_in_list(cur_space_name_hlp, znach3) # вспомогательная переменная. Индексы найдённых имён пространств или [] если пространства не найдены в ES.
			if cur_cons_list != []: # если текущее имя пространства есть в Хранилище:
				rated_illumination.append(znach3[cur_cons_list[0]+1]) # выписываем нормируемую освещённость для данного имени пространства
			else:
				rated_illumination.append('Нет данных')

selected_sources = _select_space_sources(doc)
if not selected_sources:
	TaskDialog.Show('Проверка освещённости', 'Источник пространств не выбран.')
	sys.exit()

IllCheck_dataGridView_Fill(znach3) # запускаем эту функцию чтобы объявить списки пространств и освещённостей

IllCheck_label1_Text = 'Нормы освещённости и высоты рабочих плоскостей выставляются в Настройках ' + Program_name

'''
# Отображение формы поверх всех окон
self.TopMost = True
self.InitializeComponent()
'''




class IlluminationCheckWindow(Form):
	def __init__(self):
		self.TopMost = True
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._IllCheck_dataGridView1 = System.Windows.Forms.DataGridView()
		self._IllCheck_OKbutton = System.Windows.Forms.Button()
		self._IllCheck_Cancelbutton = System.Windows.Forms.Button()
		self._IllCheck_CheckAgainbutton = System.Windows.Forms.Button()
		self._IllCheck_Column4 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IllCheck_Column1 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IllCheck_Column2 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IllCheck_Column3 = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._IllCheck_Show_Column = System.Windows.Forms.DataGridViewButtonColumn()
		self._IllCheck_label1 = System.Windows.Forms.Label()
		self._IllCheck_dataGridView1.BeginInit()
		self.SuspendLayout()
		# 
		# IllCheck_dataGridView1
		# 
		self._IllCheck_dataGridView1.AllowUserToAddRows = False
		self._IllCheck_dataGridView1.AllowUserToDeleteRows = False
		self._IllCheck_dataGridView1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._IllCheck_dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._IllCheck_dataGridView1.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._IllCheck_Column4,
			self._IllCheck_Column1,
			self._IllCheck_Column2,
			self._IllCheck_Column3,
			self._IllCheck_Show_Column]))
		self._IllCheck_dataGridView1.Location = System.Drawing.Point(23, 38)
		self._IllCheck_dataGridView1.Name = "IllCheck_dataGridView1"
		self._IllCheck_dataGridView1.ReadOnly = True
		self._IllCheck_dataGridView1.Size = System.Drawing.Size(636, 325)
		self._IllCheck_dataGridView1.TabIndex = 0
		self._IllCheck_dataGridView1.CellContentClick += self.IllCheck_dataGridView1CellContentClick
		# 
		# IllCheck_OKbutton
		# 
		self._IllCheck_OKbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._IllCheck_OKbutton.Location = System.Drawing.Point(23, 423)
		self._IllCheck_OKbutton.Name = "IllCheck_OKbutton"
		self._IllCheck_OKbutton.Size = System.Drawing.Size(75, 23)
		self._IllCheck_OKbutton.TabIndex = 1
		self._IllCheck_OKbutton.Text = "OK"
		self._IllCheck_OKbutton.UseVisualStyleBackColor = True
		self._IllCheck_OKbutton.Click += self.IllCheck_OKbuttonClick
		# 
		# IllCheck_Cancelbutton
		# 
		self._IllCheck_Cancelbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._IllCheck_Cancelbutton.Location = System.Drawing.Point(584, 423)
		self._IllCheck_Cancelbutton.Name = "IllCheck_Cancelbutton"
		self._IllCheck_Cancelbutton.Size = System.Drawing.Size(75, 23)
		self._IllCheck_Cancelbutton.TabIndex = 2
		self._IllCheck_Cancelbutton.Text = "Cancel"
		self._IllCheck_Cancelbutton.UseVisualStyleBackColor = True
		self._IllCheck_Cancelbutton.Click += self.IllCheck_CancelbuttonClick
		# 
		# IllCheck_CheckAgainbutton
		# 
		self._IllCheck_CheckAgainbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._IllCheck_CheckAgainbutton.Location = System.Drawing.Point(23, 385)
		self._IllCheck_CheckAgainbutton.Name = "IllCheck_CheckAgainbutton"
		self._IllCheck_CheckAgainbutton.Size = System.Drawing.Size(117, 23)
		self._IllCheck_CheckAgainbutton.TabIndex = 3
		self._IllCheck_CheckAgainbutton.Text = "Проверить ещё раз"
		self._IllCheck_CheckAgainbutton.UseVisualStyleBackColor = True
		self._IllCheck_CheckAgainbutton.Click += self.IllCheck_CheckAgainbuttonClick
		# 
		# IllCheck_Column4
		# 
		self._IllCheck_Column4.HeaderText = "Номер пространства"
		self._IllCheck_Column4.Name = "IllCheck_Column4"
		self._IllCheck_Column4.ReadOnly = True
		# 
		# IllCheck_Column1
		# 
		self._IllCheck_Column1.AutoSizeMode = System.Windows.Forms.DataGridViewAutoSizeColumnMode.Fill
		self._IllCheck_Column1.HeaderText = "Имя пространства"
		self._IllCheck_Column1.Name = "IllCheck_Column1"
		self._IllCheck_Column1.ReadOnly = True
		# 
		# IllCheck_Column2
		# 
		self._IllCheck_Column2.HeaderText = "Нормируемая освещённость (Лк)"
		self._IllCheck_Column2.Name = "IllCheck_Column2"
		self._IllCheck_Column2.ReadOnly = True
		# 
		# IllCheck_Column3
		# 
		self._IllCheck_Column3.HeaderText = "Расчётная освещённость (Лк)"
		self._IllCheck_Column3.Name = "IllCheck_Column3"
		self._IllCheck_Column3.ReadOnly = True
		# 
		# IllCheck_Show_Column
		# 
		self._IllCheck_Show_Column.HeaderText = "Показать"
		self._IllCheck_Show_Column.Name = "IllCheck_Show_Column"
		self._IllCheck_Show_Column.ReadOnly = True
		# 
		# IllCheck_label1
		# 
		self._IllCheck_label1.Location = System.Drawing.Point(23, 13)
		self._IllCheck_label1.Name = "IllCheck_label1"
		self._IllCheck_label1.Size = System.Drawing.Size(636, 23)
		self._IllCheck_label1.TabIndex = 4
		self._IllCheck_label1.Text = "Заполняется программно"
		# 
		# IlluminationCheckWindow
		# 
		self.ClientSize = System.Drawing.Size(694, 458)
		self.Controls.Add(self._IllCheck_label1)
		self.Controls.Add(self._IllCheck_CheckAgainbutton)
		self.Controls.Add(self._IllCheck_Cancelbutton)
		self.Controls.Add(self._IllCheck_OKbutton)
		self.Controls.Add(self._IllCheck_dataGridView1)
		self.Name = "IlluminationCheckWindow"
		self.Text = "Проверка освещённости"
		self.Load += self.IlluminationCheckWindowLoad
		self._IllCheck_dataGridView1.EndInit()
		self.ResumeLayout(False)

		if iconmy:
			self.Icon = iconmy


	def IllCheck_dataGridView1CellContentClick(self, sender, e):
		# Обрабатываем нажатие кнопок "Показать"
		if self._IllCheck_dataGridView1.CurrentCell.ColumnIndex == 4 and self._IllCheck_dataGridView1.CurrentCell.RowIndex != -1:
			row_idx = self._IllCheck_dataGridView1.CurrentCell.RowIndex
			if row_idx < 0 or row_idx >= len(spaces_meta):
				return
			meta = spaces_meta[row_idx]
			elem = meta.get("element")
			if elem is None:
				return

			# Показываем пространство в модели
			try:
				ElemsSet = ElementSet() #Создаём пустой набор элементов
				ElemsSet.Insert(elem) # засовываем в этот набор найденные элементы
				uidoc.ShowElements(ElemsSet)
			except Exception:
				pass

			# Подсвечиваем элементы в модели
			try:
				ele_ids = List[ElementId]([elem.Id])
				uidoc.Selection.SetElementIds(ele_ids)
			except Exception:
				try:
					link_inst = meta.get("link_instance")
					if link_inst:
						uidoc.ShowElements(link_inst.Id)
						TaskDialog.Show('Проверка освещённости', 'Элемент находится в связи. Выделение ограничено.')
				except Exception:
					pass



	def IlluminationCheckWindowLoad(self, sender, e):
		# Заполняем таблицу
		a = 0 # счётчик
		while a < len(spaces_els_names):
			self._IllCheck_dataGridView1.Rows.Add(spaces_els_numbers[a], spaces_els_names_display[a], rated_illumination[a], spaces_els_illumination_calculated[a], 'Показать') # Заполняем таблицу исходными данными
			# Красим ячейки
			if rated_illumination[a] != 'Нет данных':
				if int(rated_illumination[a]) > int(spaces_els_illumination_calculated[a]):
					self._IllCheck_dataGridView1.Rows[a].Cells[1].Style.ForeColor = Color.Red # меняет цвет в ячейке
					self._IllCheck_dataGridView1.Rows[a].Cells[2].Style.ForeColor = Color.Red
					self._IllCheck_dataGridView1.Rows[a].Cells[3].Style.ForeColor = Color.Red
			a = a + 1
		self._IllCheck_label1.Text = IllCheck_label1_Text


		

	def IllCheck_CheckAgainbuttonClick(self, sender, e):
		# сначала удаляем все строки
		a = self._IllCheck_dataGridView1.Rows.Count
		while a > 0:
			self._IllCheck_dataGridView1.Rows.RemoveAt(0) # сначала удаляем все строки
			a = a - 1
		IllCheck_dataGridView_Fill(znach3) # запускаем эту функцию чтобы объявить списки пространств и освещённостей
		# Заполняем таблицу
		a = 0 # счётчик
		while a < len(spaces_els_names):
			self._IllCheck_dataGridView1.Rows.Add(spaces_els_numbers[a], spaces_els_names_display[a], rated_illumination[a], spaces_els_illumination_calculated[a], 'Показать') # Заполняем таблицу исходными данными
			# Красим ячейки
			if rated_illumination[a] != 'Нет данных':
				if int(rated_illumination[a]) > int(spaces_els_illumination_calculated[a]):
					self._IllCheck_dataGridView1.Rows[a].Cells[1].Style.ForeColor = Color.Red # меняет цвет в ячейке
					self._IllCheck_dataGridView1.Rows[a].Cells[2].Style.ForeColor = Color.Red
					self._IllCheck_dataGridView1.Rows[a].Cells[3].Style.ForeColor = Color.Red
			a = a + 1

	def IllCheck_OKbuttonClick(self, sender, e):
		self.Close()

	def IllCheck_CancelbuttonClick(self, sender, e):
		self.Close()


#IlluminationCheckWindow().ShowDialog()	
IlluminationCheckWindow().Show()	


'''
ara = spaces_els[0] # <Autodesk.Revit.DB.Mechanical.Space object at 0x000000000000006C [Autodesk.Revit.DB.Mechanical.Space]>

GetBuiltinParam(ara, BuiltInParameter.ROOM_NAME).AsString() # Получаем имя пространства

self._IllCheck_dataGridView1.Rows[1].Cells[2].Style.ForeColor = Color.Aqua # меняет цвет в ячейке
'''
