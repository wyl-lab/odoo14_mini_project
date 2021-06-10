odoo.define('report.web_report_designer', function (require) {
// var ControlPanelMixin = require('web.ControlPanelMixin');
var ActionManager = require('web.ActionManager');
var AbstractAction = require('web.AbstractAction');
var rpc = require('web.rpc');
// var Widget = require('web.Widget');
var core = require('web.core');

var _t = core._t;

	ActionManager.include({
	    _executeReportAction: function(action, options) {
	        var self = this;
	        action = _.clone(action);
	        if (action && action.report_type == 'pdf_designer') {
				return rpc.query({
					model: 'report.designer',
					method: 'pdf_designer_controller',
					args: [false, action],
					kwargs: {context: action.context},
				}).then(function (result) {
					return self.do_action(result);
				});
	        } else {
	        	return self._super(action, options);
	        }
	    }
	});

	var report_designer = AbstractAction.extend({
		hasControlPanel: true,
		init: function(parent, action, options) {
	        // this.actionManager = parent;
	        this.designer_id = action.params && action.params.active_id || action.context && action.context.active_id || false;
	        if (action.name == undefined){
	        	action.name = "报表设计"

			}
	        return this._super.apply(this, arguments);
	    },

	    start: function() {
	    	// this.update_cp();
	    	var url = "<iframe src='/report/designer?active_id=" + this.designer_id + "' class='o_content' style='border: none;margin-top: -35px'/>";
	    	this.$el.html(url);
	        return this._super.apply(this, arguments);
	    },

	    // update_cp: function() {//加载面包屑
		// 	var status = {
		// 		cp_content: this.cp_content,
		// 		title: this.getTitle() || '报表设计',
		// 	};
	    //     return this.updateControlPanel();
	    // },

	    do_show: function() {
	        this._super();
	        // this.update_cp();
	    },
	    
	});
	core.action_registry.add("report_designer", report_designer);
	return report_designer;
});
