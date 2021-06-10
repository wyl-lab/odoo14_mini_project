# -*- coding: utf-8 -*-
import base64
import copy
import datetime
import os
import time

from reportbro import Report

from odoo import models, fields, api, tools

from ..controllers.main import page_list, Styles, Documentproperties, map_struct, \
    string_struct, datetime_struct, date_struct, number_struct, array_struct
from odoo.modules import get_module_resource


class ReportDesignerSort(models.Model):
    _name = 'report.designer.sort'
    _description = u"报表排序"

    model_name = fields.Char(u"模型名称")
    field_name = fields.Char(u"排序字段说明")

    def sort_field_model(self, model_name, field_name):
        if model_name in self.env['report.designer'].get_sort_model():
            self.create({'model_name': model_name, 'field_name': field_name})

    def clean_field_model(self, model_name):
        self.search([('create_uid', '=', self.env.uid), ('model_name', '=', model_name)]).unlink()


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    show_report = fields.Boolean(u"报表显示")


class IrActionsReportXml(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[("pdf_designer", u"PDF设计器")], ondelete={'pdf_designer': 'cascade'})
    designer_id = fields.Many2one('report.designer', string=u"报表设计")


class ReportGenerate(models.Model):
    _name = 'report.generate'
    _description = u"报表生成"

    key = fields.Char(u"键值")
    report_definition = fields.Text(u"报表")
    data = fields.Text(u"数据")
    is_test_data = fields.Boolean(u"测试文本")


class ReportDesigner(models.Model):
    _name = 'report.designer'
    _inherit = 'image.mixin'
    _rec_name = 'name'
    _order = 'name asc,id desc'
    _description = u"报表设计"

    name = fields.Char(u"报表名称", required=True)
    content = fields.Text(u"报表设计")
    model = fields.Selection([], string=u"报表对象", required=True)

    @api.model
    def _get_default_image(self):
        img_path = get_module_resource('web_report_designer', 'static/src/img', 'report.png')
        with open(img_path, 'rb') as f:
            image = f.read()
        return base64.b64encode(image)

    @api.model
    def create(self, vals):
        if not vals.get('image_1920'):
            vals['image_1920'] = self._get_default_image()
        designer_id = super(ReportDesigner, self).create(vals)
        vals = {
            'designer_id': designer_id.id,
            'report_type': 'pdf_designer',
            'name': vals['name'],
            'model': vals['model'],
            'report_name': vals['model'],
        }
        report_id = self.env['ir.actions.report'].create(vals)
        report_id.create_action()
        return designer_id

    def write(self, vals):
        if 'name' in vals.keys():
            for designer in self:
                report_id = self.env['ir.actions.report'].search([('designer_id', '=', designer.id)], limit=1)
                if report_id:
                    translation_id = self.env['ir.translation'].search(
                        [('res_id', '=', report_id.id), ('value', '=', report_id.name),
                         ('name', '=', 'ir.actions.report,name')], limit=1)
                    if translation_id:
                        translation_id.write({'value': vals['name']})
                    report_id.write({'name': vals['name']})
        if 'model' in vals.keys():
            for designer in self:
                report_id = self.env['ir.actions.report'].search([('designer_id', '=', designer.id)], limit=1)
                if report_id:
                    report_id.write({'model': vals['model'], 'report_name': vals['model']})
        return super(ReportDesigner, self).write(vals)

    def unlink(self):
        for designer in self:
            report_ids = self.env['ir.actions.report'].search([('designer_id', '=', designer.id)])
            if report_ids:
                report_ids.unlink_action()
                report_ids.unlink()
        return super(ReportDesigner, self).unlink()

    def do_report_designer(self):
        return self.env.ref('web_report_designer.action_report_designer_client').read()[0]

    def pdf_designer_controller(self, action):
        context = self._context
        action_id = action['id']
        report = self.env['ir.actions.report'].browse(action_id)
        final_url = "/report/print?model=%s&active_ids=%s&designer_id=%s" % (
            context['active_model'], context['active_ids'], report.designer_id.id or '')
        return {'type': 'ir.actions.act_url', 'url': final_url, 'target': 'new'}

    def get_sort_model(self):
        return []

    def report_print(self, model, active_ids, rotate, sbpl):
        """报表打印"""
        id = 12
        yy = 0
        docElements = []
        parameters = copy.deepcopy(page_list)
        dates = []
        model_obj = self.env[model]
        ir_obj = self.env['ir.model']
        field_obj = self.env['ir.model.fields']
        model_id = ir_obj.search([('model', '=', model)], limit=1).id
        designer = self
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
                        model_id2 = ir_obj.search([('model', '=', self.env[att['relation']]._name)], limit=1).id
                        for name2, field2 in self.env[att['relation']]._fields.items():
                            manual_field2 = field_obj.search(
                                [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                            if manual_field2 or getattr(field2, 'show_report', False):
                                m2o_att = self.env[att['relation']].fields_get([name2])[name2]
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
                                        dict(s for s in m2o_att['selection'])[model_obj[name][name2]] if \
                                        model_obj[name][
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
                        sort_id = self.env['report.designer.sort'].search(
                            [('create_uid', '=', self.env.uid), ('model_name', '=', att['relation'])], limit=1,
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
                                o2m_att = self.env[att['relation']].fields_get([field_name])[field_name]
                                if o2m_att['type'] == 'many2one':
                                    lines.sort(key=lambda r: r[field_name].name_get()[0][1], reverse=reverse)
                                else:
                                    lines.sort(key=lambda r: r[field_name], reverse=reverse)
                        else:
                            lines = model_obj[name]
                        for line in lines:
                            testData += "{"
                            linfo = {}
                            model_id2 = ir_obj.search([('model', '=', self.env[att['relation']]._name)], limit=1).id
                            for name2, field2 in self.env[att['relation']]._fields.items():
                                manual_field2 = field_obj.search(
                                    [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                                if manual_field2 or getattr(field2, 'show_report', False):
                                    o2m_att = self.env[att['relation']].fields_get([name2])[name2]
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
                        model_id2 = ir_obj.search([('model', '=', self.env[att['relation']]._name)], limit=1).id
                        for name2, field2 in self.env[att['relation']]._fields.items():
                            manual_field2 = field_obj.search(
                                [('model_id', '=', model_id2), ('name', '=', name2), ('show_report', '=', True)])
                            if manual_field2 or getattr(field2, 'show_report', False):
                                o2m_att = self.env[att['relation']].fields_get([name2])[name2]
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
            "documentProperties": documentProperties,
            "rotate": rotate,
        }
        if sbpl:
            return self.get_sbpl(data, parametersDict)
        else:
            return []

    def get_sbpl(self, data, parametersDict):

        lst = []
        rd = data['docElements']
        documentProperties = data['documentProperties']
        parametersAdd = data['parameters']
        styles = data['styles']
        f_path = os.path.join(
            os.path.join(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'controllers'), 'fonts'), 'yahei.ttf')
        sbplData = copy.deepcopy(data)
        if rd and isinstance(rd[0], dict):
            rd = [rd]
        for definition in rd:
            sbplData['docElements'] = definition
            report = Report(sbplData, parametersDict, True,
                            additional_fonts=[dict(value='Microsoft YaHei', filename=f_path)])
            cmd = report.generate_sbpl()
            lst.append(bytes(cmd, encoding='utf-8'))
        return lst

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
