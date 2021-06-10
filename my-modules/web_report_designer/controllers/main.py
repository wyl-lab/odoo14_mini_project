# -*- coding: utf-8 -*-
import logging
import os, uuid, copy
from odoo import http
from odoo.exceptions import Warning
from odoo.http import request
from reportbro import Report, ReportBroError
import time
import datetime
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportbro.enums import DocElementType
import json

_logger = logging.getLogger(__name__)

page_list = [{
    "id": 10,
    "name": "页数",
    "type": "number",
    "eval": False,
    "pattern": "",
    "expression": "",
    "showOnlyNameType": True,
    "testData": ""
},
    {
        "id": 11,
        "name": "页码",
        "type": "number",
        "eval": False,
        "pattern": "",
        "expression": "",
        "showOnlyNameType": True,
        "testData": ""
    }]
Documentproperties = {  # 文档参数-固定
    "pageFormat": "user_defined",
    "pageWidth": "100",
    "pageHeight": "70",
    "unit": "mm",
    "orientation": "portrait",
    "contentHeight": "",
    "marginLeft": "0",
    "marginTop": "0",
    "marginRight": "0",
    "marginBottom": "0",
    "header": False,
    "headerSize": "60",
    "headerDisplay": "always",
    "footer": False,
    "footerSize": "60",
    "footerDisplay": "always",
    "patternLocale": "de",
    "patternCurrencySymbol": "￥"
}
Docelements = []  # 报表元素位置
Styles = []  # 样式


def string_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """文本数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "string",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData,
    }


def datetime_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """日期数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "string",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData,
    }


def date_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """日期数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "string",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData,
    }


def number_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """数字数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "number",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData or 0.0,
    }


