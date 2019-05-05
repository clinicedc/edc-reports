import os

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import TableStyle, Paragraph

from .report import Report


class CrfPdfReport(Report):

    default_page = dict(
        rightMargin=1.0 * cm,
        leftMargin=1.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.5 * cm,
        pagesize=A4,
    )

    logo = os.path.join(
        settings.STATIC_ROOT or os.path.dirname(os.path.abspath(__file__)),
        "edc_reports", "clinicedc_logo.jpg"),
    logo_dim = {"first_page": (0.83 * cm, 0.83 * cm),
                "later_pages": (0.625 * cm, 0.625 * cm)}

    model_attr = "object"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_model_cls = get_user_model()
        self.bg_cmd = ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey)

    @property
    def title(self):
        verbose_name = getattr(self, self.model_attr).verbose_name.upper()
        subject_identifier = getattr(self, self.model_attr).subject_identifier
        return f"{verbose_name} FOR {subject_identifier}"

    def draw_end_of_report(self, story):
        story.append(Paragraph(f"- End of report -",
                               self.styles["line_label_center"]))

    def get_user(self, obj, field=None):
        field = field or "user_created"
        try:
            user = self.user_model_cls.objects.get(
                username=getattr(obj, field))
        except ObjectDoesNotExist:
            user_created = getattr(obj, field)
        else:
            user_created = f"{user.first_name} {user.last_name}"
        return user_created

    def on_first_page(self, canvas, doc):
        super().on_first_page(canvas, doc)
        width, height = A4
        canvas.drawImage(self.logo, 35, height - 50,
                         *self.logo_dim["first_page"])

        if self.confidential:
            canvas.setFont("Helvetica", 10)
            canvas.drawRightString(
                width - 35, height - 50, "CONFIDENTIAL")

        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(width - 35, height - 40, self.title)

    def on_later_pages(self, canvas, doc):
        super().on_later_pages(canvas, doc)
        width, height = A4
        canvas.drawImage(self.logo, 35, height - 40,
                         *self.logo_dim["later_pages"])
        if self.confidential:
            canvas.setFont("Helvetica", 10)
            canvas.drawRightString(
                width - 35, height - 45, "CONFIDENTIAL")
        if self.title:
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(width - 35, height - 35, self.title)

    def set_table_style(self, t, bg_cmd=None):
        cmds = [
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
        ]
        if bg_cmd:
            cmds.append(bg_cmd)
        t.setStyle(TableStyle(cmds))
        t.hAlign = "LEFT"
        return t

    def history_change_message(self, obj):
        LogEntry = django_apps.get_model('admin.logentry')
        log_entry = (
            LogEntry.objects.filter(
                action_time__gte=obj.modified, object_id=str(obj.id)
            )
            .order_by("action_time")
            .first()
        )
        try:
            return log_entry.get_change_message()
        except AttributeError:
            return None
