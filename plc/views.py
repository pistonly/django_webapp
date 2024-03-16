from django.shortcuts import render

# Create your views here.
from .plc_control import plcControl
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.is_superuser or user.is_staff

plc = plcControl()

@login_required
@api_view(['get'])
def plc_connected(request):
    return Response({"connected": plc.connected()})

@login_required
@api_view(['POST'])
def get_selected_registers(request):
    # get M
    reg_values = {}
    for m in ['M202', 'M1', 'M11', 'M212', 'M4', 'M14']:
        success, v = plc.get_M(m)
        if success:
            reg_values.update({m: v})

    for d in ['D850', 'D864', 'D856', 'D870', 'D814', 'D812']:
        success, v = plc.read_D(d)
        if success:
            reg_values.update({d: v})
    return Response({'reg_values': reg_values})


@login_required
@api_view(['POST'])
def plc_setM(request):
    address_name = request.data.get("register")
    value = request.data.get("value")
    success, message = plc.set_M(address_name, int(value))
    if success:
        return Response({"message": message}, status=status.HTTP_200_OK)
    else:
        return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST'])
def plc_getM(request):
    address_name = request.data.get("register")
    success, value = plc.get_M(address_name)
    if success:
        return Response({"value": value}, status=status.HTTP_200_OK)
    else:
        return Response({"value": value}, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST'])
def plc_writeD(request):
    address_name = request.data.get("register")
    value = request.data.get("value")
    success, message = plc.write_D(address_name, int(value))
    if success:
        return Response({"message": message}, status=status.HTTP_200_OK)
    else:
        return Response({"message": message}, status=status.HTTP_400_BAD_REQUEST)


@login_required
@api_view(['POST'])
def plc_readD(request):
    address_name = request.data.get("register")
    success, value = plc.read_D(address_name)
    if success:
        return Response({"value": value}, status=status.HTTP_200_OK)
    else:
        return Response({"value": value}, status=status.HTTP_400_BAD_REQUEST)