def map_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """字典数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "map",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData,
        "children": []
    }


def array_struct(id, name, eval=False, pattern="", expression="", showOnlyNameType=False, testData=""):
    """列表数据集合"""
    return {
        "id": id,
        "name": name,
        "type": "array",
        "eval": eval,
        "pattern": pattern,
        "expression": expression,
        "showOnlyNameType": showOnlyNameType,
        "testData": testData,
        "children": []
    }


def error_raise(report, report_url=""):
    """报表错误返回"""
    error_info = ""
    for err in report.errors:
        if err.get('field') == 'content':
            error_info += err.get('info', '') + u"，"
        elif err.get('field') == 'data_source':
            error_info += u"表格没有选择数据源，"
        else:
            error_info += err.get('msg_key', '') + u"，"
    error_info += u"在系统中找不到，请重新选择"
    return request.make_response(json.dumps({'errors': error_info, 'report_url': report_url}), {
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/html; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
    })


class SheetController(http.Controller):

    @http.route(['/save/designer'], type='http', auth='user', csrf=False)
    def save_designer(self, **kw):
        """报表保存 """
        result = {'flag': False}
        try:
            if kw.get('active_id', False):
                model = request.env['report.designer'].browse(int(kw.get('active_id', 0)))
                model.write({'content': kw.get('content', '')})
                result['flag'] = True
        except Exception as e:
            _logger.info("save report designer occur error message %s" % str(e))
        return request.make_response(json.dumps(result), {
            'Cache-Control': 'no-cache',
            'Content-Type': 'text/html; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
        })

    @http.route(['/report/put'], type='http', auth='user', csrf=False)
    def report_put(self, **kw):
        json_data = json.loads(kw.get('info', ''))
        report_definition = json_data.get('report')
        output_format = json_data.get('outputFormat')
        if output_format not in ('pdf', 'xlsx'):
            raise Warning(u"无效的输出格式")
        data = json_data.get('data')
        is_test_data = bool(json_data.get('isTestData'))
        # 获取报表设计的URL***************
        action_id = request.env.ref("web_report_designer.action_report_designer_client").id
        menu_id = request.env.ref("web_report_designer.menu_report_designer_root").id
        url = "/web#action=%s&active_id=%s&menu_id=%s" % (action_id, json_data.get('designer_id', ''), menu_id)
        report_url = '<a href="%s">%s</a>' % (url, u"点击进行编辑")
        # 获取报表设计的URL***************
        now = datetime.datetime.now()
        # 查询数据库，将早的数据删除-本来就有8个小时的时差，大于8小时的会删除
        generate_ids = request.env['report.generate'].search(
            [('write_date', '<', (now - datetime.timedelta(hours=16)).strftime('%Y-%m-%d %H:%M:%S'))])
        generate_ids.unlink()
        # 1、设计报表的预览需要返回json数据进行alert提示
        # 2、报表打印的需要返回render页面进行提示
        f_path = os.path.split(os.path.realpath(__file__))[0]
        f_path = f_path.replace('\\', '/')
        rd = copy.deepcopy(report_definition['docElements'])
        if rd and isinstance(rd[0], dict):
            rd = [rd]
        for definition in rd:
            report_definition['docElements'] = definition
            report = Report(report_definition, data, is_test_data,
                            additional_fonts=[dict(value='Microsoft YaHei', filename=f_path + '/fonts/yahei.ttf')])
            if report.errors:
                return error_raise(report, report_url)
            try:
                report_file = report.generate_pdf()
            except ReportBroError as e:
                print(e)
                return error_raise(report, report_url)
            except Exception as e:
                print(e)
        report_definition['docElements'] = rd
        key = str(uuid.uuid4())
        request.env['report.generate'].create({
            'key': key,
            'report_definition': str(report_definition),
            'data': str(data),
            'is_test_data': is_test_data
        })
        return request.make_response(
            "key:" + key,
            headers=[
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS'),
                ('Access-Control-Allow-Headers',
                 'Origin, X-Requested-With, X-HTTP-Method-Override, Content-Type, Accept, Z-Key')
            ]
        )

    @http.route(['/report/get'], type='http', auth='user', csrf=False)
    def report_get(self, **kw):
        key = kw.get('key', '')
        report = None
        report_file = None
        if key and len(key) == 36:
            generate_id = request.env['report.generate'].search([('key', '=', key)], limit=1)
            if not generate_id:
                raise Warning(u"请重选选择打印")
            report_definition = eval(generate_id.report_definition)
            data = eval(generate_id.data)
            f_path = os.path.split(os.path.realpath(__file__))[0]
            f_path = f_path.replace('\\', '/')
            now = datetime.datetime.now()
            if kw.get('outputFormat', 'xlsx') == 'xlsx':
                report_file = report.generate_xlsx()
                return request.make_response(
                    report_file,
                    headers=[
                        ('Access-Control-Allow-Origin', '*'),
                        ('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS'),
                        ('Access-Control-Allow-Headers',
                         'Origin, X-Requested-With, X-HTTP-Method-Override, Content-Type, Accept, Z-Key'),
                        ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                        ('Content-Disposition',
                         'inline; filename="{filename}"'.format(filename='report-' + str(now) + '.xlsx')),
                    ]
                )
            else:
                filenames = []
                root_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
                root_path = os.path.join(root_path, 'pdf')
                rd = copy.deepcopy(report_definition['docElements'])
                for index, definition in enumerate(rd):
                    report_definition['docElements'] = definition
                    report = Report(report_definition, data, generate_id.is_test_data, additional_fonts=[
                        dict(value='Microsoft YaHei', filename=f_path + '/fonts/yahei.ttf')])
                    filename = os.path.join(root_path, key + str(index) + '.pdf')
                    filenames.append(filename)
                    report_file = report.generate_pdf(filename)
                output = PdfFileWriter()
                outputPages = 0
                streams = []
                for each in filenames:
                    e = open(each, "rb")
                    input = PdfFileReader(e)
                    pageCount = input.getNumPages()
                    outputPages += pageCount
                    for iPage in range(0, pageCount):
                        output.addPage(input.getPage(iPage))
                    streams.append(e)
                merge_filename = os.path.join(root_path, key + str(len(rd)) + '.pdf')
                with open(merge_filename, 'wb') as mf:
                    output.write(mf)
                with open(merge_filename, 'rb') as pdfdocument:
                    report_file = pdfdocument.read()
                for s in streams:
                    s.close()
                for each in filenames:
                    os.remove(each)
                os.remove(merge_filename)
                return request.make_response(
                    report_file,
                    headers=[
                        ('Access-Control-Allow-Origin', '*'),
                        ('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS'),
                        ('Access-Control-Allow-Headers',
                         'Origin, X-Requested-With, X-HTTP-Method-Override, Content-Type, Accept, Z-Key'),
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition',
                         'inline; filename="{filename}"'.format(filename='report-' + str(now) + '.pdf')),
                    ]
                )

    @http.route(['/report/designer'], type='http', auth='user')
    def report_designer(self, **kw):
        """报表设计"""
        designer = request.env['report.designer'].browse(int(kw.get('active_id')))
        if designer.content:
            content = designer.content.replace('false', 'False')
            content = content.replace('true', 'True')
            content = content.replace('"pattern":null', '"pattern":""')
            data = eval(content)
            docElements = data['docElements']
            styles = data['styles']
            documentProperties = data['documentProperties']
            parametersAdd = data['parameters']
        else:
            docElements = copy.deepcopy(Docelements)
            styles = copy.deepcopy(Styles)
            documentProperties = copy.deepcopy(Documentproperties)
            parametersAdd = []
        dates = []
        model_obj = request.env[designer.model]
        ir_obj = request.env['ir.model']
        field_obj = request.env['ir.model.fields']
        model_id = request.env['ir.model'].search([('model', '=', designer.model)], limit=1).id
        id = 13
        for doc in docElements:
            id = max(id, doc.get('id', 0))
            for d in ['headerData', 'footerData']:
                if doc.get(d, False):
                    id = max(id, doc[d].get('id', 0))
                    for column in doc[d].get('columnData', []):
                        id = max(id, column.get('id', 0))
            for d in ['contentDataRows', ]:
                for di in doc.get(d, []):
                    id = max(id, di.get('id', 0))
                    for column in di.get('columnData', []):
                        id = max(id, column.get('id', 0))
        id += 1
        parameters = copy.deepcopy(page_list)
        order = map_struct(12, model_obj._description)
        parameters.append(order)
        for name, field in model_obj._fields.items():
            manual_field = field_obj.search(
                [('model_id', '=', model_id), ('name', '=', name), ('show_report', '=', True)])
            if manual_field or getattr(field, 'show_report', False):
                att = model_obj.fields_get([name])[name]
                type = att['type']
                if type == 'char' or type == 'text' or type == 'binary':
                    order['children'].append(string_struct(id, att['string']))
                    id += 1
                elif type == 'datetime':
                    dates.append(att['string'])
                    order['children'].append(datetime_struct(id, att['string'],
                                                             pattern=self.get_parameter_pattern(att['string'],
                                                                                                parametersAdd)))
                    id += 1
                elif type == 'date':
                    dates.append(att['string'])
                    order['children'].append(date_struct(id, att['string'],
                                                         pattern=self.get_parameter_pattern(att['string'],
                                                                                            parametersAdd)))
                    id += 1
                elif type == 'selection':
                    order['children'].append(string_struct(id, att['string']))
                    id += 1
                elif type == 'float' or type == 'integer' or type == 'monetary':
                    order['children'].append(number_struct(id, att['string'],
                                                           pattern=self.get_parameter_pattern(att['string'],
                                                                                              parametersAdd)))
                    id += 1
                elif type == 'many2one':
                    m2o = map_struct(id, att['string'])
                    id += 1
                    model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                    for name2, field2 in request.env[att['relation']]._fields.items():
                        manual_field2 = field_obj.search(
                            [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                        if manual_field2 or getattr(field2, 'show_report', False):
                            m2o_att = request.env[att['relation']].fields_get([name2])[name2]
                            if m2o_att['type'] in ['char', 'text', 'date', 'datetime', 'selection', 'binary']:
                                m2o['children'].append(string_struct(id, m2o_att['string']))
                                id += 1
                            elif m2o_att['type'] in ['float', 'integer', 'monetary']:
                                m2o['children'].append(number_struct(id, m2o_att['string'],
                                                                     pattern=self.get_parameter_pattern(
                                                                         m2o_att['string'], parametersAdd,
                                                                         parent=att['string'])))
                                id += 1
                    parameters.append(m2o)
                elif type == 'many2many':
                    order['children'].append(string_struct(id, att['string']))
                    id += 1
                elif type == 'one2many':
                    o2m = array_struct(id, att['string'])
                    id += 1
                    testData = "[{"
                    sequence = 1
                    for line in model_obj[name]:
                        model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                        for name2, field2 in request.env[att['relation']]._fields.items():
                            manual_field2 = field_obj.search(
                                [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                            if manual_field2 or getattr(field2, 'show_report', False):
                                o2m_att = request.env[att['relation']].fields_get([name2])[name2]
                                testData += "\"" + o2m_att['string'] + "\":\"" + str("") + "\","
                        testData += "\"" + u"序号" + "\":\"" + str(sequence) + "\"}"
                        sequence += 1
                    testData += "]"
                    o2m['testData'] = testData
                    model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                    for name2, field2 in request.env[att['relation']]._fields.items():
                        manual_field2 = field_obj.search([('model_id', '=', model_id2), ('name', '=', name2),
                                                          ('show_report', '=', True)])  # ('state','=','manual')
                        if manual_field2 or getattr(field2, 'show_report', False):
                            o2m_att = request.env[att['relation']].fields_get([name2])[name2]
                            if o2m_att['type'] in ['integer', 'float', 'monetary']:
                                o2m['children'].append(number_struct(id, o2m_att['string'],
                                                                     pattern=self.get_parameter_pattern(
                                                                         o2m_att['string'], parametersAdd,
                                                                         parent=att['string'])))
                            else:
                                o2m['children'].append(string_struct(id, o2m_att['string']))
                            id += 1
                    o2m['children'].append(string_struct(id, u"序号"))
                    id += 1
                    parameters.append(o2m)
        for pa in parametersAdd:
            if pa.get('type') == 'map':
                for p in pa.get('children', []):
                    if p.get('type') in ['date', 'sum', 'average'] and p.get('name', False) not in dates:
                        p['id'] = id
                        id += 1
                        order['children'].append(p)
        data = {
            "docElements": docElements,
            "parameters": parameters,
            "styles": styles,
            "version": 3,
            "documentProperties": documentProperties
        }
        return request.render("web_report_designer.designer_index", {'model': 'sale.order', 'model_ids': [1, 2, 3],
                                                                     'data': json.dumps(data, ensure_ascii=False)})

    @http.route(['/report/print'], type='http', auth='user')
    def report_print(self, **kw):
        """报表打印"""
        if not kw.get('designer_id', False):
            return ""
        active_ids = json.loads(kw.get('active_ids', ''))
        id = 12
        yy = 0
        docElements = []
        parameters = copy.deepcopy(page_list)
        dates = []
        model_obj = request.env[kw.get('model', '')]
        ir_obj = request.env['ir.model']
        field_obj = request.env['ir.model.fields']
        model_id = ir_obj.search([('model', '=', kw.get('model', ''))], limit=1).id
        designer = request.env['report.designer'].browse(int(kw.get('designer_id', 0)))
        if designer.content:
            dContent = designer.content.replace('false', 'False')
            dContent = dContent.replace('true', 'True')
            dContent = dContent.replace('"pattern":null', '"pattern":""')
            eContent = eval(dContent)
            documentProperties = eContent['documentProperties']
            parametersAdd = eContent['parameters']
            styles = eContent['styles']
        else:
            eContent = ''
            styles = copy.deepcopy(Styles)
            documentProperties = copy.deepcopy(Documentproperties)
            parametersAdd = []
        for doc in docElements:
            id = max(id, doc.get('id', 0))
            for d in ['headerData', 'footerData']:
                if doc.get(d, False):
                    id = max(id, doc[d].get('id', 0))
                    for column in doc[d].get('columnData', []):
                        id = max(id, column.get('id', 0))
            for d in ['contentDataRows', ]:
                for di in doc.get(d, []):
                    id = max(id, di.get('id', 0))
                    for column in di.get('columnData', []):
                        id = max(id, column.get('id', 0))
        id += 1
        model_objs = model_obj.browse(active_ids)
        parametersDict = {}
        for index, model_obj in enumerate(model_objs):
            if eContent:
                content = copy.deepcopy(eContent['docElements'])
            else:
                content = []
            order = map_struct(model_obj.id * 10 ** len(str(id)) + id, model_obj._description + str(model_obj.id))
            id += 1
            for c in content:
                if 'content' in c.keys():
                    c['content'] = c['content'].replace('${' + model_obj._description,
                                                        '${' + model_obj._description + str(model_obj.id))
                if 'source' in c.keys():
                    c['source'] = c['source'].replace('${' + model_obj._description,
                                                      '${' + model_obj._description + str(model_obj.id))
                if 'dataSource' in c.keys():
                    c['dataSource'] = c['dataSource'].replace('${' + model_obj._description,
                                                              '${' + model_obj._description + str(model_obj.id))
                if c.get('headerData', False):
                    for column in c['headerData'].get('columnData', []):
                        if 'content' in column.keys():
                            column['content'] = column['content'].replace('${' + model_obj._description,
                                                                          '${' + model_obj._description + str(
                                                                              model_obj.id))
                if c.get('contentDataRows', []):
                    for cdr in c.get('contentDataRows', []):
                        for column in cdr.get('columnData', []):
                            if 'content' in column.keys():
                                column['content'] = column['content'].replace('${' + model_obj._description,
                                                                              '${' + model_obj._description + str(
                                                                                  model_obj.id))
                if c.get('footerData', False):
                    for column in c['footerData'].get('columnData', []):
                        if 'content' in column.keys():
                            column['content'] = column['content'].replace('${' + model_obj._description,
                                                                          '${' + model_obj._description + str(
                                                                              model_obj.id))
            parameters.append(order)
            parametersDict[model_obj._description + str(model_obj.id)] = {}
            for name, field in model_obj._fields.items():
                manual_field = field_obj.search(
                    [('model_id', '=', model_id), ('name', '=', name), ('show_report', '=', True)])
                if manual_field or getattr(field, 'show_report', False):
                    att = model_obj.fields_get([name])[name]
                    type = att['type']
                    if type == 'char' or type == 'text' or type == 'binary':
                        order['children'].append(string_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'],
                                                               testData=model_obj[name] or ''))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = model_obj[
                                                                                                        name] or ''
                        id += 1
                    elif type == 'datetime':
                        if model_obj[name]:
                            dd = (model_obj[name] + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            dd = ''
                        dates.append(att['string'])
                        order['children'].append(
                            datetime_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'], testData=dd,
                                            pattern=self.get_parameter_pattern(att['string'], parametersAdd)))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = dd
                        id += 1
                    elif type == 'date':
                        if model_obj[name]:
                            dd = model_obj[name].strftime('%Y-%m-%d')
                        else:
                            dd = ''
                        dates.append(att['string'])
                        order['children'].append(
                            date_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'], testData=dd,
                                        pattern=self.get_parameter_pattern(att['string'], parametersAdd)))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = dd
                        id += 1
                    elif type == 'selection':
                        order['children'].append(string_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'],
                                                               testData=dict(s for s in att['selection'])[
                                                                   model_obj[name]] if model_obj[name] else ''))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = \
                        dict(s for s in att['selection'])[model_obj[name]] if model_obj[name] else ''
                        id += 1
                    elif type == 'float' or type == 'integer' or type == 'monetary':
                        order['children'].append(number_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'],
                                                               testData=model_obj[name] or '',
                                                               pattern=self.get_parameter_pattern(att['string'],
                                                                                                  parametersAdd)))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = model_obj[
                                                                                                        name] or ''
                        id += 1
                    elif type == 'many2one':
                        m2o = map_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'] + str(model_obj.id))
                        id += 1
                        for c in content:
                            if 'content' in c.keys():
                                c['content'] = c['content'].replace('${' + att['string'],
                                                                    '${' + att['string'] + str(model_obj.id))
                            if 'dataSource' in c.keys():
                                c['dataSource'] = c['dataSource'].replace('${' + att['string'],
                                                                          '${' + att['string'] + str(model_obj.id))
                            if c.get('headerData', False):
                                for column in c['headerData'].get('columnData', []):
                                    if 'content' in column.keys():
                                        column['content'] = column['content'].replace('${' + att['string'],
                                                                                      '${' + att['string'] + str(
                                                                                          model_obj.id))
                            if c.get('contentDataRows', []):
                                for cdr in c.get('contentDataRows', []):
                                    for column in cdr.get('columnData', []):
                                        if 'content' in column.keys():
                                            column['content'] = column['content'].replace('${' + att['string'],
                                                                                          '${' + att['string'] + str(
                                                                                              model_obj.id))
                            if c.get('footerData', False):
                                for column in c['footerData'].get('columnData', []):
                                    if 'content' in c.keys():
                                        column['content'] = column['content'].replace('${' + att['string'],
                                                                                      '${' + att['string'] + str(
                                                                                          model_obj.id))
                        parametersDict[att['string'] + str(model_obj.id)] = {}
                        model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                        for name2, field2 in request.env[att['relation']]._fields.items():
                            manual_field2 = field_obj.search(
                                [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                            if manual_field2 or getattr(field2, 'show_report', False):
                                m2o_att = request.env[att['relation']].fields_get([name2])[name2]
                                if m2o_att['type'] in ['char', 'text', 'date', 'datetime', 'float', 'integer',
                                                       'monetary', 'binary']:
                                    m2o['children'].append(
                                        string_struct(model_obj.id * 10 ** len(str(id)) + id, m2o_att['string'],
                                                      testData=str(model_obj[name][name2] or '')))
                                    parametersDict[att['string'] + str(model_obj.id)][m2o_att['string']] = str(
                                        model_obj[name][name2] or '')
                                    id += 1
                                elif m2o_att['type'] == 'selection':
                                    m2o['children'].append(
                                        string_struct(model_obj.id * 10 ** len(str(id)) + id, m2o_att['string'],
                                                      testData=dict(s for s in m2o_att['selection'])[
                                                          model_obj[name][name2]] if model_obj[name][name2] else ''))
                                    parametersDict[att['string'] + str(model_obj.id)][m2o_att['string']] = \
                                    dict(s for s in m2o_att['selection'])[model_obj[name][name2]] if model_obj[name][
                                        name2] else ''
                                    id += 1
                        parameters.append(m2o)
                    elif type == 'many2many':
                        mstr = ""
                        for line in model_obj[name]:
                            mstr += line.name_get()[0][1] or ""
                            mstr += ","
                        mstr = mstr.rstrip(',')
                        order['children'].append(
                            string_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'], testData=mstr))
                        parametersDict[model_obj._description + str(model_obj.id)][att['string']] = mstr
                        id += 1
                    elif type == 'one2many':
                        o2m = array_struct(model_obj.id * 10 ** len(str(id)) + id, att['string'] + str(model_obj.id))
                        for c in content:
                            if 'content' in c.keys():
                                c['content'] = c['content'].replace('${' + att['string'],
                                                                    '${' + att['string'] + str(model_obj.id))
                            if 'dataSource' in c.keys():
                                c['dataSource'] = c['dataSource'].replace('${' + att['string'],
                                                                          '${' + att['string'] + str(model_obj.id))
                            if c.get('headerData', False):
                                for column in c['headerData'].get('columnData', []):
                                    if 'content' in column.keys():
                                        column['content'] = column['content'].replace('${' + att['string'],
                                                                                      '${' + att['string'] + str(
                                                                                          model_obj.id))
                            if c.get('contentDataRows', []):
                                for cdr in c.get('contentDataRows', []):
                                    for column in cdr.get('columnData', []):
                                        if 'content' in column.keys():
                                            column['content'] = column['content'].replace('${' + att['string'],
                                                                                          '${' + att['string'] + str(
                                                                                              model_obj.id))
                            if c.get('footerData', False):
                                for column in c['footerData'].get('columnData', []):
                                    if 'content' in column.keys():
                                        column['content'] = column['content'].replace('${' + att['string'],
                                                                                      '${' + att['string'] + str(
                                                                                          model_obj.id))
                        parametersDict[att['string'] + str(model_obj.id)] = []
                        id += 1
                        testData = "["
                        sequence = 1
                        sort_id = request.env['report.designer.sort'].search(
                            [('create_uid', '=', request.env.uid), ('model_name', '=', att['relation'])], limit=1,
                            order="id desc")
                        if sort_id:
                            lines = [i for i in model_obj[name]]
                            sort_fields = eval(sort_id.field_name)
                            sort_fields = list(reversed(sort_fields))
                            for field_name in sort_fields:
                                if field_name[0] == '-':
                                    reverse = True
                                    field_name = field_name[1:]
                                else:
                                    reverse = False
                                o2m_att = request.env[att['relation']].fields_get([field_name])[field_name]
                                if o2m_att['type'] == 'many2one':
                                    lines.sort(key=lambda r: r[field_name].name_get()[0][1], reverse=reverse)
                                else:
                                    lines.sort(key=lambda r: r[field_name], reverse=reverse)
                        else:
                            lines = model_obj[name]
                        for line in lines:
                            testData += "{"
                            linfo = {}
                            model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                            for name2, field2 in request.env[att['relation']]._fields.items():
                                manual_field2 = field_obj.search(
                                    [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                                if manual_field2 or getattr(field2, 'show_report', False):
                                    o2m_att = request.env[att['relation']].fields_get([name2])[name2]
                                    if o2m_att['type'] == 'many2one':
                                        testData += "\"" + o2m_att['string'] + "\":\"" + str(
                                            line[name2].name_get()[0][1] or "" if line[name2] else "") + "\","
                                        linfo[o2m_att['string']] = str(
                                            line[name2].name_get()[0][1] or "" if line[name2] else "")
                                    elif o2m_att['type'] == 'many2many':
                                        mstr = ""
                                        for l in line[name2]:
                                            mstr += l.name_get()[0][1] or ""
                                            mstr += ","
                                        mstr = mstr.rstrip(',')
                                        testData += "\"" + o2m_att['string'] + "\":\"" + mstr + "\","
                                        linfo[o2m_att['string']] = mstr
                                    elif o2m_att['type'] in ['char', 'text', 'date', 'datetime', 'binary']:
                                        testData += "\"" + o2m_att['string'] + "\":\"" + str(line[name2] or "") + "\","
                                        linfo[o2m_att['string']] = str(line[name2] or "")
                                    elif o2m_att['type'] == 'selection':
                                        testData += "\"" + o2m_att['string'] + "\":\"" + str(
                                            dict(s for s in o2m_att['selection'])[line[name2]] if line[
                                                name2] else '') + "\","
                                        linfo[o2m_att['string']] = str(
                                            dict(s for s in o2m_att['selection'])[line[name2]] if line[name2] else '')
                                    elif o2m_att['type'] in ['float', 'integer', 'monetary']:
                                        testData += "\"" + o2m_att['string'] + "\":\"" + str(line[name2] or "") + "\","
                                        linfo[o2m_att['string']] = line[name2] or 0.0
                            testData += "\"" + u"序号" + "\":\"" + str(sequence) + "\"},"
                            linfo[u"序号"] = str(sequence)
                            parametersDict[att['string'] + str(model_obj.id)].append(linfo)
                            sequence += 1
                        testData = testData.rstrip(',')
                        testData += "]"
                        o2m['testData'] = testData
                        model_id2 = ir_obj.search([('model', '=', request.env[att['relation']]._name)], limit=1).id
                        for name2, field2 in request.env[att['relation']]._fields.items():
                            manual_field2 = field_obj.search(
                                [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                            if manual_field2 or getattr(field2, 'show_report', False):
                                o2m_att = request.env[att['relation']].fields_get([name2])[name2]
                                if o2m_att['type'] in ['float', 'monetary']:
                                    o2m['children'].append(
                                        number_struct(model_obj.id * 10 ** len(str(id)) + id, o2m_att['string'],
                                                      pattern=self.get_parameter_pattern(o2m_att['string'],
                                                                                         parametersAdd,
                                                                                         parent=att['string'])))
                                else:
                                    o2m['children'].append(
                                        string_struct(model_obj.id * 10 ** len(str(id)) + id, o2m_att['string']))
                                id += 1
                        o2m['children'].append(string_struct(model_obj.id * 10 ** len(str(id)) + id, u"序号"))
                        parameters.append(o2m)
            y = 0
            for elem in content:
                elem['id'] = model_obj.id * 10 ** len(str(id)) + id
                # elem['y'] += yy
                id += 1
                y = max(y, elem.get('height', 10) + elem.get('y', 0))
                if elem.get('headerData', False):
                    elem['headerData']['id'] = model_obj.id * 10 ** len(str(id)) + id
                    id += 1
                    for column in elem['headerData'].get('columnData', []):
                        column['id'] = model_obj.id * 10 ** len(str(id)) + id
                        id += 1
                if elem.get('footerData', False):
                    elem['footerData']['id'] = model_obj.id * 10 ** len(str(id)) + id
                    id += 1
                    for column in elem['footerData'].get('columnData', []):
                        column['id'] = model_obj.id * 10 ** len(str(id)) + id
                        id += 1
                if elem.get('contentDataRows', []):
                    for cdr in elem.get('contentDataRows', []):
                        cdr['id'] = model_obj.id * 10 ** len(str(id)) + id
                        id += 1
                        for column in cdr.get('columnData', []):
                            column['id'] = model_obj.id * 10 ** len(str(id)) + id
                            id += 1
            yy = y
            docElements.append(content)
            for pa in parametersAdd:
                if pa.get('type') == 'map':  # 还差表头的优化
                    for pat in pa.get('children', []):
                        if pat.get('type') in ['date', 'sum', 'average'] and pat.get('name', False) not in dates:
                            p = copy.deepcopy(pat)
                            if p['expression']:
                                p['expression'] = p['expression'].replace('.', str(model_obj.id) + '.')
                            if p['type'] == 'date':
                                nw = time.strftime('%Y-%m-%d %H:%M:%S')
                                if p['pattern'] == 'yyyy-MM-dd hh:mm:ss':
                                    expression = (datetime.datetime.strptime(nw,
                                                                             '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                                        hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                                elif p['pattern'] == 'yyyy-MM-dd':
                                    expression = (datetime.datetime.strptime(nw,
                                                                             '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                                        hours=8)).strftime('%Y-%m-%d')
                                elif p['pattern'] == 'yyyy/M/d':
                                    expression = (datetime.datetime.strptime(nw,
                                                                             '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                                        hours=8)).strftime('%Y/%m/%d')
                                elif p['pattern'] == 'yyyy/M/d hh:mm':
                                    expression = (datetime.datetime.strptime(nw,
                                                                             '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                                        hours=8)).strftime('%Y/%m/%d %H:%M')
                                else:
                                    expression = (datetime.datetime.strptime(nw,
                                                                             '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                                        hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                                p['id'] = id
                                order['children'].append(
                                    string_struct(model_obj.id * 10 ** len(str(id)) + id, p['name'],
                                                  testData=expression))
                                parametersDict[model_obj._description + str(model_obj.id)][p['name']] = expression
                                id += 1
                            else:
                                p['id'] = id
                                order['children'].append(p)
                                parametersDict[model_obj._description + str(model_obj.id)][p['name']] = ''
                                id += 1
        # documentProperties['contentHeight'] = str(y)
        data = {
            "docElements": docElements,
            "parameters": parameters,
            "styles": styles,
            "version": 3,
            "documentProperties": documentProperties
        }
        return request.render("web_report_designer.designer_preview",
                              {'designer_id': designer.id, 'parameters': json.dumps(parametersDict, ensure_ascii=False),
                               'model': 'sale.order', 'model_ids': [1, 2, 3],
                               'data': json.dumps(data, ensure_ascii=False)})

    # def get_sbpl(self, data, parametersDict):
    #
    #     lst = []
    #     rd = data['docElements']
    #     documentProperties = data['documentProperties']
    #     parametersAdd = data['parameters']
    #     styles = data['styles']
    #     f_path = os.path.split(os.path.realpath(__file__))[0]
    #     f_path = f_path.replace('\\', '/')
    #     sbplData = copy.deepcopy(data)
    #     if rd and isinstance(rd[0], dict):
    #         rd = [rd]
    #     for definition in rd:
    #         sbplData['docElements'] = definition
    #         report = Report(sbplData, parametersDict, True, additional_fonts=[dict(value='Microsoft YaHei', filename=f_path + '/fonts/yahei.ttf')])
    #         cmd = report.generate_sbpl()
    #         lst.append(cmd)
    #     return lst

    def get_parameter_pattern(self, name, parameters, parent=""):
        """获取页面设置的格式"""
        value = ""
        for parameter in parameters:
            if parent and parameter.get('name', "") == parent:
                for child in parameter.get('children', []):
                    if child.get('name', "") == name:
                        value = child.get('pattern', "")
                        break
            elif parameter.get('name', "") == name:
                value = child.get('pattern', "")
                break
        return value or ""
