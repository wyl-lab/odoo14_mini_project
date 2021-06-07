# -*- coding: utf-8 -*-
from odoo import http


class Laboratory(http.Controller):
    @http.route('/laboratory/laboratory/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/laboratory/laboratory/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('laboratory.listing', {
            'root': '/laboratory/laboratory',
            'objects': http.request.env['laboratory.laboratory'].search([]),
        })

    @http.route('/laboratory/laboratory/objects/<model("laboratory.laboratory"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('laboratory.object', {
            'object': obj
        })
