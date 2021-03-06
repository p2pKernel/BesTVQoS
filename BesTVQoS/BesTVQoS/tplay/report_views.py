# -*- coding: utf-8 -*-
import logging
import xlwt

from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from common.views import write_xls, write_remarks_to_xls, HtmlTable
from common.date_time_tool import current_time
from tplay.functions import get_filter_param_values
from tplay.views import VIEW_TYPES
from tplay.models import BestvPlayinfo, BestvFbuffer, BestvFluency, \
    BestvPlaytime
from tplayloading.models import VersionInfo, TPlayloadingInfo

import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )

ezxf=xlwt.easyxf

logger = logging.getLogger("django.request")

STUCK = 2
DBUFFER = 3

def get_records_data(view_types, begin_date, end_date, service_type, beta_ver, master_ver):
    qos_data = []
    vers = []
    if len(beta_ver)>0:
        vers.append(beta_ver)
    if len(master_ver)>0:
        vers.append(master_ver)

    for ver in vers:        
        Q_conditions = Q(ServiceType=service_type) & Q(DeviceType=ver)
        if service_type == "B2C":
            Q_conditions = Q_conditions & Q(ISP='all') & Q(Area='all')
        Q_conditions = Q_conditions & Q(ViewType__in=[view_type[0] for view_type in view_types]) 
        Q_conditions = Q_conditions & \
            Q(Date__gte=begin_date) & Q(Date__lte=end_date)        
        Q_conditions = Q_conditions & Q(Hour=24)

        begin_time = current_time()
        playinfos = BestvPlayinfo.objects.filter(Q_conditions)
        view_type_data = {}
        for (view, _) in view_types:
            view_type_data[view] = 0
        for playinfo in playinfos:
            view_type_data[playinfo.ViewType] += playinfo.Records

        temp = []
        temp.append("%s"%(ver))
        for (view, _) in view_types:
            temp.append(view_type_data[view])
        temp.append(sum(view_type_data.values()))
        qos_data.append(temp)
        logger.info("execute sql: ver: %s, get records, cost: %s" % (ver, (current_time() - begin_time)))

    return qos_data

def get_single_qos_data2(view_types, begin_date, end_date, service_type, beta_ver, master_ver):
    qos_data = []
    vers = []
    if len(beta_ver)>0:
        vers.append(beta_ver)
    if len(master_ver)>0:
        vers.append(master_ver)
    
    single_qos = [BestvFbuffer, BestvFluency, BestvFluency]
    qos_name = ['SucRatio', 'Fluency', 'PRatio']
    qos_desc = [u'首次缓冲成功率', u'一次不卡比例', u'卡用户卡时间比']
    for index, qos in enumerate(qos_name):
        for ver in vers:
            temp = []
            temp.append("%s-%s"%(qos_desc[index], ver))

            Q_conditions = Q(ServiceType=service_type) & Q(DeviceType=ver)
            if service_type == "B2C":
                Q_conditions = Q_conditions & Q(ISP='all') & Q(Area='all')
            Q_conditions = Q_conditions & Q(ViewType__in=[view_type[0] for view_type in view_types]) 
            Q_conditions = Q_conditions & \
                Q(Date__gte=begin_date) & Q(Date__lte=end_date)            
            Q_conditions = Q_conditions & Q(Hour=24)

            begin_time = current_time()      
            items = single_qos[index].objects.filter(Q_conditions)
            view_type_data = {}
            for (view, _) in view_types:
                view_type_data[view] = []
            for item in items:
                qos_value = getattr(item,qos)
                if qos_value:
                    view_type_data[item.ViewType].append(qos_value)
            for (view, _) in view_types:
                if view_type_data[view]:
                    temp.append(float("%.3f"%(sum(view_type_data[view])/len(view_type_data[view]))))
                else:
                    temp.append(0)
                logger.info("qos count: ver: %s, get %s, count: %s" % (ver, qos, len(view_type_data[view])))
            qos_data.append(temp)
            logger.info("execute sql: ver: %s, get %s, cost: %s" % (ver, qos, 
                    (current_time() - begin_time)))

    return qos_data

