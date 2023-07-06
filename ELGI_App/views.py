import datetime
import os.path
import random
import time

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.templatetags.static import static
from .models import *
import pyodbc
import ast
import base64
from PIL import Image
from io import BytesIO
from django.conf import settings
from pymodbus.client import ModbusTcpClient
import json
import struct

client = ModbusTcpClient('172.17.235.72')  # 172.17.235.72
conn = client.connect()
print("conn ", conn)


# Create your views here.

def db_connection():
    conn = pyodbc.connect('DRIVER={SQL Server};SERVER=PROD-DF;DATABASE=TT;UID=MEI_DF;PWD=MEI@mac;Trusted_Connection=yes')
    # conn = pyodbc.connect('DRIVER={SQL Server};SERVER=20.212.149.30;DATABASE=TT;UID=sa;PWD=ElgiAzure@123;Trusted_Connection=yes')
    cursor = conn.cursor()
    return cursor



def no_access(request):
    return render(request,"general/no_access.html")


def signin(request):
    msg = ""
    if request.user.is_authenticated:
        return redirect(home)
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.groups.filter(name='Admin').exists():
                print("ADMINNN")
                user_id = User.objects.get(username=username)
                print("username",user_id.id)
                emp_details = Employee_Details.objects.get(Username=user_id.id)
                print("emp_details", emp_details.Employee_Name)
                request.session['emp_name'] = emp_details.Employee_Name
                print("request.session['emp_name']", request.session['emp_name'])
                return redirect(home)
            if user.groups.filter(name='Supervisor').exists():
                user_id = User.objects.get(username=username)
                print("username", user_id.id)
                emp_details = Employee_Details.objects.get(Username=user_id.id)
                print("emp_details", emp_details.Employee_Name)
                request.session['emp_name'] = emp_details.Employee_Name
                print("request.session['emp_name']", request.session['emp_name'])
                return redirect(dms_app)
            if user.groups.filter(name='Operator').exists():
                user_id = User.objects.get(username=username)
                print("username",user_id.id)
                emp_details = Employee_Details.objects.get(Username=user_id.id)
                print("emp_details", emp_details.Employee_Name)
                # request.session = emp_details
                # print("request.session['emp_name']", request.session['emp_name'])
                return redirect(stations_list)
            else:
                print("user admin", user)
                return redirect('/')

        else:
            if username == "":
                msg = "Username Incorrect"
            elif password == "":
                msg = "Password Incorrect"
            elif user is None:
                msg = "Username & Password Incorrect"

            return render(request, 'login.html',{"username":username, "password":password, "msg":msg})
    return render(request, 'login.html',{"msg":msg})


def signout(request):
    print("User Logging Out")
    logout(request)
    return redirect('/')


@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def home(request):
    return render(request, "dashboard.html")



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def station_bypass(request):
    cursor = db_connection()

    if request.method == "POST":
        station_id = request.POST.get('station_id')
        bypass = request.POST.get('bypass')
        print(station_id, bypass)
        cursor.execute(
            """
            UPDATE [dbo].[Station_Bypass]
            SET [Bypass] = ?
            WHERE [Station_ID] = ?
            """, bypass, station_id)
        cursor.commit()

        bypass_reg_details = cursor.execute("SELECT [Bypass_registers] FROM [TT].[dbo].[Station_Bypass] WHERE Station_ID = ?", station_id)
        bypass_reg_data = [obj[0] for obj in bypass_reg_details]
        print("bypass_reg_data ",bypass_reg_data)


        # print(reg)

        try:
            reg = float(bypass_reg_data[0])
            reg_value = client.read_holding_registers(int(reg), 1).registers

            bit16_reg = bin(reg_value[0] & 0xFFFF)[2:].zfill(16)
            # print("1bit_reg", bit16_reg)
            list_16 = list(bit16_reg)
            # print("list 16        ", list_16)
            bit = int(str(reg).split('.')[1])
            # print("bit ", bit)

            if bypass == "Bypass":
                list_16[(16 - bit) - 1] = '1'
                # print("list 16 update ", list_16)
                update_value = int(''.join(list_16), 2)
                # print("update_value", update_value)
                client.write_register(int(reg), update_value)

            elif bypass == "Live":
                list_16[(16 - bit) - 1] = '0'
                # print("list 16 update ", list_16)
                update_value = int(''.join(list_16), 2)
                # print("update_value", update_value)
                client.write_register(int(reg), update_value)

        except:
            pass

    station_bypass_details = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Station_Bypass]""")

    station_bypass_data = [{
        "Station_ID": obj[0], "Screen_text": obj[1], "Bypass": obj[2]
    } for obj in station_bypass_details]

    # print(station_bypass_data)
    return render(request, 'station_bypass.html', {"station_bypass_data": station_bypass_data})

@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def child_part_details(request):
    cursor = db_connection()

    child_part_detail = cursor.execute(
        """SELECT * FROM[TT].[dbo].[LN_CP_Details] WHERE
    Fab_Number IN (
     SELECT TOP(500)[FAB_NO] FROM[TT].[dbo].[LN_Order_Release] ORDER BY[Release_Date] DESC
    )""")

    child_part_detail_data = [
        {"TPL_Number": obj[0], "Part_No": obj[1], "Part_No_Rev": obj[2], "Spec_1_Description": obj[3],
         "Spec_1_Value": obj[4],
         "Spec_2_Description": obj[5], "Spec_2_Value": obj[6], "Spec_3_Description": obj[7], "Spec_3_Value": obj[8],
         "Spec_4_Description": obj[9], "Spec_4_Value": obj[10], "Spec_5_Description": obj[11], "Spec_5_Value": obj[12],
         "Spec_6_Description": obj[13], "Spec_6_Value": obj[14]
            , "Spec_7_Description": obj[15], "Spec_7_Value": obj[16], "Spec_8_Description": obj[17],
         "Spec_8_Value": obj[18], "Spec_9_Description": obj[19], "Spec_9_Value": obj[20],
         "Spec_10_Description": obj[21], "Spec_10_Value": obj[22], "Spec_11_Description": obj[23],
         "Spec_11_Value": obj[24], "Spec_12_Description": obj[25], "Spec_12_Value": obj[26]
            , "Child_Part_Code": obj[27], "Fab_Number": obj[28]
         } for obj in child_part_detail]

    return render(request, 'child_part_details.html', {"child_part_detail_data": child_part_detail_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def order_release(request):
    cursor = db_connection()
    # order_release_details = cursor.execute(
    #     """SELECT * FROM [TT].[dbo].[LN_Order_Release]""")

    order_release_details = cursor.execute(
        """ SELECT TOP(500) [TPL_No],  [FAB_NO], [pd_no]
    , [Release_Date], [Status], [Model_Code]
    , [Description], [TPL_Description], [Completed_Date]
    FROM [TT].[dbo].[LN_Order_Release] ORDER BY[Release_Date] DESC """)

    order_release_data = [
        {"Release_Date": obj[3], "TPL_No": obj[0], "FAB_NO": obj[1], "pd_no": obj[2],
         "Status": obj[4], "Model_Code": obj[5], "Description": obj[6], "TPL_Description": obj[7],
         "Completed_Date": obj[8]
         } for obj in order_release_details]

    return render(request, 'order_release.html', {"order_release_data": order_release_data})


@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def order_release_error_table(request):
    cursor = db_connection()
    # order_release_error_details = cursor.execute(
    #     """SELECT * FROM [TT].[dbo].[LN_Order_Release_Error]""")

    order_release_error_details = cursor.execute(
        """ SELECT TOP(500)[TPL_No]
    , [FAB_NO], [Model_Code], [Po_No]
    , [Release_Date], [Description], [TPL_Description]
    FROM[TT].[dbo].[LN_Order_Release_Error] ORDER BY[Release_Date] DESC""")

    order_release_error_data = [
        {"TPL_No": obj[0], "FAB_NO": obj[1], "Model_Code": obj[2], "Po_No": obj[3],
         "Release_Date": obj[4], "Description": obj[5], "TPL_Description": obj[6]
         } for obj in order_release_error_details]

    return render(request, 'order_release_error_table.html', {"order_release_error_data": order_release_error_data})


#################

@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def company(request):
    cursor = db_connection()
    # st_operation_tab

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "update":
            cursor.execute(
                """ UPDATE [TT].[dbo].[Operator]
               SET "Skill_Required" = ?
                  ,"Reponsible_For" = ?
                  ,"Screen_text" = ?
             WHERE Sub_Station_Code = ? and Operator_Code = ? """, request.POST["skill_required"],
                request.POST["responsible_for"],
                request.POST["screen_text"], request.POST["sub_station_code"], request.POST["st_operator_code"])
            cursor.commit()

    st_operation_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Operator] order by Station_Order ASC""")
    st_operation_tab = [
        {"Sub_Station_Code": obj[0], "Operator_Code": obj[1], "Skill_Required": obj[2], "Reponsible_For": obj[3],
         "Screen_text": obj[4]} for obj in st_operation_tab]

    # state_tab
    state_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[State]""")
    state_tab = [
        {"Country_Code": obj[0], "State_Code": obj[1], "State_Name": obj[2]} for obj in
        state_tab]

    # city_tab
    city_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[City]""")
    city_tab = [
        {"State_Code": obj[0], "City_Code": obj[1], "City_Name": obj[2]} for obj in
        city_tab]

    # address_tab
    address_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Address]""")
    address_tab = [
        {"City_Code": obj[0], "Address_Code": obj[1], "Address": obj[2]} for obj in
        address_tab]

    # company tab
    company_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Company]""")
    company_tab = [
        {"Address_Code": obj[0], "Company_Code": obj[1], "Company_Name": obj[2], "Latitude": obj[3],
         "Longitude": obj[4]} for obj in
        company_tab]

    # plant_tab
    plant_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Plant]""")
    plant_tab = [
        {"Company_Code": obj[0], "Plant_Code": obj[1], "Plant_Name": obj[2]} for obj in
        plant_tab]

    # line tab
    line_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Line]""")
    line_tab = [
        {"Plant_Code": obj[0], "Line_Code": obj[1], "Line_Name": obj[2]} for obj in
        line_tab]

    # station tab
    station_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Station]""")
    station_tab = [
        {"Line_Code": obj[0], "Station_Code": obj[1], "Station_name": obj[2], "Station_Purpose": obj[3]} for obj in
        station_tab]

    # substation tab
    substation_tab = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Sub_Station]""")
    substation_tab = [
        {"Station_Code": obj[0], "Sub_Station_Code": obj[1], "Station_Name": obj[2], "Station_Purpose": obj[3],
         "By_pass": obj[4]} for obj in substation_tab]

    # country tab
    country_tab = cursor.execute(
        """SELECT [Country_Code], [Country_Name] FROM[TT].[dbo].[Country]""")
    country_data = [{"Country_Code": obj[0], "Country_Name": obj[1]} for obj in country_tab]

    return render(request, 'company.html',
                  {'st_operation_tab': st_operation_tab, 'state_tab': state_tab, 'city_tab': city_tab,
                   'address_tab': address_tab, 'company_tab': company_tab, 'plant_tab': plant_tab, 'line_tab': line_tab,
                   'station_tab': station_tab, 'substation_tab': substation_tab, 'country_data': country_data})




@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def tpl_master(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "Add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[TPL_Master] (
                        "TPL_No"
                      ,"Model_Group"
                      ,"TPL_Description"
                      ,"Machines_on_AGV"
                      ,"PDI_Insp")
                      VALUES (?,?,?,?,?)""", request.POST["TPL_Code"],
                request.POST["Group"], request.POST["TPL_Description"], request.POST["AGV"], request.POST["PDI_Insp"])
            cursor.commit()

            error_release_details = cursor.execute(
                """ select * from  [TT].[dbo].[LN_Order_Release_Error] where TPL_No = ? """,request.POST["TPL_Code"]
            )
            error_release_data = [{"TPL_No":obj[0],"Fab_No":obj[1],"PO_No":obj[3],"TPL_Desc":obj[5],"Status":"R",
                                        "Releasedata":obj[4],"desc":obj[5]} for obj in error_release_details]

            for data in error_release_data:
                cursor.execute(""" INSERT INTO [TT].[dbo].[LN_Order_Release] (
                        "TPL_No"
                      ,"FAB_NO"
                      ,"pd_no"
                      ,"Release_Date"
                      ,"Status"
                      ,"Description"
                      ,"TPL_Description"
                      )
                      VALUES (?,?,?,?,?,?,?)""", data["TPL_No"],data["Fab_No"],data["PO_No"],data["Releasedata"],
                               data["Status"],data["desc"],data["TPL_Desc"]
                )
                cursor.commit()




            # cursor.execute(
            #     """ INSERT INTO [TT].[dbo].[Process_Master_Mapping] (
            #      "Model_Group"
            #      ,"TPL_No"
            #    ,"Operator_Code"
            #    ,"Process_Code"
            #    ,"Process_Seq_No"
            #    ,"Line_Code")VALUES (?,?,?,?,?,?)""", request.POST["group"], request.POST["tpl_code"],
            #     request.POST["operator_code"],
            #     request.POST["process_code"], request.POST["sequence_no"], "EL1_P1_L1")
            # cursor.commit()



        elif request.POST["submit"] == "Modify":
            cursor.execute(
                """ UPDATE [TT].[dbo].[TPL_Master]
               SET "TPL_No" = ?
                  ,"Model_Group" = ?
                  ,"TPL_Description" = ?
                  ,"Machines_on_AGV" = ?
                  ,"PDI_Insp" = ?
             WHERE TPL_No = ?""", request.POST["TPL_Code"],
                request.POST["Group"], request.POST["TPL_Description"], request.POST["AGV"], request.POST["PDI_Insp"], request.POST["TPL_Code"])
            cursor.commit()

    tpl_code_details = cursor.execute(
        """SELECT DISTINCT  [TPL_No] FROM [TT].[dbo].[LN_Order_Release_Error]""")
    tpl_code_data = [obj[0] for obj in tpl_code_details]
    # print("model_code_data",model_code_data)

    tpl_desc_details = cursor.execute(
        """SELECT [TPL_No], [TPL_Description] FROM [TT].[dbo].[LN_Order_Release_Error]""")
    tpl_desc_data = [{"TPL_Code": obj[0], "TPL_Description": obj[1]} for obj in tpl_desc_details]
    # print("model_code_data",model_code_data)





    tpl_master_details = cursor.execute(
        "SELECT * FROM[TT].[dbo].[TPL_Master]")

    tpl_master_data = [{
        "TPL_Code": obj[0], "Model_Group": obj[1],
        "TPL_Description": obj[2], "Machines_on_AGV": obj[3],"PDI_Insp":obj[4]
    } for obj in tpl_master_details]

    # print("tpl_data",tpl_master_data)
    lis = []
    lis1 = []

    for i in tpl_desc_data:
        for k,v in i.items():
            if k == "TPL_Code":
                lis.append(v)
            if k == "TPL_Description":
                lis1.append(v)

    dd_data = dict(zip(lis,lis1))
    # print("dd_data",dd_data,type(dd_data))

    return render(request, 'tpl_master.html', {"tpl_master_data": tpl_master_data, 'tpl_code_data':tpl_code_data, 'tpl_desc_data':tpl_desc_data, "dd_data" :dd_data})


# Process master
@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def process_master(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))
        try:
            if request.POST["Bolt_Count"] == "":
                Bolt_Count = 0
            else:
                Bolt_Count = request.POST["Bolt_Count"]

            if request.POST["Cycle_Time"] == "":
                Cycle_Time = 0
            else:
                Cycle_Time = request.POST["Cycle_Time"]

            if request.POST["Tool_ID"] == "":
                Tool_ID = "NULL"
            else:
                Tool_ID = request.POST["Tool_ID"]

        except:
            pass

        if request.POST["submit"] == "Add":
            # print(" bc ", Bolt_Count)
            # print(" ct ", request.POST["Cycle_Time"])
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Process_Master] (
             "Line_Code"
           ,"Pro_Type_Code"
           ,"Process_Desc"
           ,"Tool_ID"
           ,"Process_Code"
           ,"Bolt_Count"
           ,"Process_Photo_Path"
           ,"Takt_Time"
           ,"Torque")VALUES (?,?,?,?,?,?,?,?,?)""", "EL1_P1_L1", request.POST["Process_Type"],
                request.POST["Process_Description"],
                Tool_ID, request.POST["Process_Code"], int(Bolt_Count), request.POST["Guide_Pic_Path"], int(Cycle_Time),
                request.POST["Torque"])
            cursor.commit()

        elif request.POST["submit"] == "Modify":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Process_Master]
               SET "Line_Code" = ?
                  ,"Pro_Type_Code" = ?
                  ,"Process_Desc" = ?
                  ,"Tool_ID" = ?
                  ,"Process_Code" = ?
                  ,"Bolt_Count" = ?
                  ,"Process_Photo_Path" = ?
                  ,"Takt_Time" = ?
                  ,"Torque" = ?
             WHERE Process_Code = ?""", "EL1_P1_L1", request.POST["Process_Type"], request.POST["Process_Description"],
                Tool_ID, request.POST["Process_Code"], int(Bolt_Count), request.POST["Guide_Pic_Path"], int(Cycle_Time),
                request.POST["Torque"], request.POST["Process_Code"])
            cursor.commit()

        elif request.POST["submit"] == "Delete":
            cursor.execute(
                """
                DELETE FROM [TT].[dbo].[Process_Master]
                WHERE Process_Code = ?""", request.POST["Process_Code"])
            cursor.commit()
        try:
            if request.POST["radio_selection"] == "process_code":
                if request.POST["submit"] == "PM_Add":
                    cursor.execute(
                        """ INSERT INTO [TT].[dbo].[Process_Master_Mapping] (
                         "Model_Group"
                         ,"TPL_No"
                       ,"Operator_Code"
                       ,"Process_Code"
                       ,"Process_Seq_No"
                       ,"Line_Code")VALUES (?,?,?,?,?,?)""", request.POST["group"], request.POST["tpl_code"],
                        request.POST["operator_code"],
                        request.POST["process_code"], request.POST["sequence_no"], "EL1_P1_L1")
                    cursor.commit()

            if request.POST["radio_selection"] == "active_tpl_code":
                if request.POST["submit"] == "PM_Add":
                    copy_tpl_processes(request.POST["Active_TPL_Code"], request.POST["tpl_code"])


        except:
            print('error')

        # elif request.POST["submit"] == "PM_Modify":
        #     cursor.execute(
        #         """
        #         UPDATE [TT].[dbo].[Process_Map_Master]
        #         SET "Model_Group" = ?
        #           ,"Model_Code" = ?
        #           ,"Operator_Code" = ?
        #           ,"Process_Code" = ?
        #           ,"Process_Seq_No" = ?
        #           ,"Line_Code" = ?
        #         WHERE PMMKEY = ?""", request.POST["group"], request.POST["model_code"], request.POST["operator_code"],
        #         request.POST["process_code"], request.POST["sequence_no"],"EL1_P1_L1",request.POST["pmmkey"])
        #     cursor.commit()
        #
        # elif request.POST["submit"] == "PM_Delete":
        #     cursor.execute(
        #         """
        #         DELETE FROM [TT].[dbo].[Process_Map_Master]
        #         WHERE PMMKEY = ?""", request.POST["pmmkey"])
        #     cursor.commit()

    process_library_details = cursor.execute(
        """SELECT * FROM[TT].[dbo].[Process_Master]""")

    print("*************************************************************************")
    print("*************************************************************************")
    print("*************************************************************************")
    # print(process_library_details)

    process_library_data = [{
        "Line_Code": obj[0], "Pro_Type_Code": obj[1], "Process_Desc": obj[2], "Tool_ID": obj[3],
        "Process_Code": obj[4], "Bolt_Count": obj[5], "Process_Photo_Path": obj[6], "Takt_Time": obj[7],
        "Torque": obj[8]
    } for obj in process_library_details]
    # print({"process_master_data":process_master_data})

    process_type_details = cursor.execute(
        """SELECT [Pro_Type_Code] FROM [TT].[dbo].[Process_Type_Master]""")
    process_type_data = [i[0] for i in process_type_details]
    # print("process_type_data  ",process_type_data)

    tool_id_details = cursor.execute(
        """SELECT [Tool_ID] FROM [TT].[dbo].[Tools_Master]""")
    tool_id_data = [j[0] for j in tool_id_details]
    # print("tool_ids ", tool_id_data)

    operator_code_details = cursor.execute(
        """SELECT [Operator_Code] FROM[TT].[dbo].[Operator] order by Station_Order ASC""")
    operator_code_data = [obj[0] for obj in operator_code_details]
    # print("operator_code_data",operator_code_data)

    process_code_details = cursor.execute(
        """SELECT [Process_Code] FROM[TT].[dbo].[Process_Master]""")
    process_code_data = [obj[0] for obj in process_code_details]
    # print("process_code_data",process_code_data)

    tpl_code_details = cursor.execute(
        """SELECT DISTINCT  [TPL_No] FROM [TT].[dbo].[TPL_Master]""")
    tpl_code_data = [obj[0] for obj in tpl_code_details]
    # print("model_code_data",model_code_data)

    active_tpls_details = cursor.execute(
        """SELECT DISTINCT  [TPL_No]
      ,[TPL_Description]
      ,[Operator_Code]
      ,[No_of_Processes]
       ,[Total_Processes]FROM[TT].[dbo].[Active_TPL_List]""")
    active_tpls_data = [{
        "TPL_Code": obj[0], "TPL_Description": obj[1], "Operation_Code": obj[2], "No_of_Processes": obj[3],"Total_Process":obj[4]
    } for obj in active_tpls_details]
    # print("active_tpls_data ", active_tpls_data)

    print("*************************************************************************")
    print("*************************************************************************")
    print("*************************************************************************")

    return render(request, 'process_master_1605.html',
                  {"tpl_code_data": tpl_code_data, "process_code_data": process_code_data,
                   "operator_code_data": operator_code_data, "process_type_data": process_type_data,
                   "tool_id_data": tool_id_data, "process_library_data": process_library_data,
                   "active_tpls_data": active_tpls_data})


def copy_tpl_processes(active_tpl, new_tpl):
    cursor = db_connection()
    active_tpl_details = cursor.execute(
        """ SELECT * FROM [TT].[dbo].[Process_Master_Mapping] WHERE "TPL_No" = ?""", active_tpl)

    new_tpl_list = [{"Model_Group": obj[0], "TPL_No": new_tpl, "Operator_Code": obj[2], "Process_Code": obj[3],
                     "Process_Seq_No": obj[4], "Line_Code": obj[5]} for obj in active_tpl_details]
    for element in new_tpl_list:
        print(element)
        cursor.execute(
            """ INSERT INTO [TT].[dbo].[Process_Master_Mapping] (
            "Model_Group"
          ,"TPL_No"
          ,"Operator_Code"
          ,"Process_Code"
          ,"Process_Seq_No"
          ,"Line_Code"
          )VALUES (?,?,?,?,?,?)""", element["Model_Group"], element["TPL_No"], element["Operator_Code"],
            element["Process_Code"], element["Process_Seq_No"], element["Line_Code"])
        cursor.commit()

