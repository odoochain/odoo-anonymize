import os
from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.tools.sql import column_exists
from odoo.exceptions import UserError, RedirectWarning, ValidationError
import logging

logger = logging.getLogger(__name__)


class Anonymizer(models.AbstractModel):
    _name = "frameworktools.anonymizer"

    @api.model
    def rename_logins(self):
        self.env.cr.execute("select id, login from res_users where id > 2;")
        for rec in self.env.cr.fetchall():
            login = f"user{rec[0]}"
            self.env.cr.execute(
                "update res_users set login = %s where id=%s", (login, rec[0])
            )

    @api.model
    def _run(self):
        if os.environ["DEVMODE"] != "1":
            return

        self.rename_logins()
        self.env["ir.model.fields"]._apply_default_anonymize_fields()

        for field in self.env["ir.model.fields"].search([("anonymize", "!=", False)]):
            try:
                obj = self.env[field.model]
            except KeyError:
                continue
            table = obj._table
            cr = self.env.cr
            if not column_exists(cr, table, field.name):
                logger.info(f"Ignoring not existent column: {table}:{field.name}")
                continue

            cr.execute(f"select id, {field.name} from {table} order by id desc")
            recs = cr.fetchall()
            logger.info(f"Anonymizing {len(recs)} records of {table}")
            for rec in recs:
                v = rec[1] or ""
                v = field._anonymize_value(v)
                cr.execute(
                    f"update {table} set {field.name} = %s where id = %s",
                    (
                        v,
                        rec[0],
                    ),
                )
