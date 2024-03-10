from django.urls import path
from . import views

urlpatterns = [
    path("plc/connected", views.plc_connected, name='plc_connected'),
    path("plc/setM", views.plc_setM, name='plc_setM'),
    path("plc/getM", views.plc_getM, name='plc_getM'),
    path("plc/writeD", views.plc_writeD, name='plc_writeD'),
    path("plc/readD", views.plc_readD, name='plc_readD'),
    path("plc/get_selected_registers", views.get_selected_registers, name='plc_get_selected_registers'),
]