@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def active_tpl_list(request, tpl_code, operation_code):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "update":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Process_Master_Mapping]
               SET "Operator_Code" = ?
                  ,"Process_Seq_No" = ?
             WHERE PMKEY = ? """,
                request.POST["station"], request.POST["sequence"], request.POST["pmkey"])
            cursor.commit()

        if request.POST["submit"] == "delete":
            cursor.execute(
                """DELETE FROM [TT].[dbo].[Process_Master_Mapping]
                WHERE PMKEY = ?""", request.POST["pmkey"])
            cursor.commit()
    #print(tpl_code, operation_code)
    process_details = cursor.execute(
        """select * FROM[TT].[dbo].[Process_Master_Mapping] WHERE TPL_No = ? """, tpl_code
    )

    processes_list_data = [{"Model_Group": obj[0], "TPL_No": obj[1], "Operation_Code": obj[2],
                            "Process_Code": obj[3], "Sequence_No": round(obj[4], 1), "Line_Code": obj[5], "PMKEY": obj[6]} for obj
                           in
                           process_details]
    # print(processes_list_data)
    return render(request, 'active_tpl_list.html', {"processes_list_data": processes_list_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def tool_maintenance(request):
    cursor = db_connection()
    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "Add":
            print("Add group")

            # ,"Tool_ID","Warning_Type","Set_Frequency","Act_Frequency","Created_Date","Reset_Date","Warning_Status", "Duration_Date"
            #  ,?,?,?,?,?,?,
            #                 ?,?  , ,int(request.POST["set_frequency"]),
            #                 int(request.POST["actual_frequency"]),datetime.datetime.now().date(),datetime.datetime.now().date(),"N",request.POST["fdate"]

            cursor.execute(
                """INSERT INTO [TT].[dbo].[Tool_Maintainance] ("Line_Code" ,"Tool_ID","Warning_Type","Set_Frequency","Act_Frequency","Duration_Date","Created_Date"
                ) VALUES (?,?,?,?,?,?,?)""", "EL1_P1_L1", request.POST["tool_id"], request.POST["warning_type"],
                request.POST["set_frequency"], request.POST["actual_frequency"],
                request.POST["fdate"], str(datetime.datetime.now().date()))
            cursor.commit()

        elif request.POST["submit"] == "Modify":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Tool_Maintainance]
                SET "Warning_Type" = ?
                    ,"Set_Frequency" = ?
                    ,"Act_Frequency" = ?
                    ,"Duration_Date" = ?
                    ,"Reset_Date" = ?
                WHERE PMMKEY = ?""", request.POST["warning_type"], request.POST["set_frequency"],
                request.POST["actual_frequency"], request.POST["fdate"], str(datetime.datetime.now().date()),
                request.POST["PMMKEY"])
            cursor.commit()

        elif request.POST["submit"] == "Delete":
            cursor.execute(
                """
                    DELETE FROM [TT].[dbo].[Tool_Maintainance]
                    WHERE PMMKEY = ?""", request.POST["PMMKEY"])
            cursor.commit()

    tools_details = cursor.execute(
        """ SELECT [Tool_ID] FROM [TT].[dbo].[Tools_Master]"""
    )
    tools_details_data = [obj[0] for obj in tools_details]

    tool_maintenance_details = cursor.execute(
        """SELECT *
        FROM [TT].[dbo].[Tool_Maintainance]""")

    tool_maintenance_data = [{
        "PK_Code": obj[0], "Line_Code": obj[1], "Tool_ID": obj[2], "Warning_Type": obj[3], "Set_Frequency": obj[4],
        "Act_Frequency": obj[5], "Duration_Date": obj[6], "Created_Date": obj[7], "Reset_Date": obj[8],
        "Warning_Status": obj[9]
    } for obj in tool_maintenance_details]

    return render(request, 'tool_maintenance.html',
                  {"tools_details_data": tools_details_data, "tool_maintenance_data": tool_maintenance_data})




@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def tool_traceability_list(request):
    cursor = db_connection()
    Tool_Traceability_list = cursor.execute(
        "SELECT * FROM[TT].[dbo].[Tool_Traceability_list]")

    Tool_Traceability_list_data = [{
        "Operator_Code": obj[0], "Tool_ID": obj[1], "Pro_Type_Code": obj[2]
    } for obj in Tool_Traceability_list]
    return render(request, 'tool_traceability.html', {"Tool_Traceability_list_data": Tool_Traceability_list_data})


@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def employee(request):
    cursor = db_connection()

    employee_details = cursor.execute(
        """SELECT * FROM[TT].[dbo].[Employee_Details_UPD]""")
    employee_data = [{"Company_Code": obj[0], "Emp_ID": obj[1], "Emp_Name": obj[2], "Role_Code": obj[6],
                      "Emp_Photo_Path": obj[3], "User_Name": obj[4], "Password": obj[5]} for obj in employee_details]

    employee_skills = cursor.execute("""SELECT * FROM[TT].[dbo].[Emp_Skill_Matrix]""")
    employee_skills_data = [{"Emp_ID": obj[0], "Emp_Name": obj[1], "Sub1_OP1": obj[2], "Sub2_OP1": obj[3], "Sub3_OP1": obj[4], "Sub4_OP1": obj[5]
                             , "Sub4_OP2": obj[6], "Ass1_OP1": obj[7], "Ass1_OP2": obj[8], "Ass2_OP1": obj[9], "Ass2_OP2": obj[10]
                             , "Ass3_OP1": obj[11], "Ass3_OP2": obj[12], "Ass4_OP1": obj[13], "Ass4_OP2": obj[14], "Ass5_OP1": obj[15], "Ass5_OP2": obj[16]
                             , "Ass6_OP1": obj[17], "Ass6_OP2": obj[18], "Ass7_OP1": obj[19], "Ass7_OP2": obj[20], "Ass8_OP1": obj[21], "Ass8_OP2": obj[22]
                             , "Ass9_OP1": obj[23], "Ass9_OP2": obj[24], "Ass10_OP1": obj[25], "Ass10_OP2": obj[26], "Ass11_OP1": obj[27], "Ass11_OP2": obj[28], "Sub5_OP1":obj[30]} for obj in employee_skills]
    groups_list = Group.objects.all()
    station_list_query = cursor.execute("""SELECT Operator_Code FROM[TT].[dbo].[Operator]""")
    station_list = [obj[0] for obj in station_list_query]
    if request.method == "POST":
        if request.method == "POST" and "ED_Add" in request.POST['submit']:
            print("addddd ED")
            emp_company_code = request.POST["line-code"]
            emp_name = request.POST["emp_name"]
            emp_id = request.POST["emp_id"]
            emp_username = request.POST["emp_id"]
            emp_passwd = request.POST["pwd"]
            emp_photopath = request.POST["photo_path"]
            emp_role = request.POST["emp_role"]
            emp_dept = request.POST["emp_dept"]

            user_instance = User.objects.create_user(username = emp_username, password = emp_passwd)
            group_instance = Group.objects.get(name = emp_role)
            user_instance.groups.add(group_instance.id)
            Employee_Details.objects.create(Username = user_instance, Employee_ID = emp_id, Employee_Name=emp_name, Company_Code = emp_company_code,Employee_Photo_Path = emp_photopath,Employee_Department = emp_dept )

            cursor.execute("""INSERT INTO [TT].[dbo].[Employee_Details_UPD]
               ([Company_Code]
               ,[Emp_ID]
               ,[Emp_Name]
               ,[Emp_Photo_Path]
               ,[User_Name]
               ,[Password]
               ,[Emp_Role]
          ,[Emp_Dept])VALUES (?,?,?,?,?,?,?,?)""",emp_company_code, emp_id, emp_name, emp_photopath, emp_username, emp_passwd, emp_role, emp_dept)
            cursor.commit()

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Emp_Skill_Matrix] (
                "Emp_ID"
                ,"Emp_Name"
                ) VALUES (?,?)""",emp_id,emp_name)
            cursor.commit()
        if request.method == "POST" and "ED_Modify" in request.POST['submit']:
            print("ED MOdify")
            emp_company_code = request.POST["line-code"]
            emp_name = request.POST["emp_name"]
            emp_id = request.POST["emp_id"]
            emp_username = request.POST["emp_name"]
            emp_passwd = request.POST["pwd"]
            emp_photopath = request.POST["photo_path"]
            emp_role = request.POST["emp_role"]
            emp_dept = request.POST["emp_dept"]
            print(emp_company_code,emp_name,emp_id,emp_username,emp_passwd,emp_photopath,emp_role,emp_dept)

            user_instance = User.objects.get(username=emp_username)
            # group_instance = Group.objects.get(name=emp_role)
            # user_instance.groups.add(group_instance.id)
            # Employee_Details.objects.create(Username=user_instance, Employee_ID=emp_id, Employee_Name=emp_name,
            #                                 Company_Code=emp_company_code, Employee_Photo_Path=emp_photopath,
            #                                 Employee_Department=emp_dept)
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Employee_Details_UPD] 
                SET [Company_Code]=?
                ,[Emp_ID]=?
                ,[Emp_Name]=?
                ,[Emp_Photo_Path]=?
                ,[User_Name]=?
                ,[Password]=?
                ,[Emp_Dept]=?
                WHERE [Emp_ID]=?""",
                emp_company_code,emp_id,emp_name,emp_photopath ,emp_username,emp_passwd,emp_dept,emp_id)
            cursor.commit()
        if request.method == "POST" and "ED_Delete" in request.POST['submit']:
            print("ED Delete")
            emp_company_code = request.POST["line-code"]
            emp_name = request.POST["emp_name"]
            emp_id = request.POST["emp_id"]
            emp_username = request.POST["emp_name"]
            emp_passwd = request.POST["pwd"]
            emp_photopath = request.POST["photo_path"]
            emp_role = request.POST["emp_role"]
            emp_dept = request.POST["emp_dept"]

            cursor.execute(
                """
                    DELETE FROM [TT].[dbo].[Employee_Details_UPD]
                    WHERE emp_id = ?""", emp_id)
            cursor.commit()

        if request.method == "POST" and "ES_Modify" in request.POST['submit'] or "ES_Add" in request.POST['submit']:
            print("ES_Modify")
            emp_id1 = request.POST["emp_id1"]
            station_name = request.POST["station_name"]
            skill_level = request.POST["skill_level"]

            emp_skill_query = cursor.execute(
                """ UPDATE [TT].[dbo].[Emp_Skill_Matrix] SET """ + station_name + """=""" + skill_level + """ WHERE Emp_ID = ? """,
                emp_id1)
            cursor.commit()

            print(emp_skill_query, "empskillquery..")
        if request.method == "POST" and "ES_Delete" in request.POST['submit']:
            emp_id = request.POST["emp_id1"]
            station_name = request.POST["station_name"]
            skill_level = request.POST["skill_level"]
            print("ES_Delete")
            cursor.execute(
                """
                    DELETE FROM [TT].[dbo].[Emp_Skill_Matrix]
                    WHERE Emp_ID = ?""", emp_id)
            cursor.commit()
    return render(request, 'employee_2905.html', {'employee_data': employee_data, "group_list":groups_list, 'employee_skills':employee_skills_data, 'station_list':station_list})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def packing(request):
    cursor = db_connection()
    packing_details = cursor.execute(
        """SELECT * FROM[TT].[dbo].[Packing_DD]""")
    packing_data = [{"Package_Code": obj[0]} for obj in packing_details]

    return render(request, 'packing.html', {'packing_data': packing_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
@login_required(login_url='login')
def drive_coupling_master(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "Add":
            cursor.execute(
            """ INSERT INTO [TT].[dbo].[Drive_Coupling_Master] (
                "TPL_No",
                "TPL_Description",
                "Distance",
                "Sensor_No",
                "Test_Certificate"
              )VALUES (?,?,?,?,?)""",  request.POST["TPL_No"], request.POST["TPL_Description"],
            request.POST["Distance"], request.POST["Sensor_No"], request.POST["Test_Certificate"])
            cursor.commit()

        if request.POST["submit"] == "Update":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Drive_Coupling_Master]
               SET "TPL_Description" = ?
                ,"Distance" = ?
                ,"Sensor_No" = ?
                ,"Test_Certificate" = ?
             WHERE TPL_No = ? """,request.POST["TPL_Description"],
            request.POST["Distance"], request.POST["Sensor_No"], request.POST["Test_Certificate"],request.POST["TPL_No"])
            cursor.commit()

        if request.POST["submit"] == "Del":
            cursor.execute("""
                            DELETE FROM [TT].[dbo].[Drive_Coupling_Master]
                            WHERE TPL_No = ?""", request.POST["TPL_No"])
            cursor.commit()

    tpl_code_details = cursor.execute(
        """SELECT DISTINCT  [TPL_No] FROM [TT].[dbo].[TPL_Master]""")
    tpl_code_data = [obj[0] for obj in tpl_code_details]
    # print("model_code_data",model_code_data)


    dc_master_details = cursor.execute(
        """ SELECT * FROM [TT].[dbo].[Drive_Coupling_Master] """)
    dc_master_data = [{"TPL_No": obj[0], "TPL_Description": obj[1], "Model_Code": obj[2], "Distance": obj[3],
                       "Sensor_No": obj[4], "Test_Certificate": obj[5]} for obj in dc_master_details]
    # print("drive coupling")
    return render(request, 'drive_coupling_master.html', {'dc_master_data':dc_master_data, 'tpl_code_data':tpl_code_data})



@permission_required('ELGI_App.station_view', login_url = 'no_access')
@login_required(login_url='login')
def stations_list(request):
    cursor = db_connection()
    stations_details = cursor.execute(
        """ SELECT * FROM [TT].[dbo].[Operator] ORDER BY Station_Order ASC"""
    )
    station_data = [{"station_name":obj[4],"statiion_id":obj[1]} for obj in stations_details]
    return render(request, 'stations/stations.html', {'station_data':station_data})



@permission_required('ELGI_App.supervisor_view', login_url = 'no_access')
@login_required(login_url='login')
def dms_master(request):
    cursor = db_connection()
    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "P_Add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[DMS_Master] (
            		"DMS_Type",
            		"Level_1",
            		"Level_2",
            		"Level_3",
            		"Level_4",
            		"Level_5"
                  )VALUES (?,?,?,?,?,?)""", "P_Loss", request.POST["Level_1"], request.POST["Level_2"],
                request.POST["Level_3"], request.POST["Level_4"], request.POST["Level_5"])
            cursor.commit()

        elif request.POST["submit"] == "Q_Add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[DMS_Master] (
                    "DMS_Type",
                    "Level_1",
                    "Level_2",
                    "Level_3",
                    "Level_4",
                    "Level_5"
                  )VALUES (?,?,?,?,?,?)""", "Q_Loss", request.POST["Level_1"], request.POST["Level_2"],
                request.POST["Level_3"], request.POST["Level_4"], request.POST["Level_5"])
            cursor.commit()


        elif request.POST["submit"] == "Modify":
            cursor.execute(
                """ UPDATE [TT].[dbo].[DMS_Master]
               SET "Level_1" = ?
                  ,"Level_2" = ?
                  ,"Level_3" = ?
                  ,"Level_4" = ?
                  ,"Level_5" = ?
             WHERE PMMKEY = ?""", request.POST["Level_1"], request.POST["Level_2"], request.POST["Level_3"],
                request.POST["Level_4"], request.POST["Level_5"], request.POST["PMMKEY"])
            cursor.commit()

        elif request.POST["submit"] == "Delete":
            cursor.execute(
                """ DELETE FROM [TT].[dbo].[DMS_Master]
                WHERE PMMKEY = ?""", request.POST["PMMKEY"])
            cursor.commit()

    pdms = cursor.execute(
        "SELECT * FROM[TT].[dbo].[DMS_Master] WHERE DMS_Type = ?", "P_Loss")

    pdms_data = [{
        "PMMKEY": obj[0], "Level_1": obj[2], "Level_2": obj[3],
        "Level_3": obj[4], "Level_4": obj[5], "Level_5": obj[6]} for obj in pdms]
    print(pdms_data)

    qdms = cursor.execute(
        "SELECT * FROM[TT].[dbo].[DMS_Master] WHERE DMS_Type = ?", "Q_Loss")

    qdms_data = [{
        "PMMKEY": obj[0], "Level_1": obj[2], "Level_2": obj[3],
        "Level_3": obj[4], "Level_4": obj[5], "Level_5": obj[6]} for obj in qdms]
    print(qdms_data)

    return render(request, 'dms_master.html', {"pdms_data": pdms_data, "qdms_data": qdms_data})


def P_Loss(cursor, request):
    cursor.execute(
        """ INSERT INTO [TT].[dbo].[DMS_P_Loss_Update] (
            "Fab_No"
             ,"TPL_No"
             ,"Model_group"
             ,"Emp_Name"
             ,"Emp_ID"
             ,"Station"
             ,"Timestamp"
             ,"Time_Diff"
             ,"Level_1"
             ,"Level_2"
             ,"Level_3"
             ,"Level_4"
             ,"Level_5"
             )VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", request.POST["FAB_NO"], request.POST["TPL_No"],
        request.POST["Model_Group"], request.POST["Emp_Name"],
        request.POST["Emp_ID"], request.POST["station_id"], "Timestamp", str(request.POST["Difference"]),
        request.POST["Level1"], request.POST["Level2"],
        "Level_3", "Level_4", "Level_5")
    cursor.commit()
    return "complete"





def Q_Loss(cursor, request, Q_method):

    if Q_method == "status":

        status_details = cursor.execute(
            "SELECT [Status] FROM[TT].[dbo].[DMS_Q_Loss_Update] where DMS_ID = ?", request.POST['DMS_ID']
        )
        status = [i[0] for i in status_details]
        print('status', status)
        # status = "completed/inprogress"
        return {"response": status[0]}

    if Q_method == "update":
        process_data = ast.literal_eval(request.POST["process_data"])
        cursor.execute(
            """ UPDATE [TT].[dbo].[DMS_Q_Loss_Update]
           SET "DMS_Time" = ?
         WHERE DMS_ID = ? """, process_data['Time'], process_data['DMS_ID'] )
        cursor.commit()

        return {"response": "completed"}



    if Q_method == "create":
        process_data = ast.literal_eval(request.POST["process_data"])
        print("**************************************************************")
        print("request data", request.POST["FAB_NO"], request.POST["TPL_No"], request.POST["Emp_Name"],
              request.POST["Emp_ID"], request.POST["station_id"], process_data["Level1"], process_data["Level2"])

        DMS_ID = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cursor.execute(
            """ INSERT INTO [TT].[dbo].[DMS_Q_Loss_Update] (
           		"Fab_No"
                 ,"TPL_No"
                 ,"Process_Desc"
                 ,"Operator_Emp_Name"
                 ,"Operator_Emp_ID"
                 ,"Station"
                 ,"Timestamp"
                 ,"Level_1"
                 ,"Level_2"
                 ,"DMS_ID"
                 ,"Status"
                 )VALUES (?,?,?,?,?,?,?,?,?,?,?)""", request.POST["FAB_NO"], request.POST["TPL_No"],
            request.POST["Process_Desc"], request.POST["Emp_Name"],
            request.POST["Emp_ID"], request.POST["station_id"], datetime.datetime.now().isoformat(" ").split(".")[0], process_data["Level1"],
            process_data["Level2"], DMS_ID,"inprogress")
        cursor.commit()
        return {"response": "submitted", "DMS_ID": DMS_ID}


def P_Q_Levels(cursor, method):
    l1 = cursor.execute(
        "SELECT DISTINCT [Level_1] FROM [TT].[dbo].[DMS_Master] WHERE DMS_Type = ?", method)
    l1_data = [obj[0] for obj in l1]
    l2 = cursor.execute(
        "SELECT DISTINCT [Level_2] FROM [TT].[dbo].[DMS_Master] WHERE DMS_Type = ?", method)
    l2_data = [obj[0] for obj in l2]

    return {"level_1_data": l1_data, "level_2_data": l2_data}



