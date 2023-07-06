from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns =[
    path('', views.signin, name="home"),
    path('login', views.signin, name="login"),
    path('logout', views.signout, name="logout"),
    path('noaccess/', views.no_access, name="no_access"),

    path('dashboard/', views.home, name="dashboard"),

    #Master Configuration
    path('company/', views.company, name="company"),
    path('tplmaster/', views.tpl_master, name="tplmaster"),
    path('toolmaster/', views.tool_master, name="toolmaster"),
    path('processmaster', views.process_master, name="processmaster"),
    path('employee/', views.employee, name="Employee"),
    path('toolwarningmaster/', views.tool_warning_master, name="toolwarningmaster"),
    path('packing/', views.packing, name="packing"),
    path('drivecouplingmaster', views.drive_coupling_master, name="drivecouplingmaster"),
    path('pdi_master/', views.pdi_master, name="pdi_master"),

    path('activetpllist/<str:tpl_code>/<str:operation_code>', views.active_tpl_list, name="activetpllist"),

    #LN API Tables
    path('childpartdetails/', views.child_part_details, name="childpartdetails"),
    path('orderrelease/', views.order_release, name="order_release"),
    path('orderreleaseerrortable/', views.order_release_error_table, name="order_release_error_table"),

    #Child Part
    # path('childpartdropdown', views.child_part_dropdown, name="child_part_dropdown page"),

    #Schedule
    path('breakdisplayconfiguration/', views.break_display_configuration, name="breakdisplayconfiguration"),
    path('holidays/', views.holidays, name="holidays"),
    path('messages/', views.messages, name="messages"),
    path('messageconfiguration/', views.message_configuration, name="messageconfiguration"),
    path('shiftandbreak/', views.breakandshift, name="shift_and_break"),

    #StationByPass
    path('stationbypass', views.station_bypass, name="station_bypass"),

    #Tool Master
    path('toolmaintenance/', views.tool_maintenance, name="toolmaintenance"),
    path('tooltraceability/', views.tool_traceability_list, name="tool_traceability"),

    #Test Booth
    path('testboothlib/',views.testboothlib, name="testbooth_library"),
    path('testboothmst/',views.testboothmst, name="testbooth_master"),

    # Operator Screen
    # path('listoffabnumber', views.list_of_fab_number, name="List Of Fab Number"),
    # path('scanfabnumber', views.scan_fab_number, name="Scan Fab Number"),
    # path('starttest', views.start_test, name="Start Test"),

    #Alphaline Stations
    path('stations/', views.stations_list, name="stations page"),
    path('stations/<str:station_id>/', views.station_order_release, name="stations homepage"),
    path('stations/<str:station_id>/<str:tplno>/<str:fabno>', views.substation, name="substation"),
    path('store/', views.store, name="store"),
    path('dms_master/', views.dms_master, name="dms_master"),
    path('dms_app/', views.dms_app, name="dms_app"),
    path('substationapi',views.substation_api, name="sub station api"),
    path('torqueapi', views.torque_api, name="torqueapi"),
    path('qlossapi', views.qloss_api, name="qlossapi"),
    path('drivecoupling', views.drive_coupling_api, name="drivecoupling"),
    path('package_station/<str:TPL_No>/<str:FAB_NO>', views.package_station, name="package_station"),

    # pdi
    path('pdi_inspection_process/<str:tplno>/<str:fabno>', views.pdi_inspection_process, name="pdi_inspection_process"),
    path('pdi_inspection_api/', views.pdi_inspection_api, name="pdi_inspection_api"),

    # path('cleco_torque', views.cleco_tool, name="torque_test_page"),
    # path('digital_torque', views.digital_tool, name="torque_test_page"),
    # path('process', views.process, name="Process Screen development"),
    # path('process_p', views.process_p, name="Process Screen development"),
    # path('dmi', views.dmi, name="dmi"),
    # path('pdi', views.pdi, name="pdi"),
    # path('testboothmaster', views.test_booth_master, name="Test Booth Master"),
    # path('testcertificate1', views.test_certificate_1, name="Test Certificate 1"),
    # path('testcertificate2', views.test_certificate_2, name="Test Certificate 2"),
    # path('testcertificate3', views.test_certificate_3, name="Test Certificate 3"),
    # path('testcertificate4', views.test_certificate_4, name="Test Certificate 4"),
    # path('testcertificate5', views.test_certificate_5, name="Test Certificate 5"),
    # path('testcertificate6', views.test_certificate_6, name="Test Certificate 6"),
    # path('testcertificate7', views.test_certificate_7, name="Test Certificate 7"),
    # path('testcertificate8', views.test_certificate_8, name="Test Certificate 8"),
    # path('pdi_2', views.pdi_2, name="pdi_2"),
    # path('pdi_3', views.pdi_3, name="pdi_3"),
    # path('reports', views.reports, name="reports"),
    # path('compressprocessstatus', views.compressprocessstatus, name="compressprocessstatus"),
    # path('lnserverstatus', views.lnserverstatus, name="lnserverstatus"),
    # path('processstatus', views.processstatus, name="processstatus"),
    # path('lnerpstatus', views.lnerpstatus, name="lnerpstatus"),
    # path('tpldetails', views.tpldetails, name="tpldetails"),
    # path('processsequence', views.processsequence, name="processsequence"),
    # path('alphaline', views.alpha_line, name="alpha_line page"),
    # path('station_order_release', views.station_order_release, name="station_order_release"),
    # path('substation/<str:tplno>/<str:fabno>', views.substation, name="substation"),
    # path('alphalinesample', views.alphalinesample, name="alphalinesample page"),
    # path('substationbase',views.substation_base, name="substationbase"),
    # path('camera_test', views.camera_test, name="camera_test"),
    # path('del_record/<str:db>/<str:uid>', views.del_record, name="del_record"),

    path('pditest',views.pditest, name="pditest"),
    # path('newassemblytest', views.newassemblytest, name='new_assembly_test')


    #rework
    path('rework_station/<str:tpl_no>/<str:fab_no>', views.rework_station, name='rework_station'),
    path('rework_submit/', views.rework_submit, name='rework_submit'),

]

if settings.DEBUG:
    #urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