# p25, 50, 75, 90, 95, avg
def get_multi_qos_data(table, view_types, begin_date, end_date, 
    service_type, beta_ver, master_ver, p95_exception_value, base_radis=1):
    qos_data = []
    vers = []
    if len(beta_ver)>0:
        vers.append(beta_ver)
    if len(master_ver)>0:
        vers.append(master_ver)

    for (view, second) in view_types:
        for ver in vers:
            begin_time = current_time()
            temp = [0 for i in range(7)]
            temp[0] = u"%s-%s" % (ver, second)

            Q_conditions = Q(ServiceType=service_type) & Q(DeviceType=ver)
            if service_type == "B2C":
                Q_conditions = Q_conditions & Q(ISP='all') & Q(Area='all')
            Q_conditions = Q_conditions & Q(ViewType=view) 
            Q_conditions = Q_conditions & \
                Q(Date__gte=begin_date) & Q(Date__lte=end_date)            
            Q_conditions = Q_conditions & Q(Hour=24)

            count = 0
            items = table.objects.filter(Q_conditions)
            for item in items:
                if item.P95 < p95_exception_value:
                    continue
                temp[1]+=item.P25
                temp[2]+=item.P50
                temp[3]+=item.P75
                temp[4]+=item.P90
                temp[5]+=item.P95
                temp[6]+=item.AverageTime
                count += 1
            if count > 0:
                for i in range(6):
                    temp[i+1] = temp[i+1]/count/base_radis

            qos_data.append(temp)
            logger.info("execute sql: ver: %s, pnvalues, cost: %s" % (ver, 
                    (current_time() - begin_time)))

    return qos_data

def get_playtm_data(begin_date, end_date, service_type, beta_ver, master_ver):
    return get_multi_qos_data(BestvPlaytime, VIEW_TYPES[1:4], 
        begin_date, end_date, service_type, beta_ver, master_ver, 1800, 60)

def get_fbuffer_data(begin_date, end_date, service_type, beta_ver, master_ver):
    return get_multi_qos_data(BestvFbuffer, VIEW_TYPES[1:4],
        begin_date, end_date, service_type, beta_ver, master_ver, 3)

def get_desc_for_daily_report(begin_date, end_date, beta_ver, master_ver=""):
    desc = [
        [u'日期: %s - %s' % (begin_date, end_date)],
        [u'%s -- %s' % ('首选版本', beta_ver)]
        ]
    if len(master_ver)>0:
        desc.append([u'%s -- %s'%('对比版本', master_ver)])
    return desc

def generate_report(wb, begin_date, end_date, service_type, device_type, version, version2=""):
    begin_time = current_time()
    (beta_ver, master_ver)=get_version_version2(device_type, version, version2)

    book = wb
    sheet = book.add_sheet("version-report")
    sheet.col(0).width=10000
    
    heading_xf = ezxf('borders: left thin, right thin, top thin, bottom thin; \
        font: bold on; pattern: pattern solid, fore_colour bright_green')
    data_xf = ezxf('borders: left thin, right thin, top thin, bottom thin; \
        font: name Arial')

    rowx = 0

    #
    # step 0: spec
    #
    spec_xf = ezxf('font: name Arial, colour Red')
    spec_data = get_desc_for_daily_report(begin_date, end_date, \
        beta_ver, master_ver)
    
    rowx = write_xls(book, sheet, rowx, [], spec_data, [], spec_xf)
    rowx += 2
    
    #
    # step 1: records
    #
    records_headings = [u'记录数/版本', u'点播', u'回看', u'直播', u'连看', u'总计']
    # prepare data
    records_data = get_records_data(VIEW_TYPES[1:5], begin_date, end_date, service_type, \
        beta_ver, master_ver)
    rowx = write_xls(book, sheet, rowx, records_headings, records_data, 
        heading_xf, data_xf)
    rowx += 2
    print "step 1: ", current_time() - begin_time
    #
    # step 2: single Qos
    #     
    single_qos_headings = [u'单指标QoS/版本', u'点播', u'回看', u'直播', u'连看']
    single_qos_data = get_single_qos_data2(VIEW_TYPES[1:5], begin_date, end_date, service_type, 
        beta_ver, master_ver)
    rowx = write_xls(book, sheet, rowx, single_qos_headings, single_qos_data, 
        heading_xf, data_xf)
    rowx += 2
    print "step 2: ", current_time() - begin_time

    #
    # step 3: playtm
    #    
    playtm_headings = [u'播放时长(分钟)', 'P25', 'P50', 'P75', 'P90', 'P95', u'均值']
    playtm_data = get_playtm_data(begin_date, end_date, service_type, beta_ver, master_ver)
    rowx = write_xls(book, sheet, rowx, playtm_headings, playtm_data, 
        heading_xf, data_xf)
    rowx += 2
    print "step 3: ", current_time() - begin_time
    
    #
    # step 4: fbuffer
    #    
    fbuffer_headings = [u'首次缓冲时长(秒)', 'P25', 'P50', 'P75', 'P90', 'P95', u'均值']
    fbuffer_data = get_fbuffer_data(begin_date, end_date, service_type, beta_ver, master_ver)
    rowx = write_xls(book, sheet, rowx, fbuffer_headings, fbuffer_data, 
        heading_xf, data_xf)
    rowx += 2
    print "step 4: ", current_time() - begin_time
    
    # stuck
    stuck_headings = [u'卡缓冲', 'P25', 'P50', 'P75', 'P90', 'P95']
    stuck_data = get_tplayloading_data(begin_date, end_date, service_type, device_type, 
        version, version2, STUCK)
    rowx = write_xls(book, sheet, rowx, stuck_headings, stuck_data, 
        heading_xf, data_xf)
    rowx += 2

    # dbuffer
    dbuffer_headings = [u'拖动缓冲', 'P25', 'P50', 'P75', 'P90', 'P95']
    dbuffer_data = get_tplayloading_data(begin_date, end_date, service_type, device_type, 
        version, version2, DBUFFER)
    rowx = write_xls(book, sheet, rowx, dbuffer_headings, dbuffer_data, 
        heading_xf, data_xf)
    rowx += 2

    #
    # step 5: remarks
    #    
    remark_xf = ezxf('font: name Arial, colour Red')
    remarks = [u'备注: ', u'一次不卡比例：无卡顿播放次数/加载成功的播放次数', u'卡用户卡时间比：卡顿总时长/卡顿用户播放总时长',\
        u'缓冲异常值过滤：如果P95<3秒，则认为数据有问题', u'播放时长异常值过滤：如果P95小于30分钟，则认为数据有问题', \
        u'多天报表的算均值：算均值可能存在差错']
    rowx = write_remarks_to_xls(book, sheet, rowx, remarks, remark_xf)
    rowx += 2
    print "step 4: ", current_time() - begin_time
    
    logger.info("generate_report:  %s - %s, cost: %s" %
                (begin_date, end_date, (current_time() - begin_time)))
    print begin_date, end_date, beta_ver, current_time() - begin_time