@permission_required('ELGI_App.supervisor_view', login_url = 'no_access')
@login_required(login_url='login')
def dms_app(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        base64_string = request.POST['img_url']
        try:
            data = base64.b64decode(base64_string.split(',')[1])

            img = Image.open(BytesIO(data))
        except:
            img = ""
        #img.show()

        static_path = os.path.join(settings.BASE_DIR,'ELGI_App','static/images/IMG/DMS_Pictures')
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        file_name = str(request.POST['fab_no'])+"_" + current_time + ".png"
        print(file_name)
        if img != "":
            img.save(os.path.join(static_path, file_name))

        cursor = db_connection()
        cursor.execute(
            """
            UPDATE [TT].[dbo].[DMS_Q_Loss_Update]
           SET "Supervisor_Emp_Name" = ?
           ,"Supervisor_Emp_ID" = ?
           ,"Level_3" = ?
           ,"Level_4" = ?
           ,"Level_5" = ?
           ,"img" = ?
           ,status = 'C'
         WHERE PMMKEY = ?""", request.POST['Emp_Name'], request.POST['Emp_Id'], request.POST['level_3'], request.POST['level_4'], request.POST['level_5'], "defect_img.img", request.POST['PMMKEY'] )
        cursor.commit()

    qdms = cursor.execute(
        "SELECT Level_3, Level_4, level_5 FROM[TT].[dbo].[DMS_Master] WHERE DMS_Type = ?", "Q_Loss")

    qdms_data = [{
        "level_3": obj[0], "level_4": obj[1], "level_5": obj[2]} for obj in qdms]
    # print(qdms_data)

    level_3 = [i['level_3'] for i in qdms_data]
    level_4 = [i['level_4'] for i in qdms_data]
    level_5 = [i['level_5'] for i in qdms_data]

    q_loss_details = cursor.execute(
        "SELECT * FROM[TT].[dbo].[DMS_Q_Loss_Update] where Status = 'inprogress' ")

    q_loss_details_list = [{
        "PMMKEY": obj[0], "TPL_No": obj[1], "FAB_No": obj[2], "Station": obj[3], "Process_desc": obj[4],
        "Level_1": obj[11], "Level_2": obj[12]
    } for obj in q_loss_details]

    user_name = str(request.user)
    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Photo_Path": static("images/IMG/Employee_Picture/" + str(obj[2]))
    } for obj in cursor.execute(employee_details_query, user_name)]

    employee_skill_query = """ SELECT Sub5_OP1 FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
    employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_name)]
    print("employee_skill_list  ", employee_skill_list)
    Skill_Level = employee_skill_list[0][0]
    employee_details_list[0].update({"Skill_Level": Skill_Level})

    return render(request, 'dms_app.html', {'q_loss_details_list': q_loss_details_list, 'level_3': level_3, 'level_4': level_4, 'level_5': level_5, "employee_details_list":employee_details_list[0]})
    # return render(request, 'dms_app_2803.html', {'q_loss_details_list': q_loss_details_list, 'level_3': level_3, 'level_4': level_4, 'level_5': level_5})



@permission_required('ELGI_App.station_view', login_url = 'no_access')
@login_required(login_url='login')
def store(request):
    cursor = db_connection()
    user_name = str(request.user)
    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Photo_Path": static("images/IMG/Employee_Picture/" +  str(obj[2]))
    } for obj in cursor.execute(employee_details_query, user_name)]

    print("employee_details_list ",employee_details_list)
    print("User ",user_name)

    employee_skill_query = """ SELECT Sub5_OP1 FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
    employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_name)]
    print("employee_skill_list  ",employee_skill_list)
    Skill_Level = employee_skill_list[0][0]
    employee_details_list[0].update({"Skill_Level":Skill_Level})

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST['submit'] == "release":
            cursor.execute(
                """
                    UPDATE [TT].[dbo].[Store_Home_View]
                   SET "Status" = 'P'
                 WHERE TPL_No = ? and FAB_NO = ?""", request.POST['tpl_number'], request.POST['fab_number'])
            cursor.commit()


            release_details = cursor.execute(
                """
                SELECT * FROM [TT].[dbo].[Store_Home_View] WHERE TPL_No = ? AND FAB_NO = ?""",
                request.POST['tpl_number'], request.POST['fab_number']
            )
            release_data = [{"TPL_No": obj[0], "FAB_NO": obj[1], "pd_no": obj[2], "Release_Date": obj[3],
                             "Status": obj[4], "TPL_Description": obj[5], "Completed_Date": obj[6]} for obj in
                            release_details]

            print("release_data  ", release_data)

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Store_CP_Details] (
                    "PO_No"
                   ,"FAB_NO"
                   ,"TPL_Desc"
                      )VALUES (?,?,?)""", release_data[0]['pd_no'], release_data[0]['FAB_NO'],
                release_data[0]['TPL_Description'])
            cursor.commit()


            cp_details = cursor.execute(
                """
                SELECT Part_No, Child_Part_Code, Fab_Number FROM [TT].[dbo].[LN_CP_Details] WHERE TPL_Number = ? AND Fab_Number = ?""" ,
                request.POST['tpl_number'], request.POST['fab_number']
            )

            cp_details_data = [{"Part_no":obj[0], "Child_Part_Code":obj[1], "Fab_No":obj[2]} for obj in cp_details]
            print("cp_details ", cp_details_data)

            print(len(cp_details_data))

            for cp in cp_details_data:
               try:
                    cursor.execute(
                            """
                            UPDATE [TT].[dbo].[Store_CP_Details]
                           SET """+ cp["Child_Part_Code"]+ """ = ?
                         WHERE FAB_NO = ? """, cp["Part_no"][-4:], cp["Fab_No"])
                    cursor.commit()
               except:
                   pass

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Store_Status] (
                	"TPL_No"
                      ,"FAB_NO"
                      ,"pd_no"
                      ,"TPL_Description"
                      ,"Release_Date"
                      ,"Status"
                      ,"Station"
                      ,"Completed_Date"
                      )VALUES (?,?,?,?,?,?,?,?)""", release_data[0]['TPL_No'], release_data[0]['FAB_NO'],
                release_data[0]['pd_no'], release_data[0]['TPL_Description'], datetime.datetime.now().isoformat(" ").split(".")[0],
                release_data[0]['Status'], "Store", " ")
            cursor.commit()

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Fab_History] (
                 "TPL_No"
                   ,"Fab_No"
                   ,"pd_no"
                   ,"TPL_Description"
                   ,"Start_datetime"
                   ,"Status"
                   ,"Station_Name"
                   ,"Completed_Datetime"
                   ,"Emp_Name"
                   ,"Emp_ID"
                   )VALUES (?,?,?,?,?,?,?,?,?,?)""", release_data[0]['TPL_No'], release_data[0]['FAB_NO'],
                release_data[0]['pd_no'],
                release_data[0]['TPL_Description'], release_data[0]['Release_Date'],
                "C", "Store", datetime.datetime.now().isoformat(" ").split(".")[0], "", "")
            cursor.commit()

            for stations in ['Sub1_OP1', 'Sub2_OP1', 'Sub3_OP1', 'Ass1_OP1', 'Ass1_OP2']:
                cursor.execute(
                    """ INSERT INTO [TT].[dbo].[Fab_History] (
                     "TPL_No"
                       ,"Fab_No"
                       ,"pd_no"
                       ,"TPL_Description"
                       ,"Start_datetime"
                       ,"Status"
                       ,"Station_Name"
                       ,"Completed_Datetime"
                       ,"Emp_Name"
                       ,"Emp_ID"
                       )VALUES (?,?,?,?,?,?,?,?,?,?)""", release_data[0]['TPL_No'], release_data[0]['FAB_NO'],
                    release_data[0]['pd_no'],
                    release_data[0]['TPL_Description'], "",
                    "P", stations, "", "", "")
                cursor.commit()

    store_home_details = cursor.execute(
        "SELECT * FROM[TT].[dbo].[Store_Home_View] WHERE Status = 'R'")

    store_home_data = [{
        "TPL_No": obj[0], "FAB_NO": obj[1], "pd_no": obj[2], "Release_Date": obj[3],
        "Status": obj[4], "TPL_Description": obj[5], "Completed_Date": obj[6]
    } for obj in store_home_details]

    cpdetails = cursor.execute(
        "SELECT * FROM [TT].[dbo].[Store_CP_Details]")

    cp_details_data = [{
        "PO_No": obj[1], "FAB_NO": obj[2], "TPL_Desc": obj[3], "CP_AIREND": obj[4], "CP_MOTOR": obj[6], "CP_CONTROL_PANEL": obj[8],
        "CP_TANK": obj[10], "CP_FAN_MOTOR": obj[12],
        "CP_COOLER": obj[14], "CP_VFD": obj[16], "CP_DRYER": obj[18], "CP_CANOPY": obj[20], "SHR": obj[22], "ADR": obj[24], "COU": obj[26], "STS":"P"
    } for obj in cpdetails]

    status_details = cursor.execute(
        "SELECT * FROM[TT].[dbo].[Store_Status] WHERE Status = 'P' ")

    status_data = [{
        "TPL_No": obj[0], "FAB_NO": obj[1], "pd_no": obj[2], "TPL_Description": obj[3],
        "Release_Date": obj[4], "Status": obj[5], "Station": obj[6], "Completed_Date": obj[7]
    } for obj in status_details]

    return render(request, 'store.html',
                  {'store_home_data': store_home_data, "cp_details_data": cp_details_data, "status_data": status_data,
                   "employee_details": {
                       "Emp_Name": employee_details_list[0]["Emp_Name"],
                       "Emp_ID": employee_details_list[0]["Emp_ID"],
                       "Skill_level": employee_details_list[0]["Skill_Level"],
                       "Photo_Path":employee_details_list[0]["Photo_Path"]

                   }
                   })


# schedules
@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def break_display_configuration(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[break_Disp_Config] (
            "Break_Name"
            ,"Img_Disp"
            ,"Info_Disp"
                  )VALUES (?,?,?)""", request.POST['break_name'], request.POST['img_file'], request.POST['info'])
            cursor.commit()
        if request.POST["submit"] == "update":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[break_Disp_Config]
               SET "Img_Disp" = ?
            ,"Info_Disp" = ?
             WHERE "Break_Name" = ?""", request.POST['img_file'], request.POST['info'], request.POST['break_name'])
            cursor.commit()
        if request.POST["submit"] == "del":
            cursor.execute(
                """
                DELETE FROM [TT].[dbo].[break_Disp_Config]
                WHERE "Break_Name" = ?""", request.POST['break_name'])
            cursor.commit()

    break_details = cursor.execute(
        "SELECT * FROM [TT].[dbo].[break_Disp_Config]")
    break_details_data = [{"name": obj[0], "img": obj[1], "info": obj[2]} for obj in break_details]
    return render(request, 'break_display_configuration.html', {'break_details_data': break_details_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def message_configuration(request):
    cursor = db_connection()
    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Msg_info] (
                    "Message_Type"
                   ,"Station_Code"
                   ,"Information"
                   ,"Data_File"
       )VALUES (?,?,?,?)""", request.POST['msg_type'], request.POST['st_code'], request.POST['info'],
                request.POST['data_file'])
            cursor.commit()
        if request.POST["submit"] == "update":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Msg_info]
               SET "Message_Type" = ?
                   ,"Station_Code" = ?
                   ,"Information" = ?
                   ,"Data_File" = ?
             WHERE "PMMKEY" = ?""", request.POST['msg_type'], request.POST['st_code'], request.POST['info'],
                request.POST['data_file'], request.POST['PMMKEY'])
            cursor.commit()
        if request.POST["submit"] == "del":
            cursor.execute(
                """
                DELETE FROM [TT].[dbo].[Msg_info]
                WHERE "PMMKEY" = ?""", request.POST['PMMKEY'])
            cursor.commit()

    msg_details = cursor.execute(
        "SELECT * FROM [TT].[dbo].[Msg_info]")
    msg_data = [{"Message_Type": obj[0], "Station_Code": obj[1], "Information": obj[2], "Data_File":obj[3], "PMMKEY":obj[4]} for obj in msg_details]



    return render(request, 'message_configuration.html',{'msg_data':msg_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def breakandshift(request):

    return render(request, 'shift_and_break_main.html')


@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def holidays(request):

    return render(request, 'holidays.html')


@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def messages(request):

    return render(request, 'messages.html')



def tower_lamp(station_id, type = None, loss = 0, tpl_no = None, fab_no = None):
    cursor = db_connection()
    tower_lamp_st_reg = cursor.execute(
        "SELECT [Tower_Lamp_Reg] FROM[TT].[dbo].[Operator] WHERE Operator_Code = ? ", station_id)

    tower_reg = [obj[0] for obj in tower_lamp_st_reg]
    print("tower_reg ", tower_reg)

    if type == "start":
        reg_value  = 2
        try:
            client.write_register(tower_reg[0],reg_value)
        except:
            print("no tower lamp reg")
        print("*******************  YELLOW")

    if type == "completed":
        loss_time_details = cursor.execute(
            "SELECT [Loss] FROM [TT].[dbo].[Fab_History] WHERE TPL_No = ? and FAB_No = ? and Station_Name = ?", tpl_no, fab_no,station_id
        )
        loss_data = [obj[0] for obj in loss_time_details]
        print("loss_data" ,loss_data)
        # loss_data[0] = 1 # test data
        if int(loss_data[0]) > 0:
            reg_value = 3
            try:
                client.write_register(tower_reg[0],reg_value)
            except:
                print("no tower lamp reg ")
            print("*******************  RED")

        elif int(loss_data[0]) <= 0:
            reg_value = 1
            try:
                client.write_register(tower_reg[0], reg_value)
            except:
                print("no tower lamp reg")
            print("*******************  GREEN")


    if type == "loss":
        cycle_time = cycle_time_conversion(cursor, fab_no, station_id)
        actual_time_details = cursor.execute("SELECT [Actual_Time_Sec] FROM[TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? and Fab_No = ? and Station_ID = ? ",tpl_no,fab_no,station_id)
        actual_time = [obj[0] for obj in actual_time_details]
        print("*************** ",cycle_time , actual_time)
        loss_time = int(cycle_time[1]) - int(actual_time[-1])

        if loss_time >= 0:
            reg_value = 2
            try:
                client.write_register(tower_reg[0], reg_value)
            except:
                print("no tower lamp reg")
            print("*******************  YELLOW")

        elif loss_time < 0:
            reg_value = 3
            try:
                client.write_register(tower_reg[0], reg_value)
            except:
                print("no tower lamp reg")
            print("*******************  RED")





@permission_required('ELGI_App.station_view', login_url = 'no_access')
@login_required(login_url='login')
def station_order_release(request, station_id):

    cursor = db_connection()
    user_id = str(request.user)
    try:
        print("station_id   ",station_id)
        print("Emp_ID   ",user_id)
        emp_skill_query = """SELECT """+ station_id + """ FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID = ?"""
        cursor.execute(emp_skill_query, user_id)
        Emp_SKill = cursor.fetchall()
        print("skillllll ",Emp_SKill)
        cursor.execute("""SELECT [Skill_Required] FROM [TT].[dbo].[Operator] WHERE Operator_Code = ?""", station_id)
        Req_Skill = cursor.fetchall()
    except:
        Emp_SKill = [[10]]
        Req_Skill = [[10]]
        # Emp_SKill[0][0] = 10
        # Req_Skill[0][0] = 1


    print("Employee Skill", Emp_SKill, type(Emp_SKill))
    print("Req Skill", Req_Skill[0][0], type(Req_Skill[0][0]))

    # if Emp_SKill.Skill_Level < Req_Skill.Skill_Required:
    if Emp_SKill[0][0] != None and Req_Skill[0][0] != None and Emp_SKill[0][0]>0 and Req_Skill[0][0]>0 and Emp_SKill[0][0] >= Req_Skill[0][0]:

        bypass_stations = cursor.execute(
            """ SELECT Station_ID
            FROM [TT].[dbo].[Station_Bypass] where Bypass = 'Bypass' """)
        bypass_stations_list = [obj[0] for obj in bypass_stations]

        if station_id in bypass_stations_list:
            bypass_status = {
                "popup": "show",
                "message": "Station " + station_id + " is Bypassed"
            }
        else:
            bypass_status = {
                "popup": "hide"
            }


        employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
        employee_details_list = [{
            "Emp_ID": obj[0],
            "Emp_Name": obj[1],
            "Photo_Path": static("images/IMG/Employee_Picture/" + str(obj[2]))
        } for obj in cursor.execute(employee_details_query,user_id)]

        employee_skill_query = """ SELECT """+ station_id +""" FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
        employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_id)]
        print("employee_skill_list  ", employee_skill_list)
        Skill_Level = employee_skill_list[0][0]
        employee_details_list[0].update({"Skill_Level": Skill_Level})


        if station_id == "Sub5_OP1":
            return redirect(store)

        if station_id == "Q_DMS":
            return redirect(dms_app)

        # elif station_id == "Rework_OP1":
        #     return render(request,'stations/station_home.html')




        elif station_id in ["Sub1_OP1","Sub2_OP1","Sub3_OP1","Sub4_OP1","Sub4_OP2"]:
            switch = {
                "Sub1_OP1": "Sub_Station_1_Home",
                "Sub2_OP1": "Sub_Station_2_Home",
                "Sub3_OP1": "Sub_Station_3_Home",
                "Sub4_OP1": "Sub_Station_4A_Home",
                "Sub4_OP2": "Sub_Station_4B_Home",
            }
            result = switch.get(station_id,"error")
            print("result ", result)




            order_release_query = """SELECT * FROM [TT].[dbo].[""" + result  + """] """  # WHERE Release_Date >= DATEADD(day, -50, GETDATE()) AND Status = 'R'"""
            order_release_table = [{
                "TPL_No": obj[0],
                "FAB_No": obj[1],
                "TPL_Description": obj[3],
                "Status": obj[5]
            } for obj in cursor.execute(order_release_query)]
            print(order_release_query)

            # order_release_error_query = """SELECT * FROM [TT].[dbo].[Sub1_OP1_Fab_Init_View] WHERE Release_Date >= DATEADD(day, -30, GETDATE()) AND Status = NULL """
            # order_release_error_table = [{
            #     "TPL_No": obj[0],
            #     "FAB_No": obj[1],
            #     "Release_Date": obj[3],
            #     "TPL_Description": obj[7]
            # } for obj in cursor.execute(order_release_error_query)]
            # print("order_release_table",order_release_table)
            #print("order release error table", order_release_error_table)



            json_data = {
                "order_release_table":order_release_table,
                # "order_release_error_table":order_release_error_table,
                "employee_details_list":employee_details_list[0],
                "popup_status":bypass_status
            }
            print(json_data)
            return render(request,'stations/station_home.html',json_data)
        else:
            print("main station submit")
            json_data = {
                # "order_release_table": order_release_table,
                # "order_release_error_table":order_release_error_table,
                "station_id" :station_id,
                "employee_details_list": employee_details_list[0],
                "popup_status": bypass_status
            }
            if request.method == "POST":
                fabno = request.POST["fab_no"]
                print("fabno", fabno, type(fabno))
                tpl_no_details = cursor.execute("select TPL_No FROM[TT].[dbo].[LN_Order_Release] where FAB_NO = ?", fabno)
                print("tpl details", tpl_no_details)
                tpl_no_data = [obj[0] for obj in tpl_no_details]
                print(tpl_no_data)
                process_url =  str(tpl_no_data[0]) +"/"+str(request.POST["fab_no"])
                print(process_url)
                return redirect(process_url,json_data)
            print("json_dtaaaa", json_data)
            return render(request, 'stations/mainstation_home.html',json_data)
    else:
        print("redirect_station_order_release")
        return redirect(stations_list)


