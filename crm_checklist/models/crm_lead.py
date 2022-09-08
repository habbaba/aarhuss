#coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


REGRESS_WARNING = _(u"The opportunity '{}' cannot be moved back to stage '{}'. This stage does not allow regress!")
STAGEVALIDATIONERRORMESSAGE = _(u"""Please enter the checklist for the opportunity '{0}'!
You can't move this case forward until you confirm all jobs have been done on the stage '{1}'. Not done checkpoints: 
 * {2}""")

class crm_lead(models.Model):
    _inherit = "crm.lead"

    @api.depends(
        "stage_id", "stage_id.default_crm_check_list_ids", "check_list_line_ids", "team_id", 
        "stage_id.default_crm_check_list_ids.team_ids",
    )
    def _compute_check_list_len(self):
        """
        Compute method for 'check_list_len' & 'checklist_progress'

        Methods:
         * _get_filtered of crm.check.list

        Extra info:
         * we filter 'check_list_line_ids' by active stage to overcome cached checpoints in case of stage change
        """
        for lead_id in self:
            stage_id = lead_id.stage_id
            team_id = lead_id.team_id
            default_crm_check_list_ids = stage_id and \
                stage_id.default_crm_check_list_ids._get_filtered(stage_id, team_id) or self.env["crm.check.list"]
            check_list_len = len(default_crm_check_list_ids)
            check_list_line_ids = lead_id.check_list_line_ids._get_filtered(stage_id, team_id)
            lead_id.check_list_len = check_list_len
            lead_id.checklist_progress = check_list_len and (len(check_list_line_ids)/check_list_len)*100 or 0.0

    check_list_line_ids = fields.Many2many(
        "crm.check.list",
        "crm_lead_crm_check_list_rel_table",
        "crm_lead_id",
        "crm_check_list_id",
        string="Check list",
        help="Confirm that you finished all the points. Otherwise, you would not be able to move the lead forward",
        copy=False,
    )
    check_list_history_ids = fields.One2many(
        "crm.check.history", 
        "lead_id",
        string="History",
        copy=False,
    )
    check_list_len = fields.Integer(
        string="Total points",
        compute= _compute_check_list_len, 
        store=True,
        copy=False,
    )
    checklist_progress = fields.Float(
        string="Progress", 
        compute=_compute_check_list_len,
        store=True,
        copy=False,
    )

    @api.model
    def create(self, vals):
        """
        Overwrite to check whether the check list is pre-filled and check whether this user might do that

        Methods:
         * _get_initial_stage
        """
        # simulate create with default stage and no chekpoints (so we consider transfer default stage > new stage)
        new_values = {}
        if vals.get("stage_id"):
            default_stage_id = self._get_initial_stage(vals.get("team_id"))
            if default_stage_id and vals.get("stage_id") != default_stage_id.id:
                new_values.update({"stage_id": vals.get("stage_id")})
                vals.update({"stage_id": default_stage_id.id})
        if vals.get("check_list_line_ids"):
            new_values.update({"check_list_line_ids": vals.get("check_list_line_ids")})
            vals.pop("check_list_line_ids")
        task_id = super(crm_lead, self).create(vals)

        # write new stage and checkpoints to trigger checks
        if new_values:
            task_id.write(new_values)
        return task_id

    def write(self, vals):
        """
        Overwrite to check:
         1. if check item is entered: whether a user has rights for that
         2. if stage is changed: whether a check list is filled (in case of progress)

        Methods:
         * _check_cheklist_rights of check.list
         * _register_history
         * _check_regress_possible
         * _check_checklist_complete
         * _recover_filled_checklist
        """
        def _get_team_from_vals(s_vals):
            """
            The method to browse team from vals

            Returns:
             * crm.team object or False (if empty team is written)
             * None if not written
            """
            team_id = s_vals.get("team_id")
            if team_id:
                team_id = self.env["crm.team"].browse(team_id)
            return team_id

        # 1
        if vals.get("check_list_line_ids") and not self.env.context.get("automatic_checks"):
            new_check_line_ids = self.env["crm.check.list"].browse(vals.get("check_list_line_ids")[0][2])
            for lead_id in self:
                old_check_line_ids = lead_id.check_list_line_ids
                to_add_items = (new_check_line_ids - old_check_line_ids)
                to_remove_items = (old_check_line_ids - new_check_line_ids)
                changed_items = to_add_items | to_remove_items
                changed_items._check_cheklist_rights()
                lead_id._register_history(to_add_items, "done")
                lead_id._register_history(to_remove_items, "reset")
        # 2
        if vals.get("stage_id"):
            self._check_regress_possible(vals)
            team_id = _get_team_from_vals(vals)
            self._check_checklist_complete(vals, team_id)
            self._recover_filled_checklist(vals.get("stage_id"))
        return super(crm_lead, self).write(vals)

    @api.model
    def _get_initial_stage(self, team_id):
        """
        The method to find default stage based on written team

        Args:
         * team_id - int

        Reutrns:
         * crm.stage object
        """
        if team_id:
            search_domain = ["|", ("team_id", "=", False), ("team_id", "=", team_id)]
        else:
            search_domain = [("team_id", "=", False)]
        search_domain.append(("fold", "=", False))
        return self.env["crm.stage"].search(search_domain, order="sequence", limit=1)   

    def _register_history(self, changed_items, done_action="done"):
        """
        The method to register check list history by leads

        Args:
         * changed_items - dict of filled in or reset items
         * done_action - either 'done', or 'reset'
        """
        for lead_id in self:
            for item in changed_items:
                history_item_vals = {
                    "lead_id": lead_id.id,
                    "check_list_id": item.id,
                    "done_action": done_action,
                }
                self.env["crm.check.history"].create(history_item_vals)

    def _check_regress_possible(self, vals):
        """
        The method to check whether it is regress, and if yes whether the stage allows that

        Args:
         * vals - dict of of written values
        """
        if not self.env.user.has_group("crm_checklist.group_crm_checklist_superuser") and not self.env.su:
            new_stage_id = self.env["crm.stage"].browse(vals.get("stage_id"))
            if new_stage_id.forbid_back_progress:
                for lead_id in self:
                    if new_stage_id.sequence < lead_id.stage_id.sequence:
                        raise ValidationError(REGRESS_WARNING.format(lead_id.name, new_stage_id.name))

    def _check_checklist_complete(self, vals, team_id):
        """
        The method to make sure checklist is filled in case of lead progress

        Args:
         * vals - dict of of written values
         * team_id - crm.team object or None or False

        Methods:
         * _get_filtered of crm.check.list
        """
        if not self.env.user.has_group("crm_checklist.group_crm_checklist_superuser") and not self.env.su:
            new_stage_id = self.env["crm.stage"].browse(vals.get("stage_id"))
            for lead_id in self:
                if team_id is not None:
                    new_team_id = v_team_id
                else:
                    new_team_id = lead_id.team_id
                prev_stage_id = lead_id.stage_id
                if prev_stage_id != new_stage_id and new_stage_id.sequence >= prev_stage_id.sequence \
                        and not new_stage_id.no_need_for_checklist:
                    written_checkpoints = vals.get("check_list_line_ids")
                    if written_checkpoints:
                        written_checkpoints = written_checkpoints[0][2]
                    else:
                        written_checkpoints = lead_id.check_list_line_ids.ids
                    # written checkpoints should relate to the previous stage
                    done_checkpoints = self.env["crm.check.list"].browse(written_checkpoints)
                    done_checkpoints = done_checkpoints._get_filtered(prev_stage_id, new_team_id)
                    # calculate real checkpoints & what is not done 
                    required_checkpoints = prev_stage_id and prev_stage_id.default_crm_check_list_ids._get_filtered(
                        prev_stage_id, new_team_id
                    ) or self.env["crm.check.list"]
                    not_done_checkpoints = required_checkpoints - done_checkpoints
                    if not_done_checkpoints:
                        not_done_warning = "\n * ".join(not_done_checkpoints.mapped("name"))
                        raise ValidationError(STAGEVALIDATIONERRORMESSAGE.format(
                            lead_id.name, 
                            lead_id.stage_id.name,
                            not_done_warning,
                        ))

    def _recover_filled_checklist(self, stage_id):
        """
        The method to recover already done check list from history

        Args:
         * stage_id - int - new crm.stage.type (required)
        """
        for lead_id in self:
            to_recover = []
            already_considered = []
            for history_item in lead_id.check_list_history_ids:
                check_item_id = history_item.check_list_id
                if check_item_id.crm_stage_st_id.id == stage_id \
                        and not check_item_id.should_be_reset \
                        and check_item_id.id not in already_considered \
                        and history_item.done_action == "done":
                    to_recover.append(check_item_id.id)
                already_considered.append(check_item_id.id)
            lead_id.with_context(automatic_checks=True).check_list_line_ids = [(6, 0, to_recover)]
