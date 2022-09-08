/** @odoo-module **/

import relationalFields from "web.relational_fields";
import fieldRegistry from "web.field_registry";
import { qweb } from "web.core";

/*
* This update represents an ugnly hack to overcome 'Discard behavior' which doesn't influence domain appearance
* So, we have to suboptimmally make rpc for each re-render
*/
const checklistBoxes = relationalFields.FieldMany2ManyCheckBoxes.extend({
    /*
     * Re-write to trigger domain update and in case of discard to show correct items
    */
    async _render() {
        var self = this;
        this.m2mValues = await this._rpc({
            model: this.record.fields[this.name].relation,
            method: "name_search",
            args: ["", this.record.getDomain({fieldName: this.name})],
            context: this.record.getContext({fieldName: this.name}),
        })
        this.$el.html(qweb.render(this.template, {widget: this}));
        _.each(this.value.res_ids, function (id) {
            self.$('input[data-record-id="' + id + '"]').prop('checked', true);
        });
        this.$("input").prop("disabled", this.hasReadonlyModifier);    
    },
});


fieldRegistry.add('many2many_checklist_boxes', checklistBoxes);

export default checklistBoxes;