# operator screens
@permission_required('ELGI_App.station_view', login_url = 'no_access')
@login_required(login_url='login')
def substation(request,station_id, tplno, fabno):
    user_name = str(request.user)

    if station_id == "Rework_OP1":
        return redirect(rework_station,tplno,fabno)


    if station_id == "PDI_I1_OP1":
        return redirect(pdi_inspection_process, tplno=tplno, fabno=fabno)

    if station_id == "Packing1_OP1":
        return redirect(package_station, TPL_No=tplno, FAB_NO=fabno)

    # if station_id == "Packing1_OP1":
    #     return redirect(packing)

    cursor = db_connection()
    process_seq_list  = []
    # user_name = "100213"
    user_name = str(request.user)
    if request.method == 'POST':
        print("*********************")
        print(request.POST)

    # print("***************************************************")
    # print("station id in substation fn", station_id)
    missed_stations = station_interlock_check(station_id, tplno, fabno)
    # print("missed_Stations in substation ", missed_stations)

    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Photo_Path": static("images/IMG/Employee_Picture/" + str(obj[2]))
    } for obj in cursor.execute(employee_details_query,user_name)]

    employee_skill_query = """ SELECT Sub5_OP1 FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
    employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_name)]
    Skill_Level = employee_skill_list[0][0]
    employee_details_list[0].update({"Skill_Level": Skill_Level})

    if missed_stations == True:
        # print("missed_stations_substation",missed_stations)

        process_seq_data = finding_seq(station_id, tplno, fabno)

        if process_seq_data == "seq_complete":
            cycle_time = cycle_time_conversion(cursor, fabno, station_id)
            print("cycle_timecycle_timecycle_time ",cycle_time)
            actual_time_query = """SELECT TOP 1 Actual_Time, Actual_Time_Sec
                                      FROM [TT].[dbo].[Process_Update_Table]
                                      WHERE TPL_No = ? and Fab_No = ? and Station_ID = ?
                                      order by Process_Seq_No DESC"""
            # completed_seq_no_list = [obj[0] for obj in cursor.execute(completed_seq_no_query, tplno, fabno, station_id)]
            actual_time = [obj for obj in cursor.execute(actual_time_query, tplno, fabno, station_id)]
            print("actual_timeactual_time  ",actual_time)
            print("ACTUAL_TIMEEEEEEE", actual_time)
            print("Employee Details List", employee_details_list)
            print("FAB DETAILS", tplno, fabno, station_id)

            cursor.execute("""SELECT * FROM [TT].[dbo].[Fab_History] WHERE TPL_NO = ? and Fab_No = ? and Station_Name = ?""", tplno, fabno, station_id)
            slect_q = cursor.fetchall()
            print("SELECT QUERY", slect_q)

            fab_status_update_query="""UPDATE  [TT].[dbo].[Fab_History] 
            SET Emp_ID = ?, Emp_Name = ?, Emp_Skill = ?, Cycle_time = ?, Actual_time = ?, Loss = ?
            WHERE TPL_NO = ? and Fab_No = ? and Station_Name = ?"""
            # print("ac ",actual_time[0][1])
            # print("ct ",cycle_time[1])
            try:
                loss = int(actual_time[0][1]) - int(cycle_time[1])
            except:
                loss = 0
                actual_time = [("00:00",0)]


            cursor.execute(fab_status_update_query, employee_details_list[0]["Emp_ID"], employee_details_list[0]["Emp_Name"],
                           employee_details_list[0]["Skill_Level"], cycle_time[0], actual_time[0][0], loss, tplno, fabno, station_id)
            cursor.commit()

            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            # tower lamp Green/Red
            # tower_lamp(station_id, type="completed", tpl_no=tplno, fab_no=fabno)

            return redirect(station_order_release,station_id = station_id)

        file_info = info_button(station_id)
        skip_processes = skipped_process(tplno, fabno)
        if len(skip_processes) == 0:
            popup_status = "hide"
        else:
            popup_status = "show"


        json_data = {
                "process_type":process_seq_data["Pro_Type_Code"],
                "employee_details": {
                    "Emp_Name": employee_details_list[0]["Emp_Name"],
                    "Emp_ID": employee_details_list[0]["Emp_ID"],
                    "Skill_level": employee_details_list[0]["Skill_Level"],
                    "Photo_Path": employee_details_list[0]["Photo_Path"],
                },
                "process_seq": process_seq_data,
                "popup_status": "hide",
                "file_info" : file_info,
                "skiped_popup":popup_status,
                "skiped_process": skip_processes
            }
    else:
        json_data = {
            "process_type": "",
            "employee_details": {
                "Emp_Name": employee_details_list[0]["Emp_Name"],
                "Emp_ID": employee_details_list[0]["Emp_ID"],
                "Skill_level": employee_details_list[0]["Skill_Level"]
            },
            "process_seq": [],
            "popup_status":"show","missed_stations_list":missed_stations,
            "station_id":station_id
        }


    # if missed_stations != True:
    #     json_data.update({"popup_status":"show","missed_stations_list":missed_stations})
    # else:
    #     json_data.update({"popup_status": "hide"})
    #
    # print("final josn", json_data)
    # return render(request,'stations/substation_2703.html',json_data)
    # return render(request,'stations/substation_2905.html',json_data)
    return render(request,'stations/substation_3005.html',json_data)



def finding_seq(station_id, tplno, fabno):

    cursor = db_connection()
    base_url = r"static/images/users/"
    completed_seq_no_query = """ SELECT Process_Seq_No FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? AND Fab_No = ? AND Station_ID = ? ORDER BY Process_Seq_No ASC """
    completed_seq_no_list  = [obj[0] for obj in cursor.execute(completed_seq_no_query,tplno, fabno, station_id)]
    process_seq_no_query  = """SELECT Process_Seq_No FROM [TT].[dbo].[Sub_Station_Screens_Data_View] WHERE TPL_No = ? AND FAB_NO = ? AND Operator_Code = ? ORDER BY Process_Seq_No ASC"""
    process_seq_no_list = [obj[0] for obj in cursor.execute(process_seq_no_query, tplno, fabno, station_id)]
    print("seq_no lists", completed_seq_no_list, process_seq_no_list, station_id, tplno, fabno)

    for i in completed_seq_no_list:                         # need change
        if i in process_seq_no_list:
            process_seq_no_list.remove(i)
    print("present seq_no",process_seq_no_list)


    if len(process_seq_no_list) == 0:     # completed


        start_time = datetime.datetime.now().isoformat(" ").split(".")[0]
        cursor.execute(
            """
            UPDATE [TT].[dbo].[Fab_History]
           SET "Completed_Datetime" = ?, Status = 'C'
         WHERE TPL_No = ? and Fab_No = ? and Station_Name = ? """, start_time, tplno, fabno, station_id)
        cursor.commit()

        # store status  station update
        cursor.execute(
            """
            UPDATE [TT].[dbo].[Store_Status]
           SET "Station" = ?
         WHERE TPL_No = ? and Fab_No = ?""",station_id, tplno, fabno)
        cursor.commit()

        if station_id == "Sub3_OP1":
            insert_validate = cursor.execute(
                    "SELECT TPL_No,Fab_No,Station_Name  FROM[TT].[dbo].[Fab_History] WHERE TPL_No = ? AND Fab_No = ? AND ((Station_Name = ?) OR (Station_Name = ?)) "
            ,tplno, fabno,"Sub4_OP1", "Sub4_OP2")

            insert_validate_data = [{
                    "TPL_No": obj[0], "Fab_No": obj[1], "Station_Name": obj[2]
                } for obj in insert_validate]
            print("############################################")
            print("insert validate output",insert_validate_data)
            if len(insert_validate_data) == 0:
                print("######station id", station_id)
                for stations in ['Sub4_OP1', 'Sub4_OP2']:
                    cursor.execute(
                        """ INSERT INTO [TT].[dbo].[Fab_History] (
                         "TPL_No"
                           ,"Fab_No"
                           ,"pd_no"
                           ,"TPL_Description"
                           ,"Start_datetime"
                           ,"Status"
                           ,"Station_Name"
                           ,"Completed_Datetime"
                           ,"Emp_Name"
                           ,"Emp_ID"
                           )VALUES (?,?,?,?,?,?,?,?,?,?)""", tplno, fabno,
                        "", "", "", "P", stations, "", "", "")
                    cursor.commit()
        try:
            agv(tplno, fabno, station_id,"completed")
        except:
            print("no agv reg ")

        # # tower lamp Green/Red
        # tower_lamp(station_id, type="completed", tpl_no=tplno, fab_no=fabno)
        return "seq_complete"



    if len(completed_seq_no_list) == 0:   # starting
        actual_time = "00:00"
        # agv(tplno, fabno, station_id, "start")

        #tower lamp yellow
        tower_lamp(station_id, type = "start")

        if station_id not in ["Sub1_OP1","Sub2_OP1","Sub3_OP1","Sub4_OP1","Sub4_OP2","Ass1_OP1","Ass1_OP2"]:
            insert_validate = cursor.execute(
                "SELECT TPL_No,Fab_No,Station_Name  FROM[TT].[dbo].[Fab_History] WHERE TPL_No = ? AND Fab_No = ? AND Station_Name = ?"
                , tplno, fabno, station_id)

            insert_validate_data = [{
                "TPL_No": obj[0], "Fab_No": obj[1], "Station_Name": obj[2]
            } for obj in insert_validate]
            print("############################################")
            print("insert validate output", insert_validate_data)
            if len(insert_validate_data) == 0:
                cursor.execute(
                    """ INSERT INTO [TT].[dbo].[Fab_History] (
                     "TPL_No"
                       ,"Fab_No"
                       ,"pd_no"
                       ,"TPL_Description"
                       ,"Start_datetime"
                       ,"Status"
                       ,"Station_Name"
                       ,"Completed_Datetime"
                       ,"Emp_Name"
                       ,"Emp_ID"
                       )VALUES (?,?,?,?,?,?,?,?,?,?)""",tplno, fabno,
                    "","", datetime.datetime.now().isoformat(" ").split(".")[0],"P", station_id, "", "", "")
                cursor.commit()
        else:
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Fab_History]
               SET "Start_datetime" = ?
             WHERE TPL_No = ? and Fab_No = ? and Station_Name = ? """,  datetime.datetime.now().isoformat(" ").split(".")[0],
                tplno, fabno, station_id)
            cursor.commit()




    else:
        print("completed_seq_no_list", completed_seq_no_list)

        actual_time_query = """SELECT Actual_Time FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? AND FAB_NO = ? AND Process_Seq_No = ? AND Station_ID = ?"""
        actual_time_list = [obj[0] for obj in cursor.execute(actual_time_query, tplno, fabno, completed_seq_no_list[len(completed_seq_no_list)-1], station_id)]
        actual_time = actual_time_list[0]
        print("Actual Time",actual_time)

    cycle_time = cycle_time_conversion(cursor, fabno, station_id)[0]


    process_seq = cursor.execute(
        """SELECT * FROM [TT].[dbo].[Sub_Station_Screens_Data_View] WHERE TPL_No = ? AND FAB_NO = ? AND Process_Seq_No = ? AND Operator_Code = ? """,tplno, fabno, process_seq_no_list[0], station_id)



    process_seq_list = [{"FAB_NO": obj[0]
                            , "TPL_No": obj[1]
                            , "Operator_Code": obj[2]
                            , "Process_Seq_No": obj[3]
                            , "Pro_Type_Code": obj[4]
                            , "Process_Desc": obj[5]
                            , "Process_Photo_Path": static("images/IMG/Process_Picture/" + str(obj[6]))          #static("images/e.png")  #obj[6]   need changes
                            , "Torque": obj[7]
                            , "Tool_ID": obj[8]
                            , "Tool_Joint": obj[9]
                            , "Takt_Time": obj[10]
                            , "Total_Processes": obj[11]
                            , "Model_Group": obj[12]
                            , "TPL_Description": obj[13]
                         } for obj in process_seq]
    process_seq_list[0].update({"Cycle_Time":cycle_time,"Actual_Time":actual_time,"Completed_Process":len(completed_seq_no_list)})    # need changes
    print("tool obj  ",process_seq_list[0]["Tool_ID"])
    p_loss_levels = P_Q_Levels(cursor, "P_loss")
    q_loss_levels = P_Q_Levels(cursor, "Q_Loss")
    process_seq_list[0].update({"p_loss_levels": p_loss_levels, "q_loss_levels": q_loss_levels})

    if process_seq_list[0]["Pro_Type_Code"] == "CP_CONTROL_PANEL":
        cpdropdown_query = """SELECT Drop_Down_String FROM [TT].[dbo].[CP_Dropdown] WHERE Child_Part_Code = 'CP_CONTROL_PANEL' """
        cpdropdown_list = [obj[0] for obj in cursor.execute(cpdropdown_query)]
        print("cp_dropdown", cpdropdown_list)
        process_seq_list[0].update({"cpdropdown_list":cpdropdown_list})

    if process_seq_list[0]["Pro_Type_Code"] == "CP_VALVE_OTHER":
        cpdropdown_query = """SELECT TOP 1 [IV_No]
                                  ,[AOS_No]
                                  ,[SV_No]
                                  ,[TV_Element]
                                  ,[MPV_No]
                                  ,[OF_No]
                                  ,[Range]
                              FROM [TT].[dbo].[Process_Update_Table]
                              WHERE Process_Code = 'CP_VALVE_OTHER' AND TPL_No = ? AND Fab_No = ? 
                              ORDER BY PMMKEY DESC"""
        cpdropdown_list = [{"IV_No":obj[0], "AOS_No":obj[1], "SV_No":obj[2], "TV_Element":obj[3], "MPV_No":obj[4], "OF_No":obj[5], "Range": obj[6]} for obj in cursor.execute(cpdropdown_query, process_seq_list[0]["TPL_No"], process_seq_list[0]["FAB_NO"])]
        print("cp_dropdown cp valve other...........", cpdropdown_list)
        if cpdropdown_list == []:
            cpdropdown_list = {"IV_No": "", "AOS_No": "", "SV_No": "", "TV_Element": "", "MPV_No": "","OF_No": "", "Range": ""}
            process_seq_list[0].update({"cpdropdown_list": cpdropdown_list})
        else:
            process_seq_list[0].update({"cpdropdown_list":cpdropdown_list[0]})

    if process_seq_list[0]["Pro_Type_Code"] == "CP_BELT_DETAILS":
        cpdropdown_query = """SELECT Drop_Down_String FROM [TT].[dbo].[CP_Dropdown] WHERE Child_Part_Code = 'CP_BELT_DETAILS' """
        cpdropdown_list = [obj[0] for obj in cursor.execute(cpdropdown_query)]
        print("cp_dropdown", cpdropdown_list)
        process_seq_list[0].update({"cpdropdown_list":cpdropdown_list})

    if process_seq_list[0]["Pro_Type_Code"] == "TORQUE":
        print("TOOL_ID  fs", process_seq_list[0]['Tool_ID'][0])
        if process_seq_list[0]['Tool_ID'][0]=="C":
            process_seq_list[0].update({"Tool_Type":"CLECO","card_type":"TORQUE1"})


            # tool enable
            cursor = db_connection()
            print("staion_id ", station_id)
            tool_enable_reg = cursor.execute(
                """ SELECT Tool_Enable FROM [TT].[dbo].[Operator] where Operator_Code = ? """, station_id)
            tool_enable_reg_data = [obj[0] for obj in tool_enable_reg]

            enable_reg = tool_enable_reg_data[0]
            client.write_register(int(enable_reg), 2)

        if process_seq_list[0]['Tool_ID'][0]=="R":
            process_seq_list[0].update({"card_type":"TORQUE2"})


    if process_seq_list[0]["Pro_Type_Code"] == "LEAK_TESTER":
        leak_status = leak_test("process_card")
        print("leak_status", leak_status)
        process_seq_list[0].update(leak_status)
        # process_seq_list[0].update({
        #     "status":{
        #         "leaktester1": "running",
        #         "leaktester2": "available",
        #         "leaktester3": "available",
        #         "leaktester4": "available"
        #     }
        # })

    if process_seq_list[0]["Pro_Type_Code"] == "CP_DRIVE_COUPLING":
        drivecoupling("start",process_seq_list[0]["TPL_No"])

    # print("Process Seq List _ find seq", process_seq_list[0])

    return process_seq_list[0]



def cp_details_check(revno, partno, fabno, cp_name):
    cursor = db_connection()
    result = ""


    print("fab no ", fabno)

    if cp_name == "CP_BELT_TENSION":
        ln_cp_details_query = """SELECT * FROM [TT].[dbo].[LN_CP_Details] WHERE Fab_Number=? AND Child_Part_Code = 'CP_BELT_DETAILS' """

        ln_cp_details = [{
            "avg": obj[18]
        } for obj in cursor.execute(ln_cp_details_query, fabno)]
        print("ln_cp_details ",ln_cp_details)
        min_value = ln_cp_details[0]["avg"][:3]
        max_value = ln_cp_details[0]["avg"][-3:]
        print(min_value, max_value)

        if int(revno) in range(int(min_value), int(max_value)):
            print("data validated")
            result = "data_validated"
            return result
        else:
            result = "Average Not Match"
            print("data  not  validated")
            return result


    else:

        ln_cp_details_query = """SELECT * FROM [TT].[dbo].[LN_CP_Details] WHERE Fab_Number=? AND Child_Part_Code = ?"""

        ln_cp_details = [{
            "Part_No": obj[1],
            "Rev_No": obj[2]
        } for obj in cursor.execute(ln_cp_details_query, fabno, cp_name)]

        if revno == ln_cp_details[0]["Rev_No"] and partno == ln_cp_details[0]["Part_No"]:
            result = "data_validated"
            return result
        elif revno == ln_cp_details[0]["Rev_No"] and partno != ln_cp_details[0]["Part_No"]:
            result = "Part No. not Valid"
            return result
        elif revno != ln_cp_details[0]["Rev_No"] and partno == ln_cp_details[0]["Part_No"]:
            result = "Rev No. not Valid"
            return result
        else:
            result = "Part No. and Rev No. not Valid"
            return result

    # print("result", result)
    # return result

def actual_time_convertion(actual_time):
    min = int(actual_time.split(":")[0])
    sec = int(actual_time.split(":")[1])
    total_sec = (min*60) + sec
    return total_sec

def cycle_time_conversion(cursor, fabno, station_id):
    try:
        print("Fab no, station id", fabno, station_id)
        cycle_time_query = cursor.execute(
            """SELECT  SUM(Takt_Time) FROM [TT].[dbo].[Sub_Station_Screens_Data_View]
                where FAB_NO = ? and Operator_Code = ? """, fabno, station_id
        )

        total_sec = [obj[0] for obj in cycle_time_query]
        print("Total seccccc", total_sec, type(total_sec[0]))
        minutes = total_sec[0] // 60
        secs = total_sec[0] % 60
        cycle_time = str(minutes).zfill(2) + ":" + str(secs).zfill(2)

        cycle_time_secs = actual_time_convertion(cycle_time)
        print("cycle time ", cycle_time,cycle_time_secs)
        return [cycle_time, cycle_time_secs]
    except:
        return ["00:00","0"]


def process_validate_api(type, fabno, tplno, empname, empid, process_seqno, process_code, process_data, actual_time, station_id):
    cursor = db_connection()
    result = ""

    if type == "process_skip":
        process_data = ast.literal_eval(process_data)
        # print("process data", type(process_data))

        cursor.execute(
            "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Actual_Time],[Process_Status],[Station_ID],[Process_Desc],[Skip_Reason],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?)",
            tplno, fabno, empname, empid, process_seqno,
            process_code,actual_time, "S",station_id, process_data["process_desc"], process_data["process_skip_reason"],actual_time_convertion(actual_time))
        cursor.commit()
        cursor.close()

        # tower lamp Red
        tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

        return "process_skip"

    if type == "unit_skip":
        process_data = ast.literal_eval(process_data)
        completed_seq_no_query = """ SELECT Process_Seq_No FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? AND Fab_No = ? AND Station_ID = ? ORDER BY Process_Seq_No ASC """
        completed_seq_no_list = [obj[0] for obj in cursor.execute(completed_seq_no_query, tplno, fabno,station_id)]
        process_seq_no_query = """SELECT Process_Seq_No FROM [TT].[dbo].[Sub_Station_Screens_Data_View] WHERE TPL_No = ? AND FAB_NO = ? AND Operator_Code = ?  ORDER BY Process_Seq_No ASC"""
        process_seq_no_list = [obj[0] for obj in cursor.execute(process_seq_no_query, tplno, fabno, station_id)]
        print("seq_no lists", completed_seq_no_list, process_seq_no_list)

        for i in completed_seq_no_list:
            if i in process_seq_no_list:
                process_seq_no_list.remove(i)
        print("present seq_no in process validate", process_seq_no_list)

        for i in process_seq_no_list:
            print("**********",i)
            seq_details = cursor.execute(
                """ SELECT Process_Seq_No, Pro_Type_Code, Process_Desc FROM [TT].[dbo].[Sub_Station_Screens_Data_View] WHERE Process_Seq_No = ? AND FAB_NO = ? AND TPL_No = ? AND Operator_Code = ?"""
                , i, fabno, tplno, station_id)
            seq_data = [{"Process_Seq_No": obj[0], "Pro_Type_Code": obj[1], "Process_Desc": obj[2]} for obj in seq_details]

            cursor.execute(
                        "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Actual_Time],[Process_Code],[Process_Status],[Station_ID],[Process_Desc],[Skip_Reason],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?)",
                        tplno, fabno,
                        empname, empid, i,actual_time,
                        seq_data[0]["Pro_Type_Code"], "S",station_id, seq_data[0]["Process_Desc"], process_data["unit_skip_reason"],actual_time_convertion(actual_time))
            cursor.commit()

            # tower lamp Red
            tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

        # for i in process_seq_no_list:
        #     cursor.execute(
        #         "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Process_Status],[Station_ID],[Process_Desc],[Skip_Reason]) values (?,?,?,?,?,?,?,?,?,?)",
        #         tplno, fabno,
        #         empname, empid, i,
        #         process_code, "S",station_id, process_data["process_desc"], process_data["unit_skip_reason"] )
        #     cursor.commit()
        # cursor.close()
        return "unit_skip"


    if type == "validate":
        if "CP_AIREND" == process_code or "CP_CANOPY" == process_code:
            process_data = ast.literal_eval(process_data)
            print("process_data", process_data)
            #print("process_data", type(process_data))
            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]

            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result
        elif "CP_CONTROL_PANEL" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            model = process_data["model"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Model],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,model,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result
        elif "CP_COOLER" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result
        elif "CP_BELT_DETAILS" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            batchone = process_data["beltdetails_bone"]
            batchtwo = process_data["beltdetails_btwo"]
            batchthree = process_data["beltdetails_bthree"]
            make = process_data["beltdetails_make"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[BeltDetails_Batchone],[BeltDetails_Batchtwo],[BeltDetails_Batchthree],[BeltDetails_Make],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno,batchone, batchtwo, batchthree, make, actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result
        elif "CP_DRIVE_PULLEY" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result
        elif "CP_DRIVEN_PULLEY" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_DRYER" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_FAN_MOTOR" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            kw = process_data["fanmotor_kw"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[FANMOTOR_kw],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,kw,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_MOTOR" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            motor_efficiency = process_data["motor_efficiency"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Motor_Efficency],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,motor_efficiency,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_NEURON" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_VFD" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_TANK" == process_code:
            process_data = ast.literal_eval(process_data)
            #print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]
            cp_details_result = cp_details_check(revno, partno, fabno, process_code)

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, partno, revno, serialno,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "SUBMIT" == process_code:
            process_data = process_data
            #print("process_data", type(process_data))
            #submit = process_data["SUBMIT"]
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[SUBMIT],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, process_code,actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "TORQUE" == process_code:
            process_data = ast.literal_eval(process_data)
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Tool_ID],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code,process_data["Tool_ID"],actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()


                if process_data["Tool_ID"][0] == 'C':
                    cursor = db_connection()
                    print("staion_id ",station_id)
                    tool_enable_reg = cursor.execute(""" SELECT Tool_Enable FROM [TT].[dbo].[Operator] where Operator_Code = ? """, station_id)
                    tool_enable_reg_data = [obj[0] for obj in tool_enable_reg]

                    enable_reg = tool_enable_reg_data[0]
                    client.write_register(int(enable_reg), 0)



                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "LEAK_TESTER" == process_code:
            process_data = ast.literal_eval(process_data)

            print("Leak TEST UPDATED")
            #print("process_data", type(process_data))
            #submit = process_data["SUBMIT"]
            unit = process_data["assign"]
            print("unit" ,unit)
            # print("unit" ,type(unit)))
            leak_selected = leak_test("selection",int(unit[-1]))
            cursor.execute( """
                UPDATE [TT].[dbo].[Leaktest_Details]
                SET "TPL_No" = ?
                ,"FAB_NO" = ?
                ,"Station_ID" = ?
                WHERE Leak_Devices = ? """,tplno,fabno,station_id,int(unit[-1]))
            cursor.commit()

            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":

                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[LeakTester_Unit],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, unit[-1],actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)
                leak_tower_lamp(int(unit[-1]),"start")



            return cp_details_result
        elif "CP_DRIVE_COUPLING" == process_code:
            process_data = ast.literal_eval(process_data)
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[sensor_selected],[specification],[sensor_live_value],[sensor_reached],[correction],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,empname, empid,process_seqno,process_code,
                    process_data["sensor_selected"], process_data["specification"], process_data["sensor_live_value"], process_data["sensor_reached"],
                    process_data["correction"],actual_time, "C",station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_VALVE_OTHER" == process_code:
            process_data = ast.literal_eval(process_data)
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[IV_No],[AOS_No],[SV_No],[TV_Element],[MPV_No],[OF_No],[Range],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,empname, empid,process_seqno,process_code,
                    process_data["IV_No"], process_data["AOS_No"], process_data["SV_No"], process_data["TV_Element"],
                    process_data["MPV_No"], process_data["OF_No"], process_data["Range"],actual_time, "C",station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "CP_AIREND_CHECK" == process_code or "CP_COOLER_CHECK" == process_code or "CP_DRYER_CHECK" == process_code or "CP_FAN_MOTOR_CHECK" == process_code or "CP_MOTOR_CHECK" == process_code or "CP_VFD_CHECK" == process_code or "CP_TANK_CHECK" == process_code :
            process_data = ast.literal_eval(process_data)
            print("process_data", process_data)
            # print("process_data", type(process_data))

            partno = process_data["Partno"]
            revno = process_data["Revno"]
            serialno = process_data["Serialno"]

            airend_query = """ SELECT [Part_No],[Rev_No],[Serial_No] FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No= ? and  Fab_No = ? and Process_Code = ? """
            cpdetails_list = [{
                "PartNo": obj[0],
                "RevNo": obj[1],
                "Serial": obj[2]
            } for obj in cursor.execute(airend_query, tplno, fabno, process_code[:-6])]
            if partno == cpdetails_list[0]["PartNo"] and revno == cpdetails_list[0]["RevNo"] and serialno == cpdetails_list[0]["Serial"]:
                cp_details_result = "data_validated"
            else:
                cp_details_result = "Details not matching with " + process_code

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Part_No],[Rev_No],[Serial_No],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid, process_seqno,
                    process_code, partno, revno, serialno, actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif "PDI_Image_Capture" == process_code :
            process_data = ast.literal_eval(process_data)
            base64_string = process_data['img_url']
            # data = base64.b64decode(base64_string.split(',')[1])

            # img = Image.open(BytesIO(data))
            # img.show()
            static_path = os.path.join(settings.BASE_DIR, 'ELGI_App', 'static/images/IMG/PDI_Pictures')
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            file_name = str(fabno) + "_" + current_time + ".png"
            print(file_name)
            # img.save(os.path.join(static_path, file_name))
            cp_details_result = "data_validated"
            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[PDI_Image_URL],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, file_name, actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)



            return cp_details_result
        elif "PDI_Scan" == process_code:
            process_data = ast.literal_eval(process_data)
            qr_data = process_data["qr_data"]
            cp_details_result = "data_validated"
            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[PDI_Scan_Data],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,process_seqno,
                    process_code, qr_data, actual_time, "C", station_id,actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)



                # tower lamp Red
                tower_lamp(station_id, type="completed", tpl_no=tplno, fab_no=fabno)


            return cp_details_result
        elif  "CP_BELT_TENSION" == process_code:
            process_data = ast.literal_eval(process_data)
            print("process_data", process_data)
            # print("process_data", type(process_data))
            # assuming we have to store only avg value in the process update table if we have to store all the vaules.
            test1 = process_data["test1"]
            test2 = process_data["test2"]
            test3 = process_data["test3"]
            test4 = process_data["test4"]
            avg = process_data["avg"]
            #Compare the data from avg coming from front end with LN Details

            cp_details_result = cp_details_check(avg, 0, fabno, process_code)

            print("--------------------- cp belt tension result ", cp_details_result)
            # cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Process_Seq_No],[Process_Code],[Test_1],[Test_2],[Test_3],[Test_4],[Test_Avg],[Actual_Time],[Process_Status],[Station_ID],[Actual_Time_Sec]) values (?,?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid, process_seqno,
                    process_code, test1, test2, test3, test4, avg, actual_time, "C", station_id,
                    actual_time_convertion(actual_time))
                cursor.commit()
                cursor.close()

                # tower lamp Red
                tower_lamp(station_id, type="loss", tpl_no=tplno, fab_no=fabno)

            return cp_details_result