@login_required
def pre_day_reporter(request, dev=""):
    (service_type, device_type, device_types, 
            version, versions, version2, versions2, begin_date, end_date) \
        = get_report_filter_param_values(request, "playinfo")
    context = {}
    context['default_service_type'] = service_type
    context['service_types'] = ["B2B", "B2C"]
    context['default_device_type'] = device_type
    context['device_types'] = device_types
    context['default_version'] = version
    context['versions'] = versions
    context['default_version2'] = version2
    context['versions2'] = versions2
    context['default_begin_date'] = str(begin_date)
    context['default_end_date'] = str(end_date)
    context['has_table'] = False
    response = render_to_response('show_daily_report.html', context)
    return response

def get_records_data_for_table(urls_suffix, begin_date, end_date, service_type, beta_ver, master_ver):
    datas = get_records_data(VIEW_TYPES[1:5], begin_date, end_date, service_type, beta_ver, master_ver)
    tables = []
    for i, data in enumerate(datas):
        item = {}
        item['click'] = True
        item['url'] = "tplay/show_playing_trend?%s" % (urls_suffix[i])
        item['data'] = data
        tables.append(item)
    return tables

def get_single_qos_data2_for_table(urls_suffix, begin_date, end_date, service_type, beta_ver, master_ver):
    datas = get_single_qos_data2(VIEW_TYPES[1:5], begin_date, end_date, service_type, beta_ver, master_ver)
    tables = []
    urls_prefix = ['show_fbuffer_sucratio?', 'show_fluency?', 
        'show_fluency_pratio?']
    for i, data in enumerate(datas):
        j = i
        if len(datas)==6:
            j /= 2
            i %= 2
        else:
            i = 0
        item = {}
        item['click'] = True
        item['url'] = "tplay/%s%s" % (urls_prefix[j], urls_suffix[i])
        item['data'] = data
        tables.append(item)
    return tables

def get_playtm_data_for_table(urls_suffix, begin_date, end_date, service_type, beta_ver, master_ver):
    datas = get_playtm_data(begin_date, end_date, service_type, beta_ver, master_ver)
    tables = []
    for i, data in enumerate(datas):
        if len(datas)==6:
            i %= 2
        else:
            i = 0
        item = {}
        item['click'] = True
        item['url'] = "tplay/show_play_time?%s" % (urls_suffix[i])
        item['data'] = data
        tables.append(item)
    return tables

