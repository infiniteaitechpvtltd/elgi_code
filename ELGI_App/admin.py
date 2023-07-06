from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Employee_Details, Station_Details
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
class EmployeeDetailsInline(admin.StackedInline):
    model = Employee_Details
    can_delete = False

class AccountsUserAdmin(AuthUserAdmin):
    inlines=(EmployeeDetailsInline,)

admin.site.unregister(User)
admin.site.register(User,AccountsUserAdmin)
admin.site.register(Station_Details)