@csrf_exempt
def substation_api(request):
    cursor = db_connection()
    if request.method == "POST":
        print("****************************** substation api")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))
        print("****************************** substation api")

    if request.method=="POST" and "process_submit"==request.POST["method"]:
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        process_seqno = request.POST["Process_Seq_No"]
        process_code = request.POST["Pro_Type_Code"]
        process_data = request.POST["process_data"]
        actual_time = request.POST["Actual_Time"]
        station_id = request.POST["station_id"]


        cursor.execute("""SELECT * FROM [TT].[dbo].[Process_Update_Table] WHERE Process_Seq_No=? AND Fab_No = ? AND TPL_No = ? AND Station_ID = ?""", process_seqno, fabno, tplno, station_id)
        process_code_check = cursor.fetchall()
        print("process code check", process_code_check)
        if len(process_code_check) != 0:
            result =  "process_complete"
        else:
            print("----------------------------------------------------------------")
            print("----------------------------------------------------------------")
            print("process data " , process_data)
            result = process_validate_api("validate", fabno, tplno, empname, empid, process_seqno, process_code, process_data, actual_time, station_id)

        if result == "data_validated":
            process_seq_data = finding_seq(station_id, tplno, fabno)
            json_data = {
                "process_validation":"Success",
                "process_seq": process_seq_data
            }
            return JsonResponse(json_data)
        elif result == "process_complete":
            process_seq_data = finding_seq(station_id, tplno, fabno)
            json_data = {
                "process_validation": "process_complete",
                "process_seq": process_seq_data
            }
            return JsonResponse(json_data)
        else:
            json_data = {
                "process_validation": "Fail",
                "Message":result
            }
            return JsonResponse(json_data)
    if request.method=="POST" and "process_seq"==request.POST["method"]:
        tplno = request.POST["Tpl_No"]
        fabno = request.POST["Fab_No"]
        station_id = request.POST["station_id"]

        print('station_id', station_id)

        process_seq_data = finding_seq(station_id, tplno, fabno)   # need Changes
        json_data = {
            "process_seq": process_seq_data
        }
        return JsonResponse(json_data)
    if request.method == "POST" and "unit_skip" == request.POST["method"]:
        print("unit skippppppppppppppppp")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        process_seqno = request.POST["Process_Seq_No"]
        process_code = request.POST["Pro_Type_Code"]
        process_data = request.POST["process_data"]
        actual_time = request.POST["Actual_Time"]
        station_id = request.POST["station_id"]

        result = process_validate_api("unit_skip", fabno, tplno, empname, empid, process_seqno, process_code, process_data, actual_time,station_id)

        if result == "unit_skip":
            process_seq_data = finding_seq(station_id, tplno, fabno)
            json_data = {
                "process_validation": "unit_skip",
                "process_seq": process_seq_data
            }
            return JsonResponse(json_data)
    if request.method == "POST" and "process_skip" == request.POST["method"]:
        print("process skip")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        process_seqno = request.POST["Process_Seq_No"]
        process_code = request.POST["Pro_Type_Code"]
        process_data = request.POST["process_data"]
        actual_time = request.POST["Actual_Time"]
        station_id = request.POST["station_id"]

        result = process_validate_api("process_skip", fabno, tplno, empname, empid, process_seqno, process_code,
                                      process_data, actual_time,station_id)

        if result == "process_skip":
            process_seq_data = finding_seq(station_id, tplno, fabno)
            json_data = {
                "process_validation": "process_skip",
                "process_seq": process_seq_data
            }
            return JsonResponse(json_data)
    if request.method == "POST" and "p_loss" == request.POST["method"]:
        print("p loss")
        result = P_Loss(cursor, request)
        print("result", result)
        json_data = {
            "method": "p_loss",
            "status": result
        }
        return JsonResponse(json_data)
    if request.method == "POST" and "q_loss" == request.POST["method"]:
        print("q loss")
        process_data = ast.literal_eval(request.POST["process_data"])

        if request.method == "POST":
            print("******************************")
            for key, value in request.POST.items():
                print('Key: %s' % (key))
                print('Value %s' % (value))

        if process_data["type"] == "create":
            result = Q_Loss(cursor, request, "create")
            json_data = {
                "method": "q_loss",
                "status": result["response"],
                "DMS_ID":result["DMS_ID"]
            }
            return JsonResponse(json_data)
        if process_data["type"] == "update":
            result = Q_Loss(cursor, request, "update")
            json_data = {
                "method": "q_loss",
                "status": result["response"]
            }
            return JsonResponse(json_data)

    if request.method == "POST" and "retest_leak" == request.POST["method"]:
        print("callingn leak retest")
        lfabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        unit = request.POST["unit"]
        print("unit in substationapi ", unit[-1])
        leak_test("retest_leak",unit[-1])

    if request.method == "POST" and "skip_leak" == request.POST["method"]:
        print("callingn skip retest")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        unit = request.POST["unit"]
        print("unit in substationapi ", unit[-1])
        leak_test("skip_leak", unit[-1])


    if request.method == "POST" and "status_list" == request.POST["method"]:
        json_data = leak_test("leak_status")
        print(json_data)
        print("leak test status list")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]

        # json_data = [
        #     {
        #         "FabNo": "AUHC373514",
        #         "TplNo": "tpl13",
        #         "leaktesterno": "Leak Tester 01",
        #         "SationID": "SS1",
        #         "TesterStatus": "available",
        #         "TestStatus": "available"
        #     },
        #     {
        #         "FabNo": "AUHC373514",
        #         "TplNo": "tpl13",
        #         "leaktesterno": "Leak Tester 02",
        #         "SationID": "SS1",
        #         "TesterStatus": "available",
        #         "TestStatus": "available"
        #     },
        #     {
        #         "FabNo": "AUHC373514",
        #         "TplNo": "tpl13",
        #         "leaktesterno": "Leak Tester 03",
        #         "SationID": "SS1",
        #         "TesterStatus": "available",
        #         "TestStatus": "available"
        #     },
        #     {
        #         "FabNo": "AUHC373514",
        #         "TplNo": "tpl13",
        #         "leaktesterno": "Leak Tester 04",
        #         "SationID": "SS1",
        #         "TesterStatus": "available",
        #         "TestStatus": "available"
        #     }
        # ]
        return JsonResponse({"list":json_data})
    if request.method == "POST" and "status_leaktester" == request.POST["method"]:
        print("leak test status list")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        unit = request.POST["unit"]
        print("unit in substationapi ", unit[-1])
        json_data = leak_test("leak_tester",unit[-1])
        print("json data ",json_data)
        # json_data = {
        #     "initial_pressure":"6.18",
        #     "pressure_after_stabilization":"6.09",
        #     "allowable_final_pressure":"6.08",
        #     "allowable_pressure_drop":"0.030",
        #     "actual_pressure_drop":"0.010",
        #     "status":"Pass",
        #     "Leak_Testing_Timer":"20",
        # }
        return JsonResponse(json_data)
    print("-------------------****************************-------------- ",request.POST["method"])
    if request.method == "POST" and "status_setting" == request.POST["method"]:
        print("leak test setting")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        unit = request.POST["unit"]
        json_data = leak_test("status_setting", unit[-1])
        # json_data = {
        #     "pressure_specification":"50",
        #     "stabilization_timer":"30",
        #     "Leak_Testing_Timer":"60",
        # }
        return JsonResponse(json_data)
    if request.method == "POST" and "status_setting_update" == request.POST["method"]:
        print("leak test setting")
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        unit = request.POST["unit"]
        json_data = leak_test("status_setting_update",unit[-1],request.POST["pressure_specification"], request.POST["stabilization_timer"], request.POST["Leak_Testing_Timer"]  )
        # if "pressure_specification" in request.POST and "stabilization_timer" in request.POST and "Leak_Testing_Timer" in request.POST:
        #     pressure_specification = request.POST["pressure_specification"]
        #     stabilization_timer = request.POST["stabilization_timer"]
        #     Leak_Testing_Timer = request.POST["Leak_Testing_Timer"]
        #
        #     json_data = {
        #         "status":"updated"
        #     }
        # else:
        #     json_data = {
        #         "status": "parameters_missing"
        #     }
        print(json_data)
        return JsonResponse(json_data)

    return HttpResponse("SUBSTATION API")


def info_button(station_id):
    cursor = db_connection()
    info_details = cursor.execute(
        "SELECT Message_Type, Data_File FROM Msg_info "
        "where Station_Code = ? ", station_id
    )

    info_details_data = [{"Message_Type" : obj[0], "Data_File": obj[1],"pdf_url" : static("images/IMG/Information_Data/" + obj[1])}
                         for obj in info_details]

    return  info_details_data





@csrf_exempt
def torque_api(request):
    cursor = db_connection()
    print("TORQUE API")
    print("POST DATAAA",request.POST)

    # if request.POST["Tool_ID"][0] == 'C':
    #     cursor = db_connection()
    #     print("staion_id ", request.POST["station_id"])
    #     tool_enable_reg = cursor.execute(""" SELECT Tool_Enable FROM [TT].[dbo].[Operator] where Operator_Code = ? """,
    #                                      station_id)
    #     tool_enable_reg_data = [obj[0] for obj in tool_enable_reg]
    #
    #     enable_reg = tool_enable_reg_data[0]
    #     client.write_register(int(enable_reg), 0)

    if request.method=="POST" and "torque_status"==request.POST["method"]:
        fabno = request.POST["FAB_NO"]
        tplno = request.POST["TPL_No"]
        empname = request.POST["Emp_Name"]
        empid = request.POST["Emp_ID"]
        process_seqno = request.POST["Process_Seq_No"]
        process_code = request.POST["Pro_Type_Code"]
        #process_data = json.loads(request.POST["process_data"])
        process_data = ast.literal_eval(request.POST["process_data"])
        card_type = request.POST["card_type"]
        actual_time = request.POST["Actual_Time"]
        station_id = request.POST["station_id"]
        print("card_type",card_type)
        print("****************************************")
        print("****************************************")
        print("****************************************")
        print("station_id",station_id)

        required_torque_query = """SELECT [Torque]
          FROM [TT].[dbo].[Sub_Station_Screens_Data_View]
          WHERE FAB_No = ? and TPL_No = ? and Operator_Code = ? and Tool_ID = ? and Process_Seq_No = ? """
        required_torque = [obj[0] for obj in cursor.execute(required_torque_query, fabno, tplno, station_id, process_data["Tool_ID"], process_seqno)]


        if card_type == "TORQUE1":
            print("Torque1")
            json_data = cleco_tool(station_id,process_data["Tool_ID"], required_torque[0])

            # json_data = {
            # "connection_status":"Active",
            # "tool_connection": "Offline",
            # "app_status":"Matched",
            # "tool_status":"Enabled",
            # "tool_working":"Stop",
            # "tool_output":"Pass",
            # "actual_torque":10.2,
            # "required_torque":10
            # }
            #
            return JsonResponse(json_data)
        elif card_type == "TORQUE2":
            # station_id = "Ass4_OP2"
            print("-------------------------------------------")
            print("process_data tool_id ", process_data)
            print("process_data tool_id ", process_data["Tool_ID"])
            station_id = request.POST["station_id"]
            print("station id ", station_id)
            json_data = digital_tool(station_id,process_data["Tool_ID"])
            print("json_dataaa", json_data)
            # json_data = {
            #     "connection_status": "Active",
            #     "tool_output": "Pass",
            # }
            return JsonResponse(json_data)
        else:
            json_data = {
                "connection_status":"Inactive"
            }
            return JsonResponse(json_data)

@csrf_exempt
def drive_coupling_api(request):
    if request.method == "POST":
        TPL_No = request.POST["TPL_No"]
        json_data = drivecoupling("status", TPL_No)
        # json_data = {
        #     "sensor_selected": "AP01",
        #     "specification": 150,
        #     "sensor_live_value": 150,
        #     "sensor_reached": 135,
        #     "status":"complete"
        # }
        return JsonResponse(json_data)

@csrf_exempt
def qloss_api(request):
    print("qloss_api")
    cursor = db_connection()

    # if request.method == 'POST':
    #     print("*********************")
    #     print(request.POST)

    if request.method == "POST" and "q_loss" == request.POST["method"]:
        print("*********************")
        print(request.POST)
        result = Q_Loss(cursor, request, "status")
        if result["response"] == "C":
            status  = "completed"
        else:
            status = "inprogress"
        # result["response"]
        json_data = {
            "method": "q_loss",
            "status": status
        }

        return JsonResponse(json_data)
    return JsonResponse("Q Loss p")

# station interlocks
def station_interlock_check(station_id,tpl_no, fab_no):
    cursor = db_connection()
    print("--------------------------------------------------")
    print('station_id  in station interlocks ',station_id)

    stations = ['Store','Sub1_OP1','Sub2_OP1','Sub3_OP1','Sub4_OP1','Sub4_OP2','Ass1_OP1','Ass1_OP2','Ass2_OP1','Ass2_OP2','Ass3_OP1','Ass3_OP2','Ass4_OP1','Ass4_OP2'
                ,'Ass5_OP1','Ass5_OP2','Ass6_OP1','Ass6_OP2','Ass7_OP1','Ass7_OP2','Ass8_OP1','Ass8_OP2','Ass9_OP1','Ass9_OP2','Ass10_OP1','Ass10_OP2','Ass11_OP1','Ass11_OP2', 'PDI_P1_OP1','PD1_I1_OP1','Packing1_OP1']
    current_station_index = stations.index(station_id)
    print("current_station_index ",current_station_index)

    bypass_stations = cursor.execute(
        """ SELECT Station_ID
        FROM [TT].[dbo].[Station_Bypass] where Bypass = 'Bypass' """)
    bypass_stations_list = [obj[0] for obj in bypass_stations]

    # [stations.remove(i) for i in bypass_stations_list]
    print("bypass_stations_list ",bypass_stations_list)

    if current_station_index in [1, 2, 3, 6, 7]:
        actual_seq = ['Store']
        print("actual_seq ", actual_seq)

    elif ((current_station_index == 4) or (current_station_index == 5)):
        actual_seq = ["Store","Sub3_OP1"]
        print("actual_seq ", actual_seq)


    elif ((current_station_index > 7) and (current_station_index % 2 == 0)):
        actual_seq = [stations[i] for i in range(0,current_station_index)]
        print("actual_seq ",actual_seq)

    elif ((current_station_index > 7) and (current_station_index % 2 != 0)):
        actual_seq = [stations[i] for i in range(0,current_station_index - 1)]
        print("actual_seq ",actual_seq)



    completed_stations = cursor.execute(
        """ SELECT Station_Name
        FROM [TT].[dbo].[Fab_History] where TPL_NO = ? and Fab_No = ? and Status = ? """, tpl_no, fab_no, 'C')
    completed_stations_list = [obj[0] for obj in completed_stations]
    print("completed_stations_list ", completed_stations_list)

    completed_stations_list.extend(bypass_stations_list)
    print("completed stations extend ", completed_stations_list)

    missed_stations = []
    for station in actual_seq:
        if station not in completed_stations_list:
            missed_stations.append(station)
    print(missed_stations)

    if len(missed_stations) == 0:
        print(True)
        return True
    else:
        print(False , missed_stations)
        return missed_stations

def skipped_process(tpl_no,fab_no):
    cursor = db_connection()

    skipped_process_details = cursor.execute(
        "SELECT Station_ID,Process_Desc,Skip_Reason FROM[TT].[dbo].[Process_Update_Table]"
        "WHERE TPL_No = ? and Fab_No = ? and Process_Status = ?", tpl_no, fab_no, 'S')
    skipped_process_list = [{"station":obj[0], "Process_Desc":obj[1], "reason":obj[2]} for obj in skipped_process_details]

    return skipped_process_list


@permission_required('ELGI_App.supervisor_view', login_url = 'no_access')
@login_required(login_url='login')
def pdi_master(request):
    cursor = db_connection()

    if request.method == "POST":
        print("******************************")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))

        if request.POST["submit"] == "L_Add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[PDI_CL_Library] (
            		"CL_Code"
                  ,"CL_Type_Code"
                  ,"Check_List_description"
                  ,"OK_Photo_Path"
                  ,"NOT_OK_Photo_Path"
                  ,"Sample_Image_Capture"
                  ,"Line_Code"
                  ,"Tack_Time"
                  )VALUES (?,?,?,?,?,?,?,?)""", request.POST["cl_code"], request.POST["cl_type_code"], request.POST["cl_description"],
                    request.POST["ok_img"], request.POST["not_ok_img"],
                    request.POST["guide_img"],"EL1_P1_L1",request.POST["takt_time"])
            cursor.commit()



        elif request.POST["submit"] == "L_Modify":
            cursor.execute(
                """ UPDATE [TT].[dbo].[PDI_CL_Library]
               SET "CL_Type_Code" = ?
                  ,"Check_List_description" = ?
                  ,"OK_Photo_Path" = ?
                  ,"NOT_OK_Photo_Path" = ?
                  ,"Sample_Image_Capture" = ? 
                  ,"Line_Code" = ?
                  ,"Tack_Time" = ?
             WHERE CL_Code = ?""",  request.POST["cl_type_code"], request.POST["cl_description"],
                request.POST["ok_img"],request.POST["not_ok_img"],request.POST["guide_img"],
                "EL1_P1_L1", request.POST["takt_time"],request.POST["cl_code"])
            cursor.commit()

        elif request.POST["submit"] == "L_Delete":
            cursor.execute(
                """ DELETE FROM [TT].[dbo].[PDI_CL_Library]
                WHERE CL_Code = ?""",request.POST["cl_code"])
            cursor.commit()


        elif request.POST["submit"] == "PM_Add":
            cursor.execute(
                """ INSERT INTO [TT].[dbo].[PDI_Master_Mapping] (
            		    "TPL_No"
                      ,"PDI_CL_Code"
                      ,"Order_No"
                      ,"Line_Code"
                  )VALUES (?,?,?,?)""", request.POST["tpl_no"], request.POST["cl_code_master"],
                request.POST["order_no"],"EL1_P1_L1")
            cursor.commit()



        elif request.POST["submit"] == "PM_Modify":
            cursor.execute(
                """ UPDATE [TT].[dbo].[PDI_Master_Mapping]
               SET "TPL_No" = ?
                      ,"PDI_CL_Code" = ?
                      ,"Order_No" = ?
                      ,"Line_Code" = ?
             WHERE PMMKEY = ?""", request.POST["tpl_no"], request.POST["cl_code_master"], request.POST["order_no"],
                "EL1_P1_L1",request.POST["PMMKEY"])
            cursor.commit()


        elif request.POST["submit"] == "PM_Delete":
            cursor.execute(
                """ DELETE FROM [TT].[dbo].[PDI_Master_Mapping]
                WHERE PMMKEY = ?""", request.POST["PMMKEY"])
            cursor.commit()



    tpl_no_details = cursor.execute(
        "SELECT TPL_No FROM[TT].[dbo].[TPL_Master]")
    tpl_no_data = [obj[0] for obj in tpl_no_details]

    cl_code_details = cursor.execute(
        "SELECT CL_Code FROM[TT].[dbo].[PDI_CL_Library]")
    cl_code_data = [obj[0] for obj in cl_code_details]


    pdi_library_details = cursor.execute(
        "SELECT * FROM[TT].[dbo].[PDI_CL_Library]")

    pdi_library_data = [{
        "CL_Code": obj[0], "CL_Type_Code": obj[1], "Check_List_description": obj[2],
        "OK_Photo_Path": obj[3], "NOT_OK_Photo_Path": obj[4],
        "Sample_Image_Capture": obj[5], "Line_Code": obj[6], "Tack_Time": obj[7]
    } for obj in pdi_library_details]
    # print(pdi_master_data)

    pdi_master_details = cursor.execute(
        "SELECT * FROM [TT].[dbo].[PDI_CL_Map_Master]")

    pdi_master_data = [{
        "PMMKEY": obj[0], "TPL_No": obj[1], "PDI_CL_Code": obj[2], "Order_No": obj[3], "Line_Code": obj[4]
    } for obj in pdi_master_details]

    cursor.close()
    return render(request, 'pdi_master.html',
                  {"pdi_library_data": pdi_library_data, "pdi_master_data": pdi_master_data, "tpl_no_data":tpl_no_data, "cl_code_data":cl_code_data})
@login_required(login_url='login')
def pdi_inspection_process(request, tplno, fabno):
    cursor = db_connection()
    process_seq_list = []
    # user_name = "100213"
    user_name = str(request.user)
    if request.method == 'POST':
        print("*********************")

        print(request.POST)

    # print("***************************************************")
    # print("station id in substation fn", station_id)
    # missed_stations = station_interlock_check(station_id, tplno, fabno)
    # print("missed_Stations in substation ", missed_stations)

    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Photo_Path": static("images/users/" + str(obj[2]))
    } for obj in cursor.execute(employee_details_query, user_name)]

    employee_skill_query = """ SELECT Sub5_OP1 FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
    employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_name)]
    Skill_Level = employee_skill_list[0][0]
    employee_details_list[0].update({"Skill_Level": Skill_Level})

    process_seq_data = pdi_finding_seq(tplno, fabno)

    if process_seq_data == "seq_complete":
        return redirect(station_order_release, station_id='PDI_I1_OP1')

    file_info = info_button('PDI_I1_OP1')
    skip_processes = skipped_process(tplno, fabno)
    if len(skip_processes) == 0:
        popup_status = "hide"
    else:
        popup_status = "show"

    json_data = {
        "process_type": process_seq_data["CL_Type_Code"],
        "employee_details": {
            "Emp_Name": employee_details_list[0]["Emp_Name"],
            "Emp_ID": employee_details_list[0]["Emp_ID"],
            "Skill_level": employee_details_list[0]["Skill_Level"],
            "Photo_Path": employee_details_list[0]["Photo_Path"],
        },
        "process_seq": process_seq_data,
        "popup_status": "hide",
        "file_info": file_info,
        "skiped_popup": popup_status,
        "skiped_process": skip_processes
    }

    # print("final josn", json_data)
    return render(request, 'pdi_inspection_process.html', json_data)

@csrf_exempt
def pdi_inspection_api(request):
    cursor = db_connection()
    json_data = {}
    if request.method == "POST":
        print("****************************** pdi inspection api")
        for key, value in request.POST.items():
            print('Key: %s' % (key))
            print('Value %s' % (value))
        if request.method == "POST" and "process_submit" == request.POST["method"]:
            fabno = request.POST["FAB_NO"]
            tplno = request.POST["TPL_No"]
            empname = request.POST["Emp_Name"]
            empid = request.POST["Emp_ID"]
            Order_No = request.POST["Order_No"]
            CL_Type_Code = request.POST["CL_Type_Code"]
            process_data = request.POST["process_data"]
            actual_time = request.POST["Actual_Time"]
            station_id = request.POST["station_id"]

            cursor.execute(
                """SELECT * FROM [TT].[dbo].[PDI_Process_Update_Table] WHERE Order_Number=? AND Fab_No = ? AND TPL_No = ? AND Station_id = ?""",
                Order_No, fabno, tplno, station_id)
            process_code_check = cursor.fetchall()
            print("process code check", process_code_check)
            if len(process_code_check) != 0:
                result = "process_complete"
            else:
                result = pdi_process_validate_api("validate", fabno, tplno, empname, empid, Order_No, CL_Type_Code,process_data, actual_time, station_id)

            if result == "data_validated":
                process_seq_data = pdi_finding_seq(tplno, fabno)
                json_data = {
                    "process_validation": "Success",
                    "process_seq": process_seq_data
                }
                return JsonResponse(json_data)
            elif result == "process_complete":
                process_seq_data = pdi_finding_seq(tplno, fabno)
                json_data = {
                    "process_validation": "process_complete",
                    "process_seq": process_seq_data
                }
                return JsonResponse(json_data)
            else:
                json_data = {
                    "process_validation": "Fail",
                    "Message": result
                }
                return JsonResponse(json_data)

        if request.method == "POST" and "process_seq" == request.POST["method"]:
            tplno = request.POST["Tpl_No"]
            fabno = request.POST["Fab_No"]
            # station_id = request.POST["station_id"]



            process_seq_data = pdi_finding_seq(tplno, fabno)  # need Changes
            json_data = {
                "process_seq": process_seq_data
            }
        return JsonResponse(json_data)
    cursor.close()
    return HttpResponse("PDI_Inspection")