def get_fbuffer_data_for_table(urls_suffix, begin_date, end_date, service_type, beta_ver, master_ver):
    datas = get_fbuffer_data(begin_date, end_date, service_type, beta_ver, master_ver)
    tables = []
    for i, data in enumerate(datas):
        if len(datas)==6:
            i %= 2
        else:
            i = 0
        item = {}
        item['click'] = True
        item['url'] = "tplay/show_fbuffer_time?%s" % (urls_suffix[i])
        item['data'] = data
        tables.append(item)
    return tables

def get_tplayloading_data(begin_date, end_date, service_type, device_type, version, version2, ttype):
    qos_data = []
    vers = []
    if len(version)>0:
        vers.append(version)
    if version != version2:
        vers.append(version2)
    view_types = VIEW_TYPES[1:2]
    for (view, second) in view_types:
        for ver in vers:
            begin_time = current_time()
            temp = [0 for i in range(6)]
            temp[0] = u"%s_%s-%s" % (device_type, ver, second)

            try:
                q_conditions = Q(ServiceType=service_type)
                q_conditions = q_conditions & Q(DeviceType=device_type)
                q_conditions = q_conditions & Q(VersionType=ver)
                version_id = VersionInfo.objects.get(q_conditions)

                q_conditions = Q(VersionId=version_id)
                q_conditions = q_conditions & Q(ISP='all') & Q(Area='all')
                q_conditions = q_conditions & Q(Hour=24) & Q(ChokeType=ttype)
                q_conditions = q_conditions & Q(Date__gte=begin_date) & Q(Date__lte=end_date)
                q_conditions = q_conditions & Q(ViewType=view)

                count = 0
                items = TPlayloadingInfo.objects.filter(q_conditions)
                for item in items:
                    if item.Records > 0:
                        temp[1]+=item.P25
                        temp[2]+=item.P50
                        temp[3]+=item.P75
                        temp[4]+=item.P90
                        temp[5]+=item.P95
                        count += 1
                if count > 0:
                    for i in range(6):
                        temp[i+1] = temp[i+1]/count
            except Exception, e:
                logger.info("tplayloading sql query exception, %s" % e)

            qos_data.append(temp)
            logger.info("execute tplayloading sql: ver: %s_%s, pnvalues, cost: %s" % (device_type, ver, 
                    (current_time() - begin_time)))

    return qos_data

def get_stuck_data_for_table(urls_suffix, begin_date, end_date, service_type, device_type, version, version2):
    datas = get_tplayloading_data(begin_date, end_date, service_type, device_type, version, version2, STUCK)
    tables  = []
    for i, data in enumerate(datas):
        i %= 2
        item = {}
        item['click'] = True
        item['url'] = "tplayloading/show_stuck?%s" % (urls_suffix[i])
        item['data'] = data
        tables.append(item)

    return tables

def get_dbuffer_data_for_table(urls_suffix, begin_date, end_date, service_type, device_type, version, version2):
    datas = get_tplayloading_data(begin_date, end_date, service_type, device_type, version, version2, DBUFFER)
    tables = []
    for i, data in enumerate(datas):
        i %= 2
        item = {}
        item['click'] = True
        item['url'] = 'tplayloading/show_dbuffer?%s' % (urls_suffix[i])
        item['data'] = data
        tables.append(item)

    return tables


