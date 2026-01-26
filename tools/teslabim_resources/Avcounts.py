'''
Программа производит расчёт однолинейных схем ВРУ и щитов собранных с помощью семейств с названиями: 'GA_SHM_2D автоматический выключатель_ВРУ' или 'GA_SHM_2D автоматический выключатель_Щит'. 
Запись результатов расчёта производится в итоговые таблички (семейства с названиями: 'GA_SHM_Таблица_Расчетная для схемы' или 'GA_SHM_Таблица_Расчетная для щитов').


Ещё функции программы:

1) Программа подбирает уставку аппарата защиты для каждого автомата, если расчётный ток линии меньше номинала защиты. Учитываются коэффициенты совместной установки и метод выбора сечения кабелей. 
Метод выбора сечения кабелей можно настроить запустив окно настроек Программы.
Однако, если номинал защиты окажется больше расчётного тока (даже на несколько ступеней), то программа не станет его изменять. 
В этом случае около автомата вы увидите небольшой красный восклицательный знак, предупреждающий о том, что номинал автомата завышен.
Пример:
Группа 1 - Номинал защиты 16 А, расчётный ток 38,28 А - Программа автоматически выберет уставку 40 А и запишет её в автомат.
Группа 2 - Номинал защиты 80 А, расчётный ток 38,28 А - Программа не изменит уставку, а оставит её 80 А и покажет красный восклицательный знак у автомата.
ВАЖНО!
Если расчётный ток линии больше максимальной стандартной уставки в 1000 А - программа не выберет для неё номинал, а выдаст соответствующее предупреждение. Остальные расчёты будут проведены корректно.
Номиналы автоматов с которыми работает программа: '10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 700, 800, 900, 1000' А.
Пример:
Группа 3 - Номинал защиты 1000 А, расчётный ток 1050,93 А - Программа выдаёт предупреждения, что номинал более 1000 А не выбирается.

2) Программа выбирает сечения кабелей в соответствии с уставкой аппаратов защиты. (Учитывая коэффициенты совместной прокладки)
Однако если сечение окажется больше минимально необходимого, программа не станет его менять, а оставит прежним. 
В этом случае около кабеля вы увидите небольшой красный восклицательный знак, предупреждающий о том, что сечение кабеля завышено.
Пример:
Группа 4 - Номинал защиты 40 А, сечение 2,5 кв.мм - Программа автоматически выберет сечение 6 кв.мм и запишет его в автомат.
Группа 5 - Номинал защиты 40 А, сечение 25 кв.мм - Программа не изменит сечение, а оставит его равным 25 кв.мм и покажет красный восклицательный знак у кабеля.
ВАЖНО!
Программа работает только с сечениями из следующего списка: '1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400, 500, 630, 800, 1000' кв.мм
Если пользователь ввёл какое-то иное сечение, программа выдаст ошибку и прекратит работу.
ВАЖНО!
Если уставка аппарата защиты введена пользователем вручную и превышает 1143 А (ток для сечения 1000 кв.мм), программа не станет выбирать для него сечение, выдаст соответствующее предупреждение и завершит работу без всяких расчётов.

3) Программа выдаёт предупреждение о превышении потерь в 1,5% для соответствующих групп. При этом все расчёты проводятся и результаты записываются в чертёж корректно. Граничное значение потерь 
можно установить в окне настроек Программы.

4) Программа работает с количеством лучей кабелей в одной линии. Например ВВГнг-LS 2х(5х95). И количестовм жил для линии. Например ВВГнг-LS 4х95, ВВГнг-LS 5(1х240) или ВВГнг-LS 2х5(1х16).
Количество жил проставляется автоматически равным 3 или 5 при соответствующем напряжении 230 и 400 В (также программа работаетс напряжениями 220 и 380 В).
Однако, если пользователь ввёл вручную количество жил 4 - то при напряжении 400 В программа оставит это значение, не переписав его на 5 жил.
Если же пользователь ввёл количество жил 1 - то программа также не перезапишет его независимо ни от какого напряжения.
Кроме того, программа работает с отдельными PE проводниками, например: ВВГнг-LS 4х95+1х50. Подбор сечения отдельного проводника происходит в соответствии с п.1.7.126 ПУЭ.
Если количество проводников PE для автомата выставлено 1 и более, а количество жил или количество проводников основной линии при этом больше 4, то программа остановит работу, предупредив
пользователя о том, что такого быть не может. 
Пример 1:
Было: ВВГнг-LS 5х2.5, номинал защиты 16 А.
При расчётах ток получился равным 34 А.
Стало: ВВГнг-LS 5х16, номинал защиты 63 А.

Пример 2:
Было: ВВГнг-LS 2х4(1х2.5)+1х2.5, номинал защиты 16 А.
При расчётах ток получился равным 179 А.
Стало: ВВГнг-LS 2х4(1х95)+1х95, номинал защиты 200 А.

5) Программа выбирает условный проход труб до 50 мм. Выбор проходит только если есть значения в параметре Способ прокладки. Если же этот параметр пуст, то и условный проход программа поставит пустым.
Принцип подбора следующий:
сечения от 1,5 до 2,5 кв.мм включительно - 20 мм;
сечение 4 кв.мм - 25 мм;
сечение от 6 до 10 кв.мм включительно - 32 мм;
сечение от 16 до 25 кв.мм включительно - 50 мм;
для сечений 35 и более кв.мм - в параметр условного прохода не будет записано ничего (пустая строка). Подразумевается, что такие большие сечения уже не прокладываются в трубах, а только на лотках или полках.
Способ прокладки п. или т. (в ПВХ или стальной трубе) выбирается пользователем. Однако для сечений 35 и более кв.мм этот параметр очищается (автоматически записывается пустая строка).
Если был какой-то автомат, у которого сечение было больше 35 кв.мм, и поля 'Способ прокладки' и 'Условный проход' были не заполнены,
затем пользователь вручную уменьшил сечение (25 и менее кв.мм), то программа запишет диаметр условного прохода, 
однко способ прокладки записан не будет. Его нужно будет записать вручную.
Если пользователь удалил Способ прокладки (очистил параметр), то условный проход также не будет записан.

6) Программа рассчитывает квартирные стояки. 
Для того чтобы включился расчёт квартирного стояка у семейства 'GA_SHM_2D автоматический выключатель_ВРУ' нужно выставить флажок параметра 'Квартирный стояк'.
После этого нужно заполнить параметры 'Количество квартир 1 (2,3)' и 'Расчётная мощность одной квартиры (кВт) 1 (2,3)'. Допускается питание трёх разных типов квартир (по мощности) от одного стояка.
Например 'Количество квартир 1' = 65, 'Расчётная мощность одной квартиры (кВт) 1' = 10, 'Количество квартир 2' = 23, 'Расчётная мощность одной квартиры (кВт) 1' = 12.
После запуска программы будет произведён расчёт согласно СП 256.1325800.2016. Выбранные удельные нагрузки или коэффициенты спроса квартир будут автоматически записаны в параметры 'Рр.уд. (кВт) или Ко 1 (2,3)',
подробный расчёт запишется в параметр 'Пояснение расчёта квартир'.

7) Программа рассчитывает распределённые потери если найдёт в параметре "Наименование электроприёмника" часть строки из списка Volt_Dropage_key (сейчас это ['ОСВЕЩ', 'СВЕТ']).
Volt_Dropage_key задаётся в окне настроек Программы.
Распределённые потери пока что получаются простым делением потерь пополам.
Пример:
Группа 1: В параметре наименование электроприёмника написано: "Рабочее освещение лестничной клетки в подвале и на 1-м этаже". Программа найдёт часть строки "ОСВЕЩ" и разделит потери данной группы пополам.
Группа 2: В параметре наименование электроприёмника написано: "Указатель номера дома и пожарного гидранта". Программа не найдёт совпадений 'ОСВЕЩ' или 'СВЕТ' и посчитает всю нагрузку на конце линии.

8) Программа учитывает понижающие коэффициенты для совместной прокладки кабелей по ГОСТ Р 50571.5.52-2011, а также коэффициенты одновременности автоматических выключателей установленных 
совместно (ГОСТ 32397-2013, ГОСТ 32396-2013). Совместная прокладка кабелей и совместно установленные аппараты защиты считаются по параметру "Принадлежность щиту". 
Для автоматов с номиналом более 63 А программа не вводит понижающие коэффициенты, т.к. считает, что это автоматы в литом корпусе, на которые не распространяется действие понижающих
коэффициентов. Пояснения по выбору понижающих коэффициентов автоматов и кабелей можно автоматически записать в отдельное семейство "GA_SHM_Понижающие коэффициенты.rfa".
Делается это так:
 - обводим автоматы которые хотим просчитать;
 - выбираем вместе с ними и семейство "GA_SHM_Понижающие коэффициенты.rfa";
 - видим подробную расшифровку какие коэффициенты и для чего выбраны.

Пример:
В панели РП1.1 установлено 24 автоматических выключателя. У каждого в параметре "Принадлежность щиту" стоит значение "РП1.1". Программа посчитает, что все эти автоматы установлены рядом, 
а отходящие кабели проложены совместно. Будут выбраны коэффициенты: 0,68 для кабелей и 0,5 для автоматических выключателей.
ВАЖНО!
При незаполненном параметре "Принадлежность щиту" программа не будет вводить никакие понижающие коэффициенты.

9) Программа автоматически записывает количество полюсов и количество модулей в каждый автомат.

10) Программа работает с медными и алюминиевыми проводниками.
Определение типа проводника происходит по параметру "Марка проводника". Если она начинается с буквы "А" (не важно кириллицей, латиницей, заглавной или строчной), 
то программа считает что это алюминиевый проводник.

Пример:
ВВГнг-LS 3х10 - медный кабель АВВГнг-LS 3х10 - алюминиевый кабель.



11) С версии 8.8 добавилась возможность выбора сечения кабелей не только по токам, но и по потерям. 
Граничное значение потерь по умолчанию выставлено 2 % (см. Настройки программы). При превышении этого значения в расчётах схем Программа автоматически будет подбирать большие сечения, 
пока значение потерь не станет меньше или равным 2 %. 
Если для каких-то конкретных групп вы хотите превысить граничное значение потерь, вам следует зайти в окно "Потери по группам" Настроек Программы. 
В нём можно выставить любое значение потерь для отдельных групп. Оно останется неизменным при расчётах схем, сечение под него подбираться не будет.
Вы также можете снять флажок "Выбирать сечение кабеля по потерям". В этом случае Программа будет выдавать предупреждение о превышении потерь выше граничного значения у соответствующих групп. 
Но повышать сечение не будет. 



12) После каждого расчёта программа выдаёт окно результата расчёта. В нём есть возможность выбрать способ расчёта:

Способ расчёта "Простой":
Рр.общ. = Ру.суммарное * Кс. Сумма установленных мощностей выбранных нагрузок умноженная на итоговый коэффциент спроса (существующий или расчётный).
Если вместе с автоматами в выборку была включена таблица для записи результата, 
то в окне "Результат" будет показан Кс из этой таблицы. Он называется Кс.сущ. Также будет показан расчётный коэффициент спроса (Кс.расч.) - это Рр / Ру. 
Этот коэффициент спроса можно изменить вручную и перезаписать в таблицу результата расчёта.

Способ расчёта "Жилой дом":
Рр.ж.д = Ркв + 0,9 * Рс (п.7.1.10 СП 256.1325800). Расчёт нагрузок жилого дома. Учитываются коэффициенты спроса квартир и лифтов.
Чтобы использовать этот спопсоб необходимо заранее назаначить значения параметра "Классификация нагрузок" у автоматов. Значения должны быть следующими:
"Лифты" - для автоматов питающих лифтовое оборудование.
"Квартиры" или "Апартаменты" - для автоматов питающих жилые квартиры.
Вся остальная нагрузка просуммируется в отдельное слагаемое Рс. Например: Рр.ж.д = Ркв*nкв*Ко + 0,9*(Ру.л*Кс.л + Рс)
Запись результата происходит в семейства "Расчётная таблица для схем/щитов". Параметр "Пояснение" при этом перезаписывается при каждом расчёте.

Способ расчёта "С коэффициентами спроса":
Рр.общ. = Рр + Рр1 * Кс1 + ... + Ррn * Ксn. Расчёт в соответствии с классификацией нагрузок.
В данной версии учитываются только коэффициенты спроса на лифты и квартиры. Вся остальная нагрузка просуммируется в отдельное слагаемое Рс. 
Например: Рр = Рр + Ру.л*Кс.л. + Ркв*nкв*Ко.
Чтобы использовать этот спопсоб необходимо заранее назаначить значения параметра "Классификация нагрузок" у автоматов. Значения должны быть следующими:
"Лифты" - для автоматов питающих лифтовое оборудование.
"Квартиры" или "Апартаменты" - для автоматов питающих жилые квартиры.
Подходит также для расчёта пожарных режимов ВРУ жилого дома (т.к. не вводит коэффициент 0,9 на силовую нагрузку жилого дома).










ПРОВЕРИТЬ случай если выбран кабель 3-ВВГнг 1х2,5, например. То есть однофазный одножильный. Кажется я этого не предусмотрел.
Потом добавить проверку если у квартирных стояков заполнено несколько параметров Расчётная мощность одной квартиры (кВт) ... но они по 10 кВт (то есть обычные квартиры). Так быть не должно, расчёт будет неправильный.




Для понимания о кабелях:
ВВГнг-LS 2х3(1х240)
тут первая цифра это параметр 'Количество лучей', вторая 'Количество проводников', третья 'Количество жил'
если просто ВВГнг-LS 5х25
то тут первая цифра 'Количество жил'

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
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.ApplicationServices import Application
import System.Drawing
import System.Windows.Forms
from System.Windows.Forms import *
from System.Drawing import *
import sys
clr.AddReference('RevitAPIUI') # подгружаем библиотеку для набора Autodesk.Revit.UI.Selection
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import ObjectType
# Библиотеки ExtensibleStorage
import System.Runtime.InteropServices
from Autodesk.Revit.DB.ExtensibleStorage import *
from Autodesk.Revit.DB.ExtensibleStorage import *
from System import Guid # you need to import this, when you work with Guids!
from System.Collections.Generic import *
import math



#doc = __revit__.ActiveUIDocument.Document
#uidoc = __revit__.ActiveUIDocument


#Создадим список с именами семейств с которыми работает программа - разлочить при тестировании в Python Shell. А так получаем на входе от C#
'''
avt_family_names = ['TSL_2D автоматический выключатель_ВРУ', 'TSL_2D автоматический выключатель_Щит']
calculated_tables_family_names = ['TSL_Таблица_Расчетная для схемы', 'TSL_Таблица_Расчетная для щитов']
Note_table_family_name = ['TSL_Понижающие коэффициенты']
using_any_avtomats = ['TSL_Вводной автомат для щитов', 'TSL_Любой автомат для схем'] # все автоматы не относящиеся к семействам из списка avt_family_names
using_reserve_avtomats = ['TSL_Резервный автомат для ВРУ', 'TSL_Резервный автомат для щитов'] # резервные автоматы
using_auxiliary_cables = ['TSL_Кабель', 'TSL_Кабель с текстом 1.8']
# А также имена параметров семейств с которыми работает программа:
Param_Py = 'Py'
Param_Kc = 'Kc'
Param_Pp = 'Pp'
Param_Cosf = 'Cosf'
Param_Ip = 'Ip'
Param_Sp = 'Sp'
Param_Upit = 'Напряжение'
Param_Cable_length = 'Длина проводника'
Param_Accessory = 'Принадлежность щиту'
Param_Circuit_number = 'Номер цепи'
Param_Cable_section = 'Сечение проводника'
Param_Circuit_breaker_nominal = 'Уставка аппарата'
Param_Voltage_drop = 'Потери'
Param_Moment = 'Момент'
Param_Wire_brand = 'Марка проводника'
Param_PE_section = 'Сечение проводника PE'
Param_3phase_CB = '3-фазный аппарат'
Param_Flat_type_1 = 'Кол-во квартир 1 типа'
Param_Flat_type_2 = 'Кол-во квартир 2 типа'
Param_Flat_type_3 = 'Кол-во квартир 3 типа'
Param_Flat_type_4 = 'Кол-во квартир 4 типа'
Param_Flat_type_5 = 'Кол-во квартир 5 типа'
Param_Flat_type_6 = 'Кол-во квартир 6 типа'
Param_PpPv_Flat_type_1 = 'Рр или Рвыд одной квартиры 1 типа (кВт)'
Param_PpPv_Flat_type_2 = 'Рр или Рвыд одной квартиры 2 типа (кВт)'
Param_PpPv_Flat_type_3 = 'Рр или Рвыд одной квартиры 3 типа (кВт)'
Param_PpPv_Flat_type_4 = 'Рр или Рвыд одной квартиры 4 типа (кВт)'
Param_PpPv_Flat_type_5 = 'Рр или Рвыд одной квартиры 5 типа (кВт)'
Param_PpPv_Flat_type_6 = 'Рр или Рвыд одной квартиры 6 типа (кВт)'
Param_Laying_Method = 'Способ прокладки'
Param_Internal_pipe_diameter = 'Условный проход'
Param_Wires_quantity = 'Количество жил'
Param_Module_quantity = 'Кол-во модулей'
Param_Pole_quantity = 'Кол-во полюсов'
Param_Visibility_Knife_switch = 'Рубильник'
Param_Visibility_Circuit_breaker = 'Автоматический выключатель'
Param_Visibility_RCCB = 'Дифф.автомат'
Param_Visibility_RCD = 'УЗО'
Param_Current_breaker_overestimated = 'Номинал защиты больше Ip'
Param_Cab_section_overestimated = 'Сечение больше необходимого'
Param_Electric_receiver_Name = 'Наименование электроприёмника'
Param_Rays_quantity = 'Количество лучей'
Param_Conductor_quantity = 'Количество проводников'
Param_PE_Conductor_quantity = 'Количество проводников PE'
Param_Load_Class = 'Классификация нагрузок'
Param_Explanation = 'Пояснение' # раньше назывался 'Номер ввода'
Param_Breaking_capacity = 'Отключающая способность (кА)'
Param_CB_type = 'Тип аппарата'
Param_CB_characteristic = 'Характеристика аппарата'
Param_Leakage_current = 'Ток утечки УЗО'
Param_Consumers_count = 'Число электроприёмников'
Param_SchSize_Height = 'Высота (мм)'
Param_SchSize_Width = 'Ширина (мм)'
Param_SchSize_Depth = 'Глубина (мм)'
Param_SpecifyByName = 'Выписывать по наименованию'
Param_TypeLeakage_current = 'Тип тока утечки'
Param_ADSK_product_code = 'ADSK_Код изделия'
Param_Short_Circuit_3ph = 'Ток КЗ 3ф (кА)' 
Param_Short_Circuit_1ph = 'Ток КЗ 1ф (кА)'
Param_IdQFsCalc = 'Id расчётных аппаратов'
Param_ReducedWireLength = "Длина проводника приведённая"


# По какой откл. способности выбирать автоматы?
Way_ofselecting_Breaking_capacity = 'Icn' # может быть одно из Icn, Icu, Ics


# Переменные отвечающие за соединение с хранилищем имён параметров (4-е хранилище Настроек Тэслы)
Guidstr_Param_Names_Storage = '44bf8d44-4a4a-4fde-ada8-cd7d802648c4'
SchemaName_for_Param_Names_Storage = 'Param_Names_Storage'
FieldName_for_Param_Names_Storage = 'Param_Names_Storage_list'


# Переменные отвечающие за соединение с ExtensibleStorage
Guidstr = 'c94ca2e5-771e-407d-9c09-f62feb4448b6'
FieldName_for_Tesla_settings = 'Tesla_settings_list'
Cable_section_calculation_method_for_Tesla_settings = 'Cable_section_calculation_method'
Volt_Dropage_key_for_Tesla_settings = 'Volt_Dropage_key'
DeltaU_boundary_value_for_Tesla_settings = 'deltaU_boundary_value'
Round_value_for_Tesla_settings = 'Round_value_ts'
Require_tables_select_for_Tesla_settings = 'Require_tables_select_ts'
Select_Cable_by_DeltaU_for_Tesla_settings = 'Select_Cable_by_DeltaU_ts'
flat_calculation_way_for_Tesla_settings = 'flat_calculation_way_ts'
Distributed_Volt_Dropage_koefficient_for_Tesla_settings = 'Distributed_Volt_Dropage_koefficient'

# Необходимые данные для соединения со вторым хранилищем (где храним инфу о распределённых потерях)
Guidstr_Distributed_volt_dropage_Tesla_settings = '64261417-f3b0-4156-9db2-5c2fd1fd2059'
SchemaName_for_Distributed_volt_dropage_Tesla_settings = 'Distributed_volt_dropage_Tesla_settings_Storage'
FieldName_for_Distributed_volt_dropage_Tesla_settings = 'Distributed_volt_dropage_Tesla_settings_list' # отдельное поле для хранения информации о распределённых потерях

# Необходимые данные для соединения с третьим хранилищем (Calculation Resourses (CR)) (где хранятся исходные данные для расчётов)
Guidstr_CR = 'c96a640d-7cf1-47dd-bd1d-1a938122227f' # был раньше такой: '9c2310f8-4930-49d6-837c-d8307a356bbc'
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



# Необходимые данные для соединения с Хранилищами данных по производителю
# Необходимые данные для соединения с хранилищем автоматов
Guidstr_AV_ListDB_ManufacturerSelect = 'b9081bd1-6c79-478d-8ac0-9af54da5b8a0'
SchemaName_for_AV_ListDB_ManufacturerSelect = 'AV_ListDB_ManufacturerSelect_Storage'
FieldName_for_AV_ListDB_ManufacturerSelect = 'AV_ListDB_ManufacturerSelect_list' # отдельное поле для хранения информации обо всех автоматах

# В этом списке пусть 0-й элемент - это тот производитель который сейчас выбран пользователем для проекта
# Необходимые данные для соединения с хранилищем Имён производителей
Guidstr_ManufNames_ManufacturerSelect = 'd17eba7e-01db-4c04-ad54-3a73437731d1'
SchemaName_for_ManufNames_ManufacturerSelect = 'ManufNames_ManufacturerSelect_Storage'
FieldName_for_ManufNames_ManufacturerSelect = 'ManufNames_ManufacturerSelect_list' # отдельное поле для хранения информации имён производителей


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


# Данные для соединения с хранилищем настроек Выбора производителя (9 хранилище)
Guidstr_ManufacturerSettings = '8a3c4aad-74f6-46b2-b685-d17cd7c53a6b'
SchemaName_for_ManufacturerSettings = 'ManufacturerSettings_SchemaName'
FieldName_for_ManufacturerSettings = 'ManufacturerSettings_FieldName'


fam_param_names = ['ADSK_Единица измерения', 'ADSK_Завод-изготовитель', 'ADSK_Наименование', 'ADSK_Обозначение']
# для понимания соответствия: fam_param_names[0] fam_param_names[1] fam_param_names[2]  fam_param_names[3] 



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



# Сделать окно RPS модальным:
#TaskDialog.Show('название окна', 'ara')

#____________________________________________________


#!!!!!!!!!!!!!!!!!!!СДЕЛАТЬ МОДУЛЬ ПО ЗАПИСИ МАКС. ОТКЛ. СПОСОБНОСТИ АВТОМАТИЧЕСКИ В ЗАВИСИМОСТИ ОТ ТОКОВ КЗ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!



# Из C# мы получаем списки с конкретным типом данных string. И почему-то к таким спискам нельзя применять некоторые команды, например .count(i.Name)
# поэтому для корректной работы придётся пересобрать все входящие списки заново. Для этого нужен вспомогательный список CS_help = []
CS_help = []
[CS_help.append(i) for i in avt_family_names]
avt_family_names = []
[avt_family_names.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in calculated_tables_family_names]
calculated_tables_family_names = []
[calculated_tables_family_names.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in using_any_avtomats]
using_any_avtomats = []
[using_any_avtomats.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in using_reserve_avtomats]
using_reserve_avtomats = []
[using_reserve_avtomats.append(i) for i in CS_help]
CS_help = []
[CS_help.append(i) for i in fam_param_names]
fam_param_names = []
[fam_param_names.append(i) for i in CS_help]







#_________Перевод на другие языки______________________________

TelsaLanguage = 'EN'
TelsaLanguage = 'RU'


if TelsaLanguage == 'RU':
	# Перевод DifferentAlertsForm
	DifferentAlertsForm_selfText_texttrans = 'Предупреждение' # название формы
	# Перевод ExtensibleStorage
	AvcountsComandName_texttrans = 'Расчёт схем'

	AvcountsESalerttext_texttrans = 'Имена параметров с которыми работает спецификация не были найдены в Настройках Программы.\n Будут использованы имена параметров по умолчанию.\nЧтобы избежать появления этого предупреждения - откройте Настройки Программы и нажмите "Сохранить и закрыть".'

	error_text_in_window1_texttrans = 'Ничего не выбрано. Пожалуйста выберите автоматы среди которых будет произведён расчёт. А также, если угодно, и табличку для записи результатов расчётов.'
	error_text_in_window2_1_texttrans = 'Вы не выбрали автоматические выключатели для расчёта. Программа работает только с определёнными семействами автоматических выключателей: '
	error_text_in_window2_2_texttrans = '. Пожалуйста, выберите их и запустите программу заново.'

	wrong_avt_family_names_texttrans_1 = 'Внимание! Среди выбранных семейств есть семейства с неправильными именами:\n'
	wrong_avt_family_names_texttrans_2 = '.\nОни будут исключены из расчётов!'
	wrong_avt_family_names_texttrans_3 = 'Предупреждение'

	# Хранилище настроек Тэслы
	schemaGuid_for_Tesla_settings_texttrans_1 = 'Невозможно найти настройки программы.\nЗначения настроек будут использованы по умолчанию.\nДля исправления этой ошибки откройте Настройки Программы.'
	Exception_newversion_texttrans = 'С выходом новой версии программы добавились новые настройки.\nЗапустите сначала кнопку "Настройки" для корректной работы.'

	#если не выбраны таблички результатов расчётов и примечания
	Require_tables_select_texttrans_1 = 'Вы не выбрали семейство для записи результатов расчётов, а также семейство примечаний к расчётам: "'
	Require_tables_select_texttrans_2 = '". Пожалуйста добавьте эти семейства в выборку и перезапустите программу.'
	Require_tables_select_texttrans_3 = 'Вы не выбрали одно из семейств для записи результатов расчётов: "'
	Require_tables_select_texttrans_4 = '" или "'
	Require_tables_select_texttrans_5 = 'Вы не выбрали семейство примечаний к расчётам: "'
	Require_tables_select_texttrans_6 = '". Пожалуйста добавьте это семейство в выборку и перезапустите программу.'

	elems_calculation_table_texttrans = 'Выберите только одну таблицу для записи результатов. Сейчас выбрано несколько таблиц.'

	Distributed_volt_dropage_Tesla_settings_texttrans_1 = 'Настройки'
	Distributed_volt_dropage_Tesla_settings_texttrans_2 = 'Данные о значениях распределённых потерь не были найдены.\nРаспределённые потери не будут учтены.\nДля исправления этой ошибки откройте Настройки Программы.'

	CR_texttrans_1 = 'Настройки'
	CR_texttrans_2 = 'Исходные данные для расчётов не найдены или были повреждены.\n Будут использованы исходные данные по умолчанию.'

	Avcounts_Dif_texttrans_1 = 'У следующих автоматов уставка отсутствует в списке уставок с которыми работает программа. Id элементов: '
	Avcounts_Dif_texttrans_2 = '. Список уставок: '
	Avcounts_Dif_texttrans_3 = '. Измените уставки в соответствии со списком уставок вручную или добавьте недостающие значение уставок в настройки программы.'
	Avcounts_Dif_texttrans_4 = 'У следующих автоматов и кабелей сечение отсутствует в списке сечений проводников с которыми работает программа. Id элементов: '
	Avcounts_Dif_texttrans_5 = '. Список сечений: '
	Avcounts_Dif_texttrans_6 = '. Измените сечения в соответствии со списком сечений вручную или добавьте недостающие значение сечений в настройки программы.'

	Avcounts_Dif_texttrans_7 = 'без принадлежности'
	Avcounts_Dif_texttrans_8 = 'Кол-во модулей в НКУ: '

	Avcounts_Dif_texttrans_9 = 'У автоматического выключателя Id:'
	Avcounts_Dif_texttrans_10 = ' некорректный параметр "'
	Avcounts_Dif_texttrans_11 = '". Обновите семейство до последней версии и перезапустите расчёт.'
	Avcounts_Dif_texttrans_12 = 'У автоматического выключателя "'
	Avcounts_Dif_texttrans_13 = '" отсутствуют параметры "'

	Avcounts_Dif_texttrans_14 = 'В одном из квартирных стояков 10-киловаттная квартира записана два раза. Каждая мощность квартир должна встречаться только один раз для каждого квартирного стояка.'
	Avcounts_Dif_texttrans_15 = 'В одном из квартирных стояков есть несоответствие мощностей и количества квартир одного и того же типа.\nЕсли мощность какого-то типа квартир = 0, то и количество таких квартир должно быть = 0. И наоборот.\nРасчёт прерван, проверьте правильность заполнения этих параметров.'

	Avcounts_Dif_texttrans_16 = 'Рр.кв. = '
	Avcounts_Dif_texttrans_17 = 'Рр.уд. (кВт) или Ко ' # !!! ОТСЛЕДИТЬ ПРИ ПЕРЕИМЕНОВАНИИ ПАРАМЕТРОВ НА АНГЛИЙСКОМ
	Avcounts_Dif_texttrans_18 = ' кВт'

	Avcounts_Dif_texttrans_19 = 'У группы: '
	Avcounts_Dif_texttrans_20 = ' количество лучей меньше нуля. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_21 = ' количество проводников меньше нуля или больше пяти. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_22 = ' количество жил меньше нуля или больше пяти. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_23 = ' количество проводников больше 1, при этом и количество жил больше 1 - чего быть не может. При количестве проводников больше 1, количество жил всегда должно быть равным 1. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_24 = 'Группа '
	Avcounts_Dif_texttrans_25 = ' трёхфазная. Однако вы выбрали одножильный кабель и указали количество таких кабелей: '
	Avcounts_Dif_texttrans_26 = '. Такого быть не может. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_27 = ' что-то не так с количеством жил. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.'
	Avcounts_Dif_texttrans_28 = 'У одной или нескольких групп сечение кабеля не соответствует списку: '
	Avcounts_Dif_texttrans_29 = ' (кв.мм). Программа работает только с сечениями из этого списка. Никакие данные не были записаны в чертёж. Пожалуйста выберите сечения из этого списка и перезапустите расчёт.'

	Avcounts_Dif_texttrans_30 = '\nКоэффициенты одновременности аппаратов выбраны по ГОСТ 32397;\nпонижающие коэффициенты совместной прокладки кабелей по ГОСТ Р 50571.5.52.'
	Avcounts_Dif_texttrans_31 = '\nКоэффициенты одновременности аппаратов выбраны по ГОСТ 32397.'
	Avcounts_Dif_texttrans_32 = '\nПонижающие коэффициенты совместной прокладки кабелей по ГОСТ Р 50571.5.52.'

	Avcounts_Dif_texttrans_33 = ' расчётный ток больше стандартной уставки аппарата защиты в '
	Avcounts_Dif_texttrans_34 = ' А. Номинал аппарата защиты не выбран! Его нужно выбрать вручную. Остальные группы посчитаны корректно.'

	NoManufactirer_texttrans = '(нет производителя)'

	Avcounts_Dif_texttrans_35 = 'Кабель '
	Avcounts_Dif_texttrans_36 = ' является установочным или контрольным и не может быть использован в качестве силового. Выберите другую марку кабеля для силовой трассы.'
	Avcounts_Dif_texttrans_37 = 'У одной или нескольких групп сечение кабеля не найдено у выбранного производителя: '
	Avcounts_Dif_texttrans_38 = ' (кв.мм). Выберите другую марку кабеля или отключите подбор Производителя кабелей и задайте нужное сечение в Настройках Программы. Никакие данные не были записаны в чертёж.'

	Avcounts_Dif_texttrans_39 = 'Для группы '
	Avcounts_Dif_texttrans_40 = ' невозможно подобрать сечение, т.к. сечений пропускающих указанный в линии ток нет в Исходных данных для расчёта (кнопка "Настройки"). Остальные группы посчитаны корректно.'
	Avcounts_Dif_texttrans_41 = ' номинал аппарата защиты больше '
	Avcounts_Dif_texttrans_42 = ' А. Сечение кабеля для этой группы не выбрано! Его нужно выбрать вручную. Остальные группы посчитаны корректно.'
	Avcounts_Dif_texttrans_43 = ' невозможно подобрать сечение, т.к. сечений пропускающих указанный в линии ток нет в Исходных данных для расчёта (кнопка "Настройки"). Остальные группы посчитаны корректно.'
	Avcounts_Dif_texttrans_44 = 'Следующие марки кабелей не были найдены у выбранного производителя: '
	Avcounts_Dif_texttrans_45 = '. Расчётные данные для них были взяты из общих Настроек.'
	Avcounts_Dif_texttrans_46 = ' невозможно подобрать сечение кабеля в соответвии с коэффициентами одновременности при совместной прокладке кабельных линий. Это произошло потому что необходимо сечение большее ' 
	Avcounts_Dif_texttrans_47 = ' кв.мм с которым работает программа. Сечение кабеля для этой группы выбрано без учёта коэффициента совместной прокладки! Остальные группы посчитаны корректно.'

	Avcounts_Dif_texttrans_48 = 'Для следующих групп не удалось подобрать сечение по потерям, т.к. кончился список возможных сечений, а потери по-прежнему более граничного значения: '
	Avcounts_Dif_texttrans_49 = '\nДля следующих групп потери были рассчитаны как распределённые:\n'
	Avcounts_Dif_texttrans_50 = 'У следующих автоматических выключателей потери превышают '

	Avcounts_Dif_texttrans_51 = 'В процессе расчёта схем возникли следующие предупреждения:'

	Avcounts_Dif_texttrans_52 = 'Расчёт выполнен. Данные записаны в аппараты.'

	Avcounts_Dif_texttrans_53 = 'У автоматического выключателя Id:'
	Avcounts_Dif_texttrans_54 = ' некорректный параметр "'
	Avcounts_Dif_texttrans_55 = '". Обновите семейство до последней версии и перезапустите расчёт.'

	Avcounts_Dif_texttrans_56 = 'В выборке присутствуют автоматы питания лифтов с одинкавыми номерами групп. Для корректного расчёта итога номера групп должны быть различными. Переименуйте группы и перезапустите расчёт. Имена повторяющихся групп : '
	Avcounts_Dif_texttrans_57 = '. Результаты расчёта не записаны в итоговую табличку.'

	KsElevatorsForm_texttrans_1 = 'Укажите этажность работы лифтов (в таблице указаны группы питания лифтов)'
	KsElevatorsForm_texttrans_2 = 'До 12 этажей'
	KsElevatorsForm_texttrans_3 = '12 эт. и выше'
	KsElevatorsForm_texttrans_4 = 'Кс лифтов'

	KcForm_texttrans_1 = "Py, [кВт] ="
	KcForm_texttrans_2 = "Kc"
	KcForm_texttrans_3 = "Kc.сущ. ="
	KcForm_texttrans_4 = "Kc.расч. ="
	KcForm_texttrans_5 = "Pp, [кВт] ="
	KcForm_texttrans_6 = "Ip, [А] ="
	KcForm_texttrans_7 = "Напряжение"
	KcForm_texttrans_8 = "230 [В]"
	KcForm_texttrans_9 = "400 [В]"
	KcForm_texttrans_10 = "Записать"
	KcForm_texttrans_11 = "Рассчитать"
	KcForm_texttrans_12 = "Способ расчёта"
	KcForm_texttrans_13 = "Жилой дом (рабочий режим)"
	KcForm_texttrans_14 = "Простой"
	KcForm_texttrans_15 = "Жилой дом (режим при пожаре)"
	KcForm_texttrans_16 = "Пользовательский"
	KcForm_texttrans_17 = "Результат"
	KcForm_texttrans_18 = 'Введённое значение должно быть числом с разделителем целой и дробной частей в виде точки.'
	KcForm_texttrans_19 = " [В]"
	KcForm_texttrans_20 = 'Коэффициент спроса содержащийся в семействе таблички результатов расчёта'
	KcForm_texttrans_21 = 'Коэффициент спроса расчётный: Рр / Ру\nМожно ввести значение вручную'
	KcForm_texttrans_22 = 'Рр.общ. = Ру.суммарное * Кс\nСумма установленных мощностей выбранных нагрузок умноженная на итоговый коэффциент спроса\n(существующий или расчётный)'
	KcForm_texttrans_23 = 'Рр.ж.д = Кп.к. * Ркв + 0,9 * Рс (п.7.1.10 СП 256.1325800)\nРасчёт нагрузок жилого дома. Учитываются коэффициенты спроса квартир и лифтов.'
	KcForm_texttrans_24 = 'Рр.ж.д. = Кп.к. * Ркв + Рс\nРасчёт нагрузок жилого дома при пожаре (не вводится 0,9 на силовую нагрузку).'
	KcForm_texttrans_25 = 'Расчёт по формулам, созданным в Редакторе формул.'






elif TelsaLanguage == 'EN':
	# Перевод DifferentAlertsForm
	DifferentAlertsForm_selfText_texttrans = 'Notification' # название формы
	# Перевод ExtensibleStorage
	AvcountsComandName_texttrans = 'Schemes calculation'
	AvcountsESalerttext_texttrans = 'The parameter names that the specification works with were not found in the Program Options.\n Default parameter names will be used.\nTo avoid this warning, open the Program Options and click Save and Close.'

	error_text_in_window1_texttrans = 'Nothing is selected. Please select the circuit breakers among which the calculation will be made. And a plate for recording the results of calculations if you wish.'
	error_text_in_window2_1_texttrans = 'You have not selected circuit breakers for calculation. The program works only with certain families of circuit breakers: '
	error_text_in_window2_2_texttrans = '. Please select them and restart the program.'

	wrong_avt_family_names_texttrans_1 = 'Attention! There are families with incorrect names among the selected families:\n'
	wrong_avt_family_names_texttrans_2 = '.\nThey will be excluded from the calculations.!'
	wrong_avt_family_names_texttrans_3 = 'Notification'

	# Хранилище настроек Тэслы
	schemaGuid_for_Tesla_settings_texttrans_1 = 'Unable to find program settings.\nSetting values will be used by default.\nTo correct this error, open Program Settings.'
	Exception_newversion_texttrans = 'With the release of the new version of the program, new settings have been added.\nFirst launch the "Settings" button for correct operation.'

	#если не выбраны таблички результатов расчётов и примечания
	Require_tables_select_texttrans_1 = 'You have not selected a family for recording results of calculations, as well as a family of notes to calculations:"'
	Require_tables_select_texttrans_2 = '". Please add these families to the selection and restart the program.'
	Require_tables_select_texttrans_3 = 'You have not selected one of the families to record the calculation results: "'
	Require_tables_select_texttrans_4 = '" or "'
	Require_tables_select_texttrans_5 = 'You have not selected an analysis note family: "'
	Require_tables_select_texttrans_6 = '". Please add this family to the selection and restart the program.'

	elems_calculation_table_texttrans = 'Choose only one table to record the results. Several tables are now selected.'

	Distributed_volt_dropage_Tesla_settings_texttrans_1 = 'Settings'
	Distributed_volt_dropage_Tesla_settings_texttrans_2 = 'No distributed loss data was found.\nDistributed loss will not be taken into account.\nTo correct this error, open the Program Settings.'

	CR_texttrans_1 = 'Settings'
	CR_texttrans_2 = 'The source data for calculations was not found or was corrupted.\n The default source data will be used.'

	Avcounts_Dif_texttrans_1 = 'For the following circuit breakers, the current rating is not in the list of current ratings with which the program works. Element IDs: '
	Avcounts_Dif_texttrans_2 = '. Current ratings list: '
	Avcounts_Dif_texttrans_3 = '. Change the current rating according to the current ratings list manually or add the missing current ratings to the program settings.'
	Avcounts_Dif_texttrans_4 = 'The following circuit breakers and cables have no section in the list of conductor sections with which the program works. Element IDs: '
	Avcounts_Dif_texttrans_5 = '. Conductor sections list: '
	Avcounts_Dif_texttrans_6 = '. Change the sections according to the list of sections manually or add the missing section values to the program settings.'

	Avcounts_Dif_texttrans_7 = 'without belonging'
	Avcounts_Dif_texttrans_8 = 'Number of modules in the low voltage distribution switchboard: '

	Avcounts_Dif_texttrans_9 = 'Circuit breaker Id:'
	Avcounts_Dif_texttrans_10 = ' has an invalid parameter "'
	Avcounts_Dif_texttrans_11 = '". Update the family to the latest version and restart the calculation.'
	Avcounts_Dif_texttrans_12 = 'Circuit breaker "'
	Avcounts_Dif_texttrans_13 = '" has no required parameters "'

	Avcounts_Dif_texttrans_14 = 'In one of the apartment risers, a 10-kilowatt apartment was recorded twice. Each apartment allocated power must occur only once for each apartment riser.'
	Avcounts_Dif_texttrans_15 = 'There is a discrepancy between the apartment allocated powers and the number of apartments of the same type in one of the apartment risers.\nIf the apartment allocated power of some type of apartments = 0, then the number of such apartments should also be = 0. And vice versa.\nCalculation is interrupted, check the correctness of filling these parameters.'

	Avcounts_Dif_texttrans_16 = 'P_rated.apts = '
	Avcounts_Dif_texttrans_17 = 'Р_rated_densit. (kW) or simultaneity factor '
	Avcounts_Dif_texttrans_18 = ' kW'

	Avcounts_Dif_texttrans_19 = 'Electrical circuit: '
	Avcounts_Dif_texttrans_20 = ' has the number of rays less than zero. No data has been written to the drawing. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_21 = ' has the number of conductors less than zero or more than five. No data has been written to the drawing. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_22 = ' has the number of conductive cores less than zero or more than five. No data has been written to the drawing. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_23 = ' has the number of conductors greater than 1, while the number of conductive cores is greater than 1 - it is a mistake. If the number of conductors is greater than 1, the number of conductive cores must always be 1. No data has been written to the drawing. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_24 = 'Electrical circuit '
	Avcounts_Dif_texttrans_25 = ' is three-phased. However, you have selected a single-core cable and entered the number of such cables: '
	Avcounts_Dif_texttrans_26 = '. It is a mistake. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_27 = ' has something wrong with the number of conductive cores. No data has been written to the drawing. Check this group manually and restart the calculation.'
	Avcounts_Dif_texttrans_28 = 'One or more of electrical circuits has a cable cross section that does not match the list: '
	Avcounts_Dif_texttrans_29 = ' (sq.mm). The program works only with sections from this list. No data has been written to the drawing. Please select sections from this list and restart the calculation.'

	Avcounts_Dif_texttrans_30 = '\nThe simultaneity factors of the devices are selected according to GOST 32397 (Distribution boards for industrial and social buildings. General specifications);\nthe reduction coefficients for the joint laying of cables are according to GOST R 50571.5.52. (Low-voltage electrical installations. Part 5-52. Selection and installation of electrical equipment - Wiring systems)'
	Avcounts_Dif_texttrans_31 = '\nThe simultaneity factors of the devices are selected according to GOST 32397 (Distribution boards for industrial and social buildings. General specifications)'
	Avcounts_Dif_texttrans_32 = '\nthe reduction coefficients for the joint laying of cables are according to GOST R 50571.5.52. (Low-voltage electrical installations. Part 5-52. Selection and installation of electrical equipment - Wiring systems)'

	Avcounts_Dif_texttrans_33 = ' has rated current greater than the standard rated currents list of the protection device: '
	Avcounts_Dif_texttrans_34 = ' A. The rating of the protection device is not selected! It must be selected manually. The rest of the electrical circuits were calculated correctly.'

	NoManufactirer_texttrans = '(no vendor)'

	Avcounts_Dif_texttrans_35 = 'Cable '
	Avcounts_Dif_texttrans_36 = ' is installation cable or control cable and cannot be used as a power cable. Select a different brand of cable for the power line.'
	Avcounts_Dif_texttrans_37 = 'For one or more electrical circuits, the cable section was not found for the selected vendor: '
	Avcounts_Dif_texttrans_38 = ' (sq.mm). Please select a different brand of cable or disable the selection of the Cable vendor and set the desired cross section in the Program Settings. No data has been written to the drawing.'

	Avcounts_Dif_texttrans_39 = 'For the electrical circuit '
	Avcounts_Dif_texttrans_40 = ' it is impossible to choose a section, because cross-sections passing the current specified in the electrical circuit are not in the Initial data for calculation ("Settings" button). The remaining electrical circuits are calculated correctly.'
	Avcounts_Dif_texttrans_41 = ' has the rating of protection device greater than '
	Avcounts_Dif_texttrans_42 = ' A. No cable cross section selected for this electrical circuit! It must be selected manually. The rest of the electrical circuits were calculated correctly.'
	Avcounts_Dif_texttrans_43 = ' it is impossible to choose a section, because cross-sections passing the current specified in the electrical circuit are not in the Initial data for calculation ("Settings" button). The remaining electrical circuits are calculated correctly.'
	Avcounts_Dif_texttrans_44 = 'The following cable brands were not found from the selected vendor: '
	Avcounts_Dif_texttrans_45 = '. The calculated data for them was taken from the General Settings.'
	Avcounts_Dif_texttrans_46 = ' it is impossible to select the cable cross-section in accordance with the simultaneity coefficients when laying cable lines together. This happened because a larger cross section is needed then '
	Avcounts_Dif_texttrans_47 = ' sq. mm with which the program works. The cable cross-section for this electrical circuit was chosen without taking into account the joint laying coefficient! The remaining electrical circuits are calculated correctly.'

	Avcounts_Dif_texttrans_48 = 'For the following electrical circuits, it was not possible to select a cross section for voltage drops, since the list of possible sections has ended, and the voltage drops are still more than the boundary value: '
	Avcounts_Dif_texttrans_49 = '\nFor the following electrical circuits, voltage drops were calculated as distributed:\n'
	Avcounts_Dif_texttrans_50 = 'The following circuit breakers have more voltage drops than '

	Avcounts_Dif_texttrans_51 = 'The following warnings occurred during schema calculation:'

	Avcounts_Dif_texttrans_52 = 'Calculation completed. The data has been written to the devices.'

	Avcounts_Dif_texttrans_53 = 'Circuit breaker Id:'
	Avcounts_Dif_texttrans_54 = ' has an invalid parameter "'
	Avcounts_Dif_texttrans_55 = '". Update the family to the latest version and restart the calculation.'

	Avcounts_Dif_texttrans_56 = 'There are elevator feeders with the same electrical circuits numbers in the sample. For the correct calculation of the total result, the electrical circuits numbers must be different. Please rename the electrical circuits and restart the calculation. Repeated electrical circuits names : '
	Avcounts_Dif_texttrans_57 = '. The results of the calculation are not recorded in the result table.'

	KsElevatorsForm_texttrans_1 = 'Indicate the number of floors of the elevators (the table shows the power supply electrical circuits of the elevators)'
	KsElevatorsForm_texttrans_2 = 'Below 12 floors'
	KsElevatorsForm_texttrans_3 = '12 floor and above'
	KsElevatorsForm_texttrans_4 = 'Elevators demand factor'

	'''
	Ру - true load, true power, Pt
	Рр - rated power, Pr
	Кс - demand facor, Df
	Sр - apparent power, Sa
	cosf - power factor, cosf
	Iр - rated current, Ir
	Рр.общ. - Pr.total
	Ру.суммарное - Pt.summary
	Рр.ж.д - Pr.residental
	Кп.к. - Df.low.apts.
	Ркв - Papts
	Рс - P
	'''

	KcForm_texttrans_1 = "Pt, [kW] ="
	KcForm_texttrans_2 = "Df"
	KcForm_texttrans_3 = "Df.exsist. ="
	KcForm_texttrans_4 = "Df.rated. ="
	KcForm_texttrans_5 = "Pr, [kW] ="
	KcForm_texttrans_6 = "Ir, [A] ="
	KcForm_texttrans_7 = "Voltage"
	KcForm_texttrans_8 = "230 [V]"
	KcForm_texttrans_9 = "400 [V]"
	KcForm_texttrans_10 = "Write"
	KcForm_texttrans_11 = "Calculate"
	KcForm_texttrans_12 = "Calculation method"
	KcForm_texttrans_13 = "Residential (normal mode)"
	KcForm_texttrans_14 = "Simple"
	KcForm_texttrans_15 = "Residential (fire mode)"
	KcForm_texttrans_16 = "Custom"
	KcForm_texttrans_17 = "Result"
	KcForm_texttrans_18 = 'The entered value must be a number with a decimal separator as a dot.'
	KcForm_texttrans_19 = " [V]"
	KcForm_texttrans_20 = 'Demand factor contained in the calculation results table family'
	KcForm_texttrans_21 = 'Demand coefficient calculated: Pr / Pt\nYou can enter the value manually'
	KcForm_texttrans_22 = 'Pr.total = Pt.summary * Df\nThe sum of the installed capacities of the selected loads multiplied by the final demand factor\n(existing or estimated)'
	KcForm_texttrans_23 = 'Pr.residental = Df.low.apts. * Papts + 0,9 * P (п.7.1.10 Electrical equipment of residential and public buildings. Rules of design and erection 256.1325800)\nCalculation of loads of a residential building. Demand factors for apartments and elevators are taken into account.'
	KcForm_texttrans_24 = 'Pr.residental = Df.low.apts. * Papt + P\nCalculation of the loads of a residential building in case of fire (0.9 is not entered for the power load).'
	KcForm_texttrans_25 = 'Calculation by formulas created in the Formula Editor.'


#__________________________________________________________________________________________________________________________________________

































#___________Функции необходимые для работы программы________________________________________________________________________________________________

# Функция поиска элементов списка строк в строке (используется для определения классификации нагрузок)
# На входе: список который будем искать в строке, строка в которой ищем. Например: List_in_string (['flat', 'apartament'], 'flats') выдаст True
# На выходе: True если найдено совпадение, False если не найдено.
def List_in_string (input_list, input_string):
	# Сразу преобразуем всё в верхний регистр
	input_list = [i.upper() for i in input_list]
	input_string = input_string.upper()
	for i in input_list:
		if i in input_string:
			resbool = True
			break
		else:
			resbool = False
	return resbool
	




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


'''
# функция получения индексов одинаковых элементов в списке
# на входе: элемент который ищем, список в котором ищем. На выходе список с индексами найденных элементов. Например: [2, 4]. Если совпадений не найдено - на выходе пустой список: []
def Get_coincidence_in_list (search_element, search_list):
	index_list = []
	for n, i in enumerate(search_list):
		if i == search_element:
			index_list.append(n)
	return index_list
'''

# функция получения индексов одинаковых элементов в подсписках списка
# на входе: элемент который ищем, позиция искомого элемента в подсписках основного списка, список в подсписках которого ищем. На выходе список с индексами найденных элементов. Например: [2, 4]. Если совпадений не найдено - на выходе пустой список: []
def Get_coincidence_in_sublist (search_element, position_in_sub_lists, search_list):
	index_list = []
	for n, i in enumerate(search_list):
		if i[position_in_sub_lists] == search_element:
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



# Функция по определению материала проводника.
# Определяемся какой проводник используется: медный или алюминиевый. Al примем если марка кабеля начинается с буквы "А". В остальных случая медный..
# Пример обращения: Is_Cu_or_Al(elems_avtomats[0], Param_Wire_brand)
# На выходе из функции True если медь, False если алюминий
def Is_Cu_or_Al (element_in_elems_avtomats, Param_Wire_brand):
	wirebrandstr = element_in_elems_avtomats.LookupParameter(Param_Wire_brand).AsString()
	if wirebrandstr[0] == 'А' or wirebrandstr[0] == 'а' or wirebrandstr[0] == 'A' or wirebrandstr[0] == 'a':
		exitbool = False
	else:
		exitbool = True
	return exitbool	






# Окошко для всяких предупреждений.
class DifferentAlertsForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._DifferentAlertsForm_label1 = System.Windows.Forms.Label()
		self._DifferentAlertsForm_textBox1 = System.Windows.Forms.TextBox()
		self._DifferentAlertsForm_OKbutton = System.Windows.Forms.Button()
		self.SuspendLayout()
		# 
		# DifferentAlertsForm_label1
		# 
		self._DifferentAlertsForm_label1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._DifferentAlertsForm_label1.Location = System.Drawing.Point(13, 13)
		self._DifferentAlertsForm_label1.Name = "DifferentAlertsForm_label1"
		self._DifferentAlertsForm_label1.Size = System.Drawing.Size(387, 40)
		self._DifferentAlertsForm_label1.TabIndex = 0
		self._DifferentAlertsForm_label1.Text = "label1"
		# 
		# DifferentAlertsForm_textBox1
		# 
		self._DifferentAlertsForm_textBox1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._DifferentAlertsForm_textBox1.Location = System.Drawing.Point(13, 56)
		self._DifferentAlertsForm_textBox1.Multiline = True
		self._DifferentAlertsForm_textBox1.Name = "DifferentAlertsForm_textBox1"
		self._DifferentAlertsForm_textBox1.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
		self._DifferentAlertsForm_textBox1.Size = System.Drawing.Size(387, 118)
		self._DifferentAlertsForm_textBox1.TabIndex = 1
		# 
		# DifferentAlertsForm_OKbutton
		# 
		self._DifferentAlertsForm_OKbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._DifferentAlertsForm_OKbutton.Location = System.Drawing.Point(169, 184)
		self._DifferentAlertsForm_OKbutton.Name = "DifferentAlertsForm_OKbutton"
		self._DifferentAlertsForm_OKbutton.Size = System.Drawing.Size(75, 23)
		self._DifferentAlertsForm_OKbutton.TabIndex = 2
		self._DifferentAlertsForm_OKbutton.Text = "OK"
		self._DifferentAlertsForm_OKbutton.UseVisualStyleBackColor = True
		self._DifferentAlertsForm_OKbutton.Click += self.DifferentAlertsForm_OKbuttonClick
		# 
		# DifferentAlertsForm
		# 
		self.ClientSize = System.Drawing.Size(412, 216)
		self.Controls.Add(self._DifferentAlertsForm_OKbutton)
		self.Controls.Add(self._DifferentAlertsForm_textBox1)
		self.Controls.Add(self._DifferentAlertsForm_label1)
		self.Name = "DifferentAlertsForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = DifferentAlertsForm_selfText_texttrans
		self.Load += self.DifferentAlertsFormLoad
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell

	def DifferentAlertsForm_OKbuttonClick(self, sender, e):
		self.Close()


	def DifferentAlertsFormLoad(self, sender, e):
		self.ActiveControl = self._DifferentAlertsForm_OKbutton # ставим фокус на кнопку ОК чтобы по Enter её быстро нажимать
		self._DifferentAlertsForm_label1.Text = DifferentAlerts_TextForLabel
		self._DifferentAlertsForm_textBox1.Text = DifferentAlerts_TextFortextBox

#________________________________________________________________________________________________________________________________




#________Объявляем коэффициенты спроса___________________________________________________________________

# получаем объект "информация о проекте"
ProjectInfoObject = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ProjectInformation).WhereElementIsNotElementType().ToElements()[0] 


schemaGuid_for_Kc_Storage = System.Guid(Guidstr_Kc_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
#Получаем Schema:
sch_Kc_Storage = Schema.Lookup(schemaGuid_for_Kc_Storage)
# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch_Kc_Storage) будет <type 'NoneType'>
if sch_Kc_Storage is None or ProjectInfoObject.GetEntity(sch_Kc_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	# Объявляем табличные данные по умолчанию:
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
else:
	# Считываем данные из Хранилища
	Kc_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_Kc_Storage, ProjectInfoObject)
	# Переобъявляем считанные данные
	Kkr_flats_koefficient = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_1) + 1)]] # Обращение к содержимому по имени поля.
	Flat_count_SP = [int(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_2) + 1)]]
	Flat_unit_wattage_SP = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_3) + 1)]]
	Py_high_comfort = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_4) + 1)]]
	Ks_high_comfort = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_5) + 1)]]
	Flat_count_high_comfort = [int(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_6) + 1)]]
	Ko_high_comfort = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_7) + 1)]]
	Kcpwrres = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_8) + 1)]]
	Elevator_count_SP = [int(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_9) + 1)]]
	Ks_elevators_below12 = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_10) + 1)]]
	Ks_elevators_above12 = [float(i) for i in Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_11) + 1)]]
	Load_Class_elevators = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_12) + 1)]
	Load_Class_falts = Kc_Storage_DataList[int(Kc_Storage_DataList.index(FieldName_for_Kc_13) + 1)] # [u'КВАРТИР', u'АПАРТАМЕНТ']

Kcpwrres = Kcpwrres[0] # Этот у нас дальше в коде не списком а цифрой идёт. Вот и переобъявим его.
Kkr_flats_koefficient = Kkr_flats_koefficient[0] # Этот у нас дальше в коде не списком а цифрой идёт. Вот и переобъявим его.








#___________Достаём имена параметров из хранилища________________________________________________________________________________
schemaGuid_for_Param_Names_Storage = System.Guid(Guidstr_Param_Names_Storage) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!

# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch_Param_Names_Storage = Schema.Lookup(schemaGuid_for_Param_Names_Storage)

# Внутренние (только для этой программы) названия параметров:
Param_name_0_for_Param_Names_Storage = 'Param_name_0_for_Param_Names_Storage'
Param_name_1_for_Param_Names_Storage = 'Param_name_1_for_Param_Names_Storage'
Param_name_2_for_Param_Names_Storage = 'Param_name_2_for_Param_Names_Storage'
Param_name_3_for_Param_Names_Storage = 'Param_name_3_for_Param_Names_Storage'
Param_name_17_for_Param_Names_Storage = 'Param_name_17_for_Param_Names_Storage'

# Если ExtensibleStorage с указанным guid'ом отсутствует, то type(sch_Param_Names_Storage) будет <type 'NoneType'>
if sch_Param_Names_Storage is None or ProjectInfoObject.GetEntity(sch_Param_Names_Storage).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то создадим хранилище.
	TaskDialog.Show(AvcountsComandName_texttrans, AvcountsESalerttext_texttrans)
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

	# Переназначим список fam_param_names из Хранилища
	fam_param_names = []

	fam_param_names = [znachParams[int(znachParams.index(Param_name_0_for_Param_Names_Storage) + 1)],
	znachParams[int(znachParams.index(Param_name_1_for_Param_Names_Storage) + 1)],
	znachParams[int(znachParams.index(Param_name_2_for_Param_Names_Storage) + 1)],
	znachParams[int(znachParams.index(Param_name_3_for_Param_Names_Storage) + 1)]]

	try:
		Param_ADSK_product_code = znachParams[int(znachParams.index(Param_name_17_for_Param_Names_Storage) + 1)]
	except ValueError:
		TaskDialog.Show(AvcountsComandName_texttrans, AvcountsESalerttext_texttrans)


















# Строка для вывода предупреждений, возникающих в процессе работы программы
CabSecAlertString = ''


#______________Выбор элементов пользователем________________________________________________________________________________________

''' создаём выборку. Пользователь выбирает нужные элементы'''
ids = uidoc.Selection.GetElementIds()
idd = [str(i) for i in ids]
# Если пользователь до запуска программы ничего не выбрал, то предложим ему выбрать после запуска программы
if len(ids) == 0:
	pickedObjs = uidoc.Selection.PickObjects(ObjectType.Element, "Выберите автоматические выключатели и расчётную табличку")
	idd = [str(i.ElementId) for i in pickedObjs]


#сообщение об ошибке которое должно вывестись в следующем модуле
error_text_in_window = error_text_in_window1_texttrans # задаётся в начале в зависимости от языка программы
#если ничего не выбрано, выйти из программы
if idd == []: 
	raise Exception(error_text_in_window)
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
elems_avtomats = [] # все автоматы которые участвуют в электротехнических расчётах
elems_any_avtomats = [] # вводной автомат и любой автомат для схем (им прописываем только кол-во полюсов и модулей)
elems_reserve_avtomats = [] # резервные автоматы (для ВРУ и щитов) (им прописываем только кол-во полюсов и модулей)
elems_auxiliary_cables = [] # семейства кабелей (отдельные). Пока введены только для проверки соответствия сечений с Настройками. В расчётах не участвуют.

for element in elems:
	if element.Name in avt_family_names: elems_avtomats.append(element)
	elif element.Name in using_any_avtomats: elems_any_avtomats.append(element)
	elif element.Name in using_reserve_avtomats: elems_reserve_avtomats.append(element)
	elif element.Name in using_auxiliary_cables: elems_auxiliary_cables.append(element)


#сообщение об ошибке которое должно вывестись в следующем модуле
error_text_in_window = error_text_in_window2_1_texttrans + ', '.join(avt_family_names) + error_text_in_window2_2_texttrans



#если не выбраны основные автоматы, выйти из программы
if elems_avtomats == []: 
	raise Exception(error_text_in_window)
	#MessageBox.Show(error_text_in_window, 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	#sys.exit()

# Вытащим себе Idшники автоматов на основании которых проводится расчёт (для записи потом в итоговую табличку в параметр с Id)
Ids_elems_avtomats = [] # Вид: ['772377', '772401', '772403']

for i in elems_avtomats:
	try: # для Ревитов до 2025 включительно
		Ids_elems_avtomats.append(str(i.Id.IntegerValue))
	except: # для 2026 Ревита
		Ids_elems_avtomats.append(str(i.Id.Value))

# И сделаем строчку для записи этих айдишников через точку с запятой
Str_Ids_elems_avtomats = ';'.join(Ids_elems_avtomats) # Вид: '772377;772401;772403'

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
	MessageBox.Show(wrong_avt_family_names_texttrans_1 + '", "'.join(wrong_avt_family_names) + wrong_avt_family_names_texttrans_2, wrong_avt_family_names_texttrans_3, MessageBoxButtons.OK, MessageBoxIcon.Exclamation)







#_________________________________Работаем с Хранилищем настроек Тэслы__________________________________________________________
# Проверяем связь с настройками Тэслы. Если ExtensibleStorage с гуидом Guidstr присутствет в проекте, берём значения переменных оттуда.
# Если такого хранилища нет, выдадим предупреждение и выставим значения переменных по умолчанию.
schemaGuid_for_Tesla_settings = System.Guid(Guidstr) # Этот guid не менять! Он отвечает за ExtensibleStorage настроек!
# Сначала проверяем создано ли ExtensibleStorage у категории OST_ProjectInformation
#Для того, чтобы считать записанную информацию, нужно получить элемент модели, знать GUID хранилища и имена параметров.
#Получаем Schema:
sch = Schema.Lookup(schemaGuid_for_Tesla_settings)
if sch is None or ProjectInfoObject.GetEntity(sch).IsValid() == False: # Проверяем есть ли ExtensibleStorage
	TaskDialog.Show(AvcountsComandName_texttrans, schemaGuid_for_Tesla_settings_texttrans_1) # Показывает окошко в стиле Ревит
	# Предложим пользователю возможность выбора сечений кабелей (делается в проге "Настройки Тэслы"). Либо по току уставки автомата, либо по току срабатывания автоматов с учётом коэффициентов совместной установки.
	Cable_section_calculation_method = 0 # 1 - если сечение выбирается по уставке автомата, 0 - если по расчётному току линии.
	Volt_Dropage_key = ['ОСВЕЩ', 'СВЕТ'] # всё что будет найдено из этого списка, будет рассчитано с распределёнными потерями (то есть потери пополам)
	deltaU_boundary_value = 2 # Будет выдаваться предупреждение при превышении потерь относительно этой цифры
	Round_value_ts = 1 # округление до 1-го знака после запятой
	Require_tables_select_ts = 1 # требовать выбора табличек результата и примечаний
	Select_Cable_by_DeltaU_ts = 1 # маркер из настроек программы. Выбирать ли кабель по граничному значению потерь. 1 - да, выбирать; 0 - нет, не выбирать.
	flat_calculation_way_ts = 0 # Переменная из хранилища. Если равна 1, то считается Ко для каждого типа квартир отдельно. Если равна 0, то считается Ко сразу для общего количества квартир.
	Distributed_Volt_Dropage_koefficient = 1 / 0.5
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
	if len(znach) < 22: # Вот эту цифру и будем менять здесь в коде при добавлении новых настроек Тэслы
		raise Exception(Exception_newversion_texttrans)
		#TaskDialog.Show('Расчёт схем', 'С выходом новой версии программы добавились новые настройки.\n Запустите сначала кнопку "Настройки" для корректной работы.')
		#sys.exit()
	# Присваиваем значения переменным в соответствии с информацией полученной из хранилища
	Cable_section_calculation_method = int(znach[int(znach.index(Cable_section_calculation_method_for_Tesla_settings) + 1)]) # поясняю: находим значение самой переменной на следующей (+1) позиции за именем самой переменной в списке из хранилища
	Volt_Dropage_key = znach[int(znach.index(Volt_Dropage_key_for_Tesla_settings) + 1)].split('\r\n')
	deltaU_boundary_value = float(znach[int(znach.index(DeltaU_boundary_value_for_Tesla_settings) + 1)])	
	Round_value_ts = int(znach[int(znach.index(Round_value_for_Tesla_settings) + 1)])
	Require_tables_select_ts = int(znach[int(znach.index(Require_tables_select_for_Tesla_settings) + 1)])
	Select_Cable_by_DeltaU_ts = int(znach[int(znach.index(Select_Cable_by_DeltaU_for_Tesla_settings) + 1)])
	flat_calculation_way_ts = int(znach[int(znach.index(flat_calculation_way_for_Tesla_settings) + 1)])
	Distributed_Volt_Dropage_koefficient = 1 / float(znach[int(znach.index(Distributed_Volt_Dropage_koefficient_for_Tesla_settings) + 1)]) # из настроек нам приходит цифра десятичная (например 0.5), а дальше в коде нам нужно делить потери на целое число (например / 2). Поэтому мы и делаем тут 1 / 0.5 (например)





#делаем ещё список с табличками для записи результатов расчётов по всему щитку
elems_calculation_table = []	
for element in elems:
	if element.Name in calculated_tables_family_names: elems_calculation_table.append(element)


#делаем ещё список с семействами примечаний
elems_note_table = []	
for element in elems:
	if element.Name in Note_table_family_name: elems_note_table.append(element)


#если не выбраны таблички результатов расчётов и примечания, а в Настройках установлен флажок "Требовать выбора", выйти из программы
if Require_tables_select_ts == 1:
	if elems_calculation_table == [] and elems_note_table == []: 
		raise Exception(Require_tables_select_texttrans_1 + '", "'.join(calculated_tables_family_names) + '", ' + '", "'.join(Note_table_family_name) + Require_tables_select_texttrans_2)
	elif elems_calculation_table == [] and elems_note_table != []: 
		raise Exception(Require_tables_select_texttrans_3 + Require_tables_select_texttrans_4.join(calculated_tables_family_names) + Require_tables_select_texttrans_2)
	elif elems_calculation_table != [] and elems_note_table == []: 
		raise Exception(Require_tables_select_texttrans_5 + '", "'.join(Note_table_family_name) + Require_tables_select_texttrans_6)


if len(elems_calculation_table) > 1: 
	raise Exception(elems_calculation_table_texttrans)



# MessageBox.Show('Вы не выбрали семейство примечаний к расчётам: "' + '", "'.join(Note_table_family_name) + '". Пожалуйста добавьте это семейство в выборку и перезапустите программу.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)





# ________________________________Работаем с Хранилищем данных о распределённых потерях____________________________________________________

# Guid для этого хранилища
schemaGuid_for_Distributed_volt_dropage_Tesla_settings = System.Guid(Guidstr_Distributed_volt_dropage_Tesla_settings)

#Получаем Schema:
schDeltaU = Schema.Lookup(schemaGuid_for_Distributed_volt_dropage_Tesla_settings)

# Проверяем корректность хранилища
if schDeltaU is None or ProjectInfoObject.GetEntity(schDeltaU).IsValid() == False:
	TaskDialog.Show(Distributed_volt_dropage_Tesla_settings_texttrans_1, Distributed_volt_dropage_Tesla_settings_texttrans_2)
	GroupsAndNamesFor_Distributed_volt_dropage_from_Storage = []

else: # Если с Хранилищем всё в порядке, считываем данные оттуда
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
	GroupsAndNamesFor_Distributed_volt_dropage_from_Storage = []
	for i in znach1:
		GroupsAndNamesFor_Distributed_volt_dropage_from_Storage.append([i.partition('?!?')[0], i.partition('?!?')[2].partition('?!?')[0], i.partition('?!?')[2].partition('?!?')[2]])
	

# Итак, получили список - имя группы, наим.электропр., значение распр. потерь из Хранилища:
# GroupsAndNamesFor_Distributed_volt_dropage_from_Storage - [['M-1', u'освещение приквартирного коридора', '0'], ['M-2', u'освещение приквартирного коридора', '2.3'], ['M-3', u'освещение лифтовых холлов', '0'], ['M-4', u'васька', '1.1'], [u'ЩРВ-1', u' .1', '0'], [u'ЩРВ-2', u' .2', '0']]
# Причём этот список будет пустым если нет данных из Хранилища.





# ________________________________Работаем с Хранилищем исходных данных Calculation Resourses (CR)____________________________________________________

# Guid для этого хранилища
schemaGuid_for_CR = System.Guid(Guidstr_CR)

#Получаем Schema:
schCR = Schema.Lookup(schemaGuid_for_CR)

# Если ExtensibleStorage с указанным guid'ом отсутствет, то type(sch) будет <type 'NoneType'>
if schCR is None or ProjectInfoObject.GetEntity(schCR).IsValid() == False: # Проверяем есть ли ExtensibleStorage. Если ExtensibleStorage с указанным guid'ом отсутствет, то примем значения по умолчанию.
	TaskDialog.Show(CR_texttrans_1, CR_texttrans_2)

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
	Current_breaker_nominal_DB = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 700, 800, 900, 1000, 3200]
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
	U3f = 400
	U1f = 230
	



	#___________________________________________________________________________________________________________________
else: # Если с Хранилищем всё в порядке, считываем данные оттуда
	# Считываем данные из Хранилища
	CRF_Storage_DataList = Read_all_fields_to_ExtensibleStorage (schemaGuid_for_CR, ProjectInfoObject)
	Sections_of_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)]] # поясню: это обращение к содержимому списка по имени поля в хранилище
	Currents_for_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_2) + 1)]]
	Currents_for_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_3) + 1)]]
	Currents_for_singlewire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_4) + 1)]]
	Currents_for_singlewire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_5) + 1)]]
	Current_breaker_nominal_DB =  [int(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_6) + 1)]]
	Cables_trays_reduction_factor_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_7) + 1)]]
	Circuit_breakers_reduction_factor_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_8) + 1)]]
	VoltageDrop_Coefficiets_Knorr_ES = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_9) + 1)]]
	Cmed3f = VoltageDrop_Coefficiets_Knorr_ES[0]
	Cmed1f = VoltageDrop_Coefficiets_Knorr_ES[1]
	Cal3f = VoltageDrop_Coefficiets_Knorr_ES[2]
	Cal1f = VoltageDrop_Coefficiets_Knorr_ES[3]
	Currents_for_1phase_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_10) + 1)]]
	Currents_for_1phase_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_11) + 1)]]
	U3f = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_12) + 1)]][0]
	U1f = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_12) + 1)]][1]


# Данные для расчёта тока:
U3fsqrt3forI = math.sqrt(3) * U3f * 0.001
U1fforI = U1f * 0.001


elems_avts_for_pole_and_module = elems_avtomats + elems_any_avtomats + elems_reserve_avtomats # сумма трёх список выбранных автоматов

# Проверим, что уставки автоматов и сечения кабелей в выборке присутствуют в настройках с которыми работает программа. Иначе вылетает бага.
Ids_without_CB = [] # список с айдишниками автоматов чьей уставки нет в списке уставок из настроек
Ids_without_section = [] # список с айдишниками автоматов чьего сечение нет в списке сечений из настроек
for i in elems_avtomats + elems_auxiliary_cables:
	if i.LookupParameter(Param_Cable_section).AsDouble() not in Sections_of_cables_DB:
		Ids_without_section.append(str(i.Id))

for i in elems_avts_for_pole_and_module:
	if i.LookupParameter(Param_Circuit_breaker_nominal).AsDouble() not in Current_breaker_nominal_DB:
		Ids_without_CB.append(str(i.Id))		

strforexept = '' # строка для вывода ошибки
if Ids_without_CB != []:
	strforexept = strforexept + Avcounts_Dif_texttrans_1 + ', '.join(Ids_without_CB) + Avcounts_Dif_texttrans_2 + ', '.join([str(j) for j in Current_breaker_nominal_DB]) + Avcounts_Dif_texttrans_3
if Ids_without_section != []:
	strforexept = strforexept + Avcounts_Dif_texttrans_4 + ', '.join(Ids_without_section) + Avcounts_Dif_texttrans_5 + ', '.join([str(j) for j in Sections_of_cables_DB]) + Avcounts_Dif_texttrans_6
if strforexept != '':
	raise Exception(strforexept)






# MessageBox.Show(strforexept, 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)






#___________________________________________Модуль по вычислению количества полюсов и модулей автоматов________________________________________________________________________________________________________________________

# Создадим список со всеми необходимыми данными для вычисления кол-ва полюсов и модулей. Структура списка:
#[[Id элемента 1, Напряжение 1 (1-если 3 фазы, 0-если 1 фаза), Внешний вид элемента 1 (рубильник, УЗО и пр.), принадлежность элемента 1, вычисленное кол-во модулей 1, вычисленное кол-во полюсов 1, ] .....   ]
pole_and_module_list = []
for i in elems_avts_for_pole_and_module:
	curlist = [] # вспомогательный список. текущий подсписок большого списка
	curlist.append(str(i.Id)) # пишем айдишник
	curlist.append(i.LookupParameter(Param_3phase_CB).AsInteger()) # пишем напряжение элемента (1-если 3 фазы, 0-если 1 фаза)
	if Param_Visibility_Knife_switch in [p.Definition.Name for p in i.Parameters] and i.LookupParameter(Param_Visibility_Knife_switch).AsInteger() == 1: # если этот параметр есть в семействе AND флажок выставлен (равен единице)
		curlist.append(Param_Visibility_Knife_switch) # пишем что это рубильник
	elif Param_Visibility_Circuit_breaker in [p.Definition.Name for p in i.Parameters] and i.LookupParameter(Param_Visibility_Circuit_breaker).AsInteger() == 1:  
		curlist.append(Param_Visibility_Circuit_breaker) # пишем что это Автоматический выключатель
	elif Param_Visibility_RCCB in [p.Definition.Name for p in i.Parameters] and i.LookupParameter(Param_Visibility_RCCB).AsInteger() == 1: 
		curlist.append(Param_Visibility_RCCB) # пишем что это Дифф.автомат
	elif Param_Visibility_RCD in [p.Definition.Name for p in i.Parameters] and i.LookupParameter(Param_Visibility_RCD).AsInteger() == 1: 
		curlist.append(Param_Visibility_RCD) # пишем что это УЗО
	else: 
		curlist.append(Param_Visibility_Circuit_breaker) # если ничего из вышеперечисленного не подошло, то считаем что это автомат
	curlist.append(i.LookupParameter(Param_Accessory).AsString()) # пишем принадлежность
	# вычисляем кол-во модулей и полюсов
	if curlist[1] == 1 and curlist[2] in [Param_Visibility_Knife_switch, Param_Visibility_Circuit_breaker]: # Если напряжение 3-фазное и это рубильник или автомат
		curlist.append(3) # пишем 3 модуля
		if i.LookupParameter(Param_Pole_quantity).AsInteger() < 3: # и если при этом количество полюсов 1 или 2 было
			curlist.append(3) # пишем 3 полюса
		else:
			curlist.append(i.LookupParameter(Param_Pole_quantity).AsInteger()) # оставляем сколько было полюсов
	elif curlist[1] == 0 and curlist[2] in [Param_Visibility_Knife_switch, Param_Visibility_Circuit_breaker]: # Если напряжение 1-фазное и это рубильник или автомат
		curlist.append(1) # пишем 1 модуль
		if i.LookupParameter(Param_Pole_quantity).AsInteger() > 2: # и если при этом количество полюсов 3 или 4 было
			curlist.append(1) # пишем 1 полюс
		else:
			curlist.append(i.LookupParameter(Param_Pole_quantity).AsInteger()) # оставляем сколько было полюсов
	elif curlist[1] == 1 and curlist[2] in [Param_Visibility_RCCB, Param_Visibility_RCD]: # Если напряжение 3-фазное и это Дифф.автомат или УЗО
		curlist.append(4) # пишем 4 модуля
		curlist.append(4) # пишем 4 полюса
	elif curlist[1] == 0 and curlist[2] in [Param_Visibility_RCCB, Param_Visibility_RCD]: # Если напряжение 1-фазное и это Дифф.автомат или УЗО
		curlist.append(2) # пишем 2 модуля
		curlist.append(2) # пишем 2 полюса
	pole_and_module_list.append(curlist)


'''
if int(Unique_AVmodelCodes[n][5]) < 3: # и если при этом количество полюсов 1 или 2 было
	i.LookupParameter(Param_Pole_quantity).Set(3) # пишем 3 полюса

'''




# Открываем группу транзакций
# http://adn-cis.org/primer-ispolzovaniya-grupp-tranzakczij.html
transGroup = TransactionGroup(doc, "AvCounts")
transGroup.Start()




#Записываем нужные нам параметры в каждый элемент
t = Transaction(doc, 'Pole_and_module write down')
t.Start()
for n, i in enumerate(elems_avts_for_pole_and_module):
	for j in pole_and_module_list:
		if str(i.Id) == j[0]:
			i.LookupParameter(Param_Module_quantity).Set(j[4])
			i.LookupParameter(Param_Pole_quantity).Set(j[5])
t.Commit()







# Готовим текст для вывода пользователю. Сколько модулей в каком НКУ у нас получилось. modules_in_boxes_alertstring
modules_in_boxes_alertstring_list = [] # вспомогательный список [[принадлежность НКУ 1, кол-во модулей внутри этого НКУ 1] ...  ]
for i in pole_and_module_list:
	curlist = []
	cur_indx = Get_coincidence_in_sublist (i[3], 3, pole_and_module_list) # получаем индексы совпавших элементов. Например [1, 2]
	if i[3] != '': # если принадлежность заполнена
		curlist.append(i[3]) # пишем принадлежность
	else:
		curlist.append(Avcounts_Dif_texttrans_7) # 'без принадлежности'
	cur_module_count = 0 # количество модулей для текущей принадлежности
	for j in cur_indx:
		cur_module_count = cur_module_count + pole_and_module_list[j][4] # плюсуем количество модулей данной принадлежности
	curlist.append(str(cur_module_count))
	modules_in_boxes_alertstring_list.append(curlist)
	Delete_indexed_elements_in_list (cur_indx, pole_and_module_list) # удаляем совпавшие элементы из списка

# 'Кол-во модулей в НКУ: '
modules_in_boxes_alertstring = Avcounts_Dif_texttrans_8 +    ', '.join([' - '.join(i) for i in modules_in_boxes_alertstring_list]) + '.'

'''
# Это чтобы смотреть что в подсписках с перекодировкой. ПОЛЕЗНО!!
MessageBox.Show('[[' +    '], ['.join([', '.join(i) for i in modules_in_boxes_alertstring_list]) + ']]', 'Справочная информация', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
MessageBox.Show('Кол-во модулей в НКУ: ' +    ', '.join([' - '.join(i) for i in modules_in_boxes_alertstring_list]), 'Справочная информация', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
'''













#___________________________________________Модуль по расчёту квартирных стояков________________________________________________________________________________________________________________________
# Сначала он вписывает Ру, Кс в автомат, а потом уж запускается основной модуль программы
# Достанем из общей выборки только автоматы в которых проставлен флажок "Квартирный стояк"
is_flat_riser = [] # список с автоматами у которых проставлен флажок "Квартирный стояк"

# Проверки квартирных стояков на правильность параметров. Введены чтобы не выскакивали непонятные баги при выходе новых версий.
for i in elems_avtomats:
	try:
		if List_in_string(Load_Class_falts, i.LookupParameter(Param_Load_Class).AsValueString()):
			is_flat_riser.append(i)
	except System.MissingMemberException:
		raise Exception(Avcounts_Dif_texttrans_9 + str(i.Id) + Avcounts_Dif_texttrans_10 + Param_Load_Class + Avcounts_Dif_texttrans_11)
		break

# проверка на три параметра 6-го типа квартир.
for i in is_flat_riser:
	if Param_Flat_type_6 not in [p.Definition.Name for p in i.Parameters] or Param_PpPv_Flat_type_6 not in [p.Definition.Name for p in i.Parameters] or 'Рр.уд. (кВт) или Ко 6' not in [p.Definition.Name for p in i.Parameters]:
		raise Exception(Avcounts_Dif_texttrans_12 + i.Name + Avcounts_Dif_texttrans_13 + Param_Flat_type_6 + '", "' + Param_PpPv_Flat_type_6 + '", "' + 'Рр.уд. (кВт) или Ко 6' + Avcounts_Dif_texttrans_11)



# вытаскиваем нужные нам параметры
Flat_count = [] # список с количествами квартир. Причём если в данном стояке есть квартиры разной мощности,
# то список Flat_count состоит из подсписков с этими мощностями. Например: [[60, 0, 0], [60, 0, 0], [60, 20, 0]]
Flat_Pp_wattage = [] # аналогично формируется список с расчётными мощностями квартир. Например: [[10.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 12.0, 0.0]]
for i in is_flat_riser:
	Flat_count.append([i.LookupParameter(Param_Flat_type_1).AsInteger(), i.LookupParameter(Param_Flat_type_2).AsInteger(), i.LookupParameter(Param_Flat_type_3).AsInteger(), i.LookupParameter(Param_Flat_type_4).AsInteger(), i.LookupParameter(Param_Flat_type_5).AsInteger(), i.LookupParameter(Param_Flat_type_6).AsInteger()])
	Flat_Pp_wattage.append([i.LookupParameter(Param_PpPv_Flat_type_1).AsDouble(), i.LookupParameter(Param_PpPv_Flat_type_2).AsDouble(), i.LookupParameter(Param_PpPv_Flat_type_3).AsDouble(), i.LookupParameter(Param_PpPv_Flat_type_4).AsDouble(), i.LookupParameter(Param_PpPv_Flat_type_5).AsDouble(), i.LookupParameter(Param_PpPv_Flat_type_6).AsDouble()])

# Выдадим предупреждение если 10-киловаттные квартиры встречаются несколько раз. Иначе потом багов не оберёшься.
for i in Flat_Pp_wattage:
	if len(Get_coincidence_in_list(10, i)) > 1:
		raise Exception(Avcounts_Dif_texttrans_14)


# Нужно предупреждение если неправильно заполнены параметры мощностей и количества квартир
# Например для какого-то типа квартир указана мощность, но не указано количество. И наоборот. В этом случае расчёт получается неверным.
wrong_flat_data_counter = 0 # вспомогательный счётчик
for n, i in enumerate(Flat_count):
	for m, j in enumerate(i):
		if Flat_Pp_wattage[n][m] == 0 and j != 0: # Если мощность данного типа квартир =0, а количество данного типа квартир не равно 0
			wrong_flat_data_counter = wrong_flat_data_counter + 1
		if Flat_Pp_wattage[n][m] != 0 and j == 0: # Наоброт: мощность не равна 0, а количество равно 0.
			wrong_flat_data_counter = wrong_flat_data_counter + 1

if wrong_flat_data_counter > 0:
	raise Exception(Avcounts_Dif_texttrans_15)


'''
допустим:
Flat_count
[[35, 21, 33], [57, 0, 0], [42, 0, 0]]
Flat_Pp_wattage
[[8.4000000000000004, 10.0, 15.0], [12.0, 0.0, 0.0], [10.0, 0.0, 0.0]]

'''



# Функция интерполяции
def interpol (x1, x2, x3, y1, y3):
	y2 = ((x2 - x1)*(y3 - y1)) / (x3 - x1) + y1
	return y2



if flat_calculation_way_ts == 1: # способ расчёта - каждый тип квартир со своим Ко
	# Начинаем обсчитывать и записывать квартирные стояки:
	for k, j in enumerate(is_flat_riser):
		Pp_current_riser = 0 # временная переменная. Pp для данного стояка
		Kc_current_riser = 0 # временная переменная. Коэффициент спроса для данного стояка
		Kc_count = 0 # временная переменная. Количество ненулевых значений в параметрах Расчётная мощность одной квартиры (кВт) 1,2,3 для того чтобы вычислить среднее арифметическое по коэффициенту спроса стояка
		# Avcounts_Dif_texttrans_16 это 'Рр.кв. = '
		Calculation_explanation = Avcounts_Dif_texttrans_16 + str(Kkr_flats_koefficient) + '*(' # строка с пояснением расчёта квартир
		for l, m in enumerate(Flat_Pp_wattage[k]):
			if m == 10 and Flat_count[k][l] != 0: # если расчётная мощность одной квартиры 10 кВт и количество квартир не ноль, то...
				for n, i in enumerate(Flat_count_SP):
					if Flat_count[k][l] <= 5 and Flat_count[k][l] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
					elif Flat_count[k][l] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
					elif Flat_count[k][l] > Flat_count_SP[n-1] and Flat_count[k][l] < Flat_count_SP[n]:
						x1 = Flat_count_SP[n-1]
						x2 = Flat_count[k][l]
						x3 = Flat_count_SP[n]
						y1 = Flat_unit_wattage_SP[n-1]
						y3 = Flat_unit_wattage_SP[n]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
					elif Flat_count[k][l] == Flat_count_SP[n]:
						Flat_unit_wattage = Flat_unit_wattage_SP[n]
	#				else:
	#					Flat_unit_wattage = 0
				Pp_current_riser = Pp_current_riser + Flat_count[k][l]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного стояка
				if Flat_unit_wattage != 0:
					t = Transaction(doc, 'Change Flat_unit_wattage')
					t.Start()
					# 'Рр.уд. (кВт) или Ко ' начало имени параметра проследить на английском!!!!!!!!!!
					j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(Flat_unit_wattage) # записываем текущую удельную нагрузку на одну квартиру
					t.Commit()
					Kc_current_riser = Kc_current_riser + 0.8 # добавляем значение текущего коэффициента спроса с общему коэффициенту спроса данного стояка
					Kc_count = Kc_count + 1 # добавляем единицу как очередное ненулевое значение для вычисления среднего арифметического коэффициента спроса стояка
					Calculation_explanation = Calculation_explanation + str(round(Flat_unit_wattage, 4)) + '*' + str(Flat_count[k][l]) + '+'
			elif m != 10 and m > 0 and Flat_count[k][l] != 0: # если расчётная мощность одной квартиры не 10 кВт, и больше нуля то и квартир не ноль штук...
				for n, i in enumerate(Flat_count_high_comfort):
					if Flat_count[k][l] <= 5 and Flat_count[k][l] > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
					elif Flat_count[k][l] > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
					elif Flat_count[k][l] > Flat_count_high_comfort[n-1] and Flat_count[k][l] < Flat_count_high_comfort[n]:
						x1 = Flat_count_high_comfort[n-1]
						x2 = Flat_count[k][l]
						x3 = Flat_count_high_comfort[n]
						y1 = Ko_high_comfort[n-1]
						y3 = Ko_high_comfort[n]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
					elif Flat_count[k][l] == Flat_count_high_comfort[n]:
						Ko_unit_high_comfort = Ko_high_comfort[n]
	#				else:
	#					Ko_unit_high_comfort = 0
				Pp_current_riser = Pp_current_riser + m*Flat_count[k][l]*Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности
				if Ko_unit_high_comfort != 0:
					t = Transaction(doc, 'Change Ko_unit_high_comfort')
					t.Start()
					j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(Ko_unit_high_comfort) # записываем текущий коэфф. одновременности квартир повышенной комфортности
					t.Commit()
					# Вычисляем текущий коэффициент спроса для квартир повышенной комфортности
					Ks_high_comfort_current = 0.8 # пока пусть тоже будет 0,8
					Kc_current_riser = Kc_current_riser + Ks_high_comfort_current # добавляем значение текущего коэффициента спроса с общему коэффициенту спроса данного стояка
					Kc_count = Kc_count + 1 # добавляем единицу как очередное ненулевое значение для вычисления среднего арифметического коэффициента спроса стояка
					Calculation_explanation = Calculation_explanation + str(m) + '*' + str(Flat_count[k][l]) + '*' + str(round(Ko_unit_high_comfort, 4)) + '+'
			elif m == 0 or Flat_count[k][l] == 0: # Если мощность или количество квартир равна нулю (то есть попросту нет квартир), то записать нули и в параметры Рр.уд. (кВт) или Ко 1,2,3
				t = Transaction(doc, 'Change PpandKo')
				t.Start()
				j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(0) # записываем ноль
				t.Commit()		
		'''
		# Вычисляем коэффициент спроса стояка
		Kc_current_riser = Kc_current_riser / Kc_count
		Так я делал раньше, но по просьбе публики, теперь Кс будем брать просто из параметра Кс самого стояка.
		'''
		Kc_current_riser = j.LookupParameter(Param_Kc).AsDouble()

		# Умножаем расчётную мощность стояка на понижающий коэффициент в зависимости от региона
		Pp_current_riser = Kkr_flats_koefficient * Pp_current_riser

		# Убираем плюсик и пробел в конеце строки пояснения
		if len(Calculation_explanation) > 0:
			while '+' == Calculation_explanation[len(Calculation_explanation)-1] or ' ' == Calculation_explanation[len(Calculation_explanation)-1]:
				Calculation_explanation = Calculation_explanation[:-1]

		# Записываем результаты в в квартирный стояк
		t = Transaction(doc, 'Change Flat_unit_wattage')
		t.Start()
		j.LookupParameter(Param_Pp).Set(round(Pp_current_riser, Round_value_ts))
		#j.LookupParameter(Param_Kc).Set(round(Kc_current_riser, 2)) сейчас уже не переписываем Кс
		j.LookupParameter(Param_Py).Set(round(Pp_current_riser/Kc_current_riser, Round_value_ts))
		j.LookupParameter('Пояснение расчёта квартир').Set(Calculation_explanation + ') = ' + str(round(Pp_current_riser, Round_value_ts)) + Avcounts_Dif_texttrans_18)
		t.Commit()

	#Calculation_explanation_numbers = str(Kkr_flats_koefficient) + '*(' # строка с цифровыми пояснением расчёта жилого дома
	#Calculation_explanation_text = 'Рр.ж.д = Кп.к*(' # строка с текстовыми пояснениями расчёта

elif flat_calculation_way_ts == 0: # способ расчёта - все квартиры с общим Ко
	# Начинаем обсчитывать и записывать квартирные стояки:
	for k, j in enumerate(is_flat_riser):
		Pp_current_riser = 0 # временная переменная. Pp для данного стояка
		Kc_current_riser = 0 # временная переменная. Коэффициент спроса для данного стояка
		Ko_unit_high_comfort = 0 # коэффициент одновременности для всех квартир сразу (кроме 10-киловаттных)
		Calculation_explanation = '' # строка с пояснением расчёта квартир
		# теперь нужно просто перемножить каждое количество квартир на каждую мощность, всё это сложить и вычислить Ко для общего количества квартир
		sum_count_of_flats = 0 # временная переменная. Суммарное количество квартир для данного стояка.
		sum_Pp_of_flats = 0 # временная переменная. Суммарная мощность всех квартир данного стояка (арифметическая большая сумма).
		Flat_count_10kVt = '' # вспомогательная переменная. Количество 10-киловаттных квартир. Нужна для формирования пояснения.
		for l, m in enumerate(Flat_Pp_wattage[k]):
			if m == 10 and Flat_count[k][l] > 0: # если расчётная мощность одной квартиры 10 кВт и количество квартир не ноль, то...
				for n, i in enumerate(Flat_count_SP):
					if Flat_count[k][l] <= 5 and Flat_count[k][l] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
						break
					elif Flat_count[k][l] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
						break
					elif Flat_count[k][l] > Flat_count_SP[n-1] and Flat_count[k][l] < Flat_count_SP[n]:
						x1 = Flat_count_SP[n-1]
						x2 = Flat_count[k][l]
						x3 = Flat_count_SP[n]
						y1 = Flat_unit_wattage_SP[n-1]
						y3 = Flat_unit_wattage_SP[n]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
						break
					elif Flat_count[k][l] == Flat_count_SP[n]:
						Flat_unit_wattage = Flat_unit_wattage_SP[n]
						break
				Pp_current_riser = Pp_current_riser + Flat_count[k][l]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного стояка
				if Flat_unit_wattage != 0:
					t = Transaction(doc, 'Change Flat_unit_wattage')
					t.Start()
					j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(Flat_unit_wattage) # записываем текущую удельную нагрузку на одну квартиру
					t.Commit()
					Flat_count_10kVt = str(Flat_count[k][l])

			elif m != 10 and Flat_count[k][l] > 0: # если мощность квартиры не 10 кВт AND количество квартир больше нуля
				sum_count_of_flats = sum_count_of_flats + Flat_count[k][l] # добавляем следующее количество квартир к общему количеству
				sum_Pp_of_flats = sum_Pp_of_flats + m * Flat_count[k][l] # добавляем следующую мощность квартиры к суммарной мощности
				if Calculation_explanation == '': # чтобы скобочка правильно добавлялась
					Calculation_explanation = Calculation_explanation + '('
				elif Calculation_explanation[0] != '(':
					Calculation_explanation = Calculation_explanation + '('
				Calculation_explanation = Calculation_explanation + str(m) + '*' + str(Flat_count[k][l]) + '+'
				for n, i in enumerate(Flat_count_high_comfort):
					if sum_count_of_flats <= 5 and sum_count_of_flats > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
						break
					elif sum_count_of_flats > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
						break
					elif sum_count_of_flats > Flat_count_high_comfort[n-1] and sum_count_of_flats < Flat_count_high_comfort[n]:
						x1 = Flat_count_high_comfort[n-1]
						x2 = sum_count_of_flats
						x3 = Flat_count_high_comfort[n]
						y1 = Ko_high_comfort[n-1]
						y3 = Ko_high_comfort[n]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
						break
					elif sum_count_of_flats == Flat_count_high_comfort[n]:
						Ko_unit_high_comfort = Ko_high_comfort[n]
						break

		Pp_current_riser = Pp_current_riser + sum_Pp_of_flats * Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности
		if Ko_unit_high_comfort != 0: # Пишем Ко во все параметры одинаковый (т.к. по стояку он будет один на все типы квартир)
			t = Transaction(doc, 'Change Ko_unit_high_comfort')
			t.Start()
			j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(Ko_unit_high_comfort) # записываем текущий коэфф. одновременности квартир повышенной комфортности
			t.Commit()
			Calculation_explanation = Calculation_explanation[:-1] # убираем последний плюсик из строки пояснения
			Calculation_explanation = Calculation_explanation + ')*' + str(round(Ko_unit_high_comfort, 4))
		elif m == 0 or Flat_count[k][l] == 0: # Если мощность или количество квартир равна нулю (то есть попросту нет квартир), то записать нули и в параметры Рр.уд. (кВт) или Ко 1,2,3
			t = Transaction(doc, 'Change PpandKo')
			t.Start()
			j.LookupParameter(Avcounts_Dif_texttrans_17 + str(l + 1)).Set(0) # записываем ноль
			t.Commit()	
		Kc_current_riser = j.LookupParameter(Param_Kc).AsDouble()

		# Умножаем расчётную мощность стояка на понижающий коэффициент в зависимости от региона
		Pp_current_riser = Kkr_flats_koefficient * Pp_current_riser

		# Убираем плюсик и пробел в конеце строки пояснения
		if len(Calculation_explanation) > 0:
			while '+' == Calculation_explanation[len(Calculation_explanation)-1] or ' ' == Calculation_explanation[len(Calculation_explanation)-1]:
				Calculation_explanation = Calculation_explanation[:-1]

		# доформировываем строку-пояснение
		# Avcounts_Dif_texttrans_16 это 'Рр.кв. = '
		if Flat_count_10kVt == '':
			Calculation_explanation = Avcounts_Dif_texttrans_16 + str(Kkr_flats_koefficient) + '*(' + Calculation_explanation + ') = ' + str(round(Pp_current_riser, Round_value_ts)) + Avcounts_Dif_texttrans_18
		elif Flat_count_10kVt != '':
			if Calculation_explanation != '':
				Calculation_explanation = Avcounts_Dif_texttrans_16 + str(Kkr_flats_koefficient) + '*(' + str(round(Flat_unit_wattage, 4)) + '*' + Flat_count_10kVt + '+' + Calculation_explanation + ') = ' + str(round(Pp_current_riser, Round_value_ts)) + Avcounts_Dif_texttrans_18
			else:
				Calculation_explanation = Avcounts_Dif_texttrans_16 + str(Kkr_flats_koefficient) + '*(' + str(round(Flat_unit_wattage, 4)) + '*' + Flat_count_10kVt + ') = ' + str(round(Pp_current_riser, Round_value_ts)) + Avcounts_Dif_texttrans_18

		# Записываем результаты в в квартирный стояк
		t = Transaction(doc, 'Change Flat_unit_wattage')
		t.Start()
		j.LookupParameter(Param_Pp).Set(round(Pp_current_riser, Round_value_ts))
		j.LookupParameter(Param_Py).Set(round(Pp_current_riser/Kc_current_riser, Round_value_ts))
		j.LookupParameter('Пояснение расчёта квартир').Set(Calculation_explanation)
		t.Commit()

















#__________________________________________________________________Основной расчётный модуль_____________________________________________________________________________________________________________
	
''' вытаскиваем нужные нам параметры'''

Py = [] # список всех установленных мощностей
for i in elems_avtomats:
	if i.LookupParameter(Param_Py).AsDouble() > 1:
		Py.append(round(i.LookupParameter(Param_Py).AsDouble(), Round_value_ts)) # если Py больше киловатта, округляем его
	else:
		Py.append(i.LookupParameter(Param_Py).AsDouble())
		


#сразу суммируем все значения для последующей записи в итоговую табличку
Py_sum = 0
for i in Py:
	Py_sum = Py_sum + i

''' вытаскиваем нужные нам параметры'''
Kc = [element.LookupParameter(Param_Kc).AsDouble() for element in elems_avtomats]

#Рассчитываем Рр:
Pp = []	
a = 0
while a < len(Py):
	for w in Py:
		if w > 1: # округляем только то, что больше киловатта
			Pp.append(round(w*Kc[a], Round_value_ts))
		else: # если Ру < 1 кВт, то окургляем до 2-х знаков после запятой
			Pp.append(round(w*Kc[a], 2))
		a = a + 1


#И суммарную Рр
Pp_sum = 0
for i in Pp:
	Pp_sum = Pp_sum + i
		
''' вытаскиваем нужные нам параметры'''
cosf = [element.LookupParameter(Param_Cosf).AsDouble() for element in elems_avtomats]


#Рассчитываем средневзвешенный косинус
#Сначала сделаем вспомогательную переменную содержащую число равное сумме каждой Рр умноженной на каждый косинус
Pp_multiplication_cosf_sum = 0
for i in list(map(lambda x,y: x*y, Pp, cosf)):
	Pp_multiplication_cosf_sum = Pp_multiplication_cosf_sum + i
cosf_average = (round ((Pp_multiplication_cosf_sum / Pp_sum), 2))
# а вот эта штуковина ниже делает список, состоящий из каждой Рр умноженной на каждый косинус
#ara = list(map(lambda x,y: x*y, Pp, cosf)) 

#Рассчитаем сразу общую полную мощность
if (Pp_sum / cosf_average) > 1: # округляем только то, что больше киловатта
	Sp_average = (round ((Pp_sum / cosf_average), Round_value_ts))
else:
	Sp_average = (round ((Pp_sum / cosf_average), 2))




''' вытаскиваем нужные нам параметры'''
Length_of_cable = [element.LookupParameter(Param_Cable_length).AsDouble() for element in elems_avtomats]

#___________сюда вставлен расчёт моментов по приведённой длине (для распределённых потерь от Марата)_________________________________________________
#__т.е. где-то будут моенты от настоящей длины, а где-то от приведённой_____________
Length_of_cable_withReducedWireLength = [] # вспом. список - длины кабелей с приведённой длиной, если она вообще есть и не равна нулю.
QFs_indexes_with_ReducedWireLength = [] # вспомогательный список с порядковыми номерами автоматов для которых момент был рассчитан по приведённой длине
if Param_ReducedWireLength in [p.Definition.Name for p in elems_avtomats[0].Parameters]: # если параметр "Длина проводника приведённая" вообще существует
	for n, i in enumerate(elems_avtomats):
		if i.LookupParameter(Param_ReducedWireLength).AsDouble() > 0: # если параметр "Длина проводника приведённая" больше нуля
			Length_of_cable_withReducedWireLength.append(i.LookupParameter(Param_ReducedWireLength).AsDouble()) # пишем в список приведённую длину
			QFs_indexes_with_ReducedWireLength.append(n) # добавляем индекс (порядковый номер в выборке) автомата для которого была взята приведённая длина
		else:
			Length_of_cable_withReducedWireLength.append(i.LookupParameter(Param_Cable_length).AsDouble()) # пишем в список обычную длину
else: # если параметра "Длина проводника приведённая" нет у автомата, то в списке будут только обычные длины
	Length_of_cable_withReducedWireLength = [element.LookupParameter(Param_Cable_length).AsDouble() for element in elems_avtomats]


# Предупредим пользователя, что для некоторых автоматов потери буду рассчитаны по приведённой длине
if QFs_indexes_with_ReducedWireLength != []:
	td = TaskDialog('Распределённые потери')
	td.MainContent = 'По какому параметру рассчитать распределённые потери?'
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, Param_Cable_length, 'Расчёт потерь будет выполнен на основании длины, указанной в параметре "' + Param_Cable_length + '"')
	td.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, Param_ReducedWireLength, 'Расчёт потерь будет выполнен на основании длины, указанной в параметре "' + Param_ReducedWireLength + '"')
	td.FooterText = 'Расчёт потерь по приведённой длине имеет приоритет над упрощённым расчётом распределённых потерь из настроек. Потери зафиксированные для отдельных групп в настройках будут записаны в любом случае. '
	GetUserResult = td.Show()
	if GetUserResult == TaskDialogResult.CommandLink1: # первый вариант ответа
		# возвращаем всё как было как будто и нет никакой приведённой длины
		Length_of_cable_withReducedWireLength = [element.LookupParameter(Param_Cable_length).AsDouble() for element in elems_avtomats]
		QFs_indexes_with_ReducedWireLength = []
	elif GetUserResult == TaskDialogResult.CommandLink2: # второй вариант ответа
		pass


#Считаем моменты
Moment = []
a = 0
while a < len(Pp):
	for w in Pp:
		Moment.append(w*Length_of_cable_withReducedWireLength[a])
		a = a+1

''' вытаскиваем нужные нам параметры'''
Uavt = [element.LookupParameter(Param_3phase_CB).AsInteger() for element in elems_avtomats]
''' Создадим список с напряжениями автоматов, переведя логические значения списка Uavt (они 1 если автомат 380 и 0 если 220)
в вспомогательный список Uavt_volts, где будут уже значения 0,658 и 0,22 соответственно'''
Uavt_volts = []
for i in Uavt:
	if i == 1: Uavt_volts.append(U3fsqrt3forI)
	else: Uavt_volts.append(U1fforI)


#Считаем расчётные токи
Ip = []
b = 0
while b < len(Pp):
	for v in Pp:
		if v > 1: # округляем только то, что больше киловатта
			Ip.append(round((v / cosf[b] / Uavt_volts[b]), Round_value_ts))   #Сразу же и округляем токи
		else:
			Ip.append(round((v / cosf[b] / Uavt_volts[b]), 2))
		b = b+1


# список, указывающий Количество лучей для каждой линии. Например 2-ВВГнг-LS 5х25. 
# Сначала имеет вид: ['', '2']. Где '' - значит один кабель (например ВВГнг-LS 5х25); '2' - значит два кабеля (например 2-ВВГнг-LS 5х25).
# Но мы его переведём в целочисленные значения, где '' пусть станет единицей. То есть получим список из целых чисел, а не строк, вида: [1, 2]
Cable_count_for_a_line = []
for i in [element.LookupParameter(Param_Rays_quantity).AsInteger() for element in elems_avtomats]:
	if i == 0: # если пользователь установил Количество лучей 0, то мы будем считать, что имеется в виду 1
		Cable_count_for_a_line.append(1)
	else:
		Cable_count_for_a_line.append(i)
# Сделаем проверку, что Количество лучей существующее (то есть взятое только что из чертежа) должно быть больше или равно нулю
for n, i in enumerate(Cable_count_for_a_line):
	if i <= 0:
		raise Exception(Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_20)
		#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' количество лучей меньше нуля. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()
# Аналогично сформируем список со всеми значениями параметров "Количество проводников"
Wire_count_for_a_line = []
for i in [element.LookupParameter(Param_Conductor_quantity).AsInteger() for element in elems_avtomats]:
	if i == 0:
		Wire_count_for_a_line.append(1)
	else:
		Wire_count_for_a_line.append(i)
# Сделаем проверку, что количество проводников существующее (то есть взятое только что из чертежа) должно быть целым числом от 1 до 5
for n, i in enumerate(Wire_count_for_a_line):
	if i <= 0 or i > 5:
		raise Exception(Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_21) 
		#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' количество проводников меньше нуля или больше пяти. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()



# Разбираемся с количеством жил. Если напряжение 0.658 - записать 5 жил, если 0.22 - записать 3 жилы. 
# Но! Если, например, пользователь заранее ввёл одну жилу (к примеру ВВГнг-LS 4(1х185))
# или четыре жилы (для трёхфазных двигателей - ВВГнг-LS 4х10),
# то тогда оставим 1 или 4 жилы и не будем их переписывать.
Cab_wires_from_drawing = [element.LookupParameter(Param_Wires_quantity).AsInteger() for element in elems_avtomats]
# Сделаем проверку, что количество жил существующее (то есть взятое только что из чертежа) должно быть целым числом от 1 до 5
for n, i in enumerate(Cab_wires_from_drawing):
	if i <= 0 or i > 5:
		raise Exception(Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_22)
		#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' количество жил меньше нуля или больше пяти. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()

# Сделаем проверку: если количество проводников больше 1, то количество жил должно быть равно только 1 (возможна только одна жила)
for n, i in enumerate(Wire_count_for_a_line):
	if i > 1 and Cab_wires_from_drawing[n] != 1:
		raise Exception(Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_23)
		#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' количество проводников больше 1, при этом и количество жил больше 1 - чего быть не может. При количестве проводников больше 1, количество жил всегда должно быть равным 1. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()



#Считаем (и поправляем пользователя) количество жил в зависимости от напряжения
Cab_wires = []
a = 0
while a < len(Uavt_volts):
	for i in Uavt_volts:
		if i == U3fsqrt3forI and Cab_wires_from_drawing[a] != 1 and Cab_wires_from_drawing[a] != 4: # если напряжение 0.658 AND число жил, записанное в автомате не равно 1 и 4
			Cab_wires.append(5)
		elif i == U1fforI and Cab_wires_from_drawing[a] != 1 and Cab_wires_from_drawing[a] != 4: # если напряжение 0.22 AND число жил, записанное в автомате не равно 1 и 4
			Cab_wires.append(3)
		elif i == U3fsqrt3forI and Cab_wires_from_drawing[a] == 4: # если напряжение 0.658 AND если количество жил было записано 4 - то так и оставить
			Cab_wires.append(4)
		elif i == U3fsqrt3forI and Cab_wires_from_drawing[a] == 1 and Wire_count_for_a_line[a] < 3: # если напряжение 0.658 AND если количество жил было записано 1 AND Количество проводников меньше 3 - выдать ошибку!
			raise Exception(Avcounts_Dif_texttrans_24 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_25 + str(Cable_count_for_a_line[a]) + Avcounts_Dif_texttrans_26)
			#MessageBox.Show('Группа ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' трёхфазная. Однако вы выбрали одножильный кабель и указали количество таких кабелей: ' + str(Cable_count_for_a_line[a]) + '. Такого быть не может. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
			#sys.exit()
		elif Cab_wires_from_drawing[a] == 1: # если количество жил было записано 1 - то так и оставить
			Cab_wires.append(1)
		else:
			raise Exception(Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_27)
			#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' что-то не так с количеством жил. Никакие данные не были записаны в чертёж. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
			#sys.exit()
		a = a + 1





''' вытаскиваем нужные нам параметры'''
Cab_type = [element.LookupParameter(Param_Wire_brand).AsString() for element in elems_avtomats]
Cab_section = [element.LookupParameter(Param_Cable_section).AsDouble() for element in elems_avtomats]



# Делаем проверку на то, что если введённое пользователем сечение кабеля отсутствует в списке возможных сечений - выкинуть его из программы.
heplp_var = 0 # вспомогательная переменная. Если после следующего цикла она останется меньше длины списка Cab_section, значит где-то нет совпадения пользовательского сечения и сечения из Sections_of_cables_DB и надо завершить программу.
for i in Cab_section:
	a = 0
	while a < len(Sections_of_cables_DB):
		if i == Sections_of_cables_DB[a]:
			heplp_var = heplp_var + 1
		a = a + 1
if heplp_var < len(Cab_section):
	raise Exception(Avcounts_Dif_texttrans_28 + ', '.join([str(i) for i in Sections_of_cables_DB]) +  Avcounts_Dif_texttrans_29)
	#MessageBox.Show('У одной или нескольких групп сечение кабеля не соответствует списку: ' + ', '.join([str(i) for i in Sections_of_cables_DB]) +  ' (кв.мм). Программа работает только с сечениями из этого списка. Никакие данные не были записаны в чертёж. Пожалуйста выберите сечения из этого списка и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	#sys.exit()









# ___________________________Разбираемся с понижающими коэффициентами_____________________________________________________________________________________________________________________________________

Accessory_list = [element.LookupParameter(Param_Accessory).AsString() for element in elems_avtomats] # Получаем список с принадлежностями всех автоматов. Нужен для дальнейших действий

# Внимание: костыль!
# Если количество автоматов с одинаковой принадлежностью больше 9 (длины списка Cables_trays_reduction_factor_DB), то мы будем всё время выходить за пределы диапазона и будет вылетать
# критическая ошибка. Поэтому дополним список Cables_trays_reduction_factor_DB до длины равной количеству всех выбранных автоматов плюс дополнительные лучи кабелей. Причём, понятное дело, все дополненные коэффициенты
# одновременности будут равны последнему члену списка Cables_trays_reduction_factor_DB.
last_member = Cables_trays_reduction_factor_DB[len(Cables_trays_reduction_factor_DB)-1] # вспомогательная переменная: последний член исходного списка Cables_trays_reduction_factor_DB

Cable_count_all = sum(Cable_count_for_a_line) # Получаем количество проводников в выборке включая лучи отдельных автоматов, если их больше одного

# Дополняем список понижающих коэффициентов кабелей до числа кабелей в выборке
a = len(Cables_trays_reduction_factor_DB)
if a < Cable_count_all:
	while a < Cable_count_all:
		Cables_trays_reduction_factor_DB.append(last_member)
		a = a + 1

# То же самое для списка понижающих коэффициентов автоматов. Только здесь не плюсуем лучи кабелей, а берём просто количество выбранных автоматов.
last_member = Circuit_breakers_reduction_factor_DB[len(Circuit_breakers_reduction_factor_DB)-1]
a = len(Circuit_breakers_reduction_factor_DB)
if a < len(elems_avtomats):
	while a < len(elems_avtomats):
		Circuit_breakers_reduction_factor_DB.append(last_member)
		a = a + 1
# Список понижающих коэффициентов для автоматов по ГОСТ 32397-2013 табл. В.1 (коэффициенты одновременности)
# 0-й элемент: 1 автомат; 1-й: 2авт; 2-й: 3 авт. и т.д. до 10 автоматов
# Circuit_breakers_reduction_factor_DB = [1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5]




# Создаём вспомогательный список в котором подсписками будут члены из 3-х элементов. 
# 0-й: принадлежность, 1-й: сколько раз такая принадлежность встречается, 2-й: понижающий коэффициент совместной прокладки кабелей, 3-й: понижающий коэффициент автоматов (установленных рядом)
# на выходе получим список вида: [['РП2.1', 4, 0.77, 0.7], ['РП2.1'', 4, 0.77, 0.7], ['РП2.1', 4, 0.77, 0.7], ['РП2.1', 4, 0.77, 0.7], ['РП1.1', 2, 0.8, 0.8], ['РП1.1', 2, 0.8, 0.8]]
Accessory_count_list = []
for i in Accessory_list:
	Accessory_count_list.append([])
for n, i in enumerate(Accessory_count_list):
	i.append(Accessory_list[n])
	cur_indx = Get_coincidence_in_list (Accessory_list[n], Accessory_list) # получаем индексы совпавших элементов
	i.append(len(cur_indx)) # формируем спсиок с количеством одинаковых элементов
	# Теперь если у автоматов встречается количество лучей, то нужно добавить эти кабели к совместно проложенным
	if Accessory_list[n] != '': # Если принадлежность не пустая строка '' (если пустая, то не считаем совместную прокладку, не вводим понижающие коэффициенты)
		x = 0 # вспомогательный счётчик количества лучей
		for j in elems_avtomats:
			if j.LookupParameter(Param_Rays_quantity).AsInteger() > 1 and j.LookupParameter(Param_Accessory).AsString() == Accessory_list[n]:
				# если количество лучей текущего автомата > 1
				# AND
				# Принадлежность текущего автомата такая же как для текущего цикла
				x = x + j.LookupParameter(Param_Rays_quantity).AsInteger() - 1 # добавляем луч (или лучи)
		if len(cur_indx) + x - 1 <= len(Cables_trays_reduction_factor_DB): # если учтя количество лучей мы не вышли за пределы списка коэффициентов, то...  
			i.append(  Cables_trays_reduction_factor_DB[len(cur_indx) + x - 1]  ) # добавляем текущий коэффициент одновременности при совместной прокладке кабелей
			# Кстати вот это:      len(cur_indx) + x       - количество отдельных лучей для текущей принадлежности. Если чо - удобно проверять правильно ли выбран понижающий коэффициент
		elif len(cur_indx) + x - 1 > len(Cables_trays_reduction_factor_DB): # если учтя количество лучей мы вышли за пределы списка коэффициентов, то...
			i.append(  Cables_trays_reduction_factor_DB[-1]  ) # добавляем последний коэффициент одновременности из списка
	else:
		i.append(1.0) # если же принадлежность равна '', то не вводим понижающий коэффициент
	# Теперь добавим 3-й член подсписков - понижающий коэффициент автоматов
	if Accessory_list[n] != '': # Если принадлежность не пустая строка '' (если пустая, то не считаем совместную прокладку, не вводим понижающие коэффициенты)
		i.append(   Circuit_breakers_reduction_factor_DB[len(cur_indx)-1]   )
	else:
		i.append(1.0) # если же принадлежность равна '', то не вводим понижающий коэффициент
	

# Преобразуем Accessory_count_list в читаемый вид для вывода в табличку примечаний на схеме
# пример вида: [[u'\u0420\u041f2', 3, 0.8, 0.8], [u'\u0420\u041f2', 3, 0.8, 0.8], [u'\u0420\u041f1', 4, 0.77, 0.69], [u'\u0420\u041f1', 4, 0.77, 0.69], [u'\u0420\u041f1', 4, 0.77000000000000002, 0.69999999999999996], [u'\u0420\u041f1', 4, 0.77000000000000002, 0.69999999999999996], [u'\u0420\u041f2', 3, 0.80000000000000004, 0.80000000000000004]]
Accessory_count_list_readable = 'Примечание: ' # читаемый вид
if Cable_section_calculation_method == 1:
	Accessory_count_list_readable = Accessory_count_list_readable + '\nВыбор сечений кабелей осуществлён по уставкам аппаратов защиты.'
elif Cable_section_calculation_method == 0:
	Accessory_count_list_readable = Accessory_count_list_readable + '\nВыбор сечений кабелей осуществлён по токам срабатывания аппаратов защиты (ток уставки * Ко).'


Accessory_count_list_copy = [] # копия Accessory_count_list
for i in Accessory_count_list:
	Accessory_count_list_copy.append(i)

for i in Accessory_count_list_copy:
	if i[0] == '': # выкинем элементы с пустой принадлежностью
		cur_indx = Get_coincidence_in_list (i, Accessory_count_list_copy) # получаем индексы совпавших элементов
		Delete_indexed_elements_in_list (cur_indx, Accessory_count_list_copy) # удаляем совпавшие элементы из списка
	else:
		cur_indx = Get_coincidence_in_list (i, Accessory_count_list_copy) # получаем индексы совпавших элементов
		Accessory_count_list_readable = Accessory_count_list_readable + '\n' + i[0] + ' в составе ' + str(len(cur_indx)) + ' аппаратов, Ко = ' + str(i[3]) + '.\nДля ' + str(Cable_count_all) + ' проводников: способ монтажа Е, Кп.проводников = ' + str(i[2]) + '.'
		Delete_indexed_elements_in_list (cur_indx, Accessory_count_list_copy) # удаляем совпавшие элементы из списка


# Проверим соответствуют ли понижающие коэффциенты стандартным значениям из ГОСТ.
# Если не соответствуют, то есть пользователь ввёл какие-то свои понижающие коэффициенты, то в примечании уберём запись, что коэффициенты выбраны по ГОСТам.
if Cables_trays_reduction_factor_DB[:9] == [1.0, 0.87, 0.8, 0.77, 0.75, 0.73, 0.71, 0.7, 0.68] and Circuit_breakers_reduction_factor_DB[:10] == [1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5]:
	Accessory_count_list_readable = Accessory_count_list_readable + Avcounts_Dif_texttrans_30
elif Cables_trays_reduction_factor_DB[:9] != [1.0, 0.87, 0.8, 0.77, 0.75, 0.73, 0.71, 0.7, 0.68] and Circuit_breakers_reduction_factor_DB[:10] == [1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5]:
	Accessory_count_list_readable = Accessory_count_list_readable + Avcounts_Dif_texttrans_31
elif Cables_trays_reduction_factor_DB[:9] == [1.0, 0.87, 0.8, 0.77, 0.75, 0.73, 0.71, 0.7, 0.68] and Circuit_breakers_reduction_factor_DB[:10] != [1.0, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.6, 0.6, 0.5]:
	Accessory_count_list_readable = Accessory_count_list_readable + Avcounts_Dif_texttrans_32

# MessageBox.Show(Accessory_count_list_readable)


# Вытаскиваем номиналы аппаратов защиты:
Current_breaker_nominal = [element.LookupParameter(Param_Circuit_breaker_nominal).AsDouble() for element in elems_avtomats]

# Проверочный список для вывода предупреждение о завышении аппарата защиты пользователю.
# В этом списке значение 0 означает что аппарат не завышен, значение 1, что завышен. Потом с этого списка заполним соответствующий параметр в семействе.
# При этом данная проверка начинает работать при номиналах выше 16 А. Иначе она везде будет предупреждать о превышении.
Current_breaker_overestimated = []

# Подберём номиналы аппаратов защиты не менее расчётных токов (с понижающими коэффициентами сразу):
Current_breaker_nominal_min = [] 

# натянем на список расчётных токов понижающие коэффициенты для совместно установленных автоматов
# Сюда ввести проверку, что если ток больше 63 А, то его будет защищать автомат больше 63 А. А у таких автоматов литой корпус и на них понижающие коэффциенты не действуют.
Ip_reduced = []
for n, i in enumerate(Ip):
	if i <= 63:
		Ip_reduced.append(i / Accessory_count_list[n][3])
	else:
		Ip_reduced.append(i)



a = 0
while a < len(Current_breaker_nominal):
	for i in Ip_reduced:
		if i >= Current_breaker_nominal[a] and Current_breaker_nominal[a] <= Current_breaker_nominal_DB[len(Current_breaker_nominal_DB)-1] and i <= Current_breaker_nominal_DB[len(Current_breaker_nominal_DB)-1]: 
			# если 
			# расчётный ток больше уставки аппарата защиты 
			# AND 
			# он не выходит за пределы списка стандартных номиналов аппаратов защиты 
			# AND 
			# расчётный ток меньше максимального из списка стандартных уставнок аппаратов защиты
			b = 0
			curr_nom = 0  # вводится вспомогательная переменная curr_nom 
			while curr_nom <= i:  
				curr_nom = Current_breaker_nominal_DB[b]
				b = b + 1
			Current_breaker_nominal_min.append(Current_breaker_nominal_DB[b-1])
			Current_breaker_overestimated.append(0)
		elif i < Current_breaker_nominal[a]: # если расчётный ток меньше номинала аппарата защиты
			Current_breaker_nominal_min.append(Current_breaker_nominal[a])
			# Сделаем проверку: если расчётный ток меньше номинала аппарата защиты на две ступени, значит выдадим предупреждение, что номинал автомата выбран с запасом (завышен)
			if Current_breaker_nominal[a] > 16 and i < Current_breaker_nominal_DB[Current_breaker_nominal_DB.index(Current_breaker_nominal[a])-1]: 
				# начинаем проверки с треьего члена списка (уставка 20 А), чтобы не было ошибок
				# если
				# номинал автомата больше 16 А
				# AND
				# расчётный ток меньше на две ступени чем номинал автомата
				Current_breaker_overestimated.append(1)
			else:
				Current_breaker_overestimated.append(0)
		else:  # если расчётный ток выходит за пределы стандартных уставок автоматов в списке Current_breaker_nominal_DB
			Current_breaker_nominal_min.append(Current_breaker_nominal[a])
			CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_33 + str(Current_breaker_nominal_DB[-1]) + Avcounts_Dif_texttrans_34
			#MessageBox.Show('У группы: ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' расчётный ток больше стандартной уставки аппарата защиты в ' + str(Current_breaker_nominal_DB[-1]) + ' А. Номинал аппарата защиты не выбран! Его нужно выбрать вручную. Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
			Current_breaker_overestimated.append(1)
		a = a + 1



# Реально автоматы отключатся не при их номинальном токе, а при номинальном токе умноженном на понижающий коэффициент совместной установки.
# Вот по этому току мы и подберём сечения если Cable_section_calculation_method = 0.
# Следовательно, если переменная Cable_section_calculation_method = 1, то дальше для выбора сечений пользуемся списком Current_breaker_nominal_min.
# Если же переменная Cable_section_calculation_method = 0, то на список Current_breaker_nominal_min натянем понижающие коэффициенты совместной установки автоматов
# и уже по такому списку будем подбирать сечения.
Current_breaker_nominal_real = [] # список с токами срабатывания автоматов
if Cable_section_calculation_method == 1: # если пользователь хочет выбирать сечения по уставкам автоматов...
	Current_breaker_nominal_real = Current_breaker_nominal_min # то списки равны. Сечения выбираем по уставкам автоматов.
elif Cable_section_calculation_method == 0: # если пользователь хочет выбирать сечения по токам срабаотывания автоматов...
	for n, i in enumerate(Current_breaker_nominal_min):
		if i <= 63: # если номинальный ток автомата меньше или равен 63 А
			Current_breaker_nominal_real.append(i * Accessory_count_list[n][3] * 1.049) # вычисляем реальный ток срабатывания автомата. Номинальный ток * понижающий коэффициент совместной установки * эмпирический коэффициент от Димона (небольшой запас для сечения)
		else:
			Current_breaker_nominal_real.append(i) # при номинале автомата больше 63 А понижающие коэффциенты на него не действуют

#__________________________________________________________________________________________________________________________________________________________________________




	


#___________________________________________________________________________________________________________________________________________
#____________________Работа с производителями кабелей_________________________________________________________________________________
#___________________________________________________________________________________________________________________________________________

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


# Функция декодирует список с разделителями из ES в список со списками (такая же как в команде ManufacturerSelectCable.py)
# На входе единый список вида: 
# На выходе список списков вида: 
def DecodingListofListsforES (ListwithSeparators):
	znach1hlp = []
	for i in ListwithSeparators:
		znach1hlp.append(i.split('?!?'))
	return znach1hlp


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


# Функция получает список кабелей используемых в данной модели по имени конкретного производителя. (такая же как в команде ManufacturerSelectCable.py)
# На входе супер список со всеми данными по кабелям всех производителей из Хранилища, Имя производителя (строка)
# На выходе список с используемыми марками кабелей. # Вид: [u'ВВГнг', u'КПвПпБП']
def GetusedCabs (Wires_ListDB_from_ExtStorage, CabManufName):
	# Формируем список кабелей, использующихся в данной модели.
	Used_CabList = [] # Вид: [u'ВВГнг', u'КПвПпБП']
	for i in Wires_ListDB_from_ExtStorage:
		for j in i:
			if j[2] not in Used_CabList and j[5] == 'True' and j[7] == CabManufName: # j[2] - это марка кабеля, например ВВГнг, j[5] используется или нет в модели 'True', j[7] - Имя производителя
				Used_CabList.append(j[2])
	return Used_CabList


# Функция определения материала проводника у конкретного кабеля производителя
# На выходе из функции True если медь, False если алюминий. Или строка '(нет производителя)' если производитель не выбран, или "не найдена марка кабеля", если нет такой марки у производителя
def Is_Cu_or_Al_withCabManuf (element_in_elems_avtomats, Param_Wire_brand, Wires_List_UsedinModel):
	wirebrandstr = element_in_elems_avtomats.LookupParameter(Param_Wire_brand).AsString() # Марка кабеля (строка)
	if Wires_List_UsedinModel == []: # Если нет производителя
		# NoManufactirer_texttrans это '(нет производителя)'
		exitbool = NoManufactirer_texttrans
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

# Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel)
'''
element_in_elems_avtomats = elems_avtomats[n]

'''



#_______Работа с хранилищем имён производителей кабелей______________
# Guid для этого хранилища
schemaGuid_for_ManufNames_ManufacturerSelectCable = System.Guid(Guidstr_ManufNames_ManufacturerSelectCable)

#Получаем Schema:
schCable_ManufNames = Schema.Lookup(schemaGuid_for_ManufNames_ManufacturerSelectCable)

# Проверяем корректность хранилища
if schCable_ManufNames is None or ProjectInfoObject.GetEntity(schCable_ManufNames).IsValid() == False:
	# Будем считать что выбрано '(нет производителя) это NoManufactirer_texttrans'
	Cable_ManufSelected = NoManufactirer_texttrans
else:
	# объявляем . Вид: [[u'(нет производителя)'], [u'Кольчугинский кабельный завод', 'https://elcable.ru/'], ['VASA', 'https://SAIT.RU']]
	# В этом списке на первой позиции должен стоять выбранный производитель.
	ManufNamesCable_Selected = ReadES_ManufacturerSelect(schemaGuid_for_ManufNames_ManufacturerSelectCable, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelectCable)
	Cable_ManufSelected = ManufNamesCable_Selected[0][0] # Объявляем имя выбранного производителя кабелей

#___________Достанем списки производителей кабелей из Хранилища_____________
# Guid для этого хранилища
schemaGuid_for_Cable_ListDB_ManufacturerSelectCable = System.Guid(Guidstr_Cable_ListDB_ManufacturerSelect)
#Получаем Schema:
schCable_ListDB = Schema.Lookup(schemaGuid_for_Cable_ListDB_ManufacturerSelectCable)
# Проверяем корректность хранилища
if schCable_ListDB is None or ProjectInfoObject.GetEntity(schCable_ListDB).IsValid() == False:
	# Будем считать что выбрано '(нет производителя)'
	Cable_ManufSelected = NoManufactirer_texttrans
	#TaskDialog.Show('Предупреждение', 'Не найдены характеристики кабелей: "' + Cable_ManufSelected + '". Запустите команду выбора производителя кабельной продукции. Если ошибка повторится, обратитесь к разработчику. Далее при расчётах будут использованы данные по кабелям из основных настроек программы.')
else:
	# объявляем список с кабелями уже из Хранилища данной модели. Вид: [[[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']], [[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', 'QUQUSHKA'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', 'QUQUSHKA'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', 'QUQUSHKA']]]
	Wires_ListDB_from_ExtStorage = Data_DecodingXML(ReadString_from_ExtensibleStorage(schemaGuid_for_Cable_ListDB_ManufacturerSelectCable, ProjectInfoObject, FieldName_for_Cable_ListDB_ManufacturerSelect))


Wires_List_UsedinModel = [] # Вид: [[[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['29', '39', '50'], ['24', '33', '42'], ['24', '33', '42'], ['10', '7', '4'], ['0.1', '0.12', '0.1'], ['Al', 'Al', 'Al']], [[u'АВВГнг', u'АВВГнг'], ['3', '1'], ['1.5', '70'], ['126', '4900'], ['9.5', '43'], ['0.3', '1.1']], u'АВВГнг', u'тут и так всё ясно но алюминий', '555', 'False', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]]
UsedWireMarks = [] # список используемых марок кабелей. Вид: [u'ВВГнг', u'КПвПпБП']
if Cable_ManufSelected != NoManufactirer_texttrans:
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


# Теперь нам нужна функция которая будет переобъявлять списки с токами и сечениями которые у нас были по умолчанию из Настроек.
# На входе текущий автомат (семейство), имя параметра Марка кабеля, список используемых кабелей производителя, текущее сечение кабеля, логическая переменная "Вернуть к Настройкам"
# На выходе нужные списки по сечениям и токам переобъявлены, если был выбран производитель. 
# Или марка не найденного кабеля в виде строки или пустая строка если не был выбран производитель.
# RedeclareToSettings - маркер чтобы переобъявить переменные обратно из Хранилища. Возможные значения True - вернуть к данным из Хранилища. False - не возвращать к данным их Хранилища.
# Функция переобъявляет списки только для медного или алюминиевого проводника, сама определяя какой попался. Для другого не переопределяет.
# Если марка кабеля не найдена, то переобъявляем токи обратно из Хранилища.
# Чтоб тестить element_in_elems_avtomats = elems_avtomats[0]
def ReDeclareCableChars (element_in_elems_avtomats, Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, Cab_section_Redeclare, RedeclareToSettings):
	global Sections_of_cables_DB # сечения   i[0][0]
	global Currents_for_1phase_multiwire_copper_cables_DB # ток для многожильного 1ф Cu  i[0][1]
	global Currents_for_1phase_multiwire_aluminium_cables_DB # ток для многожильного 1ф Al	i[0][1]
	global Currents_for_multiwire_copper_cables_DB # ток для многожильного 3ф Cu	i[0][2]
	global Currents_for_multiwire_aluminium_cables_DB # ток для многожильного 3ф Al		i[0][2]
	global Currents_for_singlewire_copper_cables_DB # ток одножильного Cu		i[0][3]
	global Currents_for_singlewire_aluminium_cables_DB # ток одножильного Al		i[0][3]

	WireMarkNotFound = '' # Если не нашли нужную марку кабеля, то предупредим об этом пользователя

	if RedeclareToSettings == True: # Переобъявляет списки на те что были в Хранилище.
		Sections_of_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)]] # поясню: это обращение к содержимому списка по имени поля в хранилище
		Currents_for_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_2) + 1)]]
		Currents_for_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_3) + 1)]]
		Currents_for_singlewire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_4) + 1)]]
		Currents_for_singlewire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_5) + 1)]]
		Currents_for_1phase_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_10) + 1)]]
		Currents_for_1phase_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_11) + 1)]]
		return 'Redeclared_to_Storage'

	# Переобъявление переменных
	if Wires_List_UsedinModel != []: # если вообще производитель выбран
		# Получаем текущую марку проводника
		wirebrandstr = element_in_elems_avtomats.LookupParameter(Param_Wire_brand).AsString() # Марка проводника в виде строки. Вид: u'ППГнг(А)-HF'
		if wirebrandstr not in UsedWireMarks: # Если не нашли такую марку, то выведем её и завершим функцию (вернув значения переменных к данным из Хранилища)
			WireMarkNotFound = wirebrandstr
			Sections_of_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_1) + 1)]] # поясню: это обращение к содержимому списка по имени поля в хранилище
			Currents_for_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_2) + 1)]]
			Currents_for_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_3) + 1)]]
			Currents_for_singlewire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_4) + 1)]]
			Currents_for_singlewire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_5) + 1)]]
			Currents_for_1phase_multiwire_copper_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_10) + 1)]]
			Currents_for_1phase_multiwire_aluminium_cables_DB = [float(i) for i in CRF_Storage_DataList[int(CRF_Storage_DataList.index(FieldName_for_CR_11) + 1)]]
			return WireMarkNotFound
		# Ищем эту марку в списке используемых кабелей
		for i in Wires_List_UsedinModel:
			if i[2] == wirebrandstr: # Если нашли нужную марку кабеля
				# Переобъявляем переменные.
				Sections_of_cables_DB = [float(j) for j in i[0][0]]
				if i[8] == 'Al': # Если проводник алюминиевый
					Currents_for_1phase_multiwire_aluminium_cables_DB = [float(j) for j in i[0][1]]
					Currents_for_multiwire_aluminium_cables_DB = [float(j) for j in i[0][2]]
					Currents_for_singlewire_aluminium_cables_DB = [float(j) for j in i[0][3]]
					# У Кольчугино есть контрольные кабели с нулевыми токами. Для них сделаем отдельное предупреждение.
					if sum(Currents_for_1phase_multiwire_aluminium_cables_DB) == 0 or sum(Currents_for_multiwire_aluminium_cables_DB) == 0 or sum(Currents_for_singlewire_aluminium_cables_DB) == 0:
						raise Exception(Avcounts_Dif_texttrans_35 + i[2] +  Avcounts_Dif_texttrans_36)
				else: # Если проводник медный
					Currents_for_1phase_multiwire_copper_cables_DB = [float(j) for j in i[0][1]]
					Currents_for_multiwire_copper_cables_DB = [float(j) for j in i[0][2]]
					Currents_for_singlewire_copper_cables_DB = [float(j) for j in i[0][3]]
					if sum(Currents_for_1phase_multiwire_copper_cables_DB) == 0 or sum(Currents_for_multiwire_copper_cables_DB) == 0 or sum(Currents_for_singlewire_copper_cables_DB) == 0:
						raise Exception(Avcounts_Dif_texttrans_35 + i[2] +  Avcounts_Dif_texttrans_36)
				# !!!!!!!!!!!!!!!!!!! И теперь ещё надо проверить что сечение у выбранного автомата есть в списке сечений у выбранного производителя (по текущей марке)
				# Делаем проверку на то, что если введённое пользователем сечение кабеля отсутствует в списке возможных сечений - выкинуть его из программы.
				if Cab_section_Redeclare not in Sections_of_cables_DB:
					raise Exception(Avcounts_Dif_texttrans_37 + str(Cab_section_Redeclare) +  Avcounts_Dif_texttrans_38)

				break
		return WireMarkNotFound # Выводим пустую строку. А переменные уже переобъявлены.

	else: # Если производитель не выбран, то ничего переобъявлять не будем
		return WireMarkNotFound





'''
Список Wires_List_UsedinModel и его расшифровка. Сам список - это кабели одного производителя, используемые в модели.
[[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино'], [[['2.5', '4', '6'], ['28', '38', '49'], ['23', '32', '41'], ['23', '32', '41'], ['9', '6', '3'], ['0.08', '0.11', '0.08'], ['Cu', 'Cu', 'Cu']], [[u'КПвПпБП', u'КПвПпБП'], ['3', '1'], ['1.5', '70'], ['110', '4700'], ['7.5', '40'], ['0.2', '0.75']], u'КПвПпБП', u'вот так-то', '888', 'True', u'Нефтегазовая', u'Кольчугино']]
Wires_List_UsedinModel[0] - все данные по одному типу кабеля
[[['2.5', '4', '6'], ['30', '40', '51'], ['25', '34', '43'], ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']], [[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']], u'ВВГнг', u'тут и так всё ясно', '777', 'True', u'Строительство', u'Кольчугино']
Wires_List_UsedinModel[0][0] - характеристики кабеля по сечениям:
[['2.5', '4', '6'],    ['30', '40', '51'],     ['25', '34', '43'],      ['25', '34', '43'], ['8', '5', '3.33'], ['0.09', '0.1', '0.09'], ['Cu', 'Cu', 'Cu']]
	сечения		    ток для многожильного 1ф   ток для многожильного 3ф   ток одножильного    активное сопр.       индуктивное сопр.      материал проводника
Wires_List_UsedinModel[0][1] - веса, диаметры, горючая масса по типам кабелей (пока не используем)
[[u'ВВГнг', u'ВВГнг'], ['3', '1'], ['1.5', '70'], ['123.499', '4885.613'], ['8.82', '40.15'], ['0.2', '0.9']]
Wires_List_UsedinModel[0][2] - марка кабеля (искать совпадения по ней)
u'ВВГнг'
Wires_List_UsedinModel[0][3] - наименование и техническая характеристика (это для спецификации)
u'тут и так всё ясно'
Wires_List_UsedinModel[0][4] - код (артикул) для спецификации
'777'
Wires_List_UsedinModel[0][5] - используется / не используется в проекте
'True'
Wires_List_UsedinModel[0][6] - название линейки у производителя
u'Строительство'
Wires_List_UsedinModel[0][7] - завод-изготовитель
u'Кольчугино'
Wires_List_UsedinModel[0][8] - материал проводника
'Cu' или 'Al'
'''




#___________________Конец модуля по работе с производителями кабелей____________________________________________________________________________________________





































#___________________________________________________________________________________________________________________________________________
#____________________модуль по выбору сечений кабелей_________________________________________________________________________________
#___________________________________________________________________________________________________________________________________________

WireMarksnotFound = [] # список с марками кабелей которые не были найдены у производителя. Вид: ['', u'ППГнг(А)-HF', u'ППГнг(А)-HF']
# Создадим список с сечениями, большими чем нужно для номинала аппаратов защиты (но пока без понижающих коэффициентов):
Cab_section_min_no_reduce = []
a = 0
while a < len(Current_breaker_nominal_real):
	for n, i in enumerate(Cab_section):
		# Сюда вставлено обращение к БД Кольчугино и переназначение переменных о сечениях и токах кабелей.
		# Логика такая:
		# 1) Функция переобъявляет переменные по сечениям и токам кабелей если найдёт текущую марку кабеля в списке используемых марок производителя.
		# 2) Если производитель не выбран, функция ничего не переобъявляет
		# 3) Если не найдена текщая марка у производителя, то функция переобъявляет переменные на те что были в Хранилище и выдаёт на выходе марку ненайденного кабеля 
		# (для последующего вывода в окно предупреждения пользователю)
		# Переобъявляем переменные по характеристикам кабелей. И заодно сразу собираем список с ненайденными марками кабелей у производителя.
		WireMarksnotFound.append(ReDeclareCableChars(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, i, False))
		if Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == True or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == True: # Если текущий проводник медный...
			if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
				Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
				# Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_copper_cables_DB] # раньше так делал
				for z in Currents_for_1phase_multiwire_copper_cables_DB:
					if z != 0: # Убираем нули которые могут быть выставлены в Настройках. Типа нет сечений таких (тогда там ноль ставится)
						Currents_for_cur_multiwire_cable.append(z)
			else: # если автомат трёхфазный (напряжение 400 В)
				Currents_for_cur_multiwire_cable = []
				#Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_copper_cables_DB]
				for z in Currents_for_multiwire_copper_cables_DB:
					if z != 0: # Убираем нули которые могут быть выставлены в Настройках. Типа нет сечений таких (тогда там ноль ставится)
						Currents_for_cur_multiwire_cable.append(z)
			if Cab_wires[a] != 1 and (Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) <= Current_breaker_nominal_real[a] and Current_breaker_nominal_real[a] <= (Currents_for_cur_multiwire_cable[len(Currents_for_cur_multiwire_cable)-1] * Cable_count_for_a_line[a]): 
				# если число жил не равно 1 
				# AND 
				# ток для текущего сечения (умноженный на Количество лучей) меньше или равен току уставки автомата 
				# AND 
				# ток уставки меньше последнего тока (умноженного на Количество лучей) в списке допустимых длительных токов
				c = 0
				cur_cur = 0  # вводится вспомогательная переменная cur_cur - текущий ток для текущего сечения в списке Sections_of_cables_DB
				try:
					while cur_cur <= Current_breaker_nominal_real[a]:  
						cur_cur = (Currents_for_cur_multiwire_cable[c] * Cable_count_for_a_line[a])
						c = c + 1
				except System.IndexOutOfRangeException:
					CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_39 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_40
					# MessageBox.Show('Для группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' невозможно подобрать сечение, т.к. сечений пропускающих указанный в линии ток нет в Исходных данных для расчёта (кнопка "Настройки"). Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
				Cab_section_min_no_reduce.append(Sections_of_cables_DB[c-1])
			elif Cab_wires[a] == 1 and (Currents_for_singlewire_copper_cables_DB[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) <= Current_breaker_nominal_real[a] and Current_breaker_nominal_real[a] <= Currents_for_singlewire_copper_cables_DB[len(Currents_for_singlewire_copper_cables_DB)-1]: 
				# если число жил равно 1 
				# AND 
				# ток для текущего сечения (умноженный на Количество лучей) меньше или равен току уставки автомата 
				# AND 
				# ток уставки меньше последнего тока в списке допустимых длительных токов
				c = 0
				cur_cur = 0  # вводится вспомогательная переменная cur_cur - текущий ток для текущего сечения в списке Sections_of_cables_DB
				while cur_cur <= Current_breaker_nominal_real[a]:  
					cur_cur = Currents_for_singlewire_copper_cables_DB[c] * Cable_count_for_a_line[a]
					c = c + 1
				Cab_section_min_no_reduce.append(Sections_of_cables_DB[c-1])
			elif Cab_wires[a] != 1 and (Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) > Current_breaker_nominal_real[a]: 
				# если число жил не равно 1 
				# AND 
				# ток для текущего сечения (умноженного на Количество лучей) больше номинала аппарата защиты, то оставить сечение как есть
				Cab_section_min_no_reduce.append(i)
			elif Cab_wires[a] == 1 and (Currents_for_singlewire_copper_cables_DB[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) > Current_breaker_nominal_real[a]: 
				# если число жил равно 1 
				# AND ток для текущего сечения (умноженного на Количество лучей) больше номинала аппарата защиты, то оставить сечение как есть
				Cab_section_min_no_reduce.append(i)
			else:
				CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_41 + str(Currents_for_cur_multiwire_cable[-1]) + Avcounts_Dif_texttrans_42
				#MessageBox.Show('У группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' номинал аппарата защиты больше ' + str(Currents_for_cur_multiwire_cable[-1]) + ' А. Сечение кабеля для этой группы не выбрано! Его нужно выбрать вручную. Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
				Cab_section_min_no_reduce.append(i)


		elif Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == False or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == False: # Если текущий проводник алюминиевый...
			if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
				Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
				#Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_aluminium_cables_DB]
				for z in Currents_for_1phase_multiwire_aluminium_cables_DB:
					if z != 0: # Убираем нули которые могут быть выставлены в Настройках. Типа нет сечений таких (тогда там ноль ставится)
						Currents_for_cur_multiwire_cable.append(z)
			else: # если автомат трёхфазный (напряжение 400 В)
				Currents_for_cur_multiwire_cable = []
				#Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_aluminium_cables_DB]
				for z in Currents_for_multiwire_aluminium_cables_DB:
					if z != 0: # Убираем нули которые могут быть выставлены в Настройках. Типа нет сечений таких (тогда там ноль ставится)
						Currents_for_cur_multiwire_cable.append(z)
			if Cab_wires[a] != 1 and (Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) <= Current_breaker_nominal_real[a] and Current_breaker_nominal_real[a] <= (Currents_for_cur_multiwire_cable[len(Currents_for_cur_multiwire_cable)-1] * Cable_count_for_a_line[a]): 
				# если число жил не равно 1 
				# AND 
				# ток для текущего сечения (умноженный на Количество лучей) меньше или равен току уставки автомата 
				# AND 
				# ток уставки меньше последнего тока (умноженного на Количество лучей) в списке допустимых длительных токов
				c = 0
				cur_cur = 0  # вводится вспомогательная переменная cur_cur - текущий ток для текущего сечения в списке Sections_of_cables_DB
				try:
					while cur_cur <= Current_breaker_nominal_real[a]:  
						cur_cur = (Currents_for_cur_multiwire_cable[c] * Cable_count_for_a_line[a])
						c = c + 1
				except System.IndexOutOfRangeException:
					CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_39 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_43
					#MessageBox.Show('Для группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' невозможно подобрать сечение, т.к. сечений пропускающих указанный в линии ток нет в Исходных данных для расчёта (кнопка "Настройки"). Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
				Cab_section_min_no_reduce.append(Sections_of_cables_DB[c-1])
			elif Cab_wires[a] == 1 and (Currents_for_singlewire_aluminium_cables_DB[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) <= Current_breaker_nominal_real[a] and Current_breaker_nominal_real[a] <= Currents_for_singlewire_aluminium_cables_DB[len(Currents_for_singlewire_aluminium_cables_DB)-1]: 
				# если число жил равно 1 
				# AND 
				# ток для текущего сечения (умноженный на Количество лучей) меньше или равен току уставки автомата 
				# AND 
				# ток уставки меньше последнего тока в списке допустимых длительных токов
				c = 0
				cur_cur = 0  # вводится вспомогательная переменная cur_cur - текущий ток для текущего сечения в списке Sections_of_cables_DB
				while cur_cur <= Current_breaker_nominal_real[a]:  
					cur_cur = Currents_for_singlewire_aluminium_cables_DB[c] * Cable_count_for_a_line[a]
					c = c + 1
				Cab_section_min_no_reduce.append(Sections_of_cables_DB[c-1])
			elif Cab_wires[a] != 1 and (Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) > Current_breaker_nominal_real[a]: 
				# если число жил не равно 1 
				# AND 
				# ток для текущего сечения (умноженного на Количество лучей) больше номинала аппарата защиты, то оставить сечение как есть
				Cab_section_min_no_reduce.append(i)
			elif Cab_wires[a] == 1 and (Currents_for_singlewire_aluminium_cables_DB[Sections_of_cables_DB.index(i)] * Cable_count_for_a_line[a]) > Current_breaker_nominal_real[a]: 
				# если число жил равно 1 
				# AND ток для текущего сечения (умноженного на Количество лучей) больше номинала аппарата защиты, то оставить сечение как есть
				Cab_section_min_no_reduce.append(i)
			else:
				CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_19 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + Avcounts_Dif_texttrans_41 + str(Currents_for_cur_multiwire_cable[-1]) + Avcounts_Dif_texttrans_42
				#MessageBox.Show('У группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][a] + ' номинал аппарата защиты больше ' + str(Currents_for_cur_multiwire_cable[-1]) + ' А. Сечение кабеля для этой группы не выбрано! Его нужно выбрать вручную. Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
				Cab_section_min_no_reduce.append(i)

		a = a + 1



# Почистим список WireMarksnotFound
hlp_lst = []
for i in WireMarksnotFound:
	if i != '' and i != 'Redeclared_to_Storage' and i not in hlp_lst:
		hlp_lst.append(i)
WireMarksnotFound = [i for i in hlp_lst]
if WireMarksnotFound != []:
	CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_44 + ', '.join(WireMarksnotFound) + Avcounts_Dif_texttrans_45




# Теперь накатим на список Cab_section_min_no_reduce понижающие коэффициенты при совместной прокладке
# Accessory_count_list[n][2] - текущий понижающий коэффициент

# Понизим токи которые пропускают наши кабели в соответствии с понижающими коэффициентами
Currents_for_cables_reduced = [] # список с пониженными пропускными токами вида: [363.44, 269.5, 234.84999999999999, 73.150000000000006, 304.5, 265.35000000000002]
for n, i in enumerate(Cab_section_min_no_reduce):
	ReDeclareCableChars(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, i, False) # переобъявляем харакатеристики кабелей по конкретному производителю
	if Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == True or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == True: # Если текущий проводник медный...
		if Cab_wires[n] != 1: # если многожильный кабель
			if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
				Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
				Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_copper_cables_DB]
			else: # если автомат трёхфазный (напряжение 400 В)
				Currents_for_cur_multiwire_cable = []
				Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_copper_cables_DB]
			Currents_for_cables_reduced.append(  Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Accessory_count_list[n][2]  )  # ток для данного сечения умноженный на понижающий коэффициент
		else: # если одножильный кабель
			Currents_for_cables_reduced.append(  Currents_for_singlewire_copper_cables_DB[Sections_of_cables_DB.index(i)] * Accessory_count_list[n][2]  )  # ток для данного сечения умноженный на понижающий коэффициент
	elif Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == False or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == False: # Если текущий проводник алюминиевый...
		if Cab_wires[n] != 1: # если многожильный кабель
			if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
				Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
				Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_aluminium_cables_DB]
			else: # если автомат трёхфазный (напряжение 400 В)
				Currents_for_cur_multiwire_cable = []
				Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_aluminium_cables_DB]
			Currents_for_cables_reduced.append(  Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)] * Accessory_count_list[n][2]  )  # ток для данного сечения умноженный на понижающий коэффициент
		else: # если одножильный кабель
			Currents_for_cables_reduced.append(  Currents_for_singlewire_aluminium_cables_DB[Sections_of_cables_DB.index(i)] * Accessory_count_list[n][2]  )  # ток для данного сечения умноженный на понижающий коэффициент





# Теперь проверим годятся ли ещё эти пониженные токи для номиналов автоматов которые их защищают.
Cab_section_min = [] # Список с сечениями уже учитывающий понижающие коэффициенты совместной прокладки
for n, i in enumerate(Currents_for_cables_reduced):
	ReDeclareCableChars(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, Cab_section_min_no_reduce[n], False) # переобъявляем харакатеристики кабелей по конкретному производителю
	if i <= Current_breaker_nominal_real[n] and Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + 1 > len(Sections_of_cables_DB) - 1: 
		# Если пониженный пропускной ток кабеля стал < номнала автомата  
		# AND 
		# кончились сечения в списке с которым работает программа, то выдать предупреждение
		CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_39 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_46 + str(Sections_of_cables_DB[-1]) + Avcounts_Dif_texttrans_47
		#MessageBox.Show('Для группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' невозможно подобрать сечение кабеля в соответвии с коэффициентами одновременности при совместной прокладке кабельных линий. Это произошло потому что необходимо сечение большее ' + str(Sections_of_cables_DB[-1]) + ' кв.мм с которым работает программа. Сечение кабеля для этой группы выбрано без учёта коэффициента совместной прокладки! Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
		Cab_section_min.append(Cab_section_min_no_reduce[n]) # к сожалению оставить сечение как было
	elif i <= Current_breaker_nominal_real[n]: 
		# Если пониженный пропускной ток кабеля стал < номнала автомата (считаем, что есть куда повышать сечения, т.к. в предыдущем if идёт проверка не вышли ли мы за пределы списка с сечениями с которыми работает программма)
		# То начнём смотреть проходит ли следующее сечение
		a = 0 # начинаем смотреть с текущего сечения на всякий случай
		while a < len(Sections_of_cables_DB) - 1 and Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a < len(Sections_of_cables_DB) - 1: # пока счётчик не дойдёт до конца списка с сечениями кабелей
			if Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == True or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == True: # Если текущий проводник медный...
				if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
					Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
					Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_copper_cables_DB]
				else: # если автомат трёхфазный (напряжение 400 В)
					Currents_for_cur_multiwire_cable = []
					Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_copper_cables_DB]
				if Cab_wires[n] != 1 and Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a] * Accessory_count_list[n][2] * Cable_count_for_a_line[n] > Current_breaker_nominal_real[n]:
					# Если многожильный кабель
					# AND
					# у следующего проверяемого сечения пропускной ток * на коэффициент совместной прокладки * количество лучей стал > номинала защиты группы, то всё - сечение подобрано
						Cab_section_min.append(    Sections_of_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a]   ) # выставляем нужное сечение
						a = a + 1000000 # выходим из цикла
				elif Cab_wires[n] == 1 and Currents_for_singlewire_copper_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a] * Accessory_count_list[n][2] * Cable_count_for_a_line[n] > Current_breaker_nominal_real[n]:
					# Если одножильный кабель
					# AND
					# у следующего проверяемого сечения пропускной ток * на коэффициент совместной прокладки * количество лучей стал > номинала защиты группы, то всё - сечение подобрано
						Cab_section_min.append(    Sections_of_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a]   ) # выставляем нужное сечение
						a = a + 1000000 # выходим из цикла
			elif Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == False or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == False: # Если текущий проводник алюминиевый...
				if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
					Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
					Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_aluminium_cables_DB]
				else: # если автомат трёхфазный (напряжение 400 В)
					Currents_for_cur_multiwire_cable = []
					Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_aluminium_cables_DB]
				if Cab_wires[n] != 1 and Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a] * Accessory_count_list[n][2] * Cable_count_for_a_line[n] > Current_breaker_nominal_real[n]:
					# Если многожильный кабель
					# AND
					# у следующего проверяемого сечения пропускной ток * на коэффициент совместной прокладки * количество лучей стал > номинала защиты группы, то всё - сечение подобрано
						Cab_section_min.append(    Sections_of_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a]   ) # выставляем нужное сечение
						a = a + 1000000 # выходим из цикла
				elif Cab_wires[n] == 1 and Currents_for_singlewire_aluminium_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a] * Accessory_count_list[n][2] * Cable_count_for_a_line[n] > Current_breaker_nominal_real[n]:
					# Если одножильный кабель
					# AND
					# у следующего проверяемого сечения пропускной ток * на коэффициент совместной прокладки * количество лучей стал > номинала защиты группы, то всё - сечение подобрано
						Cab_section_min.append(    Sections_of_cables_DB[Sections_of_cables_DB.index(Cab_section_min_no_reduce[n]) + a]   ) # выставляем нужное сечение
						a = a + 1000000 # выходим из цикла
			a = a + 1
		if a < 1000000: # Если же пройдя по всем сечениям с которыми работает программа, так и не удалось подобрать нужное, то выдать предупреждение
			CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_39 + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + Avcounts_Dif_texttrans_46 + str(Sections_of_cables_DB[-1]) + Avcounts_Dif_texttrans_47
			#MessageBox.Show('Для группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' невозможно подобрать сечение кабеля в соответвии с коэффициентами одновременности при совместной прокладке кабельных линий. Это произошло потому что необходимо сечение большее ' + str(Sections_of_cables_DB[-1]) + ' кв.мм с которым работает программа. Сечение кабеля для этой группы выбрано без учёта коэффициента совместной прокладки! Остальные группы посчитаны корректно.', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
			Cab_section_min.append(Cab_section_min_no_reduce[n]) # к сожалению оставить сечение как было
	else:
		Cab_section_min.append(Cab_section_min_no_reduce[n]) # иначе оставить сечение как было





#___________________________________________________________________________________________________________________________________________
#____________________конец модуля по выбору сечений кабелей_________________________________________________________________________________
#___________________________________________________________________________________________________________________________________________













# Теперь проверим, если какое-то из сечений в списке Cab_section_min на ступень больше чем необходимо (по току уставки автомата), то заполним предупредительными
# значениями следующий список (по аналогии с Current_breaker_overestimated). 1 - если сечение завышено, 0 - если нет.
# При этом данная проверка начинает работать при сечениях выше 2.5. Иначе она везде будет предупреждать о превышении.
Cab_section_overestimated = []
for n, i in enumerate(Cab_section_min):
	ReDeclareCableChars(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, i, False) # переобъявляем харакатеристики кабелей по конкретному производителю
	if Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == True  or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == True: # Если текущий проводник медный...
		if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
			Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
			Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_copper_cables_DB]
		else: # если автомат трёхфазный (напряжение 400 В)
			Currents_for_cur_multiwire_cable = []
			Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_copper_cables_DB]
		if Cab_wires[n] != 1 and Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)-1]  *  Accessory_count_list[n][2]  *  Cable_count_for_a_line[n]   > Current_breaker_nominal_DB[Current_breaker_nominal_DB.index(Current_breaker_nominal_min[n])] and i > Sections_of_cables_DB[1]: 
			# Если многожильный кабель
			# AND
			# ток предыдущего (относительно текущего) сечения кабеля * на его понижающий коэффициент * количество лучей > тока текущего аппарата защиты; 
			# AND 
			# текущее сечение кабеля > сечения 2,5 кв.мм (второго элемента в списке Sections_of_cables_DB)
			Cab_section_overestimated.append(1)
		elif Cab_wires[n] == 1 and Currents_for_singlewire_copper_cables_DB[Sections_of_cables_DB.index(i)-1]  *  Accessory_count_list[n][2]  *  Cable_count_for_a_line[n]   > Current_breaker_nominal_DB[Current_breaker_nominal_DB.index(Current_breaker_nominal_min[n])] and i > Sections_of_cables_DB[1]: 
			# Если одножильный кабель
			# AND
			# ток предыдущего (относительно текущего) сечения кабеля * на его понижающий коэффициент * количество лучей > тока текущего аппарата защиты; 
			# AND 
			# текущее сечение кабеля > сечения 2,5 кв.мм (второго элемента в списке Sections_of_cables_DB)
			Cab_section_overestimated.append(1)
		else:
			Cab_section_overestimated.append(0)
	elif Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == False or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == False: # Если текущий проводник алюминиевый...
		if Uavt[n] == 0: # если автомат однофазный (напряжение 230 В)
			Currents_for_cur_multiwire_cable = [] # токи для текущего кабеля (однофазного или трёхфазного, но всегда многожильного, т.к. для одножильного свои токи)
			Currents_for_cur_multiwire_cable = [z for z in Currents_for_1phase_multiwire_aluminium_cables_DB]
		else: # если автомат трёхфазный (напряжение 400 В)
			Currents_for_cur_multiwire_cable = []
			Currents_for_cur_multiwire_cable = [z for z in Currents_for_multiwire_aluminium_cables_DB]
		if Cab_wires[n] != 1 and Currents_for_cur_multiwire_cable[Sections_of_cables_DB.index(i)-1]  *  Accessory_count_list[n][2]  *  Cable_count_for_a_line[n]   > Current_breaker_nominal_DB[Current_breaker_nominal_DB.index(Current_breaker_nominal_min[n])] and i > Sections_of_cables_DB[1]: 
			# Если многожильный кабель
			# AND
			# ток предыдущего (относительно текущего) сечения кабеля * на его понижающий коэффициент * количество лучей > тока текущего аппарата защиты; 
			# AND 
			# текущее сечение кабеля > сечения 2,5 кв.мм (второго элемента в списке Sections_of_cables_DB)
			Cab_section_overestimated.append(1)
		elif Cab_wires[n] == 1 and Currents_for_singlewire_aluminium_cables_DB[Sections_of_cables_DB.index(i)-1]  *  Accessory_count_list[n][2]  *  Cable_count_for_a_line[n]   > Current_breaker_nominal_DB[Current_breaker_nominal_DB.index(Current_breaker_nominal_min[n])] and i > Sections_of_cables_DB[1]: 
			# Если одножильный кабель
			# AND
			# ток предыдущего (относительно текущего) сечения кабеля * на его понижающий коэффициент * количество лучей > тока текущего аппарата защиты; 
			# AND 
			# текущее сечение кабеля > сечения 2,5 кв.мм (второго элемента в списке Sections_of_cables_DB)
			Cab_section_overestimated.append(1)
		else:
			Cab_section_overestimated.append(0)













#__________________________________________________________________________________________________________________________________
# Рассчитываем потери
# и подбираем под них сечения
#__________________________________________________________________________________________________________________________________

deltaU = [] # итоговый список со значениями потерь

selected_by_deltaU_markerlist = [] # список вида [0, 1, 1, 0, 0...] в котором значения "1" и "0" говорят о том, завышено ли сечение не смотря на потери: 1-да, всё равно завышено; 0-нет, сечение как раз нужно из-за потерь


# Функция выбора сечения кабеля по граничному значению потерь
# На входе: 
# deltaU_boundary_value - граничное значение потреь из БД, 
# cur_Cab_section - текущее сечение кабеля
# cur_Moment- текущее значение момента
# Sections_of_cables_DB - список сечений кабеля из БД
# Ckoeff - коэффициент для расчёта потерь из Кнорринга
# cur_Cable_count_for_a_line - количество лучей кабеля
# distr_marker - маркер "делим ли потери на понижающий коэффициент распр.потерь из Настроек?" 2-да, делим, 1-нет, не делим. 
# Round_value_ts - до какого значения округляем
# element_in_elems_avtomats - текущий автомат
# На выходе: 
# - сечение кабеля для которого потери будут меньше или равны граничному значению
# DeltaUres - значение потерь для этого сечения
# overestimated_marker - маркер "завышено ли сечение с учётом потерь?" 1-да, всё равно завышено; 0-нет, сечение как раз нужно из-за потерь
# errtxtstr - строка с возможным предупреждением о невозможности выбрать сечение для какой-то группы
# Пример обращения: Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cmed3f, Cable_count_for_a_line[n], 1, Round_value_ts)
def Select_Cable_Section_by_DeltaUBoundary (deltaU_boundary_value, cur_Cab_section, cur_Moment, Sections_of_cables_DB, Ckoeff, cur_Cable_count_for_a_line, distr_marker, Round_value_ts, element_in_elems_avtomats):
	if distr_marker == 1:
		distr_marker_inside = 1
	else:
		distr_marker_inside = Distributed_Volt_Dropage_koefficient
	# Расчитываем потери
	DeltaUres = (cur_Moment / (cur_Cab_section * cur_Cable_count_for_a_line) / Ckoeff) / distr_marker_inside
	cur_cur_Cab_section = cur_Cab_section
	counter = 1 # счётчик
	errtxtstr = '' # строка с предупреждением о невозможности выбрать сечение
	while DeltaUres > deltaU_boundary_value: # пока потери больше граничного значения
		try:
			cur_cur_Cab_section = Sections_of_cables_DB[Sections_of_cables_DB.index(cur_Cab_section) + counter] # вспомогательное сечение. Увеличивается по мере расчёта потерь пока не станет нужным.
			DeltaUres = (cur_Moment / (cur_cur_Cab_section * cur_Cable_count_for_a_line) / Ckoeff) / distr_marker_inside
			counter = counter + 1
		except IndexError: # если кончился список с сечениями кабелей, а по потерям так и не проходит
			errtxtstr = element_in_elems_avtomats.LookupParameter(Param_Circuit_number).AsString()
			#MessageBox.Show('Для одной из групп не удалось подобрать сечение по потерям, т.к. кончился список возможных сечений, а потери по-прежнему более граничного значения', 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
			break

	# теперь разберёмся завышено ли сечение вручную пользователем или оно выбрано исходя из граничного значения потерь.
	# если предыдущее перед выбранным сечением также проходит по потерям, значит пользователь вручную завысил сечение,
	# если предыдущее сечение уже не проходит, значит выбрано по потерям.
	if (cur_Moment / (Sections_of_cables_DB[Sections_of_cables_DB.index(cur_cur_Cab_section) - 1] * cur_Cable_count_for_a_line) / Ckoeff) / distr_marker_inside > deltaU_boundary_value:
		overestimated_marker = 0
	else:
		overestimated_marker = 1

	# Округлим потери если Только они не менее 0,05%
	if DeltaUres >= 0.05:
		DeltaUres = round(DeltaUres, Round_value_ts)
	else:
		DeltaUres = round(DeltaUres, 2)

	return (cur_cur_Cab_section, DeltaUres, overestimated_marker, errtxtstr)







Found_Distributed_volt_dropage = [] # вспомогательный список с индексами автоматов для которых были приминены распр. потери
# Сразу запишем в этот список индексы автоматов для которых расчёт будет по приведённой длине (это тоже распределённые потери)
for i in QFs_indexes_with_ReducedWireLength:
	Found_Distributed_volt_dropage.append(str(i))
SecNotSelAlert = [] # Список с номерами групп для которых не удалось подобрать сечение по потерям (для вывода предупреждения пользователю)
# Если в параметре 'Наименование электроприёмника' попадётся что-то связанное с освещением или любым другим корнем из списка Volt_Dropage_key, то будем делить потери пополам (распределённые потери)
for n, i in enumerate(Uavt_volts):
	ReDeclareCableChars(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel, UsedWireMarks, Cab_section_min[n], False) # переобъявляем харакатеристики кабелей по конкретному производителю
	znDistDu = 0 # вспомогательная переменная. Содержит значение распр. потерь, если были найдены совпадения из списка GroupsAndNamesFor_Distributed_volt_dropage_from_Storage
	for k in GroupsAndNamesFor_Distributed_volt_dropage_from_Storage:
		# ищем совпадения из списка GroupsAndNamesFor_Distributed_volt_dropage_from_Storage
		# если список из Хранилища ненулевой
		# если имя группы и наим.электропр. у текущего автомата найдены в списке из Хранилища...
		if GroupsAndNamesFor_Distributed_volt_dropage_from_Storage != [] and [elems_avtomats[n].LookupParameter(Param_Circuit_number).AsString(), elems_avtomats[n].LookupParameter(Param_Electric_receiver_Name).AsString()] == [k[0], k[1]]: 
			if k[2] != '0':
				znDistDu = float(k[2]) # запишем значение распр. потерь из хранилища 
				Found_Distributed_volt_dropage.append(str(n)) # запишем порядковый номер автомата во вспомогательный список. Потом по нему выдадим примечание что учли распр. потери.
	list_h = [] # вспомогательный список. Если его длина в следующем цикле будет ненулевой, значит были найдены совпадения из списка Volt_Dropage_key
	for j in Volt_Dropage_key:
		if n not in QFs_indexes_with_ReducedWireLength: # проверяем не был ли уже момент рассчитан по приведённой длине. И если был, то не нужно делить потери пополам по корням слов из Volt_Dropage_key
			if [element.LookupParameter(Param_Electric_receiver_Name).AsString() for element in elems_avtomats][n].upper().find(j) != -1: # ищем совпадения из списка Volt_Dropage_key в параметре Param_Electric_receiver_Name
				list_h.append(str(n)) # запишем порядковый номер автомата во вспомогательный список. 
				Found_Distributed_volt_dropage.append(str(n)) # запишем порядковый номер автомата во вспомогательный список. Потом по нему выдадим примечание что учли распр. потери.
	if Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == True or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == True: # Если текущий проводник медный...
		if i == U3fsqrt3forI: # если напряжение 380 В
			if znDistDu != 0: # если было задано конкретное значение потерь из Хранилища
				deltaU.append(znDistDu) # то перепишем это значение в потери автомата
				selected_by_deltaU_markerlist.append(1) # в этом случае сечение выбрано не исходя из потерь
			elif len(list_h) > 0: # если были найдены совпадения в 'Наименование электроприёмника' со списком Volt_Dropage_key
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] # выходной список фунции подбора сечения по потерям [значение сечения, значения потерь, маркер "выбрано ли сечение по потерям"]
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cmed3f, Cable_count_for_a_line[n], 2, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2]) # записываем маркер "выбрано ли сечение по потерям"
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append(((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cmed3f) / Distributed_Volt_Dropage_koefficient))
					selected_by_deltaU_markerlist.append(1)
			else: # просто считаем потери (не делим на понижающий коэффициент для распределённых потерь)
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cmed3f, Cable_count_for_a_line[n], 1, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cmed3f))
					selected_by_deltaU_markerlist.append(1)
		elif i == U1fforI: # если напряжение 220
			if znDistDu != 0: # если переписываем конкретное значение потерь из БД
				deltaU.append(znDistDu) 
				selected_by_deltaU_markerlist.append(1)
			elif len(list_h) > 0: # если делим потери пополам
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cmed1f, Cable_count_for_a_line[n], 2, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append(((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cmed1f) / Distributed_Volt_Dropage_koefficient))
					selected_by_deltaU_markerlist.append(1)
			else: # если просто считаем потери (не делим на понижающий коэффициент для распределённых потерь)
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cmed1f, Cable_count_for_a_line[n], 1, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else:
					deltaU.append((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cmed1f))
					selected_by_deltaU_markerlist.append(1)
	elif Is_Cu_or_Al(elems_avtomats[n], Param_Wire_brand) == False or Is_Cu_or_Al_withCabManuf(elems_avtomats[n], Param_Wire_brand, Wires_List_UsedinModel) == False: # Если текущий проводник алюминиевый...
		if i == U3fsqrt3forI: # если напряжение 380 В
			if znDistDu != 0: 
				deltaU.append(znDistDu)
				selected_by_deltaU_markerlist.append(1)
			elif len(list_h) > 0: # если были найдены совпадения в 'Наименование электроприёмника' со списком Volt_Dropage_key
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cal3f, Cable_count_for_a_line[n], 2, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append(((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cal3f) / Distributed_Volt_Dropage_koefficient))   
					selected_by_deltaU_markerlist.append(1)
			else: # просто считаем потери (не делим на понижающий коэффициент для распределённых потерь)
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cal3f, Cable_count_for_a_line[n], 1, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cal3f))  
					selected_by_deltaU_markerlist.append(1) 
		elif i == U1fforI: # если напряжение 220
			if znDistDu != 0: 
				deltaU.append(znDistDu)
				selected_by_deltaU_markerlist.append(1)
			elif len(list_h) > 0: # если делим потери пополам
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cal1f, Cable_count_for_a_line[n], 2, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append(((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cal1f) / Distributed_Volt_Dropage_koefficient))
					selected_by_deltaU_markerlist.append(1)
			else: # просто считаем потери (не делим на понижающий коэффициент для распределённых потерь)
				if Select_Cable_by_DeltaU_ts == 1: # если выставлен маркер "да, выбирать сечение по потерям"
					# расчитываем потери и новое сечение
					cur_SecAnddeltaU = [] 
					cur_SecAnddeltaU = Select_Cable_Section_by_DeltaUBoundary(deltaU_boundary_value, Cab_section_min[n], Moment[n], Sections_of_cables_DB, Cal1f, Cable_count_for_a_line[n], 1, Round_value_ts, elems_avtomats[n])
					deltaU.append(cur_SecAnddeltaU[1]) # пишем потери
					Cab_section_min.insert(n, cur_SecAnddeltaU[0]) # меняем сечение по потерям
					Cab_section_min.pop(n+1) # удаляем старое значение сечения из списка
					selected_by_deltaU_markerlist.append(cur_SecAnddeltaU[2])
					SecNotSelAlert.append(cur_SecAnddeltaU[3]) # ловим группу для которой не удалось подобрать сечение по потерям (для предупреждения пользователю)
				else: # если маркер не выставлен, то просто считаем потери
					deltaU.append((Moment[n] / (Cab_section_min[n] * Cable_count_for_a_line[n]) / Cal1f))
					selected_by_deltaU_markerlist.append(1)


# Чистим и доформировываем список с предупреждениями SecNotSelAlert
hlp_lst = []
for i in SecNotSelAlert:
	if i != '' and i not in hlp_lst:
		hlp_lst.append(i)
SecNotSelAlert = [i for i in hlp_lst]
if SecNotSelAlert != []:
	CabSecAlertString = CabSecAlertString + '\r\n\r\n' + Avcounts_Dif_texttrans_48 + ', '.join(SecNotSelAlert) + '. '


# Округлим список потерь до нужных значений
deltaU_hlp = []
for i in deltaU:
	if i >= 0.05:
		deltaU_hlp.append(round(i, Round_value_ts))
	else:
		deltaU_hlp.append(round(i, 2))
# Переобъявляем списки
deltaU = []
deltaU = [i for i in deltaU_hlp]

# Допишем в примечания (Accessory_count_list_readable) инфу о том для каких групп потери были рассчитаны как распределённые
# Сначала прочитстим список с индексами автоматов у которых распр. потери. Потому что на один автомат могут действовать условия распр. потерь
# по поиску части слова и по заданному значению потерь. И список может иметь вид ['0', '1', '1', '2']. А нам нужно ['0', '1', '2'].
if Found_Distributed_volt_dropage != []:
	Found_Distributed_volt_dropage_copy = []
	Found_Distributed_volt_dropage_copy_copy = []
	for i in Found_Distributed_volt_dropage:
		Found_Distributed_volt_dropage_copy.append(i)
	for i in Found_Distributed_volt_dropage:
		for j in Found_Distributed_volt_dropage_copy:
			if i == j:
				Found_Distributed_volt_dropage_copy_copy.append(j) # добавляем совпавший элемент к итоговому списку
				cur_indx = Get_coincidence_in_list (j, Found_Distributed_volt_dropage_copy) # получаем индексы совпавших элементов
				Delete_indexed_elements_in_list (cur_indx, Found_Distributed_volt_dropage_copy) # удаляем совпавшие элементы из списка 
	Accessory_count_list_readable = Accessory_count_list_readable + Avcounts_Dif_texttrans_49
	for i in Found_Distributed_volt_dropage_copy_copy:
		Accessory_count_list_readable = Accessory_count_list_readable + elems_avtomats[int(i)].LookupParameter(Param_Circuit_number).AsString() + ', '
	Accessory_count_list_readable = Accessory_count_list_readable[0:-2] + '.'




# Формируем предупреждение о превышении допустимых потерь в 1,5%
deltaU_greater_than_1_5 = []
for i in deltaU:
	if i > deltaU_boundary_value:
		deltaU_greater_than_1_5.append([element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][deltaU.index(i)]) # вытаскиваем номер группы у которой потери больше 1,5%
		deltaU_greater_than_1_5.append(' - ')
		deltaU_greater_than_1_5.append(str(i))
		deltaU_greater_than_1_5.append('%; ')
# формируем сообщение об ошибке если где-то потери больше 1,5%
if deltaU_greater_than_1_5 != []:
	error_text_in_window = (Avcounts_Dif_texttrans_50 + str(deltaU_boundary_value) + '%: ' + ''.join(deltaU_greater_than_1_5))
	CabSecAlertString = CabSecAlertString + '\r\n\r\n' + error_text_in_window
	#MessageBox.Show(error_text_in_window, 'Предупреждение', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)



# Выводим предупреждения
if CabSecAlertString != '':
	DifferentAlerts_TextForLabel = Avcounts_Dif_texttrans_51
	DifferentAlerts_TextFortextBox = CabSecAlertString
	DifferentAlertsForm().ShowDialog()


#_______конец модуля расчёта потерь_______________________________________________________________________________________________
#__________________________________________________________________________________________________________________________________




















# Подкорректируем список Cab_section_overestimated, уберём флажки "сечение завышено" если сечение завысилось из-за потерь
for n, i in enumerate(selected_by_deltaU_markerlist):
	if i == 0: # если сечение было завышено по условиям потерь
		# заменяем единичку на нолик в списке завышений
		Cab_section_overestimated.insert(n, 0) # меняем сечение по потерям
		Cab_section_overestimated.pop(n+1) # удаляем старое значение из списка







#__________________________# Разбираемся с сечением отдельного проводника PE, если таковое нужно пользователю.________________________________________

# Вернём значения сечений (и остальных характеристик кабелей) на исходные значения из Хранилища
# потому что с PE проводником неохота заморачиваться с поиском сечений по производителю,
# да и не нужно заморачиваться, т.к. основные сечения уже подобраны по производителю и значит для PE тоже такие сечения имеются у производителя.
ReDeclareCableChars('', '', '', '', '', True)

# Функция округляет введённое значение до ближайших больших значений из введённого списка.
# Например: на вводе число 47.5 и список [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300, 400], функция выдаст 50.
# Пример обращения: Round_to_list (47.5, Sections_of_cables_DB)
def Round_to_list (number_in, list_to_round_to):
	a = 0
	while a < len(list_to_round_to):
		if number_in == list_to_round_to[a]:
			number_out = list_to_round_to[a]
		elif number_in > list_to_round_to[a] and number_in <= list_to_round_to[a+1]:
			number_out = list_to_round_to[a+1]
		a = a + 1
	return number_out

# Достаём из чертежа количества жил отдельного проводника PE
PE_Cab_wires_from_drawing = [element.LookupParameter(Param_PE_Conductor_quantity).AsInteger() for element in elems_avtomats]

# Сделаем проверку чтобы количество проводников и/или количество жил не могло быть больше 4, если присутствует отдельный PE-проводник.
for n, i in enumerate(Cab_wires_from_drawing):
	if (i > 4 or Wire_count_for_a_line[n] > 4) and PE_Cab_wires_from_drawing[n] >= 1:
		raise Exception('У группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' есть отдельный PE-проводник. Однако вы указали количество жил или количество проводников основной линии больше 4. Такого не должно быть. Проверьте эту группу вручную и перезапустите расчёт.')
		#MessageBox.Show('У группы ' + [element.LookupParameter(Param_Circuit_number).AsString() for element in elems_avtomats][n] + ' есть отдельный PE-проводник. Однако вы указали количество жил или количество проводников основной линии больше 4. Такого не должно быть. Проверьте эту группу вручную и перезапустите расчёт.', 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()

# Делаем список с расчётными сечениями PE в соответствии с п.1.7.126 ПУЭ о сечении заземляющего проводника
Cab_section_for_separate_PE_calculated = []
for n, i in enumerate(Cab_section_min):
	if i * Cable_count_for_a_line[n] <= 16: # если сечение основных проводников (умноженное на количество лучей) до 16 кв.мм, то PE должен равняться этому сечению... см. ПУЭ
		Cab_section_for_separate_PE_calculated.append(i)
	elif i * Cable_count_for_a_line[n] > 16 and i * Cable_count_for_a_line[n] <= 35:  # если сечение основных проводников (умноженное на количество лучей) больше 16, но меньше или равно 35 кв.мм, то PE 16 кв.мм
		Cab_section_for_separate_PE_calculated.append(16)
	elif i * Cable_count_for_a_line[n] > 35 and PE_Cab_wires_from_drawing[n] <= 1:
		Cab_section_for_separate_PE_calculated.append(Round_to_list ((i * Cable_count_for_a_line[n])/2, Sections_of_cables_DB)) # если сечение основных проводников больше 35 и Количество проводников PE - 1, кв.мм, то PE - половина основных проводников
	elif i * Cable_count_for_a_line[n] > 35 and PE_Cab_wires_from_drawing[n] > 1:
		Cab_section_for_separate_PE_calculated.append(Round_to_list ((Round_to_list ((i * Cable_count_for_a_line[n])/2, Sections_of_cables_DB)/PE_Cab_wires_from_drawing[n]), Sections_of_cables_DB)) # если сечение основных проводников больше 35 и Количество проводников PE больше 1, кв.мм, то PE - половина основных проводников


#__________________________# конец модуля подбора отдельного проводника PE.________________________________________
























# Запишем диаметр условного прохода в зависимости от сечения кабеля
# Но если пользователь удалил Способ прокладки (очистил параметр), то ничего насильно писать не будем.
method_of_laying_from_drawing = [element.LookupParameter(Param_Laying_Method).AsString() for element in elems_avtomats]
internal_pipe_diameter = []
for n, i in enumerate(Cab_section_min):
	if i < 4 and method_of_laying_from_drawing[n] != '': # если сечение меньше 4 кв.мм и пользователь не потёр Способ прокладки, тогда выбрать условный проход. Иначе очистить условный проход.
		internal_pipe_diameter.append('20')
	elif i == 4 and method_of_laying_from_drawing[n] != '':
		internal_pipe_diameter.append('25')
	elif i >= 6 and i <= 10 and method_of_laying_from_drawing[n] != '':
		internal_pipe_diameter.append('32')
	elif i >= 16 and i <= 25 and method_of_laying_from_drawing[n] != '':
		internal_pipe_diameter.append('50')
	else:
		internal_pipe_diameter.append('')

# Теперь вытащим способ прокладки, и если для какого-то элемента в этом списке условный проход окажется '' (пустым), то и сотрём значение самого способа прокладки п. или т. Сделаем его также пустым ''.
# стирать значение способа прокладки НЕ БУДЕМ!
method_of_laying = []
a = 0
while a < len(internal_pipe_diameter):
	for i in internal_pipe_diameter:
		if i == '':
			method_of_laying.append([element.LookupParameter(Param_Laying_Method).AsString() for element in elems_avtomats][a])
			#method_of_laying.append('') # больше не стриаем способ прокладки
		else:
			method_of_laying.append([element.LookupParameter(Param_Laying_Method).AsString() for element in elems_avtomats][a])
		a = a + 1
'''
Неплохо бы помнить, что если параметр Способ прокладки был пустым, потом мы уменьшили сечение кабеля до 25 кв.мм и менее, Способ прокладки останется пустым!
И его придётся вновь записывать вручную! 
При этом 'Условный проход' запишется в соответствии с новым сечением, меньшим 25 кв.мм.
'''



'''функция для записи нужных данных в чертёж
обращение:
Transaction_sukhov (doc, Param_Py, Py_sum, elems_calculation_table, 0)
где:
doc - текущий документ (объявлен в начале программы)
changing_parametr - изменяемый параметр в формате String. То есть тот параметр который нужно искать в выбранном элементе
element_to_write_down - элемент для записи. То есть данные которые нужно записать. Например число 20.
list_in_which_to_write_down - список выбранных элементов среди которых мы должны выбрать один. Например список всех автоматов, в которые будет пошагово производиться запись расчётных данных
current_element_in_list - текущий элемент в предыдущем списке. То есть конкретный объект в который мы записываем нужный нам параметр. В формате Integer, то есть 0, 1 или 2 элемент цифрой.
'''
def Transaction_sukhov (doc, changing_parametr, element_to_write_down, list_in_which_to_write_down, current_element_in_list):
	t = Transaction(doc, 'Change changing_parametr')
	t.Start()
	list_in_which_to_write_down[current_element_in_list].LookupParameter(changing_parametr).Set(element_to_write_down)
	#TransactionManager.Instance.TransactionTaskDone()
	t.Commit()


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



# Пишем пояснения к расчёту в соответствующее семейство
t = Transaction(doc, 'Change note_table')
t.Start()
for n, i in enumerate(elems_note_table):
	i.LookupParameter('Примечание').Set(Accessory_count_list_readable)
t.Commit()







#___________Модуль записи максимальной отключающей способности не менее расчётных токов КЗ_______________________________________________________________
Breaking_capacity_Scale = [4.5, 6, 10, 15, 20, 25, 35, 50, 100, 150, 200] # Шкала токов максимальной отключающей способности (кА)

t = Transaction(doc, 'Write_Breaking_capacity')
t.Start()
for i in elems_avtomats + elems_any_avtomats + elems_reserve_avtomats:
	curMaxShortCircuit = max(i.LookupParameter(Param_Short_Circuit_3ph).AsDouble(), i.LookupParameter(Param_Short_Circuit_1ph).AsDouble()) # максимальный (из 1 и 3 фазного) ток КЗ у данного автомата
	cur_Breaking_capacity = i.LookupParameter(Param_Breaking_capacity).AsDouble() # текущая макс. откл. способность автомата
	if cur_Breaking_capacity <= curMaxShortCircuit:
		Needed_Breaking_capacity = Breaking_capacity_Scale[-1] # Необходимая минимальная откл. способность (из шкалы). # Если ток КЗ больше чем максимальная шкала откл. способностей, то просто возьмём самую большую откл. способность из шкалы.
		for j in Breaking_capacity_Scale:
			if j >= curMaxShortCircuit:
				Needed_Breaking_capacity = j
				break
		i.LookupParameter(Param_Breaking_capacity).Set(Needed_Breaking_capacity)
t.Commit()

#________Конец модуля записи максимальной отключающей способности не менее расчётных токов КЗ____________________________________________________________














TaskDialog.Show(AvcountsComandName_texttrans, Avcounts_Dif_texttrans_52) # Показывает окошко в стиле Ревит

transGroup.Assimilate() # принимаем группу транзакций

#______________________________________________________________________________________________________________________________________________________________________________________
#___________Конец расчёта и записи в автоматы_______________________________________________________________________________________________________________________________________
#______________________________________________________________________________________________________________________________________________________________________________________






















#________Связь с Хранилищем производителей автоматов___(перевести вместе с командой подбора производителя!!!!ы)_______________________________________

# Функции для работы с записью производителя

# Вложенная в SetAVinAllModel функция кодирования автоматов в по нашему супер принципу
# Например "по какой макс. откл. способности выбирать автомат?" и "тип тока утечки"
# На выходе список с уникальными кодами автоматов Вид: [['1', '0', '10.0', 'D', '30.0', '3', '10.0'], ['1', '0', '10.0', 'D', '30.0', '3', '10.0'],....]
'''
Здесь коды автоматов будут отличаться от кодов содержащихся в БД, т.к.
придётся расширить списки с кодами автоматов, т.к. после ABB появились дополнительные параметры по которым автоматы нужно вытаскивать из БД.
0) 0 - 1-фазный автомат, 1 - 3-фазный автомат   				 
1) 0 - просто автомат, 1 - диф.автомат, 2 - рубильник, 3 - УЗО   
2) 16 - Уставка автомата 										 
3) С - Характеристика автомата									 
4) 30 - Ток утечки УЗО											 
5) 3 - Количество полюсов										
6) 6 - Максимальная отключающая способность	(уже выбранная среди трёх возможных Icn, Icu, Ics)
7) AC - тип тока утечки УЗО (бывает A, AC, B)


  0    1     2      3      4     5      6     7  
['1', '0', '16.0', 'C', '30.0', '1', '10.0', 'AC']

'''
# Пример обращения: CB_encoding(elems_avtomats, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCD, Param_Visibility_RCCB, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_TypeLeakage_current)
def CB_encoding (elems_avtomats, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCD, Param_Visibility_RCCB, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_TypeLeakage_current):
	Unique_AVmodelCodes_hlp = [] # выходной список с уникальными кодами Вид: [['1', '0', '10.0', 'D', '30.0', '3', '10.0', 'AC'], ['1', '0', '10.0', 'D', '30.0', '3', '10.0', 'AC'],....]
	for i in elems_avtomats:
		unique_av_code = []
		unique_av_code.append(str(i.LookupParameter(Param_3phase_CB).AsInteger()))
		if Param_Visibility_Knife_switch not in [p.Definition.Name for p in i.Parameters] and Param_Visibility_RCD not in [p.Definition.Name for p in i.Parameters]: # этим условием мы отсекаем автоматы у которых нет параметров Рубильник и УЗО
			unique_av_code.append(str(i.LookupParameter(Param_Visibility_RCCB).AsInteger()))
		elif i.LookupParameter(Param_Visibility_Knife_switch).AsInteger() == 1:
			unique_av_code.append('2')
		elif i.LookupParameter(Param_Visibility_RCD).AsInteger() == 1:
			unique_av_code.append('3')
		else:
			unique_av_code.append(str(i.LookupParameter(Param_Visibility_RCCB).AsInteger()))
		unique_av_code.append(str(i.LookupParameter(Param_Circuit_breaker_nominal).AsDouble()))
		unique_av_code.append(i.LookupParameter(Param_CB_characteristic).AsString())
		unique_av_code.append(str(i.LookupParameter(Param_Leakage_current).AsDouble()))
		unique_av_code.append(str(i.LookupParameter(Param_Pole_quantity).AsInteger()))
		unique_av_code.append(str(i.LookupParameter(Param_Breaking_capacity).AsDouble()))
		unique_av_code.append(i.LookupParameter(Param_TypeLeakage_current).AsString())
		Unique_AVmodelCodes_hlp.append(unique_av_code)
	return Unique_AVmodelCodes_hlp


# Функция декодирует список с разделителями из ES в список со списками
# На входе единый список вида: ['0?!?0?!?16?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?0?!?25?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?1?!?16?!?C?!?30?!?2?!?3.5?!?Basic?!?EKF?!?1', '0?!?0?!?16?!?C?!?0?!?1?!?4?!?iC60N?!?Schneider?!?0']
# На выходе список списков вида: [['0', '0', '16', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ['0', '0', '25', 'C', '0', '1', '3.5', 'AVERES', 'EKF', '1'], ...]
def DecodingListofListsforES (ListwithSeparators):
	znach1hlp = []
	for i in ListwithSeparators:
		znach1hlp.append(i.split('?!?'))
	return znach1hlp



# Функция по считыванию данных из хранилища имён производителей
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
	[znach2.append(i) for i in CS_help] # вид: [[u'(\u043d\u0435\u0442 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f)'], ['EKF', u'AV_\u042d\u043a\u043e\u043d\u043e\u043c', u'AV_\u0411\u0438\u0437\u043d\u0435\u0441', u'EQ_\u041e\u0434\u043d\u0430 \u043b\u0438\u043d\u0435\u0439\u043a\u0430']]

	return znach2



# Вложенная в SetAVinAllModel функция сравнения автоматов с Хранилищем и их записи в модель
# На выходе контрольная сумма. В сколько автоматов были записаны данные и айдишники автоматов в которые удалось записать данные
# Пример обращения: CB_writedown_byManuf(....
def CB_writedown_byManuf (
	elems_avtomats, # выбранные автоматы в модели
	Unique_AVmodelCodes, # уникальные коды автоматов из модели
	AV_ManufNameandLineName_list, # список с характеристиками автоматов только выбранного производителя и его выбранной линейки
	Family_names_avt, Family_names_reserve_avt, Family_names_using_any_avtomats, # имена семейств автоматов с которыми работает программа	
	Param_Breaking_capacity, Param_CB_type, fam_param_names, # имена параметров у автоматов в модели
	Manuf_WebSite, # сайт производителя
	Param_Module_quantity, Param_SchSize_Height, Param_SchSize_Width, Param_SchSize_Depth, # параметры размеров
	Param_TypeLeakage_current, # имя параметра типа тока утечки УЗО
	Way_ofselecting_Breaking_capacity # может быть одно из Icn, Icu, Ics
):
	Written_AVs_hlp = 0 # контрольная сумма. В сколько автоматов были записаны данные
	Ids_written = [] # список айдишников в которые удалось записать данные производителя

	# Определимся какую именно макс.откл.способность будем брать у производителя Icn, Icu, Ics
	Breaking_capacity_index_in_manuf_list = 16 # индекс нужной нам макс.откл.способности
	if Way_ofselecting_Breaking_capacity == 'Icn':
		Breaking_capacity_index_in_manuf_list = 16
	elif Way_ofselecting_Breaking_capacity == 'Icu':
		Breaking_capacity_index_in_manuf_list = 17
	elif Way_ofselecting_Breaking_capacity == 'Ics':
		Breaking_capacity_index_in_manuf_list = 18
	else:
		TaskDialog.Show('Запись конкретного производителя в автоматы', 'Не удалось применить сохранённую макс.откл.способность. Будет использована Icn.')

	t = Transaction(doc, 'Manufacturer Circuit Breakers write down hlp')
	t.Start()
	try:
		for n, i in enumerate(elems_avtomats):
			# если это просто автомат (или резерный) для схем или щитов AND и если он не дифф.
			if i.Name in Family_names_avt+Family_names_reserve_avt and Unique_AVmodelCodes[n][1] == '0': 
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND характеристику AND количество полюсов 
					# AND что в данный автомат ещё не была произведена запись AND что можно записывать откл.спос. (она ближе всего по значению к той что сейчас записана в параметре Param_Breaking_capacity автомата)
					# AND что данный автомат используется в модели
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and Comparison_Translated_CB_characteristic(Unique_AVmodelCodes[n][3], j[3]) and Unique_AVmodelCodes[n][5] == j[5] and str(i.Id) not in Ids_written and Breaking_capacity_writedown_bool(j, AV_ManufNameandLineName_list, i, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list) and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # тип аппарата
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))

			# если это просто автомат (или резерный) для схем или щитов AND и если он дифф.
			elif i.Name in Family_names_avt+Family_names_reserve_avt and Unique_AVmodelCodes[n][1] == '1':  	
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND характеристику AND ток утечки УЗО AND количество полюсов AND тип тока утечки
					# AND что в данный автомат ещё не была произведена запись AND что можно записывать откл.спос. (она ближе всего по значению к той что сейчас записана в параметре Param_Breaking_capacity автомата)
					# AND что данный автомат используется в модели
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and Comparison_Translated_CB_characteristic(Unique_AVmodelCodes[n][3], j[3]) and float(Unique_AVmodelCodes[n][4]) == float(j[4]) and Unique_AVmodelCodes[n][5] == j[5] and Comparison_Translated_TypeLeakage_current(Unique_AVmodelCodes[n][7], j[19]) and str(i.Id) not in Ids_written and Breaking_capacity_writedown_bool(j, AV_ManufNameandLineName_list, i, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list) and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # # тип аппарата
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))

			# если это любой или вводной автомат AND и если он просто автомат.
			elif i.Name in Family_names_using_any_avtomats and Unique_AVmodelCodes[n][1] == '0':  	
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND характеристику AND количество полюсов 
					# AND что в данный автомат ещё не была произведена запись AND что можно записывать откл.спос. (она ближе всего по значению к той что сейчас записана в параметре Param_Breaking_capacity автомата)
					# AND что данный автомат используется в модели
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and Comparison_Translated_CB_characteristic(Unique_AVmodelCodes[n][3], j[3]) and Unique_AVmodelCodes[n][5] == j[5] and str(i.Id) not in Ids_written and Breaking_capacity_writedown_bool(j, AV_ManufNameandLineName_list, i, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list) and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # # тип аппарата				
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))

			# если это любой или вводной автомат AND и если он дифф. автомат.
			elif i.Name in Family_names_using_any_avtomats and Unique_AVmodelCodes[n][1] == '1':  	
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND характеристику AND ток утечки УЗО AND количество полюсов AND тип тока утечки УЗО
					# AND что в данный автомат ещё не была произведена запись AND что можно записывать откл.спос. (она ближе всего по значению к той что сейчас записана в параметре Param_Breaking_capacity автомата)
					# AND что данный автомат используется в модели
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and Comparison_Translated_CB_characteristic(Unique_AVmodelCodes[n][3], j[3]) and float(Unique_AVmodelCodes[n][4]) == float(j[4]) and Unique_AVmodelCodes[n][5] == j[5] and Comparison_Translated_TypeLeakage_current(Unique_AVmodelCodes[n][7], j[19]) and str(i.Id) not in Ids_written and Breaking_capacity_writedown_bool(j, AV_ManufNameandLineName_list, i, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list) and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # # тип аппарата
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))

			# если это любой или вводной автомат AND и если он УЗО.
			elif i.Name in Family_names_using_any_avtomats and Unique_AVmodelCodes[n][1] == '3':  	
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND ток утечки УЗО AND количество полюсов AND тип тока утечки УЗО
					# AND что в данный автомат ещё не была произведена запись
					# AND что данный автомат используется в модели
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and float(Unique_AVmodelCodes[n][4]) == float(j[4]) and Unique_AVmodelCodes[n][5] == j[5] and Comparison_Translated_TypeLeakage_current(Unique_AVmodelCodes[n][7], j[19]) and str(i.Id) not in Ids_written and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # # тип аппарата
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))

			# если это любой или вводной автомат AND и если он рубильник.
			# AND что в данный автомат ещё не была произведена запись
			# AND что данный автомат используется в модели
			elif i.Name in Family_names_using_any_avtomats and Unique_AVmodelCodes[n][1] == '2':  	
				for j in AV_ManufNameandLineName_list:
					# сравниваем фазность AND внешний вид AND уставку AND количество полюсов 
					if Unique_AVmodelCodes[n][0] == j[0] and Unique_AVmodelCodes[n][1] == j[1] and float(Unique_AVmodelCodes[n][2]) == float(j[2]) and Unique_AVmodelCodes[n][5] == j[5] and str(i.Id) not in Ids_written and j[10] != '0': 
						i.LookupParameter(Param_Breaking_capacity).Set(float(j[Breaking_capacity_index_in_manuf_list])) # отключающая способность
						i.LookupParameter(Param_ADSK_product_code).Set(j[7]) # обозначение
						i.LookupParameter(fam_param_names[1]).Set(Manuf_WebSite) # # завод-изготовитель
						i.LookupParameter(Param_CB_type).Set(j[11]) # # тип аппарата
						i.LookupParameter(Param_Module_quantity).Set(int(j[12])) # кол-во модулей
						i.LookupParameter(fam_param_names[2]).Set(j[20]) # наименование
						i.LookupParameter(Param_SpecifyByName).Set(1) # выставляем флажок "Выписывать по наименованию"
						try: # для 2019 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), DisplayUnitType.DUT_MILLIMETERS)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), DisplayUnitType.DUT_MILLIMETERS)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), DisplayUnitType.DUT_MILLIMETERS)) # глубина (мм)
						except: # для 2022 Ревита
							i.LookupParameter(Param_SchSize_Height).Set(UnitUtils.ConvertToInternalUnits(float(j[13]), UnitTypeId.Millimeters)) # высота (мм)
							i.LookupParameter(Param_SchSize_Width).Set(UnitUtils.ConvertToInternalUnits(float(j[14]), UnitTypeId.Millimeters)) # ширина (мм)
							i.LookupParameter(Param_SchSize_Depth).Set(UnitUtils.ConvertToInternalUnits(float(j[15]), UnitTypeId.Millimeters)) # глубина (мм)
						Written_AVs_hlp = Written_AVs_hlp + 1
						Ids_written.append(str(i.Id))
	except:
		raise Exception('Проверьте наличие необходимых параметров в семействах на схеме (лучше всего обновите семейства до последней версии). Также проверьте имена параметров спецификации с которыми работает Программа. Их имена в Настройках - кнопка Имена Параметров должны быть такими же как и у всех аппаратов на схемах.')
	t.Commit()

	exit_list = [Written_AVs_hlp, Ids_written] # выходной список списков
	return exit_list



# Вложенная в CB_writedown_byManuf функция по проверке какую отключающую способность пишем в текущий автомат
# В одной линейке для одинаковых автоматов могут быть разные откл.способности. 
# Писать будем ту которая ближе всего по значению к значению параметра Param_Breaking_capacity в самом автомате.
# Причём на вход этой функции ещё к тому же будем подавать какую именно откл.способность искать (может быть одно из Icn, Icu, Ics)
# На входе:
# Текущий элемент из списка производителя. Например AV_ManufNameandLineName_current = AV_ManufNameandLineName_list[0] вид: ['0', '0', '16', 'C', '0', '1', '4.5', u'\u041a\u043e\u04341', 'EKF', 'Basic', '1', u'\u0422\u0438\u043f \u0410\u0412']
# Список всех аппаратов текущей линейки: AV_ManufNameandLineName_list
# Текущий автомат в который мы записываем откл.способность. Например elems_avtomats_current = elems_avtomats[0] вид: <Autodesk.Revit.DB.AnnotationSymbol object at 0x000000000000002C [Autodesk.Revit.DB.AnnotationSymbol]>
# Имя параметра в который пишем: Param_Breaking_capacity
# На выходе логическое: True если можно записывать откл.спос., False если нельзя
# пример обращения из CB_writedown_byManuf: Breaking_capacity_writedown_bool(j, AV_ManufNameandLineName_list, i, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list)
'''
чтоб тестить
j = AV_ManufNameandLineName_list[0]
i = elems_avtomats[0]

AV_ManufNameandLineName_current = j
elems_avtomats_current = i
'''
def Breaking_capacity_writedown_bool (AV_ManufNameandLineName_current, AV_ManufNameandLineName_list, elems_avtomats_current, Param_Breaking_capacity, Breaking_capacity_index_in_manuf_list):
	exit_bool = False # выходная логическая переменная
	# Для проверки какую отключающую способность писать в автомат, если их несколько в одной линейке, сделаем список
	# со всеми отключающими способностями данного автомата в данной линейке.
	Breaking_capacities_in_current_line = [] # список вида [4.5, 10.0, 6.0]
	for i in AV_ManufNameandLineName_list:
		if i[0:6]+[i[19]] == AV_ManufNameandLineName_current[0:6]+[AV_ManufNameandLineName_current[19]]: # сравнение всех характеристик кроме отключающей способности. ['0', '1', '16', 'C', '30', '2', 'AC']
			Breaking_capacities_in_current_line.append(float(i[Breaking_capacity_index_in_manuf_list])) # добавляем откл.спос. в список
	Breaking_capacities_in_current_line.sort() # сортируем список по возрастанию [4.5, 6.0, 10.0]
	# Смотрим какая откл.спос. сейчас в параметре у автомата
	curBCel = elems_avtomats_current.LookupParameter(Param_Breaking_capacity).AsDouble() # Вид: 10.0
	# И какая у текущего элемента производителя
	curBCmanuf = float(AV_ManufNameandLineName_current[Breaking_capacity_index_in_manuf_list])
	# Теперь проверяем: если у текущего элемента производителя AV_ManufNameandLineName_current откл.спос. равна или
	# ближе всего (по минимуму) к той что сейчас записана в параметре автомата, то перепишем откл.спос. производителя в автомат
	if curBCel == curBCmanuf:
		exit_bool = True
	elif curBCel > curBCmanuf:
		exit_bool = False
	else:
		for i in Breaking_capacities_in_current_line:
			if i >= curBCel and i < curBCmanuf:
				exit_bool = False
				break
			elif i >= curBCel and i == curBCmanuf:
				exit_bool = True
				break

	return exit_bool



# Вложенная в CB_writedown_byManuf функция по сравнению характеристики автоматов из модели и из Хранилища
# независимо от того на русском или английском записаны данные характеристики
# Смысл вот в таком сравнении Unique_AVmodelCodes[n][3] == j[3] - True или False
# Пример обращения: Comparison_Translated_CB_characteristic(Unique_AVmodelCodes[n][3], j[3])
# Например Comparison_Translated_CB_characteristic('С', 'C')  (характеристика из модели, характеристика из Хранилища)
def Comparison_Translated_CB_characteristic (charac_model, charac_storage):
	exit_bool = False # выходная логическая переменная
	charac_model = charac_model.upper() # Перевод в верхний регистр для сравнения
	charac_storage = charac_storage.upper()
	# Условия соответствия, т.е. True
	if charac_model == charac_storage: # Просто совпадение
		exit_bool = True
	elif (charac_model == 'B' or charac_model == 'В') and (charac_storage == 'B' or charac_storage == 'В'): # Первая русская, вторя латинская
		exit_bool = True
	elif (charac_model == 'С' or charac_model == 'C') and (charac_storage == 'С' or charac_storage == 'C'): # Первая русская, вторя латинская
		exit_bool = True
	elif (charac_model == 'А' or charac_model == 'A') and (charac_storage == 'А' or charac_storage == 'A'): # Первая русская, вторя латинская
		exit_bool = True

	return exit_bool




# Вложенная в CB_writedown_byManuf функция по сравнению типа тока утечки УЗО из модели и из Хранилища
# независимо от того на русском или английском записаны данные
# Смысл вот в таком сравнении Unique_AVmodelCodes[n][7] == j[19] - True или False
# Пример обращения: Comparison_Translated_TypeLeakage_current(Unique_AVmodelCodes[n][7], j[19])
# Например Comparison_Translated_TypeLeakage_current('AC', 'AC')  (тип утечки из модели, тип утечки из Хранилища)
def Comparison_Translated_TypeLeakage_current (TypeLeakage_current_model, TypeLeakage_current_storage):
	exit_bool = False # выходная логическая переменная
	TypeLeakage_current_model = TypeLeakage_current_model.upper() # Перевод в верхний регистр для сравнения
	TypeLeakage_current_storage = TypeLeakage_current_storage.upper()
	# Условия соответствия, т.е. True
	if TypeLeakage_current_model == TypeLeakage_current_storage: # Просто совпадение
		exit_bool = True
	elif (TypeLeakage_current_model == 'B' or TypeLeakage_current_model == 'В') and (TypeLeakage_current_storage == 'B' or TypeLeakage_current_storage == 'В'): # Первая русская, вторя латинская
		exit_bool = True
	elif (TypeLeakage_current_model == 'АС' or TypeLeakage_current_model == 'AC') and (TypeLeakage_current_storage == 'АС' or TypeLeakage_current_storage == 'AC'): # Первая русская, вторя латинская
		exit_bool = True
	elif (TypeLeakage_current_model == 'А' or TypeLeakage_current_model == 'A') and (TypeLeakage_current_storage == 'А' or TypeLeakage_current_storage == 'A'): # Первая русская, вторя латинская
		exit_bool = True

	return exit_bool



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


# Окошко с айдишниками незаписанных автоматов. Используется в функции SetAVinAllModel.
class ManufacturerSelect_AlertForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._ManufacturerSelect_AlertForm_label1 = System.Windows.Forms.Label()
		self._textBox1 = System.Windows.Forms.TextBox()
		self._ManufacturerSelect_AlertForm_OKbutton = System.Windows.Forms.Button()
		self.SuspendLayout()
		# 
		# ManufacturerSelect_AlertForm_label1
		# 
		self._ManufacturerSelect_AlertForm_label1.Location = System.Drawing.Point(24, 20)
		self._ManufacturerSelect_AlertForm_label1.Name = "ManufacturerSelect_AlertForm_label1"
		self._ManufacturerSelect_AlertForm_label1.Size = System.Drawing.Size(355, 67)
		self._ManufacturerSelect_AlertForm_label1.TabIndex = 0
		self._ManufacturerSelect_AlertForm_label1.Text = "Данные производителя были записаны в 50 элементов из 100. Для следующих элементов у Производителя нет соответствуюих аппаратов. ID: "
		# 
		# textBox1
		# 
		self._textBox1.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._textBox1.Location = System.Drawing.Point(24, 90)
		self._textBox1.Multiline = True
		self._textBox1.Name = "textBox1"
		self._textBox1.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
		self._textBox1.Size = System.Drawing.Size(355, 85)
		self._textBox1.TabIndex = 1
		# 
		# ManufacturerSelect_AlertForm_OKbutton
		# 
		self._ManufacturerSelect_AlertForm_OKbutton.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._ManufacturerSelect_AlertForm_OKbutton.Location = System.Drawing.Point(165, 183)
		self._ManufacturerSelect_AlertForm_OKbutton.Name = "ManufacturerSelect_AlertForm_OKbutton"
		self._ManufacturerSelect_AlertForm_OKbutton.Size = System.Drawing.Size(80, 23)
		self._ManufacturerSelect_AlertForm_OKbutton.TabIndex = 2
		self._ManufacturerSelect_AlertForm_OKbutton.Text = "OK"
		self._ManufacturerSelect_AlertForm_OKbutton.UseVisualStyleBackColor = True
		self._ManufacturerSelect_AlertForm_OKbutton.Click += self.ManufacturerSelect_AlertForm_OKbuttonClick
		# 
		# ManufacturerSelect_AlertForm
		# 
		self.ClientSize = System.Drawing.Size(412, 216)
		self.Controls.Add(self._ManufacturerSelect_AlertForm_OKbutton)
		self.Controls.Add(self._textBox1)
		self.Controls.Add(self._ManufacturerSelect_AlertForm_label1)
		self.Name = "ManufacturerSelect_AlertForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = "Запись конкретного производителя в автоматы"
		self.Load += self.ManufacturerSelect_AlertFormLoad
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def ManufacturerSelect_AlertForm_OKbuttonClick(self, sender, e):
		self.Close()

	def ManufacturerSelect_AlertFormLoad(self, sender, e):
		self.ActiveControl = self._ManufacturerSelect_AlertForm_OKbutton # ставим фокус на кнопку ОК чтобы по Enter её быстро нажимать
		self._ManufacturerSelect_AlertForm_label1.Text = AlertFormTextLabel
		self._textBox1.Text = Ids_notwritten_Textstring






# Функция записи всех автоматов выбранного производителя на все чертёжные виды модели или только в выбранные элементы. 
# ЭТА ФУНКЦИЯ ТУТ НЕМНОГО ОТЛИЧАЕТСЯ ОТ ТАКОЙ ЖЕ В СКРИПТЕ ManufacturerSelect.py !!!!!!!!!!!!
# ТУТ МЫ НЕ ПРОПИСЫВАЕМ ПОЛЮСА ПОТОМУ ЧТО УЖЕ РАНЬШЕ ИХ ЗАПИСАЛИ В АВТОМАТЫ!!!!!!!!!
def SetAVinAllModel (Family_names_avt, Family_names_reserve_avt, Family_names_using_any_avtomats,
Param_3phase_CB,
Param_Visibility_Knife_switch,
Param_Visibility_RCCB,
Param_Visibility_RCD,
Param_Circuit_breaker_nominal,
Param_CB_characteristic,
Param_Leakage_current,
Param_Pole_quantity,
Param_Breaking_capacity,
Param_CB_type,
schemaGuid_for_ManufNames_ManufacturerSelect, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelect,
schemaGuid_for_AV_ListDB_ManufacturerSelect, FieldName_for_AV_ListDB_ManufacturerSelect,
Way_of_writing, # способ записи: 0 - если во всю модель целиком, 1 - если только в выбранные автоматы. 
elems, # выбранные элементы или пустой список (если хотим во всю модель целиком). 
Param_Module_quantity, Param_SchSize_Height, Param_SchSize_Width, Param_SchSize_Depth, # параметры размеров
Param_TypeLeakage_current, # имя параметра типа тока утечки УЗО
Way_ofselecting_Breaking_capacity # может быть одно из Icn, Icu, Ics
): 

	'''чтоб тестить 
	Way_of_writing = 1
	elems = elems_hlp
	'''

	# Собираем автоматы из модели
	using_avtomats = Family_names_avt + Family_names_reserve_avt + Family_names_using_any_avtomats # все используемые имена семейств автоматов
	elems_avtomats = [] # семейства автоматических выключателей выбранные программно
	if Way_of_writing == 0:
		for i in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_GenericAnnotation).WhereElementIsNotElementType().ToElements():
			if using_avtomats.count(i.Name) > 0: elems_avtomats.append(i) 
	elif Way_of_writing == 1:
		for i in elems: 
			if i.Name in using_avtomats: elems_avtomats.append(i)

	# Кодируем их по нашему супер принципу
	Unique_AVmodelCodes = [] # Вид: [['0', '0', '16.0', 'C', '30.0', '1', '10.0', 'AC'], ['0', '1', '16.0', 'C', '30.0', '2', '10.0', 'AC']]
	Unique_AVmodelCodes = CB_encoding(elems_avtomats, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCD, Param_Visibility_RCCB, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_TypeLeakage_current)

	transGroup = TransactionGroup(doc, 'Manufacturer Circuit Breakers write down')
	transGroup.Start()
	'''
	# Прописываем количество полюсов в автоматы
	Poles_writedown(Unique_AVmodelCodes, elems_avtomats, Param_Pole_quantity)
	# После этого снова перекодируем наши автоматы
	Unique_AVmodelCodes = CB_encoding(elems_avtomats, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCD, Param_Visibility_RCCB, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_TypeLeakage_current)
	'''
	# Формируем аналогичный список из Хранилища. В нём будут коды автоматов конкретного производителя
	# объявляем znach2. Вид: [['EKF', 'AV_Averes', 'AV_Basic', 'AV_PROxima', 'EQ_Basic', 'EQ_Averes', 'EQ_PROxima'], [u'(нет производителя)']]
	# причём в нём используемая линейка автоматов идёт первой с префиксом 'AV_' и аналогично первая 'EQ_' для оборудования
	znach2 = ReadES_ManufacturerSelect(schemaGuid_for_ManufNames_ManufacturerSelect, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelect)
	# Считываем автоматы из Хранилища. [['0', '0', '16', 'C', '0', '1', '3.5', u'\u041a\u043e\u04341', 'EKF', 'Basic', '1', 'Тип для схемы'], ... ]
	znach1 = ReadES_ManufacturerSelect(schemaGuid_for_AV_ListDB_ManufacturerSelect, ProjectInfoObject, FieldName_for_AV_ListDB_ManufacturerSelect) # [['0', '0', '16', 'C', '0', '1', '3.5', u'\u041a\u043e\u04341', 'EKF', 'Basic', '1', u'\u0422\u0438\u043f \u0410\u0412'],...]

	# Для ускорения работы программы составим список с характеристиками автоматов только выбранного производителя и его выбранной линейки
	AV_ManufNameandLineName_list = []
	for i in znach1:
		if i[8] == znach2[0][0] and i[9] == znach2[0][1][3:] and i[10] == '1':
			AV_ManufNameandLineName_list.append(i) # Вид: [['0', '0', '6', 'B', '0', '1', '4.5', 'mcb4729-1-06-b', 'ekf', 'basic', '1', u'ВА 47-29', '1', '80', '18', '72'],,...]

	Manuf_WebSite = znach2[0][-1] # сайт производителя 'https://ekfgroup.com/' # для записи в fam_param_names[1]

	Written_AVs_hlp = 0 # контрольная сумма. В сколько автоматов были записаны данные
	Ids_written = [] # список айдишников в которые удалось записать данные производителя

	# Теперь можно начинать записывать данные в автоматы
	exit_list_hlp = CB_writedown_byManuf(elems_avtomats, Unique_AVmodelCodes, AV_ManufNameandLineName_list, Family_names_avt, Family_names_reserve_avt, Family_names_using_any_avtomats, Param_Breaking_capacity, Param_CB_type, fam_param_names, Manuf_WebSite, Param_Module_quantity, Param_SchSize_Height, Param_SchSize_Width, Param_SchSize_Depth, Param_TypeLeakage_current, Way_ofselecting_Breaking_capacity)
	#  [Written_AVs_hlp, Ids_written] # выходной список списков
	Ids_written = Ids_written + exit_list_hlp[1] # добавляем айдишники записанных в этот раз аппаратов [['494051', '494059', '494086', '494100']]
	Written_AVs_hlp = Written_AVs_hlp + exit_list_hlp[0] # плюсуем количество записанных автоматов. Вид: 4

	# Если не все автоматы записались, то дальше начинаем искать по другим линейкам у производителя
	if Written_AVs_hlp != len(elems_avtomats):
		# Теперь нужно записать данные производителя в ещё незаписанные автоматы из других линеек
		# Для этого переназначим список элементов. Оставим в нём только ещё незаписанные автоматы
		elems_avtomats_2iter = [] # список 2-й итерации
		for i in elems_avtomats:
			if str(i.Id) not in Ids_written:
				elems_avtomats_2iter.append(i)

		# Закодируем оставшиеся автоматы:
		Unique_AVmodelCodes_2iter = [] # Вид: [['0', '0', '32.0', 'C', '30.0', '1', '3.5'], ['0', '1', '32.0', 'C', '30.0', '1', '3.5'],....]
		Unique_AVmodelCodes_2iter = CB_encoding(elems_avtomats_2iter, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCD, Param_Visibility_RCCB, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_TypeLeakage_current)

		AVs_exceptmain_list = [] # список с названиями линеек автоматов из Хранилища, кроме выбранной пользователем линейки. Вид: ['AV_Averes', 'AV_PROxima']
		for i in znach2[0][2:]: # вид: ['AV_Averes', 'AV_PROxima', 'EQ_Basic', 'EQ_Averes', 'EQ_PROxima']
			if 'AV_' in i:
				AVs_exceptmain_list.append(i)
		# Составим список с кодами автоматов других линеек кроме той что изначально выбрал Пользователь (из Хранилища)
		AV_ManufNameandLineName_list_2iter = [] # Вид: [['0', '0', '32', 'C', '0', '1', '3.5', u'\u041a\u043e\u04342', 'EKF', 'Averes', '1', u'\u0422\u0438\u043f \u0410\u0412'], ['0', '1', '32', 'C', '30', '1', '3.5', u'\u041a\u043e\u04342', 'EKF', 'Averes', '1', u'\u0422\u0438\u043f \u0410\u0412']]
		for i in znach1:
			if i[8] == znach2[0][0] and 'AV_'+i[9] in AVs_exceptmain_list and i[10] == '1':
				AV_ManufNameandLineName_list_2iter.append(i) # Вид: [['0', '0', '16', 'C', '0', '1', '3.5', u'\u041a\u043e\u04341', 'EKF', 'Basic', '1', u'\u0422\u0438\u043f \u0410\u0412'],...]

		# прописываем данные из других линеек в оставшиеся автоматы в модели
		# Вот тут бага была) invalid literal for float(): 16А - из-за списка производителя от Вити))
		exit_list_hlp = CB_writedown_byManuf(elems_avtomats_2iter, Unique_AVmodelCodes_2iter, AV_ManufNameandLineName_list_2iter, Family_names_avt, Family_names_reserve_avt, Family_names_using_any_avtomats, Param_Breaking_capacity, Param_CB_type, fam_param_names, Manuf_WebSite, Param_Module_quantity, Param_SchSize_Height, Param_SchSize_Width, Param_SchSize_Depth, Param_TypeLeakage_current, Way_ofselecting_Breaking_capacity)
		#  [Written_AVs_hlp, Ids_written] # выходной список списков
		Ids_written = Ids_written + exit_list_hlp[1] # добавляем айдишники записанных в этот раз аппаратов [['494051', '494059', '494086', '494100']]
		Written_AVs_hlp = Written_AVs_hlp + exit_list_hlp[0] # плюсуем количество записанных автоматов. Вид: 4


	# Находим айдишники незаписанных аппаратов:
	t = Transaction(doc, 'Set_Param_SpecifyByName_toZero')
	t.Start()
	Ids_notwritten = [] # список с айдишниками автоматов в которые не прописались данные производителя
	for i in elems_avtomats:
		if str(i.Id) not in Ids_written:
			Ids_notwritten.append(str(i.Id))
			i.LookupParameter(Param_SpecifyByName).Set(0) # И тут же сбрасываем флажок 'Выписывать по наименованию'
	t.Commit()

	transGroup.Assimilate() # принимаем группу транзакций

	hlplst = []
	for i in Ids_notwritten:
		hlplst.append(int(i))
	Ids_notwritten = []
	Ids_notwritten = [str(i) for i in hlplst]

	#TaskDialog.Show('Запись конкретного производителя в автоматы', 'Данные производителя были записаны в ' + str(Written_AVs_hlp) + ' элементов из ' + str(len(elems_avtomats)))
	if Written_AVs_hlp == len(elems_avtomats):
		MessageBox.Show('Данные производителя были записаны в ' + str(Written_AVs_hlp) + ' элементов из ' + str(len(elems_avtomats)) + '.', 'Запись конкретного производителя в автоматы', MessageBoxButtons.OK, MessageBoxIcon.Asterisk)
	#elif len(Ids_notwritten) < 0: # при большой длине у пользователя может быть шок, да и бага вылетает когда окошко в экран не влезает
	#	MessageBox.Show('Данные производителя были записаны в ' + str(Written_AVs_hlp) + ' элементов из ' + str(len(elems_avtomats)) + '. Для следующих элементов у Производителя нет соответствуюих аппаратов. ID: ' + ';'.join(Ids_notwritten), 'Запись конкретного производителя в автоматы', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
	else:
		global AlertFormTextLabel
		AlertFormTextLabel = 'Данные производителя были записаны в ' + str(Written_AVs_hlp) + ' элементов из ' + str(len(elems_avtomats)) + '. Для следующих элементов у Производителя нет соответствуюих аппаратов. ID: '
		global Ids_notwritten_Textstring
		Ids_notwritten_Textstring = ';'.join(Ids_notwritten)
		ManufacturerSelect_AlertForm().ShowDialog()


#__________________Работа с хранилищем настроек выбора производителя из настроек Теслы__________________________________________________________________
# По какой откл. способности выбирать автоматы?
# Way_ofselecting_Breaking_capacity = 'Icn' # может быть одно из Icn, Icu, Ics

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

znach_ManufacturerSettings = ReadES_ManufacturerSelect(schemaGuid_for_ManufacturerSettings, ProjectInfoObject, FieldName_for_ManufacturerSettings)
Way_ofselecting_Breaking_capacity = znach_ManufacturerSettings[0][0]

#________________________________________________________________________________________________________________________________________________________




#_______Работа с хранилищем автоматов______________

# Guid для этого хранилища
schemaGuid_for_AV_ListDB_ManufacturerSelect = System.Guid(Guidstr_AV_ListDB_ManufacturerSelect)

#Получаем Schema:
schAV_ListDB = Schema.Lookup(schemaGuid_for_AV_ListDB_ManufacturerSelect)

ES_AVEQ_OK_marker = [] # маркер того что оба хранилища в порядке. Будет список длиной в два элемента если всё ок. Иначе отбой.

# Проверяем корректность хранилища и продолжаем работу только если оно существует
if schAV_ListDB is not None:
	# Считываем данные о последнем использованном элементе из Хранилища
	#Получаем Schema:
	sch1 = Schema.Lookup(schemaGuid_for_AV_ListDB_ManufacturerSelect)
	#Получаем Entity из элемента:
	ent1 = ProjectInfoObject.GetEntity(sch1)
	#Уже знакомым способом получаем «поля»:
	field2 = sch1.GetField(FieldName_for_AV_ListDB_ManufacturerSelect)
	#Для считывания значений используем метод Entity.Get:
	znach1 = ent1.Get[IList[str]](field2) 

	# пересоберём список чтобы привести его к нормальному виду
	CS_help = []
	[CS_help.append(i) for i in znach1]
	znach1 = []
	[znach1.append(i) for i in CS_help] # вид: ['0?!?0?!?16?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?0?!?25?!?C?!?0?!?1?!?3.5?!?AVERES?!?EKF?!?1', '0?!?1?!?16?!?C?!?30?!?2?!?3.5?!?Basic?!?EKF?!?1', '0?!?0?!?16?!?C?!?0?!?1?!?4?!?iC60N?!?Schneider?!?0']
	# Перекодируем его в список со списками:
	CS_help = []
	CS_help = DecodingListofListsforES(znach1)
	znach1 = []
	[znach1.append(i) for i in CS_help] # вид: [['0', '0', '16', 'C', '0', '1', '3.5', 'AVERES', 'EKF', u'\u042d\u043a\u043e\u043d\u043e\u043c', '1'], ['0', '0', '16', 'C', '0', '1', '3.5', 'AVERES', 'EKF', u'\u0411\u0438\u0437\u043d\u0435\u0441', '0'], ['0', '0', '25', 'C', '0', '1', '3.5', 'AVERES', 'EKF', u'\u042d\u043a\u043e\u043d\u043e\u043c', '1'], ['0', '1', '16', 'C', '30', '2', '3.5', 'Basic', 'EKF', u'\u042d\u043a\u043e\u043d\u043e\u043c', '1'], ['0', '0', '16', 'C', '0', '1', '4', 'iC60N', 'Schneider', u'\u042d\u043a\u043e\u043d\u043e\u043c', '0']]

	ES_AVEQ_OK_marker.append('ok') # дописываем в маркер что это хранилище в порядке


#_______Работа с хранилищем имён производителей______________
# Guid для этого хранилища
schemaGuid_for_ManufNames_ManufacturerSelect = System.Guid(Guidstr_ManufNames_ManufacturerSelect)

#Получаем Schema:
schAV_ListDB = Schema.Lookup(schemaGuid_for_ManufNames_ManufacturerSelect)

# Проверяем корректность хранилища и продолжаем работу только если оно существует
if schAV_ListDB is not None:
	# объявляем znach2. Вид: [['EKF', 'AV_Averes', 'AV_Basic', 'AV_PROxima', 'EQ_Basic', 'EQ_Averes', 'EQ_PROxima', 'https://ekfgroup.com/'], [u'(нет производителя)']]
	znach2 = ReadES_ManufacturerSelect(schemaGuid_for_ManufNames_ManufacturerSelect, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelect)
	ES_AVEQ_OK_marker.append('ok') # дописываем в маркер что это хранилище в порядке

# Далее продолжаем только если оба хранилища в порядке и производитель был выбран:
if len(ES_AVEQ_OK_marker) == 2:
	if znach2[0][0] != '(нет производителя)': 
		# Пишем данные из Хранилища в автоматы
		SetAVinAllModel (avt_family_names, using_reserve_avtomats, using_any_avtomats, Param_3phase_CB, Param_Visibility_Knife_switch, Param_Visibility_RCCB, Param_Visibility_RCD, Param_Circuit_breaker_nominal, Param_CB_characteristic, Param_Leakage_current, Param_Pole_quantity, Param_Breaking_capacity, Param_CB_type, schemaGuid_for_ManufNames_ManufacturerSelect, ProjectInfoObject, FieldName_for_ManufNames_ManufacturerSelect, schemaGuid_for_AV_ListDB_ManufacturerSelect, FieldName_for_AV_ListDB_ManufacturerSelect, 1, elems, Param_Module_quantity, Param_SchSize_Height, Param_SchSize_Width, Param_SchSize_Depth, Param_TypeLeakage_current, Way_ofselecting_Breaking_capacity)



#________Конец модуля связи с Хранилищем производителей автоматов___________________________________________________________________________





























#______________________________________________________________________________________________________________________________________________________________________________________
# Записываем результаты в расчётные таблички через окно.
#______________________________________________________________________________________________________________________________________________________________________________________

'''
# Это уже не нужно. Раньше было.
#сообщение об ошибке которое должно вывестись в следующем модуле
error_text_in_window = 'Ошибка! Неправильно указано напряжение в выбранной Вами расчётной таблице результатов. Параметр напряжения в этих таблицах должен быть строго (!) либо 400, либо 230 В. Результаты расчётов не были записаны в чертёж! Измените параметры напряжения в таблице результатов и запустите расчёт заново.'
'''

# Записываем данные в расчётную табличку
# Сначала вытащим из неё напряжение питания, чтобы понимать какой будет общий ток.
Upit_calculation_table = [element.LookupParameter(Param_Upit).AsDouble() for element in elems_calculation_table]
# это получился список вида [380.0]. Теперь переведём 380 и 220 вольт в 0,658 и 0,22 соответственно
Upit_calculation_table_volts = []
for i in Upit_calculation_table:
	if i == 380 or i == 400: Upit_calculation_table_volts.append(U3fsqrt3forI)
	if i == 220 or i == 230: Upit_calculation_table_volts.append(U1fforI)
	if i != 380 and i != 220 and i != 230 and i != 400: # Если напряжение отличается от 220,230,380,400 В, то примем как-будто оно трёхфазное. Потом всё равно после окошка напряжение в табличку запишется как полагается.
		Upit_calculation_table_volts.append(U3fsqrt3forI)
		# raise Exception(error_text_in_window) # это уже не нужно. Раньше было.
		#MessageBox.Show(error_text_in_window, 'Ошибка', MessageBoxButtons.OK, MessageBoxIcon.Exclamation)
		#sys.exit()


# Готовим исходные данные для заполнения окошка Кс лифтов
elems_avtomats_elevators = [] # автоматы у которых классификация нагруок - лифты
elems_avtomats_elevators_groupsnames = [] # имена групп автоматов "лифтов"
for i in elems_avtomats:
	try:
		if List_in_string(Load_Class_elevators, i.LookupParameter(Param_Load_Class).AsValueString()):
			elems_avtomats_elevators.append(i)
			elems_avtomats_elevators_groupsnames.append(i.LookupParameter(Param_Circuit_number).AsString())
	except System.MissingMemberException:
		raise Exception(Avcounts_Dif_texttrans_53 + str(i.Id) + Avcounts_Dif_texttrans_54 + Param_Load_Class + Avcounts_Dif_texttrans_55)
		break


# Поставим проверку чтобы не было повторяющихся имён групп у лифтов. Иначе потом при расчёте несколько раз будут учитываться одни и те же лифты.
hlpcntlst = [] # вспомогательный список с повторяющимися группами
for i in elems_avtomats_elevators_groupsnames:
	if elems_avtomats_elevators_groupsnames.count(i) > 1:
		if i not in hlpcntlst:
			hlpcntlst.append(i)
if hlpcntlst != []:
	raise Exception(Avcounts_Dif_texttrans_56 + ', '.join(hlpcntlst) +  Avcounts_Dif_texttrans_57)



elevators_groupsnames_below12 = [] # группы у которых лифты до 12 этажей
elevators_groupsnames_above12 = [] # группы у которых лифты 12 и выше этажей

# Окошко коэффициентов спроса лифтов

class KsElevatorsForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._OK_button = System.Windows.Forms.Button()
		self._Ksbelow12_dataGridView = System.Windows.Forms.DataGridView()
		self._Ksabove12_dataGridView = System.Windows.Forms.DataGridView()
		self._KsElevatorsForm_label1 = System.Windows.Forms.Label()
		self._MoveLeft_button = System.Windows.Forms.Button()
		self._MoveRight_button = System.Windows.Forms.Button()
		self._KsBelow12_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._KsAbove12_Column = System.Windows.Forms.DataGridViewTextBoxColumn()
		self._Ksbelow12_dataGridView.BeginInit()
		self._Ksabove12_dataGridView.BeginInit()
		self.SuspendLayout()
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom
		self._OK_button.Location = System.Drawing.Point(177, 327)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(75, 23)
		self._OK_button.TabIndex = 0
		self._OK_button.Text = "OK"
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# Ksbelow12_dataGridView
		# 
		self._Ksbelow12_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom
		self._Ksbelow12_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._Ksbelow12_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._KsBelow12_Column]))
		self._Ksbelow12_dataGridView.Location = System.Drawing.Point(12, 48)
		self._Ksbelow12_dataGridView.Name = "Ksbelow12_dataGridView"
		self._Ksbelow12_dataGridView.ReadOnly = True
		self._Ksbelow12_dataGridView.Size = System.Drawing.Size(159, 258)
		self._Ksbelow12_dataGridView.TabIndex = 1
		# 
		# Ksabove12_dataGridView
		# 
		self._Ksabove12_dataGridView.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom
		self._Ksabove12_dataGridView.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize
		self._Ksabove12_dataGridView.Columns.AddRange(System.Array[System.Windows.Forms.DataGridViewColumn](
			[self._KsAbove12_Column]))
		self._Ksabove12_dataGridView.Location = System.Drawing.Point(258, 48)
		self._Ksabove12_dataGridView.Name = "Ksabove12_dataGridView"
		self._Ksabove12_dataGridView.ReadOnly = True
		self._Ksabove12_dataGridView.Size = System.Drawing.Size(159, 258)
		self._Ksabove12_dataGridView.TabIndex = 3
		# 
		# KsElevatorsForm_label1
		# 
		self._KsElevatorsForm_label1.Location = System.Drawing.Point(12, 9)
		self._KsElevatorsForm_label1.Name = "KsElevatorsForm_label1"
		self._KsElevatorsForm_label1.Size = System.Drawing.Size(405, 36)
		self._KsElevatorsForm_label1.TabIndex = 5
		self._KsElevatorsForm_label1.Text = KsElevatorsForm_texttrans_1
		# 
		# MoveLeft_button
		# 
		self._MoveLeft_button.Location = System.Drawing.Point(177, 129)
		self._MoveLeft_button.Name = "MoveLeft_button"
		self._MoveLeft_button.Size = System.Drawing.Size(75, 23)
		self._MoveLeft_button.TabIndex = 6
		self._MoveLeft_button.Text = "<<"
		self._MoveLeft_button.UseVisualStyleBackColor = True
		self._MoveLeft_button.Click += self.MoveLeft_buttonClick
		# 
		# MoveRight_button
		# 
		self._MoveRight_button.Location = System.Drawing.Point(177, 158)
		self._MoveRight_button.Name = "MoveRight_button"
		self._MoveRight_button.Size = System.Drawing.Size(75, 23)
		self._MoveRight_button.TabIndex = 7
		self._MoveRight_button.Text = ">>"
		self._MoveRight_button.UseVisualStyleBackColor = True
		self._MoveRight_button.Click += self.MoveRight_buttonClick
		# 
		# KsBelow12_Column
		# 
		self._KsBelow12_Column.HeaderText = KsElevatorsForm_texttrans_2
		self._KsBelow12_Column.Name = "KsBelow12_Column"
		self._KsBelow12_Column.ReadOnly = True
		# 
		# KsAbove12_Column
		# 
		self._KsAbove12_Column.HeaderText = KsElevatorsForm_texttrans_3
		self._KsAbove12_Column.Name = "KsAbove12_Column"
		self._KsAbove12_Column.ReadOnly = True
		# 
		# KsElevatorsForm
		# 
		self.ClientSize = System.Drawing.Size(437, 362)
		self.Controls.Add(self._MoveRight_button)
		self.Controls.Add(self._MoveLeft_button)
		self.Controls.Add(self._KsElevatorsForm_label1)
		self.Controls.Add(self._Ksabove12_dataGridView)
		self.Controls.Add(self._Ksbelow12_dataGridView)
		self.Controls.Add(self._OK_button)
		self.Name = "KsElevatorsForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = KsElevatorsForm_texttrans_4
		self.Load += self.KsElevatorsFormLoad
		self._Ksbelow12_dataGridView.EndInit()
		self._Ksabove12_dataGridView.EndInit()
		self.ResumeLayout(False)
		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell


	def KsElevatorsFormLoad(self, sender, e):
		for i in elems_avtomats_elevators_groupsnames:
			self._Ksabove12_dataGridView.Rows.Add(i) # Заполняем таблицу исходными данными

	def MoveLeft_buttonClick(self, sender, e):
		Selected_cells = [i for i in self._Ksabove12_dataGridView.SelectedCells] # список выбранных ячеек
		for i in Selected_cells:
			try:
				self._Ksbelow12_dataGridView.Rows.Add(i.Value) # Добавляем значения в таблицу
				self._Ksabove12_dataGridView.Rows.RemoveAt(i.RowIndex) # Удаляем значения из таблицы
			except:
				pass

	def MoveRight_buttonClick(self, sender, e):
		Selected_cells = [i for i in self._Ksbelow12_dataGridView.SelectedCells] # список выбранных ячеек
		for i in Selected_cells:
			try:
				self._Ksabove12_dataGridView.Rows.Add(i.Value) # Добавляем значения в таблицу
				self._Ksbelow12_dataGridView.Rows.RemoveAt(i.RowIndex) # Удаляем значения из таблицы
			except:
				pass

	def OK_buttonClick(self, sender, e):
		global elevators_groupsnames_below12 # группы у которых лифты до 12 этажей
		elevators_groupsnames_below12 = []
		global elevators_groupsnames_above12 # группы у которых лифты 12 и выше этажей
		elevators_groupsnames_above12 = []
		for i in range(self._Ksbelow12_dataGridView.Rows.Count-1):
			elevators_groupsnames_below12.append(self._Ksbelow12_dataGridView[0, i].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.
		for i in range(self._Ksabove12_dataGridView.Rows.Count-1):
			elevators_groupsnames_above12.append(self._Ksabove12_dataGridView[0, i].Value) # обращение "столбец", "строка". Нумерация идёт начиная с нуля.

		self.Close()




















#__________Работаем с пользовательскими режимами расчёта_______ЗАНЯТЬСЯ ПЕРЕВОДОМ НАЧАВ С КОДА В НАСТРОЙКАХ!!!!!___________________________________________

# ФУНКЦИИ КАК В НАСТРОЙКАХ ТЕСЛЫ
# Функция считывания данных о пользовательских Кс, Р и формулах из Хранилища
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
# [[u'Таблица 7.6 - Коэффициенты спроса для рабочего освещения', u'Рабочее освещение', u'Кс.о.', 'epcount', u'Не зависит от уд.веса в других нагрузках', [''], [u'Рраб.осв.'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9'], [u'Столбец 1. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 2. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Мощность ЭП (в 1-й строке), значения Кс (в остальных строках)'], [['5', '10', '15', '25', '50', '100', '200', '400', '500'], ['1', '0.8', '0.7', '0.6', '0.5', '0.4', '0.35', '0.3', '0.3']]], [u'Таблица 7.9 - Коэффициенты спроса для предприятий общественного питания и пищеблоков', u'Тепловое оборудование пищеблоков', u'Кс.гор.пищ.', 'epcount', u'Не зависит от уд.веса в других нагрузках', [''], [u'Ргор.пищ.'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11'], [u'Столбец 1. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [['2', '3', '5', '8', '10', '15', '20', '30', '60', '100', '120'], ['0.9', '0.85', '0.75', '0.65', '0.6', '0.5', '0.45', '0.4', '0.3', '0.3', '0.25']]], [u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин', u'Системы ОВ', u'Кс.сан.тех.', 'epcount', u'Зависит от уд.веса в других нагрузках', [u'Ру (вся)'], [u'Рр.сантех.', u'Рр.ов'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11', 'column12'], [u'Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84', '0', '0', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74', '0', '0', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49', '0', '0', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '0', '0', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]]]


#_________Пользовательские мощности______________________________________________________
schemaGuid_for_UserP = System.Guid(Guidstr_UserP) # Этот guid не менять! Он отвечает за ExtensibleStorage!
#Получаем Schema:
schUserP = Schema.Lookup(schemaGuid_for_UserP)
# Данные по умолчанию
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


#_________Пользовательские формулы___________________________________
schemaGuid_for_UserFormula = System.Guid(Guidstr_UserFormula) # Этот guid не менять! Он отвечает за ExtensibleStorage!
#Получаем Schema:
schUserFormula = Schema.Lookup(schemaGuid_for_UserFormula)
# Данные по умолчанию
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

# Вот эти 'Ру (вся)', 'Рр (вся)' сделаем переменными, чтобы потом в коде на них ссылаться и переименовывать легко если надо
# ОНИ ТУТ КАК В НАСТРОЙКАХ. ОТДЕЛЬНО НЕ МЕНЯТЬ. КАЖЕТСЯ ИЗ НИХ ПОЛОВИНА НЕ ИСПОЛЬЗУЕТСЯ НИГДЕ.
PyAll = 'Ру (вся)'
PpAll = 'Рр (вся)'




#_____________________________________________________________________________________________________________________________________________________





































# Окошко результатов расчётов


global Button_Cancel_pushed # Переменная чтобы выйти из программы если пользователь нажал Cancel в окошке
Button_Cancel_pushed = 1



class KcForm(Form):
	def __init__(self):
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._Py_textBox = System.Windows.Forms.TextBox()
		self._Py_label = System.Windows.Forms.Label()
		self._Kc_groupBox = System.Windows.Forms.GroupBox()
		self._Kcpresent_radioButton = System.Windows.Forms.RadioButton()
		self._Kcpresent_textBox = System.Windows.Forms.TextBox()
		self._Kccalculated_textBox = System.Windows.Forms.TextBox()
		self._Kccalculated_radioButton = System.Windows.Forms.RadioButton()
		self._Pp_label = System.Windows.Forms.Label()
		self._Pp_textBox = System.Windows.Forms.TextBox()
		self._Cosf_label = System.Windows.Forms.Label()
		self._Cosf_textBox = System.Windows.Forms.TextBox()
		self._Ip_label = System.Windows.Forms.Label()
		self._Ip_textBox = System.Windows.Forms.TextBox()
		self._U_groupBox = System.Windows.Forms.GroupBox()
		self._U230_radioButton = System.Windows.Forms.RadioButton()
		self._U400_radioButton = System.Windows.Forms.RadioButton()
		self._OK_button = System.Windows.Forms.Button()
		self._Cancel_button = System.Windows.Forms.Button()
		self._Calculate_button = System.Windows.Forms.Button()
		self._CalculationWay_groupBox = System.Windows.Forms.GroupBox()
		self._CalcWay_Residental_radioButton = System.Windows.Forms.RadioButton()
		self._CalcWay_Simple_radioButton = System.Windows.Forms.RadioButton()
		self._CalcWay_Coefficient_radioButton = System.Windows.Forms.RadioButton()
		self._CalcWay_User_radioButton = System.Windows.Forms.RadioButton()
		self._Select_UserMode_comboBox = System.Windows.Forms.ComboBox()
		self._textBox_FormulaShow = System.Windows.Forms.TextBox()
		self._CalcWay_ResidentalplusUser_radioButton = System.Windows.Forms.RadioButton()
		self._Kc_groupBox.SuspendLayout()
		self._U_groupBox.SuspendLayout()
		self._CalculationWay_groupBox.SuspendLayout()
		self.SuspendLayout()
		# 
		# Py_textBox
		# 
		self._Py_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Py_textBox.Location = System.Drawing.Point(87, 316)
		self._Py_textBox.Name = "Py_textBox"
		self._Py_textBox.ReadOnly = True
		self._Py_textBox.Size = System.Drawing.Size(157, 22)
		self._Py_textBox.TabIndex = 0
		# 
		# Py_label
		# 
		self._Py_label.Location = System.Drawing.Point(18, 319)
		self._Py_label.Name = "Py_label"
		self._Py_label.Size = System.Drawing.Size(60, 23)
		self._Py_label.TabIndex = 1
		self._Py_label.Text = KcForm_texttrans_1
		# 
		# Kc_groupBox
		# 
		self._Kc_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Kc_groupBox.Controls.Add(self._Kccalculated_textBox)
		self._Kc_groupBox.Controls.Add(self._Kccalculated_radioButton)
		self._Kc_groupBox.Controls.Add(self._Kcpresent_textBox)
		self._Kc_groupBox.Controls.Add(self._Kcpresent_radioButton)
		self._Kc_groupBox.Location = System.Drawing.Point(12, 344)
		self._Kc_groupBox.Name = "Kc_groupBox"
		self._Kc_groupBox.Size = System.Drawing.Size(288, 86)
		self._Kc_groupBox.TabIndex = 2
		self._Kc_groupBox.TabStop = False
		self._Kc_groupBox.Text = KcForm_texttrans_2
		# 
		# Kcpresent_radioButton
		# 
		self._Kcpresent_radioButton.Location = System.Drawing.Point(6, 19)
		self._Kcpresent_radioButton.Name = "Kcpresent_radioButton"
		self._Kcpresent_radioButton.Size = System.Drawing.Size(104, 24)
		self._Kcpresent_radioButton.TabIndex = 0
		self._Kcpresent_radioButton.TabStop = True
		self._Kcpresent_radioButton.Text = KcForm_texttrans_3
		self._Kcpresent_radioButton.UseVisualStyleBackColor = True
		# 
		# Kcpresent_textBox
		# 
		self._Kcpresent_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Kcpresent_textBox.Location = System.Drawing.Point(84, 22)
		self._Kcpresent_textBox.Name = "Kcpresent_textBox"
		self._Kcpresent_textBox.ReadOnly = True
		self._Kcpresent_textBox.Size = System.Drawing.Size(157, 22)
		self._Kcpresent_textBox.TabIndex = 3
		# 
		# Kccalculated_textBox
		# 
		self._Kccalculated_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Kccalculated_textBox.Location = System.Drawing.Point(84, 51)
		self._Kccalculated_textBox.Name = "Kccalculated_textBox"
		self._Kccalculated_textBox.Size = System.Drawing.Size(157, 22)
		self._Kccalculated_textBox.TabIndex = 5
		self._Kccalculated_textBox.TextChanged += self.Kccalculated_textBoxTextChanged
		self._Kccalculated_textBox.Leave += self.KccalculatedFocusLeave
		# 
		# Kccalculated_radioButton
		# 
		self._Kccalculated_radioButton.Location = System.Drawing.Point(6, 48)
		self._Kccalculated_radioButton.Name = "Kccalculated_radioButton"
		self._Kccalculated_radioButton.Size = System.Drawing.Size(104, 24)
		self._Kccalculated_radioButton.TabIndex = 4
		self._Kccalculated_radioButton.TabStop = True
		self._Kccalculated_radioButton.Text = KcForm_texttrans_4
		self._Kccalculated_radioButton.UseVisualStyleBackColor = True
		# 
		# Pp_label
		# 
		self._Pp_label.Location = System.Drawing.Point(30, 439)
		self._Pp_label.Name = "Pp_label"
		self._Pp_label.Size = System.Drawing.Size(60, 23)
		self._Pp_label.TabIndex = 4
		self._Pp_label.Text = KcForm_texttrans_5
		# 
		# Pp_textBox
		# 
		self._Pp_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Pp_textBox.Location = System.Drawing.Point(96, 436)
		self._Pp_textBox.Name = "Pp_textBox"
		self._Pp_textBox.ReadOnly = True
		self._Pp_textBox.Size = System.Drawing.Size(157, 22)
		self._Pp_textBox.TabIndex = 3
		# 
		# Cosf_label
		# 
		self._Cosf_label.Location = System.Drawing.Point(51, 471)
		self._Cosf_label.Name = "Cosf_label"
		self._Cosf_label.Size = System.Drawing.Size(39, 23)
		self._Cosf_label.TabIndex = 6
		self._Cosf_label.Text = "Cosf ="
		# 
		# Cosf_textBox
		# 
		self._Cosf_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Cosf_textBox.Location = System.Drawing.Point(96, 468)
		self._Cosf_textBox.Name = "Cosf_textBox"
		self._Cosf_textBox.ReadOnly = True
		self._Cosf_textBox.Size = System.Drawing.Size(157, 22)
		self._Cosf_textBox.TabIndex = 5
		# 
		# Ip_label
		# 
		self._Ip_label.Location = System.Drawing.Point(42, 590)
		self._Ip_label.Name = "Ip_label"
		self._Ip_label.Size = System.Drawing.Size(48, 23)
		self._Ip_label.TabIndex = 8
		self._Ip_label.Text = KcForm_texttrans_6
		# 
		# Ip_textBox
		# 
		self._Ip_textBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Ip_textBox.Location = System.Drawing.Point(96, 587)
		self._Ip_textBox.Name = "Ip_textBox"
		self._Ip_textBox.ReadOnly = True
		self._Ip_textBox.Size = System.Drawing.Size(157, 22)
		self._Ip_textBox.TabIndex = 7
		# 
		# U_groupBox
		# 
		self._U_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._U_groupBox.Controls.Add(self._U230_radioButton)
		self._U_groupBox.Controls.Add(self._U400_radioButton)
		self._U_groupBox.Location = System.Drawing.Point(12, 495)
		self._U_groupBox.Name = "U_groupBox"
		self._U_groupBox.Size = System.Drawing.Size(288, 86)
		self._U_groupBox.TabIndex = 6
		self._U_groupBox.TabStop = False
		self._U_groupBox.Text = KcForm_texttrans_7
		# 
		# U230_radioButton
		# 
		self._U230_radioButton.Location = System.Drawing.Point(57, 48)
		self._U230_radioButton.Name = "U230_radioButton"
		self._U230_radioButton.Size = System.Drawing.Size(104, 24)
		self._U230_radioButton.TabIndex = 4
		self._U230_radioButton.TabStop = True
		self._U230_radioButton.Text = KcForm_texttrans_8
		self._U230_radioButton.UseVisualStyleBackColor = True
		# 
		# U400_radioButton
		# 
		self._U400_radioButton.Location = System.Drawing.Point(57, 19)
		self._U400_radioButton.Name = "U400_radioButton"
		self._U400_radioButton.Size = System.Drawing.Size(104, 24)
		self._U400_radioButton.TabIndex = 0
		self._U400_radioButton.TabStop = True
		self._U400_radioButton.Text = KcForm_texttrans_9
		self._U400_radioButton.UseVisualStyleBackColor = True
		# 
		# OK_button
		# 
		self._OK_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._OK_button.Location = System.Drawing.Point(12, 660)
		self._OK_button.Name = "OK_button"
		self._OK_button.Size = System.Drawing.Size(91, 23)
		self._OK_button.TabIndex = 9
		self._OK_button.Text = KcForm_texttrans_10
		self._OK_button.UseVisualStyleBackColor = True
		self._OK_button.Click += self.OK_buttonClick
		# 
		# Cancel_button
		# 
		self._Cancel_button.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._Cancel_button.Location = System.Drawing.Point(209, 660)
		self._Cancel_button.Name = "Cancel_button"
		self._Cancel_button.Size = System.Drawing.Size(91, 23)
		self._Cancel_button.TabIndex = 10
		self._Cancel_button.Text = "Cancel"
		self._Cancel_button.UseVisualStyleBackColor = True
		self._Cancel_button.Click += self.Cancel_buttonClick
		# 
		# Calculate_button
		# 
		self._Calculate_button.Location = System.Drawing.Point(12, 619)
		self._Calculate_button.Name = "Calculate_button"
		self._Calculate_button.Size = System.Drawing.Size(91, 23)
		self._Calculate_button.TabIndex = 11
		self._Calculate_button.Text = KcForm_texttrans_11
		self._Calculate_button.UseVisualStyleBackColor = True
		self._Calculate_button.Click += self.Calculate_buttonClick
		# 
		# CalculationWay_groupBox
		# 
		self._CalculationWay_groupBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._CalculationWay_groupBox.Controls.Add(self._CalcWay_ResidentalplusUser_radioButton)
		self._CalculationWay_groupBox.Controls.Add(self._textBox_FormulaShow)
		self._CalculationWay_groupBox.Controls.Add(self._Select_UserMode_comboBox)
		self._CalculationWay_groupBox.Controls.Add(self._CalcWay_User_radioButton)
		self._CalculationWay_groupBox.Controls.Add(self._CalcWay_Coefficient_radioButton)
		self._CalculationWay_groupBox.Controls.Add(self._CalcWay_Residental_radioButton)
		self._CalculationWay_groupBox.Controls.Add(self._CalcWay_Simple_radioButton)
		self._CalculationWay_groupBox.Location = System.Drawing.Point(12, 12)
		self._CalculationWay_groupBox.Name = "CalculationWay_groupBox"
		self._CalculationWay_groupBox.Size = System.Drawing.Size(288, 298)
		self._CalculationWay_groupBox.TabIndex = 6
		self._CalculationWay_groupBox.TabStop = False
		self._CalculationWay_groupBox.Text = KcForm_texttrans_12
		# 
		# CalcWay_Residental_radioButton
		# 
		self._CalcWay_Residental_radioButton.Location = System.Drawing.Point(6, 48)
		self._CalcWay_Residental_radioButton.Name = "CalcWay_Residental_radioButton"
		self._CalcWay_Residental_radioButton.Size = System.Drawing.Size(243, 24)
		self._CalcWay_Residental_radioButton.TabIndex = 4
		self._CalcWay_Residental_radioButton.TabStop = True
		self._CalcWay_Residental_radioButton.Text = KcForm_texttrans_13
		self._CalcWay_Residental_radioButton.UseVisualStyleBackColor = True
		self._CalcWay_Residental_radioButton.CheckedChanged += self.CalcWay_Residental_radioButtonCheckedChanged
		# 
		# CalcWay_Simple_radioButton
		# 
		self._CalcWay_Simple_radioButton.Location = System.Drawing.Point(6, 19)
		self._CalcWay_Simple_radioButton.Name = "CalcWay_Simple_radioButton"
		self._CalcWay_Simple_radioButton.Size = System.Drawing.Size(243, 24)
		self._CalcWay_Simple_radioButton.TabIndex = 0
		self._CalcWay_Simple_radioButton.TabStop = True
		self._CalcWay_Simple_radioButton.Text = KcForm_texttrans_14
		self._CalcWay_Simple_radioButton.UseVisualStyleBackColor = True
		self._CalcWay_Simple_radioButton.CheckedChanged += self.CalcWay_Simple_radioButtonCheckedChanged
		# 
		# CalcWay_Coefficient_radioButton
		# 
		self._CalcWay_Coefficient_radioButton.Location = System.Drawing.Point(6, 78)
		self._CalcWay_Coefficient_radioButton.Name = "CalcWay_Coefficient_radioButton"
		self._CalcWay_Coefficient_radioButton.Size = System.Drawing.Size(243, 24)
		self._CalcWay_Coefficient_radioButton.TabIndex = 5
		self._CalcWay_Coefficient_radioButton.TabStop = True
		self._CalcWay_Coefficient_radioButton.Text = KcForm_texttrans_15
		self._CalcWay_Coefficient_radioButton.UseVisualStyleBackColor = True
		self._CalcWay_Coefficient_radioButton.CheckedChanged += self.CalcWay_Coefficient_radioButtonCheckedChanged
		# 
		# CalcWay_User_radioButton
		# 
		self._CalcWay_User_radioButton.Location = System.Drawing.Point(6, 108)
		self._CalcWay_User_radioButton.Name = "CalcWay_User_radioButton"
		self._CalcWay_User_radioButton.Size = System.Drawing.Size(243, 24)
		self._CalcWay_User_radioButton.TabIndex = 6
		self._CalcWay_User_radioButton.TabStop = True
		self._CalcWay_User_radioButton.Text = KcForm_texttrans_16
		self._CalcWay_User_radioButton.UseVisualStyleBackColor = True
		self._CalcWay_User_radioButton.CheckedChanged += self.CalcWay_User_radioButtonCheckedChanged
		# 
		# Select_UserMode_comboBox
		# 
		self._Select_UserMode_comboBox.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._Select_UserMode_comboBox.FormattingEnabled = True
		self._Select_UserMode_comboBox.Location = System.Drawing.Point(16, 178)
		self._Select_UserMode_comboBox.Name = "Select_UserMode_comboBox"
		self._Select_UserMode_comboBox.Size = System.Drawing.Size(252, 24)
		self._Select_UserMode_comboBox.TabIndex = 7
		self._Select_UserMode_comboBox.SelectedIndexChanged += self.Select_UserMode_comboBoxSelectedIndexChanged
		# 
		# textBox_FormulaShow
		# 
		self._textBox_FormulaShow.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._textBox_FormulaShow.BackColor = System.Drawing.SystemColors.Window
		self._textBox_FormulaShow.Location = System.Drawing.Point(16, 218)
		self._textBox_FormulaShow.Multiline = True
		self._textBox_FormulaShow.Name = "textBox_FormulaShow"
		self._textBox_FormulaShow.ReadOnly = True
		self._textBox_FormulaShow.Size = System.Drawing.Size(252, 62)
		self._textBox_FormulaShow.TabIndex = 8
		# 
		# CalcWay_ResidentalplusUser_radioButton
		# 
		self._CalcWay_ResidentalplusUser_radioButton.Location = System.Drawing.Point(6, 138)
		self._CalcWay_ResidentalplusUser_radioButton.Name = "CalcWay_ResidentalplusUser_radioButton"
		self._CalcWay_ResidentalplusUser_radioButton.Size = System.Drawing.Size(276, 24)
		self._CalcWay_ResidentalplusUser_radioButton.TabIndex = 9
		self._CalcWay_ResidentalplusUser_radioButton.TabStop = True
		self._CalcWay_ResidentalplusUser_radioButton.Text = "Жилой дом + пользовательский"
		self._CalcWay_ResidentalplusUser_radioButton.UseVisualStyleBackColor = True
		self._CalcWay_ResidentalplusUser_radioButton.CheckedChanged += self.CalcWay_ResidentalplusUser_radioButtonCheckedChanged
		# 
		# KcForm
		# 
		self.ClientSize = System.Drawing.Size(320, 697)
		self.Controls.Add(self._CalculationWay_groupBox)
		self.Controls.Add(self._Calculate_button)
		self.Controls.Add(self._Cancel_button)
		self.Controls.Add(self._OK_button)
		self.Controls.Add(self._U_groupBox)
		self.Controls.Add(self._Ip_label)
		self.Controls.Add(self._Ip_textBox)
		self.Controls.Add(self._Cosf_label)
		self.Controls.Add(self._Cosf_textBox)
		self.Controls.Add(self._Pp_label)
		self.Controls.Add(self._Pp_textBox)
		self.Controls.Add(self._Kc_groupBox)
		self.Controls.Add(self._Py_label)
		self.Controls.Add(self._Py_textBox)
		self.MinimumSize = System.Drawing.Size(338, 744)
		self.Name = "KcForm"
		self.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
		self.Text = KcForm_texttrans_17
		self.Load += self.KcFormLoad
		self._Kc_groupBox.ResumeLayout(False)
		self._Kc_groupBox.PerformLayout()
		self._U_groupBox.ResumeLayout(False)
		self._CalculationWay_groupBox.ResumeLayout(False)
		self._CalculationWay_groupBox.PerformLayout()
		self.ResumeLayout(False)
		self.PerformLayout()

		self.Icon = iconmy # Принимаем иконку из C#. Залочить при тестировании в Python Shell



	def CalcWay_Simple_radioButtonCheckedChanged(self, sender, e):
		# Активируем участвующие в расчёте поля при выборе не "простого" способа расчёта
		self._Calculate_button.Enabled = True
		self._U400_radioButton.Enabled = True
		self._U230_radioButton.Enabled = True
		if elems_calculation_table != []: # Если табличка результатов выбрана...
			self._Kcpresent_radioButton.Enabled = True
		self._Select_UserMode_comboBox.Enabled = False
		self._textBox_FormulaShow.Enabled = False

		# Показываем нужные поля чтобы не путать пользователя
		self._Kccalculated_radioButton.Visible = True
		self._Kccalculated_textBox.Visible = True
		self._Kcpresent_radioButton.Visible = True
		self._Kcpresent_textBox.Visible = True
		self._Pp_textBox.Visible = True
		self._Pp_label.Visible = True
		self._Ip_textBox.Visible = True
		self._Ip_label.Visible = True

	def CalcWay_Residental_radioButtonCheckedChanged(self, sender, e):
		# Засереваем неучаствующие в расчёте поля при выборе способа расчёта "жилой дом"
		self._Calculate_button.Enabled = False
		self._U400_radioButton.Enabled = False
		self._U400_radioButton.Checked = True # жилой дом будем считать всегда трёхфазным
		self._U230_radioButton.Enabled = False
		self._Select_UserMode_comboBox.Enabled = False
		self._textBox_FormulaShow.Enabled = False

		# Скрываем ненужные поля чтобы не путать пользователя
		self._Kccalculated_radioButton.Visible = False
		self._Kccalculated_textBox.Visible = False
		self._Kcpresent_radioButton.Visible = False
		self._Kcpresent_textBox.Visible = False
		self._Pp_textBox.Visible = False
		self._Pp_label.Visible = False
		self._Ip_textBox.Visible = False
		self._Ip_label.Visible = False

	def CalcWay_Coefficient_radioButtonCheckedChanged(self, sender, e):
		# Засереваем неучаствующие в расчёте поля при выборе способа расчёта "Жилой дом при пожаре"
		self._Calculate_button.Enabled = False
		self._U400_radioButton.Enabled = False
		self._U400_radioButton.Checked = True # этот расчёт будем считать всегда трёхфазным
		self._U230_radioButton.Enabled = False
		self._Select_UserMode_comboBox.Enabled = False
		self._textBox_FormulaShow.Enabled = False

		# Скрываем ненужные поля чтобы не путать пользователя
		self._Kccalculated_radioButton.Visible = False
		self._Kccalculated_textBox.Visible = False
		self._Kcpresent_radioButton.Visible = False
		self._Kcpresent_textBox.Visible = False
		self._Pp_textBox.Visible = False
		self._Pp_label.Visible = False
		self._Ip_textBox.Visible = False
		self._Ip_label.Visible = False

	def CalcWay_User_radioButtonCheckedChanged(self, sender, e):
		self._Select_UserMode_comboBox.Enabled = True
		self._textBox_FormulaShow.Enabled = True
		# Засереваем неучаствующие в расчёте поля при выборе способа расчёта "Пользовательский"
		self._Calculate_button.Enabled = False
		self._U400_radioButton.Enabled = False
		self._U400_radioButton.Checked = True # этот расчёт будем считать всегда трёхфазным
		self._U230_radioButton.Enabled = False

		# Скрываем ненужные поля чтобы не путать пользователя
		self._Kccalculated_radioButton.Visible = False
		self._Kccalculated_textBox.Visible = False
		self._Kcpresent_radioButton.Visible = False
		self._Kcpresent_textBox.Visible = False
		self._Pp_textBox.Visible = False
		self._Pp_label.Visible = False
		self._Ip_textBox.Visible = False
		self._Ip_label.Visible = False

	def CalcWay_ResidentalplusUser_radioButtonCheckedChanged(self, sender, e):
		self._Select_UserMode_comboBox.Enabled = True
		self._textBox_FormulaShow.Enabled = True
		# Засереваем неучаствующие в расчёте поля при выборе способа расчёта "Пользовательский"
		self._Calculate_button.Enabled = False
		self._U400_radioButton.Enabled = False
		self._U400_radioButton.Checked = True # этот расчёт будем считать всегда трёхфазным
		self._U230_radioButton.Enabled = False

		# Скрываем ненужные поля чтобы не путать пользователя
		self._Kccalculated_radioButton.Visible = False
		self._Kccalculated_textBox.Visible = False
		self._Kcpresent_radioButton.Visible = False
		self._Kcpresent_textBox.Visible = False
		self._Pp_textBox.Visible = False
		self._Pp_label.Visible = False
		self._Ip_textBox.Visible = False
		self._Ip_label.Visible = False

	def Kccalculated_textBoxTextChanged(self, sender, e):
		self._Kccalculated_radioButton.Checked = True # выставим сюда радиокнопку если пользователь начал редактировать Кс

	def KccalculatedFocusLeave(self, sender, e): # функция ухода фокуса из этого поля. Подписана на соответствующее событие self._Kccalculated_textBox.Leave += self.KccalculatedFocusLeave
		try:
			float(self._Kccalculated_textBox.Text)
		except:
			TaskDialog.Show(AvcountsComandName_texttrans, KcForm_texttrans_18)	
			self._Kccalculated_textBox.Select() # Устанавливаем фокус в этот текст бокс (и не выпустим пользователя пока он не введёт число)

	def KcFormLoad(self, sender, e):
		self.ActiveControl = self._OK_button # ставим фокус на кнопку

		# Выставляем способ расчёта
		self._CalcWay_Simple_radioButton.Checked = True
		if len(is_flat_riser) == 0: # если в выборке не было квартир, то запретим выбор способа расчёта "жилой дом"
			self._CalcWay_Residental_radioButton.Enabled = False
			self._CalcWay_Coefficient_radioButton.Enabled = False
			self._CalcWay_ResidentalplusUser_radioButton.Enabled = False
		#if len(elems_avtomats_elevators) == 0: # если в выборке не было лифтов, то запретим выбор способа расчёта "С коэффициентами спроса"
		#	self._CalcWay_Coefficient_radioButton.Enabled = False


		# Выставляем данные при загрузке окна
		self._Py_textBox.Text = str(round(Py_sum, Round_value_ts))
		self._Cosf_textBox.Text = str(cosf_average)
		self._U230_radioButton.Text = str(int(U1f)) + KcForm_texttrans_19
		self._U400_radioButton.Text = str(int(U3f)) + KcForm_texttrans_19
		# Выставим значение Кс. Если табличка результатов выбрана, то радиокнопку ставим у Кс существующего. Если не выбрана, то у расчётного.
		if elems_calculation_table != []: # Если табличка результатов выбрана...
			if Upit_calculation_table_volts[0] == U1fforI: # если в табличке указано однофазное напряжение
				self._U230_radioButton.Checked = True
				self._Ip_textBox.Text = str(round(((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()) / cosf_average / U1fforI), Round_value_ts))
			else: # если в табличке указано трёхфазное напряжение
				self._U400_radioButton.Checked = True
				self._Ip_textBox.Text = str(round(((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()) / cosf_average / U3fsqrt3forI), Round_value_ts))
			self._Kcpresent_textBox.Text = str(elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble())
			self._Pp_textBox.Text = str(round((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()), Round_value_ts))
			#self._Ip_textBox.Text = str(round(((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()) / cosf_average / Upit_calculation_table_volts[0]), Round_value_ts))
			self._Kccalculated_textBox.Text = str(round((Pp_sum / Py_sum), 2)) # расчётный Кс тоже запишем в соответствующий текст-бокс
			self._Kcpresent_radioButton.Checked = True
		else: #  Если не выбрана...
			self._U400_radioButton.Checked = True
			self._Kccalculated_radioButton.Checked = True
			self._Kccalculated_textBox.Text = str(round((Pp_sum / Py_sum), 2))
			self._Pp_textBox.Text = str(round((Py_sum * (Pp_sum / Py_sum)), Round_value_ts))
			self._Ip_textBox.Text = str(round(((Py_sum * (Pp_sum / Py_sum)) / cosf_average / U3fsqrt3forI), Round_value_ts))
			self._Kcpresent_radioButton.Enabled = False # засереваем радиокнопку, т.к. расчётная табличка не выбрана
			self._Kcpresent_textBox.Enabled = False # засереваем текстбокс, т.к. расчётная табличка не выбрана

		# делаем всплывающие подсказки
		ToolTip().SetToolTip(self._Kcpresent_radioButton, KcForm_texttrans_20) 
		ToolTip().SetToolTip(self._Kccalculated_radioButton, KcForm_texttrans_21) 
		ToolTip().SetToolTip(self._CalcWay_Simple_radioButton, KcForm_texttrans_22) 
		ToolTip().SetToolTip(self._CalcWay_Residental_radioButton, KcForm_texttrans_23) 
		ToolTip().SetToolTip(self._CalcWay_Coefficient_radioButton, KcForm_texttrans_24) 
		ToolTip().SetToolTip(self._CalcWay_User_radioButton, KcForm_texttrans_25) 
		ToolTip().SetToolTip(self._CalcWay_ResidentalplusUser_radioButton, 'Рр = Рр.ж.д + Рс\nРасчёт жилого дома по п.7.1.10 СП 256.1325800, где Рс - рассчитывается по пользовательской формуле')

		self._Select_UserMode_comboBox.DataSource = UserFormulaNamesList # список пользовательских режимов расчёта
		self._Select_UserMode_comboBox.Enabled = False # засереваем пока не выбрали этот режим


	def Calculate_buttonClick(self, sender, e):
		if self._Kcpresent_radioButton.Checked == True: # если считаем по Кс существующему (из таблички)
			self._Pp_textBox.Text = str(round((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()), Round_value_ts))
			if self._U230_radioButton.Checked == True: # если напряжение выбрано однофазное	
				self._Ip_textBox.Text = str(round(((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()) / cosf_average / U1fforI), Round_value_ts))
			else: # если напряжение выбрано трёхфазное	
				self._Ip_textBox.Text = str(round(((Py_sum * elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()) / cosf_average / U3fsqrt3forI), Round_value_ts))
		elif self._Kccalculated_radioButton.Checked == True: # если считаем по Кс расчётному (введённому пользователем)
			self._Pp_textBox.Text = str(round((Py_sum * float(self._Kccalculated_textBox.Text)), Round_value_ts))
			if self._U230_radioButton.Checked == True: # если напряжение выбрано однофазное	
				self._Ip_textBox.Text = str(round(((Py_sum * float(self._Kccalculated_textBox.Text)) / cosf_average / U1fforI), Round_value_ts))
			else: # если напряжение выбрано трёхфазное	
				self._Ip_textBox.Text = str(round(((Py_sum * float(self._Kccalculated_textBox.Text)) / cosf_average / U3fsqrt3forI), Round_value_ts))

	def Select_UserMode_comboBoxSelectedIndexChanged(self, sender, e):
		SelectedFormulaName = self._Select_UserMode_comboBox.SelectedItem # Берём имя выбранной формулы
		for i in Readable_znachUserFormula:
			if i[0] == SelectedFormulaName:
				self._textBox_FormulaShow.Text = ' '.join(i[1]) # Показываем выбранную формулу
				break

	def OK_buttonClick(self, sender, e):
		# Собираем данные для расчёта и записи:
		global Kc_window # значение Kc из окошка
		global Upit_window # значение напряжение из окошка
		global UserFormulaSelected # Выбранный пользователем режим расчёта (формула)

		if self._Kcpresent_radioButton.Checked == True: # если считаем по Кс существующему (из таблички)
			Kc_window = elems_calculation_table[0].LookupParameter(Param_Kc).AsDouble()
		elif self._Kccalculated_radioButton.Checked == True: # если считаем по Кс расчётному (введённому пользователем)
			Kc_window = float(self._Kccalculated_textBox.Text)
		if self._U230_radioButton.Checked == True: # если напряжение выбрано однофазное	
			Upit_window = U1fforI
		else: # если напряжение выбрано трёхфазное	
			Upit_window = U3fsqrt3forI

		# Смотрим какой тип расчёта выбран
		global CalcWay # 0 - простой расчёт; 1 - расчёт жилого дома (рабочий режим); 
		# 2 - расчёт жилого дома (пожарный режим) ; 3 - пользовательский расчёт; 4 - жилой дом + пользовательский
		if self._CalcWay_Simple_radioButton.Checked == True:
			CalcWay = 0
		elif self._CalcWay_Residental_radioButton.Checked == True:
			CalcWay = 1
			if len(elems_avtomats_elevators) > 0: # если в выборке присутствовали лифты, то покажем окошко с лифтами
				KsElevatorsForm().ShowDialog()
		elif self._CalcWay_Coefficient_radioButton.Checked == True:
			CalcWay = 2
			if len(elems_avtomats_elevators) > 0: # если в выборке присутствовали лифты, то покажем окошко с лифтами
				KsElevatorsForm().ShowDialog()
		elif self._CalcWay_User_radioButton.Checked == True:
			CalcWay = 3
			if len(elems_avtomats_elevators) > 0: # если в выборке присутствовали лифты, то покажем окошко с лифтами
				KsElevatorsForm().ShowDialog()
			UserFormulaSelected = self._Select_UserMode_comboBox.SelectedItem # Например 'Расчёт Рр'
		elif self._CalcWay_ResidentalplusUser_radioButton.Checked == True:
			CalcWay = 4
			if len(elems_avtomats_elevators) > 0: # если в выборке присутствовали лифты, то покажем окошко с лифтами
				KsElevatorsForm().ShowDialog()
			UserFormulaSelected = self._Select_UserMode_comboBox.SelectedItem # Например 'Расчёт Рр'

		# Выставляем "кнопка отмена не нажата"
		global Button_Cancel_pushed
		Button_Cancel_pushed = 0
		self.Close()

	def Cancel_buttonClick(self, sender, e):
		self.Close()





KcForm().ShowDialog()



# Функция простой записи результатов расчёта в расчётные таблички (работает внутри открытой транзакции)
# На входе: необходимые переменные для расчёта и записи в табличку
# На выходе ничего - просто всё должно записаться в табличку
def Simple_Write_to_calculation_table (calculation_table, Upit_window, U1fforI, U1f, U3f, Param_Upit, Param_Py, Param_Kc, Param_Pp, Param_Cosf, Param_Ip, Param_Sp, Py_sum, Round_value_ts, Kc_window, cosf_average):
	if Upit_window == U1fforI:
		calculation_table.LookupParameter(Param_Upit).Set(int(U1f)) # Пишем Напряжение
	else:
		calculation_table.LookupParameter(Param_Upit).Set(int(U3f))
	calculation_table.LookupParameter(Param_Py).Set(round(Py_sum, Round_value_ts)) # Пишем Py
	calculation_table.LookupParameter(Param_Kc).Set(Kc_window) # Пишем Kc
	calculation_table.LookupParameter(Param_Pp).Set(round(Py_sum * Kc_window, Round_value_ts)) # Пишем Pp
	calculation_table.LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
	calculation_table.LookupParameter(Param_Ip).Set(round(Py_sum * Kc_window / cosf_average / Upit_window, Round_value_ts)) # Пишем Ip
	calculation_table.LookupParameter(Param_Sp).Set(round(Py_sum * Kc_window / cosf_average, Round_value_ts)) # Пишем Sp
	calculation_table.LookupParameter(Param_IdQFsCalc).Set(Str_Ids_elems_avtomats) # Пишем Idшники автоматов на которых был произведён расчёт





#_____считаем общую нагрузку на квартиры____________

# Вычислим значение параметра 'Рр.уд. (кВт) или Ко' - 
# В этом параметре могут храниться две разные величины:
# Удельная расчётная электрическая нагрузка (кВт) для квартир мощностью Рр=10 кВт (по табл.7.1 СП 256.1325800.2016), или коэффициент одновременности для квартир повышенной комфортности (по табл.7.3 того же СП)


# Функция расчёта и записи жилого дома в итоговые таблички (работает внутри открытой транзакции)
# На входе: необходимые переменные для расчёта и записи в табличку
# На выходе ничего - просто всё должно записаться в табличку
def Residental_Write_to_calculation_table (calculation_table, elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, Write_to_table):

	# Write_to_table бывает True/False
	# True - всё считается и пишется как раньше
	# False - в этом случае функция расчёта ж/д используется для последующего объединения с пользовательской формулой.
	# и тогда получается, что тут не нужно считать лифты и ОДН, а также нужно пересчитать Ру суммарное и косинус жилого дома.

	# вытаскиваем нужные нам параметры
	Flat_count_average = [] # список с общим количеством квартир. Причём если в данном стояке есть квартиры разной мощности,
	# то список Flat_count_average состоит из подсписков с этими мощностями. Например: [[60, 0, 0], [60, 0, 0], [60, 20, 0]]
	Flat_Pp_wattage_average = [] # аналогично формируется список с расчётными мощностями квартир. Например: [[10.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 12.0, 0.0]]

	# Из данных по отдельным автоматам нам нужно собрать два общих списка квартир разной мощности и количества в виде:
	'''
	допустим:
	Flat_count
	[[35, 21, 33], [57, 0, 0], [42, 0, 0]]
	Flat_Pp_wattage
	[[8.4000000000000004, 10.0, 15.0], [12.0, 0.0, 0.0], [10.0, 0.0, 0.0]]

	'''

	# Flat_count_average Например: [35, 21+42=63, 33, 57] количество квартир
	# Flat_Pp_wattage_average Например: [8.4000000000000004, 10.0, 15.0, 12] мощности квартир
	# Определяться будем по спискам с мощностями квартир
	# Счётчики: порядковые номера n m l; сами элементы: i, j, k.
	for n, i in enumerate(Flat_Pp_wattage):
		for m, j in enumerate(i): # j - это мощность квартиры
			if j not in Flat_Pp_wattage_average and j > 0:
				Flat_Pp_wattage_average.append(j)
				Flat_count_average.append(Flat_count[n][m])
			elif j in Flat_Pp_wattage_average:
				ind = Flat_Pp_wattage_average.index(j) # текущий индекс совпавшей мощности
				curcntplus = Flat_count_average.pop(ind) + Flat_count[n][m] # удаляем старое кол-во квартир и сразу суммируем к нему новое
				Flat_count_average.insert(ind, curcntplus)

	# Рассчитываем Рр квартир
	Pp_flats = 0 # Рр.квартир
	# Формируем строку - пояснение
	Calculation_explanation_numbers = str(Kkr_flats_koefficient) + '*(' # строка с цифровыми пояснением расчёта жилого дома
	Calculation_explanation_text = 'Рр.ж.д = Кп.к*(' # строка с текстовыми пояснениями расчёта

	if flat_calculation_way_ts == 1: # способ расчёта - каждый тип квартир со своим Ко
		for n, i in enumerate(Flat_Pp_wattage_average):
			if i == 10: # если расчётная мощность одной квартиры 10 кВт то...
				for m, j in enumerate(Flat_count_SP):
					if Flat_count_average[n] <= 5 and Flat_count_average[n] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
					elif Flat_count_average[n] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
					elif Flat_count_average[n] > Flat_count_SP[m-1] and Flat_count_average[n] < Flat_count_SP[m]:
						x1 = Flat_count_SP[m-1]
						x2 = Flat_count_average[n]
						x3 = Flat_count_SP[m]
						y1 = Flat_unit_wattage_SP[m-1]
						y3 = Flat_unit_wattage_SP[m]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
					elif Flat_count_average[n] == Flat_count_SP[m]:
						Flat_unit_wattage = Flat_unit_wattage_SP[m]
				Pp_flats = Pp_flats + Flat_count_average[n]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного режима
				Calculation_explanation_numbers = Calculation_explanation_numbers + str(round(Flat_unit_wattage, 4)) + '*' + str(Flat_count_average[n]) + '+'
				Calculation_explanation_text = Calculation_explanation_text + 'Ркв.уд*nкв+'

			elif i != 10 and Flat_count_average[n] != 0: # если расчётная мощность одной квартиры не 10 кВт, и больше нуля то и квартир не ноль штук...
				for m, j in enumerate(Flat_count_high_comfort):
					if Flat_count_average[n] <= 5 and Flat_count_average[n] > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
					elif Flat_count_average[n] > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
					elif Flat_count_average[n] > Flat_count_high_comfort[m-1] and Flat_count_average[n] < Flat_count_high_comfort[m]:
						x1 = Flat_count_high_comfort[m-1]
						x2 = Flat_count_average[n]
						x3 = Flat_count_high_comfort[m]
						y1 = Ko_high_comfort[m-1]
						y3 = Ko_high_comfort[m]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
					elif Flat_count_average[n] == Flat_count_high_comfort[m]:
						Ko_unit_high_comfort = Ko_high_comfort[m]
				Pp_flats = Pp_flats + i*Flat_count_average[n]*Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности
				Calculation_explanation_numbers = Calculation_explanation_numbers + str(i) + '*' + str(Flat_count_average[n]) + '*' + str(round(Ko_unit_high_comfort, 4)) + '+'
				Calculation_explanation_text = Calculation_explanation_text + 'Ркв*nкв*Ко+'

	elif flat_calculation_way_ts == 0: # способ расчёта - все квартиры с общим Ко

		Ko_unit_high_comfort = 0 # коэффициент одновременности для всех квартир сразу (кроме 10-киловаттных)
		#Calculation_explanation = '' # строка с пояснением расчёта квартир
		# теперь нужно просто перемножить каждое количество квартир на каждую мощность, всё это сложить и вычислить Ко для общего количества квартир
		sum_count_of_flats = 0 # временная переменная. Суммарное количество квартир для данного стояка.
		sum_Pp_of_flats = 0 # временная переменная. Суммарная мощность всех квартир данного стояка (арифметическая большая сумма).
		Flat_count_10kVt = '' # вспомогательная переменная. Количество 10-киловаттных квартир. Нужна для формирования пояснения.
		for l, m in enumerate(Flat_Pp_wattage_average):

			if m == 10: # если расчётная мощность одной квартиры 10 кВт, то...
				for n, i in enumerate(Flat_count_SP):
					if Flat_count_average[l] <= 5 and Flat_count_average[l] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
						break
					elif Flat_count_average[l] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
						break
					elif Flat_count_average[l] > Flat_count_SP[n-1] and Flat_count_average[l] < Flat_count_SP[n]:
						x1 = Flat_count_SP[n-1]
						x2 = Flat_count_average[l]
						x3 = Flat_count_SP[n]
						y1 = Flat_unit_wattage_SP[n-1]
						y3 = Flat_unit_wattage_SP[n]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
						break
					elif Flat_count_average[l] == Flat_count_SP[n]:
						Flat_unit_wattage = Flat_unit_wattage_SP[n]
						break
				Pp_flats = Pp_flats + Flat_count_average[l]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного стояка
				if Flat_unit_wattage != 0:
					Flat_count_10kVt = str(Flat_count_average[l])

			elif m != 10 and Flat_count_average[l] > 0: # если мощность квартиры не 10 кВт AND количество квартир больше нуля
				sum_count_of_flats = sum_count_of_flats + Flat_count_average[l] # добавляем следующее количество квартир к общему количеству
				sum_Pp_of_flats = sum_Pp_of_flats + m * Flat_count_average[l] # добавляем следующую мощность квартиры к суммарной мощности
				if Calculation_explanation_text == 'Рр.ж.д = Кп.к*(': # чтобы скобочка правильно добавлялась
					Calculation_explanation_text = Calculation_explanation_text + '('

				Calculation_explanation_text = Calculation_explanation_text + 'Pкв.*nкв.+'

				if Calculation_explanation_numbers == str(Kkr_flats_koefficient) + '*(': # чтобы скобочка правильно добавлялась
					Calculation_explanation_numbers = Calculation_explanation_numbers + '('
				Calculation_explanation_numbers = Calculation_explanation_numbers + str(m) + '*' + str(Flat_count_average[l]) + '+'

				for n, i in enumerate(Flat_count_high_comfort):
					if sum_count_of_flats <= 5 and sum_count_of_flats > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
						break
					elif sum_count_of_flats > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
						break
					elif sum_count_of_flats > Flat_count_high_comfort[n-1] and sum_count_of_flats < Flat_count_high_comfort[n]:
						x1 = Flat_count_high_comfort[n-1]
						x2 = sum_count_of_flats
						x3 = Flat_count_high_comfort[n]
						y1 = Ko_high_comfort[n-1]
						y3 = Ko_high_comfort[n]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
						break
					elif sum_count_of_flats == Flat_count_high_comfort[n]:
						Ko_unit_high_comfort = Ko_high_comfort[n]
						break

		Pp_flats = Pp_flats + sum_Pp_of_flats * Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности

		# доформировываем строку-пояснение
		if Ko_unit_high_comfort != 0:
			Calculation_explanation_numbers = Calculation_explanation_numbers[:-1] # убираем последний плюсик
			Calculation_explanation_numbers = Calculation_explanation_numbers + ')*' + str(round(Ko_unit_high_comfort, 4)) + '+'

		if Ko_unit_high_comfort != 0: # !!!!!ТОЖЕ САМОЕ ЧТО И ВПРОШЛОМ if НАВЕРНОЕ БАГА!!!!!!!!!!!!!!
			Calculation_explanation_text = Calculation_explanation_text[:-1] # убираем последний плюсик из строки пояснения
			Calculation_explanation_text = Calculation_explanation_text + ')*Ko+'
			#Calculation_explanation_text = Calculation_explanation_text + ')*' + str(round(Ko_unit_high_comfort, 4))

		if Flat_count_10kVt != '':
			Calculation_explanation_text = Calculation_explanation_text + 'Pкв.уд*nкв.+'
			Calculation_explanation_numbers = Calculation_explanation_numbers + str(round(Flat_unit_wattage, 4)) + '*' + Flat_count_10kVt + '+'

	# Убираем плюсик в конце пояснений
	Calculation_explanation_numbers = Calculation_explanation_numbers[:-1] # убираем последний плюсик
	Calculation_explanation_text = Calculation_explanation_text[:-1] # убираем последний плюсик
	# Закрываем итоговую скобочку, связанную с поправочным коэффициентом квартир.
	Calculation_explanation_text = Calculation_explanation_text + ')'
	Calculation_explanation_numbers = Calculation_explanation_numbers + ')'

	# Считаем Ру ОДН
	Podn = 0
	for i in elems_avtomats:
		if i not in is_flat_riser + elems_avtomats_elevators: # фильтруем все не квартиры и не лифты
			Podn = Podn + i.LookupParameter(Param_Py).AsDouble()

	if Write_to_table == True:
		# Теперь добавим общедомовую нагрузку

		# Разбираемся с лифтами
		#elems_avtomats_elevators
		#elevators_groupsnames_below12 # группы у которых лифты до 12 этажей
		#elevators_groupsnames_above12 # группы у которых лифты 12 и выше этажей
		# Сначала вычисли коэффициенты спроса для лифтов до и более 12 этажей.
		KsElevbelow12cnt = 0 # Кс лифтов до 12 этажей
		KsElevabove12cnt = 0 # Кс лифтов до 12 этажей
		
		# Вычисляем Кс для лифтов до 12 этажей:
		for n, i in enumerate(Elevator_count_SP):
			if len(elevators_groupsnames_below12) == i: # если кол-во лифтов совпало с таблицей СП
				KsElevbelow12cnt = Ks_elevators_below12[n] 
			elif len(elevators_groupsnames_below12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
				KsElevbelow12cnt = Ks_elevators_below12[-1] 
			elif len(elevators_groupsnames_below12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_below12) < Elevator_count_SP[n]:
				x1 = Elevator_count_SP[n-1]
				x2 = len(elevators_groupsnames_below12)
				x3 = Elevator_count_SP[n]
				y1 = Ks_elevators_below12[n-1]
				y3 = Ks_elevators_below12[n]
				KsElevbelow12cnt = interpol (x1, x2, x3, y1, y3)

		# Вычисляем Кс для лифтов 12 этажей и выше:
		for n, i in enumerate(Elevator_count_SP):
			if len(elevators_groupsnames_above12) == i: # если кол-во лифтов совпало с таблицей СП
				KsElevabove12cnt = Ks_elevators_above12[n] 
			elif len(elevators_groupsnames_above12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
				KsElevabove12cnt = Ks_elevators_above12[-1] 
			elif len(elevators_groupsnames_above12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_above12) < Elevator_count_SP[n]:
				x1 = Elevator_count_SP[n-1]
				x2 = len(elevators_groupsnames_above12)
				x3 = Elevator_count_SP[n]
				y1 = Ks_elevators_above12[n-1]
				y3 = Ks_elevators_above12[n]
				KsElevabove12cnt = interpol (x1, x2, x3, y1, y3)

		РуElevbelow12cnt = 0 # Ру лифтов до 12 этажей
		РуElevabove12cnt = 0 # Ру лифтов 12 этажей и выше


		# Вычисляем Ру для лифтов до 12 этажей
		for i in elevators_groupsnames_below12:
			for j in elems_avtomats_elevators:
				if i == j.LookupParameter(Param_Circuit_number).AsString():
					РуElevbelow12cnt = РуElevbelow12cnt + j.LookupParameter(Param_Py).AsDouble()


		# Вычисляем Ру для лифтов 12 этажей и выше
		for i in elevators_groupsnames_above12:
			for j in elems_avtomats_elevators:
				if i == j.LookupParameter(Param_Circuit_number).AsString():
					РуElevabove12cnt = РуElevabove12cnt + j.LookupParameter(Param_Py).AsDouble()



		# Добавим ОДН и лифты к общей нагрузке с Кс = 0,9
		Pp_residental = 0 # Pp жилого дома для данного расчёта и записи результата
		Pp_residental = Kkr_flats_koefficient * Pp_flats + Kcpwrres * (РуElevbelow12cnt * KsElevbelow12cnt + РуElevabove12cnt * KsElevabove12cnt + Podn)

		# Формируем далее строку - пояснение
		if Podn > 0 and РуElevbelow12cnt > 0 and РуElevabove12cnt > 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт.+Рс) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + '+' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + '+' + str(Podn) + ')'
		elif Podn > 0 and РуElevbelow12cnt > 0 and РуElevabove12cnt == 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л+Рс) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + '+' + str(Podn) + ')'
		elif Podn > 0 and РуElevbelow12cnt == 0 and РуElevabove12cnt > 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л+Рс) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + '+' + str(Podn) + ')'
		elif Podn == 0 and РуElevbelow12cnt > 0 and РуElevabove12cnt > 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт.) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + '+' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + ')'
		elif Podn == 0 and РуElevbelow12cnt > 0 and РуElevabove12cnt == 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + ')'
		elif Podn == 0 and РуElevbelow12cnt == 0 and РуElevabove12cnt > 0:
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*(Ру.л*Кс.л) = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*(' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + ')'
		elif Podn == 0 and РуElevbelow12cnt == 0 and РуElevabove12cnt == 0: # есть только квартиры
			Calculation_explanation_text = Calculation_explanation_text + ' = '
		elif Podn > 0 and РуElevbelow12cnt == 0 and РуElevabove12cnt == 0: # нет лифтов, но есть ОДН
			Calculation_explanation_text = Calculation_explanation_text + '+0,9*Рс = '
			Calculation_explanation_numbers = Calculation_explanation_numbers + '+' + str(Kcpwrres) + '*' + str(Podn)


		Calculation_explanation = Calculation_explanation_text + Calculation_explanation_numbers

		# Вычисляем условный Кс на жилой дом
		Kc_cond_residental = Pp_residental / Py_sum
		
		# Пишем результаты
		calculation_table.LookupParameter(Param_Explanation).Set(Calculation_explanation)
		calculation_table.LookupParameter(Param_Py).Set(round(Py_sum, Round_value_ts)) # Пишем Py
		calculation_table.LookupParameter(Param_Kc).Set(round(Kc_cond_residental, 2)) # Пишем Kc
		calculation_table.LookupParameter(Param_Pp).Set(round(Pp_residental, Round_value_ts)) # Пишем Pp
		calculation_table.LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
		calculation_table.LookupParameter(Param_Ip).Set(round(Pp_residental / cosf_average / U3fsqrt3forI, Round_value_ts)) # Пишем Ip
		calculation_table.LookupParameter(Param_Sp).Set(round(Pp_residental / cosf_average, Round_value_ts)) # Пишем Sp
		calculation_table.LookupParameter(Param_IdQFsCalc).Set(Str_Ids_elems_avtomats) # Пишем Idшники автоматов на которых был произведён расчёт
		
	else: # если потом объединяем с пользовательской формулой
		# Получаем итоговую расчётную мощность без лифтов и ОДН
		Pp_residental = Kkr_flats_koefficient * Pp_flats 
		# Считаем Ру лифтов чтобы потом вычесть её из общей Ру
		Pyelevetors = 0
		for i in elems_avtomats_elevators:
			Pyelevetors = Pyelevetors + i.LookupParameter(Param_Py).AsDouble()
		# Из Py_sum нужно вычесть лифты и ОДН
		Py_sum = Py_sum - Podn - Pyelevetors
		# И общий косинус пересчитать чтобы он был только с квартир
		Pp_flat_riser = []
		cosf_flat_riser = []
		# достаём значения Рр и косинуса из каждого квартирного стояка
		for i in is_flat_riser:
			Pp_flat_riser.append(i.LookupParameter(Param_Pp).AsDouble())
			cosf_flat_riser.append(i.LookupParameter(Param_Cosf).AsDouble())
		#Сделаем вспомогательную переменную содержащую число равное сумме каждой Рр умноженной на каждый косинус
		Pp_multiplication_cosf_sum = 0
		for i in list(map(lambda x,y: x*y, Pp_flat_riser, cosf_flat_riser)): # а вот эта штуковина ниже делает список, состоящий из каждой Рр умноженной на каждый косинус
			Pp_multiplication_cosf_sum = Pp_multiplication_cosf_sum + i
		cosf_average = (round ((Pp_multiplication_cosf_sum / sum(Pp_flat_riser)), 2))
			
	#попробуем вывести на выход список с результатми расчётов, чтобы объединять его с редактором формул
	ResidentalResulList = [Calculation_explanation_text, Calculation_explanation_numbers, Py_sum, Pp_residental, cosf_average]

	return ResidentalResulList






# Функция расчёта и записи нагрузок с коэффициентами (работает внутри открытой транзакции)
# ПОКА ЧТО УЧИТЫВАЕТ КОЭФФИЦИЕНТЫ ТОЛЬКО ЛИФТОВ И КВАРТИР
# На входе: необходимые переменные для расчёта и записи в табличку
# На выходе ничего - просто всё должно записаться в табличку
def Coefficient_Write_to_calculation_table (calculation_table, elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient):

	# Формируем строку - пояснение
	Calculation_explanation_numbers = '' # строка с цифровыми пояснением расчёта
	Calculation_explanation_text = 'Рр.ж.д = ' # строка с текстовыми пояснениями расчёта


	#_____________________________________________________________________________________________________________________________________________
	# Собираем все нагрузки кроме лифтов и квартир. Фактически здесь собираем все нагрузки на которые не будут вводиться коэффициенты спроса.
	Рр_without_coefficients = 0 # собирается РАСЧЁТНАЯ нагрузка
	for i in elems_avtomats:
		if i not in elems_avtomats_elevators + is_flat_riser:
			Рр_without_coefficients = Рр_without_coefficients + i.LookupParameter(Param_Pp).AsDouble()

	# Формируем далее строку - пояснение
	if Рр_without_coefficients > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(Рр_without_coefficients) + ' + '
		Calculation_explanation_text = Calculation_explanation_text + 'Рр + '






	#_____________________________________________________________________________________________________________________________________________
	# Разбираемся с лифтами
	#elems_avtomats_elevators
	#elevators_groupsnames_below12 # группы у которых лифты до 12 этажей
	#elevators_groupsnames_above12 # группы у которых лифты 12 и выше этажей
	# Сначала вычисли коэффициенты спроса для лифтов до и более 12 этажей.
	KsElevbelow12cnt = 0 # Кс лифтов до 12 этажей
	KsElevabove12cnt = 0 # Кс лифтов до 12 этажей
	
	# Вычисляем Кс для лифтов до 12 этажей:
	for n, i in enumerate(Elevator_count_SP):
		if len(elevators_groupsnames_below12) == i: # если кол-во лифтов совпало с таблицей СП
			KsElevbelow12cnt = Ks_elevators_below12[n] 
		elif len(elevators_groupsnames_below12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
			KsElevbelow12cnt = Ks_elevators_below12[-1] 
		elif len(elevators_groupsnames_below12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_below12) < Elevator_count_SP[n]:
			x1 = Elevator_count_SP[n-1]
			x2 = len(elevators_groupsnames_below12)
			x3 = Elevator_count_SP[n]
			y1 = Ks_elevators_below12[n-1]
			y3 = Ks_elevators_below12[n]
			KsElevbelow12cnt = interpol (x1, x2, x3, y1, y3)

	# Вычисляем Кс для лифтов 12 этажей и выше:
	for n, i in enumerate(Elevator_count_SP):
		if len(elevators_groupsnames_above12) == i: # если кол-во лифтов совпало с таблицей СП
			KsElevabove12cnt = Ks_elevators_above12[n] 
		elif len(elevators_groupsnames_above12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
			KsElevabove12cnt = Ks_elevators_above12[-1] 
		elif len(elevators_groupsnames_above12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_above12) < Elevator_count_SP[n]:
			x1 = Elevator_count_SP[n-1]
			x2 = len(elevators_groupsnames_above12)
			x3 = Elevator_count_SP[n]
			y1 = Ks_elevators_above12[n-1]
			y3 = Ks_elevators_above12[n]
			KsElevabove12cnt = interpol (x1, x2, x3, y1, y3)

	РуElevbelow12cnt = 0 # Ру лифтов до 12 этажей
	РуElevabove12cnt = 0 # Ру лифтов 12 этажей и выше

	# Вычисляем Ру для лифтов до 12 этажей
	for i in elevators_groupsnames_below12:
		for j in elems_avtomats_elevators:
			if i == j.LookupParameter(Param_Circuit_number).AsString():
				РуElevbelow12cnt = РуElevbelow12cnt + j.LookupParameter(Param_Py).AsDouble()


	# Вычисляем Ру для лифтов 12 этажей и выше
	for i in elevators_groupsnames_above12:
		for j in elems_avtomats_elevators:
			if i == j.LookupParameter(Param_Circuit_number).AsString():
				РуElevabove12cnt = РуElevabove12cnt + j.LookupParameter(Param_Py).AsDouble()


	# Формируем далее строку - пояснение
	if РуElevbelow12cnt > 0 and РуElevabove12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + '+' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + ' + ' 
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт. + '
	elif РуElevbelow12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + ' + ' 
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л. + '
	elif РуElevabove12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) + ' + ' 
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л. + '





	#_____________________________________________________________________________________________________________________________________________
	# Разбираемся с квартирами (код такой же как и в функции расчёта жилого дома)
	Flat_count_average = [] # список с общим количеством квартир. Причём если в данном стояке есть квартиры разной мощности,
	# то список Flat_count_average состоит из подсписков с этими мощностями. Например: [[60, 0, 0], [60, 0, 0], [60, 20, 0]]
	Flat_Pp_wattage_average = [] # аналогично формируется список с расчётными мощностями квартир. Например: [[10.0, 0.0, 0.0], [10.0, 0.0, 0.0], [10.0, 12.0, 0.0]]

	# Из данных по отдельным автоматам нам нужно собрать два общих списка квартир разной мощности и количества в виде:
	'''
	допустим:
	Flat_count
	[[35, 21, 33], [57, 0, 0], [42, 0, 0]]
	Flat_Pp_wattage
	[[8.4000000000000004, 10.0, 15.0], [12.0, 0.0, 0.0], [10.0, 0.0, 0.0]]

	'''
	# Flat_count_average Например: [35, 21+42=63, 33, 57] количество квартир
	# Flat_Pp_wattage_average Например: [8.4000000000000004, 10.0, 15.0, 12] мощности квартир
	# Определяться будем по спискам с мощностями квартир
	# Счётчики: порядковые номера n m l; сами элементы: i, j, k.
	for n, i in enumerate(Flat_Pp_wattage):
		for m, j in enumerate(i): # j - это мощность квартиры
			if j not in Flat_Pp_wattage_average and j > 0:
				Flat_Pp_wattage_average.append(j)
				Flat_count_average.append(Flat_count[n][m])
			elif j in Flat_Pp_wattage_average:
				ind = Flat_Pp_wattage_average.index(j) # текущий индекс совпавшей мощности
				curcntplus = Flat_count_average.pop(ind) + Flat_count[n][m] # удаляем старое кол-во квартир и сразу суммируем к нему новое
				Flat_count_average.insert(ind, curcntplus)

	# Вписываем в пояснения поправочный коэффициент Региона квартир
	if len(Flat_count_average) > 0: # Если в выборке вообще были квартиры
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(Kkr_flats_koefficient) + '*('
		Calculation_explanation_text = Calculation_explanation_text + 'Кп.к*('

	# Рассчитываем Рр квартир
	Pp_flats = 0 # Рр.квартир

	if flat_calculation_way_ts == 1: # способ расчёта - каждый тип квартир со своим Ко
		for n, i in enumerate(Flat_Pp_wattage_average):
			if i == 10: # если расчётная мощность одной квартиры 10 кВт то...
				for m, j in enumerate(Flat_count_SP):
					if Flat_count_average[n] <= 5 and Flat_count_average[n] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
					elif Flat_count_average[n] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
					elif Flat_count_average[n] > Flat_count_SP[m-1] and Flat_count_average[n] < Flat_count_SP[m]:
						x1 = Flat_count_SP[m-1]
						x2 = Flat_count_average[n]
						x3 = Flat_count_SP[m]
						y1 = Flat_unit_wattage_SP[m-1]
						y3 = Flat_unit_wattage_SP[m]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
					elif Flat_count_average[n] == Flat_count_SP[m]:
						Flat_unit_wattage = Flat_unit_wattage_SP[m]
				Pp_flats = Pp_flats + Flat_count_average[n]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного режима
				Calculation_explanation_numbers = Calculation_explanation_numbers + str(round(Flat_unit_wattage, 4)) + '*' + str(Flat_count_average[n]) + '+'
				Calculation_explanation_text = Calculation_explanation_text + 'Ркв.уд*nкв + '

			elif i != 10 and Flat_count_average[n] != 0: # если расчётная мощность одной квартиры не 10 кВт, и больше нуля то и квартир не ноль штук...
				for m, j in enumerate(Flat_count_high_comfort):
					if Flat_count_average[n] <= 5 and Flat_count_average[n] > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
					elif Flat_count_average[n] > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
					elif Flat_count_average[n] > Flat_count_high_comfort[m-1] and Flat_count_average[n] < Flat_count_high_comfort[m]:
						x1 = Flat_count_high_comfort[m-1]
						x2 = Flat_count_average[n]
						x3 = Flat_count_high_comfort[m]
						y1 = Ko_high_comfort[m-1]
						y3 = Ko_high_comfort[m]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
					elif Flat_count_average[n] == Flat_count_high_comfort[m]:
						Ko_unit_high_comfort = Ko_high_comfort[m]
				Pp_flats = Pp_flats + i*Flat_count_average[n]*Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности
				Calculation_explanation_numbers = Calculation_explanation_numbers + str(i) + '*' + str(Flat_count_average[n]) + '*' + str(round(Ko_unit_high_comfort, 4)) + '+'
				Calculation_explanation_text = Calculation_explanation_text + 'Ркв*nкв*Ко + '

	elif flat_calculation_way_ts == 0: # способ расчёта - все квартиры с общим Ко

		Ko_unit_high_comfort = 0 # коэффициент одновременности для всех квартир сразу (кроме 10-киловаттных)
		#Calculation_explanation = '' # строка с пояснением расчёта квартир
		# теперь нужно просто перемножить каждое количество квартир на каждую мощность, всё это сложить и вычислить Ко для общего количества квартир
		sum_count_of_flats = 0 # временная переменная. Суммарное количество квартир для данного стояка.
		sum_Pp_of_flats = 0 # временная переменная. Суммарная мощность всех квартир данного стояка (арифметическая большая сумма).
		Flat_count_10kVt = '' # вспомогательная переменная. Количество 10-киловаттных квартир. Нужна для формирования пояснения.
		for l, m in enumerate(Flat_Pp_wattage_average):

			if m == 10: # если расчётная мощность одной квартиры 10 кВт, то...
				for n, i in enumerate(Flat_count_SP):
					if Flat_count_average[l] <= 5 and Flat_count_average[l] > 0:
						Flat_unit_wattage = Flat_unit_wattage_SP[0] # удельная расчётная электрическая нагрузка при количестве квартир...
						break
					elif Flat_count_average[l] > 1000:
						Flat_unit_wattage = Flat_unit_wattage_SP[13]
						break
					elif Flat_count_average[l] > Flat_count_SP[n-1] and Flat_count_average[l] < Flat_count_SP[n]:
						x1 = Flat_count_SP[n-1]
						x2 = Flat_count_average[l]
						x3 = Flat_count_SP[n]
						y1 = Flat_unit_wattage_SP[n-1]
						y3 = Flat_unit_wattage_SP[n]
						Flat_unit_wattage = interpol (x1, x2, x3, y1, y3)
						break
					elif Flat_count_average[l] == Flat_count_SP[n]:
						Flat_unit_wattage = Flat_unit_wattage_SP[n]
						break
				Pp_flats = Pp_flats + Flat_count_average[l]*Flat_unit_wattage # добавляем мощность очередного типа квартир к Pp данного стояка
				if Flat_unit_wattage != 0:
					Flat_count_10kVt = str(Flat_count_average[l])

			elif m != 10 and Flat_count_average[l] > 0: # если мощность квартиры не 10 кВт AND количество квартир больше нуля
				sum_count_of_flats = sum_count_of_flats + Flat_count_average[l] # добавляем следующее количество квартир к общему количеству
				sum_Pp_of_flats = sum_Pp_of_flats + m * Flat_count_average[l] # добавляем следующую мощность квартиры к суммарной мощности
				if Calculation_explanation_text[-1] == '(':
					Calculation_explanation_text = Calculation_explanation_text + '(' # чтобы скобочка правильно добавлялась

				Calculation_explanation_text = Calculation_explanation_text + 'Pкв.*nкв.+'

				if Calculation_explanation_numbers != '' and Calculation_explanation_numbers[-1] == '(':
					Calculation_explanation_numbers = Calculation_explanation_numbers + '(' # чтобы скобочка правильно добавлялась

				Calculation_explanation_numbers = Calculation_explanation_numbers + str(m) + '*' + str(Flat_count_average[l]) + '+'

				for n, i in enumerate(Flat_count_high_comfort):
					if sum_count_of_flats <= 5 and sum_count_of_flats > 0:
						Ko_unit_high_comfort = Ko_high_comfort[0] # коэффициент одновременности для квартир повышенной комфортности
						break
					elif sum_count_of_flats > 600:
						Ko_unit_high_comfort = Ko_high_comfort[12]
						break
					elif sum_count_of_flats > Flat_count_high_comfort[n-1] and sum_count_of_flats < Flat_count_high_comfort[n]:
						x1 = Flat_count_high_comfort[n-1]
						x2 = sum_count_of_flats
						x3 = Flat_count_high_comfort[n]
						y1 = Ko_high_comfort[n-1]
						y3 = Ko_high_comfort[n]
						Ko_unit_high_comfort = interpol (x1, x2, x3, y1, y3)
						break
					elif sum_count_of_flats == Flat_count_high_comfort[n]:
						Ko_unit_high_comfort = Ko_high_comfort[n]
						break

		Pp_flats = Pp_flats + sum_Pp_of_flats * Ko_unit_high_comfort # считаем мощность квартир повышенной комфортности

		# доформировываем строку-пояснение
		if Ko_unit_high_comfort != 0:
			Calculation_explanation_numbers = Calculation_explanation_numbers[:-1] # убираем последний плюсик
			Calculation_explanation_numbers = Calculation_explanation_numbers + ')*' + str(round(Ko_unit_high_comfort, 4)) + '+'

		if Ko_unit_high_comfort != 0: 
			Calculation_explanation_text = Calculation_explanation_text[:-1] # убираем последний плюсик из строки пояснения
			Calculation_explanation_text = Calculation_explanation_text + ')*Ko+'
			#Calculation_explanation_text = Calculation_explanation_text + ')*' + str(round(Ko_unit_high_comfort, 4))

		if Flat_count_10kVt != '':
			Calculation_explanation_text = Calculation_explanation_text + 'Pкв.уд*nкв.+'
			Calculation_explanation_numbers = Calculation_explanation_numbers + str(round(Flat_unit_wattage, 4)) + '*' + Flat_count_10kVt + '+'

	if Calculation_explanation_numbers[-1] == '+':
		Calculation_explanation_numbers = Calculation_explanation_numbers[:-1]

	# Закрываем итоговую скобочку, связанную с поправочным коэффициентом квартир.
	if Pp_flats > 0: # Если вообще был расчёт квартир
		# убираем последние плюсики и пробелы из строки пояснения
		n = -1
		while Calculation_explanation_text[n] == '+' or Calculation_explanation_text[n] == ' ':
			Calculation_explanation_text = Calculation_explanation_text[:-1]
			n = n - 1
		Calculation_explanation_text = Calculation_explanation_text + ')'
		Calculation_explanation_numbers = Calculation_explanation_numbers + ')'




	#_____________________________________________________________________________________________________________________________________________
	# Собираем цифру общей нагрузки
	# Добавим лифты и квартиры к нагрузке которая без коэффициентов
	Pp_coefficient = 0 # Pp для данного расчёта и записи результата
	Pp_coefficient = Рр_without_coefficients + РуElevbelow12cnt * KsElevbelow12cnt + РуElevabove12cnt * KsElevabove12cnt + Kkr_flats_koefficient * Pp_flats

	# Окончательно формируем строку - пояснение (и убираем последние плюсики и пробелы из неё)
	n = -1
	while Calculation_explanation_text[n] == '+' or Calculation_explanation_text[n] == ' ':
		Calculation_explanation_text = Calculation_explanation_text[:-1]
		n = n - 1

	Calculation_explanation = Calculation_explanation_text + ' = ' + Calculation_explanation_numbers # Calculation_explanation_numbers[:-1]

	# чистим плюсики и пробелы в конце строки
	n = -1
	while Calculation_explanation[n] == '+' or Calculation_explanation[n] == ' ':
		Calculation_explanation = Calculation_explanation[:-1]
		n = n - 1	

	# Вычисляем условный Кс на всю нагрузку
	Kc_cond_coefficient = Pp_coefficient / Py_sum

	# Пишем результаты
	calculation_table.LookupParameter(Param_Explanation).Set(Calculation_explanation)
	calculation_table.LookupParameter(Param_Py).Set(round(Py_sum, Round_value_ts)) # Пишем Py
	calculation_table.LookupParameter(Param_Kc).Set(round(Kc_cond_coefficient, 2)) # Пишем Kc
	calculation_table.LookupParameter(Param_Pp).Set(round(Pp_coefficient, Round_value_ts)) # Пишем Pp
	calculation_table.LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
	calculation_table.LookupParameter(Param_Ip).Set(round(Pp_coefficient / cosf_average / U3fsqrt3forI, Round_value_ts)) # Пишем Ip
	calculation_table.LookupParameter(Param_Sp).Set(round(Pp_coefficient / cosf_average, Round_value_ts)) # Пишем Sp
	calculation_table.LookupParameter(Param_IdQFsCalc).Set(Str_Ids_elems_avtomats) # Пишем Idшники автоматов на которых был произведён расчёт












# Функция Ру или Рр есть мощность по её имени
# На выходе 'Py' или 'Pp'
# Обращение PyorPpDepOnPName('Рр.сантех.', Readable_znachP)
def PyorPpDepOnPName (Pname, Readable_znachP):
	ExitStr = ''
	for i in Readable_znachP:
		if i[0] == Pname:
			ExitStr = ExitStr + i[2]
	return ExitStr

# Функция поиска необходимых строк в таблицах Кс
# На входе значение (числовое), список в котором нужно искать (строковый)
# На выходе кортеж индексов строк (ближайшая меньшая строка, ближайшая большая строка, конкретная строка, если искали по списку с процентами для таблиц с удельным весом)
# Пример обращения FindNeesesStrings(UnitWeightPercent, precentageList)
def FindNeesesStrings (ValueToFind, ListSearch):
	NeededStringIndexHigh = 0 # индекс ближайшей большей строки
	NeededStringIndexLow = 0 # индекс ближайшей меньшей строки
	NeededStringIndex = 0 # а это индекс прямо нужной нам строки
	if float(ListSearch[0]) > float(ListSearch[-1]): # Если список был по убыванию ['100', '84', '74', '49', '24']
		for n, i in enumerate(ListSearch): 
			if ValueToFind < float(i):
				try:
					if ValueToFind < float(ListSearch[n+1]):
						#ara1 = 1222
						pass
					elif ValueToFind > float(ListSearch[n+1]):
						NeededStringIndexHigh = n
						NeededStringIndexLow = n+1
						#ara = 2
						break
				except:
					NeededStringIndexHigh = n
					NeededStringIndexLow = n
					#ara = 3
					break
			elif ValueToFind == float(i):
				NeededStringIndexHigh = n
				NeededStringIndexLow = n
				#ara = 4
				break
			elif ValueToFind > float(i):
				NeededStringIndexHigh = n
				NeededStringIndexLow = n
				#ara = 5
				break
		NeededStringIndex = NeededStringIndexLow
	else: # Если список был по возрастанию ['24', '49', '74', '84', '100']
		for n, i in enumerate(ListSearch): 
			if ValueToFind > float(i):
				try:
					if ValueToFind > float(ListSearch[n+1]):
						pass
					elif ValueToFind < float(ListSearch[n+1]):
						NeededStringIndexLow = n
						NeededStringIndexHigh = n+1
						break
				except:
					NeededStringIndexHigh = n
					NeededStringIndexLow = n
					break
			elif ValueToFind == float(i):
				NeededStringIndexHigh = n
				NeededStringIndexLow = n
				break
			elif ValueToFind < float(i):
				NeededStringIndexHigh = n
				NeededStringIndexLow = n
				break
		NeededStringIndex = NeededStringIndexHigh
	return NeededStringIndexLow, NeededStringIndexHigh, NeededStringIndex
'''
Чтоб тестить
ValueToFind = UnitWeightPercent
ListSearch = precentageList
'''



# Функция по выбору значения Кс из таблицы при зависимости удельного веса мощности от других нагрузок
# На входе: мощность по конкретному Кс, кол-во эл.приёмников по конкретному Кс, общая мощность от которой зависит данный Кс (другие нагрузки), значения (список) Кс в котором будем искать значение
# содержимое таблицы в виде: [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84', '1', '1', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74', '1', '1', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49', '1', '1', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '1', '1', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]
# На выходе значение Кс (float)
# Пример обращения: FindKcWithPDependent(PsumforKc[n], ConsumersSumforKc[n], curPsum, j[11])
# Пример обращения: FindKcWithPDependent(0.1, 2, 1.34, j[11])            
def FindKcWithPDependent (PbyKc, ConsumersCountbyKc, PaveragebyKc, ElementInReadable_znachKc):
	# Определимся в какой строке надо оскать Кс. Для этого вычислим удельный вес меньшей мощности в большей
	UnitWeightPercent = (PbyKc *100) / PaveragebyKc # Результат В ПРОЦЕНТАХ, например: 7.4626865671641784

	# Выстроим значения процентов в таблице в одном списке:
	precentageList = []
	for n, i in enumerate(ElementInReadable_znachKc):
		if n > 0:
			precentageList.append(i[0]) # ['100', '84', '74', '49', '24']. или ['24', '49', '74', '84', '100']

	NeededStringIndex = FindNeesesStrings(UnitWeightPercent, precentageList)[2] # Ищем нужную строку в столбце с процентами

	if NeededStringIndex == 0: # если попали прямо в 100% в других нагрузках (в первый элемент списка процентов). Была такая бага у юзера. Тогда нужно искать не в 0-й строке где у нас число ЭР, а всё-таки в 1-й где значения Кс.
		NeededStringIndex = NeededStringIndex + 1
	elif NeededStringIndex == len(precentageList)-1 and FindNeesesStrings(UnitWeightPercent, precentageList)[0] == FindNeesesStrings(UnitWeightPercent, precentageList)[1] == FindNeesesStrings(UnitWeightPercent, precentageList)[2]: # если попали в последний элемент списка процентов. Тоже добавляем 1 к номеру строки, а то он начинает выбирать по предыдущей строке (предыдущему проценту).
		NeededStringIndex = NeededStringIndex + 1

	# Итого, нужная нам строка с Кс ElementInReadable_znachKc[NeededStringIndex] - ['24', '1', '1', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']
	# теперь ищем нужный нам столбец (вернее диапазон столбец слева и справа от нужного значения)
	# Но опять же ищем начиная не с 0-го элемента, т.к. в нулевом проценты, а не кол-во эл.приём. А получаем индекс по списку
	LowStrIndex = FindNeesesStrings(ConsumersCountbyKc, ElementInReadable_znachKc[0][1:])[0] + 1
	HighStrIndex = FindNeesesStrings(ConsumersCountbyKc, ElementInReadable_znachKc[0][1:])[1] + 1
	# В нашем примере оба значения получились единички, т.к. у нас кол-во эл.приём было 2.

	# Теперь выберем Кс если мы получили граничные значения (минимальное или максимальное или точно попали в кол-во потребителей)
	KcResValue = 1 # во избежание возможных баг наверное для начала
	if LowStrIndex == HighStrIndex and HighStrIndex == 1: # левое значение
		KcResValue = float(ElementInReadable_znachKc[NeededStringIndex][1])
	elif LowStrIndex == HighStrIndex and HighStrIndex == len(ElementInReadable_znachKc[NeededStringIndex])-1: # правое значение
		KcResValue = float(ElementInReadable_znachKc[NeededStringIndex][len(ElementInReadable_znachKc[NeededStringIndex])-1])
	elif LowStrIndex == HighStrIndex and HighStrIndex != 1 and HighStrIndex != len(ElementInReadable_znachKc[NeededStringIndex])-1: # совпавшее значение
		KcResValue = float(ElementInReadable_znachKc[NeededStringIndex][HighStrIndex])
	else: # интерполируем
		try:
			KcResValue = interpol(float(ElementInReadable_znachKc[0][LowStrIndex]), ConsumersCountbyKc, float(ElementInReadable_znachKc[0][HighStrIndex]), float(ElementInReadable_znachKc[NeededStringIndex][LowStrIndex]), float(ElementInReadable_znachKc[NeededStringIndex][HighStrIndex]))
		except ZeroDivisionError:
			TaskDialog.Show('Ошибка', 'Один из коэффициентов спроса, используемых при расчёте равен нулю. Такого быть не должно. Проверьте Таблицы с коэффициентами спроса в Настройках.')

	if KcResValue > 1: # Проверка чтобы Кс не был больше 1.
		TaskDialog.Show('Ошибка', 'Один из коэффициентов спроса, используемых при расчёте больше 1. Такого быть не должно. Проверьте Таблицы с коэффициентами спроса в Настройках или обратитесь к разработчику.')

	return KcResValue

'''
Чтоб тестить
PbyKc = 21
ConsumersCountbyKc = 15
PaveragebyKc = 59
ElementInReadable_znachKc = Readable_znachKc[3][11]
precentageList = ['100', '84', '74', '49', '24']
precentageList = ['24', '49', '74', '84', '100']

PbyKc =3.1
ConsumersCountbyKc = 4
PaveragebyKc = 8.6
ElementInReadable_znachKc = Readable_znachKc[8][11]
precentageList = ['100', '84', '74', '49', '24']

#NeededStringIndex = NeededStringIndex + 1 # т.к. мы начинали не с 0-й строки, а искать-то надо по всему списку ElementInReadable_znachKc. Не надо это??!! Было неправильно!
'''



# Функция поиска Кс по таблице Кс в зависимости от кол-ва или мощности эл.приём (что по сути одно и то же для функционала)
# На входе: мощность по конкретному Кс ИЛИ кол-во эл.приёмников по конкретному Кс,  
# содержимое таблицы в виде: [['5', '10', '15', '25', '50', '100', '200', '400', '500'], ['1', '0.8', '0.7', '0.6', '0.5', '0.4', '0.35', '0.3', '0.3']]
# На выходе значение Кс (float)
# пример обращения: FindKc(6, j[11])     FindKc(ConsumersSumforKc[n], j[11])
def FindKc (PorConsumersCountbyKc, ElementInReadable_znachKc):
	# Искать столбец надо в этой: ElementInReadable_znachKc[0] - ['5', '10', '15', '25', '50', '100', '200', '400', '500']
	# А нужная нам строка с Кс ElementInReadable_znachKc[1] - ['1', '0.8', '0.7', '0.6', '0.5', '0.4', '0.35', '0.3', '0.3']
	# Ищем нужный нам столбец (вернее диапазон столбец слева и справа от нужного значения)
	LowStrIndex = FindNeesesStrings(PorConsumersCountbyKc, ElementInReadable_znachKc[0])[0]
	HighStrIndex = FindNeesesStrings(PorConsumersCountbyKc, ElementInReadable_znachKc[0])[1]

	# Теперь выберем Кс если мы получили границные значения (минимальное или максимальное или точно попали в кол-во потребителей)
	KcResValue = 1 # во избежание возможных баг наверное для начала
	if LowStrIndex == HighStrIndex and HighStrIndex == 0: # левое значение
		KcResValue = float(ElementInReadable_znachKc[1][0])
	elif LowStrIndex == HighStrIndex and HighStrIndex == len(ElementInReadable_znachKc[0])-1: # правое значение
		KcResValue = float(ElementInReadable_znachKc[1][len(ElementInReadable_znachKc[0])-1])
	elif LowStrIndex == HighStrIndex and HighStrIndex != 0 and HighStrIndex != len(ElementInReadable_znachKc[0])-1: # совпавшее значение
		KcResValue = float(ElementInReadable_znachKc[1][HighStrIndex])
	else: # интерполируем
		try:
			KcResValue = interpol(float(ElementInReadable_znachKc[0][LowStrIndex]), PorConsumersCountbyKc, float(ElementInReadable_znachKc[0][HighStrIndex]), float(ElementInReadable_znachKc[1][LowStrIndex]), float(ElementInReadable_znachKc[1][HighStrIndex]))
		except ZeroDivisionError:
			TaskDialog.Show('Ошибка', 'Один из коэффициентов спроса, используемых при расчёте равен нулю. Такого быть не должно. Проверьте Таблицы с коэффициентами спроса в Настройках.')

	return KcResValue






# Отдельная функция по лифтам
# Выдаёт строки с пояснением текстовым и числовым по лифтам
def ElevatorsCounts (Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12):
	#_____________________________________________________________________________________________________________________________________________
	# Разбираемся с лифтами
	#elems_avtomats_elevators
	#elevators_groupsnames_below12 # группы у которых лифты до 12 этажей
	#elevators_groupsnames_above12 # группы у которых лифты 12 и выше этажей
	# Сначала вычисли коэффициенты спроса для лифтов до и более 12 этажей.
	KsElevbelow12cnt = 0 # Кс лифтов до 12 этажей
	KsElevabove12cnt = 0 # Кс лифтов до 12 этажей
	
	# Вычисляем Кс для лифтов до 12 этажей:
	for n, i in enumerate(Elevator_count_SP): # [1, 2, 3, 4, 5, 6, 10, 20, 25]
		if len(elevators_groupsnames_below12) == i: # если кол-во лифтов совпало с таблицей СП
			KsElevbelow12cnt = Ks_elevators_below12[n] 
		elif len(elevators_groupsnames_below12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
			KsElevbelow12cnt = Ks_elevators_below12[-1] 
		elif len(elevators_groupsnames_below12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_below12) < Elevator_count_SP[n]:
			x1 = Elevator_count_SP[n-1]
			x2 = len(elevators_groupsnames_below12)
			x3 = Elevator_count_SP[n]
			y1 = Ks_elevators_below12[n-1]
			y3 = Ks_elevators_below12[n]
			KsElevbelow12cnt = interpol (x1, x2, x3, y1, y3)

	# Вычисляем Кс для лифтов 12 этажей и выше:
	for n, i in enumerate(Elevator_count_SP):
		if len(elevators_groupsnames_above12) == i: # если кол-во лифтов совпало с таблицей СП
			KsElevabove12cnt = Ks_elevators_above12[n] 
		elif len(elevators_groupsnames_above12) > Elevator_count_SP[-1]: # если лифтов более 25 (последний член списка)
			KsElevabove12cnt = Ks_elevators_above12[-1] 
		elif len(elevators_groupsnames_above12) > Elevator_count_SP[n-1] and len(elevators_groupsnames_above12) < Elevator_count_SP[n]:
			x1 = Elevator_count_SP[n-1]
			x2 = len(elevators_groupsnames_above12)
			x3 = Elevator_count_SP[n]
			y1 = Ks_elevators_above12[n-1]
			y3 = Ks_elevators_above12[n]
			KsElevabove12cnt = interpol (x1, x2, x3, y1, y3)

	РуElevbelow12cnt = 0 # Ру лифтов до 12 этажей
	РуElevabove12cnt = 0 # Ру лифтов 12 этажей и выше

	# Вычисляем Ру для лифтов до 12 этажей
	for i in elevators_groupsnames_below12:
		for j in elems_avtomats_elevators:
			if i == j.LookupParameter(Param_Circuit_number).AsString():
				РуElevbelow12cnt = РуElevbelow12cnt + j.LookupParameter(Param_Py).AsDouble()


	# Вычисляем Ру для лифтов 12 этажей и выше
	for i in elevators_groupsnames_above12:
		for j in elems_avtomats_elevators:
			if i == j.LookupParameter(Param_Circuit_number).AsString():
				РуElevabove12cnt = РуElevabove12cnt + j.LookupParameter(Param_Py).AsDouble()


	# Формируем далее строку - пояснение
	Calculation_explanation_numbers = '' # '13.0*0.9'
	Calculation_explanation_text = '' # 'Ру.л*Кс.л.'
	if РуElevbelow12cnt > 0 and РуElevabove12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) + '+' + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt) 
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт.'
	elif РуElevbelow12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevbelow12cnt) + '*' + str(KsElevbelow12cnt) 
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л.'
	elif РуElevabove12cnt > 0:
		Calculation_explanation_numbers = Calculation_explanation_numbers + str(РуElevabove12cnt) + '*' + str(KsElevabove12cnt)
		Calculation_explanation_text = Calculation_explanation_text + 'Ру.л*Кс.л.'

	ExitKc = []
	if KsElevbelow12cnt == 0:
		ExitKc = [KsElevabove12cnt]
	elif KsElevabove12cnt == 0:
		ExitKc = [KsElevbelow12cnt]
	else: # если есть лифты и до и более 12 этажей
		ExitKc = [KsElevbelow12cnt, KsElevabove12cnt]

	# Если лифтов не было, то запишем в поянение цифр нули. Чтобы пользователь увидел в цифровом пояснении формулы что мощность и Кс лифтов у него ноль.
	if Calculation_explanation_numbers == '': 
		Calculation_explanation_numbers = '0*0'


	return ExitKc, Calculation_explanation_text, Calculation_explanation_numbers




# Функция по очистке Calculation_explanation_numers от всякой ереси
# На входе корявая строка
# На выходе строка отличная
# Calculation_explanation_numers = '0.04*0.96+1.0*0.9+0.1*1.0+*+0.2'
# Пример обращения: Clear_caclformula('0.04*0.96+1.0*0.9+0.1*1.0+*+0.2')
def Clear_caclformula (Calculation_explanation_numers):
	'''
	ara = 'abcdef'
	ara[:2] - 'ab' выкидывает начиная со 2 элемента включительно
	ara[3:] - 'def' начинает с 3 элемента включительно
	ara.find('c') - 2
	Calculation_explanation_numers = '*+0.04*0.96+*+(+1.0*0.9+)++0.1*1.0+*+0.2+'
	'''
	# Прогоним это всё раз 5 от греха)
	for i in range(5):
		# Почистим просто по известным мне шаблонам
		while '+*+' in Calculation_explanation_numers: # Превращаем '+*+'  в '+'
			beginindex = Calculation_explanation_numers.find('+*+')
			Calculation_explanation_numers = Calculation_explanation_numers[:beginindex] + Calculation_explanation_numers[beginindex+2:]
		while '++' in Calculation_explanation_numers: # Превращаем '++'  в '+'
			beginindex = Calculation_explanation_numers.find('++')
			Calculation_explanation_numers = Calculation_explanation_numers[:beginindex] + Calculation_explanation_numers[beginindex+1:]
		while '(+' in Calculation_explanation_numers: # Превращаем '(+'  в '('
			beginindex = Calculation_explanation_numers.find('(+')
			Calculation_explanation_numers = Calculation_explanation_numers[:beginindex+1] + Calculation_explanation_numers[beginindex+2:]
		while '+)' in Calculation_explanation_numers: # Превращаем '+)'  в ')'
			beginindex = Calculation_explanation_numers.find('+)')
			Calculation_explanation_numers = Calculation_explanation_numers[:beginindex] + Calculation_explanation_numers[beginindex+1:]
		while '*+' in Calculation_explanation_numers: # Превращаем '*+'  в '+'
			beginindex = Calculation_explanation_numers.find('*+')
			Calculation_explanation_numers = Calculation_explanation_numers[:beginindex] + Calculation_explanation_numers[beginindex+1:]
		# Почистим математические символы в начале и конце формулы кроме скобок
		MathSymbToClear = ['+', '-', '*', '/']
		while Calculation_explanation_numers[0] in MathSymbToClear: # Чистим начало
			Calculation_explanation_numers = Calculation_explanation_numers[1:]
		while Calculation_explanation_numers[-1] in MathSymbToClear: # Чистим окончание
			Calculation_explanation_numers = Calculation_explanation_numers[:-1]

	return Calculation_explanation_numers


'''
# Вот эти 'Ру (вся)', 'Рр (вся)' сделаем переменными, чтобы потом в коде на них ссылаться и переименовывать легко если надо
# ОНИ ТУТ КАК В НАСТРОЙКАХ. ОТДЕЛЬНО НЕ МЕНЯТЬ.
PyAll = 'Ру (вся)' # соответствующая ей особая классификация нагрузок: 'ALL'
PpAll = 'Рр (вся)' # 'ALL'
PyNoClass = 'Ру (без классиф.)' # 'Нет классификации' или ''
PpNoClass = 'Рр (без классиф.)' # 'Нет классификации' или ''
PyOtherClass = 'Ру (др. классиф.)' # 'OTHER'
PpOtherClass = 'Рр (др. классиф.)' # 'OTHER'
'''

# aralst = ['cat', 'dog', 'pig', 'bird', 'bear']
# [p for p in aralst]
# обращение DelElFromList([p for p in aralst], 'pig')
# функция удаляет элемент из списка и возвращает список без удалённого элемента
'''
def DelElFromList(lst, what_to_remove):
    lst.remove(what_to_remove)
    return lst
'''


# Ру.раб.осв. * Кс.о. + Ру.гор.пищ. * Кс.гор.пищ. + Ру.сантех. * Кс.сан.тех. + Ру.л * Кс.л. + Рр (без классиф.)

# Функция записи в табличку по пользовательскому режиму расчёта
# Пример обращения: 
def UserFormula_Write_to_calculation_table (UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, calculation_table, Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, Write_to_table):
	# Итак, начнём-с )

	# Из всех выбранных автоматов соберём список вида:
	# [[Py, Pp, Классификация нагрузок, Число электроприёмников, cosf], аналогично для всех автоматов....]
	Avtomats_DataForUserFormula = [] # Вид: [[0.2, 0.2, '', 2, 0.93], [0.1, 0.1, u'Системы ОВ', 2, 0.93], [0.01, 0.01, u'Рабочее освещение', 2, 0.977], [0.03, 0.03, u'Рабочее освещение', 4, 0.97], [0.5, 0.5, u'Тепловое оборудование пищеблоков', 1, 0.85], [0.5, 0.5, u'Тепловое оборудование пищеблоков', 1, 0.85]]	
	for i in elems_avtomats:
		curel = []
		curel.append(i.LookupParameter(Param_Py).AsDouble())
		curel.append(i.LookupParameter(Param_Pp).AsDouble())
		curel.append(i.LookupParameter(Param_Load_Class).AsValueString())
		curel.append(i.LookupParameter(Param_Consumers_count).AsInteger())
		curel.append(i.LookupParameter(Param_Cosf).AsDouble())
		Avtomats_DataForUserFormula.append(curel)

	# Теперь вытащим из хранилища нужную нам формулу
	for i in Readable_znachUserFormula:
		if i[0] == UserFormulaSelected:
			UserFormulaList = i # ['test count', [u'Рраб.осв.', '*', u'Кс.о.', '+', u'Ргор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Рр.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру (вся)', '*', u'Кс.л.', '+', u'Рр (без классиф.)'], u'Резерв 1', u'Резерв 2', u'Резерв 3']

	# Список со всеми возможными мощностями из Хранилища
	AvailablePList = [] # Вид: [u'Ру (вся)', u'Рр (вся)', u'Ру (без классиф.)', u'Рр (без классиф.)', u'Ру (др. классиф.)', u'Рр (др. классиф.)', u'Ру.л', u'Рр.ов', u'Ргор.пищ.']
	for i in Readable_znachP:
		AvailablePList.append(i[0]) 

	# Список с мощностями из формулы. Из формулы вытащим имена мощностей которые в ней задействованы
	PinFormula = [] # Вид: [u'Рр.сантех.', u'Рр (др. классиф.)']
	for i in UserFormulaList[1]: # [u'Рраб.осв.', '*', u'Кс.о.', '+', u'Ргор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Рр.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру.л', '*', u'Кс.л.', '+', u'Рр (без классиф.)']
		if i in AvailablePList:
			PinFormula.append(i)

	FormulaClassList = [] # Список с классификациями на которые распространяется формула. Вид: ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ', 'other']
	for i in PinFormula:
		for j in Readable_znachP: # [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рраб.осв.', [u'Рабочее освещение'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ргор.пищ.', [u'Тепловое оборудование пищеблоков'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ру (без классиф.)', [u'Нет классификации'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (без классиф.)', [u'Нет классификации', ''], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.ов', [u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ру.л', [u'Лифты'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
			if i == j[0]: # если совпало имя мощности
				for k in j[1]:
					FormulaClassList.append(k)

	LoadClasses = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_ElectricalLoadClassifications).ToElements()
	LoadClassesNames = []
	for i in LoadClasses:
		LoadClassesNames.append(i.Name) # Имена всех классификаций в проекте.

	# Если у нас в формуле есть Ру (др. классиф.) или Рр (др. классиф.)
	# Все классификации нагрузок кроме тех что уже участвуют в формуле
	FormulaClassListOther = [] # [u'Прочее', u'Мощность', u'Освещение', 'hvac', u'Двигатель', u'Резервная', u'Квартиры', u'Лифты', u'Силовые цепи', u'Резервные', u'Аварийное освещение', u'НКУ', u'Подъёмные механизмы', u'Полотенцесушители', u'Посудомоечные машины', u'Розетки', u'Термическая нагрузка', u'Холодильные установки', u'ЭВМ', u'Рабочее освещение', u'Розетки бытовые', u'Розетки компьютерные', u'Розетки технологические', u'Механическое оборудование', u'Апартаменты', u'Офисы']
	if 'Ру (др. классиф.)' in PinFormula or 'Рр (др. классиф.)' in PinFormula:
	# Если у нас в формуле есть Ру (др. классиф.) или Рр (др. классиф.), то нужен список всех классификаций из модели.
	# И этим мощностям мы присвоим все классификации кроме тех, что уже есть в других мощностях формулы.
		# Теперь добавим все остальные классификации в FormulaClassList, чтобы не выкинуть нужные автоматы из выборки.
		for i in LoadClassesNames:
			if i not in FormulaClassList and i != 'Нет классификации': # Нет классификации тоже выкидываем, чтобы не было задвоения по мощности
				FormulaClassListOther.append(i)
		hlp_lst2 = FormulaClassList + FormulaClassListOther
		FormulaClassList = [i for i in hlp_lst2] # Теперь тут вообще все классификации. То есть по сути мы уже никакие автоматы из выборки не выкидываем.
	elif 'Ру (вся)' in PinFormula or 'Рр (вся)' in PinFormula:
	# Если у нас в формуле есть Ру вся или Рр, то нужен список всех классификаций из модели.
	# Теперь добавим все классификации в FormulaClassList, чтобы не выкинуть нужные автоматы из выборки.
		for i in LoadClassesNames:
			if i not in FormulaClassList:
				FormulaClassListOther.append(i)
		hlp_lst2 = FormulaClassList + FormulaClassListOther
		FormulaClassList = [i for i in hlp_lst2] # Теперь тут вообще все классификации. То есть по сути мы уже никакие автоматы из выборки не выкидываем.
	
					
	# Список Avtomats_DataForUserFormula нужно фильтрануть. Выкинуть из него данные автоматов с теми классификациями нагрузок, которые не рассчитываются формулой.		
	hlp_lst = []
	LoadClassesAbsence = []
	for i in Avtomats_DataForUserFormula:
		if i[2] in FormulaClassList: # если у автомата та классификация которая есть в формуле
			hlp_lst.append(i)
		else: 
			if i[2] not in LoadClassesAbsence:
				if i[2] == '' and 'Нет классификации' not in LoadClassesAbsence:
					LoadClassesAbsence.append('Нет классификации')
				else:
					LoadClassesAbsence.append(i[2])
	Avtomats_DataForUserFormula = [i for i in hlp_lst] # Пересобираем список. Теперь в нём только автоматы с классификацией которая есть в формуле.

	# Если внезапно пришлось выкинуть все автоматы, это значит:
	if Avtomats_DataForUserFormula == []:
		raise Exception('Среди выбранных автоматов нет ни одного с классификацией нагрузок которая входит в выбранную Вами формулу. Расчёт прерван.')


	# Сделаем суммарную Ру и Рр (для выбора коэффициентов спроса пригодится)
	PySum = 0 # Вид: 1.34
	PpSum = 0 # Вид: 1.34
	for i in Avtomats_DataForUserFormula:
		PySum = PySum + i[0]
		PpSum = PpSum + i[1]


	# Сделаем три списка в полном соответствии друг с другом. В первом имена мощностей, во втором их значения собранные с автоматов.
	# В третьем число электроприёмников по каждой мощности
	PNamesListinProject = [] # Вид: [u'Рраб.осв.', u'Ргор.пищ.', u'Рр.сантех.', u'Ру.л', u'Рр (без классиф.)']
	#global PpowerListinProject
	PpowerListinProject = [] # Вид: [16.800000000000001, 0, 50.600000000000001, 24.0, 40.700000000000003]
	PConsumersListinProject = [] # Вид: [6, 2, 2, 2] число электроприёмников по каждой мощности
	# А также список с классификациями нагрузок которые входят в мощности участвующие в расчётах (в точном соответствии с PNamesListinProject)
	LoadClassNamesinProject = [] # Вид: [[u'Рабочее освещение'], [u'Тепловое оборудование пищеблоков'], ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], [u'Лифты'], [u'Нет классификации', '', '', '', '']]
	# А также список в котором для каждой мощности указано что надо брать с автоматов: Py или Pp
	PyOrPpListinProject = [] # Вид: ['Pp', 'Pp', 'Pp', 'Py', 'Pp']
	# А также список Кс которые применяются в данном расчёте 
	KcNamesListinProject = [] # Вид: [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.', u'Кс.л.']

	# Список с Кс из хранилища
	AvailableKcList = [] # [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.']
	for i in Readable_znachKc:
		AvailableKcList.append(i[2])

	for i in UserFormulaList[1]: # Собственно сама формула: [u'Рраб.осв.', '*', u'Кс.о.', '+', u'Ргор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Рр.сантех.', '*', u'Кс.сан.тех.', '+', u'Рр (без классиф.)']
		if i in AvailablePList:
			PNamesListinProject.append(i)
		if i in AvailableKcList:
			KcNamesListinProject.append(i)

	for i in PNamesListinProject:
		PpowerListinProject.append(0) # Заготовочка чтобы плюсовать мощности было удобно [0, 0, 0, 0]
		PConsumersListinProject.append(0)

	for i in PNamesListinProject:
		for j in Readable_znachP:
			if i == j[0]: # если совпало имя мощности
				LoadClassNamesinProject.append(j[1])
				PyOrPpListinProject.append(j[2])

	# Сделаем проверку если в формуле есть мощность которой нет среди выбранных автоматов. 
	for i in PinFormula: # [u'Ргор.пищ.', u'Ру.л', u'Рр (без классиф.)']
		if i not in PNamesListinProject:
			raise Exception('В расчётной формуле есть мощность "' + i + '", её классификации нагрузок нет среди выбранных автоматов. Расчёт будет некорректным. Зайдите в Настройки и добавьте новую мощность с нужными классификациями нагрузок.')
			break

	# Если классификация не заполнена, то добавим пустую строку в член 'Нет классификации', если такой есть
	for n, i in enumerate(PNamesListinProject):
		if i == 'Ру (без классиф.)' or i == 'Рр (без классиф.)':
			LoadClassNamesinProject[n].append('')
		if i == 'Ру (др. классиф.)' or i == 'Рр (др. классиф.)' or i == 'Ру (вся)' or i == 'Рр (вся)':
			LoadClassNamesinProject[n] = FormulaClassListOther # [['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], [u'Прочее', u'Мощность', u'Освещение', 'hvac', u'Двигатель', u'Резервная', u'Квартиры', u'Лифты', u'Силовые цепи', u'Резервные', u'Аварийное освещение', u'НКУ', u'Подъёмные механизмы', u'Полотенцесушители', u'Посудомоечные машины', u'Розетки', u'Термическая нагрузка', u'Холодильные установки', u'ЭВМ', u'Рабочее освещение', u'Розетки бытовые', u'Розетки компьютерные', u'Розетки технологические', u'Механическое оборудование', u'Апартаменты', u'Офисы']]

	# Если в выборке есть автоматы с классификацией которой нет в Формуле, то нужно как-то предупредить пользователя.
	if LoadClassesAbsence != []:
		if 'Ру (др. классиф.)' not in PNamesListinProject and 'Рр (др. классиф.)' not in PNamesListinProject:
			if Write_to_table == True: # если считаем просто по пользовательскому режиму (без жилого дома)
				TaskDialog.Show('Расчёт схем', 'В выборке есть автоматы с классификациями которых нет в Формуле. Отсутствующие в формуле классификации: ' + ', '.join(LoadClassesAbsence) + '. Мощности этих классификаций нагрузок не будут учтены в результате расчёта.')
			else: # а если считам режимом пользовательский + жилой дом, то не нужно выводить сообщение об отсутствии классификаций Квартиры
				try:
					LoadClassesAbsence_hlp = [i for i in LoadClassesAbsence]# здесь выкинули Квартиры и Апартаменты
					LoadClassesAbsence_hlp.remove('Квартиры')
					LoadClassesAbsence_hlp.remove('Апартаменты')
					if LoadClassesAbsence_hlp != []:
						TaskDialog.Show('Расчёт схем', 'В выборке есть автоматы с классификациями которых нет в Формуле. Отсутствующие в формуле классификации: ' + ', '.join(LoadClassesAbsence) + '. Мощности этих классификаций нагрузок не будут учтены в результате расчёта.')
				except:
					pass

	# Теперь посчитаем значения мощностей, учатсвующих в формуле.
	# Для этого вытащим из Хранилища классификации нагрузок для мощностей, участвующих в формуле,
	# И по ним соберём каждую отдельную мощность.
	for n, i in enumerate(LoadClassNamesinProject): # i это [u'Рабочее освещение']
		for j in Avtomats_DataForUserFormula: # j это [0.1, 0.1, u'Системы ОВ', 2, 0.93]
			if j[2] in i: # Если у конкретного автомата классификация нагрузок соответствует списку Р участвующих в расчётах...
				if PyOrPpListinProject[n].upper() == 'Py'.upper(): # понимаем какую мощность брать с автомата...
					PpowerListinProject[n] = PpowerListinProject[n] + j[0] # суммируем мощность
				else: # если берём расчётную мощность
					PpowerListinProject[n] = PpowerListinProject[n] + j[1] # суммируем мощность
				PConsumersListinProject[n] = PConsumersListinProject[n] + j[3] # суммируем число электроприёмников

	# Теперь будем подбирать Кс для каждой мощности в проекте.
	# Для этого соберём список в соответствии с KcNamesListinProject (# Вид: [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.']), 
	# в котором будут суммарные мощности для каждого Кс.
	# И такой же список с суммарным количеством электроприёмников для каждого Кс
	PsumforKc = [] # Вид: [16.800000000000001, 0, 50.600000000000001, 24.0]
	ConsumersSumforKc = [] # Вид: [39, 0, 15, 15]
	for i in KcNamesListinProject:
		PsumforKc.append(0) # Заготовочки по числу Кс-ов участвующих в расчёте
		ConsumersSumforKc.append(0) # [0, 0, 0]
	# Ещё нужен список на какие мощности влияет каждый Кс.
	KcDependsOnP_ListinProject = [] # Вид: [[u'Рраб.осв.'], [u'Ргор.пищ.'], [u'Рр.сантех.', u'Рр.ов']] или [[u'Рраб.осв.'], [u'Ргор.пищ.'], [u'Рр.сантех.', u'Рр.ов'], [u'Ру.л']]
	for i in KcNamesListinProject:
		for j in Readable_znachKc:
			if i == j[2]: # если совпало имя Кс
				KcDependsOnP_ListinProject.append(j[6])
	for n, i in enumerate(KcDependsOnP_ListinProject):
		for m, j in enumerate(PNamesListinProject): # [u'Рраб.осв.', u'Ргор.пищ.', u'Рр.сантех.', u'Рр (без классиф.)']
			if j in i: # Если совпали имена мощностей
				PsumforKc[n] = PsumforKc[n] + PpowerListinProject[m]
				ConsumersSumforKc[n] = ConsumersSumforKc[n] + PConsumersListinProject[m]

	# Ну всё, все списки готовы, теперь нужно выбрать значения Кс из хранилища.
	KcValues = [] # [0.68, 0.9, 0.5, [0.9]]
	elevRes = [] # результат по лифтам ([1.0, 1.0], u'Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт.', '6.5*1.0+6.5*1.0')
	for n, i in enumerate(KcNamesListinProject): # Вид: [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.'] или [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.', u'Кс.л.']
		if i == 'Кс.л.': # если лифты, с ними отдельная песня
			elevRes = ElevatorsCounts(Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12)
			KcValues.append(elevRes[0])
		else: # Если не лифты, продолжаем
			for j in Readable_znachKc: # j - текущие данные по Кс. [u'Таблица 7.5 - Коэффициенты спроса для сантехнического оборудования и холодильных машин', u'Системы ОВ', u'Кс.сан.тех.', 'epcount', u'Зависит от уд.веса в других нагрузках', [u'Ру (вся)'], [u'Рр.сантех.', u'Рр.ов'], [u'Резерв 2'], [u'Резерв 3'], ['column1', 'column2', 'column3', 'column4', 'column5', 'column6', 'column7', 'column8', 'column9', 'column10', 'column11', 'column12'], [u'Столбец 1. Удельный вес установленной мощности работающего сантехнического и холодильного оборудования, включая системы кондиционирования воздуха в общей установленной мощности работающих силовых электроприемников, \\', u'Столбец 2. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 3. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 4. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 5. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 6. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 7. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 8. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 9. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 10. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 11. Число ЭП (в 1-й строке), значения Кс (в остальных строках)', u'Столбец 12. Число ЭП (в 1-й строке), значения Кс (в остальных строках)'], [[u'Количество электроприёмников:', '2', '3', '5', '8', '10', '15', '20', '30', '50', '100', '200'], ['100', '1', '0.9', '0.8', '0.75', '0.7', '0.65', '0.65', '0.6', '0.55', '0.55', '0.5'], ['84', '1', '1', '0.75', '0.7', '0.65', '0.6', '0.6', '0.6', '0.55', '0.55', '0.5'], ['74', '1', '1', '0.7', '0.65', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.45'], ['49', '1', '1', '0.65', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45'], ['24', '1', '1', '0.6', '0.6', '0.55', '0.5', '0.5', '0.5', '0.45', '0.45', '0.4']]]
				if i == j[2]: # если совпало имя Кс
					if j[4] == 'Зависит от уд.веса в других нагрузках':
						curOtherPUnitDependent = j[5] # от каких мощностей зависит (при удельном весе). Например [u'Ру (вся)']
						curPsum = 0 # текущая общая мощность от которой зависит Кс
						if PyAll in curOtherPUnitDependent: # если зависит от всей установленной мощности
							curPsum = PySum
						elif PpAll in curOtherPUnitDependent: # если зависит от всей расчётной мощности
							curPsum = PpSum
						else: # если зависит от каких-то других мощностей
							for m, k in enumerate(LoadClassNamesinProject): # k это [u'Рабочее освещение']
								for l in Avtomats_DataForUserFormula: # l это [0.1, 0.1, u'Системы ОВ', 2]
									if l[2] in k: # Если у конкретного автомата классификация нагрузок соответствует списку Р участвующих в расчётах...
										if PyorPpDepOnPName(l[2], Readable_znachP).upper() == 'Py'.upper(): # понимаем какую мощность брать с автомата...
											curPsum = curPsum + l[0]
										else:
											curPsum = curPsum + l[1]
						# Теперь у нас есть мощность по Кс, кол-во эл.приём. по Кс и суммарная мощность других Р от которой Кс зависит
						if j[3].upper() == 'EPcount'.upper(): # если зависит от числа электроприёмников
							KcValues.append(FindKcWithPDependent(PsumforKc[n], ConsumersSumforKc[n], curPsum, j[11]))
						else: # если зависит от мощности электроприёмников
							KcValues.append(FindKcWithPDependent(PsumforKc[n], PsumforKc[n], curPsum, j[11]))
					else: # Если не зависит от уд.веса в других нагрузках
						if j[3].upper() == 'EPcount'.upper(): # если зависит от числа электроприёмников
							KcValues.append(FindKc(ConsumersSumforKc[n], j[11]))
						else: # если зависит от мощности электроприёмников
							KcValues.append(FindKc(PsumforKc[n], j[11]))

	# Округляем KcValues до знаков после запятой
	lst_hlp = []
	for i in KcValues:
		if type(i) != list:
			lst_hlp.append(round(i, 2))
		else:
			lst_hlp.append(i)
	KcValues = [i for i in lst_hlp] # Пересобираем список (уже с округлёнными значениями)

	# Всё вычислили и нашли! Теперь можно сосавлять пояснение к расчёту и считать нагрузку!

	# Строки с пояснением
	Calculation_explanation_text = ' '.join(UserFormulaList[1]) # Просто наша формула 'Рраб.осв. * Кс.о. + Ргор.пищ. * Кс.гор.пищ. + Рр.сантех. * Кс.сан.тех. + Рр (без классиф.)'
	Calculation_explanation_numers = '' # Вид: '0.04*0.96+1.0*0.9+0.1*1.0+0.2'
	# PySum - суммарная установленная мощность
	# Считаем Рр по нашей формуле и заодно составляем цифровое пояснение
	# UserFormulaList[1] - [u'Рраб.осв.', '*', u'Кс.о.', '+', u'Ргор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Рр.сантех.', '*', u'Кс.сан.тех.', '+', u'Рр (без классиф.)']
	# Или такая[u'Рраб.осв.', '*', u'Кс.о.', '+', u'Ргор.пищ.', '*', u'Кс.гор.пищ.', '+', u'Рр.сантех.', '*', u'Кс.сан.тех.', '+', u'Ру.л', '*', u'Кс.л.', '+', u'Рр (без классиф.)']
	# elevRes это ([1.0, 1.0], u'Ру.л*Кс.л.до12эт.+Ру.л*Кс.л.более12эт.', '6.5*1.0+6.5*1.0')
	MathSymbolsList = ['+', '-', '*', '/', '(', ')'] # Вшитые возможные математические символы. Как в настройках Теслы!
	for m, i in enumerate(UserFormulaList[1]):
		if i in PNamesListinProject: # [u'Рраб.осв.', u'Ргор.пищ.', u'Рр.сантех.', u'Ру.л', u'Рр (без классиф.)']
			for n, j in enumerate(PNamesListinProject):
				if i == 'Ру.л': # цифры для лифтов берём из лифтовой функции
					Calculation_explanation_numers = Calculation_explanation_numers + elevRes[2]
					break
				elif i == j and i != 'Ру.л': # Если совпало имя мощности и это не лифты
					Calculation_explanation_numers = Calculation_explanation_numers + str(PpowerListinProject[n])
					break
		elif i in MathSymbolsList: # ['+', '-', '*', '/', '(', ')']
			for n, j in enumerate(MathSymbolsList):
				if i == j:
					Calculation_explanation_numers = Calculation_explanation_numers + str(MathSymbolsList[n])
					break
		elif i in KcNamesListinProject: # [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.', u'Кс.л.']
			for n, j in enumerate(KcNamesListinProject):
				if i == 'Кс.л.': # Кс для лифтов не пишем, т.к. уже взяли его из мощности
					break
				elif i == j and i != 'Кс.л.':
					Calculation_explanation_numers = Calculation_explanation_numers + str(KcValues[n])
					break

	# Calculation_explanation_numers - '0.04*0.96+1.0*0.9+0.1*1.0+6.5*1.0+6.5*1.0*+0.2' чтобы стало '0.04*0.96+1.0*0.9+0.1*1.0+6.5*1.0+6.5*1.0+0.2'
	# Теперь нужно почистить Calculation_explanation_numers, убрать * слева или справа от elevRes[2] - '6.5*1.0+6.5*1.0'
	try:
		elevbeginindex = Calculation_explanation_numers.find(elevRes[2])
		if Calculation_explanation_numers[elevbeginindex - 1] == '*' and elevbeginindex - 1 >= 0: # поиск * слева от elevRes[2]
			Calculation_explanation_numers = Calculation_explanation_numers[:elevbeginindex - 1] + Calculation_explanation_numers[elevbeginindex:]
		elif Calculation_explanation_numers[elevbeginindex + len(elevRes[2])] == '*': # поиск * справа от elevRes[2]
			Calculation_explanation_numers = Calculation_explanation_numers[:elevbeginindex + len(elevRes[2])] + Calculation_explanation_numers[elevbeginindex + len(elevRes[2])+1:]
	except IndexError:
		pass

	# Прочистим Calculation_explanation_numers от всякой ерунды
	Calculation_explanation_numers = Clear_caclformula(Calculation_explanation_numers)

	Calculation_explanation = Calculation_explanation_text + ' = ' + Calculation_explanation_numers # Вид: 'Рраб.осв. * Кс.о. + Ргор.пищ. * Кс.гор.пищ. + Рр.сантех. * Кс.сан.тех. + Рр (без классиф.) = 0.04*0.96+1.0*0.9+0.1*1.0+0.2'
	# 'Рраб.осв. * Кс.о. + Ргор.пищ. * Кс.гор.пищ. + Рр.сантех. * Кс.сан.тех. + Ру.л * Кс.л. + Рр (без классиф.) = 0.04*0.96+1.0*0.9+0.1*1.0+6.5*1.0+6.5*1.0*+0.2'

	Pp_coefficient = 0 # Расчётная мощность которая у нас получилась. Например 8.8384
	try:
		Pp_coefficient = eval(Calculation_explanation_numers)
	except:
		TaskDialog.Show('Ошибка', 'Ошибка в расчётной формуле. Зайдите в Настройки и проверьте вашу формулу. Так же проверье выборку на основании которой проводился расчёт.')

	Kc_cond_coefficient = Pp_coefficient / PySum # Средний итоговый Кс. Например 0.92


	#_____________средневзвешенный косинус________________________________________________________________________________
	# А ещё тут сделаем список в соответствии с Avtomats_DataForUserFormula в котором для каждого автомата будет написано какую мощность брать Ру или Рр (это для косинуса итогового надо)
	PyOrPpForEachAv = [] # Вид: ['Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Py', 'Py']
	for i in Avtomats_DataForUserFormula:
		for m, j in enumerate(LoadClassNamesinProject):
			if i[2] in j:
				PyOrPpForEachAv.append(PyOrPpListinProject[m])


	#LoadClassNamesinProject = [] # Вид: [[u'Рабочее освещение'], [u'Тепловое оборудование пищеблоков'], ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], [u'Лифты'], [u'Нет классификации', '', '', '', '']]
	#PyOrPpListinProject = [] # Вид: ['Pp', 'Pp', 'Pp', 'Py', 'Pp']

	#Рассчитываем средневзвешенный косинус (здесь он не такой как во всей остальной программе, т.к. может зависеть от Ру или Рр)
	# Для правильного расчёта средневзвешенного косинуса нам нужно:
	# Каждую исходную мощность каждого автомата умножить на её Кс
	PListinEachAvwithKc = [] # [1.91, 5.25, 4.38, 14.4, 11.3, 3.0, 12.0, 8.8, 16.5, 10.8, 10.8]
	CosfListinEachAv = [] # список косинусов каждого автомата. [0.94999999999999996, 0.94999999999999996, 0.94999999999999996, 0.81000000000000005, 0.85999999999999999, 0.84999999999999998, 0.97999999999999998, 0.84999999999999998, 0.97999999999999998, 0.65000000000000002, 0.65000000000000002]
	# Нужен список классификаций нагрузок которые обслуживает конкретный Кс. Он в соответствии с KcNamesListinProject [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.', u'Кс.л.']
	KcLoadClassDependsOn = [] # [[u'Рабочее освещение'], [u'Тепловое оборудование пищеблоков'], ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ', u'Системы ОВ'], [u'Лифты']]
	for i in KcDependsOnP_ListinProject: # Вид: [[u'Рраб.осв.'], [u'Ргор.пищ.'], [u'Рр.сантех.', u'Рр.ов'], [u'Ру.л']]
		curlst = []
		for j in i: # i - это [u'Рраб.осв.'] j - это 'Рраб.осв.'
			for k in Readable_znachP: # [[u'Ру (вся)', ['all'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (вся)', ['all'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ру (без классиф.)', [u'Нет классификации', ''], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (без классиф.)', [u'Нет классификации', '', '', ''], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ру (др. классиф.)', ['other'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр (др. классиф.)', ['other'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ру.л', [u'Лифты'], 'py', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.сантех.', ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рраб.осв.', [u'Рабочее освещение'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Ргор.пищ.', [u'Тепловое оборудование пищеблоков'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3'], [u'Рр.ов', [u'Системы ОВ'], 'pp', u'Резерв 1', u'Резерв 2', u'Резерв 3']]
				if j == k[0]: # совпали имена мощностей
					for l in k[1]: # k[1] - это [u'Рабочее освещение']
						curlst.append(l) 
		KcLoadClassDependsOn.append(curlst)

	# Раскатаем KcLoadClassDependsOn в линейный список
	KcLoadClassDependsOn_Line = [] # Вид: [u'Рабочее освещение', u'Тепловое оборудование пищеблоков', 'hvac', u'ОВК', u'Системы ВК', u'Системы ОВ', u'Системы ОВ', u'Лифты']
	for i in KcLoadClassDependsOn:
		for j in i:
			KcLoadClassDependsOn_Line.append(j)

	curKcindec_1 = 'not found' # вспомогательная костыльная переменная если одну мощность обслуживают не один, а два Кс.
	for n, i in enumerate(Avtomats_DataForUserFormula): # [[3.5, 2.8, u'Рабочее освещение', 13, 0.95], [9.6, 7.7, u'Рабочее освещение', 13, 0.95], [7.94, 6.3, u'Рабочее освещение', 13, 0.94999999999999996], [18.0, 14.4, '', 0, 0.81000000000000005], [14.1, 11.300000000000001, '', 0, 0.85999999999999999], [4.5, 3.0, '', 0, 0.84999999999999998], [12.0, 12.0, '', 0, 0.97999999999999998], [22.0, 17.600000000000001, u'Системы ОВ', 11, 0.84999999999999998], [41.200000000000003, 33.0, u'Системы ОВ', 4, 0.97999999999999998], [12.0, 9.5999999999999996, u'Лифты', 11, 0.65000000000000002], [12.0, 9.5999999999999996, u'Лифты', 4, 0.65000000000000002]]
		if i[2] in KcLoadClassDependsOn_Line: # если данную мощность обслуживает конкретный Кс. Например 'Рабочее освещение'.
			curLoadClass = i[2] # Например 'Рабочее освещение'. # i - это [41.200000000000003, 33.0, u'Системы ОВ', 4, 0.97999999999999998]
			for m, j in enumerate(KcLoadClassDependsOn): 
				if curLoadClass in j:
					curKcindec = m
					break
			# Но бывает, что в формуле есть ещё Кс, которые обслуживают ту же мощность.
			# Выясним, есть ли ещё curLoadClass в списке KcLoadClassDependsOn, кроме того что уже найдено в предыдущем шаге.
			# Но тут пока костыль. Считаем, что в одной формуле не может быть более 2-х Кс, обслуживающих одну и ту же мощность.
			#hlp_lst3 = DelElFromList([p for p in KcLoadClassDependsOn_Line], curLoadClass)
			try:
				for l, ara344 in enumerate(KcLoadClassDependsOn):
					if curLoadClass in ara344 and l != m: # l != m чтобы два раза случайно не учесть один и тот же Кс
						curKcindec_1 = l
						break
					else:
						curKcindec_1 = 'not found'
			except:
				curKcindec_1 = 'not found'
			if PyOrPpForEachAv[n].upper() == 'Py'.upper(): # j - Это ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ', u'Системы ОВ']
				if type(KcValues[curKcindec]) == list and curKcindec_1 == 'not found': # из-за лифтов, т.к. значение Кс списком идёт
					PListinEachAvwithKc.append(i[0]*min(KcValues[curKcindec])) # Костыль! Неохота точно считать, поэтому лифты для общего косинуса возьмём просто минимальный Кс
					#break
				elif type(KcValues[curKcindec]) == list and curKcindec_1 != 'not found':
					PListinEachAvwithKc.append(i[0]*min(KcValues[curKcindec])*KcValues[curKcindec_1])
				elif curKcindec_1 != 'not found' and type(KcValues[curKcindec_1]) == list:
					PListinEachAvwithKc.append(i[0]*min(KcValues[curKcindec_1])*KcValues[curKcindec])
				else:
					if curKcindec_1 != 'not found':
						PListinEachAvwithKc.append(i[0]*KcValues[curKcindec]*KcValues[curKcindec_1])
					else:
						PListinEachAvwithKc.append(i[0]*KcValues[curKcindec])
					#break
			else: # Если надо брать расчётную мощность
				if type(KcValues[curKcindec]) == list and curKcindec_1 == 'not found': # из-за лифтов, т.к. значение Кс списком идёт
					PListinEachAvwithKc.append(i[1]*min(KcValues[curKcindec])) # Костыль! Неохота точно считать, поэтому лифты для общего косинуса возьмём просто минимальный Кс
					#break
				elif type(KcValues[curKcindec]) == list and curKcindec_1 != 'not found':
					PListinEachAvwithKc.append(i[1]*min(KcValues[curKcindec])*KcValues[curKcindec_1])
				elif curKcindec_1 != 'not found' and type(KcValues[curKcindec_1]) == list:
					PListinEachAvwithKc.append(i[1]*min(KcValues[curKcindec_1])*KcValues[curKcindec])
				else:
					if curKcindec_1 != 'not found':
						PListinEachAvwithKc.append(i[1]*KcValues[curKcindec]*KcValues[curKcindec_1])
					else:
						PListinEachAvwithKc.append(i[1]*KcValues[curKcindec])
					#break
		else: # Если на данный автомат нет коэффициента спроса
			if PyOrPpForEachAv[n].upper() == 'Py'.upper():
				PListinEachAvwithKc.append(i[0])
			else:
				PListinEachAvwithKc.append(i[1])
	# PyOrPpForEachAv  ['Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Pp', 'Py', 'Py']
	# KcValues [0.68, 0.9, 0.5, [0.9]]
	# KcLoadClassDependsOn [[u'Рабочее освещение'], [u'Тепловое оборудование пищеблоков'], ['hvac', u'ОВК', u'Системы ВК', u'Системы ОВ', u'Системы ОВ'], [u'Лифты']]
	# KcNamesListinProject [u'Кс.о.', u'Кс.гор.пищ.', u'Кс.сан.тех.', u'Кс.л.']
	# [[3.5, 2.8, u'Рабочее освещение', 13, 0.95], [9.6, 7.7, u'Рабочее освещение', 13, 0.95], [7.94, 6.3, u'Рабочее освещение', 13, 0.95], [18.0, 14.4, '', 0, 0.81], [14.1, 11.3, '', 0, 0.86], [4.5, 3.0, '', 0, 0.85], [12.0, 12.0, '', 0, 0.98], [22.0, 17.6, u'Системы ОВ', 11, 0.85], [41.2, 33.0, u'Системы ОВ', 4, 0.98], [12.0, 9.6, u'Лифты', 11, 0.65], [12.0, 9.6, u'Лифты', 4, 0.65]]
	# PListinEachAvwithKc [1.91, 5.25, 4.38, 14.4, 11.3, 3.0, 12.0, 8.8, 16.5, 10.8, 10.8]
	for i in Avtomats_DataForUserFormula:
		CosfListinEachAv.append(i[4])


	#Сначала сделаем вспомогательную переменную содержащую число равное сумме каждой Рр умноженной на каждый косинус
	Pp_multiplication_cosf_sum = 0
	for i in list(map(lambda x,y: x*y, PListinEachAvwithKc, CosfListinEachAv)):
		Pp_multiplication_cosf_sum = Pp_multiplication_cosf_sum + i
	cosf_average = (round ((Pp_multiplication_cosf_sum / Pp_coefficient), 2)) # Например 0.94

	if cosf_average > 1 or round(PySum, Round_value_ts) < round(Pp_coefficient, Round_value_ts):
		raise Exception('Ошибка в расчётной формуле! Расчёт отменён, проверьте правильность составления формулы. Скорее всего для какой-то из мощностей, участвующих в формуле задана неправильная классификация нагрузок. Или для какого-то из коэффициентов спроса неправильно указаны мощности которые он обслуживает.')

	# Write_to_table бывает True/False
	# True - всё считается и пишется как раньше
	# False - в этом случае функция расчёта ж/д используется для последующего объединения с пользовательской формулой.
	# и тогда получается, что тут не нужно считать лифты и ОДН, а также нужно пересчитать Ру суммарное и косинус жилого дома.

	if Write_to_table == True: # если считаем просто по пользовательскому режиму (без жилого дома)
	# Пишем результаты в табличку
		calculation_table.LookupParameter(Param_Explanation).Set(Calculation_explanation)
		calculation_table.LookupParameter(Param_Py).Set(round(PySum, Round_value_ts)) # Пишем Py
		calculation_table.LookupParameter(Param_Kc).Set(round(Kc_cond_coefficient, 2)) # Пишем Kc
		calculation_table.LookupParameter(Param_Pp).Set(round(Pp_coefficient, Round_value_ts)) # Пишем Pp
		calculation_table.LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
		calculation_table.LookupParameter(Param_Ip).Set(round(Pp_coefficient / cosf_average / U3fsqrt3forI, Round_value_ts)) # Пишем Ip
		calculation_table.LookupParameter(Param_Sp).Set(round(Pp_coefficient / cosf_average, Round_value_ts)) # Пишем Sp
		calculation_table.LookupParameter(Param_IdQFsCalc).Set(Str_Ids_elems_avtomats) # Пишем Idшники автоматов на которых был произведён расчёт

	#попробуем вывести на выход список с результатми расчётов, чтобы объединять его с расчётом жилого дома
	UserFormulaResulList = [Calculation_explanation_text, Calculation_explanation_numers, PySum, Pp_coefficient, cosf_average]

	return UserFormulaResulList

# eval('6.5*1.0*+0.2')



# Объединение жилого дома и пользовательской формулы на основе функций Residental_Write_to_calculation_table и UserFormula_Write_to_calculation_table
# Обращение:
# Residental_and_User_Write_to_calculation_table (Residental_Write_to_calculation_table(elems_calculation_table[0], elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, False), UserFormula_Write_to_calculation_table(UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, elems_calculation_table[0], Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, False), elems_calculation_table[0])
def Residental_and_User_Write_to_calculation_table (ResidentalResulList, UserFormulaResulList, calculation_table):

	'''
	Чтоб тестить
	# жилой дом уже точно без лифтов и ОДН
	ResidentalResulList = Residental_Write_to_calculation_table (elems_calculation_table[0], elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, False)
	# [u'Рр.ж.д = Кп.к*((Pкв.*nкв.+Pкв.*nкв.+Pкв.*nкв.+Pкв.*nкв.)*Ko+Pкв.уд*nкв.)', '1.0*((12.0*38+14.0*41+17.0*36+19.0*5)*0.156+2.075*32)', 474.40000000000009, 337.37199999999996, 0.94999999999999996]
	UserFormulaResulList = UserFormula_Write_to_calculation_table (UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, elems_calculation_table[0], Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12)
	# [u'Ру.раб.осв. * Кс.раб.осв. + Ру.ав.осв. + Ру.л * Кс.л. + ( Ру.мех.об. + Ру.ов + Ру.вк + Ру.холод. ) * Кс.сан.тех. + Ру.посудом. * Кс.посудом. + Ру.полот.суш. * Кс.полот.суш. + ( Ру.роз.быт. + Ру.роз.техн. ) * Кс.роз.быт.техн.питающ. + Ру.роз.комп. * Кс.роз.комп. + Ру.терм. * Кс.терм. + Ру.щгп + Рр (без классиф.)', '21.0*0.87+0+13.4*0.9+(0+63.2+16.5+0)*0.5+0*1.0+0*0.4+(14.1+0)*0.2+18.0*0.4+92.6*0.52+0+0', 238.79999999999995, 128.352, 0.92000000000000004]
	'''

	# пробуем объединить по виду: Pр.ж.д = kп.к·Pкв + юзерформула
	# Формируем пояснения и цифры жилого дома

	# Общее текстовое пояснение жилья и юзер формулы. (# выкидываем 'Рр.ж.д = ' в начале строки для пояснения жилого дома)
	Residental_and_User_calculation_explanation_text = 'Pp =' + ResidentalResulList[0][8:] + ' + ' + UserFormulaResulList[0]
	 # Вид: u'Pp = Кп.к*((Pкв.*nкв.+Pкв.*nкв.+Pкв.*nкв.+Pкв.*nкв.)*Ko+Pкв.уд*nкв.) + Ру.раб.осв. * Кс.раб.осв. + Ру.ав.осв. + Ру.л * Кс.л. + ( Ру.мех.об. + Ру.ов + Ру.вк + Ру.холод. ) * Кс.сан.тех. + Ру.посудом. * Кс.посудом. + Ру.полот.суш. * Кс.полот.суш. + ( Ру.роз.быт. + Ру.роз.техн. ) * Кс.роз.быт.техн.питающ. + Ру.роз.комп. * Кс.роз.комп. + Ру.терм. * Кс.терм. + Ру.щгп + Рр (без классиф.)'
	# Общее числовое пояснение жилья и юзер формулы
	Residental_and_User_calculation_explanation_numers = ResidentalResulList[1] + ' + ' + UserFormulaResulList[1]
	# Вид: '1.0*((12.0*38+14.0*41+17.0*36+19.0*5)*0.156+2.075*32) + 21.0*0.87+0+13.4*0.9+(0+63.2+16.5+0)*0.5+0*1.0+0*0.4+(14.1+0)*0.2+18.0*0.4+92.6*0.52+0+0'
	#		                     270.972 +    66.4 = ж/д  337.372   18,27   	12,06		39.85                         2,82        7,2      48,152     ====   465,724
	Residental_and_User_PySum = float(ResidentalResulList[2]) + float(UserFormulaResulList[2]) 
	Residental_and_User_Pp = eval(Residental_and_User_calculation_explanation_numers)
	Residental_and_User_Kc_cond_coefficient = Residental_and_User_Pp / Residental_and_User_PySum
	Residental_and_User_Calculation_explanation = Residental_and_User_calculation_explanation_text + ' = ' + Residental_and_User_calculation_explanation_numers
	Residental_and_User_cosf_average = (eval(ResidentalResulList[1]) * ResidentalResulList[4] + eval(UserFormulaResulList[1]) * UserFormulaResulList[4]) / Residental_and_User_Pp
	Residental_and_User_cosf_average = round(Residental_and_User_cosf_average, 2)

	# Пишем результаты в табличку
	calculation_table.LookupParameter(Param_Explanation).Set(Residental_and_User_Calculation_explanation)
	calculation_table.LookupParameter(Param_Py).Set(round(Residental_and_User_PySum, Round_value_ts)) # Пишем Py
	calculation_table.LookupParameter(Param_Kc).Set(round(Residental_and_User_Kc_cond_coefficient, 2)) # Пишем Kc
	calculation_table.LookupParameter(Param_Pp).Set(round(Residental_and_User_Pp, Round_value_ts)) # Пишем Pp
	calculation_table.LookupParameter(Param_Cosf).Set(Residental_and_User_cosf_average) # Пишем Cosf
	calculation_table.LookupParameter(Param_Ip).Set(round(Residental_and_User_Pp / Residental_and_User_cosf_average / U3fsqrt3forI, Round_value_ts)) # Пишем Ip
	calculation_table.LookupParameter(Param_Sp).Set(round(Residental_and_User_Pp / Residental_and_User_cosf_average, Round_value_ts)) # Пишем Sp
	calculation_table.LookupParameter(Param_IdQFsCalc).Set(Str_Ids_elems_avtomats) # Пишем Idшники автоматов на которых был произведён расчёт



'''
Руками проверяю:
Ру.раб.осв. число ЭП 39, Ру = 21 кВт, Кс.о. должен быть = 0.544
Ру.гор.пищ. число ЭП 14, Ру = 92.6 кВт, Кс.гор.пищ. должен быть = 0.52 
Ру.сантех. число ЭП 15, Ру = 63.2 кВт, Ру вся = 75.2, уд.вес 84%, Кс.сан.тех. должен быть = 0.6

Ру.раб.осв. * Кс.о. + Ру.гор.пищ. * Кс.гор.пищ. + Ру.сантех. * Кс.сан.тех. + Ру.л * Кс.л. + Рр (без классиф.) = 
= 21.0*0.544+92.6*0.52+63.2*0.5+12.0*1.0+12.0*1.0+40.7


	# Сначала выкинем лифты из общего списка автоматов, т.к. с лифтами отдельная песня.
	hlp_lst = []
	for i in elems_avtomats:
		if i not in elems_avtomats_elevators:
			hlp_lst.append(i)
	# Переобъявляем список автоматов (без лифтов)
	elems_avtomats = []
	elems_avtomats = [i for i in hlp_lst]

'''



















#_______________________________________________________________________________________________________________________________________________
# Пишем данные в таблички результатов

t = Transaction(doc, 'Write to calculation_table')
t.Start()
if Button_Cancel_pushed != 1: # Если кнопка "Cancel" не была нажата
	if elems_calculation_table != []: # если табличка для записи результатов была изначально выбрана
		if CalcWay == 0: # если способ расчёта "простой"
			Simple_Write_to_calculation_table (elems_calculation_table[0], Upit_window, U1fforI, U1f, U3f, Param_Upit, Param_Py, Param_Kc, Param_Pp, Param_Cosf, Param_Ip, Param_Sp, Py_sum, Round_value_ts, Kc_window, cosf_average)
		elif CalcWay == 1: # если способ расчёта "жилой дом"
			Residental_Write_to_calculation_table (elems_calculation_table[0], elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, True)
		elif CalcWay == 2: # если способ расчёта "жилой дом при пожаре"
			Coefficient_Write_to_calculation_table (elems_calculation_table[0], elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient)
		elif CalcWay == 3: # если способ расчёта "Пользовтаельский"
			UserFormula_Write_to_calculation_table (UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, elems_calculation_table[0], Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, True)
		elif CalcWay == 4: # если способ расчёта "Жилой дом + Пользовтаельский"
			Residental_and_User_Write_to_calculation_table (Residental_Write_to_calculation_table(elems_calculation_table[0], elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, False), UserFormula_Write_to_calculation_table(UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, elems_calculation_table[0], Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, False), elems_calculation_table[0])
	elif elems_calculation_table == []: # если табличка для записи результатов не была изначально выбрана
		try:
			pickedResTable = doc.GetElement(uidoc.Selection.PickObjects(ObjectType.Element, "Выберите табличку для записи результата")[0])
			if pickedResTable.Name in calculated_tables_family_names:
				if CalcWay == 0: # если способ расчёта "простой"
					Simple_Write_to_calculation_table (pickedResTable, Upit_window, U1fforI, U1f, U3f, Param_Upit, Param_Py, Param_Kc, Param_Pp, Param_Cosf, Param_Ip, Param_Sp, Py_sum, Round_value_ts, Kc_window, cosf_average)
				elif CalcWay == 1: # если способ расчёта "жилой дом"
					Residental_Write_to_calculation_table (pickedResTable, elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, True)
				elif CalcWay == 2: # если способ расчёта "жилой дом при пожаре"
					Coefficient_Write_to_calculation_table (pickedResTable, elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient)
				elif CalcWay == 3: # если способ расчёта "Пользовтаельский"
					UserFormula_Write_to_calculation_table (UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, pickedResTable, Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, True)
				elif CalcWay == 4: # если способ расчёта "Жилой дом + Пользовтаельский"
					Residental_and_User_Write_to_calculation_table (Residental_Write_to_calculation_table(pickedResTable, elems_avtomats, elems_avtomats_elevators, is_flat_riser, Flat_count, Flat_Pp_wattage, Flat_count_SP, Flat_unit_wattage_SP, Flat_count_high_comfort, Ko_high_comfort, Round_value_ts, Kcpwrres, Elevator_count_SP, Ks_elevators_below12, Ks_elevators_above12, elevators_groupsnames_below12, elevators_groupsnames_above12, Param_Circuit_number, Param_Py, Param_Pp, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, Param_Load_Class, Param_Explanation, cosf_average, Py_sum, U3fsqrt3forI, flat_calculation_way_ts, Kkr_flats_koefficient, False), UserFormula_Write_to_calculation_table(UserFormulaSelected, elems_avtomats, Param_Consumers_count, Param_Py, Param_Pp, Param_Load_Class, Readable_znachUserFormula, Readable_znachP, Readable_znachKc, PyAll, PpAll, pickedResTable, Param_Explanation, Round_value_ts, Param_Kc, Param_Cosf, Param_Ip, Param_Sp, U3fsqrt3forI, Elevator_count_SP, elevators_groupsnames_below12, elevators_groupsnames_above12, Ks_elevators_below12, Ks_elevators_above12, False), pickedResTable)
			else: 
				TaskDialog.Show('Расчёт схем', 'Таблица для записи результата не была выбрана, результаты расчёта не были записаны.')
		except:
			TaskDialog.Show('Расчёт схем', 'Таблица для записи результата не была выбрана, результаты расчёта не были записаны.')
t.Commit()




















'''
if Button_Cancel_pushed != 1: # Если кнопка "Cancel" не была нажата
	if elems_calculation_table != []: # если табличка для записи результатов была изначально выбрана
		t = Transaction(doc, 'Write to calculation_table')
		t.Start()
		if Upit_window == U1fforI:
			elems_calculation_table[0].LookupParameter(Param_Upit).Set(int(U1f)) # Пишем Напряжение
		else:
			elems_calculation_table[0].LookupParameter(Param_Upit).Set(int(U3f))
		elems_calculation_table[0].LookupParameter(Param_Py).Set(round(Py_sum, Round_value_ts)) # Пишем Py
		elems_calculation_table[0].LookupParameter(Param_Kc).Set(Kc_window) # Пишем Kc
		elems_calculation_table[0].LookupParameter(Param_Pp).Set(round(Py_sum * Kc_window, Round_value_ts)) # Пишем Pp
		elems_calculation_table[0].LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
		elems_calculation_table[0].LookupParameter(Param_Ip).Set(round(Py_sum * Kc_window / cosf_average / Upit_window, Round_value_ts)) # Пишем Ip
		elems_calculation_table[0].LookupParameter(Param_Sp).Set(round(Py_sum * Kc_window / cosf_average, Round_value_ts)) # Пишем Sp
		t.Commit()
	elif elems_calculation_table == []: # если табличка для записи результатов не была изначально выбрана
		pickedResTable = doc.GetElement(uidoc.Selection.PickObjects(ObjectType.Element, "Выберите табличку для записи результата")[0])
		if pickedResTable.Name in calculated_tables_family_names:
			t = Transaction(doc, 'Write to calculation_table')
			t.Start()
			if Upit_window == U1fforI:
				pickedResTable.LookupParameter(Param_Upit).Set(int(U1f)) # Пишем Напряжение
			else:
				pickedResTable.LookupParameter(Param_Upit).Set(int(U3f))
			pickedResTable.LookupParameter(Param_Py).Set(round(Py_sum, Round_value_ts)) # Пишем Py
			pickedResTable.LookupParameter(Param_Kc).Set(Kc_window) # Пишем Kc
			pickedResTable.LookupParameter(Param_Pp).Set(round(Py_sum * Kc_window, Round_value_ts)) # Пишем Pp
			pickedResTable.LookupParameter(Param_Cosf).Set(cosf_average) # Пишем Cosf
			pickedResTable.LookupParameter(Param_Ip).Set(round(Py_sum * Kc_window / cosf_average / Upit_window, Round_value_ts)) # Пишем Ip
			pickedResTable.LookupParameter(Param_Sp).Set(round(Py_sum * Kc_window / cosf_average, Round_value_ts)) # Пишем Sp
			t.Commit()
		else: 
			TaskDialog.Show('Расчёт схем', 'Таблица для записи результата не была выбрана, результаты расчёта не были записаны.')
'''