def pdi_finding_seq(tplno, fabno):
    cursor = db_connection()

    completed_seq_no_query = """ SELECT Order_Number FROM [TT].[dbo].[PDI_Process_Update_Table] WHERE TPL_No = ? AND Fab_No = ? AND Station_id = ? ORDER BY Order_Number ASC """
    completed_seq_no_list = [obj[0] for obj in cursor.execute(completed_seq_no_query, tplno, fabno, 'PDI_I1_OP1')]
    process_seq_no_query = """SELECT Order_No FROM [TT].[dbo].[PDI_Insp_Data_View] WHERE TPL_No = ? AND FAB_NO = ? ORDER BY Order_No ASC"""
    process_seq_no_list = [obj[0] for obj in cursor.execute(process_seq_no_query, tplno, fabno)]
    print("seq_no lists", completed_seq_no_list, process_seq_no_list, 'PDI_I1_OP1', tplno, fabno)

    for i in completed_seq_no_list:  # need change
        if i in process_seq_no_list:
            process_seq_no_list.remove(i)
    print("present seq_no", process_seq_no_list)

    if len(process_seq_no_list) == 0:  # completed



        start_time = datetime.datetime.now().isoformat(" ").split(".")[0]
        cursor.execute(
            """
            UPDATE [TT].[dbo].[Fab_History]
           SET "Completed_Datetime" = ?, Status = 'C'
         WHERE TPL_No = ? and Fab_No = ? and Station_Name = ? """, start_time, tplno, fabno, 'PDI_I1_OP1')
        cursor.commit()

        # store status  station update
        cursor.execute(
            """
            UPDATE [TT].[dbo].[Store_Status]
           SET "Station" = ?
         WHERE TPL_No = ? and Fab_No = ?""", 'PDI_I1_OP1', tplno, fabno)
        cursor.commit()
        return "seq_complete"

    if len(completed_seq_no_list) == 0:  # starting
        actual_time = "00:00"
        if 'PDI_I1_OP1' not in ["Sub1_OP1", "Sub2_OP1", "Sub3_OP1", "Sub4_OP1", "Sub4_OP2", "Ass1_OP1", "Ass1_OP2"]:
            insert_validate = cursor.execute(
                "SELECT TPL_No,Fab_No,Station_Name  FROM[TT].[dbo].[Fab_History] WHERE TPL_No = ? AND Fab_No = ? AND Station_Name = ?"
                , tplno, fabno, 'PDI_I1_OP1')

            insert_validate_data = [{
                "TPL_No": obj[0], "Fab_No": obj[1], "Station_Name": obj[2]
            } for obj in insert_validate]
            print("############################################")
            print("insert validate output", insert_validate_data)
            if len(insert_validate_data) == 0:
                cursor.execute(
                    """ INSERT INTO [TT].[dbo].[Fab_History] (
                     "TPL_No"
                       ,"Fab_No"
                       ,"pd_no"
                       ,"TPL_Description"
                       ,"Start_datetime"
                       ,"Status"
                       ,"Station_Name"
                       ,"Completed_Datetime"
                       ,"Emp_Name"
                       ,"Emp_ID"
                       )VALUES (?,?,?,?,?,?,?,?,?,?)""", tplno, fabno,
                    "", "", datetime.datetime.now().isoformat(" ").split(".")[0], "P", 'PDI_I1_OP1', "", "", "")
                cursor.commit()
        else:
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Fab_History]
               SET "Start_datetime" = ?
             WHERE TPL_No = ? and Fab_No = ? and Station_Name = ? """,
                datetime.datetime.now().isoformat(" ").split(".")[0],
                tplno, fabno, 'PDI_I1_OP1')
            cursor.commit()




    else:
        print("completed_seq_no_list", completed_seq_no_list)

        actual_time_query = """SELECT Actual_Time FROM [TT].[dbo].[PDI_Process_Update_Table] WHERE TPL_No = ? AND FAB_NO = ? AND Order_Number = ? AND Station_id = ?"""
        actual_time_list = [obj[0] for obj in cursor.execute(actual_time_query, tplno, fabno,
                                                             completed_seq_no_list[len(completed_seq_no_list) - 1],
                                                             'PDI_I1_OP1')]
        actual_time = actual_time_list[0]
        print("Actual Time", actual_time)

    cycle_time_query = cursor.execute(
        """SELECT  SUM(Tack_Time) FROM [TT].[dbo].[PDI_Insp_Data_View]
            where FAB_NO = ? """, fabno
    )

    total_sec = [obj[0] for obj in cycle_time_query]
    minutes = total_sec[0] // 60
    secs = total_sec[0] % 60
    cycle_time = str(minutes).zfill(2) + ":" + str(secs).zfill(2)
    # cycle_time = "00:20"

    process_seq = cursor.execute(
        """SELECT * FROM [TT].[dbo].[PDI_Insp_Data_View] WHERE TPL_No = ? AND FAB_NO = ? AND Order_No = ? """,
        tplno, fabno, process_seq_no_list[0])

    # static("images/IMG/Process_Picture/" + str(obj[6]))
    process_seq_list = [{"FAB_NO": obj[0]
                            , "TPL_No": obj[1]
                            , "Station_id": "PDI_I1_OP1"
                            , "TPL_Description": obj[2]
                            , "Order_No": obj[3]
                            , "PDI_CL_Code": obj[4]
                            , "Tack_Time": obj[5]
                            , "Line_Code": obj[6]
                         # static("images/e.png")  #obj[6]   need changes
                            , "Sample_Image_Capture": static("images/IMG/PDI_Guide_Picture/" + str(obj[7]))
                            , "NOT_OK_Photo_Path": static("images/IMG/PDI_NOT_OK_Picture/" + str(obj[8]))
                            , "OK_Photo_Path": static("images/IMG/PDI_OK_Picture/" + str(obj[9]))
                            , "Check_List_description": obj[10]
                            , "CL_Type_Code": obj[11]
                            , "Total_Processes": obj[12]} for obj in process_seq]
    process_seq_list[0].update({"Cycle_Time": cycle_time, "Actual_Time": actual_time,
                                "Completed_Process": len(completed_seq_no_list)})  # need changes

    p_loss_levels = P_Q_Levels(cursor, "P_loss")
    q_loss_levels = P_Q_Levels(cursor, "Q_Loss")
    process_seq_list[0].update({"p_loss_levels": p_loss_levels, "q_loss_levels": q_loss_levels})

    return process_seq_list[0]

def pdi_process_validate_api(type, fabno, tplno, empname, empid, Order_No, CL_Type_Code,process_data, actual_time, station_id):
    cursor = db_connection()
    if type == "validate":
        if "Check_List" == CL_Type_Code:
            process_data = ast.literal_eval(process_data)
            print("process_data", process_data)
            #print("process_data", type(process_data))
            status = process_data["status"]

            # cp_details_result = cp_details_check(revno, partno, fabno, CL_Type_Code)
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[PDI_Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Order_Number],[CL_Type_Code],[status],[Actual_Time],[Process_Status],[Station_id]) values (?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,Order_No,
                    CL_Type_Code, status,actual_time, "C", station_id)
                cursor.commit()
                cursor.close()
            return cp_details_result
        if "Image_Capture" == CL_Type_Code:
            process_data = ast.literal_eval(process_data)
            print("process_data", process_data)
            #print("process_data", type(process_data))
            img_url = process_data["img_url"]

            # cp_details_result = cp_details_check(revno, partno, fabno, CL_Type_Code)
            cp_details_result = "data_validated"

            if cp_details_result == "data_validated":
                cursor.execute(
                    "insert into [TT].[dbo].[PDI_Process_Update_Table] ([TPL_No],[Fab_No],[Emp_Name],[Emp_ID],[Order_Number],[CL_Type_Code],[img_url],[Actual_Time],[Process_Status],[Station_id]) values (?,?,?,?,?,?,?,?,?,?)",
                    tplno, fabno,
                    empname, empid,Order_No,
                    CL_Type_Code, img_url,actual_time, "C", station_id)
                cursor.commit()
                cursor.close()
            return cp_details_result

# def torque_test(request):
#     global conn
#     print("connection ", conn)
#     cursor = db_connection()
#     # controller = client.write_register(28,1)
#     # # tool = client.write_register(29,1)
#     # # app = client.write_register(30,1)
#     #
#     # Torque = client.read_holding_registers(12017,1)
#     # Angle = client.read_holding_registers(12019,1) # D12019      - Angle
#     # Pass = client.read_holding_registers(20,1) # D12350      - Tool Pass
#     # Fail = client.read_holding_registers(21,1) # D12352      - Tool Fail
#     # Completed = client.read_holding_registers(22,1) # D12354      - Tool Completed
#     # Appmatch = client.read_holding_registers(23,1) # D12356      - Tool Appmatch
#     # Enable = client.read_holding_registers(24,1) # D12358      - Tool Enable
#     # online = client.read_holding_registers(25,1) # D12360      - Tool online
#     # Running = client.read_holding_registers(26,1) # D12362      - Tool Running
#     # # print("Torque    ",Torque.registers[0])
#     # # print("Angle     ",Angle.registers[0])
#     # # # print("Pass      ",Pass.registers)
#     # # # print("Fail      ",Fail.registers)
#     # # print("Completed ",Completed.registers)
#     # # print("Appmatch  ",Appmatch.registers)
#     # # print("Enable    ",Enable.registers)
#     # # print("online    ",online.registers)
#     # # print("Running   ",Running.registers)
#     #
#     #
#     #
#     # print("torque ",Torque.registers)
#     #
#
#
#     station = 1
#     tool_id = "C1-T04-AP01"
#
#     plc_input = cursor.execute(
#         "SELECT Tag_Index_no, Cleco_Program_No FROM [TT].[dbo].[Tools_Master] WHERE Tool_ID = ? ", tool_id)
#     plc_input_data = [{"index_no": obj[0], "app_no": obj[1]} for obj in plc_input]
#     print(plc_input_data)
#
#     app = client.write_register(1224, plc_input_data[0]["app_no"])
#     tool = client.write_register(1225, plc_input_data[0]["index_no"])
#
#     cursor = db_connection()
#
#     station = 1
#     tool_id = "C1-T01-AP25"
#
#     plc_input = cursor.execute(
#         "SELECT Tag_Index_no, Cleco_Program_No FROM [TT].[dbo].[Tools_Master] WHERE Tool_ID = ? ", tool_id)
#     plc_input_data = [{"index_no": obj[0], "app_no": obj[1]} for obj in plc_input]
#     print(plc_input_data)
#
#     tool = client.write_register(1224, plc_input_data[0]["index_no"])
#     app = client.write_register(1225, plc_input_data[0]["app_no"])
#
#     torque = client.read_holding_registers(12000, 1)
#     output1 = client.read_holding_registers(12001, 1)
#     output2 = client.read_holding_registers(12002, 1)
#     print("output1 ", output1.registers[0])
#     print("output2 ", output2.registers[0])
#
#     return render(request, 'toolscreen.html')


def agv(tpl_no,fab_no,station_id,method):
    cursor = db_connection()

    machines_on_agv_details = cursor.execute("select [Machines_on_AGV] FROM [TT].[dbo].[TPL_Master] where TPL_No = ?",tpl_no)
    machines_on_agv_data = [obj[0] for obj in machines_on_agv_details]
    print("*************************************************")
    print("*************************************************")
    print("method ", method)
    print("machines_on_agv_data  ", machines_on_agv_data)


    agv_station_register_details = cursor.execute("select [Comp_On_AGV] FROM [TT].[dbo].[Operator] where Operator_Code = ?",station_id)
    agv_station_register_data = [obj[0] for obj in agv_station_register_details]
    print("Register & machines", agv_station_register_data, machines_on_agv_data)
    print(agv_station_register_data[0],machines_on_agv_data[0])
    client.write_register(agv_station_register_data[0],int(machines_on_agv_data[0]))
    # client.write_register(3040,1)
    print("station_id",station_id)
    station_reg_details = cursor.execute("select [Process_Completion_Status] FROM [TT].[dbo].[Operator] where Operator_Code = ?",station_id)
    station_reg_data = [obj[0] for obj in station_reg_details]
    print("station_reg_data   ",station_reg_data)

    reg_no = int(station_reg_data[0].split('.')[0])
    bit_no =int(station_reg_data[0].split('.')[1], 16)
    print("reg_no ", reg_no)
    print("bit_no ", bit_no)

    reg_value = client.read_holding_registers(reg_no, 1).registers
    print("reg_value", reg_value)

    bit16_reg = bin(reg_value[0] & 0xFFFF)[2:].zfill(16)
    print("1bit_reg", bit16_reg)
    list_16 = list(bit16_reg)
    print("list 16        ", list_16)
    # bit = int(str(station_reg_data).split('.')[1])
    bit = bit_no
    print("bit ", bit)

    if method == "start":
        list_16[(16 - bit) - 1] = '0'
        print("list 16 update ", list_16)
        update_value = int(''.join(list_16), 2)
        print("update_value", update_value)
        client.write_register(reg_no, update_value)


    if method == "completed":
        list_16[(16 - bit) - 1] = '1'
        print("list 16 update ", list_16)
        update_value = int(''.join(list_16), 2)
        print("update_value", update_value)
        client.write_register(reg_no, update_value)

        time.sleep(1)
        list_16[(16 - bit) - 1] = '0'
        print("list 16 update ", list_16)
        update_value = int(''.join(list_16), 2)
        print("update_value", update_value)
        client.write_register(reg_no, update_value)



    return {"status":"completed"}


def write_float(value,reg1):
    packed_data = struct.pack('f', value)

    int1,int2 = struct.unpack('HH',packed_data)

    reg2 = reg1 + 1

    print("reg1     ",reg1)
    print("reg2     ",reg2)
    client.write_register(reg1,int1)
    client.write_register(reg2,int2)


def float_convertion(a,b):
    combined_int = (a << 16) | b

    float_value = struct.unpack('f',struct.pack('I',combined_int))[0]
    # print("float_value  ",float_value)
    return float_value

prev_pf = " "
reset = 1
def cleco_tool(station_id, tool_id, required_torque):
    global prev_pf
    global reset
    cursor = db_connection()
    station_id = station_id
    # tool_id = "C1-T03-AP01"

    print("station_id", station_id)
    print("tool_id  ct ", tool_id)


    plc_input = cursor.execute(
        "SELECT Tag_Index_no, Cleco_Program_No FROM [TT].[dbo].[Tools_Master] WHERE Tool_ID = ? ", tool_id)
    plc_input_data = [{"index_no": obj[0], "app_no": obj[1]} for obj in plc_input]
    print("plc_input_data ", plc_input_data)

    tool_app_details = cursor.execute(
        "SELECT App_Index, Tool_Index FROM [TT].[dbo].[Station_Registers] WHERE Station_ID = ? ", station_id)
    tool_app_data = [{"app_index": obj[0], "tool_index": obj[1]} for obj in tool_app_details]
    print("tool_app_data ", tool_app_data)


    tool = client.write_register(tool_app_data[0]["tool_index"], plc_input_data[0]["index_no"])  # 1224
    app = client.write_register(tool_app_data[0]["app_index"], plc_input_data[0]["app_no"])  # 1225

    # tool = client.write_register(1224, plc_input_data[0]["index_no"])  # 1224
    # app = client.write_register(1225, plc_input_data[0]["app_no"])  # 1225


    torque_output_details = cursor.execute(
        "SELECT Torque, Output FROM [TT].[dbo].[Cleco_Tool_Registers] WHERE Index_no = ? ", plc_input_data[0]["index_no"])
    torque_output_data = [{"torque":obj[0], "output":obj[1]} for obj in torque_output_details]
    print("torque_output_data ", torque_output_data)


    torque = client.read_holding_registers(torque_output_data[0]["torque"], 1)
    output = client.read_holding_registers(torque_output_data[0]["output"], 1)  # 12019
    print("torque ", torque)
    print("output ", output)


    # torque = client.read_holding_registers(12017, 1)
    # output = client.read_holding_registers(12014, 1)  # 12019



    # tool_status = client.read_holding_registers(1224, 1)
    # app_status_1 = client.read_holding_registers(1225, 1)

    tool_status = client.read_holding_registers(tool_app_data[0]["tool_index"], 1)
    app_status_1 = client.read_holding_registers(tool_app_data[0]["app_index"], 1)

    output_binary = format(output.registers[0], '016b')
    app_selected = int((output_binary[9:]), 2)

    # output_binary = format(output.registers[0], '016b')
    # app_selected = int((output_binary[9:]), 2)

    print("app_selected", app_selected)

    if app_selected == plc_input_data[0]["app_no"]:
        print("app matched")
        app_status = "App Matched"
    else:
        print("app not matched")
        app_status = "App Not Matched"

    pas = int(output_binary[7])
    fail = int(output_binary[6])
    online = int(output_binary[5])
    completed = int(output_binary[4])
    running = int(output_binary[3])
    enable = int(output_binary[2])

    print("decimal", output.registers[0])
    print("16bits", output_binary)
    print("9-16bits", output_binary[8:])
    print("1-8bits", output_binary[0:8])
    print("pas    ", pas)
    print("fail   ", fail)
    print("complete   ", completed)
    print("online ", online)
    print("running ", running)
    print("enable  ", enable)

    if pas == 1:
        pf = "Pass"

        # print("/////////////////////////////////////////////")
        # print("pf        ",pf)
        # print("prev pf   ",prev_pf)
        #
        # print("/////////////////////////////////////////////")

        output_binary = str(output_binary)
        print("binary_output pass   ", output_binary)
        print("*************************************")
        print(type(output_binary))
        if prev_pf == "Pass":
            print("-------------------------------------------------------")
            print("-------------------------------------------------------")
            # pf = "Fail"
            lst = list(output_binary)
            print("lst      ",lst)
            lst[7] = "0"
            lst[4] = "0"
            print("reset    ",lst)
            reset_bit = "".join(lst)
            reset_int = int(reset_bit,2)
            print("reset_int ",reset_int)

            write_reg = client.write_register(12014,reset_int)
            print("write_reg ", write_reg)
            read_reset = client.read_holding_registers(12014,1)
            print("reset_value ", read_reset.registers[0])

            pf = " "

        # prev_pf = "Pass"

        print("binary_output pass   ", output_binary)
        print("binary_output reset  ", output_binary)
        print("binary_output reset  ", )
        print("binary_output reset  ", )

        # reset = client.write_register(1224, plc_input_data[0]["index_no"])  # 1224
    elif fail == 1:
        pf = "Fail"
        prev_pf = "Fail"
    else:
        pf = " "
        prev_pf = " "

    if enable == 1:
        en_dis = "Enable"
    if enable == 0:
        en_dis = "Disable"

    if online == 1:
        on_off = "Online"
    if online == 0:
        on_off = "Offline"

    if running == 1:
        run_stop = "Running"
        reset = 1
        print("--------------------  reseted --------------")
    if running == 0:
        run_stop = "Stopped"


    print(reset)

    if pas == 1 and reset == 1:
    # if pas == 1:
        pf = "Pass"
        reset = 0

    else:
        pf = "Fail"


    # print("tool_status ", tool_status.registers[0])
    # print("app_status ", app_status_1.registers[0])
    # print("output ", output.registers[0])
    # print("torque ", torque.registers[0])

    print("*****************")
    print(pf)
    print("*****************")

    json_data = {
        "connection_status": "Active",
        "tool_connection": on_off,
        "app_status": app_status,
        "tool_status": en_dis,
        "tool_working": run_stop,
        "tool_output": pf,
        "actual_torque": torque.registers[0] / 10,
        "required_torque": required_torque
    }

    # data = {"tool_connection": on_off, "app_status": app_status, "tool_status": en_dis, "tool_working": run_stop,
    #         "tool_output": pf, "actual_torque": torque.registers[0] / 10, "required_torque": 11}

    # return render(request, 'toolscreen.html')

    return json_data


def digital_tool(station_id,tool_id):
    # time.sleep(2)
    station = station_id
    # station = "Ass4_OP2"

    tool_id = tool_id
    print("tool_id dt ", tool_id)

    cursor = db_connection()

    tool_index = cursor.execute(
        "SELECT Register FROM [TT].[dbo].[Digital_Tool_Registers] WHERE Tool_ID = ? ", tool_id)
    tool_index_value = [{"reg": obj[0]} for obj in tool_index]
    # print("Input_Register ", tool_index_value)

    input_reg = int(tool_index_value[0]["reg"])
    print("reg no   ",input_reg)
    print("x reg" ,input_reg)
    Tool_Tight_status = client.read_discrete_inputs(int(input_reg) ,1)
    status = Tool_Tight_status.bits[0]
    # print("Tool_Tight_status ", status)
    if status == True:
        status = "Pass"
    if status == False:
        status = "Fail"

    # print("========== status ",status)
    json_data= {
        "connection_status": "Active",
        "tool_output": status}

    return json_data




def drivecoupling(type, tpl_no):
    cursor = db_connection()

    if type == "start":
        print("*************************-------------------------------------------************************")
        print("start")
        write_reg = cursor.execute(
            "SELECT Distance, Sensor_No FROM [TT].[dbo].[Drive_Coupling_Master] WHERE TPL_No = ? ", tpl_no)
        write_reg_value = [{"Distance": obj[0], "Sensor_No": obj[1]} for obj in write_reg]
        # print("Input_Register ", write_reg_value[0]["Distance"], write_reg_value[0]["Sensor_No"])

        Distance_write = client.write_register(2760, write_reg_value[0]["Distance"])
        Sensor_write = client.write_register(2764, write_reg_value[0]["Sensor_No"])

        return {"Process":"Started"}

    if type == "status":
        print("*************************-------------------------------------------************************")
        print("status")
        Sensor_Selection = client.read_holding_registers(2764,1).registers[0]
        specification = client.read_holding_registers(2760, 1).registers[0]
        Sensor_live_value = client.read_holding_registers(2766, 1).registers[0]
        Sensors_data_reached = client.read_holding_registers(2762, 1).registers[0]
        Sensor = client.read_holding_registers(2768, 1)  # D12362      - Tool Running
        bits = list(format(Sensor.registers[0], '016b'))

        print("Sensor_1_reached       ", bits[11])
        print("Sensor_2_reached       ", bits[10])
        print("Sensor_3_reached       ", bits[9])
        print("Sensor_4_reached       ", bits[8])

        print("!!!!!!!!!!!!!!!!!  ", int(Sensor_Selection), int(bits[9]))

        if Sensor_Selection == 1 and bits[11] == 1:
            status = "completed"
        elif Sensor_Selection == 2 and bits[10] == 1:
            status = "completed"
        elif int(Sensor_Selection) == 3 and int(bits[9]) == 1:
            status = "completed"
        elif Sensor_Selection == 4 and bits[8] == 1:
            status = "completed"
        else:
            status = "inprogress"

        print("sensor_selection ",Sensor_Selection)
        print("specification ",specification)
        print("Sensor_live_value ",Sensor_live_value)
        print("Sensors_data_reached ",Sensors_data_reached)
        print("============ status ",status)

        # data = {
        #     "sensor_selected": "2",
        #     "specification": 150,
        #     "sensor_live_value": 150,
        #     "sensor_reached": 15,
        #     "status":"completed"
        # }
        data = {"sensor_selected":Sensor_Selection, "specification":specification,
                "sensor_live_value":Sensor_live_value, "sensor_reached":Sensors_data_reached, "status":status }
    return data


def leaktest_data_logs(device, intial_press, press_after_stable, final_press, allowable_press_drop, actual_press_drop):
    cursor = db_connection()

    cursor.execute(
                   """ INSERT INTO [TT].[dbo].[Leaktest_Data] (
    		"leak_device"
          ,"Intial_Pressure"
          ,"Pressure_After_Stabbilization"
          ,"Allowable_Final_Pressure"
          ,"Allowable_Pressure_Drop"
          ,"Actual_Pressure_Drop"
          )VALUES (?,?,?,?,?,?)""",device, intial_press, press_after_stable,
               final_press,allowable_press_drop, actual_press_drop )
    cursor.commit()




def leak_test(type, device = None, pressure_spec = None, Stable_time = None, Leak_time = None):
    cursor = db_connection()

    if type == "retest_leak":
        print("********************************************")
        print("reset_leak            ", device)
        if device == '1':
            client.write_register(3000,1)
        if device == '2':
            client.write_register(3510,2)
        if device == '3':
            client.write_register(3480,3)
        if device == '4':
            client.write_register(3450,4)


    if type == "skip_leak":
        print("********************************************")
        print("********************************************")
        print("********************************************")
        print("skip_leak            ", device)

        cursor.execute("""    
                 INSERT INTO [TT].[dbo].[Process_Update_Table] (
		TPL_No, Fab_No,Process_Code,Process_Status,Station_ID
        )VALUES (?,?,?,?,?)""","S011733","BWBC379485","leaktest","S","Ass1_OP1")
        cursor.commit()


        print("********************************************")
        print("********************************************")
        print("********************************************")



    if type == "process_card":
        print("leak_test_process_card")

        leak_1 = client.read_holding_registers(3000,1).registers
        leak_2 = client.read_holding_registers(3510,1).registers
        leak_3 = client.read_holding_registers(3480,1).registers
        leak_4 = client.read_holding_registers(3450,1).registers

        if leak_1[0] == 1:
            leak_1 = "running"
        else:
            leak_1 = "available"

        if leak_2[0] == 2:
            leak_2 = "running"
        else:
            leak_2 = "available"

        if leak_3[0] == 3:
            leak_3 = "running"
        else:
            leak_3 = "available"

        if leak_4[0] == 4:
            leak_4 = "running"
        else:
            leak_4 = "available"


        print("----------------------------------------")
        print("leak status ", leak_1,leak_2,leak_3,leak_4)
        print("----------------------------------------")

        leak_json = {"status": {
            "leaktester1": leak_1,
            "leaktester2": leak_2,
            "leaktester3": leak_3,
            "leaktester4": leak_4
        }}

        return leak_json

    if type == "selection":
        print("leak selection")
        value = device
        switch = {
            1: 3000,
            2: 3510,
            3: 3480,
            4: 3450
        }
        result = switch.get(device, "error")
        print(device, value,result)
        selection_ = client.write_register(result, value)
        selected_reg = client.read_holding_registers(result,1)

        print("selected reg ", selected_reg.registers)
        # return {"responce":"selected"}
        return "data_validated"

    if type == "leak_tester":
        print("++++++++++++++++++++++")
        print("device  ", device)

        if device == '1':
            live_pressure11 = client.read_holding_registers(3002, 2)  # float
            initial_pressure11 = client.read_holding_registers(3014, 2)  # float
            after_stable11 = client.read_holding_registers(3016, 2)  # float
            final_pressure11 = client.read_holding_registers(3022, 2)  # float
            allow_pressure11 = client.read_holding_registers(3020, 2)  # float
            actual_pressure_drop11 = client.read_holding_registers(3018, 2)

            run11 = client.read_holding_registers(3024, 1)
            bits11 = list(format(run11.registers[0], '016b'))

            print("************************************************************")
            print("stable -> ", int(bits11[8]))
            print("filling -> ",int(bits11[9]))
            print("leak -> ",int(bits11[10]))
            print("************************************************************")

            if int(bits11[9]) == 1 and int(bits11[8]) == 0 and int(bits11[10]) == 0:
                status11 = "Filling Status"
                timer11 = ""
            elif int(bits11[9]) == 0 and int(bits11[8]) == 1 and int( bits11[10]) == 0:
                status11 = "Stable Status"
                timer11 = client.read_holding_registers(3010,1).registers[0]
            elif int(bits11[9]) == 0 and int(bits11[8]) == 0 and int(bits11[10]) == 1:
                status11 = "Leak Status"
                timer11 = client.read_holding_registers(3012,1).registers[0]
            else:
                status11 = "" #"TEST STATUS"
                timer11 = "" # random.randint(1,10)

            if int(bits11[11]) == 1 and int(bits11[14]) == 0:
                ok_nok11 = "OK"
                client.write_register(3000, 0)

                leak_test_selection11 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures11 = float_convertion(initial_pressure11.registers[1], initial_pressure11.registers[0])
                after_stables11 = float_convertion(after_stable11.registers[1], after_stable11.registers[0])
                allowed_final_pressure11 = float_convertion(final_pressure11.registers[1],
                                                            final_pressure11.registers[0])
                allowed_pressure_drop11 = float_convertion(allow_pressure11.registers[1], allow_pressure11.registers[0])
                actual_pressure_drops11 = float_convertion(actual_pressure_drop11.registers[1],
                                                           actual_pressure_drop11.registers[0])

                leaktest_data_logs(device , initial_pressures11, after_stables11, allowed_final_pressure11, allowed_pressure_drop11,actual_pressure_drops11)

            elif int(bits11[11]) == 0 and int(bits11[14]) == 1:
                leak_test_selection11 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures11 = float_convertion(initial_pressure11.registers[1], initial_pressure11.registers[0])
                after_stables11 = float_convertion(after_stable11.registers[1], after_stable11.registers[0])
                allowed_final_pressure11 = float_convertion(final_pressure11.registers[1],
                                                            final_pressure11.registers[0])
                allowed_pressure_drop11 = float_convertion(allow_pressure11.registers[1], allow_pressure11.registers[0])
                actual_pressure_drops11 = float_convertion(actual_pressure_drop11.registers[1],
                                                           actual_pressure_drop11.registers[0])

                leaktest_data_logs(device, initial_pressures11, after_stables11, allowed_final_pressure11,
                                   allowed_pressure_drop11, actual_pressure_drops11)

                ok_nok11 = "NOT OK"
                client.write_register(3000, 0)
            else:
                if int(bits11[9]) == 1 or int(bits11[8]) == 1 or int(bits11[10]) == 1:
                    ok_nok11 = "Processing"
                else:
                    ok_nok11 = "Idle"



            leak_test_selection11 = client.read_holding_registers(3000, 1).registers[0]
            live_pressures11 = float_convertion(live_pressure11.registers[1], live_pressure11.registers[0])
            initial_pressures11 = float_convertion(initial_pressure11.registers[1], initial_pressure11.registers[0])
            after_stables11 = float_convertion(after_stable11.registers[1], after_stable11.registers[0])
            allowed_final_pressure11 = float_convertion(final_pressure11.registers[1], final_pressure11.registers[0])
            allowed_pressure_drop11 = float_convertion(allow_pressure11.registers[1], allow_pressure11.registers[0])
            actual_pressure_drops11 = float_convertion(actual_pressure_drop11.registers[1], actual_pressure_drop11.registers[0])

            print("------------------- LIve pressure ", format(live_pressures11, ".2f"))
            json_data11 = {
                "live_pressures": format(live_pressures11, ".2f"),
                "initial_pressure": format(initial_pressures11, ".2f"),
                "pressure_after_stabilization": format(after_stables11, ".2f"),
                "allowable_final_pressure": format(allowed_final_pressure11, ".2f"),
                "allowable_pressure_drop": format(allowed_pressure_drop11, ".2f"),
                "actual_pressure_drop": format(actual_pressure_drops11, ".2f"),
                "status": status11,
                "Leak_Testing_Timer": timer11,
                "ok_nok": ok_nok11,
                "leak_selected": leak_test_selection11,
                "valve_1": bits11[13],
                "valve_2": bits11[12]
            }
            print("leak test json data")
            print(json_data11)
            return json_data11

        if device == '2':
            live_pressure12 = client.read_holding_registers(3512, 2)  # float
            initial_pressure12 = client.read_holding_registers(3524, 2)  # float
            after_stable12 = client.read_holding_registers(3526, 2)  # float
            final_pressure12 = client.read_holding_registers(3532, 2)  # float
            allow_pressure12 = client.read_holding_registers(3530, 2)  # float
            actual_pressure_drop12 = client.read_holding_registers(3528, 2)

            run12 = client.read_holding_registers(3534, 1)
            bits12 = list(format(run12.registers[0], '016b'))

            print("************************************************************")
            print("stable -> ", int(bits12[8]))
            print("filling -> ", int(bits12[9]))
            print("leak -> ", int(bits12[10]))
            print("************************************************************")


            if int(bits12[9]) == 1 and int(bits12[8]) == 0 and int(bits12[10]) == 0:
                status12 = "Filling Status"
                timer12 = ""
            elif int(bits12[9]) == 0 and int(bits12[8]) == 1 and int(bits12[10]) == 0:
                status12 = "Stable Status"
                timer12 = client.read_holding_registers(3520, 1).registers[0]
            elif int(bits12[9]) == 0 and int(bits12[8]) == 0 and int(bits12[10]) == 1:
                status12 = "Leak Status"
                timer12 = client.read_holding_registers(3522, 1).registers[0]
            else:
                status12 = ""
                timer12 = ""

            if int(bits12[11]) == 1 and int(bits12[14]) == 0:
                ok_nok12 = "OK"
                client.write_register(3510, 0)

                leak_test_selection12 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures12 = float_convertion(initial_pressure12.registers[1], initial_pressure12.registers[0])
                after_stables12 = float_convertion(after_stable12.registers[1], after_stable12.registers[0])
                allowed_final_pressure12 = float_convertion(final_pressure12.registers[1],
                                                            final_pressure12.registers[0])
                allowed_pressure_drop12 = float_convertion(allow_pressure12.registers[1], allow_pressure12.registers[0])
                actual_pressure_drops12 = float_convertion(actual_pressure_drop12.registers[1],
                                                           actual_pressure_drop12.registers[0])

                leaktest_data_logs(device, initial_pressures12, after_stables12,
                                   allowed_final_pressure12, allowed_pressure_drop12, actual_pressure_drops12)

            elif int(bits12[11]) == 0 and int(bits12[14]) == 1:
                leak_test_selection12 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures12 = float_convertion(initial_pressure12.registers[1], initial_pressure12.registers[0])
                after_stables12 = float_convertion(after_stable12.registers[1], after_stable12.registers[0])
                allowed_final_pressure12 = float_convertion(final_pressure12.registers[1],
                                                            final_pressure12.registers[0])
                allowed_pressure_drop12 = float_convertion(allow_pressure12.registers[1], allow_pressure12.registers[0])
                actual_pressure_drops12 = float_convertion(actual_pressure_drop12.registers[1],
                                                           actual_pressure_drop12.registers[0])

                leaktest_data_logs(device, initial_pressures12, after_stables12,
                                   allowed_final_pressure12, allowed_pressure_drop12, actual_pressure_drops12)
                ok_nok12 = "NOT_OK"
                # client.write_register(3510, 0)
            else:
                if int(bits12[9]) == 1 or int(bits12[8]) == 1 or int(bits12[10]) == 1:
                    ok_nok12 = "Processing"
                else:
                    ok_nok12 = "Idle"



            leak_test_selection12 = client.read_holding_registers(3510, 1).registers[0]
            live_pressures12 = float_convertion(live_pressure12.registers[1], live_pressure12.registers[0])
            initial_pressures12 = float_convertion(initial_pressure12.registers[1], initial_pressure12.registers[0])
            after_stables12 = float_convertion(after_stable12.registers[1], after_stable12.registers[0])
            allowed_final_pressure12 = float_convertion(final_pressure12.registers[1], final_pressure12.registers[0])
            allowed_pressure_drop12 = float_convertion(allow_pressure12.registers[1], allow_pressure12.registers[0])
            actual_pressure_drops12 = float_convertion(actual_pressure_drop12.registers[1],
                                                     actual_pressure_drop12.registers[0])

            print("------------------- LIve pressure ", format(live_pressures12, ".2f"))
            json_data12 = {
                "live_pressures": format(live_pressures12, ".2f"),
                "initial_pressure": format(initial_pressures12, ".2f"),
                "pressure_after_stabilization": format(after_stables12, ".2f"),
                "allowable_final_pressure": format(allowed_final_pressure12, ".2f"),
                "allowable_pressure_drop": format(allowed_pressure_drop12, ".2f"),
                "actual_pressure_drop": format(actual_pressure_drops12, ".2f"),
                "status": status12,
                "Leak_Testing_Timer": timer12,
                "ok_nok": ok_nok12,
                "leak_selected": leak_test_selection12,
                "valve_1": bits12[13],
                "valve_2": bits12[12]
            }
            return json_data12

        if device == '3':
            live_pressure13 = client.read_holding_registers(3482, 2)  # float
            initial_pressure13 = client.read_holding_registers(3494, 2)  # float
            after_stable13 = client.read_holding_registers(3496, 2)  # float
            final_pressure13 = client.read_holding_registers(3502, 2)  # float
            allow_pressure13 = client.read_holding_registers(3500, 2)  # float
            actual_pressure_drop13 = client.read_holding_registers(3498, 2)

            run13 = client.read_holding_registers(3504, 1)
            bits13 = list(format(run13.registers[0], '016b'))

            if int(bits13[9]) == 1 and int(bits13[8]) == 0 and int(bits13[10]) == 0:
                status13 = "Filling Status"
                timer13 = ""
            elif int(bits13[9]) == 0 and int(bits13[8]) == 1 and int(bits13[10]) == 0:
                status13 = "Stable Status"
                timer13 = client.read_holding_registers(3490, 1).registers[0]
            elif int(bits13[9]) == 0 and int(bits13[8]) == 0 and int(bits13[10]) == 1:
                status13 = "Leak Status"
                timer13 = client.read_holding_registers(3492, 1).registers[0]
            else:
                status13 = ""
                timer13 = ""

            if int(bits13[11]) == 1 and int(bits13[14]) == 0:
                ok_nok13 = "OK"
                client.write_register(3480, 0)

                leak_test_selection13 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures13 = float_convertion(initial_pressure13.registers[1], initial_pressure13.registers[0])
                after_stables13 = float_convertion(after_stable13.registers[1], after_stable13.registers[0])
                allowed_final_pressure13 = float_convertion(final_pressure13.registers[1],
                                                            final_pressure13.registers[0])
                allowed_pressure_drop13 = float_convertion(allow_pressure13.registers[1], allow_pressure13.registers[0])
                actual_pressure_drops13 = float_convertion(actual_pressure_drop13.registers[1],
                                                           actual_pressure_drop13.registers[0])

                leaktest_data_logs(device, initial_pressures13, after_stables13,
                                   allowed_final_pressure13, allowed_pressure_drop13, actual_pressure_drops13)


            elif int(bits13[11]) == 0 and int(bits13[14]) == 1:
                ok_nok13 = "NOT_OK"
                client.write_register(3480, 0)
                leak_test_selection13 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures13 = float_convertion(initial_pressure13.registers[1], initial_pressure13.registers[0])
                after_stables13 = float_convertion(after_stable13.registers[1], after_stable13.registers[0])
                allowed_final_pressure13 = float_convertion(final_pressure13.registers[1],
                                                            final_pressure13.registers[0])
                allowed_pressure_drop13 = float_convertion(allow_pressure13.registers[1], allow_pressure13.registers[0])
                actual_pressure_drops13 = float_convertion(actual_pressure_drop13.registers[1],
                                                           actual_pressure_drop13.registers[0])

                leaktest_data_logs(device, initial_pressures13, after_stables13,
                                   allowed_final_pressure13, allowed_pressure_drop13, actual_pressure_drops13)

            else:
                if int(bits13[9]) == 1 or int(bits13[8]) == 1 or int(bits13[10]) == 1:
                    ok_nok13 = "Processing"
                else:
                    ok_nok13 = "Idle"

            leak_test_selection13 = client.read_holding_registers(3480, 1).registers[0]
            live_pressures13 = float_convertion(live_pressure13.registers[1], live_pressure13.registers[0])
            initial_pressures13 = float_convertion(initial_pressure13.registers[1], initial_pressure13.registers[0])
            after_stables13 = float_convertion(after_stable13.registers[1], after_stable13.registers[0])
            allowed_final_pressure13 = float_convertion(final_pressure13.registers[1], final_pressure13.registers[0])
            allowed_pressure_drop13 = float_convertion(allow_pressure13.registers[1], allow_pressure13.registers[0])
            actual_pressure_drops13 = float_convertion(actual_pressure_drop13.registers[1],
                                                     actual_pressure_drop13.registers[0])

            print("------------------- LIve pressure ", format(live_pressures13, ".2f"))
            json_data13 = {
                "live_pressures": format(live_pressures13, ".2f"),
                "initial_pressure": format(initial_pressures13, ".2f"),
                "pressure_after_stabilization": format(after_stables13, ".2f"),
                "allowable_final_pressure": format(allowed_final_pressure13, ".2f"),
                "allowable_pressure_drop": format(allowed_pressure_drop13, ".2f"),
                "actual_pressure_drop": format(actual_pressure_drops13, ".2f"),
                "status": status13,
                "Leak_Testing_Timer": timer13,
                "ok_nok": ok_nok13,
                "leak_selected": leak_test_selection13,
                "valve_1": bits13[13],
                "valve_2": bits13[12]
            }
            return json_data13

        if device == '4':
            live_pressure14 = client.read_holding_registers(3452, 2)  # float
            initial_pressure14 = client.read_holding_registers(3464, 2)  # float
            after_stable14 = client.read_holding_registers(3466, 2)  # float
            final_pressure14 = client.read_holding_registers(3472, 2)  # float
            allow_pressure14 = client.read_holding_registers(3470, 2)  # float
            actual_pressure_drop14 = client.read_holding_registers(3468, 2)

            run14 = client.read_holding_registers(3474, 1)
            bits14 = list(format(run14.registers[0], '016b'))

            if int(bits14[9]) == 1 and int(bits14[8]) == 0 and int(bits14[10]) == 0:
                status14 = "Filling Status"
                timer14 = ""
            elif int(bits14[9]) == 0 and int(bits14[8]) == 1 and int(bits14[10]) == 0:
                status14 = "Stable Status"
                timer14 = client.read_holding_registers(3460, 1).registers[0]
            elif int(bits14[9]) == 0 and int(bits14[8]) == 0 and int(bits14[10]) == 1:
                status14 = "Leak Status"
                timer14 = client.read_holding_registers(3462, 1).registers[0]
            else:
                status14 = ""
                timer14 = ""

            if int(bits14[11]) == 1 and int(bits14[14]) == 0:
                ok_nok14 = "OK"
                client.write_register(3450, 0)

                leak_test_selection14 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures14 = float_convertion(initial_pressure14.registers[1], initial_pressure14.registers[0])
                after_stables14 = float_convertion(after_stable14.registers[1], after_stable14.registers[0])
                allowed_final_pressure14 = float_convertion(final_pressure14.registers[1],
                                                            final_pressure14.registers[0])
                allowed_pressure_drop14 = float_convertion(allow_pressure14.registers[1], allow_pressure14.registers[0])
                actual_pressure_drops14 = float_convertion(actual_pressure_drop14.registers[1],
                                                           actual_pressure_drop14.registers[0])

                leaktest_data_logs(device, initial_pressures14, after_stables14,
                                   allowed_final_pressure14, allowed_pressure_drop14, actual_pressure_drops14)


            elif int(bits14[11]) == 0 and int(bits14[14]) == 1:
                ok_nok14 = "NOT_OK"
                client.write_register(3450, 0)
                leak_test_selection14 = client.read_holding_registers(3000, 1).registers[0]
                initial_pressures14 = float_convertion(initial_pressure14.registers[1], initial_pressure14.registers[0])
                after_stables14 = float_convertion(after_stable14.registers[1], after_stable14.registers[0])
                allowed_final_pressure14 = float_convertion(final_pressure14.registers[1],
                                                            final_pressure14.registers[0])
                allowed_pressure_drop14 = float_convertion(allow_pressure14.registers[1], allow_pressure14.registers[0])
                actual_pressure_drops14 = float_convertion(actual_pressure_drop14.registers[1],
                                                           actual_pressure_drop14.registers[0])

                leaktest_data_logs(device, initial_pressures14, after_stables14,
                                   allowed_final_pressure14, allowed_pressure_drop14, actual_pressure_drops14)


            else:
                if int(bits14[9]) == 1 or int(bits14[8]) == 1 or int(bits14[10]) == 1:
                    ok_nok14 = "Processing"
                else:
                    ok_nok14 = "Idle"

            leak_test_selection14 = client.read_holding_registers(3450, 1).registers[0]
            live_pressures14 = float_convertion(live_pressure14.registers[1], live_pressure14.registers[0])
            initial_pressures14 = float_convertion(initial_pressure14.registers[1], initial_pressure14.registers[0])
            after_stables14 = float_convertion(after_stable14.registers[1], after_stable14.registers[0])
            allowed_final_pressure14 = float_convertion(final_pressure14.registers[1], final_pressure14.registers[0])
            allowed_pressure_drop14 = float_convertion(allow_pressure14.registers[1], allow_pressure14.registers[0])
            actual_pressure_drops14 = float_convertion(actual_pressure_drop14.registers[1],
                                                     actual_pressure_drop14.registers[0])


            print("------------------- LIve pressure ",format(live_pressures14,".2f"))
            json_data14 = {
                "live_pressures": format(live_pressures14,".2f"),
                "initial_pressure": format(initial_pressures14,".2f"),
                "pressure_after_stabilization": format(after_stables14,".2f"),
                "allowable_final_pressure": format(allowed_final_pressure14,".2f"),
                "allowable_pressure_drop": format(allowed_pressure_drop14,".2f"),
                "actual_pressure_drop": format(actual_pressure_drops14,".2f"),
                "status": status14,
                "Leak_Testing_Timer": timer14,
                "ok_nok": ok_nok14,
                "leak_selected": leak_test_selection14,
                "valve_1": bits14[13],
                "valve_2": bits14[12]
            }
            return json_data14

        # json_data = {
        #     "initial_pressure": "6.18",
        #     "pressure_after_stabilization": "6.09",
        #     "allowable_final_pressure": "6.08",
        #     "allowable_pressure_drop": "0.030",
        #     "actual_pressure_drop": "0.010",
        #     "status": "Pass",
        #     "Leak_Testing_Timer": "20",
        # }
        #


    if type == "status_setting":
        print("unit in status settings ", device)

        if device == '1':
            press_specs11 =  client.read_holding_registers(3004, 2)
            press_specs1 = float_convertion(press_specs11.registers[1],press_specs11.registers[0])   # client.read_holding_registers(3004, 2).registers[0]  # float
            stabilization_timer1 = client.read_holding_registers(3006, 1).registers[0]  # decimal
            leaktest_timer1 = client.read_holding_registers(3008, 1).registers[0]

            json_data1 = {
                "pressure_specification": str(press_specs1)[:5],
                "stabilization_timer": stabilization_timer1,
                "Leak_Testing_Timer": leaktest_timer1,
            }
            print("********************************************")
            print(" device 1 settings ")
            print("********************************************")
            print(json_data1)
            return json_data1

        if device == '2':
            press_specs12 = client.read_holding_registers(3514, 2)
            press_specs2 =  float_convertion(press_specs12.registers[1],press_specs12.registers[0])   # client.read_holding_registers(3514, 2).registers[0]  # float
            stabilization_timer2 = client.read_holding_registers(3516, 1).registers[0]  # decimal
            leaktest_timer2 = client.read_holding_registers(3518, 1).registers[0]

            json_data2 = {
                "pressure_specification": str(press_specs2)[:5],
                "stabilization_timer": stabilization_timer2,
                "Leak_Testing_Timer": leaktest_timer2,
            }
            print("********************************************")
            print(" device 2 settings ")
            print("********************************************")
            print(json_data2)
            return json_data2

        if device == '3':
            press_specs13 = client.read_holding_registers(3484, 2)
            press_specs3 =  float_convertion(press_specs13.registers[1],press_specs13.registers[0])  # client.read_holding_registers(3484, 2).registers[0]  # float
            stabilization_timer3 = client.read_holding_registers(3486, 1).registers[0]  # decimal
            leaktest_timer3 = client.read_holding_registers(3488, 1).registers[0]

            json_data3 = {
                "pressure_specification": str(press_specs3)[:5],
                "stabilization_timer": stabilization_timer3,
                "Leak_Testing_Timer": leaktest_timer3,
            }
            print("********************************************")
            print(" device 3 settings ")
            print("********************************************")
            print(json_data3)
            return json_data3

        if device == '4':
            press_specs14 = client.read_holding_registers(3454, 2)
            press_specs4 =  float_convertion(press_specs14.registers[1],press_specs14.registers[0])  # client.read_holding_registers(3454, 2).registers[0]  # float
            stabilization_timer4 = client.read_holding_registers(3456, 1).registers[0]  # decimal
            leaktest_timer4 = client.read_holding_registers(3458, 1).registers[0]

            json_data4 = {
                "pressure_specification": str(press_specs4)[:5],
                "stabilization_timer": stabilization_timer4,
                "Leak_Testing_Timer": leaktest_timer4,
            }
            print("********************************************")
            print(" device 4 settings ")
            print("********************************************")
            print(json_data4)
            return json_data4

    if type == "status_setting_update":
        print("################################################################")
        print("################################################################")
        print("################################################################")
        print("################################################################")
        if device == '1':
            if pressure_spec != None and Stable_time != None and Leak_time != None:
                pressure_specification = pressure_spec
                stabilize_timer = Stable_time
                Leak_Testing_Timer = Leak_time

                press_specs_ =  write_float(float(pressure_specification),3004)               # client.write_register(3004,int(pressure_specification))                   # float
                stabilization_timer_ = client.write_register(3006,int(stabilize_timer))          # decimal
                leaktest_timer_ = client.write_register(3008,int(Leak_Testing_Timer))
                print("///////////////////////// updated 111111111111111")
                json_data= {
                    "status": "updated"
                }
            else:
                json_data= {
                    "status": "parameters_missing"
                }
            return json_data

    if device == '2':
        if pressure_spec != None and Stable_time != None and Leak_time != None:
            pressure_specification = pressure_spec
            stabilize_timer = Stable_time
            Leak_Testing_Timer = Leak_time

            press_specs_ = write_float(float(pressure_specification),3514)               #client.write_register(3514, int(pressure_specification))  # float
            stabilization_timer_ = client.write_register(3516, int(stabilize_timer))  # decimal
            leaktest_timer_ = client.write_register(3518, int(Leak_Testing_Timer))
            print("///////////////////////// updated 222222222222222")

            json_data = {
                "status": "updated"
            }
        else:
            json_data = {
                "status": "parameters_missing"
            }
        return json_data

    if device == '3':
        if pressure_spec != None and Stable_time != None and Leak_time != None:
            pressure_specification = pressure_spec
            stabilize_timer = Stable_time
            Leak_Testing_Timer = Leak_time

            press_specs_ = write_float(float(pressure_specification),3484)               #client.write_register(3484, int(pressure_specification))  # float
            stabilization_timer_ = client.write_register(3486, int(stabilize_timer))  # decimal
            leaktest_timer_ = client.write_register(3488, int(Leak_Testing_Timer))
            print("///////////////////////// updated 3333333333333333333")

            json_data = {
                "status": "updated"
            }
        else:
            json_data = {
                "status": "parameters_missing"
            }
        return json_data

    if device == '4':
        if pressure_spec != None and Stable_time != None and Leak_time != None:
            pressure_specification = pressure_spec
            stabilize_timer = Stable_time
            Leak_Testing_Timer = Leak_time

            press_specs_ = write_float(float(pressure_specification),3454)               #client.write_register(3454, int(pressure_specification))  # float
            stabilization_timer_ = client.write_register(3456, int(stabilize_timer))  # decimal
            leaktest_timer_ = client.write_register(3458, int(Leak_Testing_Timer))
            print("///////////////////////// updated 4444444444444444")

            json_data = {
                "status": "updated"
            }
        else:
            json_data = {
                "status": "parameters_missing"
            }
        return json_data

    if type == "leak_status":
        cursor = db_connection()
        leak_details = cursor.execute("SELECT TPL_No, FAB_NO, Station_ID FROM [TT].[dbo].[Leaktest_Details]")
        leak_details_list = [{"TPL_No":obj[0], "Fab_No":obj[1], "Station_ID":obj[2]} for obj in leak_details]

        run1 = client.read_holding_registers(3024, 1)
        bits1 = list(format(run1.registers[0], '016b'))
        run2 = client.read_holding_registers(3534, 1)
        bits2 = list(format(run2.registers[0], '016b'))
        run3 = client.read_holding_registers(3504, 1)
        bits3 = list(format(run3.registers[0], '016b'))
        run4 = client.read_holding_registers(3474, 1)
        bits4 = list(format(run4.registers[0], '016b'))



        ok1 = bits1[11]
        nok1 = bits1[14]
        filling1 = bits1[9]
        stable1 = bits1[8]
        leak1 = bits1[10]


        ok2 = bits2[11]
        nok2 = bits2[14]
        filling2 = bits2[9]
        stable2 = bits2[8]
        leak2 = bits2[10]

        ok3 = bits3[11]
        nok3 = bits3[14]
        filling3 = bits3[9]
        stable3 = bits3[8]
        leak3 = bits3[10]

        ok4 = bits4[11]
        nok4 = bits4[14]
        filling4 = bits4[9]
        stable4 = bits4[8]
        leak4 = bits4[10]



        if int(ok1) == 1 and int(nok1) == 0:
            leak_status1 = "OK"
            leak_tower_lamp(1, "Pass")
            client.write_register(3000,0)
        elif int(ok1) == 0 and int(nok1) == 1:
            leak_status1 = "NOT OK"
            leak_tower_lamp(1, "Fail")
        else:
            leak_status1 = "------"

        if int(ok2) == 1 and int(nok2) == 0:
            leak_status2 = "OK"
            client.write_register(3510, 0)
            leak_tower_lamp(2, "Pass")
        elif int(ok2) == 0 and int(nok2) == 1:
            leak_status2 = "NOT OK"
            leak_tower_lamp(2, "Fail")
        else:
            leak_status2 = "------"

        if int(ok3) == 1 and int(nok3) == 0:
            leak_status3 = "OK"
            client.write_register(3480, 0)
            leak_tower_lamp(3, "Pass")
        elif int(ok3) == 0 and int(nok3) == 1:
            leak_status3 = "NOT OK"
            leak_tower_lamp(3, "Fail")
        else:
            leak_status3 = "------"

        if int(ok4) == 1 and int(nok4) == 0:
            leak_status4 = "OK"
            client.write_register(3450, 0)
            leak_tower_lamp(4, "Pass")
        elif int(ok4) == 0 and int(nok4) == 1:
            leak_status4 = "NOT OK"
            leak_tower_lamp(4, "Fail")
        else:
            leak_status4 = "------"


        print("*******************************************************")
        print(int(stable1))
        print("Filllig -> "+filling1 + " Stale -> " + stable1 + " leak -> " + leak1)
        print("*******************************************************")
        if int(filling1) == 1:
            TesterStatus1 = "Filling"
            leak_tower_lamp(1,"Processing")
            print("*************  TestStatus1", TesterStatus1)
        elif int(leak1) == 1:
            TesterStatus1 = "Leak_Counter"
            leak_tower_lamp(1,"start")
            print("*************  TestStatus1", TesterStatus1)
        elif int(stable1) == 1:
            TesterStatus1 = "Stable_Counter"
            leak_tower_lamp(1,"Processing")
            print("*************  TestStatus1", TesterStatus1)
        else:
            TesterStatus1 = "------"
            print("*************  TestStatus1", TesterStatus1)


        if int(filling2) == 1:
            TesterStatus2 = "Filling"
            leak_tower_lamp(2,"Processing")
        elif int(leak2) == 1:
            TesterStatus2 = "Leak_Counter"
            leak_tower_lamp(2,"start")
        elif int(stable2) == 1:
            TesterStatus2 = "Stable_Counter"
            leak_tower_lamp(2,"Processing")
        else:
            TesterStatus2 = "------"

        if int(filling3) == 1:
            TesterStatus3 = "Filling"
            leak_tower_lamp(3,"Processing")
        elif int(leak3) == 1:
            TesterStatus3 = "Leak_Counter"
            leak_tower_lamp(3,"start")
        elif int(stable3) == 1:
            TesterStatus3 = "Stable_Counter"
            leak_tower_lamp(3,"Processing")
        else:
            TesterStatus3 = "------"


        if int(filling4) == 1:
            TesterStatus4 = "Filling"
            leak_tower_lamp(4,"Processing")
        elif int(leak4) == 1:
            TesterStatus4 = "Leak_Counter"
            leak_tower_lamp(4,"start")
        elif int(stable4) == 1:
            TesterStatus4 = "Stable_Counter"
            leak_tower_lamp(4,"Processing")
        else:
            TesterStatus4 = "------"



        json_data= [
            {
                "FabNo": leak_details_list[0]["Fab_No"],
                "TplNo": leak_details_list[0]["TPL_No"],
                "leaktesterno": "Leak Tester 01",
                "SationID": leak_details_list[0]["Station_ID"],
                "TesterStatus":TesterStatus1,
                "TestStatus": leak_status1
            },
            {
                "FabNo": leak_details_list[1]["Fab_No"],
                "TplNo": leak_details_list[1]["TPL_No"],
                "leaktesterno": "Leak Tester 02",
                "SationID": leak_details_list[1]["Station_ID"],
                "TesterStatus": TesterStatus2,
                "TestStatus": leak_status2
            },
            {
                "FabNo": leak_details_list[2]["Fab_No"],
                "TplNo": leak_details_list[2]["TPL_No"],
                "leaktesterno": "Leak Tester 03",
                "SationID": leak_details_list[2]["Station_ID"],
                "TesterStatus": TesterStatus3,
                "TestStatus": leak_status3
            },
            {
                "FabNo": leak_details_list[3]["Fab_No"],
                "TplNo": leak_details_list[3]["TPL_No"],
                "leaktesterno": "Leak Tester 04",
                "SationID": leak_details_list[3]["Station_ID"],
                "TesterStatus": TesterStatus4,
                "TestStatus": leak_status4
            }
        ]
        return json_data


def leak_tower_lamp(device, state):
    print("device ", device)
    print("state ", state)
    cursor  = db_connection()

    leak_device = cursor.execute("SELECT  Tower_Lamp_Reg FROM [TT].[dbo].[Leaktest_Details] where Leak_Devices = ?", int(device))
    reg_value = [obj for obj in leak_device]
    print("leak test tower lamp reg_value",reg_value)
    if state == "start":
        print("*********** yellow ",device)
        client.write_register(int(reg_value[0][0]),2)
    if state == "Pass":
        print("*********** Green",device)
        client.write_register(int(reg_value[0][0]),1)
    if state == "Fail":
        print("************ Red",device)
        client.write_register(int(reg_value[0][0]),3)
    if state == "Processing":
        print("************ Red",device)
        client.write_register(int(reg_value[0][0]),4)





@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def testboothlib(request):
    cursor = db_connection()
    if request.method=="POST":
        print("******************")
        for key,value in request.POST.items():
            print("key: %s" %(key))
            print("value: %s" %(value))
        Test_Code=request.POST['Test_Code']
        Test_Description = request.POST['Test_Description']
        Input_Type = request.POST['Input_Type']
        Cycle_Time = request.POST['Cycle_Time']


        if request.POST["submit"] == "Add":

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Testbooth_Library] (
                "Test_Code"
                ,"Test_Description"
                ,"Input_Type"
                ,"Cycle_Time"
                )VALUES (?,?,?,?)""",request.POST['Test_Code'],
                request.POST['Test_Description'],request.POST["Input_Type"],
                request.POST['Cycle_Time'])
            cursor.commit()

        elif request.POST["submit"] == "Edit":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Testbooth_Library]
                SET 
                "Test_Description"=?
                ,"Input_Type"=?
                ,"Cycle_Time"=?
                WHERE Test_Code = ?""",
                request.POST['Test_Description'],request.POST["Input_Type"],
                request.POST['Cycle_Time'],request.POST['Test_Code'])

            cursor.commit()

        elif request.POST["submit"] == "Delete":
            cursor.execute(
                """
                DELETE FROM [TT].[dbo].[Testbooth_Library]
                WHERE Test_Code = ?""", request.POST["Test_Code"])
            cursor.commit()




    #query for test_input dropdown in testbooth library
    test_input_details = cursor.execute(
        """SELECT *  FROM [TT].[dbo].[Testbooth_Input_Type]""")
    test_input_data = [obj[1] for obj in test_input_details]
    print("test input data ",test_input_data)

    # query for table data displayed in testbooth library
    testbooth_library_details=cursor.execute(
        """SELECT DISTINCT  [Test_Code],[Test_Description],[Input_Type],[Cycle_Time] FROM [TT].[dbo].[Testbooth_Library]""")
    testbooth_library_data= [{'Test_Code':obj[0],'Test_Description':obj[1],'Input_Type':obj[2],
                              'Cycle_Time':obj[3]} for obj in testbooth_library_details]



    return render(request,'Testbooth/testboothlib.html',{'test_input_data':test_input_data,'testbooth_library_data':testbooth_library_data})



@permission_required('ELGI_App.admin_view', login_url = 'no_access')
@login_required(login_url='login')
def testboothmst(request):
    cursor=db_connection()
    if request.method=="POST":
        print("******************")

        for key,value in request.POST.items():
            print("key: %s" %(key))
            print("value: %s" %(value))
        PMMKEY = request.POST['PMMKEY']  # int
        Test_Code=request.POST['Test_Code']
        Test_Category = request.POST['Test_Category']
        Test_Category_Seq = request.POST['Test_Category_Seq']
        Tpl_No = request.POST['Tpl_No']
        Test_Code_Seq_No = request.POST['Test_Code_Seq_No']
        Fan_Motor_Current_Measurement = request.POST['Fan_Motor_Current_Measurement']
        Number_of_Fans = request.POST['Number_of_Fans']  # int
        VFD_Model_Testing = request.POST['VFD_Model_Testing']
        Oil_Recommended = request.POST['Oil_Recommended']
        VFD = request.POST['VFD']
        Dryer = request.POST['Dryer']
        Belt_Driven = request.POST['Belt_Driven']
        SPM_Reading_Color = request.POST['SPM_Reading_Color']

        if request.POST["submit"] == "Add":

            cursor.execute(
                """ INSERT INTO [TT].[dbo].[Testbooth_Master] ( 
             "Test_Code"  
            ,"Test_Category" 
            ,"Test_Category_Seq" 
            ,"Tpl_No" 
            ,"Test_Code_Seq_No"  
            ,"Fan_Motor_Current_Measurement"
            ,"Number_of_Fans"
            ,"VFD_Model_Testing"
            ,"Oil_Recommended"
            ,"VFD"
            ,"Dryer"
            ,"Belt_Driven"
            ,"SPM_Reading_Color")VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", request.POST["Test_Code"],
                request.POST["Test_Category"],request.POST["Test_Category_Seq"], request.POST["Tpl_No"],
                request.POST["Test_Code_Seq_No"],request.POST["Fan_Motor_Current_Measurement"],request.POST["Number_of_Fans"]
                ,request.POST["VFD_Model_Testing"],request.POST["Oil_Recommended"],request.POST["VFD"]
                ,request.POST["Dryer"],request.POST["Belt_Driven"],request.POST["SPM_Reading_Color"])
            cursor.commit()

        elif request.POST["submit"] == "Edit":
            cursor.execute(
                """
                UPDATE [TT].[dbo].[Testbooth_Master]
               SET "Test_Code"=?  
            ,"Test_Category" =?
            ,"Test_Category_Seq"=? 
            ,"Tpl_No" =?
            ,"Test_Code_Seq_No"=?  
            ,"Fan_Motor_Current_Measurement"=?
            ,"Number_of_Fans"=?
            ,"VFD_Model_Testing"=?
            ,"Oil_Recommended"=?
            ,"VFD"=?
            ,"Dryer"=?
            ,"Belt_Driven"=?
            ,"SPM_Reading_Color"=? WHERE PMMKEY = ?""",  request.POST["Test_Code"],
                request.POST["Test_Category"],request.POST["Test_Category_Seq"], request.POST["Tpl_No"],
                request.POST["Test_Code_Seq_No"],request.POST["Fan_Motor_Current_Measurement"],request.POST["Number_of_Fans"]
                ,request.POST["VFD_Model_Testing"],request.POST["Oil_Recommended"],request.POST["VFD"]
                ,request.POST["Dryer"],request.POST["Belt_Driven"],request.POST["SPM_Reading_Color"],request.POST["PMMKEY"])
            cursor.commit()

        elif request.POST["submit"] == "Delete":
            cursor.execute(
                """
                DELETE FROM [TT].[dbo].[Testbooth_Master]
                WHERE PMMKEY = ?""", request.POST["PMMKEY"])
            cursor.commit()
    #query for test_code dropdown in testbooth master screen
    test_code_details = cursor.execute(
        """SELECT  [Test_Code]  FROM [TT].[dbo].[Testbooth_Library]""")
    test_code_data = [obj[0] for obj in test_code_details]
    print("test_code_data  ",test_code_data)

    #query for tpl_code dropdown in testbooth master screen
    tpl_code_details = cursor.execute(
        """SELECT DISTINCT  [TPL_No] FROM [TT].[dbo].[TPL_Master]""")
    tpl_code_data = [obj[0] for obj in tpl_code_details]

    #query for test_category dropdown in testbooth master screen
    test_category_details = cursor.execute(
        """SELECT *  FROM [TT].[dbo].[Testbooth_Test_Type]""")
    test_category_data = [obj[1] for obj in test_category_details]

    return render(request,'Testbooth/testboothmst.html',{'test_code_data':test_code_data,'tpl_code_data':tpl_code_data,
                                               "test_category_data":test_category_data})