def get_daily_report_tables(urls_suffix, begin_date, end_date, service_type, device_type, version, version2=""):
    tables = []
    (beta_ver, master_ver)=get_version_version2(device_type, version, version2)
    # 0. date-ver table
    table = HtmlTable()
    table.mtitle = "records信息"
    table.mheader = ['日期-版本']
    table.msub = []
    descs = get_desc_for_daily_report(begin_date, end_date, 
        beta_ver, master_ver)
    for desc in descs:
        item = {}
        item['click'] = False
        item['url'] = '' 
        item['data'] = desc
        table.msub.append(item)
    tables.append(table)

    # 1. record table
    table = HtmlTable()
    table.mtitle = "日期版本信息"
    table.mheader = ['记录数/版本', '点播', '回看', '直播', '连看', '总计'] 
    table.msub = get_records_data_for_table(urls_suffix, begin_date, 
        end_date, service_type, beta_ver, master_ver)
    tables.append(table)

    # 2. single Qos table
    table = HtmlTable()
    table.mtitle = "SingleQos信息"
    table.mheader = ['单指标QoS/版本', '点播', '回看', '直播', '连看']
    table.msub = get_single_qos_data2_for_table(urls_suffix, 
        begin_date, end_date, service_type, beta_ver, master_ver)
    tables.append(table)

    # 3. playtm table
    table = HtmlTable()
    table.mtitle = "playtm信息"
    table.mheader = ['播放时长(分钟)', 'P25', 'P50', 'P75', 'P90', 'P95', '均值']
    table.msub = get_playtm_data_for_table(urls_suffix, 
        begin_date, end_date, service_type, beta_ver, master_ver)
    tables.append(table)

    # 4. fbuffer table
    table = HtmlTable()
    table.mtitle = "fbuffer信息"
    table.mheader = ['首次缓冲时长(秒)', 'P25', 'P50', 'P75', 'P90', 'P95', '均值']
    table.msub = get_fbuffer_data_for_table(urls_suffix, 
        begin_date, end_date, service_type, beta_ver, master_ver)
    tables.append(table)

    # stcuk 
    table = HtmlTable()
    table.mtitle = "卡缓冲"
    table.mheader = ['卡缓冲(秒)', 'P25', 'P50', 'P75', 'P90', 'P95']
    table.msub = get_stuck_data_for_table(urls_suffix, 
        begin_date, end_date, service_type, device_type, version, version2)
    tables.append(table)

    # dbuffer
    table = HtmlTable()
    table.mtitle = "拖动缓冲"
    table.mheader = ['拖动缓冲(秒)', 'P25', 'P50', 'P75', 'P90', 'P95']
    table.msub = get_dbuffer_data_for_table(urls_suffix,
        begin_date, end_date, service_type, device_type, version, version2)
    tables.append(table)

    # 5. remarks table
    table = HtmlTable()
    table.mtitle = "备注信息"
    table.mheader = ['备注']
    table.msub = []
    datas = [
        ['点击表格可跳转到相应的Qos'],
        ['一次不卡比例：无卡顿播放次数/加载成功的播放次数'], ['卡用户卡时间比：卡顿总时长/卡顿用户播放总时长'],\
        ['缓冲异常值过滤：如果P95<3秒，则认为数据有问题'],
        ['播放时长异常值过滤：如果P95小于30分钟，则认为数据有问题'],
        ['多天报表的算均值：算均值可能存在差错']]
    for data in datas:
        item = {}
        item['click'] = False
        item['url'] = '' 
        item['data'] = data
        table.msub.append(item)
    
    tables.append(table)
    
    return tables

def get_version_version2(device_type, version, version2):
    if version != "All":
        version = '%s_%s' % (device_type, version) 
    else:
        version = device_type
    if version2 != "All":
        version2 = '%s_%s' % (device_type, version2) 
    else:
        version2 = device_type
    if version == version2:
        version2 = ""
    return (version, version2)


@login_required
def display_daily_reporter(request, dev=""):
    begin_time = current_time()
    (service_type, device_type, device_types, 
            version, versions, version2, versions2, begin_date, end_date) \
        = get_report_filter_param_values(request, "playinfo")
    context = {}
    context['default_service_type'] = service_type
    context['service_types'] = ["B2B", "B2C"]
    context['default_device_type'] = device_type
    context['device_types'] = device_types
    context['default_version'] = version
    context['versions'] = versions
    context['default_version2'] = version2
    context['versions2'] = versions2
    context['default_begin_date'] = str(begin_date)
    context['default_end_date'] = str(end_date)

    urls_suffix = ['service_type=%s&device_type=%s&version=%s&begin_date=%s&end_date=%s ' \
        % (service_type, device_type, version, begin_date, end_date), \
        'service_type=%s&device_type=%s&version=%s&begin_date=%s&end_date=%s' \
        % (service_type, device_type, version2, begin_date, end_date),]

    tables = get_daily_report_tables(urls_suffix, begin_date, end_date, 
        service_type, device_type, version, version2)
    context['has_table'] = True
    context['tables'] = tables

    response = render_to_response('show_daily_report.html', context)
    logger.info("generate report, cost: %s" % (current_time() - begin_time))

    return response

@login_required
def download_daily_reporter(request, dev=""):
    (service_type, device_type, device_types, version, versions, version2, \
        versions2, begin_date, end_date) = get_report_filter_param_values(request, "playinfo")

    xlwt_wb = xlwt.Workbook()
    generate_report(xlwt_wb, begin_date, end_date, service_type, device_type, version, version2)

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=%s_report_%s.xls' \
        % (version, begin_date)
    xlwt_wb.save(response)
    return response

def get_report_filter_param_values(request, table):
    service_type, device_type, device_types, version, versions, begin_date, end_date = get_filter_param_values(request)
    version2 = request.GET.get("version2", "").encode("utf-8")
    versions2 = versions
    return service_type, device_type, device_types, version, versions, version2, versions2, begin_date, end_date
