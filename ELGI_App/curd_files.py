
import pyodbc

def db_connection():
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=PROD-DF;DATABASE=TT;UID=MEI_DF;PWD=MEI@mac;Trusted_Connection=yes')
    cursor = conn.cursor()
    return cursor




# # select data from db
# cursor = db_connection()
# process_master_details = cursor.execute(
#     "SELECT * FROM[TT].[dbo].[Process_Master]")
#
# process_master_data = [{
#     "Line_Code": obj[0], "Pro_Type_Code": obj[1], "Process_Desc": obj[2], "Tool_ID": obj[3],
#     "Process_Code": obj[4], "Bolt_Count": obj[5], "Process_Photo_Path": obj[6], "Takt_Time": obj[7],
#     "Torque": obj[8]
# } for obj in process_master_details]
# print(process_master_data)


# # insert
# cursor = db_connection()
# cursor.execute(
#                """ INSERT INTO [TT].[dbo].[LN_CP_Details] (
# 		"TPL_Number"
#       ,"Part_No"
#       ,"Part_No_Rev"
#       ,"Child_Part_Code"
#       ,"Fab_Number"
#       )VALUES (?,?,?,?,?)""","S013370","X990825", "R01",
#            "CP_DRIVEN_PULLEY","BWAC379154")
# cursor.commit()
#
#
# # update
# cursor = db_connection()
# cursor.execute(
#     """
#     UPDATE [TT].[dbo].[LN_Order_Release]
#    SET "Status" = 'R'
#  WHERE FAB_NO = 'BVGC377517' """)
# cursor.commit()
# #
# cursor.execute(
#     """
#     UPDATE [TT].[dbo].[LN_CP_Details]
#    SET "TPL_Number" = 'tpl_101'
#  WHERE Fab_Number = 'AUES03520' and Child_Part_Code = 'CP_AIREND_CHECK' """)
# cursor.commit()
#

#
# delete
cursor = db_connection()
cursor.execute(
    """
    DELETE FROM [TT].[dbo].[Process_Update_Table]

    """)
cursor.commit()


# update
# cursor = db_connection()
#
# TPL_MASTER = cursor.execute(
#     "SELECT * FROM[TT].[dbo].[Process_Map_Master]")
#
# TPL_MASTER_DATA = [{
#     "tpl": obj[2]
# } for obj in TPL_MASTER]
# print(len(TPL_MASTER_DATA))
#
# for data in TPL_MASTER_DATA:
#     cursor = db_connection()
#     tpl = data["tpl"]
#     print("***** tpl *****",tpl)
#     cursor.execute
#
#     (
#         """
#         UPDATE [TT].[dbo].[Process_Map_Master]
#        SET "Model_Group" = ?
#      WHERE Model_Code = ? """,tpl[:2] , tpl)
#     cursor.commit()




#edit query in tmaster afterclick
# cursor.execute(
#                 """
#                 UPDATE [TT].[dbo].[Testbooth_Master]
#                SET "Test_Code"=?
#             ,"Test_Category" =?
#             ,"Test_Category_Seq"=?
#             ,"Tpl_No" =?
#             ,"Test_Code_Seq_No"=?
#             ,"Fan_Motor_Current_Measurement"=?
#             ,"Number_of_Fans"=?
#             ,"VFD_Model_Testing"=?
#             ,"Oil_Recommended"=?
#             ,"VFD"=?
#             ,"Dryer"=?
#             ,"Belt_Driven"=?
#             ,"SPM_Reading_Color"=? WHERE TPL_No = ?""",  request.POST["Test_Code"],
#                 request.POST["Test_Category"], request.POST["Tpl_No"],
#                 request.POST["Test_Code_Seq_No"],request.POST["Fan_Motor_Current_Measurement"],request.POST["Number_of_Fans"]
#                 ,request.POST["VFD_Model_Testing"],request.POST["Oil_Recommended"],request.POST["VFD"]
#                 ,request.POST["Dryer"],request.POST["Belt_Driven"],request.POST["SPM_Reading_Color"],request.POST["PMMKEY"])
#             cursor.commit()
#
#
# cursor.execute(
#                 """
#                 DELETE FROM [TT].[dbo].[Testbooth_Master]
#                 WHERE TPL_No = ?""", request.POST["TPL_No"])
#             cursor.commit()


# cursor = db_connection()
# cursor.execute(
#                 """
#                 DELETE FROM [TT].[dbo].[Testbooth_Master]
#                 WHERE TPL_No = ?""", "")#tpl_no
# cursor.commit()


# cursor = db_connection()
# cursor.execute(
#                 """
#                 UPDATE [TT].[dbo].[Testbooth_Master]
#                SET "Test_Code"=?
#             ,"Test_Category" =?
#             ,"Test_Category_Seq"=?
#             ,"TPL_No" =?
#             ,"Test_Code_Seq_No"=?
#             ,"Fan_Motor_Current_Measurement"=?
#             ,"Number_of_Fans"=?
#             ,"VFD_Model_Testing"=?
#             ,"Oil_Recommended"=?
#             ,"VFD"=?
#             ,"Dryer"=?
#             ,"Belt_Driven"=?
#             ,"SPM_Reading_Color"=? WHERE TPL_No = ?""",  "testcode10",
#                  "Fan_Motor_Current_Measurement",
#                 "3","EGG TPL","1"
#                 ,"Auto Mode","1","vfdtestvalue"
#                 ,"oilvalue","vfdvalue","dryervalue","beltvalue","spmvalue","EG TPL")
# cursor.commit()


# details= cursor.execute(
#         """SELECT DISTINCT [Test_Code],[Test_Category],[Test_Category_Seq],[TPL_No],
#         [Test_Code_Seq_No],[Fan_Motor_Current_Measurement],[Number_of_Fans],[VFD_Model_Testing]
#         ,[Oil_Recommended],[VFD],[Dryer],[Belt_Driven],[SPM_Reading_Color] FROM [TT].[dbo].[Testbooth_Master]""")
#
# data = [{'Test_Code': obj[1], 'Test_Category': obj[2], 'Test_Category_Seq': obj[3]
#                            ,'TPL_No': obj[4],'Test_Code_Seq_No': obj[5],'Fan_Motor_Current_Measurement': obj[6]
#             ,'Number_of_Fans': obj[7],'VFD_Model_Testing': obj[8],'Oil_Recommended':obj[9],'VFD': obj[10],'Dryer': obj[11]
#             ,'Belt_Driven': obj[12],'SPM_Reading_Color': obj[13]} for obj in details]
#
#

# cursor = db_connection()
# activetest_tpl_details = cursor.execute(
#      "SELECT DISTNCT [TPL_No],[TPL_Description],[Test_Category],[No_of_Tests],[Total_Tests] FROM[TT].[dbo].[Active_Test_TPL_List44]")
#
#
# activetest_tpl_data=[{
#      "TPL_No": obj[0], "TPL_Description": obj[1], "Test_Category": obj[2],
#      "No_of_Tests": obj[3], "Total_Tests": obj[4]} for obj in activetest_tpl_details]








