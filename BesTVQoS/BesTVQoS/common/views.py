﻿# -*- coding: utf-8 -*-

"""
Definition of views.
"""

import logging
import json

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import Context
from django.db import connection
from navi import Navi
from date_time_tool import today

logger = logging.getLogger("django.request")


def home(request):
    logger.debug("Qos request")
    return render_to_response('index.html', Context())

def p_home(request):
    return render_to_response('home.html', Context())

def m_home(reuest):
    context = {}
    context["is_mobile"] = True
    context["top_title"] = "BesTV QoS Monitor"
    #context["navi"] = Navi().get_sub_items()

    return render_to_response('m_navi_menu.html', context)


def navi(request, target_url=""):
    if target_url:
        navi = Navi()
        navi_path = navi.get_path(request.path)
        context = {}
        context["navi"] = navi.get_sub_items(request.path)
        context["is_mobile"] = True
        context["top_title"] = navi_path[-1].name
        context["show_topbar"] = True
        context["path"] = navi_path[:-1]
        return render_to_response('m_navi_menu.html', context)
    else:
        return m_home(request)


def get_device_types1(table, service_type, begin_date, end_date, cu=None):
    fitlers = "where Date >= '%s' and Date <= '%s'" % (begin_date, end_date)
    if service_type != "All":
        fitlers = fitlers + " and ServiceType = '%s'" % (service_type)
    sql_command = "select distinct DeviceType from %s %s" % (table, fitlers)
    sql_command += " and DeviceType not like '%.%'"

    if cu is None:
        cu = connection.cursor()

    logger.debug("SQL %s" % sql_command)
    cu.execute(sql_command)

    device_types = []
    for item in cu.fetchall():
        device_types.append(item[0].encode('utf-8'))

    if len(device_types) == 0:
        device_types = ['']

    return device_types


def get_device_types(table, service_type, begin_date, end_date):
    device_types = []

    if service_type == "All":
        q = table.objects.filter(Date__gte=begin_date, Date__lte=end_date).exclude(
            DeviceType__contains='.').values('DeviceType').distinct()
    else:
        q = table.objects.filter(
            ServiceType=service_type, Date__gte=begin_date, Date__lte=end_date).exclude(
                DeviceType__contains='.').values('DeviceType').distinct()

    if len(q) > 0:
        device_types = [i["DeviceType"] for i in q]

    return device_types


def get_versions(table, service_type, device_type, begin_date, end_date):
    versions = ["All"]

    if device_type == "":
        return versions

    version_patten = '%s_' % (device_type)

    if service_type == "All":
        q = table.objects.filter(
            Date__gte=begin_date, Date__lte=end_date, DeviceType__contains=version_patten).values('DeviceType').distinct()
    else:
        q = table.objects.filter(
            ServiceType=service_type, Date__gte=begin_date, Date__lte=end_date, DeviceType__contains=version_patten).values(
                'DeviceType').distinct()

    if len(q) > 0:
        version_pos = len(device_type) + 1
        for i in q:
            versions.append(i["DeviceType"][version_pos:])

    return versions


def get_table_name(url):
    table_name = ""
    if url.find("playing_trend") != -1:
        table_name = "playinfo"
    elif url.find("fbuffer") != -1:
        table_name = "fbuffer"
    elif url.find("play_time") != -1:
        table_name = "playtime"
    elif url.find("fluency") != -1:
        table_name = "fluency"
    elif url.find("3sratio") != -1:
        table_name = "Bestv3SRatio"
    elif url.find("avg_pcount") != -1 or url.find("avg_ptime") != -1:
        table_name = "BestvAvgPchoke"

    return table_name


def get_device_type(request, dev=""):
    respStr = json.dumps({"device_types": []})
    if(request.method == 'GET'):
        try:
            service_type = request.GET.get('service_type')
            begin_date = request.GET.get('begin_date')
            end_date = request.GET.get('end_date')
            url = request.META.get('HTTP_REFERER')

            table_name = get_table_name(url)

            device_types = get_device_types1(
                table_name, service_type, begin_date, end_date)
            respStr = json.dumps({"device_types": device_types})

        except Exception, e:
            raise e

    return HttpResponse(respStr, content_type="text/json")


def get_versions1(table, service_type, device_type, begin_date, end_date, cu=None):
    fitlers = "where Date >= '%s' and Date <= '%s'" % (begin_date, end_date)
    if service_type != "All":
        fitlers = fitlers + " and ServiceType = '%s'" % (service_type)
    fitlers += " and DeviceType like '%s_%%'" % (device_type)
    sql_command = "select distinct DeviceType from %s %s" % (table, fitlers)

    if cu is None:
        cu = connection.cursor()

    logger.debug("SQL %s" % sql_command)
    cu.execute(sql_command)

    version_pos = len(device_type) + 1
    device_types = ["All"]
    for item in cu.fetchall():
        device_types.append(item[0][version_pos:])

    return device_types


def get_version(request, dev=""):
    respStr = json.dumps({"versions": []})
    if(request.method == 'GET'):
        try:
            service_type = request.GET.get('service_type')
            device_type = request.GET.get('device_type')
            begin_date = request.GET.get('begin_date')
            end_date = request.GET.get('end_date')
            url = request.META.get('HTTP_REFERER')

            table_name = get_table_name(url)

            versions = get_versions1(
                table_name, service_type, device_type, begin_date, end_date)
            respStr = json.dumps({"versions": versions})

        except Exception, e:
            raise e

    return HttpResponse(respStr, content_type="text/json")


def get_default_values_from_cookie(request):
    filter_map = json.loads('{"st":"All","dt":"","vt":"","begin":"%s","end":"%s"}' % (
        today(), today()))
    try:
        filter_map = json.loads(request.COOKIES["bestvFilters"])
        if("st" not in filter_map or "dt" not in filter_map or "vt" not in filter_map or
                "begin" not in filter_map or "end" not in filter_map):
            raise Exception()
    except:
        logger.info("Loads Cookie['bestvFilters'] failed! ")

    return filter_map


def set_default_values_to_cookie(response, context):
    response.set_cookie("bestvFilters",
                        json.dumps({"st": context["default_service_type"],
                                    "dt": context["default_device_type"],
                                    "vt": context["default_version"],
                                    "begin": context['default_begin_date'],
                                    "end": context['default_end_date']}),
                        max_age=30000)
