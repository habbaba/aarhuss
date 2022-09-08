# -*- coding: utf-8 -*-
{
    "name": "CRM Check List and Approval Process",
    "version": "15.0.1.2.1",
    "category": "Sales",
    "author": "faOtools",
    "website": "https://faotools.com/apps/15.0/crm-check-list-and-approval-process-624",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "crm"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/crm_stage.xml",
        "views/crm_lead.xml",
        "views/crm_chek_list.xml",
        "data/data.xml"
    ],
    "assets": {
        "web.assets_backend": [
                "crm_checklist/static/src/js/many2many_checkboxes.js"
        ]
},
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The tool to make sure required jobs are carefully done on each CRM pipeline stage. CRM checklists",
    "description": """
For the full details look at static/description/index.html

* Features * 




#odootools_proprietary

    """,
    "images": [
        "static/description/main.png"
    ],
    "price": "28.0",
    "currency": "EUR",
    "live_test_url": "https://faotools.com/my/tickets/newticket?&url_app_id=14&ticket_version=15.0&url_type_id=3",
}