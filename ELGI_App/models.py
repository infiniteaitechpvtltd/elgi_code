from django.db import models
from django.contrib.auth.admin import User


class Employee_Details(models.Model):
    class Meta():
        permissions = [
            ("employee_page_view","employee page view"),("station_view","station view"),("admin_view", "admin view"), ("supervisor_view", "supervisor view")
        ]
    objects = models.Manager()
    Username = models.OneToOneField(User, on_delete=models.CASCADE)
    Employee_ID = models.IntegerField()
    Employee_Name = models.CharField(max_length=30)
    Company_Code = models.CharField(max_length=30)
    Employee_Photo_Path = models.CharField(max_length=30)
    Employee_Department = models.CharField(max_length=30)

class Station_Details(models.Model):
    objects = models.Manager()
    Station_ID = models.CharField(max_length=30)
    Skill_Required = models.IntegerField()

    def __str__(self):
        return self.Station_ID
