#coding: utf-8

from odoo import fields, models

class crm_stage(models.Model):
    """
    Overwrite to add checklist and checklist settings
    """
    _inherit = "crm.stage"

    default_crm_check_list_ids = fields.One2many(
        "crm.check.list",
        "crm_stage_st_id",
        string="Check List",
    )
    no_need_for_checklist = fields.Boolean(
        string="No need for checklist",
        help="If checked, when you move a lead TO this stage, no checklist is required (e.g. for 'Cancelled')"
    )
    forbid_back_progress = fields.Boolean(
        string="Forbid regress to this stage",
        help="If checked, moving a lead back TO this stage from further stages would be impossible",
    )