def rework_station(request,tpl_no,fab_no):
    cursor = db_connection()
    user_name = str(request.user)
    print("*****",tpl_no)

    assembly_details = cursor.execute("SELECT TPL_No ,Fab_No, Station_ID,Process_Seq_No, Process_Code, Process_Desc, Process_Status,  Skip_Reason FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? and Fab_No = ?",tpl_no,fab_no)
    assembly_data = [{"TPL_No":obj[0], "Fab_No":obj[1], "Station_ID":obj[2],"Process_Seq_No":obj[3], "Process_Code":obj[4], "Process_Desc":obj[5], "Process_Status":obj[6], "Skip_Reason":obj[7]}
                     for obj in assembly_details]
    # print("assembly_data******",assembly_data)

    pdi_details = cursor.execute("select * FROM [TT].[dbo].[PDI_Process_Update_Table] WHERE TPL_No = ? and Fab_No = ?",tpl_no,fab_no)
    pdi_data = [{"TPL_No":obj[0],"Fab_No":obj[1],"Station_id":obj[2],"Emp_Name":obj[3],"Emp_ID":obj[4],"Order_Number":obj[5],
                 "CL_Code":obj[6],"CL_Type_Code":obj[7],"status":obj[8],"img_url":obj[9],"Actual_Time":obj[10],"Process_Status":obj[11]} for obj in pdi_details]

    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Photo_Path": static("images/users/" + str(obj[2]))
    } for obj in cursor.execute(employee_details_query, user_name)]
    # print("employee_details_list******",employee_details_list)

    employee_skill_query = """ SELECT Sub5_OP1 FROM [TT].[dbo].[Emp_Skill_Matrix] WHERE Emp_ID=? """
    employee_skill_list = [obj for obj in cursor.execute(employee_skill_query, user_name)]
    Skill_Level = employee_skill_list[0][0]
    employee_details_list[0].update({"Skill_Level": Skill_Level})

    # processupdate_details = cursor.execute("SELECT TPL_No ,Fab_No, Station_ID, Process_Code, Process_Desc, Process_Status,  Skip_Reason FROM [TT].[dbo].[Process_Update_Table] WHERE TPL_No = ? and Fab_No = ?",tpl_no,fab_no)

    return render(request, 'rework_station/process_list.html', {'assembly_data':assembly_data, "pdi_data":pdi_data, "TPL_No":tpl_no,"Fab_No":fab_no, "employee_details_list":employee_details_list[0]})





