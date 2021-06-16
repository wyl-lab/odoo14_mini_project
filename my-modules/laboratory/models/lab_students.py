# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import api, fields, models, _


class LabReport(models.AbstractModel):
    _name = 'laboratory.report.studentsrecords'
    _description = 'Lab Students Report'

    sID = fields.Char()
    sName = fields.Char()
    sSex = fields.Char()
    def _get_data_from_report(self, data):
        res = []
        Students = self.env['laboratory.students']
        res.append(Students.search())
        # if 'sID' in data:
        #     res.append({'data': [
        #         self._get_leaves_summary(data['date_from'], stu.id, data['holiday_type'])
        #         for sID in Students.browse(data['sID'])
        #     ]})
        return res

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        data['sID'] = self.env.context.get('sID_ids', [])
        students = self.env['laboratory.students'].browse(data['sID'])
        datas = {
            'ids': [],
            'model': 'laboratory.students',
            'form': data,
        }
        return self.env.ref('laboratory.report_studentsrecords').report_action(students, data=datas)

    def _get_students_status(self):
        res = []
        for stu in self.env['laboratory.students'].search([]):
            res.append({'id': stu.sID, 'name': stu.sName})
        return res

    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        # get the report action back as we will need its data
        students_report = self.env['ir.actions.report']._get_report_from_name('laboratory.report_studentsrecords')
        # get the records selected for this rendering of the report
        obj = self.env[students_report.model].browse(docids)
        # return a custom rendering context
        return {
            # 'lines': docids.get_lines()
            # 'doc_ids': self.ids,
            'doc_model': students_report.model,
            # 'get_data_from_report': self._get_data_from_report(data['form']),
            'get_students_status': self._get_students_status(),
        }