@csrf_exempt
def rework_submit(request):
    cursor = db_connection()

    print("hello")
    # for key, value in request.POST.items():
    #     print('Key: %s' % (key))
    #     print('Value %s' % (value))
    tplno = request.POST["Tpl_No"]
    fabno = request.POST["Fab_No"]

    update_seq_query = """UPDATE [TT].[dbo].[Process_Update_Table]
                            SET Process_Status = 'C'
                            WHERE Process_Status = 'S' AND TPL_No = ? AND Fab_No = ?"""
    cursor.execute(update_seq_query, tplno, fabno)

    check_skip_query = """SELECT *
  FROM [TT].[dbo].[Process_Update_Table]
  WHERE Process_Status = 'S' AND TPL_No = ? AND Fab_No = ?
"""
    cursor.execute(check_skip_query, tplno, fabno)
    data = cursor.fetchall()
    print("tplno and fabno", tplno, fabno, data)
    return HttpResponse("Submit")
    # return redirect(station_order_release("Rework_OP1"))

@login_required(login_url='login')
def package_station(request,TPL_No,FAB_NO):
    cursor = db_connection()
    user_name = str(request.user)
    employee_details_query = """ SELECT * FROM [TT].[dbo].[Employee_Details_View] WHERE User_Name=? """
    employee_details_list = [{
        "Emp_ID": obj[0],
        "Emp_Name": obj[1],
        "Skill_Level": obj[2],
        "Photo_Path": static("images/users/" + str(obj[3]))
    } for obj in cursor.execute(employee_details_query, user_name)]
    print("employee_details_list",employee_details_list)

    if request.method=="POST":
        print("******************")

        for key,value in request.POST.items():
            print("key: %s" %(key))
            print("value: %s" %(value))

        TPL_No = request.POST['TPL_No']
        # TPL_Description = request.POST['TPL_Description']
        FAB_NO = request.POST['FAB_NO']
        Package_Code = request.POST['Package_Code']
        # Emp_ID = request.POST['Emp_ID']
        # Date_Time = request.POST['Date_Time']
        if request.POST["submit"] == "Update":

            cursor.execute(
                            """ INSERT INTO [TT].[dbo].[Package_Station] (
                                    "TPL_No"
                                  ,"FAB_NO"
                                  ,"Package_Code"
                                  ,"Emp_ID"
                                  ,"Date_Time"
                                  )VALUES (?,?,?,?,?)""", request.POST["TPL_No"]
                             ,request.POST["FAB_NO"], request.POST["Package_Code"],user_name
                            ,datetime.datetime.now().isoformat(" ").split(".")[0])
            cursor.commit()
            return redirect(station_order_release, station_id='Packing1_OP1')


    packing_details = cursor.execute(
        """SELECT [Package_Code]  FROM [TT].[dbo].[Packing_DD]""")
    packing_data = [obj[0] for obj in packing_details]
    print("packing_data ", packing_data)

    # emp_id = cursor.execute(
    #     """SELECT [Emp_ID]  FROM [TT].[dbo].[Employee_Details_UPD]""")


    return render(request, 'stations/package_station.html',{'packing_data':packing_data,'TPL_No':TPL_No,'FAB_NO':FAB_NO,'employee_details':employee_details_list[0]})#'emp_id':emp_id
def pditest(request):
    return render(request, 'pditestingfile.html')




def tool_master(request):
    return render(request, 'general/underdevelopment.html')


def tool_warning_master(request):
    return render(request, 'general/underdevelopment.html')

def newassemblytest(request):
    return render(request, 'new_assembly_test.html')

